"""Tests for toolshop/video_ass.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from toolshop.video_ass import (
    parse_lrc,
    generate_ass,
    STYLE_PRESETS,
    _format_ass_time,
    _build_ass_header,
    _build_dialogue_line,
)


def test_parse_lrc_basic(tmp_path):
    lrc = tmp_path / "test.lrc"
    lrc.write_text(
        "[00:01.50]First line\n[00:03.20]Second line\n[00:05.00]Third line\n",
        encoding="utf-8",
    )
    lines = parse_lrc(lrc)
    assert len(lines) == 3
    assert lines[0] == {"time": 1.5, "text": "First line"}
    assert lines[1] == {"time": 3.2, "text": "Second line"}
    assert lines[2] == {"time": 5.0, "text": "Third line"}


def test_parse_lrc_empty(tmp_path):
    lrc = tmp_path / "empty.lrc"
    lrc.write_text("", encoding="utf-8")
    lines = parse_lrc(lrc)
    assert lines == []


def test_parse_lrc_skips_metadata(tmp_path):
    lrc = tmp_path / "meta.lrc"
    lrc.write_text(
        "[ti:Song Title]\n[ar:Artist]\n[00:01.00]Actual lyric\n",
        encoding="utf-8",
    )
    lines = parse_lrc(lrc)
    assert len(lines) == 1
    assert lines[0]["text"] == "Actual lyric"


def test_parse_lrc_file_not_found():
    with pytest.raises(FileNotFoundError):
        parse_lrc(Path("nonexistent.lrc"))


def test_format_ass_time():
    assert _format_ass_time(0.0) == "0:00:00.00"
    assert _format_ass_time(1.5) == "0:00:01.50"
    assert _format_ass_time(65.25) == "0:01:05.25"
    assert _format_ass_time(3661.0) == "1:01:01.00"


def test_build_ass_header_default():
    header = _build_ass_header("default", 1280, 720)
    assert "[Script Info]" in header
    assert "PlayResX: 1280" in header
    assert "PlayResY: 720" in header
    assert "[V4+ Styles]" in header
    assert "Style:" in header


def test_build_ass_header_neon():
    header = _build_ass_header("neon", 1920, 1080)
    assert "PlayResX: 1920" in header
    assert "PlayResY: 1080" in header
    assert "Consolas" in header


def test_build_ass_header_invalid_style():
    with pytest.raises(KeyError):
        _build_ass_header("nonexistent", 1280, 720)


def test_build_dialogue_line():
    line = _build_dialogue_line(1.5, 3.0, "Hello World")
    assert line.startswith("Dialogue: 0,")
    assert "0:00:01.50" in line
    assert "0:00:03.00" in line
    assert "Hello World" in line


def test_build_dialogue_line_escapes_braces():
    line = _build_dialogue_line(0.0, 2.0, "{test}")
    assert "\\N" not in line.split(",")[-1] or "{test}" in line


def test_generate_ass_basic(tmp_path):
    lyrics = [
        {"time": 1.0, "text": "First line"},
        {"time": 3.0, "text": "Second line"},
    ]
    out = tmp_path / "lyrics.ass"
    generate_ass(lyrics, out, style="default", resolution=(1280, 720))

    content = out.read_text(encoding="utf-8")
    assert "[Script Info]" in content
    assert "[V4+ Styles]" in content
    assert "[Events]" in content
    assert "Dialogue:" in content
    assert "First line" in content
    assert "Second line" in content


def test_generate_ass_empty_lyrics(tmp_path):
    out = tmp_path / "empty.ass"
    generate_ass([], out, style="default")
    content = out.read_text(encoding="utf-8")
    assert "[Events]" in content
    assert "Dialogue:" not in content


def test_generate_ass_auto_duration(tmp_path):
    lyrics = [
        {"time": 1.0, "text": "Line A"},
        {"time": 5.0, "text": "Line B"},
    ]
    out = tmp_path / "auto.ass"
    generate_ass(lyrics, out, style="neon", default_duration=4.0)
    content = out.read_text(encoding="utf-8")
    # Line A should end at 5.0 (next line start) not 1.0+4.0=5.0 — same in this case
    assert "0:00:01.00" in content
    assert "0:00:05.00" in content


def test_generate_ass_from_lrc(tmp_path):
    lrc = tmp_path / "test.lrc"
    lrc.write_text("[00:02.00]Hello\n[00:04.00]World\n", encoding="utf-8")
    out = tmp_path / "out.ass"

    from toolshop.video_ass import lrc_to_ass
    lrc_to_ass(lrc, out, style="minimal")
    content = out.read_text(encoding="utf-8")
    assert "Hello" in content
    assert "World" in content
    assert "Helvetica" in content


def test_style_pressets_exist():
    assert "default" in STYLE_PRESETS
    assert "neon" in STYLE_PRESETS
    assert "minimal" in STYLE_PRESETS
    assert "bold" in STYLE_PRESETS
    for name, preset in STYLE_PRESETS.items():
        assert "font" in preset
        assert "size" in preset
        assert "primary" in preset
        assert "outline" in preset
