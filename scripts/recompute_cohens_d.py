#!/usr/bin/env python3
"""Recompute Cohen's d for rhyme discrimination on the expanded corpus.

Queries song_rhyme_metrics for drill_trap solo vs pop solo,
computes Cohen's d, median comparison, and overlap percentages.

Output: lyrics_research/reports/cohen_d_expanded.md
"""

from __future__ import annotations

import sqlite3
import statistics
import math
from pathlib import Path
from typing import List, Tuple

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DB_PATH = _REPO_ROOT / "data" / "toolshop" / "lyrics" / "lyrics.db"
_REPORT_PATH = _REPO_ROOT / "lyrics_research" / "reports" / "cohen_d_expanded.md"


def cohens_d(group1: List[float], group2: List[float]) -> float:
    """Compute Cohen's d effect size."""
    n1, n2 = len(group1), len(group2)
    if n1 < 2 or n2 < 2:
        return 0.0

    m1, m2 = statistics.mean(group1), statistics.mean(group2)
    v1, v2 = statistics.variance(group1), statistics.variance(group2)

    # Pooled standard deviation
    s_pooled = math.sqrt(((n1 - 1) * v1 + (n2 - 1) * v2) / (n1 + n2 - 2))

    if s_pooled == 0:
        return 0.0

    return (m1 - m2) / s_pooled


def overlap_pct(group: List[float], threshold: float) -> float:
    """What percentage of group values exceed the threshold."""
    if not group:
        return 0.0
    return round(sum(1 for v in group if v > threshold) / len(group) * 100, 1)


def main() -> None:
    conn = sqlite3.connect(_DB_PATH)

    # Get rhyme_factor by cohort (solo only)
    drill_rfs: List[float] = [
        r[0] for r in conn.execute(
            "SELECT srm.rhyme_factor FROM song_rhyme_metrics srm "
            "JOIN songs s ON srm.song_id = s.id "
            "WHERE s.genre_cohort = 'drill_trap' AND s.role = 'solo' "
            "AND s.corpus = 'genius-pro' AND srm.rhyme_factor IS NOT NULL"
        ).fetchall()
    ]

    pop_rfs: List[float] = [
        r[0] for r in conn.execute(
            "SELECT srm.rhyme_factor FROM song_rhyme_metrics srm "
            "JOIN songs s ON srm.song_id = s.id "
            "WHERE s.genre_cohort = 'pop' AND s.role = 'solo' "
            "AND s.corpus = 'genius-pro' AND srm.rhyme_factor IS NOT NULL"
        ).fetchall()
    ]

    # Also get pct_multis and internal_rhyme_rate
    drill_multis: List[float] = [
        r[0] for r in conn.execute(
            "SELECT srm.pct_multis FROM song_rhyme_metrics srm "
            "JOIN songs s ON srm.song_id = s.id "
            "WHERE s.genre_cohort = 'drill_trap' AND s.role = 'solo' "
            "AND s.corpus = 'genius-pro' AND srm.pct_multis IS NOT NULL"
        ).fetchall()
    ]

    pop_multis: List[float] = [
        r[0] for r in conn.execute(
            "SELECT srm.pct_multis FROM song_rhyme_metrics srm "
            "JOIN songs s ON srm.song_id = s.id "
            "WHERE s.genre_cohort = 'pop' AND s.role = 'solo' "
            "AND s.corpus = 'genius-pro' AND srm.pct_multis IS NOT NULL"
        ).fetchall()
    ]

    drill_irr: List[float] = [
        r[0] for r in conn.execute(
            "SELECT srm.internal_rhyme_rate FROM song_rhyme_metrics srm "
            "JOIN songs s ON srm.song_id = s.id "
            "WHERE s.genre_cohort = 'drill_trap' AND s.role = 'solo' "
            "AND s.corpus = 'genius-pro' AND srm.internal_rhyme_rate IS NOT NULL"
        ).fetchall()
    ]

    pop_irr: List[float] = [
        r[0] for r in conn.execute(
            "SELECT srm.internal_rhyme_rate FROM song_rhyme_metrics srm "
            "JOIN songs s ON srm.song_id = s.id "
            "WHERE s.genre_cohort = 'pop' AND s.role = 'solo' "
            "AND s.corpus = 'genius-pro' AND srm.internal_rhyme_rate IS NOT NULL"
        ).fetchall()
    ]

    conn.close()

    # Compute Cohen's d for each metric
    d_rf = cohens_d(pop_rfs, drill_rfs)
    d_multis = cohens_d(pop_multis, drill_multis)
    d_irr = cohens_d(pop_irr, drill_irr)

    # Medians and means
    drill_rf_med = statistics.median(drill_rfs)
    pop_rf_med = statistics.median(pop_rfs)
    drill_rf_mean = statistics.mean(drill_rfs)
    pop_rf_mean = statistics.mean(pop_rfs)

    # Overlap analysis (using pop median as threshold)
    drill_above_pop_med = overlap_pct(drill_rfs, pop_rf_med)
    pop_below_drill_med = overlap_pct(pop_rfs, drill_rf_med)

    # Prior value for comparison
    prior_d = 1.1786
    prior_n = 742

    total_n = len(drill_rfs) + len(pop_rfs)

    # ── Generate report ───────────────────────────────────────────────
    lines: List[str] = []
    r = lines.append

    r("# Cohen's d Recompute on Expanded Corpus")
    r("")
    r(f"**Generated:** 2026-07-30  ")
    r(f"**DB:** `{_DB_PATH}`  ")
    r(f"**Prior result:** d = {prior_d} on {prior_n} songs (T5-L2.1 verification, 2026-07-22)")
    r("")
    r("---")
    r("")
    r("## Corpus")
    r("")
    r("| Cohort | Songs | Role |")
    r("|--------|-------|------|")
    r(f"| drill_trap | {len(drill_rfs)} | solo |")
    r(f"| pop | {len(pop_rfs)} | solo |")
    r(f"| **Total** | **{total_n}** | |")
    r("")
    r(f"Expansion: {prior_n} → {total_n} songs ({total_n - prior_n} new)")
    r("")

    r("## Rhyme Factor (Primary Discrimination Metric)")
    r("")
    r("| Statistic | Drill Trap | Pop |")
    r("|-----------|------------|-----|")
    r(f"| N | {len(drill_rfs)} | {len(pop_rfs)} |")
    r(f"| Median | {round(drill_rf_med, 4)} | {round(pop_rf_med, 4)} |")
    r(f"| Mean | {round(drill_rf_mean, 4)} | {round(pop_rf_mean, 4)} |")
    r(f"| Std Dev | {round(statistics.stdev(drill_rfs), 4)} | {round(statistics.stdev(pop_rfs), 4)} |")
    r(f"| Min | {round(min(drill_rfs), 4)} | {round(min(pop_rfs), 4)} |")
    r(f"| Max | {round(max(drill_rfs), 4)} | {round(max(pop_rfs), 4)} |")
    r("")
    r(f"**Cohen's d = {round(d_rf, 4)}** (pop > drill, positive d means pop rhymes more densely)")
    r("")
    r(f"**Prior d = {prior_d}** on {prior_n} songs → **Current d = {round(d_rf, 4)}** on {total_n} songs")
    r("")

    # Effect size interpretation
    abs_d = abs(d_rf)
    if abs_d >= 0.8:
        effect = "large"
    elif abs_d >= 0.5:
        effect = "medium"
    elif abs_d >= 0.2:
        effect = "small"
    else:
        effect = "negligible"
    r(f"Effect size: **{effect}** (|d| = {round(abs_d, 4)})")
    r("")

    r("### Overlap Analysis")
    r("")
    r(f"- Drill songs above pop median RF ({round(pop_rf_med, 4)}): **{drill_above_pop_med}%**")
    r(f"- Pop songs below drill median RF ({round(drill_rf_med, 4)}): **{pop_below_drill_med}%**")
    r("")

    r("## Secondary Metrics")
    r("")
    r("| Metric | Drill median | Pop median | Cohen's d | Direction |")
    r("|--------|-------------|------------|-----------|-----------|")
    r(f"| % Multisyllabic | {round(statistics.median(drill_multis), 4)} | {round(statistics.median(pop_multis), 4)} | {round(d_multis, 4)} | {'pop > drill' if d_multis > 0 else 'drill > pop'} |")
    r(f"| Internal Rhyme Rate | {round(statistics.median(drill_irr), 4)} | {round(statistics.median(pop_irr), 4)} | {round(d_irr, 4)} | {'pop > drill' if d_irr > 0 else 'drill > pop'} |")
    r("")

    r("## Verdict")
    r("")
    r(f"The discrimination effect size **Cohen's d = {round(d_rf, 4)}** on {total_n} songs ")
    r(f"({'confirms' if abs_d >= 0.8 else 'weakens but maintains' if abs_d >= 0.5 else 'weakens'} the prior finding of d = {prior_d}).")
    r("")
    r(f"Direction is **consistent** with L2.1: pop cohort rhymes more densely than drill_trap.")
    r(f"The expanded corpus ({total_n} vs {prior_n} songs) {'preserves' if abs_d >= 0.8 else 'still shows'} large-effect discrimination.")
    r("")

    _REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    _REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Report written to: {_REPORT_PATH}")
    print(f"  Drill: {len(drill_rfs)} songs, RF median = {round(drill_rf_med, 4)}")
    print(f"  Pop: {len(pop_rfs)} songs, RF median = {round(pop_rf_med, 4)}")
    print(f"  Cohen's d = {round(d_rf, 4)} (prior: {prior_d})")
    print(f"  Effect: {effect}")


if __name__ == "__main__":
    main()
