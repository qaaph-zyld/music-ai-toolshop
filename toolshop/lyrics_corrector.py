"""Lyrics correction engine — detects and fixes formatting, section labels,
diacritic inconsistency, phonetic English spellings, and corpus-validated
deviations in user-authored lyrics files.

Supports three modes: report, auto-fix, interactive.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from toolshop.lyricsdb import _ascii_fold, _TYPE_MAP, parse_section_label


# ── Data structures ───────────────────────────────────────────────────

@dataclass
class Issue:
    """A single detected correction issue."""
    line_no: int
    category: str
    severity: str          # "safe", "suggest", "flag"
    original: str
    suggested: str
    auto_safe: bool
    context: str = ""      # surrounding text for display


@dataclass
class CorrectionReport:
    """Full report of all detected issues."""
    issues: List[Issue] = field(default_factory=list)
    stats: Dict[str, int] = field(default_factory=dict)
    corrected_text: str = ""

    @property
    def safe_issues(self) -> List[Issue]:
        return [i for i in self.issues if i.auto_safe]

    @property
    def uncertain_issues(self) -> List[Issue]:
        return [i for i in self.issues if not i.auto_safe]


@dataclass
class CorrectedSection:
    """A section parsed from the lyrics file."""
    label_raw: str
    label_line_no: int
    lines: List[Tuple[int, str]]  # (line_no, text)


# ── Phonetic English map (hardcoded seed) ─────────────────────────────

PHONETIC_ENGLISH_MAP: Dict[str, str] = {
    "mejbi": "maybe",
    "kruelu": "Cruella",
    "fres": "fresh",
    "kul": "cool",
    "smas": "smash",
    "bul": "bull",
    "ful": "full",
    "dadi": "daddy",
    "bejbi": "baby",
    "lejdi": "lady",
    "šou": "show",
    "sou": "show",
    "flek": "flex",
    "bles": "bless",
    "keš": "cash",
    "kes": "cash",
    "brend": "brand",
    "flejv": "flave",
    "stejdž": "stage",
    "stejd": "stage",
    "pardi": "party",
    "brejk": "break",
    "blejm": "blame",
    "šejk": "shake",
    "sejk": "shake",
    "fejs": "face",
    "seks": "sex",
    "dejtm": "date 'em",
    "hej": "hey",
    "ou": "oh",
    "je": "yeah",
    "jeee": "yeah",
    "jaaaa": "yeah",
}


# ── Section label normalizer ──────────────────────────────────────────

_SECTION_LABEL_RE = re.compile(r"^\[(.+?)\]\s*$")

# Performer-role keywords that indicate a performer-first label.
_PERFORMER_KEYWORDS = {"male", "female", "both", "duet", "male calls", "female calls"}

# Canonical type mapping for user-authored labels.
_USER_TYPE_MAP: Dict[str, str] = {
    "build-up": "prerefren",
    "buildup": "prerefren",
    "breakdown": "bridge",
    "call-response": "call_response",
    "call_response": "call_response",
    "calls": "call_response",
    "verse": "strofa",
    "chorus": "refren",
    "hook": "hook",
    "intro": "intro",
    "outro": "outro",
    "bridge": "bridge",
    "pre-chorus": "prerefren",
    "pre-hook": "prerefren",
    "post-chorus": "postrefren",
    "drop": "hook",
}


def _fix_dash_spacing(label_text: str) -> str:
    """Fix missing space after dash in a label string.
    Only fixes ' -X' patterns (space-dash-nonspace), not internal hyphens like 'Build-up'.
    """
    return re.sub(r' -(\S)', r' - \1', label_text)


def _fix_label_line(line: str) -> str:
    """Fix missing space after dash inside a [label] line."""
    return re.sub(r"\[(.+?)\]", lambda m: "[" + _fix_dash_spacing(m.group(1)) + "]", line)


def _normalize_label(label_text: str) -> Optional[str]:
    """Normalize a user-authored section label to canonical format.

    Returns the canonical label string, or None if no normalization needed.
    """
    text = label_text.strip()
    if not text:
        return None

    # Check if already in canonical format (Type N: Performer)
    parsed = parse_section_label(text)
    if parsed.type != "other":
        return None  # Already parseable by existing parser

    # Check for performer-first format: "Male - Verse", "Female", etc.
    text_lower = text.lower()

    # Call-and-response: "Male calls - Female answers"
    if "calls" in text_lower and "answer" in text_lower:
        parts = re.split(r"\s*-\s*", text, 1)
        performers = []
        for part in parts:
            # Extract performer from "Male calls" / "Female answers"
            words = part.strip().split()
            if words:
                performers.append(words[0])
        return f"Call-Response: {' & '.join(performers)}"

    # Performer-first with dash: "Male - Verse" or "Male - Build-up"
    if " - " in text:
        parts = text.split(" - ", 1)
        performer = parts[0].strip()
        type_part = parts[1].strip()
        type_lower = type_lower_fold = _ascii_fold(type_part).lower().strip()
        # Check if the type part is a known type
        canonical_type = _USER_TYPE_MAP.get(type_lower_fold)
        if canonical_type:
            return f"{_canonical_type_label(canonical_type)}: {performer}"
        return None

    # Bare performer: "Female", "Male"
    if text_lower in _PERFORMER_KEYWORDS:
        # Uncertain — suggest Refren but flag for review
        return f"Refren: {text}"

    return None


def _canonical_type_label(type_key: str) -> str:
    """Convert internal type key to display label."""
    labels = {
        "strofa": "Strofa",
        "refren": "Refren",
        "prerefren": "Pred-Refren",
        "postrefren": "Post-Refren",
        "bridge": "Prelaz",
        "hook": "Hook",
        "intro": "Uvod",
        "outro": "Završetak",
        "call_response": "Call-Response",
        "instrumental": "Instrumentalna pauza",
        "interlude": "Interlude",
        "spoken": "Izgovoreno",
    }
    return labels.get(type_key, type_key.capitalize())


# ── Main corrector class ──────────────────────────────────────────────

class LyricsCorrector:
    """Detect and correct issues in a lyrics file."""

    def __init__(
        self,
        file_path: str | Path,
        db_path: Optional[str | Path] = None,
        research_json_path: Optional[str | Path] = None,
    ) -> None:
        self.file_path = Path(file_path)
        self.db_path = Path(db_path) if db_path else None
        self._research_data: Optional[dict] = None
        self._slang_allowlist: Optional[set] = None
        self._diacritic_pairs: Optional[List[dict]] = None
        self._corpus_vocab: Optional[Dict[str, int]] = None

        # Auto-detect research JSON
        if research_json_path is None:
            default_research = (
                self.file_path.parent.parent / "reports" / "corpus_correction_research.json"
            )
            if default_research.exists():
                research_json_path = default_research

        if research_json_path and Path(research_json_path).exists():
            with Path(research_json_path).open("r", encoding="utf-8") as f:
                self._research_data = json.load(f)

    # ── Text loading and section splitting ───────────────────────────

    def _load_text(self) -> str:
        return self.file_path.read_text(encoding="utf-8")

    def _split_sections(self, text: str) -> List[CorrectedSection]:
        lines = text.split("\n")
        sections: List[CorrectedSection] = []
        current_label = ""
        current_label_line = 0
        current_lines: List[Tuple[int, str]] = []

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            match = _SECTION_LABEL_RE.match(stripped)
            if match:
                if current_lines:
                    sections.append(CorrectedSection(
                        label_raw=current_label,
                        label_line_no=current_label_line,
                        lines=current_lines,
                    ))
                current_label = match.group(1).strip()
                current_label_line = i
                current_lines = []
            else:
                current_lines.append((i, line))

        if current_lines:
            sections.append(CorrectedSection(
                label_raw=current_label,
                label_line_no=current_label_line,
                lines=current_lines,
            ))

        return sections

    # ── Check: whitespace ────────────────────────────────────────────

    def check_whitespace(self, lines: List[Tuple[int, str]]) -> List[Issue]:
        issues: List[Issue] = []
        for line_no, text in lines:
            # Double spaces (not at line start)
            if re.search(r"\S  +\S", text):
                fixed = re.sub(r"  +", " ", text)
                issues.append(Issue(
                    line_no=line_no,
                    category="double_space",
                    severity="safe",
                    original=text.rstrip(),
                    suggested=fixed.rstrip(),
                    auto_safe=True,
                    context=text.strip()[:60],
                ))
            # Trailing whitespace
            elif text != text.rstrip():
                issues.append(Issue(
                    line_no=line_no,
                    category="trailing_whitespace",
                    severity="safe",
                    original=repr(text),
                    suggested=repr(text.rstrip()),
                    auto_safe=True,
                    context=text.strip()[:60],
                ))
        return issues

    # ── Check: section labels ────────────────────────────────────────

    def check_section_labels(self, sections: List[CorrectedSection]) -> List[Issue]:
        issues: List[Issue] = []
        for section in sections:
            if not section.label_raw:
                continue

            # Check for missing space after dash: "[Male -Build-up]"
            if re.search(r" -\S", section.label_raw):
                fixed_label = _fix_dash_spacing(section.label_raw)
                issues.append(Issue(
                    line_no=section.label_line_no,
                    category="missing_space_after_dash",
                    severity="safe",
                    original=f"[{section.label_raw}]",
                    suggested=f"[{fixed_label}]",
                    auto_safe=True,
                    context=section.label_raw,
                ))
                # Re-check the fixed label for normalization
                normalized = _normalize_label(fixed_label)
                if normalized:
                    issues.append(Issue(
                        line_no=section.label_line_no,
                        category="section_label_normalize",
                        severity="suggest",
                        original=f"[{fixed_label}]",
                        suggested=f"[{normalized}]",
                        auto_safe=False,
                        context=section.label_raw,
                    ))
                continue

            # Check for normalization need
            normalized = _normalize_label(section.label_raw)
            if normalized and normalized != section.label_raw:
                # Determine if it's a bare performer (uncertain)
                is_bare = section.label_raw.lower().strip() in _PERFORMER_KEYWORDS
                issues.append(Issue(
                    line_no=section.label_line_no,
                    category="section_label_normalize",
                    severity="flag" if is_bare else "suggest",
                    original=f"[{section.label_raw}]",
                    suggested=f"[{normalized}]",
                    auto_safe=False,
                    context=section.label_raw,
                ))

        return issues

    # ── Check: phonetic English ──────────────────────────────────────

    def check_phonetic_english(self, lines: List[Tuple[int, str]]) -> List[Issue]:
        issues: List[Issue] = []
        for line_no, text in lines:
            stripped = text.strip()
            if not stripped or _SECTION_LABEL_RE.match(stripped):
                continue

            # Tokenize while preserving positions
            tokens = re.finditer(r"\S+", stripped)
            for match in tokens:
                token = match.group()
                # Strip punctuation for lookup
                clean = re.sub(r"[^\w']", "", token).lower()
                # Also try ascii-folded version
                clean_folded = _ascii_fold(clean).lower()

                suggestion = PHONETIC_ENGLISH_MAP.get(clean)
                if not suggestion:
                    suggestion = PHONETIC_ENGLISH_MAP.get(clean_folded)

                if suggestion:
                    # Preserve surrounding punctuation
                    issues.append(Issue(
                        line_no=line_no,
                        category="phonetic_english",
                        severity="suggest",
                        original=token,
                        suggested=suggestion,
                        auto_safe=False,
                        context=stripped[:60],
                    ))
        return issues

    # ── Check: diacritic consistency ─────────────────────────────────

    def check_diacritics(self, lines: List[Tuple[int, str]]) -> List[Issue]:
        issues: List[Issue] = []

        # Build word frequency map for this file
        word_forms: Dict[str, Dict[str, int]] = {}  # folded_key -> {form: count}

        for line_no, text in lines:
            stripped = text.strip()
            if not stripped or _SECTION_LABEL_RE.match(stripped):
                continue
            tokens = re.findall(r"\b\w+\b", stripped)
            for token in tokens:
                folded = _ascii_fold(token).lower()
                form_key = token.lower()
                # Only track words that could have diacritic variants
                # (skip very short tokens and pure ASCII words with no diacritic potential)
                if len(folded) < 3:
                    continue
                if folded not in word_forms:
                    word_forms[folded] = {}
                word_forms[folded][form_key] = word_forms[folded].get(form_key, 0) + 1

        # Flag inconsistent forms within the same file
        for folded, forms in word_forms.items():
            if len(forms) < 2:
                continue
            # Find the dominant form
            dominant = max(forms.items(), key=lambda x: x[1])
            for form, count in forms.items():
                if form == dominant[0]:
                    continue
                # Find lines with the minority form
                for line_no, text in lines:
                    stripped = text.strip()
                    if not stripped or _SECTION_LABEL_RE.match(stripped):
                        continue
                    if re.search(r"\b" + re.escape(form) + r"\b", stripped, re.IGNORECASE):
                        # Check corpus for canonical form if available
                        canonical = self._corpus_diacritic_canonical(folded)
                        suggestion = canonical or dominant[0]
                        issues.append(Issue(
                            line_no=line_no,
                            category="diacritic_inconsistency",
                            severity="suggest",
                            original=form,
                            suggested=suggestion,
                            auto_safe=False,
                            context=stripped[:60],
                        ))

        return issues

    def _corpus_diacritic_canonical(self, folded_key: str) -> Optional[str]:
        """Look up corpus-dominant form for a diacritic variant pair."""
        if self._diacritic_pairs is None and self._research_data:
            self._diacritic_pairs = self._research_data.get("diacritic_variant_pairs", [])

        if not self._diacritic_pairs:
            return None

        best: Optional[Tuple[str, int]] = None
        for pair in self._diacritic_pairs:
            if pair.get("normalized_key") == folded_key:
                diacritic_freq = pair.get("diacritic_freq", 0)
                plain_freq = pair.get("plain_freq", 0)
                if diacritic_freq > plain_freq:
                    form = pair.get("diacritic_form", "")
                else:
                    form = pair.get("plain_form", "")
                freq = max(diacritic_freq, plain_freq)
                if best is None or freq > best[1]:
                    best = (form, freq)

        return best[0] if best else None

    # ── Check: corpus frequency validation ───────────────────────────

    def _load_slang_allowlist(self) -> set:
        if self._slang_allowlist is not None:
            return self._slang_allowlist

        self._slang_allowlist = set()
        if self._research_data:
            for term in self._research_data.get("oov_slang_terms", []):
                self._slang_allowlist.add(term.get("form", "").lower())
        return self._slang_allowlist

    def _load_corpus_vocab(self) -> Dict[str, int]:
        if self._corpus_vocab is not None:
            return self._corpus_vocab

        self._corpus_vocab = {}
        if self.db_path and self.db_path.exists():
            conn = sqlite3.connect(str(self.db_path))
            try:
                rows = conn.execute(
                    "SELECT text_norm, COUNT(*) as freq FROM lines "
                    "JOIN sections ON lines.section_id = sections.id "
                    "GROUP BY text_norm"
                ).fetchall()
                # Build word frequency from all lines
                word_freq: Dict[str, int] = {}
                for (text_norm, _) in rows:
                    for word in re.findall(r"\b\w+\b", text_norm.lower()):
                        word_freq[word] = word_freq.get(word, 0) + 1
                self._corpus_vocab = word_freq
            finally:
                conn.close()

        return self._corpus_vocab

    def check_corpus_frequency(self, lines: List[Tuple[int, str]]) -> List[Issue]:
        if not self.db_path or not self.db_path.exists():
            return []

        vocab = self._load_corpus_vocab()
        allowlist = self._load_slang_allowlist()
        issues: List[Issue] = []

        for line_no, text in lines:
            stripped = text.strip()
            if not stripped or _SECTION_LABEL_RE.match(stripped):
                continue

            tokens = re.findall(r"\b\w+\b", stripped)
            for token in tokens:
                token_lower = token.lower()
                token_folded = _ascii_fold(token_lower)

                # Skip if in allowlist
                if token_lower in allowlist or token_folded in allowlist:
                    continue

                # Skip very short tokens
                if len(token_folded) < 3:
                    continue

                # Check frequency in corpus
                freq = vocab.get(token_folded, 0)
                if freq == 0:
                    # Try to find 1-edit-distance alternatives
                    alternatives = self._edit_distance_suggestions(token_folded, vocab)
                    suggestion = ", ".join(alternatives[:3]) if alternatives else "(no match in corpus)"
                    issues.append(Issue(
                        line_no=line_no,
                        category="unknown_word",
                        severity="flag",
                        original=token,
                        suggested=suggestion,
                        auto_safe=False,
                        context=stripped[:60],
                    ))
        return issues

    @staticmethod
    def _edit_distance_suggestions(word: str, vocab: Dict[str, int], max_distance: int = 1) -> List[str]:
        """Find corpus words within edit distance 1, sorted by frequency."""
        candidates: List[Tuple[str, int]] = []
        for candidate, freq in vocab.items():
            if abs(len(candidate) - len(word)) > 1:
                continue
            dist = LyricsCorrector._levenshtein(word, candidate)
            if dist <= max_distance and freq >= 3:
                candidates.append((candidate, freq))
        candidates.sort(key=lambda x: -x[1])
        return [c[0] for c in candidates[:5]]

    @staticmethod
    def _levenshtein(a: str, b: str) -> int:
        if len(a) < len(b):
            a, b = b, a
        if len(b) == 0:
            return len(a)
        prev = list(range(len(b) + 1))
        for i, ca in enumerate(a):
            curr = [i + 1]
            for j, cb in enumerate(b):
                insert = prev[j + 1] + 1
                delete = curr[j] + 1
                substitute = prev[j] + (ca != cb)
                curr.append(min(insert, delete, substitute))
            prev = curr
        return prev[-1]

    # ── Check: filename mismatch ─────────────────────────────────────

    def check_filename(self) -> List[Issue]:
        issues: List[Issue] = []
        filename = self.file_path.stem
        # Try to detect title from first non-label line
        text = self._load_text()
        lines = text.split("\n")
        title_guess = ""
        for line in lines:
            stripped = line.strip()
            if not stripped or _SECTION_LABEL_RE.match(stripped):
                continue
            title_guess = stripped
            break

        if title_guess:
            # Normalize both for comparison
            filename_norm = _ascii_fold(filename.lower()).replace("_", " ")
            title_norm = _ascii_fold(title_guess.lower())
            # Check if they share significant overlap
            if title_norm not in filename_norm and filename_norm not in title_norm:
                # Check word overlap
                fn_words = set(filename_norm.split())
                title_words = set(title_norm.split())
                overlap = fn_words & title_words
                if len(overlap) == 0:
                    issues.append(Issue(
                        line_no=0,
                        category="filename_mismatch",
                        severity="flag",
                        original=filename,
                        suggested=title_guess,
                        auto_safe=False,
                        context=f"Filename: {filename}.txt",
                    ))
        return issues

    # ── Run all checks ───────────────────────────────────────────────

    def run_all_checks(self) -> CorrectionReport:
        text = self._load_text()
        sections = self._split_sections(text)

        # Flatten all content lines (excluding labels)
        all_lines: List[Tuple[int, str]] = []
        for section in sections:
            all_lines.extend(section.lines)

        issues: List[Issue] = []

        # Whitespace (safe)
        issues.extend(self.check_whitespace(all_lines))

        # Section labels (mix of safe and suggest)
        issues.extend(self.check_section_labels(sections))

        # Phonetic English (suggest)
        issues.extend(self.check_phonetic_english(all_lines))

        # Diacritic consistency (suggest)
        issues.extend(self.check_diacritics(all_lines))

        # Corpus frequency (flag, optional)
        issues.extend(self.check_corpus_frequency(all_lines))

        # Filename mismatch (flag)
        issues.extend(self.check_filename())

        # Sort by line number
        issues.sort(key=lambda x: (x.line_no, x.category))

        # Build stats
        stats: Dict[str, int] = {}
        for issue in issues:
            stats[issue.category] = stats.get(issue.category, 0) + 1
        stats["total"] = len(issues)
        stats["auto_safe"] = len([i for i in issues if i.auto_safe])

        report = CorrectionReport(issues=issues, stats=stats, corrected_text=text)
        return report

    # ── Apply fixes ──────────────────────────────────────────────────

    def apply_fixes(self, report: CorrectionReport, auto_safe_only: bool = True) -> str:
        """Apply fixes to the text and return corrected text."""
        text = self._load_text()
        lines = text.split("\n")

        # Group issues by line number
        issues_by_line: Dict[int, List[Issue]] = {}
        for issue in report.issues:
            if auto_safe_only and not issue.auto_safe:
                continue
            issues_by_line.setdefault(issue.line_no, []).append(issue)

        for line_no, line_issues in sorted(issues_by_line.items(), reverse=True):
            if line_no == 0:
                continue  # Filename issues don't modify text
            idx = line_no - 1  # 1-indexed to 0-indexed
            if idx < 0 or idx >= len(lines):
                continue

            for issue in line_issues:
                if issue.category == "double_space":
                    lines[idx] = re.sub(r"  +", " ", lines[idx])
                elif issue.category == "trailing_whitespace":
                    lines[idx] = lines[idx].rstrip()
                elif issue.category == "missing_space_after_dash":
                    lines[idx] = _fix_label_line(lines[idx])

        corrected = "\n".join(lines)
        report.corrected_text = corrected
        return corrected

    # ── Interactive review ───────────────────────────────────────────

    def interactive_review(self, report: CorrectionReport) -> str:
        """Review each issue interactively, return corrected text."""
        text = self._load_text()
        lines = text.split("\n")

        applied_fixes: List[Issue] = []

        for issue in report.issues:
            print(f"\n--- Line {issue.line_no} [{issue.category}] ---")
            if issue.context:
                print(f"  Context: {issue.context}")
            print(f"  Original:  {issue.original}")
            print(f"  Suggested: {issue.suggested}")

            if issue.auto_safe:
                response = input("  Apply? [Y/n/q] ").strip().lower()
            else:
                response = input("  Apply? [y/N/q] ").strip().lower()

            if response == "q":
                break
            if response == "y" or (issue.auto_safe and response != "n"):
                applied_fixes.append(issue)

        # Apply selected fixes
        for issue in sorted(applied_fixes, key=lambda x: -x.line_no):
            idx = issue.line_no - 1
            if idx < 0 or idx >= len(lines):
                continue
            if issue.category == "double_space":
                lines[idx] = re.sub(r"  +", " ", lines[idx])
            elif issue.category == "trailing_whitespace":
                lines[idx] = lines[idx].rstrip()
            elif issue.category == "missing_space_after_dash":
                lines[idx] = _fix_label_line(lines[idx])
            elif issue.category == "phonetic_english":
                lines[idx] = lines[idx].replace(issue.original, issue.suggested)
            elif issue.category == "section_label_normalize":
                lines[idx] = lines[idx].replace(f"[{issue.context}]", issue.suggested)
            elif issue.category == "diacritic_inconsistency":
                lines[idx] = re.sub(
                    r"\b" + re.escape(issue.original) + r"\b",
                    issue.suggested,
                    lines[idx],
                    flags=re.IGNORECASE,
                )

        corrected = "\n".join(lines)
        report.corrected_text = corrected
        return corrected


# ── Report formatting ─────────────────────────────────────────────────

def format_report_text(report: CorrectionReport) -> str:
    """Format a CorrectionReport as a human-readable text table."""
    if not report.issues:
        return "No issues found."

    lines = []
    lines.append(f"{'Line':>5}  {'Category':<28} {'Severity':<8} {'Auto':<5} Original → Suggested")
    lines.append("-" * 100)

    for issue in report.issues:
        auto = "YES" if issue.auto_safe else "no"
        orig = issue.original[:30] if issue.original else ""
        sug = issue.suggested[:30] if issue.suggested else ""
        lines.append(f"{issue.line_no:>5}  {issue.category:<28} {issue.severity:<8} {auto:<5} {orig} → {sug}")

    lines.append("-" * 100)
    lines.append(f"Total: {report.stats.get('total', 0)} issues "
                 f"({report.stats.get('auto_safe', 0)} auto-safe, "
                 f"{report.stats.get('total', 0) - report.stats.get('auto_safe', 0)} uncertain)")

    # Category breakdown
    lines.append("\nBy category:")
    for cat, count in sorted(report.stats.items(), key=lambda x: -x[1]):
        if cat not in ("total", "auto_safe"):
            lines.append(f"  {cat:<28} {count}")

    return "\n".join(lines)


def format_report_json(report: CorrectionReport) -> str:
    """Format a CorrectionReport as JSON."""
    return json.dumps({
        "stats": report.stats,
        "issues": [
            {
                "line_no": i.line_no,
                "category": i.category,
                "severity": i.severity,
                "original": i.original,
                "suggested": i.suggested,
                "auto_safe": i.auto_safe,
                "context": i.context,
            }
            for i in report.issues
        ],
    }, indent=2, ensure_ascii=False)
