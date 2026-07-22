"""L3 discrimination report — statistics only, no lyric dumps.

Compares drill_trap vs pop cohorts on:
1. Slang lexicon distinctiveness (log-ratio distribution)
2. Theme mix divergence (Jensen-Shannon divergence over topic shares)
3. Per-topic overrepresentation (drill vs pop share ratio)

HARD EXIT GATE: if discrimination fails (JSD < 0.05 AND no slang terms with
|distinctiveness| > 1.0), exit with code 2.
"""

from __future__ import annotations

import json
import math
import sqlite3
import sys
from typing import Any, Dict, List, Optional

from toolshop.lyricsdb import DEFAULT_DB_PATH


def _jsd(p: List[float], q: List[float]) -> float:
    """Jensen-Shannon divergence between two distributions."""
    # Align lengths
    n = max(len(p), len(q))
    p = p + [0.0] * (n - len(p))
    q = q + [0.0] * (n - len(q))

    # Normalize
    sp = sum(p)
    sq = sum(q)
    if sp == 0 or sq == 0:
        return 0.0
    p = [x / sp for x in p]
    q = [x / sq for x in q]

    m = [(pi + qi) / 2 for pi, qi in zip(p, q)]

    def _kl(a: List[float], b: List[float]) -> float:
        return sum(ai * math.log2(ai / bi) for ai, bi in zip(a, b) if ai > 0 and bi > 0)

    return (_kl(p, m) + _kl(q, m)) / 2


def generate_report(conn: sqlite3.Connection) -> Dict[str, Any]:
    """Generate the L3 discrimination report (statistics only)."""

    # ── 1. Annotation coverage ──
    total_lines = conn.execute("SELECT count(*) FROM lines WHERE text_raw IS NOT NULL AND text_raw != ''").fetchone()[0]
    annotated_lines = conn.execute("SELECT count(DISTINCT line_id) FROM tokens").fetchone()[0]
    total_tokens = conn.execute("SELECT count(*) FROM tokens").fetchone()[0]
    entity_count = conn.execute("SELECT count(*) FROM entities").fetchone()[0]

    script_rows = conn.execute(
        "SELECT source_script, count(*) FROM tokens GROUP BY source_script"
    ).fetchall()
    by_script = {r[0]: r[1] for r in script_rows}

    # ── 2. Slang lexicon summary ──
    slang_total = conn.execute("SELECT count(*) FROM slang_terms").fetchone()[0]
    drill_distinct = conn.execute("SELECT count(*) FROM slang_terms WHERE distinctiveness > 0.5").fetchone()[0]
    pop_distinct = conn.execute("SELECT count(*) FROM slang_terms WHERE distinctiveness < -0.5").fetchone()[0]

    # Top drill-distinctive
    top_drill = conn.execute(
        "SELECT form, lemma, freq, drill_freq, pop_freq, distinctiveness FROM slang_terms "
        "WHERE distinctiveness > 0.5 ORDER BY distinctiveness DESC LIMIT 10"
    ).fetchall()

    # Top pop-distinctive
    top_pop = conn.execute(
        "SELECT form, lemma, freq, drill_freq, pop_freq, distinctiveness FROM slang_terms "
        "WHERE distinctiveness < -0.5 ORDER BY distinctiveness ASC LIMIT 10"
    ).fetchall()

    # Distinctiveness distribution
    dist_rows = conn.execute(
        "SELECT CASE WHEN distinctiveness > 2 THEN '>2' "
        "WHEN distinctiveness > 1 THEN '1-2' "
        "WHEN distinctiveness > 0.5 THEN '0.5-1' "
        "WHEN distinctiveness > -0.5 THEN '-0.5 to 0.5' "
        "WHEN distinctiveness > -1 THEN '-1 to -0.5' "
        "WHEN distinctiveness > -2 THEN '-2 to -1' "
        "ELSE '<-2' END AS bucket, count(*) "
        "FROM slang_terms GROUP BY bucket ORDER BY bucket"
    ).fetchall()

    # ── 3. Theme mix ──
    # Per-cohort topic shares
    cohort_topic_rows = conn.execute(
        """SELECT s.genre_cohort, st.topic_id, count(*) as cnt
           FROM section_topics st
           JOIN sections sec ON st.section_id = sec.id
           JOIN songs s ON sec.song_id = s.id
           WHERE s.role = 'solo' AND s.genre_cohort IS NOT NULL
           GROUP BY s.genre_cohort, st.topic_id"""
    ).fetchall()

    drill_topics: Dict[int, int] = {}
    pop_topics: Dict[int, int] = {}
    for cohort, tid, cnt in cohort_topic_rows:
        if cohort == "drill_trap":
            drill_topics[tid] = cnt
        elif cohort == "pop":
            pop_topics[tid] = cnt

    drill_total_sections = sum(drill_topics.values())
    pop_total_sections = sum(pop_topics.values())

    # Build aligned distributions for JSD
    all_topic_ids = sorted(set(list(drill_topics.keys()) + list(pop_topics.keys())))
    drill_dist = [drill_topics.get(tid, 0) for tid in all_topic_ids]
    pop_dist = [pop_topics.get(tid, 0) for tid in all_topic_ids]

    jsd_score = _jsd(drill_dist, pop_dist)

    # Per-topic overrepresentation
    topic_overrep = []
    for tid in all_topic_ids:
        d_share = drill_topics.get(tid, 0) / drill_total_sections if drill_total_sections else 0
        p_share = pop_topics.get(tid, 0) / pop_total_sections if pop_total_sections else 0
        ratio = d_share / p_share if p_share > 0 else float("inf")
        topic_overrep.append({
            "topic_id": tid,
            "drill_share": d_share,
            "pop_share": p_share,
            "ratio": ratio,
        })

    # Sort by ratio (drill-overrepresented first)
    topic_overrep.sort(key=lambda x: x["ratio"] if x["ratio"] != float("inf") else 999, reverse=True)

    # Topic labels
    topic_labels = {}
    label_rows = conn.execute("SELECT topic_id, label, top_terms FROM topics").fetchall()
    for tid, label, terms in label_rows:
        topic_labels[tid] = {"label": label, "top_terms": terms}

    # ── 4. Discrimination gate ──
    has_slang_discrimination = drill_distinct > 0 and pop_distinct > 0
    has_theme_discrimination = jsd_score > 0.05
    has_strong_slang = conn.execute(
        "SELECT count(*) FROM slang_terms WHERE abs(distinctiveness) > 1.0"
    ).fetchone()[0]

    gate_passed = has_slang_discrimination and has_theme_discrimination and has_strong_slang > 0

    # ── Print report ──
    print("=" * 70)
    print("  L3 LANGUAGE & THEMES — DISCRIMINATION REPORT")
    print("=" * 70)

    print(f"\n── Annotation Coverage ──")
    print(f"  Total lines:      {total_lines}")
    print(f"  Annotated lines:  {annotated_lines} ({annotated_lines/total_lines*100:.1f}%)")
    print(f"  Total tokens:     {total_tokens}")
    print(f"  Cyrillic tokens:  {by_script.get('cyrillic', 0)}")
    print(f"  Latin tokens:     {by_script.get('latin', 0)}")
    print(f"  Entities:         {entity_count}")

    print(f"\n── Slang Lexicon ──")
    print(f"  Total slang terms:       {slang_total}")
    print(f"  Drill-distinctive (>0.5): {drill_distinct}")
    print(f"  Pop-distinctive (<-0.5):  {pop_distinct}")
    print(f"  Strong (|dist| > 1.0):    {has_strong_slang}")

    print(f"\n  Distinctiveness distribution:")
    for bucket, cnt in dist_rows:
        print(f"    {bucket:>20s}: {cnt}")

    print(f"\n  Top 10 drill-distinctive terms:")
    print(f"    {'Form':<15} {'Freq':>5} {'Drill/10K':>10} {'Pop/10K':>10} {'Distinct':>10}")
    for form, lemma, freq, df, pf, dist in top_drill:
        print(f"    {form:<15} {freq:>5} {df:>10.2f} {pf:>10.2f} {dist:>10.3f}")

    print(f"\n  Top 10 pop-distinctive terms:")
    print(f"    {'Form':<15} {'Freq':>5} {'Drill/10K':>10} {'Pop/10K':>10} {'Distinct':>10}")
    for form, lemma, freq, df, pf, dist in top_pop:
        print(f"    {form:<15} {freq:>5} {df:>10.2f} {pf:>10.2f} {dist:>10.3f}")

    print(f"\n── Theme Mix ──")
    print(f"  Drill sections (solo): {drill_total_sections}")
    print(f"  Pop sections (solo):   {pop_total_sections}")
    print(f"  Topics:                {len(all_topic_ids)}")
    print(f"  JSD(drill || pop):     {jsd_score:.4f}")

    print(f"\n  Top 10 drill-overrepresented topics:")
    print(f"    {'Topic':>5} {'Label':<35} {'Drill%':>7} {'Pop%':>7} {'Ratio':>7}")
    for t in topic_overrep[:10]:
        tid = t["topic_id"]
        label = topic_labels.get(tid, {}).get("label", "?")[:35]
        print(f"    {tid:>5} {label:<35} {t['drill_share']*100:>6.1f}% {t['pop_share']*100:>6.1f}% {t['ratio']:>7.2f}")

    print(f"\n  Top 10 pop-overrepresented topics:")
    print(f"    {'Topic':>5} {'Label':<35} {'Drill%':>7} {'Pop%':>7} {'Ratio':>7}")
    for t in sorted(topic_overrep, key=lambda x: x["ratio"] if x["ratio"] > 0 else 999)[:10]:
        tid = t["topic_id"]
        label = topic_labels.get(tid, {}).get("label", "?")[:35]
        print(f"    {tid:>5} {label:<35} {t['drill_share']*100:>6.1f}% {t['pop_share']*100:>6.1f}% {t['ratio']:>7.2f}")

    print(f"\n── Discrimination Gate ──")
    print(f"  Slang discrimination (both cohorts have distinctive terms): {'PASS' if has_slang_discrimination else 'FAIL'}")
    print(f"  Strong slang terms (|dist| > 1.0): {has_strong_slang} {'PASS' if has_strong_slang > 0 else 'FAIL'}")
    print(f"  Theme discrimination (JSD > 0.05): {'PASS' if has_theme_discrimination else 'FAIL'} (JSD={jsd_score:.4f})")
    print(f"  OVERALL: {'PASS' if gate_passed else 'FAIL'}")

    return {
        "annotation": {
            "total_lines": total_lines,
            "annotated_lines": annotated_lines,
            "total_tokens": total_tokens,
            "by_script": by_script,
            "entity_count": entity_count,
        },
        "slang": {
            "total_terms": slang_total,
            "drill_distinctive": drill_distinct,
            "pop_distinctive": pop_distinct,
            "strong_terms": has_strong_slang,
            "top_drill": top_drill,
            "top_pop": top_pop,
            "distribution": dist_rows,
        },
        "themes": {
            "drill_sections": drill_total_sections,
            "pop_sections": pop_total_sections,
            "topic_count": len(all_topic_ids),
            "jsd": jsd_score,
            "topic_overrep": topic_overrep,
        },
        "gate_passed": gate_passed,
    }


def run_report(db_path: Optional[Any] = None) -> Dict[str, Any]:
    """CLI entry point: generate discrimination report."""
    from pathlib import Path

    if db_path is None:
        db_path = DEFAULT_DB_PATH
    db_path = Path(db_path)

    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return {}

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=ON")

    report = generate_report(conn)
    conn.close()

    if not report.get("gate_passed", False):
        print("\n  *** DISCRIMINATION GATE FAILED — exiting with code 2 ***")
        sys.exit(2)

    return report
