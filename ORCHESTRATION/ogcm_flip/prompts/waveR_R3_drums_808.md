# R3 — Drill drums + sliding 808 built from the track's own stems (OGCM flip)

You are a **researcher** agent. Web research only — do not grep local files, do not run code, do not make implementation decisions. Every factual claim must carry a URL citation.

## Context

Project: flip **2Pac — "Only God Can Judge Me"** (~89.1 BPM, A major) into a drill-style beat in `Music-AI-Toolshop`. Hard user constraint: **drum and 808 material is extracted from the track itself** where possible — no external kit download. Available material: a separated `drums.wav` stem (all kit pieces mixed: kick/snare/hats) and a `bass.wav` stem from htdemucs_6s, plus a possible better separation pass pending (a parallel researcher R1 picks the model — assume we can get at minimum a clean drums stem; if R1 finds kit-piece separation, one-shots may come pre-split).

A parallel researcher (R2) covers chop/grid mechanics and tempo options — coordinate only at the level of "what beat programming fits the grid"; don't re-research tempo selection.

## Key questions

1. **Drill drum grammar**: canonical UK/NY drill programming — tempo feel (140-ish BPM half-time), snare placement (on 3 vs 4, "counter-snare"), kick syncopation, hi-hat rolls/triplets/stutters, open-hat and perc usage. Give concrete step-sequenced pattern descriptions producers document, not just vibes.
2. **808 slide mechanics**: how the glide is actually programmed — monophonic legato, portamento/glide time ranges, tuning the 808 sample to the song key, envelope settings (attack/decay/sustain/release with long hold), "cut itself" behavior to avoid overlapping notes, layering a punchy kick on the 808 attack.
3. **Mining one-shots from a mixed drums stem**: onset detection → per-hit segmentation → classify kick vs snare vs hat from audio features (spectral centroid, low-band energy, decay profile). Cite concrete methods/repositories for drum-hit classification or transcription-driven extraction (e.g., drum transcription models that output per-hit MIDI you can slice against).
4. **808 source decision**: can OGCM's `bass.wav` stem yield a usable sustained 808-like voice (pitch, gate, sustain processing) — or is a synthesized sine + pitch-envelope + soft-saturation 808 objectively better for slides? What does each path sound like and cost on CPU?
5. **Pattern rendering, CPU-only**: options to turn a programmed pattern into audio without a DAW — direct WAV segment assembly, MIDI → SoundFont render (fluidsynth), per-hit sample playback engine in Python. What exists and what's solid on Windows/Python 3.11?
6. **Honoring the constraint**: when the extracted drums are too "boom-bap" for drill, what's the documented producer approach — layering extracted transients over synthesized subs, heavy transient/pitch processing of extracted hits, or synthesizing hat/snare entirely? Keep "from the track" as the honored spirit: cite real precedents.

## Deliverable

Write `D:\Projects\.workspace_archive\handoffs\researcher_ogcm_drums_808_<yyyymmdd_hhmm>.md` containing:

- A concrete drill pattern grammar (bar-by-bar description usable as a programming spec)
- The sliding-808 recipe (envelope/glide/tuning numbers)
- One-shot mining method + kick/snare/hat classification features
- 808 source recommendation (stem-derived vs synthesized) with reasoning
- CPU render path recommendation
- End with this fenced contract:

```yaml
findings:
  pattern_grammar: "<one-line summary of the drum map chosen>"
  one_shot_mining: "<method + classifier features>"
  kick_snare_hat_split: "<feasible|partial|no — why>"
  808_source: "<bass-stem|synth|hybrid> — reason"
  render_path: "<buffer-assembly|fluidsynth|other>"
  sources: <n URLs cited>
```
