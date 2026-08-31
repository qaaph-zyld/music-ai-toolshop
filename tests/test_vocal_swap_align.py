"""Alignment tests: a known offset must be recovered, and a bad one flagged."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from toolshop.vocal_swap import align


SR = align.ANALYSIS_SR
FRAMES_PER_SECOND = SR / align.HOP_LENGTH
#: One envelope frame is 11.6 ms; allow two frames of slack.
TOLERANCE_S = 2.0 / FRAMES_PER_SECOND


def _click_track(path: Path, period_s: float, duration_s: float,
                 lead_silence_s: float = 0.0, sr: int = SR, seed: int = 7) -> Path:
    """Write a click train whose amplitudes follow a fixed pattern.

    The amplitudes matter. A *perfectly periodic* click train has no unique
    alignment - it correlates exactly as well at every multiple of the period, so
    asking for "the" offset is ill-posed and the estimator is right to return any
    of them. Real music is not periodic like that; varying the accents gives the
    envelope the structure a correlation peak needs, which is what makes this a
    fair fixture rather than a trick question.
    """
    total = int((duration_s + lead_silence_s) * sr)
    audio = np.zeros(total, dtype=np.float32)
    click = np.hanning(int(0.01 * sr)).astype(np.float32)
    start = int(lead_silence_s * sr)
    step = int(period_s * sr)
    rng = np.random.default_rng(seed)
    positions = list(range(start, total - len(click), step))
    amplitudes = rng.uniform(0.3, 1.0, size=len(positions))
    for amp, pos in zip(amplitudes, positions):
        audio[pos : pos + len(click)] += click * amp
    sf.write(str(path), audio, sr)
    return path


def _rhythm_track(path: Path, duration_s: float, lead_silence_s: float = 0.0,
                  tempo_scale: float = 1.0, sr: int = SR, seed: int = 3) -> Path:
    """Write an *irregular* rhythm - onsets at non-uniform intervals.

    Amplitude variation alone is not enough to make a click train unambiguous:
    `onset_strength` works on log-mel spectral flux, and the log compresses a
    3x amplitude range into almost nothing. What survives is *when* onsets fall,
    so the pattern here varies the intervals. `tempo_scale` stretches every
    interval by a constant factor, which is what a tempo difference actually is.
    """
    total = int((duration_s + lead_silence_s) * sr)
    audio = np.zeros(total, dtype=np.float32)
    click = np.hanning(int(0.01 * sr)).astype(np.float32)
    rng = np.random.default_rng(seed)

    pos = int(lead_silence_s * sr)
    while pos < total - len(click):
        audio[pos : pos + len(click)] += click * float(rng.uniform(0.5, 1.0))
        interval = float(rng.choice([0.25, 0.375, 0.5, 0.75])) * tempo_scale
        pos += int(interval * sr)
    sf.write(str(path), audio, sr)
    return path


def test_offset_recovered_for_delayed_take(tmp_path):
    """A take carrying 1.5 s of lead silence must be pulled 1.5 s earlier."""
    instrumental = _rhythm_track(tmp_path / "instr.wav", 20.0)
    vocal = _rhythm_track(tmp_path / "vocal.wav", 20.0, lead_silence_s=1.5)

    result = align.estimate_offset(instrumental, vocal)

    assert result.offset_seconds == pytest.approx(-1.5, abs=TOLERANCE_S + 0.05)
    assert result.method == "cross_correlation"
    assert not result.ambiguous


def test_periodic_material_is_flagged_ambiguous(tmp_path):
    """A perfectly periodic click train has no unique alignment - say so.

    This is the failure the pipeline exists to prevent: on periodic material the
    correlation peaks once per beat, confidence stays high, and the winning peak
    can be a whole beat away from the truth. Confidence alone would call this a
    good alignment; `peak_margin` is what catches it.
    """
    instrumental = _click_track(tmp_path / "instr.wav", 0.5, 24.0)
    vocal = _click_track(tmp_path / "vocal.wav", 0.5, 24.0, lead_silence_s=0.75)

    result = align.estimate_offset(instrumental, vocal)

    assert result.confidence > 0.8, "the trap is that confidence looks fine"
    assert result.ambiguous
    assert not result.trustworthy
    assert "ambiguous" in result.notes.lower()


def test_identical_sources_align_at_zero(tmp_path):
    track = _rhythm_track(tmp_path / "a.wav", 20.0)
    result = align.estimate_offset(track, track)
    assert result.offset_seconds == pytest.approx(0.0, abs=TOLERANCE_S)
    assert result.confidence > 0.9
    assert result.trustworthy


def test_unrelated_sources_report_low_confidence(tmp_path):
    """Noise against a click train must not look like a good alignment."""
    instrumental = _click_track(tmp_path / "instr.wav", 0.5, 10.0)
    rng = np.random.default_rng(0)
    noise = rng.normal(0, 0.05, int(10.0 * SR)).astype(np.float32)
    noise_path = tmp_path / "noise.wav"
    sf.write(str(noise_path), noise, SR)

    result = align.estimate_offset(instrumental, noise_path)
    assert result.confidence < align.DEFAULT_MIN_CONFIDENCE
    assert not result.trustworthy
    assert result.notes


def test_matching_tempo_is_not_flagged_as_mismatch(tmp_path):
    """Two takes at the same tempo must pass, even offset from each other.

    This is the case a tempo-estimate comparison gets wrong. `beat_track` reports
    identical material to within only ~3%, so a tight tempo tolerance rejects
    good takes; drift measurement sees the same material agree to ~12 ms.
    """
    instrumental = _rhythm_track(tmp_path / "instr.wav", 30.0)
    vocal = _rhythm_track(tmp_path / "vocal.wav", 30.0, lead_silence_s=0.75)

    result = align.estimate_offset(instrumental, vocal)
    assert not result.tempo_mismatch
    assert result.mismatch_basis == "drift"
    assert result.drift_seconds is not None
    assert abs(result.drift_seconds) <= align.DEFAULT_DRIFT_TOLERANCE_S


def test_drift_catches_what_confidence_alone_would_accept(tmp_path):
    """A 0.2% tempo difference: confidence passes, drift catches it.

    MEASURED 2026-08-31, sweeping tempo_scale over a 40 s irregular rhythm:

        0.2%  confidence 0.491  drift  -70 ms   <- confidence ALONE would pass
        0.4%  confidence 0.215  drift -116 ms
        1.0%  confidence 0.091  drift -302 ms
        2.0%  confidence 0.131  drift unmeasurable (correlation destroyed)

    This case is the reason drift is measured at all. 0.491 clears the confidence
    threshold, so a confidence-only check accepts a take that slips 70 ms across
    the track - audible flamming that no mastering can repair. Above ~2% the
    correlation collapses and confidence catches it instead; between the two,
    drift is the only thing watching.
    """
    instrumental = _rhythm_track(tmp_path / "instr.wav", 40.0)
    vocal = _rhythm_track(tmp_path / "vocal.wav", 40.0, tempo_scale=1.002)

    result = align.estimate_offset(instrumental, vocal)

    assert result.confidence > align.DEFAULT_MIN_CONFIDENCE, (
        "the premise of this test is that a confidence check would pass it"
    )
    assert result.mismatch_basis == "drift"
    assert result.tempo_mismatch
    assert abs(result.drift_seconds) > align.DEFAULT_DRIFT_TOLERANCE_S
    assert result.drift_span_seconds and result.drift_span_seconds > 10.0
    assert not result.trustworthy


def test_gross_tempo_difference_is_caught_by_confidence(tmp_path):
    """At 2% the correlation collapses; the take must still be refused."""
    instrumental = _rhythm_track(tmp_path / "instr.wav", 40.0)
    vocal = _rhythm_track(tmp_path / "vocal.wav", 40.0, tempo_scale=1.02)

    result = align.estimate_offset(instrumental, vocal)
    assert result.confidence < align.DEFAULT_MIN_CONFIDENCE
    assert not result.trustworthy


def test_short_material_falls_back_to_tempo(tmp_path):
    """Under the drift-analysis floor the verdict must say it used tempo."""
    instrumental = _rhythm_track(tmp_path / "instr.wav", 6.0)
    vocal = _rhythm_track(tmp_path / "vocal.wav", 6.0)

    result = align.estimate_offset(instrumental, vocal)
    assert result.drift_seconds is None
    assert result.mismatch_basis in ("tempo", "none")


def test_declared_offset_is_trusted():
    result = align.declared_offset(2.25)
    assert result.offset_seconds == 2.25
    assert result.confidence == 1.0
    assert result.trustworthy
    assert result.method == "declared"


def test_max_offset_bounds_the_search(tmp_path):
    """A 10 s displacement must not be found when only 2 s is searched."""
    instrumental = _rhythm_track(tmp_path / "instr.wav", 30.0)
    vocal = _rhythm_track(tmp_path / "vocal.wav", 30.0, lead_silence_s=10.0)

    result = align.estimate_offset(instrumental, vocal, max_offset_s=2.0)
    assert abs(result.offset_seconds) <= 2.0 + TOLERANCE_S


class TestApplyOffset:
    def test_positive_offset_prepends_silence(self):
        audio = np.ones((100, 2), dtype=np.float32)
        shifted = align.apply_offset(audio, sr=100, offset_seconds=0.5)
        assert shifted.shape == (150, 2)
        assert np.all(shifted[:50] == 0)
        assert np.all(shifted[50:] == 1)

    def test_negative_offset_trims_head(self):
        audio = np.ones((100, 2), dtype=np.float32)
        shifted = align.apply_offset(audio, sr=100, offset_seconds=-0.25)
        assert shifted.shape == (75, 2)

    def test_zero_offset_is_identity(self):
        audio = np.ones((10, 2), dtype=np.float32)
        assert align.apply_offset(audio, sr=100, offset_seconds=0.0) is audio

    def test_mono_input_supported(self):
        audio = np.ones(100, dtype=np.float32)
        shifted = align.apply_offset(audio, sr=100, offset_seconds=0.1)
        assert shifted.shape == (110,)


class TestTimeStretch:
    def test_unity_ratio_is_a_no_op(self):
        audio = np.ones((1000, 2), dtype=np.float32)
        assert align.time_stretch_to(audio, 44100, 1.0) is audio
        assert align.time_stretch_to(audio, 44100, None) is audio

    def test_stereo_stretch_shortens_when_ratio_above_one(self):
        rng = np.random.default_rng(1)
        audio = rng.normal(0, 0.1, (44100, 2)).astype(np.float32)
        stretched = align.time_stretch_to(audio, 44100, 1.25)
        assert stretched.shape[1] == 2
        assert stretched.shape[0] < audio.shape[0]


def test_result_serialises_with_derived_verdict():
    result = align.declared_offset(1.0)
    data = result.to_dict()
    assert data["trustworthy"] is True
    assert data["offset_seconds"] == 1.0
    assert data["method"] == "declared"
