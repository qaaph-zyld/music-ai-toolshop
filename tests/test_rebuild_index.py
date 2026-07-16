"""Tests for rebuild_index() in Genious_lyrics_extractor.extract_artists."""

import json
import sys
from pathlib import Path

import pytest

# Ensure the extractor directory is importable
_extractor_dir = Path(__file__).resolve().parent.parent / "Genious_lyrics_extractor"
if str(_extractor_dir) not in sys.path:
    sys.path.insert(0, str(_extractor_dir))

from extract_artists import rebuild_index, _norm_key, slugify


def _write_song_json(
    cat_dir: Path,
    title: str,
    artist: str,
    featured: list | None = None,
    song_id=None,
) -> Path:
    """Helper: write a minimal song JSON + TXT in a category subfolder."""
    cat_dir.mkdir(parents=True, exist_ok=True)
    base = f"{slugify(artist)}-{slugify(title)}"
    json_path = cat_dir / f"{base}.json"
    txt_path = cat_dir / f"{base}.txt"
    data = {
        "title": title,
        "artist": artist,
        "url": "https://genius.com/test",
        "language": None,
        "raw_lyrics": "test lyrics",
        "clean_lyrics": "test lyrics",
        "sections": [],
        "artist_config": cat_dir.name,
        "primary_artist": artist,
        "featured_artists": featured or [],
        "genius_song_id": song_id,
    }
    json_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    txt_path.write_text("test lyrics", encoding="utf-8")
    return json_path


def test_rebuild_basic(tmp_path):
    """Rebuild produces index with correct entries from disk files."""
    out = tmp_path / "lyrics"
    _write_song_json(out / "buba-solo", "Song A", "Buba Corelli")
    _write_song_json(out / "jala-solo", "Song B", "Jala Brat")

    stats = rebuild_index(out)

    assert stats["unique_songs"] == 2
    assert stats["skipped_dup"] == 0
    assert stats["buba-solo"] == 1
    assert stats["jala-solo"] == 1

    index = json.loads((out / "_index.json").read_text(encoding="utf-8"))
    assert len(index) == 2
    assert all("file" in e for e in index)
    assert all(e["json_path"] for e in index)
    assert all(e["txt_path"] for e in index)


def test_rebuild_dedup_same_title_artist(tmp_path):
    """Duplicate (title, primary_artist) across categories collapses to one entry."""
    out = tmp_path / "lyrics"
    _write_song_json(out / "jala-buba-coby-trio", "O.D.D.D.", "Jala Brat")
    # Same song appears in another category folder (as happened with the trio bug)
    _write_song_json(out / "jala-solo", "O.D.D.D.", "Jala Brat")

    stats = rebuild_index(out)

    assert stats["unique_songs"] == 1
    assert stats["skipped_dup"] == 1

    index = json.loads((out / "_index.json").read_text(encoding="utf-8"))
    assert len(index) == 1
    assert index[0]["title"] == "O.D.D.D."


def test_rebuild_populates_file_field(tmp_path):
    """Every index entry has a 'file' field pointing to the JSON path."""
    out = tmp_path / "lyrics"
    jp = _write_song_json(out / "coby-solo", "Test Song", "Coby")

    stats = rebuild_index(out)

    index = json.loads((out / "_index.json").read_text(encoding="utf-8"))
    assert len(index) == 1
    assert index[0]["file"] == str(jp)
    assert index[0]["json_path"] == str(jp)


def test_rebuild_writes_summary(tmp_path):
    """Rebuild writes _summary.md with reconciliation info."""
    out = tmp_path / "lyrics"
    _write_song_json(out / "buba-solo", "Song A", "Buba Corelli")

    rebuild_index(out)

    summary = (out / "_summary.md").read_text(encoding="utf-8")
    assert "rebuilt from disk" in summary
    assert "Unique songs" in summary
    assert "File Reconciliation" in summary


def test_rebuild_writes_dedup_log(tmp_path):
    """Rebuild writes _dedup_log.json."""
    out = tmp_path / "lyrics"
    _write_song_json(out / "buba-solo", "Dup Song", "Buba Corelli")
    _write_song_json(out / "jala-solo", "Dup Song", "Buba Corelli")

    rebuild_index(out)

    dedup = json.loads((out / "_dedup_log.json").read_text(encoding="utf-8"))
    assert len(dedup) == 1
    assert dedup[0]["title"] == "Dup Song"


def test_rebuild_empty_dir(tmp_path):
    """Rebuild on empty directory produces empty index."""
    out = tmp_path / "lyrics"
    out.mkdir(parents=True)

    stats = rebuild_index(out)

    assert stats["unique_songs"] == 0
    assert stats["skipped_dup"] == 0
    index = json.loads((out / "_index.json").read_text(encoding="utf-8"))
    assert len(index) == 0


def test_norm_key():
    """Normalized key strips punctuation and lowercases."""
    k1 = _norm_key("O.D.D.D.", "Jala Brat")
    k2 = _norm_key("oddd", "jala brat")
    assert k1 == k2


def test_rebuild_different_artists_same_title(tmp_path):
    """Same title but different primary_artist are NOT duplicates."""
    out = tmp_path / "lyrics"
    _write_song_json(out / "buba-solo", "Love", "Buba Corelli")
    _write_song_json(out / "jala-solo", "Love", "Jala Brat")

    stats = rebuild_index(out)

    assert stats["unique_songs"] == 2
    assert stats["skipped_dup"] == 0
