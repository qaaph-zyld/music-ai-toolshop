# GATE S4 wave s4b — independent verification handoff (agent B)

Date: 2026-09-30 · READ-ONLY review of wave s4a (commit `f46da72` + docs
`38bf09c`, `8ecdc6c`). Lane: OGCM flip / Suno sample.
Plan: `D:\Projects\.workspace_archive\plans\ogcm-s4-recognizable-riff.md`
Spec: `D:\Projects\.workspace_archive\plans\expected_output_ogcm_suno_sample_s4_20260930_212015.md`
Python used: `D:/Projects/Music-AI-Toolshop/.venv/Scripts/python.exe` only.
No files edited, no commits, no re-renders. Only this handoff was written.

**Verdict: all technical checks PASS and all wave-s4a headline numbers
reproduce exactly under independent recomputation. Acceptance still gated
on the user's ear test (http://127.0.0.1:8777/flip_sample/).**

## Check 1 — git state: PASS

```
git log --oneline -3
8ecdc6c docs(#073): s4a handoff - final git state + closeout evidence
38bf09c docs(#073): GATE S4 wave s4a handoff - O1'-O5 green, riff + chord table of record
f46da72 feat(#073): GATE S4 recognizable riff - raw native-key (F#m) transcription transposed -4 to Dm, never scale-snapped
(exit 0)
```

- Handoff's commit `f46da72` exists.
- `git show --stat f46da72` (exit 0): 9 files — `CHANGELOG.md`,
  `ORCHESTRATION/ogcm_flip/LEDGER.md`, `wave_s4a/key_check_audio.py`,
  `wave_s4a/print_riff.py`, `scripts/check_riff.py` (new),
  `scripts/ogcm_sample.py`, `scripts/ogcm_transcribe_segment.py`,
  `tests/test_flip_sample.py`, `toolshop/flip/sample_voices.py`.
  **No `bed_lanes.py`, `arrange.py`, `master.py` in the commit.**
- `git show --name-only f46da72 | grep -i "\.wav"` → **exit 1 (no WAVs
  committed)**. `8ecdc6c` contains only the s4a handoff md.
- `git status --short` on `sample_voices.py`, `ogcm_sample.py`,
  `check_riff.py`, `test_flip_sample.py`, `ogcm_transcribe_segment.py`,
  `bed_lanes.py`, `arrange.py`, `master.py` → **all clean** (empty output).
- Remaining tree dirt is foreign-lane/pre-existing only:
  `MAirina_Tucc/*`, `lyrics_research/*`, `scratch_*`, `nul`,
  `wt_bog_probe.txt`, `ORCHESTRATION/ogcm_flip/wave_m1/`,
  `wave_m2/agent_b_bed_spike_handoff.md` (M), `prompts/`,
  `waves_megaplan.json`, `ORCHESTRATION/prompts/*`,
  `handoffs/orchestration_ledger_ogcm_s4_20260930.md`,
  `mastering_tool`/`suno_prompter` submodule pointers, `.scratch_*`.
  Matches the dirt declared in the s4a handoff.

## Check 2 — gates re-run from the S4 spec: all PASS

| Gate | Command (abbrev.) | Exit | Key output |
|---|---|---|---|
| O1′ | `verify_sample_pack.py --dir …\audition_s4 --glob "s4_*.wav" --min-files 4 --min-s 15 --max-s 45 --lufs -16 --lufs-tol 1.0 --tp-max -1.0` | **0** | `PASS` ×5: 4×21.5s + REF 26.9s, all `44100Hz 2ch -16.00LUFS`, tp −8.48/−7.29/−8.27/−8.77/−3.61 dBTP; `verify_sample_pack: PASS` |
| O2 | `python -m pytest tests/test_flip_sample.py -q` | **0** | `39 passed, 1 warning in 2.96s` |
| O3′ | `check_audition_serve.py --base http://127.0.0.1:8777/flip_sample --glob "audition_s4/s4_*.wav" --dir …\flip_sample --index index.html` | **0** | `PASS` ×5 `http=200 linked=yes`; `check_audition_serve: PASS` |
| O4 | `pytest test_flip_sample test_flip_arrange test_flip_master test_flip_bed_lanes -q` | **0** | `87 passed, 1 warning in 8.59s` |
| O5 | `check_riff.py --manifest …\audition_s4\manifest.json` | **0** | `6/6 PASS` — coverage 0.969, n=13, 2.413 n/s, leap 10, snapped 0, `F# minor -4 -> pc2`; `O5: PASS` |

Notes:
- The :8777 server was **down** at verification start (`curl` → `000`).
  Per spec/plan ("start it if it is down") it was started with
  `python -m http.server 8777 --directory Stemmeca_alatkka/stems`
  (process only — no file writes). Server is left running for the ear test.
- `verification.json` in `audition_s4/` reads `"pass": true`,
  `spread_lu: 0.0`, `lufs_ok/tp_ok/clips_ok: true`.
- Counts match s4a claims: 39 tests in the file, 87 in the O4 suite.

## Check 3 — independent spot-check (own code: json + numpy + pretty_midi; no toolshop import): PASS

Ran via stdin heredoc (no files written). Source: manifest riff notes +
`Stemmeca_alatkka/stems/flip_bed_lanes/midi/region_54_67_raw.mid`.

Manifest recomputation (13 riff notes, `cell_s=5.3872`):

| Metric | Recomputed | Manifest | Match |
|---|---|---|---|
| coverage = Σdur/cell_s | 0.969 | 0.969 | exact |
| notes_per_s = n/cell_s | 2.413 | 2.413 | exact |
| max_leap_st | 10 | 10 | exact |
| n_notes | 13 | 13 | exact |

- **Dm pitch-class containment:** pcs used `{0,2,4,5,7,9}` ⊆
  `{2,4,5,7,9,10,0}` — zero out-of-scale notes.
- **dm+4 == native note-for-note:** 0 mismatches across all 13 notes
  (transpose, not snap, confirmed structurally).
- **16th grid:** onsets land on slots
  `[1,4,5,6,8,12,15,18,19,21,25,28,29]` of `cell_s/32 = 0.1683 s`;
  worst deviation 0.0003 slots.
- Monophony: max end-past-next-onset overshoot 0.0001 s — pure JSON
  4-decimal rounding; effectively monophonic.

Raw-MIDI key check (118 notes, duration-weighted pc histogram):

```
C# .289  F# .198  D .161  B .153  A .145  G# .033  E .021
weight in F# natural minor = 1.0000
weight in D natural minor  = 0.3268
independent Krumhansl: F# minor r=+0.7965 (manifest 0.7965, exact);
                       A major +0.564, B minor +0.547, F# major +0.538
                       D minor r=-0.0012
```

- Max |histogram − plan claim| = **0.0046** (< 1% flag threshold) — the
  plan's pc profile is accurate.
- **F#-minor-dominated confirmed**: 100% of duration weight inside
  F# natural minor; D minor uncorrelated. The s4a premise holds.
- `snapped_notes=0` is consistent with transpose-not-snap evidence above.

No mismatches > 1% anywhere; in fact every recomputed number is identical
to the manifest/handoff to the reported precision.

## Check 4 — files + page labels: PASS

`audition_s4/` contains all 5 WAVs + `manifest.json` + `verification.json`:

```
s4_01_riff_sine.wav  s4_02_riff_ep.wav  s4_03_riff_oct.wav
s4_04_riff_native_Fsm.wav  s4_05_chop_REF.wav
```

`flip_sample/index.html` S4 section (on top, S3 marked superseded/snapped):

- `s4_05 · chop_REF` labelled **"(D minor) — the real 54–67s slice of the
  record, pitched −4 into the same key as 01–03"** → −4/D minor ✓
- `s4_04 · riff_native_Fsm` labelled **"(F# minor — original key)"** →
  native F# minor ✓
- Header note explicitly states 01/02/03/05 = D minor, 04 = F# minor.

## Result matrix

| Check | Verdict |
|---|---|
| 1. Git state / commit hygiene | **PASS** |
| 2a. O1′ pack verify | **PASS** (exit 0) |
| 2b. O2 riff tests | **PASS** (exit 0, 39) |
| 2c. O3′ HTTP serve | **PASS** (exit 0, 5/5) |
| 2d. O4 regression suite | **PASS** (exit 0, 87) |
| 2e. O5 riff gate | **PASS** (exit 0, 6/6) |
| 3. Independent spot-check | **PASS** — manifest numbers exact, F#m-dominated raw confirmed |
| 4. Files + index.html labels | **PASS** |

## Deviations / notes for the orchestrator

- Started the :8777 audition server (was down) — required by O3′ per the
  spec's own instruction; process only, no repo writes. Left running for
  the user's ear test.
- Historical `git log --all -- "*.wav"` shows old commits
  (`843a806`, `53cf9c6`) touching WAVs — pre-existing history, **not**
  this wave; `f46da72`/`38bf09c`/`8ecdc6c` are WAV-free.
- The s4a handoff's numbers were fully reproducible; nothing unverified
  remains on the technical side.
- **Acceptance is NOT declared** — per plan, only the user's ear test on
  http://127.0.0.1:8777/flip_sample/ (compare s4_01–03 / s4_05 in D minor,
  s4_04 against `instrumental.wav` 54–67 s) decides. On rejection the
  fallback is plan option 3 (hand-programmed riff).
- Known carried-over issue (reported, not fixed, per plan): S2 regions
  `region_63_66_cleaned_Dm.mid` / `region_233_258_cleaned_Dm.mid` likely
  carry the same key-snap defect.
