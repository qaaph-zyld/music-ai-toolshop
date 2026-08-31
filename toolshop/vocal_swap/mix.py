"""Sum an aligned vocal over an instrumental at a defensible level.

**Gain staging is done in LUFS, not peaks.** Peak-matching two sources says
nothing about how loud they *sound* together: a compressed rap vocal and a
sparse instrumental can share a peak level and be 6 dB apart perceptually. So
both are measured with an ITU-R BS.1770 integrated loudness meter and the vocal
is placed a stated number of dB relative to the instrumental.

**The bus is levelled in LUFS too, under a peak ceiling.** It used to be peak
normalised, which handed the mastering chain wildly different loudnesses for the
same peak and made it undershoot its target on sparse mixes - see
`DEFAULT_BUS_LUFS` for the three masters that showed it. There is still no bus
compression or limiting: the next stage is a real mastering chain that expects
headroom and an intact crest factor, and anything done here to make the premaster
sound "finished" is work the limiter then has to fight - and would fail the M4
gates on crest factor and PSR, which is exactly what those gates are for.

Default balance is a **starting point, not a mastered decision** - the same
caveat `family_policy.sh` attaches to its genre presets.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

#: Working sample rate for the mix. 44.1k because the mastering chain and every
#: deliverable downstream are 44.1k; resampling once here beats resampling twice.
MIX_SR = 44100

#: Vocal loudness relative to the instrumental, in LU. +1.5 sits the vocal just
#: forward of the beat, which is the rap convention. STARTING POINT - bracket it
#: per track, exactly as the mastering profiles instruct.
DEFAULT_VOCAL_BALANCE_DB = 1.5

#: Loudness the summed bus is normalised to, in LUFS.
#:
#: **Peak normalisation was the wrong instrument, and three masters proved it.**
#: The bus used to be normalised to a peak of -6 dBFS, which says nothing about how
#: loud the mix actually is: a sparse, vocal-forward mix has a high crest factor, so
#: at an identical peak it lands several LU quieter than a dense one. The mastering
#: chain then had to make up the difference, and did not fully:
#:
#:     premaster LUFS   ->  master LUFS   shortfall vs -8.5 target
#:     -16.69               -8.70          0.20   pass
#:     -21.00               -9.58          1.08   flag
#:     -21.46               -9.55          1.05   flag
#:
#: Monotonic across all three: the quieter the premaster, the more the chain
#: undershoots. -17.0 is chosen as the level of the one premaster that passed, so
#: it is a measured setting rather than a round number.
#:
#: This is the same argument the vocal balance already made one function above -
#: gain staging belongs in LUFS - which had simply not been applied to the bus.
DEFAULT_BUS_LUFS = -17.0

#: Hard peak ceiling for the bus, in dBFS. The LUFS target above yields to this.
#:
#: -3.5 keeps premaster gate 3 (`sample_peak_dbfs <= -3.0` passes) comfortably
#: satisfied while leaving the mastering chain the headroom its stage A expects.
#: On high-crest material the ceiling binds before the LUFS target is reached, and
#: `MixResult.bus_limited_by` records which constraint actually decided the level -
#: never inferred.
DEFAULT_BUS_PEAK_DBFS = -3.5

#: Ducking depth. 0 disables it. Modest by default: heavy ducking on a rap mix
#: pumps audibly, and the instrumental is already an artefact of stem separation.
DEFAULT_DUCK_DB = 0.0

#: High-pass on the vocal. Removes rumble, plosive energy and DC without touching
#: any pitch a human voice produces.
DEFAULT_VOCAL_HPF_HZ = 80.0

#: Linear fade applied at both ends after filtering. Short enough to be inaudible,
#: long enough to kill a filter's edge transient - see `fade_edges`.
EDGE_FADE_MS = 5.0

_EPS = 1e-12


@dataclass
class MixResult:
    """Every number the mix decided, so the result can be audited not trusted."""

    output_path: str
    sample_rate: int
    duration_seconds: float
    instrumental_lufs: float
    vocal_lufs_before: float
    vocal_gain_db: float
    vocal_balance_db: float
    duck_db: float
    bus_gain_db: float
    bus_lufs_target: float
    #: "lufs" when the loudness target set the level, "peak_ceiling" when the
    #: ceiling bound first. High-crest mixes hit the ceiling.
    bus_limited_by: str
    output_peak_dbfs: float
    output_lufs: float
    #: Seconds the vocal runs past the end of the instrumental, if any. Non-zero
    #: means the output was extended rather than the take silently truncated.
    vocal_overhang_seconds: float
    vocal_hpf_hz: float

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        for key, value in data.items():
            if isinstance(value, float):
                data[key] = round(value, 3)
        return data


def load_audio(path: Path, sr: int = MIX_SR):
    """Load `path` as float32, samples-first, stereo.

    Everything downstream assumes (n, 2); normalising here means no other
    function has to carry a mono/stereo branch.
    """
    import librosa
    import numpy as np

    y, _ = librosa.load(str(path), sr=sr, mono=False)
    y = np.asarray(y, dtype=np.float32)
    if y.ndim == 1:
        y = np.stack([y, y], axis=0)
    audio = y.T  # librosa is channels-first; we work samples-first
    if audio.shape[1] == 1:
        audio = np.repeat(audio, 2, axis=1)
    elif audio.shape[1] > 2:
        audio = audio[:, :2]
    return np.ascontiguousarray(audio)


def integrated_lufs(audio, sr: int = MIX_SR) -> float:
    """ITU-R BS.1770 integrated loudness, or -inf for silence/too-short input."""
    import numpy as np
    import pyloudnorm as pyln

    audio = np.asarray(audio, dtype=np.float64)
    # The meter's 400 ms block plus gating needs a real amount of audio.
    if audio.shape[0] < int(sr * 0.5):
        return float("-inf")
    try:
        meter = pyln.Meter(sr)
        value = float(meter.integrated_loudness(audio))
    except Exception:  # pragma: no cover - meter raises on pathological input
        logger.warning("loudness measurement failed", exc_info=True)
        return float("-inf")
    return value if np.isfinite(value) else float("-inf")


def peak_dbfs(audio) -> float:
    import numpy as np

    peak = float(np.max(np.abs(np.asarray(audio)))) if np.size(audio) else 0.0
    return 20.0 * np.log10(peak) if peak > 0 else float("-inf")


def fade_edges(audio, sr: int, milliseconds: float = EDGE_FADE_MS):
    """Apply a short linear fade at both ends, in place on a copy.

    **Why this is not cosmetic.** `sosfiltfilt` pads by reflection, so a take that
    ends mid-waveform gets a discontinuity at the pad boundary and the filter
    rings on it. MEASURED 2026-08-31: a 1 kHz tone at exactly 0.300 peak came back
    from an 80 Hz high-pass at **0.449 in its last 11 samples** - +3.5 dB - while
    the interior was 0.29999, correct to five figures.

    That artefact is 11 samples long and inaudible, but `mix()` sets the bus gain
    from the *peak*, so it would have pulled the entire premaster down 3.5 dB for
    no reason. A 5 ms fade removes it and costs nothing a listener can hear.
    """
    import numpy as np

    audio = np.array(audio, dtype=np.float32, copy=True)
    n = int(sr * milliseconds / 1000.0)
    if n <= 0 or audio.shape[0] < 2 * n:
        return audio
    ramp = np.linspace(0.0, 1.0, n, dtype=np.float32)
    if audio.ndim == 1:
        audio[:n] *= ramp
        audio[-n:] *= ramp[::-1]
    else:
        audio[:n] *= ramp[:, None]
        audio[-n:] *= ramp[::-1, None]
    return audio


def highpass(audio, sr: int, cutoff: float):
    """Second-order Butterworth high-pass, zero-phase, with faded edges.

    `filtfilt` rather than `lfilter`: a vocal that has been phase-smeared at the
    bottom does not sit the same way against a bass line, and the cost of the
    forward-backward pass is irrelevant at these lengths. See `fade_edges` for
    why the result is faded rather than returned raw.
    """
    import numpy as np
    from scipy import signal

    if not cutoff or cutoff <= 0:
        return audio
    audio = np.asarray(audio, dtype=np.float64)
    sos = signal.butter(2, cutoff, btype="highpass", fs=sr, output="sos")
    filtered = signal.sosfiltfilt(sos, audio, axis=0)
    filtered = np.ascontiguousarray(filtered, dtype=np.float32)
    # The ring lasts on the order of the cutoff's own period, not a fixed 5 ms:
    # MEASURED at 80 Hz, a flat 5 ms fade left a 0.336 peak 254 samples from the
    # end (still +1.0 dB over the true 0.300). Two periods of the cutoff - 25 ms
    # at 80 Hz - covers it, and scales correctly if the cutoff is changed.
    fade_ms = max(EDGE_FADE_MS, 2000.0 / float(cutoff))
    return fade_edges(filtered, sr, fade_ms)


def _envelope(audio, sr: int, attack_ms: float, release_ms: float):
    """One-pole attack/release follower over the mono sum of `audio`."""
    import numpy as np

    mono = np.abs(np.asarray(audio, dtype=np.float64)).mean(axis=1)
    attack = np.exp(-1.0 / max(1.0, sr * attack_ms / 1000.0))
    release = np.exp(-1.0 / max(1.0, sr * release_ms / 1000.0))

    env = np.zeros_like(mono)
    current = 0.0
    for i, sample in enumerate(mono):
        coeff = attack if sample > current else release
        current = coeff * current + (1.0 - coeff) * sample
        env[i] = current
    return env


def duck(instrumental, vocal, sr: int, depth_db: float,
         attack_ms: float = 10.0, release_ms: float = 220.0):
    """Attenuate `instrumental` by up to `depth_db` while the vocal is present."""
    import numpy as np

    if not depth_db:
        return instrumental
    env = _envelope(vocal, sr, attack_ms, release_ms)
    ceiling = float(np.percentile(env, 95)) or 1.0
    normalised = np.clip(env / (ceiling + _EPS), 0.0, 1.0)
    gain = 10.0 ** ((-abs(depth_db) * normalised) / 20.0)
    return (np.asarray(instrumental) * gain[:, None]).astype(np.float32)


def _fit_lengths(instrumental, vocal) -> Tuple[Any, Any, float, int]:
    """Pad both to a common length; never truncate the vocal silently."""
    import numpy as np

    instr_len, vocal_len = instrumental.shape[0], vocal.shape[0]
    total = max(instr_len, vocal_len)
    overhang_samples = max(0, vocal_len - instr_len)

    def pad(audio):
        missing = total - audio.shape[0]
        if missing <= 0:
            return audio
        return np.concatenate(
            [audio, np.zeros((missing, audio.shape[1]), dtype=audio.dtype)], axis=0
        )

    return pad(instrumental), pad(vocal), overhang_samples, total


def mix(
    instrumental,
    vocal,
    sr: int = MIX_SR,
    vocal_balance_db: float = DEFAULT_VOCAL_BALANCE_DB,
    duck_db: float = DEFAULT_DUCK_DB,
    bus_lufs_target: float = DEFAULT_BUS_LUFS,
    bus_peak_dbfs: float = DEFAULT_BUS_PEAK_DBFS,
    vocal_hpf_hz: float = DEFAULT_VOCAL_HPF_HZ,
    output_path: Optional[Path] = None,
) -> Tuple[Any, MixResult]:
    """Sum an already-aligned vocal over an instrumental. Returns (audio, result)."""
    import numpy as np

    vocal = highpass(vocal, sr, vocal_hpf_hz)
    instrumental, vocal, overhang_samples, _ = _fit_lengths(instrumental, vocal)

    instr_lufs = integrated_lufs(instrumental, sr)
    vocal_lufs = integrated_lufs(vocal, sr)

    if np.isfinite(instr_lufs) and np.isfinite(vocal_lufs):
        vocal_gain_db = (instr_lufs + vocal_balance_db) - vocal_lufs
    else:
        # One of them is silent or too short to measure. Applying a computed gain
        # from an -inf reading would be a silent catastrophe, so do nothing and
        # say so in the record.
        vocal_gain_db = 0.0
        logger.warning(
            "loudness unmeasurable (instrumental=%s, vocal=%s LUFS); "
            "vocal gain left at 0 dB",
            instr_lufs, vocal_lufs,
        )

    vocal_scaled = (np.asarray(vocal) * (10.0 ** (vocal_gain_db / 20.0))).astype(np.float32)
    instr_ducked = duck(instrumental, vocal_scaled, sr, duck_db)

    summed = np.asarray(instr_ducked, dtype=np.float32) + vocal_scaled

    # Bus level: aim for a loudness, but never breach the peak ceiling. Whichever
    # constraint binds is recorded, because "why is this premaster quiet?" is not
    # answerable from the audio alone.
    current_peak = peak_dbfs(summed)
    current_lufs = integrated_lufs(summed, sr)

    if np.isfinite(current_lufs):
        wanted_db = bus_lufs_target - current_lufs
        limited_by = "lufs"
    else:
        # Unmeasurable loudness: fall back to the ceiling rather than guessing.
        wanted_db = (bus_peak_dbfs - current_peak) if np.isfinite(current_peak) else 0.0
        limited_by = "peak_ceiling"

    if np.isfinite(current_peak):
        headroom_db = bus_peak_dbfs - current_peak
        if wanted_db > headroom_db:
            wanted_db = headroom_db
            limited_by = "peak_ceiling"

    bus_gain_db = float(wanted_db)
    summed = (summed * (10.0 ** (bus_gain_db / 20.0))).astype(np.float32)

    result = MixResult(
        output_path=str(output_path) if output_path else "",
        sample_rate=sr,
        duration_seconds=summed.shape[0] / float(sr),
        instrumental_lufs=instr_lufs,
        vocal_lufs_before=vocal_lufs,
        vocal_gain_db=vocal_gain_db,
        vocal_balance_db=vocal_balance_db,
        duck_db=duck_db,
        bus_gain_db=bus_gain_db,
        bus_lufs_target=bus_lufs_target,
        bus_limited_by=limited_by,
        output_peak_dbfs=peak_dbfs(summed),
        output_lufs=integrated_lufs(summed, sr),
        vocal_overhang_seconds=overhang_samples / float(sr),
        vocal_hpf_hz=vocal_hpf_hz,
    )
    return summed, result


def write_wav(audio, path: Path, sr: int = MIX_SR, subtype: str = "FLOAT") -> Path:
    """Write 32-bit float WAV. Float because the master chain reads pcm_f32le."""
    import soundfile as sf

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), audio, sr, subtype=subtype)
    return path
