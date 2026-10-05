# 02 — Data sources

Paths are relative to the **workspace root** (`D:\Projects`) unless they start with a repo name. Every format claim
below was observed on disk on 2026-10-06; the evidence is in brackets. Collectors must tolerate everything listed
under "messiness".

All of these are configured in `toolshop/hub/hub_config.json`, with no absolute paths (rule R4).

## S1 — Git commits (collector `git_log`, W1)

| | |
|---|---|
| Repos | Parent `Music-AI-Toolshop` + every `path` in its `.gitmodules` (9 on 2026-10-06: MAirina_Tucc, Stemmeca_alatkka, mastering_tool, open_DAW, studio, suno_extractor, suno_prompter, track_inventory, track_reverse_engineering) + the linked worktrees each repo reports through `git worktree list --porcelain`. Extra repos are listed under `extra_repos` in the config, which is empty in v1. |
| Command | `git log --all --since=<horizon_days>.days --name-only --format=%x1e%H%x1f%an%x1f%aI%x1f%s%x1f%D` (horizon default 90) |
| Dedupe | By full hash. Worktrees share their parent's object DB, so the same commit appears once and its repo is the canonical repo path |
| Event | `kind=commit`, `ts=author date`, `title=subject`, `repo`, `lane`, `artist`, `refs=[hash]`, `link=git:<repo>@<hash>` |
| Messiness | Most subjects have **no scope**: in 90 days across the parent, studio and MAirina there are 67 `docs:`, 21 `feat:`, 17 `fix:` and 16 `chore:`. Some scopes are changelog IDs, not lanes (`feat(#060)`). Subjects like `submodule: studio -> 8a9a5f3` are pointer bumps. |

**Lane and artist attribution.** Rules are applied in this order; the first match wins. Rules are data, defined in
`hub_config.json` → `lane_rules`.

1. **Path rules.** A majority vote over the changed files:
   - `artists/<name>/…` (studio) gives `artist=<name>` and `lane=<name>`.
   - `ORCHESTRATION/<lane>/…` gives `lane=<lane>`.
   - Additional `path_prefix → lane` pairs, e.g. `MAirina_Tucc/` → `mairina`, `toolshop/hub/` → `hub`,
     `analysis/` or `pipeline/` in studio → `studio-engine`.
2. **Scope alias.** The conventional-commit scope mapped through `lane_aliases`
   (`beat-flip`/`beat` → `nachtfahrt`, `ogcm` → `ogcm`, `lyrics` → `lyrics`, `mairina` → `mairina`,
   `vocal-chain` → `studio-engine`). Scopes matching `^#\d+$` are ignored here.
3. **Repo default.** The submodule name, e.g. `suno_extractor`.
4. Otherwise `lane=null`, shown as "unassigned".

`submodule: <child> -> <sha>` commits in the parent get `kind=pointer_bump`, with the child repo linked.

## S2 — Session records (collector `sessions`, W1)

| | |
|---|---|
| Path | `ai_dev_meta_layer/memory/episodic/sessions/*.md` |
| Filename schemes | **A:** `YYYY-MM-DD_HHMMSS_<slug>.md` (280 files) and **B:** `session_record_YYYYMMDD_<slug>.md` (10 files). Others (README.md, `devin-*.json`, 3 files) are skipped. |
| Title | First `# ` line. Both `# Session Record — …` and `# Session record — …` exist. |
| Fields | Optional bullets `- **Date:**`, `- **Project:**`, `- **Scope:**`, `- **Plan:**` (scheme B). Scheme A often has only `**Session scope:**` prose. |
| Timestamp | From the filename. Scheme A has date + time; scheme B has the date only, with the time taken from the file mtime and flagged `ts_approx=true`. |
| Music filter | Keep a record when its first 40 lines (which include the title and the Project field) contain any of the `music_keywords`, **case-insensitive** (config: `Music-AI-Toolshop`, `studio`, `music_toolshop_v2`, `MAirina`, `Tale`, `Zeldi`, `MixAll`, `PE3`, `OGCM`, `OGCJ`, `Nachtfahrt`, `lyrics`, `Stemmeca`, `suno`, `audition`, …). Records that don't match are skipped (they are corporate or framework work). |
| Event | `kind=session`, `title`, `excerpt` (first 300 chars of "What happened" or the scope), `refs`=receipts candidates, `link=file:<path>` |
| Receipts | Yes (see `03` § Receipts) |

## S3 — Handoffs (collector `handoffs`, W1)

| | |
|---|---|
| Path | `.workspace_archive/handoffs/*.md` (86 on 2026-10-06), named `YYYY-MM-DD_HHMMSS_<slug>.md` |
| Header | `# Handoff: <title>`, `**Date**: YYYY-MM-DD HH:MM`, `**Project**: \`…\``, `**Previous Handoff**`, `**Session Record**` [seen in `2026-10-04_010000_oss_w1b_mosqito_plus_audition_review.md`] |
| Sections used | `## Session Summary` (excerpt), `## Known Issues`, `## Remaining Work` (shown as text; **never** converted to inbox items, see `07` D6) |
| Spent flag | A handoff is **spent** when a newer session record cites its filename (the `handoff-freshness` rule). It is shown greyed with "consumed by <record>". |
| Music filter | Same as S2 (first 40 lines, case-insensitive `music_keywords`) |
| Event | `kind=handoff`, plus receipts |

## S4 — Ledgers (collector `ledgers`, W1)

| | |
|---|---|
| Paths | `Music-AI-Toolshop/ORCHESTRATION/*/LEDGER.md` and `…/ledger.md`, `Music-AI-Toolshop/handoffs/*.md` (orchestration ledgers), `Music-AI-Toolshop/studio/artists/*/ledgers/*.md`, `Music-AI-Toolshop/studio/handoffs/*.md`, `Music-AI-Toolshop/studio/ORCHESTRATION/*/ledger.md` (27 files matched on 2026-10-06) |
| Shapes | At least six table headers [counted]: `\| Wave \| Agent \| Status \| Handoff \| Notes \|` ×4, `\| Wave \| Status \| Agent \| Artifact \| Notes \|` ×2, `\| Wave \| Agent(s) \| Status \| Handoff \| Notes \|` ×2, `\| Wave \| Agent \| State \| Handoff \|` ×2, `\| Gate \| Status \| Evidence \|` ×2, `\| Wave \| Name \| Mode \| Status \| Gate \|` ×1 |
| Treatment | Stored as a **Doc**: path, lane (from its folder), mtime, title, and the **last table row + last heading** as an excerpt. A ledger with a new mtime yields one `kind=ledger_update` event per index run. **No cell parsing into state.** |

## S5 — Listening comments (collector `audition`, W1)

| | |
|---|---|
| Path | `Music-AI-Toolshop/Stemmeca_alatkka/stems/_audition_comments/<page-slug>.jsonl` [`scripts/audition_review.py:38` `COMMENTS_DIR`] |
| Line | `{"ts_utc": "2026-10-05T18:02:47+00:00", "audio": "B_vocal2_win.mp3", "verdict": "pick", "comment": "0:01-0:22"}` [mojgrad_khansovac_122.jsonl]. Verdicts: `pick ok flag reject` |
| Event | One `kind=listen_verdict` event per line, grouped in the UI by page and minute. Link: `http://127.0.0.1:8778/<page>/` (the page path comes from the slug mapping in `audition_review._slug`). Reverse-map it, or store the page path from the pack index. |
| Note | The `stems/` tree is the live OGCJ/Nachtfahrt lane's output: **read-only, never touched**. |

## S6 — Inbox (collector `inbox` through `store`, W1/W2)

| | |
|---|---|
| Path | `TOOLSHOP_DATA_DIR/hub/inbox.jsonl`. This is the hub's own **source of truth**, append-only. |
| Writers | CLI `python -m toolshop.hub ask/resolve/snooze/reopen/note` (agents and the user), plus UI POSTs |
| Schema | `03_DATA_MODEL.md` § Inbox |
| Seed | `ORCHESTRATION/hub/seed_inbox.jsonl`, imported once in W2 by `python -m toolshop.hub import-seed` (idempotent by id) |
| Backup | Must be added to `toolshop/backup.py` coverage, with a test asserting it appears in the manifest (W5; AGENTS.md "Backups are verified by coverage") |

## S7 — Repo state (collector `repo_state`, W3)

| Per repo/worktree | Command |
|---|---|
| Branch, HEAD | `git rev-parse --abbrev-ref HEAD`, `git rev-parse --short HEAD` |
| Dirty | `git status --porcelain` lines, split into modified / untracked. Submodule dirtiness uses the child's own status |
| Ahead/behind | `git rev-list --left-right --count @{u}...HEAD` (no fetch, "as of last fetch") |
| Worktrees | `git worktree list --porcelain` |
| Stashes | `git stash list` count |
| Pointer drift | For each submodule, compare the parent's gitlink (`git ls-tree HEAD <path>`) with the child's HEAD |
| Orchestrator marker | `.workspace_archive/orchestration/ACTIVE`: the `task:` line plus every `override:` line, shown as a warning badge because one override suspends the guard workspace-wide (`orchestrator-boundary` rule) |

## S8 — Artists (collector `artists`, W4)

| | |
|---|---|
| ARTIST.md | `Music-AI-Toolshop/studio/artists/<name>/ARTIST.md`. Songs table header `\| song \| source \| rounds \| status \|` [tale, zeldi, mixall, pe3, arpino]. Sections `## Voice profile` / `## Voice profile & chain` |
| Profiles | `Music-AI-Toolshop/studio/voice_profiles/<name>.json`: `target.*` fields, `consequence.snr_db`, `sources.recording_path`, `sources.notes` (low-confidence text). Engine fix state 2026-10-06: f0 and levels trustworthy; sibilance measured on fricative events (F15), capped ≈8.95 kHz. PE3 SNR 0.89 dB means low confidence. |
| Chain maps | `Music-AI-Toolshop/studio/artists/<name>/**/chain_map*.svg`, produced by `/mix_svg_tree`. Its SKILL text still says `ORCHESTRATION/<song>/` and must be updated to `artists/<name>/rounds/<round>/` in W4 (framework repo `ai_dev_meta_layer`, separate commit). |
| Listening packs | `Music-AI-Toolshop/Stemmeca_alatkka/stems/**/index.html` (pack pages), linked to an artist through `hub_config.json` → `pack_artist_rules` (path substring → artist) |
| Sources | The songs-table `source` column (`D:\2026\…` or `data/…`): a read-only link, shown with an exists ✓/✗ check |

## S9 — CHANGELOG entries (optional, W3)

`### Answer #NNN - <title>` + `**Timestamp:** YYYY-MM-DD` [Music-AI-Toolshop/CHANGELOG.md]. Becomes `kind=changelog`.
IDs ≤ #084 are **not unique** (`CHANGELOG.md` ID note), so key on file position + title, never on ID alone.
