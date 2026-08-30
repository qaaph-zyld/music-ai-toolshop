"""Audio feature extraction for music video generation.

Extracts librosa features (beats, onsets, RMS envelope, spectral centroid,
chroma, sections) into a sidecar JSON for downstream visual synthesis.
"""

from __future__ import annotations

import json
from pathlib import Path
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

from . import key_detection

try:
    import librosa
    import numpy as np

    _HAS_LIBROSA = True
except ImportError:
    _HAS_LIBROSA = False

_KEYS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

STYLE_PRESETS = {
    "default": {"font": "Arial", "size": 48, "primary": "&H00FFFFFF", "outline": "&H00000000"},
    "neon": {"font": "Consolas", "size": 52, "primary": "&H00FF00FF", "outline": "&H00FF00FF"},
    "minimal": {"font": "Helvetica", "size": 40, "primary": "&H00FFFFFF", "outline": "&H00000000"},
    "bold": {"font": "Impact", "size": 56, "primary": "&H00FFFFFF", "outline": "&H00000000"},
}


def _check_librosa() -> None:
    if not _HAS_LIBROSA:
        raise RuntimeError(
            "librosa is required for audio feature extraction. "
            "Install with: pip install librosa numpy"
        )


def _detect_sections(y: Any, sr: int) -> List[Dict[str, Any]]:
    """Detect structural sections.

    Delegates to `toolshop.structure` (H2-M2, #048). The previous body called
    ``librosa.segment.agglomerative(chroma, k=None)`` - invalid, raises on every
    input - inside a bare ``except Exception: return []``, so it returned an empty
    list for every track ever analysed. The intro/verse/chorus labels below it
    (assigned from ``i % 2``) were unreachable, and would have been fabricated
    anyway.

    Sections now carry a repetition ``segment_class`` derived from the audio
    instead of an invented name.
    """
    from . import structure

    try:
        result = structure.segment_track(y, sr)
    except Exception:
        # Still defensive at the call site, but the failure is no longer invisible:
        # structure.segment_track raises, and its own tests assert it does.
        logger.warning("structure segmentation failed", exc_info=True)
        return []
    return result["segments"]


def _compute_stem_energies(stems_dir: Path, hop_length: int = 512) -> Dict[str, List[float]]:
    """Compute per-stem RMS envelopes from WAV files in stems_dir."""
    if not _HAS_LIBROSA:
        return {}

    energies: Dict[str, List[float]] = {}
    for wav_path in sorted(stems_dir.glob("*.wav")):
        try:
            y, sr = librosa.load(str(wav_path), sr=22050, mono=True)
            rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=hop_length)
            energies[wav_path.stem] = [round(float(v), 6) for v in rms[0, ::50]]
        except Exception:
            continue
    return energies


def extract_features(
    audio_path: Path,
    output_path: Optional[Path] = None,
    stems_dir: Optional[Path] = None,
    hop_length: int = 512,
) -> Dict[str, Any]:
    """Extract audio features for music video generation.

    Args:
        audio_path: Path to audio file (WAV/MP3).
        output_path: If provided, write features JSON to this path.
        stems_dir: If provided, compute per-stem RMS energies from WAVs in this dir.
        hop_length: librosa hop length in samples.

    Returns:
        Dictionary with tempo, beats, onsets, rms_env, spectral_centroid,
        chroma_mean, duration, key, mode, sections, and optionally stem_energies.
    """
    _check_librosa()
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    y, sr = librosa.load(str(audio_path), sr=22050, mono=True)
    duration = float(librosa.get_duration(y=y, sr=sr))

    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    bpm = float(np.atleast_1d(tempo)[0])
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)

    onset_frames = librosa.onset.onset_detect(y=y, sr=sr, units="frames")
    onset_times = librosa.frames_to_time(onset_frames, sr=sr)
    onset_strength = librosa.onset.onset_strength(y=y, sr=sr)

    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=hop_length)
    rms_env = [round(float(v), 6) for v in rms[0, ::50]]

    spec_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
    spec_centroid_env = [round(float(v), 2) for v in spec_centroid[0, ::50]]

    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    chroma_mean = [round(float(v), 4) for v in np.mean(chroma, axis=1)]
    # Krumhansl-Schmuckler (H2-M1, #047) - was the same argmax + `> 0.5` defect.
    # chroma_mean is already a plain list of 12 floats; detect_key_from_chroma
    # does its own asarray. Do NOT wrap it in np.array() here - tests patch this
    # module's `np` wholesale, so that would hand the detector a MagicMock.
    _key_est = key_detection.detect_key_from_chroma(chroma_mean)
    key = _key_est.key
    mode = _key_est.mode

    sections = _detect_sections(y, sr)

    result: Dict[str, Any] = {
        "file": str(audio_path),
        "tempo": round(bpm, 2),
        "key": key,
        "mode": mode,
        "duration": round(duration, 3),
        "sample_rate": sr,
        "beats": [round(float(t), 3) for t in beat_times],
        "onsets": [round(float(t), 3) for t in onset_times],
        "onset_strength": [round(float(v), 4) for v in onset_strength[::50]],
        "rms_env": rms_env,
        "spectral_centroid": spec_centroid_env,
        "chroma_mean": chroma_mean,
        "sections": sections,
    }

    if stems_dir and stems_dir.is_dir():
        result["stem_energies"] = _compute_stem_energies(stems_dir, hop_length)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    return result
