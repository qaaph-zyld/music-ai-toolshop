"""CLI handler for the `toolshop remix` command."""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import batch, remix_adapter


def _default_data_root() -> Path:
    return Path(os.environ.get("TOOLSHOP_DATA_DIR", r"D:\MusicData\toolshop"))


def _parse_fx(fx_args: Optional[List[str]]) -> Optional[List[str]]:
    if not fx_args:
        return None
    result: List[str] = []
    for token in fx_args:
        for part in token.split(","):
            part = part.strip()
            if part:
                result.append(part)
    return result or None


def _default_format(mode: str, explicit: Optional[str]) -> str:
    if explicit:
        return explicit
    return "flac" if mode == "sample" else "wav"


def _is_audio_path(path: Path) -> bool:
    return path.suffix.lower() in (".wav", ".flac", ".mp3")


def _resolve_output_path(input_path: Path, args: Any) -> Path:
    """Return the output file (remix) or directory (sample) for one input."""
    mode = args.mode
    slug = batch.safe_slug(input_path.name)
    fmt = _default_format(mode, args.format)
    ext = ".wav" if fmt == "wav" else ".flac"

    explicit_file = Path(args.output) if args.output else None
    explicit_dir = Path(args.output_dir) if args.output_dir else None

    if mode == "remix":
        if explicit_file and _is_audio_path(explicit_file):
            return explicit_file
        # Treat explicit path or directory as a folder containing the remix file.
        out_dir = explicit_file or explicit_dir
        if out_dir is None:
            out_dir = _default_data_root() / "remixes" / slug
        return out_dir / f"{slug}_remix{ext}"

    # sample mode writes into a directory
    if explicit_file:
        return explicit_file
    if explicit_dir:
        return explicit_dir
    return _default_data_root() / "samples" / slug


def _process_one(input_path: Path, args: Any) -> Dict[str, Any]:
    mode = args.mode
    output_path = _resolve_output_path(input_path, args)

    target_bpm = args.target_bpm
    target_key = args.target_key
    if target_bpm is not None and target_bpm <= 0:
        raise ValueError("target-bpm must be positive")

    result = remix_adapter.create_remix(
        input_path=input_path,
        output_path=output_path,
        target_bpm=target_bpm,
        target_key=target_key,
        mode=mode,
        segment_beats=args.segment_beats,
        fx_chain=_parse_fx(args.fx),
        max_duration=args.max_duration,
        source_bpm=args.source_bpm,
        source_key=args.source_key,
        output_format=_default_format(mode, args.format),
        stems_dir=args.stems_dir,
        stem_name=args.stem,
        crossfade_ms=args.crossfade_ms,
    )
    return {
        "status": "completed",
        "result": result,
    }


def _process_one_for_batch(input_path: Path, args: Any) -> Dict[str, Any]:
    original_output = args.output
    original_output_dir = args.output_dir
    try:
        if args.output_dir:
            slug = batch.safe_slug(input_path.name)
            per_file_dir = Path(args.output_dir) / slug
            args.output = str(per_file_dir)
            args.output_dir = None
        return _process_one(input_path, args)
    except Exception as exc:
        logging.exception("Failed to remix %s", input_path)
        return {"status": "failed", "error": f"{exc.__class__.__name__}: {exc}"}
    finally:
        args.output = original_output
        args.output_dir = original_output_dir


def _print_result(result: remix_adapter.RemixResult, mode: str) -> None:
    print(f"Created {mode} from {result.source}")
    print(f"  Output: {result.output_file}")
    print(f"  Source BPM/Key: {result.bpm:.2f} / {result.key}")
    if result.target_bpm:
        print(f"  Target BPM: {result.target_bpm:.2f}")
    if result.target_key:
        print(f"  Target Key: {result.target_key}")
    if result.fx_chain:
        print(f"  FX: {', '.join(result.fx_chain)}")
    if result.truncated:
        print(f"  Truncated to {result.duration_seconds:.2f}s")
    if result.manifest_path:
        print(f"  Manifest: {result.manifest_path}")
    if result.samples:
        print(f"  Samples: {len(result.samples)}")


def run(args: Any) -> int:
    """Entry point for `toolshop remix`."""
    try:
        remix_adapter._require_deps()
    except remix_adapter.MissingDependencyError as exc:
        print(f"Missing dependency: {exc}", file=sys.stderr)
        print("Install with: pip install -e '.[remix]'", file=sys.stderr)
        return 1

    input_path = Path(args.path)
    if not input_path.exists():
        print(f"Path not found: {input_path}", file=sys.stderr)
        return 1

    if input_path.is_file():
        result_dict = _process_one(input_path, args)
        if result_dict["status"] == "failed":
            print(f"Error: {result_dict.get('error')}", file=sys.stderr)
            return 1
        result = result_dict["result"]
        if args.json:
            print(json.dumps(result.to_dict(), indent=2, default=str))
        else:
            _print_result(result, args.mode)
        return 0

    # Directory / batch mode.
    if args.output:
        print("--output is for single files; use --output-dir for batches.", file=sys.stderr)
        return 1

    default_root = _default_data_root() / ("samples" if args.mode == "sample" else "remixes")
    output_root = Path(args.output_dir) if args.output_dir else default_root
    files = batch.discover_files(
        input_path,
        extensions=["wav", "mp3", "flac"],
        limit=args.limit or 0,
        offset=args.offset or 0,
    )
    if not files:
        print(f"No audio files found in {input_path}", file=sys.stderr)
        return 1

    status = batch.run_batch(
        files=files,
        output_dir=output_root,
        process=lambda p: _process_one_for_batch(p, args),
        resume=not args.no_resume,
        offset=args.offset or 0,
        description=f"remix/{args.mode}",
    )
    completed = sum(1 for t in status.get("tracks", []) if t["status"] == "completed")
    failed = sum(1 for t in status.get("tracks", []) if t["status"] == "failed")
    print(f"Batch complete: {completed} completed, {failed} failed.")
    return 0 if failed == 0 else 1
