# Agent D3 handoff — chain_dsl unwired-parameter defect

## Task
Fix HPF.slope, Compressor.knee_db, Limiter.lookahead_ms declared in
mastering_tool/tools/chain_dsl/schema.py but never read by
mastering_tool/tools/chain_dsl/executors/pedalboard_exec.py::build_pedalboard.

## Step 1: establish pedalboard 0.9.24 API support (venv python)

Ran:
```
.venv/Scripts/python.exe -c "import pedalboard; ..."
```
inspect.signature fails on pedalboard's pybind11 builtins (no signature found),
so used instance dir() + docstrings instead.

Results (pedalboard.__version__ == 0.9.24):
- HighpassFilter: docstring explicitly says "first-order high-pass filter with
  a roll-off of 6dB/octave" (fixed). Public attrs: only `cutoff_frequency_hz`.
  NO slope control at all -> HPF.slope is UNSUPPORTED.
- Compressor: public attrs = attack_ms, ratio, release_ms, threshold_db.
  NO knee_db -> Compressor.knee_db is UNSUPPORTED.
- Limiter: public attrs = release_ms, threshold_db.
  NO lookahead_ms -> Limiter.lookahead_ms is UNSUPPORTED.

Conclusion: pedalboard supports NONE of the three parameters. There is nothing
to "wire" in pedalboard_exec.py — all three must refuse loudly when the caller
sets a non-default value, and stay silent (no error) at default.

## Step 2: masterbus_exec.py check
- to_masterbus_dict() (schema.py) DOES already include limit_lookahead_ms in
  the flat JSON, and open_DAW/daw-engine/src/master_bus.rs genuinely consumes
  it (Limiter::new/reconfigure take lookahead_ms) -> that one IS wired end to
  end for the masterbus path. No fix needed there.
- hpf_slope and comp_knee_db are NOT present in Rust's MasterBusConfig struct
  (open_DAW/daw-engine/src/master_bus.rs) and NOT emitted by to_masterbus_dict()
  -> same silent-drop gap as pedalboard_exec, for those two only.
- open_DAW is listed as "Parked (no investment without user sign-off)" in
  AGENTS.md, so making Rust actually honour hpf_slope/comp_knee_db is out of
  scope (not "small"). Applying the same refuse-loudly guard in
  masterbus_exec.py (Python-only, small) is in scope -> did that.

(continues below as work proceeds)

## Step 3: implementation

### pedalboard_exec.py
Confirmed via venv python (dir() on instances, since inspect.signature fails
on pedalboard's pybind11 builtins with "no signature found for builtin"):
- pedalboard.HighpassFilter() attrs: only `cutoff_frequency_hz`. Docstring:
  "first-order high-pass filter with a roll-off of 6dB/octave" (fixed, not
  configurable) -> HPF.slope UNSUPPORTED.
- pedalboard.Compressor() attrs: attack_ms, ratio, release_ms, threshold_db.
  No knee_db -> Compressor.knee_db UNSUPPORTED.
- pedalboard.Limiter() attrs: release_ms, threshold_db. No lookahead_ms ->
  Limiter.lookahead_ms UNSUPPORTED.

pedalboard 0.9.24 supports NONE of the three. All three now refuse loudly in
`build_pedalboard` via a new `_reject_if_nondefault()` helper + a new
`UnsupportedParameterError(ValueError)`, only when the owning stage is
*active* (not bypassed) and the value differs from the schema default. At
default: silent, as before (existing callers unaffected).

### masterbus_exec.py
Added the same `_reject_if_nondefault` pattern (separate small helper, same
shape) for HPF.slope and Compressor.knee_db, called from
`to_masterbus_config()` before delegating to `chain.to_masterbus_dict()`.
Limiter.lookahead_ms is NOT guarded here -- confirmed it IS present in
open_DAW/daw-engine/src/master_bus.rs's `MasterBusConfig` struct and genuinely
consumed by `Limiter::new`/`reconfigure`. Making Rust honour hpf_slope /
comp_knee_db would require changes inside open_DAW, which AGENTS.md marks
"Parked (no investment without user sign-off)" -- out of scope, so only the
Python-side refusal was added there, not full wiring.

## Step 4: tests
New file: `tests/test_chain_dsl_unwired_params.py` (parent repo tests/, NOT
mastering_tool/tools/chain_dsl/test_chain_dsl.py) -- because pytest.ini has
`testpaths = tests`, so nothing inside the mastering_tool submodule is ever
collected by the default `pytest -q` run. Confirmed by
`pytest --collect-only -q | grep chain_dsl`: only the 14 new tests show up;
the submodule's own 5 tests (mastering_tool/tools/chain_dsl/test_chain_dsl.py)
never appear. That submodule file has *never run* under the parent suite --
same "1,440 lines of tests that have never once run" failure class called out
in AGENTS.md's Lane discipline section. Reported as a finding; not fixed
(pytest.ini's testpaths is out of scope for this task -- flagging only).

14 tests, all passing:
- 3x pedalboard HPF.slope (raise / default-no-raise / bypassed-no-raise)
- 2x pedalboard Compressor.knee_db (raise / default-no-raise)
- 3x pedalboard Limiter.lookahead_ms (raise / default-no-raise / render-still-works)
- 2x masterbus HPF.slope (raise / default-no-raise)
- 2x masterbus Compressor.knee_db (raise / default-no-raise)
- 2x masterbus Limiter.lookahead_ms (NOT raise + value differs in output dict,
  proving it's genuinely wired for this path)

No "renders differ" audio test was needed for the three defect parameters
themselves: none of them could be honoured by pedalboard, so none were
"wired" there -- all three became refusals instead. The one already-wired
param (masterbus limit_lookahead_ms) got a differencing assertion instead
(`config["limit_lookahead_ms"] != default_config["limit_lookahead_ms"]`)
per the spirit of the "wired must measurably differ" rule.
