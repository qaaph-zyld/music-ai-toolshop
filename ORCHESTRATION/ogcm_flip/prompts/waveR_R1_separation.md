# R1 — Separation stack for a 1996 hip-hop master (OGCM flip)

You are a **researcher** agent. Web research only — do not grep local files, do not run code, do not make implementation decisions. Every factual claim must carry a URL citation. When sources conflict, say so and prefer measured benchmarks over marketing.

## Context

Project: rebuild a failed "drill flip" of **2Pac — "Only God Can Judge Me"** (1996, *All Eyez on Me*; ~297 s, ~89.1 BPM, A major) in `Music-AI-Toolshop`.

Current stems were produced July 2026 with **Demucs `htdemucs_6s`** (6 stems: vocals, drums, bass, other, guitar, piano) on CPU — ~8 min/track. Two remix attempts using these stems sounded bad; the project is being rebuilt around *chop-and-rebuild sampling* (chop the instrumental, re-trigger on a new grid, program new drums) with the original acapella re-laid over the new beat.

Machine constraints (hard): **Windows, CPU-only** (no usable CUDA), Python 3.11, corporate network (downloads possible but flaky; no paid APIs like MVSEP API — free/open-source only).

## Key questions

1. **Best 2025-26 open model for a low-bleed instrumental bed** from a 1996 compressed hip-hop master. Compare `htdemucs_6s` against: MDX23C, BS-RoFormer (vocal/instr variants), Mel-Band RoFormer, UVR MDX-NET inst/karaoke models, any newer OSS leaders on the MVSEP multisong leaderboard. Which produces the least residual vocal bleed in the non-vocal sum?
2. **Best acapella extraction**: `--two-stems vocals` vs dedicated vocal models (UVR-Voc, Reverb HQ, karaoke packs). Is a two-model vocal pass (vocal model → de-reverb/de-bleed pass) measurably better than a single demucs vocal stem?
3. **Kit-piece drum separation**: which open models split a drums stem (or full mix) into kick/snare/hat/toms (drumsep, MDX drum models, etc.)? This matters because drill one-shots must be mined from the track itself.
4. **CPU feasibility**: model formats (onnx vs pth), RAM, minutes-per-track on a mid-range CPU, install path on Windows (pip package, UVR repo, mvsep-open, audio-separator). Which are actually runnable here, not just hypothetically?
5. **Ground-truth-free quality metrics**: how to measure vocal bleed into the instrumental and acapella cleanliness when no reference stems exist (e.g., vocal-activity cross-check, energy-in-vocal-frames ratio, ensemble disagreement). Cite concrete metrics people use.

## Deliverable

Write `D:\Projects\.workspace_archive\handoffs\researcher_ogcm_separation_<yyyymmdd_hhmm>.md` containing:

- Ranked model table per need (instrumental bed / acapella / kit-piece drums) with install command, expected runtime, and artifact caveats
- A concrete recommended separation recipe (which models, in which order, expected runtime) that fits CPU-only Windows
- The bleed/cleanliness measurement method to apply at verification time
- End with this fenced contract:

```yaml
findings:
  recommended_pipeline: "<model chain>"
  instrumental_pick: "<model> — one-line reason"
  acapella_pick: "<model> — one-line reason"
  drums_pick: "<model> — one-line reason"
  cpu_feasible: true|false
  biggest_risk: "<one line>"
  sources: <n URLs cited>
```
