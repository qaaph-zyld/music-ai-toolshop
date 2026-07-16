# H1-M1c-FINAL — Consolidation: Commit Debt, Data Boundary, Extractor Fixes, Submodule Hygiene

> **REVISED 2026-07-16 (late)** by strategy review after the Genius extraction ran ahead of the original
> M1c plan. This version supersedes the earlier content of this file. One milestone; no new features.
> Obey `AGENTS.md`. **This is a consolidation session — nothing new gets built until the repo is clean.**

## Context (verified by strategy review)

- Extraction SUCCEEDED: 415 songs / 775 files, exit 0. But output went to **`Music-AI-Toolshop\lyrics_output\`
  (inside the repo — data-boundary violation; untracked, nothing leaked)** instead of `D:\MusicData\toolshop\lyrics\`.
- **Trio discrepancy explained:** `_index.json` holds 3 entries that are all the SAME song (`O.D.D.D.`),
  each with an EMPTY `file` field; folder has the song once. Root causes: (a) a song reachable from all
  3 artists' pages is counted once per artist — index/summary count entries, not unique songs; (b) the
  index writer never fills `file`. `_dedup_log.json` reporting 0 confirms dedup misses index/counters.
- `other-collab == 0` is suspicious with `include_features=True` — categorization likely buckets
  "tracked artist + outsider" songs into solo categories. Review the logic.
- Debt carried 3 sessions: CHANGELOG entry, `load_or_create_status` resume fix, and now uncommitted:
  `toolshop/genius_*.py`, `lyrics_analyzer.py`, 3 test files, `cli.py`/`pyproject.toml`/`__init__.py` mods,
  `Genious_lyrics_extractor/`, M1c plan file, junk (`pytest_tail.txt`, `output.json`).
- `mastering_tool` submodule: dozens of modified files (July-13 CRLF fixes + doc edits) never committed
  inside the submodule; parent pointer stale. Risk for H1-M4.

## State re-verified 2026-07-17 (strategy session) — read before executing

- **Task 1 data move is ALREADY DONE:** `lyrics_output` is gone from the repo; corpus lives at
  `D:\MusicData\toolshop\lyrics\genius\` (775 files). Task 1 remaining: extractor default output dir
  + `.gitignore` + junk deletion only. Do NOT move anything again.
- **Reconciled counts:** 386 unique songs on disk (386 json + 386 txt + 3 meta). Index: 415 entries,
  28 duplicated `(title, primary_artist)` keys — confirms the Task 2 dedup bug. Target after rebuild:
  index entries == unique songs on disk.
- **NEW defect for Task 2:** every index entry's `json_path`/`txt_path` still points to the old
  `d:\Projects\Music-AI-Toolshop\lyrics_output\...` location. The rebuild-from-disk must write paths
  **relative to the genius root** so future moves don't break the index again.
- **Cross-folder duplicate found:** `jala-brat-dandara` exists in two category folders — the rebuild
  should detect cross-folder dups and record the canonical copy in `_dedup_log.json`.
- T5-L1 (`plans/2026-07-17-t5l1-lyrics-db-foundation.md`) is queued immediately after this milestone
  and consumes the rebuilt index — extra reason the counts must reconcile.

### Task 1: Move lyrics data out of the repo (move, never delete)
- [ ] `Move-Item Music-AI-Toolshop\lyrics_output D:\MusicData\toolshop\lyrics\genius` (create parents).
- [ ] Update `extract_artists.py` default output dir to that path (env-var override `TOOLSHOP_DATA_DIR` aware).
- [ ] `.gitignore`: add `lyrics_output/`, `Genious_lyrics_extractor/samples/`, `pytest_tail.txt`. Delete
      `pytest_tail.txt` and stale root `output.json`/`output.txt` (generated junk — deletion allowed for these three ONLY).

### Task 2: Extractor correctness fixes (TDD)
- [ ] Index dedup: key = normalized (title, primary_artist); one entry per unique song; `file` field populated
      with the written path; summary counts unique songs (415 → recount; trio becomes 1).
- [ ] Re-generate `_index.json`/`_summary.md` from the existing downloaded files (NO re-fetch; write a small
      rebuild function) — counts must reconcile: files/2 == unique songs.
- [ ] Review categorization: songs by a tracked artist featuring non-tracked artists — decide bucket
      (recommend: keep in artist's solo bucket but add `featured` field to index; `other-collab` reserved for
      multi-tracked-artist combos not matching duo/trio). Document the rule in the README.

### Task 3: Resume-logic fix (carried from M1b)
- [ ] TDD-fix `load_or_create_status` (runner + `toolshop/batch.py` if shared): resume preserves
      `skipped_long`/`failed` entries; `skipped_long` not re-processed unless `--no-resume`.

### Task 4: Mastering submodule hygiene (prerequisite for H1-M4)
- [ ] Inside `mastering_tool/`: review `git status` — expect CRLF-normalization diffs + July-13 doc/path fixes.
      Commit as `fix: LF normalization + post-move path fixes (2026-07-13 session)`; do NOT touch pipeline logic.
- [ ] Parent repo: stage the submodule pointer bump in the commit wave below.

### Task 5: Commit wave + CHANGELOG (finally)
- [ ] CHANGELOG Answer entry covering: H1-M1 completion (140 → 221+1, backend incident + guards),
      Genius subproject + extraction (415 songs), extractor fixes, resume fix.
- [ ] Commits: (a) `feat(lyrics): Genius extractor + toolshop lyrics modules` (code+tests+spec, NO .env/samples/lyrics),
      (b) `fix(lyrics): index dedup, file refs, categorization rule`, (c) `fix(batch): preserve skipped/failed on resume`,
      (d) `chore: submodule pointer + gitignore + junk removal`, (e) CHANGELOG.
- [ ] `PROJECTS_INDEX.md`: add Genius lyrics lane (✅ Active, 415-song corpus at D:\MusicData) and link STATUS board.
- [ ] Push; CI green.

### Task 6: Handoff
- [ ] `<yyyy-MM-dd_HHmm>_music-ai-toolshop-h1m1c-final.md`: per-task evidence (reconciled counts, pytest tails,
      commit hashes, submodule hash), deviations, remaining debt (should be ONLY the ~10 numpy test failures).
      `session_end.py`.

## Verification checklist
- [ ] Repo `git status` clean except intentionally-untracked local dirs; CI green after push
- [ ] Lyrics live under `D:\MusicData\toolshop\lyrics\genius\`; index `file` fields resolve; unique-song counts reconcile
- [ ] Resume-fix tests green; submodule committed + pointer bumped
- [ ] CHANGELOG + PROJECTS_INDEX updated

---

## Copy-Paste Bootstrap Prompt

```text
FRAMEWORK BOOTSTRAP (v11) — Execute in order:
1. Read `ai_dev_meta_layer/framework_loader.md` and load core memories + soul.
2. Read `D:\Projects\Music-AI-Toolshop\AGENTS.md`.
3. WAIT FOR MY TASK.
4. Run: python scripts/session_brief.py "H1-M1c-final: consolidation (commits, data boundary, extractor + resume fixes, submodule)" --files "Music-AI-Toolshop/docs/superpowers/plans/2026-07-16-h1m1c-cleanup-genius-run.md"
5. Load the KBs the brief names.
6. Draft a short plan from the plan file, get approval, then execute task-by-task.
7. After completion, run `python scripts/session_end.py --status completed --duration <min> --helpful <skill>`.

MY TASK: Execute D:\Projects\Music-AI-Toolshop\docs\superpowers\plans\2026-07-16-h1m1c-cleanup-genius-run.md
(the REVISED version) exactly as written. Consolidation only — no new features. Move data, never delete it
(the three named junk files are the only allowed deletions). NEVER commit .env, samples, or lyrics files.
NO re-fetching from Genius — rebuild the index from files on disk.

WHEN DONE — REPORT BACK: create d:\Projects\.windsurf\handoffs\<yyyy-MM-dd_HHmm>_music-ai-toolshop-h1m1c-final.md
with per-task evidence, reconciled song counts, pytest tails, commit hashes (parent + submodule), CI status,
deviations, blockers. After review, H1-M2 and H1-M4 are released.

OPEN FILES: Music-AI-Toolshop/docs/superpowers/plans/2026-07-16-h1m1c-cleanup-genius-run.md
```
