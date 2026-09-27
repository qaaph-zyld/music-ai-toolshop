# OGCM Flip — Orchestration Ledger

Config: `waves.json` · Plan: `D:\Projects\.workspace_archive\plans\ogcm-flip-research-first-rebuild.md` · Dispatch card: `DISPATCH.md`

## Wave R — Research (status: COMPLETE 2026-09-27)

Executed inline by orchestrator session (no native subagent dispatch in harness; user approved inline). All four handoffs verified: present, URL-cited, fenced YAML `findings` contract with all required keys.

| Agent | Handoff | Contract | Key pick |
|---|---|---|---|
| R1 | `researcher_ogcm_separation_20260927_0158.md` | ✔ 7/7 keys, 31 sources | MelBand RoFormer voc/instr + karaoke + de-reverb; MDX23C DrumSep on drums.wav; CPU-feasible (est 30–90 min/track — measure at W0) |
| R2 | `researcher_ogcm_chop_rebuild_20260927_0158.md` | ✔ 6/6 keys, 23 sources | 2–4 bar melodic chops via SSM novelty; buffer-assembly retrigger; **tempo 178.2 written / 89.1 felt** |
| R3 | `researcher_ogcm_drums_808_20260927_0158.md` | ✔ 6/6 keys, 18 sources | snare-on-3 + 3+3+2 kick + triplet-burst hats; drum-sample-extractor one-shot mining; hybrid 808 (synth voice + stem transients) |
| R4 | `researcher_ogcm_acapella_relay_20260927_0158.md` | ✔ 6/6 keys, 17 sources | native-grid + phrase realign; stretch ceiling ~1.1–1.2× rap; **vocal grid 178.2 / 89.1 felt** |

Handoffs dir: `D:\Projects\.workspace_archive\handoffs\`

### Reconciliation notes for wave 0

- **Tempo: no conflict.** R2 and R4 independently picked 178.2 written / 89.1 felt (2:1 bridge, zero vocal stretch). Synthesis can freeze this unless user wants the 133.65 triplet alternative evaluated.
- **R3↔R1 dependency resolved:** R1 found MDX23C DrumSep (jarredou/aufr33) — kit-piece separation is on the table, satisfying R3's assumption.
- **Flagged risks to carry into spec:** RoFormer CPU runtime unmeasured (overnight-batch); model downloads via flaky proxy (pre-seed cache); hybrid 808 recommended over pure stem-derived.

## Wave 0 — Synthesis + spec freeze (SPEC FROZEN 2026-09-27 — awaiting user gate)

Spec: `D:\Projects\.workspace_archive\plans\ogcm-flip-synthesis.spec.md` (D1–D9).

Frozen picks: tempo **178.2 written / 89.1 felt** (2:1 bridge — reconciled R2-vs-R4; R4's vocal-side pick was actually 133.65, documented as fallback) · key **D minor via −4 st** (UK-dark pitch-down) · separation **MelBand RoFormer + karaoke + anvuew de-reverb; MDX23C DrumSep on drums.wav** · chops = SSM+novelty+seam-score manifest, ±10 % stretch budget · kit = DrumSep→drum-sample-extractor→manifest (DrumScript fallback) · 808 = hybrid synth-glide + OGCM transients · render = buffer assembly · vocal = phrase-realign anchored ≤30 ms, zero stretch at 178.2 · master −14 LUFS / TP ≤ −1.

Gate questions pending user: tempo confirm vs 133.65 alt · key confirm · snare density (every-bar vs every-other-bar) · scope confirm.

## Wave 1 — W0 re-separation (blocked: needs spec approval)

## Wave 2 — Beat build (blocked: needs wave 1; user listen gate)

## Wave 3 — Vocal re-lay + master (blocked: needs wave 2; user gate)
