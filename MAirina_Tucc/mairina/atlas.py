"""Device atlas: how often the corpus artists use each device. STATS ONLY.

One read-only pass over the corpus lines (``corpus.CORPORA``) runs the same
``devices`` rules the X-ray uses and keeps nothing but running counters, sums
and sums of squares, per lane and per ``target_artist``. No line, no song id,
no section id ever enters the blob or the printed table, so the cache is safe
to keep and nothing in the output can quote a lyric.

The per-lane ``numeric`` block ({feature: mean/std/n}) is also the prior the
personal fingerprint shrinks toward (``fingerprint.fingerprint``).

Verse-level devices (anaphora, multisyllabic rhyme) are computed per corpus
section with the very rules ``devices.analyze_verse`` uses (shared helpers);
that is an approximation of the real verse, declared here.
"""

from __future__ import annotations

import hashlib
import math
import os
import pickle
import re
import sys
from collections import Counter
from pathlib import Path

from toolshop.syllables import count_line

from mairina import DATA_DIR, corpus, devices
from mairina.used import tokenize

ATLAS_VERSION = 1
MIN_ARTIST_LINES = 30           # an artist with fewer corpus lines gets no row
KINDS = ("simile", "anaphora", "allit", "internal", "code_switch", "name_drop", "multi")
# atlas counter -> device kind(s) on the line (anaphora/multi come from the section scan)
_LINE_KIND = {"simile": "simile", "allit": "alliteration", "internal": "internal_rhyme",
              "code_switch": "code_switch", "name_drop": "name_drop"}
_CYRILLIC = re.compile("[Ѐ-ӿ]")      # phonetics is Latin-only: skip such lines


class _Acc:
    """Running tallies for one scope (a lane or an artist). No line is kept."""

    def __init__(self):
        self.n = 0
        self.counts = dict.fromkeys(KINDS, 0)
        self.cons = 0.0
        self.syl: Counter = Counter()
        self.sums = {f: [0.0, 0.0] for f in devices.NUMERIC_FEATURES}     # sum, sum of squares

    def add(self, hits, feats: dict, syl: int) -> None:
        self.n += 1
        for k in hits:
            self.counts[k] += 1
        self.cons += feats["cons_density"]
        self.syl[syl] += 1
        for f, acc in self.sums.items():
            x = float(feats[f])
            acc[0] += x
            acc[1] += x * x

    def median_syl(self) -> float | None:
        if not self.n:
            return None
        lo, hi, seen = None, None, 0
        for v in sorted(self.syl):
            seen += self.syl[v]
            if lo is None and seen >= (self.n + 1) // 2:
                lo = v
            if seen >= self.n // 2 + 1:
                hi = v
                break
        return (lo + hi) / 2 if self.n % 2 == 0 else float(hi)

    def result(self) -> dict:
        n = self.n
        numeric = {}
        for f, (s, ss) in self.sums.items():
            mean = s / n if n else 0.0
            numeric[f] = {"mean": mean, "std": math.sqrt(max(0.0, ss / n - mean * mean)) if n else 0.0,
                          "n": n}
        return {"n_lines": n, "counts": dict(self.counts),
                "cons_mean": self.cons / n if n else 0.0,
                "median_syl": self.median_syl(), "numeric": numeric}


def _section(buf, cohort, artist, lanes, artists, gazetteer, index) -> None:
    """Analyse one corpus section and fold the per-line results into the tallies."""
    rows = [(t, s) for t, s in buf if not _CYRILLIC.search(t)]
    toks_all = [tokenize(t) for t, _ in rows]
    keep = [i for i, tk in enumerate(toks_all) if tk]
    if not keep:
        return
    texts = [rows[i][0] for i in keep]
    sylls = [rows[i][1] for i in keep]
    tokens = [toks_all[i] for i in keep]
    multi = devices._multi_suffixes(texts)
    anaphora = {k for a, b, _p in devices.anaphora_runs(tokens) for k in range(a, b)}
    targets = [acc for lane, acc in lanes.items()
               if corpus.LANE_COHORTS[lane] is None or cohort in corpus.LANE_COHORTS[lane]]
    if artist:
        targets.append(artists.setdefault(artist, _Acc()))
    for k, text in enumerate(texts):
        kinds = {t["kind"] for t in devices.analyze_line(text, k + 1, (), gazetteer, index)}
        hits = {name for name, kind in _LINE_KIND.items() if kind in kinds}
        if k in anaphora:
            hits.add("anaphora")
        if k in multi:
            hits.add("multi")
            kinds.add("multisyllabic_rhyme")
        syl = sylls[k] if sylls[k] and sylls[k] > 0 else count_line(text)
        feats = devices.line_features(syl, devices.consonance_density(text), tokens[k],
                                      kinds, len(multi.get(k, "")))
        for acc in targets:
            acc.add(hits, feats, syl)


def _scan(con, gazetteer, index) -> dict:
    sql = ("SELECT sec.id, l.text_raw, l.syllable_count, s.genre_cohort, s.target_artist "
           "FROM lines l JOIN sections sec ON sec.id = l.section_id "
           "JOIN songs s ON s.id = sec.song_id "
           "WHERE length(trim(l.text_raw)) > 0" + corpus._corpus_sql("s") +
           " ORDER BY sec.id, l.ordinal")
    lanes = {lane: _Acc() for lane in corpus.LANE_COHORTS}
    artists: dict[str, _Acc] = {}
    cur, buf, meta = None, [], (None, None)
    for sec_id, text, syl, cohort, artist in con.execute(sql):
        if sec_id != cur:
            if buf:
                _section(buf, *meta, lanes, artists, gazetteer, index)
            cur, buf, meta = sec_id, [], (cohort, artist)
        buf.append((text, syl))
    if buf:
        _section(buf, *meta, lanes, artists, gazetteer, index)
    return {"lanes": {lane: acc.result() for lane, acc in lanes.items()},
            "artists": {a: acc.result() for a, acc in sorted(artists.items())
                        if acc.n >= MIN_ARTIST_LINES}}


def cache_path(db_path: Path, cache_dir: Path) -> Path:
    tag = hashlib.sha1(str(Path(db_path).resolve()).encode("utf-8")).hexdigest()[:8]
    return Path(cache_dir) / f"atlas_{tag}.pkl"


def load(db_path=None, cache_dir=None, rebuild: bool = False, notify: bool = True) -> dict:
    """The atlas blob for this lyrics.db, cached while its mtime+size are unchanged.

    ``{v, mtime_ns, size, lanes: {lane: stats}, artists: {slug: stats}}``. Built inside
    ``corpus.build_guarded`` (refuses while a writer is active) after ``check_annotated``.
    """
    path = Path(db_path or corpus.DEFAULT_LYRICS_DB)
    if not path.is_file():
        raise corpus.DbUnavailable(f"lyrics.db not found. Expected at: {path}")
    st = path.stat()
    cdir = Path(cache_dir or DATA_DIR)
    cfile = cache_path(path, cdir)
    if not rebuild and cfile.is_file():
        try:
            with open(cfile, "rb") as fh:
                blob = pickle.load(fh)
            if (isinstance(blob, dict) and blob.get("v") == ATLAS_VERSION
                    and blob.get("mtime_ns") == st.st_mtime_ns and blob.get("size") == st.st_size):
                return blob
        except Exception:
            pass                                   # corrupt or stale cache: rebuild below
    con = corpus.open_ro(path)
    try:
        corpus.check_annotated(con, path)
    finally:
        con.close()
    index = corpus.load_index(path, cdir)
    gazetteer = devices.load_gazetteer(str(path))
    if notify:
        print("Note: building the device atlas (one pass over the corpus, then cached)...",
              file=sys.stderr)

    def _work():
        con = corpus.open_ro(path)
        try:
            st0 = path.stat()
            blob = _scan(con, gazetteer, index)
        finally:
            con.close()
        blob.update(v=ATLAS_VERSION, mtime_ns=st0.st_mtime_ns, size=st0.st_size)
        return blob

    blob = corpus.build_guarded(path, _work)
    tmp = cfile.with_name(cfile.name + ".tmp")
    try:
        cdir.mkdir(parents=True, exist_ok=True)
        with open(tmp, "wb") as fh:
            pickle.dump(blob, fh, protocol=pickle.HIGHEST_PROTOCOL)
        os.replace(tmp, cfile)
    except OSError:
        tmp.unlink(missing_ok=True)                # cache is an optimisation only
    return blob


def lane_numeric(blob: dict, lane: str) -> dict[str, tuple[float, float]]:
    """{feature: (mean, std)} corpus priors for the lane (empty when the lane has no lines)."""
    stats = (blob.get("lanes") or {}).get(lane) or {}
    if not stats.get("n_lines"):
        return {}
    return {f: (v["mean"], v["std"]) for f, v in stats["numeric"].items()}


def artist_slugs(blob: dict) -> list[str]:
    return sorted(blob.get("artists") or {})


_COLS = (("lines", 7), ("simile", 7), ("anaph", 6), ("allit", 6), ("intern", 7),
         ("code-sw", 8), ("name", 6), ("multi%", 7), ("cons", 6), ("med-syl", 8))


def _row(label: str, st: dict) -> str:
    n = st["n_lines"]
    rate = lambda k: f"{100.0 * st['counts'][k] / n:.1f}" if n else "n/a"
    cells = [str(n), rate("simile"), rate("anaphora"), rate("allit"), rate("internal"),
             rate("code_switch"), rate("name_drop"), rate("multi"),
             f"{st['cons_mean']:.2f}",
             "n/a" if st["median_syl"] is None else f"{st['median_syl']:g}"]
    return f"{label:<20}" + "".join(f"{c:>{w + 1}}" for c, (_n, w) in zip(cells, _COLS))


def render(blob: dict, lane: str, artists=()) -> list[str]:
    """Compact table: the lane row, then one row per requested artist.
    Rates are per 100 corpus lines; nothing but numbers and slugs is printed."""
    out = [f"Device atlas  corpus={','.join(corpus.CORPORA)}  rates per 100 lines "
           "(stats only - no lyrics shown)",
           f"{'scope':<20}" + "".join(f"{n:>{w + 1}}" for n, w in _COLS)]
    lane_stats = (blob.get("lanes") or {}).get(lane)
    out.append(_row(f"lane {lane}", lane_stats) if lane_stats
               else f"lane {lane}: no data")
    known = {a.lower(): a for a in (blob.get("artists") or {})}
    for a in artists:
        key = known.get(a.lower())
        out.append(_row(f"artist {key}", blob["artists"][key]) if key
                   else f"artist {a}: no atlas row (unknown slug or under {MIN_ARTIST_LINES} lines)")
    if not artists and known:
        out.append("Artists with a row: " + ", ".join(sorted(known.values())) + "  (use --artist)")
    return out
