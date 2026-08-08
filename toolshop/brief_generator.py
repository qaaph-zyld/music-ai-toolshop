"""Brief generator — Suno-ready writing brief from corpus fingerprints.

Combines per-artist or per-cohort fingerprints (rhyme craft, structure,
lexical, content) with structure templates and rimer DB lookups to produce
a structured brief for guiding Suno prompts or human writing.

Usage::

    from toolshop.brief_generator import generate_brief, format_brief
    brief = generate_brief(artist="Jala Brat", db_path=db_path)
    print(format_brief(brief))
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from toolshop.lyricsdb import DEFAULT_DB_PATH
from toolshop.fingerprint import build_fingerprint, build_cohort_fingerprint
from toolshop.structure_template import generate_template
from toolshop.rimer_db import rank_pairs


# ── Cohort display names ──────────────────────────────────────────────

_COHORT_DISPLAY = {
    "drill_trap": "Drill Trap",
    "pop": "Pop",
}

_COHORT_STYLE_HINTS = {
    "drill_trap": (
        "style: Serbian drill trap, dark piano, 808 bass, fast flow\n"
        "language: Serbian (Latin)\n"
        "vocal style: aggressive, rhythmic delivery"
    ),
    "pop": (
        "style: Serbian pop, melodic, synth pads, punchy drums\n"
        "language: Serbian (Latin)\n"
        "vocal style: melodic, expressive, auto-tune friendly"
    ),
}


def _query_top_themes(
    conn: sqlite3.Connection, cohort: str, top_k: int = 5
) -> List[Dict[str, Any]]:
    """Query top themes for a cohort from section_topics + topics tables."""
    rows = conn.execute(
        """SELECT t.topic_id, t.label, t.top_terms, count(*) as section_count
           FROM section_topics st
           JOIN topics t ON st.topic_id = t.topic_id
           JOIN sections s ON st.section_id = s.id
           JOIN songs sg ON s.song_id = sg.id
           WHERE sg.genre_cohort = ? AND sg.role = 'solo'
           GROUP BY t.topic_id
           ORDER BY section_count DESC
           LIMIT ?""",
        (cohort, top_k),
    ).fetchall()

    themes: List[Dict[str, Any]] = []
    for topic_id, label, top_terms_json, count in rows:
        try:
            terms = json.loads(top_terms_json) if top_terms_json else []
        except (json.JSONDecodeError, TypeError):
            terms = []
        themes.append({
            "topic_id": topic_id,
            "label": label or f"Topic {topic_id}",
            "top_terms": terms,
            "section_count": count,
        })
    return themes


def _query_top_rhyme_pairs(
    conn: sqlite3.Connection, cohort: str, top_k: int = 10
) -> List[Dict[str, Any]]:
    """Query top attested rhyme pairs for a cohort from rhyme_pairs table."""
    # Check if rhyme_pairs table exists
    table_exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='rhyme_pairs'"
    ).fetchone()

    if not table_exists:
        return []

    filter_clause = ""
    if cohort == "drill_trap":
        filter_clause = "AND drill_count > 0"
    elif cohort == "pop":
        filter_clause = "AND pop_count > 0"

    rows = conn.execute(
        f"""SELECT word_a, word_b, vowel_skeleton, match_length,
                  frequency, drill_count, pop_count
           FROM rhyme_pairs
           WHERE frequency >= 2 {filter_clause}
           ORDER BY frequency DESC, match_length DESC
           LIMIT ?""",
        (top_k,),
    ).fetchall()

    return [
        {
            "word_a": r[0],
            "word_b": r[1],
            "vowel_skeleton": r[2],
            "match_length": r[3],
            "frequency": r[4],
        }
        for r in rows
    ]


# ── Main API ──────────────────────────────────────────────────────────


def generate_brief(
    artist: Optional[str] = None,
    cohort: Optional[str] = None,
    topic: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Generate a structured writing brief.

    Args:
        artist: Artist name for per-artist fingerprint.  If None, uses cohort.
        cohort: Genre cohort ('drill_trap' or 'pop').  Required if artist is None.
            If artist is given, cohort is derived from the fingerprint.
        topic: Optional topic/keyword hint to include in the brief.
        db_path: Path to lyrics.db.  Defaults to ``DEFAULT_DB_PATH``.

    Returns:
        Dict with keys: artist_or_cohort, cohort, craft_targets, structure,
        themes, rhyme_pairs, suno_hints, topic.
    """
    if artist is None and cohort is None:
        raise ValueError("Either artist or cohort must be specified")

    if db_path is None:
        db_path = DEFAULT_DB_PATH

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys=ON")

    try:
        # Build fingerprint
        if artist is not None:
            fp = build_fingerprint(conn, artist)
            cohort = fp.get("cohort", "unknown")
            name = artist
        else:
            fp = build_cohort_fingerprint(conn, cohort)
            name = _COHORT_DISPLAY.get(cohort, cohort or "Unknown")

        # Build structure template
        if cohort and cohort in ("drill_trap", "pop"):
            template = generate_template(cohort=cohort, db_path=db_path)
        else:
            template = {"sections": [], "cohort": cohort or "unknown", "total_lines": 0}

        # Query top themes
        if cohort and cohort in ("drill_trap", "pop"):
            themes = _query_top_themes(conn, cohort)
        else:
            themes = []

        # Query top rhyme pairs
        if cohort and cohort in ("drill_trap", "pop"):
            rhyme_pairs = _query_top_rhyme_pairs(conn, cohort)
        else:
            rhyme_pairs = []

        # Extract craft targets from fingerprint
        rc = fp.get("rhyme_craft", {})
        lex = fp.get("lexical", {})
        struct = fp.get("structure", {})

        craft_targets = {
            "rhyme_factor": rc.get("rhyme_factor_median", 0.0),
            "pct_multis": rc.get("pct_multis_median", 0.0),
            "internal_rhyme_rate": rc.get("internal_rhyme_rate_median", 0.0),
            "dominant_schemes": rc.get("dominant_schemes", {}),
            "ttr": lex.get("ttr_median", 0.0),
            "syllables_per_line": lex.get("syllables_per_line_median", 0.0),
            "avg_sections": struct.get("avg_sections_per_song", 0.0),
            "avg_lines_per_section": struct.get("avg_lines_per_section", 0.0),
        }

        # Suno style hints
        suno_hints = _COHORT_STYLE_HINTS.get(cohort or "", "")

        brief = {
            "name": name,
            "cohort": cohort or "unknown",
            "song_count": fp.get("song_count", 0),
            "craft_targets": craft_targets,
            "structure": template,
            "themes": themes,
            "rhyme_pairs": rhyme_pairs,
            "suno_hints": suno_hints,
            "topic": topic,
        }
        return brief

    finally:
        conn.close()


def format_brief(brief: Dict[str, Any]) -> str:
    """Format a brief dict as a human-readable text brief.

    Args:
        brief: Dict from ``generate_brief``.

    Returns:
        Formatted multi-line string suitable for display or file output.
    """
    lines: List[str] = []
    name = brief.get("name", "Unknown")
    cohort = brief.get("cohort", "unknown")
    song_count = brief.get("song_count", 0)

    lines.append(f"=== SUNO BRIEF: {name} style ({cohort}) ===")
    lines.append("")

    # Structure
    lines.append("STRUCTURE:")
    template = brief.get("structure", {})
    for sec in template.get("sections", []):
        sec_type = sec.get("type", "?")
        n_lines = sec.get("lines", 0)
        scheme = sec.get("rhyme_scheme", "?")
        lines.append(f"  [{sec_type.title()}] — {n_lines} lines, {scheme}")
    lines.append("")

    # Craft targets
    ct = brief.get("craft_targets", {})
    lines.append("CRAFT TARGETS:")
    lines.append(f"  Rhyme factor: {ct.get('rhyme_factor', 0.0):.2f}")
    lines.append(f"  Multisyllabic: {ct.get('pct_multis', 0.0) * 100:.0f}% of rhymes")
    lines.append(f"  Internal rhyme rate: {ct.get('internal_rhyme_rate', 0.0):.2f}")
    lines.append(f"  TTR: {ct.get('ttr', 0.0):.2f}")
    lines.append(f"  Syllables/line: {ct.get('syllables_per_line', 0.0):.1f}")
    schemes = ct.get("dominant_schemes", {})
    if schemes:
        top_schemes = sorted(schemes.items(), key=lambda x: x[1], reverse=True)[:3]
        scheme_str = ", ".join(f"{s} ({c})" for s, c in top_schemes)
        lines.append(f"  Dominant schemes: {scheme_str}")
    lines.append("")

    # Theme palette
    themes = brief.get("themes", [])
    if themes:
        lines.append("THEME PALETTE (top-5 cohort themes):")
        for i, theme in enumerate(themes[:5], 1):
            label = theme.get("label", "?")
            terms = theme.get("top_terms", [])
            terms_str = ", ".join(terms[:5]) if terms else ""
            lines.append(f"  {i}. {label}" + (f" ({terms_str})" if terms_str else ""))
        lines.append("")

    # Top rhyme pairs
    pairs = brief.get("rhyme_pairs", [])
    if pairs:
        lines.append(f"TOP RHYME PAIRS (attested in {cohort}):")
        for p in pairs[:10]:
            wa = p.get("word_a", "?")
            wb = p.get("word_b", "?")
            freq = p.get("frequency", 0)
            lines.append(f"  {wa} → {wb} (×{freq})")
        lines.append("")

    # Topic hint
    topic = brief.get("topic")
    if topic:
        lines.append(f"TOPIC HINT: {topic}")
        lines.append("")

    # Suno prompt hints
    hints = brief.get("suno_hints", "")
    if hints:
        lines.append("SUNO PROMPT HINTS:")
        lines.append(f"  {hints.replace(chr(10), chr(10) + '  ')}")
        lines.append("")

    lines.append(f"=== END BRIEF ({song_count} songs in baseline) ===")
    return "\n".join(lines)


def format_suno_prompt(brief: Dict[str, Any]) -> str:
    """Format a brief dict as a condensed Suno prompt string.

    Args:
        brief: Dict from ``generate_brief``.

    Returns:
        Single string suitable for pasting into a Suno prompt.
    """
    parts: List[str] = []
    cohort = brief.get("cohort", "unknown")
    ct = brief.get("craft_targets", {})

    # Style
    hints = brief.get("suno_hints", "")
    if hints:
        parts.append(hints)

    # Structure summary
    template = brief.get("structure", {})
    sections = template.get("sections", [])
    if sections:
        section_summary = " → ".join(
            f"{s['type']}({s['lines']})" for s in sections
        )
        parts.append(f"structure: {section_summary}")

    # Craft targets (condensed)
    parts.append(f"rhyme density: {ct.get('rhyme_factor', 0.0):.2f}")
    parts.append(f"multis: {ct.get('pct_multis', 0.0) * 100:.0f}%")

    # Topic
    topic = brief.get("topic")
    if topic:
        parts.append(f"topic: {topic}")

    return "\n".join(parts)
