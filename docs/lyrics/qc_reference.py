#!/usr/bin/env python3
"""QC slop-detector — per-song pass/fail report against the Constitution."""

from __future__ import annotations

import csv
import json
import re
import sys
import tomllib
from collections import Counter
from pathlib import Path
from typing import Any

# Thresholds from docs/CONSTITUTION.md
ENGLISH_CAP = 0.15
LAZY_RHYME_CAP = 0.25
CONCRETENESS_MIN = 1.5
CORPUS_OVERLAP_CAP = 0.02

LAZY_ENDINGS = (
    "ama",
    "ima",
    "ao",
    "la",
    "le",
    "lo",
    "li",
    "će",
    "ću",
    "ćemo",
    "ćete",
    "ti",
    "te",
    "še",
    "mo",
    "mo",
    "om",
    "em",
    "u",
    "i",
    "a",
    "o",
    "e",
)

# Expanded from scripts/analyze_lyrics.py
ENGLISH_TOKENS = {
    "the", "and", "for", "you", "are", "not", "but", "with", "your", "from",
    "have", "has", "had", "this", "that", "when", "where", "what", "who",
    "how", "why", "yes", "no", "hey", "ho", "go", "tell", "know",
    "just", "only", "like", "all", "get", "got", "can", "will", "would",
    "show", "some", "everybody", "hands", "up", "we", "ve", "ll", "re",
    "oh", "yeah", "mwah", "kiss", "he", "she", "they", "them",
    "his", "her", "our", "my", "mine", "its", "it", "is", "am", "be", "been",
    "being", "do", "does", "did", "done", "doing", "so", "if", "because", "as",
    "than", "then", "now", "here", "there", "again", "once", "never", "always",
    "every", "two", "three", "four", "first", "last", "next", "other",
    "new", "old", "good", "bad", "big", "small", "little", "right", "left",
    "love", "live", "alive", "high", "drive", "dry", "forever", "toy", "boy",
    "game", "chess", "single", "multiplayer", "artificial", "intelligence",
    "modern", "technology", "generation", "queen", "king", "boom", "bang",
    "bitch", "mode", "switch", "broke", "gangsta", "nasty", "girl", "squad",
    "fashion", "models", "money", "cash", "drill", "trap", "rap", "magic",
    "playback", "choky", "brena", "hotel", "barca",
    "supreme", "bmw", "benz", "bull", "dior", "gucci",
    "fendi", "vuitton", "louis", "paciotti", "martini", "bikini", "popov",
    "amor", "naomi", "dogg", "tarantino", "wannabe", "fashion",
    "opp", "drop", "plug", "kriza", "skrrt", "wooh", "rah",
}


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_text_list(path: Path) -> list[str]:
    entries: list[str] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            entries.append(line.lower())
    return entries


def load_lexicons() -> dict[str, Any]:
    lex_dir = project_root() / "data" / "lexicons"
    calques = load_text_list(lex_dir / "calques.txt")
    cliches = load_text_list(lex_dir / "cliches.txt")
    abstract = load_text_list(lex_dir / "abstract_nouns.txt")
    concrete: set[str] = set()
    with (lex_dir / "concrete_nouns.csv").open("r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            if row:
                concrete.add(row[0].strip().lower())
    dialect_ek: set[str] = set()
    dialect_ij: set[str] = set()
    with (lex_dir / "dialect_pairs.csv").open("r", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            if row and len(row) >= 2:
                dialect_ek.add(row[0].strip().lower())
                dialect_ij.add(row[1].strip().lower())
    return {
        "calques": calques,
        "cliches": cliches,
        "abstract": set(abstract),
        "concrete": concrete,
        "ekavica": dialect_ek,
        "ijekavica": dialect_ij,
    }


def load_corpus_ngrams() -> set[tuple[str, ...]]:
    corpus_dir = project_root() / "data"
    ngrams: set[tuple[str, ...]] = set()
    for name in ("corpus.txt", "corpus_rap.txt"):
        path = corpus_dir / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        tokens = tokenize(text)
        for i in range(len(tokens) - 3):
            ngrams.add(tuple(tokens[i : i + 4]))
    return ngrams


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zšđčćž]+", text.lower())


def line_sections(lyrics: str) -> list[list[str]]:
    """Split lyrics into blocks separated by blank lines; each block is a list of lines."""
    sections: list[list[str]] = []
    current: list[str] = []
    for raw in lyrics.splitlines():
        line = raw.strip()
        if not line:
            if current:
                sections.append(current)
                current = []
        else:
            current.append(line)
    if current:
        sections.append(current)
    return sections


def check_dialect(lyrics: str, lex: dict[str, Any], declared: str | None = None) -> dict[str, Any]:
    tokens = set(tokenize(lyrics))
    ek_hits = tokens & lex["ekavica"]
    ij_hits = tokens & lex["ijekavica"]
    mixed = bool(ek_hits and ij_hits)
    result: dict[str, Any] = {
        "ekavica_hits": sorted(ek_hits),
        "ijekavica_hits": sorted(ij_hits),
        "mixed": mixed,
    }
    if declared:
        declared = declared.lower()
        if declared == "ekavica" and ij_hits:
            result["pass"] = False
            result["reason"] = f"declared ekavica but found ijekavica: {sorted(ij_hits)}"
        elif declared == "ijekavica" and ek_hits:
            result["pass"] = False
            result["reason"] = f"declared ijekavica but found ekavica: {sorted(ek_hits)}"
        else:
            result["pass"] = True
    else:
        result["pass"] = not mixed
        if mixed:
            result["reason"] = "ekavica and ijekavica forms detected"
    return result


def check_english_ratio(lyrics: str) -> dict[str, Any]:
    tokens = tokenize(lyrics)
    if not tokens:
        return {"ratio": 0.0, "pass": True, "english_tokens": []}
    english = [t for t in tokens if t in ENGLISH_TOKENS]
    ratio = len(english) / len(tokens)
    return {
        "ratio": round(ratio, 3),
        "pass": ratio <= ENGLISH_CAP,
        "english_tokens": english,
    }


def last_token(line: str) -> str | None:
    tokens = tokenize(line)
    return tokens[-1] if tokens else None


def is_lazy_rhyme_pair(a: str, b: str) -> bool:
    """Heuristic: two different words rhyme only because they share a grammatical suffix."""
    if a == b:
        return False  # self-rhyme is a different gate
    # Same lemma twin (e.g., rukama / nogama) is lazy
    if len(a) > 3 and len(b) > 3:
        # Check common grammatical endings
        for end in LAZY_ENDINGS:
            if a.endswith(end) and b.endswith(end):
                # They must also have different meaningful roots
                root_a = a[: -len(end)].rstrip("a")
                root_b = b[: -len(end)].rstrip("a")
                if root_a != root_b:
                    return True
    return False


def check_lazy_rhyme(lyrics: str) -> dict[str, Any]:
    sections = line_sections(lyrics)
    pairs: list[tuple[str, str]] = []
    lazy_pairs: list[tuple[str, str]] = []
    for section in sections:
        for i in range(len(section) - 1):
            a = last_token(section[i])
            b = last_token(section[i + 1])
            if a and b:
                pair = (a, b)
                pairs.append(pair)
                if is_lazy_rhyme_pair(a, b):
                    lazy_pairs.append(pair)
    total = len(pairs)
    ratio = len(lazy_pairs) / total if total else 0.0
    return {
        "ratio": round(ratio, 3),
        "pass": ratio <= LAZY_RHYME_CAP,
        "total_pairs": total,
        "lazy_pairs": lazy_pairs,
    }


def check_concreteness(lyrics: str, lex: dict[str, Any]) -> dict[str, Any]:
    sections = line_sections(lyrics)
    section_reports: list[dict[str, Any]] = []
    all_pass = True
    for section in sections:
        text = "\n".join(section)
        tokens = tokenize(text)
        concrete = sum(1 for t in tokens if t in lex["concrete"])
        abstract = sum(1 for t in tokens if t in lex["abstract"])
        density = concrete / abstract if abstract else float("inf")
        passes = density >= CONCRETENESS_MIN or abstract == 0
        if not passes:
            all_pass = False
        section_reports.append({
            "concrete": concrete,
            "abstract": abstract,
            "density": round(density, 3) if abstract else None,
            "pass": passes,
        })
    return {
        "pass": all_pass,
        "sections": section_reports,
    }


def find_banned_phrases(lyrics: str, banned: list[str]) -> list[tuple[str, int]]:
    """Return (banned_phrase, line_number) for each hit."""
    hits: list[tuple[str, int]] = []
    lowered = lyrics.lower()
    for phrase in banned:
        # Use line-level context for reporting
        for idx, line in enumerate(lyrics.splitlines(), start=1):
            if phrase in line.lower():
                hits.append((phrase, idx))
    return hits


def check_banned_calques(lyrics: str, lex: dict[str, Any]) -> dict[str, Any]:
    hits = find_banned_phrases(lyrics, lex["calques"])
    return {"pass": not hits, "hits": hits}


def check_banned_cliches(lyrics: str, lex: dict[str, Any]) -> dict[str, Any]:
    hits = find_banned_phrases(lyrics, lex["cliches"])
    return {"pass": not hits, "hits": hits}


def check_corpus_overlap(lyrics: str, corpus_ngrams: set[tuple[str, ...]]) -> dict[str, Any]:
    tokens = tokenize(lyrics)
    matches: list[list[str]] = []
    for i in range(len(tokens) - 3):
        ngram = tokens[i : i + 4]
        if tuple(ngram) in corpus_ngrams:
            matches.append(ngram)
    total_lines = len([l for l in lyrics.splitlines() if l.strip()])
    # line-level overlap: any line containing a 4-gram match
    matched_lines: set[int] = set()
    # Recompute with line positions for reporting
    line_tokens: list[list[str]] = []
    for idx, line in enumerate(lyrics.splitlines(), start=1):
        if line.strip():
            line_tokens.append((idx, tokenize(line)))
    for idx, toks in line_tokens:
        for i in range(len(toks) - 3):
            if tuple(toks[i : i + 4]) in corpus_ngrams:
                matched_lines.add(idx)
    line_ratio = len(matched_lines) / total_lines if total_lines else 0.0
    return {
        "pass": len(matches) == 0 and line_ratio <= CORPUS_OVERLAP_CAP,
        "ngram_matches": [" ".join(m) for m in matches],
        "matched_lines": sorted(matched_lines),
        "line_ratio": round(line_ratio, 3),
    }


def check_self_rhyme(lyrics: str) -> dict[str, Any]:
    sections = line_sections(lyrics)
    warnings: list[tuple[str, int, int]] = []
    for section in sections:
        for i in range(len(section) - 1):
            line_a = section[i]
            line_b = section[i + 1]
            # Hook/chorus repetition is earned; skip identical lines.
            if line_a.strip().lower() == line_b.strip().lower():
                continue
            a = last_token(line_a)
            b = last_token(line_b)
            if a and b:
                # Same word or same lemma (strip common inflectional suffix)
                if a == b or a[: -3] == b[: -3] and len(a) > 3 and len(b) > 3:
                    warnings.append((a, i + 1, i + 2))
    return {"warnings": warnings, "pass": not warnings}  # soft gate, report only


def check_hook_presence(lyrics: str, hook_lines: list[str] | None = None) -> dict[str, Any]:
    lines = [l.strip() for l in lyrics.splitlines() if l.strip()]
    if not lines:
        return {"pass": False, "reason": "no lyrics"}
    # Auto-detect: repeated lines are candidates
    counts = Counter(lines)
    repeated = [line for line, count in counts.items() if count >= 3]
    if hook_lines:
        # Verify declared hook lines appear at least 3 times
        missing = [h for h in hook_lines if lines.count(h.strip()) < 3]
        return {
            "pass": not missing,
            "declared_hooks": hook_lines,
            "missing": missing,
            "auto_repeated": repeated,
        }
    return {
        "pass": bool(repeated),
        "auto_repeated": repeated,
        "note": "no hook declared; auto-detected repeated lines",
    }


def check_song(
    lyrics: str,
    lex: dict[str, Any] | None = None,
    corpus_ngrams: set[tuple[str, ...]] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if lex is None:
        lex = load_lexicons()
    if corpus_ngrams is None:
        corpus_ngrams = load_corpus_ngrams()
    meta = metadata or {}

    dialect = check_dialect(lyrics, lex, declared=meta.get("dialect"))
    english = check_english_ratio(lyrics)
    lazy = check_lazy_rhyme(lyrics)
    concrete = check_concreteness(lyrics, lex)
    calques = check_banned_calques(lyrics, lex)
    cliches = check_banned_cliches(lyrics, lex)
    overlap = check_corpus_overlap(lyrics, corpus_ngrams)
    self_rhyme = check_self_rhyme(lyrics)
    hook = check_hook_presence(lyrics, meta.get("hook_lines"))

    hard_gates = [
        dialect["pass"],
        english["pass"],
        lazy["pass"],
        concrete["pass"],
        calques["pass"],
        cliches["pass"],
        overlap["pass"],
    ]
    passed = all(hard_gates)

    report: dict[str, Any] = {
        "passed": passed,
        "persona": meta.get("persona"),
        "dialect": meta.get("dialect"),
        "title": meta.get("title"),
        "gates": {
            "dialect": dialect,
            "english_ratio": english,
            "lazy_rhyme": lazy,
            "concreteness": concrete,
            "banned_calques": calques,
            "banned_cliches": cliches,
            "corpus_overlap": overlap,
        },
        "soft_gates": {
            "self_rhyme": self_rhyme,
            "hook_presence": hook,
        },
    }
    return report


def render_report(report: dict[str, Any]) -> str:
    lines: list[str] = []
    status = "✅ PASS" if report["passed"] else "❌ FAIL"
    lines.append(f"Lyrics Popper QC Report — {status}")
    lines.append(f"Title: {report.get('title') or '(untitled)'}")
    lines.append(f"Persona: {report.get('persona') or '(none)'}")
    lines.append("")
    for gate, data in report["gates"].items():
        symbol = "✅" if data["pass"] else "❌"
        lines.append(f"{symbol} {gate}")
        for key, value in data.items():
            if key == "pass":
                continue
            lines.append(f"   {key}: {value}")
    lines.append("")
    lines.append("Soft gates (report only):")
    for gate, data in report["soft_gates"].items():
        symbol = "✅" if data["pass"] else "⚠️"
        lines.append(f"{symbol} {gate}: {data}")
    return "\n".join(lines)


def load_song(path: Path) -> tuple[str, dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".toml":
        data = tomllib.loads(text)
        lyrics = data.get("lyrics", "")
        metadata = {k: v for k, v in data.items() if k != "lyrics"}
        return lyrics, metadata
    if path.suffix == ".json":
        data = json.loads(text)
        return data.get("lyrics", ""), data
    return text, {}


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Lyrics Popper QC slop-detector")
    parser.add_argument("song", type=Path, help="Path to song file (.toml/.json/.txt)")
    parser.add_argument("--output", "-o", type=Path, help="Path to write JSON report")
    parser.add_argument("--json", action="store_true", help="Print JSON report to stdout")
    args = parser.parse_args(argv)

    lyrics, metadata = load_song(args.song)
    report = check_song(lyrics, metadata=metadata)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"Report written to {args.output}")

    if args.json or not args.output:
        print(render_report(report))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
