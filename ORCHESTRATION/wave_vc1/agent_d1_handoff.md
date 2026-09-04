# Wave 2 / Agent D1 -- Vocal chain differential round-trip harness

Deliverable: `toolshop/vocal_chain/` (new subpackage) -- a differential round-trip
recovery harness answering: given a dry vocal and the same vocal rendered through
a *known* `Chain` (`mastering_tool/tools/chain_dsl/schema.py`), how much of the
chain's parameters can be recovered from the (dry, wet) pair alone?

Files:
- `toolshop/vocal_chain/__init__.py`
- `toolshop/vocal_chain/roundtrip.py` -- `render_known`, `extract_differential`,
  `Recovery`, and one `recover_*` function per stage.
- `tests/test_vocal_chain_roundtrip.py` -- synthetic sweeps + one `@pytest.mark.slow`
  real-audio test.

This is written incrementally as findings land. Do not treat an earlier section as
final until the "Verification" section at the bottom is filled in.

---

## Methods used (one per stage, each honest about what it can't do)

| stage | method | principle |
|---|---|---|
| HPF cutoff | `transfer_function_h1_minus3db` | H1 estimator `H(f)=Pxy(f)/Pxx(f)` (Welch-averaged csd/welch), -3dB crossing found by linear interpolation between bins. pedalboard's `HighpassFilter` *defines* its cutoff as the -3dB point, so this measures the same quantity the DSL sets, not a proxy. |
| EQ band gains | `transfer_function_h1_band_sample` | Same H(f), sampled at a fixed table of standard octave-band centres (31.5Hz-16kHz), each relative to a baseline measured >=1.5 octaves away. `extract_differential` is not told the chain, so it reports a generic band table, not "the" EQ band. |
| Compressor threshold | `rms_io_hinge_fit` | Per-frame (100ms) RMS(dB) in vs out, grid search over a hinge point (0.25dB steps), two independent least-squares lines either side. Guards against reporting a threshold when the two fitted slopes don't actually differ (see "Guard added" below). |
| Compressor ratio | `rms_io_hinge_fit_above_slope` | `1/slope` of the above-hinge line. |
| Compressor makeup | `below_threshold_offset_median` | Median `y_db - x_db` for frames >=6dB below the recovered threshold. |
| Clipper drive | `tanh_waveshaper_inversion` | pedalboard's `Distortion` docstring gives the exact model `y = tanh(x * db_to_gain(drive_db))`. Inverted exactly per-sample: `g = arctanh(y)/x`, `drive_db = 20*log10(median(g))`. Not a curve fit -- an analytic inversion. Only valid when `dry` is genuinely the clipper's input (no upstream stage altered it first). |

## Guard added during development (important finding, not a bug report)

`recover_compressor`'s grid search initially reported a specific-looking
`threshold_db` even for a **bypassed** (identity) chain: fitting two lines to a
perfectly straight input=output line gives ~zero residual for *any* arbitrary
split point, so the search picked whatever candidate happened to minimize
noise first -- a fabricated-looking number for an unidentifiable quantity.
Fixed by checking `|slope_above - slope_below|` against a `MIN_SLOPE_DIFFERENCE`
threshold (0.05); below it, `threshold_db` returns `None` with a reason instead
of a number. `ratio` and `makeup_db` remain well-defined even without a real
hinge (ratio correctly reads ~1.0 = "no compression"; makeup remains a valid
offset measurement) so they are not gated by the same guard.

---

## Recovery table

Every synthetic value below was swept at >=3 points with a fixed-seed test
signal (see `tests/test_vocal_chain_roundtrip.py` for exact generators and
tolerance reasoning). Confidence is this module's own self-reported [0,1]
score, not an external check.

| parameter | signal | set value | recovered | abs error | rel error | method | verdict |
|---|---|---|---|---|---|---|---|
| HPF cutoff (Hz) | white noise | 60.0 | 60.857 | 0.857 | 1.43% | transfer_function_h1_minus3db | RECOVERS |
| HPF cutoff (Hz) | white noise | 90.0 | 90.710 | 0.710 | 0.79% | transfer_function_h1_minus3db | RECOVERS |
| HPF cutoff (Hz) | white noise | 120.0 | 120.688 | 0.688 | 0.57% | transfer_function_h1_minus3db | RECOVERS |
| HPF cutoff (Hz) | click train (broadband cross-check) | 60.0 | 60.520 | 0.520 | 0.87% | transfer_function_h1_minus3db | RECOVERS |
| HPF cutoff (Hz) | click train | 90.0 | 90.094 | 0.094 | 0.10% | transfer_function_h1_minus3db | RECOVERS |
| HPF cutoff (Hz) | click train | 120.0 | 120.330 | 0.330 | 0.28% | transfer_function_h1_minus3db | RECOVERS |
| HPF cutoff (Hz) | white noise, chain fully bypassed | n/a (identity) | **None** | -- | -- | transfer_function_h1_minus3db | HONEST NON-RECOVERY (correct -- no crossing exists) |
| EQ band gain (dB @1000Hz) | white noise | -8.0 | -7.974 | 0.026 | 0.32% | transfer_function_h1_band_sample | RECOVERS |
| EQ band gain (dB @1000Hz) | white noise | 4.0 | 3.988 | 0.012 | 0.29% | transfer_function_h1_band_sample | RECOVERS |
| EQ band gain (dB @1000Hz) | white noise | 10.0 | 9.965 | 0.035 | 0.35% | transfer_function_h1_band_sample | RECOVERS |
| Compressor ratio | white noise staircase | 2.0 | 2.000002 | 0.000002 | 0.0001% | rms_io_hinge_fit_above_slope | RECOVERS |
| Compressor ratio | white noise staircase | 4.0 | 4.001031 | 0.001031 | 0.026% | rms_io_hinge_fit_above_slope | RECOVERS |
| Compressor ratio | white noise staircase | 8.0 | 8.007475 | 0.007475 | 0.093% | rms_io_hinge_fit_above_slope | RECOVERS |
| Compressor makeup (dB) | white noise staircase | 0.0 | 0.000000 | 0.0 | -- | below_threshold_offset_median | RECOVERS |
| Compressor makeup (dB) | white noise staircase | 6.0 | 6.000000 | ~3e-7 | ~0% | below_threshold_offset_median | RECOVERS |
| Compressor makeup (dB) | white noise staircase | 12.0 | 12.000001 | ~5e-7 | ~0% | below_threshold_offset_median | RECOVERS |
| Compressor threshold (dB, absolute) | white noise staircase | -24.0 | -27.766 | 3.766 | -- | rms_io_hinge_fit | PARTIAL -- systematic offset, see below |
| Compressor threshold (dB, absolute) | white noise staircase | -18.0 | -21.766 | 3.766 | -- | rms_io_hinge_fit | PARTIAL -- same offset |
| Compressor threshold (dB, absolute) | white noise staircase | -12.0 | -15.766 | 3.766 | -- | rms_io_hinge_fit | PARTIAL -- same offset |
| Compressor threshold (dB, **relative delta** across the 3 rows above) | white noise staircase | delta=12.0 | delta=12.000 | ~0 | ~0% | rms_io_hinge_fit | RECOVERS (delta only) |
| Compressor threshold/ratio, bypassed chain | white noise staircase | n/a (identity) | thr=**None**, ratio=1.000 | -- | -- | rms_io_hinge_fit | HONEST NON-RECOVERY for threshold; ratio correctly reads "no compression" |
| Clipper drive (dB) | sine sweep 40Hz-12kHz | 6.0 | 6.0000003 | 3e-7 | ~0% | tanh_waveshaper_inversion | RECOVERS (near-exact analytic inversion) |
| Clipper drive (dB) | sine sweep | 15.0 | 14.9999997 | 3e-7 | ~0% | tanh_waveshaper_inversion | RECOVERS |
| Clipper drive (dB) | sine sweep | 24.0 | 24.0000007 | 7e-7 | ~0% | tanh_waveshaper_inversion | RECOVERS |
| Clipper drive, bypassed chain | white noise | n/a (identity, low-amplitude) | 0.054 | -- | -- | tanh_waveshaper_inversion | **KNOWN AMBIGUITY** -- see below, not a hard failure |

### Real dry vocal take (`Main Vokal 0001 [2026-08-26 223320].wav`, 166.07s, 44100Hz mono float, the longest of 39 candidates -- full take used, not a clip)

| parameter | set value | recovered | abs error | verdict |
|---|---|---|---|---|
| HPF cutoff (Hz) | 90.0 | 91.426 | 1.43 | RECOVERS -- matches synthetic-level accuracy |
| EQ band gain (dB @1000Hz) | 6.0 | 5.977 | 0.023 | RECOVERS -- matches synthetic-level accuracy |
| Clipper drive (dB) | 15.0 | 14.9999997 | 3e-7 | RECOVERS -- matches synthetic (expected: exact analytic inversion is signal-independent) |
| Compressor threshold (dB) | -18.0 | -27.278 | 9.28 | **DOES NOT MATCH SYNTHETIC** -- see below |
| Compressor ratio | 4.0 | 1.440 | 2.56 (64% rel) | **DOES NOT MATCH SYNTHETIC -- FAILS** |
| Compressor makeup (dB) | 6.0 | 6.0000003 | 3e-7 | RECOVERS -- robust even when threshold/ratio are wrong |

---

## What recovers, what doesn't, and why

**Recovers cleanly, differential floor holds:**
- **HPF cutoff** -- sub-1.5% error on both white noise and an unrelated broadband
  source (jittered click train), and matches on real vocal too (1.43Hz error at
  90Hz). This one is genuinely solid: pedalboard defines the cutoff as the -3dB
  point, so the H1-estimator method measures the literal quantity being set.
- **EQ band gain** -- sub-0.4% error synthetic, sub-0.4% error on real vocal.
  Same H1 estimator, just sampled at a point instead of searching for a crossing.
- **Clipper drive** -- effectively exact (error ~3e-7 dB) on both synthetic and
  real material. This is not a fit; it's an analytic inversion of pedalboard's
  documented `tanh` model, so signal content is irrelevant as long as samples
  aren't saturated to the arctanh singularity. The one caveat: at very low/zero
  drive, a genuine near-transparent clipper is statistically indistinguishable
  from a bypassed stage (both are near-identity on modest amplitudes) -- this
  showed up as a plausible-looking ~0dB reading on an actually-bypassed chain.
  Not a fabrication (0dB genuinely means "no measurable distortion"), but it
  means this method cannot answer "is there a clipper here at all" for very low
  drive settings -- only "how much, given that one is active and driven enough
  to matter." Tested range (6/15/24dB) is unambiguous.
- **Compressor ratio and makeup gain** -- recover to <0.1% and <0.001dB error
  respectively, but **only on the quasi-static synthetic staircase** used to
  validate them (blocks held 1.2s, each ~15-240x longer than attack/release).

**Does not recover / recovers only partially -- this is the load-bearing finding for D2:**
- **Compressor absolute threshold_db** -- carries a reproducible, non-noise
  offset from the true value. On the white-noise staircase it was a stable
  ~3.8dB (checked across frame_ms in {10,20,50,100,200,300}ms and across every
  ratio/threshold combination tried -- variance <0.05dB, i.e. not fit noise,
  a genuine calibration mismatch between "block RMS in dBFS" and whatever
  detector pedalboard.Compressor uses internally). **On the real vocal take the
  offset was 9.28dB, not 3.8dB** -- confirming the offset is signal-statistics-
  dependent (crest factor of Gaussian noise != crest factor of a sung vocal),
  which means there is no single correction constant to bake in; the method as
  built cannot report a trustworthy absolute threshold_db on arbitrary material.
  Relative deltas (same dry signal, only the chain parameter changes) do recover
  precisely, but that is not useful for a single blind wet signal.
- **Compressor ratio on real material fails outright**: 4.0 set, 1.44 recovered
  (64% relative error). Real vocal dynamics change continuously (phrasing,
  vibrato, consonant transients) rather than holding a level long enough for a
  5ms-attack/80ms-release envelope to settle within a 100ms analysis frame the
  way the synthetic staircase does. The frame-based RMS-in/RMS-out hinge fit
  fundamentally assumes quasi-static input; a real vocal violates that
  assumption continuously, and the fit responds by flattening the apparent
  compression ratio toward 1. **D2 needs a genuinely different measurement
  approach for the compressor on real material** -- e.g. a matched envelope
  follower (attack/release-aware, not block RMS) or working directly on an
  instantaneous per-sample or per-very-short-frame gain-reduction estimate --
  not a parameter tweak to this harness.
- **Clipper "is it active at all" for near-zero drive** -- see above, a real but
  narrow limitation (only matters near drive_db=0, not for driven distortion).

**Not attempted (per plan): blind extraction (wet-only, no dry reference).**
Given that even the differential floor fails for the compressor on real
material, blind extraction of compressor parameters is not attempted here --
the floor result says it would be strictly harder, not easier.

---

## What D2 must build (concrete, from the failures above)

1. A compressor threshold/ratio recovery method that works on continuously
   dynamic material, not quasi-static test tones -- likely needs an envelope
   model matched to attack_ms/release_ms rather than fixed-width block RMS,
   or a fundamentally different observable (e.g. instantaneous gain-reduction
   estimate from very short frames with attack/release-aware smoothing).
2. If an absolute threshold_db is still wanted, it needs either (a) knowledge
   of the input signal's crest factor to calibrate the ~signal-dependent
   detector-reference offset, or (b) a different, offset-free way to locate
   the hinge (this harness's grid-search hinge location has no crest-factor
   dependency by construction -- the bias is between "block RMS reference" and
   "pedalboard's internal detector reference", not the hinge search itself).
3. HPF, EQ, and Clipper recovery are solid; D2 does not need to touch them.

---

## Verification

Commands run from `D:\Projects\Music-AI-Toolshop`.

### `pytest tests/test_vocal_chain_roundtrip.py -v`

```
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0
collected 23 items

tests/test_vocal_chain_roundtrip.py::test_hpf_cutoff_recovery_white_noise[60.0] PASSED
tests/test_vocal_chain_roundtrip.py::test_hpf_cutoff_recovery_white_noise[90.0] PASSED
tests/test_vocal_chain_roundtrip.py::test_hpf_cutoff_recovery_white_noise[120.0] PASSED
tests/test_vocal_chain_roundtrip.py::test_hpf_cutoff_recovery_click_train[60.0] PASSED
tests/test_vocal_chain_roundtrip.py::test_hpf_cutoff_recovery_click_train[90.0] PASSED
tests/test_vocal_chain_roundtrip.py::test_hpf_cutoff_recovery_click_train[120.0] PASSED
tests/test_vocal_chain_roundtrip.py::test_hpf_bypassed_chain_returns_none_with_reason PASSED
tests/test_vocal_chain_roundtrip.py::test_eq_band_gain_recovery[-8.0] PASSED
tests/test_vocal_chain_roundtrip.py::test_eq_band_gain_recovery[4.0] PASSED
tests/test_vocal_chain_roundtrip.py::test_eq_band_gain_recovery[10.0] PASSED
tests/test_vocal_chain_roundtrip.py::test_compressor_ratio_recovery[2.0] PASSED
tests/test_vocal_chain_roundtrip.py::test_compressor_ratio_recovery[4.0] PASSED
tests/test_vocal_chain_roundtrip.py::test_compressor_ratio_recovery[8.0] PASSED
tests/test_vocal_chain_roundtrip.py::test_compressor_makeup_recovery[0.0] PASSED
tests/test_vocal_chain_roundtrip.py::test_compressor_makeup_recovery[6.0] PASSED
tests/test_vocal_chain_roundtrip.py::test_compressor_makeup_recovery[12.0] PASSED
tests/test_vocal_chain_roundtrip.py::test_compressor_threshold_recovery_absolute_and_relative PASSED
tests/test_vocal_chain_roundtrip.py::test_compressor_bypassed_chain_returns_none_threshold_with_reason PASSED
tests/test_vocal_chain_roundtrip.py::test_clipper_drive_recovery_sine_sweep[6.0] PASSED
tests/test_vocal_chain_roundtrip.py::test_clipper_drive_recovery_sine_sweep[15.0] PASSED
tests/test_vocal_chain_roundtrip.py::test_clipper_drive_recovery_sine_sweep[24.0] PASSED
tests/test_vocal_chain_roundtrip.py::test_extract_differential_recovers_active_hpf_and_reports_dict_shape PASSED
tests/test_vocal_chain_roundtrip.py::test_real_vocal_hpf_and_clip_recovery PASSED

======================= 23 passed, 2 warnings in 8.50s ========================
```
Exit code: 0. 23/23 passed (includes the real-audio `@pytest.mark.slow` test --
no marker exclusion configured in this repo's `pytest.ini`, so it ran).

### Full suite `pytest -q`

STATUS: IN PROGRESS -- kicked off in the background before writing this file
(large repo, ~90+ test files, several exercise CPU-only ML models per
AGENTS.md). Result will be appended below before this handoff is treated as
final. A pre-existing, unrelated red test is expected and NOT a regression I
introduced: `tests/test_chain_dsl_unwired_params.py` currently asserts that
`pedalboard_exec.build_pedalboard` raises for non-default `HPF.slope` /
`Compressor.knee_db` / `Limiter.lookahead_ms`, but the installed
`pedalboard_exec.py` still silently ignores those fields (per this task's own
background brief: "another agent is fixing that; do not touch that file").
My own chains in `tests/test_vocal_chain_roundtrip.py` never set those three
fields away from their schema defaults, so this harness cannot be affected by
either the pre-fix or post-fix state of that file.

<!-- APPEND FULL-SUITE RESULT HERE -->

---

## Tree state note (not my changes)

`git status` on the parent repo shows `mastering_tool` (submodule) as modified.
Inside the submodule, `tools/chain_dsl/executors/pedalboard_exec.py` and
`masterbus_exec.py` are locally modified, plus some untracked files
(`.gitattributes`, `.session_archive/`, `hiphop/`, `wave2_run1_output.txt`,
`wave2_run2_output.txt`). **I did not make these changes** -- I only ever
`Read` `pedalboard_exec.py`, never `Edit`/`Write` on it or `masterbus_exec.py`,
per this task's explicit instruction not to touch that file. This is
consistent with the background brief's mention of "another agent is fixing
that" -- i.e. a concurrent session editing the same submodule checkout during
this wave. Declaring it here per AGENTS.md close-out discipline ("clean tree
or declared") -- the orchestrator should attribute/verify this against
whichever agent owns that lane, not this one.

## Files touched

- `toolshop/vocal_chain/__init__.py` (new)
- `toolshop/vocal_chain/roundtrip.py` (new)
- `tests/test_vocal_chain_roundtrip.py` (new)
- `ORCHESTRATION/wave_vc1/agent_d1_handoff.md` (this file, new)
- `data/toolshop/vocal_chain/roundtrip_real/*.wav` (generated by the slow test;
  gitignored, not committed -- `data/` is fully excluded in `.gitignore`)

No existing files were modified. `mastering_tool/tools/chain_dsl/executors/pedalboard_exec.py`
was read but not touched, per instructions.
