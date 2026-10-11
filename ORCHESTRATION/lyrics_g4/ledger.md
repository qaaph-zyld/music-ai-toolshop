# Orchestration ledger — lyrics-g4 (German corpus `genius-de`, Tier-1 CrhymeTV roster)

Lane: `lyrics-g4` | Worktree: `Music-AI-Toolshop/.worktrees/lyrics-g4` | Megaplan: `.workspace_archive/plans/lyrics-g4-genius-de-megaplan.md`
GATE G4: approved 2026-10-10 — Tier-1 roster (8 acts), separate corpus `genius-de`, approx+flag metrics.
Adversarial plan review: `.workspace_archive/reviews/2026-10-09_lyrics_g4_plan.md` — all findings folded in.
Execution note: fetch/audit/ingest/verify ran inline by the orchestrator (single-lane sequential work; `waves.json` subagent dispatch not needed). All wave outputs verified directly.

| Wave | Status | Commit | Evidence |
|---|---|---|---|
| G4-pre | DONE | — | worktree at `63779ff`; ledger + waves.json seeded |
| G4-I | DONE | `fb46382` | registry row, fold, cohorts, TYPE_MAP, count_line_de, rhymes-skip, language plumbing, backup glob, word-boundary, roster_g4.json — 30 new + 253 existing tests green |
| GATE G4-ROSTER | APPROVED | `3db6242` | all 8 resolved + pinned (probe-verified 187-circle songs; Maxwell→`Maxwell 187` id=1040924 not US R&B) — user approved 2026-10-10 |
| G4-B fetch | DONE | `e9f78af` | All 8 done. done_ids: bonez 449 · raf 475 · gzuz 253 · lx 178 · sa4 137 · maxwell 119 · 187 79 · capuz 15 = 1,705 processed → 1,480 saved (rest = FAIL/no-lyrics). Incidents: (1) cp1252 emoji crash → UTF-8 reconfigure fix committed; (2) shell-session death → Start-Process detached; (3) 30s read-timeout wave (raf, lx, sa4, maxwell errored) → timeout 30→60s + 1-retry-on-transient committed; resume passes completed all. |
| G4-A audit | DONE | `72a36ac` | VERDICT: INGEST READY — 1,478 files, 0 null ids, 0 bad_lang, 0 empty_sections (200-sample). 4 empty-body stub pages (Genius page, no transcription) quarantined to `_quarantine_no_lyrics/`. Audit-script fix: multi-token folders now match inside duo/trio dirs (`_belongs` contiguous-token-subsequence). |
| G4-DB ingest | DONE | — | corpus-scoped rebuild via worktree `build_database` (main-repo paths): **1,455 songs · 10,161 sections · 81,837 lines**; 21 intra-corpus fid collisions dropped (`_dedup_log.json`); 0 rhymes computed (de-skip active). |
| G4-V verify | DONE | — | genius-de 1,455 rows, all `language='de'`, fid 100% populated, 0 dup fids; cohort german_drill 1,215 / NULL 238 (featured+other-collab) / drill_trap 2 (Jala Brat primary — correct); metrics 100% on 81,837 lines (avg 11.1 syl vs pro 10.8); **0 de line_rhymes**; licensing 100% study-only/release_ok=no; integrity ok, 0 fk violations; other corpora byte-identical (25,195→26,650 = +1,455). 95 tests green. |
| MERGE | pending | — | Answer ID at merge; push user-gated |

## Roster (PROPOSED → frozen at GATE G4-ROSTER)

8 acts, all `german_drill`: Bonez MC, RAF Camora, GZUZ, LX, Sa4, Maxwell,
187 Strassenbande, Capuz. See `roster_g4.json` for variants + pinned ids.

## Decisions locked (user-approved 2026-10-10)

- Separate corpus `genius-de` (`genius-de/` dir, registry row) — NOT genius-pro.
- `language='de'` corpus-declared via `--language` flag → `save_song` param.
- `count_line_de` approximate German syllable counter, exact `'de'` dispatch.
- `populate_rhymes` SKIPPED for `language='de'` — zero German line_rhymes;
  phonemizer-de is the later lane. `rimer_db.py` untouched.
- Word-boundary match for ≤4-char COHORT_MAP keys (LX/Sa4 safety; absorbs
  the standing G3 short-key follow-up).
- `_ASCII_FOLD_MAP` extended ä/ö/ü/ß (no-op on existing corpora — test-proven).
- backup.py covers `lyrics/genius-de/**` (Tier-1) + coverage test.
