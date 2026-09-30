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
| s6r research | R | dispatched (foreground) | `wave_s6r/research_s6_report.md` | TASK_S6R below |
| s6a implement + render | A | not started | `wave_s6a/agent_a_s6a_handoff.md` | prompt finalized after s6r |
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
