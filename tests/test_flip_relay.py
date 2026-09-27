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


def test_relay_manifest_deterministic():
    beats = [i * 0.5 for i in range(24)]
    phrases = relay.detect_phrases(_words(), None, SR)
    relay.annotate_grid(phrases, beats)
    pl = relay.map_phrases(phrases, bpm=133.65, bars=4)
    m1 = relay.relay_manifest(phrases, pl, 133.65, "vocals.wav")
    m2 = relay.relay_manifest(phrases, pl, 133.65, "vocals.wav")
    assert m1 == m2
    assert m1["phrase_count"] == 2 and m1["placed"] == 2
