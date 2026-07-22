# Long-Term Goals — 12-Month Full-Studio Horizon

**Date:** 2026-07-22 · **Owner:** orchestrator · **Status:** **v1.0** (finalized 2026-07-22 evening
after the landscape research report landed at `docs/superpowers/research/2026-07-22-full-studio-oss-landscape.md`;
research verdicts in §8, residual gaps listed there — none block the goal set).
**Relationship to existing docs:** this sits ABOVE `2026-07-15-longterm-roadmap-v2.md`, which remains
the execution backlog of record for horizons H1–H4. Nothing there is invalidated. This doc extends the
horizon to 12 months and adds what roadmap v2 does not cover: the missing studio domains (composition,
synthesis, mixing, vocal production), the 3-device fleet, and an explicit deferred GPU tier with an
upgrade path to stronger machines.

---

## 1. Mission (by 2027-07)

**A local-first, open-source-built, complete music production studio toolkit** covering every stage:

```
IDEA → COMPOSE → SOUND-DESIGN → GENERATE/RECORD → ARRANGE → MIX → MASTER → RELEASE → CATALOGUE → LEARN
```

- Runs on the current 3-machine CPU fleet (all 16 GB RAM; i7-4770 class ×2, i5 9th-gen ×1).
- Everything CPU-realistic now; GPU-dependent capabilities live on a documented **deferred shelf**
  with per-item hardware requirements, so acquiring stronger machines is an informed unlock, not a bet.
- Built by integrating existing OSS first (adapter pattern), building only glue, domain logic, and
  what doesn't exist (per `2026-07-15-oss-integration-map.md` §1 policy — unchanged).
- Used daily on real material (Serbian/Balkan drill-trap + pop cohorts, German rap) and compounding
  through the catalogue and corpus assets.

## 2. Ground truth — what exists today (verified 2026-07-22)

| Asset | State |
|---|---|
| T0 Core platform | v1: pinned 3.11 venv, resumable batch, manifests, doctor, backup engine (#019), 349+ tests green locally |
| T1 Stems | v0.4: Demucs adapter, presets, registry; CPU opt (M3) pending; ~30 min/track default |
| T2 Dossier/RE | v1: 222-track CrhymeTV catalogue complete; v2 accuracy upgrades (key, structure, chords, timed lyrics) = H2, not started |
| T3 Mastering | Mature daily product (tray EXE, submodule); M4 e2e verification pending |
| T4 Vocal Lab | 12 FX detectors + cleaning shipped; transcription pending (H2); known bug: `min_silence` debt 1c |
| T5 Library Intelligence | Flagship data asset: lyrics.db 742 songs / 36,572 lines, rhyme fingerprint **independently verified** (Cohen's d=1.18 pop vs drill_trap); L3 themes in flight; 2,633 Suno tracks + catalogues await ingestion |
| T6 Creation Bridge | Corpus + briefs groundwork; rimer/brief-generator/scorer = L5 |
| T7 Sample Forge | v1 partial: section-consuming remix + spec naming shipped; auto section detection deferred to H2 |
| T8 Restore "Track Doctor" | Strategy adopted; E1 diagnose plan ready, not started |
| T9 Session Bridge | Strategy adopted; E5 universal pack + E6 Ableton `.als` writer decided (D1), not started |
| Parked | open_DAW, Voicebox, ACE-Step, real-time plugin authoring, RVC/so-vits |
| Infra | Tier-1 backup C:\Backups\toolshop (same physical box — NOT true DR); CI billing-locked → local pytest is the gate; espeak-ng, ffmpeg portable, WSL sidecar pattern proven |

Corpus/data assets (all under `D:\MusicData\toolshop\`): 749-song lyrics corpus (742 in DB),
222-track dossier catalogue, 2,633 Suno songs, PapaPedro beats, mastering reference library.

## 3. New strategic facts (2026-07-22, user decisions)

1. **Fleet of 3 devices**, approximately equal capability (16 GB RAM each; this box = i7-4770 +
   GT 640 2 GB; one i5 9th-gen). Overnight batch throughput can roughly triple **if** we build a
   simple job-distribution + data-sync layer. Also finally enables **true cross-machine DR backups**
   (current Tier-1 backup lives on the same physical box as the data).
2. **Stronger machines are planned later.** GPU-gated tools stay deferred but get a maintained
   shelf doc (what each unlocks, minimum spec), so the future purchase is targeted.
3. **Scope widens from "tool suite" to "full studio":** composition, synthesis/sound design,
   mixing, and vocal production (pitch/time correction) enter scope as research-gated lanes.
4. **Research-first:** no new domain is adopted without the landscape report (see §8) — same
   discipline that produced the OSS integration map.

## 4. Studio coverage matrix (the gap map this plan closes)

| Studio function | Today | 12-month target |
|---|---|---|
| Ingest / acquisition | ✅ yt, Suno downloader | keep |
| Analysis / reverse-engineering | 🟡 v1 heuristics | ✅ trustworthy Dossier v2 (key, structure, chords, timed lyrics, confidence fields) |
| Stem separation | ✅ working, slow | ✅ ≤10 min/track fast preset or documented best-achievable; fleet-parallel batches |
| Lyric / writing intelligence | ✅ flagship (verified fingerprints) | ✅ L3–L6 complete: themes, artist fingerprints, gap reports vs pro corpus, rimer DB, brief generator, draft scorer, German lane |
| Composition & MIDI (chords, melodies, drums, arrangement) | ❌ none | 🆕 v1 lane: research-selected OSS + own pattern-mining over dossier corpus |
| Synthesis / sound design (instrument palette) | ❌ none | 🆕 v1: headless-renderable open synth + SFZ/soundfont palette, renderable from MIDI via CLI |
| Sampling | 🟡 forge v1 partial | ✅ forge v1.1: auto-sections, pack presets |
| Vocal production (correction, comping, harmony) | 🟡 detect+clean only | 🆕 pitch/time correction chain (research-gated); transcription + alignment shipped |
| Mixing (multitrack, buses, chains) | ❌ (Airwindows via mastering only) | 🆕 chains core (E2) grown into reusable YAML mix-chain tool with plugin suite adoption |
| Restoration | 📝 planned | ✅ T8 E1–E3 daily tools (diagnose → treat presets → verify) |
| Mastering | ✅ flagship | ✅ + dossier bridge + matchering reference-match mode |
| Generation | ✅ external (Suno) | ✅ Suno remains engine of record; local-gen models on the GPU shelf with unlock specs |
| DAW handoff | ❌ | ✅ T9: universal pack + `.als` template writer ("Live 12 opens a generated 2-track session") |
| Library intelligence / search | 🟡 lyrics only | ✅ full-corpus catalogue: CLAP similarity + text search, chromaprint dedup, DuckDB/Datasette dashboards |
| Fleet / distributed batches | ❌ | 🆕 3-machine overnight batch grid + data sync |
| Backup / DR | 🟡 same-box only | ✅ true cross-machine DR via fleet + doctor checks |

## 5. The 12-month goal set

- **G1 — Trustworthy analysis core.** Close H1 remnants (M2, M3, M4, M5) and ship Dossier v2 (H2)
  with the eval harness proving accuracy. Everything downstream consumes dossiers; this is the keystone.
- **G2 — Closed creation loop.** Lyric Intelligence L3–L6 shipped; dossier → brief → Suno →
  recreate-and-compare diff scoring; flow analyzer (the genuinely novel build) operational on
  whisperX timings × beat grid.
- **G3 — Studio breadth wave (research-gated).** Composition/MIDI lane, synthesis palette,
  mix-chains tool, and vocal correction chain — adopted per the landscape report's verdicts,
  one integration per session, adapter + measured cost each.
- **G4 — Session Bridge shipped.** E5 universal pack (stems + marker MIDI + click) and E6 `.als`
  template writer for Ableton Live 12; FL 21 served by the universal pack.
- **G5 — Fleet operational.** A deliberately simple 3-machine job distribution layer (pick per
  research WS7), LAN data sync, and **true DR**: nightly cross-machine backup of MusicData +
  catalogues + repo mirrors. Kill the same-box backup caveat.
- **G6 — Library intelligence at full scale.** All corpora ingested into one catalogue; CLAP
  embeddings overnight batch; similarity + zero-shot text search; chromaprint dedup; taste-profile
  v2 as an automated report.
- **G7 — Restoration + chains as daily tools.** T8 E1→E3 and E2 chains core in weekly real use on
  incoming material (yt-rips, voice notes, Suno preps).
- **G8 — Platform & discipline hardening.** `toolshop closeout` mechanical gate (dirty-tree/unpushed
  fail), version-controlled pre-push hook, model mirror + checksums, doctor as the single health
  surface, CI billing decision resolved or local-gate formalized.
- **G9 — GPU-tier readiness.** Maintained deferred shelf (from research WS6/WS8): per capability —
  minimum spec, expected quality, license. When stronger machines arrive, onboarding is a checklist,
  not a research project.
- **G10 — Compounding daily use.** The suite is the default way tracks get made/finished here;
  catalogue rows and corpus size are the KPIs; docs-honesty and spot-check verification rules stay
  in force.

## 6. Quarter mapping (2026-08 → 2027-07)

| Quarter | Theme | Contents |
|---|---|---|
| **Q1** Aug–Oct 2026 | *Keystone + hygiene* | H1 close (M2/M3/M4/M5), Dossier v2 (H2) complete, L3–L4 lyric phases, E1–E2, closeout gate mechanized (G8 start), fleet pilot: pick + prove job queue on 2 machines, first cross-machine backup |
| **Q2** Nov 2026–Jan 2027 | *Integration + breadth wave 1* | H3 (T5 Library v1, T6 briefs v1, mastering bridge, forge v1 full), L5 apply-phase (rimer/brief/scorer), first studio-breadth adoptions from research (likely mix-chains + composition/MIDI v0), fleet in production for all overnight batches, true DR routine |
| **Q3** Feb–Apr 2027 | *Creation loop + sessions* | Recreate-and-compare daily practice, T9 E5+E6 shipped, breadth wave 2 (vocal correction, synthesis palette), CLAP similarity search (T5 v2), L6 German+flow |
| **Q4** May–Jul 2027 | *Surfaces + decision gate* | H4 surfaces (dashboard sibling repo, watch folders, UMAP library map, Panako sample detection), GPU/new-machine decision gate with the shelf doc as input, 12-month retrospective → roadmap v4 |

Execution model unchanged: one milestone ≈ one session, plans in `docs/superpowers/plans/`,
orchestrator spot-checks every handoff, STATUS.md is the portfolio board.

## 7. Governance carried forward (unchanged, restated as binding)

1. CPU-budget rule: measured min/track in every ML-feature handoff; >15 min ⇒ overnight batch engine.
2. Adapter pattern + license ledger for every adoption; model mirror + checksums.
3. Data boundary: code in repo, data in `D:\MusicData\toolshop\`; never commit lyrics/tokens.
4. Close-out discipline (AGENTS.md): clean tree + pushed before a session is DONE; verified verdicts
   only; CI claims need evidence (currently: local pytest output, CI billing-locked).
5. One integration per session; eval-first for model-based defaults; no big-bang rewrites.
6. Research-gated expansion: no new domain lane opens before its landscape-report section exists.

## 8. Research verdicts (v1.0, from the 2026-07-22 landscape report)

Report: `research/2026-07-22-full-studio-oss-landscape.md` (brief:
`research/2026-07-22-research-brief-full-studio-landscape.md`). **Coverage assessment (orchestrator):**
substantive on composition/MIDI, synthesis, generation shelf, and DAW integration; partial on vocal,
rhythm, hardware, adapt-vs-mine; thin on mixing suites and fleet job distribution. The evidence bar
(URLs, checked dates, confidence labels) was NOT met — treat every verdict below as `likely` and
re-verify license/maintenance/CPU-cost at adoption time (our eval-first policy already requires this).

### 8.1 Adoption candidates (enter via normal one-integration-per-session plans)

| Studio gap | Pick | Notes |
|---|---|---|
| Composition anchor | **MusicLang** (`musiclang_predict`) | CPU-fast symbolic generation with chord control; actively maintained |
| Drum patterns | **beatstoch** / **midi-drums** + **wobblemidi** humanization | MIDI-out generators; humanization learned from Groove MIDI Dataset; **midihum** (GBT velocity model) = mine |
| Headless MIDI→audio | **FluidSynth** (primary SF2 path) + **surgepy** + **DawDreamer** (VST3 host/offline render) | ⚠ sfizz is ARCHIVED (Jan 2024) — pysfizz wheels work today but treat as frozen; FluidSynth is the durable pick |
| Mix-chain host | **pedalboard** (already adopted) | ⚠ **known bug: VST3 effect plugins can render dry on Windows (PR #476, open)** — mandatory test gate in E2 before relying on external VST3 FX; built-in FX unaffected |
| Vocal pitch correction | **QPitch** / **OpenTune** (VST3, both 🧪 EVALUATE) | No credible open Melodyne-class note editor exists — confirmed gap; GSnap = closed-freeware fallback |
| Vocal strip / de-ess | **Nebula De-Esser** (VST3 Win, AGPLv3) · **Morass** full chain (🧪 new, July 2026) | Load via pedalboard/DawDreamer after the PR#476 gate |
| `.als` writer prior art (E6) | **ableton-set-builder** + **als-wire** + **ableton-project-processor** + pyableton | Major de-risk: E6 shifts from "novel build" to "adapt prior art"; ableton-project-processor is Live 12-tested, XML-level |
| REAPER alternative | **reapy-next** (v0.10.1, 2025) | Windows undocumented but ReaScript-based; backup path if .als fights back |
| Fleet data sync | **Syncthing** (live inter-machine) + **rclone** (nightly versioned backup) | Job-distribution pick intentionally left to a hands-on pilot (§8.2.2) |
| Vocal synthesis (new option) | **GPT-SoVITS** (CPU-fast fork exists, MIT, active) | Supersedes parked Voicebox as the someday-path; 🧪 EVALUATE only after core lanes |
| CPU generation curiosity | **MusicGen small** (2–3 min per 30 s on CPU) | Overnight-viable locally; genre quality unproven — Suno stays engine of record |

### 8.2 GPU shelf headline + fleet note

1. **The shelf got cheap.** ACE-Step v1.5 (MIT, SOTA-class, runs offloaded in <4 GB VRAM),
   Demucs GPU 3 GB, RVC/BS-Roformer 4 GB, DiffRhythm 8 GB. A single used **8–12 GB** card unlocks
   nearly the entire shelf (only YuE-full stays out of reach). This sharpens G9: the future-machine
   spec target is modest.
2. **Fleet job distribution:** research returned only sync-layer answers. Decision: run a
   **2-machine pilot** extending our existing resumable batch engine with a shared-folder/SQLite
   file-queue (simplest thing that can work) before considering Redis/RQ. Pilot = Q1 item.

### 8.3 Gap-fill verdicts (second dispatch, RESOLVED 2026-07-22 — `research/2026-07-22-gapfill-report.md`)

This report met the evidence bar (URLs, checked dates, confidence labels) — verdicts below are
dispatch-`verified`; standard re-verify-at-adoption still applies.

| Question | Answer |
|---|---|
| Free Windows VST3 mixing suite | **RESOLVED:** Airwindows Consolidated (MIT, ~500 FX, weekly builds) + ZL Equalizer 2 / ZL Compressor (AGPL, very active 2026) + Dragonfly Reverb (GPL). x42 / Calf = LV2-only, SKIP. LSP Windows binaries PAID (source buildable via MinGW — not worth it now) |
| Auto-mixing maturity | **Nothing production-grade exists** — the field is at "diagnose and suggest". Watch: Keel (beta 2026-06, AGPL engine / noncommercial GUI). Demucs `automix.py` = research script only |
| Stem-mix / masking analysis | **Phantom** (AGPL, `pip install phantom-audio`, 19 tools incl. per-octave `multi_stem_masking` + EBU R128 + batch-50 diagnostics) = INTEGRATE candidate, natural T8/E-lane companion. pyloudnorm confirmed (already in the E1 plan). Note: masking algo is patent-pending with AGPL patent grant — ledger it |
| Vocal time-alignment | **Confirmed gap — no OSS VocAlign equivalent anywhere** (existing tools do offset alignment, not time-warping). If ever needed: novel build (DTW over pitch contours + PSOLA) → build-ourselves list, LOW priority |
| Harmony / doubles | No dedicated tool; the classic recipe (±0.1–0.3 st detune + micro time-stretch + pan) is buildable TODAY on pedalboard's bundled Rubber Band — small T4 feature, not an adoption. HachiTune (AGPL, VST3 neural pitch editor, v0.1.2) 🧪 watch |
| Python MIDI foundation | **mido + pretty_midi** (both MIT, both active 2026); add music21 (BSD, heavy) ONLY for theory analysis; SKIP miditoolkit (stale since 2024-06). → Composition v0 stack now fully specified: MusicLang + mido/pretty_midi + beatstoch/midi-drums + wobblemidi + FluidSynth/sforzando render |
| Instrument content (legal) | CC0-first: **VCSL** (5 GB orchestral) + **VCSL Keys**, **Meadowlark** (CC0 trap one-shots), **TR808-fischer** (CC0 SFZ); **GareBear99 808 kit** (94 chromatic 808s, free commercial use, no-redistribute clause), Wave Alchemy 808 Tape (free), Salamander piano (CC-BY = attribution required). SFZ player: **Plogue sforzando** (free but PROPRIETARY, VST3, active 2026-04) — accepted as the no-OSS-peer exception since sfizz is archived |
| AbletonOSC | INTEGRATE — the only Live OSC bridge; MIT, maintained-but-slow (last push 2025-11, 5+ unmerged PRs); Windows WSAECONNRESET fix PR #214 may need local apply |
| FL Studio format | Downgraded from "dead end" to "severely limited": Music2DAW (.NET 10, 2026) can create/edit .flp from template, but NO plugin loading, NO render API, undocumented format → **D1 decision stands** (Ableton `.als` native target; FL served by universal pack) |

Remaining open (minor, fold into lane sessions): groove-extraction-from-audio prior art (rhythm
lane); license-ledger entries at each adoption (standing policy — new copyleft items to ledger:
ZL AGPL, Dragonfly GPL, Phantom AGPL, HachiTune AGPL; Rubber Band already covered via pedalboard).
