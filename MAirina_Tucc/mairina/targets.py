"""Syllable targets per lane x section type: p25 / median / p75 of
``lines.syllable_count`` in lyrics.db (read-only), pickled like the word index.
The same cache also carries per-lane consonance-density quantiles for the
xray gauge.

Verified against the corpus: drill strofa 10/13/15, drill refren 8/11/13,
pop strofa 8/11/13, pop refren 8/11/13.
"""

from __future__ import annotations

import hashlib
import pickle
from pathlib import Path

from mairina import DATA_DIR, corpus

SECTION_TYPES = ("strofa", "refren", "prerefren", "postrefren", "hook", "bridge")
MIN_N = 30        # below this a lane x section cell is too thin: use the lane range
BLOB_VERSION = 2


class Target(tuple):
    """(p25, median, p75); ``approx`` marks a small-n cell shown as '10–15~'."""

    def __new__(cls, p25: int, med: int, p75: int, approx: bool = False):
        t = super().__new__(cls, (p25, med, p75))
        t.approx = approx
        return t


_memo: dict[tuple[str, int, int], dict[str, Target]] = {}
_cons_memo: dict[tuple[str, int, int], tuple[float, float, float] | None] = {}
_blob_memo: dict[tuple[int, int], dict] = {}


def _pct(sorted_vals: list, p: float):
    return sorted_vals[int(p * (len(sorted_vals) - 1))]


def _cache_path(db_path: Path, cache_dir: Path) -> Path:
    tag = hashlib.sha1(str(db_path.resolve()).encode("utf-8")).hexdigest()[:8]
    return cache_dir / f"targets_{tag}.pkl"


def _density(text: str) -> float:
    from mairina.devices import consonance_density      # lazy: avoids an import loop
    return consonance_density(text)


def _query(con, cohorts: tuple | None) -> dict:
    """{sections: {type: [syl]}, densities: [float]} for one lane."""
    sql = ("SELECT sec.type, l.syllable_count, l.text_norm FROM lines l "
           "JOIN sections sec ON sec.id = l.section_id "
           "JOIN songs s ON s.id = sec.song_id WHERE l.syllable_count > 0"
           + corpus._corpus_sql("s"))
    args: tuple = ()
    if cohorts:
        sql += f" AND s.genre_cohort IN ({','.join('?' * len(cohorts))})"
        args = cohorts
    sections: dict[str, list[int]] = {}
    densities: list[float] = []
    for stype, syl, text in con.execute(sql, args):
        if stype in SECTION_TYPES:
            sections.setdefault(stype, []).append(syl)
        if text:
            densities.append(_density(text))
    return {"sections": sections, "densities": densities}


def _blob(path: Path, cdir: Path) -> dict:
    """The cached {'lanes': {lane: {sections, densities}}} blob for this db file."""
    st = path.stat()
    key = (st.st_mtime_ns, st.st_size)
    if key in _blob_memo:
        return _blob_memo[key]
    cfile = _cache_path(path, cdir)
    blob = None
    if cfile.is_file():
        try:
            with open(cfile, "rb") as fh:
                blob = pickle.load(fh)
        except Exception:
            blob = None
    if not (isinstance(blob, dict) and blob.get("v") == BLOB_VERSION
            and blob.get("mtime_ns") == st.st_mtime_ns and blob.get("size") == st.st_size):
        def _work():
            con = corpus.open_ro(path)
            try:
                corpus.check_annotated(con, path)
                st0 = path.stat()
                return {"v": BLOB_VERSION, "mtime_ns": st0.st_mtime_ns, "size": st0.st_size,
                        "lanes": {ln: _query(con, cohorts)
                                  for ln, cohorts in corpus.LANE_COHORTS.items()}}
            finally:
                con.close()

        blob = corpus.build_guarded(path, _work)
        try:
            cdir.mkdir(parents=True, exist_ok=True)
            with open(cfile, "wb") as fh:
                pickle.dump(blob, fh, protocol=pickle.HIGHEST_PROTOCOL)
        except OSError:
            pass                    # cache is an optimisation only
    _blob_memo[key] = blob
    return blob


def lane_table(lane: str = "all", db_path=None, cache_dir=None) -> dict[str, Target]:
    """{section_type: Target(p25, median, p75)} for the lane. n<MIN_N -> lane-wide '~'."""
    path = Path(db_path or corpus.DEFAULT_LYRICS_DB)
    if not path.is_file():
        raise corpus.DbUnavailable(f"lyrics.db not found. Expected at: {path}")
    st = path.stat()
    key = (lane, st.st_mtime_ns, st.st_size)
    if key not in _memo:
        sections = (_blob(path, Path(cache_dir or DATA_DIR))["lanes"].get(lane) or {})["sections"]
        pooled = sorted(syl for vals in sections.values() for syl in vals)
        table: dict[str, Target] = {}
        for t, vals in sections.items():
            if not vals:
                continue
            src, approx = (sorted(vals), False) if len(vals) >= MIN_N else (pooled, True)
            if src:
                table[t] = Target(*(_pct(src, q) for q in (0.25, 0.5, 0.75)), approx=approx)
        _memo[key] = table
    return _memo[key]


def target(lane: str = "all", section: str = "strofa", db_path=None,
           cache_dir=None) -> Target | None:
    """Target(p25, median, p75) syllable target for lane x section, or None."""
    return lane_table(lane, db_path, cache_dir).get(section)


def cons_thresholds(lane: str = "all", db_path=None,
                    cache_dir=None) -> tuple[float, float, float] | None:
    """Lane consonance-density quantiles (p25/p50/p75) for the xray gauge, or None."""
    path = Path(db_path or corpus.DEFAULT_LYRICS_DB)
    if not path.is_file():
        raise corpus.DbUnavailable(f"lyrics.db not found. Expected at: {path}")
    st = path.stat()
    key = (lane, st.st_mtime_ns, st.st_size)
    if key not in _cons_memo:
        dens = sorted((_blob(path, Path(cache_dir or DATA_DIR))["lanes"].get(lane) or {})
                      .get("densities") or [])
        _cons_memo[key] = (None if len(dens) < MIN_N or dens[-1] <= 0
                           else tuple(_pct(dens, q) for q in (0.25, 0.5, 0.75)))
    return _cons_memo[key]


def fmt_range(t: tuple | None) -> str:
    """'10–15' (p25–p75), '10–15~' for a small-n lane-wide fallback, or 'n/a'."""
    if t is None:
        return "n/a"
    return f"{t[0]}–{t[2]}" + ("~" if getattr(t, "approx", False) else "")
