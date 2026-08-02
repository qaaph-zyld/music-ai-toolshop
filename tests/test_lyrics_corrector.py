"""Tests for the lyrics correction engine."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from toolshop.lyrics_corrector import (
    CorrectionReport,
    Issue,
    LyricsCorrector,
    PHONETIC_ENGLISH_MAP,
    format_report_json,
    format_report_text,
)


# ── Fixtures ──────────────────────────────────────────────────────────

NISI_SVESNECCA_TEXT = """\
[Male - Verse]
Nisi svesna
Kako bih te mazio
Pitam se
Da li bih se pazio
kao u koridi, osećam se kao bull
Dupe, oči, ma cela si full
Bio normalan, sad postao lud
Noću ne spavam, pred očima mi samo blud

[Female]
Oseti kako te greje ovaj plamen
Kada oko prsta motam kose pramen
bacim ti pogled ti ostaneš ranjen
Ali momak ne znaš kad da staneš
Kažeš  ti si jak, ti sve smeš
look je fresh, a ja sam ti (smash)

[Male calls - Female answers]
Nisi svesna
(Kako bi me mazio)
Pitam se
(Da li bi me pazio)
Misliš da sam cool
(ma ti si momak lud....)

[Male -Build-up]
Tvoja koža se sija
Na suncu ceo dan prava zmija
Zovi me "Daddy"
Ili zovi me "Baby"
Glumiš Kruelu pa
ću kol te mejbi
A jaaaaa.....
[Male - Breakdown]
S tobom bih se smirio,
ti i ja skupa teritoriju da širimo
A vetar piri, duva,
Stiže novo vreme,
Dajem ti sve
(A ti mi daj sebe)

[Female - Chorus]
Oseti kako te greje ovaj plamen
Kada oko prsta motam kose pramen
bacim ti pogled ti ostaneš ranjen
Ali momak ne znaš kad da staneš
Kažeš  ti si jak, ti sve smeš
look je fresh, a ja sam ti (smash)

[Male calls - Female answers]
Nisi svesna
(Kako bi me mazio)
Pitam se
(Da li bi me pazio)
Misliš da sam cool
(ma ti si momak lud....)
"""


@pytest.fixture
def nisi_file(tmp_path: Path) -> Path:
    """Write the Nisi_Svesnecca test file to a temp directory."""
    # Create the directory structure so research JSON auto-detection works
    (tmp_path / "reports").mkdir(exist_ok=True)
    file_path = tmp_path / "Nisi_Svesnecca.txt"
    file_path.write_text(NISI_SVESNECCA_TEXT, encoding="utf-8")
    return file_path


@pytest.fixture
def simple_file(tmp_path: Path) -> Path:
    """A simple file with known issues."""
    (tmp_path / "reports").mkdir(exist_ok=True)
    file_path = tmp_path / "test_lyrics.txt"
    file_path.write_text(
        "[Verse]\n"
        "Ovo  je test  pesma\n"
        "Nisi svesna\n"
        "Nisi svesna\n"
        "mejbi cu da pojdem\n"
        "Kruelu je lik\n",
        encoding="utf-8",
    )
    return file_path


# ── TestWhitespaceCheck ───────────────────────────────────────────────

class TestWhitespaceCheck:
    def test_double_spaces_detected(self, simple_file: Path):
        c = LyricsCorrector(simple_file)
        text = c._load_text()
        sections = c._split_sections(text)
        all_lines = []
        for s in sections:
            all_lines.extend(s.lines)
        issues = c.check_whitespace(all_lines)
        double_space_issues = [i for i in issues if i.category == "double_space"]
        assert len(double_space_issues) >= 1
        assert all(i.auto_safe for i in double_space_issues)

    def test_double_space_fix(self, simple_file: Path):
        c = LyricsCorrector(simple_file)
        report = c.run_all_checks()
        corrected = c.apply_fixes(report, auto_safe_only=True)
        # No double spaces should remain in content lines
        assert "  " not in corrected.split("\n")[1]  # Line 2 was "Ovo  je test  pesma"

    def test_trailing_whitespace_detected(self, tmp_path: Path):
        (tmp_path / "reports").mkdir(exist_ok=True)
        f = tmp_path / "trailing.txt"
        f.write_text("[Verse]\nNisi svesna   \n", encoding="utf-8")
        c = LyricsCorrector(f)
        text = c._load_text()
        sections = c._split_sections(text)
        all_lines = []
        for s in sections:
            all_lines.extend(s.lines)
        issues = c.check_whitespace(all_lines)
        trailing = [i for i in issues if i.category == "trailing_whitespace"]
        assert len(trailing) == 1
        assert trailing[0].auto_safe


# ── TestPhoneticEnglish ───────────────────────────────────────────────

class TestPhoneticEnglish:
    def test_mejbi_detected(self, nisi_file: Path):
        c = LyricsCorrector(nisi_file)
        text = c._load_text()
        sections = c._split_sections(text)
        all_lines = []
        for s in sections:
            all_lines.extend(s.lines)
        issues = c.check_phonetic_english(all_lines)
        phonetic = [i for i in issues if i.category == "phonetic_english"]
        suggestions = {i.original.lower(): i.suggested.lower() for i in phonetic}
        assert "mejbi" in suggestions
        assert suggestions["mejbi"] == "maybe"

    def test_kruelu_detected(self, nisi_file: Path):
        c = LyricsCorrector(nisi_file)
        text = c._load_text()
        sections = c._split_sections(text)
        all_lines = []
        for s in sections:
            all_lines.extend(s.lines)
        issues = c.check_phonetic_english(all_lines)
        phonetic = [i for i in issues if i.category == "phonetic_english"]
        originals = [i.original.lower() for i in phonetic]
        assert "kruelu" in originals

    def test_phonetic_not_auto_safe(self, nisi_file: Path):
        c = LyricsCorrector(nisi_file)
        text = c._load_text()
        sections = c._split_sections(text)
        all_lines = []
        for s in sections:
            all_lines.extend(s.lines)
        issues = c.check_phonetic_english(all_lines)
        for issue in issues:
            assert not issue.auto_safe

    def test_phonetic_map_has_entries(self):
        assert "mejbi" in PHONETIC_ENGLISH_MAP
        assert PHONETIC_ENGLISH_MAP["mejbi"] == "maybe"
        assert "kruelu" in PHONETIC_ENGLISH_MAP
        assert PHONETIC_ENGLISH_MAP["kruelu"] == "Cruella"


# ── TestSectionLabels ─────────────────────────────────────────────────

class TestSectionLabels:
    def test_performer_first_label(self, nisi_file: Path):
        c = LyricsCorrector(nisi_file)
        text = c._load_text()
        sections = c._split_sections(text)
        issues = c.check_section_labels(sections)
        normalize_issues = [i for i in issues if i.category == "section_label_normalize"]
        # [Male - Verse] should be detected
        originals = [i.context for i in normalize_issues]
        assert "Male - Verse" in originals

    def test_build_up_label(self, nisi_file: Path):
        c = LyricsCorrector(nisi_file)
        text = c._load_text()
        sections = c._split_sections(text)
        issues = c.check_section_labels(sections)
        # [Male -Build-up] should trigger missing_space_after_dash
        dash_issues = [i for i in issues if i.category == "missing_space_after_dash"]
        assert len(dash_issues) >= 1
        assert any("Build" in i.context for i in dash_issues)

    def test_call_and_response(self, nisi_file: Path):
        c = LyricsCorrector(nisi_file)
        text = c._load_text()
        sections = c._split_sections(text)
        issues = c.check_section_labels(sections)
        normalize_issues = [i for i in issues if i.category == "section_label_normalize"]
        # [Male calls - Female answers] should be detected
        call_response = [i for i in normalize_issues if "Call-Response" in i.suggested]
        assert len(call_response) >= 1

    def test_bare_performer_flagged(self, nisi_file: Path):
        c = LyricsCorrector(nisi_file)
        text = c._load_text()
        sections = c._split_sections(text)
        issues = c.check_section_labels(sections)
        normalize_issues = [i for i in issues if i.category == "section_label_normalize"]
        # [Female] should be flagged as bare performer
        bare = [i for i in normalize_issues if i.severity == "flag"]
        assert any("Female" in i.context for i in bare)

    def test_breakdown_label(self, nisi_file: Path):
        c = LyricsCorrector(nisi_file)
        text = c._load_text()
        sections = c._split_sections(text)
        issues = c.check_section_labels(sections)
        # [Male - Breakdown] should trigger normalization
        normalize_issues = [i for i in issues if i.category == "section_label_normalize"]
        breakdown = [i for i in normalize_issues if "Breakdown" in i.context or "breakdown" in i.context.lower()]
        assert len(breakdown) >= 1


# ── TestDiacriticConsistency ──────────────────────────────────────────

class TestDiacriticConsistency:
    def test_intra_file_inconsistency(self, tmp_path: Path):
        (tmp_path / "reports").mkdir(exist_ok=True)
        f = tmp_path / "diacritic_test.txt"
        f.write_text(
            "[Verse]\n"
            "osećam se dobro\n"
            "osecam se lose\n",
            encoding="utf-8",
        )
        c = LyricsCorrector(f)
        text = c._load_text()
        sections = c._split_sections(text)
        all_lines = []
        for s in sections:
            all_lines.extend(s.lines)
        issues = c.check_diacritics(all_lines)
        assert len(issues) >= 1
        assert all(i.category == "diacritic_inconsistency" for i in issues)
        assert all(not i.auto_safe for i in issues)

    def test_no_false_positive_consistent(self, tmp_path: Path):
        (tmp_path / "reports").mkdir(exist_ok=True)
        f = tmp_path / "consistent_test.txt"
        f.write_text(
            "[Verse]\n"
            "osećam se dobro\n"
            "osećam se lose\n",
            encoding="utf-8",
        )
        c = LyricsCorrector(f)
        text = c._load_text()
        sections = c._split_sections(text)
        all_lines = []
        for s in sections:
            all_lines.extend(s.lines)
        issues = c.check_diacritics(all_lines)
        assert len(issues) == 0


# ── TestAutoFix ───────────────────────────────────────────────────────

class TestAutoFix:
    def test_auto_fix_only_safe(self, nisi_file: Path):
        c = LyricsCorrector(nisi_file)
        report = c.run_all_checks()
        corrected = c.apply_fixes(report, auto_safe_only=True)
        # Double spaces should be fixed
        assert "Kažeš  ti" not in corrected
        # But phonetic English should NOT be fixed (not auto_safe)
        assert "mejbi" in corrected

    def test_auto_fix_preserves_labels(self, nisi_file: Path):
        c = LyricsCorrector(nisi_file)
        report = c.run_all_checks()
        corrected = c.apply_fixes(report, auto_safe_only=True)
        # Labels should still be present
        assert "[Male - Verse]" in corrected or "[Male" in corrected


# ── TestReportMode ────────────────────────────────────────────────────

class TestReportMode:
    def test_report_has_issues(self, nisi_file: Path):
        c = LyricsCorrector(nisi_file)
        report = c.run_all_checks()
        assert len(report.issues) > 0
        assert report.stats["total"] > 0
        assert report.stats["auto_safe"] > 0

    def test_json_report(self, nisi_file: Path):
        c = LyricsCorrector(nisi_file)
        report = c.run_all_checks()
        json_str = format_report_json(report)
        data = json.loads(json_str)
        assert "issues" in data
        assert "stats" in data
        assert data["stats"]["total"] > 0

    def test_text_report(self, nisi_file: Path):
        c = LyricsCorrector(nisi_file)
        report = c.run_all_checks()
        text = format_report_text(report)
        assert "Line" in text
        assert "Category" in text
        assert "Total:" in text

    def test_empty_report_text(self):
        report = CorrectionReport()
        text = format_report_text(report)
        assert "No issues found" in text


# ── TestCorpusValidation ──────────────────────────────────────────────

class TestCorpusValidation:
    def test_no_db_skips_check(self, nisi_file: Path):
        """Without a DB path, corpus validation should return no issues."""
        c = LyricsCorrector(nisi_file, db_path=None)
        text = c._load_text()
        sections = c._split_sections(text)
        all_lines = []
        for s in sections:
            all_lines.extend(s.lines)
        issues = c.check_corpus_frequency(all_lines)
        assert len(issues) == 0

    def test_slang_allowlist_loaded_from_research(self, tmp_path: Path):
        """Slang allowlist should be loaded from research JSON."""
        (tmp_path / "reports").mkdir(exist_ok=True)
        research = {
            "oov_slang_terms": [
                {"form": "jebo", "lemma": "jebati", "freq": 29},
                {"form": "reperi", "lemma": "reper", "freq": 29},
            ],
            "diacritic_variant_pairs": [],
        }
        research_path = tmp_path / "reports" / "corpus_correction_research.json"
        research_path.write_text(json.dumps(research), encoding="utf-8")

        f = tmp_path / "test.txt"
        f.write_text("[Verse]\njebo reperi\n", encoding="utf-8")
        c = LyricsCorrector(f, research_json_path=research_path)
        allowlist = c._load_slang_allowlist()
        assert "jebo" in allowlist
        assert "reperi" in allowlist

    def test_diacritic_corpus_canonical(self, tmp_path: Path):
        """Corpus-validated diacritic canonical form should be used."""
        (tmp_path / "reports").mkdir(exist_ok=True)
        research = {
            "oov_slang_terms": [],
            "diacritic_variant_pairs": [
                {
                    "diacritic_form": "što",
                    "diacritic_freq": 1619,
                    "plain_form": "sto",
                    "plain_freq": 301,
                    "normalized_key": "sto",
                },
            ],
        }
        research_path = tmp_path / "reports" / "corpus_correction_research.json"
        research_path.write_text(json.dumps(research), encoding="utf-8")

        f = tmp_path / "test.txt"
        f.write_text("[Verse]\nsto je to\nšto je to\n", encoding="utf-8")
        c = LyricsCorrector(f, research_json_path=research_path)
        canonical = c._corpus_diacritic_canonical("sto")
        assert canonical == "što"  # diacritic form is more frequent


# ── TestFilenameMismatch ──────────────────────────────────────────────

class TestFilenameMismatch:
    def test_filename_mismatch_detected(self, tmp_path: Path):
        (tmp_path / "reports").mkdir(exist_ok=True)
        f = tmp_path / "Completely_Different_Title.txt"
        f.write_text("[Verse]\nNisi svesna\nKako bih te mazio\n", encoding="utf-8")
        c = LyricsCorrector(f)
        issues = c.check_filename()
        assert len(issues) == 1
        assert issues[0].category == "filename_mismatch"
        assert not issues[0].auto_safe

    def test_matching_filename_no_issue(self, tmp_path: Path):
        (tmp_path / "reports").mkdir(exist_ok=True)
        f = tmp_path / "Nisi_Svesna.txt"
        f.write_text("[Verse]\nNisi svesna\nKako bih te mazio\n", encoding="utf-8")
        c = LyricsCorrector(f)
        issues = c.check_filename()
        assert len(issues) == 0


# ── TestFullRunOnNisiSvesnecca ────────────────────────────────────────

class TestFullRunOnNisiSvesnecca:
    def test_full_report_has_all_categories(self, nisi_file: Path):
        c = LyricsCorrector(nisi_file)
        report = c.run_all_checks()
        categories = {i.category for i in report.issues}
        # Should have at least these
        assert "double_space" in categories
        assert "section_label_normalize" in categories or "missing_space_after_dash" in categories
        assert "phonetic_english" in categories

    def test_auto_fix_removes_double_spaces(self, nisi_file: Path):
        c = LyricsCorrector(nisi_file)
        report = c.run_all_checks()
        corrected = c.apply_fixes(report, auto_safe_only=True)
        # No double spaces in content lines (not labels)
        for line in corrected.split("\n"):
            if not line.strip().startswith("["):
                assert "  " not in line or line.strip() == ""
