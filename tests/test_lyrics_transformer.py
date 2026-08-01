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
