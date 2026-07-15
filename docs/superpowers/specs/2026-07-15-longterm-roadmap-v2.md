# Music-AI-Toolshop — Long-Term Roadmap v2: The Toolshop Suite

**Date:** 2026-07-15
**Status:** Strategy approved in session; supersedes phase table of `2026-07-11-strategic-roadmap-v1.md` (thesis, constraints and defect log there remain valid; Phases 0–1 completed 2026-07-11 → 2026-07-14).
**Execution model:** one milestone ≈ one IDE-agent session, bootstrapped via the framework (session_brief → plan → approval → execute → handoff). Detailed per-milestone plans go in `docs/superpowers/plans/` as they are picked up.
**Companion spec:** `2026-07-15-oss-integration-map.md` — verified OSS technology per tool (integrate vs wrap vs build), eval harness, license ledger. Consult it before implementing any T1–T7 milestone.

---

## 0. Locked Strategic Parameters (user decisions, 2026-07-15)

| Decision | Value | Consequence |
|---|---|---|
| Compute | **CPU-only** (no GPU purchase, no cloud) | Every ML feature must be CPU-realistic; heavy work = overnight batches; GPU-dependent tools go to the Parked Lane. Revisit triggers in §6. |
| Scope | **Music-first, reusable core** | Roadmap is music; `core` layer (batch, manifest, catalogue, doctor, config) stays domain-neutral for later corporate reuse. No corporate phases here. |
| Packaging | **Tool suite, one repo** | Monorepo; tools are separately versioned packages sharing `core`; each tool gets its own CLI verb + optional tray/EXE launcher (Mastering pattern). Split-out later remains possible. |
| CrhymeTV backlog (82 tracks) | **Analyze-only now** | Add `--no-stems` to the batch runner; complete 222/222 analysis overnight; stems backfilled per-track on demand. |

## 1. North Star

**A local-first, CPU-realistic suite of music production tools — deconstruct any track, understand it as data, recreate and master new ones — used every day and compounding via the catalogue.**

The suite pipeline (unchanged): `INGEST → SEPARATE → ANALYZE → DOSSIER → CREATE → MASTER → CATALOGUE`.

Definition of "a tool" (the Mastering Toolshop bar): launchable by itself, profile/preset-driven, produces verified artifacts with manifests, honest about time cost, covered by tests + doctor checks.

## 2. The Portfolio (target structure)

```
Music-AI-Toolshop (monorepo)
├── toolshop/core        # T0 PLATFORM: config+data-root, resumable batch engine, manifests,
│                        #    model registry, doctor, catalogue DB, UTF-8 guards  [domain-neutral]
├── toolshop/stems       # T1 STEM TOOL         — v0.4 shipped; → v1.0 CPU-optimized
├── toolshop/dossier     # T2 RE / DOSSIER TOOL — recipe v1 shipped; → dossier v2
├── mastering_tool/      # T3 REMASTERING TOOL  — mature submodule; tray EXE; own lane
├── toolshop/vocal       # T4 VOCAL LAB         — voice-FX detect + cleaning shipped; + whisper lyrics
├── toolshop/lib         # T5 LIBRARY INTELLIGENCE — the data-science tool over all catalogues
├── toolshop/create      # T6 CREATION BRIDGE   — dossier → Suno seeds; recreate-and-compare
├── toolshop/forge       # T7 SAMPLE FORGE (new) — stems+grid+sections → labeled loop/one-shot packs
└── PARKED: open_DAW (long horizon) · Voicebox (GPU-gated, archive) · ACE-Step local gen (GPU-gated; Suno covers generation)
```

Current CLI verbs stay (`toolshop stems|track|voice|clean|yt|suno|doctor`); the package reorganization is gradual (H1-M5), never a big-bang rewrite.

## 3. Tool Charters — long-term goal per tool, broken into milestones

### T0 Core (platform)
**Goal:** every tool stands on the same resumable-batch, manifest, registry, catalogue and doctor machinery; a new tool costs days, not weeks.
- v1 (H1): extract `batch.py` pattern into documented core API; config module (data-root, ffmpeg, model cache paths); doctor extended with disk watchdog + backup-age check.
- v2 (H3): catalogue DB (SQLite) as shared service; manifest schema versioned; plugin-style tool registration.

### T1 Stem Tool
**Goal:** any wav/mp3 (file or folder) → correct stems in ≤10 min/track fast preset on this CPU; overnight for HQ/batches.
- v0.4 ✅ (2026-07-14): registry, presets, Demucs adapter, manifests, batch, 47 tests.
- v0.5 (H1): Demucs e2e verified; model cache complete + doctor clean; **CPU optimization pass** — onnxruntime thread tuning, segment/overlap tuning, evaluate lighter MDX variants; publish measured benchmark table; target karaoke ≤10 min/track (from ~30).
- v1.0 (H2): on-demand single-track UX polish (`--eta`, progress); stems-backfill command reading catalogue gaps; quality listening notes per preset.

### T2 Reverse-Engineering / Dossier Tool
**Goal:** one command → **track dossier**: structure timeline, key/mode (trustworthy), per-section chords, beat grid, loudness/premaster profile, timed lyrics, instrument hints, effect fingerprint, Suno seed. The dossier is THE unit of knowledge the whole suite consumes.
- v1 ✅: recipe.md pipeline, 140 tracks done.
- v1.1 (H1-M1): `--no-stems` mode; finish CrhymeTV 222/222 analyze-only; regenerate catalogue.
- v2.0 (H2, milestone-per-line):
  - structure segmentation via CPU-cheap self-similarity/novelty (librosa/MSAF approach; no Demucs-dependent allin1)
  - Krumhansl-Schmuckler key/mode replacing the bogus heuristic (fix "G major vs Gm" defect); chords with confidence, grouped per section
  - beat grid + downbeats export (JSON + MIDI click)
  - loudness/dynamics/spectral profile aligned with `mastering_tool` PREMASTER_ACCEPTANCE_SPEC
  - lyrics via **faster-whisper** (CTranslate2 int8, CPU-viable) on vocal stem when present, else full mix
  - `dossier.json` schema v2 + recipe.md v2 renderer; regenerate all 222 CrhymeTV + PapaPedro dossiers from cached analysis
- v2.1 (H3): melody/bass MIDI via basic-pitch ONNX (CPU); ingest-from-URL one-shot (`toolshop dossier <file|yt-url>`).

### T3 Remastering Tool (mastering_tool)
**Goal:** stays the flagship finisher; gets fed by dossiers instead of manual guesswork.
- Now (H1-M4): finish pending e2e verification of `german_drill` via tray EXE (open item from 2026-07-13 handoff).
- Bridge v1 (H3): dossier → premaster acceptance check + reference/profile suggestion (reuse CLAP matcher); `toolshop master <track>` passthrough into the pipeline.
- Long term: keep WSL/bash guts while they work; port stages to cross-platform Python only when a stage actually hurts; sync CATALOGUE/REFERENCE_LIBRARY into T5.

### T4 Vocal Lab
**Goal:** everything vocal: detection (12 FX detectors ✅), cleaning (✅), transcription, alignment, QC.
- v1 (H2): `toolshop voice transcribe` via faster-whisper (model size configurable, int8 default); timed-lyrics artifact shared with T2.
- v1.1 (H3): lyrics↔beat-grid alignment (bars/phrases); vocal QC bridge to mastering_tool `vocal_doctor`/`vocal_qc`.
- Parked: Voicebox synthesis (GPU) — archive the vendored fork out of the repo, keep an ADR pointing to upstream.

### T5 Library Intelligence (the data-science tool)
**Goal:** every track you touch — 2,633 Suno songs, 222 CrhymeTV, PapaPedro beats, your own releases — queryable and analyzable; taste and catalogue become data assets.
- v1 (H3): SQLite catalogue ingesting dossiers + Suno metadata + CrhymeTV catalogue; `toolshop lib find --bpm 88-96 --key Gm --effect reverb --min-duration 120`; `toolshop lib stats` (BPM/key/effect distributions).
- v1.1 (H3): taste-profile v2 (rebuild the 2025-12 analysis on the full corpus, automated as a report); playlist/export generators.
- v2 (H4): similarity search via CLAP embeddings (retrieval on a personal-size library is CPU-fine; embeddings computed overnight); "find me references like X" for mastering and creation.
- Long term: this is the layer with direct **corporate-skill crossover** (SQL, reporting, dashboards) — same patterns as PVS/Efficiency reports, personal domain.

### T6 Creation Bridge
**Goal:** close the loop: dossier → generation brief → Suno output → compare against target dossier → iterate.
- v1 (H3): seed generator from dossier (extend existing SUNO_PROMPT_TEMPLATES + suno_prompts.md work); brief includes structure, BPM/key, effect fingerprint, reference lyrics themes.
- v1.1 (H3/H4): **recreate-and-compare** — run the new Suno track through T2, diff dossiers (tempo/key/structure/loudness deltas) = objective "did we hit the target?" score.
- Adjacent products: MAirina_Tucc rimer (Serbian rhyme tool) and lyrics_research stay separate UIs; T6 consumes their outputs (rhyme schemes, lyric corpora) as inputs to briefs.
- Parked: ACE-Step local generation (GPU). Suno is the generation engine of record.

### T7 Sample Forge (new, CPU-cheap, high daily value)
**Goal:** any analyzed track → labeled sample material: section loops (8-bar chorus loop, intro riser), drum one-shots from stem onsets, BPM/key-tagged filenames ready for the DAW.
- v1 (H3): slice stems by dossier sections + beat grid → loops; onset-based one-shot extraction from drum/percussion stems; naming convention `<key>_<bpm>_<section>_<n>.flac` + pack manifest.
- v1.1 (H4): pack presets ("remix kit", "drum kit", "acapella kit"); auto pack-README.

### Parked Lane (explicit non-investment until §6 triggers fire)
- **open_DAW** — long-horizon; minimal eventual integration = "open dossier as session template". No sessions allocated in H1–H3.
- **Voicebox** — GPU-gated; archive from repo.
- **ACE-Step local gen** — GPU-gated.

## 4. Horizons (goals → session-sized milestones)

### H1 — Finish & Solidify (now → ~4 weeks) · theme: *zero loose ends*
| # | Milestone | Size | Exit evidence |
|---|---|---|---|
| M1 | `--no-stems` batch mode + run 82 CrhymeTV analyze-only + regen catalogue | 1 session + overnight | batch_status 222/222; catalogue.md refreshed |
| M2 | Demucs e2e smoke (htdemucs download + 4-stem run) + complete model cache + doctor clean | 1 session | doctor: 0 warnings; manifest from real run |
| M3 | Stems CPU-optimization pass (ORT threads, segments, lighter variants) + benchmark table | 1–2 sessions | measured table in README; karaoke ≤10 min/track or documented best-achievable |
| M4 | Mastering e2e: full `german_drill` run via tray EXE, capture deliverables | 1 session | `master/` + `verification/` artifacts, handoff note |
| M5 | Suite reorganization: core/tool package layout, AGENTS.md, register project in meta-layer project table + KB entry | 1–2 sessions | imports/CLI unchanged (tests green); AGENTS.md live; session_brief detects project |
| M6 | Data governance: backup job for D:\MusicData + catalogue DBs; doctor disk/backup-age checks | 1 session | restore-tested backup; doctor reports backup age |

### H2 — Dossier v2 (~weeks 4–10) · theme: *the RE tool becomes trustworthy*
Milestones = the six T2-v2.0 bullets above, one session each, ending with full 222-track dossier regeneration + catalogue v2 schema. Plus T4-v1 (faster-whisper transcribe) which T2 consumes.

### H3 — Intelligence & Integration (~weeks 10–18) · theme: *tools start feeding each other*
Order: T5 Library v1 → T2 v2.1 one-shot ingest → T6 Creation Bridge v1 → T3 Mastering bridge v1 → T7 Sample Forge v1 → T6 v1.1 recreate-and-compare.

### H4 — Surfaces & Compounding (~months 5–8) · theme: *lower friction, widen reuse*
Local dashboard (thin sibling repo importing the suite — respects "no web UI in core" rule); SendTo/watch-folder + toolshop tray launcher; CLAP similarity search (T5 v2); Sample Forge presets; evaluate extracting `core` for corporate reuse; revisit Parked Lane + compute decision.

## 5. Cross-Cutting Policies
1. **CPU-realism rule:** no ML feature merges without measured min/track on this machine in the PR/handoff; overnight is the unit for >15-min work; interactive commands must offer a fast preset.
2. **Data governance:** code in repo, audio/artifacts under `D:\MusicData\toolshop\` (env-var `TOOLSHOP_DATA_DIR`); FLAC default; backups per H1-M6 (disk is currently comfortable: ~250 GB free post-cleanup).
3. **Quality bar:** TDD on adapters; doctor as merge gate; UTF-8 round-trip test with `Täterprofil ćevap.mp3`-style names; every batch resumable with status JSON.
4. **Framework integration:** every session starts from a handoff + session_brief and ends with session_end + handoff; milestone plans live in `docs/superpowers/plans/`; CHANGELOG Answer-format maintained.
5. **Docs honesty:** PROJECTS_INDEX and README updated in the same session as the change, never later.

## 6. Decision Gates & Revisit Triggers
- **G1 compute (LOCKED: CPU-only, 2026-07-15).** Revisit if any fires: (a) stem backlog >50 tracks needed within a week; (b) T6 recreate-loop becomes daily practice and Suno iteration cost dominates; (c) a Roformer-quality vocal isolation is required for a release; (d) hardware gift/windfall. Then: cheapest path is a used 12 GB CUDA card; cloud burst is the no-hardware alternative.
- **G2 web UI:** thin sibling repo, earliest H4.
- **G3 Voicebox:** archive out of repo in H1-M5 (ADR + upstream link).
- **G4 open_DAW:** parked; formal review at H4 close.

## 7. Risks
| Risk | Mitigation |
|---|---|
| CPU optimization (M3) underdelivers; stems stay ~30 min | Accept overnight-only batching; per-track on-demand uses karaoke/fast presets only; revisit trigger G1(a) |
| Dossier v2 accuracy disappoints (chords/structure on dense mixes) | Confidence fields everywhere; per-section human-checkable recipe; treat as hints not truth; listening spot-checks in every milestone |
| Suite reorg (M5) breaks working CLI | Tests-first, alias old verbs, no big-bang moves |
| mastering_tool WSL dependency rots | e2e run (M4) becomes a doctor-checkable smoke; port stages only on pain |
| Solo-maintainer drift / abandoned milestones | Handoff discipline + this roadmap as the single backlog; one milestone per session, no kitchen sinks |

## 8. Next Three Sessions (concrete)
1. **H1-M1**: implement `--no-stems`, launch overnight analyze-only batch for the 82 tracks, regenerate catalogue. (Plan: `plans/2026-07-15-h1m1-crhymetv-analyze-only.md` — to be written by the executing agent.)
2. **H1-M2**: Demucs e2e + model cache + doctor clean.
3. **H1-M4**: mastering `german_drill` e2e via tray EXE (independent of M2/M3; can run any evening).
