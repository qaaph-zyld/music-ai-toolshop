"""Tests for toolshop/backup.py."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from toolshop import backup


def _make_fake_lyrics_db(path: Path) -> None:
    conn = sqlite3.connect(str(path))
    conn.executescript(
        "CREATE TABLE songs (id INTEGER PRIMARY KEY, title TEXT);"
        "INSERT INTO songs VALUES (1, 'Test Song');"
    )
    conn.commit()
    conn.close()


def test_run_backup_copies_files(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "backup"

    lyrics_dir = source / "lyrics" / "genius" / "artist-solo"
    lyrics_dir.mkdir(parents=True)
    (lyrics_dir / "song1.json").write_text('{"title": "Song 1"}', encoding="utf-8")
    (lyrics_dir / "song1.txt").write_text("lyrics here", encoding="utf-8")

    db_path = source / "lyrics" / "lyrics.db"
    _make_fake_lyrics_db(db_path)

    manifest = backup.run_backup(target=target, source_root=source, repo_root=tmp_path)

    assert manifest.file_count >= 3
    assert manifest.verified is True
    assert (target / "backup_manifest.json").exists()
    assert (target / "lyrics" / "lyrics.db").exists()
    assert (target / "lyrics" / "genius" / "artist-solo" / "song1.json").exists()


def test_check_backup_no_manifest(tmp_path):
    result = backup.check_backup(target=tmp_path)
    assert result["ok"] is False
    assert "no manifest" in result["reason"]


def test_check_backup_valid(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "backup"

    lyrics_dir = source / "lyrics" / "genius"
    lyrics_dir.mkdir(parents=True)
    (lyrics_dir / "song.json").write_text("{}", encoding="utf-8")

    db_path = source / "lyrics" / "lyrics.db"
    _make_fake_lyrics_db(db_path)

    backup.run_backup(target=target, source_root=source, repo_root=tmp_path)
    result = backup.check_backup(target=target)

    assert result["ok"] is True
    assert result["verified"] is True
    assert result["file_count"] >= 2


def test_verify_db(tmp_path):
    db_path = tmp_path / "test.db"
    _make_fake_lyrics_db(db_path)
    assert backup.verify_db(db_path) is True


def test_verify_db_missing(tmp_path):
    assert backup.verify_db(tmp_path / "nonexistent.db") is False


# ---------------------------------------------------------------- Suno coverage
#
# Regression guard for assessment F1b (2026-08-19): the backup verified clean for
# a month while collecting zero Suno data. A green manifest against the wrong
# asset set is exactly what these tests exist to prevent.


def _make_suno_tree(source: Path, n_meta: int = 2, n_audio: int = 2) -> None:
    suno = source / "suno"
    suno.mkdir(parents=True, exist_ok=True)
    for i in range(n_meta):
        (suno / f"track{i}_metadata.json").write_text(
            f'{{"id": "track{i}", "audio_url": "https://cdn1.suno.ai/track{i}.mp3"}}',
            encoding="utf-8",
        )
    audio = suno / "audio"
    audio.mkdir(exist_ok=True)
    (audio / "_download_manifest.json").write_text('{"entries": []}', encoding="utf-8")
    for i in range(n_audio):
        (audio / f"track{i}.mp3").write_bytes(b"ID3\x03\x00" + b"\x00" * 64)


def test_backup_includes_suno_metadata_and_manifest(tmp_path):
    """Tier-1 must carry the metadata: it is the only index of what exists."""
    source = tmp_path / "source"
    (source / "lyrics").mkdir(parents=True)
    _make_suno_tree(source)

    manifest = backup.run_backup(
        target=tmp_path / "backup",
        source_root=source,
        repo_root=tmp_path,
        include_external=False,
    )

    assert (tmp_path / "backup" / "suno" / "track0_metadata.json").exists()
    assert (tmp_path / "backup" / "suno" / "track1_metadata.json").exists()
    assert (tmp_path / "backup" / "suno" / "audio" / "_download_manifest.json").exists()

    backed_up = {Path(f["relative_path"]).name for f in manifest.files}
    assert "track0_metadata.json" in backed_up
    assert "_download_manifest.json" in backed_up


def test_backup_excludes_audio_by_default(tmp_path):
    """Audio is Tier-2: covered on request, not by default."""
    source = tmp_path / "source"
    (source / "lyrics").mkdir(parents=True)
    _make_suno_tree(source)

    backup.run_backup(
        target=tmp_path / "backup",
        source_root=source,
        repo_root=tmp_path,
        include_external=False,
    )

    assert not (tmp_path / "backup" / "suno" / "audio" / "track0.mp3").exists()


def test_backup_includes_audio_when_requested(tmp_path):
    source = tmp_path / "source"
    (source / "lyrics").mkdir(parents=True)
    _make_suno_tree(source)

    manifest = backup.run_backup(
        target=tmp_path / "backup",
        source_root=source,
        repo_root=tmp_path,
        include_audio=True,
        include_external=False,
    )

    assert (tmp_path / "backup" / "suno" / "audio" / "track0.mp3").exists()
    assert (tmp_path / "backup" / "suno" / "audio" / "track1.mp3").exists()
    assert any(f["relative_path"].endswith("track0.mp3") for f in manifest.files)


def test_backup_includes_external_suno_extractor(tmp_path, monkeypatch):
    """The pre-2026-08-19 downloads live outside every source root."""
    extractor = tmp_path / "suno_extractor"
    (extractor / "suno_songs").mkdir(parents=True)
    (extractor / "suno_songs" / "liked.json").write_text("[]", encoding="utf-8")
    (extractor / "suno_downloads").mkdir()
    (extractor / "suno_downloads" / "legacy.mp3").write_bytes(b"ID3\x03\x00" + b"\x00" * 32)
    monkeypatch.setenv("TOOLSHOP_SUNO_EXTRACTOR_DIR", str(extractor))

    source = tmp_path / "source"
    (source / "lyrics").mkdir(parents=True)

    manifest = backup.run_backup(
        target=tmp_path / "backup",
        source_root=source,
        repo_root=tmp_path,
        include_audio=True,
    )

    names = {Path(f["relative_path"]).name for f in manifest.files}
    assert "liked.json" in names
    assert "legacy.mp3" in names
