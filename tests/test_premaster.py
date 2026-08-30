"""Tests for the premaster acceptance profile (H2-M4).

Synthetic signals with known properties, so each gate is asserted against a
constructed answer rather than "a number came back".
"""

from __future__ import annotations

import numpy as np
import pytest
import soundfile as sf

from toolshop import premaster


def write_wav(path, y, sr=48000):
    sf.write(str(path), y, sr)
    return path


def tone(seconds=5.0, freq=220.0, sr=48000, amp=0.3):
    t = np.linspace(0, seconds, int(sr * seconds), endpoint=False)
    return (np.sin(2 * np.pi * freq * t) * amp).astype(np.float64)


def stereo(left, right):
    return np.column_stack([left, right])


# ------------------------------------------------------------------ grading


def test_grade_higher_is_better():
    assert premaster._grade(0.0, -0.20, -0.50, True) == premaster.PASS
    assert premaster._grade(-0.30, -0.20, -0.50, True) == premaster.FLAG
    assert premaster._grade(-0.90, -0.20, -0.50, True) == premaster.FAIL


def test_grade_lower_is_better():
    assert premaster._grade(-6.0, -3.0, 0.0, False) == premaster.PASS
    assert premaster._grade(-1.0, -3.0, 0.0, False) == premaster.FLAG
    assert premaster._grade(2.0, -3.0, 0.0, False) == premaster.FAIL


def test_grade_boundaries_are_inclusive_of_pass():
    assert premaster._grade(11.0, 11.0, 8.0, True) == premaster.PASS
    assert premaster._grade(8.0, 11.0, 8.0, True) == premaster.FLAG


# ------------------------------------------------------------------ phase gates


def test_in_phase_stereo_passes_the_phase_gates(tmp_path):
    y = tone()
    r = premaster.analyze_premaster(write_wav(tmp_path / "inphase.wav", stereo(y, y)))
    g1 = next(g for g in r["gates"] if g["gate"] == 1)
    g2 = next(g for g in r["gates"] if g["gate"] == 2)
    assert g1["verdict"] == premaster.PASS
    assert g2["verdict"] == premaster.PASS


def test_inverted_channel_fails_the_full_band_phase_gate(tmp_path):
    """A polarity-flipped channel is the textbook anti-phase failure."""
    y = tone()
    r = premaster.analyze_premaster(write_wav(tmp_path / "antiphase.wav", stereo(y, -y)))
    g1 = next(g for g in r["gates"] if g["gate"] == 1)
    assert g1["value"] < -0.9
    assert g1["verdict"] == premaster.FAIL
    assert r["verdict"] == premaster.FAIL


def test_mono_reports_phase_gates_as_not_measured_rather_than_passing(tmp_path):
    """A mono file has no phase relationship - it must not be scored as PASS."""
    r = premaster.analyze_premaster(write_wav(tmp_path / "mono.wav", tone()))
    for num in (1, 2):
        g = next(g for g in r["gates"] if g["gate"] == num)
        assert g["verdict"] == premaster.NOT_MEASURED
        assert g["value"] is None
        assert "mono" in g["note"].lower()


def test_not_measured_gates_do_not_affect_the_overall_verdict(tmp_path):
    r = premaster.analyze_premaster(write_wav(tmp_path / "m.wav", tone()))
    assert premaster.NOT_MEASURED not in (r["failing_gates"] + r["flagged_gates"])


# ------------------------------------------------------------------ level gates


def test_quiet_signal_passes_peak_headroom(tmp_path):
    y = tone(amp=0.1)  # about -20 dBFS
    r = premaster.analyze_premaster(write_wav(tmp_path / "quiet.wav", stereo(y, y)))
    g3 = next(g for g in r["gates"] if g["gate"] == 3)
    assert g3["value"] < -3.0
    assert g3["verdict"] == premaster.PASS


def test_full_scale_signal_fails_peak_headroom(tmp_path):
    y = tone(amp=1.0)
    r = premaster.analyze_premaster(write_wav(tmp_path / "hot.wav", stereo(y, y)))
    g3 = next(g for g in r["gates"] if g["gate"] == 3)
    assert g3["verdict"] in (premaster.FLAG, premaster.FAIL)


def test_dc_offset_is_detected(tmp_path):
    y = tone(amp=0.2) + 0.02  # well past the 0.005 fail threshold
    r = premaster.analyze_premaster(write_wav(tmp_path / "dc.wav", stereo(y, y)))
    g6 = next(g for g in r["gates"] if g["gate"] == 6)
    assert g6["value"] > 0.005
    assert g6["verdict"] == premaster.FAIL


def test_clean_signal_has_no_dc_offset(tmp_path):
    y = tone(amp=0.2)
    r = premaster.analyze_premaster(write_wav(tmp_path / "clean.wav", stereo(y, y)))
    g6 = next(g for g in r["gates"] if g["gate"] == 6)
    assert g6["verdict"] == premaster.PASS


def test_crest_factor_drops_when_the_signal_is_crushed(tmp_path):
    """Hard-clipping destroys crest factor - the gate must notice."""
    y = tone(amp=0.3)
    crushed = np.clip(y * 8.0, -0.3, 0.3)
    r_dyn = premaster.analyze_premaster(write_wav(tmp_path / "dyn.wav", stereo(y, y)))
    r_sq = premaster.analyze_premaster(write_wav(tmp_path / "sq.wav", stereo(crushed, crushed)))
    crest_dyn = next(g for g in r_dyn["gates"] if g["gate"] == 4)["value"]
    crest_sq = next(g for g in r_sq["gates"] if g["gate"] == 4)["value"]
    assert crest_sq < crest_dyn, "a squashed signal must show a lower crest factor"


# ------------------------------------------------------------------ true peak


def test_true_peak_is_at_least_the_sample_peak():
    y = tone(amp=0.5)
    tp = premaster.true_peak_dbfs(y)
    sample_peak = 20 * np.log10(np.max(np.abs(y)))
    assert tp >= sample_peak - 0.1, "inter-sample peaks cannot be below the sample peak"


def test_true_peak_of_silence_is_negative_infinity():
    assert premaster.true_peak_dbfs(np.zeros(1000)) == -np.inf


def test_true_peak_is_labelled_as_an_approximation(tmp_path):
    """It is 4x oversampling, not a certified BS.1770-4 meter."""
    y = tone()
    r = premaster.analyze_premaster(write_wav(tmp_path / "t.wav", stereo(y, y)))
    assert "true_peak_dbfs_approx" in r, "the field name must not imply a certified TP meter"


# ------------------------------------------------------------------ reporting


def test_verdict_is_fail_when_any_gate_fails(tmp_path):
    y = tone()
    r = premaster.analyze_premaster(write_wav(tmp_path / "af.wav", stereo(y, -y)))
    assert r["verdict"] == premaster.FAIL
    assert r["failing_gates"]


def test_all_seven_gates_are_reported(tmp_path):
    y = tone()
    r = premaster.analyze_premaster(write_wav(tmp_path / "all.wav", stereo(y, y)))
    assert [g["gate"] for g in r["gates"]] == [1, 2, 3, 4, 5, 6, 7]


def test_provenance_gate_is_declared_manual_not_guessed(tmp_path):
    y = tone()
    r = premaster.analyze_premaster(write_wav(tmp_path / "p.wav", stereo(y, y)))
    g7 = next(g for g in r["gates"] if g["gate"] == 7)
    assert g7["verdict"] == premaster.NOT_MEASURED
    assert "manual" in g7["note"].lower()


def test_result_cites_the_spec_it_grades_against(tmp_path):
    y = tone()
    r = premaster.analyze_premaster(write_wav(tmp_path / "s.wav", stereo(y, y)))
    assert "PREMASTER_ACCEPTANCE_SPEC" in r["spec"]


def test_every_gate_carries_its_threshold(tmp_path):
    """A verdict without its threshold is unauditable."""
    y = tone()
    r = premaster.analyze_premaster(write_wav(tmp_path / "th.wav", stereo(y, y)))
    for g in r["gates"]:
        assert g["threshold"], f"gate {g['gate']} has no stated threshold"
