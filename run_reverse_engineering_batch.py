r"""Generic reverse-engineering batch runner.

Applies the PapaPedro-proven pipeline to any directory of audio files.
Supports chunked, resumable processing and produces per-track recipes plus
a batch-level status JSON.

Run via PowerShell with:
    & "d:\Projects\Music-AI-Toolshop\run_crhymetv_batch.ps1"

Or directly:
    python run_reverse_engineering_batch.py --input-dir <dir> --output-dir <dir>
"""
import argparse
import json
import os
import re
import sys
import traceback
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import librosa


def _norm_path(path: Any) -> str:
    """Return a case-insensitive, NFC-normalized path string for comparison."""
    s = str(path)
    s = unicodedata.normalize("NFC", s)
    if sys.platform == "win32":
        s = s.lower()
    return s

# Force UTF-8 for stdout/stderr so filenames with fullwidth chars do not crash cp1252 console
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


def probe_duration(path: Path) -> Optional[float]:
    """Return audio duration in seconds without loading the full signal."""
    try:
        return float(librosa.get_duration(path=str(path)))
    except Exception as exc:
        print(f"WARNING: could not probe duration for {path}: {exc}", file=sys.stderr)
        return None


def discover_tracks(input_dir: Path, limit: int = 0, offset: int = 0) -> List[Path]:
    """Discover and return a sorted, sliced list of audio files."""
    tracks = sorted(input_dir.glob("*.mp3"), key=lambda p: p.name.lower())
    if offset:
        tracks = tracks[offset:]
    if limit > 0:
        tracks = tracks[:limit]
    return tracks


def load_or_create_status(output_dir: Path, input_dir: Path, total: int, chunk_size: int) -> Dict[str, Any]:
    """Load existing batch status or create a new one."""
    status_path = output_dir / "batch_status.json"
    if status_path.exists():
        try:
            status = json.loads(status_path.read_text(encoding="utf-8"))
            # Verify it matches the current run parameters; if not, treat as stale and reset.
            if _norm_path(status.get("input_dir")) == _norm_path(input_dir) and status.get("total_tracks") == total:
                status.setdefault("tracks", [])
                status.setdefault("errors", [])
                return status
        except Exception as exc:
            print(f"WARNING: Could not read existing status ({exc}); starting fresh.", file=sys.stderr)

    return {
        "started": datetime.now().isoformat(),
        "finished": None,
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "total_tracks": total,
        "chunk_size": chunk_size,
        "last_completed_index": -1,
        "tracks": [],
        "errors": [],
    }


def save_status(status: Dict[str, Any], output_dir: Path) -> None:
    """Persist batch status to JSON."""
    status_path = output_dir / "batch_status.json"
    status_path.write_text(json.dumps(status, indent=2, default=str), encoding="utf-8")
    sys.stdout.flush()


def write_recipe(
    track_path: Path,
    track_out: Path,
    analysis: Dict[str, Any],
    voice: Dict[str, Any],
    stems: Dict[str, Any],
) -> str:
    """Write a human-readable recipe.md for a single track."""
    recipe_path = track_out / "recipe.md"
    md = [
        f"# {track_path.stem}",
        f"- **Source:** `{track_path}`",
        "",
        "## Tempo & Key",
        f"- **BPM:** {analysis.get('bpm')}",
        f"- **Key:** {analysis.get('key')} {analysis.get('mode')}",
        f"- **Duration:** {analysis.get('duration_seconds')} s",
        f"- **Backend:** {analysis.get('analysis_backend')}",
    ]
    if analysis.get("tuning_offset"):
        md.append(f"- **Tuning offset:** {analysis.get('tuning_offset')}")

    md += ["", "## Chord Progression"]
    for c in analysis.get("chord_progression", [])[:8]:
        md.append(f"- `{c.get('name')}` @ {c.get('start_time', 0):.2f}s")

    md += ["", "## Detected Instruments"]
    for i in analysis.get("instruments", [])[:8]:
        score = i.get("score")
        score_str = f"{score:.0%}" if isinstance(score, (int, float)) else str(score)
        md.append(f"- {i.get('label')} ({score_str})")

    md += ["", "## Production Effects (full-mix proxy)"]
    for e in voice.get("effects_detected", []):
        if e.get("confidence", 0) > 0.3:
            md.append(f"- **{e.get('effect')}** — {e.get('confidence', 0):.0%}")
            if "reason" in e:
                md.append(f"  - {e.get('reason')}")

    md += ["", "## Stems"]
    if isinstance(stems, dict) and stems.get("skipped"):
        md.append("*Skipped: analyze-only pass; run `toolshop stems <file>` later.*")
    else:
        stem_paths = stems.get("stems", {}) if isinstance(stems, dict) else {}
        if isinstance(stem_paths, dict):
            for k, v in stem_paths.items():
                md.append(f"- **{k}:** `{v}`")
        else:
            md.append(str(stems))

    md += [
        "",
        "## Recreation Notes",
        "- Start with the BPM and key above.",
        "- Use the chord progression as the harmonic skeleton.",
        "- Match the detected effects chain to approximate the mix character.",
        "- Reference the separated stems for layer layout.",
        "- Note: effects are detected on the original full mix (proxy for vocal processing).",
        "",
        "## Suno Prompt Seed",
        f"{analysis.get('bpm')} bpm, {analysis.get('key')} {analysis.get('mode')}, "
        f"German rap / hip-hop, {track_path.stem[:40]}",
    ]
    recipe_path.write_text("\n".join(md), encoding="utf-8")
    return str(recipe_path)


def process_track(
    track_path: Path,
    track_out: Path,
    use_gpu: bool,
    high_quality: bool,
    adapters: Any,
    no_stems: bool = False,
) -> Dict[str, Any]:
    """Run the reverse-engineering pipeline on one track, optionally skipping stems."""
    reverse_engineering_adapter = adapters.reverse_engineering_adapter
    stem_extractor_adapter = adapters.stem_extractor_adapter
    voice_effects_adapter = adapters.voice_effects_adapter

    track_info = {
        "source": str(track_path),
        "slug": track_out.name,
        "out_dir": str(track_out),
        "status": "pending",
        "analysis_json": None,
        "voice_json": None,
        "stems": None,
        "recipe_md": None,
        "error": None,
    }

    track_out.mkdir(parents=True, exist_ok=True)

    print(f"Analyzing {track_out.name}...")
    analysis = reverse_engineering_adapter.analyze_track(
        track_path,
        export_json=True,
        output_dir=track_out,
        effects=True,
        instruments=True,
        chords=True,
        notes=True,
        separation="hpss",
        backend="advanced",
    )
    track_info["analysis_json"] = str(track_out / f"{track_path.stem}_analysis.json")
    track_info["analysis_summary"] = {
        "bpm": analysis.get("bpm"),
        "key": f"{analysis.get('key')} {analysis.get('mode')}",
        "duration": analysis.get("duration_seconds"),
        "backend": analysis.get("analysis_backend"),
        "chords": [c.get("name") for c in analysis.get("chord_progression", [])[:6]],
        "instruments": [i.get("label") for i in analysis.get("instruments", [])[:5]],
    }

    if no_stems:
        print(f"Skipping stems for {track_out.name} (--no-stems).")
        stems: Dict[str, Any] = {"skipped": True}
    else:
        print(f"Extracting stems {track_out.name}...")
        stems = stem_extractor_adapter.extract_stems(
            track_path,
            output_dir=track_out / "stems",
            use_gpu=use_gpu,
            high_quality=high_quality,
        )
        # Normalize relative stem paths to absolute
        if isinstance(stems, dict):
            stem_paths = stems.get("stems", {})
            if isinstance(stem_paths, dict):
                for k, v in stem_paths.items():
                    if v and not Path(v).is_absolute():
                        stem_paths[k] = str(track_out / "stems" / v)
    track_info["stems"] = stems

    print(f"Analyzing voice/effects {track_out.name}...")
    voice = voice_effects_adapter.analyze_voice(
        track_path,
        export_json=True,
        output_dir=track_out,
    )
    track_info["voice_json"] = str(track_out / f"{track_path.stem}_voice_analysis.json")
    track_info["voice_summary"] = [
        e.get("effect") for e in voice.get("effects_detected", []) if e.get("confidence", 0) > 0.3
    ]

    track_info["recipe_md"] = write_recipe(track_path, track_out, analysis, voice, stems)
    track_info["status"] = "completed"
    return track_info


class Adapters:
    """Lazy-loaded adapter module handle."""

    def __init__(self):
        self._loaded = False
        self.reverse_engineering_adapter = None
        self.stem_extractor_adapter = None
        self.voice_effects_adapter = None

    def load(self) -> None:
        if self._loaded:
            return
        from toolshop import reverse_engineering_adapter, stem_extractor_adapter, voice_effects_adapter

        self.reverse_engineering_adapter = reverse_engineering_adapter
        self.stem_extractor_adapter = stem_extractor_adapter
        self.voice_effects_adapter = voice_effects_adapter
        self._loaded = True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generic reverse-engineering batch runner.")
    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Directory containing audio files to analyze.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory for batch results.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Maximum number of tracks to process (0 = all).",
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Number of tracks to skip at the start.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=30,
        help="Number of tracks per chunk for progress reporting.",
    )
    parser.add_argument(
        "--use-gpu",
        action="store_true",
        help="Use GPU for stem separation (default: CPU).",
    )
    parser.add_argument(
        "--high-quality",
        action="store_true",
        help="Use high-quality (slower) stem separation models.",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Ignore existing batch_status.json and start fresh.",
    )
    parser.add_argument(
        "--no-stems",
        action="store_true",
        help="Skip stem extraction; analyze-only pass.",
    )
    parser.add_argument(
        "--require-advanced",
        action="store_true",
        help="Fail fast if the wav_reverse_engineer advanced backend is not available.",
    )
    parser.add_argument(
        "--max-duration",
        type=int,
        default=0,
        help="Skip tracks longer than this many seconds (0 = off). Record status as skipped_long.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_dir = args.input_dir.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if not input_dir.exists():
        print(f"ERROR: Input directory not found: {input_dir}", file=sys.stderr)
        return 1

    all_tracks = discover_tracks(input_dir, limit=0, offset=0)
    target_tracks = discover_tracks(input_dir, limit=args.limit, offset=args.offset)
    total = len(target_tracks)
    chunk_size = max(1, args.chunk_size)

    print(f"Discovered {len(all_tracks)} tracks; will process {total} (offset={args.offset}, limit={args.limit})")
    print(f"Chunk size: {chunk_size}")
    print(f"Output: {output_dir}")
    sys.stdout.flush()

    status = load_or_create_status(output_dir, input_dir, len(all_tracks), chunk_size)
    if args.no_resume:
        status = {
            "started": datetime.now().isoformat(),
            "finished": None,
            "input_dir": str(input_dir),
            "output_dir": str(output_dir),
            "total_tracks": len(all_tracks),
            "chunk_size": chunk_size,
            "last_completed_index": -1,
            "tracks": [],
            "errors": [],
        }

    adapters = Adapters()
    try:
        adapters.load()
    except Exception as e:
        status["errors"].append(f"toolshop import failed: {traceback.format_exc()}")
        save_status(status, output_dir)
        print("IMPORT_FAILED", file=sys.stderr)
        return 1

    if args.require_advanced and not adapters.reverse_engineering_adapter._WAV_RE_AVAILABLE:
        msg = "Advanced backend (wav_reverse_engineer) is required but not available."
        status["errors"].append(msg)
        save_status(status, output_dir)
        print(f"ERROR: {msg}", file=sys.stderr)
        return 1

    # Build a lookup of existing completed tracks by source path for resume
    status["tracks"] = status.get("tracks", [])
    completed_by_source = {
        _norm_path(t.get("source")): t for t in status["tracks"] if t.get("status") == "completed"
    }
    completed_tracks = list(completed_by_source.values())

    started_at = datetime.now()
    for idx, track_path in enumerate(target_tracks, start=args.offset):
        if _norm_path(track_path) in completed_by_source:
            print(f"[{idx + 1}/{len(all_tracks)}] SKIPPED (already completed): {track_path.name}")
            sys.stdout.flush()
            continue

        if args.max_duration > 0:
            duration = probe_duration(track_path)
            if duration is not None and duration > args.max_duration:
                print(
                    f"[{idx + 1}/{len(all_tracks)}] SKIPPED_LONG ({duration:.0f}s > {args.max_duration}s): {track_path.name}",
                    file=sys.stderr,
                )
                sys.stderr.flush()
                track_info = {
                    "source": str(track_path),
                    "slug": safe_slug(track_path.name),
                    "out_dir": str(output_dir / "per_track" / safe_slug(track_path.name)),
                    "status": "skipped_long",
                    "duration_seconds": duration,
                    "analysis_json": None,
                    "voice_json": None,
                    "stems": None,
                    "recipe_md": None,
                    "error": None,
                }
                status["tracks"] = [t for t in status["tracks"] if _norm_path(t.get("source")) != _norm_path(track_path)]
                status["tracks"].append(track_info)
                save_status(status, output_dir)
                continue

        chunk_num = (idx // chunk_size) + 1
        total_chunks = max(1, (len(all_tracks) + chunk_size - 1) // chunk_size)
        print(f"[{idx + 1}/{len(all_tracks)}] Chunk {chunk_num}/{total_chunks}: {track_path.name}")
        sys.stdout.flush()

        slug = safe_slug(track_path.name)
        track_out = output_dir / "per_track" / slug
        track_info = {
            "source": str(track_path),
            "slug": slug,
            "out_dir": str(track_out),
            "status": "pending",
            "analysis_json": None,
            "voice_json": None,
            "stems": None,
            "recipe_md": None,
            "error": None,
        }
        # Remove any prior entry for this source to avoid duplicates on resume
        status["tracks"] = [t for t in status["tracks"] if _norm_path(t.get("source")) != _norm_path(track_path)]
        try:
            track_info = process_track(
                track_path, track_out, args.use_gpu, args.high_quality, adapters,
                no_stems=args.no_stems,
            )
            status["last_completed_index"] = idx
        except Exception as e:
            track_info["status"] = "failed"
            track_info["error"] = traceback.format_exc()
            status["errors"].append(f"{slug}: {str(e)}")
            print(f"FAILED {slug}: {e}", file=sys.stderr)
            sys.stderr.flush()
        finally:
            status["tracks"].append(track_info)
            save_status(status, output_dir)

    # completed_tracks are already in status["tracks"]; ensure they remain
    status["finished"] = datetime.now().isoformat()
    status["duration_seconds"] = (datetime.now() - started_at).total_seconds()
    save_status(status, output_dir)

    print("BATCH_DONE")
    sys.stdout.flush()
    if status["errors"]:
        print(f"Errors: {len(status['errors'])}", file=sys.stderr)
        sys.stderr.flush()
    return 0 if not status["errors"] else 1


if __name__ == "__main__":
    sys.exit(main())
