"""Tests for toolshop.flip.assemble — W3 buffer-based beat assembly."""

import numpy as np
import pytest

from toolshop.flip import assemble, drums


SR = 22050


def _manifest_and_bed(sr=SR):
    """8-bar bed (4 s at 120 BPM feel) + a manifest with 2 candidates."""
    n = int(8.0 * sr)
    t = np.arange(n) / sr
    bed = 0.4 * np.sin(2 * np.pi * 220 * t)
    manifest = {
        "grid": {"tempo": 120.0, "beat_times": [i * 0.5 for i in range(16)],
                 "downbeat_times": [i * 2.0 for i in range(4)]},
        "candidates": [
            {"id": "cand_000", "start_s": 0.0, "end_s": 4.0,
             "start_sample": 0, "end_sample": int(4.0 * sr), "bars": 2,
             "segment_class": "A", "repetitions": 2, "seam_score": 0.9,
             "seq_score": 0.5, "boundary_score": 0.5, "duration_score": 1.0,
             "bleed_penalty": 0.0, "score": 0.9,
             "tonal_center": "F#", "tonal_mode": "minor",
             "tonal_confidence": 0.4, "shift_keys": {-1: "F minor"}},
            {"id": "cand_001", "start_s": 4.0, "end_s": 8.0,
             "start_sample": int(4.0 * sr), "end_sample": int(8.0 * sr), "bars": 2,
             "segment_class": "A", "repetitions": 2, "seam_score": 0.8,
             "seq_score": 0.5, "boundary_score": 0.4, "duration_score": 1.0,
             "bleed_penalty": 0.0, "score": 0.8,
             "tonal_center": "A", "tonal_mode": "major",
             "tonal_confidence": 0.4, "shift_keys": {-1: "G# major"}},
        ],
        "duration": 8.0,
    }
    return manifest, bed


def test_render_beat_places_chops():
    manifest, bed = _manifest_and_bed()
    placements = [
        assemble.Placement("cand_000", start_beat=0.0, length_beats=8.0, gain=0.8),
        assemble.Placement("cand_001", start_beat=8.0, length_beats=8.0, gain=0.8),
    ]
    res = assemble.render_beat(bed, SR, manifest, placements, bpm=120.0, total_beats=16.0)
    assert res.audio.size > int(7.5 * SR)
    assert np.abs(res.audio).max() > 0.2
    assert len(res.events) == 2
    assert res.events[1]["time_s"] == pytest.approx(8.0 * 0.5, abs=0.02)


def test_unknown_candidate_warns():
    manifest, bed = _manifest_and_bed()
    res = assemble.render_beat(
        bed, SR, manifest,
        [assemble.Placement("nope", 0.0, 4.0)], bpm=120.0, total_beats=8.0,
    )
    assert res.warnings and "nope" in res.warnings[0]
    assert np.abs(res.audio).max() == 0.0


def test_fit_slot_bounded_stretch():
    manifest, bed = _manifest_and_bed()
    cand = manifest["candidates"][0]
    from toolshop.flip import chops
    chunk = chops.slice_candidate(bed, SR, cand)
    # slot = 8 source beats at dst=90 bpm on a src=120 bpm chop: chop is 4s,
    # slot is 8*60/90=5.33s → ratio 1.33 > 1.25 → refused, unfitted.
    out, ratio, fitted = assemble.fit_chop_to_slot(
        chunk, SR, src_bpm=120.0, slot_beats=8.0, src_span_beats=8.0, dst_bpm=90.0
    )
    assert fitted is False and abs(ratio - 1.0) < 1e-6
    # slot within bounds → fitted
    out2, ratio2, fitted2 = assemble.fit_chop_to_slot(
        chunk, SR, src_bpm=120.0, slot_beats=8.0, src_span_beats=8.0, dst_bpm=110.0
    )
    assert fitted2 is True
    assert len(out2) == pytest.approx(8.0 * 60.0 / 110.0 * SR, rel=0.05)


def test_pitch_shift_changes_pitch():
    manifest, bed = _manifest_and_bed()
    cand = manifest["candidates"][0]
    from toolshop.flip import chops
    chunk = chops.slice_candidate(bed, SR, cand)
    shifted, _, _ = assemble.fit_chop_to_slot(
        chunk, SR, src_bpm=120.0, slot_beats=8.0, src_span_beats=8.0,
        dst_bpm=120.0, semitones=-4.0,
    )
    import librosa
    f_orig = np.median(librosa.yin(chunk[1000:20000], fmin=80, fmax=400, sr=SR))
    f_new = np.median(librosa.yin(shifted[1000:20000], fmin=60, fmax=400, sr=SR))
    # -4 st ≈ ratio 0.7937
    assert f_new / f_orig == pytest.approx(2 ** (-4 / 12), rel=0.08)


def test_render_beat_full_stack():
    manifest, bed = _manifest_and_bed()
    placements = [assemble.Placement("cand_000", 0.0, 16.0, semitones=-4.0, fit_slot=True)]
    pattern = drums.drill_pattern(bars=4, ghost_snare=False)
    events = drums.grid_events(pattern, bpm=178.2)
    kick = np.zeros(int(0.3 * SR), dtype=np.float32)
    t = np.arange(kick.size) / SR
    kick[:] = np.sin(2 * np.pi * 50 * t) * np.exp(-t / 0.08)
    from toolshop.flip import bass808
    notes = [bass808.Note808(0.0, 2.0, 36.0), bass808.Note808(2.0, 2.0, 43.0)]
    sub = bass808.render_808(notes, SR)
    res = assemble.render_beat(
        bed, SR, manifest, placements, bpm=178.2,
        drum_events=events, one_shots={"kick": kick},
        bass808_audio=sub, src_bpm=120.0, total_beats=16.0,
    )
    assert np.abs(res.audio).max() > 0.3
    assert res.audio.size > int(16.0 * (60.0 / 178.2) * SR)


def test_render_beat_bed_lane():
    """m3: a pre-rendered bed lane mixes in under the "bed" gain key."""
    manifest, bed = _manifest_and_bed()
    t = np.arange(int(8 * SR)) / SR
    lane = (0.5 * np.sin(2 * np.pi * 330 * t)).astype(np.float32)
    res = assemble.render_beat(
        bed, SR, manifest, [], bpm=120.0, bed_lane=lane,
        total_beats=16.0, mix_levels={"bed": 0.5},
    )
    assert np.abs(res.audio).max() > 0.15
    # gain=0 silences the lane
    res0 = assemble.render_beat(
        bed, SR, manifest, [], bpm=120.0, bed_lane=lane,
        total_beats=16.0, mix_levels={"bed": 0.0},
    )
    assert np.abs(res0.audio).max() == pytest.approx(0.0)
