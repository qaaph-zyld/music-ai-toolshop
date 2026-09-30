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

CACHE_VERSION = 4
DROP_UPOS = frozenset({"PUNCT", "X", "SYM", "NUM"})
LANE_COHORTS = {"drill": ("drill_trap",), "pop": ("pop",), "all": None}
# MAirina reads only the Serbian rap corpus; lyrics.db also holds English/other
# corpora (ccmixter, gutenberg_pd, hymnary, lrclib, mudcat-digitrad, sacred-texts)
# which must never leak into the vocabulary, bigrams, gazetteer or targets.
CORPORA = ("genius-pro",)
MIN_TOKEN_COVERAGE = 0.9
# Artist-name spellings seen in the corpus that songs.* columns do not spell exactly.
EXTRA_ARTIST_TOKENS = frozenset({"senida", "senidah", "jalom", "lamelo", "balkaton", "biba"})


class DbUnavailable(Exception):
    """lyrics.db is missing or cannot be opened (CLI exit code 2)."""


class CorpusNotAnnotated(DbUnavailable):
    """lyrics.db exists but has (almost) no CLASSLA tokens for CORPORA."""


def _corpus_sql(alias: str = "s") -> str:
    """SQL fragment restricting to the allowed corpora: ' AND s.corpus IN (...)'."""
    return f" AND {alias}.corpus IN ({','.join(repr(c) for c in CORPORA)})"


def check_annotated(con, db_path: Path | str | None = None) -> None:
    """Refuse to build from a corpus whose CLASSLA layer is absent or partial.

    Coverage = allowed-corpus lines carrying >=1 token / allowed-corpus lines
    with non-empty text_norm. Below MIN_TOKEN_COVERAGE the index would be empty
    or silently partial, so we raise instead of building or caching it.
    """
    base = ("FROM lines l JOIN sections sec ON sec.id = l.section_id "
            "JOIN songs s ON s.id = sec.song_id "
            "WHERE length(trim(coalesce(l.text_norm, ''))) > 0" + _corpus_sql("s"))
    non_empty = con.execute(f"SELECT COUNT(*) {base}").fetchone()[0]
    covered = con.execute(
        f"SELECT COUNT(*) {base} AND EXISTS (SELECT 1 FROM tokens t WHERE t.line_id = l.id)"
    ).fetchone()[0]
    if non_empty == 0 or covered < MIN_TOKEN_COVERAGE * non_empty:
        raise CorpusNotAnnotated(
            f"lyrics.db has no CLASSLA tokens for {', '.join(CORPORA)} - "
            "run: toolshop lyrics annotate --resume")


def build_guarded(db_path: Path, work):
    """Run `work()` only while nobody else writes lyrics.db.

    The immutable=1 URI assumes no concurrent writer. In WAL mode a reader
    also leaves a -wal/-shm pair behind, so a 0-byte -wal (and any -shm) is
    not a writer signal: refuse on a -journal or a non-empty -wal, and retry
    once (then raise) when the file changes mid-build — a cache built on a
    moving file would be corrupt but look valid.
    """
    for _ in range(2):
        if Path(str(db_path) + "-journal").exists():
            raise DbUnavailable(
                f"lyrics.db is being written ({db_path.name}-journal present) - "
                "retry when the writer finishes")
        wal = Path(str(db_path) + "-wal")
        if wal.exists() and wal.stat().st_size > 0:
            raise DbUnavailable(
                f"lyrics.db is being written ({db_path.name}-wal non-empty) - "
                "retry when the writer finishes")
        st0 = db_path.stat()
        result = work()
        st1 = db_path.stat()
        if (st0.st_mtime_ns, st0.st_size) == (st1.st_mtime_ns, st1.st_size):
            return result
    raise DbUnavailable(f"lyrics.db changed during the build ({db_path}) - retry")


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
        q = f"SELECT DISTINCT {col} FROM songs s WHERE s.{col} IS NOT NULL" + _corpus_sql("s")
        for (name,) in con.execute(q):
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
        "WHERE t.source_script = 'latin'" + _corpus_sql("s") +
        " ORDER BY t.line_id, t.ordinal"
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
    def _work():
        con = open_ro(path)
        try:
            check_annotated(con, path)
        finally:
            con.close()
        return _build(path)

    forms, names, bigrams = build_guarded(path, _work)
    try:
        cdir.mkdir(parents=True, exist_ok=True)
        with open(cfile, "wb") as fh:
            pickle.dump({"version": CACHE_VERSION, "mtime_ns": st.st_mtime_ns,
                         "size": st.st_size, "forms": forms,
                         "artist_names": names, "bigrams": bigrams}, fh, protocol=pickle.HIGHEST_PROTOCOL)
    except OSError:
        pass  # cache is an optimisation only
    return Index(forms, str(path), st.st_mtime_ns, names, bigrams)
