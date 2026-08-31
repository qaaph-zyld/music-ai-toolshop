"""Mix tests: gain staging must be measurable, and silence must not detonate it."""

from __future__ import annotations

import numpy as np
import pytest
import soundfile as sf

from toolshop.vocal_swap import mix as mix_mod


SR = mix_mod.MIX_SR


def _tone(seconds: float, freq: float = 220.0, amp: float = 0.2, sr: int = SR):
    t = np.arange(int(seconds * sr)) / sr
    wave = (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32)
    return np.stack([wave, wave], axis=1)


def _noise(seconds: float, amp: float = 0.1, seed: int = 0, sr: int = SR):
    rng = np.random.default_rng(seed)
    wave = rng.normal(0, amp, int(seconds * sr)).astype(np.float32)
    return np.stack([wave, wave], axis=1)


class TestLoadAudio:
    def test_mono_file_becomes_stereo(self, tmp_path):
        path = tmp_path / "mono.wav"
        sf.write(str(path), np.zeros(SR, dtype=np.float32), SR)
        audio = mix_mod.load_audio(path)
        assert audio.ndim == 2 and audio.shape[1] == 2

    def test_stereo_survives_round_trip(self, tmp_path):
        path = tmp_path / "stereo.wav"
        sf.write(str(path), _tone(1.0), SR)
        audio = mix_mod.load_audio(path)
        assert audio.shape == (SR, 2)


class TestGainStaging:
    def test_vocal_placed_at_requested_balance(self):
        """The whole point: the vocal must land where it was asked to land."""
        instrumental = _tone(4.0, freq=110.0, amp=0.30)
        vocal = _tone(4.0, freq=440.0, amp=0.02)  # much quieter to begin with

        _, result = mix_mod.mix(instrumental, vocal, vocal_balance_db=1.5, duck_db=0.0)

        placed = result.vocal_lufs_before + result.vocal_gain_db
        assert placed == pytest.approx(result.instrumental_lufs + 1.5, abs=0.1)
        assert result.vocal_gain_db > 0, "a quiet vocal must be turned up"

    def test_negative_balance_puts_vocal_under_the_beat(self):
        instrumental = _tone(4.0, freq=110.0, amp=0.1)
        vocal = _tone(4.0, freq=440.0, amp=0.1)
        _, result = mix_mod.mix(instrumental, vocal, vocal_balance_db=-6.0)
        placed = result.vocal_lufs_before + result.vocal_gain_db
        assert placed == pytest.approx(result.instrumental_lufs - 6.0, abs=0.1)

    def test_bus_hits_the_loudness_target(self):
        """The bus is levelled in LUFS, because peak does not predict loudness.

        Peak normalisation handed the mastering chain premasters between -16.7 and
        -21.5 LUFS for the same peak, and it undershot its target in proportion.
        """
        instrumental = _tone(6.0, amp=0.4)
        vocal = _tone(6.0, freq=440.0, amp=0.4)
        audio, result = mix_mod.mix(instrumental, vocal, bus_lufs_target=-17.0)
        assert result.output_lufs == pytest.approx(-17.0, abs=0.2)
        assert result.bus_limited_by == "lufs"

    def test_peak_ceiling_overrides_the_loudness_target(self):
        """A high-crest mix must not breach the ceiling chasing loudness."""
        instrumental = _tone(6.0, amp=0.4)
        vocal = _tone(6.0, freq=440.0, amp=0.4)
        audio, result = mix_mod.mix(
            instrumental, vocal, bus_lufs_target=0.0, bus_peak_dbfs=-3.5
        )
        assert result.output_peak_dbfs == pytest.approx(-3.5, abs=0.01)
        assert result.bus_limited_by == "peak_ceiling"
        assert result.output_lufs < -3.5, "loudness must fall short, not clip"

    def test_which_constraint_bound_is_recorded(self):
        """Never inferred: 'why is this premaster quiet' must be answerable."""
        instrumental = _tone(6.0, amp=0.4)
        vocal = _tone(6.0, freq=440.0, amp=0.4)
        _, quiet = mix_mod.mix(instrumental, vocal, bus_lufs_target=-30.0)
        _, loud = mix_mod.mix(instrumental, vocal, bus_lufs_target=0.0)
        assert quiet.bus_limited_by == "lufs"
        assert loud.bus_limited_by == "peak_ceiling"

    def test_headroom_is_left_for_mastering(self):
        """A premaster at 0 dBFS is a bug; the chain needs room to work."""
        audio, result = mix_mod.mix(_tone(6.0, amp=0.9), _tone(6.0, 440.0, 0.9))
        # Gate 3 of the M4 premaster spec passes at <= -3.0 dBFS.
        assert result.output_peak_dbfs <= -3.0
        assert np.max(np.abs(audio)) < 1.0


class TestSilenceSafety:
    def test_silent_vocal_does_not_apply_an_infinite_gain(self):
        """-inf LUFS must not become an infinite gain. This is the crash case."""
        instrumental = _tone(3.0, amp=0.3)
        silence = np.zeros((3 * SR, 2), dtype=np.float32)

        audio, result = mix_mod.mix(instrumental, silence)

        assert result.vocal_gain_db == 0.0
        assert np.all(np.isfinite(audio))

    def test_silent_instrumental_is_survivable(self):
        silence = np.zeros((3 * SR, 2), dtype=np.float32)
        audio, result = mix_mod.mix(silence, _tone(3.0, amp=0.2))
        assert np.all(np.isfinite(audio))
        assert result.vocal_gain_db == 0.0

    def test_too_short_to_measure_returns_negative_infinity(self):
        assert mix_mod.integrated_lufs(_tone(0.05)) == float("-inf")


class TestLengths:
    def test_shorter_vocal_is_padded_not_stretched(self):
        instrumental = _tone(4.0)
        vocal = _tone(2.0, freq=440.0)
        audio, result = mix_mod.mix(instrumental, vocal)
        assert audio.shape[0] == 4 * SR
        assert result.vocal_overhang_seconds == 0.0

    def test_longer_vocal_extends_the_output_and_is_reported(self):
        """A take that runs past the beat must not be silently truncated."""
        instrumental = _tone(2.0)
        vocal = _tone(3.0, freq=440.0)
        audio, result = mix_mod.mix(instrumental, vocal)
        assert audio.shape[0] == 3 * SR
        assert result.vocal_overhang_seconds == pytest.approx(1.0, abs=0.01)


class TestHighpass:
    def test_dc_offset_is_removed(self):
        audio = np.ones((SR, 2), dtype=np.float32) * 0.5
        filtered = mix_mod.highpass(audio, SR, 80.0)
        assert abs(float(np.mean(filtered))) < 0.01

    def test_zero_cutoff_is_a_no_op(self):
        audio = _tone(1.0)
        assert mix_mod.highpass(audio, SR, 0) is audio

    def test_passband_content_survives(self):
        audio = _tone(1.0, freq=1000.0, amp=0.3)
        filtered = mix_mod.highpass(audio, SR, 80.0)
        assert mix_mod.peak_dbfs(filtered) == pytest.approx(
            mix_mod.peak_dbfs(audio), abs=0.5
        )

    def test_edge_transient_does_not_inflate_the_peak(self):
        """The regression this guards: an 11-sample filter artefact at +3.5 dB.

        Without the edge fade, an 80 Hz high-pass returned 0.449 in the final
        samples of a 0.300-peak tone. `mix()` sets bus gain from the peak, so that
        artefact alone would have pulled the whole premaster down 3.5 dB.
        """
        audio = _tone(1.0, freq=1000.0, amp=0.3)
        filtered = mix_mod.highpass(audio, SR, 80.0)
        assert float(np.max(np.abs(filtered))) <= 0.31

    def test_fade_edges_leaves_the_interior_untouched(self):
        audio = _tone(1.0, freq=1000.0, amp=0.3)
        faded = mix_mod.fade_edges(audio, SR)
        interior = faded[SR // 4 : -SR // 4]
        assert float(np.max(np.abs(interior))) == pytest.approx(0.3, abs=1e-3)

    def test_fade_edges_skips_input_shorter_than_the_fade(self):
        tiny = np.ones((4, 2), dtype=np.float32)
        assert np.all(mix_mod.fade_edges(tiny, SR) == 1.0)


class TestDuck:
    def test_zero_depth_is_a_no_op(self):
        instrumental = _tone(1.0)
        assert mix_mod.duck(instrumental, _noise(1.0), SR, 0.0) is instrumental

    def test_instrumental_is_quieter_where_the_vocal_sits(self):
        instrumental = _tone(4.0, amp=0.3)
        vocal = np.zeros((4 * SR, 2), dtype=np.float32)
        vocal[2 * SR :] = _tone(2.0, freq=440.0, amp=0.3)  # vocal in the 2nd half

        ducked = mix_mod.duck(instrumental, vocal, SR, depth_db=6.0)

        quiet_half = float(np.max(np.abs(ducked[3 * SR :])))
        loud_half = float(np.max(np.abs(ducked[: int(1.5 * SR)])))
        assert quiet_half < loud_half


def test_write_wav_is_float_and_readable(tmp_path):
    path = tmp_path / "nested" / "out.wav"
    mix_mod.write_wav(_tone(1.0), path)
    assert path.exists()
    info = sf.info(str(path))
    assert info.samplerate == SR
    assert "FLOAT" in info.subtype


def test_result_serialises_to_rounded_floats():
    _, result = mix_mod.mix(_tone(2.0), _tone(2.0, 440.0))
    data = result.to_dict()
    assert isinstance(data["vocal_gain_db"], float)
    assert data["sample_rate"] == SR
