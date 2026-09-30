"""Detect which shown suggestions ended up in the user's own text (strongest signal)."""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path

_WORD = re.compile(r"[^\W\d_]+")


def read_text(path: Path | str) -> str:
    """UTF-8 (BOM ok), falling back to cp1250 for legacy Windows files; NFC-normalized."""
    raw = Path(path).read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("cp1250", errors="replace")
    return unicodedata.normalize("NFC", text)


def tokenize(text: str) -> list[str]:
    """Lowercased alphabetic words; keeps diacritics (NFC)."""
    return _WORD.findall(unicodedata.normalize("NFC", text).lower())


def token_spans(text: str) -> list[tuple[str, int, int]]:
    """(token, start, end) char offsets, lowercased — same tokens as `tokenize`."""
    return [(m.group(0), m.start(), m.end())
            for m in _WORD.finditer(unicodedata.normalize("NFC", text).lower())]


def scan(path: Path | str, days: int, con) -> list[str]:
    """Candidates shown in the last `days` days that appear in the file.

    Multi-word candidates match as consecutive words. Sorted alphabetically.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(timespec="seconds")
    shown = [r[0] for r in con.execute("SELECT DISTINCT candidate FROM shown WHERE ts >= ?", (cutoff,))]
    hay = " " + " ".join(tokenize(read_text(path))) + " "
    hits = []
    for cand in shown:
        toks = tokenize(cand)
        if toks and f" {' '.join(toks)} " in hay:
            hits.append(cand)
    return sorted(hits)
