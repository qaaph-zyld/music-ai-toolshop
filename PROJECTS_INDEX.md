# Music AI Toolshop - Projects Index

## Active Projects

| # | Project | Status | Description |
|---|---------|--------|-------------|
| 01 | suno-library | ✅ Active | 2,633 Suno songs with lyrics, styles, metadata |
| 02 | ace-step | 🟡 Parked | AI music generation with ACE-Step (GPU-gated) |
| 03 | lyrics-writer | ⏳ Planned | AI lyrics generation tools |
| 04 | stem-extractor | ✅ Active | Shipped in `toolshop` core (`toolshop stem extract`) |
| 05 | track-reverse-engineering | ✅ Active | Integrated wav_reverse_engineer production analysis |
| 06 | open-daw | 🟡 Long horizon | Rust/C++ DAW engine; AI modules stubbed |
| 07 | genius-lyrics | ✅ Active | 385-song corpus at D:\MusicData\toolshop\lyrics\genius\ + lyrics.db (SQLite, stats CLI) |
| - | mastering_tool | ✅ Active | Git submodule: LUFS, reference, vocal doctor, chain DSL |
| - | Voicebox | 🟡 External | Vendored fork removed; re-clone when GPU gate opens |
| - | MAirina_Tucc | 🟡 Separate | Serbian rhyme tool + React UI |

## Strategic Roadmap

- [2026-07-11 Strategic Roadmap v1](./docs/superpowers/specs/2026-07-11-strategic-roadmap-v1.md)
- [Phase 0: Take Control](./docs/superpowers/plans/2026-07-11-phase0-take-control.md)
- [Phase 1: Stem Tool v1.0](./docs/superpowers/plans/2026-07-11-phase1-stem-tool-v1.md)

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
