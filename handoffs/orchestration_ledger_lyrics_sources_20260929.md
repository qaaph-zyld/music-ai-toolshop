# Orchestration ledger · lyrics-sources megaplan · 2026-09-29

- **Plan:** `D:\Projects\.workspace_archive\plans\lyrics-sources-megaplan.md` (adversarially reviewed: `.workspace_archive/reviews/2026-09-29_2326_lyrics-sources-plan.md`, verdict approved-with-fixes)
- **Waves:** `ORCHESTRATION/lyrics_sources/waves_megaplan.json` (agent task prompts embedded; waveR prompts at `prompts/waveR_*.md`)
- **Mode:** waves sequential, gates are USER gates (GATE R after research, GATE 0 after SPEC.md). Orchestrator does not code.

| Wave | Agent(s) | Status | Handoff | Notes |
|---|---|---|---|---|
| WR Research | R1 ccMixter/CC · R2 PD-text · R3 gray audit · R4 standards | ✅ done — 4 handoffs in `.workspace_archive/handoffs/` (20260929_2355) | researcher_lyrsrc_{ccmixter,pdtext,grayaudit,standards}_20260929_2355.md | 12+26+30+19 URLs cited |
| **GATE R** | user | ✅ **PASSED** — roster frozen: auto = sr/en.wikisource, gutenberg, mudcat zip, hymnary, sacred-texts, ccmixter (polite fetch, documented open API), jamendo (env-gated), lrclib (study-only), pdinfo (titles); manual = looperman; catalog-only = voclr/a4u; registry-only = 6 paid packs; cut = musixmatch, FMA, wikimedia commons, contemplator | — | key calls: ccMixter polite-fetch over robots-strict; wikisource API-walk with dump fallback |
| W0 Spec | P1 planner | ✅ done — `SPEC.md` (672 lines) + P1 handoff | `wave_0/P1_handoff.md` + `SPEC.md` | all 8 open Qs surfaced for GATE 0 |
| **GATE 0** | user | ✅ **PASSED** — all recommended options accepted: hymnary = CSV-primary+HTML-fallback; mudcat unflagged = `release_ok=yes`+manifest note; `conditional→yes` via `modified_note`; 5 spec defaults confirmed (no-suffix dirs, in-Python dedup, genius corpus_dir exception, --refresh deferred, jamendo inert adapter) | — | SPEC.md §10 resolutions recorded; wave B added to plan (I6-I8: gutenberg/mudcat, hymnary/sacred_texts, jamendo/lrclib) |
| W1 Infra | I1 implementer (`4f012f06`) | ✅ **done** — `sources/` pkg + registry.json (20 rows) + dispatcher + 53 tests; commits `1adb2d1`, `717d1a1` | `wave_1/I1_handoff.md` | policy gates verified: voclr/looperman/genius fetch → rc=2; A7 confirmed |
| WA Adapters | I2 ccmixter (`65e518f4`) · I3 wikisource+gutenberg (`d5853b3d`) · I4 pdinfo+looperman (`ef66abae`) | ✅ **all done** — I4 `471cdf7`,`eea32b5` (pdinfo pilot **6,750 titles**, looperman zero-network AST-verified); I2 `c72b2ee`,`b5e9898`,`3f086a2` (ccmixter pilot 17/25); I3 `31cc9df`,`2549b89` **committed by orchestrator** (agent session ended pre-commit; orchestrator found+fixed PG double-spacing bug — 0→125 parseable Child variants) | `wave_a/I{2,3,4}_handoff.md` | wikisource live pilot deferred on 429 → relaunched in background; registry merged sr+en→wikisource_pd (19 rows) |
| WB Adapters | I6 mudcat (`aa7764a9`) · I7 hymnary+sacred_texts (`230c7b03`) · I8 jamendo+lrclib (`b6adfe53`) | ✅ **all done** — I6 `0dfe9a9`,`b1750aa` (orchestrator-committed; **8,980 catalog → 1,672 ©-dropped**); I8 `2a14177`,`edefc7d` (lrclib 25/25 synced; jamendo inert); I7 `bf44587`,`ddb4ca6` (orchestrator-committed; sacred-texts 23 fetched, hymnary CSV catalog 527 + 403-deferred fetch) | `wave_b/I{6,7,8}_handoff.md` | 309 tests green across all adapter files |
| W5 Ingest | I5 implementer (`613969f7`) | ✅ **done** — `38027c8`..`22e472e` pushed to origin; 12 license cols on `songs`, `ensure_license_columns()` migrate guard, corpus-scoped rebuild + additive `--incremental`, `populate_song_metrics(song_ids=)`, `rhyme_miner --corpus`, corpus_inventory `--corpus`+license matrix | `wave_5/I5_handoff.md` | **genius invariant proven**: 1425/10654/65912/273801 byte-identical after ingest; 7 corpora / 1,519 songs; incremental verified (0 new on lrclib re-run); 271 tests |
| W5b gap | export_release.py + ccmixter pd-token fix (`d4ab3b99`) | ✅ done — **orchestrator-committed** `7afa490`,`5efa906` (agent tool-rejected at closeout; verified: 50 tests, smoke 69 emitted / 0 genius+lrclib, TASL credits) | `wave_5/I5b_handoff.md` | §8.2 fell between scopes; ccmixter lic=pd → `LicenseRef-public-domain` + 6 JSONs repaired |
| W6 Review | V1 (`08e8302a` — produced nothing, orchestrator ran checklist) | ✅ **APPROVED** — review `reviews/2026-09-30_2018_lyrics-sources-impl.md`; all gates passed: genius invariant verbatim, incremental idempotent, license audit 41/41 sampled matches, ©-containment, release-gate smoke, zero-network looperman | `wave_6/V1_handoff.md` | 2 low nits accepted-risk; closeout exit-1 = other lanes' dirt + 2 unpushed commits |

**Deferred pilots:** wikisource_pd live catalog walk — sr.wikisource.org rate-limited the IP (429 on bare probes), 25+ min walk killed; adapter fixture-verified (18 tests), `--resume` safe, re-run when limit clears. hymnary text-fetch deferred on 403s (catalog built).

## Invariants checked at each wave boundary
- `lyrics.db` genius-pro counts unchanged (corpus_inventory before/after any ingest work)
- no corpus/lyric data committed (`git ls-files` under `data/toolshop/lyrics/`)
- no `import toolshop` inside `Genious_lyrics_extractor/sources/`
- no fetch path exists for `catalog-only`/`manual`/`uncleared` sources
