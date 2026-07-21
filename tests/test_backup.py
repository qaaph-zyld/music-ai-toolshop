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
