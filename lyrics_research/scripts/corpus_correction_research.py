#!/usr/bin/env python3
"""Corpus correction research: English loanwords, section labels, diacritic pairs, slang, call-and-response."""

from __future__ import annotations

import json
import sqlite3
import sys
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "toolshop" / "lyrics" / "lyrics.db"
REPORT_PATH = Path(__file__).resolve().parent.parent / "reports" / "corpus_correction_research.json"

# English seed list from analyze_lyrics.py english_words() function
COMMON_ENGLISH = {
    "the", "and", "for", "you", "are", "not", "but", "with", "your", "from",
    "have", "has", "had", "this", "that", "when", "where", "what", "who",
    "how", "why", "yes", "no", "hey", "ho", "go", "tell", "know", "time",
    "its", "just", "only", "like", "all", "get", "got", "can", "will", "would",
    "show", "some", "everybody", "put", "hands", "up", "we", "ve", "ll", "re",
    "oh", "yeah", "u", "mwah", "kiss", "da", "ba", "he", "she", "they", "them",
    "his", "her", "our", "my", "mine", "it", "is", "am", "be", "been",
    "being", "do", "does", "did", "done", "doing", "so", "if", "because", "as",
    "than", "then", "now", "here", "there", "again", "once", "never", "always",
    "every", "one", "two", "three", "four", "first", "last", "next", "other",
    "new", "old", "good", "bad", "big", "small", "little", "right", "left",
    "love", "live", "alive", "high", "drive", "dry", "forever", "toy", "boy",
    "game", "chess", "single", "multiplayer", "artificial", "intelligence",
    "modern", "technology", "generation", "queen", "king", "boom", "bang",
    "bitch", "mode", "switch", "broke", "gangsta", "nasty", "girl", "squad",
    "fashion", "models", "money", "cash", "drill", "trap", "rap", "magic",
    "playback", "vroom", "ave", "choky", "felna", "brena", "hotel", "barca",
    "face", "supreme", "bmw", "benz", "red", "bull", "dior", "gucci",
    "fendi", "vuitton", "louis", "paciotti", "martini", "bikini", "popov",
    "amor", "naomi", "dogg", "tarantino", "wannabe", "taxi", "tv",
}

# Diacritic mapping for Serbian/Croatian/Bosnian
DIACRITIC_MAP = str.maketrans("čćšžđ", "ccszd")


# ── Helpers ───────────────────────────────────────────────────────────


def strip_diacritics(text: str) -> str:
    """Strip Serbian diacritics: č→c, ć→c, š→s, ž→z, đ→d."""
    return text.translate(DIACRITIC_MAP)


def has_diacritics(text: str) -> bool:
    """Check if text contains any Serbian diacritic characters."""
    return any(c in text for c in "čćšžđ")


def levenshtein_one(s1: str, s2: str) -> bool:
    """Check if two strings have Levenshtein distance of exactly 1."""
    if abs(len(s1) - len(s2)) > 1:
        return False
    if len(s1) == len(s2):
        diffs = sum(1 for a, b in zip(s1, s2) if a != b)
        return diffs == 1
    # Length differs by 1 — check single insertion/deletion
    longer, shorter = (s1, s2) if len(s1) > len(s2) else (s2, s1)
    i = j = 0
    found_diff = False
    while i < len(longer) and j < len(shorter):
        if longer[i] != shorter[j]:
            if found_diff:
                return False
            found_diff = True
            i += 1  # skip one char in longer
        else:
            i += 1
            j += 1
    return True


# ── Analysis functions ────────────────────────────────────────────────


def get_corpus_stats(conn: sqlite3.Connection) -> dict:
    """Get high-level corpus statistics."""
    c = conn.cursor()
    songs = c.execute("SELECT COUNT(*) FROM songs").fetchone()[0]
    lines = c.execute("SELECT COUNT(*) FROM lines").fetchone()[0]
    tokens = c.execute("SELECT COUNT(*) FROM tokens").fetchone()[0]
    return {"songs": songs, "lines": lines, "tokens": tokens}


def analyze_english_loanwords(conn: sqlite3.Connection) -> list[dict]:
    """
    English loanword inventory: for each common English word found in the corpus,
    report frequency, cohort split, and 1-edit-distance variants.
    """
    c = conn.cursor()

    # Get all unique token forms with frequencies, joined to songs for cohort
    rows = c.execute("""
        SELECT t.form, s.genre_cohort, COUNT(*) as freq
        FROM tokens t
        JOIN lines l ON t.line_id = l.id
        JOIN sections sec ON l.section_id = sec.id
        JOIN songs s ON sec.song_id = s.id
        WHERE t.form IS NOT NULL
        GROUP BY t.form, s.genre_cohort
    """).fetchall()

    # Build per-token cohort frequencies
    token_cohort_freq: dict[str, dict[str, int]] = {}
    token_total_freq: dict[str, int] = {}
    all_forms_set: set[str] = set()

    for form, cohort, freq in rows:
        form_lower = form.lower() if form else ""
        if not form_lower:
            continue
        all_forms_set.add(form_lower)
        if form_lower not in token_cohort_freq:
            token_cohort_freq[form_lower] = {}
        token_cohort_freq[form_lower][cohort or "NULL"] = (
            token_cohort_freq[form_lower].get(cohort or "NULL", 0) + freq
        )
        token_total_freq[form_lower] = token_total_freq.get(form_lower, 0) + freq

    # Get all unique forms for edit-distance search (as a sorted list for efficiency)
    all_forms_sorted = sorted(all_forms_set)

    results = []
    for word in sorted(COMMON_ENGLISH):
        if word not in token_total_freq:
            # Word not in corpus at all — skip
            continue

        cohort_freqs = token_cohort_freq.get(word, {})
        drill_freq = cohort_freqs.get("drill_trap", 0)
        pop_freq = cohort_freqs.get("pop", 0)
        total = token_total_freq[word]

        # Determine dominant cohort
        if drill_freq > pop_freq:
            cohort = "drill_trap"
        elif pop_freq > drill_freq:
            cohort = "pop"
        else:
            cohort = "tie"

        # Find 1-edit-distance variants in the corpus
        variants = []
        for candidate in all_forms_sorted:
            if candidate == word:
                continue
            if levenshtein_one(word, candidate):
                var_total = token_total_freq.get(candidate, 0)
                if var_total > 0:
                    variants.append({
                        "variant": candidate,
                        "frequency": var_total,
                    })

        results.append({
            "token": word,
            "frequency": total,
            "drill_trap_freq": drill_freq,
            "pop_freq": pop_freq,
            "cohort": cohort,
            "variants": sorted(variants, key=lambda v: v["frequency"], reverse=True),
        })

    # Sort by total frequency descending
    results.sort(key=lambda x: x["frequency"], reverse=True)
    return results


def analyze_section_labels(conn: sqlite3.Connection) -> list[dict]:
    """Section label census: top 100 label_raw by count."""
    c = conn.cursor()
    rows = c.execute("""
        SELECT label_raw, COUNT(*) as cnt
        FROM sections
        WHERE label_raw IS NOT NULL
        GROUP BY label_raw
        ORDER BY cnt DESC
        LIMIT 100
    """).fetchall()

    return [{"label_raw": label, "count": cnt} for label, cnt in rows]


def analyze_diacritic_pairs(conn: sqlite3.Connection) -> list[dict]:
    """Find words appearing both with and without diacritics."""
    c = conn.cursor()

    # Get all unique token forms with frequencies
    rows = c.execute("""
        SELECT form, COUNT(*) as freq
        FROM tokens
        WHERE form IS NOT NULL AND form != ''
        GROUP BY form
    """).fetchall()

    # Group by diacritic-stripped key
    groups: dict[str, list[tuple[str, int]]] = {}
    for form, freq in rows:
        key = strip_diacritics(form.lower())
        if key not in groups:
            groups[key] = []
        groups[key].append((form, freq))

    # Find pairs where both diacritic and non-diacritic forms exist
    results = []
    for key, members in groups.items():
        diacritic_forms = [(f, fr) for f, fr in members if has_diacritics(f.lower())]
        plain_forms = [(f, fr) for f, fr in members if not has_diacritics(f.lower())]

        if diacritic_forms and plain_forms:
            for d_form, d_freq in diacritic_forms:
                for p_form, p_freq in plain_forms:
                    results.append({
                        "diacritic_form": d_form,
                        "diacritic_freq": d_freq,
                        "plain_form": p_form,
                        "plain_freq": p_freq,
                        "normalized_key": key,
                    })

    # Sort by total frequency (diacritic + plain) descending
    results.sort(key=lambda x: x["diacritic_freq"] + x["plain_freq"], reverse=True)
    return results


def analyze_slang_terms(conn: sqlite3.Connection) -> list[dict]:
    """Top 50 OOV slang terms by frequency."""
    c = conn.cursor()
    rows = c.execute("""
        SELECT form, lemma, freq, drill_freq, pop_freq, distinctiveness, is_oov
        FROM slang_terms
        ORDER BY freq DESC
        LIMIT 50
    """).fetchall()

    return [
        {
            "form": form,
            "lemma": lemma,
            "freq": freq,
            "drill_freq": drill_freq,
            "pop_freq": pop_freq,
            "distinctiveness": distinctiveness,
            "is_oov": bool(is_oov) if is_oov is not None else False,
        }
        for form, lemma, freq, drill_freq, pop_freq, distinctiveness, is_oov in rows
    ]


def analyze_call_response(conn: sqlite3.Connection) -> list[dict]:
    """Call-and-response patterns in section labels."""
    c = conn.cursor()
    rows = c.execute("""
        SELECT label_raw, COUNT(*) as cnt
        FROM sections
        WHERE label_raw IS NOT NULL
          AND (
            LOWER(label_raw) LIKE '%call%'
            OR LOWER(label_raw) LIKE '%answer%'
            OR LOWER(label_raw) LIKE '%response%'
            OR LOWER(label_raw) LIKE '%duet%'
            OR label_raw LIKE '%(%'
          )
        GROUP BY label_raw
        ORDER BY cnt DESC
    """).fetchall()

    return [{"label_raw": label, "count": cnt} for label, cnt in rows]


# ── Main ──────────────────────────────────────────────────────────────


def main() -> None:
    if not DB_PATH.exists():
        print(f"ERROR: Database not found at {DB_PATH}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(str(DB_PATH))
    try:
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "db_path": str(DB_PATH),
            "corpus_stats": get_corpus_stats(conn),
            "english_loanwords": analyze_english_loanwords(conn),
            "section_label_census": analyze_section_labels(conn),
            "diacritic_variant_pairs": analyze_diacritic_pairs(conn),
            "oov_slang_terms": analyze_slang_terms(conn),
            "call_and_response_patterns": analyze_call_response(conn),
        }
    finally:
        conn.close()

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with REPORT_PATH.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # Summary to stdout
    print(f"Report saved to {REPORT_PATH}")
    print(f"  Corpus: {report['corpus_stats']['songs']} songs, "
          f"{report['corpus_stats']['lines']} lines, "
          f"{report['corpus_stats']['tokens']} tokens")
    print(f"  English loanwords: {len(report['english_loanwords'])}")
    print(f"  Section labels: {len(report['section_label_census'])}")
    print(f"  Diacritic pairs: {len(report['diacritic_variant_pairs'])}")
    print(f"  Slang terms: {len(report['oov_slang_terms'])}")
    print(f"  Call-and-response: {len(report['call_and_response_patterns'])}")


if __name__ == "__main__":
    main()
