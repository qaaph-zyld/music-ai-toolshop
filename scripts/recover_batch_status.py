"""Recover batch_status.json entries from existing per_track directories."""
import json
from pathlib import Path
from datetime import datetime

from run_reverse_engineering_batch import discover_tracks, safe_slug, load_or_create_status

INPUT_DIR = Path(r"d:\Projects\Tools\yt_extractor\downloads\CrhymeTV")
OUTPUT_DIR = Path(r"d:\Projects\Music-AI-Toolshop\results\crhymetv_re")


def track_is_complete(track_dir: Path) -> bool:
    """Check if a per_track directory contains all expected outputs."""
    if not track_dir.is_dir():
        return False
    # Find analysis/voice/recipe files by extension/prefix
    analysis_json = list(track_dir.glob("*_analysis.json"))
    voice_json = list(track_dir.glob("*_voice_analysis.json"))
    recipe_md = list(track_dir.glob("recipe.md"))
    stems_dir = track_dir / "stems"
    if not (analysis_json and voice_json and recipe_md and stems_dir.is_dir()):
        return False
    stems = list(stems_dir.glob("*.wav"))
    return len(stems) >= 2


def build_entry(track_path: Path, track_dir: Path) -> dict:
    """Build a minimal completed entry from existing files."""
    analysis_json = next(track_dir.glob("*_analysis.json"))
    voice_json = next(track_dir.glob("*_voice_analysis.json"))
    recipe_md = next(track_dir.glob("recipe.md"))
    stems_dir = track_dir / "stems"
    instrumental = next((p for p in stems_dir.glob("*.wav") if "instrumental" in p.name.lower()), None)
    main_vocals = next((p for p in stems_dir.glob("*.wav") if "vocals" in p.name.lower()), None)
    return {
        "source": str(track_path),
        "slug": track_dir.name,
        "out_dir": str(track_dir),
        "status": "completed",
        "analysis_json": str(analysis_json),
        "voice_json": str(voice_json),
        "stems": {
            "input_file": str(track_path),
            "output_dir": str(stems_dir),
            "stems": {
                "instrumental": str(instrumental) if instrumental else None,
                "main_vocals": str(main_vocals) if main_vocals else None,
                "backing_vocals": None,
            },
            "models_used": {"pass1": "UVR-MDX-NET-Voc_FT.onnx", "pass2": "UVR-BVE-4B_SN-44100-1.pth"},
            "gpu_used": False,
            "quality_mode": "fast",
        },
        "recipe_md": str(recipe_md),
        "error": None,
        "analysis_summary": {},
        "voice_summary": [],
    }


def main():
    all_tracks = discover_tracks(INPUT_DIR, limit=0, offset=0)
    status = load_or_create_status(OUTPUT_DIR, INPUT_DIR, total=len(all_tracks), chunk_size=30)
    track_by_source = {str(t): t for t in all_tracks}

    existing_completed = {t.get("source") for t in status.get("tracks", []) if t.get("status") == "completed"}
    per_track_dir = OUTPUT_DIR / "per_track"
    recovered = 0
    for track_dir in per_track_dir.iterdir():
        if not track_dir.is_dir():
            continue
        # Map slug back to source by finding a matching track
        matching = [src for src in track_by_source if safe_slug(Path(src).name) == track_dir.name]
        if not matching:
            print(f"No source match for {track_dir.name}")
            continue
        source = matching[0]
        if source in existing_completed:
            continue
        if not track_is_complete(track_dir):
            print(f"Incomplete outputs for {track_dir.name}")
            continue
        entry = build_entry(Path(source), track_dir)
        status["tracks"].append(entry)
        recovered += 1
        print(f"Recovered: {track_dir.name}")

    # Recompute last_completed_index
    completed_sources = {t.get("source") for t in status["tracks"] if t.get("status") == "completed"}
    last_completed = -1
    for idx, track in enumerate(all_tracks):
        if str(track) in completed_sources:
            last_completed = idx
    status["last_completed_index"] = max(last_completed, status.get("last_completed_index", -1))
    status["total_tracks"] = len(all_tracks)
    status["finished"] = status.get("finished", datetime.now().isoformat())

    status_path = OUTPUT_DIR / "batch_status.json"
    status_path.write_text(json.dumps(status, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Recovered {recovered} tracks. Total completed: {len(completed_sources)}. Last index: {status['last_completed_index']}")


if __name__ == "__main__":
    main()
