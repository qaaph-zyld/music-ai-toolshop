# fx_wave2 W1A handoff — Live bridge parity fix + install

**Date:** 2026-10-03 · **Agent:** Devin session (window 1) · **State:** code complete — **USER GATE OPEN** (Control Surface prefs)

## Done

- **Parity fix** in `toolshop/daw/live_bridge_script.py`:
  - `plugins.get_param` / `plugins.set_param` now accept `param_index` (the exact kwarg `toolshop/daw/plugins.py` sends); legacy `param` kept as fallback via `_resolve_param_index`.
  - Added `plugins.get_param_name` handler → `{name, param}`.
  - Docstring method surface updated.
- **`toolshop daw bridge-install`** added to `daw_cli.py` — local op (bypasses DAW connect), scans `%APPDATA%\Ableton\Live *` prefs dirs, reports `installed|updated|unchanged`, prints the manual prefs steps.
- **Install executed**: `Live 12.1.11: installed` and `Live 12.2: installed` → `C:\Users\015ZCS\AppData\Roaming\Ableton\<ver>\Preferences\User Remote Scripts\ToolshopLive\__init__.py`.

## Evidence

- `pytest tests\test_live_bridge.py -v` → **15 passed** (incl. `test_plugins_client_param_index_convention`, `test_plugins_param_index_missing_is_error`), 99.7s.
- `pytest test_fx_dawdreamer_eval.py + test_live_bridge.py + test_daw.py -m "not slow"` → **164 passed, 7 deselected**, 30.65s.
- `toolshop daw bridge-install` → output quoted above; exit 0.

## USER GATE — manual, cannot be automated

1. (Re)start Ableton Live 12.1.11
2. Options → Preferences → Link/Tempo/MIDI → Control Surface → **ToolshopLive** (no In/Out ports)
3. Then verify: `toolshop daw --port 9878 status` (expect `bridge: ToolshopLive`) + `tracks.list` / `devices.list` smoke.
   Evidence cross-check: `%APPDATA%\Ableton\Live 12.1.11\Preferences\Log.txt` should contain `[ToolshopLive] TCP server listening on 127.0.0.1:9878`.

## Notes for next windows

- W2C depends on this gate for the live export proof; the code path (devices.list/get_params) is bridge-side already.
- Master-track support (`track=-1` → `song.master_track`) still to add in `_track()` (W2C/W4).
