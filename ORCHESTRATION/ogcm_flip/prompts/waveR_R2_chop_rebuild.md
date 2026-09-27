# R2 — Chop-and-rebuild sample-flip mechanics (OGCM flip)

You are a **researcher** agent. Web research only — do not grep local files, do not run code, do not make implementation decisions. Every factual claim must carry a URL citation. Prefer producer tutorials, technical docs, and OSS source over listicles.

## Context

Project: flip **2Pac — "Only God Can Judge Me"** (~89.1 BPM, A major) into a new drill/trap beat in `Music-AI-Toolshop`. The July approach — stretch the whole summed instrumental to a new tempo — produced "the same song slightly slower/darker." The confirmed rethink is **chop-and-rebuild**: slice the instrumental into chops, re-trigger them on a new beat grid, and program *new* drums underneath (a separate researcher covers drum/808 construction — do not spend effort there; stay on the sample side).

Local machinery already exists (context only — you don't need to verify): beat-grid + downbeat detection, self-similarity section segmentation (segment_class A/B/C + repetitions), onset/beat/section slicing helpers, pedalboard (Rubber Band R3) for per-buffer stretch/pitch.

## Key questions

1. **Producer method**: how do producers actually flip a full song into drill (which sections get picked, 2/4/8-bar loops vs transient chops, half-time vs double-time grid, layering, reversing, low-passing/darkening the chop, pitch-down range for drill darkness)?
2. **Loop/chop finding from audio**: algorithms for finding loopable regions — self-similarity / recurrence matrices, novelty + repetition scoring, bar-synchronous feature matching. Concrete open implementations (librosa recipes, papers, repos).
3. **Slicing technique**: zero-crossing vs onset-aligned cuts; microfade lengths that avoid clicks at retriggers; whether per-chop EQ gating or envelope shaping helps chopped drums bleed in the source.
4. **Per-chop time/pitch budget**: how much can a single chop be time-stretched inaudibly to fit a grid (what's the accepted artifact threshold for Rubber Band-style stretching — ±5%? ±10%?); pitch shifting chops ±2–4 st — formant/timbre consequences on melodic material.
5. **Re-triggering the grid**: direct buffer assembly (place samples at sample offsets) vs MIDI→sampler render (SFZ/SF2, fluidsynth CPU) vs DAW scripting — trade-offs for a headless Python pipeline.
6. **Tempo map given a fixed vocal**: the acapella stays at ~89.1 BPM unless stretched. Evaluate beat-grid options: 89.1 native, 133.65 (= 1.5×, triplet relation), 178.2 (= 2×), canonical ~140 drill — what half-time/double-time tricks make a drill beat grid compatible with an unstretched 89 BPM vocal? Cite any producers discussing acapella-over-new-tempo grid math.

## Deliverable

Write `D:\Projects\.workspace_archive\handoffs\researcher_ogcm_chop_rebuild_<yyyymmdd_hhmm>.md` containing:

- The chop selection + slicing recipe (with the reasoning, not just steps)
- Loop-finding algorithm pick + implementation sketch for Python/librosa
- Per-chop stretch/pitch budget table (artifact-free ranges)
- Re-trigger mechanism recommendation for a headless CPU pipeline
- Tempo-map options table with vocal-compatibility column
- End with this fenced contract:

```yaml
findings:
  chop_strategy: "<phrase|bar|transient + length guidance>"
  loop_finder: "<algorithm + impl>"
  per_chop_stretch_budget: "<±x% inaudible>"
  retrigger: "<buffer-assembly|midi-sampler|daw> — one-line reason"
  tempo_map_pick: "<bpm> — why it fits an unstretched 89.1 BPM vocal"
  sources: <n URLs cited>
```
