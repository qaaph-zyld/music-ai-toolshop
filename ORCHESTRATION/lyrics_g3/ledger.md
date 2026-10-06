# Orchestration ledger — lyrics-g3 (P3 genius-pro roster expansion)

Lane: `lyrics-g3` | Worktree: `Music-AI-Toolshop-wt-lyrics-g3` | Megaplan: `.workspace_archive/plans/lyrics-genius-expansion-megaplan.md`
GATE P3: approved 2026-10-06 — all roster artists with researched cohort tags.

| Wave | Status | Commit | Evidence |
|---|---|---|---|
| G3-pre | DONE | — | worktree at `44888ed`; ACTIVE override scoped to lane |
| G3-I | DONE | `1700720`, `8a82573` | `extract_roster.py` + `roster_g3.json` (16 artists, pinned ids) + `COHORT_MAP`/`_FOLDER_COHORT_MAP` + `tests/test_lyrics_genius_roster.py` — 18/18 green; `8a82573` fixed lyricsgenius 3.x `.id`→`_body` (corpus-wide `genius_song_id=null` bug) |
| Dry-run resolve | DONE | — | 14/16 clean OK; Fox+Zoi top-hit wrong → pinned ids (13438, 1584694); song-probe verified all pins |
| G3-B fetch | RUNNING (bg) | — | `extract_roster.py --resume --delay 1.5` → canonical `data/toolshop/lyrics/genius`; Zera 21 + Mimi 112 done; duo cat live-verified (`fox-mimi-mercedez-duo`); ~9 songs/min ⇒ ETA hours; resume-safe (`_fetch_status_g3.json` done-gates) |
| G3-DB ingest | pending | — | `build_unified_index` + `build_database(corpus='genius-pro', incremental=True)`; invariant: pre-1,425 rows unchanged |
| G3-V review | pending | — | refutation gates per megaplan |
| Merge + Answer ID | pending | — | user-gated session (P2 convention) |

## Roster (FINAL — pinned)

See megaplan Roster table. 16 artists; all `genius_artist_id` pinned after
song-probe verification. `Bulevar` = YU new-wave band (id 369563, ~2 songs,
cohort provisional `pop`).
