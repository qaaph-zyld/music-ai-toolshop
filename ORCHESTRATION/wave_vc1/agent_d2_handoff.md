# Wave 2 / Agent D2 -- Compressor recovery on real vocal material

Deliverable: fix compressor ratio/threshold recovery, which D1 found fails on real
material (frame-based RMS-in/RMS-out hinge fit assumes quasi-static input; a sung
vocal violates that continuously). Approach directed by the plan: use the
**instantaneous per-sample gain-reduction** `GR_db(t) = 20*log10(|wet(t)|/|dry(t)|)`
against an **attack/release-aware envelope-follower detector level**, instead of
block RMS.

This file is written incrementally as findings land -- do not treat any section
final until "Verification" at the bottom is filled in.

Status: IN PROGRESS -- `recover_compressor_gain_reduction` implemented in
`toolshop/vocal_chain/roundtrip.py`; diagnostic sweep (old vs new, synthetic +
real, 3 ratios x 3 thresholds) running to get real numbers before tolerances
are chosen for the tests. Not yet run through pytest.

## Implementation (`toolshop/vocal_chain/roundtrip.py`)

Added, without touching `recover_compressor`, `recover_hpf_cutoff_hz`,
`recover_eq_band_gains`, or `recover_clipper_drive_db`:

- `_decimate_for_envelope(x, sr)` -- stride-decimates toward ~6kHz before the
  envelope follower runs (see benchmark above; keeps a 36-combination
  attack/release grid search affordable on the 166s real file).
- `_one_pole_envelope_db(x_abs, sr, attack_ms, release_ms)` -- the
  attack/release "ballistics" detector: `env[n] = a*env[n-1] + (1-a)*x[n]`,
  `a` switched per-sample between `a_att`/`a_rel` (`exp(-1/(sr*t_s))`,
  standard time-constant convention) depending on whether the input is above
  or below the current envelope. Written as a plain Python loop -- this
  recursion is data-dependent (coefficient choice depends on the *running
  output*, not just position), so it cannot be vectorized with
  `scipy.signal.lfilter`.
- `_hinge_fit(x_db, y_db, min_points_per_side)` -- factored out of
  `recover_compressor`'s grid-search-a-hinge-point logic so the new method
  reuses the identical fitting procedure, just on different x/y data.
- `recover_compressor_gain_reduction(dry, wet, sr, ...)` -- the new method:
  1. Reuses `recover_compressor(...)["makeup_db"]` (D1 found this accurate
     even where threshold/ratio fail) to remove the makeup-gain confound from
     the y-axis. Documented in code why threshold/ratio are actually
     invariant to this even if it fails (constant y-offset doesn't move a
     hinge x-position or change a slope).
  2. `GR_db(t) = 20*log10(|wet(t)|/|dry(t)|) - makeup_db` at every (decimated,
     dry-floor-masked) sample -- the *exact* instantaneous gain for a pure
     scalar-gain stage, not a block average.
  3. Grid search over `attack_candidates_ms x release_candidates_ms` (6x6=36
     by default): for each pair, build the envelope on `|dry|`, hinge-fit
     `GR_db` against envelope-level-db, keep the pair with lowest SSE.
  4. `threshold_db` = hinge x-position; `ratio = 1/(1 + slope_above)`
     (derived: `GR_db = (1/ratio - 1)*(level_db - threshold_db)` above
     threshold, so `slope_above = 1/ratio - 1`).
  5. `attack_ms`/`release_ms` reported `None` with a reason if the best-SSE
     candidate isn't meaningfully better than the grid's median SSE
     (`convergence_ratio=0.7`) -- i.e. many envelope shapes fit about equally
     well, so the specific time constants aren't identifiable from this data.
- `extract_differential` gained four new keys (`comp_threshold_db_gr`,
  `comp_ratio_gr`, `comp_attack_ms`, `comp_release_ms`) wired to the new
  method. The four existing compressor keys are untouched -- same values,
  same method, same contract as before.

## Diagnostic script (not committed as a test)

`diag_compressor.py` (scratchpad) sweeps old vs new methods across ratio in
{2,4,8} x threshold in {-24,-18,-12} on the synthetic staircase and the full
real vocal take, printing recovered threshold/ratio/attack/release and timing.
Used to get real numbers before writing pytest tolerances -- results below.

---

## Plan (from the task brief)

1. Subtract makeup gain (reuse existing `recover_compressor`'s makeup_db -- D1
   found it robust, ~exact, even on real material where threshold/ratio failed).
2. One-pole attack/release envelope follower over `|dry|`, coefficients from
   candidate `attack_ms`/`release_ms`.
3. Hinge-fit GR_db vs detector-level-db (2-line fit, grid search over threshold).
4. Grid-search attack/release candidates, pick the pair minimizing fit residual;
   report None with reason if the grid doesn't converge to a clear minimum.

## Environment notes

- venv confirmed: numpy 2.4.6, scipy 1.17.1, pedalboard 0.9.24, numba 0.66.0 (numba
  present transitively per `requirements.lock.txt` but not a declared/used dep
  anywhere in `toolshop/` -- per AGENTS.md "no new deps outside the OSS map without
  sign-off", the envelope follower is implemented in pure Python/NumPy, not numba).
- Benchmarked a pure-Python one-pole switching-coefficient loop (this filter is
  inherently sequential/data-dependent -- cannot be vectorized with `scipy.lfilter`,
  which only handles fixed-coefficient LTI filters): 7.3M samples (166s @ 44.1kHz,
  the real vocal's length) processed in ~3.05s. To keep a multi-candidate
  attack/release grid search affordable, the detector is run on `|dry|` decimated
  to ~4kHz (attack times of interest, 1-50ms, are 4-200+ decimated samples -- ample
  resolution) rather than full sample rate.
