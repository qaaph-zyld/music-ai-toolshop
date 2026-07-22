# RESEARCH BRIEF — Full-Studio OSS Landscape (dispatch to research sub-agent)

**Date:** 2026-07-22 · **Commissioned by:** orchestrator, Music-AI-Toolshop
**Your role:** research-only specialist. You do web research and produce ONE markdown report.
You do NOT write code, install anything, modify any existing file, or make decisions for the
project — you deliver verified facts and ranked recommendations.

**Save your report to exactly this path:**
`D:\Projects\Music-AI-Toolshop\docs\superpowers\research\2026-07-22-full-studio-oss-landscape.md`
Create nothing else anywhere else.

---

## 1. Context you must respect (do not re-litigate)

The Music-AI-Toolshop is a working monorepo suite of music-production tools (stem separation,
track reverse-engineering/dossiers, mastering, vocal lab, lyric/library intelligence, sample forge)
built by integrating open-source tools behind thin adapters. Pipeline:
`INGEST → SEPARATE → ANALYZE → DOSSIER → CREATE (Suno) → MASTER → CATALOGUE`.
The 12-month goal is expansion to a **complete studio toolkit**: adding composition/MIDI,
synthesis/sound design, mixing, and vocal production (correction), plus distributed batch
processing across a small fleet.

**Hard constraints (locked user decisions):**
- **CPU-only compute for now.** No cloud inference, no GPU purchases yet. Fleet: 3 Windows 10/11
  machines, each 16 GB RAM — two i7-4770-class (Haswell, AVX2, NO AVX-512), one i5 9th-gen.
  Only useless GPUs (GT 640 2 GB class). Anything needing a modern GPU goes on a "deferred shelf"
  WITH its minimum hardware spec recorded (stronger machines are planned later).
- **Windows-first**, Python 3.11 venv standard; WSL2 Ubuntu available as a sidecar for
  Linux-only tools (proven pattern). ffmpeg available.
- **Open-source / free-local only.** No paid SaaS, no subscription plugins. Freeware
  closed-source is acceptable only if clearly noted as such and there is no OSS equivalent.
- **Integrate first, build only what doesn't exist.** Prefer tools with a CLI or Python API
  (headless/scriptable beats GUI-only); GUI-only tools are still reportable but score lower.
- DAWs in use: Ableton Live 12 Suite + FL Studio 21. Generation engine of record: Suno (external).
- Heavy work runs as resumable overnight batches; interactive tools must be CPU-snappy.

**Already researched and DECIDED 2026-07-15 — do NOT re-research these** (only flag in WS11 if
something material changed: project dead, repo moved, license changed, superseded):
demucs, python-audio-separator, BS/MelBand-Roformer infer pkgs, museval, beat_this, pychorus,
allin1, Chordino/NNLS, BTC, crema, basic-pitch, PANNs, faster-whisper, whisperX, matchering,
DeepFilterNet 3, noisereduce, pedalboard, DuckDB, Datasette, CLAP (laion), sqlite-vec,
chromaprint/pyacoustid, Panako, UMAP/HDBSCAN, mir_eval, phonemizer+espeak-ng, cyrtranslit, beets.

## 2. Workstreams — answer ALL of these

### WS1 — Composition & MIDI engine
The suite has zero composition tooling. Find the current best OSS for:
- Chord-progression generation/suggestion (rule-based and ML; CPU-viable).
- Melody generation on CPU (what remains of Magenta? maintained forks? musiclang? anything
  transformer-based that runs CPU int8?).
- Drum-pattern/groove generation and variation.
- MIDI manipulation foundations: music21 vs pretty_midi vs mido vs miditoolkit — current
  maintenance state and which combination a 2026 project should pick.
- Humanization/quantization tools; arrangement/song-structure templating.
- Pattern-mining angle: tools/approaches for extracting reusable chord/melody/drum patterns from
  our OWN analyzed corpus (we have beat grids + will have chords per section) — prior art?

### WS2 — Synthesis & instrument palette (headless-renderable)
We need `MIDI in → audio out` fully scriptable on CPU:
- Open synths with headless/CLI/Python rendering: Surge XT (surgepy status?), Dexed, ZynAddSubFX,
  Odin2, Vital (note license situation), sfizz/liquidsfz (SFZ), FluidSynth (soundfonts).
- DawDreamer specifically: maintenance status 2026, Windows wheel health, can it host VST3 +
  render offline reliably? (It could be the single render engine for this whole workstream.)
- Where to get quality free instrument content legally: SFZ/soundfont/sample libraries suitable
  for trap/drill/pop production (808s, keys, strings, brass); license per source.
- Wavetable/sample-based sound design utilities that are scriptable.

### WS3 — Mixing toolchain
- Open plugin suites worth adopting for programmatic mix chains (we already use Airwindows in
  mastering; pedalboard can host VST3): LSP, x42, Calf (WSL?), Dragonfly Reverb, Airwindows
  Consolidated, ZL Audio, others active in 2026 — Windows VST3 availability per suite.
- Automatic mixing: what is the actual 2026 state of auto-mix research/tools (e.g. deep-learning
  mix models, WAVE-U-Net-style, anything from the AES/ISMIR community with released CPU-runnable
  code)? Be honest about maturity — "research code, not usable" is a valid verdict.
- Stem-mix analysis utilities: per-stem loudness/masking/panning analysis OSS.
- Reference-mix comparison (we have matchering for master-stage; anything analogous for mixes?).

### WS4 — Vocal production chain
- Pitch correction OSS truth: autotalent lineage, GSnap, X42/zita options, anything newer and
  maintained with Windows builds or Python bindings; is there ANY credible open Melodyne-style
  note-based editor (research code counts, state maturity)?
- Time alignment (VocAlign-style) OSS/prior art.
- Harmony/doubles generation (pitch-shift-based, CPU).
- De-esser / de-breath / de-click beyond what DeepFilterNet+noisereduce cover.
- RVC / so-vits-svc / Applio 2026 status: CPU inference reality (minutes per second of audio?),
  minimum GPU that makes them usable → shelf entries.

### WS5 — Rhythm & groove tools
- Hydrogen, DrumGizmo: scriptability, Windows status.
- Groove extraction from audio (onset microtiming → groove template) prior art; swing/quantize
  utilities that operate on MIDI programmatically.

### WS6 — Local music generation landscape (populates the deferred-GPU shelf)
For each currently-credible local generation model — MusicGen/AudioCraft family, Stable Audio
Open, ACE-Step, YuE, DiffRhythm, MusicGPT-style wrappers, and anything newer that matters in
mid-2026 — record: what it generates (full song / instrumental / stems / vocals), quality
reputation for hip-hop/trap/pop, license (code AND weights, commercial-use status), VRAM/RAM
minimum, does ANY variant run on CPU in overnight-batch time, and the cheapest GPU tier that
runs it well. Conclusion: a table ranking which would matter most for this studio when stronger
machines arrive. (Suno stays the engine of record — this is shelf-stocking, not a migration plan.)

### WS7 — Fleet orchestration (3 Windows machines, LAN)
Recommend ONE primary approach with runner-up, optimizing for simplicity and Windows-friendliness:
- Job distribution: dead-simple shared-folder/file-lock queue vs Redis+RQ vs Celery vs Dask vs
  Prefect/Dagster (probably overkill — verify) vs custom SQLite-backed queue. We already have a
  resumable batch engine per-machine; the need is dispatch + status across 3 boxes.
- Data sync for `D:\MusicData` working sets: Syncthing vs rclone vs robocopy/SMB — reliability
  with large audio files, partial-sync patterns.
- Cross-machine backup topology (this finally enables true DR — currently backups live on the
  same physical box as the data): recommended nightly design, versioning, verification.
- Practicalities: Windows service vs scheduled task for workers, wake-on-LAN, secrets handling
  (.env tokens must not sync in plaintext).

### WS8 — Hardware unlock map (input for the future purchase; NOT financial advice, a spec table)
- For each shelf capability (Roformer-quality separation, RVC-class voice conversion, WS6
  generation models, faster whisper tiers): minimum and comfortable GPU spec (VRAM being the
  axis), and what a used-market mid-range card (e.g. 12 GB / 16 GB classes) unlocks vs doesn't.
- Also: does the i5 9th-gen box differ materially from the i7-4770 boxes for our CPU workloads
  (AVX2 both; memory bandwidth; onnxruntime perf) — should it get the heavier batch role?

### WS9 — DAW integration refresh
- Prior art for generating Ableton `.als` files programmatically (they're gzipped XML): existing
  libraries/projects, pitfalls, Live 12 schema notes. AbletonOSC maintenance status.
- REAPER as a scriptable alternative: reapy status, .RPP writers.
- FL Studio project format: confirm still a dead end for generation.

### WS10 — Adapt-vs-mine audit of whole OSS studio projects
For LMMS, Zrythm, Ardour, Stargate DAW, and any other active open DAW/studio project: is there
any component worth MINING (engines, plugin hosts, file-format code) rather than adopting the
whole app? One paragraph each, honest "nothing for us" allowed.

### WS11 — Delta check on the decided stack (quick pass)
For the do-not-re-research list in §1: flag ONLY items that died, moved, relicensed, or got
superseded since 2026-07-15. Specifically confirm current safe download sources for BS-Roformer
weights (the 2026-06 HF account deletion burned us once — hence our model-mirror policy).

## 3. Method & evidence bar (non-negotiable)

- Primary sources: the GitHub/GitLab repo, official docs, PyPI. For every candidate record:
  **name · repo URL · license (code AND models/content separately where applicable) · last
  release/commit date you actually checked · Windows-native vs WSL-only · interface (CLI /
  Python API / VST3 / GUI-only) · CPU-viability estimate on i7-4770-class 16 GB (state basis:
  measured claims, issue reports, or inference — label which) · verdict.**
- Verdict vocabulary (match our existing map): ✅ INTEGRATE · ➕ WRAP · 🧪 EVALUATE ·
  ⏸ PARK-GPU (with min spec) · ❌ SKIP — each with a one-line rationale.
- Confidence label per verdict: `verified` (primary source read) / `likely` (secondary source) /
  `unverified` (flag for us to check). Never present marketing claims as fact. If two sources
  conflict, say so.
- Recency matters: prefer projects with activity in the last 12 months; a dead-but-done tool can
  still be INTEGRATE if it's stable and dependency-light — say that explicitly.
- It is a VALID and useful result to report "no credible OSS exists for X; build or skip" —
  do not pad weak candidates to fill a table.

## 4. Report structure (write exactly this skeleton)

```
# Full-Studio OSS Landscape Report — 2026-07-22
## 0. Executive summary            (≤1 page: the 10 most consequential findings)
## 1. Top-10 highest-leverage adoptions (ranked, with one-line why + which workstream)
## 2. WS1 Composition & MIDI       (table + notes)
## 3. WS2 Synthesis palette        (table + notes; DawDreamer verdict prominent)
## 4. WS3 Mixing toolchain         (table + notes; honest auto-mix maturity assessment)
## 5. WS4 Vocal production         (table + notes)
## 6. WS5 Rhythm & groove          (table + notes)
## 7. WS6 Local generation shelf   (model table + GPU-tier ranking)
## 8. WS7 Fleet orchestration      (ONE recommended design + runner-up, with rationale)
## 9. WS8 Hardware unlock map      (spec table per shelf capability + i5-9th-gen note)
## 10. WS9 DAW integration refresh
## 11. WS10 Adapt-vs-mine audit
## 12. WS11 Decided-stack delta check
## 13. Risks & unknowns            (what you could not verify; what needs hands-on evaluation)
## 14. Source appendix             (every URL you relied on, grouped by workstream)
```

Length: as long as the evidence requires — the companion doc
`docs/superpowers/specs/2026-07-15-oss-integration-map.md` is the quality bar, and your scope is
roughly 3× wider. Depth over polish; tables over prose where possible.

## 5. Explicit exclusions

- No code, no installs, no downloads of models/binaries, no modification of any project file
  other than creating the single report file at the path in the header.
- No cloud/SaaS/paid recommendations (noting a paid tool as "the closed benchmark for X" in one
  line is fine for context).
- No purchase orders or financial advice — WS8 is a technical spec/unlock table only.
- Do not redesign our architecture or roadmap; recommend components, not reorganizations.
