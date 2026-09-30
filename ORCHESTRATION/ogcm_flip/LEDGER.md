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
| m4 W4 relay | done | D | `wave_m4/agent_d_relay_handoff.md` | lattice-anchored phrase relay; identical schedule both arms PASS; median anchor correction 0.00 ms (all 20 phrases floated — none ≤30 ms of lattice, syncopation kept); 20 lead phrases + 77 backing strips; hooks = backing strips in hook_sections (3/6 strips); nearest-hit medians 5.4/18.7 ms; clips 0; coverage limit: 3/20 + 8/20 phrases fit the 65.6/130.3 s renders (full placements emitted) |
| m5 W5 master → GATE F | **rejected at gate** | E | `wave_m5/agent_e_master_handoff.md` | `flip/master.py` (F9: −14 LUFS ±0.3 + pedalboard.Limiter → TP≤−1 dBTP, boost_est loop) + `ogcm_master.py`; unity mixes (felt_89 clip-guard 1.058→0.99); masters −13.97/−14.00 LUFS, TP −3.63/−3.72 dBTP; GATE F pack `stems/flip_final/audition/` ADR-009 verified (0.0 LU spread, bijection PASS); club-9 variants PASS (−9.29/−9.07) |
| **GATE F verdict (2026-09-29)** | **both arms rejected** | user | `stems/flip_sample/` | user: "both flips sound terrible, don't understand the idea." Diagnosis: fragment coverage (3/20 + 8/20 phrases), placeholder synth timbres, no real record audio in bed. **PIVOT**: new deliverable = Suno-ready melodic *sample* (west-coast sound, chords+melody, simple, no full beat); keep synths but polish. Closeout-resume on m5 cancelled; GATE F audio kept on disk (never-delete rule) |
| s1 Suno sample | dispatched (in-process — no subagent tool this session) | orchestrator | `stems/flip_sample/` | NEW `toolshop/flip/sample_voices.py` (Rhodes/warm-pad/G-funk lead/sub voices, derived Dm7 harmony, register split, loop fold, pedalboard chain) + `scripts/ogcm_sample.py` + `tests/test_flip_sample.py`; GATE S pack: 5 variants A–E (E = real chop REF), −16.0 LUFS each, 0.0 LU spread, TP≤−1, no clips |
| s3 Suno sample — simple recognizable motif | done (O1–O4 green) | devin (in-process) | `stems/flip_sample/audition_s3/` | Spec `expected_output_ogcm_suno_sample_simple_recognizable_melody_20260929_220703.md`; segment = **user-picked instrumental 54–67s** (fresh `region_54_67_cleaned_Dm.mid`: 118 raw → 69 cleaned notes via `ogcm_transcribe_segment.py`), chop ref = `ref_slice_54_67.wav` (bed slice, doubled 5-bar, already D-centered → 0 st). NEW in `sample_voices.py`: `quantize`, `extract_motif` (most-repeated 2-bar top-line cell → ≤8 grid-quantized Dm notes, monophonic), `tile_motif`, `answer_motif`, `render_simple_lead` (plain sine+0.15·2nd). `ogcm_sample.py` now argparse (`--pack/--region/--chop/--shift`); NEW `verify_sample_pack.py` + `check_audition_serve.py`; 8 new motif tests. Pack: 5 files 13.5–26.9 s, −16.0 LUFS each (spread 0.0), TP ≤ −3.9 dBTP, no clips, `verification.json` pass=true; serve check all 200 + linked |
| s4 Suno sample — recognizable riff (key-snap fix) | rendered (O1′–O5 green; ear-test pending) | A (wave s4a) | `stems/flip_sample/audition_s4/` | **Root cause of S3 reject (measured):** `region_54_67_cleaned_Dm.mid` was `cleanup(root="D")` scale-locked from **F# minor** material — C#→D, F#→F, G#→G, B→Bb rewrote every riff interval; the S3 "already D-centred → shift 0" inference was circular (drawn from snapped MIDI). Audio-side chroma check on `instrumental.wav` 54–67 s: **F# minor r=+0.367** beats D minor r=+0.039; `estimate_key(raw)` = F#m r=+0.797. S4 reads `region_54_67_raw.mid`, **transposes −4** (F#m→Dm exactly, never snaps). NEW in `sample_voices.py`: `GRID_16TH_S`, `transpose`, `estimate_key` (Krumhansl, numpy), `fold_octaves`, `extract_riff` (register floor → top_line → fold → FULL-2-bar-cell winner by onset-slot+pc match → 16th grid → ≤16 notes by velocity → legato fill capped 1 beat), `riff_stats`; `extract_motif` untouched (s3 reproducible). `ogcm_sample.py`: `--pack s4` + `--transpose` (default −4), `_render_s3(chords=)`, `_s4_variants` (s4_01 sine / s4_02 EP / s4_03 oct / **s4_04 native F#m** / s4_05 REF chop `ref_slice_54_67.wav` −4). NEW `scripts/check_riff.py` (O5) + key-estimate guard in `ogcm_transcribe_segment.py`. Riff: 13 notes, 2.41 n/s, 97% coverage, max leap 10 st, snapped 0; chords Dm7–Bbmaj7 alternating (from segment bass). Spec `expected_output_ogcm_suno_sample_s4_20260930_212015.md`. S2 regions likely snapped too (same cleanup path) — reported, not fixed |
| s5a GATE S5 — wail finder + whine probe + dotted-8th sync | done (O1″–O5 green; **G1 user gate pending**) | A (wave s5a) | `wave_s5a/agent_a_s5a_handoff.md` · `stems/flip_sample/audition_s5/` (Suno-safe, synthesis only) · `audition_s5_stems/` (LOCAL ID ONLY — source-audio slices, never for Suno) | CHANGELOG #074. NEW `scripts/ogcm_stem_audition.py`: 54–67 s window of htdemucs_6s guitar/other/vocals/bass + v2 backing-vox residue → −20 LUFS clips; pyin metrics + documented `wail_score` → `stem_ranking.json`; whole-song timelines (top-2 by score, pyin hop 512 to fit the 6 min budget) → `timeline_<stem>.json`. `sample_voices.py`: `DOTTED_8TH_S` (0.505 s) + `west_coast_chain(lead_delay_s=0.375)` (default unchanged; S2–S4 reproduce — S4 re-render to scratch byte-identical: 5 WAVs + manifest + verification). `ogcm_sample.py --pack s5` → `s5_00_riff_whine` only (S4 riff on `render_gfunk_lead`, dotted-8th echo, `source_audio_in_output: false`). 49 flip_sample tests / 97 flip suite pass. The ranking is a heuristic for where to LISTEN — it does not identify the wail; the user's ear decides at G1 |
