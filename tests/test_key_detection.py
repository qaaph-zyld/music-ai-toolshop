"""Tests for Krumhansl-Schmuckler key detection (H2-M1).

These assert against **known answers**, not merely that a value comes back. The
implementation being replaced returned a value every time and was wrong: it chose
the tonic by loudness and decided mode from the absolute magnitude of one chroma
bin, reporting "major" for 7 of 8 measured tracks.
"""

from __future__ import annotations

import numpy as np
import pytest

from toolshop import key_detection as kd


def chroma_for(pitch_classes, tonic_boost=1.0, base=0.05):
    """Build a synthetic chroma vector with energy on the given pitch classes."""
    c = np.full(12, base, dtype=float)
    for pc in pitch_classes:
        c[pc % 12] = 1.0
    if pitch_classes:
        c[pitch_classes[0] % 12] += tonic_boost
    return c


# Scale degrees as semitone offsets from the tonic.
MAJOR_SCALE = [0, 2, 4, 5, 7, 9, 11]
MINOR_SCALE = [0, 2, 3, 5, 7, 8, 10]  # natural minor


@pytest.mark.parametrize("tonic,name", [(0, "C"), (7, "G"), (2, "D"), (9, "A"), (5, "F")])
def test_major_scales_detect_as_major(tonic, name):
    est = kd.detect_key_from_chroma(chroma_for([(tonic + d) % 12 for d in MAJOR_SCALE]))
    assert est.key == name
    assert est.mode == "major", f"{name} major scale detected as {est.label}"


@pytest.mark.parametrize("tonic,name", [(9, "A"), (4, "E"), (0, "C"), (7, "G")])
def test_minor_scales_detect_as_minor(tonic, name):
    est = kd.detect_key_from_chroma(chroma_for([(tonic + d) % 12 for d in MINOR_SCALE]))
    assert est.key == name
    assert est.mode == "minor", f"{name} minor scale detected as {est.label}"


def test_mode_is_not_decided_by_loudness():
    """The exact defect being replaced.

    The old rule was `mode = "major" if chroma_mean[key] > 0.5 else "minor"`.
    Scaling a chroma vector changes every magnitude but no musical relationship, so
    a correct detector must be invariant to it. The old one would flip.
    """
    quiet = chroma_for([(9 + d) % 12 for d in MINOR_SCALE]) * 0.2   # peak well below 0.5
    loud = chroma_for([(9 + d) % 12 for d in MINOR_SCALE]) * 5.0    # peak well above 0.5

    assert kd.detect_key_from_chroma(quiet).label == kd.detect_key_from_chroma(loud).label
    assert kd.detect_key_from_chroma(loud).mode == "minor", (
        "a loud A-minor scale must still be minor - the old code called this major"
    )


def test_relative_minor_is_reported_as_the_alternate():
    """K-S's known weakness, surfaced rather than hidden.

    C major and A minor share a pitch-class set, so the runner-up should be the
    relative key and the margin should be small.
    """
    est = kd.detect_key_from_chroma(chroma_for(MAJOR_SCALE))
    assert est.key == "C" and est.mode == "major"
    assert (est.alternate_key, est.alternate_mode) == ("A", "minor")
    assert est.margin < 0.5, "relative major/minor should be genuinely close"


def test_confidence_is_higher_for_a_clean_key_than_for_noise():
    clean = kd.detect_key_from_chroma(chroma_for(MAJOR_SCALE))
    rng = np.random.default_rng(42)
    noise = kd.detect_key_from_chroma(rng.random(12))
    assert clean.confidence > noise.confidence


def test_chromatic_input_has_low_confidence():
    """All twelve pitch classes equal - no key. Confidence must not be high."""
    est = kd.detect_key_from_chroma(np.ones(12))
    assert est.confidence < 0.3


def test_rejects_wrong_bin_count():
    with pytest.raises(ValueError, match="12 chroma bins"):
        kd.detect_key_from_chroma(np.ones(7))


def test_to_dict_carries_the_evidence():
    d = kd.detect_key_from_chroma(chroma_for(MAJOR_SCALE)).to_dict()
    assert d["key"] == "C" and d["mode"] == "major"
    assert d["method"] == "krumhansl-schmuckler"
    for field in ("confidence", "alternate_key", "alternate_mode", "margin"):
        assert field in d, f"dossiers need {field} - the roadmap asks for confidence"


def test_label_matches_the_historical_string_form():
    assert kd.detect_key_from_chroma(chroma_for(MAJOR_SCALE)).label == "C major"


def test_transposition_invariance():
    """The same scale shape in every key must detect as that key, in all twelve."""
    for tonic in range(12):
        est = kd.detect_key_from_chroma(chroma_for([(tonic + d) % 12 for d in MAJOR_SCALE]))
        assert est.key == kd.PITCH_CLASSES[tonic]
        assert est.mode == "major"
