"""Tests for the lyrics transformer engine."""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

import pytest

from toolshop.lyrics_transformer import (
    LyricsTransformer,
    Suggestion,
    TransformationReport,
    format_transform_json,
    format_transform_text,
)


# ── Test fixture text ─────────────────────────────────────────────────

NISI_TEXT = """\
[Male - Verse]
Nisi svesna
Kako bih te mazio
Pitam se
Da li bih se pazio
kao u koridi, osecam se kao bull
Dupe, oci, ma cela si full

[Female]
Oseti kako te greje ovaj plamen
Kada oko prsta motam kose pramen
"""


# ── Mock DB helpers ───────────────────────────────────────────────────


def _make_mock_db(db_path: Path) -> sqlite3.Connection:
    """Create a mock lyrics DB with tokens and slang_terms tables."""
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        CREATE TABLE tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            line_id INTEGER NOT NULL,
            ordinal INTEGER NOT NULL,
            form TEXT,
            lemma TEXT,
            upos TEXT,
            feats TEXT,
            is_oov INTEGER DEFAULT 0,
            source_script TEXT
        );
        CREATE TABLE slang_terms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            form TEXT,
            lemma TEXT,
            freq INTEGER,
            drill_freq REAL,
            pop_freq REAL,
            distinctiveness REAL,
            is_oov INTEGER DEFAULT 0
        );
        CREATE TABLE songs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            genre_cohort TEXT
        );
        CREATE TABLE sections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            song_id INTEGER NOT NULL
        );
        CREATE TABLE lines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            section_id INTEGER NOT NULL
        );
    """)
    return conn


def _insert_token(conn, line_id, ordinal, form, lemma, upos, is_oov=0):
    conn.execute(
        "INSERT INTO tokens (line_id, ordinal, form, lemma, upos, is_oov) VALUES (?, ?, ?, ?, ?, ?)",
        (line_id, ordinal, form, lemma, upos, is_oov),
    )


def _insert_slang(conn, form, lemma, freq, drill_freq, pop_freq, distinctiveness, is_oov=0):
    conn.execute(
        "INSERT INTO slang_terms (form, lemma, freq, drill_freq, pop_freq, distinctiveness, is_oov) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (form, lemma, freq, drill_freq, pop_freq, distinctiveness, is_oov),
    )


@pytest.fixture
def mock_db(tmp_path: Path) -> Path:
    """Create a mock DB file with test data."""
    db_path = tmp_path / "test.db"
    conn = _make_mock_db(db_path)

    # Insert a song + section + line so JOINs work
    conn.execute("INSERT INTO songs (genre_cohort) VALUES ('drill_trap')")
    conn.execute("INSERT INTO songs (genre_cohort) VALUES ('pop')")
    conn.execute("INSERT INTO sections (song_id) VALUES (1)")
    conn.execute("INSERT INTO sections (song_id) VALUES (2)")
    conn.execute("INSERT INTO lines (section_id) VALUES (1)")
    conn.execute("INSERT INTO lines (section_id) VALUES (2)")

    # Tokens: low-freq word "mazio" (freq=2), same lemma "maziti" with higher freq form "mazim" (freq=20)
    _insert_token(conn, 1, 1, "mazio", "maziti", "VERB")
    _insert_token(conn, 1, 2, "mazim", "maziti", "VERB")
    _insert_token(conn, 1, 3, "mazim", "maziti", "VERB")
    # Repeat to reach freq 20 for "mazim"
    for i in range(18):
        _insert_token(conn, 1, 4 + i, "mazim", "maziti", "VERB")

    # Low-freq word "koridi" (freq=1), no same-lemma alternative, but same UPOS "NOUN" with high freq "ulica"
    _insert_token(conn, 1, 22, "koridi", "korid", "NOUN")
    _insert_token(conn, 1, 23, "ulica", "ulica", "NOUN")
    for i in range(15):
        _insert_token(conn, 1, 24 + i, "ulica", "ulica", "NOUN")

    # High-freq word "svesna" (freq=50) — should NOT be flagged
    for i in range(50):
        _insert_token(conn, 1, 40 + i, "svesna", "svesan", "ADJ")

    # "malo" — generic word (freq=30, in slang_terms but low distinctiveness)
    for i in range(30):
        _insert_token(conn, 1, 100 + i, "malo", "malo", "ADV")

    # Slang terms as tokens (needed for UPOS matching in _find_slang_for_upos)
    _insert_token(conn, 1, 130, "brat", "brat", "NOUN")
    _insert_token(conn, 1, 131, "kes", "kes", "NOUN")
    _insert_token(conn, 1, 132, "ljubav", "ljubav", "NOUN")

    # Slang terms: drill-distinctive and pop-distinctive
    _insert_slang(conn, "brat", "brat", 100, 5.0, 0.1, 2.5, 0)
    _insert_slang(conn, "kes", "kes", 80, 4.0, 0.2, 2.0, 1)
    _insert_slang(conn, "ljubav", "ljubav", 200, 0.1, 4.0, -2.0, 0)
    _insert_slang(conn, "malo", "malo", 30, 0.5, 0.5, 0.0, 0)  # below threshold

    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def nisi_file(tmp_path: Path) -> Path:
    f = tmp_path / "Nisi_Svesnecca.txt"
    f.write_text(NISI_TEXT, encoding="utf-8")
    return f


# ── TestVocabularyEnhancement ─────────────────────────────────────────


class TestVocabularyEnhancement:
    def test_low_freq_word_suggested(self, nisi_file, mock_db):
        t = LyricsTransformer(nisi_file, db_path=mock_db, target_genre="drill_trap")
        report = t.run_all_transforms(["vocabulary"])
        assert len(report.suggestions) > 0
        vocab = [s for s in report.suggestions if s.direction == "vocabulary"]
        assert len(vocab) > 0

    def test_high_freq_word_not_flagged(self, nisi_file, mock_db):
        t = LyricsTransformer(nisi_file, db_path=mock_db, target_genre="drill_trap")
        report = t.run_all_transforms(["vocabulary"])
        # "svesna" has freq=50, should not appear as original
        originals = [s.original.lower() for s in report.suggestions]
        assert "svesna" not in originals

    def test_same_lemma_suggestion_is_auto_safe(self, mock_db, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("[Verse]\nmazio\n", encoding="utf-8")
        t = LyricsTransformer(f, db_path=mock_db, target_genre="drill_trap")
        report = t.run_all_transforms(["vocabulary"])
        same_lemma = [s for s in report.suggestions if s.category == "vocabulary_same_lemma"]
        assert len(same_lemma) > 0
        assert all(s.auto_safe for s in same_lemma)

    def test_upos_fallback_not_auto_safe(self, mock_db, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("[Verse]\nkoridi\n", encoding="utf-8")
        t = LyricsTransformer(f, db_path=mock_db, target_genre="drill_trap")
        report = t.run_all_transforms(["vocabulary"])
        upos_fb = [s for s in report.suggestions if s.category == "vocabulary_upos_fallback"]
        assert len(upos_fb) > 0
        assert all(not s.auto_safe for s in upos_fb)

    def test_short_words_skipped(self, mock_db, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("[Verse]\nda li\n", encoding="utf-8")
        t = LyricsTransformer(f, db_path=mock_db, target_genre="drill_trap")
        report = t.run_all_transforms(["vocabulary"])
        originals = [s.original.lower() for s in report.suggestions]
        assert "da" not in originals
        assert "li" not in originals


# ── TestSlangInjection ────────────────────────────────────────────────


class TestSlangInjection:
    def test_generic_word_gets_distinctive_suggestion(self, mock_db, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("[Verse]\nulica mi je\n", encoding="utf-8")
        t = LyricsTransformer(f, db_path=mock_db, target_genre="drill_trap")
        report = t.run_all_transforms(["slang"])
        slang_sugs = [s for s in report.suggestions if s.direction == "slang"]
        assert len(slang_sugs) > 0

    def test_distinctiveness_threshold(self, mock_db, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("[Verse]\nulica\n", encoding="utf-8")
        t = LyricsTransformer(f, db_path=mock_db, target_genre="drill_trap")
        report = t.run_all_transforms(["slang"])
        slang_sugs = [s for s in report.suggestions if s.direction == "slang"]
        assert len(slang_sugs) > 0
        for s in slang_sugs:
            assert "distinctiveness" in s.reasoning.lower()
            match = re.search(r"distinctiveness=([\d.]+)", s.reasoning)
            assert match is not None
            assert abs(float(match.group(1))) > 1.0

    def test_cohort_direction_drill(self, mock_db, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("[Verse]\nljubav mi je\n", encoding="utf-8")
        t = LyricsTransformer(f, db_path=mock_db, target_genre="drill_trap")
        report = t.run_all_transforms(["slang"])
        drill_sugs = [s for s in report.suggestions if s.direction == "slang"]
        # For drill_trap, suggestions should have positive distinctiveness
        for s in drill_sugs:
            assert s.auto_safe is False

    def test_slang_suggestion_has_reasoning(self, mock_db, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("[Verse]\nulica mi je\n", encoding="utf-8")
        t = LyricsTransformer(f, db_path=mock_db, target_genre="drill_trap")
        report = t.run_all_transforms(["slang"])
        slang_sugs = [s for s in report.suggestions if s.direction == "slang"]
        assert len(slang_sugs) > 0
        for s in slang_sugs:
            assert len(s.reasoning) > 0


# ── TestApplyTransforms ───────────────────────────────────────────────


class TestApplyTransforms:
    def test_auto_safe_only_applies_same_lemma(self, mock_db, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("[Verse]\nmazio\nkoridi\n", encoding="utf-8")
        t = LyricsTransformer(f, db_path=mock_db, target_genre="drill_trap")
        report = t.run_all_transforms(["vocabulary"])
        result = t.apply_transforms(report, auto_safe_only=True)
        # "mazio" → "mazim" should be applied (auto_safe=True)
        assert "mazim" in result
        # "koridi" → "ulica" should NOT be applied (auto_safe=False)
        assert "koridi" in result

    def test_apply_replaces_word(self, mock_db, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("[Verse]\nmazio\n", encoding="utf-8")
        t = LyricsTransformer(f, db_path=mock_db, target_genre="drill_trap")
        report = t.run_all_transforms(["vocabulary"])
        result = t.apply_transforms(report, auto_safe_only=True)
        assert "mazim" in result
        assert "mazio" not in result

    def test_apply_preserves_section_labels(self, mock_db, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("[Verse]\nmazio\n", encoding="utf-8")
        t = LyricsTransformer(f, db_path=mock_db, target_genre="drill_trap")
        report = t.run_all_transforms(["vocabulary"])
        result = t.apply_transforms(report, auto_safe_only=True)
        assert "[Verse]" in result


# ── TestReportFormatting ──────────────────────────────────────────────


class TestReportFormatting:
    def test_text_format_has_header(self):
        report = TransformationReport(suggestions=[], stats={"total": 0}, transformed_text="")
        text = format_transform_text(report)
        assert "No suggestions" in text or "Line" in text

    def test_json_format_has_suggestions(self):
        s = Suggestion(
            line_no=1, direction="vocabulary", category="vocabulary_same_lemma",
            severity="safe", original="mazio", suggested="mazim",
            reasoning="same lemma, higher freq", auto_safe=True, context="mazio",
        )
        report = TransformationReport(
            suggestions=[s], stats={"total": 1}, transformed_text="",
            target_genre="drill_trap",
        )
        out = format_transform_json(report)
        data = json.loads(out)
        assert "suggestions" in data
        assert len(data["suggestions"]) == 1
        assert data["suggestions"][0]["original"] == "mazio"

    def test_empty_report_text(self):
        report = TransformationReport(suggestions=[], stats={"total": 0}, transformed_text="")
        text = format_transform_text(report)
        assert "No suggestions" in text


# ── TestNisiSvesneccaFixture ──────────────────────────────────────────


class TestNisiSvesneccaFixture:
    def test_vocabulary_on_nisi(self, nisi_file, mock_db):
        t = LyricsTransformer(nisi_file, db_path=mock_db, target_genre="drill_trap")
        report = t.run_all_transforms(["vocabulary"])
        assert report.stats.get("total", 0) > 0
        assert report.target_genre == "drill_trap"

    def test_full_run_all_directions(self, nisi_file, mock_db):
        t = LyricsTransformer(nisi_file, db_path=mock_db, target_genre="drill_trap")
        report = t.run_all_transforms(["vocabulary", "slang"])
        assert report.stats.get("total", 0) > 0
        directions = {s.direction for s in report.suggestions}
        assert "vocabulary" in directions


# ── Mock DB helpers for structure + flow tests ────────────────────────


def _make_structure_mock_db(db_path: Path) -> sqlite3.Connection:
    """Create a mock DB with song_metrics, sections (type/ordinal), lines (syllable_count)."""
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        CREATE TABLE songs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            genre_cohort TEXT
        );
        CREATE TABLE sections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            song_id INTEGER NOT NULL,
            ordinal INTEGER NOT NULL,
            type TEXT NOT NULL,
            type_number INTEGER,
            label_raw TEXT,
            performers TEXT
        );
        CREATE TABLE lines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            section_id INTEGER NOT NULL,
            ordinal INTEGER NOT NULL,
            text_raw TEXT,
            text_norm TEXT,
            word_count INTEGER,
            syllable_count INTEGER
        );
        CREATE TABLE song_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            song_id INTEGER NOT NULL,
            total_words INTEGER,
            unique_words INTEGER,
            ttr REAL,
            line_count INTEGER,
            avg_words_per_line REAL,
            avg_syllables_per_line REAL,
            hook_repetition_max INTEGER,
            hook_repetition_ratio REAL,
            english_loanword_rate REAL,
            section_type_counts TEXT
        );
        CREATE TABLE tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            line_id INTEGER NOT NULL,
            ordinal INTEGER NOT NULL,
            form TEXT,
            lemma TEXT,
            upos TEXT,
            feats TEXT,
            is_oov INTEGER DEFAULT 0,
            source_script TEXT
        );
        CREATE TABLE slang_terms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            form TEXT,
            lemma TEXT,
            freq INTEGER,
            drill_freq REAL,
            pop_freq REAL,
            distinctiveness REAL,
            is_oov INTEGER DEFAULT 0
        );
    """)
    return conn


def _insert_section(conn, song_id, ordinal, sec_type, type_number=None):
    conn.execute(
        "INSERT INTO sections (song_id, ordinal, type, type_number) VALUES (?, ?, ?, ?)",
        (song_id, ordinal, sec_type, type_number),
    )
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def _insert_line(conn, section_id, ordinal, text, word_count, syllable_count):
    conn.execute(
        "INSERT INTO lines (section_id, ordinal, text_raw, text_norm, word_count, syllable_count) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (section_id, ordinal, text, text.lower(), word_count, syllable_count),
    )


@pytest.fixture
def structure_db(tmp_path: Path) -> Path:
    """Mock DB with cohort section sequences and song_metrics for structure/flow tests."""
    db_path = tmp_path / "structure_test.db"
    conn = _make_structure_mock_db(db_path)

    # Drill cohort songs with typical structure: intro, hook, strofa, prerefren, hook, strofa, bridge, hook, outro
    for i in range(10):
        conn.execute("INSERT INTO songs (genre_cohort) VALUES ('drill_trap')")
        song_id = i + 1
        sid = _insert_section(conn, song_id, 1, "intro")
        _insert_line(conn, sid, 1, "intro line", 2, 4)
        sid = _insert_section(conn, song_id, 2, "hook")
        for j in range(4):
            _insert_line(conn, sid, j + 1, f"hook line {j}", 3, 5)
        sid = _insert_section(conn, song_id, 3, "strofa", 1)
        for j in range(8):
            _insert_line(conn, sid, j + 1, f"verse line {j}", 4, 7)
        sid = _insert_section(conn, song_id, 4, "prerefren")
        for j in range(2):
            _insert_line(conn, sid, j + 1, f"pre line {j}", 3, 5)
        sid = _insert_section(conn, song_id, 5, "hook")
        for j in range(4):
            _insert_line(conn, sid, j + 1, f"hook line {j}", 3, 5)
        sid = _insert_section(conn, song_id, 6, "strofa", 2)
        for j in range(8):
            _insert_line(conn, sid, j + 1, f"verse2 line {j}", 4, 7)
        sid = _insert_section(conn, song_id, 7, "bridge")
        for j in range(2):
            _insert_line(conn, sid, j + 1, f"bridge line {j}", 2, 4)
        sid = _insert_section(conn, song_id, 8, "hook")
        for j in range(4):
            _insert_line(conn, sid, j + 1, f"hook line {j}", 3, 5)
        sid = _insert_section(conn, song_id, 9, "outro")
        _insert_line(conn, sid, 1, "outro line", 2, 3)

        # song_metrics
        section_counts = json.dumps({"intro": 1, "hook": 3, "strofa": 2, "prerefren": 1, "bridge": 1, "outro": 1})
        conn.execute(
            "INSERT INTO song_metrics (song_id, avg_syllables_per_line, section_type_counts) VALUES (?, ?, ?)",
            (song_id, 5.5, section_counts),
        )

    # Pop cohort songs: verse, prerefren, refren, verse, bridge, refren, outro
    for i in range(10):
        conn.execute("INSERT INTO songs (genre_cohort) VALUES ('pop')")
        song_id = i + 11
        sid = _insert_section(conn, song_id, 1, "strofa", 1)
        for j in range(8):
            _insert_line(conn, sid, j + 1, f"verse line {j}", 5, 8)
        sid = _insert_section(conn, song_id, 2, "prerefren")
        for j in range(3):
            _insert_line(conn, sid, j + 1, f"pre line {j}", 4, 6)
        sid = _insert_section(conn, song_id, 3, "refren")
        for j in range(5):
            _insert_line(conn, sid, j + 1, f"chorus line {j}", 4, 6)
        sid = _insert_section(conn, song_id, 4, "strofa", 2)
        for j in range(8):
            _insert_line(conn, sid, j + 1, f"verse2 line {j}", 5, 8)
        sid = _insert_section(conn, song_id, 5, "bridge")
        for j in range(4):
            _insert_line(conn, sid, j + 1, f"bridge line {j}", 3, 5)
        sid = _insert_section(conn, song_id, 6, "refren")
        for j in range(5):
            _insert_line(conn, sid, j + 1, f"chorus line {j}", 4, 6)
        sid = _insert_section(conn, song_id, 7, "outro")
        _insert_line(conn, sid, 1, "outro line", 2, 3)

        section_counts = json.dumps({"strofa": 2, "prerefren": 1, "refren": 2, "bridge": 1, "outro": 1})
        conn.execute(
            "INSERT INTO song_metrics (song_id, avg_syllables_per_line, section_type_counts) VALUES (?, ?, ?)",
            (song_id, 6.5, section_counts),
        )

    conn.commit()
    conn.close()
    return db_path


# ── TestStructureOptimization ─────────────────────────────────────────


class TestStructureOptimization:
    def test_missing_intro_detected(self, structure_db, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("[Strofa 1]\nverse line one\nverse line two\n\n[Refren]\nchorus line\n", encoding="utf-8")
        t = LyricsTransformer(f, db_path=structure_db, target_genre="drill_trap")
        report = t.run_all_transforms(["structure"])
        struct_sugs = [s for s in report.suggestions if s.direction == "structure"]
        categories = [s.category for s in struct_sugs]
        assert any("missing" in c for c in categories)

    def test_missing_pre_chorus_detected(self, structure_db, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("[Strofa 1]\nverse line\n\n[Refren]\nchorus line\n", encoding="utf-8")
        t = LyricsTransformer(f, db_path=structure_db, target_genre="drill_trap")
        report = t.run_all_transforms(["structure"])
        struct_sugs = [s for s in report.suggestions if s.direction == "structure"]
        categories = [s.category for s in struct_sugs]
        assert any("missing" in c for c in categories)

    def test_section_ordering(self, structure_db, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text(
            "[Outro]\noutro line\n\n[Strofa 1]\nverse line\n",
            encoding="utf-8",
        )
        t = LyricsTransformer(f, db_path=structure_db, target_genre="drill_trap")
        report = t.run_all_transforms(["structure"])
        struct_sugs = [s for s in report.suggestions if s.direction == "structure"]
        ordering = [s for s in struct_sugs if "ordering" in s.category]
        assert len(ordering) > 0

    def test_add_section_is_auto_safe(self, structure_db, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("[Strofa 1]\nverse line\n\n[Refren]\nchorus line\n", encoding="utf-8")
        t = LyricsTransformer(f, db_path=structure_db, target_genre="drill_trap")
        report = t.run_all_transforms(["structure"])
        struct_sugs = [s for s in report.suggestions if s.direction == "structure"]
        missing = [s for s in struct_sugs if "missing" in s.category]
        assert len(missing) > 0
        for s in missing:
            assert s.auto_safe is True

    def test_structure_suggestion_has_reasoning(self, structure_db, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("[Strofa 1]\nverse line\n\n[Refren]\nchorus line\n", encoding="utf-8")
        t = LyricsTransformer(f, db_path=structure_db, target_genre="drill_trap")
        report = t.run_all_transforms(["structure"])
        struct_sugs = [s for s in report.suggestions if s.direction == "structure"]
        assert len(struct_sugs) > 0
        for s in struct_sugs:
            assert len(s.reasoning) > 0

    def test_structure_on_nisi_fixture(self, nisi_file, structure_db):
        t = LyricsTransformer(nisi_file, db_path=structure_db, target_genre="drill_trap")
        report = t.run_all_transforms(["structure"])
        struct_sugs = [s for s in report.suggestions if s.direction == "structure"]
        assert len(struct_sugs) > 0


# ── TestFlowPatternMatching ───────────────────────────────────────────


class TestFlowPatternMatching:
    def test_uniform_pattern_detected(self, structure_db, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("[Strofa 1]\na b\na b\na b\n", encoding="utf-8")
        t = LyricsTransformer(f, db_path=structure_db, target_genre="drill_trap")
        report = t.run_all_transforms(["flow"])
        flow_sugs = [s for s in report.suggestions if s.direction == "flow"]
        assert len(flow_sugs) > 0

    def test_alternating_pattern_suggested(self, structure_db, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text(
            "[Strofa 1]\nshort line here\n"
            "a much longer line with more syllables\n"
            "short line here\n"
            "a much longer line with more syllables\n",
            encoding="utf-8",
        )
        t = LyricsTransformer(f, db_path=structure_db, target_genre="drill_trap")
        report = t.run_all_transforms(["flow"])
        flow_sugs = [s for s in report.suggestions if s.direction == "flow"]
        pattern_sugs = [s for s in flow_sugs if "pattern" in s.category]
        assert len(pattern_sugs) > 0

    def test_flow_suggestion_not_auto_safe(self, structure_db, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("[Strofa 1]\na b\na b\n", encoding="utf-8")
        t = LyricsTransformer(f, db_path=structure_db, target_genre="drill_trap")
        report = t.run_all_transforms(["flow"])
        flow_sugs = [s for s in report.suggestions if s.direction == "flow"]
        assert len(flow_sugs) > 0
        for s in flow_sugs:
            assert s.auto_safe is False

    def test_syllable_count_comparison(self, structure_db, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text(
            "[Strofa 1]\nvery short\nvery short\nvery short\nvery short\n",
            encoding="utf-8",
        )
        t = LyricsTransformer(f, db_path=structure_db, target_genre="drill_trap")
        report = t.run_all_transforms(["flow"])
        flow_sugs = [s for s in report.suggestions if s.direction == "flow"]
        syllable_sugs = [s for s in flow_sugs if "syllable" in s.category]
        assert len(syllable_sugs) > 0

    def test_flow_on_nisi_fixture(self, nisi_file, structure_db):
        t = LyricsTransformer(nisi_file, db_path=structure_db, target_genre="drill_trap")
        report = t.run_all_transforms(["flow"])
        assert report.stats.get("total", 0) > 0
        directions = {s.direction for s in report.suggestions}
        assert "flow" in directions


# ── TestStructureAutoFix ──────────────────────────────────────────────


class TestStructureAutoFix:
    def test_auto_fix_inserts_section_label(self, structure_db, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("[Strofa 1]\nverse line\n\n[Refren]\nchorus line\n", encoding="utf-8")
        t = LyricsTransformer(f, db_path=structure_db, target_genre="drill_trap")
        report = t.run_all_transforms(["structure"])
        result = t.apply_transforms(report, auto_safe_only=True)
        missing_sugs = [s for s in report.suggestions if "missing" in s.category and s.auto_safe]
        if missing_sugs:
            assert result != f.read_text(encoding="utf-8")

    def test_auto_fix_preserves_existing_lyrics(self, structure_db, tmp_path):
        f = tmp_path / "test.txt"
        original = "[Strofa 1]\nverse line one\n\n[Refren]\nchorus line here\n"
        f.write_text(original, encoding="utf-8")
        t = LyricsTransformer(f, db_path=structure_db, target_genre="drill_trap")
        report = t.run_all_transforms(["structure"])
        result = t.apply_transforms(report, auto_safe_only=True)
        assert "verse line one" in result
        assert "chorus line here" in result


# ── TestCLIIntegration ────────────────────────────────────────────────


class TestCLIIntegration:
    def test_direction_choices_include_structure_flow(self):
        from toolshop.cli import build_parser
        parser = build_parser()
        # Parse a transform command with --direction structure
        args = parser.parse_args([
            "lyrics", "transform", "dummy.txt",
            "--direction", "structure",
        ])
        assert args.direction == "structure"

        args2 = parser.parse_args([
            "lyrics", "transform", "dummy.txt",
            "--direction", "flow",
        ])
        assert args2.direction == "flow"

    def test_all_directions_runs(self, structure_db, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("[Strofa 1]\nverse line\n\n[Refren]\nchorus line\n", encoding="utf-8")
        t = LyricsTransformer(f, db_path=structure_db, target_genre="drill_trap")
        report = t.run_all_transforms(["structure", "flow"])
        assert report.stats.get("total", 0) > 0
        directions = {s.direction for s in report.suggestions}
        assert "structure" in directions or "flow" in directions


# ── Mock DB helpers for rhyme tests ───────────────────────────────────


def _make_rhyme_mock_db(db_path: Path) -> sqlite3.Connection:
    """Create a mock DB with song_rhyme_metrics, tokens, songs for rhyme tests."""
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        CREATE TABLE songs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            genre_cohort TEXT,
            role TEXT
        );
        CREATE TABLE sections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            song_id INTEGER NOT NULL,
            ordinal INTEGER NOT NULL,
            type TEXT NOT NULL,
            type_number INTEGER,
            label_raw TEXT,
            performers TEXT
        );
        CREATE TABLE lines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            section_id INTEGER NOT NULL,
            ordinal INTEGER NOT NULL,
            text_raw TEXT,
            text_norm TEXT,
            word_count INTEGER,
            syllable_count INTEGER
        );
        CREATE TABLE tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            line_id INTEGER NOT NULL,
            ordinal INTEGER NOT NULL,
            form TEXT,
            lemma TEXT,
            upos TEXT,
            feats TEXT,
            is_oov INTEGER DEFAULT 0,
            source_script TEXT
        );
        CREATE TABLE song_rhyme_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            song_id INTEGER NOT NULL,
            rhyme_factor REAL,
            pct_multis REAL,
            internal_rhyme_rate REAL,
            dominant_scheme TEXT,
            top_vowel_pairs TEXT
        );
        CREATE TABLE slang_terms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            form TEXT,
            lemma TEXT,
            freq INTEGER,
            drill_freq REAL,
            pop_freq REAL,
            distinctiveness REAL,
            is_oov INTEGER DEFAULT 0
        );
        CREATE TABLE song_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            song_id INTEGER NOT NULL,
            total_words INTEGER,
            unique_words INTEGER,
            ttr REAL,
            line_count INTEGER,
            avg_words_per_line REAL,
            avg_syllables_per_line REAL,
            hook_repetition_max INTEGER,
            hook_repetition_ratio REAL,
            english_loanword_rate REAL,
            section_type_counts TEXT
        );
    """)
    return conn


@pytest.fixture
def rhyme_db(tmp_path: Path) -> Path:
    """Mock DB with song_rhyme_metrics and tokens for rhyme enhancement tests."""
    db_path = tmp_path / "rhyme_test.db"
    conn = _make_rhyme_mock_db(db_path)

    # Drill cohort songs with RF around 0.56
    for i in range(5):
        conn.execute("INSERT INTO songs (genre_cohort, role) VALUES ('drill_trap', 'solo')")
        conn.execute(
            "INSERT INTO song_rhyme_metrics (song_id, rhyme_factor, pct_multis, internal_rhyme_rate, dominant_scheme) VALUES (?, ?, ?, ?, ?)",
            (i + 1, 0.50 + i * 0.02, 0.45, 0.30, "AABB"),
        )

    # Pop cohort songs with RF around 0.74
    for i in range(5):
        conn.execute("INSERT INTO songs (genre_cohort, role) VALUES ('pop', 'solo')")
        conn.execute(
            "INSERT INTO song_rhyme_metrics (song_id, rhyme_factor, pct_multis, internal_rhyme_rate, dominant_scheme) VALUES (?, ?, ?, ?, ?)",
            (i + 6, 0.70 + i * 0.02, 0.55, 0.40, "ABAB"),
        )

    # Insert a section + line so tokens can reference line_ids
    conn.execute("INSERT INTO sections (song_id, ordinal, type) VALUES (1, 1, 'strofa')")
    conn.execute("INSERT INTO lines (section_id, ordinal, text_raw, text_norm) VALUES (1, 1, 'test', 'test')")

    # Tokens with known vowel skeletons for word suggestion matching
    # "plamen" → "ae", "pramen" → "ae", "stanes" → "ae", "ranjen" → "ae"
    # "sama" → "aa" (different, should not match "ae" target)
    for i, (word, lemma, upos) in enumerate([
        ("plamen", "plamen", "NOUN"),
        ("pramen", "pramen", "NOUN"),
        ("stanes", "stanes", "VERB"),
        ("ranjen", "ranjen", "ADJ"),
        ("sama", "sama", "ADJ"),
    ]):
        for j in range(10):
            conn.execute(
                "INSERT INTO tokens (line_id, ordinal, form, lemma, upos) VALUES (?, ?, ?, ?, ?)",
                (1, i * 10 + j + 1, word, lemma, upos),
            )

    conn.commit()
    conn.close()
    return db_path


# ── TestRhymeEnhancement ──────────────────────────────────────────────


RHYME_AABB_TEXT = """\
[Verse]
Oseti kako te greje ovaj plamen
Kada oko prsta motam kose pramen
Nisi svesna kako bih te mazio
Da li bih se ja tako pazio
"""

RHYME_AAB_TEXT = """\
[Verse]
Oseti kako te greje ovaj plamen
Kada oko prsta motam kose pramen
Pitam se da li si ti sama
"""

RHYME_ABAB_TEXT = """\
[Verse]
Oseti kako te greje ovaj plamen
Nisi svesna kako bih te mazio
Kada oko prsta motam kose pramen
Da li bih se ja tako pazio
"""


class TestRhymeEnhancement:
    def test_rhyme_factor_computed(self, rhyme_db, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text(RHYME_AAB_TEXT, encoding="utf-8")
        t = LyricsTransformer(f, db_path=rhyme_db, target_genre="drill_trap")
        report = t.run_all_transforms(["rhyme"])
        assert "rhyme_factor" in report.user_metrics
        assert report.user_metrics["rhyme_factor"] > 0.0

    def test_cohort_median_comparison(self, rhyme_db, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text(RHYME_AAB_TEXT, encoding="utf-8")
        t = LyricsTransformer(f, db_path=rhyme_db, target_genre="drill_trap")
        report = t.run_all_transforms(["rhyme"])
        rf_sugs = [s for s in report.suggestions if s.category == "rhyme_factor_low"]
        assert len(rf_sugs) > 0

    def test_isolated_line_detection(self, rhyme_db, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text(RHYME_AAB_TEXT, encoding="utf-8")
        t = LyricsTransformer(f, db_path=rhyme_db, target_genre="drill_trap")
        report = t.run_all_transforms(["rhyme"])
        isolated = [s for s in report.suggestions if s.category == "rhyme_isolated_line"]
        assert len(isolated) > 0

    def test_rhyme_target_suggestion(self, rhyme_db, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text(RHYME_AAB_TEXT, encoding="utf-8")
        t = LyricsTransformer(f, db_path=rhyme_db, target_genre="drill_trap")
        report = t.run_all_transforms(["rhyme"])
        isolated = [s for s in report.suggestions if s.category == "rhyme_isolated_line"]
        assert len(isolated) > 0
        for s in isolated:
            assert "skeleton" in s.reasoning.lower() or "rhyme" in s.reasoning.lower()

    def test_scheme_inference_aabb(self, rhyme_db, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text(RHYME_AABB_TEXT, encoding="utf-8")
        t = LyricsTransformer(f, db_path=rhyme_db, target_genre="drill_trap")
        report = t.run_all_transforms(["rhyme"])
        scheme_sugs = [s for s in report.suggestions if s.category == "rhyme_scheme_upgrade"]
        assert len(scheme_sugs) > 0
        assert "ABAB" in scheme_sugs[0].suggested

    def test_scheme_inference_abab(self, rhyme_db, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text(RHYME_ABAB_TEXT, encoding="utf-8")
        t = LyricsTransformer(f, db_path=rhyme_db, target_genre="drill_trap")
        report = t.run_all_transforms(["rhyme"])
        scheme_sugs = [s for s in report.suggestions if s.category == "rhyme_scheme_upgrade"]
        assert len(scheme_sugs) == 0

    def test_all_rhyme_suggestions_not_auto_safe(self, rhyme_db, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text(RHYME_AAB_TEXT, encoding="utf-8")
        t = LyricsTransformer(f, db_path=rhyme_db, target_genre="drill_trap")
        report = t.run_all_transforms(["rhyme"])
        rhyme_sugs = [s for s in report.suggestions if s.direction == "rhyme"]
        assert len(rhyme_sugs) > 0
        for s in rhyme_sugs:
            assert s.auto_safe is False

    def test_rhyme_direction_in_run_all(self, rhyme_db, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text(RHYME_AAB_TEXT, encoding="utf-8")
        t = LyricsTransformer(f, db_path=rhyme_db, target_genre="drill_trap")
        report = t.run_all_transforms(["rhyme"])
        directions = {s.direction for s in report.suggestions}
        assert "rhyme" in directions

    def test_rhyme_on_nisi_fixture(self, nisi_file, rhyme_db):
        t = LyricsTransformer(nisi_file, db_path=rhyme_db, target_genre="drill_trap")
        report = t.run_all_transforms(["rhyme"])
        assert "rhyme_factor" in report.user_metrics
        assert report.user_metrics["rhyme_factor"] >= 0.0

    def test_cli_direction_includes_rhyme(self):
        from toolshop.cli import build_parser
        parser = build_parser()
        args = parser.parse_args([
            "lyrics", "transform", "dummy.txt",
            "--direction", "rhyme",
        ])
        assert args.direction == "rhyme"
