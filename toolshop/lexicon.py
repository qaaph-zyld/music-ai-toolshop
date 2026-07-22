"""Slang lexicon via OOV mining from CLASSLA tokens.

Mines ``tokens.is_oov`` + low-frequency-lemma heuristic to build a slang
lexicon with per-cohort frequency and a distinctiveness score
(drill_freq vs pop_freq log-ratio).  Solo songs only, cohort-scoped.

Populates: ``slang_terms``.
"""

from __future__ import annotations

import math
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

from toolshop.lyricsdb import DEFAULT_DB_PATH


# Minimum total frequency for a term to be considered for the lexicon.
_MIN_FREQ = 3
# Smoothing constant for log-ratio (avoids log(0) and div-by-zero).
_SMOOTH = 0.5


def _compute_distinctiveness(drill_freq: float, pop_freq: float) -> float:
    """Log-ratio distinctiveness score.

    Positive → drill-distinctive, negative → pop-distinctive.
    """
    return math.log2((drill_freq + _SMOOTH) / (pop_freq + _SMOOTH))


def mine_slang(conn: sqlite3.Connection) -> Dict[str, Any]:
    """Mine slang terms from tokens table, populating slang_terms.

    Uses is_oov flag + low-frequency-lemma heuristic.  Computes per-cohort
    frequency (drill_trap vs pop, solo songs only) and distinctiveness.

    Returns summary dict.
    """
    # Wipe existing
    conn.execute("DELETE FROM slang_terms")

    # Step 1: Get total token counts per cohort (solo songs only)
    cohort_counts = conn.execute(
        """SELECT s.genre_cohort, count(*) as tok_count
           FROM tokens t
           JOIN lines l ON t.line_id = l.id
           JOIN sections sec ON l.section_id = sec.id
           JOIN songs s ON sec.song_id = s.id
           WHERE s.role = 'solo' AND s.genre_cohort IS NOT NULL
           GROUP BY s.genre_cohort"""
    ).fetchall()
    total_by_cohort = {row[0]: row[1] for row in cohort_counts}

    drill_total = total_by_cohort.get("drill_trap", 0)
    pop_total = total_by_cohort.get("pop", 0)

    print(f"  Total tokens — drill_trap: {drill_total}, pop: {pop_total}")

    # Step 2: Get per-lemma frequencies split by cohort
    # OOV tokens (is_oov=1) or low-frequency lemmas (freq < 10 across corpus)
    lemma_rows = conn.execute(
        """SELECT t.lemma, t.form, t.is_oov,
                  s.genre_cohort, count(*) as freq
           FROM tokens t
           JOIN lines l ON t.line_id = l.id
           JOIN sections sec ON l.section_id = sec.id
           JOIN songs s ON sec.song_id = s.id
           WHERE s.role = 'solo' AND s.genre_cohort IS NOT NULL
             AND t.lemma IS NOT NULL AND t.lemma != '_'
             AND t.upos NOT IN ('PUNCT', 'ADP', 'AUX', 'DET', 'PRON', 'SCONJ', 'CCONJ', 'PART')
           GROUP BY t.lemma, t.form, t.is_oov, s.genre_cohort"""
    ).fetchall()

    # Aggregate per (lemma, form, is_oov) across cohorts
    terms: Dict[Tuple[str, str, int], Dict[str, int]] = {}
    for lemma, form, is_oov, cohort, freq in lemma_rows:
        key = (lemma, form, is_oov)
        if key not in terms:
            terms[key] = {"drill_trap": 0, "pop": 0}
        terms[key][cohort] = terms[key].get(cohort, 0) + freq

    # Step 3: Compute total freq, per-cohort relative freq, distinctiveness
    slang_rows = []
    for (lemma, form, is_oov), counts in terms.items():
        total_freq = counts.get("drill_trap", 0) + counts.get("pop", 0)
        if total_freq < _MIN_FREQ:
            continue

        # Only keep OOV or low-frequency terms
        if not is_oov and total_freq >= 10:
            continue

        drill_freq_raw = counts.get("drill_trap", 0)
        pop_freq_raw = counts.get("pop", 0)

        # Normalize per 10K tokens for comparability
        drill_freq = (drill_freq_raw / drill_total * 10000) if drill_total else 0.0
        pop_freq = (pop_freq_raw / pop_total * 10000) if pop_total else 0.0

        distinctiveness = _compute_distinctiveness(drill_freq, pop_freq)

        slang_rows.append({
            "form": form,
            "lemma": lemma,
            "freq": total_freq,
            "drill_freq": drill_freq,
            "pop_freq": pop_freq,
            "distinctiveness": distinctiveness,
            "is_oov": is_oov,
        })

    # Sort by absolute distinctiveness (most distinctive first)
    slang_rows.sort(key=lambda r: abs(r["distinctiveness"]), reverse=True)

    # Insert
    for row in slang_rows:
        conn.execute(
            """INSERT INTO slang_terms
               (form, lemma, freq, drill_freq, pop_freq, distinctiveness, is_oov)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                row["form"], row["lemma"], row["freq"],
                row["drill_freq"], row["pop_freq"],
                row["distinctiveness"], row["is_oov"],
            ),
        )

    conn.commit()

    drill_distinctive = [r for r in slang_rows if r["distinctiveness"] > 0.5]
    pop_distinctive = [r for r in slang_rows if r["distinctiveness"] < -0.5]

    print(f"  Slang terms mined: {len(slang_rows)}")
    print(f"  Drill-distinctive (>0.5): {len(drill_distinctive)}")
    print(f"  Pop-distinctive (<-0.5): {len(pop_distinctive)}")

    return {
        "total_terms": len(slang_rows),
        "drill_distinctive_count": len(drill_distinctive),
        "pop_distinctive_count": len(pop_distinctive),
    }


def get_slang_terms(
    conn: sqlite3.Connection,
    cohort: Optional[str] = None,
    top: int = 20,
) -> List[Dict[str, Any]]:
    """Retrieve slang terms, optionally filtered by cohort direction.

    Args:
        cohort: 'drill_trap' for drill-distinctive, 'pop' for pop-distinctive,
                None for all.
        top: Limit number of results.
    """
    query = "SELECT form, lemma, freq, drill_freq, pop_freq, distinctiveness, is_oov FROM slang_terms"
    params: List[Any] = []

    if cohort == "drill_trap":
        query += " WHERE distinctiveness > 0.5 ORDER BY distinctiveness DESC"
    elif cohort == "pop":
        query += " WHERE distinctiveness < -0.5 ORDER BY distinctiveness ASC"
    else:
        query += " ORDER BY abs(distinctiveness) DESC"

    query += " LIMIT ?"
    params.append(top)

    rows = conn.execute(query, params).fetchall()
    return [
        {
            "form": r[0], "lemma": r[1], "freq": r[2],
            "drill_freq": r[3], "pop_freq": r[4],
            "distinctiveness": r[5], "is_oov": r[6],
        }
        for r in rows
    ]


def run_lexicon(db_path: Optional[Any] = None) -> Dict[str, Any]:
    """CLI entry point: mine slang from tokens."""
    from pathlib import Path

    if db_path is None:
        db_path = DEFAULT_DB_PATH
    db_path = Path(db_path)

    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return {}

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=ON")

    print(f"  Mining slang lexicon from tokens...")
    summary = mine_slang(conn)

    conn.close()
    return summary
