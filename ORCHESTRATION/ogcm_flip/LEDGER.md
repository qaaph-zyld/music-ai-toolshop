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

Canonical spec: `D:\Projects\.workspace_archive\plans\ogcm-flip.spec.md` (user-adjudicated
2026-09-27). `ogcm-flip-synthesis.spec.md` and `ogcm-flip-rebuild.spec.md` are SUPERSEDED
(banners on disk) — kept as reconciliation/analysis records. Implementation plan:
`C:\Users\015ZCS\.devin\plans\plan-87307e9665c424d6.md` (mirrored
`.workspace_archive\plans\ogcm-flip-research-first-rebuild.md`).

Adversarial review applied (target: plan) → **approved-with-fixes**, all medium findings fixed
in plan. Report: `D:\Projects\.workspace_archive\reviews\2026-09-27_1629_ogcm-flip-plan.md`.

**User gate picks (differ from earlier frozen defaults):**
- Tempo: **build BOTH grids** — 178.2 written / 89.1 felt AND 133.65 — blind-pick at W5.
- Key direction: **Down / UK-dark** — per-chop landing keys reported (no global-key assumption).
- Dependencies: **authorized** — audio-separator models pre-seeded to `~/.cache/toolshop-models`.
- Code location: **`toolshop/flip/`** subpackage.

## Wave 1 — implementation W0+W1 (executed by polite-piranha; continued by devin session 2026-09-27)

- W0 registry: `stem_models.py` extended — MelBand RoFormer Kim bleedless
  (`mel_band_roformer_kim_ft2_bleedless_unwa.ckpt`), anvuew dereverb, MDX23C DrumSep;
  `ogcm-flip` chain preset + `ogcm-drumsep` preset; dynamic CLI preset choices.
  Cache verified complete, zero orphans. Commit `eecfd0b`.
- W0 run DONE: full-track `ogcm-flip` chain → `stems/v2/` — 3 passes ≈52 min CPU
  (Kim 18.07 / karaoke 17.42 / anvuew dereverb 16.07 min on the 4.95-min track).
  Incident: registry `output_patterns` imagined `(Vocals)`/`(Instrumental)` — real
  emissions are `(other)`/`(vocals)` and `(noreverb)`/`(reverb)`; bed orphaned,
  lead claimed the reverb tail. Fixed patterns + manifest repaired in place (audio
  was always correct); committed by continuation session → `50f5a25`.
- Bleed evidence `stems/v2/bleed_evidence.json`: `vocal_active_env_corr_v2` 0.0,
  `vocal_silent_rms_ratio_v2` 0.0 vs legacy 0.01015, `reverb_tail_peak_ratio` 0.124
  (modest ambience removal — not hollowed).
- DrumSep DONE 18:48 (~59 min wall): `stems/v2_drums/` — kick/snare/hh/crash/ride/toms
  FLACs; kick+snare+hh carry real signal, toms/ride/crash sparse (true to source).
  Manifest maps kick/snare/toms only — other pieces present as extra outputs.
- W1 chops: `toolshop/flip/chops.py` + `toolshop flip chops` CLI. **Gating pack =
  `stems/flip_chops_v2/`** (24 candidates on the v2 bed, top 0.616 vs 0.555 legacy;
  B×7 segment-class discrimination vs collapsed A×8; tonal centers F#m/Bm/D).
  Caveat: `downbeat_confidence` 0.02–0.08 — bar-1 phase by ear at GATE C.
  (v1 pack on legacy bed superseded.)
- W2 scaffolding: `drums.py` (one-shot mining + `piece_hint` + fallback classifier +
  drill grammar) + `bass808.py` (mono-legato glide sub + transient layer + ducking).
- W3/W4 scaffolding: `assemble.py` (bounded-stretch grid placement, single-pass
  pedalboard) + `relay.py` (gap+energy-dip phrases, beat-fraction preserving map).
  Commit `7b3f625`. 59 tests claimed by wave-1 handoff; stem tests re-verified 27 ✓
  by continuation session.
- Records: CHANGELOG #060, STATUS.md Flip lane row (updated to v2-complete), `[flip]`
  extra in pyproject.

- Continuation-session prep (pick-independent, done while GATE C awaits user
  audition): `scripts/ogcm_mine_oneshots.py` → `stems/flip_kit/` 18 one-shot
  WAVs + `kit_manifest.json` (6 pieces × 3 reps); `scripts/ogcm_transcribe_lead.py`
  → `stems/flip_relay/lead_transcript.json` (911 words, en p=1.00, mean_p 0.812,
  115.3 s). GATE C staged: `stems/flip_chops_v2/GATE_C.md` + `audition/` loops.

Remaining: GATE C audition on `flip_chops_v2` pack (chop set + pitch arm + hook) →
W2 kit verify + 808 root config → W3 dual-grid renders (178.2 + 133.65) →
W4 relay per grid (transcript + grid source cached) → W5 master + blind A/B (GATE F).

## Wave 2 — Beat build (blocked: needs W0 outputs + GATE C pick)

## Wave 3 — Vocal re-lay + master (blocked: needs wave 2; user gate)

## Megaplan execution — native subagent dispatch (started 2026-09-28)

Config: `waves_megaplan.json` · Manifest: `prompts/subagent_dispatch.json` · Plan: `D:\Projects\.workspace_archive\plans\ogcm-flip-megaplan.md` (supersedes remaining-wave prompts where they conflict).

Dispatch mode: **native subagents** (`run_subagent`, profile `wave-implementer`, model `swe-2-max`, sequential — shared git repo). Waves m1→m5; user gates at m2 (GATE C2 audition) and m5 (GATE F blind pick).

| Wave | Status | Agent | Artifact | Notes |
|------|--------|-------|----------|-------|
| m1 W-1 fixes | done | A (wave-implementer) | `wave_m1/agent_a_w1_fixes_handoff.md` | commit `5edfa4e`; F1 patterns + manifest 6/6, F2 source-felt relay, F5 docstring; 38 targeted + 1328 full suite pass; A29 kit audit PASS (all peaks ≥ MIN_PEAK); transcript sane |
| m2 W1′ spike → GATE C2 | done — pick made | B | `wave_m2/agent_b_bed_spike_handoff.md` | commit `69bb637`; pip `--no-deps basic-pitch mir_eval` OK; ONNX predict verified on real 10s region (67 events); 3 GATE-C regions transcribed (67/68/170 raw notes); `bed_lanes.py` + `ogcm_bed_spike.py` + 19 tests pass; GATE C2 pack 22 files (Lane A×4 + B×6 + C×12) × 2 grid arms, LU spread 0.0 LU, no clipping, bijection OK; audio pack NOT committed (gitignored) |
| **GATE C2 pick (2026-09-28)** | resolved | user | `stems/flip_bed_lanes/manifest.json` | picked bed_004 + bed_011 + bed_021 → **arm felt_89 (178.2w) = Lane B** interpolated `region_63_66` epiano Dm; **arm triplet_133 (133.65) = Lane C** motifs `motif_dm_1` (pad, Dm) + `motif_csm_1` (epiano, C#m) as section alternates; **hook = backing_vocals**; build both arms; Lane A chops not used |
| m3 W2+W3 build | done | C | `wave_m3/agent_c_build_handoff.md` | kit audit → `kit_audit.json` (cymbal weak, fallback declared); 808 retune (140 ms glide, m3/P4, 2–3 slides/4 bars on kicks); F5 true 2-bar cycle; NEW `arrange.py`; renders `beat_felt_89.wav` (48 bars) + `beat_triplet_133.wav` (72 bars, LCM-12 supercycle) — clips 0, grid PASS, mono<120 Hz PASS; 80 flip tests pass |
| m4 W4 relay | pending | D | — | blocked on m3 |
| m5 W5 master → GATE F | pending | E | — | user blind-pick, then resume agent for closeout |
