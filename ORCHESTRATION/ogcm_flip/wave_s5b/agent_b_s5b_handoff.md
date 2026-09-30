# Wave s5b handoff - GATE S5b: resynthesized guitar wail (pyin contour, no source audio) + A/B/C pack at 105 BPM

Agent: B (implementer) - Date: 2026-10-01 - Plan: `D:\Projects\.workspace_archive\plans\ogcm-s5-wail-resynth.md` (s5b)
Spec: `D:\Projects\.workspace_archive\plans\expected_output_ogcm_suno_sample_s5_20261001_005621.md`
Repo: `D:/Projects/Music-AI-Toolshop` (branch `master`; `git rev-parse --show-toplevel` = `D:/Projects/Music-AI-Toolshop`)

**Status: s5b done, all six gates green. Gate G2 (the user's ear) is pending.** Nothing below claims the wail sounds right. Every quality number here is a measurement of the contour or the files, not a verdict on the sound.

## Commits

| Hash | Subject |
|---|---|
| `d4960c7` | `feat(#075): GATE S5b - resynthesized guitar wail (pyin contour, no source audio) + A/B/C pack at 105 BPM` - 6 files, +1418/-23: `toolshop/flip/sample_voices.py`, `scripts/ogcm_sample.py`, `scripts/check_contour.py` (new), `tests/test_flip_sample.py`, `CHANGELOG.md` (#075), `ORCHESTRATION/ogcm_flip/LEDGER.md` (s5b row) |
| (follow-up) | `docs(#075): ...` - this handoff only; its hash is in `git log` (a file cannot cite its own commit) |

Checks on `d4960c7`: zero `.wav/.flac/.mp3/.npz` staged (`git diff --cached --name-only` filtered: 0); `git diff --stat -- bed_lanes.py arrange.py master.py` is empty; `git diff -U0 -- sample_voices.py` has **zero removed lines** (additive only; `extract_motif`/`extract_riff` untouched). `git check-ignore -v` confirms `audition_s5/s5_A_layer.wav`, `audition_s5/contour.npz`, `index.html` are ignored by `.gitignore:58 Stemmeca_alatkka/stems/`; nothing force-added. Pre-flight: HEAD was `e47be17`; the dirty tree was foreign lanes only (MAirina_Tucc, lyrics scratch, hemija prompts, ogcm megaplan leftovers); none staged, none touched.

## Gates (all foreground, venv python 3.11.9, absolute paths)

| Gate | Command (abridged) | Exit | Key output |
|---|---|---|---|
| O1'' | `scripts/verify_sample_pack.py --dir .../audition_s5 --glob "s5_*.wav" --min-files 4 --min-s 15 --max-s 45 --lufs -16 --lufs-tol 1.0 --tp-max -1.0` | 0 | 5 files PASS, each 18.3 s 44100 Hz 2ch -16.00 LUFS; tp -7.37 / -7.67 / -7.91 / **-5.54 (B_saw)** / -7.77 dBTP; `verify_sample_pack: PASS` |
| O2 | `pytest tests/test_flip_sample.py -q` | 0 | **73 passed** (49 prior + 24 new), 19.53 s |
| O3'' | `scripts/check_audition_serve.py --base http://127.0.0.1:8777/flip_sample --dir .../flip_sample --glob "audition_s5/s5_*.wav" --index index.html` | 0 | 5/5 `http=200 linked=yes`. :8777 was already up (HTTP 200 on `index.html` checked first, pid 25172), so I did not start a server |
| O4 | pytest on `test_flip_sample/arrange/master/bed_lanes` | 0 | **121 passed**, 23.57 s |
| O5 | `scripts/check_riff.py --manifest .../audition_s4/manifest.json` | 0 | 6/6 PASS (coverage 0.969, 13 notes, 2.413 n/s, leap 10, snapped 0, F# minor -4 -> pc2); `O5: PASS` |
| O6 | `scripts/check_contour.py --manifest .../audition_s5/manifest.json` | 0 | 7/7 PASS: coverage 0.7608, octave_jumps 0, in_key 1.0 (16/16), source_audio false + no chop/REF, bpm 105.0, recomputed stats match, npz native + transpose == stored; `O6: PASS` |
| closeout | `python -m toolshop.cli closeout` | **1 (declared)** | see "Close-out" |

**S4 unchanged (evidence):** `ogcm_sample.py --pack s4 --outdir <scratch>` exit 0 (22 s); SHA256 of all 7 outputs identical to the committed-render run in `audition_s4/`: `manifest.json 3752E05FD0E9`, `s4_01 35929CD2A0CA`, `s4_02 52F8BEB8677B`, `s4_03 BB52033FA485`, `s4_04 59C922E624E3`, `s4_05_chop_REF 97BF363F6518`, `verification.json E31C2935F37D` (same hashes s5a recorded). `_render_s3` and the S2-S4 builders were not edited; the only touch on the S4 path is an additive `bass_dm` key in `_s4_source`'s return dict.

**s5a probe preserved:** `--pack s5 --tempo-bpm 89.1 --outdir <scratch>` renders `s5_00_riff_whine.wav` **byte-identical** to the s5a render (SHA256 `0CC2108BFDBB3C9D...`, saved before I overwrote `audition_s5/`). This proves the tempo refactor (`_render_s5_bus`, `bar_s`) changes nothing at the felt tempo.

**Determinism:** two full `--pack s5` renders (105 BPM; second to a scratch outdir) gave **identical SHA256 for all 8 files**: `contour.npz 4EF91B6188EE`, `manifest.json 0C016F6F5068`, `s5_00 92D515E6D3DE`, `s5_A 2CD544E21B68`, `s5_B ADB46486756D`, `s5_B_saw 0DF55B9C9108`, `s5_C 5423EDADEBA6`, `verification.json 3F38DF331843`.

## What the pack is (synthesis only)

All at **105 BPM = 1.1785x the record's 89.1** (time factor 0.848571, bar 2.2857 s, 8-bar loop 18.286 s), D minor, -16 LUFS. Lead echo = dotted 8th at 105 = **0.428571 s**. `manifest.json` records `bpm: 105.0`, `tempo_factor: 0.848571`, `lead_delay_s: 0.428571`, `source_audio_in_output: false`.

| File | Contents | Level (vs the S4 sine lead lane RMS over the loop) |
|---|---|---|
| `s5_00_riff_whine` | S4 riff on `render_gfunk_lead` + derived chords + sub, re-rendered at 105 BPM with the new-tempo delay | - |
| `s5_A_layer` | riff on the S4 sine lead + chords + sub, plus the wail in the same lead lane (shared echo + reverb) | wail -3 dB (gain 0.6644) |
| `s5_B_replace` | wail as the lead over the same chords + sub; riff muted; sine 1.0 + saw 0.35 | wail 0 dB (gain 0.9386) |
| `s5_B_replace_saw` | B with saw 1.0, sine 0.3, `LadderFilter` LPF24 at 5 kHz, resonance 0.2 (**the saw-heavy one**) | 0 dB (gain 1.3723) |
| `s5_C_texture` | riff lead; wail at half speed (contour time axis x2, pitch kept), LPF 2.2 kHz, fully wet echo (fb 0.40) + reverb, dry lane bypasses the chain | -12 dB measured AFTER the FX (gain 0.0738) |

**Provenance:** the guitar stem is opened once, in `ogcm_sample._s5_wail` (`sf.SoundFile` at line ~550), and the array is deleted right after `extract_f0_contour`; only `times/f0_hz/voiced_prob/rms` survive. `_real_chop` is referenced only by the S2/S3/S4 builders (grep). `main` raises `SystemExit` if an s5 variant name contains `chop`/`_REF`; `source_audio_in_output` is computed from the variant names, not hard-coded, and `check_contour` also rejects chop/REF names in the manifest. The independent provenance audit is s5c's job.

## Wail source, window, bars

- Stem: `Stemmeca_alatkka/stems/htdemucs_6s/2Pac - Only God Can Judge Me/guitar.wav` (44.1 kHz stereo, 297.06 s), used for pitch + RMS only.
- **Absolute window: 59.3872 - 70.1616 s record time** = `54.0 + cell_t0 (5.3872)` through +4 bars at 89.1 BPM (10.7744 s). pyin runs on 0.3 s of extra context each side, cropped off afterwards.
- **Bars chosen: 4**, by an explicit rule I wrote (`_phrase_continues`): extend to 4 bars if the contour is voiced at the 2-bar boundary, or voiced again within 0.3 s after it. Recorded in the manifest (`wail_source.window_bars_reason`): "voiced at the 5.387 s boundary: a note sustains across it" (the G#4 at 5.012-5.813 s). Tiled x2 over the 8 bars; the half-speed texture is 8 bars x1. **`--wail-bars 2` renders the 2-bar alternative** (2-bar window, tiled x4) if the 4-bar choice is wrong by ear. Verified: `--pack s5 --wail-bars 2 --outdir <scratch>` exit 0 (38 s, `pass: true`), window 59.3872-64.7744 s, stats coverage 0.8026, octave_jumps 0, in_key 9/9, vibrato 129.0 cents; `check_contour` on that scratch pack exit 0. It is not written to `audition_s5/`.
- Time alignment sanity: sweeping the riff onsets by k*(sixteenth/4), k=-12..12, recall peaks at offset **0** (0.4615), so the `54.0 + cell_t0` mapping is supported.

## contour_stats (recomputed by `check_contour` from `contour.npz`; identical to the manifest)

```
{"hop_s": 0.005805, "n_frames": 1856, "n_voiced_frames": 1231,
 "voiced_coverage_in_phrases": 0.7608, "n_phrases": 3, "octave_jumps": 0,
 "in_key_ratio": 1.0, "n_segments": 16, "n_segments_in_key": 16,
 "vibrato_pp_cents": 124.4, "n_sustained": 6,
 "median_midi": 66.875, "p10_midi": 64.0, "p90_midi": 70.0}
```
(median/p10/p90 are in D minor after the -4 transpose; native median is ~70.9 = B4, matching s5a's 71.0). Note segments in D minor (record-time s from window start): E4 0.00-0.50, A#4 1.36-2.00, A4 2.11-2.20, G4 2.33-2.52, A4 2.61-3.17, A4 3.64-3.89, F4 4.11-4.61, E4 4.75-4.87, E4 5.01-5.81, A4 6.12-6.52, G4 6.70-7.86, A4 8.04-8.52, D4 8.88-9.17, E4 9.28-9.89, F4 10.03-10.41, G4 10.63-10.72.

**Is the in-key check discriminating?** Same contour at other transposes (in_key_ratio): 0 -> 0.188, -1 -> 0.812, -2 -> 0.438, -3 -> 0.562, **-4 -> 1.000**, -5 -> 0.188, -6 -> 0.812, -7 -> 0.375. So -4 is the unique perfect fit, but caveat: diatonic sets overlap, so -1 and -6 also clear the 0.8 threshold. O6 confirms the -4 choice; it would not by itself reject those two neighbours. Threshold not loosened.

## Riff agreement diagnostic (native key, within 1 sixteenth = 0.1684 s and 1 semitone)

- **Bars 1-2 (the riff's own cell): 6 of 13 riff notes matched = 0.4615; precision 6/9 = 0.667** (contour segments in the cell that match a riff note).
- **Bars 3-4 (same riff, repeated): 1 of 13 = 0.0769.**
- Matched: riff 0 G#4, 5 C#5, 6 C#5, 9 C#5, 10 A4, 11 G#4 (dt -0.167/+0.089/+0.089/+0.106/-0.097/+0.037 s, dpitch 0 to +0.19 st). Unmatched: 1 A4 (0.673 s), 2 F#4 (0.842), 3 F#4 (1.010), 4 E5 (1.347; guitar holds D5 = 74.1, 1.9 st under), 7 C#5 (3.030), 8 B4 (3.199), 12 F#4 (4.882). The guitar is silent from 0.50 to 1.36 s while the riff has three notes there.
- **Reading: the guitar is NOT a unison doubling of the riff.** It partly doubles it in bars 1-2 and plays something different in bars 3-4 while the riff repeats. So in variant A the wail partly doubles and partly runs against the riff. This is a measurement; how A sounds is the user's call.

## Vibrato: measurement and choice

Measured contour vibrato = **124.4 cents peak-to-peak** (median over 6 note segments >= 0.5 s; p95-p5 of the MIDI curve after subtracting a 0.36 s moving average, first/last 0.06 s trimmed). Rule from the s5r report: add synthetic vibrato only if under ~40 cents. 124.4 >= 40, so **`add_vibrato=False`**: the wail's vibrato is the performance's own (recorded in `recipe.vibrato`). Consequence of the speed-up: the performance's vibrato rate scales by 1/0.8486 = 1.18x in A/B/B_saw, and by 0.59x in C (half speed).

## Functions added (`sample_voices.py`, additive)

`extract_f0_contour` (pyin fmin 196 / fmax 2093 / frame 1024 / hop 128 at 22.05 kHz, default HMM, `fill_na=nan`; voiced = flag AND prob >= 0.5 AND RMS gate > -60 dBFS and within 35 dB of p95), `clean_contour` (octave fix per segment vs the +-1 s local median and the global median, median 5 frames inside segments only, drop islands < 9 frames, bridge gaps <= 17 frames across <= 3 st; frame counts rescale for other hops), `transpose_contour`, `time_scale_contour`, `crop_contour`, `tile_contour`, `contour_from_arrays`, `note_segments`, `contour_stats`, `render_f0_lead` (phase-accumulating oscillator, constant 20 ms pitch smoothing, no portamento, legato across bridged gaps / retrigger on longer gaps, 10 ms attack / 70 ms release, tanh + peak guard <= 0.99, L == R). Hop 128 was used throughout, so the frame counts are as specified, unscaled.

**Render audit (objective only):** pyin run on the rendered wail (default and saw timbres) versus the contour it was rendered from: 2096/2096 voiced frames compared, median deviation 0.000 st, 100% within 0.5 st; output finite, peak 0.821 (default) / 0.933 (saw, at the 22.05 kHz audit rate), L == R, silent (rms 0) where the contour is unvoiced. This shows the oscillator follows the contour, not that it sounds good.

## Wall times

pyin on the 4-bar window (11.4 s of audio at hop 128): 16.7 s (explore), 18.7 s, 17.2 s. Full `--pack s5` render incl. pyin: 43 s (89.1), 38 s (105), 33 s (determinism run). S4 re-render 22 s. O2 19.5 s, O4 23.6 s.

## Deviations and choices that were mine (please read)

1. **Bash tool unusable here** (`git`, `ls`, `wc` not on PATH: exit 127 x3, classified as PATH, switched to the PowerShell tool). One PowerShell call failed with pytest exit 4 because `$T` (tests dir) collided with `$t` (Get-Date), PowerShell variables being case-insensitive; re-run with distinct names, not an identical retry.
2. I ran one **repo-wide recursive markdown search** for "Answer #075" that hung past the 120 s timeout; it broke the search-scope rule, I stopped it, and confirmed #075 unused with a CHANGELOG-only grep (0 hits).
3. **Metric definitions the brief left open (mine):** phrase = voiced runs with gaps <= 0.4 s; note segment = voiced run split at adjacent-frame steps >= 0.75 st, segments < 0.06 s ignored; vibrato measured on segments >= 0.5 s. They are in `contour_stats`' signature and docstring; `check_contour` recomputes with the same defaults.
4. **Amplitude curve:** smoothed RMS normalised by the voiced p95, then raised to `dyn_exp = 0.5` (gentle compression), not used literally, because the guitar's pluck decays would otherwise make the synth plucky. Recorded in `recipe.render`. A literal mapping is `dyn_exp=1.0`.
5. **PolyBLEP saw** in `render_f0_lead` (not the naive `_saw` the older voices use) because a naive saw at 0.3-1.7 kHz aliases into the audible band.
6. **Levels** are RMS-matched to the S4 sine lead over the loop (A -3 dB, B 0 dB, C -12 dB post-FX); my choice, recorded. The C texture LPF (2.2 kHz), echo feedback (0.40) and reverb (room 0.8) are also mine.
7. **Window = 4 bars** by my own continuation rule (see above); a 2-bar alternative is one flag away.
8. `s5_00_riff_whine` in `audition_s5/` was overwritten by the 105 BPM re-render (as requested); the s5a 89.1 render is still reproducible (`--tempo-bpm 89.1`). I updated the s5a block's caption in `index.html` accordingly.
9. `_s4_source` gained a `bass_dm` key so chords are re-derived at the new tempo via `derive_chords(..., bar_s=)`; result `chords_match_s4: true` (Dm7 Bbmaj7 alternating, same as S4). A new `_render_s5_bus` mirrors `_render_s3` (same lane order, gains and chain) with a pre-rendered lead lane; `_render_s3` itself is untouched.
10. **Contour sensitivity:** in my exploratory run (window read with `int()` sample rounding) the stats were coverage 0.7676 / 1242 voiced frames; the committed pipeline (rounding with `round()`) gives 0.7608 / 1231. pyin's output moves slightly with a 1-sample shift of the window. The committed pipeline is deterministic (2 identical runs); the point is only that the contour is a measurement with some jitter, not exact.
11. `index.html` is gitignored and local; I edited it with the Edit tool (new S5b block on top, between `S5B-SECTION-BEGIN/END` markers; s5a block and everything below unchanged apart from the probe caption and page title).
12. **Not done:** README / PROJECTS_INDEX update (not in the approved commit list; still open from s5a), `session_end.py`, any push. No Suno upload (the user's action at G2).
13. **Not verified:** how any of the five files sounds; target-environment behaviour (local only); that the tile seam and the cropped first note read naturally by ear (note at the window start sounds from frame 0 with the 10 ms attack).

## Files

- Committed: `toolshop/flip/sample_voices.py`, `scripts/ogcm_sample.py`, `scripts/check_contour.py`, `tests/test_flip_sample.py`, `CHANGELOG.md`, `ORCHESTRATION/ogcm_flip/LEDGER.md`. Outside the repo: `D:/Projects/.workspace_archive/plans/expected_output_ogcm_suno_sample_s5_20261001_005621.md`.
- Local, gitignored (`D:/Projects/Music-AI-Toolshop/Stemmeca_alatkka/stems/flip_sample/`): `audition_s5/` = `s5_00_riff_whine.wav`, `s5_A_layer.wav`, `s5_B_replace.wav`, `s5_B_replace_saw.wav`, `s5_C_texture.wav`, `manifest.json`, `verification.json`, `contour.npz` (times, f0_hz [D minor], voiced, rms, f0_hz_native, transpose_st, hop_s, window_start_abs_s, window_bars); `index.html`. `audition_s5_stems/` (s5a, LOCAL ID ONLY) untouched. Listen at http://127.0.0.1:8777/flip_sample/.
- Scratch (session scratchpad, not in the repo): baseline copy of the s5a render, the 89.1 regression render, the determinism render, the S4 re-render and the exploration scripts.

## Close-out (AGENTS.md)

- All six paths I changed are committed in `d4960c7`; `git status` shows none of them dirty. The `git status --short` filtered for my paths returns nothing.
- `python -m toolshop.cli closeout` **exit 1, declared**: (a) working tree not clean, all foreign lanes (listed below); (b) 14 commits ahead of `origin/master` (mine `d4960c7` plus 13 earlier, from `f25c664`); I did not push, pushing is the user's cadence. Submodules: ` 9bddc72... mastering_tool (heads/claude/wonderful-johnson-h6xj4d)`, ` 7acba12... suno_prompter (heads/main)`, no `+/-/U` prefix (the plain `git status` shows them as ` M`, working-tree markers, not mine).
- Still-dirty paths, none staged or touched by me: `MAirina_Tucc/` (13 modified files plus untracked `devices.py`, `phonetics.py`, `rules.py`, `targets.py`, `lexicons/`, `ORCHESTRATION/mairina_v2/`, 5 new tests); `ORCHESTRATION/prompts/` (modified `prompts_index.md`; untracked hemija lyricist/reviewer prompts, index, `subagent_dispatch.json`); `ORCHESTRATION/ogcm_flip/` megaplan leftovers (modified `wave_m2/agent_b_bed_spike_handoff.md`; untracked `wave_m1/`, `waves_megaplan.json`, `prompts/prompts_index.md`, `prompts/subagent_dispatch.json`); `handoffs/orchestration_ledger_mairina_v2_20260930.md`; `lyrics_research/documents/` and `external_downloads/`; ~30 `scratch_*` probe files, `.scratch_i6/`, `.scratch_v1_audit.py`, `wt_bog_probe.txt`, stray `nul`. After this handoff commit the only tree delta I introduce is this file, committed separately.
