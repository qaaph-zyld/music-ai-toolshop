# Nachtfahrt b4 — Independent Verification Handoff

Verifier: reviewer subagent `b6b6a99b` (orchestrated wave b4, read-only). Persisted by orchestrator (agent had no write tools).

## Verdict: needs-fix

Release gates O1–O5 pass. O6's mud guard fails by the spec's literal metric (ratio 36.56 against a limit of 1.25). Two minor deviations from the spec also stand: O4 for `stems/*.wav` fails, and the dry stems are not linked from the page. No measurement shows an audible defect in the main master, so the mud-guard fix is mostly a metric and arrangement question. Treat it as a fix-wave candidate, not a release blocker.

## Per-check table

| # | Check | Result | Evidence |
|---|---|---|---|
| 1a | b1–b3 commits exist | PASS | `092d276` (b1), `7b6ed92` (b2), `b7c09d7` (b3), plus docs commits. `git log` shows all of them. |
| 1b | No audio files in any commit | PASS | `git log --name-only 6c51d81..HEAD` filtered for wav/flac/mp3/mid/midi gave rc=1 (no match). |
| 1c | `toolshop/flip` and `toolshop/premaster.py` untouched since `6c51d81` | PASS | `git diff 6c51d81..HEAD --stat -- toolshop/flip toolshop/premaster.py` was empty. |
| 1d | `git status --short toolshop scripts tests` clean | PASS | No output. |
| 2 O1 | `check_beat_release.py` | PASS | exit 0, "PASS (21/21)". Main -9.01 LUFS / -1.006 dBTP, streaming -14.00 / -2.472, residual -107.4 dB, hook spread 0.19 LU. |
| 2 O2 | `test_beat_nachtfahrt.py` | PASS | rc=0, 43 passed. |
| 2 O3 | Flip regression (4 test files) | PASS | rc=0, 151 passed. |
| 2 O4 | Page served from :8777 | PARTIAL | `--glob "*.wav"` rc=0 (3 files, http=200, linked). `--glob "stems/*.wav"` rc=1 (http=200 but linked=NO). `--glob "stems_mixed/*.wav"` rc=0. |
| 3 O5a | Determinism | PASS | Two independent `--stage all` scratch builds (`out`, `out2`) were compared with real-outdir SHA256. Both: 23/23 wavs identical, 0 diffs. That covers the masters, the premix, 10 `stems_mixed` and 10 dry `stems`. |
| 3 O5b | Audit-hook provenance | PASS, with a coverage caveat | Runner installed `sys.addaudithook` and ran `build_nachtfahrt.main(["--stage","all","--outdir",scratch])`. Recorded 23 audio-extension opens, all mode `r` inside the scratch outdir. Opens outside scratch: **0**. Build printed `files_read=0`, RC 0. |
| 4 O6a | Lead audibility in hook bars | PASS | Lead's 1–5 kHz level is the highest in every hook section, both mixed and dry stems. Mixed, all hook bars (dB): lead 24.6, synthbass 12.0, pad 11.9, stabs 9.9, arp 5.3, bass808 -19.2. |
| 4 O6b | Mud guard | **FAIL** | 200–500 Hz share of the master: hooks 0.1447, verses 0.0040, ratio **36.6** vs limit 1.25. See D1. |
| 4 O6c | Premix peak | PASS | Premix peak -6.00 dBFS (limit ≤ -3). Low-band (<120 Hz) peak -11.13 dBFS. |
| 4 O6d | Crest and PLR | PASS (judgement below) | Main master: crest 9.27 dB whole track, 7.59 dB hooks. PLR 8.01 dB (>7 dB line). Streaming: crest 12.14 dB, PLR 11.53 dB. |
| 4 O6e | Section loudness table | PASS | Matches O1 printout. See table below. |
| 4 O6f | No digital-silence gaps inside content | PASS | Master and premix: 0 digital-silence spans ≥ 0.25 s. Silent stems match plan's gaps. 100 ms RMS percentiles computed with digital silence excluded. |
| 4 | b3 `loud_master` deviation | ACCEPTABLE | See judgement below. |
| 5 | `index.html` | PASS, with a minor gap | Credit line present verbatim. Links both masters, premix, 10 `stems_mixed/*.wav`. Dry `stems/*.wav` NOT linked. |

**Section loudness, recomputed** (LU relative to mean of four hooks = -7.16 LUFS):

| Section | LUFS | Rel. LU |
|---|---|---|
| intro | -26.60 | -19.44 |
| hook_a | -7.20 | -0.04 |
| verse1 | -11.25 | -4.10 |
| hook_b | -7.21 | -0.05 |
| verse2 | -11.22 | -4.06 |
| hook_c | -7.20 | -0.04 |
| bridge (whole) | -12.18 | -5.02 |
| bridge bars 61–64 | -13.83 | -6.67 |
| hook_d | -7.02 | +0.14 |
| outro | -26.80 | -19.65 |

Agrees with the O1 printout and the second scratch build.

**Silence and dynamics detail:**
- Silent stem spans correspond to plan: no drums in bars 61–64 apart from filtered kick, lead absent in verses/outro, synthbass only in hooks and bridge.
- 100 ms RMS percentiles (digital silence excluded), p5/p50/p95: hooks ≈ -11.7/-8.7/-7.0 dB; verses ≈ -18/-11.2/-7.2 dB.

**`loud_master` judgement (acceptable):**
- Lands target (-9.01 LUFS, -1.006 dBTP) with 0 samples ≥ 0.999 and PLR 8.0 dB. Hook crest 7.6 dB.
- Hook peak 0.8795. In hooks, 19.9% samples exceed 0.5, 5.1% exceed 0.7, 0.083% exceed 0.85 — soft knee working moderately.
- b3 showed `master_audio`'s limiter loop flattens sections: intro/outro were +0.4 to +0.5 LU relative to hooks, failing the plan's own section table.
- Deviation documented; streaming master still uses `master_audio`. Reuse of `toolshop/flip/master` not violated.
- Residual risk: soft clip's harmonic distortion not measured; no listening test.

## Defect list

1. **Mud guard fails by the spec's literal metric.**
   - Measured: master 200–500 Hz share hooks 0.1447 / verses 0.0040 → ratio 36.6 vs limit ≤ 1.25.
   - Other sections: intro 0.419, bridge 0.028, outro 0.409.
   - Cause: verses are bass-dominated (808 only, no lead/synthbass) → share ratio mostly arrangement artifact. Hooks at 14.5% share not mud in absolute terms.
   - Fix options, in order of preference:
     - (a) Change metric to absolute 200–500 Hz level (dB) hooks vs verses, re-baseline spec.
     - (b) Raise mid content in verses: verse pad/Rhodes-style lane at 200–500 Hz, or lower 808 fundamental in verses.
     - (c) 2–3 dB cut ~300 Hz on pad, stabs, arp in hooks.
   - Hook-side check: report absolute hook-vs-verse level before any hook EQ.
2. **O4 `stems/*.wav` fails.** All 10 dry stems return 200 but are not linked from index.html. b3 substituted `stems_mixed/*.wav` (rc=0) without changing the spec. Fix: link dry `stems/` in `_index_html` (scripts/build_nachtfahrt.py:174), or amend spec to `stems_mixed`.
3. **Audit hook coverage limited.** `sys.addaudithook` "open" does not see libsndfile C-level reads (`soundfile.read`). Zero-read claim relies on hook + static grep of `toolshop/beat/*.py` (no `sf.read`/`open(`/`load(` calls; only match is `hat_open`). `mix_stage` read of own `stems/*.wav` is by design. Hardening: also wrap `soundfile.read` and `SoundFile.__init__` in the build's audit.
4. **Premix verdict FLAG (not FAIL)** — crest/PSR flags. Not a failure; PLR 8.0 dB acceptable, no change needed.
5. **Minor (b3 handoff hygiene).** `taskkill //F //IM python.exe` killed the :8777 audition server; restarted by hand. Process incident, not code defect. Server up and serving.

## Nits

- Intro/outro at -19.4/-19.6 LU vs hook mean — pass the ≤-6 LU requirement but are very quiet (~-26.6/-26.8 LUFS). Consider ~-10 LU for listenability.
- `bass808` at 1–5 kHz is -19.2 dB in hooks — expected for a sub bass.

## What was checked

- [x] Correctness: O1–O6 re-run, sections, hashes
- [x] Security: audit hook shows no reads outside scratch outdir
- [x] Style: no code edits; read-only review
- [x] Performance: each full build ≈5–8 min
- [x] Tests: O2 43 passed, O3 151 passed
- [ ] Coverage gaps: no listening test; soft-clip harmonic distortion not measured

Scratch dir: `C:/Users/015ZCS/AppData/Local/Temp/tmp.4cxb5ekV2w`. Nothing written to repo or real outdir. No commits.
