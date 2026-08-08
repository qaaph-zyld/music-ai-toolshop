"""Draft scorer — 5-component lyric evaluation with originality check.

Extends ``ai_scorer.score_lyrics`` with a 5th component (Originality) that
checks n-gram overlap between the draft and the full corpus.  Also supports
per-artist comparison via ``--vs`` mode.

Usage::

    from toolshop.draft_scorer import score_draft
    result = score_draft("draft.txt", artist="Jala Brat", db_path=db_path)
    print(result["overall_score"], result["components"]["originality"]["score"])
"""

from __future__ import annotations

import re
import sqlite3
import statistics
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from toolshop.lyricsdb import DEFAULT_DB_PATH, normalize_text
from toolshop.ai_scorer import (
    _parse_sections,
    _z_score,
    _z_to_score,
    _query_cohort_baselines,
)
from toolshop.rhyme_miner import (
    find_internal_rhymes,
    multisyllabic_rhymes,
    rhyme_factor,
)
from toolshop.syllables import count_line
from toolshop.lyrics_analyzer import _tokenize


# ── N-gram originality check ──────────────────────────────────────────

_WORD_RE = re.compile(r"[a-z]+")


def _extract_ngrams(tokens: List[str], n: int = 3) -> set:
    """Extract a set of n-gram tuples from a token list."""
    if len(tokens) < n:
        return set()
    return {tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}


def _ngram_overlap(
    text: str,
    n: int = 3,
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Compute n-gram overlap between draft text and the full corpus.

    Args:
        text: Normalized draft lyrics text.
        n: N-gram size (default 3 = trigrams).
        db_path: Path to lyrics.db.

    Returns:
        Dict with:
        - overlap_pct: percentage of draft n-grams found in corpus (0-100)
        - total_draft_ngrams: total unique n-grams in draft
        - matched_ngrams: count of draft n-grams found in corpus
        - source_songs: list of {song_id, title, artist, matched_count}
          for top-5 songs with most overlap
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    # Extract draft n-grams
    draft_tokens = _WORD_RE.findall(text.lower())
    draft_ngrams = _extract_ngrams(draft_tokens, n)

    if not draft_ngrams:
        return {
            "overlap_pct": 100.0,
            "total_draft_ngrams": 0,
            "matched_ngrams": 0,
            "source_songs": [],
        }

    # Query all corpus lines and build per-song n-gram sets
    conn = sqlite3.connect(str(db_path))
    try:
        rows = conn.execute(
            """SELECT l.text_norm, s.song_id
               FROM lines l
               JOIN sections s ON l.section_id = s.id
               WHERE l.text_norm IS NOT NULL AND l.text_norm != ''""",
        ).fetchall()
    finally:
        conn.close()

    # Build per-song n-gram sets
    song_ngrams: Dict[int, set] = {}
    for text_norm, song_id in rows:
        tokens = _WORD_RE.findall((text_norm or "").lower())
        ngs = _extract_ngrams(tokens, n)
        if song_id not in song_ngrams:
            song_ngrams[song_id] = set()
        song_ngrams[song_id].update(ngs)

    # Count matches
    matched = 0
    song_match_counts: Counter = Counter()
    for ng in draft_ngrams:
        found = False
        for sid, song_set in song_ngrams.items():
            if ng in song_set:
                found = True
                song_match_counts[sid] += 1
        if found:
            matched += 1

    overlap_pct = round((matched / len(draft_ngrams)) * 100, 2) if draft_ngrams else 100.0

    # Get top-5 source songs
    top_songs = song_match_counts.most_common(5)
    source_songs: List[Dict[str, Any]] = []

    if top_songs:
        conn = sqlite3.connect(str(db_path))
        try:
            for song_id, match_count in top_songs:
                row = conn.execute(
                    "SELECT title, primary_artist FROM songs WHERE id=?",
                    (song_id,),
                ).fetchone()
                if row:
                    source_songs.append({
                        "song_id": song_id,
                        "title": row[0],
                        "artist": row[1],
                        "matched_count": match_count,
                    })
        finally:
            conn.close()

    return {
        "overlap_pct": overlap_pct,
        "total_draft_ngrams": len(draft_ngrams),
        "matched_ngrams": matched,
        "source_songs": source_songs,
    }


# ── Per-artist baseline ───────────────────────────────────────────────


def _query_artist_baselines(
    conn: sqlite3.Connection, artist: str
) -> Dict[str, Any]:
    """Query per-artist baseline metrics for --vs mode."""
    # song_metrics baselines
    cursor = conn.execute(
        """SELECT avg(m.line_count), avg(m.ttr), avg(m.avg_syllables_per_line),
                  avg(m.hook_repetition_ratio),
                  count(DISTINCT s.id) as song_count,
                  avg(sec_count) as avg_sections
           FROM song_metrics m
           JOIN songs s ON m.song_id = s.id
           JOIN (
               SELECT song_id, count(*) as sec_count
               FROM sections GROUP BY song_id
           ) sc ON sc.song_id = s.id
           WHERE s.primary_artist = ? AND s.role = 'solo'""",
        (artist,),
    )
    row = cursor.fetchone()
    sm_baselines = {
        "avg_line_count": row[0] or 0.0,
        "avg_ttr": row[1] or 0.0,
        "avg_syllables_per_line": row[2] or 0.0,
        "avg_hook_repetition_ratio": row[3] or 0.0,
        "song_count": row[4] or 0,
        "avg_sections": row[5] or 0.0,
    }

    # song_rhyme_metrics baselines
    cursor = conn.execute(
        """SELECT avg(srm.rhyme_factor), avg(srm.pct_multis),
                  avg(srm.internal_rhyme_rate)
           FROM song_rhyme_metrics srm
           JOIN songs s ON srm.song_id = s.id
           WHERE s.primary_artist = ? AND s.role = 'solo'""",
        (artist,),
    )
    row = cursor.fetchone()
    rm_baselines = {
        "avg_rhyme_factor": row[0] or 0.0,
        "avg_pct_multis": row[1] or 0.0,
        "avg_internal_rhyme_rate": row[2] or 0.0,
    }

    # Std devs
    cursor = conn.execute(
        """SELECT m.line_count, m.ttr, m.avg_syllables_per_line,
                  m.hook_repetition_ratio
           FROM song_metrics m
           JOIN songs s ON m.song_id = s.id
           WHERE s.primary_artist = ? AND s.role = 'solo'""",
        (artist,),
    )
    rows = cursor.fetchall()
    sm_stds = {
        "line_count": statistics.pstdev([r[0] or 0 for r in rows]) if len(rows) > 1 else 0.0,
        "ttr": statistics.pstdev([r[1] or 0 for r in rows]) if len(rows) > 1 else 0.0,
        "avg_syllables_per_line": statistics.pstdev([r[2] or 0 for r in rows]) if len(rows) > 1 else 0.0,
        "hook_repetition_ratio": statistics.pstdev([r[3] or 0 for r in rows]) if len(rows) > 1 else 0.0,
    }

    cursor = conn.execute(
        """SELECT srm.rhyme_factor, srm.pct_multis, srm.internal_rhyme_rate
           FROM song_rhyme_metrics srm
           JOIN songs s ON srm.song_id = s.id
           WHERE s.primary_artist = ? AND s.role = 'solo'""",
        (artist,),
    )
    rows = cursor.fetchall()
    rm_stds = {
        "rhyme_factor": statistics.pstdev([r[0] or 0 for r in rows]) if len(rows) > 1 else 0.0,
        "pct_multis": statistics.pstdev([r[1] or 0 for r in rows]) if len(rows) > 1 else 0.0,
        "internal_rhyme_rate": statistics.pstdev([r[2] or 0 for r in rows]) if len(rows) > 1 else 0.0,
    }

    return {
        "song_metrics": sm_baselines,
        "song_rhyme_metrics": rm_baselines,
        "sm_stds": sm_stds,
        "rm_stds": rm_stds,
    }


# ── Main API ──────────────────────────────────────────────────────────


def score_draft(
    input_path: Path,
    artist: Optional[str] = None,
    cohort: str = "drill_trap",
    db_path: Optional[Path] = None,
    ngram_size: int = 3,
) -> Dict[str, Any]:
    """Score a draft lyrics file with 5 components including originality.

    Extends ``ai_scorer.score_lyrics`` with:
    - Originality check (n-gram overlap vs corpus)
    - Per-artist comparison mode (``artist`` parameter)

    Args:
        input_path: Path to draft lyrics text file.
        artist: If given, compare against this artist's baselines instead of
            cohort averages.  Also sets the comparison label.
        cohort: Genre cohort for baseline comparison (used when artist is None).
        db_path: Path to lyrics.db.
        ngram_size: N-gram size for originality check (default 3).

    Returns:
        Dict with ``overall_score``, ``components`` (5 components),
        ``comparison_target`` (artist name or cohort), and ``originality``.
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    # Read and normalize input
    raw_text = Path(input_path).read_text(encoding="utf-8")
    normalized = normalize_text(raw_text)

    # Parse sections
    sections = _parse_sections(normalized)
    all_lines: List[str] = []
    for _, lines in sections:
        all_lines.extend(lines)

    section_count = len(sections)
    total_lines = len(all_lines)

    # ── Structural metrics ──
    struct_input = {
        "section_count": section_count,
        "total_lines": total_lines,
    }

    # ── Rhyme metrics ──
    rf = rhyme_factor(all_lines) if all_lines else 0.0
    multi_matches = multisyllabic_rhymes(all_lines) if all_lines else []
    multi_count = sum(len(m.line_indices) for m in multi_matches)
    pct_multis = round(multi_count / len(all_lines), 4) if all_lines else 0.0

    internal_count = 0
    for line in all_lines:
        if find_internal_rhymes(line, min_match=2):
            internal_count += 1
    internal_rhyme_rate = round(internal_count / total_lines, 4) if total_lines else 0.0

    rhyme_input = {
        "rhyme_factor": rf,
        "pct_multis": pct_multis,
        "internal_rhyme_rate": internal_rhyme_rate,
    }

    # ── Lexical metrics ──
    tokens = _tokenize(normalized)
    total_tokens = len(tokens)
    unique_tokens = len(set(tokens))
    ttr = round(unique_tokens / total_tokens, 4) if total_tokens else 0.0
    avg_syl = round(sum(count_line(l) for l in all_lines) / total_lines, 2) if total_lines else 0.0

    lexical_input = {
        "ttr": ttr,
        "avg_syllables_per_line": avg_syl,
    }

    # ── Repetition metrics ──
    line_counter = Counter(all_lines)
    repeated = sum(1 for c in line_counter.values() if c > 1)
    hook_repetition_ratio = round(repeated / total_lines, 4) if total_lines else 0.0

    repetition_input = {
        "hook_repetition_ratio": hook_repetition_ratio,
    }

    # ── Originality check ──
    orig_result = _ngram_overlap(normalized, n=ngram_size, db_path=db_path)
    # Originality score: 100 - overlap_pct (higher overlap = lower originality)
    originality_score = max(0.0, min(100.0, 100.0 - orig_result["overlap_pct"]))

    # ── Query baselines ──
    conn = sqlite3.connect(str(db_path))
    try:
        if artist is not None:
            baselines = _query_artist_baselines(conn, artist)
            comparison_target = artist
        else:
            baselines = _query_cohort_baselines(conn, cohort)
            comparison_target = cohort
    finally:
        conn.close()

    sm = baselines["song_metrics"]
    rm = baselines["song_rhyme_metrics"]
    sm_stds = baselines["sm_stds"]
    rm_stds = baselines["rm_stds"]

    # ── Component scores via z-score ──
    avg_sections = sm.get("avg_sections", 0.0)
    avg_line_count = sm.get("avg_line_count", 0.0)
    z_lines = _z_score(total_lines, avg_line_count, sm_stds.get("line_count", 0.0))
    z_sections = _z_score(section_count, avg_sections, 0.0)
    structural_score = _z_to_score((z_lines + z_sections) / 2)

    z_rf = _z_score(rf, rm.get("avg_rhyme_factor", 0.0), rm_stds.get("rhyme_factor", 0.0))
    z_multis = _z_score(pct_multis, rm.get("avg_pct_multis", 0.0), rm_stds.get("pct_multis", 0.0))
    z_irr = _z_score(internal_rhyme_rate, rm.get("avg_internal_rhyme_rate", 0.0), rm_stds.get("internal_rhyme_rate", 0.0))
    rhyme_score = _z_to_score((z_rf + z_multis + z_irr) / 3)

    z_ttr = _z_score(ttr, sm.get("avg_ttr", 0.0), sm_stds.get("ttr", 0.0))
    z_syl = _z_score(avg_syl, sm.get("avg_syllables_per_line", 0.0), sm_stds.get("avg_syllables_per_line", 0.0))
    lexical_score = _z_to_score((z_ttr + z_syl) / 2)

    z_hook = _z_score(hook_repetition_ratio, sm.get("avg_hook_repetition_ratio", 0.0), sm_stds.get("hook_repetition_ratio", 0.0))
    repetition_score = _z_to_score(z_hook)

    # ── Weighted sum (5 components, 20% each) ──
    overall = (
        structural_score * 0.20
        + rhyme_score * 0.20
        + lexical_score * 0.20
        + repetition_score * 0.20
        + originality_score * 0.20
    )
    overall = round(overall, 2)

    return {
        "overall_score": overall,
        "comparison_target": comparison_target,
        "components": {
            "structural": {
                "score": round(structural_score, 2),
                "metrics": struct_input,
                "baselines": {
                    "avg_sections": avg_sections,
                    "avg_line_count": avg_line_count,
                },
            },
            "rhyme": {
                "score": round(rhyme_score, 2),
                "metrics": rhyme_input,
                "baselines": {
                    "avg_rhyme_factor": rm.get("avg_rhyme_factor", 0.0),
                    "avg_pct_multis": rm.get("avg_pct_multis", 0.0),
                    "avg_internal_rhyme_rate": rm.get("avg_internal_rhyme_rate", 0.0),
                },
            },
            "lexical": {
                "score": round(lexical_score, 2),
                "metrics": lexical_input,
                "baselines": {
                    "avg_ttr": sm.get("avg_ttr", 0.0),
                    "avg_syllables_per_line": sm.get("avg_syllables_per_line", 0.0),
                },
            },
            "repetition": {
                "score": round(repetition_score, 2),
                "metrics": repetition_input,
                "baselines": {
                    "avg_hook_repetition_ratio": sm.get("avg_hook_repetition_ratio", 0.0),
                },
            },
            "originality": {
                "score": round(originality_score, 2),
                "metrics": {
                    "overlap_pct": orig_result["overlap_pct"],
                    "total_draft_ngrams": orig_result["total_draft_ngrams"],
                    "matched_ngrams": orig_result["matched_ngrams"],
                    "source_songs": orig_result["source_songs"],
                },
            },
        },
    }
