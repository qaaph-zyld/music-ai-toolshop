"""Per-artist pro fingerprints from persisted data only.

Aggregates rhyme craft, structure, lexical, and content metrics from
the lyrics database without recomputing any rhymes or topics.
"""

from __future__ import annotations

import json
import statistics
import sqlite3
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from toolshop.lyricsdb import COHORT_MAP

# 8 target artists for pro fingerprints
TARGET_ARTISTS: List[str] = [
    "Buba Corelli",
    "Jala Brat",
    "Coby",
    "Corona",
    "Indođija",
    "Nikolija",
    "Senidah",
    "Relja",
]

# UPOS tags to exclude from distinctive vocabulary
_EXCLUDE_UPOS = {"PRON", "DET", "ADP", "CCONJ", "SCONJ", "AUX", "PART", "PUNCT", "SYM"}

# Cohorts for rollup
COHORTS = ["drill_trap", "pop"]


def _median(values: List[float]) -> float:
    if not values:
        return 0.0
    return round(statistics.median(values), 4)


def _iqr(values: List[float]) -> Tuple[float, float, float]:
    """Return (q1, median, q3) using statistics.quantiles."""
    if not values:
        return (0.0, 0.0, 0.0)
    if len(values) < 2:
        v = round(values[0], 4)
        return (v, v, v)
    q = statistics.quantiles(values, n=4, method="inclusive")
    return (round(q[0], 4), round(q[1], 4), round(q[2], 4))


def _get_solo_song_ids(conn: sqlite3.Connection, artist: str) -> List[int]:
    cur = conn.execute(
        """SELECT id FROM songs
           WHERE primary_artist = ? AND corpus = 'genius-pro' AND role = 'solo'
           ORDER BY id""",
        (artist,),
    )
    return [r[0] for r in cur.fetchall()]


def _get_cohort_song_ids(conn: sqlite3.Connection, cohort: str) -> List[int]:
    cur = conn.execute(
        """SELECT id FROM songs
           WHERE genre_cohort = ? AND corpus = 'genius-pro' AND role = 'solo'
           ORDER BY id""",
        (cohort,),
    )
    return [r[0] for r in cur.fetchall()]


def _get_song_ids_for_artist_or_cohort(
    conn: sqlite3.Connection, artist: Optional[str] = None, cohort: Optional[str] = None
) -> List[int]:
    if artist is not None:
        return _get_solo_song_ids(conn, artist)
    if cohort is not None:
        return _get_cohort_song_ids(conn, cohort)
    return []


def _build_rhyme_craft(conn: sqlite3.Connection, song_ids: List[int]) -> Dict[str, Any]:
    if not song_ids:
        return {
            "rhyme_factor_median": 0.0,
            "rhyme_factor_iqr": (0.0, 0.0, 0.0),
            "pct_multis_median": 0.0,
            "pct_multis_iqr": (0.0, 0.0, 0.0),
            "internal_rhyme_rate_median": 0.0,
            "dominant_schemes": {},
            "top_vowel_pairs": [],
        }

    placeholders = ",".join("?" * len(song_ids))
    cur = conn.execute(
        f"""SELECT rhyme_factor, pct_multis, internal_rhyme_rate,
                  dominant_scheme, top_vowel_pairs
           FROM song_rhyme_metrics
           WHERE song_id IN ({placeholders})""",
        song_ids,
    )
    rows = cur.fetchall()

    if not rows:
        return {
            "rhyme_factor_median": 0.0,
            "rhyme_factor_iqr": (0.0, 0.0, 0.0),
            "pct_multis_median": 0.0,
            "pct_multis_iqr": (0.0, 0.0, 0.0),
            "internal_rhyme_rate_median": 0.0,
            "dominant_schemes": {},
            "top_vowel_pairs": [],
        }

    rf_values = [r[0] for r in rows if r[0] is not None]
    pm_values = [r[1] for r in rows if r[1] is not None]
    ir_values = [r[2] for r in rows if r[2] is not None]

    schemes = Counter(r[3] for r in rows if r[3])

    # Aggregate vowel pairs across all songs
    vowel_pair_counter: Counter = Counter()
    for r in rows:
        if r[4]:
            try:
                pairs = json.loads(r[4])
                for skeleton, count in pairs:
                    vowel_pair_counter[skeleton] += count
            except (json.JSONDecodeError, TypeError, ValueError):
                continue

    top_vp = vowel_pair_counter.most_common(10)

    rf_iqr = _iqr(rf_values)
    pm_iqr = _iqr(pm_values)

    return {
        "rhyme_factor_median": _median(rf_values),
        "rhyme_factor_iqr": rf_iqr,
        "pct_multis_median": _median(pm_values),
        "pct_multis_iqr": pm_iqr,
        "internal_rhyme_rate_median": _median(ir_values),
        "dominant_schemes": dict(schemes),
        "top_vowel_pairs": top_vp,
    }


def _build_structure(conn: sqlite3.Connection, song_ids: List[int]) -> Dict[str, Any]:
    if not song_ids:
        return {
            "section_type_distribution": {},
            "avg_sections_per_song": 0.0,
            "avg_lines_per_section": 0.0,
            "refren_share": 0.0,
            "hook_repetition_ratio": 0.0,
        }

    placeholders = ",".join("?" * len(song_ids))

    # Section type distribution
    cur = conn.execute(
        f"""SELECT s.type, count(*) FROM sections s
           WHERE s.song_id IN ({placeholders})
           GROUP BY s.type""",
        song_ids,
    )
    type_dist = dict(cur.fetchall())
    total_sections = sum(type_dist.values())

    # Avg sections per song
    cur = conn.execute(
        f"""SELECT s.song_id, count(*) as cnt FROM sections s
           WHERE s.song_id IN ({placeholders})
           GROUP BY s.song_id""",
        song_ids,
    )
    section_counts = [r[1] for r in cur.fetchall()]
    avg_sections = round(sum(section_counts) / len(section_counts), 2) if section_counts else 0.0

    # Avg lines per section
    cur = conn.execute(
        f"""SELECT count(*) FROM lines l
           JOIN sections s ON l.section_id = s.id
           WHERE s.song_id IN ({placeholders})""",
        song_ids,
    )
    total_lines = cur.fetchone()[0]
    avg_lines_per_section = round(total_lines / total_sections, 2) if total_sections else 0.0

    # Refren share
    refren_count = type_dist.get("refren", 0)
    refren_share = round(refren_count / total_sections, 4) if total_sections else 0.0

    # Hook repetition ratio from song_metrics
    cur = conn.execute(
        f"""SELECT hook_repetition_ratio FROM song_metrics
           WHERE song_id IN ({placeholders})""",
        song_ids,
    )
    hr_values = [r[0] for r in cur.fetchall() if r[0] is not None]
    hook_rep = _median(hr_values) if hr_values else 0.0

    return {
        "section_type_distribution": type_dist,
        "avg_sections_per_song": avg_sections,
        "avg_lines_per_section": avg_lines_per_section,
        "refren_share": refren_share,
        "hook_repetition_ratio": hook_rep,
    }


def _build_lexical(conn: sqlite3.Connection, song_ids: List[int]) -> Dict[str, Any]:
    if not song_ids:
        return {
            "ttr_median": 0.0,
            "syllables_per_line_median": 0.0,
            "distinctive_vocabulary": [],
        }

    placeholders = ",".join("?" * len(song_ids))

    # TTR + syllables from song_metrics
    cur = conn.execute(
        f"""SELECT ttr, avg_syllables_per_line FROM song_metrics
           WHERE song_id IN ({placeholders})""",
        song_ids,
    )
    rows = cur.fetchall()
    ttr_values = [r[0] for r in rows if r[0] is not None]
    syl_values = [r[1] for r in rows if r[1] is not None]

    # Distinctive vocabulary from tokens
    # Get all line_ids for these songs
    cur = conn.execute(
        f"""SELECT l.id FROM lines l
           JOIN sections s ON l.section_id = s.id
           WHERE s.song_id IN ({placeholders})""",
        song_ids,
    )
    line_ids = [r[0] for r in cur.fetchall()]

    vocab: Counter = Counter()
    if line_ids:
        line_placeholders = ",".join("?" * len(line_ids))
        cur = conn.execute(
            f"""SELECT form, upos FROM tokens
               WHERE line_id IN ({line_placeholders})""",
            line_ids,
        )
        for form, upos in cur.fetchall():
            if form and upos and upos not in _EXCLUDE_UPOS:
                vocab[form] += 1

    distinctive_vocab = vocab.most_common(20)

    return {
        "ttr_median": _median(ttr_values),
        "syllables_per_line_median": _median(syl_values),
        "distinctive_vocabulary": distinctive_vocab,
    }


def _build_content(conn: sqlite3.Connection, song_ids: List[int]) -> Dict[str, Any]:
    if not song_ids:
        return {
            "top_entities": {"PER": [], "LOC": [], "ORG": []},
            "top_topics": [],
        }

    placeholders = ",".join("?" * len(song_ids))

    # Top entities by NER type
    cur = conn.execute(
        f"""SELECT text, ner_type, count(*) as cnt FROM entities
           WHERE song_id IN ({placeholders})
           GROUP BY text, ner_type
           ORDER BY cnt DESC""",
        song_ids,
    )
    entity_rows = cur.fetchall()

    entities_by_type: Dict[str, List[Tuple[str, int]]] = {"PER": [], "LOC": [], "ORG": []}
    for text, ner_type, cnt in entity_rows:
        if ner_type in entities_by_type:
            entities_by_type[ner_type].append((text, cnt))

    # Trim to top-10 per type
    for k in entities_by_type:
        entities_by_type[k] = entities_by_type[k][:10]

    # Top-5 topics with shares
    cur = conn.execute(
        f"""SELECT t.label, count(*) as section_count, avg(st.probability) as avg_prob
           FROM section_topics st
           JOIN sections s ON st.section_id = s.id
           JOIN topics t ON st.topic_id = t.topic_id
           WHERE s.song_id IN ({placeholders})
           GROUP BY t.topic_id
           ORDER BY section_count DESC
           LIMIT 5""",
        song_ids,
    )
    topic_rows = cur.fetchall()

    total_topic_sections = sum(r[1] for r in topic_rows) if topic_rows else 1
    top_topics: List[Tuple[str, float]] = [
        (label, round(section_count / total_topic_sections, 4))
        for label, section_count, _ in topic_rows
    ]

    return {
        "top_entities": entities_by_type,
        "top_topics": top_topics,
    }


def _derive_craft_profile(fp: Dict[str, Any]) -> str:
    """Generate 2-3 sentence rule-based craft profile from fingerprint numbers."""
    rc = fp["rhyme_craft"]
    st = fp["structure"]
    lex = fp["lexical"]

    parts: List[str] = []

    # Rhyme craft sentence
    rf = rc["rhyme_factor_median"]
    pm = rc["pct_multis_median"]
    ir = rc["internal_rhyme_rate_median"]
    if rf > 0.7:
        parts.append(f"High rhyme density (RF={rf:.2f}) with heavy multisyllabic rhymes ({pm:.1%}).")
    elif rf > 0.55:
        parts.append(f"Moderate rhyme density (RF={rf:.2f}) with {pm:.1%} multisyllabic rhymes.")
    else:
        parts.append(f"Lean rhyme style (RF={rf:.2f}) with {pm:.1%} multis.")

    # Structure sentence
    refren_share = st["refren_share"]
    hook_rep = st["hook_repetition_ratio"]
    avg_sections = st["avg_sections_per_song"]
    if refren_share > 0.25:
        parts.append(f"Hook-heavy structure ({refren_share:.0%} refren, {avg_sections:.1f} sections/song).")
    else:
        parts.append(f"Verse-driven structure ({refren_share:.0%} refren, {avg_sections:.1f} sections/song).")

    # Lexical sentence
    ttr = lex["ttr_median"]
    syl = lex["syllables_per_line_median"]
    if ttr > 0.55:
        parts.append(f"Lexically diverse (TTR={ttr:.2f}, {syl:.1f} syllables/line).")
    else:
        parts.append(f"Repetitive lexicon (TTR={ttr:.2f}, {syl:.1f} syllables/line).")

    return " ".join(parts)


def build_fingerprint(conn: sqlite3.Connection, artist: str) -> Dict[str, Any]:
    """Build a pro fingerprint for a single artist from persisted data only.

    Args:
        conn: SQLite connection to lyrics.db
        artist: Primary artist name (must match songs.primary_artist)

    Returns:
        Dict with keys: artist, cohort, song_count, rhyme_craft, structure,
        lexical, content, craft_profile
    """
    song_ids = _get_solo_song_ids(conn, artist)
    cohort = COHORT_MAP.get(artist)
    if cohort is None and song_ids:
        cur = conn.execute(
            "SELECT genre_cohort FROM songs WHERE id=? AND genre_cohort IS NOT NULL LIMIT 1",
            (song_ids[0],),
        )
        row = cur.fetchone()
        if row:
            cohort = row[0]

    fp: Dict[str, Any] = {
        "artist": artist,
        "cohort": cohort or "unknown",
        "song_count": len(song_ids),
        "rhyme_craft": _build_rhyme_craft(conn, song_ids),
        "structure": _build_structure(conn, song_ids),
        "lexical": _build_lexical(conn, song_ids),
        "content": _build_content(conn, song_ids),
    }
    fp["craft_profile"] = _derive_craft_profile(fp)
    return fp


def build_cohort_fingerprint(conn: sqlite3.Connection, cohort: str) -> Dict[str, Any]:
    """Build a cohort rollup fingerprint from persisted data only.

    Args:
        conn: SQLite connection to lyrics.db
        cohort: 'drill_trap' or 'pop'

    Returns:
        Dict with keys: cohort, song_count, rhyme_craft, structure, lexical,
        content, craft_profile
    """
    song_ids = _get_cohort_song_ids(conn, cohort)

    fp: Dict[str, Any] = {
        "cohort": cohort,
        "song_count": len(song_ids),
        "rhyme_craft": _build_rhyme_craft(conn, song_ids),
        "structure": _build_structure(conn, song_ids),
        "lexical": _build_lexical(conn, song_ids),
        "content": _build_content(conn, song_ids),
    }
    fp["craft_profile"] = _derive_craft_profile(fp)
    return fp


def render_fingerprint_md(fp: Dict[str, Any]) -> str:
    """Render a single fingerprint dict to a markdown section."""
    name = fp.get("artist") or fp.get("cohort", "Unknown")
    cohort = fp.get("cohort", "unknown")
    song_count = fp.get("song_count", 0)

    lines: List[str] = []
    lines.append(f"## {name}")
    lines.append("")
    lines.append(f"**Cohort:** {cohort} | **Songs:** {song_count}")
    lines.append("")

    # Craft profile
    lines.append(f"**Craft Profile:** {fp.get('craft_profile', '')}")
    lines.append("")

    # Rhyme craft
    rc = fp["rhyme_craft"]
    lines.append("### Rhyme Craft")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Rhyme Factor (median) | {rc['rhyme_factor_median']:.4f} |")
    q1, med, q3 = rc["rhyme_factor_iqr"]
    lines.append(f"| Rhyme Factor (IQR) | {q1:.4f} – {q3:.4f} |")
    lines.append(f"| % Multis (median) | {rc['pct_multis_median']:.4f} |")
    q1, med, q3 = rc["pct_multis_iqr"]
    lines.append(f"| % Multis (IQR) | {q1:.4f} – {q3:.4f} |")
    lines.append(f"| Internal Rhyme Rate (median) | {rc['internal_rhyme_rate_median']:.4f} |")
    schemes = rc["dominant_schemes"]
    if schemes:
        top_schemes = sorted(schemes.items(), key=lambda x: -x[1])[:5]
        scheme_str = ", ".join(f"{k}: {v}" for k, v in top_schemes)
    else:
        scheme_str = "(none)"
    lines.append(f"| Dominant Schemes | {scheme_str} |")
    vp = rc["top_vowel_pairs"]
    if vp:
        vp_str = ", ".join(f"{k} ({v})" for k, v in vp[:5])
    else:
        vp_str = "(none)"
    lines.append(f"| Top Vowel Pairs | {vp_str} |")
    lines.append("")

    # Structure
    st = fp["structure"]
    lines.append("### Structure")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    type_dist = st["section_type_distribution"]
    if type_dist:
        type_str = ", ".join(f"{k}: {v}" for k, v in sorted(type_dist.items(), key=lambda x: -x[1]))
    else:
        type_str = "(none)"
    lines.append(f"| Section Type Distribution | {type_str} |")
    lines.append(f"| Avg Sections/Song | {st['avg_sections_per_song']:.2f} |")
    lines.append(f"| Avg Lines/Section | {st['avg_lines_per_section']:.2f} |")
    lines.append(f"| Refren Share | {st['refren_share']:.2%} |")
    lines.append(f"| Hook Repetition Ratio | {st['hook_repetition_ratio']:.4f} |")
    lines.append("")

    # Lexical
    lex = fp["lexical"]
    lines.append("### Lexical")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| TTR (median) | {lex['ttr_median']:.4f} |")
    lines.append(f"| Syllables/Line (median) | {lex['syllables_per_line_median']:.2f} |")
    vocab = lex["distinctive_vocabulary"]
    if vocab:
        vocab_str = ", ".join(f"{word} ({cnt})" for word, cnt in vocab[:20])
    else:
        vocab_str = "(none)"
    lines.append(f"| Distinctive Vocabulary (top-20) | {vocab_str} |")
    lines.append("")

    # Content
    ct = fp["content"]
    lines.append("### Content")
    lines.append("")
    entities = ct["top_entities"]
    for ner_type in ("PER", "LOC", "ORG"):
        ents = entities.get(ner_type, [])
        if ents:
            ent_str = ", ".join(f"{text} ({cnt})" for text, cnt in ents[:5])
        else:
            ent_str = "(none)"
        lines.append(f"| Top {ner_type} Entities | {ent_str} |")

    topics = ct["top_topics"]
    if topics:
        topic_str = ", ".join(f"{label} ({share:.1%})" for label, share in topics)
    else:
        topic_str = "(none)"
    lines.append(f"| Top-5 Topics | {topic_str} |")
    lines.append("")

    return "\n".join(lines)


def render_report(
    conn: sqlite3.Connection,
    artists: Optional[List[str]] = None,
    cohorts: Optional[List[str]] = None,
) -> str:
    """Render the full pro fingerprints report: artist pages + cohort pages.

    Args:
        conn: SQLite connection to lyrics.db
        artists: Override list of artist names (defaults to TARGET_ARTISTS)
        cohorts: Override list of cohorts (defaults to COHORTS)
    """
    if artists is None:
        artists = TARGET_ARTISTS
    if cohorts is None:
        cohorts = COHORTS

    lines: List[str] = []
    lines.append("# Pro Fingerprints — Per-Artist Craft Profiles (T5-L4)")
    lines.append("")
    lines.append("> **Statistics only.** No lyric text is stored in this report.")
    lines.append("> Generated from `lyrics.db` (persisted data only, no recomputation).")
    lines.append("")

    # Artist pages
    for artist in artists:
        fp = build_fingerprint(conn, artist)
        lines.append(render_fingerprint_md(fp))
        lines.append("---")
        lines.append("")

    # Cohort rollups
    for cohort in cohorts:
        fp = build_cohort_fingerprint(conn, cohort)
        lines.append(render_fingerprint_md(fp))
        lines.append("---")
        lines.append("")

    return "\n".join(lines)
