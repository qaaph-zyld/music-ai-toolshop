"""Resumable batch runner shared by toolshop pipelines.

Extracted from `run_reverse_engineering_batch.py` so the new `toolshop stems`
command and the existing reverse-engineering batch can share the same resume,
status, and UTF-8-safety logic.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# Force UTF-8 for stdout/stderr so filenames with fullwidth chars do not crash
# a cp1252 console.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def safe_slug(name: str) -> str:
    """Create a filesystem-safe slug from a track filename.

    Preserves the YouTube-style [id].mp3 suffix if present.
    """
    m = re.search(r"\[([^\]]+)\]\.mp3$", name)
    if m:
        base = name[: m.start()].strip()
        id_part = m.group(1)
    else:
        base = Path(name).stem
        id_part = "unknown"
    slug = re.sub(r"[^a-zA-Z0-9_]+", "_", base).strip("_")
    return f"{slug[:50]}_{id_part}"


def _norm_path(path: Any) -> str:
    """Return a comparable path key (NFC, lower-case, forward slashes)."""
    s = str(path)
    s = unicodedata.normalize("NFC", s)
    s = s.replace("\\", "/")
    if sys.platform == "win32":
        s = s.lower()
    return s


def discover_files(input_dir: Path, extensions: List[str], limit: int = 0, offset: int = 0) -> List[Path]:
    """Discover and return a sorted, sliced list of audio files."""
    exts = {e.lower().lstrip(".") for e in extensions}
    tracks: List[Path] = []
    for ext in exts:
        tracks.extend(input_dir.rglob(f"*.{ext}"))
    tracks = sorted({p.resolve() for p in tracks}, key=lambda p: p.name.lower())
    if offset:
        tracks = tracks[offset:]
    if limit > 0:
        tracks = tracks[:limit]
    return tracks


def load_or_create_status(status_path: Path, input_dir: Path, total: int) -> Dict[str, Any]:
    """Load existing batch status or create a new one."""
    if status_path.exists():
        try:
            status = json.loads(status_path.read_text(encoding="utf-8"))
            if (
                _norm_path(status.get("input_dir")) == _norm_path(input_dir)
                and status.get("total_tracks") == total
            ):
                status.setdefault("tracks", [])
                status.setdefault("errors", [])
                return status
        except Exception as exc:
            logging.warning("Could not read existing status (%s); starting fresh.", exc)

    return {
        "started": datetime.now().isoformat(),
        "finished": None,
        "input_dir": str(input_dir),
        "output_dir": str(status_path.parent),
        "total_tracks": total,
        "last_completed_index": -1,
        "tracks": [],
        "errors": [],
    }


def save_status(status: Dict[str, Any], status_path: Path) -> None:
    """Persist batch status to JSON."""
    status_path.write_text(json.dumps(status, indent=2, default=str), encoding="utf-8")
    sys.stdout.flush()


def run_batch(
    files: List[Path],
    output_dir: Path,
    process: Callable[[Path], Dict[str, Any]],
    *,
    status_path: Optional[Path] = None,
    resume: bool = True,
    offset: int = 0,
    description: str = "batch",
) -> Dict[str, Any]:
    """Run a resumable batch over a list of files.

    Args:
        files: List of input files to process.
        output_dir: Root output directory.
        process: Callable that takes a Path and returns a result dict. It should
            set a "status" key ("completed" or "failed").
        status_path: Path to batch_status.json. Defaults to
            <output_dir>/batch_status.json.
        resume: If True, skip files already marked completed in status.
        offset: Global offset used for display indexing.
        description: Human-readable name for progress messages.

    Returns:
        The status dictionary after the run.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    status_path = status_path or output_dir / "batch_status.json"

    total = len(files)
    input_dir = files[0].parent if files else output_dir
    status = load_or_create_status(status_path, input_dir, total)

    completed_by_source = {
        _norm_path(t.get("source")): t
        for t in status.get("tracks", [])
        if t.get("status") == "completed"
    }

    for idx, file_path in enumerate(files, start=offset):
        norm_source = _norm_path(file_path)
        if resume and norm_source in completed_by_source:
            print(f"[{idx + 1}/{total}] SKIPPED (already completed): {file_path.name}")
            sys.stdout.flush()
            continue

        print(f"[{idx + 1}/{total}] {description}: {file_path.name}")
        sys.stdout.flush()

        # Remove any prior entry for this source to avoid duplicates on retry.
        status["tracks"] = [t for t in status["tracks"] if _norm_path(t.get("source")) != norm_source]

        track_info: Dict[str, Any] = {
            "source": str(file_path),
            "slug": safe_slug(file_path.name),
            "status": "pending",
            "started": datetime.now().isoformat(),
            "finished": None,
            "result": None,
            "error": None,
        }

        try:
            result = process(file_path)
            track_info["status"] = result.get("status", "completed")
            track_info["result"] = result
            track_info["finished"] = datetime.now().isoformat()
        except Exception as exc:
            track_info["status"] = "failed"
            track_info["error"] = f"{exc.__class__.__name__}: {exc}"
            track_info["finished"] = datetime.now().isoformat()
            logging.exception("Failed to process %s", file_path)

        status["tracks"].append(track_info)
        status["last_completed_index"] = idx
        save_status(status, status_path)

    status["finished"] = datetime.now().isoformat()
    save_status(status, status_path)
    return status
