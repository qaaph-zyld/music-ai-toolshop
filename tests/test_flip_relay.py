"""Tests for toolshop.flip.relay — W4 vocal phrase re-lay."""

import numpy as np
import pytest

from toolshop.flip import relay


SR = 22050


class FakeWord:
    def __init__(self, text, start, end):
        self.text = text
        self.start = start
        self.end = end
        self.probability = 0.9


def _vocal_with_gaps(sr=SR):
    """Tone bursts at 1.0–1.4s and 3.0–3.4s — silence between."""
    n = int(5.0 * sr)
    y = np.zeros(n, dtype=np.float32)
    for start, dur in ((1.0, 0.4), (3.0, 0.4)):
        t = np.arange(int(dur * sr)) / sr
        y[int(start * sr) : int(start * sr) + t.size] = 0.5 * np.sin(2 * np.pi * 300 * t)
    return y


def _words():
    # two phrases: gap 1.6s between end of w3 (1.4) and start of w4 (3.0)
    return [
        FakeWord("word", 1.00, 1.15),
        FakeWord("word", 1.18, 1.30),
        FakeWord("word", 1.32, 1.40),
        FakeWord("word", 3.00, 3.15),
        FakeWord("word", 3.18, 3.40),
    ]


def test_detect_phrases_splits_on_confirmed_gap():
    y = _vocal_with_gaps()
    phrases = relay.detect_phrases(_words(), y, SR, min_gap_ms=300.0)
    assert len(phrases) == 2
    assert phrases[0].word_count == 3
    assert phrases[1].word_count == 2
    assert phrases[1].gap_before_ms == pytest.approx(1600.0, abs=50)


def test_detect_phrases_no_audio_falls_back_to_gap_only():
    phrases = relay.detect_phrases(_words(), None, SR)
    assert len(phrases) == 2


def test_detect_phrases_subthreshold_gap_keeps_phrase():
    words = _words()[:3] + [FakeWord("word", 1.55, 1.7)]  # 150 ms gap
    y = _vocal_with_gaps()
    phrases = relay.detect_phrases(words, y, SR, min_gap_ms=300.0)
    assert len(phrases) == 1


def test_annotate_grid_beat_fraction():
    beats = [i * 0.5 for i in range(24)]  # 120 BPM, 4/4
    phrases = relay.detect_phrases(_words(), None, SR)
    relay.annotate_grid(phrases, beats)
    # phrase 0 starts at 1.0s → beat 2.0 → bar 0, fraction 2.0
    assert phrases[0].source_bar == 0
    assert phrases[0].beat_fraction == pytest.approx(2.0)
    # phrase 1 at 3.0s → beat 6.0 → bar 1 fraction 2.0
    assert phrases[1].source_bar == 1
    assert phrases[1].beat_fraction == pytest.approx(2.0)


def test_map_phrases_places_at_source_felt_time():
    """F2: zero-stretch relay — phrases land at their SOURCE absolute time, so
    both grid arms get an IDENTICAL schedule. The written-grid fields are
    reporting only (target_beat = source_beat * bpm_written / bpm_source)."""
    beats = [i * 0.5 for i in range(24)]  # source 120 BPM, 4/4
    phrases = relay.detect_phrases(_words(), None, SR)
    relay.annotate_grid(phrases, beats)
    # phrase 0 starts at 1.0s in the source → must land at 1.0s on BOTH arms
    pl_fast = relay.map_phrases(phrases, bpm=178.2, bars=4, bpm_source=120.0)
    pl_slow = relay.map_phrases(phrases, bpm=133.65, bars=4, bpm_source=120.0)
    assert pl_fast[0].start_s == pytest.approx(phrases[0].start_s, abs=1e-6)
    assert pl_slow[0].start_s == pytest.approx(phrases[0].start_s, abs=1e-6)
    # identical schedule regardless of written bpm
    assert [p.start_s for p in pl_fast] == [p.start_s for p in pl_slow]
    # written-grid reporting rescales: source_beat 2.0 @120 → 2.0*178.2/120 = 2.97
    assert pl_fast[0].target_beat_fraction == pytest.approx(
        (2.0 * 178.2 / 120.0) % 4.0, abs=1e-3
    )


def test_map_phrases_preserves_syncopation():
    """F2: syncopation is preserved because placement is at source time; the
    within-bar fraction is reported (not applied) on the written grid."""
    beats = [i * 0.5 for i in range(24)]
    phrases = relay.detect_phrases(_words(), None, SR)
    relay.annotate_grid(phrases, beats)
    pl = relay.map_phrases(phrases, bpm=140.0, bars=4, bpm_source=120.0)
    # phrase 0 → source 1.0s → placed at 1.0s (NOT snapped to a written downbeat)
    assert pl[0].start_s == pytest.approx(1.0)
    # written-grid fraction is reported, non-zero (syncopation preserved)
    assert pl[0].target_beat_fraction != pytest.approx(0.0, abs=1e-3)


def test_map_phrases_flags_overlaps_source_time():
    """F2: at source-time placement, an overlap means the source itself had a
    short gap relative to phrase duration — reported, not stretched. The
    buggy written-bpm semantic (phrases colliding because they were placed at
    written-beat positions) is gone: placement no longer depends on bpm."""
    # Two phrases back to back in source → short gap relative to duration.
    words = [
        FakeWord("a", 0.0, 0.4), FakeWord("b", 0.42, 0.8), FakeWord("c", 0.82, 1.6),
        FakeWord("d", 2.0, 2.4),
    ]
    phrases = relay.detect_phrases(words, None, SR, min_gap_ms=300.0)
    beats = [i * 0.5 for i in range(24)]
    relay.annotate_grid(phrases, beats)
    # Placement is identical at both written bpms — the old collision came
    # from placing at written-beat positions; that no longer happens.
    pl_fast = relay.map_phrases(phrases, bpm=178.2, bars=4, bpm_source=120.0)
    pl_slow = relay.map_phrases(phrases, bpm=133.65, bars=4, bpm_source=120.0)
    assert [p.start_s for p in pl_fast] == [p.start_s for p in pl_slow]
    if len(pl_fast) >= 2:
        # placed starts equal the source phrase starts (zero-stretch)
        assert pl_fast[0].start_s == pytest.approx(phrases[0].start_s, abs=1e-6)
        assert pl_fast[1].start_s == pytest.approx(phrases[1].start_s, abs=1e-6)
        # warp is reported as the gap/duration ratio, never applied
        assert pl_fast[0].warp <= 1.0
        if pl_fast[0].warp < 1.0 / relay.MAX_WARP:
            assert not pl_fast[0].warped
            assert pl_fast[0].notes


def test_strip_phrase_padded_and_faded():
    y = _vocal_with_gaps()
    phrases = relay.detect_phrases(_words(), y, SR)
    chunk = relay.strip_phrase(y, SR, phrases[0])
    # ~0.4s of content + 2×60ms pad ≈ 0.52s ± snap
    assert abs(len(chunk) / SR - 0.52) < 0.06
    assert abs(chunk[0]) < 0.3 and abs(chunk[-1]) < 0.3


# --- W4: lattice-anchored placement -----------------------------------------


def test_map_phrases_lattice_identical_schedule_both_arms():
    """A20: lattice placement gives every arm the SAME absolute schedule —
    start_s must not depend on the written bpm it is reported against."""
    beats = [i * 0.5 for i in range(24)]  # source 120 BPM grid
    phrases = relay.detect_phrases(_words(), None, SR)
    relay.annotate_grid(phrases, beats)
    pl_a = relay.map_phrases(phrases, bpm=178.2, bars=99, bpm_source=120.0,
                             lattice_bpm=89.1)
    pl_b = relay.map_phrases(phrases, bpm=133.65, bars=99, bpm_source=120.0,
                             lattice_bpm=89.1)
    assert len(pl_a) == len(pl_b) == 2
    assert [p.start_s for p in pl_a] == [p.start_s for p in pl_b]
    # identical audio schedule; written-grid reporting differs per arm
    assert pl_a[0].target_bar != pl_b[0].target_bar or (
        pl_a[0].target_beat_fraction != pl_b[0].target_beat_fraction
    )


def test_map_phrases_lattice_anchor_bounds():
    """Every placed phrase is either snapped within ANCHOR_TOLERANCE_MS or
    floats at its nominal mapped position (correction exactly 0)."""
    beats = [i * 0.5 for i in range(24)]
    phrases = relay.detect_phrases(_words(), None, SR)
    relay.annotate_grid(phrases, beats)
    pl = relay.map_phrases(phrases, bpm=178.2, bars=99, lattice_bpm=89.1)
    for p in pl:
        assert 0.0 <= p.anchor_offset_ms <= relay.ANCHOR_TOLERANCE_MS + 1e-6
        if p.anchor_kind == "float":
            assert p.anchor_offset_ms == 0.0
            assert p.anchor_beat == -1.0
        else:
            assert p.anchor_beat >= 0.0
    # snapped onsets sit exactly on lattice positions
    snapped = [p for p in pl if p.anchor_kind != "float"]
    felt_s = 60.0 / 89.1
    for p in snapped:
        assert (p.start_s / felt_s) == pytest.approx(round(p.start_s / felt_s))


def test_map_phrases_lattice_downbeat_preferred_and_bias_early():
    """Downbeats win ties of class; equal-class ties place on the EARLIER
    anchor (laid-back correction is early→on, never late)."""
    # nominal 3.99 beats -> within 30 ms of beat 4 (downbeat, phase 0)
    beat_s = 60.0 / 89.1
    a, kind = relay._choose_anchor(4.0 - 0.02 / beat_s, beat_s, 30.0)
    assert a == 4.0 and kind == "downbeat"
    # equal-class tie: nominal 2.0, beats 0 and 4 both downbeats at equal
    # distance inside a wide tolerance -> the EARLIER anchor wins
    a, kind = relay._choose_anchor(2.0, beat_s, 1400.0)
    assert a == 0.0 and kind == "downbeat"
    # nothing inside tolerance -> float
    a, kind = relay._choose_anchor(0.5, beat_s, 30.0)
    assert a is None and kind == "float"


def test_map_phrases_lattice_float_preserves_syncopation():
    """A phrase deep inside a bar floats at its source beat fraction — no
    quantize-away-the-swing."""
    words = [FakeWord("a", 0.0, 0.2), FakeWord("b", 0.8, 1.0)]
    phrases = relay.detect_phrases(words, None, SR, min_gap_ms=300.0)
    assert len(phrases) == 2
    beats = [i * 0.5 for i in range(24)]  # 120 BPM: 0.8s = beat 1.6
    relay.annotate_grid(phrases, beats)
    pl = relay.map_phrases(phrases, bpm=178.2, bars=99, lattice_bpm=89.1)
    p1 = pl[1]
    # source beat 1.6 -> nominal 1.6*felt_s; 0.6*673ms = 404ms off -> float
    assert p1.anchor_kind == "float"
    assert p1.anchor_offset_ms == 0.0
    felt_s = 60.0 / 89.1
    assert p1.start_s == pytest.approx(1.6 * felt_s, abs=1e-3)


def test_detect_strips_energy_splits_on_gaps():
    y = _vocal_with_gaps()  # bursts at 1.0-1.4 and 3.0-3.4
    strips = relay.detect_strips_energy(y, SR, min_gap_ms=300.0)
    assert len(strips) == 2
    assert strips[0].start_s == pytest.approx(1.0, abs=0.1)
    assert strips[1].start_s == pytest.approx(3.0, abs=0.1)


def test_detect_strips_energy_merges_short_gaps():
    sr = SR
    y = np.zeros(int(3.0 * sr), dtype=np.float32)
    for start, dur in ((0.5, 0.3), (0.95, 0.3)):  # 150 ms gap -> merge
        t = np.arange(int(dur * sr)) / sr
        y[int(start * sr): int(start * sr) + t.size] = 0.4 * np.sin(2 * np.pi * 300 * t)
    strips = relay.detect_strips_energy(y, sr, min_gap_ms=300.0)
    assert len(strips) == 1
    assert strips[0].end_s == pytest.approx(1.25, abs=0.1)


def test_extend_grid_left_covers_phrase_before_first_beat():
    bt = [8.0 + i * 0.66 for i in range(10)]
    ext = relay.extend_grid_left(bt, fill_to_s=0.0)
    assert ext[0] < 0.5  # grid reaches back to ~t=0
    assert len(ext) > len(bt)
    # spacing preserved
    assert np.diff(ext).max() == pytest.approx(np.median(np.diff(bt)), abs=1e-6)


def test_load_transcript_words(tmp_path):
    import json
    payload = {"segments": [{"start": 0, "end": 1, "text": "x",
                             "words": [{"text": "hi", "start": 0.1, "end": 0.2,
                                        "probability": 0.9}]}]}
    p = tmp_path / "t.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    words = relay.load_transcript_words(p)
    assert len(words) == 1 and words[0].start == pytest.approx(0.1)


def test_load_transcript_words_rejects_empty(tmp_path):
    import json
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({"segments": []}), encoding="utf-8")
    with pytest.raises(ValueError):
        relay.load_transcript_words(p)


def test_summarize_anchors_pass_bar():
    class P:
        pass
    pl = []
    for i, (off, kind) in enumerate([(10.0, "downbeat"), (0.0, "float"), (25.0, "beat")]):
        x = P(); x.anchor_offset_ms = off; x.anchor_kind = kind
        pl.append(x)
    s = relay.summarize_anchors(pl)
    assert s["median_anchor_offset_ms"] == pytest.approx(10.0)
    assert s["anchor_pass_median_le_30ms"] is True
    assert s["snapped"] == 2 and s["floated"] == 1


def test_render_vocal_lane_onset_lands_on_placement_not_pad():
    """F4: strip_phrase's pad precedes the onset; the renderer must land the
    ONSET on pl.start_s, not the pad (otherwise every phrase sits ~60 ms late
    plus the zero-crossing snap delta)."""
    y = _vocal_with_gaps()  # tone burst 1.0–1.4 s
    phrases = relay.detect_phrases(_words(), y, SR)
    strip = relay.strip_phrase(y, SR, phrases[0])
    assert 0.0 < phrases[0].pad_s <= relay.PAD_MS / 1000.0 + 0.012
    pl = [relay.RelayPlacement(phrase_index=phrases[0].index, target_bar=0,
                               target_beat_fraction=0.0, start_s=2.0,
                               warp=1.0, warped=False)]
    lane, ev = relay.render_vocal_lane({phrases[0].index: strip}, pl, phrases,
                                       SR, total_s=4.0, apply_warp=False)
    # onset = first lane sample above threshold ≈ 2.0 s, NOT 2.0 + pad
    idx = int(np.argmax(np.abs(lane) > 0.05))
    assert abs(idx / SR - 2.0) < 0.02
    assert ev[0]["rendered"] and ev[0]["start_s"] == 2.0


def test_phrase_xcorr_centres_on_effective_onset():
    """F5: the local xcorr window must centre on the acoustic onset inside
    the placed strip — whisper word-starts + pad precede it and would
    otherwise land the window on silence."""
    sr = SR
    hop = 512
    frame_s = hop / sr
    n_f = int(6.0 / frame_s) + 8
    vocal_env = np.zeros(n_f)
    drum_env = np.zeros(n_f)
    onset_f = int(1.4 / frame_s)  # acoustic onset ~0.4 s after word start 1.0
    pat = [0, 3, 7, 10, 14, 19, 25, 30]  # aperiodic syllable train
    for k in pat:
        vocal_env[onset_f + k] = 1.0
        drum_env[onset_f + k + 2] = 1.0   # drums trail by 2 frames ≈ 46 ms

    class P:
        pass
    pl = P(); pl.phrase_index = 0; pl.start_s = 1.0
    ph = P(); ph.index = 0; ph.start_s = 1.0; ph.end_s = 4.0
    rows = relay.phrase_xcorr_table(vocal_env, drum_env, [pl], sr, hop=hop,
                                    window_ms=400.0, phrases=[ph])
    assert rows[0]["lag_ms"] == pytest.approx(2 * frame_s * 1000.0,
                                              abs=frame_s * 1000.0)
    assert rows[0]["onset_delay_ms"] == pytest.approx(400.0, abs=40.0)


def test_phrase_xcorr_reports_nearest_hit():
    """Each row reports the signed distance from the effective onset to the
    nearest drum hit (negative = vocal onset lands before the hit)."""
    sr = SR
    hop = 512
    frame_s = hop / sr
    n_f = int(4.0 / frame_s) + 8
    vocal_env = np.zeros(n_f)
    drum_env = np.zeros(n_f)
    onset_f = int(1.0 / frame_s)
    for k in (0, 3, 8, 11, 17):
        vocal_env[onset_f + k] = 1.0
        drum_env[onset_f + k] = 1.0

    class P:
        pass
    pl = P(); pl.phrase_index = 0; pl.start_s = 1.0
    ph = P(); ph.index = 0; ph.start_s = 1.0; ph.end_s = 2.5
    rows = relay.phrase_xcorr_table(vocal_env, drum_env, [pl], sr, hop=hop,
                                    phrases=[ph],
                                    drum_hit_times_s=[1.02])
    assert rows[0]["nearest_hit_ms"] == pytest.approx(-20.0, abs=8.0)


def test_relay_manifest_deterministic():
    beats = [i * 0.5 for i in range(24)]
    phrases = relay.detect_phrases(_words(), None, SR)
    relay.annotate_grid(phrases, beats)
    pl = relay.map_phrases(phrases, bpm=133.65, bars=4)
    m1 = relay.relay_manifest(phrases, pl, 133.65, "vocals.wav")
    m2 = relay.relay_manifest(phrases, pl, 133.65, "vocals.wav")
    assert m1 == m2
    assert m1["phrase_count"] == 2 and m1["placed"] == 2
