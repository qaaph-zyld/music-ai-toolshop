# OGCM Flip — Orchestration Ledger

Config: `waves.json` · Plan: `D:\Projects\.workspace_archive\plans\ogcm-flip-research-first-rebuild.md` · Dispatch card: `DISPATCH.md`

## Wave R — Research (status: COMPLETE 2026-09-27)

Executed inline by orchestrator session (no native subagent dispatch in harness; user approved inline). All four handoffs verified: present, URL-cited, fenced YAML `findings` contract with all required keys.

**Canonical handoff set** — R2 and R4 each left an expanded second-pass handoff that supersedes the `_0158` draft (superseded files left on disk; do not synthesize from them):

| Agent | Canonical handoff | Contract | Key pick |
|---|---|---|---|
| R1 | `researcher_ogcm_separation_20260927_0158.md` | ✔ 7/7 keys, 31 sources | MelBand RoFormer voc/instr + karaoke + de-reverb; MDX23C DrumSep on drums.wav; CPU-feasible (est 30–90 min/track — measure at W0) |
| R2 | `researcher_ogcm_chop_rebuild_20260927_0205.md` | ✔ 6/6 keys, 56 sources | 1–4 bar phrase chops via beat-sync chroma SSM + seam-score; buffer-assembly retrigger; **tempo 178.2 written / 89.1 felt** (fallback 133.65) |
| R3 | `researcher_ogcm_drums_808_20260927_0158.md` | ✔ 6/6 keys, 18 sources | snare-on-3 + 3+3+2 kick + triplet-burst hats; drum-sample-extractor one-shot mining; hybrid 808 (synth voice + stem transients) |
| R4 | `researcher_ogcm_acapella_relay_20260927_0203.md` | ✔ 6/6 keys, 46 sources | phrase-strip → VR-Arch de-echo → whisper-gap boundaries → barline anchors ≤30 ms → ≤1.25× bounded warp; **vocal grid 133.65** (runner-up 178.2) |

Handoffs dir: `D:\Projects\.workspace_archive\handoffs\`

### Reconciliation notes for wave 0

- **Tempo: real split → USER-RESOLVED dual-build** (corrected 16:4x). Earlier "no conflict" note was stale — written against the `_0158` drafts. Final contracts: R2 picks **178.2 written (2:1, felt 89.1)**; R4's expanded handoff picks **133.65 (exact 3:2, vocal rides triplet slots)**. Both zero-stretch. User gate resolved: **build both arms, blind-pick at W5/GATE F**.
- **R3↔R1 dependency resolved:** R1 found MDX23C DrumSep (jarredou/aufr33) — kit-piece separation is on the table, satisfying R3's assumption.
- **Flagged risks to carry into spec:** RoFormer CPU runtime unmeasured (overnight-batch); model downloads via flaky proxy (pre-seed cache); hybrid 808 recommended over pure stem-derived.

## Wave 0 — Synthesis + spec freeze (APPROVED 2026-09-27 — implementation authorized)

Spec: `D:\Projects\.workspace_archive\plans\ogcm-flip-synthesis.spec.md` (D1–D9);
implementation plan: `C:\Users\015ZCS\.devin\plans\plan-87307e9665c424d6.md` (mirrored
`.workspace_archive\plans\ogcm-flip-research-first-rebuild.md`).

Adversarial review applied (target: plan) → **approved-with-fixes**, all medium findings fixed
in plan. Report: `D:\Projects\.workspace_archive\reviews\2026-09-27_1629_ogcm-flip-plan.md`.

**User gate picks (differ from earlier frozen defaults):**
- Tempo: **build BOTH grids** — 178.2 written / 89.1 felt AND 133.65 — blind-pick at W5.
- Key direction: **Down / UK-dark** — per-chop landing keys reported (no global-key assumption).
- Dependencies: **authorized** — audio-separator models pre-seeded to `~/.cache/toolshop-models`.
- Code location: **`toolshop/flip/`** subpackage.

## Wave 1 — implementation W0+W1 (IN PROGRESS 2026-09-27)

- W0 registry: `stem_models.py` extended — MelBand RoFormer Kim bleedless
  (`mel_band_roformer_kim_ft2_bleedless_unwa.ckpt`), anvuew dereverb, MDX23C DrumSep;
  `ogcm-flip` chain preset + `ogcm-drumsep` preset; dynamic CLI preset choices.
  Cache verified complete, zero orphans. Commit `eecfd0b`.
- W0 run: full-track `ogcm-flip` chain → `Stemmeca_alatkka/stems/v2/` RUNNING
  (step 1/3 Kim done 18:07; step 2 karaoke in progress; step 3 dereverb pending).
- W1 chops: `toolshop/flip/chops.py` + `toolshop flip chops` CLI — 24 candidates on legacy
  bed, seam/bleed/tonal-center scoring verified; audition pack at
  `stems/flip_chops_v1/`. Caveat: `downbeat_confidence` 0.02 (grid internally consistent,
  bar-1 phase may shift — audible check at GATE C).
- W2 scaffolding: `drums.py` (one-shot mining + fallback classifier + drill grammar) +
  `bass808.py` (mono-legato glide sub + transient layer + ducking). 15 tests.
- W3/W4 scaffolding: `assemble.py` (bounded-stretch grid placement, single-pass
  pedalboard) + `relay.py` (gap+energy-dip phrases, beat-fraction preserving map). 13 tests.
  Commit `7b3f625`.
- Records: CHANGELOG #060, STATUS.md Flip lane row, `[flip]` extra in pyproject.

Remaining: finish chain (karaoke+dereverb), `ogcm-drumsep` on drums.wav, bleed evidence JSON,
GATE C audition on v2 stems → chop pick → W2 one-shot mining on DrumSep stems → W3 dual-grid
renders → W4 relay per grid → W5 master + blind A/B.

## Wave 2 — Beat build (blocked: needs W0 outputs + GATE C pick)

## Wave 3 — Vocal re-lay + master (blocked: needs wave 2; user gate)
