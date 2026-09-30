"""Soft writing hints. They never block: every hint is advisory text with a
stable ``rule_id`` so votes and mutes can refer to it later.

Lexicons are copies kept in ``MAirina_Tucc/lexicons`` (see PROVENANCE.md) —
outside the gitignored ``data/`` so a fresh checkout has them. A missing file
disables only its own rule (one ``Note:`` line to stderr), never crashes.
No lazy-rhyme rule (deliberate, per the v2 plan).
"""

from __future__ import annotations

import csv
import os.path
import re
import sys
from functools import lru_cache

from mairina import ROOT
from mairina.used import tokenize

LEX_DIR = ROOT / "lexicons"

RULE_DIALECT_MIX = "dialect_mix"
RULE_CLICHE = "cliche"
RULE_CALQUE = "calque"
RULE_ABSTRACT_STACK = "abstract_stack"
RULE_SELF_RHYME = "self_rhyme"

SHORT_LABELS = {RULE_DIALECT_MIX: "dialect?", RULE_CLICHE: "cliché?",
                RULE_CALQUE: "calque?", RULE_ABSTRACT_STACK: "abstract×n?",
                RULE_SELF_RHYME: "self-rhyme?"}


def _missing(path, empty):
    print(f"Note: lexicon file missing: {path} — related hints disabled.",
          file=sys.stderr)
    return empty


def _text_list(path) -> list[str]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return _missing(path, [])
    return [line.lower() for raw in raw.splitlines()
            if (line := raw.strip()) and not line.startswith("#")]


def _concrete(path) -> set[str]:
    try:
        fh = path.open("r", encoding="utf-8")
    except OSError:
        return _missing(path, set())
    with fh:
        return {row[0].strip().lower() for row in csv.reader(fh)
                if row and row[0].strip().lower() != "noun"}


def _dialect(path) -> tuple[set[str], set[str]]:
    ekavica: set[str] = set()
    ijekavica: set[str] = set()
    try:
        fh = path.open("r", encoding="utf-8")
    except OSError:
        return _missing(path, (ekavica, ijekavica))
    with fh:
        for row in csv.reader(fh):
            if len(row) >= 2 and row[0].strip().lower() != "ekavica":
                ek, ij = row[0].strip().lower(), row[1].strip().lower()
                if ek == ij:
                    continue            # identical in both dialects: cannot mark mixing
                ekavica.add(ek)
                ijekavica.add(ij)
    return ekavica, ijekavica


@lru_cache(maxsize=1)
def load_lexicons() -> dict:
    """All rule lexicons from lexicons/ (mirrors qc.py's formats)."""
    d = LEX_DIR
    ekavica, ijekavica = _dialect(d / "dialect_pairs.csv")
    return {"calques": _text_list(d / "calques.txt"),
            "cliches": _text_list(d / "cliches.txt"),
            "abstract": set(_text_list(d / "abstract_nouns.txt")),
            "concrete": _concrete(d / "concrete_nouns.csv"),
            "ekavica": ekavica, "ijekavica": ijekavica}


def _phrase_hits(text: str, phrases: list[str]) -> list[str]:
    """Word-boundary phrase matches (so a phrase cannot fire inside a word)."""
    low = text.lower()
    out = []
    for phrase in phrases:
        if re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", low):
            out.append(phrase)
    return out


def line_hints(line: str, n: int, lex: dict | None = None) -> list[dict]:
    """Hints that need one line only: cliche/calque hits and abstract stacking."""
    lex = lex or load_lexicons()
    out = []
    for phrase in _phrase_hits(line, lex["cliches"]):
        out.append({"rule_id": RULE_CLICHE, "line": n,
                    "message": f"cliché phrase: '{phrase}'"})
    for phrase in _phrase_hits(line, lex["calques"]):
        out.append({"rule_id": RULE_CALQUE, "line": n,
                    "message": f"calqued phrase: '{phrase}'"})
    toks = tokenize(line)
    n_abs = sum(1 for t in toks if t in lex["abstract"])
    n_con = sum(1 for t in toks if t in lex["concrete"])
    if n_abs >= 2 and n_con == 0:
        out.append({"rule_id": RULE_ABSTRACT_STACK, "line": n,
                    "message": f"{n_abs} abstract nouns, no concrete image"})
    return out


def _self_rhyme(a: str, b: str, index=None) -> bool:
    """End words share a stem of >=4 letters, or a lemma (longer words only).

    'znaš'/'znam' (stem 'zna', 3 letters) and 'lava'/'laka' are deliberately
    NOT self-rhymes even though they share a lemma.
    """
    if a == b:
        return True
    if len(os.path.commonprefix([a, b])) >= 4:
        return True
    if index is not None and min(len(a), len(b)) >= 5:
        la = (index.forms.get(a) or {}).get("lemma")
        lb = (index.forms.get(b) or {}).get("lemma")
        return bool(la) and la == lb
    return False


def verse_hints(lines: list[str], lex: dict | None = None, index=None) -> list[dict]:
    """All hints for a verse: per-line rules plus dialect mixing and self-rhyme."""
    lex = lex or load_lexicons()
    out: list[dict] = []
    for i, line in enumerate(lines, 1):
        out.extend(line_hints(line, i, lex))

    # dialect_mix: both ekavica and ijekavica forms anywhere in the verse.
    ek_lines: dict[int, set] = {}
    ij_lines: dict[int, set] = {}
    for i, line in enumerate(lines, 1):
        toks = set(tokenize(line))
        if hits := toks & lex["ekavica"]:
            ek_lines[i] = hits
        if hits := toks & lex["ijekavica"]:
            ij_lines[i] = hits
    if ek_lines and ij_lines:
        for i in sorted(set(ek_lines) | set(ij_lines)):
            both = sorted(ek_lines.get(i, set()) | ij_lines.get(i, set()))
            out.append({"rule_id": RULE_DIALECT_MIX, "line": i,
                        "message": f"dialect mixing across the verse ({', '.join(both)})"})

    # self_rhyme: adjacent, non-identical lines ending on the same word/root.
    toks_per = [tokenize(l) for l in lines]
    for i in range(len(lines) - 1):
        a, b = toks_per[i][-1] if toks_per[i] else "", toks_per[i + 1][-1] if toks_per[i + 1] else ""
        if not a or not b:
            continue
        if lines[i].strip().lower() == lines[i + 1].strip().lower():
            continue                     # hook repetition is a device, not a hint
        if _self_rhyme(a, b, index):
            out.append({"rule_id": RULE_SELF_RHYME, "line": i + 2,
                        "message": f"line ends rhyme with themselves: '{a}'/'{b}'"})
    return out
