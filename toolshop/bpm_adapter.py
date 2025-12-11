"""BPM and key analysis adapter.

Uses librosa for standalone BPM/key detection. Can be swapped out
for the bpm_key_recognize repo once that exists.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import librosa
    import numpy as np

    _HAS_LIBROSA = True
except ImportError:
    _HAS_LIBROSA = False


def _check_librosa() -> None:
    if not _HAS_LIBROSA:
        raise RuntimeError(
            "librosa is required for BPM/key analysis. Install with: pip install librosa numpy"
        )


def analyze_track(path: Path) -> Dict[str, Any]:
    """Analyze a single audio file for BPM, key, and basic features.

    Args:
        path: Path to an audio file (WAV recommended).

    Returns:
        Dictionary with keys: bpm, key, mode, duration, sample_rate, etc.
    """
    _check_librosa()
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {path}")

    y, sr = librosa.load(str(path), sr=22050, mono=True)
    duration = librosa.get_duration(y=y, sr=sr)

    # BPM
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    bpm = float(tempo)

    # Key estimation via chroma
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    chroma_mean = np.mean(chroma, axis=1)
    key_idx = int(np.argmax(chroma_mean))
    keys = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    key = keys[key_idx]

    # Simple major/minor heuristic
    mode = "major" if chroma_mean[key_idx] > 0.5 else "minor"

    return {
        "file": str(path),
        "bpm": round(bpm, 2),
        "key": key,
        "mode": mode,
        "duration_seconds": round(duration, 2),
        "sample_rate": sr,
    }


def analyze_library(
    root: Path,
    extensions: Optional[List[str]] = None,
    output_json: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Analyze all audio files under a directory for BPM/key.

    Args:
        root: Root directory to walk.
        extensions: List of extensions to include (default: wav).
        output_json: If provided, write results to this JSON file.

    Returns:
        List of analysis results (one dict per file).
    """
    _check_librosa()
    if extensions is None:
        extensions = ["wav"]

    results: List[Dict[str, Any]] = []
    for ext in extensions:
        for audio_path in root.rglob(f"*.{ext}"):
            try:
                result = analyze_track(audio_path)
                results.append(result)
                print(f"✓ {audio_path.name}: {result['bpm']} BPM, {result['key']} {result['mode']}")
            except Exception as e:
                print(f"✗ {audio_path.name}: {e}")
                results.append({"file": str(audio_path), "error": str(e)})

    if output_json:
        output_json.parent.mkdir(parents=True, exist_ok=True)
        with output_json.open("w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to {output_json}")

    return results
