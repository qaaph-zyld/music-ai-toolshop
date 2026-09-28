# Wave m5 handoff — agent E: W5 mixdown + mastering (F9) + GATE F blind pack

**Date:** 2026-09-28 · **Wave:** m5 / W5 master + GATE F + closeout prep (OGCM "Only God Can Judge Me" drill flip)
**Status:** STAGED FOR GATE F — code + docs drafts committed `9f024b3`; audio pack on disk (gitignored). **STOPPED AT GATE F per dispatch — user blind-picks the grid; orchestrator resumes this agent with the pick to record it and finish closeout (pick-dependent CHANGELOG/STATUS lines deliberately absent).**
**Inputs read:** `AGENTS.md`, megaplan Revised Waves > W5 + finding F9, `ogcm-flip.spec.md` W5, ADR-009 pack convention (vocal-chain-v2 megaplan + m2's `ogcm_bed_spike.py` implementation), wave_m3 + wave_m4 handoffs.

---

## What was built

| Piece | Path | Notes |
|---|---|---|
| Mastering core | `toolshop/flip/master.py` (NEW) | `mix_lanes` (deterministic unity sum, tail zero-pad, clip guard @0.99 recorded), `integrated_lufs`/`true_peak_dbfs` meters (pyloudnorm BS.1770; 4x polyphase TP approximation — same documented meter as `premaster.true_peak_dbfs`), `master_audio` (the F9 function), `master_file`. |
| Driver + pack | `scripts/ogcm_master.py` (NEW) | mix per arm → master → `--club` −9 LUFS variants → ADR-009 blind pack under `stems/flip_final/` (opaque names, seeded shuffle, hidden-key `manifest.json`, `verification.json` re-measured on written files, `GATE_F.md` without arm identities). |
| Tests | `tests/test_flip_master.py` (NEW) | 10 tests — sum/pad/clip-guard/gains, meter sanity on known signal, −14 and −9 spec convergence, determinism, gain cap on unmeasurable input, file roundtrip. |

No existing mix tool fit — `mix_vocal_over_instrumental.py` (named as a candidate in the dispatch) **does not exist in the repo**; fell back to the sanctioned "sum in numpy with peak check" inside `master.mix_lanes` (assembled-style clip guard, gains + pre-guard peak recorded to `mix_{arm}_events.json`).

### Mastering design note (F9 — why the loop looks like this)

`pedalboard.Limiter` is a **maximizer**: measured on this install (0.9.24) it applies ≈ +4.75 dB makeup drive at `threshold_db=-1` into a hard clipper at 0 dBFS. A naive "normalize → limit" loop can never converge — the limiter re-inflates every pass (first implementation oscillated at −9.25 vs −14 target). `master_audio` instead measures the chain's loudness delta each pass (`boost_est` = post-chain − pre-limiter LUFS) and aims the gain stage at `target − boost_est`; it converges in 3 iterations on the −14 masters, 6 on the −9 club arm. TP path: limiter's 0 dBFS clip → fixed `10^(−1/20)` ceiling shift → 4x-oversampled TP check → trim only if inter-sample overshoot. Deterministic: no randomness anywhere; identical results across two full runs.

## Measured results (verified this session on the written files)

```
[mix] felt_89:      65.696s  beat_peak=0.937 vocal_peak=0.602 pre_guard=1.058 guard=YES  lufs=-13.07
[mix] triplet_133: 130.343s  beat_peak=0.903 vocal_peak=0.602 pre_guard=0.975 guard=no   lufs=-13.48
[master] felt_89:     -13.07 -> -13.97 LUFS (target -14.0), TP=-3.63 dBTP, iters=3, passed=True
[master] felt_89 club-9:     -9.29 LUFS, TP=-1.0 dBTP, passed=True
[master] triplet_133: -13.48 -> -14.00 LUFS (target -14.0), TP=-3.72 dBTP, iters=3, passed=True
[master] triplet_133 club-9: -9.07 LUFS, TP=-1.0 dBTP, passed=True
[pack] flip_001.wav: 65.696s  -14.0 LUFS, TP=-3.66 dBTP
[pack] flip_002.wav: 130.343s -14.0 LUFS, TP=-3.72 dBTP
[pack] REFERENCE_prior_whole_flip.wav: 304.235s -14.41 LUFS, TP=-1.0 dBTP
[verify] arm LU spread 0.0 (<= 0.3) | TP ok=True | clips=none | bijection=True | PASSED=True
(exit 0)
```

- Masters land TP ≈ −3.6/−3.7 dBTP — comfortably under the −1 ceiling (the `boost_est` loop settles conservative); spec is ≤−1, met.
- `felt_89` unity sum peaked 1.058 → clip guard scaled to 0.99 (recorded in `mix_felt_89_events.json`); `triplet_133` needed no guard (0.975).
- Pack arm copies: `flip_001` ← trim −0.031 dB (match to louder-file floor), `flip_002` verbatim. Reference gain-matched −0.549 dB → −14.41 LUFS (labelled, NOT an arm).
- Hidden key: `flip_final/manifest.json` maps `flip_001`→`felt_89`, `flip_002`→`triplet_133` (seed 20260928). **Do not read before the user picks.**

## GATE F pack contents (`Stemmeca_alatkka/stems/flip_final/`, gitignored)

```
flip_final/
  mix_felt_89.wav, mix_triplet_133.wav          # identity-named premaster mixes (FLOAT)
  mix_{arm}_events.json                          # gains, peaks, clip-guard record
  mastered_felt_89.wav, mastered_triplet_133.wav # identity-named -14 LUFS masters (PCM_24)
  mastered_{arm}_club-9.wav                      # -9 LUFS club variants
  audition/
    flip_001.wav, flip_002.wav                   # opaque arm copies <- THE BLIND PICK
    REFERENCE_prior_whole_flip.wav               # labelled sanity-floor reference
  manifest.json                                  # hidden keys (seed 20260928)
  verification.json                              # ADR-009 pre-listening re-measure
  GATE_F.md                                      # pack doc, no arm identities + honest coverage note
```

## Test + suite evidence

```
$ .venv/Scripts/python.exe -m pytest tests/test_flip_master.py -q
10 passed, 1 warning in 4.67s            (exit 0)

$ .venv/Scripts/python.exe -m pytest tests/test_flip_*.py -q   (all 7 flip files)
103 passed, 1 warning in 42.77s          (exit 0)

$ .venv/Scripts/python.exe -m pytest D:/Projects/Music-AI-Toolshop/tests -q   (full suite, Cwd=repo root)
1412 passed, 2 skipped, 34 warnings, 11 subtests passed in 1189.28s (0:19:49)   (exit 0)
```

## `toolshop closeout` evidence (final run 2026-09-28, exit 1 — expected, all dirt pre-existing)

```
============================================================
CLOSE-OUT EVIDENCE BLOCK
============================================================

--- git status --porcelain ---
M ORCHESTRATION/ogcm_flip/wave_m2/agent_b_bed_spike_handoff.md
 M ORCHESTRATION/prompts/prompts_index.md
 M mastering_tool
 M suno_prompter
?? ORCHESTRATION/ogcm_flip/prompts/prompts_index.md
?? ORCHESTRATION/ogcm_flip/prompts/subagent_dispatch.json
?? ORCHESTRATION/ogcm_flip/wave_m1/
?? ORCHESTRATION/ogcm_flip/waves_megaplan.json
?? ORCHESTRATION/prompts/prompts_index_hemija.md
?? ORCHESTRATION/prompts/subagent_dispatch.json
?? ORCHESTRATION/prompts/wave1_hemija_lyricist.md
?? ORCHESTRATION/prompts/wave2_hemija_reviewer.md
?? lyrics_research/documents/

--- git submodule status ---
9bddc721a18bb387c8af730e6d9b6383e2d755ba mastering_tool (heads/claude/wonderful-johnson-h6xj4d)
 7acba12f99e24794b577e15e8bf4aa82616ed93c suno_prompter (heads/main)

--- verdict ---
FAIL
  - working tree not clean (staged/unstaged/untracked changes)
  - unpushed commits on current branch (17 total; this wave added):
    049c054 docs(#061): ogcm flip m5 handoff - agent E W5 master + GATE F pack evidence
    9f024b3 feat(#061): ogcm flip m5 - W5 mixdown + real mastering (F9) + GATE F blind pack builder
    (remainder pre-date this wave — m1..m4 + earlier history)
============================================================
```

**Dirty-path ownership — none of these are mine:**
- ` M wave_m2/agent_b_bed_spike_handoff.md` — m2 closeout addendum left uncommitted by an earlier session (same state m3/m4 reported).
- ` M ORCHESTRATION/prompts/prompts_index.md` — pre-existing.
- ` M mastering_tool`, ` M suno_prompter` — submodule pointers (other sessions; untouched).
- `?? ogcm_flip/{prompts/*, wave_m1/, waves_megaplan.json}` — orchestrator/m1 artifacts.
- `?? prompts/{hemija,subagent_dispatch}` + `?? lyrics_research/documents/` — other lanes.
- `?? wave_m5/` (this file) existed transiently before its own docs commit.
- Unpushed queue predates this wave; push remains a user-side decision (pre-push hook state unknown to this agent).

My wave's tree is clean after `9f024b3` + this handoff's docs commit: no m5-authored tracked file is dirty; all audio is under gitignored `stems/flip_final/` (verified via `git check-ignore` → `.gitignore:58 Stemmeca_alatkka/stems/`).

## Commits

- `9f024b3` — `feat(#061): ogcm flip m5 - W5 mixdown + real mastering (F9) + GATE F blind pack builder` (6 files: master.py, ogcm_master.py, test_flip_master.py, CHANGELOG #061, STATUS row, LEDGER m5 row)
- HEAD — `docs(#061): ogcm flip m5 handoff - agent E W5 master + GATE F pack evidence` (this file; self-hash is circular — cite `git log` HEAD, `049c054` at final closeout run)

## Resume instructions for the orchestrator (post-GATE-F pick)

1. User pick arrives as a filename (`flip_001` or `flip_002`); resolve arm via `flip_final/manifest.json`.
2. CHANGELOG #061: add the pick line (picked file → arm → shipped as `mastered_<arm>.wav`); STATUS row: GATE F resolved → winner.
3. LEDGER m5 row → `done` with the pick.
4. Re-run `toolshop closeout`, paste fresh evidence, commit, hand off to `D:\Projects\.workspace_archive\handoffs\` per spec W5 closeout (canonical handoff dir).

## Deviations / honest notes

- **Club arm iteration count:** −9 LUFS on the dense 130 s mix needs 6 passes (limiter + TP-trim fight each other under hard drive); `MAX_ITERS` raised 5→8, documented in code.
- **TP margin:** masters sit at −3.6/−3.7 dBTP rather than hugging −1 — the loop favors the loudness spec; spec is a ceiling, met.
- **Coverage unchanged:** 3/20 (felt_89) + 8/20 (triplet_133) lead phrases inside the render windows — m4 declared limitation carried verbatim into `GATE_F.md`; nothing stretched.
- **`premaster.py` untouched** — it's the analyzer; the mastering function lives in `flip/master.py` per F9.
- **Reference loudness:** `2pac_drill_flip_whole.wav` included labelled per dispatch option; gain-matched only (no mastering chain on prior art), −14.41 LUFS / TP −1.0 after its −0.549 dB trim.
