import json
from pathlib import Path

import pytest

from generate_crhymetv_catalogue import generate_markdown


def test_generate_markdown_includes_skipped_long_section(tmp_path):
    """Skipped-long tracks must appear in their own catalogue section."""
    md_path = tmp_path / "catalogue.md"
    completed = [
        {
            "artist": "Artist",
            "title": "Song",
            "date": "2024-01-01",
            "bpm": 120.0,
            "key": "C",
            "mode": "major",
            "duration_seconds": 180.0,
            "top_chords": "C; G",
            "top_instruments": "piano",
            "top_effects": "",
            "suno_prompt": "120 bpm C major",
            "recipe_path": str(tmp_path / "recipe.md"),
        }
    ]
    skipped = [
        {
            "source_file": "d:/tracks/long.mp3",
            "date": "2024-02-02",
            "artist": "Doc",
            "title": "Long",
            "duration_seconds": 3600.0,
        }
    ]
    generate_markdown(completed, md_path, skipped_rows=skipped)
    text = md_path.read_text(encoding="utf-8")
    assert "Completed: 1" in text
    assert "Skipped (long): 1" in text
    assert "Skipped (long files)" in text
    assert "long.mp3" in text
    assert "3600.0s" in text
