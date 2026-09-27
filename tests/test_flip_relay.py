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


def test_map_phrases_preserves_syncopation():
    beats = [i * 0.5 for i in range(24)]
    phrases = relay.detect_phrases(_words(), None, SR)
    relay.annotate_grid(phrases, beats)
    pl = relay.map_phrases(phrases, bpm=140.0, bars=4, preserve_fraction=True)
    beat_s = 60.0 / 140.0
    # phrase 0 → bar0 beat2 → t = 2*beat_s; NOT snapped to downbeat
    assert pl[0].start_s == pytest.approx(2.0 * beat_s)
    assert pl[0].target_beat_fraction == pytest.approx(2.0)
    # quantized variant lands on downbeats
    plq = relay.map_phrases(phrases, bpm=140.0, bars=4, preserve_fraction=False)
    assert plq[0].start_s == pytest.approx(0.0)


def test_map_phrases_flags_overlaps_bounded_warp():
    # Two phrases back to back in source → on a faster grid they collide.
    words = [
        FakeWord("a", 0.0, 0.4), FakeWord("b", 0.42, 0.8), FakeWord("c", 0.82, 1.6),
        FakeWord("d", 2.0, 2.4),
    ]
    phrases = relay.detect_phrases(words, None, SR, min_gap_ms=300.0)
    beats = [i * 0.5 for i in range(24)]
    relay.annotate_grid(phrases, beats)
    pl = relay.map_phrases(phrases, bpm=178.2, bars=4, preserve_fraction=True)
    if len(pl) >= 2:
        # if phrase 0 runs into phrase 1's anchor, warp is reported, not applied
        assert pl[0].warp <= 1.0
        if pl[0].warp < 1.0 / relay.MAX_WARP:
            assert not pl[0].warped
            assert pl[0].notes


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
