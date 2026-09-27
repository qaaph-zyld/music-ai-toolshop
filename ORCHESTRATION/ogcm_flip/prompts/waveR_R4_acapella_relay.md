# R4 — Re-laying an 89 BPM rap acapella onto a new-tempo beat (OGCM flip)

You are a **researcher** agent. Web research only — do not grep local files, do not run code, do not make implementation decisions. Every factual claim must carry a URL citation.

## Context

Project: flip **2Pac — "Only God Can Judge Me"** (~89.1 BPM, A major) into a new beat in `Music-AI-Toolshop`, then **re-lay the original 2Pac acapella over the new beat** (the classic fan "drill remix" format). The extracted vocal stem exists (htdemucs_6s `vocals.wav`) but its bleed/reverb quality is unmeasured.

The failure mode to avoid: July tried time-stretching audio 89→140 BPM (~1.57×) — phase-vocoder artifacts made it unusable. The vocal carries the same constraint. Rap acapellas are rhythmic rather than melodic, so timing is the dominant axis; pitch/formant problems matter but less than for sung vocals.

Local machinery (context only): faster-whisper word-timing transcription (~3.8 min/track CPU), onset cross-correlation measurement (used in-repo for splice alignment), Rubber Band R3 via pedalboard.

## Key questions

1. **How producers sync acapellas to new-tempo beats**: whole-file stretch vs per-phrase cutting vs "phrasing" (letting the acapella start on-beat and drift) vs re-tracking tempo. What do drill-remix and mashup producers actually do at 10-40%+ tempo gaps? Cite tutorials/threads with concrete technique.
2. **Audible stretch ceiling for rap vocals**: documented threshold where Rubber Band/élastique-grade stretch on a spoken-word vocal stays clean (is ~1.2× safe? 1.3×?); what breaks first (sibilance, plosives, breaths); does `preserve_formants` help rap or is it irrelevant without melody.
3. **Phrase/bar-level realignment**: the alternative to stretching — slice the acapella at breath/phrase boundaries and place each phrase on the new grid. How much internal timing drift is tolerable per phrase before it sounds off-grid; what alignment metrics people use (onset xcorr, beat-synchronous energy); existing tooling that does acapella-to-beat alignment automatically (any OSS repos, mashup tools, DJ software approaches).
4. **Tempo-map math for the vocal**: given 89.1 BPM, evaluate 89.1 native, 118.8 (4/3), 133.65 (3/2), 178.2 (2×) as beat grids — which let phrase boundaries land on bars without stretching vs requiring how much stretch? (This feeds the tempo decision that a parallel researcher R2 also touches — your job is the vocal-side constraint specifically.)
5. **Acapella prep on an extracted stem**: vocal stems carry bleed (drums/reverb tail). Cite de-bleed/de-reverb approaches people apply before re-laying — UVR de-reverb models, gating between phrases, spectral cleanup — and what level of residual bleed is audible once the vocal sits over a new beat.

## Deliverable

Write `D:\Projects\.workspace_archive\handoffs\researcher_ogcm_acapella_relay_<yyyymmdd_hhmm>.md` containing:

- Recommended re-lay strategy ranked (whole-stretch / phrase-realign / native-grid beat) with the tempo-map implications of each
- Stretch ceiling numbers for rap vocal specifically
- Phrase-boundary slicing + placement method sketch usable in Python (which boundaries, tolerance targets, verification metric)
- Acapella prep recipe for an extracted stem
- End with this fenced contract:

```yaml
findings:
  relay_strategy: "<whole-stretch|phrase-realign|native-grid|hybrid> — one-line reason"
  max_clean_stretch: "<x.x× for rap vocal>"
  phrase_method: "<boundary type + placement tolerance>"
  vocal_grid_pick: "<bpm grid that fits the vocal>"
  acapella_prep: "<de-bleed/de-reverb steps>"
  sources: <n URLs cited>
```
