"""Track reverse engineering adapter.

Wraps the external wav_reverse_engineer analyzer when available, and falls back
to pure librosa-based analysis otherwise.
"""

from __future__ import annotations

import json
import logging
import warnings
from pathlib import Path
from typing import Any, Dict, Optional

#: `_basic_analysis` guards beat-grid, structure and premaster behind `except`
#: handlers that log and fall back. Every one of those handlers referenced an
#: undefined `logger` and so raised `NameError` instead of degrading - turning a
#: recoverable stage failure into a crash, in exactly the three field-groups M6
#: depends on. The two tests that touch `_basic_analysis` mock it out entirely,
#: so the body had never run. See JOURNAL.md J-006.
logger = logging.getLogger(__name__)

from . import beatgrid
from . import key_detection
from . import premaster
from . import structure

try:
    from wav_reverse_engineer.audio_analyzer.audio_processor import AudioProcessor
    from wav_reverse_engineer.audio_analyzer.feature_extractor import FeatureExtractor
    _WAV_RE_AVAILABLE = True
except Exception as _import_exc:
    AudioProcessor = None
    FeatureExtractor = None
    _WAV_RE_AVAILABLE = False
    _WAV_RE_IMPORT_ERROR = str(_import_exc)

try:
    from wav_reverse_engineer.audio_analyzer.effects_analyzer import analyze_effects
except Exception:
    analyze_effects = None

try:
    from wav_reverse_engineer.audio_analyzer.instrument_recognizer import InstrumentRecognizer
except Exception:
    InstrumentRecognizer = None

try:
    from wav_reverse_engineer.audio_analyzer.source_separation import separate_hpss
except Exception:
    separate_hpss = None


def _to_scalar(x):
    """Convert a numpy scalar/array or Python scalar to a plain Python scalar."""
    if hasattr(x, "item"):
        x = x.item()
    return x


def _basic_analysis(path: Path) -> Dict[str, Any]:
    """Fallback basic analysis using librosa directly."""
    try:
        import librosa
        import numpy as np
    except ImportError:
        raise RuntimeError(
            "librosa is required. Install with: pip install librosa numpy"
        )

    y, sr = librosa.load(str(path), sr=22050, mono=True)
    duration = librosa.get_duration(y=y, sr=sr)

    # BPM + beat grid (H2-M3, #049). This used to call beat_track and keep only
    # the COUNT, discarding the grid itself - the thing Sample Forge, the E5
    # universal pack and any DAW click actually need.
    try:
        grid = beatgrid.analyze_beats(y, sr)
        beat_result = grid.to_dict()
        tempo = grid.tempo
        beat_count = len(grid.beat_times)
    except Exception:
        logger.warning("beat grid analysis failed for %s", path, exc_info=True)
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        tempo = _to_scalar(tempo)
        beat_count = len(beat_frames) if hasattr(beat_frames, "__len__") else int(_to_scalar(beat_frames))
        beat_result = None

    # Key: Krumhansl-Schmuckler (H2-M1, #047). This is the dossier path, so the
    # old argmax-tonic + `chroma_mean[key] > 0.5` mode went straight into
    # dossier.json - "major" for 7 of 8 measured tracks. See toolshop/key_detection.py.
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    chroma_mean = np.mean(chroma, axis=1)
    key_estimate = key_detection.detect_key_from_chroma(chroma_mean)

    # Spectral features
    spectral_centroid = float(_to_scalar(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))))
    spectral_bandwidth = float(_to_scalar(np.mean(librosa.feature.spectral_bandwidth(y=y, sr=sr))))

    # Structure (H2-M2, #048). T7 Sample Forge's automatic sectioning was deferred
    # in #018 as "dossier emits none yet" - because the only segmenter in the repo
    # raised on every call and returned []. It emits sections now.
    try:
        structure_result = structure.segment_track(y, sr)
    except Exception:
        logger.warning("structure segmentation failed for %s", path, exc_info=True)
        structure_result = None

    # Premaster acceptance profile (H2-M4, #050). Graded against
    # mastering_tool/PREMASTER_ACCEPTANCE_SPEC.md. Reads the file directly rather
    # than reusing `y`: gates 1-2 are phase coherence and need the stereo pair,
    # which the mono load above has already summed away.
    try:
        premaster_result = premaster.analyze_premaster(path)
    except Exception:
        logger.warning("premaster profile failed for %s", path, exc_info=True)
        premaster_result = None

    # Harmonic/percussive ratio
    y_harm, y_perc = librosa.effects.hpss(y)
    harm_energy = float(_to_scalar(np.mean(y_harm**2)))
    perc_energy = float(_to_scalar(np.mean(y_perc**2)))
    harmonic_ratio = harm_energy / (harm_energy + perc_energy + 1e-10)

    return {
        "file": str(path),
        "duration_seconds": round(duration, 2),
        "sample_rate": sr,
        "bpm": round(float(tempo), 2),
        "beat_count": beat_count,
        "beat_grid": beat_result,
        "key": key_estimate.key,
        "mode": key_estimate.mode,
        "key_confidence": round(key_estimate.confidence, 4),
        "key_alternate": f"{key_estimate.alternate_key} {key_estimate.alternate_mode}",
        "key_margin": round(key_estimate.margin, 4),
        "spectral_centroid": round(spectral_centroid, 2),
        "spectral_bandwidth": round(spectral_bandwidth, 2),
        "harmonic_ratio": round(harmonic_ratio, 4),
        "structure": structure_result,
        "premaster": premaster_result,
        "analysis_backend": "basic_librosa",
    }


def _advanced_analysis(
    path: Path,
    effects: bool = False,
    instruments: bool = False,
    chords: bool = False,
    notes: bool = False,
    separation: Optional[str] = None,
) -> Dict[str, Any]:
    """Analyze a track using the external wav_reverse_engineer package."""
    if AudioProcessor is None or FeatureExtractor is None:
        raise RuntimeError("wav_reverse_engineer is not available")

    audio, sr = AudioProcessor.load_audio(str(path), target_sr=22050, mono=True)
    features = FeatureExtractor.extract_features(audio, sr)

    result: Dict[str, Any] = {
        "file": str(path),
        "duration_seconds": round(float(features["duration"]), 2),
        "sample_rate": sr,
        "bpm": round(float(features["tempo"]), 2),
        "beat_count": int(features["beat_count"]),
        "key": features["key"],
        "mode": features["mode"],
        "spectral_centroid": round(float(features["spectral_centroid"]), 2),
        "spectral_bandwidth": round(float(features["spectral_bandwidth"]), 2),
        "harmonic_ratio": round(float(features["harmonic_ratio"]), 4),
        "tuning_offset": float(features.get("tuning_offset", 0.0)),
        "onset_strength": round(float(features.get("onset_strength", 0.0)), 4),
        "analysis_backend": "wav_reverse_engineer",
    }

    if effects and analyze_effects is not None:
        try:
            result["effects"] = analyze_effects(audio, sr)
        except Exception as exc:
            result["effects_error"] = str(exc)

    if instruments and InstrumentRecognizer is not None:
        try:
            recognizer = InstrumentRecognizer()
            result["instruments"] = recognizer.recognize(audio, sr)
        except Exception as exc:
            result["instruments_error"] = str(exc)

    if chords:
        try:
            chord_list = FeatureExtractor.detect_chords(audio, sr)
            result["chord_progression"] = FeatureExtractor.summarize_chord_progression(chord_list)
        except Exception as exc:
            result["chords_error"] = str(exc)

    if notes:
        try:
            result["notes"] = FeatureExtractor.detect_notes(audio, sr)
        except Exception as exc:
            result["notes_error"] = str(exc)

    if separation:
        separation = separation.lower()
        if separation == "hpss" and separate_hpss is not None:
            try:
                stems = separate_hpss(audio)
                result["separation"] = {
                    "method": "hpss",
                    "stems": list(stems.keys()),
                }
            except Exception as exc:
                result["separation_error"] = str(exc)
        else:
            result["separation_error"] = (
                f"Separation backend '{separation}' is not available in this integration"
            )

    return result


def analyze_track(
    path: Path,
    export_json: bool = False,
    output_dir: Optional[Path] = None,
    effects: bool = False,
    instruments: bool = False,
    chords: bool = False,
    notes: bool = False,
    separation: Optional[str] = None,
    backend: str = "advanced",
) -> Dict[str, Any]:
    """Analyze a track for structure, key, BPM, and other musical features.

    Uses the external wav_reverse_engineer analyzer when available, otherwise
    falls back to pure librosa analysis.

    Args:
        path: Path to audio file.
        export_json: If True, export results to JSON.
        output_dir: Directory for JSON output (default: same as audio file).
        effects: Run effects analysis.
        instruments: Run instrument recognition.
        chords: Run chord detection.
        notes: Run note transcription.
        separation: Source separation backend (hpss).
        backend: 'advanced' to use wav_reverse_engineer, 'basic' for librosa only.

    Returns:
        Dict with analysis results.
    """
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {path}")

    use_advanced = _WAV_RE_AVAILABLE and backend != "basic"
    if use_advanced:
        try:
            result = _advanced_analysis(
                path=path,
                effects=effects,
                instruments=instruments,
                chords=chords,
                notes=notes,
                separation=separation,
            )
        except Exception as exc:
            warnings.warn(f"Advanced analysis failed ({exc}); falling back to basic librosa.")
            result = _basic_analysis(path)
    else:
        result = _basic_analysis(path)

    # Export JSON if requested
    if export_json:
        if output_dir is None:
            output_dir = path.parent
        output_dir.mkdir(parents=True, exist_ok=True)
        json_path = output_dir / f"{path.stem}_analysis.json"
        with json_path.open("w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, default=str)
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

    if result.get("tuning_offset"):
        print(f"Tuning offset: {result['tuning_offset']}")

    if result.get("chord_progression"):
        print("\nChord Progression:")
        for chord in result["chord_progression"][:5]:
            print(f"  {chord.get('name')} @ {chord.get('start_time'):.2f}s")

    if result.get("notes"):
        print(f"\nNotes detected: {len(result['notes'])}")

    if result.get("effects"):
        print("\nEffects:")
        for key, value in result["effects"].items():
            print(f"  {key}: {value}")

    if result.get("instruments"):
        print("\nInstruments:")
        for item in result["instruments"][:5]:
            print(f"  {item.get('label')}: {item.get('score')}")

    if result.get("separation"):
        print(f"\nSeparation: {result['separation']}")
