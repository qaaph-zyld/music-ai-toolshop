"""Audio metadata token cleaner for AI-generated lyrics.

Removes Suno-style audio metadata contamination (e.g. ``[female]``, ``[male]``,
``[chorus]``, ``[verse]``, ``[bass]``, ``[kick]``, ``[vox]``) from lyric text.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Dict, List, Tuple

_DEFAULT_CLICHE_PATH = (
    Path(__file__).resolve().parent.parent
    / "lyrics_research"
    / "data"
    / "cliche_list.json"
)


def _load_audio_tokens(cliche_data_path: Path | None) -> List[str]:
    """Load audio_metadata_tokens from cliche_list.json."""
    path = cliche_data_path or _DEFAULT_CLICHE_PATH
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return [t.lower() for t in data.get("audio_metadata_tokens", [])]


def clean_tokens(
    text: str, cliche_data_path: Path | None = None
) -> Tuple[str, Dict]:
    """Remove audio metadata tokens from lyrics text.

    Removes both bracketed (``[female]``) and unbracketed standalone
    occurrences of tokens listed in ``audio_metadata_tokens`` from
    ``cliche_list.json``.  Empty lines left after removal are stripped.

    Args:
        text: Raw lyrics text potentially containing audio metadata.
        cliche_data_path: Path to ``cliche_list.json``.  Defaults to
            ``lyrics_research/data/cliche_list.json`` relative to repo root.

    Returns:
        Tuple of ``(cleaned_text, report)`` where *report* has keys:
            - ``removed_count``: total tokens removed
            - ``per_token``: ``Counter`` mapping token → removal count
            - ``lines_affected``: list of 1-indexed line numbers that had removals
    """
    tokens = _load_audio_tokens(cliche_data_path)
    if not tokens:
        return text, {"removed_count": 0, "per_token": Counter(), "lines_affected": []}

    # Build regex for bracketed tokens: [female], [male], etc.
    bracket_alt = "|".join(re.escape(t) for t in tokens)
    bracket_re = re.compile(rf"\[({bracket_alt})\]", re.IGNORECASE)

    # Build regex for unbracketed standalone tokens (word-boundary match).
    # Sort longest-first so "bars" matches before "bar".
    sorted_tokens = sorted(tokens, key=len, reverse=True)
    standalone_alt = "|".join(re.escape(t) for t in sorted_tokens)
    standalone_re = re.compile(
        rf"(?<!\w)({standalone_alt})(?!\w)", re.IGNORECASE
    )

    per_token: Counter = Counter()
    lines_affected: List[int] = []
    removed_count = 0

    lines = text.split("\n")
    cleaned_lines: List[str] = []

    for i, line in enumerate(lines, start=1):
        original = line
        line_affected = False

        # Remove bracketed tokens first.
        for m in bracket_re.finditer(original):
            token = m.group(1).lower()
            per_token[token] += 1
            removed_count += 1
            line_affected = True
        original = bracket_re.sub("", original)

        # Remove unbracketed standalone tokens.
        for m in standalone_re.finditer(original):
            token = m.group(1).lower()
            per_token[token] += 1
            removed_count += 1
            line_affected = True
        original = standalone_re.sub("", original)

        if line_affected:
            lines_affected.append(i)

        # Strip trailing whitespace left by removals.
        original = original.rstrip()
        cleaned_lines.append(original)

    # Remove empty lines that result from token removal (only if the
    # original line had content beyond the tokens).
    result_lines: List[str] = []
    for orig, cleaned in zip(lines, cleaned_lines):
        if not cleaned.strip() and orig.strip():
            # Line became empty after removal — skip it.
            continue
        result_lines.append(cleaned)

    cleaned_text = "\n".join(result_lines)
    return cleaned_text, {
        "removed_count": removed_count,
        "per_token": per_token,
        "lines_affected": lines_affected,
    }
