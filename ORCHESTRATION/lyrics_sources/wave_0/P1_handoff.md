# P1 handoff — W0 planner, lyrics-sources megaplan

**Delivered:** `ORCHESTRATION/lyrics_sources/SPEC.md` (design freeze draft for GATE 0).
No implementation code written; no other files touched.

## What the spec freezes (and why)

1. **License model** — 9-value `license_tier` enum (`pd, cc0, cc-by, cc-by-sa,
   cc-by-nc, paid-rf, uploader-terms, study-only, uncleared`) × 3-value
   `fetch_policy` (`auto, catalog-only, manual`) × 3-state `release_ok`
   (`yes, conditional, no`) — the megaplan draft table, unchanged after checking
   against R1-R4. Per-item fields adopt Openverse names verbatim per R4 §3/§5 +
   GATE R instruction: `license` (SPDX token), `license_url`, TASL tuple
   (`creator, creator_url, source_url, copyright_notice, modified_note`),
   `foreign_identifier`, `derived_from`.
   - **PD convention decision:** `LicenseRef-public-domain` (no standard PD SPDX id
     exists — R4 §2). `CC0-1.0` reserved for true dedications. ccMixter `lic=pd`
     → `LicenseRef-public-domain`; `sampling+` → `LicenseRef-sampling-plus-1.0`.
   - Attribution is **computed** at export (`tasl_credit`), not stored (R4 §3).

2. **`sources/registry.json`** — committed config at
   `Genious_lyrics_extractor/sources/registry.json`. Required fields
   `{id, name, base_url, license_tier, fetch_policy, adapter, corpus_tag,
   license_ref_default, notes}` + optional `corpus_dir`, `env_gate`, `categories`,
   `politeness`. 20 rows frozen incl. a `genius` row (the one `corpus_dir: "genius"`
   exception vs tag `genius-pro`, lyricsdb.py:30) and a `cut` section
   (musixmatch/fma/wikimedia_commons/contemplator with reasons).

3. **Corpus layout** — `data/toolshop/lyrics/<corpus_dir>/<category>/*.json` +
   `_catalog.json` (resumable work queue per AGENTS.md batch rules) + `_index.json`.
   **Non-artist corpora use plain collection slugs — NO `-solo` suffix required**:
   `_derive_role_and_target` default `("solo", dirname)` (lyricsdb.py:99) is adopted
   as the contract; `-featured/-duo/-trio` forbidden for new corpora. Category slugs
   frozen per corpus (e.g. sr-wikisource: `zenske/epske/lirske/vuk-zbirke/erlangen/
   ostalo`; ccmixter: license-classed `acappella-by/pd/nc/sa` so the disk layout is
   self-auditing).

4. **lyricsdb migration — option (a), columns on `songs`.** License is 1:1 and on
   every read path; a side table adds a permanent join for zero benefit. New cols:
   `license_tier` (DEFAULT 'study-only'), `license_ref`, `license_url`,
   `release_ok` (DEFAULT 'no'), TASL cols, `foreign_identifier`, `script`,
   `derived_from`. `ensure_license_columns()` = `PRAGMA table_info` + ALTER +
   backfill genius rows to `study-only`/`proprietary`/`no`. **Dedup: in-Python
   corpus-scoped pre-check** (`SELECT title, primary_artist, foreign_identifier
   WHERE corpus=?` → `_dedup_key`), no stored norm columns — normalization stays
   single-sourced in `normalize_text`/`_dedup_key` (:371-403); cross-corpus dupes
   are correct per F9.

5. **`build_database(root, db_path=None, corpus=None, incremental=False)`.**
   Default = corpus-scoped rebuild: `DELETE FROM songs WHERE corpus=?` (FK cascades
   verified :427-541), other corpora untouched, `db_path.unlink()` removed.
   `incremental=True` = pure additive, pre-check skip on dedup-key OR
   `foreign_identifier`, metrics/rhymes only for new ids — **requires
   `populate_song_metrics(conn, song_ids=None)` param** (currently inserts
   unconditionally for all songs, lyrics_metrics.py:129-160).
   CLI: `--corpus` (default genius-pro), `--incremental|--rebuild`, `--root`/`--db`
   unchanged (cli.py:909-924, 2221-2232).

6. **Adapter contract** — `sources/<name>.py`: `SOURCE_ID`,
   `iter_catalog() → CatalogEntry`, `license_of() → LicenseInfo` (may only
   downgrade tier default), `fetch_lyrics() → song JSON v2`. catalog-only sources
   omit `fetch_lyrics` entirely; `manual` sources (looperman) may not contain any
   network code — enforced by contract tests. `_common.py` vendors `RobotsPolicy`
   (genius_adapter.py:43-117), `polite_get` (pacing/UA/backoff), `LICENSE_URL_MAP`
   (Openverse URL-fragment→SPDX pattern, R4 §1.1), `tasl_credit`, catalog IO.
   No `import toolshop` (70s init penalty, F-B1).

7. **Tests** — `tests/test_lyrics_sources_*.py` + `sys.path` shim; committed
   fixtures only from cleared sources (TASL in fixture, CREDITS.md); gray =
   synthetic structure no lyric text; `@pytest.mark.slow` for live fetches;
   required contract tests enumerated (registry↔adapter, no-fetch enforcement,
   license mapping, migration on v1 fixture DB, incremental pre-check, export
   audit).

8. **Reconciliation/export** — `corpus_inventory.py --corpus` extension (currently
   hardcodes genius-pro at :10-64) + `export_release.py --release-cleared` reading
   lyrics.db + registry, emitting only `release_ok=yes`, `CREDITS.md` with computed
   TASL lines, `RELEASE_MANIFEST.json` with pending-decision list for
   `conditional` items.

9. **Per-source ingest notes** frozen (§9): ccmixter by+pd lane w/ lyric-header
   extraction; sr wikitext-not-extracts + license-template scan + script field +
   clean_lyrics translit+fold; gutenberg catalog-first + harvest/mirror only;
   mudcat ©-drop at catalog stage; hymnary ≤1930 instance resolution; jamendo env
   gate; lrclib seed-driven catalog + plainLyrics/syncedLyrics/lyricsfile capture;
   pdinfo titles-only; looperman local-file-only.

## Assumption register

A1-A7 **all resolved** (details in SPEC §10): R1 verified ~45-60% ccMixter lyric
yield and ~650-750 release-safe pells; R2 live-verified the ~10k+ sr.wikisource
corpus and MediaWiki etiquette; R3 confirmed gray-source bans and LRCLIB's
`lyricsfile` bonus; A7 verified early — `.gitignore:47` ignores new corpus dirs.

## Open questions for GATE 0 (also in SPEC §10)

1. Non-artist dirs carry no `-solo` suffix; `("solo", dirname)` default adopted —
   confirm.
2. Jamendo lyric fill-rate unknown without a client_id (R1 §5 caveat) — inert
   env-gated adapter OK?
3. Hymnary CSV export path unverified (widgets 403'd to researcher, R2 §6) —
   adapter build gated on manual verification?
4. Mudcat unflagged items get `release_ok=yes` despite not-for-profit DT charter —
   kept as yes + manifest note for corpus/internal release; confirm.
5. `conditional→yes` via per-item user decision in `modified_note` — acceptable
   mechanism vs a separate decisions file?
6. Dedup: in-Python pre-check, no `title_norm`/`artist_norm` columns — confirm.
7. Genius registry row + `corpus_dir: "genius"` exception — confirm.
8. `incremental` has no upstream-refresh path (skips `foreign_identifier`
   matches); `--refresh` deferred — flag if wanted.

## Issues / notes for the orchestrator

- `songs.primary_artist` is `NOT NULL` (lyricsdb.py:414) — spec requires adapters
  to emit display placeholders ('Narodna pesma', 'Traditional', uploader name).
- `v_artist_stats` view hardcodes `corpus='genius-pro'` (lyrics_metrics.py:181) —
  intentionally left genius-scoped; new corpora report via `corpus_inventory`.
- `corpus_inventory.py` hardcodes `corpus='genius-pro'` at five sites — extension
  is a W5 task.
- waves_megaplan WA builds only 4 adapters (ccmixter, wikisource, pdinfo,
  looperman); remaining auto-fetch adapters (gutenberg, mudcat, hymnary,
  sacred_texts, jamendo, lrclib) need scheduling in later adapter waves — registry
  covers all.
- Megaplan dispatch note: `toolshop closeout` must exit 0 at session end; spec
  adds no third-party deps beyond existing `[lyrics]` extras (`requests`, `bs4`,
  `cyrtranslit`) — consistent with megaplan "not doing".
