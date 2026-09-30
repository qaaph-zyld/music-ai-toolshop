"""Syllables per line of the user's own text, against their median and the lane's."""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from pathlib import Path

from toolshop.syllables import count_line

from mairina import corpus
from mairina.used import read_text


@dataclass
class FlowResult:
    rows: list[tuple[int, int, str]]    # (file line number, syllables, text)
    user_median: float | None
    lane_median: float | None
    lane: str


def lane_median(lane: str, db_path=None) -> float | None:
    """Median lines.syllable_count in the lane (read-only)."""
    cohorts = corpus.LANE_COHORTS[lane]
    sql = ("SELECT l.syllable_count FROM lines l JOIN sections sec ON sec.id = l.section_id "
           "JOIN songs s ON s.id = sec.song_id WHERE l.syllable_count > 0"
           + corpus._corpus_sql("s"))
    args: tuple = ()
    if cohorts:
        sql += f" AND s.genre_cohort IN ({','.join('?' * len(cohorts))})"
        args = cohorts
    con = corpus.open_ro(db_path)
    try:
        vals = [r[0] for r in con.execute(sql, args)]
    finally:
        con.close()
    return statistics.median(vals) if vals else None


def flow(path: Path | str, lane: str = "all", db_path=None) -> FlowResult:
    rows = []
    for n, raw in enumerate(read_text(path).splitlines(), 1):
        text = raw.strip()
        if not text or (text.startswith("[") and text.endswith("]")):
            continue                      # blank lines and [Verse] headers
        syl = count_line(text)
        if syl:
            rows.append((n, syl, text))
    med = statistics.median([r[1] for r in rows]) if rows else None
    return FlowResult(rows, med, lane_median(lane, db_path), lane)


def render(res: FlowResult) -> list[str]:
    fmt = lambda v: "n/a" if v is None else f"{v:g}"
    out = [f"Flow: {len(res.rows)} lines | your median {fmt(res.user_median)} syl | "
           f"lane '{res.lane}' median {fmt(res.lane_median)} syl",
           " line  syl  vs-you  vs-lane  text"]
    for n, syl, text in res.rows:
        d_you = "" if res.user_median is None else f"{syl - res.user_median:+g}"
        d_lane = "" if res.lane_median is None else f"{syl - res.lane_median:+g}"
        out.append(f"{n:>5}  {syl:>3}  {d_you:>6}  {d_lane:>7}  {text[:50]}")
    return out
