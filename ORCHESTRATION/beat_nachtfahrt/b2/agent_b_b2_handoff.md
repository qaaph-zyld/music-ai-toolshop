# Nachtfahrt b2 handoff

Code commit: `7b6ed92` feat(#079) (toolshop/beat/nachtfahrt.py, scripts/build_nachtfahrt.py, tests/test_beat_nachtfahrt.py, CHANGELOG.md).

## Gates
- `.venv/Scripts/python.exe -m pytest tests/test_beat_nachtfahrt.py -q` -> exit 0, 35 passed (15 b1 + 20 b2)
- flip regression (test_flip_sample, test_flip_arrange, test_flip_master, test_flip_bed_lanes) -q -> rc=0, 151 passed
- `git diff --stat HEAD -- toolshop/flip toolshop/premaster.py` -> exit 0, empty
- `.venv/Scripts/python.exe -X utf8 -u scripts/build_nachtfahrt.py --stage render` -> rc=0, ~52 s wall (run twice; final run after the last code edit)
  - render_manifest.files_read_during_render = `[]`, source_audio_in_output = false
  - section_map.json: 9 sections, bars 1-80, sum n_bars 80
  - all 10 stems: 186.857 s, stereo PCM_24, non-silent

## composition_hash
`89b1fa48b54c17df7127a698280f4616d91741e94e34f5b271d58d5fa8b5be1f`

## Stem table (peak; RMS dB per section; None = digital silence)
| lane | peak | intro | hook (A) | verse1 | bridge | hook D | outro |
|---|---|---|---|---|---|---|---|
| kick | 0.891 | None | -13.18 | -13.80 | -15.39 | -13.18 | -64.0 (tail) |
| snare | 0.950 | None | -25.16 | -26.16 | -28.20 | -25.16 | None |
| hats | 0.950 | None | -23.66 | -29.71 | -66.88 | -22.66 | -61.87 |
| fx | 0.802 | -27.07 | -31.60 | -33.09 | -30.08 | -31.60 | None |
| bass808 | 0.950 | None | -10.49 | -8.73 | -11.15 | -10.49 | -49.09 |
| synthbass | 0.950 | None | -5.15 | None | None | -5.15 | None |
| pad | 0.786 | -16.35 | -14.96 | -20.90 | -16.26 | -14.96 | -16.23 |
| arp | 0.359 | -28.25 | -25.19 | -30.25 | -27.12 | -25.55 | -28.17 |
| stabs | 0.841 | -108.13 | -19.79 | -31.67 | -86.69 | -19.83 | -341.99 |
| lead | 0.950 | None | -7.06 | None | -11.56 | -6.65 | None |
Full per-section numbers: `Stemmeca_alatkka/stems/beats/nachtfahrt/render_manifest.json` (gitignored). Stems sit at 0.950 where the lane peak-guard bit (hats, snare, bass808, synthbass, lead); relative levels are untouched.

## files_read_during_render provenance
`sys.addaudithook` is installed at import and only records while `audited_call(render_lanes)` runs. It records `open` events whose path ends in .wav/.flac/.mp3/.mid/.midi; the stem writes happen after the audited call, so no output writes are in the list. The test `test_audit_hook_catches_audio_open` proves the hook records a .mid open and ignores .txt. Result: empty list.

## Section map (bars, start_s -> end_s)
intro 1-4 0->9.143; hook_a 5-12 9.143->27.429; verse1 13-28 27.429->64.0; hook_b 29-36 64.0->82.286; verse2 37-52 82.286->118.857; hook_c 53-60 118.857->137.143; bridge 61-68 137.143->155.429; hook_d 69-76 155.429->173.714; outro 77-80 173.714->182.857.

## Deviations / choices the plan left open
- Data additions: `LEVELS` and `DRUM_VEL` (per-section velocities, lane gate/glide values) are my values; they are inside composition_hash. HOOK_MELODY is the 4-bar pattern; `HOOK_MELODY_REPEAT` carries the (3,8,8,74) resolution.
- Arp: 8 tones up then the same 8 down (16 steps, top tone repeated once); gate 1.5 steps; the pluck output is peak-normalised before the low-pass automation (render_pluck is unscaled). Low-pass = two cascaded one-pole filters, cutoff updated per 512-sample block.
- Pad: `render_organ("string", attack_ms=300, release_ms=800)` via recipe overrides, no custom code needed.
- 808: `render_808` glides on every pitch change, so the 808 line is split into phrases where a pitch change is not m3/P4 (3 or 5 semitones). Those changes become hard steps, and only Bb->G (m3) and A->D (P4) slide.
- Verse 4th-bar roll: the closed-hat 8ths at steps 12 and 14 are replaced by 12,13,14,14.5,15,15.5 (velocity rising 0.5 -> 0.9), and the open hat on step 14 is kept as written, so the open hat sits on top of the ratchet.
- Bridge: bars 65-66 have kick only (no snare/hat); bar 67 snare 8ths (0.8), bar 68 snare 16ths with vel 0.4 -> 1.0 and pitch 0 -> +5 st via per-step resampled one-shots (`snare_r0..r15`). Bridge bars 61-64 kick is a separate `kick_lp` event list, rendered then 200 Hz Butterworth-4 low-passed.
- The gated reverb on the hook snare is a mix FX and is left to b3.
- Hook D lead double is rendered as its own note list (`lead_double_notes`) at -8 dB output gain, summed into the lead lane. Hook D open hats are +2 dB (velocity x1.259).
- `render_lanes(sr, bars=(first, last))` is the test-only slice parameter (1 s tail).
- Drum events use bar-relative beats; `_kick_hits_808` derives the bar from `DrumEvent.bar` to avoid float-floor errors at bar boundaries.
- Determinism not byte-compared across two full builds in this wave (b4 does it); everything is seeded and no wall-clock input enters audio.

## Git status
Dirty paths left unstaged are all foreign lanes (MAirina_Tucc/, ORCHESTRATION/ogcm_flip/*, prompts_index files, untracked mastering_tool, suno_prompter). This handoff is committed separately as docs.
