"""Track reverse engineering adapter.

Wires to the wav_reverse_engineer module in Track_reverse_engineering repo.
Falls back to a basic librosa-based analysis if the full repo is unavailable.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Path to the Track_reverse_engineering repo
_TRACK_RE_REPO = Path(__file__).resolve().parents[2] / "Track_reverse_engineering" / "CascadeProjects" / "windsurf-project"


def _try_import_wav_reverse_engineer():
    """Attempt to import the wav_reverse_engineer module from the sibling repo."""
    module_dir = _TRACK_RE_REPO / "wav_reverse_engineer"
    if not module_dir.is_dir():
        return None

    if str(_TRACK_RE_REPO) not in sys.path:
        sys.path.insert(0, str(_TRACK_RE_REPO))

    try:
        from wav_reverse_engineer.audio_analyzer.audio_processor import AudioProcessor
        from wav_reverse_engineer.audio_analyzer.feature_extractor import FeatureExtractor
        return {"AudioProcessor": AudioProcessor, "FeatureExtractor": FeatureExtractor}
    except ImportError:
        return None


def _basic_analysis(path: Path) -> Dict[str, Any]:
    """Fallback basic analysis using librosa directly."""
    try:
        import librosa
        import numpy as np
    except ImportError:
        raise RuntimeError("librosa is required. Install with: pip install librosa numpy")

    y, sr = librosa.load(str(path), sr=22050, mono=True)
    duration = librosa.get_duration(y=y, sr=sr)

    # BPM
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)

    # Key
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    chroma_mean = np.mean(chroma, axis=1)
    key_idx = int(np.argmax(chroma_mean))
    keys = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

    # Spectral features
    spectral_centroid = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)))
    spectral_bandwidth = float(np.mean(librosa.feature.spectral_bandwidth(y=y, sr=sr)))

    # Harmonic/percussive ratio
    y_harm, y_perc = librosa.effects.hpss(y)
    harm_energy = float(np.mean(y_harm ** 2))
    perc_energy = float(np.mean(y_perc ** 2))
    harmonic_ratio = harm_energy / (harm_energy + perc_energy + 1e-10)

    return {
        "file": str(path),
        "duration_seconds": round(duration, 2),
        "sample_rate": sr,
        "bpm": round(float(tempo), 2),
        "beat_count": len(beat_frames),
        "key": keys[key_idx],
        "mode": "major" if chroma_mean[key_idx] > 0.5 else "minor",
        "spectral_centroid": round(spectral_centroid, 2),
        "spectral_bandwidth": round(spectral_bandwidth, 2),
        "harmonic_ratio": round(harmonic_ratio, 4),
        "analysis_backend": "basic_librosa",
    }


def analyze_track(
    path: Path,
    export_json: bool = False,
    output_dir: Optional[Path] = None,
    effects: bool = False,
    instruments: bool = False,
) -> Dict[str, Any]:
    """Analyze a track for structure, key, BPM, and other musical features.

    Uses the full wav_reverse_engineer module if available, otherwise
    falls back to basic librosa analysis.

    Args:
        path: Path to audio file.
        export_json: If True, export results to JSON.
        output_dir: Directory for JSON output (default: same as audio file).
        effects: Run effects analysis (full module only).
        instruments: Run instrument recognition (full module only).

    Returns:
        Dict with analysis results.
    """
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {path}")

    modules = _try_import_wav_reverse_engineer()

    if modules:
        # Use full wav_reverse_engineer
        AudioProcessor = modules["AudioProcessor"]
        FeatureExtractor = modules["FeatureExtractor"]

        processor = AudioProcessor()
        audio, sr = processor.load_audio(str(path))
        audio_info = processor.get_audio_info(audio, sr)

        extractor = FeatureExtractor()
        features = extractor.extract_features(audio, sr)

        # Detect chords
        chords = extractor.detect_chords(audio, sr)
        chord_progression = FeatureExtractor.summarize_chord_progression(chords)

        result = {
            "file": str(path),
            "duration_seconds": round(audio_info.get("duration_seconds", 0), 2),
            "sample_rate": audio_info.get("sample_rate"),
            "bpm": round(features.get("tempo", 0), 2),
            "key": features.get("key"),
            "mode": features.get("mode"),
            "harmonic_ratio": round(features.get("harmonic_ratio", 0), 4),
            "spectral_centroid": round(features.get("spectral_centroid", 0), 2),
            "chord_progression": chord_progression[:10],  # Top 10 chords
            "analysis_backend": "wav_reverse_engineer",
        }

        # Optional: effects and instruments analysis
        if effects:
            try:
                from wav_reverse_engineer.audio_analyzer.effects_analyzer import analyze_effects
                result["effects"] = analyze_effects(audio, sr)
            except Exception:
                pass

        if instruments:
            try:
                from wav_reverse_engineer.audio_analyzer.instrument_recognizer import InstrumentRecognizer
                recognizer = InstrumentRecognizer()
                result["instruments"] = recognizer.recognize(audio, sr)
            except Exception:
                pass
    else:
        # Fallback to basic analysis
        result = _basic_analysis(path)

    # Export JSON if requested
    if export_json:
        if output_dir is None:
            output_dir = path.parent
        output_dir.mkdir(parents=True, exist_ok=True)
        json_path = output_dir / f"{path.stem}_analysis.json"
        with json_path.open("w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print(f"Analysis saved to {json_path}")

    return result


def print_summary(result: Dict[str, Any]) -> None:
    """Print a human-readable summary of analysis results."""
    print("\n=== Track Analysis Summary ===")
    print(f"File: {result.get('file')}")
    print(f"Duration: {result.get('duration_seconds')}s")
    print(f"BPM: {result.get('bpm')}")
    print(f"Key: {result.get('key')} {result.get('mode')}")
    print(f"Harmonic Ratio: {result.get('harmonic_ratio')}")
    print(f"Backend: {result.get('analysis_backend')}")

    if result.get("chord_progression"):
        print("\nChord Progression:")
        for chord in result["chord_progression"][:5]:
            print(f"  {chord.get('name')} @ {chord.get('start_time'):.2f}s")

    if result.get("effects"):
        print(f"\nEffects: {result['effects']}")

    if result.get("instruments"):
        print(f"Instruments: {result['instruments']}")
