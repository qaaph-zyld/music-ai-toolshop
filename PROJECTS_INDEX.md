# Music AI Toolshop - Projects Index

## Active Projects

| # | Project | Status | Description |
|---|---------|--------|-------------|
| 01 | suno-library | ✅ Active | **3,426 tracks fully preserved locally** (15.79 GB, 0 failures, 2026-08-19) at `data/toolshop/suno/audio/` + metadata JSONs |
| 02 | ace-step | 🟡 Parked | AI music generation with ACE-Step (GPU-gated) |
| 03 | lyrics-writer | ⏳ Planned | AI lyrics generation tools |
| 04 | stem-extractor | ✅ Active | Shipped in `toolshop` core (`toolshop stem extract`) |
| 05 | track-reverse-engineering | ✅ Active | Integrated wav_reverse_engineer production analysis |
| 06 | open-daw | 🟡 Long horizon | Rust/C++ DAW engine; AI modules stubbed |
| 07 | genius-lyrics | ✅ Active | **1,425-song corpus** at `data/toolshop/lyrics/genius/` + lyrics.db (10,654 sections, 65,912 lines, 273,801 rhyme rows; cohorts drill_trap 808 / pop 524) |
| 08 | sample-forge | ✅ Active | `toolshop remix` - tempo/key-matched remixes and sample packs (T7) |
| 09 | daw-bridge | ✅ Active | `toolshop daw` - live FL Studio / Ableton control via TCP bridge (12 modules, #025) |
| 10 | music-video | ✅ Active | `toolshop video` - FFmpeg compositing, ASS lyrics, audio-reactive shaders, stock footage (#028) |
| 11 | melody-carrier | ✅ Active | `toolshop melody-carrier` - audio→MIDI→carrier WAVs for Suno cover mode (#039) |
| 12 | lyrics-writing | ✅ Active | `toolshop lyrics` - L5 rimer DB, brief generator, draft scorer + 10 craft modules (#036, #037) |
| 13 | vocal-swap | ✅ Active | `toolshop vocal-swap` - Suno track + your vocal → mixed and mastered, 8 resumable stages with M4 gates (#052) |
| — | ai_modules | ✅ Resolved | **Dissolved 2026-08-31 (D6, #051).** Keepers moved into `toolshop/`; `musicgen`/`lora_finetuning` shelved to G9; the rest removed. |
| - | mastering_tool | ✅ Active | Git submodule: LUFS, reference, vocal doctor, chain DSL |
| - | Voicebox | 🟡 External | Vendored fork removed; re-clone when GPU gate opens |
| - | MAirina_Tucc | 🟡 Separate | Serbian rhyme tool + React UI |

## Strategic Roadmap

- **[Goals v2.0 — current](./docs/superpowers/specs/2026-08-19-goals-v2.md)** (goals G0–G11, phases P0–P5)
- **[State of the Project — 2026-08-19 assessment](./docs/superpowers/specs/2026-08-19-state-of-project-assessment.md)**
- [Portfolio Status Board](./docs/superpowers/STATUS.md)
- [Long-Term Roadmap v2](./docs/superpowers/specs/2026-07-15-longterm-roadmap-v2.md) — backlog of record (tool charters T0–T9)
- [2026-07-11 Strategic Roadmap v1](./docs/superpowers/specs/2026-07-11-strategic-roadmap-v1.md) (superseded)

## Directory Structure

Each project follows dev_framework principles:
- `docs/` - Project documentation
- `src/` - Source code
- `tests/` - Test suite (TDD enforced)
- `README.md` - Project overview

## Quick Navigation

- [01-suno-library](./projects/01-suno-library/) - Extracted Suno collection
- [02-ace-step](./projects/02-ace-step/) - Music generation
- [05-track-reverse-engineering](./projects/05-track-reverse-engineering/) - Track reverse engineering integration
- [06-opendaw](./projects/06-opendaw/) - DAW engine (live copy at `open_DAW/`)
- [docs/superpowers/specs](./docs/superpowers/specs/) - Design documents
- [docs/superpowers/plans](./docs/superpowers/plans/) - Implementation plans
