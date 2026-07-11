# Music-AI-Toolshop — Strategic Roadmap v1

**Date:** 2026-07-11
**Status:** Approved direction (strategy session with Claude; execution delegated to IDE agents)
**Companion plans:** `docs/superpowers/plans/2026-07-11-phase0-take-control.md`, `docs/superpowers/plans/2026-07-11-phase1-stem-tool-v1.md`

---

## 1. Product Thesis

**Music-AI-Toolshop is a local-first music deconstruction & reconstruction lab.**

Put any track in (file, YouTube URL, Suno library) → get out: stems, structure, chords/key/BPM,
lyrics, production recipe, and a mastering profile → feed those into Suno/ACE-Step to create new
tracks → master them with `mastering_tool` → everything indexed in a queryable catalogue.

The unifying pipeline every phase serves:

```
INGEST → SEPARATE → ANALYZE → DOSSIER → CREATE → MASTER → CATALOGUE
(file/YT)  (stems)   (musical +  (recipe   (Suno/     (mastering  (searchable
                      production  .json/md)  ACE-Step   _tool)      library)
                      + lyrics)              seeds)
```

Most pieces already exist as disconnected islands. **The strategy is connect + harden, not build new.**

---

## 2. Estate Map (as of 2026-07-11)

| Asset | State | Notes |
|---|---|---|
| `toolshop` CLI v0.3.0 | ✅ Works | 10 adapters: BPM/key, YT, Suno, voice FX (12 detectors), stems, cleaning, reverse-engineering. Tests exist. |
| Stem extraction | ✅ Works | audio-separator 0.44.2; proven outputs in `Stemmeca_alatkka/` (MDX fast + BS-Roformer HQ). Known bugs — see §5. |
| Reverse-engineering batch | ✅ Works, interrupted | `run_reverse_engineering_batch.py`; CrhymeTV 140/222 done, 0 failures, resumable. ~12 min/track (CPU, fast mode). |
| `mastering_tool` (submodule) | ✅ Deep | Through Phase 8: LUFS verify, reference benchmark, vocal doctor/QC/restore, CLAP matcher, chain DSL. |
| Suno library (project 01) | ✅ Data | 2,633 songs w/ lyrics + styles metadata. |
| Catalogue generator | ✅ v1 | `generate_crhymetv_catalogue.py` → CSV/MD/prompt seeds. |
| `open_DAW` | 🟡 Long horizon | Rust engine + C++ UI; AI modules NOT wired. Separate product track. |
| `Voicebox` | 🟡 Vendored fork | External OSS (jamiepine/voicebox) — voice cloning studio. Hardware-gated. |
| `MAirina_Tucc` (rimer) | 🟡 Separate product | Serbian rhyme tool + React UI. |
| `Stemmeca_alatkka` | 🔴 Retire | Scratch dir: test audio + generated stems + abandoned `stemslicer` GUI. Superseded by toolshop adapter. |
| Duplicates | 🔴 Debt | `Mastering_Toolshop` (repo root sibling) vs `mastering_tool` submodule; `open_DAW/` vs `projects/06-opendaw/`. |

## 3. Hard Constraints (design around these)

- **GPU: GeForce GT 640 2 GB (Kepler, driver 456.71) — unusable for modern CUDA/DirectML ML.
  Everything runs CPU.** Measured: ~12 min/track full RE pipeline in fast mode. Design defaults for CPU;
  keep `--gpu` flags for future hardware.
- **Disk: ~41 GB free on D:.** Stems at WAV scale will exhaust it → FLAC output + retention policy are mandatory.
- **RAM 16 GB** — fine for inference, forbids giant batch parallelism.
- **Python 3.13.5 global env, no lock.** Several audio libs (madmom, spleeter, essentia, basic-pitch TF)
  don't support it → pinned 3.11 venv is the standard; `demucs` currently NOT installed anywhere.
- **Windows 10, cp1252 console** — UTF-8 discipline required end-to-end (mojibake already visible in recipes).

## 4. Phases

### Phase 0 — Take Control (repo + environment hygiene) — *do first, ~1 agent-day*
Goal: clean git state, reproducible env, honest docs. See companion plan.
**Acceptance:** clean `git status`; one-command env setup; `toolshop doctor` passes; tests green; docs match reality.

### Phase 1 — Stem Tool v1.0: "any wav/mp3 in, stems out" — *~2-3 agent-days*
Goal: productize the working separator into the flagship command. See companion plan.
Highlights: fix stem-mapping bug, add Demucs 4/6-stem backend, model registry with CPU-benchmarked
presets (`karaoke`, `2stem-hq`, `4stem`, `6stem`), folder batch w/ resume, FLAC default, manifest.json sidecar.
**Acceptance:** `toolshop stems <file-or-folder> --preset X` works on any wav/mp3; benchmark table in docs.

### Phase 2 — Reverse-Engineering v2: the Track Dossier — *~1 agent-week*
Goal: recipe.md → **dossier** (machine `dossier.json` + human `recipe.md` v2).
- Structure segmentation (intro/verse/chorus timeline) — allin1 if CPU/py-version viable, else novelty-based librosa/MSAF fallback.
- Key/mode via Krumhansl-Schmuckler profiles (fix bogus `chroma_mean > 0.5` mode heuristic); chords with confidence, grouped per section; beat-grid export.
- MIDI extraction from stems (basic-pitch ONNX build for Windows, or torchcrepe melody line); bass + melody first, drums later.
- Loudness/dynamics/spectral profile (pyloudnorm) aligned with `mastering_tool` PREMASTER_ACCEPTANCE_SPEC.
- Lyrics: Whisper transcription of the vocal stem (reuse `D:\Projects\transcribe` + `get_transcript.py` work) → timed lyrics in dossier.
- Re-run economics: finish CrhymeTV batch on v1 NOW (overnight, resumable); regenerate dossiers later from cached stems without re-separating.
**Acceptance:** dossier on a known track passes listening sanity-check; 10-track batch regen; catalogue rebuilt.

### Phase 3 — Integration: the Lab Pipeline — *~1 agent-week*
- `toolshop dossier <file|url>` one-shot: ingest → stems → analyze → dossier folder.
- Mastering bridge: dossier feeds `mastering_tool` premaster check + CLAP reference matching; `toolshop master` passthrough.
- Catalogue v2: SQLite over all dossiers; `toolshop lib find --bpm 88-96 --key Gm --effect reverb`; playlist export. Fold in Suno library DB.
- Suno/ACE-Step seed generator from dossier (reuse SUNO_PROMPT_TEMPLATES patterns).
**Acceptance:** YouTube URL → complete dossier folder in one command; library query over ≥150 tracks.

### Phase 4 — Surfaces — *optional, after 1-3*
- Local web dashboard (Streamlit groundwork exists): drop file → stems/dossier view; library browser.
  NOTE: architecture spec says "no web UI in this repo" → either a thin sibling repo importing the package, or formally amend the spec.
- Retire `stemslicer` GUI (superseded).
- Watch-folder mode / SendTo shortcut.

### Phase 5 — Frontier Bets (sequenced by value ÷ effort; most are GPU-gated)
1. **Sample/loop pack generator** — slice stems by section + beat grid → labeled loops/one-shots. CPU-fine, high creative value.
2. **Drum-to-MIDI** — onset classification on drum stem → GM map.
3. **ACE-Step recreation loop** — dossier → generation → A/B vs original. GPU-gated.
4. **Voicebox vocal synth integration** — GPU-gated.
5. **open_DAW** — separate long-horizon track; minimal integration target: "open dossier as DAW session template."

## 5. Known Defects (fix in P0/P1, discovered 2026-07-11)

1. `stem_extractor_adapter.extract_stems` fast mode: pass-2 output matching looks for
   `"backing"`/`"other"` but UVR-BVE outputs are named `_(Vocals)_UVR-BVE...` / `_(Instrumental)_UVR-BVE...`
   → `backing_vocals: None` in every fast-mode result, and `main_vocals` may grab the wrong file.
2. Key/mode inconsistency: track reported "G major" while chord detector says Gm — mode heuristic in
   `_basic_analysis` is not a real mode detector; verify the advanced backend too.
3. Mojibake in recipe headers for non-ASCII filenames (UTF-8/cp1252 mixups) — enforce UTF-8 on all
   file writes AND reads; test with `Täterprofil`-style names.
4. `use_directml=use_gpu` in stem adapter is misleading on this hardware — default must be CPU with
   clear messaging.
5. `PROJECTS_INDEX.md` stale (says stem-extractor "Planned"; it ships). CHANGELOG top entry predates batch completion state.
6. `demucs` referenced by `Stemmeca_alatkka/demucs_runner.py` and `[track-full]` extra but not installed; 4-stem path currently dead.

## 6. Decision Gates (user decisions, not agent decisions)

- **G1 — GPU upgrade:** a used RTX 3060 12 GB-class card turns ~12 min/track into <1 min, unlocks
  Roformer-HQ-as-default, ACE-Step local gen, and Voicebox. Single highest-leverage hardware move.
  Until then: CPU presets are the default reality.
- **G2 — Web UI location:** amend "no web UI" spec vs. sibling repo.
- **G3 — Repo boundaries:** approve moving personal audio + generated outputs out of git history/tree
  (they belong in a data directory, not the tool repo).
- **G4 — open_DAW cadence:** park vs. keep slow-burn lane.

## 7. Operating Principles (unchanged from architecture spec, reaffirmed)

- CLI-first adapter layer; adapters stay pure; CLI/scripts orchestrate.
- TDD on every adapter change; batch runners must be resumable and UTF-8-safe.
- Zero hardcoded paths; every long job writes a status JSON and supports `--limit/--offset/--resume`.
- Outputs are artifacts with manifests, not loose files.
