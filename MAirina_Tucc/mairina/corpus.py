"""Word index built from the read-only lyrics corpus (spec section 4 hygiene)."""

from __future__ import annotations

import hashlib
import pickle
import re
import sqlite3
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote

from mairina import DATA_DIR, DEFAULT_LYRICS_DB

CACHE_VERSION = 3
DROP_UPOS = frozenset({"PUNCT", "X", "SYM", "NUM"})
LANE_COHORTS = {"drill": ("drill_trap",), "pop": ("pop",), "all": None}
# Artist-name spellings seen in the corpus that songs.* columns do not spell exactly.
EXTRA_ARTIST_TOKENS = frozenset({"senida", "senidah", "jalom", "lamelo", "balkaton", "biba"})


class DbUnavailable(Exception):
    """lyrics.db is missing or cannot be opened (CLI exit code 2)."""


def open_ro(db_path: Path | str | None = None) -> sqlite3.Connection:
    """Open lyrics.db strictly read-only (immutable URI, never written)."""
    path = Path(db_path or DEFAULT_LYRICS_DB)
    if not path.is_file():
        raise DbUnavailable(f"lyrics.db not found. Expected at: {path}")
    uri = "file:" + quote(path.resolve().as_posix(), safe="/:") + "?mode=ro&immutable=1"
    try:
        return sqlite3.connect(uri, uri=True)
    except sqlite3.Error as exc:
        raise DbUnavailable(f"cannot open lyrics.db at {path}: {exc}") from exc


@dataclass
class Index:
    """forms[form] = {lemma, upos, freq, freq_by_cohort, freq_by_artist, n_songs}"""

    forms: dict[str, dict]
    db_path: str = ""
    db_mtime_ns: int = 0
    artist_names: frozenset = frozenset()
    bigrams: frozenset = frozenset()     # attested (word, next word) pairs; never whole lines
    _vocab_cache: dict = field(default_factory=dict, repr=False, compare=False)
    _preds: dict = field(default_factory=dict, repr=False, compare=False)

    def predecessors(self) -> dict[str, frozenset]:
        """next word -> words seen directly before it (derived from `bigrams`)."""
        if not self._preds:
            acc: dict[str, set] = {}
            for a, b in self.bigrams:
                acc.setdefault(b, set()).add(a)
            self._preds.update({b: frozenset(v) for b, v in acc.items()})
        return self._preds

    def freq(self, form: str, lane: str = "all", artists=None) -> int:
        """Frequency in the lane; with an artist lens, in (lane AND artists)."""
        e = self.forms.get(form)
        if not e:
            return 0
        cohorts = LANE_COHORTS[lane]
        if not artists:
            return e["freq"] if cohorts is None else sum(e["freq_by_cohort"].get(c, 0) for c in cohorts)
        return sum(n for c, per in e["freq_by_cohort_artist"].items()
                   if cohorts is None or c in cohorts
                   for a, n in per.items() if a in artists)

    def vocab(self, lane: str = "all", artists=None) -> dict[str, int]:
        """{form: freq} for forms in the lane and artist lens, minus artist-name tokens."""
        key = (lane, tuple(sorted(artists or ())))
        if key not in self._vocab_cache:
            out = {}
            for form in self.forms:
                if form in self.artist_names:
                    continue
                f = self.freq(form, lane, artists)
                if f > 0:
                    out[form] = f
            self._vocab_cache[key] = out
        return self._vocab_cache[key]


def artist_tokens(con) -> frozenset:
    """Lowercased name tokens of songs.primary_artist / target_artist (split on space, hyphen, 'x')."""
    out = set(EXTRA_ARTIST_TOKENS)
    for col in ("primary_artist", "target_artist"):
        for (name,) in con.execute(f"SELECT DISTINCT {col} FROM songs WHERE {col} IS NOT NULL"):
            for tok in re.split(r"[\s\-]+", name.lower()):
                tok = "".join(c for c in tok if c.isalpha())
                if tok and tok != "x":
                    out.add(tok)
    return frozenset(out)


def _build(db_path: Path) -> tuple[dict[str, dict], frozenset, frozenset]:
    sql = (
        "SELECT t.form, t.lemma, t.upos, s.genre_cohort, s.target_artist, s.id, t.line_id, t.ordinal "
        "FROM tokens t JOIN lines l ON l.id = t.line_id "
        "JOIN sections sec ON sec.id = l.section_id "
        "JOIN songs s ON s.id = sec.song_id "
        "WHERE t.source_script = 'latin' ORDER BY t.line_id, t.ordinal"
    )
    acc: dict[str, dict] = {}
    bigrams: set = set()
    prev = None                               # (line_id, ordinal, key) of the last kept token
    con = open_ro(db_path)
    try:
        for form, lemma, upos, cohort, artist, sid, line_id, ordinal in con.execute(sql):
            if upos in DROP_UPOS or not form:
                continue
            key = form.strip().lower()
            if not key.isalpha():
                continue
            key = sys.intern(key)
            if prev and prev[0] == line_id and ordinal == prev[1] + 1:
                bigrams.add((prev[2], key))   # adjacent kept tokens of one line
            prev = (line_id, ordinal, key)
            a = acc.get(key)
            if a is None:
                a = acc[key] = {
                    "lemmas": Counter(), "uposes": Counter(), "freq": 0,
                    "cohort": Counter(), "artist": Counter(), "ca": {}, "songs": set(),
                }
            a["lemmas"][(lemma or key).strip().lower()] += 1
            a["uposes"][upos or "X"] += 1
            a["freq"] += 1
            a["cohort"][cohort or "none"] += 1
            a["artist"][artist or "none"] += 1
            per = a["ca"].setdefault(cohort or "none", Counter())
            per[artist or "none"] += 1
            a["songs"].add(sid)
        names = artist_tokens(con)
    finally:
        con.close()
    forms = {}
    for key, a in acc.items():
        lemma = sorted(a["lemmas"].items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        upos = sorted(a["uposes"].items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        forms[key] = {
            "lemma": lemma, "upos": upos, "freq": a["freq"],
            "freq_by_cohort": dict(a["cohort"]), "freq_by_artist": dict(a["artist"]),
            "freq_by_cohort_artist": {c: dict(per) for c, per in a["ca"].items()},
            "n_songs": len(a["songs"]),
        }
    return forms, names, frozenset(bigrams)


def _cache_path(db_path: Path, cache_dir: Path) -> Path:
    tag = hashlib.sha1(str(db_path.resolve()).encode("utf-8")).hexdigest()[:8]
    return cache_dir / f"index_{tag}.pkl"


def load_index(db_path: Path | str | None = None, cache_dir: Path | str | None = None,
               rebuild: bool = False) -> Index:
    """Load the word index, using the pickle cache while lyrics.db is unchanged."""
    path = Path(db_path or DEFAULT_LYRICS_DB)
    if not path.is_file():
        raise DbUnavailable(f"lyrics.db not found. Expected at: {path}")
    st = path.stat()
    cdir = Path(cache_dir or DATA_DIR)
    cfile = _cache_path(path, cdir)
    if not rebuild and cfile.is_file():
        try:
            with open(cfile, "rb") as fh:
                blob = pickle.load(fh)
            if (blob.get("version") == CACHE_VERSION and blob.get("mtime_ns") == st.st_mtime_ns
                    and blob.get("size") == st.st_size):
                return Index(blob["forms"], str(path), st.st_mtime_ns, blob["artist_names"],
                             blob["bigrams"])
        except Exception:
            pass  # corrupt or stale cache: rebuild below
    forms, names, bigrams = _build(path)
    try:
        cdir.mkdir(parents=True, exist_ok=True)
        with open(cfile, "wb") as fh:
            pickle.dump({"version": CACHE_VERSION, "mtime_ns": st.st_mtime_ns,
                         "size": st.st_size, "forms": forms,
                         "artist_names": names, "bigrams": bigrams}, fh, protocol=pickle.HIGHEST_PROTOCOL)
    except OSError:
        pass  # cache is an optimisation only
    return Index(forms, str(path), st.st_mtime_ns, names, bigrams)
