"""Tests for lyrics_analyzer module."""

import json

import pytest

from toolshop.lyrics_analyzer import (
    analyze_text,
    analyze_file,
    print_report,
    save_report,
)


SAMPLE_LYRICS = """[Verse 1]
Ovo je prva linija
Ovo je druga linija

[Chorus]
Refren refren refren
Ovo je refren"""

SAMPLE_JSON = {
    "title": "Test Song",
    "artist": "Test Artist",
    "url": "https://genius.com/test",
    "language": "sr",
    "raw_lyrics": SAMPLE_LYRICS,
    "clean_lyrics": SAMPLE_LYRICS,
    "sections": [
        {"label": "Verse 1", "content": "Ovo je prva linija\nOvo je druga linija"},
        {"label": "Chorus", "content": "Refren refren refren\nOvo je refren"},
    ],
}


def test_analyze_text_basic():
    """Test basic word and line counts."""
    stats = analyze_text(SAMPLE_LYRICS)

    assert stats["total_words"] > 0
    assert stats["unique_words"] > 0
    assert stats["total_lines"] == 6  # non-empty lines (incl. section labels)


def test_analyze_text_word_counts():
    """Test that word frequency counts are correct."""
    stats = analyze_text("hello hello world test")

    assert stats["total_words"] == 4
    assert stats["unique_words"] == 3
    top = stats["top_20_words"]
    assert top[0] == ("hello", 2)


def test_analyze_text_case_insensitive():
    """Test that tokenization is case-insensitive."""
    stats = analyze_text("Hello HELLO hello")

    assert stats["total_words"] == 3
    assert stats["unique_words"] == 1


def test_analyze_text_line_stats():
    """Test line length statistics."""
    text = "short\nthis is a longer line\nmid"
    stats = analyze_text(text)

    assert stats["total_lines"] == 3
    assert stats["max_line_length"] == len("this is a longer line")
    assert stats["avg_line_length"] > 0


def test_analyze_text_empty():
    """Test analysis of empty string."""
    stats = analyze_text("")

    assert stats["total_words"] == 0
    assert stats["unique_words"] == 0
    assert stats["total_lines"] == 0
    assert stats["avg_line_length"] == 0.0
    assert stats["max_line_length"] == 0


def test_analyze_file(tmp_path):
    """Test loading and analyzing a JSON file."""
    json_path = tmp_path / "test_song.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(SAMPLE_JSON, f, ensure_ascii=False)

    stats = analyze_file(json_path)

    assert stats["total_words"] > 0
    assert stats["source_file"] == str(json_path)


def test_analyze_file_missing_field(tmp_path):
    """Test that missing clean_lyrics raises ValueError."""
    json_path = tmp_path / "bad.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump({"title": "No lyrics"}, f)

    with pytest.raises(ValueError, match="clean_lyrics"):
        analyze_file(json_path)


def test_save_report(tmp_path):
    """Test saving analysis report as JSON."""
    stats = analyze_text(SAMPLE_LYRICS)
    out_path = tmp_path / "subdir" / "report.json"

    save_report(stats, out_path)

    assert out_path.exists()
    with out_path.open("r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["total_words"] == stats["total_words"]


def test_print_report(capsys):
    """Test that print_report produces output."""
    stats = analyze_text("hello world test")
    print_report(stats)
    captured = capsys.readouterr()

    assert "Total words" in captured.out
    assert "hello" in captured.out
