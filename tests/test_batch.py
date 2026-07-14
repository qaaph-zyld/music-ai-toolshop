from pathlib import Path
from unittest.mock import MagicMock

import pytest

from toolshop import batch


@pytest.mark.parametrize(
    "name, expected_slug",
    [
        ("My Song [abc123].mp3", "My_Song_abc123"),
        ("test track.wav", "test_track_unknown"),
        ("A/B/C [x1].mp3", "A_B_C_x1"),
    ],
)
def test_safe_slug(name, expected_slug):
    assert batch.safe_slug(name) == expected_slug


def test_discover_files(tmp_path):
    (tmp_path / "a.wav").touch()
    (tmp_path / "b.mp3").touch()
    (tmp_path / "skip.txt").touch()
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "c.flac").touch()

    files = batch.discover_files(tmp_path, ["wav", "mp3", "flac"])
    assert [p.name for p in files] == ["a.wav", "b.mp3", "c.flac"]


def test_discover_files_limit_and_offset(tmp_path):
    for i in range(5):
        (tmp_path / f"track{i:02d}.wav").touch()

    files = batch.discover_files(tmp_path, ["wav"], limit=2, offset=1)
    assert [p.name for p in files] == ["track01.wav", "track02.wav"]


def test_run_batch_resumes(tmp_path):
    (tmp_path / "a.wav").touch()
    (tmp_path / "b.wav").touch()

    def process(path: Path) -> dict:
        return {"status": "completed", "file": path.name}

    out = tmp_path / "out"
    status = batch.run_batch(
        files=[tmp_path / "a.wav", tmp_path / "b.wav"],
        output_dir=out,
        process=process,
    )
    assert status["total_tracks"] == 2
    assert len(status["tracks"]) == 2
    assert all(t["status"] == "completed" for t in status["tracks"])
    assert (out / "batch_status.json").exists()


def test_run_batch_skips_completed_on_resume(tmp_path):
    (tmp_path / "a.wav").touch()
    (tmp_path / "b.wav").touch()

    status_path = tmp_path / "out" / "batch_status.json"
    status_path.parent.mkdir(parents=True)
    status_path.write_text(
        '{"input_dir":"' + str(tmp_path).replace("\\", "/") + '"'
        ',"total_tracks":2,"tracks":[{"source":"' + str(tmp_path / "a.wav").replace("\\", "/") + '"'
        ',"slug":"a_unknown","status":"completed"}],"errors":[],"last_completed_index":0}',
        encoding="utf-8",
    )

    calls = []

    def process(path: Path) -> dict:
        calls.append(path.name)
        return {"status": "completed"}

    batch.run_batch(
        files=[tmp_path / "a.wav", tmp_path / "b.wav"],
        output_dir=tmp_path / "out",
        process=process,
        status_path=status_path,
    )

    assert calls == ["b.wav"]


def test_run_batch_records_failure(tmp_path):
    (tmp_path / "a.wav").touch()

    def process(path: Path) -> dict:
        raise RuntimeError("boom")

    status = batch.run_batch(
        files=[tmp_path / "a.wav"],
        output_dir=tmp_path / "out",
        process=process,
    )

    assert status["tracks"][0]["status"] == "failed"
    assert "boom" in status["tracks"][0]["error"]
