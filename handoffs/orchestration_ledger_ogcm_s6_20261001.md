# Orchestration ledger · OGCM GATE S6 (organ × synthwave "night drive", street-rap energy) · 2026-10-01

- **Plan:** `D:\Projects\.workspace_archive\plans\ogcm-s6-organ-synthwave.md` (hash-identical mirror of the user-approved plan)
- **Waves:** `ORCHESTRATION/ogcm_flip/waves_s6.json`
- **Mode:** Claude Code orchestrator (does not code). Agents are `general-purpose` on model sonnet. One long agent at a time, in the foreground.
- **Predecessor:** S5 is verified (`orchestration_ledger_ogcm_s5_20260930.md`, `f52f931`). S5's G2 (ear test + Suno upload) is still open on the user's side and does not block S6.

## User direction (verbatim intent)

- "Can you swap in organs? We want to create a synthwave beat, night drive." The user said "finish your previous task first", and S5 was finished before S6 started.
- Base and organ parts are delegated: "whatever fits a more energetic, street rap, Bonez MC and Gzuz style, Cratez"; "what fits with my previous answer".
- Organ type: **render all three**. Drums: **drumless** (Suno builds the beat).

## Orchestrator's calls on the delegated choices

| Element | Choice |
|---|---|
| Lead | S5-A layering: the S4 riff (sine lead) + the guitar wail in the **saw timbre** (`S5_TIMBRE_SAW`) |
| Chords → organ | Rhythmic **stabs** on the S4-derived chords (Dm7–Bbmaj7), one file per organ type: string machine / combo / drawbar + rotary |
| Bass | Driving **8th-note octave synth bass** on the chord roots (replaces the sustained sine sub) |
| Pump | Drumless quarter-note sidechain-style duck on chords + bass |
| Control | `s6_00_drive_control`: EP chords + driving bass + pump, with no organ |
| Unchanged | 105 BPM, D minor, 8 bars, synthesis only, no drums/percussion |

## Waves

| Wave | Agent | Status | Handoff | Notes |
|---|---|---|---|---|
| s6r research | R | ✅ done (report-only; committed by the orchestrator) | `wave_s6r/research_s6_report.md` | **The Cratez:** produced Bonez "Hollywood" and most of "Sampler 5" (layered synths, 808 glides). There is **no public source for stab rhythms or organ use**, so the stab grids are inference. Camp tempos cluster around 85–100 (half-time) and 118–144; 105 sits between them and inside synthwave's 80–120. **Stabs:** bar 1 `x..x..x...x..x..`, bar 2 `x..x..x.x..x..x.` with velocity accents; gate 200/110/80 ms. **Bass:** 8th-note octaves `8.6.8.6…`, saw + square + sine, LPF24 at 350 Hz with +2.2 oct env, 140 ms decay. **Pump:** bass −6 / pad −9 / stabs −2 dB, 5 ms attack, 343 ms release. **Organs:** a parameter table per type (string ensemble 0.6 + 6 Hz; combo pulse footages + bright EQ; drawbar ratios, R1 888000000 + 3rd perc, Leslie 0.83/6.67 Hz). **Suno:** artist names can block a prompt; primary prompt is 167 chars. Tunebat/WhoSampled returned 403, so some items are snippet-sourced. |
| s6a implement + render | A | dispatched (foreground) | `wave_s6a/agent_a_s6a_handoff.md` | TASK_S6A below. **Orchestrator deviations from the s6r table:** (1) the drawbar key click keeps only the 6th-harmonic 6 ms click; the 1.5 ms noise component is dropped so the no-percussion rule stays unambiguous. (2) Stab voicings stay the S4 `derive_chords` voicings; only the rhythm and accents come from s6r. |
| s6b verify | B | not started | `wave_s6b/agent_b_s6b_verify_handoff.md` | G3 follows |
| G3 | user | — | — | ear test (pick an organ type) + Suno upload with the style prompt |

## Invariants each wave

- Python: only `.venv\Scripts\python.exe`. Absolute paths; CPU only. The Bash tool lacks git/grep, so use PowerShell for git.
- No edits to `bed_lanes.py`, `arrange.py` or `master.py`. Existing functions stay unchanged, and S2–S5 outputs stay byte-identical. No new dependencies. Renders are deterministic.
- No drums/percussion. No source audio in any Suno-bound file.
- Explicit-path commits with separate add/commit. Never stage foreign-lane files (`MAirina_Tucc/`, `lyrics_*`, `Genious_*`, `scratch_*`, `ORCHESTRATION/lyrics_sources`, foreign ledgers). No WAVs.

## Dispatch prompts (verbatim record)

### TASK_S6R

```text
Web research, REPORT-ONLY, for OGCM GATE S6. Write exactly ONE file: D:/Projects/Music-AI-Toolshop/ORCHESTRATION/ogcm_flip/wave_s6r/research_s6_report.md (create the folder). No code changes, no git, no other writes.

BACKGROUND
We build a DRUMLESS melodic loop sample, which the user uploads to Suno so Suno builds the beat.
- Current state: 105 BPM, D minor, 8 bars. There is a riff lead and a "wail" lead: a guitar line re-performed on a saw synth from its tracked pitch contour. The chords alternate Dm7 / Bbmaj7, one per bar. Everything is numpy/pedalboard synthesis; no source audio is ever in the output.
- The user now wants organs, a synthwave "night drive" feel and more energy, in the style of German street rap: Bonez MC & Gzuz (187 Strassenbande), producer The Cratez.
- Plan: the organ plays rhythmic chord STABS, with three organ types rendered (string-machine pad, combo organ, drawbar + rotary). A driving 8th-note octave synth bass and a drumless quarter-note sidechain-style pump are added.

QUESTIONS

Q1 Street-rap production signatures: Bonez MC & Gzuz / 187 Strassenbande tracks produced by The Cratez, plus comparable producers of that camp.
- Tempo ranges, with named example tracks.
- Melodic instruments: organs? synth leads, pianos, bells, plucks.
- Chord rhythm: stabs vs pads, and TYPICAL STAB RHYTHMS written as 16th-step grids (e.g. x..x..x...x..x..).
- Bass behaviour (808 glides vs driving).
- Loop and arrangement energy devices.
- Any tracks with organ or synthwave/80s colour.
Cite interviews, producer breakdowns, Genius, Wikipedia, YouTube descriptions. Mark every inference as inference. "Unknown" is acceptable.

Q2 Synthwave "night drive" palette, with concrete numbers:
- typical tempo range
- driving bass patterns (8th octave, 16th), bass synth recipe (osc, filter cutoff/env, decay)
- a drumless sidechain pump: depth in dB, duck curve, release as a fraction of a beat
- reverb and delay conventions

A numpy-feasible synthesis recipe for EACH organ type, as a parameter table:
(a) String machine (Solina/ARP-style): divide-down saws, the ensemble/BBD chorus (rates such as 0.6 Hz and 6 Hz, depths in ms), filter, attack and release.
(b) Combo organ (Farfisa/Vox Continental-style): square/pulse waveforms and footages, vibrato rate and depth, a bright filter, percussive attack.
(c) Drawbar (Hammond-style):
   - additive footages 16', 5 1/3', 8', 4', 2 2/3', 2', 1 3/5', 1 1/3', 1' as harmonic ratios
   - 2-3 registrations suited to stabs (e.g. 888000000, 008800000; give the reasoning)
   - key click (level, duration)
   - percussion (2nd/3rd harmonic decay)
   - the rotary/Leslie effect: horn and drum rotor rates, slow ~0.8 Hz / fast ~6.7 Hz, AM depth, Doppler pitch depth, stereo mic spacing
For each item, say which parameters matter most for a short STAB versus a sustained pad.

Q3 Suno, from PUBLIC docs and help pages only.
- How does Suno use an uploaded instrumental? (upload/cover/extend; audio length limits; whether a drumless loop is a good input)
- Are artist names disallowed in style prompts? If so, describe the style without naming artists.
- Propose one style prompt of 200 characters or fewer for "German street rap x synthwave night drive, energetic, organ stabs, driving bass", plus 2 alternates.
OUT OF SCOPE: any technique for getting copyrighted audio or melodies past Suno's (or any) content-identification filter.

FORMAT
- A 5-bullet summary.
- Sections Q1, Q2 and Q3. Every claim carries [source URL] and a confidence level (high/med/low).
- End with three code-free blocks:
  - "Stab pattern recommendation": 16-step grids for bar 1 and bar 2, with velocity accents.
  - "Organ + bass + pump parameter table": the values s6a should use.
  - "Suno style prompt": primary + 2 alternates.
- About 1800 words at most.
Your final message: the report path, the 5-bullet summary and the three end blocks verbatim.
```

### TASK_S6A

```text
Execute wave s6a of OGCM GATE S6 in D:/Projects/Music-AI-Toolshop. You are the implementer. Do only s6a.

READ FIRST
1. D:/Projects/Music-AI-Toolshop/AGENTS.md
2. The approved plan D:/Projects/.workspace_archive/plans/ogcm-s6-organ-synthwave.md, sections Context, "s6a", Constraints and Verification.
3. The research report ORCHESTRATION/ogcm_flip/wave_s6r/research_s6_report.md, especially its three end blocks.
4. Code: scripts/ogcm_sample.py (_s4_source, _s5_wail, _s5_variants, _render_s5_bus, _texture_fx, _to_target, main) and toolshop/flip/sample_voices.py (render_f0_lead, render_simple_lead, render_rhodes, render_sub, derive_chords, chord_bednotes, bass_root_notes, west_coast_chain, fit_loop, _soft_clip). Also read the s5b handoff ORCHESTRATION/ogcm_flip/wave_s5b/agent_b_s5b_handoff.md.

WHAT TO BUILD
S6 is organ x synthwave "night drive" with street-rap energy. It is DRUMLESS: Suno builds the beat. It is SYNTHESIS ONLY: no source audio in any output file. Settings: 105 BPM, D minor, 8 bars, -16 LUFS, TP <= -1 dBTP.
- Lead (all files): the S5-A layering, i.e. the S4 riff on render_simple_lead plus the guitar wail from render_f0_lead in the SAW timbre (S5_TIMBRE_SAW), at S5_A_WAIL_DB (-3 dB) relative to the riff lead. Build it by reusing S5's riff, wail, tempo and gain construction. If you factor a shared helper out of _s5_variants, every S5 output MUST stay byte-identical; prove it.
- Chords: the S4-derived chords from derive_chords (Dm7 / Bbmaj7, one per bar), KEEPING their existing voicings. Only the rhythm changes, to stabs.
- Bass: a driving 8th-note octave synth bass on each bar's chord root. It replaces the sustained sine sub.
- Pump: a drumless quarter-note duck.

RECIPE (from s6r; use these values)

Stabs, 16th steps 1-16 per bar ("x" = hit, "." = rest; velocity 1-9 aligned to the grid):
- odd bars (1, 3, 5, 7): x..x..x...x..x..  velocity 9..6..8...5..7..
- even bars (2, 4, 6, 8): x..x..x.x..x..x.  velocity 8..5..7.9..5..6.
- Gate by velocity: vel 8-9 -> 200 ms, 6-7 -> 110 ms, 1-5 -> 80 ms.

Organs:
(a) string machine
- saws 16'/8'/4' at levels 0.3 / 1.0 / 0.6 (for stabs, 8'+4' is acceptable)
- ensemble: 3 lines at 0/120/240 deg phase, LFO 0.6 Hz (+/-2.5 ms) + 6.0 Hz (+/-0.3 ms), mixed 79/21
- LPF 5 kHz; stab envelope A 10 ms, R 150 ms
(b) combo organ
- 50% pulse footages 16'/8'/4'/2' at 0.25 / 1.0 / 0.7 / 0.35
- HP 150 Hz, +4 dB at 2.8 kHz, LPF 6.5 kHz; stab envelope A 2 ms, R 60 ms
- vibrato 5.5 Hz +/-8 cents only for pad use; OFF for stabs
(c) drawbar
- additive harmonic ratios 0.5, 1.4988, 1, 2, 2.9976, 4, 5.0409, 5.9953, 8 (footage order 16' 5 1/3' 8' 4' 2 2/3' 2' 1 3/5' 1 1/3' 1'); about 3 dB per drawbar step
- registration R1 888000000 + percussion 3rd harmonic at 0.5x (main stabs); R3 888611348 on the accent stabs (vel >= 8)
- stab envelope A 3 ms, R 70 ms
- key click: ONLY a 6th-harmonic burst, 6 ms at -18 dB. NO noise component (orchestrator deviation: keeps the no-percussion rule unambiguous).
- Leslie/rotary in numpy:
  - horn (above an 800 Hz crossover) 6.67 Hz fast; drum 5.67 Hz fast (use FAST for energy)
  - AM +/-3 dB (horn) / +/-1.5 dB (drum)
  - Doppler as a modulated delay of +/-0.44 ms
  - L/R mics 90 deg apart, so L != R
  - Deterministic; no RNG, or a fixed seed.

Bass:
- 8ths alternating low and high octave, velocity 8.6.8.6.8.6.8.6; bar root in octave 2 / octave 3 (D2/D3 on Dm7 bars, Bb1/Bb2 on Bbmaj7 bars; take the root from each chord's root_pc)
- oscillators: saw -12 cents, square -12 cents, sine an octave down at -6 dB
- filter: LPF 24 dB at base 350 Hz, envelope +2.2 octaves (~1.6 kHz peak), decay 140 ms, Q about 1.2
- amp: A 3 ms, gate 75% of an 8th, R 30 ms; soft clip about +4 dB drive

Pump:
- a duck at beats 1-4, attack 5 ms, release 343 ms exponential
- depth: bass -6 dB, pad/EP -9 dB, organ stabs -2 dB; the lead is NOT pumped

FX:
- organ and bass return: hall ~2.2 s (pedalboard Reverb room_size ~0.8), pre-delay 25 ms (pedalboard Delay mix 1.0 in front of the reverb, or a sample shift), HP 200 Hz on the return, wet -16 dB
- lead: keep west_coast_chain with lead_delay_s = the dotted 8th at 105 (0.428571 s)
- Do not change west_coast_chain's existing behavior. New lanes get their FX in a NEW S6 bus function.

TASKS

0. Pre-flight: git -C D:/Projects/Music-AI-Toolshop status --short and log --oneline -5 (use PowerShell for git; the Bash tool has none). Never touch foreign-lane files.

1. toolshop/flip/sample_voices.py. ADDITIVE ONLY, with zero removed lines and existing functions untouched.
- render_organ(notes, kind, sr=44100, **params), kind in {"string", "combo", "drawbar"}
  - accepts per-note velocity
  - drawbar picks R3 when velocity >= 0.85 (the vel-8/9 accents)
  - stereo float32, peak-guarded, deterministic
- stab_pattern(chords, bar_s, patterns=(odd_grid, even_grid), velocities=(...), gates_ms=...) returns stab BedNotes using each chord's existing "notes" voicing. Onsets on the 16th grid; notes never cross into the next bar.
- driving_bass(chords, bar_s, root_octave_low=2) returns 8 BedNotes per bar.
- render_synth_bass(notes, sr=44100, **recipe)
- pump(audio, sr, beat_s, depth_db, attack_ms=5.0, release_s=None, n_beats=None): a quarter-note duck envelope; unity at depth 0.

2. scripts/ogcm_sample.py: --pack s6 (tempo default 105 via --tempo-bpm). Writes to Stemmeca_alatkka/stems/flip_sample/audition_s6/.

   | File | Lead | Chords | Bass | Pump |
   |---|---|---|---|---|
   | s6_00_drive_control | riff + saw wail | EP whole notes as in S5 | driving bass | EP -9 dB, bass -6 dB |
   | s6_01_organ_string | same | string-machine stabs | driving bass | pump |
   | s6_02_organ_combo | same | combo stabs | driving bass | pump |
   | s6_03_organ_drawbar | same | drawbar + rotary stabs | driving bass | pump |

- Level balance: the lead stays the clear top (as in S5, the lead is the reference). The organ stabs sit about -6 dB under the lead, and the bass is present but not dominant. Report the RMS balance per lane.
- manifest.json holds:
  - bpm, tempo_factor, lead_delay_s
  - stab grids, velocities and gates
  - bass recipe, pump settings
  - organ recipe per kind; organ_kinds ["string", "combo", "drawbar"]
  - wail_source (as S5)
  - "drums": false, "source_audio_in_output": false
  - "suno_style_prompt": the s6r primary and 2 alternates, verbatim
- Also write verification.json.
- Renders are deterministic; check two runs are byte-identical.
- PROVE S4 and S5 unchanged: re-render --pack s4 and --pack s5 into scratch outdirs and compare SHA256 against the current on-disk audition_s4/ and audition_s5/ files.
  - If the on-disk S4 WAVs predate a harmless refactor (s5c saw that), a match to within the 24-bit quantum in an in-memory rebuild is acceptable. State which evidence you used.

3. NEW scripts/check_pack_meta.py (O7): --manifest <path> --bpm-min 102.5 --bpm-max 107 --require-organ-kinds string,combo,drawbar. Exits 0 only if all of these hold:
- source_audio_in_output is false and drums is false
- bpm is within range
- organ_kinds equals the required set
- every manifest file exists and is non-empty

4. tests/test_flip_sample.py (synthetic data, small SR):
- each organ kind is non-silent, finite, <= 1.0 and deterministic
- drawbar L != R (rotary)
- string/combo are deterministic
- stab_pattern onsets are multiples of a 16th, and each note ends before its bar's end
- driving_bass has exactly 8 notes per bar, with root pc == chord root_pc, alternating octave
- pump at depth 0 is the identity; at depth -6 dB the level at a beat onset is about -6 dB (+/-1 dB)
- render_synth_bass is finite, <= 1.0 and deterministic

5. Records.
- Stemmeca_alatkka/stems/flip_sample/index.html: a NEW S6 section at the TOP.
  - Title: "S6 — organ x synthwave night drive (105 BPM, D minor, drumless, synthesis only)".
  - Four players with role captions (00 = control without organ).
  - A copy box (a <pre> or <textarea readonly>) holding the primary Suno style prompt, with the 2 alternates below it.
- ALSO label every real-audio REF entry on the page (s4_05_chop_REF, s3_05_chop_REF, s2_06_E_real8_REF, the S1 sample_E, and any other real-record chop) with a visible "REAL RECORD — never upload to Suno" badge. Leave the other sections unchanged.
- Spec D:/Projects/.workspace_archive/plans/expected_output_ogcm_suno_sample_s6_<YYYYMMDD_HHMMSS>.md:
  - O1''' verify_sample_pack --dir audition_s6 --glob "s6_*.wav" --min-files 4 --min-s 15 --max-s 45 --lufs -16 --lufs-tol 1.0 --tp-max -1.0
  - O2 pytest test_flip_sample.py
  - O3''' check_audition_serve --glob "audition_s6/s6_*.wav"
  - O4 the 4-file flip suite
  - O5 check_riff (S4 manifest)
  - O6 check_contour (S5 manifest)
  - O7 check_pack_meta (S6 manifest)
- LEDGER.md: an s6a row. CHANGELOG.md: the next unique #NNN after #075 (grep CHANGELOG.md only to confirm it is unused).

6. Gates: run O1''' through O7 and quote each command, exit code and key output. Check :8777 is up before O3'''; start it from Stemmeca_alatkka/stems as a background process only if it is down.

7. Commit with explicit paths: sample_voices.py, ogcm_sample.py, check_pack_meta.py, test_flip_sample.py, CHANGELOG.md and LEDGER.md.
- Message: feat(#NNN): GATE S6a - organ x synthwave night drive pack (3 organ stab voices, driving octave bass, drumless pump) at 105 BPM.
- Separate add and commit calls. Stems stay gitignored (confirm with check-ignore; never force-add).
- Then write the handoff ORCHESTRATION/ogcm_flip/wave_s6a/agent_a_s6a_handoff.md and commit it as docs. It includes:
  - the commits
  - every command with its exit code and key output
  - the per-lane RMS balance
  - the S4/S5 identity evidence
  - wall times
  - deviations
  Do NOT claim anything "sounds" good. Only the user's ear decides.

CONSTRAINTS
- Python: only D:/Projects/Music-AI-Toolshop/.venv/Scripts/python.exe (3.11). Absolute paths; Cwd = D:/Projects/Music-AI-Toolshop; CPU only.
- No edits to bed_lanes.py, arrange.py or master.py. Existing functions keep their behavior; S2-S5 outputs stay byte-identical. No new dependencies (numpy, pedalboard and librosa only). Renders are deterministic.
- NO drums or percussion lanes and NO noise bursts. NO source audio in any audition_s6 file. The guitar stem may be read ONLY via S5's contour path.
- git -C, explicit paths, separate add/commit. Never stage MAirina_Tucc/, lyrics_*, Genious_*, scratch_*, ORCHESTRATION/lyrics_sources or foreign ledgers. No WAVs. Never --no-verify. If a concurrent session races you, re-check status and report; never force.
- Foreground only; never "background + end turn". Split long renders across calls.
- Your final message: the handoff path, commit hashes, the gate exit codes, the per-lane RMS balance and the S4/S5 identity evidence.
```
