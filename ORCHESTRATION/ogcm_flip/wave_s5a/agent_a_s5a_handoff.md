# Wave s5a handoff — GATE S5a: wail finder + whine probe + dotted-8th sync

Agent: A (implementer) · Date: 2026-10-01 · Plan: `D:\Projects\.workspace_archive\plans\ogcm-s5-wail-resynth.md` (s5a)
Repo: `D:/Projects/Music-AI-Toolshop` (branch `master`, upstream `origin/master`; `git rev-parse --show-toplevel` = `D:/Projects/Music-AI-Toolshop`)

**Status: s5a done, all gates green. Gate G1 (the user's ear) is pending.** Nothing below identifies the wail; the ranking is a heuristic for where to *listen*.

## Commits

| Hash | Subject |
|---|---|
| `3458637` | `feat(#074): GATE S5a - wail finder stem audition + whine probe + dotted-8th delay sync` — 6 files, +929/−24: `scripts/ogcm_stem_audition.py` (new), `toolshop/flip/sample_voices.py`, `scripts/ogcm_sample.py`, `tests/test_flip_sample.py`, `CHANGELOG.md` (#074), `ORCHESTRATION/ogcm_flip/LEDGER.md` (s5a row) |
| (follow-up) | `docs(#074): ...` — this handoff only; hash is in `git log` (a file cannot cite its own commit) |

Checks on `3458637`: zero `.wav/.flac/.mp3` in the commit; `git diff --stat 20e1774 HEAD -- bed_lanes.py arrange.py master.py` is empty; no diff line touches `extract_motif`/`extract_riff`. `git check-ignore` confirms `audition_s5/`, `audition_s5_stems/`, `index.html` (all under gitignored `Stemmeca_alatkka/stems/`); nothing force-added. The first commit attempt failed (I passed `-F -` plus a here-string, so git read the message as a pathspec); HEAD was unchanged, the six files stayed staged, and I retried with `-m` (a changed command). No commit was created by the failed call.

## Commands and results (all foreground, venv python 3.11, absolute paths)

| # | Command (abridged) | Exit | Key output |
|---|---|---|---|
| pre | `git -C … status --short` / `log --oneline -5` (PowerShell tool; the Bash tool has no `git` on PATH, exit 127, classified as PATH and switched tool) | 0 | dirty tree = foreign lanes only (listed below); HEAD was `20e1774` |
| pre | `.venv python -c "import librosa; print(librosa.__version__, hasattr(librosa,'pyin'))"` | 0 | `0.11.0 True` |
| O2 | `.venv python -m pytest tests/test_flip_sample.py -q` | 0 | **49 passed** (39 prior + 10 new), 14.73 s |
| O4 | `pytest` on `test_flip_sample.py`, `test_flip_arrange.py`, `test_flip_master.py`, `test_flip_bed_lanes.py` | 0 | **97 passed**, 22.87 s |
| O5 | `scripts/check_riff.py --manifest …/audition_s4/manifest.json` | 0 | 6/6 PASS (coverage 0.969, n_notes 13, 2.413 n/s, leap 10, snapped 0, F# minor −4 → pc2); `O5: PASS` |
| O1″ | `scripts/verify_sample_pack.py --dir …/audition_s5 --glob "s5_*.wav" --min-files 1 --min-s 15 --max-s 45 --lufs -16 --lufs-tol 1.0 --tp-max -1.0` | 0 | `PASS s5_00_riff_whine.wav 21.5s 44100Hz 2ch -16.00LUFS tp=-7.65dBTP` |
| O3″ (a) | `scripts/check_audition_serve.py --base http://127.0.0.1:8777/flip_sample --dir …/flip_sample --glob "audition_s5/s5_*.wav" --index index.html` | 0 | `PASS audition_s5/s5_00_riff_whine.wav http=200 linked=yes` |
| O3″ (b) | same, `--glob "audition_s5_stems/stem_*.wav"` | 0 | 5/5 `http=200 linked=yes` (backing_vox, bass, guitar, other, vocals). :8777 was already up (HTTP 200 checked first), so I did not start a server |
| S5 render | `scripts/ogcm_sample.py --pack s5` | 0 | `s5_00_riff_whine` 21.5 s, −16.0 LUFS, `pass: true`, `source_audio_in_output: false`, `lead_delay_s: 0.505051` |
| S5 determinism | same, `--outdir <scratch>` | 0 | `s5_00_riff_whine.wav`, `manifest.json`, `verification.json` SHA256 **IDENTICAL** to the first render |
| S4 proof | `scripts/ogcm_sample.py --pack s4 --outdir <scratch>` | 0 | see below |
| stem audition (rank) | `scripts/ogcm_stem_audition.py --no-timeline` | 0 | 5 clips + `stem_ranking.json`; metrics identical between my two runs (deterministic) |
| timeline 1 | `… --timeline-only --timeline-stems vocals` | 0 | 10/10 chunks, not truncated, wall 358.1 s |
| timeline 2 | `… --timeline-only --timeline-stems backing_vox` | 0 | 10/10 chunks, not truncated, wall 333.6 s |
| closeout | `toolshop.closeout.run_closeout(<repo>)` (via a scratch script; the Bash tool has no `git`, so run from PowerShell) | **1 (declared)** | see "Close-out" |

**S4 unchanged — evidence used: re-render of `--pack s4` to a scratch outdir, SHA256 of every output vs the committed-render run in `audition_s4/`** (`_s4_source` is the S4 logic moved verbatim; `git diff` also shows the S4 meta/variants block unchanged apart from the riff rows now built by the shared `_riff_rows`):

```
manifest.json              IDENTICAL  3752E05FD0E9
s4_01_riff_sine.wav        IDENTICAL  35929CD2A0CA
s4_02_riff_ep.wav          IDENTICAL  52F8BEB8677B
s4_03_riff_oct.wav         IDENTICAL  BB52033FA485
s4_04_riff_native_Fsm.wav  IDENTICAL  59C922E624E3
s4_05_chop_REF.wav         IDENTICAL  97BF363F6518
verification.json          IDENTICAL  E31C2935F37D
```

**Provenance of the Suno-bound pack:** `audition_s5/` holds exactly `s5_00_riff_whine.wav`, `manifest.json`, `verification.json`. `_s5_variants` calls `_s4_source` (reads the transcription MIDI only) and `_render_s3` with `render_gfunk_lead`; `_real_chop` is referenced only by the S2/S3/S4 builders (grep of `ogcm_sample.py`), and `main` raises `SystemExit` if an s5 variant name contains `chop`/`_REF`. `source_audio_in_output` is computed from the variant names, not hard-coded.

## Stem ranking (`audition_s5_stems/stem_ranking.json`, window 54.0–67.0 s; sorted by `wail_score`)

| # | stem | wail_score | voiced_ratio | median note (MIDI) | p10-p90 MIDI | glide_share | vibrato_score | vibrato_depth_st | mean_voiced_prob | window RMS stereo / mono-mix (dBFS) | mid_share_700_3000 | clip LUFS / dBTP |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | vocals | 0.9056 | 0.786 | A#3 (58.19) | 53.89-60.59 | 0.413 | 0.743 | 0.828 | 0.106 | -23.62 / -24.0 | 0.256 | -20.0 / -4.92 |
| 2 | backing_vox | 0.8766 | 0.496 | A#3 (57.69) | 53.59-60.09 | 0.389 | 0.867 | 0.634 | 0.113 | -34.92 / -38.02 | 0.481 | -22.86 / -1.0 |
| 3 | guitar | 0.8485 | 0.895 | B4 (70.99) | 66.29-75.69 | 0.13 | 0.962 | 0.445 | 0.564 | -33.24 / -33.46 | 0.486 | -20.0 / -10.15 |
| 4 | bass | 0.6654 | 0.85 | C2 (36.19) | 35.89-38.09 | 0.179 | 0.864 | 0.296 | 0.123 | -22.26 / -22.26 | 0.0 | -20.0 / -6.31 |
| 5 | other | 0.5262 | 0.455 | A2 (45.19) | 37.89-73.99 | 0.08 | 0.929 | 0.354 | 0.113 | -34.66 / -38.21 | 0.209 | -20.05 / -5.77 |

Piano skipped (silent in the window per the plan).

`wail_score = 0.30*V + 0.20*R + 0.25*G + 0.25*B`, each term in [0,1] (formula and weights are written into the JSON):
V = min(1, voiced_ratio/0.60) · R = 1 if median voiced MIDI in [60,90], linear fall to 0 over 12 st outside · G = min(1, glide_share/0.30) · B = vibrato_score × min(1, vibrato_depth_st/0.25). Terms: vocals V1.0 R0.849 G1.0 B0.743; backing_vox V0.827 R0.808 G1.0 B0.867; guitar V1.0 R1.0 G0.432 B0.962; bass V1.0 R0 G0.598 B0.864; other V0.759 R0 G0.266 B0.929.

## Timelines (whole song, 30 s chunks, per-2-s bins of pyin-voiced AND MIDI ≥ 60, frame-RMS gated)

| stem | chunks | wall | song mean | 0:54–1:07 mean | top-5 bins (share of the 2 s) |
|---|---|---|---|---|---|
| vocals | 10/10 | 358.1 s | 0.047 | 0.091 | 02:04-02:06 (0.488) · 02:08-02:10 (0.477) · 02:14-02:16 (0.448) · 02:20-02:22 (0.407) · 00:36-00:38 (0.337) |
| backing_vox | 10/10 | 333.6 s | 0.039 | 0.050 | 02:04-02:06 (0.384) · 01:48-01:50 (0.349) · 02:08-02:10 (0.302) · 01:56-01:58 (0.279) · 00:16-00:18 (0.267) |

Also in `timeline_<stem>.json`: `top5_bins_spaced_8s` (vocals: 02:04, 02:14, 00:36, 01:54, 01:10; backing_vox: 02:04, 01:48, 01:56, 00:16, 04:24) and the full 149-bin array.

## Wall times

- Rank stage (clips + pyin, final run): **156.5 s** total. Per stem (read/resample · clip write · pyin): guitar 1.78/0.92/29.64 s, other 0.12/0.76/30.50, vocals 0.14/3.54/29.43, bass 0.11/0.77/29.53, backing_vox 0.11/0.87/28.26. (First run: 136.5 s total, same metrics.)
- Timeline: vocals **358.1 s** (prep 3.1 + pyin 355.0), backing_vox **333.6 s** (prep 3.9 + pyin 329.7). Neither was cut off.
- Test runs: O2 14.73 s, O4 22.87 s. S5 render ≈ 20 s.

## Deviations from the prompt (please read)

1. **Timeline pyin hop is 512, not 256.** The rank stage measured ~25–30 s of pyin per 13 s of audio at hop 256, which projects to ~9.7 min per 297 s stem, over the ~6 min stop rule. I chose hop 512 (cost ~ frames × states², about 2× cheaper) with every other pyin setting identical, recorded in the timeline JSON (`pyin.hop_note`). The 6 min budget stayed as the safety stop (`--time-budget-s 360`) and was not hit. Bins are 2 s, so 23 ms frames lose nothing for this purpose; window-vs-timeline activity numbers come from slightly different frame rates.
2. **Top-2 by `wail_score` are vocals and backing_vox; guitar (the plan's prime suspect) ranks 3rd (0.8485 vs 0.8766).** I ran the timelines for the top-2 exactly as specified and did not add guitar. **Question for the orchestrator:** want guitar's timeline too? It is ~6 min: `ogcm_stem_audition.py --timeline-only --timeline-stems guitar`. The gap is 0.028, small relative to the heuristic's uncertainty.
3. **Extra CLI flags** beyond the prompt: `ogcm_stem_audition.py --timeline-only / --timeline-top / --timeline-stems / --time-budget-s` (so the long runs could be split across calls per the constraints); `ogcm_sample.py --outdir` (needed for the "re-render S4 to a scratch outdir" proof; default unchanged).
4. **Metric design choices that were mine** (the prompt asked me to define `wail_score`): (a) a frame counts as voiced only if its RMS ≥ max(−60 dBFS, p95 − 35 dB), because separated stems carry a noise floor pyin would otherwise label voiced; (b) the vibrato term is weighted by the depth of the 4–7 Hz component, because `vibrato_score` alone is weakly discriminating: all five stems score 0.74–0.96 (peak-ratio on pitch noise is high). Extra JSON fields `window_rms_dbfs_monomix`, `mid_share_700_3000`, `vibrato_depth_st`, `rms_gate_db` are cross-checks.
5. **`backing_vox` clip is −22.86 LUFS, not −20**: its transients hit the −1 dBTP guard (−2.86 dB applied), and the peak guard takes precedence. `other` is −20.05 (rounding). Others −20.0.
6. **7 extra tests** in `tests/test_flip_sample.py` beyond the 3 requested (metrics on synthetic curves, pyin on a synthetic vibrato tone and on silence). They stay in the one test file so the commit path list is as specified.
7. **README / PROJECTS_INDEX not updated** (AGENTS.md "update in the same session as the behavior change") — they were not in the approved commit list. Open item for the orchestrator.
8. `python scripts/session_end.py` not run (out of scope for s5a).
9. `index.html` is gitignored and local; I built the S5 block with a scratch script (not committed) and verified the S4/S3/S2 body after it is byte-identical to the pre-edit file. I also changed the page `<title>` and added a few CSS rules for the table and the LOCAL-ONLY banner.

## Observations for G1 / s5b planning (facts only — none of this identifies the wail)

- **The stems are the plan's stems.** My mono-mix window RMS reproduces the plan's levels: guitar −33.46 (plan −33.5), backing_vox −38.02 (−38.0), other −38.21 (−38.2). My 700–3000 Hz share matches for `other` (0.209 vs 0.20) but not for guitar (0.486 vs 0.54) or backing_vox (0.481 vs 0.35); FFT and STFT methods agree with each other, so the plan's exact method is unknown. Not load-bearing.
- **pyin confidence differs a lot by stem:** mean voiced_prob is 0.564 for guitar and ~0.11 for every other stem. If s5b extracts a contour from one of these, guitar is the only stem whose pitch track is confident.
- The guitar stem's voiced pitch (p10–p90 MIDI 66.3–75.7, median B4) sits in the same span as the S4 riff's native notes (MIDI 66–76). A range coincidence, nothing more.
- vocals ranks first mainly through G (glide_share 0.413, V saturated at 1.0). I did not listen to it, so I cannot say why its pitch moves that much; the score rewards any strongly moving pitch, so a high rank is not evidence of a wail. That is why the user's ear, not the score, should pick.
- Both top-2 timelines peak at 02:04–02:10, nowhere near 0:54–1:07; in the 54–67 s window their activity is only slightly above the song mean (vocals 0.091 vs 0.047; backing_vox 0.050 vs 0.039).

## Files

- Committed: `scripts/ogcm_stem_audition.py`, `toolshop/flip/sample_voices.py`, `scripts/ogcm_sample.py`, `tests/test_flip_sample.py`, `CHANGELOG.md`, `ORCHESTRATION/ogcm_flip/LEDGER.md`.
- Local, gitignored (under `D:/Projects/Music-AI-Toolshop/Stemmeca_alatkka/stems/flip_sample/`): `audition_s5/` (Suno-safe: `s5_00_riff_whine.wav`, `manifest.json`, `verification.json`); `audition_s5_stems/` (**LOCAL ID ONLY, source audio, never for Suno**: `stem_{guitar,other,vocals,bass,backing_vox}.wav`, `stem_ranking.json`, `timeline_vocals.json`, `timeline_backing_vox.json`); `index.html` (S5 section on top). Listen at http://127.0.0.1:8777/flip_sample/.

## Close-out (AGENTS.md)

- All six paths I changed are committed; `git status` shows none of them dirty.
- `toolshop closeout` **exit 1 — declared**, two causes, neither mine: (a) 77 dirty entries from other lanes, (b) 10 commits ahead of `origin/master` (mine `3458637` plus nine earlier, from `f25c664`) — I did not push; pushing is the user's cadence.
- Submodule status: ` 9bddc72… mastering_tool (heads/claude/wonderful-johnson-h6xj4d)`, ` 7acba12… suno_prompter (heads/main)` (no `+`/`-`/`U` prefix).
- Still-dirty paths, all foreign lanes, none staged or touched by me: `MAirina_Tucc/` (24 entries: modified `mairina/*`, `tests/*`, `README.md`; untracked `devices.py`, `phonetics.py`, `rules.py`, `targets.py`, `lexicons/`, `ORCHESTRATION/mairina_v2/`, new tests); `lyrics_research/` (2 untracked dirs); ~30 `scratch_*` probe files plus `.scratch_i6/`, `.scratch_v1_audit.py`, `wt_bog_probe.txt`, stray `nul` (lyrics-sources lane scratch); `handoffs/orchestration_ledger_mairina_v2_20260930.md`; `ORCHESTRATION/prompts/*` (hemija lyricist/reviewer prompts, index, dispatch json) and modified `ORCHESTRATION/prompts/prompts_index.md`; ogcm_flip megaplan leftovers `ORCHESTRATION/ogcm_flip/wave_m1/`, `waves_megaplan.json`, `prompts/prompts_index.md`, `prompts/subagent_dispatch.json`, and modified `wave_m2/agent_b_bed_spike_handoff.md`; `ORCHESTRATION/ogcm_flip/wave_s5r/` (the s5r research agent's output, appeared during this wave); submodule working-tree markers for `mastering_tool` and `suno_prompter`. Plus the gitignored local audio/HTML listed above.
