"""Lyrics transformation engine — suggests genre-appropriate word replacements
for user-authored lyrics files.

Four transformation directions:
  1. Vocabulary Enhancement — replace low-frequency words with higher-frequency
     same-lemma (auto_safe) or same-UPOS (suggest) alternatives from the target cohort.
  2. Slang Injection — replace generic words with cohort-distinctive slang terms.
  3. Section Structure Optimization — compare user's section sequence to cohort DB
     patterns and templates, suggest missing/reordered sections (auto_safe).
  4. Flow Pattern Matching — compare user's per-section syllable patterns to cohort
     averages, suggest line splitting/merging (not auto_safe).

Supports three modes: report, auto-fix, interactive.
"""

from __future__ import annotations

import json
import re
import sqlite3
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from toolshop.lyrics_corrector import CorrectedSection, _SECTION_LABEL_RE
from toolshop.lyricsdb import _ascii_fold, DEFAULT_DB_PATH, parse_section_label
from toolshop.rhyme_miner import (
    vowel_skeleton,
    find_rhymes,
    rhyme_factor,
    infer_scheme,
    extract_end_rhyme,
)


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
        # Rhyme metrics
        from toolshop.rhyme_miner import rhyme_factor as _rf, find_rhymes as _find_rhymes, infer_scheme as _infer_scheme
        user_rf = _rf(lines)
        rhyme_groups = _find_rhymes(lines, min_match=2)
        matched: set = set()
        for g in rhyme_groups:
            matched.update(g.line_indices)
        isolated_count = len(lines) - len(matched)
        scheme = _infer_scheme(rhyme_groups, len(lines))

        return {
            "word_count": len(words),
            "unique_words": len(unique),
            "ttr": round(ttr, 4),
            "line_count": len(lines),
            "rhyme_factor": user_rf,
            "rhyme_scheme": scheme,
            "isolated_lines": isolated_count,
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

    # ── Direction 3: Section Structure Optimization ───────────────

    # Template file mapping: cohort → template filename.
    _TEMPLATE_MAP: Dict[str, str] = {
        "drill_trap": "template_drill.md",
        "pop": "template_love_club.md",
    }

    # Canonical section order extracted from templates (by cohort).
    _TEMPLATE_ORDER: Dict[str, List[str]] = {
        "drill_trap": ["intro", "hook", "strofa", "prerefren", "hook", "strofa", "bridge", "hook", "outro"],
        "pop": ["strofa", "prerefren", "refren", "strofa", "bridge", "refren", "outro"],
    }

    # Expected section types per cohort (set form for membership checks).
    _TEMPLATE_TYPES: Dict[str, set] = {
        "drill_trap": {"intro", "hook", "strofa", "prerefren", "bridge", "outro"},
        "pop": {"strofa", "prerefren", "refren", "bridge", "outro"},
    }

    def _parse_user_section_types(self, sections: List[CorrectedSection]) -> List[Tuple[str, int]]:
        """Parse user sections into (canonical_type, label_line_no) pairs."""
        result: List[Tuple[str, int]] = []
        for sec in sections:
            if not sec.label_raw:
                result.append(("unknown", sec.label_line_no))
                continue
            parsed = parse_section_label(sec.label_raw)
            result.append((parsed.type, sec.label_line_no))
        return result

    def _query_cohort_section_sequences(self, conn: sqlite3.Connection) -> List[List[str]]:
        """Query the most common section sequences from the DB for the target cohort."""
        try:
            rows = conn.execute(
                """SELECT s.song_id, s.ordinal, s.type
                   FROM sections s
                   JOIN songs sg ON s.song_id = sg.id
                   WHERE sg.genre_cohort = ?
                   ORDER BY s.song_id, s.ordinal""",
                (self.target_genre,)
            ).fetchall()
        except sqlite3.OperationalError:
            return []

        sequences: Dict[int, List[str]] = {}
        for song_id, ordinal, sec_type in rows:
            sequences.setdefault(song_id, []).append(sec_type)

        # Return sequences sorted by frequency (most common first)
        from collections import Counter
        seq_tuples = [tuple(seq) for seq in sequences.values()]
        counter = Counter(seq_tuples)
        return [list(seq) for seq, _ in counter.most_common(5)]

    def _query_cohort_avg_syllables(self, conn: sqlite3.Connection) -> float:
        """Query the average syllables per line for the target cohort."""
        try:
            row = conn.execute(
                """SELECT AVG(sm.avg_syllables_per_line)
                   FROM song_metrics sm
                   JOIN songs s ON sm.song_id = s.id
                   WHERE s.genre_cohort = ?""",
                (self.target_genre,)
            ).fetchone()
            return round(row[0], 2) if row[0] else 0.0
        except sqlite3.OperationalError:
            return 0.0

    def _query_cohort_section_syllable_avg(
        self, conn: sqlite3.Connection, section_type: str
    ) -> Optional[float]:
        """Query the average syllables per line for a specific section type in the cohort."""
        try:
            row = conn.execute(
                """SELECT AVG(l.syllable_count)
                   FROM lines l
                   JOIN sections s ON l.section_id = s.id
                   JOIN songs sg ON s.song_id = sg.id
                   WHERE sg.genre_cohort = ? AND s.type = ?
                     AND l.syllable_count IS NOT NULL""",
                (self.target_genre, section_type)
            ).fetchone()
            return round(row[0], 2) if row[0] else None
        except sqlite3.OperationalError:
            return None

    def transform_structure(self, sections: List[CorrectedSection]) -> List[Suggestion]:
        """Suggest structural improvements by comparing user's section sequence
        to cohort DB patterns and genre templates.

        All structure suggestions are auto_safe (inserting a section label
        does not change existing lyrics).
        """
        user_types = self._parse_user_section_types(sections)
        user_type_list = [t for t, _ in user_types]

        template_order = self._TEMPLATE_ORDER.get(self.target_genre, [])
        template_types = self._TEMPLATE_TYPES.get(self.target_genre, set())

        # Query DB for cohort section sequences
        conn = self._get_conn()
        cohort_sequences: List[List[str]] = []
        if conn is not None:
            cohort_sequences = self._query_cohort_section_sequences(conn)

        suggestions: List[Suggestion] = []

        # 1. Missing sections (compare to template)
        user_type_set = set(user_type_list)
        for t_type in template_types:
            if t_type not in user_type_set and t_type != "unknown":
                # Find the best insertion point from template order
                insert_label = self._canonical_label(t_type)
                suggestions.append(Suggestion(
                    line_no=0,
                    direction="structure",
                    category="structure_missing_section",
                    severity="safe",
                    original="(missing)",
                    suggested=insert_label,
                    reasoning=f"Section type '{t_type}' is present in {self.target_genre} template but missing from user lyrics",
                    auto_safe=True,
                    context=f"template: {self._TEMPLATE_MAP.get(self.target_genre, '?')}",
                ))

        # 2. Section ordering check
        # Equivalence map: refren and hook serve the same structural role
        _ORDER_EQUIV = {"refren": "hook", "hook": "refren"}
        if template_order and len(user_type_list) >= 2:
            # Build expected order index from template (first occurrence)
            order_idx = {}
            for i, t in enumerate(template_order):
                if t not in order_idx:
                    order_idx[t] = i

            # Check if user sections are in the expected relative order
            last_expected = -1
            for i, (u_type, line_no) in enumerate(user_types):
                # Map equivalent types (refren ↔ hook)
                lookup_type = _ORDER_EQUIV.get(u_type, u_type)
                if lookup_type in order_idx:
                    expected_pos = order_idx[lookup_type]
                elif u_type in order_idx:
                    expected_pos = order_idx[u_type]
                else:
                    continue
                if expected_pos < last_expected:
                    suggestions.append(Suggestion(
                        line_no=line_no,
                        direction="structure",
                        category="structure_ordering",
                        severity="suggest",
                        original=f"{u_type} at position {i+1}",
                        suggested=f"Move after position {last_expected + 1} in template order",
                        reasoning=f"Section '{u_type}' appears before a section that typically precedes it in {self.target_genre} template",
                        auto_safe=True,
                        context=f"template order: {' → '.join(template_order[:6])}...",
                    ))
                last_expected = max(last_expected, expected_pos)

        # 3. Section count comparison
        if cohort_sequences:
            cohort_avg_sections = round(statistics.mean(len(s) for s in cohort_sequences), 1)
            user_section_count = len(user_type_list)
            if user_section_count < cohort_avg_sections - 2:
                suggestions.append(Suggestion(
                    line_no=0,
                    direction="structure",
                    category="structure_count_mismatch",
                    severity="suggest",
                    original=f"{user_section_count} sections",
                    suggested=f"~{cohort_avg_sections:.0f} sections (cohort average)",
                    reasoning=f"User has {user_section_count} sections; cohort average is {cohort_avg_sections}. Consider adding pre-chorus, bridge, or post-chorus.",
                    auto_safe=True,
                    context=f"cohort: {self.target_genre}",
                ))

        return suggestions

    @staticmethod
    def _canonical_label(section_type: str) -> str:
        """Convert a canonical type key to a display label for suggestions."""
        labels = {
            "intro": "[Intro]",
            "hook": "[Hook]",
            "strofa": "[Strofa]",
            "prerefren": "[Pred-Refren]",
            "refren": "[Refren]",
            "bridge": "[Prelaz]",
            "outro": "[Završetak]",
            "postrefren": "[Post-Refren]",
        }
        return labels.get(section_type, f"[{section_type.capitalize()}]")

    # ── Direction 4: Flow Pattern Matching ─────────────────────────

    _VOWEL_GROUPS_RE = re.compile(r"[aeiouAEIOU]+")

    def _estimate_syllables(self, text: str) -> int:
        """Estimate syllable count for a line using vowel-group heuristic."""
        words = _WORD_RE.findall(text)
        total = 0
        for word in words:
            groups = self._VOWEL_GROUPS_RE.findall(word)
            # Each vowel group ≈ 1 syllable; minimum 1 per word
            total += max(len(groups), 1)
        return total

    def transform_flow(self, sections: List[CorrectedSection]) -> List[Suggestion]:
        """Suggest flow improvements by comparing user's per-section syllable
        patterns to cohort averages.

        Flow suggestions are NOT auto_safe (line splitting/merging changes lyrics).
        """
        from toolshop.flow_analyzer import detect_patterns

        conn = self._get_conn()
        cohort_avg_syl = 0.0
        if conn is not None:
            cohort_avg_syl = self._query_cohort_avg_syllables(conn)

        suggestions: List[Suggestion] = []

        for section in sections:
            if not section.lines:
                continue

            # Compute syllable counts for this section's lines
            syl_counts: List[int] = []
            for line_no, text in section.lines:
                stripped = text.strip()
                if not stripped or _SECTION_LABEL_RE.match(stripped):
                    continue
                syl_counts.append(self._estimate_syllables(stripped))

            if len(syl_counts) < 2:
                continue

            user_pattern = detect_patterns(syl_counts)
            user_avg = round(statistics.mean(syl_counts), 2)

            # Parse section type for cohort comparison
            sec_type = "unknown"
            if section.label_raw:
                parsed = parse_section_label(section.label_raw)
                sec_type = parsed.type

            # Compare to cohort section-specific average
            cohort_section_avg = None
            if conn is not None:
                cohort_section_avg = self._query_cohort_section_syllable_avg(conn, sec_type)

            # 1. Syllable count comparison
            comparison_avg = cohort_section_avg if cohort_section_avg else cohort_avg_syl
            if comparison_avg > 0:
                diff = user_avg - comparison_avg
                if abs(diff) >= 1.5:
                    if diff > 0:
                        action = "split"
                        reason = (
                            f"Section '{sec_type}': user avg {user_avg} syllables/line vs "
                            f"cohort avg {comparison_avg}. Consider splitting longer lines."
                        )
                    else:
                        action = "merge"
                        reason = (
                            f"Section '{sec_type}': user avg {user_avg} syllables/line vs "
                            f"cohort avg {comparison_avg}. Consider merging shorter lines."
                        )
                    suggestions.append(Suggestion(
                        line_no=section.lines[0][0] if section.lines else 0,
                        direction="flow",
                        category="flow_syllable_count",
                        severity="suggest",
                        original=f"{user_avg} syllables/line",
                        suggested=f"{comparison_avg} syllables/line ({action})",
                        reasoning=reason,
                        auto_safe=False,
                        context=f"section: {sec_type}, pattern: {user_pattern}",
                    ))

            # Compute cohort CV for this section type (used by both pattern checks)
            cohort_cv: Optional[float] = None
            if conn is not None:
                try:
                    row = conn.execute(
                        """SELECT AVG(l.syllable_count),
                                  AVG(l.syllable_count * l.syllable_count)
                           FROM lines l
                           JOIN sections s ON l.section_id = s.id
                           JOIN songs sg ON s.song_id = sg.id
                           WHERE sg.genre_cohort = ? AND s.type = ?
                             AND l.syllable_count IS NOT NULL""",
                        (self.target_genre, sec_type)
                    ).fetchone()
                    if row[0] and row[1]:
                        mean_val = row[0]
                        mean_sq = row[1]
                        variance = mean_sq - mean_val * mean_val
                        if mean_val > 0:
                            cohort_cv = (variance ** 0.5) / mean_val if variance > 0 else 0.0
                except sqlite3.OperationalError:
                    pass

            # 2. Pattern mismatch: user uniform when cohort tends to be more varied
            if user_pattern == "uniform" and len(syl_counts) >= 3:
                if cohort_cv and cohort_cv > 0.15:
                    suggestions.append(Suggestion(
                        line_no=section.lines[0][0] if section.lines else 0,
                        direction="flow",
                        category="flow_pattern_mismatch",
                        severity="suggest",
                        original=f"{user_pattern}",
                        suggested="alternating or varied",
                        reasoning=(
                            f"Section '{sec_type}': user pattern is '{user_pattern}' but "
                            f"cohort shows variation (CV={cohort_cv:.2f}). "
                            f"Consider alternating line lengths for dynamic flow."
                        ),
                        auto_safe=False,
                        context=f"user avg: {user_avg}, cohort CV: {cohort_cv:.2f}",
                    ))

            # 3. Pattern mismatch: user alternating when cohort is uniform
            if user_pattern == "alternating":
                if cohort_cv is not None and cohort_cv < 0.05:
                    suggestions.append(Suggestion(
                        line_no=section.lines[0][0] if section.lines else 0,
                        direction="flow",
                        category="flow_pattern_mismatch",
                        severity="suggest",
                        original=f"{user_pattern}",
                        suggested="uniform",
                        reasoning=(
                            f"Section '{sec_type}': user pattern is 'alternating' but "
                            f"cohort tends toward uniform flow (CV={cohort_cv:.2f})."
                        ),
                        auto_safe=False,
                        context=f"user avg: {user_avg}",
                    ))

        return suggestions

    # ── Direction 5: Rhyme Scheme Enhancement ──────────────────────

    _COHORT_RF_MEDIANS: Dict[str, float] = {
        "drill_trap": 0.56,
        "pop": 0.74,
    }

    def _flatten_lyric_lines(self, sections: List[CorrectedSection]) -> List[Tuple[int, str]]:
        """Flatten sections into (line_no, text) pairs, skipping section labels and blanks."""
        flat: List[Tuple[int, str]] = []
        for section in sections:
            for line_no, text in section.lines:
                stripped = text.strip()
                if not stripped or _SECTION_LABEL_RE.match(stripped):
                    continue
                flat.append((line_no, stripped))
        return flat

    def _query_cohort_rf_median(self, conn: Optional[sqlite3.Connection]) -> Optional[float]:
        """Query the average rhyme_factor for the target cohort from song_rhyme_metrics."""
        if conn is None:
            return None
        try:
            row = conn.execute(
                """SELECT AVG(srm.rhyme_factor)
                   FROM song_rhyme_metrics srm
                   JOIN songs s ON srm.song_id = s.id
                   WHERE s.genre_cohort = ? AND s.role = 'solo'""",
                (self.target_genre,)
            ).fetchone()
            return round(row[0], 4) if row[0] else None
        except sqlite3.OperationalError:
            return None

    def _find_words_matching_skeleton(
        self, conn: sqlite3.Connection, target_skeleton: str, exclude_word: str, limit: int = 5
    ) -> List[Tuple[str, int]]:
        """Find words from the tokens table whose end vowel skeleton matches the target.

        Returns list of (form, freq) pairs sorted by descending frequency.
        """
        if not target_skeleton:
            return []
        results: List[Tuple[str, int]] = []
        try:
            rows = conn.execute(
                "SELECT form, COUNT(*) as freq FROM tokens GROUP BY form ORDER BY freq DESC LIMIT 500"
            ).fetchall()
        except sqlite3.OperationalError:
            return []

        exclude_folded = _ascii_fold(exclude_word).lower()
        for form, freq in rows:
            form_folded = _ascii_fold(form).lower()
            if form_folded == exclude_folded:
                continue
            word_skel = vowel_skeleton(form_folded)
            if not word_skel:
                continue
            if word_skel.endswith(target_skeleton) and len(word_skel) >= len(target_skeleton):
                results.append((form, freq))
                if len(results) >= limit:
                    break
        return results

    def transform_rhymes(self, sections: List[CorrectedSection]) -> List[Suggestion]:
        """Suggest rhyme scheme improvements by comparing user's rhyme density
        to cohort medians, identifying isolated lines, and proposing word
        replacements to increase multisyllabic rhyme density.

        All rhyme suggestions are auto_safe=False (word replacements are subjective).
        """
        flat_lines = self._flatten_lyric_lines(sections)
        if not flat_lines:
            return []

        line_texts = [text for _, text in flat_lines]
        line_nos = [ln for ln, _ in flat_lines]

        # Compute user rhyme factor
        user_rf = rhyme_factor(line_texts)

        # Find end-rhyme groups
        rhyme_groups = find_rhymes(line_texts, min_match=2)

        # Identify matched line indices (lines in any rhyme group)
        matched_indices: set = set()
        for group in rhyme_groups:
            matched_indices.update(group.line_indices)

        # Identify isolated lines
        isolated: List[Tuple[int, int, str]] = []  # (flat_idx, line_no, text)
        for i, (line_no, text) in enumerate(flat_lines):
            if i not in matched_indices:
                isolated.append((i, line_no, text))

        # Query cohort median RF
        conn = self._get_conn()
        cohort_rf = self._query_cohort_rf_median(conn)
        if cohort_rf is None:
            cohort_rf = self._COHORT_RF_MEDIANS.get(self.target_genre, 0.56)

        suggestions: List[Suggestion] = []

        # 1. Rhyme factor comparison
        if user_rf < cohort_rf:
            suggestions.append(Suggestion(
                line_no=0,
                direction="rhyme",
                category="rhyme_factor_low",
                severity="flag",
                original=f"RF={user_rf:.4f}",
                suggested=f"RF={cohort_rf:.4f} (cohort median)",
                reasoning=(
                    f"User rhyme factor {user_rf:.4f} is below {self.target_genre} cohort "
                    f"median {cohort_rf:.4f}. Increase multisyllabic rhyme density."
                ),
                auto_safe=False,
                context=f"cohort: {self.target_genre}, isolated lines: {len(isolated)}",
            ))

        # 2. For each isolated line, suggest a word replacement matching nearby rhyme skeleton
        for flat_idx, line_no, text in isolated:
            # Find nearest rhyming line
            best_dist = float("inf")
            best_skeleton = ""
            best_group_idx = -1
            for g_idx, group in enumerate(rhyme_groups):
                for g_line_idx in group.line_indices:
                    dist = abs(g_line_idx - flat_idx)
                    if dist < best_dist:
                        best_dist = dist
                        best_skeleton = group.vowel_skeleton
                        best_group_idx = g_idx

            if not best_skeleton:
                continue

            # Get the last word of the isolated line
            words = _WORD_RE.findall(text)
            if not words:
                continue
            last_word = words[-1]

            # Find words matching the target skeleton
            if conn is not None:
                matches = self._find_words_matching_skeleton(
                    conn, best_skeleton, exclude_word=last_word, limit=3
                )
            else:
                matches = []

            if matches:
                alt_form, alt_freq = matches[0]
                suggestions.append(Suggestion(
                    line_no=line_no,
                    direction="rhyme",
                    category="rhyme_isolated_line",
                    severity="suggest",
                    original=last_word,
                    suggested=alt_form,
                    reasoning=(
                        f"Line has no rhyme match. Nearest rhyming group has vowel skeleton "
                        f"'{best_skeleton}'. Replace '{last_word}' with '{alt_form}' "
                        f"(freq={alt_freq}) to match the rhyme pattern."
                    ),
                    auto_safe=False,
                    context=text[:60],
                ))
            else:
                suggestions.append(Suggestion(
                    line_no=line_no,
                    direction="rhyme",
                    category="rhyme_isolated_line",
                    severity="suggest",
                    original=last_word,
                    suggested=f"(word with vowel skeleton '{best_skeleton}')",
                    reasoning=(
                        f"Line has no rhyme match. Nearest rhyming group has vowel skeleton "
                        f"'{best_skeleton}'. Rewrite line ending to match this skeleton."
                    ),
                    auto_safe=False,
                    context=text[:60],
                ))

        # 3. Scheme inference: if AABB, suggest ABAB
        scheme = infer_scheme(rhyme_groups, len(line_texts))
        if scheme and len(scheme) >= 4:
            # Check for AABB pattern (two consecutive pairs of same letters)
            has_aabb = False
            i = 0
            while i < len(scheme) - 3:
                if (scheme[i] == scheme[i + 1] and
                        scheme[i + 2] == scheme[i + 3] and
                        scheme[i] != scheme[i + 2]):
                    has_aabb = True
                    break
                i += 2

            if has_aabb:
                suggestions.append(Suggestion(
                    line_no=0,
                    direction="rhyme",
                    category="rhyme_scheme_upgrade",
                    severity="suggest",
                    original=f"{scheme}",
                    suggested="ABAB with internal rhymes",
                    reasoning=(
                        f"Current scheme is {scheme} (consecutive rhyming pairs). "
                        f"Consider alternating rhymes (ABAB) with internal rhymes "
                        f"for more dynamic flow."
                    ),
                    auto_safe=False,
                    context=f"scheme: {scheme}, RF: {user_rf:.4f}",
                ))

        return suggestions

    # ── Run all transforms ─────────────────────────────────────────

    def run_all_transforms(self, directions: List[str]) -> TransformationReport:
        text = self._load_text()
        sections = self._split_sections(text)

        suggestions: List[Suggestion] = []

        if "vocabulary" in directions:
            suggestions.extend(self.transform_vocabulary(sections))
        if "slang" in directions:
            suggestions.extend(self.transform_slang(sections))
        if "structure" in directions:
            suggestions.extend(self.transform_structure(sections))
        if "flow" in directions:
            suggestions.extend(self.transform_flow(sections))
        if "rhyme" in directions:
            suggestions.extend(self.transform_rhymes(sections))

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

        # Separate structure suggestions (label insertion) from word-replacement
        structure_inserts: List[Suggestion] = []
        by_line: Dict[int, List[Suggestion]] = {}
        for s in report.suggestions:
            if auto_safe_only and not s.auto_safe:
                continue
            if s.direction == "structure" and s.category == "structure_missing_section":
                structure_inserts.append(s)
            else:
                by_line.setdefault(s.line_no, []).append(s)

        # Apply word-replacement suggestions (reverse order to preserve indices)
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

        # Apply structure label insertions (prepend at beginning of file)
        if structure_inserts:
            insert_lines: List[str] = []
            for sug in structure_inserts:
                insert_lines.append(sug.suggested)
                insert_lines.append("")
            lines = insert_lines + lines

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
