"""Cliché density checker for AI-generated lyrics.

Detects English clichés and audio metadata token contamination in lyric text.
Uses the cliché list from ``lyrics_research/data/cliche_list.json``.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Dict, List

from toolshop.lyrics_analyzer import _tokenize


_DIACRITIC_MAP = str.maketrans({
    "č": "c", "ć": "c", "š": "s", "ž": "z", "đ": "dj",
    "Č": "c", "Ć": "c", "Š": "s", "Ž": "z", "Đ": "dj",
})


def _ascii_fold(text: str) -> str:
    """Strip Serbian diacritics (č→c, ć→c, š→s, ž→z, đ→dj)."""
    return text.translate(_DIACRITIC_MAP)

_DEFAULT_CLICHE_PATH = (
    Path(__file__).resolve().parent.parent
    / "lyrics_research"
    / "data"
    / "cliche_list.json"
)


def _load_cliche_data(cliche_data_path: Path | None) -> Dict:
    """Load cliché data from JSON file."""
    path = cliche_data_path or _DEFAULT_CLICHE_PATH
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def check_cliches(
    text: str,
    cliche_data_path: Path | None = None,
    include_balkan: bool = False,
) -> Dict:
    """Check lyrics text for clichés and audio metadata contamination.

    Scans for English clichés (single-word and multi-word phrases) from
    ``english_cliches`` and ``english_extended`` lists, plus optionally
    ``balkan_cliches``.  Also detects audio metadata token contamination
    (``female``, ``male``, ``chorus``, etc.) separately.

    Args:
        text: Lyrics text to analyse.
        cliche_data_path: Path to ``cliche_list.json``.  Defaults to
            ``lyrics_research/data/cliche_list.json`` relative to repo root.
        include_balkan: If ``True``, also check ``balkan_cliches`` list.

    Returns:
        Dict with keys:
            - ``total_cliches``: number of cliché occurrences found
            - ``density_pct``: cliché token count / total tokens × 100
            - ``per_line_hits``: list of ``{"line": int, "terms": [str]}``
            - ``audio_token_count``: number of audio metadata tokens found
            - ``audio_token_lines``: list of 1-indexed line numbers
    """
    data = _load_cliche_data(cliche_data_path)

    # Build cliché sets.
    single_cliches: set[str] = set()
    multi_cliches: List[str] = []

    for key in ("english_cliches", "english_extended"):
        for term in data.get(key, []):
            term_lower = _ascii_fold(term.lower())
            if " " in term_lower:
                multi_cliches.append(term_lower)
            else:
                single_cliches.add(term_lower)

    if include_balkan:
        for term in data.get("balkan_cliches", []):
            term_lower = _ascii_fold(term.lower())
            if " " in term_lower:
                multi_cliches.append(term_lower)
            else:
                single_cliches.add(term_lower)

    audio_tokens = set(t.lower() for t in data.get("audio_metadata_tokens", []))

    # Tokenize for density and single-word matching.
    all_tokens = _tokenize(text)
    total_tokens = len(all_tokens)

    # Single-word cliché matches at token level.
    cliche_token_count = sum(1 for t in all_tokens if t in single_cliches)

    # Multi-word cliché: scan per-line with substring matching.
    lines = text.split("\n")
    per_line_hits: List[Dict] = []
    audio_token_lines: List[int] = []
    audio_token_count = 0

    for i, line in enumerate(lines, start=1):
        line_lower = line.lower()
        matched_terms: List[str] = []

        # Single-word clichés in this line.
        line_tokens = _tokenize(line)
        for t in line_tokens:
            if t in single_cliches:
                matched_terms.append(t)

        # Multi-word cliché phrases.
        for phrase in multi_cliches:
            if phrase in line_lower:
                matched_terms.append(phrase)
                # Count each word in the phrase as a cliché token.
                cliche_token_count += len(phrase.split())

        # Audio metadata tokens.
        for t in line_tokens:
            if t in audio_tokens:
                audio_token_count += 1
                if i not in audio_token_lines:
                    audio_token_lines.append(i)

        if matched_terms:
            per_line_hits.append({
                "line": i,
                "terms": matched_terms,
            })

    density_pct = round((cliche_token_count / total_tokens) * 100, 2) if total_tokens else 0.0

    return {
        "total_cliches": cliche_token_count,
        "density_pct": density_pct,
        "per_line_hits": per_line_hits,
        "audio_token_count": audio_token_count,
        "audio_token_lines": audio_token_lines,
    }
