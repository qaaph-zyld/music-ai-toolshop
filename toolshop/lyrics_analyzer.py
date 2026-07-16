"""Lyrics analyzer for basic NLP statistics.

Provides word/line frequency counts and length distributions for lyrics text.
Designed as a lightweight, extensible foundation for more advanced analysis.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional


def _tokenize(text: str) -> List[str]:
    """Split text into lowercase word tokens."""
    return re.findall(r"\b\w+\b", text.lower())


def analyze_text(lyrics: str) -> Dict:
    """Analyze lyrics text and return basic statistics.

    Args:
        lyrics: Clean lyrics text (UTF-8, newline-separated).

    Returns:
        Dict with:
            - total_words: int
            - unique_words: int
            - top_20_words: List of [word, count] pairs
            - total_lines: int
            - avg_line_length: float (in characters)
            - max_line_length: int (in characters)
    """
    lines = [l for l in lyrics.split("\n") if l.strip()]
    words = _tokenize(lyrics)
    word_counts = Counter(words)

    line_lengths = [len(l) for l in lines]
    total_lines = len(lines)
    avg_line_length = sum(line_lengths) / total_lines if total_lines else 0.0
    max_line_length = max(line_lengths) if line_lengths else 0

    return {
        "total_words": len(words),
        "unique_words": len(word_counts),
        "top_20_words": word_counts.most_common(20),
        "total_lines": total_lines,
        "avg_line_length": round(avg_line_length, 2),
        "max_line_length": max_line_length,
    }


def analyze_file(path: str | Path) -> Dict:
    """Load a lyrics JSON file and analyze its clean_lyrics field.

    Args:
        path: Path to a JSON file produced by the fetch/search commands.

    Returns:
        Analysis dict (same as analyze_text) plus the source file path.
    """
    p = Path(path)
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)

    clean = data.get("clean_lyrics", "")
    if not clean:
        raise ValueError(f"No 'clean_lyrics' field found in {path}")

    result = analyze_text(clean)
    result["source_file"] = str(p)
    return result


def print_report(stats: Dict) -> None:
    """Print a concise human-readable analysis report to stdout."""
    print(f"Total words:    {stats['total_words']}")
    print(f"Unique words:   {stats['unique_words']}")
    print(f"Total lines:    {stats['total_lines']}")
    print(f"Avg line len:   {stats['avg_line_length']} chars")
    print(f"Max line len:   {stats['max_line_length']} chars")
    print(f"\nTop 20 words:")
    for word, count in stats["top_20_words"]:
        print(f"  {word:>15s}  {count}")


def save_report(stats: Dict, output_path: str | Path) -> None:
    """Save analysis stats as a JSON file.

    Args:
        stats: Analysis dict from analyze_text or analyze_file.
        output_path: Destination JSON file path.
    """
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
