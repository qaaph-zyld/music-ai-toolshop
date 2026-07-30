#!/usr/bin/env python3
"""Suno gap report: compare AI-generated Suno lyrics vs Genius pro corpus.

Computes rhyme metrics, lexical metrics, slang overlap, and structure metrics
for Suno lyrics, then queries the Genius DB for comparison stats.

Output: lyrics_research/reports/suno_gap_report.md
"""

from __future__ import annotations

import json
import re
import sqlite3
import statistics
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── Path constants ────────────────────────────────────────────────────
_REPO_ROOT = Path(__file__).resolve().parent.parent
_SUNO_EXPORT = _REPO_ROOT / "data" / "toolshop" / "suno" / "lyrics_export.json"
_DB_PATH = _REPO_ROOT / "data" / "toolshop" / "lyrics" / "lyrics.db"
_REPORT_PATH = _REPO_ROOT / "lyrics_research" / "reports" / "suno_gap_report.md"

# ── Suno section label parsing ────────────────────────────────────────
# Suno uses [Verse], [Chorus], [Female], [Male], [vocal chops], etc.
_SECTION_RE = re.compile(r"^\s*\[([^\]]+)\]\s*$", re.MULTILINE)

# Map Suno labels to canonical types
_SUNO_TYPE_MAP: Dict[str, str] = {
    "verse": "strofa",
    "chorus": "refren",
    "refren": "refren",
    "strofa": "strofa",
    "bridge": "bridge",
    "intro": "intro",
    "outro": "outro",
    "hook": "hook",
    "pre": "prerefren",
    "pre-chorus": "prerefren",
    "pre-refren": "prerefren",
    "post": "postrefren",
    "post-chorus": "postrefren",
    "post-refren": "postrefren",
    "drop": "hook",
    "spoken": "spoken",
    "interlude": "interlude",
    "instrumental": "instrumental",
}


def _classify_suno_label(label: str) -> str:
    """Classify a Suno section label into a canonical type."""
    text = label.strip().lower()
    # Direct lookup
    if text in _SUNO_TYPE_MAP:
        return _SUNO_TYPE_MAP[text]
    # Partial match (e.g. "verse 1", "chorus 2")
    for key, val in _SUNO_TYPE_MAP.items():
        if text.startswith(key):
            return val
    # Performer labels: [Female], [Male], [Female and Male], [vocal chops]
    if any(w in text for w in ("female", "male", "vocal", "choir", "crowd", "ad")):
        return "strofa"  # treat as verse with performer info
    return "other"


def parse_suno_lyrics(lyrics: str) -> List[Dict[str, Any]]:
    """Parse Suno lyrics text into sections.

    Returns list of {label, type, lines: [str, ...]}.
    """
    if not lyrics or not lyrics.strip():
        return []

    sections: List[Dict[str, Any]] = []
    # Split on section labels
    parts = _SECTION_RE.split(lyrics)

    # parts[0] is text before first label (usually empty)
    current_label = ""
    current_lines: List[str] = []

    i = 0
    while i < len(parts):
        part = parts[i]
        # Check if this part is a label (odd indices are labels from re.split)
        if i % 2 == 1:
            # Save previous section
            if current_lines:
                sections.append({
                    "label": current_label,
                    "type": _classify_suno_label(current_label),
                    "lines": [l.strip() for l in current_lines if l.strip()],
                })
            current_label = part.strip()
            current_lines = []
        else:
            current_lines.extend(part.split("\n"))
        i += 1

    # Don't forget the last section
    if current_lines:
        sections.append({
            "label": current_label,
            "type": _classify_suno_label(current_label) if current_label else "other",
            "lines": [l.strip() for l in current_lines if l.strip()],
        })

    return sections


# ── Rhyme metrics (reusing rhyme_miner logic) ────────────────────────

def _normalize_ascii(text: str) -> str:
    """ASCII-fold + lowercase for rhyme analysis."""
    _FOLD = str.maketrans({
        "č": "c", "ć": "c", "š": "s", "ž": "z", "đ": "dj",
        "Č": "c", "Ć": "c", "Š": "s", "Ž": "z", "Đ": "dj",
    })
    # Also handle Cyrillic via simple transliteration
    try:
        import cyrtranslit
        if bool(re.search(r"[А-Яа-я]", text)):
            text = cyrtranslit.to_latin(text)
    except ImportError:
        pass
    return text.translate(_FOLD).lower()


def compute_rhyme_metrics(lines: List[str]) -> Dict[str, Any]:
    """Compute rhyme metrics for a set of lines."""
    from toolshop.rhyme_miner import (
        find_rhymes,
        find_internal_rhymes,
        rhyme_factor,
        multisyllabic_rhymes,
        infer_scheme,
    )

    if not lines or len(lines) < 2:
        return {
            "rhyme_factor": 0.0,
            "pct_multis": 0.0,
            "internal_rhyme_rate": 0.0,
            "scheme": "N/A",
            "n_rhyme_groups": 0,
            "n_multis": 0,
        }

    # Normalize lines for rhyme analysis
    norm_lines = [_normalize_ascii(l) for l in lines]

    rf = rhyme_factor(norm_lines)
    groups = find_rhymes(norm_lines, min_match=2)
    multis = multisyllabic_rhymes(norm_lines, min_length=3)
    scheme = infer_scheme(groups, len(norm_lines))

    # Internal rhyme rate
    total_internal = 0
    for line in norm_lines:
        total_internal += len(find_internal_rhymes(line, min_match=2))

    internal_rate = total_internal / len(norm_lines) if norm_lines else 0.0
    pct_multis = len(multis) / len(groups) if groups else 0.0

    return {
        "rhyme_factor": round(rf, 4),
        "pct_multis": round(pct_multis, 4),
        "internal_rhyme_rate": round(internal_rate, 4),
        "scheme": scheme,
        "n_rhyme_groups": len(groups),
        "n_multis": len(multis),
    }


# ── Lexical metrics ──────────────────────────────────────────────────

_WORD_RE = re.compile(r"[a-zA-ZÀ-ÿ]+")


def compute_lexical_metrics(lines: List[str]) -> Dict[str, Any]:
    """Compute lexical metrics for a set of lines."""
    from toolshop.syllables import count_line

    words: List[str] = []
    total_syllables = 0
    for line in lines:
        norm = _normalize_ascii(line)
        words.extend(_WORD_RE.findall(norm))
        total_syllables += count_line(norm)

    n_words = len(words)
    n_types = len(set(w.lower() for w in words))
    ttr = n_types / n_words if n_words > 0 else 0.0

    # Top terms
    term_freq = Counter(w.lower() for w in words)
    top_50 = term_freq.most_common(50)

    return {
        "n_words": n_words,
        "n_types": n_types,
        "ttr": round(ttr, 4),
        "avg_syllables_per_line": round(total_syllables / len(lines), 2) if lines else 0.0,
        "total_syllables": total_syllables,
        "top_50_terms": top_50,
    }


# ── Structure metrics ────────────────────────────────────────────────

def compute_structure_metrics(sections: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute structure metrics from parsed sections."""
    n_sections = len(sections)
    total_lines = sum(len(s["lines"]) for s in sections)
    avg_lines_per_section = total_lines / n_sections if n_sections > 0 else 0.0

    type_dist = Counter(s["type"] for s in sections)

    return {
        "n_sections": n_sections,
        "total_lines": total_lines,
        "avg_lines_per_section": round(avg_lines_per_section, 2),
        "section_type_dist": dict(type_dist.most_common()),
    }


# ── Slang overlap ────────────────────────────────────────────────────

def compute_slang_overlap(
    suno_top_terms: Counter, db_path: Path
) -> Dict[str, Any]:
    """Check overlap between Suno vocabulary and slang lexicon."""
    conn = sqlite3.connect(db_path)

    # Get drill-distinctive and pop-distinctive terms
    drill_terms = {
        row[0].lower(): row[5]
        for row in conn.execute(
            "SELECT form, lemma, freq, drill_freq, pop_freq, distinctiveness "
            "FROM slang_terms WHERE distinctiveness > 0.5"
        ).fetchall()
    }
    pop_terms = {
        row[0].lower(): row[5]
        for row in conn.execute(
            "SELECT form, lemma, freq, drill_freq, pop_freq, distinctiveness "
            "FROM slang_terms WHERE distinctiveness < -0.5"
        ).fetchall()
    }

    suno_vocab = set(suno_top_terms.keys())

    drill_overlap = suno_vocab & set(drill_terms.keys())
    pop_overlap = suno_vocab & set(pop_terms.keys())

    # Weighted overlap (by frequency)
    drill_weighted = sum(suno_top_terms[t] for t in drill_overlap)
    pop_weighted = sum(suno_top_terms[t] for t in pop_overlap)
    total_suno_words = sum(suno_top_terms.values())

    conn.close()

    return {
        "drill_overlap_count": len(drill_overlap),
        "pop_overlap_count": len(pop_overlap),
        "drill_overlap_terms": sorted(drill_overlap, key=lambda t: suno_top_terms[t], reverse=True)[:20],
        "pop_overlap_terms": sorted(pop_overlap, key=lambda t: suno_top_terms[t], reverse=True)[:20],
        "drill_overlap_pct": round(drill_weighted / total_suno_words * 100, 2) if total_suno_words else 0.0,
        "pop_overlap_pct": round(pop_weighted / total_suno_words * 100, 2) if total_suno_words else 0.0,
    }


# ── Genius DB comparison stats ───────────────────────────────────────

def get_genius_stats(db_path: Path) -> Dict[str, Any]:
    """Query Genius DB for aggregate comparison stats."""
    conn = sqlite3.connect(db_path)

    # Cohort counts
    cohort_counts = {}
    for row in conn.execute(
        "SELECT genre_cohort, role, count(*) FROM songs "
        "WHERE corpus = 'genius-pro' GROUP BY genre_cohort, role"
    ).fetchall():
        cohort, role, cnt = row
        key = f"{cohort or 'NULL'}_{role or 'NULL'}"
        cohort_counts[key] = cnt

    # Rhyme metrics by cohort (solo only)
    rhyme_stats = {}
    for cohort in ("drill_trap", "pop"):
        rows = conn.execute(
            "SELECT srm.rhyme_factor, srm.pct_multis, srm.internal_rhyme_rate, "
            "srm.dominant_scheme "
            "FROM song_rhyme_metrics srm "
            "JOIN songs s ON srm.song_id = s.id "
            "WHERE s.genre_cohort = ? AND s.role = 'solo' AND s.corpus = 'genius-pro'",
            (cohort,),
        ).fetchall()

        if not rows:
            rhyme_stats[cohort] = {"n": 0}
            continue

        rfs = [r[0] for r in rows if r[0] is not None]
        pcts = [r[1] for r in rows if r[1] is not None]
        irrs = [r[2] for r in rows if r[2] is not None]
        schemes = [r[3] for r in rows if r[3]]

        rhyme_stats[cohort] = {
            "n": len(rows),
            "rf_median": round(statistics.median(rfs), 4) if rfs else 0.0,
            "rf_mean": round(statistics.mean(rfs), 4) if rfs else 0.0,
            "pct_multis_median": round(statistics.median(pcts), 4) if pcts else 0.0,
            "pct_multis_mean": round(statistics.mean(pcts), 4) if pcts else 0.0,
            "irr_median": round(statistics.median(irrs), 4) if irrs else 0.0,
            "irr_mean": round(statistics.mean(irrs), 4) if irrs else 0.0,
            "top_schemes": dict(Counter(schemes).most_common(5)),
        }

    # Structure stats by cohort
    structure_stats = {}
    for cohort in ("drill_trap", "pop"):
        rows = conn.execute(
            "SELECT s.id, count(DISTINCT sec.id), count(DISTINCT l.id) "
            "FROM songs s "
            "JOIN sections sec ON sec.song_id = s.id "
            "JOIN lines l ON l.section_id = sec.id "
            "WHERE s.genre_cohort = ? AND s.role = 'solo' AND s.corpus = 'genius-pro' "
            "GROUP BY s.id",
            (cohort,),
        ).fetchall()

        if not rows:
            structure_stats[cohort] = {"n": 0}
            continue

        sec_counts = [r[1] for r in rows]
        line_counts = [r[2] for r in rows]

        structure_stats[cohort] = {
            "n": len(rows),
            "avg_sections": round(statistics.mean(sec_counts), 2),
            "median_sections": statistics.median(sec_counts),
            "avg_lines": round(statistics.mean(line_counts), 2),
            "median_lines": statistics.median(line_counts),
        }

    # Section type distribution by cohort
    type_dist = {}
    for cohort in ("drill_trap", "pop"):
        rows = conn.execute(
            "SELECT sec.type, count(*) FROM songs s "
            "JOIN sections sec ON sec.song_id = s.id "
            "WHERE s.genre_cohort = ? AND s.role = 'solo' AND s.corpus = 'genius-pro' "
            "GROUP BY sec.type ORDER BY count(*) DESC",
            (cohort,),
        ).fetchall()
        type_dist[cohort] = dict(rows)

    # Lexical stats (TTR, syllables/line) by cohort — sample if too many
    lexical_stats = {}
    for cohort in ("drill_trap", "pop"):
        rows = conn.execute(
            "SELECT l.text_norm, l.word_count, l.syllable_count "
            "FROM lines l "
            "JOIN sections sec ON l.section_id = sec.id "
            "JOIN songs s ON sec.song_id = s.id "
            "WHERE s.genre_cohort = ? AND s.role = 'solo' AND s.corpus = 'genius-pro'",
            (cohort,),
        ).fetchall()

        if not rows:
            lexical_stats[cohort] = {"n": 0}
            continue

        word_counts = [r[1] for r in rows if r[1] is not None]
        syl_counts = [r[2] for r in rows if r[2] is not None]

        # TTR: need total words and unique words — sample from text_norm
        all_words: List[str] = []
        for r in rows:
            if r[0]:
                all_words.extend(_WORD_RE.findall(r[0].lower()))

        ttr = len(set(all_words)) / len(all_words) if all_words else 0.0

        lexical_stats[cohort] = {
            "n_lines": len(rows),
            "avg_words_per_line": round(statistics.mean(word_counts), 2) if word_counts else 0.0,
            "avg_syl_per_line": round(statistics.mean(syl_counts), 2) if syl_counts else 0.0,
            "ttr": round(ttr, 4),
            "total_words": len(all_words),
        }

    # Top vocabulary by cohort (from tokens table if available, else from lines)
    top_vocab = {}
    for cohort in ("drill_trap", "pop"):
        try:
            rows = conn.execute(
                "SELECT t.form, sum(t.freq) FROM tokens t "
                "JOIN songs s ON t.song_id = s.id "
                "WHERE s.genre_cohort = ? AND s.role = 'solo' AND s.corpus = 'genius-pro' "
                "GROUP BY t.form ORDER BY sum(t.freq) DESC LIMIT 50",
                (cohort,),
            ).fetchall()
            top_vocab[cohort] = [(r[0], r[1]) for r in rows]
        except sqlite3.OperationalError:
            # No tokens table — compute from lines
            word_counter: Counter = Counter()
            rows = conn.execute(
                "SELECT l.text_norm FROM lines l "
                "JOIN sections sec ON l.section_id = sec.id "
                "JOIN songs s ON sec.song_id = s.id "
                "WHERE s.genre_cohort = ? AND s.role = 'solo' AND s.corpus = 'genius-pro'",
                (cohort,),
            ).fetchall()
            for r in rows:
                if r[0]:
                    word_counter.update(_WORD_RE.findall(r[0].lower()))
            top_vocab[cohort] = word_counter.most_common(50)

    conn.close()

    return {
        "cohort_counts": cohort_counts,
        "rhyme_stats": rhyme_stats,
        "structure_stats": structure_stats,
        "type_dist": type_dist,
        "lexical_stats": lexical_stats,
        "top_vocab": top_vocab,
    }


# ── Main report generation ───────────────────────────────────────────

def main() -> None:
    print("Loading Suno export...")
    with _SUNO_EXPORT.open("r", encoding="utf-8") as f:
        suno_data = json.load(f)

    total_suno = suno_data["total_liked_songs"]
    songs = suno_data["songs"]
    songs_with_lyrics = [s for s in songs if s.get("lyrics", "").strip()]

    print(f"  Total Suno songs: {total_suno}")
    print(f"  Songs with lyrics: {len(songs_with_lyrics)}")

    # Aggregate Suno metrics
    all_rfs: List[float] = []
    all_pcts: List[float] = []
    all_irrs: List[float] = []
    all_ttrs: List[float] = []
    all_syls: List[float] = []
    all_sections: List[int] = []
    all_lines: List[int] = []
    all_schemes: List[str] = []
    suno_vocab: Counter = Counter()
    suno_type_dist: Counter = Counter()

    # Process each song
    for i, song in enumerate(songs_with_lyrics):
        if (i + 1) % 100 == 0:
            print(f"  Processing {i + 1}/{len(songs_with_lyrics)}...")

        lyrics = song["lyrics"]
        sections = parse_suno_lyrics(lyrics)
        all_lines_list = [l for s in sections for l in s["lines"]]

        if not all_lines_list:
            continue

        # Rhyme metrics
        rm = compute_rhyme_metrics(all_lines_list)
        all_rfs.append(rm["rhyme_factor"])
        all_pcts.append(rm["pct_multis"])
        all_irrs.append(rm["internal_rhyme_rate"])
        all_schemes.append(rm["scheme"])

        # Lexical metrics
        lm = compute_lexical_metrics(all_lines_list)
        all_ttrs.append(lm["ttr"])
        all_syls.append(lm["avg_syllables_per_line"])
        suno_vocab.update(
            w.lower() for w in _WORD_RE.findall(_normalize_ascii(" ".join(all_lines_list)))
        )

        # Structure metrics
        sm = compute_structure_metrics(sections)
        all_sections.append(sm["n_sections"])
        all_lines.append(sm["total_lines"])
        suno_type_dist.update(sm["section_type_dist"].keys())

    # Also build full vocab counter from all lyrics
    print("  Building full Suno vocabulary...")
    full_vocab: Counter = Counter()
    for song in songs_with_lyrics:
        lyrics = song["lyrics"]
        full_vocab.update(
            w.lower() for w in _WORD_RE.findall(_normalize_ascii(lyrics))
        )

    # Slang overlap
    print("  Computing slang overlap...")
    slang = compute_slang_overlap(full_vocab, _DB_PATH)

    # Genius comparison stats
    print("  Querying Genius DB for comparison...")
    genius = get_genius_stats(_DB_PATH)

    # ── Generate report ───────────────────────────────────────────────
    print("  Generating report...")

    def _median(vals: List[float]) -> float:
        return round(statistics.median(vals), 4) if vals else 0.0

    def _mean(vals: List[float]) -> float:
        return round(statistics.mean(vals), 4) if vals else 0.0

    report_lines: List[str] = []
    r = report_lines.append

    r("# Suno Gap Report: AI-Generated vs Professional Lyrics")
    r("")
    r(f"**Generated:** 2026-07-30  ")
    r(f"**Suno corpus:** {total_suno} total liked tracks, {len(songs_with_lyrics)} with lyrics  ")
    r(f"**Genius corpus:** {genius['cohort_counts']}  ")
    r(f"**DB:** `{_DB_PATH}`")
    r("")
    r("---")
    r("")

    # L1: Structure
    r("## L1 — Structure")
    r("")
    r("| Metric | Suno AI | Genius Drill (solo) | Genius Pop (solo) |")
    r("|--------|---------|---------------------|--------------------|")
    gs_drill = genius["structure_stats"].get("drill_trap", {})
    gs_pop = genius["structure_stats"].get("pop", {})
    r(f"| Songs analyzed | {len(songs_with_lyrics)} | {gs_drill.get('n', 0)} | {gs_pop.get('n', 0)} |")
    r(f"| Avg sections/song | {_mean(all_sections)} | {gs_drill.get('avg_sections', 'N/A')} | {gs_pop.get('avg_sections', 'N/A')} |")
    r(f"| Median sections/song | {_median(all_sections)} | {gs_drill.get('median_sections', 'N/A')} | {gs_pop.get('median_sections', 'N/A')} |")
    r(f"| Avg lines/song | {_mean(all_lines)} | {gs_drill.get('avg_lines', 'N/A')} | {gs_pop.get('avg_lines', 'N/A')} |")
    r(f"| Median lines/song | {_median(all_lines)} | {gs_drill.get('median_lines', 'N/A')} | {gs_pop.get('median_lines', 'N/A')} |")
    r("")

    r("### Section Type Distribution")
    r("")
    r("| Type | Suno % | Drill % | Pop % |")
    r("|------|--------|---------|-------|")
    suno_total_sec = sum(all_sections) if all_sections else 1
    drill_types = genius["type_dist"].get("drill_trap", {})
    pop_types = genius["type_dist"].get("pop", {})
    drill_total = sum(drill_types.values()) or 1
    pop_total = sum(pop_types.values()) or 1
    all_types = set(list(suno_type_dist.keys()) + list(drill_types.keys()) + list(pop_types.keys()))
    for t in sorted(all_types):
        suno_pct = round(suno_type_dist.get(t, 0) / suno_total_sec * 100, 1)
        drill_pct = round(drill_types.get(t, 0) / drill_total * 100, 1)
        pop_pct = round(pop_types.get(t, 0) / pop_total * 100, 1)
        r(f"| {t} | {suno_pct}% | {drill_pct}% | {pop_pct}% |")
    r("")

    # L2: Rhyme
    r("## L2 — Rhyme Metrics")
    r("")
    r("| Metric | Suno AI (median) | Suno AI (mean) | Drill (median) | Pop (median) |")
    r("|--------|------------------|-----------------|-----------------|---------------|")
    rs_drill = genius["rhyme_stats"].get("drill_trap", {})
    rs_pop = genius["rhyme_stats"].get("pop", {})
    r(f"| Rhyme Factor | {_median(all_rfs)} | {_mean(all_rfs)} | {rs_drill.get('rf_median', 'N/A')} | {rs_pop.get('rf_median', 'N/A')} |")
    r(f"| % Multisyllabic | {_median(all_pcts)} | {_mean(all_pcts)} | {rs_drill.get('pct_multis_median', 'N/A')} | {rs_pop.get('pct_multis_median', 'N/A')} |")
    r(f"| Internal Rhyme Rate | {_median(all_irrs)} | {_mean(all_irrs)} | {rs_drill.get('irr_median', 'N/A')} | {rs_pop.get('irr_median', 'N/A')} |")
    r("")

    r("### Rhyme Scheme Distribution (Suno)")
    r("")
    r("| Scheme | Count | % |")
    r("|--------|-------|---|")
    scheme_counts = Counter(all_schemes)
    total_schemes = sum(scheme_counts.values()) or 1
    for scheme, cnt in scheme_counts.most_common(10):
        r(f"| {scheme} | {cnt} | {round(cnt / total_schemes * 100, 1)}% |")
    r("")

    r("### Genius Drill Top Schemes")
    r("")
    for scheme, cnt in rs_drill.get("top_schemes", {}).items():
        r(f"- **{scheme}**: {cnt}")
    r("")

    # L3: Lexical
    r("## L3 — Lexical Metrics")
    r("")
    r("| Metric | Suno AI | Genius Drill (solo) | Genius Pop (solo) |")
    r("|--------|---------|---------------------|--------------------|")
    ls_drill = genius["lexical_stats"].get("drill_trap", {})
    ls_pop = genius["lexical_stats"].get("pop", {})
    r(f"| TTR (type-token ratio) | {_median(all_ttrs)} | {ls_drill.get('ttr', 'N/A')} | {ls_pop.get('ttr', 'N/A')} |")
    r(f"| Avg syllables/line | {_median(all_syls)} | {ls_drill.get('avg_syl_per_line', 'N/A')} | {ls_pop.get('avg_syl_per_line', 'N/A')} |")
    r(f"| Avg words/line | N/A | {ls_drill.get('avg_words_per_line', 'N/A')} | {ls_pop.get('avg_words_per_line', 'N/A')} |")
    r(f"| Total words (corpus) | {sum(full_vocab.values())} | {ls_drill.get('total_words', 'N/A')} | {ls_pop.get('total_words', 'N/A')} |")
    r("")

    r("### Top-50 Vocabulary Comparison")
    r("")
    r("| Rank | Suno Term | Suno Freq | Drill Term | Drill Freq | Pop Term | Pop Freq |")
    r("|------|-----------|-----------|------------|------------|----------|----------|")
    suno_top = full_vocab.most_common(50)
    drill_top = genius["top_vocab"].get("drill_trap", [])
    pop_top = genius["top_vocab"].get("pop", [])
    for i in range(50):
        s_term, s_freq = suno_top[i] if i < len(suno_top) else ("—", 0)
        d_term, d_freq = drill_top[i] if i < len(drill_top) else ("—", 0)
        p_term, p_freq = pop_top[i] if i < len(pop_top) else ("—", 0)
        r(f"| {i+1} | {s_term} | {s_freq} | {d_term} | {d_freq} | {p_term} | {p_freq} |")
    r("")

    # L4: Slang overlap
    r("## L4 — Slang & Distinctiveness Overlap")
    r("")
    r(f"Suno vocabulary overlaps with **{slang['drill_overlap_count']}** drill-distinctive terms "
      f"and **{slang['pop_overlap_count']}** pop-distinctive terms from the Genius slang lexicon.")
    r("")
    r("| Metric | Value |")
    r("|--------|-------|")
    r(f"| Drill-distinctive overlap (weighted %) | {slang['drill_overlap_pct']}% |")
    r(f"| Pop-distinctive overlap (weighted %) | {slang['pop_overlap_pct']}% |")
    r(f"| Drill overlap (unique terms) | {slang['drill_overlap_count']} |")
    r(f"| Pop overlap (unique terms) | {slang['pop_overlap_count']} |")
    r("")

    r("### Top Drill-Distinctive Terms Found in Suno")
    r("")
    for term in slang["drill_overlap_terms"]:
        r(f"- **{term}** (freq: {full_vocab.get(term, 0)})")
    r("")

    r("### Top Pop-Distinctive Terms Found in Suno")
    r("")
    for term in slang["pop_overlap_terms"]:
        r(f"- **{term}** (freq: {full_vocab.get(term, 0)})")
    r("")

    # Summary
    r("---")
    r("")
    r("## Summary & Key Gaps")
    r("")
    r("### Structure")
    r(f"- Suno avg sections/song: **{_mean(all_sections)}** vs Genius drill: **{gs_drill.get('avg_sections', 'N/A')}**, pop: **{gs_pop.get('avg_sections', 'N/A')}**")
    r(f"- Suno avg lines/song: **{_mean(all_lines)}** vs Genius drill: **{gs_drill.get('avg_lines', 'N/A')}**, pop: **{gs_pop.get('avg_lines', 'N/A')}**")
    r("")
    r("### Rhyme Craft")
    r(f"- Suno RF median: **{_median(all_rfs)}** vs Drill: **{rs_drill.get('rf_median', 'N/A')}**, Pop: **{rs_pop.get('rf_median', 'N/A')}**")
    r(f"- Suno %multis median: **{_median(all_pcts)}** vs Drill: **{rs_drill.get('pct_multis_median', 'N/A')}**, Pop: **{rs_pop.get('pct_multis_median', 'N/A')}**")
    r(f"- Suno IRR median: **{_median(all_irrs)}** vs Drill: **{rs_drill.get('irr_median', 'N/A')}**, Pop: **{rs_pop.get('irr_median', 'N/A')}**")
    r("")
    r("### Lexical")
    r(f"- Suno TTR: **{_median(all_ttrs)}** vs Drill: **{ls_drill.get('ttr', 'N/A')}**, Pop: **{ls_pop.get('ttr', 'N/A')}**")
    r(f"- Suno syl/line: **{_median(all_syls)}** vs Drill: **{ls_drill.get('avg_syl_per_line', 'N/A')}**, Pop: **{ls_pop.get('avg_syl_per_line', 'N/A')}**")
    r("")
    r("### Slang")
    r(f"- Drill overlap: **{slang['drill_overlap_pct']}%** (weighted), **{slang['drill_overlap_count']}** unique terms")
    r(f"- Pop overlap: **{slang['pop_overlap_pct']}%** (weighted), **{slang['pop_overlap_count']}** unique terms")
    r("")

    # Write report
    _REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    _REPORT_PATH.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"\nReport written to: {_REPORT_PATH}")
    print(f"  Suno songs with lyrics: {len(songs_with_lyrics)}")
    print(f"  Suno RF median: {_median(all_rfs)}")
    print(f"  Suno TTR median: {_median(all_ttrs)}")


if __name__ == "__main__":
    main()
