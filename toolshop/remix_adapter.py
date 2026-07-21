"""Sample and remix creation adapter for music-ai-toolshop.

Uses librosa for analysis/beat detection, pedalboard (Rubber Band) for
high-quality time-stretching and pitch-shifting, and soundfile for I/O.

The adapter is intentionally importable without pedalboard installed; the CLI
and doctor will report the missing extra instead of crashing on import.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from . import batch

try:
    import librosa

    _HAS_LIBROSA = True
except ImportError:  # pragma: no cover
    librosa = None  # type: ignore
    _HAS_LIBROSA = False

try:
    import soundfile as sf

    _HAS_SOUNDFILE = True
except ImportError:  # pragma: no cover
    sf = None  # type: ignore
    _HAS_SOUNDFILE = False

try:
    import pedalboard

    _HAS_PEDALBOARD = True
except ImportError:  # pragma: no cover
    pedalboard = None  # type: ignore
    _HAS_PEDALBOARD = False


MAX_DURATION_SECONDS = 240.0

KEYS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

FLAT_TO_SHARP = {
    "Db": "C#",
    "Eb": "D#",
    "Gb": "F#",
    "Ab": "G#",
    "Bb": "A#",
    "Cb": "B",
    "Fb": "E",
}

KEY_PATTERN = re.compile(
    r"^\s*([A-G])(#|b|s|es)?\s*(m|min|minor|maj|major)?\s*$",
    re.IGNORECASE,
)


class MissingDependencyError(RuntimeError):
    """Raised when a required package is missing for the remix pipeline."""


def _require_deps() -> None:
    missing = []
    if not _HAS_LIBROSA:
        missing.append("librosa")
    if not _HAS_SOUNDFILE:
        missing.append("soundfile")
    if not _HAS_PEDALBOARD:
        missing.append("pedalboard")
    if missing:
        raise MissingDependencyError(
            "Remix features require: " + ", ".join(missing) +
            ". Install with: pip install -e '.[remix]'"
        )


def _toolshop_version() -> str:
    """Read version from pyproject.toml or return a fallback."""
    try:
        import tomllib  # Python 3.11+
    except ImportError:  # pragma: no cover
        return "unknown"
    repo_root = Path(__file__).resolve().parent.parent
    pyproject = repo_root / "pyproject.toml"
    if not pyproject.exists():
        return "unknown"
    try:
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        return data.get("project", {}).get("version", "unknown")
    except Exception:  # pragma: no cover
        return "unknown"


def _data_root() -> Path:
    return Path(os.environ.get("TOOLSHOP_DATA_DIR", r"D:\MusicData\toolshop"))


def _file_hash(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.name.encode("utf-8"))
    try:
        h.update(str(path.stat().st_size).encode("utf-8"))
    except Exception:
        pass
    return h.hexdigest()[:16]


def _parse_key(key_str: str) -> Tuple[str, str]:
    """Parse a key string like 'Gm', 'G# minor', 'F#m' -> (key, mode)."""
    if not key_str:
        raise ValueError("Empty key string")
    match = KEY_PATTERN.match(key_str)
    if not match:
        raise ValueError(f"Could not parse key: {key_str!r}")
    letter = match.group(1).upper()
    accidental = match.group(2) or ""
    accidental = accidental.lower()
    if accidental in ("#", "s"):
        key = letter + "#"
    elif accidental in ("b", "es"):
        key = FLAT_TO_SHARP.get(letter + "b", letter)
    else:
        key = letter
    if key not in KEYS:
        raise ValueError(f"Unknown key: {key!r}")
    mode_token = (match.group(3) or "").lower()
    if mode_token in ("m", "min", "minor"):
        mode = "minor"
    else:
        mode = "major"
    return key, mode


def _key_to_semitone(key: str) -> int:
    return KEYS.index(key)


def _semitone_diff(src_key: str, dst_key: str) -> int:
    """Return the minimal signed semitone distance from src to dst key."""
    diff = _key_to_semitone(dst_key) - _key_to_semitone(src_key)
    while diff > 6:
        diff -= 12
    while diff <= -6:
        diff += 12
    return diff


def _load_audio(
    path: Path,
    max_duration: float = MAX_DURATION_SECONDS,
    mono: bool = True,
) -> Tuple[np.ndarray, int, float, bool]:
    """Load audio with a duration cap.

    Returns (audio, sample_rate, duration_seconds, was_truncated).
    """
    _require_deps()
    info = sf.info(str(path))
    total_duration = info.duration
    duration_to_load = min(total_duration, max_duration)
    was_truncated = total_duration > max_duration
    if was_truncated:
        logging.warning(
            "Audio length %.2fs exceeds max_duration %.2fs; truncating to %.2fs.",
            total_duration,
            max_duration,
            duration_to_load,
        )
    audio, sr = librosa.load(
        str(path),
        sr=None,
        mono=mono,
        duration=duration_to_load,
    )
    if audio.ndim == 1 and not mono:
        audio = np.expand_dims(audio, axis=0)
    if audio.ndim == 2 and audio.shape[0] <= 2:
        # librosa returns (channels, samples) when mono=False; convert to (samples, channels)
        audio = audio.T
    return audio, sr, duration_to_load, was_truncated


def _detect_bpm_key(path: Path) -> Tuple[float, str, str]:
    """Reuse the existing bpm_adapter for source BPM/key."""
    from . import bpm_adapter

    result = bpm_adapter.analyze_track(path)
    bpm = float(result.get("bpm", 120.0))
    if bpm <= 0:
        bpm = 120.0
    return bpm, result.get("key", "C"), result.get("mode", "major")


def _detect_beats(audio: np.ndarray, sr: int) -> Tuple[float, np.ndarray]:
    """Return (bpm, beat_samples) for the audio."""
    _require_deps()
    tempo, beat_frames = librosa.beat.beat_track(y=audio, sr=sr)
    if hasattr(tempo, "item"):
        tempo = tempo.item()
    bpm = float(tempo)
    beat_samples = librosa.frames_to_samples(beat_frames)
    return bpm, beat_samples


def _slice_by_beats(
    audio: np.ndarray,
    beat_samples: np.ndarray,
    segment_beats: int = 4,
) -> List[Tuple[np.ndarray, int, int, int]]:
    """Slice audio into groups of `segment_beats` beats.

    Returns a list of (segment_audio, start_sample, end_sample, beat_count).
    """
    if len(beat_samples) < 2:
        return [(audio, 0, len(audio), 1)]
    segments: List[Tuple[np.ndarray, int, int, int]] = []
    for i in range(0, len(beat_samples), segment_beats):
        start = int(beat_samples[i])
        end_idx = i + segment_beats
        if end_idx < len(beat_samples):
            end = int(beat_samples[end_idx])
            beat_count = segment_beats
        else:
            end = len(audio)
            beat_count = len(beat_samples) - i
        if end > start:
            segments.append((audio[start:end], start, end, beat_count))
    return segments


def _slice_by_onsets(audio: np.ndarray, sr: int) -> List[Tuple[np.ndarray, int, int]]:
    """Slice audio at onset boundaries.

    Returns a list of (segment_audio, start_sample, end_sample).
    """
    _require_deps()
    onset_frames = librosa.onset.onset_detect(
        y=audio,
        sr=sr,
        wait=3,
        pre_max=3,
        post_max=3,
        pre_avg=3,
        post_avg=5,
    )
    onset_samples = librosa.frames_to_samples(onset_frames)
    if len(onset_samples) < 2:
        return [(audio, 0, len(audio))]
    segments = []
    for i, start in enumerate(onset_samples):
        end = int(onset_samples[i + 1]) if i + 1 < len(onset_samples) else len(audio)
        if end > start:
            segments.append((audio[start:end], start, end))
    return segments


def _load_sections(path: Path) -> List[Dict[str, Any]]:
    """Load section boundaries from a JSON file.

    Accepts ``sections`` at top level or nested under ``structure.sections``.
    Each entry must have ``label`` (str), ``start`` (float), ``end`` (float).
    Invalid entries are skipped with a warning.

    Returns a list of dicts sorted by ``start``.
    Raises ``ValueError`` if no valid sections are found.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    raw_sections = data.get("sections")
    if raw_sections is None:
        structure = data.get("structure")
        if isinstance(structure, dict):
            raw_sections = structure.get("sections")
    if raw_sections is None:
        raise ValueError(f"No 'sections' key found in {path}")

    cleaned: List[Dict[str, Any]] = []
    for i, entry in enumerate(raw_sections):
        try:
            label = str(entry["label"])
            start = float(entry["start"])
            end = float(entry["end"])
        except (KeyError, TypeError, ValueError):
            logging.warning("Skipping invalid section #%d in %s: %r", i, path, entry)
            continue
        if end <= start:
            logging.warning(
                "Skipping section #%d (%r): end <= start (%.3f <= %.3f)",
                i, label, end, start,
            )
            continue
        cleaned.append({"label": label, "start": start, "end": end})

    if not cleaned:
        raise ValueError(f"No valid sections in {path}")

    cleaned.sort(key=lambda s: s["start"])
    return cleaned


def _snap_to_nearest_beat(sample: int, beat_samples: np.ndarray) -> int:
    """Snap a sample index to the nearest value in *beat_samples*."""
    if beat_samples is None or len(beat_samples) == 0:
        return sample
    diffs = np.abs(beat_samples - sample)
    return int(beat_samples[int(np.argmin(diffs))])


def _slice_by_sections(
    audio: np.ndarray,
    sr: int,
    sections: List[Dict[str, Any]],
    beat_samples: Optional[np.ndarray] = None,
    snap_to_beats: bool = True,
    sub_slice_beats: Optional[int] = None,
) -> List[Tuple[np.ndarray, int, int, str, int]]:
    """Slice audio by section boundaries.

    Returns a list of ``(segment, start_sample, end_sample, label, n_within_section)``.
    """
    total = len(audio)
    result: List[Tuple[np.ndarray, int, int, str, int]] = []

    for section in sections:
        start_s = int(section["start"] * sr)
        end_s = int(section["end"] * sr)
        start_s = max(0, min(start_s, total))
        end_s = max(0, min(end_s, total))
        label = section["label"]

        if snap_to_beats and beat_samples is not None and len(beat_samples):
            start_s = _snap_to_nearest_beat(start_s, beat_samples)
            end_s = _snap_to_nearest_beat(end_s, beat_samples)

        if end_s <= start_s:
            continue

        if sub_slice_beats and beat_samples is not None and len(beat_samples):
            beats_inside = [
                int(b) for b in beat_samples
                if start_s <= int(b) < end_s
            ]
            if not beats_inside:
                result.append((audio[start_s:end_s], start_s, end_s, label, 1))
                continue

            cut_points = [start_s]
            for i, b in enumerate(beats_inside):
                if (i + 1) % sub_slice_beats == 0:
                    cut_points.append(b)
            if cut_points[-1] != end_s:
                cut_points.append(end_s)

            n = 1
            for i in range(len(cut_points) - 1):
                seg_start = cut_points[i]
                seg_end = cut_points[i + 1]
                if seg_end <= seg_start:
                    continue
                result.append((audio[seg_start:seg_end], seg_start, seg_end, label, n))
                n += 1
        else:
            result.append((audio[start_s:end_s], start_s, end_s, label, 1))

    return result


def _stretch_segment(
    segment: np.ndarray,
    sr: int,
    src_bpm: float,
    dst_bpm: Optional[float],
    src_key: str,
    dst_key: Optional[str],
    **stretch_kwargs: Any,
) -> np.ndarray:
    """Apply tempo and/or key matching to one audio segment."""
    _require_deps()
    if segment.dtype != np.float32:
        segment = segment.astype(np.float32)
    was_1d = segment.ndim == 1
    stretch_factor = 1.0
    if dst_bpm and src_bpm and src_bpm > 0:
        stretch_factor = dst_bpm / src_bpm
    pitch_shift = 0.0
    if dst_key:
        pitch_shift = float(_semitone_diff(src_key, dst_key))
    if abs(stretch_factor - 1.0) < 1e-6 and abs(pitch_shift) < 1e-6:
        return segment
    out = pedalboard.time_stretch(
        segment,
        sr,
        stretch_factor=float(stretch_factor),
        pitch_shift_in_semitones=float(pitch_shift),
        **stretch_kwargs,
    )
    # pedalboard.time_stretch returns (channels, samples) for 1-D input.
    if was_1d and out.ndim > 1:
        out = np.ascontiguousarray(out).reshape(-1)
    return out


def _build_fx_board(fx_chain: List[str], sr: int) -> "pedalboard.Pedalboard":
    """Build a simple pedalboard from a list of FX names."""
    _require_deps()
    plugins: List[Any] = []
    for fx in fx_chain:
        name = fx.lower().strip()
        if name == "reverb":
            plugins.append(
                pedalboard.Reverb(
                    room_size=0.6,
                    damping=0.5,
                    wet_level=0.25,
                    dry_level=0.75,
                )
            )
        elif name == "delay":
            plugins.append(
                pedalboard.Delay(
                    delay_seconds=0.375,
                    feedback=0.25,
                    mix=0.3,
                )
            )
        elif name == "gain":
            plugins.append(pedalboard.Gain(gain_db=6.0))
        elif name == "compressor":
            plugins.append(
                pedalboard.Compressor(
                    threshold_db=-18.0,
                    ratio=4.0,
                    attack_ms=5.0,
                    release_ms=50.0,
                )
            )
        elif name == "distortion":
            plugins.append(pedalboard.Distortion(drive_db=6.0))
        else:
            logging.warning("Unknown FX '%s'; skipping.", fx)
    return pedalboard.Pedalboard(plugins)


def _apply_fx(audio: np.ndarray, sr: int, fx_chain: Optional[List[str]]) -> np.ndarray:
    if not fx_chain:
        return audio
    _require_deps()
    board = _build_fx_board(fx_chain, sr)
    if len(board) == 0:
        return audio
    return board(audio, sr)


def _crossfade_concat(
    segments: List[np.ndarray],
    sr: int,
    crossfade_ms: float = 12.0,
) -> np.ndarray:
    """Concatenate segments with short linear crossfades."""
    if not segments:
        return np.array([], dtype=np.float32)
    if len(segments) == 1:
        return segments[0]
    crossfade_samples = int(sr * crossfade_ms / 1000.0)
    out = segments[0]
    for next_seg in segments[1:]:
        if crossfade_samples >= len(out) or crossfade_samples >= len(next_seg):
            out = np.concatenate([out, next_seg])
            continue
        fade_out = np.linspace(1.0, 0.0, crossfade_samples, dtype=np.float32)
        fade_in = np.linspace(0.0, 1.0, crossfade_samples, dtype=np.float32)
        # Ensure same dimensionality
        if out.ndim == 1 and next_seg.ndim == 1:
            tail = out[-crossfade_samples:] * fade_out
            head = next_seg[:crossfade_samples] * fade_in
            out = np.concatenate([
                out[:-crossfade_samples],
                tail + head,
                next_seg[crossfade_samples:],
            ])
        else:
            # For multichannel, apply per-channel
            tail = out[-crossfade_samples:] * fade_out.reshape(-1, 1)
            head = next_seg[:crossfade_samples] * fade_in.reshape(-1, 1)
            out = np.concatenate([
                out[:-crossfade_samples],
                tail + head,
                next_seg[crossfade_samples:],
            ], axis=0)
    return out


def _resolve_input_path(
    input_path: Path,
    stems_dir: Optional[Path] = None,
    stem_name: Optional[str] = None,
) -> Path:
    if stems_dir is None:
        return input_path
    manifest = stems_dir / "manifest.json"
    if not manifest.exists():
        logging.warning("Stems manifest not found at %s; using original input.", stems_dir)
        return input_path
    data = json.loads(manifest.read_text(encoding="utf-8"))
    stems = data.get("stems", {})
    if stem_name and stem_name in stems:
        return Path(stems[stem_name])
    for fallback in ["instrumental", "main_vocals", "vocals", "drums"]:
        if fallback in stems:
            return Path(stems[fallback])
    if stems:
        return Path(next(iter(stems.values())))
    return input_path


def _write_manifest(path: Path, manifest: Dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
    return path


@dataclass
class RemixResult:
    output_file: Path
    source: Path
    source_hash: str
    bpm: float
    key: str
    mode: str
    target_bpm: Optional[float]
    target_key: Optional[str]
    fx_chain: Optional[List[str]]
    duration_seconds: float
    output_format: str
    truncated: bool = False
    manifest_path: Optional[Path] = None
    samples: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def create_remix(
    input_path: Path,
    output_path: Path,
    *,
    target_bpm: Optional[float] = None,
    target_key: Optional[str] = None,
    mode: str = "remix",
    segment_beats: int = 4,
    fx_chain: Optional[List[str]] = None,
    max_duration: float = MAX_DURATION_SECONDS,
    source_bpm: Optional[float] = None,
    source_key: Optional[str] = None,
    output_format: str = "wav",
    stems_dir: Optional[Path] = None,
    stem_name: Optional[str] = None,
    crossfade_ms: float = 12.0,
    sections: Optional[List[Dict[str, Any]]] = None,
    sub_slice_beats: Optional[int] = None,
    snap_to_beats: bool = True,
    **stretch_kwargs: Any,
) -> RemixResult:
    """Create a remix or sample pack from an audio file.

    Args:
        input_path: Path to source audio.
        output_path: File path for remix mode; directory for sample mode.
        target_bpm: Optional target BPM.
        target_key: Optional target key string (e.g. 'Gm', 'A# major').
        mode: 'remix' or 'sample'.
        segment_beats: Number of beats per segment in remix/loop-kit mode.
        fx_chain: Optional list of FX names ('reverb', 'delay', etc.).
        max_duration: Maximum seconds to load from the input.
        source_bpm: Optional known source BPM; otherwise auto-detected.
        source_key: Optional known source key; otherwise auto-detected.
        output_format: 'wav' or 'flac'.
        stems_dir: Optional existing `toolshop stems` output directory.
        stem_name: Specific stem to use from `stems_dir`.
        crossfade_ms: Crossfade length between segments in remix mode.

    Returns:
        RemixResult with output metadata.
    """
    _require_deps()
    if not input_path.exists():
        raise FileNotFoundError(f"Audio file not found: {input_path}")

    resolved_input = _resolve_input_path(input_path, stems_dir, stem_name)
    if not resolved_input.exists():
        raise FileNotFoundError(f"Resolved input not found: {resolved_input}")

    source_hash = _file_hash(resolved_input)

    if source_bpm is None or source_key is None:
        detected_bpm, detected_key, detected_mode = _detect_bpm_key(resolved_input)
    else:
        detected_bpm, detected_key, detected_mode = source_bpm, source_key, "major"
    src_bpm = source_bpm if source_bpm is not None else detected_bpm
    if source_key is None:
        src_key = detected_key
        _ = detected_mode  # not used for pitch shift; root is enough for now
    else:
        src_key, _ = _parse_key(source_key)

    # Load audio. Use stereo for sample mode to preserve width; mono for remix
    # to keep CPU cost low and mixing simple.
    mono = mode == "remix"
    audio, sr, duration, truncated = _load_audio(
        resolved_input, max_duration=max_duration, mono=mono
    )

    target_key_letter: Optional[str] = None
    if target_key:
        target_key_letter, _ = _parse_key(target_key)

    if audio.dtype != np.float32:
        audio = audio.astype(np.float32)

    if mode == "remix":
        detected_bpm, beat_samples = _detect_beats(audio, sr)
        if src_bpm is None or src_bpm <= 0:
            src_bpm = detected_bpm
        segments = _slice_by_beats(audio, beat_samples, segment_beats=segment_beats)
        processed = []
        for seg, _start, _end, _beats in segments:
            seg = _stretch_segment(
                seg,
                sr,
                src_bpm=src_bpm,
                dst_bpm=target_bpm,
                src_key=src_key,
                dst_key=target_key_letter,
                **stretch_kwargs,
            )
            processed.append(seg)
        final = _crossfade_concat(processed, sr, crossfade_ms=crossfade_ms)
        final = _apply_fx(final, sr, fx_chain)  # apply overall FX once more
    elif mode == "sample":
        if sections is not None:
            beat_audio = audio if audio.ndim == 1 else np.mean(audio, axis=0)
            detected_bpm, beat_samples = _detect_beats(beat_audio, sr)
            if src_bpm is None or src_bpm <= 0:
                src_bpm = detected_bpm
            raw_segments = _slice_by_sections(
                audio, sr, sections,
                beat_samples=beat_samples,
                snap_to_beats=snap_to_beats,
                sub_slice_beats=sub_slice_beats,
            )
        elif segment_beats <= 1:
            raw_segments = _slice_by_onsets(audio, sr)
        else:
            detected_bpm, beat_samples = _detect_beats(audio, sr)
            if src_bpm is None or src_bpm <= 0:
                src_bpm = detected_bpm
            raw_segments = _slice_by_beats(
                audio, beat_samples, segment_beats=segment_beats
            )
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        samples: List[Dict[str, Any]] = []
        label_counters: Dict[str, int] = {}
        for seg_info in raw_segments:
            if sections is not None:
                seg, start, end, label, n_within = seg_info
                beats = None
            elif segment_beats <= 1:
                seg, start, end = seg_info
                label = "oneshot"
                beats = 1
            else:
                seg, start, end, beats = seg_info
                label = "loop"
            seg = _stretch_segment(
                seg,
                sr,
                src_bpm=src_bpm,
                dst_bpm=target_bpm,
                src_key=src_key,
                dst_key=target_key_letter,
                **stretch_kwargs,
            )
            seg = _apply_fx(seg, sr, fx_chain)
            start_time = float(start) / sr
            end_time = float(end) / sr
            if sections is not None:
                n_val = n_within
            else:
                label_counters[label] = label_counters.get(label, 0) + 1
                n_val = label_counters[label]
            name = _sample_name(
                src_key,
                src_bpm,
                label,
                n_val,
                output_format,
            )
            file_path = output_dir / name
            sf.write(str(file_path), seg, sr)
            samples.append(
                {
                    "file": str(file_path),
                    "name": name,
                    "section": label,
                    "start_seconds": round(start_time, 3),
                    "end_seconds": round(end_time, 3),
                    "source_bpm": round(src_bpm, 2),
                    "source_key": src_key,
                    "beats": beats if (segment_beats > 1 and sections is None) else None,
                }
            )
        manifest = _sample_manifest(
            resolved_input,
            source_hash,
            samples,
            output_format,
        )
        manifest_path = output_dir / "manifest.json"
        _write_manifest(manifest_path, manifest)
        return RemixResult(
            output_file=output_dir,
            source=resolved_input,
            source_hash=source_hash,
            bpm=src_bpm,
            key=src_key,
            mode="major",
            target_bpm=target_bpm,
            target_key=target_key,
            fx_chain=fx_chain,
            duration_seconds=duration,
            output_format=output_format,
            truncated=truncated,
            manifest_path=manifest_path,
            samples=samples,
        )
    else:
        raise ValueError(f"Unknown mode: {mode!r}; use 'remix' or 'sample'.")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(output_path), final, sr)

    manifest = _remix_manifest(
        resolved_input,
        source_hash,
        src_bpm,
        src_key,
        target_bpm,
        target_key,
        fx_chain,
        duration,
        output_format,
        output_path,
        truncated,
    )
    manifest_path = output_path.parent / f"{output_path.stem}_manifest.json"
    _write_manifest(manifest_path, manifest)

    return RemixResult(
        output_file=output_path,
        source=resolved_input,
        source_hash=source_hash,
        bpm=src_bpm,
        key=src_key,
        mode="major",
        target_bpm=target_bpm,
        target_key=target_key,
        fx_chain=fx_chain,
        duration_seconds=duration,
        output_format=output_format,
        truncated=truncated,
        manifest_path=manifest_path,
    )


def _sample_name(
    key: str,
    bpm: float,
    section: str,
    n: int,
    output_format: str,
) -> str:
    ext = ".wav" if output_format.lower() == "wav" else ".flac"
    safe_key = key.replace("#", "sh").replace("b", "f")
    safe_section = re.sub(r"[^a-z0-9]+", "", section.lower()) or "loop"
    return f"{safe_key}_{int(round(bpm))}_{safe_section}_{n:02d}{ext}"


def _remix_manifest(
    source: Path,
    source_hash: str,
    src_bpm: float,
    src_key: str,
    target_bpm: Optional[float],
    target_key: Optional[str],
    fx_chain: Optional[List[str]],
    duration: float,
    output_format: str,
    output_file: Path,
    truncated: bool,
) -> Dict[str, Any]:
    return {
        "version": _toolshop_version(),
        "created": datetime.now().isoformat(),
        "mode": "remix",
        "source": str(source),
        "source_hash": source_hash,
        "source_bpm": round(src_bpm, 2),
        "source_key": src_key,
        "target_bpm": round(target_bpm, 2) if target_bpm else None,
        "target_key": target_key,
        "fx_chain": fx_chain or [],
        "duration_seconds": round(duration, 2),
        "truncated": truncated,
        "output_format": output_format,
        "output_file": str(output_file),
    }


def _sample_manifest(
    source: Path,
    source_hash: str,
    samples: List[Dict[str, Any]],
    output_format: str,
) -> Dict[str, Any]:
    return {
        "version": _toolshop_version(),
        "created": datetime.now().isoformat(),
        "mode": "sample",
        "source": str(source),
        "source_hash": source_hash,
        "output_format": output_format,
        "sample_count": len(samples),
        "samples": samples,
    }
