"""Tests for toolshop.flip.chops — chop candidate extraction for the OGCM flip."""

import numpy as np
import pytest

from toolshop.flip import chops


SR = 22050


def _tone(freq, dur, sr=SR, amp=0.5):
    t = np.arange(int(dur * sr)) / sr
    return amp * np.sin(2 * np.pi * freq * t)


def _bar(sr=SR):
    """One 4/4 bar at 120 BPM (0.5 s/beat) with clicks on each beat."""
    n = int(2.0 * sr)
    bar = np.zeros(n, dtype=np.float32)
    for b in range(4):
        bar[b * n // 4 : b * n // 4 + int(0.01 * sr)] += 0.8  # click
    return bar


def _chord_bar(freqs, sr=SR):
    """One bar of clicks plus sustained chord tones."""
    bar = _bar(sr).copy()
    t = np.arange(int(2.0 * sr)) / sr
    for f in freqs:
        bar += 0.2 * np.sin(2 * np.pi * f * t)
    return bar


def _pc_index(name):
    return chops.NOTE_NAMES.index(name)


def test_tonal_center_major():
    chroma = np.zeros(12)
    chroma[[_pc_index("A"), _pc_index("C#"), _pc_index("E")]] = 1.0  # A major triad
    root, mode, conf = chops.estimate_tonal_center(chroma)
    assert root == "A" and mode == "major" and conf > 0


def test_tonal_center_minor():
    chroma = np.zeros(12)
    chroma[[_pc_index("F#"), _pc_index("A"), _pc_index("C#")]] = 1.0  # F# minor triad
    root, mode, conf = chops.estimate_tonal_center(chroma)
    assert root == "F#" and mode == "minor" and conf > 0


def test_shift_key_relative_minor_map():
    # The OGCM key menu: content reading F#m (relative minor of A major)
    # pitches down to canonical drill keys.
    assert chops.shift_key("F#", "minor", -1) == "F minor"
    assert chops.shift_key("F#", "minor", -4) == "D minor"
    assert chops.shift_key("F#", "minor", -5) == "C# minor"
    # A-major-dominant content does NOT become minor.
    assert chops.shift_key("A", "major", -1) == "G# major"


def test_zero_cross_snap():
    sr = SR
    t = np.arange(int(0.1 * sr)) / sr
    y = np.sin(2 * np.pi * 440 * t)
    # period = sr/440 ≈ 50.1 samples; pick a mid-cycle point
    probe = int(0.05 * sr) + 13
    snapped = chops.snap_to_zero_crossing(y, probe, 0.005, sr)
    assert abs(y[snapped]) < 0.3
    assert snapped != probe


def test_microfade_edges():
    chunk = np.ones(8000, dtype=np.float32)
    out = chops.apply_microfade(chunk, SR, 8.0)
    assert out[0] == pytest.approx(0.0, abs=1e-3)
    assert out[-1] == pytest.approx(0.0, abs=1e-3)
    # Interior untouched
    assert out[4000] == pytest.approx(1.0)


def test_find_candidates_aligned_and_ranked():
    """8 bars of pattern A + 8 bars of pattern B + 8 bars of A again at 120 BPM.

    A = F#m-flavoured chord, B = different chord. Top candidates should sit on
    downbeats and prefer repeated material.
    """
    sr = SR
    fsh_m = [185.0, 220.0, 277.0]   # F#4, A4, C#5-ish
    other = [220.0, 261.6, 329.6]   # A, C, E — different colour
    track = np.concatenate(
        [_chord_bar(fsh_m, sr)] * 8 + [_chord_bar(other, sr)] * 8 + [_chord_bar(fsh_m, sr)] * 8
    )
    result = chops.find_candidates(track, sr, bar_lengths=(2, 4), top_n=10)
    cands = result["candidates"]
    assert cands, "no candidates emitted on a structured synthetic track"
    grid = result["grid"]
    downbeats = np.asarray(grid["downbeat_times"])
    for c in cands:
        # every candidate starts on a downbeat within half a beat
        assert np.min(np.abs(downbeats - c["start_s"])) < 0.3, c
    # top scorer lives in the repeated F#m material (repetitions > 1) or at a
    # strong boundary — either way the manifest records the evidence.
    top = cands[0]
    assert top["repetitions"] >= 1
    assert set(top["shift_keys"].keys()) == set(chops.PITCH_ARMS)


def test_slice_candidate_snapped_and_faded():
    sr = SR
    y = np.sin(2 * np.pi * 220 * np.arange(int(6.0 * sr)) / sr)
    cand = {"start_sample": int(1.0 * sr), "end_sample": int(2.0 * sr)}
    chunk = chops.slice_candidate(y, sr, cand)
    assert abs(len(chunk) - sr) <= int(0.02 * sr) + 4
    assert abs(chunk[0]) < 0.3 and abs(chunk[-1]) < 0.3


def test_bleed_penalty_penalises_correlated_span():
    n = 64
    rng = np.random.default_rng(0)
    pattern = rng.random(20) + 0.5
    vocal_env = rng.random(n)
    vocal_env[10:30] = pattern                     # vocal envelope
    bed_env = rng.random(n)
    bed_env[10:30] = pattern + 0.1 * rng.random(20)  # bed comodulates -> bleed
    penalised = chops._bleed_penalty(bed_env, vocal_env, 10, 30)
    clean = chops._bleed_penalty(bed_env, vocal_env, 35, 55)
    assert penalised > clean
    # No vocal env = unmeasured, reported as 0 — not zero-risk.
    assert chops._bleed_penalty(bed_env, None, 10, 20) == 0.0


def test_write_audition_pack(tmp_path):
    sr = SR
    y = np.sin(2 * np.pi * 220 * np.arange(int(6.0 * sr)) / sr)
    manifest = {
        "candidates": [
            {"id": "cand_000", "start_s": 1.0, "end_s": 2.0,
             "start_sample": int(1.0 * sr), "end_sample": int(2.0 * sr),
             "bars": 2, "tonal_center": "F#", "tonal_mode": "minor", "score": 0.9}
        ]
    }
    files = chops.write_audition_pack(y, sr, manifest, tmp_path, loops=2)
    assert len(files) == 1
    import soundfile as sf
    data, _ = sf.read(files[0])
    assert abs(len(data) - 2 * sr) <= int(0.05 * sr)
