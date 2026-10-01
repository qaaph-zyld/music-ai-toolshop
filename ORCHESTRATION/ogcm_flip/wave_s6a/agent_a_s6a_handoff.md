# Wave s6a handoff - GATE S6a: organ x synthwave "night drive" pack (3 organ stab voices, driving octave bass, drumless pump) at 105 BPM

Agent: A (implementer) - Date: 2026-10-01 - Plan: `D:\Projects\.workspace_archive\plans\ogcm-s6-organ-synthwave.md` (s6a)
Spec: `D:\Projects\.workspace_archive\plans\expected_output_ogcm_suno_sample_s6_20261001_015743.md`
Research input: `ORCHESTRATION/ogcm_flip/wave_s6r/research_s6_report.md`
Repo: `D:/Projects/Music-AI-Toolshop` (branch `master`; `git rev-parse --show-toplevel` = `D:/Projects/Music-AI-Toolshop`)

**Status: s6a done, all seven gates green. Gate G3 (the user's ear, then the user's own Suno upload) is pending.** Nothing below claims any organ, the bass or the pump sounds right. Every quality number here is a measurement of the files or the code, not a verdict on the sound.

## Commits

| Hash | Subject |
|---|---|
| `4542fdd` | `feat(#076): GATE S6a - organ x synthwave night drive pack (3 organ stab voices, driving octave bass, drumless pump) at 105 BPM` - 6 files, +1282/-36: `toolshop/flip/sample_voices.py` (+478, additive), `scripts/ogcm_sample.py`, `scripts/check_pack_meta.py` (new), `tests/test_flip_sample.py`, `CHANGELOG.md` (#076), `ORCHESTRATION/ogcm_flip/LEDGER.md` (s6a row) |
| (follow-up) | `docs(#076): ...` - this handoff only; its hash is in `git log` (a file cannot cite its own commit) |

Checks on `4542fdd`: zero `.wav/.flac/.mp3/.npz` staged (0); `git diff --stat -- toolshop/flip/bed_lanes.py toolshop/flip/arrange.py toolshop/flip/master.py` is empty; `git diff -U0 -- toolshop/flip/sample_voices.py` has **zero removed lines** (0 lines matching `^-[^-]`); `git check-ignore -v` confirms `audition_s6/s6_00_drive_control.wav`, `audition_s6/manifest.json` and `index.html` are ignored by `.gitignore:58 Stemmeca_alatkka/stems/`, and `git ls-files -- Stemmeca_alatkka/stems/flip_sample` lists 0 files; nothing was force-added. Pre-flight: HEAD was `1ff7815`, the dirty tree was foreign lanes only (MAirina_Tucc, hemija prompts, ogcm megaplan leftovers, lyrics scratch); none staged, none touched. **A foreign commit `b1c066b feat(mairina): v2 wave 1 ...` landed on `master` between my pre-flight and my commit** (a concurrent session); it is not mine and my commit contains only the six paths above (its parent is `b1c066b`).

## Gates (all foreground, venv python 3.11.9, absolute paths, `:8777` already up)

| Gate | Command (abridged) | Exit | Key output |
|---|---|---|---|
| O1''' | `scripts/verify_sample_pack.py --dir .../audition_s6 --glob "s6_*.wav" --min-files 4 --min-s 15 --max-s 45 --lufs -16 --lufs-tol 1.0 --tp-max -1.0` | 0 | 4 files PASS, each 18.3 s 44100 Hz 2ch -16.00 LUFS; tp -5.32 / -5.90 / -5.87 / -5.75 dBTP; `verify_sample_pack: PASS` (4.3 s) |
| O2 | `pytest tests/test_flip_sample.py -q` | 0 | **103 passed** (73 prior + 30 new), 19.06 s |
| O3''' | `scripts/check_audition_serve.py --base http://127.0.0.1:8777/flip_sample --glob "audition_s6/s6_*.wav" --dir .../flip_sample --index index.html` | 0 | 4/4 `http=200 linked=yes`. `:8777` was already up: `curl` gave HTTP 200 on `index.html` and on `s6_00_drive_control.wav` before the run (two `http.server` processes, pids 18256 and 25172); I did not start a server |
| O4 | pytest on `test_flip_sample/arrange/master/bed_lanes` | 0 | **151 passed**, 19.38 s |
| O5 | `scripts/check_riff.py --manifest .../audition_s4/manifest.json` | 0 | 6/6 PASS (coverage 0.969, 13 notes, 2.413 n/s, leap 10, snapped 0, F# minor -4 -> pc2); `O5: PASS` |
| O6 | `scripts/check_contour.py --manifest .../audition_s5/manifest.json` | 0 | 7/7 PASS (coverage 0.7608, octave_jumps 0, in_key 1.0 = 16/16, source_audio false, bpm 105.0, stats match, npz consistent); `O6: PASS` |
| O7 | `scripts/check_pack_meta.py --manifest .../audition_s6/manifest.json --bpm-min 102.5 --bpm-max 107 --require-organ-kinds string,combo,drawbar` | 0 | 5/5 PASS: `source_audio_in_output` False, `drums` False, bpm 105.0, organ_kinds {string, combo, drawbar}, 4 files exist and non-empty; `O7: PASS` |
| closeout | `python -m toolshop.cli closeout` (run from the repo dir; a first run from `D:\Projects` read the parent repo's status and is not evidence) | **1 (declared)** | see "Close-out" |

## S2 - S5 unchanged (evidence)

Evidence kind: **SHA256 of every file in the on-disk `audition_sN/` versus a fresh re-render of the FINAL committed code into a scratch outdir** (`ogcm_sample.py --pack sN --outdir <scratch>`). All exact matches; the "24-bit quantum" fallback was not needed.

- **S5: 8/8 identical, exit 0, ~26 s** (also done once mid-wave right after the `_s5_core` refactor, 8/8 identical, 30.9 s): `contour.npz 4EF91B6188EE`, `manifest.json 0C016F6F5068`, `s5_00 92D515E6D3DE`, `s5_A 2CD544E21B68`, `s5_B_replace ADB46486756D`, `s5_B_replace_saw 0DF55B9C9108`, `s5_C_texture 5423EDADEBA6`, `verification.json 3F38DF331843`. `manifest.json` matching also proves the `_wail_source_meta` dict is the same as the old inline dict.
- **S4: 7/7 identical, exit 0, 20 s**: `manifest.json 3752E05FD0E9`, `s4_01 35929CD2A0CA`, `s4_02 52F8BEB8677B`, `s4_03 BB52033FA485`, `s4_04 59C922E624E3`, `s4_05_chop_REF 97BF363F6518`, `verification.json E31C2935F37D` (same hashes s5a and s5b recorded).
- **S3: 7/7 identical, exit 0, 19 s, but only with the arguments the on-disk pack was rendered with** (`--region region_54_67_cleaned_Dm.mid --chop ref_slice_54_67.wav --shift 0`, read from the on-disk `manifest.json`). A first re-render with the script defaults (`region_63_66_cleaned_Dm.mid`, `cand_317_...wav`, shift -4) differed in every WAV: that was my argument mistake (different region/chop), not a code change. `_render_s3` and `_s3_variants` are untouched.
- **S2: all 6 WAVs and `manifest.json` identical; `verification.json` differs** (`733F6C83A8F2` on disk vs `7B1C1A5BDE1E` new): the new file has the `"pass"` key next to `"passed"`; that line of `main()` is not in my diff and the on-disk S2 verification predates it. Not a regression of any audio.
- The refactor of `_s5_variants` (see below) is the only edit to an S2-S5 code path in `ogcm_sample.py`.

## What the pack is (synthesis only, drumless)

`audition_s6/`: 105 BPM (tempo factor 0.848571 vs the record's 89.1), 16th = 0.142857 s, 8th = 0.285714 s, beat = 0.571429 s, bar = 2.285714 s, **8-bar loop 18.2857 s**, D minor, -16 LUFS, lead echo = dotted 8th 0.428571 s. `manifest.json`: `bpm 105.0`, `drums false`, `source_audio_in_output false` (computed from the variant names, and `main` raises `SystemExit` if a name contains `chop`/`_REF`), `organ_kinds ["string","combo","drawbar"]`, the organ recipe per kind, stab grids/velocities/gates, bass and pump settings, `wail_source` (as S5), `suno_style_prompt` (primary + 2 alternates, verbatim from s6r).

| File | Lead | Chords | Bass | Pump |
|---|---|---|---|---|
| `s6_00_drive_control` | S4 riff + saw wail | EP whole notes, S5 gain 0.30 | driving bass | EP -9 dB, bass -6 dB |
| `s6_01_organ_string` | same | string-machine stabs | same | organ -2 dB, bass -6 dB |
| `s6_02_organ_combo` | same | combo-organ stabs | same | same |
| `s6_03_organ_drawbar` | same | drawbar + rotary stabs | same | same |

- **Lead** (all files): the S5-A construction in the SAW timbre: riff on `render_simple_lead` at 1.0 plus `render_f0_lead(tiled_w, **S5_TIMBRE_SAW)` at `S5_A_WAIL_DB` (-3 dB re the riff lane RMS; gain 0.9715), one `west_coast_chain` lead chain with the dotted-8th echo. Not pumped. Wail window = record 59.3872-70.1616 s (4 bars), `add_vibrato` False (contour vibrato 124.4 cents), contour stats identical to S5.
- **Chords**: `derive_chords` voicings unchanged: Dm7 = [57, 60, 64, 65] (A3 C4 E4 F4), Bbmaj7 = [57, 60, 62, 65] (A3 C4 D4 F4), alternating, `chords_match_s4: true`. These are not the F3 A3 C4 D4 grip quoted in the s6r report; the brief said keep the existing voicings, so I did.
- **Stabs**: 176 notes (44 hits x 4 tones). Grid 0 (`x..x..x...x..x..`, velocities `9..6..8...5..7..`) on bars 1, 3, 5, 7; grid 1 (`x..x..x.x..x..x.`, `8..5..7.9..5..6.`) on bars 2, 4, 6, 8 (1-indexed). Gate 200 / 110 / 80 ms for digits 8-9 / 6-7 / 1-5; velocity = digit/9.
- **Bass**: 8 BedNotes per bar, low octave on even 8ths (velocity 8/9) and the octave above on odd 8ths (6/9), gate 75 % of an 8th; low notes 38,34,38,34,... = D2/D3 on Dm7 bars, Bb1/Bb2 on Bbmaj7 bars. Replaces the sustained sub entirely.
- **Pump**: quarter-note duck, attack 5 ms, exponential release (time constant = release/3, 342.857 ms = 0.6 beat), grid starts at sample 0 so the 32 beats of the loop align; lanes are ducked before the FX.
- **FX**: organ + bass send -> 25 ms pre-delay (sample shift) -> wet-only Freeverb room 0.8 (damping 0.5) -> 200 Hz high-pass on the return -> scaled so the return RMS over the loop is -16 dB under its send. My own impulse-response measurement of that Freeverb setting: RT60 2.29 s (T20) / 2.40 s (T30), so "hall ~2.2 s" holds as an estimate, not a spec. In the control the send is the bass only. The bus is `west_coast_chain` unchanged (organ/bass/return lanes are dry in its table, so the hall return is their only FX; the EP in the control keeps its chorus + reverb chain), then the existing glue compressor, then `fit_loop`.

## Per-lane RMS balance (measured by the renderer, over the 8-bar loop, before any FX; reference = the lead lane)

| File | lead | chords lane | bass | hall return |
|---|---|---|---|---|
| `s6_00_drive_control` | 0.0 dB (-7.54 dBFS) | **-15.73 dB** (EP) | -6.0 dB | -22.0 dB |
| `s6_01_organ_string` | 0.0 | -6.0 | -6.0 | -19.0 |
| `s6_02_organ_combo` | 0.0 | -6.0 | -6.0 | -19.03 |
| `s6_03_organ_drawbar` | 0.0 | -6.0 | -6.0 | -18.99 |

Gains used: bass 0.4139, organ_string 1.8321, organ_combo 2.2997, organ_drawbar 2.1744; return scales control 0.0769, string 0.0642, combo 0.0591, drawbar 0.0726. Final files (after the chain and the -16 LUFS normalisation): sample peaks 0.542 / 0.5065 / 0.508 / 0.5156; L/R correlation 0.9609 / 0.9233 / 0.9637 / 0.9270 and side-to-mid RMS -17.0 / -14.0 / -17.3 / -14.2 dB (the string ensemble and the drawbar rotary are the wider ones; the combo file is as narrow as the control). Loop-wrap jump (max abs diff of last vs first sample) 0.076 / 0.073 / 0.063 / 0.064 (S5 for comparison: 0.049-0.182).

**Level caveat (mine, please read):** the organ stabs and the bass are calibrated to -6 dB under the lead lane; the control's EP keeps the S5 gain as the brief said ("EP whole notes as in S5") and lands at -15.7 dB. So the control has about 10 dB less chord level than the three organ files, and the A/B "what the organ adds" is also a level step. If a level-matched control is wanted it is one constant (`S3_GAINS["rhodes"]` times a gain in `_s6_variants`).

## Determinism and provenance

- **Two full `--pack s6` renders (default outdir, then a scratch outdir) gave identical SHA256 for all 6 files**: `manifest.json 4603F4915A8C`, `s6_00 5F068E3B2697`, `s6_01 7FF0916219F4`, `s6_02 2424686F2ED1`, `s6_03 0751B7895675`, `verification.json C2B31562183F`.
- **No RNG in the S6 code**: grep for `default_rng|np.random|RandomState|random\.` on `sample_voices.py` hits only the pre-existing `humanize` (line 115); on `ogcm_sample.py` it hits nothing. Every phase is a fixed constant.
- **Runtime file-open audit (my own quick wrapper that patches `builtins.open`, `io.open` and `soundfile.SoundFile.__init__`, full `--pack s6` render, exit 0, 24 s):** media/MIDI/npz opens were exactly `flip_bed_lanes/midi/region_54_67_raw.mid` (rb, x1), `htdemucs_6s/2Pac - Only God Can Judge Me/guitar.wav` (SoundFile r, x1, the S5 contour path) and then the four output WAVs (written, then re-read for the LUFS/peak verification). No other audio was opened, and `_real_chop` appears only in the S2/S3/S4 builders (grep). This is a smoke check, not the independent audit: that is s6b.
- **No percussion or noise**: the S6 voices contain no noise source (grep `noise` hits only the comments saying so); the drawbar key click is a pitched 6th-harmonic sine burst (6 ms, -18 dB); the "percussion" of the drawbar recipe is the organ's 3rd-harmonic partial, not a percussion lane; `drums` is computed from the lane names (`lead, rhodes, organ, bass, fx_return`), none of which matches a drum tag.

## Changes

- **`toolshop/flip/sample_voices.py`** (additive; appended after `render_f0_lead`): `ORGAN_KINDS`, `ORGAN_RECIPES`, `BASS_RECIPE`, `STAB_GRIDS/STAB_VELOCITIES/STAB_GATES_MS`, `BASS_*`, `organ_recipe`, `render_organ`, `rotary_leslie`, `stab_pattern`, `bass_low_midi`, `driving_bass`, `render_synth_bass`, `pump`, and private helpers (`_ar_env`, `_pulse`, `_ensemble`, `_organ_note`, `_svf_lowpass`, `_bass_note`, `_stab_gate_ms`, `_digit`). `render_organ` takes per-note velocity (drawbar picks R3 at velocity >= 0.85).
- **`scripts/ogcm_sample.py`**: `--pack s6` (`--tempo-bpm`, default 105, and `--wail-bars` now apply to s5 and s6; s2-s4 still reject `--tempo-bpm`); the head of `_s5_variants` (everything before `riff_lead = ...`) **moved unchanged** into `_s5_core`, with `_gain_for` and `_wail_source_meta` factored out; `_s5_variants` unpacks `_s5_core`, its `gain_for` closure delegates to `_gain_for` (same expression), and its manifest uses `_wail_source_meta` (same dict). New `_s6_variants`, `_render_s6_bus`, `_s6_return`, `_fit_len`, `_db`, S6 constants. The 36 removed lines in the commit (35 in `ogcm_sample.py` per `--numstat`: that move, the docstring and the CLI text; 1 in the tests file: the old last line, which had no trailing newline) are all expected. Proof that S5 did not change: the 8/8 SHA256 match above.
- **`scripts/check_pack_meta.py`** (O7): as specified; also fails on `organ_kinds` with duplicates, missing manifest, or an empty `files` list; `bpm` must be a number (not a bool).
- **`tests/test_flip_sample.py`**: +30 tests (73 -> 103). The seven requested kinds are covered (each organ kind non-silent / finite / <= 1.0 / deterministic; drawbar L != R; stab onsets on the 16th grid and every note ends before its bar; `driving_bass` 8 notes per bar on the root with alternating octaves; pump identity at depth 0 and about -6 dB (+/-1) at the beat onset; synth bass finite / <= 1.0 / deterministic) plus the accent-registration switch (4' partial ratio 0.0003 for velocity 0.5 vs 0.3664 for 0.9; 0.0011 with the accent disabled, so the test discriminates), combo vibrato off by default, velocity use, recipe merge, Leslie crossover complementarity, stab velocity-to-gate mapping, malformed grids, filter-envelope brightness (spectral centroid 597 Hz in the first 60 ms vs 265 Hz late), `check_pack_meta` pass/fail cases, `--pack s6` flag handling, `_s6_return` = -16 dB under its send, `_gain_for`/`_fit_len`/`_db`.
- **`index.html`** (gitignored, local; CRLF kept): S6 section at the top between `S6-SECTION-BEGIN/END` markers: title "S6 - organ x synthwave night drive (105 BPM, D minor, drumless, synthesis only)" (em dash in the page), four players with role captions (00 = control without an organ), the lane RMS note, the primary Suno style prompt in a readonly `<textarea>` copy box with a Copy button, and the two alternates below it (lengths 167 / 170 / 169 characters, checked). A red "REAL RECORD - never upload to Suno" badge on **nine** entries: s4_05_chop_REF, s3_05_chop_REF, s2_06_E_real8, S1 sample_E, and the five local wail-finder stem clips (#1 vocals ... #5 other). The page `<title>` now names S6. Every other section is unchanged.
- **Records**: `CHANGELOG.md` #076 (grep of CHANGELOG.md only: `#076` and `Answer #07[6-9]` had 0 hits before; latest was #075), `LEDGER.md` s6a row, the spec outside the repo.

## Wall times

Full `--pack s6` render incl. pyin: 27.0 s (28.8 s for the first scratch render; pyin 13.7 s of that). Re-renders for the identity proof: S5 26 s and 30.9 s, S4 20 s, S3 19 s, S2 31 s. Voice smoke: each organ stab render 0.3-1.5 s, synth bass 0.18 s (identical pitch/gate notes are rendered once and reused, exact). O1 4.3 s, O2 19.1 s (20.7 s wall), O4 19.4 s (21.0 s wall). One stats script took about 2 minutes wall once (machine contention from other sessions; it finished normally).

## Deviations and choices that were mine (please read)

1. **Ensemble "mixed 79/21".** I read it as weights on the two LFO depths: delay = 6 ms + 0.79 x 2.5 ms x sin(0.6 Hz, phase 0/120/240) + 0.21 x 0.3 ms x sin(6.0 Hz), i.e. a slow peak of +/-1.975 ms and a fast peak of +/-0.063 ms (inaudible, as s6r says for stabs). Line pans 0 / 0.5 / 1 (L / centre / R); dry 0.35, wet 0.65. All mine (s6r marks these L/INF).
2. **Bass "saw -12 cents, square -12 cents".** Implemented literally: both oscillators are 12 cents flat, so there is no saw/square beating and the pair sits 12 cents under the exact-pitch sine (an octave down) and under the chords. The s6r table's "-12 / -12 / -24" may have meant semitones. If a detuned spread was intended it is two parameters (`saw_cents`, `square_cents`). I did not change it.
3. **String-machine footages: the full recipe 16'/8'/4' at 0.3/1.0/0.6**, not the 8'+4' stab option. The 16' puts content at A2-F3, in the bass octave range (D2/D3 = 73/147 Hz, Bb1/Bb2 = 58/117 Hz). The drawbar R1 (888000000) also carries a 16' and a 5 1/3'. One parameter (`footages=(0, 1, 0.6)`) switches the string to 8'+4'.
4. **Filter and envelope details not in the recipe**: bass low-pass = two cascaded TPT state-variable stages, Q 1.2 on the first and 0.7071 on the second (24 dB/oct); organ amp envelopes are linear attack / flat hold / linear release; the combo's s6r "decay to 70 % in 50 ms" (INF) is not used because the brief lists only A2/R60; the drawbar percussion partial decays with a 0.2 s time constant (s6r says "fast ~1 s", L confidence); Leslie start phases fixed at horn 0 degrees, drum 60 degrees, the drum rotor uses the same +/-0.44 ms Doppler as the horn; the crossover is a zero-phase complementary FFT split (the two bands sum back to the input exactly, tested).
5. **Pump curve**: release "343 ms exponential" is implemented as a time constant of release/3 (95 % recovered at 343 ms, 99.7 % at the end of the beat). Beat 1 of the loop is at sample 0.
6. **Level targets -6 / -6 dB** for the organ stabs and the bass are my reading of "stabs about -6 dB under the lead, bass present but not dominant". See the level caveat above for the control EP.
7. **Return wet = -16 dB measured as RMS** over the loop against the send (not a pedalboard `wet_level` number); HP 200 Hz is applied after the reverb; pre-delay is a 25 ms sample shift (the brief allowed either).
8. **Bass low-octave window**: `bass_low_midi` folds the root into MIDI 34-45 (Bb1-A2) so D -> D2 and Bb -> Bb1 as specified; the pack only has Dm7 and Bbmaj7 roots, other roots are unexercised by the pack (tests cover D, Bb, F, C).
9. **Which grid on which bar**: `chord["bar"] % 2` (0-indexed), so grid 0 is on 1-indexed bars 1, 3, 5, 7.
10. **Badges on five more entries than the four named REF files** (the local wail-finder stem clips are real-record slices); and I changed the page `<title>`. The existing "LOCAL ID ONLY - not for Suno" note is unchanged.
11. **Refactor of S5 code** (allowed by the brief, proven by SHA256): `_s5_core`, `_gain_for`, `_wail_source_meta`. I preferred factoring over copying 50 lines so S5 and S6 cannot drift apart.
12. **A tool slip, no effect on outputs**: my first final render was piped through `Select-Object -First 30`, which closed the pipe and killed python mid-render (exit -1/255, after `s6_01`); I classified it (my pipeline, not the code), re-ran with the full output captured (exit 0), and that run overwrote the two partial files. The two later full runs are the identical pair above. A browser navigation to `http://127.0.0.1:8777/flip_sample/index.html` for a visual check was denied, so **the page was never rendered by me**: its checks are the patch script's assertions (all anchors found, 9 badges) and O3''' (HTTP 200 plus links).
13. **The Suno prompts mention drums** (hard trap drums, 808 drums, hi-hats, kick): they are the s6r text verbatim and describe what Suno should add; the files contain none, which O7 asserts through `drums: false` (computed from lane names, so it is a structural flag, not an audio analysis; the s6b percussion audit does that).
14. **Not done**: README / PROJECTS_INDEX update (not in the approved commit list; still open from s5a/s5b), `session_end.py`, any push, any Suno upload. **Not verified**: how any file sounds (the user's ear), that the stab rhythm reads as "street-rap energy", that the 16' content does not mud the bass, target-environment behaviour (local only), a browser render of the page, the independent provenance / percussion / byte-identity audits (s6b).

## Files

- Committed (`4542fdd`): `toolshop/flip/sample_voices.py`, `scripts/ogcm_sample.py`, `scripts/check_pack_meta.py`, `tests/test_flip_sample.py`, `CHANGELOG.md`, `ORCHESTRATION/ogcm_flip/LEDGER.md`. Outside the repo: `D:/Projects/.workspace_archive/plans/expected_output_ogcm_suno_sample_s6_20261001_015743.md`.
- Local, gitignored (`D:/Projects/Music-AI-Toolshop/Stemmeca_alatkka/stems/flip_sample/`): `audition_s6/` = `s6_00_drive_control.wav`, `s6_01_organ_string.wav`, `s6_02_organ_combo.wav`, `s6_03_organ_drawbar.wav`, `manifest.json`, `verification.json`; `index.html`. `audition_s2` ... `audition_s5` untouched. Listen at http://127.0.0.1:8777/flip_sample/.
- Scratch (session scratchpad, not in the repo): the S2/S3/S4/S5 identity renders, the first S6 render, the file-open audit wrapper, the RT60 and stats scripts.

## Close-out (AGENTS.md)

- All six paths I changed are committed in `4542fdd`; `git status --short` filtered for them returns nothing.
- `python -m toolshop.cli closeout` (run from `D:/Projects/Music-AI-Toolshop`) **exit 1, declared**: (a) working tree not clean, all foreign lanes (below); (b) **20 commits ahead of `origin/master`** (`git rev-list --count '@{u}..HEAD'` = 20; mine are `4542fdd` plus the follow-up docs commit, the rest are earlier waves and the foreign `b1c066b`); I did not push, pushing is the user's cadence. Submodules: ` 9bddc72... mastering_tool (heads/claude/wonderful-johnson-h6xj4d)`, ` 7acba12... suno_prompter (heads/main)`, no `+/-/U` prefix.
- Still-dirty paths, none staged or touched by me: `MAirina_Tucc/` (modified files plus untracked `devices.py`, `phonetics.py`, `rules.py`, `targets.py`, `lexicons/`, `ORCHESTRATION/mairina_v2/`, new tests); `ORCHESTRATION/prompts/` (modified `prompts_index.md`; untracked hemija prompts, index, `subagent_dispatch.json`); `ORCHESTRATION/ogcm_flip/` megaplan leftovers (modified `wave_m2/agent_b_bed_spike_handoff.md`; untracked `wave_m1/`, `waves_megaplan.json`, `prompts/prompts_index.md`, `prompts/subagent_dispatch.json`); `handoffs/orchestration_ledger_mairina_v2_20260930.md`; `lyrics_research/documents/` and `external_downloads/`; ~30 `scratch_*` probe files, `.scratch_i6/`, `.scratch_v1_audit.py`, `wt_bog_probe.txt`, stray `nul`; `mastering_tool` and `suno_prompter` show as ` M`/` ?` working-tree markers. After this handoff commit the only tree delta I introduce is this file, committed separately.
