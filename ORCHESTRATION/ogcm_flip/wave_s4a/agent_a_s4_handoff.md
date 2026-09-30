# GATE S4 wave s4a — implementer handoff (agent A)

Date: 2026-09-30 · Commit: `f46da72` (plus a follow-up commit adding this
handoff — see `git log`). Lane: OGCM flip / Suno sample.
Plan: `D:\Projects\.workspace_archive\plans\ogcm-s4-recognizable-riff.md`
Spec: `D:\Projects\.workspace_archive\plans\expected_output_ogcm_suno_sample_s4_20260930_212015.md`

**Verdict: all technical gates O1′–O5 PASS. No "recognizable" claim — that
is the user's ear test at http://127.0.0.1:8777/flip_sample/ (wave s4b
verifies, user gates).**

## Step 0 — key premise confirmed from AUDIO (guard passed)

`ORCHESTRATION/ogcm_flip/wave_s4a/key_check_audio.py` — librosa chroma_cqt on
`Stemmeca_alatkka/stems/instrumental.wav` 54.0–67.0 s + Krumhansl correlation.
Exit 0:

```
top-5 Krumhansl correlations:
  F# minor   r=+0.367     <- winner
  B minor    r=+0.332
  A major    r=+0.288
  D major    r=+0.277
  A# minor   r=+0.272
F# minor r=+0.367 | A major r=+0.288 | D minor r=+0.039
VERDICT: OK - F#m/Amaj beats Dm
```

D minor is essentially uncorrelated with the audio (r=+0.039). The plan's
premise holds; proceeded.

## The extracted riff (printed before rendering — `print_riff.py` + driver log)

`region_54_67_raw.mid`: 118 raw notes, span 0.01–12.91 s.
`estimate_key(raw)` = **F# minor r=+0.797**.
Winning cell = cell 1, `cell_t0=5.39 s`, `cell_s=5.39 s` (2 bars @ 89.1 BPM).
13 notes, 16th grid:

```
 on_s   dur_s  nat(F#m)      -> Dm
 0.17   0.51   G#4 (68)      -> E4 (64)
 0.67   0.17    A4 (69)      -> F4 (65)
 0.84   0.17   F#4 (66)      -> D4 (62)
 1.01   0.34   F#4 (66)      -> D4 (62)
 1.35   0.67    E5 (76)      -> C5 (72)
 2.02   0.51   C#5 (73)      -> A4 (69)
 2.53   0.51   C#5 (73)      -> A4 (69)
 3.03   0.17   C#5 (73)      -> A4 (69)
 3.20   0.34    B4 (71)      -> G4 (67)
 3.54   0.67   C#5 (73)      -> A4 (69)
 4.21   0.51    A4 (69)      -> F4 (65)
 4.71   0.17   G#4 (68)      -> E4 (64)
 4.88   0.51   F#4 (66)      -> D4 (62)
```

Sanity vs the plan's phrase shape (C#5 repeated → B4 → C#5 → A4–G#4–F#4;
in Dm: A4 repeated → G4 → A4 → F4–E4–D4): **matches in the second half of
the cell** — notes 6–13 are exactly C#5 C#5 C#5 B4 C#5 / A4 G#4 F#4 (Dm: A4
A4 A4 G4 A4 / F4 E4 D4). The cell's first half (G#4–A4–F#4–F#4–E5 →
Dm E4–F4–D4–D4–C5) is the answering gesture of the bar-pair rather than a
verbatim repeat — not wildly different, reported per instruction without
parameter tuning.

Per-bar chord names (derived from the segment's own bass inside the winning
cell, transposed −4): **Dm7 Bbmaj7 Dm7 Bbmaj7 Dm7 Bbmaj7 Dm7 Bbmaj7**
(native +4 spellings for s4_04: F#m7 Dmaj7 alternating).

`riff_stats` = `{"n_notes": 13, "notes_per_s": 2.413, "coverage": 0.969,
"max_leap_st": 10}`; `snapped_notes = 0`; `transpose_st = -4`;
`source_key = F# minor (r=+0.797)`.

## Gate results (each command quoted with exit code)

| Gate | Command | Exit | Result |
|---|---|---|---|
| Step-0 key guard | `.venv python ORCHESTRATION/ogcm_flip/wave_s4a/key_check_audio.py` | 0 | F# minor r=+0.367 top; D minor r=+0.039 |
| Render | `.venv python scripts/ogcm_sample.py --pack s4` | 0 | 5 files; `verification.json pass=true`; −16.0 LUFS each, spread 0.0, TP≤−1 |
| O1′ | `verify_sample_pack.py --dir …\audition_s4 --glob "s4_*.wav" --min-files 4 --min-s 15 --max-s 45 --lufs -16 --lufs-tol 1.0 --tp-max -1.0` | 0 | 5/5 PASS: 21.5 s synths + 26.9 s REF, tp −3.6…−8.8 dBTP |
| O2 | `pytest tests/test_flip_sample.py -q` | 0 | **39 passed** (30 pre-existing + 9 new S4) |
| O3′ | `check_audition_serve.py --base http://127.0.0.1:8777/flip_sample --glob "audition_s4/s4_*.wav" …` | 0 | 5/5 http=200 linked=yes (server started on :8777, root `Stemmeca_alatkka/stems`) |
| O4 | `pytest test_flip_sample test_flip_arrange test_flip_master test_flip_bed_lanes -q` | 0 | **87 passed** |
| O5 | `check_riff.py --manifest …\audition_s4\manifest.json` | 0 | 6/6 checks PASS |
| Spot-check | own recompute from manifest riff JSON | 0 | n=13, 2.413 n/s, coverage 0.969, leap 10; all Dm pcs ∈ {2,4,5,7,9,10,0}; native = dm+4 note-for-note; onsets on 16th grid |

## Files created/modified

- `toolshop/flip/sample_voices.py` — NEW: `GRID_16TH_S`, `PC_NAMES`,
  `note_name`, `transpose`, `estimate_key` (Krumhansl, numpy),
  `fold_octaves`, `extract_riff`, `riff_stats`. `extract_motif` untouched.
- `scripts/ogcm_sample.py` — `--pack s4`, `--transpose` (default −4),
  per-pack region/chop defaults (`region_54_67_raw.mid`,
  `ref_slice_54_67.wav`), `_render_s3(chords=)` (None = old fallback cycle),
  `_s4_variants`, `_transpose_chords`, manifest `s4` block.
- `scripts/ogcm_transcribe_segment.py` — prints `estimate_key(raw)` before
  `cleanup`; loud warning when >15 % of raw duration is outside the
  requested `--root/--mode` scale.
- `scripts/check_riff.py` — NEW (O5).
- `tests/test_flip_sample.py` — 9 new tests (synthetic only): register
  floor, octave fold, full-cell-beats-tail, 16th grid, monophony, coverage,
  transpose-into-Dm interval preservation, `estimate_key` F#m + Dm, empty.
- `Stemmeca_alatkka/stems/flip_sample/index.html` — S4 section on top; key
  labels: s4_01/02/03/05 = **D minor**, **s4_04 = native F# minor**; S3
  marked superseded/key-snapped. (Under `stems/` — gitignored, edited on
  disk only; same convention as S3.)
- `Stemmeca_alatkka/stems/flip_sample/audition_s4/` — 5 WAVs +
  manifest/verification (gitignored).
- `ORCHESTRATION/ogcm_flip/LEDGER.md` — s4 row with key-snap root cause.
- `CHANGELOG.md` — Answer #073 (next free after #072; `grep "#073"` was
  empty before use).
- `ORCHESTRATION/ogcm_flip/wave_s4a/` — `key_check_audio.py`,
  `print_riff.py`, this handoff.

## Constraints check

- `bed_lanes.py`, `arrange.py`, `master.py`: untouched (O4 suite green;
  `git show --stat f46da72` lists none of them).
- No new dependencies; renders deterministic, no model calls at render time.
- `--pack s3` path byte-identical logic (`extract_motif`, `_render_s3`
  default `chords=None` → same fallback cycle).
- No WAVs staged; foreign-lane dirt (MAirina_Tucc/, lyrics_*, Genious_*,
  scratch_*) untouched and unstaged.

## Known issues / notes for s4b

- **S2 regions likely snapped too (NOT fixed):** `region_63_66_cleaned_Dm.mid`
  and `region_233_258_cleaned_Dm.mid` went through the same
  `cleanup(root="D")` on F#m material — same defect class as the S3 root
  cause. Surfaced only; out of scope per plan.
- The s4_05 REF chop is `ref_slice_54_67.wav` pitched −4 (D minor), so the
  A/B with 01–03 is same-key; s4_04 returns the riff to native F# minor for
  direct comparison against `instrumental.wav` 54–67 s.
- Audition server left running on :8777 (`python -m http.server 8777
  --directory Stemmeca_alatkka/stems`, started this session).
- Ear test decides acceptance; on rejection the fallback is plan option 3
  (hand-programmed riff from the user's description).

## Git state at handoff

```
38bf09c docs(#073): GATE S4 wave s4a handoff - O1'-O5 green, riff + chord table of record
f46da72 feat(#073): GATE S4 recognizable riff - raw native-key (F#m) transcription transposed -4 to Dm, never scale-snapped
```

`git status --short` on every file this wave touched: **clean** (all
committed). Remaining tree dirt is foreign-lane and pre-existing, declared
per close-out discipline: `MAirina_Tucc/*`, `lyrics_research/*`,
`scratch_*`, `nul`, `wt_bog_probe.txt`, `ORCHESTRATION/ogcm_flip/wave_m1/`,
`wave_m2/agent_b_bed_spike_handoff.md` (M), `prompts/`, `waves_megaplan.json`,
`ORCHESTRATION/prompts/*`, `handoffs/orchestration_ledger_ogcm_s4_20260930.md`
(orchestrator's own file), `mastering_tool`/`suno_prompter` submodule
pointers.

**Closeout evidence** — `.venv python -m toolshop.cli closeout` → **exit 1
(FAIL, declared)**: "working tree not clean" = the foreign-lane dirt listed
above only; "unpushed commits" = the 6 commits atop `@{u}` incl. this wave's
two (user push cadence — same declared state as Answer #072). Submodule
summary clean: `mastering_tool` 9bddc72, `suno_prompter` 7acba12.
