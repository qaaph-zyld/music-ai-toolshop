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


class TestTempoConfidence:
    """A tempo estimate must be a measurement, not librosa's prior in disguise.

    MEASURED 2026-08-31 — periodicity of the onset envelope across real material:

        synthetic click grid   0.957   -> tempo reported
        Borba instrumental     0.545   -> tempo reported
        Borba full mix         0.503   -> tempo reported
        ZELDI nova full mix    0.349   -> tempo reported
        --------------------------------- threshold 0.30
        ZELDI vocal stem       0.238   -> unknown
        Borba vocal stem       0.211   -> unknown
        white noise            0.075   -> unknown

    The bug this closes: `beat_track` returned **117.4538 BPM** for two unrelated
    isolated vocals. A 120 BPM click grid reports the same 117.4538, which
    identifies it as the `start_bpm=120` prior after frame quantisation — the
    prior leaking out as data and driving `tempo_mismatch` verdicts on takes whose
    tempo was never measured.
    """

    def test_periodic_material_scores_high(self, tmp_path):
        track = _click_track(tmp_path / "grid.wav", 0.5, 30.0)
        env, tempo, conf = align._onset_envelope(track)
        assert conf > 0.8
        assert tempo is not None, "a strict click grid must yield a tempo"

    def test_unstructured_audio_scores_low_and_reports_no_tempo(self, tmp_path):
        rng = np.random.default_rng(0)
        path = tmp_path / "noise.wav"
        sf.write(str(path), rng.normal(0, 0.1, 20 * SR).astype(np.float32), SR)

        env, tempo, conf = align._onset_envelope(path)
        assert conf < align.MIN_TEMPO_CONFIDENCE
        assert tempo is None, "no periodicity must mean no tempo, not the prior"

    def test_confidence_is_bounded(self, tmp_path):
        track = _click_track(tmp_path / "grid.wav", 0.5, 20.0)
        env, _, _ = align._onset_envelope(track)
        assert 0.0 <= align.tempo_confidence(env) <= 1.0

    def test_degenerate_input_does_not_raise(self):
        assert align.tempo_confidence(np.zeros(3)) == 0.0
        assert align.tempo_confidence(np.zeros(500)) == 0.0

    def test_unmeasurable_tempo_cannot_produce_a_mismatch_verdict(self, tmp_path):
        """The actual regression: no tempo means no tempo verdict.

        Two short noise files cannot support a tempo, so `mismatch_basis` must be
        "none" — previously both would have been assigned the 120 BPM prior, the
        ratio would have been a clean 1.0, and the estimator would have reported a
        confident agreement it had not measured.
        """
        rng = np.random.default_rng(1)
        a, b = tmp_path / "a.wav", tmp_path / "b.wav"
        sf.write(str(a), rng.normal(0, 0.1, 6 * SR).astype(np.float32), SR)
        sf.write(str(b), rng.normal(0, 0.1, 6 * SR).astype(np.float32), SR)

        result = align.estimate_offset(a, b)
        assert result.instrumental_tempo is None and result.vocal_tempo is None
        assert result.tempo_ratio is None
        assert result.tempo_mismatch is False
        assert result.mismatch_basis == "none"

    def test_confidences_are_reported_for_audit(self, tmp_path):
        instrumental = _rhythm_track(tmp_path / "i.wav", 20.0)
        vocal = _rhythm_track(tmp_path / "v.wav", 20.0)
        data = align.estimate_offset(instrumental, vocal).to_dict()
        assert 0.0 <= data["instrumental_tempo_confidence"] <= 1.0
        assert 0.0 <= data["vocal_tempo_confidence"] <= 1.0


class TestOnsetAlignment:
    """Aligning two vocals on their first sung sound.

    The case this exists for, MEASURED 2026-08-31 on a real pair: the Suno vocal
    opened at 1.49 s and the artist's take at 13.79 s, so the take had to move
    **-12.31 s**. Cross-correlation returned **+12.70 s** — the mirror placement,
    25 s wrong — at a peak margin of 0.0005, i.e. choosing at random between
    near-identical peaks. Onset matching returns -12.307 s directly.
    """

    def _voice(self, path: Path, lead_silence_s: float, length_s: float = 30.0,
               seed: int = 4, sr: int = SR) -> Path:
        """A structured phrase after some silence — a stand-in for a sung entry.

        Deliberately NOT white noise. Corroboration checks that the offset still
        holds late in the track, which needs shared structure to verify against;
        noise has none, so a noise fixture would exercise the "cannot corroborate"
        branch rather than the aligned one.
        """
        total = int(length_s * sr)
        audio = np.zeros(total, dtype=np.float32)
        rng = np.random.default_rng(seed)
        # Sustained bursts, not clicks: `first_sound_at` deliberately ignores runs
        # shorter than MIN_ONSET_RUN_S so a click or breath cannot pass as the
        # first word, and a sung syllable is far longer than a click anyway.
        note = int(0.30 * sr)
        pos = int(lead_silence_s * sr)
        while pos + note < total:
            t = np.arange(note) / sr
            freq = float(rng.choice([180.0, 220.0, 260.0, 300.0]))
            body = (0.4 * np.sin(2 * np.pi * freq * t)).astype(np.float32)
            body *= np.hanning(note).astype(np.float32)
            audio[pos : pos + note] += body
            pos += note + int(float(rng.choice([0.15, 0.25, 0.4])) * sr)
        sf.write(str(path), audio, sr)
        return path

    def test_offset_is_the_gap_between_first_sounds(self, tmp_path):
        reference = self._voice(tmp_path / "ref.wav", lead_silence_s=1.5)
        take = self._voice(tmp_path / "take.wav", lead_silence_s=6.0)

        result = align.estimate_offset_by_onset(reference, take)

        # reference starts 4.5 s earlier, so the take must move -4.5 s
        assert result.offset_seconds == pytest.approx(-4.5, abs=0.1)
        assert result.method == "first_onset"
        assert result.trustworthy

    def test_take_earlier_than_reference_gives_a_positive_offset(self, tmp_path):
        reference = self._voice(tmp_path / "ref.wav", lead_silence_s=5.0)
        take = self._voice(tmp_path / "take.wav", lead_silence_s=1.0)
        result = align.estimate_offset_by_onset(reference, take)
        assert result.offset_seconds == pytest.approx(4.0, abs=0.1)

    def test_identical_entries_align_at_zero(self, tmp_path):
        reference = self._voice(tmp_path / "ref.wav", lead_silence_s=3.0)
        take = self._voice(tmp_path / "take.wav", lead_silence_s=3.0)
        assert align.estimate_offset_by_onset(reference, take).offset_seconds == \
            pytest.approx(0.0, abs=0.05)

    def test_divergent_arrangements_are_not_reported_as_aligned(self, tmp_path):
        """The real failure: the opening matches, the rest does not.

        MEASURED on a real pair — same tempo (129.2 BPM both), but the take sang
        across 150.56 s where the Suno vocal sang across 185.48 s. The opening
        aligned to -0.09 s while later windows sat at -15.09, +8.10 and -13.56 s.
        Onset matching alone called that `trustworthy`, and the mix sounded wrong.
        """
        reference = self._voice(tmp_path / "ref.wav", lead_silence_s=1.0, seed=1)
        # Same entry point, completely different phrasing after it.
        take = self._voice(tmp_path / "take.wav", lead_silence_s=1.0, seed=99)

        result = align.estimate_offset_by_onset(reference, take)

        assert result.offset_seconds == pytest.approx(0.0, abs=0.1)
        assert not result.trustworthy, (
            "matching first words must not certify the whole track"
        )
        assert "opening matches" in result.notes

    def test_silence_returns_none_rather_than_a_number(self, tmp_path):
        silent = tmp_path / "silent.wav"
        sf.write(str(silent), np.zeros(5 * SR, dtype=np.float32), SR)
        voice = self._voice(tmp_path / "v.wav", lead_silence_s=1.0)

        assert align.estimate_offset_by_onset(silent, voice) is None
        assert align.estimate_offset_by_onset(voice, silent) is None

    def test_a_click_is_not_mistaken_for_the_first_word(self, tmp_path):
        """A separation artefact before the entry must not set the offset."""
        sr = SR
        audio = np.zeros(int(10 * sr), dtype=np.float32)
        click_at = int(0.5 * sr)
        audio[click_at : click_at + int(0.02 * sr)] = 0.5   # 20 ms, below the floor
        entry = int(4.0 * sr)
        rng = np.random.default_rng(5)
        audio[entry:] = rng.normal(0, 0.3, len(audio) - entry).astype(np.float32)
        path = tmp_path / "clicky.wav"
        sf.write(str(path), audio, sr)

        assert align.first_sound_at(path) == pytest.approx(4.0, abs=0.15)

    def test_first_sound_of_silence_is_none(self, tmp_path):
        path = tmp_path / "quiet.wav"
        sf.write(str(path), np.zeros(3 * SR, dtype=np.float32), SR)
        assert align.first_sound_at(path) is None


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
