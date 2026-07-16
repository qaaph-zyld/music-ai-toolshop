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


def test_run_batch_skips_skipped_long_on_resume(tmp_path):
    """skipped_long entries are skipped on resume, like completed."""
    (tmp_path / "a.wav").touch()
    (tmp_path / "b.wav").touch()

    status_path = tmp_path / "out" / "batch_status.json"
    status_path.parent.mkdir(parents=True)
    status_path.write_text(
        '{"input_dir":"' + str(tmp_path).replace("\\", "/") + '"'
        ',"total_tracks":2,"tracks":[{"source":"' + str(tmp_path / "a.wav").replace("\\", "/") + '"'
        ',"slug":"a_unknown","status":"skipped_long","duration_seconds":999}],"errors":[],"last_completed_index":0}',
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


def test_run_batch_preserves_outside_slice_entries(tmp_path):
    """Entries for tracks outside the current --offset/--limit slice persist untouched."""
    for name in ["a.wav", "b.wav", "c.wav", "d.wav"]:
        (tmp_path / name).touch()

    status_path = tmp_path / "out" / "batch_status.json"
    status_path.parent.mkdir(parents=True)

    # Pre-existing status has entries for a (failed) and d (skipped_long)
    status_path.write_text(
        '{"input_dir":"' + str(tmp_path).replace("\\", "/") + '"'
        ',"total_tracks":4,"tracks":['
        '{"source":"' + str(tmp_path / "a.wav").replace("\\", "/") + '","slug":"a_unknown","status":"failed","error":"boom"},'
        '{"source":"' + str(tmp_path / "d.wav").replace("\\", "/") + '","slug":"d_unknown","status":"skipped_long"}'
        '],"errors":[],"last_completed_index":-1}',
        encoding="utf-8",
    )

    calls = []

    def process(path: Path) -> dict:
        calls.append(path.name)
        return {"status": "completed"}

    # Run only b and c (offset=1, limit=2)
    status = batch.run_batch(
        files=[tmp_path / "b.wav", tmp_path / "c.wav"],
        output_dir=tmp_path / "out",
        process=process,
        status_path=status_path,
        offset=1,
    )

    # b and c were processed
    assert calls == ["b.wav", "c.wav"]

    # a (failed) and d (skipped_long) entries are still in status, untouched
    sources = {batch._norm_path(t["source"]): t for t in status["tracks"]}
    assert batch._norm_path(tmp_path / "a.wav") in sources
    assert sources[batch._norm_path(tmp_path / "a.wav")]["status"] == "failed"
    assert batch._norm_path(tmp_path / "d.wav") in sources
    assert sources[batch._norm_path(tmp_path / "d.wav")]["status"] == "skipped_long"


def test_run_batch_retries_failed_when_targeted(tmp_path):
    """Failed tracks ARE retried when targeted in a subsequent run."""
    (tmp_path / "a.wav").touch()

    status_path = tmp_path / "out" / "batch_status.json"
    status_path.parent.mkdir(parents=True)
    status_path.write_text(
        '{"input_dir":"' + str(tmp_path).replace("\\", "/") + '"'
        ',"total_tracks":1,"tracks":[{"source":"' + str(tmp_path / "a.wav").replace("\\", "/") + '"'
        ',"slug":"a_unknown","status":"failed","error":"boom"}],"errors":[],"last_completed_index":-1}',
        encoding="utf-8",
    )

    calls = []

    def process(path: Path) -> dict:
        calls.append(path.name)
        return {"status": "completed"}

    status = batch.run_batch(
        files=[tmp_path / "a.wav"],
        output_dir=tmp_path / "out",
        process=process,
        status_path=status_path,
    )

    # a.wav was reprocessed (not skipped)
    assert calls == ["a.wav"]
    assert status["tracks"][0]["status"] == "completed"
