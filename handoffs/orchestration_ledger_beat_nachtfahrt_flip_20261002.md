# Orchestration ledger · "Nachtfahrt" FLIP of the OGCM 54–67 s segment · 2026-10-02

- **Plan:** `D:\Projects\.workspace_archive\plans\nachtfahrt-ogcm-flip.md` (hash-identical mirror of the user-approved plan)
- **Spec:** `D:\Projects\.workspace_archive\plans\expected_output_nachtfahrt_flip_20261002_220636.md` (O1–O6, worktree-import pitfall at the top)
- **Waves:** `ORCHESTRATION/beat_nachtfahrt_flip/waves.json`
- **Status:** **PLANNED, NOT DISPATCHED.** The user said "first you envision the process and plan, no coding here".
- **Parallel lane:** the from-scratch Nachtfahrt is being executed by another session (b1 landed on master as `092d276` feat(#078)). Never touch its files, ledger or waves.

## User direction (verbatim intent)

- "Use the 2Pac instrumental's targeted segment and, starting from that, create this beat."
- "You build a beat by remix, chopping, doing what a producer would do if he wanted to build a beat from a sample."
- "Melody should be recognizable, yet modern German production."
- Carry-over layers: "you decide".
- The earlier goal still stands: "fully done instrumental, mixed and mastered by you; don't stop until done; always /orchestrate-waves".

## Orchestrator decisions (from the plan)

- **Bed:** a drumless bed of htdemucs_6s guitar + other. The phrase is 4 bars from 59.387 s; the run-up is 54.0–59.387 s.
- **Tempo/key:** varispeed by r, about 2^(3/12), derived from the measured phrase length so the phrase lands exactly on **106 BPM**. F# minor becomes **A minor**. No time-stretch.
- **Carry-over:** drawbar organ stabs, hooks only. No resynth wail and no octave bass.
- **Drums and 808:** `toolshop/beat/drums_synth.py`, which is already on master (`092d276`), so f2 is expected to be skipped. 808 via `bass808`.
- **Arrangement:** the plan's 80-bar chop table. Masters at −9 and −14 LUFS.

**Orchestrator corrections recorded at planning time:**
1. **Hook D octave layer.** It uses `pedalboard.PitchShift(+12)`, which is time-preserving, on a −14 dB layer high-passed at 2 kHz. A ×2 varispeed would double its tempo.
2. **Verse/outro section-loudness bands.** The spec relaxes them to verse −1.5 to −6 LU and outro ≤ −4 LU, because the sample is present in the verses.
3. **Worktree import pitfall.** The editable install maps `toolshop` to the MAIN repo, so every run uses Cwd = WT and `PYTHONPATH=WT`, with a sanity print of `toolshop.__file__`.
4. **Stems path.** Gitignored stems are absent from the worktree, so every input/output path is the main repo's absolute `D:\Projects\Music-AI-Toolshop\Stemmeca_alatkka\stems\...`.

## Execution start (for the session that dispatches)

1. **Read state.** Run `git -C D:\Projects\Music-AI-Toolshop status --short` and `log --oneline -5`, and confirm that `toolshop/beat/drums_synth.py` is on master. If it is, f2 is skipped and the ledger records the commit.
2. **Create the worktree:** `git -C D:\Projects\Music-AI-Toolshop worktree add D:\Projects\Music-AI-Toolshop-wt-flip -b beat/nachtfahrt-flip master`. Then sanity-check: with Cwd `D:\Projects\Music-AI-Toolshop-wt-flip` and `$env:PYTHONPATH='D:\Projects\Music-AI-Toolshop-wt-flip'`, `D:\Projects\Music-AI-Toolshop\.venv\Scripts\python.exe -c "import toolshop; print(toolshop.__file__)"` must print a path under the worktree.
3. **Orchestrator marker.** `D:\Projects\.workspace_archive\orchestration\ACTIVE` holds another lane's task, so append `override: user-directed <date> - Nachtfahrt flip waves f1-f5`. Never delete another lane's lines.
4. **Goal.** Run `goal_helper.py status`. If no other goal is active, run:
   ```
   python "D:\Projects\ai_dev_meta_layer\scripts\goal_helper.py" set "Nachtfahrt flip fully arranged, mixed and mastered; flip release gates green" --check "D:\Projects\Music-AI-Toolshop\.venv\Scripts\python.exe -X utf8 D:\Projects\Music-AI-Toolshop-wt-flip\scripts\check_flip_release.py --dir D:\Projects\Music-AI-Toolshop\Stemmeca_alatkka\stems\beats\nachtfahrt_flip" --max-iterations 30 --check-timeout 180
   ```
5. **Dispatch** f1 → (f2 only if needed) → f3 → f4 → f5 with the prompts below, verbatim, one at a time, in the foreground.
6. **After each wave:**
   - spot-check the branch scope (`git -C WT log master..HEAD --stat`)
   - check the protected diff (`git -C WT diff --stat master -- toolshop/flip toolshop/premaster.py` must be empty)
   - check artifact mtimes
   - recompute one headline number
   - update this ledger and commit it **in the main worktree on master**, explicit path only
   - run `goal_helper.py note`
7. **Usage-limit kill:** inspect the disk state, then resume via SendMessage. Never trust the last claim.
8. **Close.**
   - O1 exits 0 and f5 PASSes; then run `goal_helper.py complete`
   - remove our override line
   - write a handoff
   - deliver http://127.0.0.1:8777/beats/nachtfahrt_flip/ with the numbers
   - **do not merge** the branch; merging is the user's call

## Execution-readiness amendments (recorded at dispatch, 2026-10-02 ~22:40)

Verified state vs the "Execution start" assumptions; drift becomes amendment lines, not redesign. 7/7 checks PASS (see plan `~/.devin/plans/plan-f6f911268f786c8d.md`).

- **A-HEAD:** master moved `56da498 → e0b44ba` (b-lane b2 landed as `7b6ed92`, #079; plus docs `afc19fd`, `e0b44ba`). No protected paths touched. The worktree branches from `e0b44ba`.
- **A-CHANGELOG:** #079 is now taken → f4's single Answer entry uses the next free number ("renumber at merge if taken" applies; **update at ~22:55: b3 landed `b7c09d7` #080 on master — next free is #081**; the f4 prompt re-greps master's CHANGELOG at write time, so it self-corrects).
- **A-GOAL:** `goal_state.json` holds a paused vocal-chain goal (2026-09-01, 20/20 iters). `goal_helper.py set` unconditionally REPLACES it (no guard — goal_helper.py:179-189). Condition "no other goal active" is met (paused ≠ active); the paused record is overwritten.
- **A-DIRTY:** main worktree is dirty with b-lane b3 in-flight (`M scripts/build_nachtfahrt.py`, `M tests/test_beat_nachtfahrt.py`, `?? toolshop/beat/mixdown.py` — untracked, so absent from the worktree; nothing in f1-f5 imports it) plus MAirina churn. Ledger commits on master stay explicit-path-only.
- **A-DISPATCH:** verified against source: the editable finder maps `toolshop` → `D:\Projects\Music-AI-Toolshop\toolshop` (pitfall confirmed verbatim); :8777 is rooted at `Stemmeca_alatkka/stems` (`/instrumental.wav` → 200, `/htdemucs_6s/` lists the 2Pac dir); all four `test_flip_*.py` regression files exist.
- **f2 confirmed SKIPPED:** `toolshop/beat/drums_synth.py` on master at `e0b44ba` with `one_shots(sr,seed)`, `riser(duration_s,sr,seed)`, `gated_reverb(x,sr,room_size,wet_db,gate_ms,fade_ms)`.

## Waves

| Wave | Agent | Status | Handoff (in WT) | Notes |
|---|---|---|---|---|
| f1 sample prep | A | **dispatch attempted** 2026-10-02 ~22:50 — `run_subagent(implementer, TASK_F1+preamble)` failed: weekly usage quota exhausted (trace 46e64c43…). Fallback = paste-mode block emitted in session; re-dispatch when quota reloads. | `ORCHESTRATION/beat_nachtfahrt_flip/f1/agent_a_f1_handoff.md` | TASK_F1 + harness preamble |
| f2 synth drums | B | **SKIPPED** — `drums_synth.py` confirmed on master `e0b44ba` (one_shots/riser/gated_reverb) | `…/f2/…` | TASK_F2 not dispatched |
| f3 arrangement + lanes | C | planned | `…/f3/agent_c_f3_handoff.md` | TASK_F3 |
| f4 mix + master + check | D | planned | `…/f4/agent_d_f4_handoff.md` | TASK_F4 |
| f5 verify (read-only) | E | planned | `…/f5/agent_e_f5_verify_handoff.md` | TASK_F5 |
| f6+ fix | F | only on defects | `…/f6/…` | from f5's numbered defects |

## Invariants every wave (copied into each prompt)

- **Python and imports.** Only `D:\Projects\Music-AI-Toolshop\.venv\Scripts\python.exe`, with `-X utf8 -u` for long runs. **Cwd = `D:\Projects\Music-AI-Toolshop-wt-flip` and `PYTHONPATH=D:\Projects\Music-AI-Toolshop-wt-flip`** for every python/pytest run. Before tests, print `toolshop.__file__` and confirm it is under the worktree.
- **Paths.** Absolute paths only. STEMS = `D:\Projects\Music-AI-Toolshop\Stemmeca_alatkka\stems` (it is absent in the worktree). OUT = `STEMS\beats\nachtfahrt_flip`.
- **Allowed audio reads.**
  - prep: htdemucs_6s `{guitar,other,bass,drums}.wav` and `STEMS\instrumental.wav`
  - render/mix/master: only `OUT\prep\**`
  - the drums/bass stems are analysis-only
- **Protected code.** No edits to `toolshop/flip/*`, `toolshop/premaster.py`, or the other lane's `toolshop/beat/{drums_synth,nachtfahrt,mixdown}.py` (reuse only). No new dependencies. Deterministic, with seeded RNG.
- **Git.**
  - `git -C D:\Projects\Music-AI-Toolshop-wt-flip` on branch `beat/nachtfahrt-flip`. Explicit paths; add / diff --cached / commit as separate calls; PowerShell for git.
  - Never checkout in the main worktree. Never merge. Never stage foreign lanes. No WAVs. Never `--no-verify`.
- **Evidence.** Every claim quotes the command, its exit code and key output. Commit before claiming. Foreground only; never "background + end turn". Never claim it "sounds" good.

## Dispatch prompts (verbatim)

### TASK_F1

```text
Execute wave f1 (sample prep) of the "Nachtfahrt" FLIP in the worktree D:/Projects/Music-AI-Toolshop-wt-flip (branch beat/nachtfahrt-flip). You are the implementer. Do only f1.

READ FIRST
1. D:/Projects/Music-AI-Toolshop-wt-flip/AGENTS.md
2. The plan D:/Projects/.workspace_archive/plans/nachtfahrt-ogcm-flip.md: Lane isolation, Context, Producer decisions, the f1 gate.
3. The spec D:/Projects/.workspace_archive/plans/expected_output_nachtfahrt_flip_20261002_220636.md. Read the WORKTREE IMPORT PITFALL at the top.
4. Reuse: toolshop/flip/chops.py (snap_to_zero_crossing(y_mono, sample, radius_s, sr), apply_microfade(chunk, sr, fade_ms)), toolshop/flip/master.py (integrated_lufs) and toolshop/flip/sample_voices.py (estimate_key, PC_NAMES). Also look at scripts/ogcm_stem_audition.py for how stems are windowed.

ENVIRONMENT (mandatory)
- Cwd = D:/Projects/Music-AI-Toolshop-wt-flip.
- PowerShell: $env:PYTHONPATH='D:\Projects\Music-AI-Toolshop-wt-flip'
- Python = D:/Projects/Music-AI-Toolshop/.venv/Scripts/python.exe
- First run: python -c "import toolshop; print(toolshop.__file__)". It MUST print a path under the worktree; otherwise STOP and report.
- STEMS = D:/Projects/Music-AI-Toolshop/Stemmeca_alatkka/stems (absolute; absent in the worktree).
- OUT = STEMS/beats/nachtfahrt_flip.
- Git: git -C D:/Projects/Music-AI-Toolshop-wt-flip, via PowerShell.

FACTS (measured earlier; your job is to re-measure locally and confirm or correct them)
- Felt grid 89.1 BPM, 2.6936 s per bar. 54.0 s sits on a bar line. The phrase window 59.3872-70.1616 s is 4 bars.
- However, chops.py measured 90.67 BPM globally, and downbeat confidence was low (0.02-0.08).
- Key F# minor. Bar harmony F#m7 | Dmaj7 alternating, starting with F#m7 at 59.387 s.
- Stems: htdemucs_6s "2Pac - Only God Can Judge Me"/{guitar,other,bass,drums}.wav. The guitar carries the lead/wail line. instrumental.wav is the full instrumental (the reference).

BUILD
1. toolshop/beat/flip_segment.py (new): pure functions, mono/stereo float32, deterministic.
   - load_window(path, t0, t1)
   - local_tempo(drums_y, sr): onset-envelope autocorrelation plus a tempogram over 45-80 s, restricted to 80-100 BPM. Return the bpm and its evidence.
   - bar_phase_offsets(drums_y, sr, bpm, anchors_s): for each anchor (54.0, 59.3872), measure the ms offset of the nearest strong low-band (<120 Hz) kick onset.
   - refine_phrase_length(bed, sr, start_s, nominal_s, tol=0.03): search L within +/-3% of nominal and maximize loop-seam continuity, i.e. the normalized cross-correlation of bed[start:start+w] vs bed[start+L:start+L+w] with w=0.5 s, combined with an onset-envelope match. Return L and its score.
   - varispeed(x, r): resample so that playback at the same sr is r times faster, with pitch +12*log2(r) st. Use scipy.signal.resample_poly with a rational p/q from fractions.Fraction(r).limit_denominator(4000). Output length = round(len/r) +/- 1. NO time-stretch.
   - make_chops(phrase, sr, bpm): returns c1..c16 (1 beat each) and h1..h8 (half bar). Boundaries are snapped with snap_to_zero_crossing (radius 2 ms), each chop gets a 3 ms apply_microfade, and each chop's nominal grid start is recorded.
   - bar_roots(bass_y, sr, start_s, bar_s, n_bars): per-bar chroma of the low band (librosa chroma_cqt, fmin about 30 Hz, a few octaves); return the argmax pitch class per bar plus confidence.
   - drum_residue(bed, drums, sr): the correlation of the bed onset envelope with the drums-stem onset envelope over the phrase, and the share of bed energy above 5 kHz at drums-onset frames vs other frames.
   - recognizability(bed, ref, sr): the mean frame-wise cosine similarity of chroma_cqt(bed) vs chroma_cqt(ref) over the same window.

2. scripts/build_nachtfahrt_flip.py (new). argparse: --stage {prep} (later waves add render/mix/master/all), --outdir (default OUT), --stems-root (default STEMS). It inserts its parent's parent into sys.path (like scripts/ogcm_sample.py) and has no input() calls. The prep stage:
   a. Records build_started_utc and installs sys.addaudithook, recording "open" events for .wav/.flac/.mp3/.mid/.midi paths.
   b. Builds the bed = guitar + other (sample-aligned sum), stereo. Bass and drums are NOT in the bed.
   c. Measures the local tempo and bar-phase offsets. Refines the phrase start to the measured downbeat nearest 59.3872 s (+/-40 ms max; report it).
   d. Refines L near 4 bars. Then r = L / (4*240/106), the target bpm is 106, and pitch_shift_st = 12*log2(r).
   e. Writes OUT/prep/phrase_native.wav (bed over [ps, ps+L]), OUT/prep/phrase_106.wav = varispeed(phrase_native, r), and OUT/prep/runup_106.wav = varispeed(bed[54.0 .. ps], r).
   f. Writes OUT/prep/chops/c01..c16.wav and h1..h8.wav from phrase_106.
   g. Computes bar_roots on the bass stem over the phrase (native), plus the +pitch_shift_st mapped roots, and states them as pitch-class names. Expected native F#/D/F#/D, i.e. A/F after the shift. If different, report; do not force it.
   h. Computes drum_residue and recognizability: bed phrase vs instrumental.wav over the same window. Target >= 0.80.
   i. Writes OUT/prep/sample_manifest.json with:
      - sources, with paths and sha256 of the input stems
      - the windows, measured bpm, phase offsets, L, r, pitch_shift_st and target bpm 106
      - native and shifted roots
      - the residue and recognizability metrics
      - per-output sha256, build_started_utc and the audit list of reads (must be ONLY the allowed stems + instrumental.wav)
   PCM_24 at 44.1 kHz throughout.

TESTS: create tests/test_beat_nachtfahrt_flip.py, section "f1", synthetic only.
- varispeed: a 440 Hz sine with r=2^(3/12) comes out with peak frequency 440*r +/- 0.5%, and the length round(n/r) +/- 1.
- refine_phrase_length finds the true period of a synthetic periodic signal (an onset train plus tone) within 1 ms.
- make_chops returns 16 + 8 chops with boundaries within 2 ms of the grid, and every chop has micro-fades (first and last samples near 0).
- bar_roots identifies synthetic bass tones (F#1 / D2 per bar).
- recognizability(x, x) == 1.0 (+/- 1e-6), and for x vs noise it is < 0.5.
- local_tempo on a synthetic 89.1 BPM click track gives 89.1 +/- 0.2.

GATES (quote each command, exit code and key output; Cwd = WT, PYTHONPATH = WT)
- the toolshop.__file__ sanity print
- python -m pytest tests/test_beat_nachtfahrt_flip.py -q
- the flip regression: python -m pytest tests/test_flip_sample.py tests/test_flip_arrange.py tests/test_flip_master.py tests/test_flip_bed_lanes.py -q
- python -X utf8 -u scripts/build_nachtfahrt_flip.py --stage prep
- Print the sample_manifest headline: bpm, phase offsets, L, r, pitch shift, roots, residue, recognizability, audit list.
- Determinism: run prep again into a scratch --outdir and confirm the SHA256 of phrase_106.wav and all chops are identical.
- git -C WT diff --stat master -- toolshop/flip toolshop/premaster.py must be empty.

COMMIT (in the worktree, on branch beat/nachtfahrt-flip)
- Explicit paths: toolshop/beat/flip_segment.py, scripts/build_nachtfahrt_flip.py, tests/test_beat_nachtfahrt_flip.py.
- Message: feat(beat-flip): f1 sample prep - drumless bed, local tempo/phase, varispeed phrase + chops.
- No CHANGELOG in f1; the single entry comes in f4. No WAVs.
- Then write the handoff ORCHESTRATION/beat_nachtfahrt_flip/f1/agent_a_f1_handoff.md (in the worktree) and commit it as docs. It includes the commits, every gate with its exit code, the full manifest headline, deviations, and whether recognizability >= 0.80 and residue is acceptable (with mitigation proposals if not).
- Final message: the handoff path, commits, gate exit codes and the manifest headline.

CONSTRAINTS (invariants)
- Allowed reads only.
- No edits to toolshop/flip/*, toolshop/premaster.py or toolshop/beat/{drums_synth,nachtfahrt,mixdown}.py.
- No new dependencies; deterministic.
- Never checkout in the main repo; never merge; never stage foreign files.
- Foreground only; never re-run an identical failed command.
```

### TASK_F2 (CONDITIONAL — dispatch ONLY if `toolshop/beat/drums_synth.py` is absent from the branch)

```text
Execute wave f2 of the "Nachtfahrt" FLIP in the worktree D:/Projects/Music-AI-Toolshop-wt-flip.
- Build the synth drum kit as toolshop/beat/flip_drums.py, following EXACTLY the recipe in TASK_B1 of D:/Projects/Music-AI-Toolshop/handoffs/orchestration_ledger_beat_nachtfahrt_20261002.md: kick, snare, clap, hat_closed, hat_open, crash, riser, gated_reverb, one_shots.
- Same tests and thresholds, appended to tests/test_beat_nachtfahrt_flip.py under section "f2".
- Same environment rules as TASK_F1 (Cwd = WT, PYTHONPATH = WT, the toolshop.__file__ sanity print).
- Commit in the worktree: feat(beat-flip): f2 synth drums (flip lane copy).
- Handoff: ORCHESTRATION/beat_nachtfahrt_flip/f2/agent_b_f2_handoff.md.
Do not touch toolshop/beat/drums_synth.py, which belongs to another lane.
```

### TASK_F3

```text
Execute wave f3 (arrangement + chop sequencer + lane renders) of the "Nachtfahrt" FLIP in the worktree D:/Projects/Music-AI-Toolshop-wt-flip (branch beat/nachtfahrt-flip). You are the implementer. Do only f3.

READ FIRST
1. The plan D:/Projects/.workspace_archive/plans/nachtfahrt-ogcm-flip.md. THE "Arrangement and chop plan" TABLE IS THE SOURCE OF TRUTH.
2. The spec (with its import pitfall).
3. ORCHESTRATION/beat_nachtfahrt_flip/f1/agent_a_f1_handoff.md and OUT/prep/sample_manifest.json: the measured roots, L, r and chop grid.
4. Reuse (do not edit):
   - toolshop/beat/drums_synth.py: one_shots, riser (or flip_drums.py if f2 ran)
   - toolshop/flip/drums.py: grid_events, render_drums
   - toolshop/flip/bass808.py: Note808, render_808
   - toolshop/flip/sample_voices.py: render_organ(kind="drawbar"), stab_pattern (its default grids are the s6r stab grids), _soft_clip
   - toolshop/flip/bed_lanes.py: BedNote

ENVIRONMENT: as in TASK_F1. Cwd = WT, PYTHONPATH = WT, the toolshop.__file__ sanity print, absolute STEMS/OUT paths, git -C WT via PowerShell.

BUILD

1. toolshop/beat/flip_arrange.py (new).

DATA
- BPM = 106, BAR_S = 240/106, STEP_S = BAR_S/16, N_BARS = 80, SR = 44100, TAIL_S = 4.0, KEY = "A minor".
- ARRANGEMENT: intro 1-4, hook_a 5-12, verse1 13-28, hook_b 29-36, verse2 37-52, hook_c 53-60, bridge 61-68, hook_d 69-76, outro 77-80.
- CHORDS per phrase bar: from sample_manifest's shifted roots. Expected A, F, A, F, i.e. Am7 [60,64,67,69] and Fmaj7 [60,64,65,69].
  - If the measured roots differ, use the A-natural-minor diatonic 7th chord on the measured root, close-voiced within MIDI 57-72, with common tones kept.
  - 808 roots: A1=33, F1=29 (or the measured root in octave 1).
- DRUM GRIDS (16 steps per bar), encoded HERE as data. Do not import them from the other lane.

  | Part | Verse | Hook |
  |---|---|---|
  | kick | bar A x.....x...x..... / bar B x..x......x..x.. | x...x...x...x... |
  | snare + clap | ....x.......x... | ....x.......x... |
  | closed hat | x.x.x.x.x.x.x.x.; every 4th bar steps 12-15 become 16ths with a 32nd ratchet on 14-15 | 16ths, accents 1.0 / 0.6 |
  | open hat | step 14 of every 4th bar | ..x...x...x...x. |
  | crash | — | bar 1 of each hook, and bar 77 |

  Bridge: bars 61-64 have only a kick on beat 1, low-passed at about 200 Hz; bars 65-68 use the hook kick; bar 67 has snare 8ths; bar 68 has snare 16ths rising in velocity 0.4 -> 1.0 and pitch +5 st across the bar (resample the one-shot).
  Risers: bars 3-4, 27-28, 51-52 and 67-68, each 2 bars, ending on the next downbeat.

SAMPLE-LANE SEQUENCER: chop-level placement, sample-accurate at round(t*SR), with 3 ms crossfades at joins. Phrase P = phrase_106 (P1-P4 = its bars); chops c1-c16 and h1-h8; run-up R = runup_106.
- intro 1-4: R followed by P1-P2, placed so the section ends exactly at bar 5's downbeat (trim R's head if needed; report it). Telephone filter: HP 300 Hz plus an LPF sweeping exponentially 600 Hz -> 4 kHz across bars 1-4. Bar 4 beat 4 = c16 reversed.
- hooks (5-12, 29-36, 53-60, 69-76): P1-P4 twice, intact.
- verse1 13-28: bars alternate P1 / P2. LPF 3 kHz and -3 dB on the whole verse. Every 4th verse bar, beat 4 = c8 retriggered as 16ths x4, with gains 1.0, 0.8, 0.6, 0.4. Every 8th verse bar (20 and 28), beats 3-4 are muted.
- verse2 37-52: as verse1, but alternating P3 / P4. Bars 45-52 use h-chop re-sequencing: (h1 h2)(h1 h4)(h5 h6)(h5 h8) repeating, 2 half-bars per bar.
- bridge 61-64: P3-P4 reversed, through a hall wash (pedalboard Reverb room 0.9, wet 1.0) mixed with 20% dry. bridge 65-68: P1 sliced into 8ths (65-66), then 16ths (67-68), with an LPF rising 2 kHz -> 10 kHz exponentially, plus a TAPE-STOP on bar 68 beat 4: variable-rate playback whose rate falls linearly 1 -> 0 over the beat, via cumulative-phase interpolation.
- outro 77-80: P1-P4, LPF closing 4 kHz -> 400 Hz exponentially, plus a tape-stop on bar 80 beat 4.
- Hook D also gets a sample_oct lane: P1-P4 x2 pitch-shifted +12 st with pedalboard.PitchShift (time-preserving; orchestrator correction: NOT varispeed), HP 2 kHz. Its level is set in f4.

OTHER LANES
- bass808: render_808. Hooks: roots on steps 0 and 8 of each bar, 8 steps each. Verses and bridge 65-68: the root on each kick hit, legato to the next hit. Silent in intro, bridge 61-64 and outro. Slides only where bass808 allows (m3/P4); A <-> F is a M3, so expect no slides.
- stabs: hooks only. stab_pattern over chords [{"bar": i, "notes": voicing}] for the hook bars, then render_organ(kind="drawbar").
- drums: kick, snare (snare + clap layered), hats (closed + open), fx (crash + risers). Use grid_events + render_drums with one_shots(), duplicated to stereo.

RENDER
- render_lanes(prep_dir, sr=44100) -> dict with EXACTLY these 8 stereo lanes, each int((N_BARS*BAR_S + TAIL_S)*sr) long: sample, sample_oct, kick, snare, hats, fx, bass808, stabs.
- DRY: no sends, sidechain or bus processing; the arrangement filters above are part of the composition and stay.
- Each lane is peak-guarded <= 0.95.
- section_map() and composition_hash(): sha256 of the canonical JSON of all data, plus sample_manifest's sha256.

2. scripts/build_nachtfahrt_flip.py: add --stage render.
- It installs the audit hook.
- It calls render_lanes(OUT/prep).
- It writes OUT/stems/<lane>.wav (PCM_24), OUT/section_map.json and OUT/render_manifest.json. The render manifest holds the per-lane per-section RMS dB and peak, composition_hash, build_started_utc, and files_read_during_render (which must be a subset of OUT/prep/**).

TESTS (append, section "f3"; no full-length renders)
- The arrangement covers 1-80 exactly once.
- The chop-map data per section equals the plan table: intro, hooks intact, the verse alternation, the stutter on every 4th bar (beat 4 = c8 x4 with gains), the mutes in bars 20/28/44/52, the h-sequence in bars 45-52, bridge reversed + slices, outro.
- Tape-stop: the rate is monotone non-increasing and ends at 0; the output length equals 1 beat.
- Reverse is exact (equals x[::-1] before fades).
- No 808 notes in intro / 61-64 / outro. Stabs only in hooks. sample_oct is non-zero only in hook D.
- The drum grids equal the plan strings.
- A render_lanes smoke test on a synthetic prep fixture (tmp_path; tiny synthetic phrase, chops and run-up) for 2 bars at sr 22050: finite and <= 1.0. Add a minimal bars= parameter for this.

GATES (quote each command, exit code and key output; Cwd = WT, PYTHONPATH = WT)
- the sanity print
- the pytest file
- the flip regression
- python -X utf8 -u scripts/build_nachtfahrt_flip.py --stage render (foreground; split if slow)
- print the per-lane per-section RMS table
- determinism: render into a scratch --outdir and confirm the 8 stem SHA256s are identical
- the audit reads are a subset of OUT/prep
- the protected diff vs master is empty

COMMIT (worktree)
- Explicit paths: toolshop/beat/flip_arrange.py, scripts/build_nachtfahrt_flip.py, tests/test_beat_nachtfahrt_flip.py.
- Message: feat(beat-flip): f3 arrangement + chop sequencer + lane renders.
- Then write the handoff ORCHESTRATION/beat_nachtfahrt_flip/f3/agent_c_f3_handoff.md and commit it as docs.
- Final message: the handoff path, commits, gate exit codes, the RMS table and the determinism evidence.

CONSTRAINTS: the invariants (as in TASK_F1).
```

### TASK_F4

```text
Execute wave f4 (mix + master + release check + page) of the "Nachtfahrt" FLIP in the worktree D:/Projects/Music-AI-Toolshop-wt-flip (branch beat/nachtfahrt-flip). You are the implementer. Do only f4.

READ FIRST
1. The plan (the "f4 mix specifics" section)
2. The spec: O1 IS YOUR TARGET; O4 too.
3. The f3 handoff, toolshop/beat/flip_arrange.py and OUT/render_manifest.json.
4. Reuse (do not edit):
   - toolshop/flip/master.py: master_audio, integrated_lufs, true_peak_dbfs. Its docstring explains the pedalboard Limiter makeup-gain trap. NEVER use pedalboard Limiter outside master_audio.
   - toolshop/premaster.py: analyze_premaster.
   - toolshop/beat/drums_synth.py: gated_reverb.

ENVIRONMENT: as in TASK_F1. Cwd = WT, PYTHONPATH = WT, the sanity print, absolute STEMS/OUT, git -C WT.

BUILD

1. toolshop/beat/flip_mix.py (new).
- Starting lane gains in dB (tune to the O1 targets):
  sample 0 (the lead element), sample_oct -14, kick 0, snare -3, hats -10, fx -12, bass808 -2, stabs -10
- EQ:
  - sample: HP 150 Hz + a peak cut of -2 dB at 300 Hz (Q about 1)
  - stabs: HP 200 Hz
  - sample_oct: HP 2 kHz
- Kick-keyed sidechain from the kick event times (from flip_arrange's builders, not detection). Attack 2 ms, exponential release ~150 ms. Depths: sample -3 dB, bass808 -4 dB, stabs -2 dB.
- Sends; each return is part of its lane's delivered stem, so stems stay additive:
  - snare -> gated_reverb at about -8 dB
  - sample -> plate (Reverb room ~0.4) at -16 dB, plus a dotted-8th delay 0.424528 s (0.75*60/106; feedback ~0.3) at -20 dB, in HOOK bars only
- Every stem: the side channel below 120 Hz is removed (M/S).
- Section gain automation is allowed to hit the O1 section-loudness targets (e.g. verse sample/hats trims).
- premix = the EXACT sum of the processed stems (no bus compression). Then one scalar so the premix peak is -6 dBFS, applied to every stem too.
- Write OUT/stems_mixed/<lane>.wav and OUT/nachtfahrt_flip_premix.wav (PCM_24).

2. Master stage (--stage master; --stage all = prep? NO; all = render + mix + master, and prep runs separately only if OUT/prep is missing):
- Glue: pedalboard Compressor (threshold about -16 dB, ratio 2, attack 30 ms, release 150 ms) on the premix.
- master_audio(glued, sr, target_lufs=-9.0, tp_ceiling_dbtp=-1.0) -> OUT/nachtfahrt_flip_master.wav
- master_audio(glued, sr, target_lufs=-14.0) -> OUT/nachtfahrt_flip_master_streaming.wav
- Persist both reports.

3. scripts/check_flip_release.py --dir <OUT>: implement EVERY O1 condition in the spec.
- Print one PASS/FAIL line per condition, with the measured value. Exit 0 only if all pass. Read-only.
- Section loudness = integrated LUFS of each section slice of the main master vs the mean of the 4 hooks.

4. OUT/release_manifest.json holds:
- composition_hash, build_started_utc, "source_audio_in_output": true
- sample_sources: the htdemucs_6s guitar/other paths + sha256, plus the sample_manifest reference
- files_read_during_render
- bpm 106, key A minor, bars 80, section_map
- the gain/automation table and both master reports
- the artifact list with sha256 and mtime
- the label: "Contains a sample of 2Pac - Only God Can Judge Me (1996). Not for Suno; sample clearance required for any release."

5. OUT/index.html holds:
- the title "Nachtfahrt (OGCM flip) — 106 BPM, A minor"
- players for the main master, the streaming master, the premix and every stems_mixed lane
- the measured-numbers table and the section map
- the sample label above, in a visible badge
- the credit: "Flipped from the OGCM 54-67 s segment; chopped, arranged, mixed and mastered by Claude (orchestrated waves)."

6. CHANGELOG.md (in the worktree): ONE Answer entry for the flip lane, with the next unique #NNN. grep the branch's CHANGELOG.md AND git -C D:/Projects/Music-AI-Toolshop show master:CHANGELOG.md; #078 is taken (the other lane's b1). Note in the entry that it is "renumber at merge if taken".

TESTS (append, section "f4"; short synthetic inputs)
- The sidechain dips by the configured depth at the kick times and recovers.
- The side channel below 120 Hz is below -40 dB vs mid after processing.
- Σ processed stems == premix within 1e-6.
- The check_flip_release condition functions: a pass on a synthetic fixture, and a fail on a broken one (e.g. a wrong LUFS or a missing file).

GATES (quote each command, exit code and key output; Cwd = WT, PYTHONPATH = WT)
- python -X utf8 -u scripts/build_nachtfahrt_flip.py --stage all (foreground; split render / mix / master across calls if slow)
- O1: python -X utf8 scripts/check_flip_release.py --dir <OUT> must EXIT 0. If it fails, iterate on the mix gains/automation (NOT the thresholds) and report every iteration's failing lines.
- O2: the pytest file
- O3: the flip regression, plus the protected diff vs master empty
- O4: check_audition_serve.py --base http://127.0.0.1:8777/beats/nachtfahrt_flip --dir <OUT> --glob "*.wav" --index index.html, and again with --glob "stems_mixed/*.wav"
  - Check :8777 first. If it is down, start `python -m http.server 8777` with cwd D:/Projects/Music-AI-Toolshop/Stemmeca_alatkka/stems as a background process and leave it running.

COMMIT (worktree)
- Explicit paths: toolshop/beat/flip_mix.py, scripts/build_nachtfahrt_flip.py, scripts/check_flip_release.py, tests/test_beat_nachtfahrt_flip.py, CHANGELOG.md.
- Message: feat(beat-flip): f4 mixdown + master (-9/-14 LUFS) + release check.
- Then write the handoff ORCHESTRATION/beat_nachtfahrt_flip/f4/agent_d_f4_handoff.md and commit it as docs. It includes the gain table, the O1 output verbatim, the master reports, the iterations and deviations.
- Final message: the handoff path, commits, the O1 output verbatim, and the other gates.

CONSTRAINTS: the invariants (as in TASK_F1).
```

### TASK_F5

```text
READ-ONLY independent verification (wave f5) of the "Nachtfahrt" FLIP. The code is in the worktree D:/Projects/Music-AI-Toolshop-wt-flip (branch beat/nachtfahrt-flip); the outputs are in OUT = D:/Projects/Music-AI-Toolshop/Stemmeca_alatkka/stems/beats/nachtfahrt_flip.
- You may write exactly ONE file: D:/Projects/Music-AI-Toolshop-wt-flip/ORCHESTRATION/beat_nachtfahrt_flip/f5/agent_e_f5_verify_handoff.md.
- No code edits, no git add/commit/merge/push. Rebuilds go ONLY to a scratch outdir under your scratchpad.

READ: the plan, the spec (O1-O6 and the import pitfall), and the f1-f4 handoffs. Treat every number in them as UNVERIFIED.

ENVIRONMENT: Cwd = WT, PYTHONPATH = WT. The python -c "import toolshop; print(toolshop.__file__)" sanity print MUST show the worktree. Git through PowerShell.

CHECKS (quote each command, exit code and key output)

1. Git.
- git -C WT log --oneline master..HEAD lists the f1-f4 commits.
- No .wav files in any of them.
- git -C WT diff --stat master -- toolshop/flip toolshop/premaster.py toolshop/beat/drums_synth.py is empty.
- status --short is clean on toolshop, scripts and tests.
- The main worktree is still on master, and no branch was merged.

2. Re-run O1, O2, O3 and O4 exactly as written in the spec. O1 must exit 0.

3. O5 determinism + provenance.
- Write a small runner in your scratchpad that installs sys.addaudithook (recording "open" of .wav/.flac/.mp3/.mid/.midi) and runs the build's main for --stage prep, then render/mix/master, into a scratch --outdir.
- Allowed reads:
  - prep: only htdemucs_6s {guitar,other,bass,drums}.wav and instrumental.wav
  - later stages: only the scratch outdir's prep/**
- Compare SHA256 of the masters, the premix, stems_mixed/* and prep/phrase_106.wav: scratch vs the real OUT.
- Code-trace that the drums and bass stems never reach an output lane.

4. O6 with your OWN code (numpy/soundfile/librosa; you may import flip_arrange only for section_map and BAR_S):
- Hook recognizability: the chroma_cqt of each master hook, pitch-compensated (roll by the measured shift, rounded to semitones), compared to instrumental.wav over 59.387-70.16 s. Frame-aligned by varispeed time mapping; a mean cosine >= 0.75 per hook.
- The sample is the lead: in hook bars, the stems_mixed/sample RMS in 1-5 kHz is >= that of stabs, bass808 and sample_oct.
- Mud guard: the master's 200-500 Hz share in the hooks is <= 1.25 x its share in the verses.
- The premix peak is <= -3 dBFS.
- Loop-seam discontinuity at every P boundary in the hooks (the sample-step jump RMS around joins vs the local RMS).
- Drum residue: the bed-vs-drums correlation from f1, re-measured on the stems_mixed/sample hook region.
- Digital-silence spans inside content sections. Exclude digital silence before percentile statistics.
- Report crest factor and PLR of the main master, with a judgement.

5. Page: index.html links all files, shows the "not for Suno / clearance" badge, and has the credit line.

OUTPUT
The handoff holds a PASS/FAIL table per check with evidence, a NUMBERED DEFECT LIST (each item with the measured value, its threshold, and a suggested fix in flip_arrange/flip_mix terms), and a one-line verdict.
Final message: the verdict, the table and the defects.

CONSTRAINTS: venv python only, absolute paths, foreground only, and never re-run an identical failed command.
```

## f1 DONE — verify-and-complete (2026-10-02/03 ~00:10, Devin orchestrator, Normal mode)

- A prior session's f1 agent wrote the implementation (23:07-23:19) and was killed by the
  quota wall before verification/commit. Found disk state was verified, not trusted:
  gates re-run on the code as found, one real defect fixed, then committed.
- Native dispatch of a verify-and-complete wave failed again on weekly quota
  (trace 7b59939542622806291597d306d32ac5) — orchestrator executed per the b5 precedent
  (b-lane: "executed by orchestrator in Normal mode after subagent quota exhausted"),
  covered by the ACTIVE override line naming this lane's waves.
- Commits on beat/nachtfahrt-flip: `fa4db22` (code, 3 files) + `2d97f1c` (f1 handoff).
- Gates re-run green on committed code: toolshop.__file__ resolves to worktree;
  test_beat_nachtfahrt_flip 6/6; flip regression 151/151; prep exit 0;
  determinism 27/27 outputs sha256-identical; protected diff (toolshop/flip,
  toolshop/premaster.py) empty.
- Fix applied by completing executor: refine_phrase_length fine-search quantized L to
  fine_step=16 samples (synthetic test failed 0.855 < 0.9, L off by 8 samples);
  added per-sample NCC local argmax + rescore. Post-fix: test score 1.0000, L err 0;
  real-audio L moved 10.5751 -> 10.6443 s (onto the coarse onset peak).
- Manifest headline: tempo 90.18 BPM local; phase +77.9 ms > 40 ms cap -> not applied;
  L=10.6443 s; r=1.175307 (+2.7964 st -> 106 BPM); drum residue clean (onset corr -0.065).
- Deviations carried for f3/f5 (documented in f1 handoff, not forced):
  recognizability 0.7697 < 0.80 target; bass roots C#/B/A/F# != expected F#/D/F#/D
  (low-confidence chroma either way); audit open_events empty because libsndfile reads
  bypass sys.addaudithook — explicit_reads list covers provenance (same class as b-lane D3).
- A-CHANGELOG-2: Answer #081 taken by b5 fix wave (commit 70776f6); flip f4 entry now
  uses the next free number (#082 as of 3a948c4) — re-grep master's CHANGELOG at f4.
- f2 remains skipped (drums_synth.py on master). Next wave: f3 (arrangement + lanes).
