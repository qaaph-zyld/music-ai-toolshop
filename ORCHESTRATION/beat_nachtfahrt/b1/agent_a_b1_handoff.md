# Nachtfahrt b1 handoff

Code commit: `092d276` feat(#078) (toolshop/beat/__init__.py, drums_synth.py, tests/test_beat_nachtfahrt.py, CHANGELOG.md).

## Gates
- `.venv/Scripts/python.exe -m pytest tests/test_beat_nachtfahrt.py -q` -> exit 0, 15 passed
- flip regression (test_flip_sample, test_flip_arrange, test_flip_master, test_flip_bed_lanes) -q -> rc=0, 151 passed
- `git diff --stat HEAD -- toolshop/flip toolshop/premaster.py` -> exit 0, empty

## Per-piece measurement (sr 44100, default seed)
| piece | dur s | peak | key |
|---|---|---|---|
| kick | 0.60 | 0.8913 | FFT peak 150-400 ms = 47.9 Hz |
| snare | 0.35 | 0.8913 | 49.4% energy in 1.5-8 kHz |
| clap | 0.30 | 0.8913 | |
| hat | 0.12 | 0.8913 | 99.8% > 5 kHz |
| openhat | 0.50 | 0.8913 | 99.8% > 5 kHz |
| crash | 2.50 | 0.8913 | |
| riser(2 s) | 2.00 | 0.8913 | ends at full level (no end fade) |
All float32 mono. one_shots keys: kick, snare, clap, hat, openhat, crash.

## Deviations
- Decay times are exp time constants chosen so the stated decay reaches about -26 dB (3 tau); e.g. kick tau 0.15 s.
- gated_reverb onset = rising edge of a 5 ms smoothed envelope over 10% of max; output length = len(x)+gate_ms; fade is truncated if an onset sits within fade_ms of the end.
- Piece seed offsets: kick1 snare2 clap3 hat4 openhat5 crash6 riser7.
- Several duplicate flip pytest runs were left in background by tool timeouts (harmless, read-only).
- Pre-existing dirty foreign-lane files (MAirina_Tucc/ etc.) were left unstaged.
