"""RT60 estimation (CHANGELOG #056, JOURNAL.md J-063).

These live in `tests/` deliberately. `wav_reverse_engineer` ships its own
`tests/test_effects_analyzer.py`, but `pytest.ini` sets `testpaths = tests`, so
that file has never been collected — and its only RT60 assertion is
`assertIn('rt60_seconds', res)`, a presence check that passes on any number
whatsoever. That is how an estimator that returned the track's own duration
survived a 221-track corpus run.
"""

import numpy as np
import pytest

# `wav_reverse_engineer` is imported from `projects/`, which is **gitignored** —
# so it is present on the machine that produced the corpus and absent from a
# fresh clone. Skip rather than error there; see JOURNAL.md J-064.
effects_analyzer = pytest.importorskip(
    "wav_reverse_engineer.audio_analyzer.effects_analyzer",
    reason="wav_reverse_engineer lives in the gitignored projects/ tree",
)

MAX_RT60_SECONDS = effects_analyzer.MAX_RT60_SECONDS
MIN_RT60_SECONDS = effects_analyzer.MIN_RT60_SECONDS
analyze_effects = effects_analyzer.analyze_effects
estimate_rt60 = effects_analyzer.estimate_rt60
estimate_rt60_detailed = effects_analyzer.estimate_rt60_detailed

SR = 22050


def _decaying_bursts(rt60_seconds, sr=SR, n_bursts=12, spacing=1.0, seed=0):
    """Noise bursts each decaying at a known RT60 — a signal whose answer we know.

    Amplitude falls by 60 dB (a factor of 1000) in `rt60_seconds`, so
    A(t) = exp(-ln(1000) * t / rt60).
    """
    rng = np.random.default_rng(seed)
    out = np.zeros(int(sr * spacing * (n_bursts + 1)), dtype=np.float64)
    k = np.log(1000.0) / rt60_seconds
    # NOTE: at `spacing=1.0` a burst is capped at 1 s, so an RT60 above ~1.5 s is
    # truncated by the FIXTURE rather than by the estimator. Accuracy measured on
    # this generator: 0.1-0.8% up to 1.2 s, 5.6% at 2.0 s for that reason.
    burst_len = int(min(spacing, rt60_seconds * 1.2) * sr)
    t = np.arange(burst_len) / sr
    for i in range(n_bursts):
        start = int(i * spacing * sr)
        burst = rng.normal(0.0, 1.0, burst_len) * np.exp(-k * t)
        out[start:start + burst_len] += burst
    return (out / np.max(np.abs(out))).astype(np.float32)


# --- the regression that matters --------------------------------------------


@pytest.mark.parametrize("duration", [10.0, 20.0, 40.0])
def test_steady_noise_is_refused_not_scaled_to_its_own_length(duration):
    """The original defect, in its minimal form.

    White noise has no reverb. The old estimator returned 14.78 / 29.40 / 58.85 s
    for these three durations — 1.47x the input length, every time. Anything that
    scales with duration is measuring the file, not the room.
    """
    rng = np.random.default_rng(0)
    noise = rng.normal(0.0, 0.1, int(SR * duration)).astype(np.float32)

    result = estimate_rt60(noise, SR)

    assert result is None or result < duration / 4.0, (
        f"rt60 {result} tracks the {duration}s input length"
    )


def test_rt60_does_not_change_when_the_same_signal_is_made_longer():
    """The direct guard: doubling the material must not double the answer.

    This is the assertion whose absence let the defect reach 221 dossiers.
    """
    short = _decaying_bursts(0.4, n_bursts=8)
    long = np.concatenate([short, short])

    a = estimate_rt60(short, SR)
    b = estimate_rt60(long, SR)

    assert a is not None and b is not None
    assert abs(a - b) < 0.1 * a, f"rt60 moved from {a:.3f} to {b:.3f} on more of the same audio"


# --- correctness against a known answer -------------------------------------


@pytest.mark.parametrize("truth", [0.3, 0.6, 1.2])
def test_recovers_a_known_decay(truth):
    got = estimate_rt60(_decaying_bursts(truth), SR)

    assert got is not None, f"no decay measured in a signal built to decay at {truth}s"
    # Measured error on this fixture is 0.1-0.8%. The 10% bound is deliberately
    # far tighter than "passes": a loose tolerance would go green on an estimator
    # that is merely in the right order of magnitude, which is exactly how the
    # original defect survived its own test.
    assert abs(got - truth) / truth < 0.10, f"expected ~{truth}s, got {got:.3f}s"


def test_a_longer_reverb_reads_as_longer():
    """Ordering is weaker than accuracy but it is the property callers rely on."""
    short = estimate_rt60(_decaying_bursts(0.3), SR)
    long = estimate_rt60(_decaying_bursts(1.2), SR)

    assert short is not None and long is not None
    assert long > short


# --- refusals ----------------------------------------------------------------


def test_silence_is_refused():
    detail = estimate_rt60_detailed(np.zeros(SR * 5, dtype=np.float32), SR)

    assert detail["rt60_seconds"] is None
    assert "silent" in detail["rt60_reason"]


def test_a_constant_tone_is_refused():
    """A sustained tone never decays, so there is nothing to measure."""
    t = np.arange(SR * 5) / SR
    tone = (0.5 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)

    assert estimate_rt60(tone, SR) is None


def test_too_short_is_refused():
    detail = estimate_rt60_detailed(np.zeros(100, dtype=np.float32), SR)

    assert detail["rt60_seconds"] is None
    assert detail["rt60_windows"] == 0


def test_a_refusal_says_why_and_counts_what_it_found():
    """J-054's rule applied here: the reader must not have to infer."""
    rng = np.random.default_rng(1)
    detail = estimate_rt60_detailed(rng.normal(0, 0.1, SR * 10).astype(np.float32), SR)

    assert set(detail) >= {"rt60_seconds", "rt60_windows", "rt60_reason"}
    if detail["rt60_seconds"] is None:
        assert detail["rt60_reason"]
        assert isinstance(detail["rt60_windows"], int)


def test_unmeasurable_is_none_not_zero():
    """0.0 is a plausible-looking value a caller will happily average. None is not."""
    assert estimate_rt60(np.zeros(SR * 5, dtype=np.float32), SR) is None


# --- the value stays inside its own stated bounds ----------------------------


@pytest.mark.parametrize("truth", [0.3, 0.6, 1.2])
def test_result_respects_the_declared_plausible_band(truth):
    got = estimate_rt60(_decaying_bursts(truth), SR)

    assert got is None or MIN_RT60_SECONDS <= got <= MAX_RT60_SECONDS


# --- the dossier surface -----------------------------------------------------


def test_analyze_effects_carries_the_evidence_not_just_the_number():
    out = analyze_effects(_decaying_bursts(0.5), SR)

    for key in ("rt60_seconds", "rt60_windows", "rt60_reason"):
        assert key in out, f"{key} missing from the effects block"


def test_analyze_effects_still_emits_its_other_fields():
    """The RT60 change must not disturb the rest of the block."""
    out = analyze_effects(_decaying_bursts(0.5), SR)

    for key in ("spectral_tilt_db_per_decade", "thd_ratio", "compression_index"):
        assert key in out
