"""Rhyme scheme checker for lyrics.

Reads plain-text lyrics, parses sections, detects rhyme schemes via
``rhyme_miner``, and optionally compares against an expected scheme.
Suggests fixes for broken lines by matching vowel skeletons.

Usage::

    from toolshop.scheme_checker import check_scheme
    result = check_scheme(Path("lyrics.txt"), expected_scheme="AABB")
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from toolshop.lyricsdb import normalize_text, parse_section_label
from toolshop.rhyme_miner import (
    extract_end_rhyme,
    find_rhymes,
    infer_scheme,
    rhyme_factor,
    vowel_skeleton,
    _word_skeleton,
)

# Matches bracketed section labels: [Verse 1], [Chorus], [Strofa 2: Jala]
_SECTION_RE = re.compile(r"^\[([^\]]+)\]\s*$")


def _parse_sections(raw_lines: List[str]) -> List[Tuple[str, List[str]]]:
    """Split raw lines into (section_type, normalized_lines) pairs.

    Lines inside brackets are treated as section labels.  Lines before
    the first label are grouped as an ``intro`` section.
    """
    sections: List[Tuple[str, List[str]]] = []
    current_type = "intro"
    current_lines: List[str] = []

    for line in raw_lines:
        stripped = line.strip()
        if not stripped:
            continue

        m = _SECTION_RE.match(stripped)
        if m:
            if current_lines:
                sections.append((current_type, current_lines))
            label = m.group(1)
            parsed = parse_section_label(label)
            current_type = parsed.type
            current_lines = []
        else:
            current_lines.append(normalize_text(stripped))

    if current_lines:
        sections.append((current_type, current_lines))

    return sections


def _suggest_fixes(
    lines: List[str],
    groups: List,
    broken_indices: List[int],
    expected_scheme: str,
) -> List[Dict[str, Any]]:
    """Suggest fix candidates for broken lines.

    For each broken line, find the expected rhyme partner (the line with
    the same expected letter), get its end-rhyme skeleton, then find
    words from other lines in the section that share that skeleton.
    """
    fixes: List[Dict[str, Any]] = []

    # Build expected letter per line
    if len(expected_scheme) != len(lines):
        return fixes

    # Collect all words in the section with their end-skeletons
    word_skeletons: Dict[str, List[str]] = {}
    for line in lines:
        words = re.findall(r"[a-zA-Z]+", line)
        for w in words:
            skel = _word_skeleton(w)
            if skel and len(skel) >= 2:
                word_skeletons.setdefault(skel, []).append(w)

    for idx in broken_indices:
        expected_letter = expected_scheme[idx]
        # Find the partner line with the same letter (not this one)
        partner_idx = None
        for i, letter in enumerate(expected_scheme):
            if i != idx and letter == expected_letter:
                partner_idx = i
                break

        if partner_idx is None:
            fixes.append({
                "line": idx,
                "word": _last_word(lines[idx]),
                "expected_letter": expected_letter,
                "candidates": [],
            })
            continue

        partner_skel = extract_end_rhyme(lines[partner_idx], n_syllables=2)
        candidates: List[str] = []
        if partner_skel and len(partner_skel) >= 2:
            # Find words whose end-skeleton matches the partner's
            for w in re.findall(r"[a-zA-Z]+", lines[partner_idx]):
                w_skel = _word_skeleton(w)
                if w_skel and w_skel.endswith(partner_skel[-2:]):
                    if w not in candidates:
                        candidates.append(w)
            # Also check all words in the section
            for skel, words in word_skeletons.items():
                if skel.endswith(partner_skel[-2:]):
                    for w in words:
                        if w not in candidates and w != _last_word(lines[idx]):
                            candidates.append(w)

        fixes.append({
            "line": idx,
            "word": _last_word(lines[idx]),
            "expected_letter": expected_letter,
            "partner_skeleton": partner_skel,
            "candidates": candidates[:10],
        })

    return fixes


def _last_word(line: str) -> str:
    """Return the last alphabetic word in a line."""
    words = re.findall(r"[a-zA-Z]+", line)
    return words[-1] if words else ""


def _compare_schemes(
    detected: str, expected: str, n_lines: int
) -> Tuple[float, List[int]]:
    """Compare detected vs expected scheme.

    Returns (match_pct, broken_line_indices).
    """
    if not expected or n_lines == 0:
        return 100.0, []

    # Pad or truncate to n_lines
    det = detected.ljust(n_lines, "?")[:n_lines]
    exp = expected.ljust(n_lines, "?")[:n_lines]

    matches = sum(1 for d, e in zip(det, exp) if d == e)
    match_pct = round(matches / n_lines * 100, 1) if n_lines else 0.0
    broken = [i for i, (d, e) in enumerate(zip(det, exp)) if d != e]

    return match_pct, broken


def check_scheme(
    input_path: Path,
    expected_scheme: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Check rhyme scheme of lyrics against an expected pattern.

    Args:
        input_path: Path to a plain-text lyrics file.
        expected_scheme: Expected scheme string (e.g. "AABB").  If None,
            only detected schemes are reported.
        db_path: Reserved for future DB-based fix suggestions.

    Returns:
        Dict with ``sections`` list, each containing:
            - type: section type (strofa, refren, etc.)
            - detected_scheme: inferred scheme string
            - expected_scheme: expected scheme (or None)
            - match_pct: percentage of lines matching expected scheme
            - broken_lines: list of line indices that break the pattern
            - fixes: list of fix suggestion dicts
            - rhyme_factor: rhyme density for the section
            - line_count: number of lines in the section
    """
    text = Path(input_path).read_text(encoding="utf-8")
    raw_lines = text.split("\n")
    sections = _parse_sections(raw_lines)

    results: List[Dict[str, Any]] = []

    for section_type, lines in sections:
        if not lines:
            continue

        groups = find_rhymes(lines, min_match=2)
        detected = infer_scheme(groups, len(lines))
        rf = rhyme_factor(lines)

        section_result: Dict[str, Any] = {
            "type": section_type,
            "detected_scheme": detected,
            "expected_scheme": expected_scheme,
            "match_pct": 100.0,
            "broken_lines": [],
            "fixes": [],
            "rhyme_factor": rf,
            "line_count": len(lines),
        }

        if expected_scheme:
            match_pct, broken = _compare_schemes(
                detected, expected_scheme, len(lines)
            )
            section_result["match_pct"] = match_pct
            section_result["broken_lines"] = broken
            section_result["fixes"] = _suggest_fixes(
                lines, groups, broken, expected_scheme
            )

        results.append(section_result)

    return {"sections": results}
