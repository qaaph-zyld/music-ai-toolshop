# Wave s5c handoff - GATE S5 independent verification + provenance audit (read-only)

Agent: C (reviewer, read-only) - Date: 2026-10-01 - Plan: `D:\Projects\.workspace_archive\plans\ogcm-s5-wail-resynth.md` (s5c + Verification)
Spec: `D:\Projects\.workspace_archive\plans\expected_output_ogcm_suno_sample_s5_20261001_005621.md`
Subject: commits `d4960c7` (feat #075) and `83137bd` (s5b handoff) on `D:/Projects/Music-AI-Toolshop` (`git rev-parse --show-toplevel` = `D:/Projects/Music-AI-Toolshop`, exit 0).

**VERDICT: PASS. Every gate re-ran green, every number I recomputed from `contour.npz` matches the manifest, and the five `s5_*` files contain no source audio (static trace, runtime open-log, and in-memory rebuild all agree). Whether any file sounds right is NOT assessed here: that is G2, the user's ear.**

Scope kept: no code edits, no write into `audition_s5/`, no git add/commit/push. This file is the only file I wrote. All analysis scripts were piped to the venv python on stdin (no scratch files); renders were rebuilt in memory only. Python: `D:\Projects\Music-AI-Toolshop\.venv\Scripts\python.exe` only. The Bash tool has no git/grep/head/wc here (exit 127 x1, classified PATH), so I used PowerShell and the Grep/Read tools. One of my own analysis scripts failed with `KeyError: 'transpose_st'` (it is under `manifest.recipe`, not top level); I fixed the key path and re-ran a changed script, not an identical retry.

## Per-check table

| # | Check | Result | Evidence (command -> exit -> key output) |
|---|---|---|---|
| 1a | `d4960c7` and `83137bd` exist | PASS | `git log --oneline -6` exit 0: `83137bd docs(#075)...`, `d4960c7 feat(#075)...`, then `e47be17`. |
| 1b | No .wav/.npz in either commit | PASS | `git show --stat d4960c7 83137bd`: d4960c7 = 6 files (CHANGELOG.md, ORCHESTRATION/ogcm_flip/LEDGER.md, scripts/check_contour.py, scripts/ogcm_sample.py, tests/test_flip_sample.py, toolshop/flip/sample_voices.py), 1418 insertions, 23 deletions (matches the handoff); 83137bd = 1 file (the handoff), 117 insertions. `git show --name-only` filtered for `.wav/.npz/.flac/.mp3`: 0. `git ls-files -- Stemmeca_alatkka/stems/flip_sample`: 0 tracked. `git check-ignore -v` shows `.gitignore:58 Stemmeca_alatkka/stems/` covering `s5_B_replace.wav`, `contour.npz`, `index.html`, `stem_guitar.wav`. |
| 1c | bed_lanes / arrange / master untouched | PASS | `git diff e47be17 HEAD -- toolshop/flip/bed_lanes.py toolshop/flip/arrange.py toolshop/flip/master.py` exit 0, 0 bytes. |
| 1d | sample_voices additive, extract_motif/extract_riff unchanged | PASS | `git diff --numstat e47be17 HEAD -- toolshop/flip/sample_voices.py`: `522 0` (0 removed). `git diff -U0` has a single hunk `@@ -809,0 +810,522 @@`, a pure append after old line 809 (old file = 809 lines; `extract_motif` is at line 227, `extract_riff` at line 386, both above the hunk, so both bodies are byte-identical). |
| 1e | Tree clean for toolshop/scripts/tests | PASS | `git status --short -- toolshop scripts tests` exit 0, 0 lines. (`ORCHESTRATION/ogcm_flip` still shows the foreign megaplan leftovers `wave_m1/`, `waves_megaplan.json`, `prompts/*`, modified `wave_m2/...handoff.md`: not s5 and not touched.) |
| 2-O1'' | pack renders to spec | PASS | `verify_sample_pack.py --dir ...\audition_s5 --glob "s5_*.wav" --min-files 4 --min-s 15 --max-s 45 --lufs -16 --lufs-tol 1.0 --tp-max -1.0` exit 0: 5 x PASS, each 18.3 s 44100 Hz 2ch -16.00 LUFS; tp -7.37 / -7.67 / -7.91 / -5.54 (B_saw) / -7.77 dBTP; `verify_sample_pack: PASS`. |
| 2-O2 | unit tests | PASS | `pytest "...\tests\test_flip_sample.py" -q` exit 0: `73 passed, 1 warning in 16.68s`. |
| 2-O3'' | server serves + index links | PASS | `check_audition_serve.py --base http://127.0.0.1:8777/flip_sample --glob "audition_s5/s5_*.wav" --dir ... --index index.html` exit 0: 5/5 `http=200 linked=yes`. :8777 was already up (HTTP 200 on index.html, LISTEN pid 25172); I did not start a server. |
| 2-O4 | no regressions | PASS | `pytest test_flip_sample + test_flip_arrange + test_flip_master + test_flip_bed_lanes -q` exit 0: `121 passed, 1 warning in 20.30s`. |
| 2-O5 | S4 riff unchanged | PASS | `check_riff.py --manifest ...\audition_s4\manifest.json` exit 0: 6/6 PASS (coverage 0.969, 13 notes, 2.413 n/s, leap 10, snapped 0, F# minor -4 -> pc2); `O5: PASS`. |
| 2-O6 | contour sound | PASS | `check_contour.py --manifest ...\audition_s5\manifest.json` exit 0: 7/7 PASS (coverage 0.7608, octave_jumps 0, in_key 1.0 (16/16), source_audio false + no chop/REF, bpm 105.0, recomputed stats match, npz native + transpose == stored); `O6: PASS`. |
| 2-extra | S4 byte-level regression (spec constraint "S4 stays byte-identical") | PASS | The on-disk S4 WAVs are dated 2026-09-30 21:19 (pre-refactor; d4960c7 is 2026-10-01 00:57). I rebuilt all 5 S4 variants in memory with the current code (`_s4_variants` + `_to_target`) and compared to disk: shape equal for all, max abs diff 1.19e-07 for each (= the PCM_24 quantum). So the `_s4_source` refactor did not change S4 output. |
| 3a | Independent recompute of contour stats (numpy only) | PASS | My own code on `contour.npz` (keys: times, f0_hz, voiced, rms, f0_hz_native, transpose_st, hop_s, window_start_abs_s, window_bars; 1856 frames). voiced frames 1231 (manifest 1231); median MIDI 66.875 (manifest 66.875); p10/p90 64.0002/70.0002 (manifest 64.0/70.0); octave jumps 0; phrases 3; coverage-in-phrases 0.7608 (manifest 0.7608); in-key 16/16 = 1.0. The npz `voiced` array equals `isfinite(f0_hz)`. Native f0 + transpose_st(-4) reproduces stored f0 to 0.000000 st. **Mismatch over 1%: none** (table below). |
| 3b | In-key segment definition | PASS (definitions agree) | Report both. [A] my plain definition: contiguous voiced runs, each run's median MIDI rounded, pitch class tested against {0,2,4,5,7,9,10}: 16 runs, 16 in key, ratio 1.0000 (also 16/16 when dropping runs < 60 ms). [B] the manifest's definition (read from `sample_voices.note_segments`/`contour_stats`: voiced runs split at adjacent-frame steps >= 0.75 st, segments < 0.06 s dropped): I re-implemented it from the docstring: 16 segments, 16 in key. A and B coincide because the largest adjacent-frame step inside any run is 0.270 st, so the 0.75 st split never fires. Octave jumps (|d midi| >= 10 between adjacent voiced frames): 0 over all pairs and 0 within runs. Largest pitch jump between consecutive runs across a gap: 8.00 st (not counted by the definition). |
| 3c | WAV properties | PASS | `soundfile`: all 5 files sr 44100, 2 ch, PCM_24, 806400 frames = 18.285714 s. Expected loop `8*4*60/105 = 18.285714 s`; |dur - expected| = 0.000000 for every file. All finite; peaks 0.4277 / 0.4121 / 0.4019 / 0.5283 / 0.4085 (manifest `sample_peak` identical). |
| 3d | Tempo consistency | PASS | manifest bpm 105.0. `lead_delay_s` 0.428571 vs `0.75*60/bpm` 0.428571 (diff 4.3e-07). `tempo_factor` 0.848571 vs `89.1/bpm` 0.848571 (diff 4.3e-07). `tempo_ratio_vs_source` 1.1785 vs 1.178451. `loop_s` 18.2857. recipe.time_scale and recipe.lead_delay_s agree. bpm in [102.5, 107]. Window span 10.7744 s = 4 bars at 89.1 BPM. |
| 4a | Provenance: static code trace | PASS | See "Provenance" below. Stem audio is opened in exactly one place (`ogcm_sample._s5_wail`, `sf.SoundFile(S5_STEM)`), consumed by `sv.extract_f0_contour`, then `del y`. `_real_chop` is referenced only at lines 150, 188, 257, 399 (S2/S3/S4 builders), never in lines 405-805 (S5). No audio read exists anywhere in `sample_voices.py` (only `librosa.resample/pyin/rms` on an in-memory array). `main` raises `SystemExit` if an s5 variant name contains `chop`/`_REF`; `source_audio_in_output` is computed from the names. |
| 4b | Provenance: runtime open-log | PASS | I called `_s5_variants(S4_REGION, -4, 105.0, "auto")` in memory with a `sys.addaudithook` (py opens) plus a patched `soundfile.SoundFile.__init__` (libsndfile opens) and then built all 5 variants. Files opened, in total: (1) `flip_bed_lanes/midi/region_54_67_raw.mid` (MIDI transcription, not audio), (2) `htdemucs_6s/2Pac - Only God Can Judge Me/guitar.wav`, both during the build phase. **File opens during the rendering of the 5 files: 0 for each.** No open of anything matching `chop`, `ref_slice`, `flip_chops`. |
| 4c | Files on disk come from the audited path | PASS | In-memory rebuild of all 5 S5 variants through `_to_target` vs the on-disk WAVs: shape equal, max abs diff 1.19e-07 for each (PCM_24 quantum). So the audited path is the one that produced the files. |
| 4d | Empirical cross-correlation (supporting only) | PASS (noise floor) | Guitar stem over 59.3872-70.1616 s (475151 samples) vs the first 4 bars of `s5_B_replace.wav` (403200 samples, 9.143 s), mono, FFT cross-correlation, max over all lags. See table below: best `|NCC|` = 0.0121 full-band, 0.0154 local-normalised band-passed 300-4 kHz, versus the < 0.3 criterion, and within the white-noise floor (0.007 to 0.032). Positive control shows the detector would fire on a copy (0.42-0.52). |
| 5 | index.html | PASS | Links all 5 (`s5_A_layer`, `s5_B_replace`, `s5_B_replace_saw`, `s5_C_texture` x1 each, `s5_00_riff_whine` x2). Line 24: "105 BPM (1.18x), D minor, synthesis only (no source audio)" and `source_audio_in_output: false`. Five stem clips (vocals, backing_vox, guitar, bass, other) all sit under the heading "Wail finder - LOCAL ID ONLY, not for Suno" and a `.local` box "LOCAL ID ONLY - not for Suno. These clips are slices of the record's separated stems (source audio)". `LOCAL ID ONLY` occurs 2x; `105 BPM` 4x; `synthesis only` 2x. The 5 clips are served HTTP 200 (and live in `audition_s5_stems/`, not `audition_s5/`). |

### 3a detail: my recompute vs manifest `contour_stats`

| stat | mine | manifest | diff % | flag |
|---|---|---|---|---|
| n_voiced_frames | 1231 | 1231 | 0.000 | ok |
| median_midi | 66.8752 | 66.875 | 0.000 | ok |
| in_key_ratio [A plain runs] | 1.0000 | 1.0 | 0.000 | ok |
| in_key_ratio [B manifest def] | 1.0000 | 1.0 | 0.000 | ok |
| octave_jumps | 0 | 0 | 0.000 | ok |
| voiced_coverage_in_phrases | 0.7608 | 0.7608 | 0.002 | ok |
| n_phrases | 3 | 3 | 0.000 | ok |
| p10 / p90 | 64.0002 / 70.0002 | 64.0 / 70.0 | 0.000 | ok |

Other handoff numbers I re-derived and found correct: the 16 note segments (start-end, note name) in the handoff list match mine exactly; in-key ratio at other transposes (mine: 0 -> 0.188, -1 -> 0.812, -2 -> 0.438, -3 -> 0.562, -4 -> 1.000, -5 -> 0.188, -6 -> 0.812, -7 -> 0.375, -8 -> 0.625) equals the handoff's; riff agreement (native key, onset within one sixteenth 0.1684 s and pitch within 1 st): bars 1-2 = 6/13 = 0.4615 and bars 3-4 = 1/13 = 0.0769, with per-note matched flags identical to the manifest `[1,0,0,0,0,1,1,0,0,1,1,1,0]`. So "the guitar is not a unison double of the riff" is supported.

### 4d detail: cross-correlation (n = samples at 44.1 kHz; `|NCC|max` = max over all lags of |sum x y| / sqrt(Ex Ey))

| stem variant vs B[0:4 bars] | full-band | 300-4000 Hz | local-norm (overlap >= 3 s), 300-4 kHz |
|---|---|---|---|
| V1 raw stem (native time + pitch) | 0.0027 | 0.0032 | 0.0062 |
| V2 numpy interp, time x0.8486 (pitch +2.84 st) | 0.0027 | 0.0037 | 0.0063 |
| V3 numpy interp, pitch -4 st (time x1.260) | 0.0077 | 0.0093 | 0.0123 |
| V4 stem pitch -4 st (pedalboard) then time x0.8486 (librosa time_stretch): the exact "chop -> D minor -> 105 BPM" derivative | 0.0121 (lag -0.003 s) | 0.0147 | 0.0154 |
| floor: V1 vs white noise | 0.0073 | 0.0178 | 0.0322 |
| positive control: V1 mixed into B at -6 dB | 0.4214 | 0.4829 | 0.5135 |
| positive control: V4 mixed into B at -6 dB | 0.4468 | 0.5160 | 0.5160 |

The shifted variants: V2 and V3 are pure numpy resampling (each fixes either tempo or pitch, not both, because resampling couples them); V4 applies both with pedalboard/librosa (venv libraries, not `toolshop`). Caveat: waveform correlation cannot see a transformation it was not built to undo, so this is supporting evidence only. The code trace (4a), the runtime open-log (4b) and the files-come-from-that-path check (4c) are the primary evidence.

## Provenance: call chain per output file

Shared front half (`scripts/ogcm_sample.py main --pack s5` -> `_s5_variants(region_54_67_raw.mid, -4, 105.0, "auto")`):

1. `_s4_source` -> `_region_notes` -> `bed_lanes.load_midi` (a MIDI transcription file, `pretty_midi`): notes only, no audio -> `sv.estimate_key`, `sv.extract_riff`, `sv.transpose`, `sv.derive_chords`, `sv.tile_motif` (riff, chords; all BedNote arithmetic).
2. `_s5_wail` -> `sf.SoundFile(guitar.wav)` seek + read of the 4-bar window (+0.3 s context) -> `sv.extract_f0_contour(y, sr)` (`librosa.resample`, `librosa.pyin`, `librosa.feature.rms`, in memory) -> `del y` -> `sv.clean_contour` -> `sv.crop_contour` -> `sv.transpose_contour(-4)`. What leaves the function: a dict of `times, f0_hz, voiced_prob, rms, voiced, bridged, hop_s, sr`. No waveform.
3. `sv.time_scale_contour(0.848571)` -> `sv.tile_contour` (and x2 time for the texture). `contour.npz` stores only those arrays (1856 frames each).
4. Renders (all in memory, zero file reads): `sv.render_f0_lead(contour)` = phase-accumulating sine + PolyBLEP saw from the f0 array, amplitude from the RMS array; `sv.render_simple_lead(BedNotes)` = sine; `sv.render_gfunk_lead(BedNotes)`; `_texture_fx` = pedalboard Delay/Reverb on the synth; `_render_s5_bus` = `sv.render_rhodes` + `sv.render_sub` (from chords) + `sv.west_coast_chain` (pedalboard) + `sv.fit_loop`; `_to_target` (gain only; `master.integrated_lufs`/`true_peak_dbfs` only measure); `sf.write`. (`master.master_file`, the one master function that reads audio, is never called.)

| Output file | Lane sum | Audio-derived inputs |
|---|---|---|
| `s5_00_riff_whine` | `bus(render_gfunk_lead(tiled_t))` + rhodes + sub | none (the contour is not used at all) |
| `s5_A_layer` | `bus(render_simple_lead(tiled_t) + g_a * render_f0_lead(tiled_w))` + rhodes + sub | f0 + RMS arrays only |
| `s5_B_replace` | `bus(g_b * render_f0_lead(tiled_w))` + rhodes + sub | f0 + RMS arrays only |
| `s5_B_replace_saw` | `bus(g_bs * render_f0_lead(tiled_w, saw timbre, LPF 5 kHz))` + rhodes + sub | f0 + RMS arrays only |
| `s5_C_texture` | `bus(render_simple_lead(tiled_t), texture = g_c * _texture_fx(render_f0_lead(tiled_slow, LPF 2.2 kHz)))` + rhodes + sub | f0 + RMS arrays only |

What is derived from the record, stated plainly so the decision at G2 is informed: no audio sample is in any file, but the pitch line, phrasing, glides, vibrato and dynamics of the real guitar performance (via f0 + RMS), the riff (via the MIDI transcription of the record's 54-67 s section) and the chord roots (derived from the record's bass notes in that cell) are the record's musical content, re-performed on synthesis. The plan already treats this as the escalation case: if Suno rejects even this, the trigger is likely the melody rather than an audio fingerprint, and that is the user's decision.

## Observations (none is a failure)

1. **Wrong-upload risk on the audition page.** `index.html` also carries real-audio reference files that are not marked "not for Suno": `s4_05_chop_REF` ("the real 54-67s slice"), `s3_05_chop_REF`, `s2_06_E_real8_REF`, S1 `sample_E_real_chop_REF`. The S5 pack files are clearly labelled synthesis-only and the stem clips are clearly labelled LOCAL ID ONLY, but the REF rows sit below on the same page the user will be uploading from. A one-line "REF = source audio, not for Suno" label would remove the risk. (The local page is gitignored; this is an optional tidy-up for the orchestrator.)
2. **In-key check does not discriminate -1 and -6.** Confirmed from my own numbers: transposes -1 and -6 give 0.812, above the 0.8 threshold. The -4 choice is the unique perfect fit (1.000) and is also the exact F# minor to D minor shift, so the result stands, but O6 alone would not reject those two neighbours.
3. **Tile seam and first note.** Not checkable here. The 4-bar wail is tiled x2 and the first note starts at frame 0 (first voiced frame 0.002 s); whether the wrap and the cut first note read naturally is for the ear.
4. `manifest.json` has `lu_tol: 0.3` (internal), the spec gate is +/-1.0 LU; O1'' measures +/-1.0 and all five files are at -16.00 LUFS, so no conflict.

## Not verified / out of scope

- How any file sounds (G2). Whether A/B/B_saw/C help the user's wail. Target-environment behaviour (local only).
- The handoff's "49 prior + 24 new tests" split: I confirmed only the totals (73 collected and passing; `def test_` count 46 at `e47be17` vs 66 at HEAD, the rest being parametrization) and did not check out the old test file.
- The handoff's wall times, the stem's 297.06 s length, and its close-out claims (14 commits ahead of origin, dirty foreign lanes): I saw that the foreign `ogcm_flip` files are still dirty, nothing else.
- S4 byte-identity was proven to the 24-bit quantum (max diff 1.19e-07), not by SHA256 of the file bytes.
- Suno acceptance: the user's upload at G2 is the real test of provenance as Suno sees it.

## Files

- Written by me: this file only.
- Read: the plan, the spec, `wave_s5b/agent_b_s5b_handoff.md`, `scripts/ogcm_sample.py`, `scripts/check_contour.py`, `toolshop/flip/sample_voices.py` (S5b block 810-1332, header, `_runs`), `toolshop/flip/bed_lanes.py`/`master.py` (grep for audio reads), `audition_s5/manifest.json`, `audition_s5/contour.npz`, all five `s5_*.wav`, `audition_s4/*`, `index.html`, the guitar stem window.
- Recommended next step (orchestrator): present G2 using the numbers above. The packs are at http://127.0.0.1:8777/flip_sample/.
