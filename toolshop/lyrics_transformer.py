"""Lyrics transformation engine — suggests genre-appropriate word replacements
for user-authored lyrics files.

Two transformation directions:
  1. Vocabulary Enhancement — replace low-frequency words with higher-frequency
     same-lemma (auto_safe) or same-UPOS (suggest) alternatives from the target cohort.
  2. Slang Injection — replace generic words with cohort-distinctive slang terms.

Supports three modes: report, auto-fix, interactive.
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from toolshop.lyrics_corrector import CorrectedSection, _SECTION_LABEL_RE
from toolshop.lyricsdb import _ascii_fold, DEFAULT_DB_PATH


# ── Data structures ───────────────────────────────────────────────────


@dataclass
class Suggestion:
    """A single transformation suggestion."""
    line_no: int
    direction: str          # "vocabulary" | "slang"
    category: str           # "vocabulary_same_lemma" | "vocabulary_upos_fallback" | "slang_injection"
    severity: str           # "safe" | "suggest" | "flag"
    original: str
    suggested: str
    reasoning: str
    auto_safe: bool
    context: str = ""


@dataclass
class TransformationReport:
    """Full report of all transformation suggestions."""
    suggestions: List[Suggestion] = field(default_factory=list)
    stats: Dict[str, int] = field(default_factory=dict)
    transformed_text: str = ""
    target_genre: str = ""
    user_metrics: Dict[str, any] = field(default_factory=dict)
    cohort_benchmarks: Dict[str, any] = field(default_factory=dict)

    @property
    def safe_suggestions(self) -> List[Suggestion]:
        return [s for s in self.suggestions if s.auto_safe]

    @property
    def uncertain_suggestions(self) -> List[Suggestion]:
        return [s for s in self.suggestions if not s.auto_safe]


# ── Tokenization helpers ──────────────────────────────────────────────

_WORD_RE = re.compile(r"\b\w+\b")

# UPOS tags that are "content words" eligible for transformation.
_CONTENT_UPOS = frozenset({"NOUN", "VERB", "ADJ", "ADV", "PROPN"})


# ── Main transformer class ────────────────────────────────────────────


class LyricsTransformer:
    """Detect and suggest genre-appropriate word replacements in a lyrics file."""

    def __init__(
        self,
        file_path: str | Path,
        db_path: Optional[str | Path] = None,
        target_genre: str = "drill_trap",
        research_json_path: Optional[str | Path] = None,
    ) -> None:
        self.file_path = Path(file_path)
        self.db_path = Path(db_path) if db_path else None
        self.target_genre = target_genre
        self._research_data: Optional[dict] = None
        self._conn: Optional[sqlite3.Connection] = None

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

    # ── DB connection ──────────────────────────────────────────────

    def _get_conn(self) -> Optional[sqlite3.Connection]:
        if self._conn is not None:
            return self._conn
        if self.db_path and self.db_path.exists():
            self._conn = sqlite3.connect(str(self.db_path))
            return self._conn
        return None

    # ── Text loading and section splitting ─────────────────────────

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

    # ── User metrics ───────────────────────────────────────────────

    def _compute_user_metrics(self, text: str) -> Dict[str, any]:
        lines = [l for l in text.split("\n") if l.strip() and not _SECTION_LABEL_RE.match(l.strip())]
        words = []
        for line in lines:
            words.extend(_WORD_RE.findall(line.lower()))
        unique = set(words)
        ttr = len(unique) / len(words) if words else 0.0
        return {
            "word_count": len(words),
            "unique_words": len(unique),
            "ttr": round(ttr, 4),
            "line_count": len(lines),
        }

    # ── Cohort benchmarks ──────────────────────────────────────────

    def _load_cohort_benchmarks(self) -> Dict[str, any]:
        conn = self._get_conn()
        if conn is None:
            return {}

        result: Dict[str, any] = {}

        # Average TTR and words per line for target cohort (may not exist in minimal DBs)
        try:
            rows = conn.execute(
                """SELECT AVG(sm.ttr), AVG(sm.avg_words_per_line)
                   FROM song_metrics sm
                   JOIN songs s ON sm.song_id = s.id
                   WHERE s.genre_cohort = ?""", (self.target_genre,)
            ).fetchone()
            result["avg_ttr"] = round(rows[0], 4) if rows[0] else 0.0
            result["avg_words_per_line"] = round(rows[1], 2) if rows[1] else 0.0
        except sqlite3.OperationalError:
            result["avg_ttr"] = 0.0
            result["avg_words_per_line"] = 0.0

        # Top slang terms for cohort
        try:
            if self.target_genre == "drill_trap":
                slang_rows = conn.execute(
                    "SELECT form, distinctiveness FROM slang_terms "
                    "WHERE distinctiveness > 1.0 ORDER BY distinctiveness DESC LIMIT 10"
                ).fetchall()
            else:
                slang_rows = conn.execute(
                    "SELECT form, distinctiveness FROM slang_terms "
                    "WHERE distinctiveness < -1.0 ORDER BY distinctiveness ASC LIMIT 10"
                ).fetchall()
            result["top_slang_terms"] = [{"form": r[0], "distinctiveness": round(r[1], 4)} for r in slang_rows]
        except sqlite3.OperationalError:
            result["top_slang_terms"] = []

        return result

    # ── Direction 1: Vocabulary Enhancement ────────────────────────

    def transform_vocabulary(self, sections: List[CorrectedSection]) -> List[Suggestion]:
        conn = self._get_conn()
        if conn is None:
            return []

        suggestions: List[Suggestion] = []

        for section in sections:
            for line_no, text in section.lines:
                stripped = text.strip()
                if not stripped or _SECTION_LABEL_RE.match(stripped):
                    continue

                tokens = _WORD_RE.findall(stripped)
                for token in tokens:
                    token_folded = _ascii_fold(token).lower()
                    if len(token_folded) < 3:
                        continue

                    # Look up word in tokens table
                    word_info = self._lookup_token(conn, token_folded)
                    if word_info is None:
                        continue

                    word_freq, word_lemma, word_upos = word_info

                    # Only flag low-frequency words
                    if word_freq >= 5:
                        continue

                    # Skip non-content words
                    if word_upos not in _CONTENT_UPOS:
                        continue

                    # Try same-lemma first
                    same_lemma = self._find_same_lemma_alternatives(
                        conn, word_lemma, token_folded, self.target_genre
                    )
                    if same_lemma:
                        alt_form, alt_freq = same_lemma[0]
                        suggestions.append(Suggestion(
                            line_no=line_no,
                            direction="vocabulary",
                            category="vocabulary_same_lemma",
                            severity="safe",
                            original=token,
                            suggested=alt_form,
                            reasoning=f"Same lemma '{word_lemma}', higher corpus freq ({alt_freq} vs {word_freq})",
                            auto_safe=True,
                            context=stripped[:60],
                        ))
                        continue

                    # Fall back to same-UPOS
                    upos_alts = self._find_upos_alternatives(
                        conn, word_upos, token_folded, self.target_genre, min_freq=5
                    )
                    if upos_alts:
                        alt_form, alt_freq = upos_alts[0]
                        suggestions.append(Suggestion(
                            line_no=line_no,
                            direction="vocabulary",
                            category="vocabulary_upos_fallback",
                            severity="suggest",
                            original=token,
                            suggested=alt_form,
                            reasoning=f"Same UPOS '{word_upos}', higher corpus freq ({alt_freq} vs {word_freq})",
                            auto_safe=False,
                            context=stripped[:60],
                        ))

        return suggestions

    def _lookup_token(self, conn: sqlite3.Connection, form: str) -> Optional[Tuple[int, str, str]]:
        """Look up a word form in tokens table. Returns (freq, lemma, upos) or None."""
        rows = conn.execute(
            "SELECT form, lemma, upos, COUNT(*) as freq FROM tokens "
            "WHERE form = ? GROUP BY form, lemma, upos ORDER BY freq DESC LIMIT 1",
            (form,)
        ).fetchall()
        if not rows:
            return None
        return (rows[0][3], rows[0][1], rows[0][2])

    def _find_same_lemma_alternatives(
        self, conn: sqlite3.Connection, lemma: str, exclude_form: str, cohort: str
    ) -> List[Tuple[str, int]]:
        """Find higher-frequency forms with the same lemma in the target cohort."""
        rows = conn.execute(
            """SELECT t.form, COUNT(*) as freq
               FROM tokens t
               JOIN lines l ON t.line_id = l.id
               JOIN sections sec ON l.section_id = sec.id
               JOIN songs s ON sec.song_id = s.id
               WHERE t.lemma = ? AND s.genre_cohort = ? AND t.form != ?
               GROUP BY t.form ORDER BY freq DESC LIMIT 3""",
            (lemma, cohort, exclude_form)
        ).fetchall()
        return [(r[0], r[1]) for r in rows if r[1] > 0]

    def _find_upos_alternatives(
        self, conn: sqlite3.Connection, upos: str, exclude_form: str,
        cohort: str, min_freq: int = 5,
    ) -> List[Tuple[str, int]]:
        """Find higher-frequency forms with the same UPOS in the target cohort."""
        rows = conn.execute(
            """SELECT t.form, COUNT(*) as freq
               FROM tokens t
               JOIN lines l ON t.line_id = l.id
               JOIN sections sec ON l.section_id = sec.id
               JOIN songs s ON sec.song_id = s.id
               WHERE t.upos = ? AND s.genre_cohort = ? AND t.form != ?
               GROUP BY t.form HAVING freq >= ? ORDER BY freq DESC LIMIT 3""",
            (upos, cohort, exclude_form, min_freq)
        ).fetchall()
        return [(r[0], r[1]) for r in rows]

    # ── Direction 2: Slang Injection ───────────────────────────────

    def transform_slang(self, sections: List[CorrectedSection]) -> List[Suggestion]:
        conn = self._get_conn()
        if conn is None:
            return []

        # Load cohort-distinctive slang terms
        if self.target_genre == "drill_trap":
            slang_rows = conn.execute(
                "SELECT form, lemma, freq, drill_freq, pop_freq, distinctiveness "
                "FROM slang_terms WHERE distinctiveness > 1.0 ORDER BY distinctiveness DESC"
            ).fetchall()
        else:
            slang_rows = conn.execute(
                "SELECT form, lemma, freq, drill_freq, pop_freq, distinctiveness "
                "FROM slang_terms WHERE distinctiveness < -1.0 ORDER BY distinctiveness ASC"
            ).fetchall()

        if not slang_rows:
            return []

        # Build lookup: form → (lemma, distinctiveness)
        slang_lookup: Dict[str, Tuple[str, float]] = {}
        for row in slang_rows:
            form_folded = _ascii_fold(row[0]).lower()
            slang_lookup[form_folded] = (row[1], row[5])

        suggestions: List[Suggestion] = []

        for section in sections:
            for line_no, text in section.lines:
                stripped = text.strip()
                if not stripped or _SECTION_LABEL_RE.match(stripped):
                    continue

                tokens = _WORD_RE.findall(stripped)
                for token in tokens:
                    token_folded = _ascii_fold(token).lower()
                    if len(token_folded) < 3:
                        continue

                    # Skip if the word is already a distinctive slang term
                    if token_folded in slang_lookup:
                        continue

                    # Look up the token's UPOS
                    word_info = self._lookup_token(conn, token_folded)
                    if word_info is None:
                        continue

                    word_freq, word_lemma, word_upos = word_info

                    # Only suggest for content words
                    if word_upos not in _CONTENT_UPOS:
                        continue

                    # Find a distinctive slang term with same UPOS
                    alt = self._find_slang_for_upos(
                        conn, word_upos, self.target_genre, exclude_form=token_folded
                    )
                    if alt:
                        alt_form, alt_dist = alt
                        suggestions.append(Suggestion(
                            line_no=line_no,
                            direction="slang",
                            category="slang_injection",
                            severity="suggest",
                            original=token,
                            suggested=alt_form,
                            reasoning=f"Cohort-distinctive slang (distinctiveness={alt_dist:.2f}), same UPOS '{word_upos}'",
                            auto_safe=False,
                            context=stripped[:60],
                        ))

        return suggestions

    def _find_slang_for_upos(
        self, conn: sqlite3.Connection, upos: str, cohort: str, exclude_form: str
    ) -> Optional[Tuple[str, float]]:
        """Find a cohort-distinctive slang term with the same UPOS."""
        if cohort == "drill_trap":
            slang_rows = conn.execute(
                "SELECT form, lemma, distinctiveness FROM slang_terms "
                "WHERE distinctiveness > 1.0 ORDER BY distinctiveness DESC"
            ).fetchall()
        else:
            slang_rows = conn.execute(
                "SELECT form, lemma, distinctiveness FROM slang_terms "
                "WHERE distinctiveness < -1.0 ORDER BY distinctiveness ASC"
            ).fetchall()

        for row in slang_rows:
            form, lemma, distinctiveness = row[0], row[1], row[2]
            form_folded = _ascii_fold(form).lower()
            if form_folded == _ascii_fold(exclude_form).lower():
                continue
            # Check if this slang term has the same UPOS in tokens
            upos_match = conn.execute(
                "SELECT upos FROM tokens WHERE form = ? LIMIT 1", (form_folded,)
            ).fetchone()
            if upos_match and upos_match[0] == upos:
                return (form, distinctiveness)

        return None

    # ── Run all transforms ─────────────────────────────────────────

    def run_all_transforms(self, directions: List[str]) -> TransformationReport:
        text = self._load_text()
        sections = self._split_sections(text)

        suggestions: List[Suggestion] = []

        if "vocabulary" in directions:
            suggestions.extend(self.transform_vocabulary(sections))
        if "slang" in directions:
            suggestions.extend(self.transform_slang(sections))

        # Sort by line number
        suggestions.sort(key=lambda s: (s.line_no, s.direction))

        # Build stats
        stats: Dict[str, int] = {}
        for s in suggestions:
            stats[s.category] = stats.get(s.category, 0) + 1
        stats["total"] = len(suggestions)
        stats["auto_safe"] = len([s for s in suggestions if s.auto_safe])

        # User metrics
        user_metrics = self._compute_user_metrics(text)

        # Cohort benchmarks
        cohort_benchmarks = self._load_cohort_benchmarks()

        return TransformationReport(
            suggestions=suggestions,
            stats=stats,
            transformed_text=text,
            target_genre=self.target_genre,
            user_metrics=user_metrics,
            cohort_benchmarks=cohort_benchmarks,
        )

    # ── Apply transforms ───────────────────────────────────────────

    def apply_transforms(self, report: TransformationReport, auto_safe_only: bool = True) -> str:
        """Apply suggestions to the text and return transformed text."""
        text = self._load_text()
        lines = text.split("\n")

        # Group suggestions by line number
        by_line: Dict[int, List[Suggestion]] = {}
        for s in report.suggestions:
            if auto_safe_only and not s.auto_safe:
                continue
            by_line.setdefault(s.line_no, []).append(s)

        for line_no, line_sugs in sorted(by_line.items(), reverse=True):
            idx = line_no - 1
            if idx < 0 or idx >= len(lines):
                continue
            for sug in line_sugs:
                lines[idx] = re.sub(
                    r"\b" + re.escape(sug.original) + r"\b",
                    sug.suggested,
                    lines[idx],
                    flags=re.IGNORECASE,
                )

        transformed = "\n".join(lines)
        report.transformed_text = transformed
        return transformed

    # ── Interactive transform ──────────────────────────────────────

    def interactive_transform(self, report: TransformationReport) -> str:
        """Review each suggestion interactively, return transformed text."""
        text = self._load_text()
        lines = text.split("\n")

        applied: List[Suggestion] = []

        for s in report.suggestions:
            print(f"\n--- Line {s.line_no} [{s.direction}/{s.category}] ---")
            if s.context:
                print(f"  Context: {s.context}")
            print(f"  Original:  {s.original}")
            print(f"  Suggested: {s.suggested}")
            print(f"  Reasoning: {s.reasoning}")

            if s.auto_safe:
                response = input("  Apply? [Y/n/q] ").strip().lower()
            else:
                response = input("  Apply? [y/N/q] ").strip().lower()

            if response == "q":
                break
            if response == "y" or (s.auto_safe and response != "n"):
                applied.append(s)

        for sug in sorted(applied, key=lambda s: -s.line_no):
            idx = sug.line_no - 1
            if idx < 0 or idx >= len(lines):
                continue
            lines[idx] = re.sub(
                r"\b" + re.escape(sug.original) + r"\b",
                sug.suggested,
                lines[idx],
                flags=re.IGNORECASE,
            )

        transformed = "\n".join(lines)
        report.transformed_text = transformed
        return transformed


# ── Report formatting ─────────────────────────────────────────────────


def format_transform_text(report: TransformationReport) -> str:
    """Format a TransformationReport as a human-readable text table."""
    if not report.suggestions:
        return "No suggestions found."

    lines = []
    lines.append(f"Target genre: {report.target_genre}")
    lines.append(f"{'Line':>5}  {'Direction':<12} {'Category':<28} {'Severity':<8} {'Auto':<5} Original → Suggested")
    lines.append("-" * 110)

    for s in report.suggestions:
        auto = "YES" if s.auto_safe else "no"
        orig = s.original[:30] if s.original else ""
        sug = s.suggested[:30] if s.suggested else ""
        lines.append(
            f"{s.line_no:>5}  {s.direction:<12} {s.category:<28} {s.severity:<8} {auto:<5} {orig} → {sug}"
        )

    lines.append("-" * 110)
    lines.append(f"Total: {report.stats.get('total', 0)} suggestions "
                 f"({report.stats.get('auto_safe', 0)} auto-safe, "
                 f"{report.stats.get('total', 0) - report.stats.get('auto_safe', 0)} uncertain)")

    # Category breakdown
    lines.append("\nBy category:")
    for cat, count in sorted(report.stats.items(), key=lambda x: -x[1]):
        if cat not in ("total", "auto_safe"):
            lines.append(f"  {cat:<28} {count}")

    # User metrics
    if report.user_metrics:
        lines.append("\nUser lyrics metrics:")
        for k, v in report.user_metrics.items():
            lines.append(f"  {k:<20} {v}")

    # Cohort benchmarks
    if report.cohort_benchmarks:
        lines.append(f"\nCohort benchmarks ({report.target_genre}):")
        for k, v in report.cohort_benchmarks.items():
            if k != "top_slang_terms":
                lines.append(f"  {k:<20} {v}")
        if report.cohort_benchmarks.get("top_slang_terms"):
            lines.append("  Top slang terms:")
            for term in report.cohort_benchmarks["top_slang_terms"][:5]:
                lines.append(f"    {term['form']:<20} distinctiveness={term['distinctiveness']}")

    return "\n".join(lines)


def format_transform_json(report: TransformationReport) -> str:
    """Format a TransformationReport as JSON."""
    return json.dumps({
        "target_genre": report.target_genre,
        "stats": report.stats,
        "user_metrics": report.user_metrics,
        "cohort_benchmarks": report.cohort_benchmarks,
        "suggestions": [
            {
                "line_no": s.line_no,
                "direction": s.direction,
                "category": s.category,
                "severity": s.severity,
                "original": s.original,
                "suggested": s.suggested,
                "reasoning": s.reasoning,
                "auto_safe": s.auto_safe,
                "context": s.context,
            }
            for s in report.suggestions
        ],
    }, indent=2, ensure_ascii=False)
