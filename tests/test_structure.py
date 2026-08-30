"""Tests for structural segmentation (H2-M2).

The implementation being replaced returned `[]` for every track ever analysed —
`librosa.segment.agglomerative(chroma, k=None)` always raises, and a bare
`except Exception: return []` hid it. So these assert on *content*, not merely
that a list comes back: a test that accepted `[]` would have passed against the
broken version for its entire life.
"""

from __future__ import annotations

import numpy as np
import pytest

from toolshop import structure


def synth_track(pattern="ABAB", seg_seconds=8.0, sr=22050):
    """Build audio whose sections are different chords, in a known order."""
    chords = {
        "A": [261.63, 329.63, 392.00],   # C major
        "B": [349.23, 440.00, 523.25],   # F major
        "C": [196.00, 246.94, 293.66],   # G major
    }
    parts = []
    for label in pattern:
        t = np.linspace(0, seg_seconds, int(sr * seg_seconds), endpoint=False)
        tone = sum(np.sin(2 * np.pi * f * t) for f in chords[label]) / 3.0
        # A soft click per second gives beat_track something to find.
        click = np.zeros_like(t)
        click[:: int(sr * 0.5)] = 1.0
        parts.append(tone * 0.8 + click * 0.2)
    return np.concatenate(parts).astype(np.float32), sr


# ---------------------------------------------------------------- boundary count


def test_estimate_segment_count_scales_with_duration():
    assert structure.estimate_segment_count(0) == structure.MIN_SEGMENTS
    assert structure.estimate_segment_count(150, target_s=15) == 10
    assert structure.estimate_segment_count(10_000) == structure.MAX_SEGMENTS
    assert structure.estimate_segment_count(1) == structure.MIN_SEGMENTS


def test_never_passes_none_to_librosa():
    """The exact defect: k=None raises inside librosa on every call."""
    for d in (0, 0.5, 30, 200, 100_000):
        k = structure.estimate_segment_count(d)
        assert isinstance(k, int) and k >= structure.MIN_SEGMENTS


# ---------------------------------------------------------------- real analysis


def test_returns_segments_for_a_real_signal():
    """A test that tolerated an empty list would have passed against the bug."""
    y, sr = synth_track("ABAB")
    r = structure.segment_track(y, sr)
    assert r["segments"], "segmentation returned nothing - the old bug"
    assert r["n_segments"] == len(r["segments"])
    assert r["duration"] > 0


def test_segments_tile_the_track_without_gaps_or_overlaps():
    y, sr = synth_track("ABAB")
    segs = structure.segment_track(y, sr)["segments"]
    assert segs[0]["start"] == pytest.approx(0.0, abs=0.5)
    for a, b in zip(segs, segs[1:]):
        assert b["start"] == pytest.approx(a["end"], abs=0.01), "gap or overlap between segments"


def test_repeated_material_shares_a_class():
    """The point of repetition classes: A-material must group with A-material.

    `n_segments` is given explicitly so this tests *clustering*, not the
    duration->boundary-count guess (covered separately above). The default target
    of 15 s/segment would ask for 3 boundaries on this 40 s fixture and could not
    find the 4 real ones.

    This test caught a genuine bug: class count was capped at
    `min(n_classes, n_segments)`, so 4 segments with 4 clusters gave every segment
    its own class and repetition could never be detected.
    """
    y, sr = synth_track("ABAB", seg_seconds=10.0)
    segs = structure.segment_track(y, sr, n_segments=4)["segments"]
    classes = [s["segment_class"] for s in segs]
    assert classes == ["A", "B", "A", "B"], f"ABAB material should classify as ABAB, got {classes}"
    assert all(s["repetitions"] == 2 for s in segs), "each class appears twice"


def test_no_segment_is_shorter_than_the_minimum():
    """A 31 s real track produced a 0.5 s opening sliver before merging."""
    y, sr = synth_track("ABCAB", seg_seconds=6.0)
    r = structure.segment_track(y, sr)
    if len(r["segments"]) > 1:
        assert min(s["duration"] for s in r["segments"]) >= structure.MIN_SEGMENT_SECONDS - 0.01


def test_letters_start_at_A_after_merging():
    """A collapsed track must not come back labelled 'B'."""
    y, sr = synth_track("AA", seg_seconds=4.0)
    segs = structure.segment_track(y, sr)["segments"]
    assert segs[0]["segment_class"] == "A"


def test_repetition_counts_match_the_letters_present():
    y, sr = synth_track("ABAB", seg_seconds=10.0)
    segs = structure.segment_track(y, sr, n_segments=4)["segments"]
    from collections import Counter
    actual = Counter(s["segment_class"] for s in segs)
    for s in segs:
        assert s["repetitions"] == actual[s["segment_class"]], (
            "repetitions must be recounted after merging, not before"
        )


def test_most_repeated_class_is_actually_the_most_repeated():
    y, sr = synth_track("ABAB", seg_seconds=10.0)
    r = structure.segment_track(y, sr, n_segments=4)
    from collections import Counter
    counts = Counter(s["segment_class"] for s in r["segments"])
    assert counts[r["most_repeated_class"]] == max(counts.values())


def test_does_not_fabricate_verse_chorus_labels():
    """The replaced code emitted 'chorus' from `i % 2`. Nothing here may claim that."""
    y, sr = synth_track("ABAB")
    r = structure.segment_track(y, sr)
    blob = str(r).lower()
    for fabricated in ("chorus", "verse", "intro", "outro", "bridge"):
        assert fabricated not in blob, (
            f"'{fabricated}' is not derivable from this analysis and must not be emitted"
        )


def test_very_short_input_returns_a_single_span_not_an_error():
    y, sr = synth_track("A", seg_seconds=1.0)
    r = structure.segment_track(y, sr)
    assert r["n_segments"] >= 1
    assert r["segments"][0]["segment_class"] == "A"


def test_failure_raises_rather_than_returning_empty():
    """Silent `except: return []` is how the original bug survived."""
    with pytest.raises(Exception):
        structure.segment_track(np.array([]), 0)


# ---------------------------------------------------------------- merge helper


def test_merge_short_absorbs_slivers():
    segs = [
        structure.Segment(0.0, 0.5, "A", 0),
        structure.Segment(0.5, 30.0, "B", 0),
    ]
    out = structure._merge_short(segs, 4.0)
    assert len(out) == 1
    assert out[0].start == 0.0 and out[0].end == 30.0


def test_merge_short_prefers_a_neighbour_of_the_same_class():
    segs = [
        structure.Segment(0.0, 20.0, "A", 0),
        structure.Segment(20.0, 21.0, "B", 0),
        structure.Segment(21.0, 41.0, "B", 0),
    ]
    out = structure._merge_short(segs, 4.0)
    assert [s.segment_class for s in out] == ["A", "B"]
    assert out[1].start == 20.0, "sliver should have joined its same-class neighbour"


def test_merge_short_leaves_long_segments_alone():
    segs = [structure.Segment(0.0, 20.0, "A", 0), structure.Segment(20.0, 40.0, "B", 0)]
    assert len(structure._merge_short(segs, 4.0)) == 2
