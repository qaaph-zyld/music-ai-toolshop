# T7.1 Section-aware Sample Forge — Handoff

**Date:** 2026-07-22
**Commits:** `3e6fadf` → `ea2e930` (6 commits on `master`, pushed to origin/master)

## What shipped

- `_load_sections()` — parses JSON section boundaries (top-level or `structure.sections`)
- `_slice_by_sections()` — section-aware slicing with beat snap and sub-slice
- `_sample_name()` — new naming: `<key>_<bpm>_<section>_<n>.<ext>` (e.g. `A_120_chorus_01.flac`)
- `create_remix()` — accepts `sections`, `sub_slice_beats`, `snap_to_beats` in sample mode
- CLI flags: `--sections`, `--sub-slice-beats`, `--no-beat-snap`
- Manifest entries include `"section"` field
- CI installs `.[audio,lyrics,remix]`
- 34 tests pass (16 new across adapter + CLI)

## Breaking changes

- **Sample filenames changed** from `<key>_<bpm>bps_<idx>_<start>s.<ext>` to `<key>_<bpm>_<section>_<n>.<ext>`. Existing scripts or DAW projects referencing old filenames will need updating.
- Manifest now includes `"section"` field (additive, non-breaking for readers).

## Deferred

- **Automatic section detection** (librosa novelty, pychorus, madmom, etc.) is explicitly deferred to H2 structure detector. Sections must be provided externally.
- No new dependencies were added.

## Known issues

- CI is billing-locked (GitHub Actions). Local pytest is the quality gate. CI config is updated and ready for when billing is resolved.
- numpy 2.0 cleaning pipeline failures were fixed in the M6/Phase-0 wave (#019, commit `27cfa35`).

## Test results

- `tests/test_remix_adapter.py`: 24 passed
- `tests/test_cli_remix.py`: 10 passed
- Full suite (post-#019): 383 passed, 1 skipped, 0 failed — in py3.11 .venv

## Next steps

- H2: automatic section detection (structure detector)
- H3: pedalboard pick promoted to core chains (E2)
