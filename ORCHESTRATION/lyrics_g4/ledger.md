# Orchestration ledger — lyrics-g4 (German corpus `genius-de`, Tier-1 CrhymeTV roster)

Lane: `lyrics-g4` | Worktree: `Music-AI-Toolshop/.worktrees/lyrics-g4` | Megaplan: `.workspace_archive/plans/lyrics-g4-genius-de-megaplan.md`
GATE G4: approved 2026-10-10 — Tier-1 roster (8 acts), separate corpus `genius-de`, approx+flag metrics.
Adversarial plan review: `.workspace_archive/reviews/2026-10-09_lyrics_g4_plan.md` — all findings folded in.

| Wave | Status | Commit | Evidence |
|---|---|---|---|
| G4-pre | DONE | — | worktree at `63779ff`; ledger + waves.json seeded |
| G4-I | in progress | — | code + tests (registry row, fold, cohorts, TYPE_MAP, count_line_de, rhymes-skip, language plumbing, backup glob, word-boundary, roster_g4.json) |
| GATE G4-ROSTER | pending | — | dry-run resolve → pinned ids → user eyeball (Maxwell/LX/Sa4 mandatory) |
| G4-B fetch | pending | — | detached `--language de --outdir …/genius-de` |
| G4-A audit | pending | — | INGEST READY verdict required |
| G4-DB ingest | pending | — | fresh-corpus build, corpus-scoped |
| G4-V verify | pending | — | reviewer + adversarial pass |
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
