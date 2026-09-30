# W5 / I5 handoff — multi-corpus lyricsdb + license columns + `--corpus` plumbing

**Wave:** 5 (implementer I5) of the lyrics-sources megaplan.
**Spec basis:** `ORCHESTRATION/lyrics_sources/SPEC.md` §4 (option-a license columns +
migrate-on-open), §5 (`build_database` signature + mode semantics + CLI), §8.1
(`corpus_inventory` extension). Where the generic wave text differed, SPEC won.
**Commits:** `38027c8` `feat(#070): lyrics-sources W5 - multi-corpus lyricsdb
(license cols, corpus rebuild/incremental, --corpus plumbing)` (code + tests +
CHANGELOG + inventory evidence); this handoff file landed in the immediately
following `docs(#070)` commit. CHANGELOG entry: **Answer #070**.

## What landed

### `toolshop/lyricsdb.py`
- **`songs` gains 12 license/provenance columns** (SPEC §4.1) in `_SCHEMA_SQL`:
  `license_tier` (DEFAULT `'study-only'`), `license_ref` (song-JSON `license`
  SPDX token), `license_url`, `release_ok` (DEFAULT `'no'`), `creator`,
  `creator_url`, `source_url`, `copyright_notice`, `modified_note`,
  `foreign_identifier`, `script`, `derived_from`.
- **`ensure_license_columns(conn)`** — migrate-on-open guard (§4.2): PRAGMA
  table_info → `ALTER TABLE` per missing column → corpus-scoped genius backfill
  (`study-only`/`proprietary`/`no`; `proprietary` not `unknown` per R4 §5).
  Idempotent; returns backfilled-row count. Called by `build_database` after
  `_create_schema`, and vendored into `corpus_inventory.py` (folder scripts must
  not `import toolshop` — eager `__init__` ≈70 s, F-B1).
- **`build_database(root, db_path=None, corpus=None, incremental=False)`** (§5):
  - `corpus=None` → `CORPUS_TAG` (`'genius-pro'`) — back-compat.
  - **`incremental=False` = corpus-scoped rebuild**: `DELETE FROM songs WHERE
    corpus=?` (FK `ON DELETE CASCADE` wipes that corpus's sections/lines/
    metrics/rhymes/tokens/entities/section_topics). The whole-DB
    `db_path.unlink()` is **removed** — other corpora are never touched.
  - **`incremental=True` = additive-only**: seeds `db_keys`/`db_fids` from
    `SELECT title, primary_artist, foreign_identifier WHERE corpus=?` through
    `_dedup_key` (in-Python, no norm columns, §4.3); files matching either arm
    are skipped and counted `already_present`; metrics/rhymes computed only for
    newly inserted ids.
  - Summary gains `corpus`, `incremental`, `already_present`,
    `license_backfilled`; `lines_ingested` is now corpus-scoped.
- **`_insert_song`** — `corpus` + `license_defaults` params; license fields read
  index-entry → song-JSON → per-corpus defaults (`_corpus_license_defaults`,
  resolved from `sources/registry.json` by file read — builtin
  `genius-pro → study-only/proprietary/no` fallback keeps zero dependency on
  the extractor folder).
- **`build_unified_index`** — copies `_INDEX_LICENSE_FIELDS` into every index
  entry (license rides the index, F8) + `foreign_identifier` intra-scan dedup.
- **`_scan_song_files`** — now skips `_`-prefixed dirs too (`_src`, `_cache`,
  `_import`, `_quarantine_*` can never become a "category"). Defensive; no
  behavior change on current data (those dirs hold no non-`_` `.json` files).
- **`corpus_dir_for(corpus)`** — registry `corpus_tag → corpus_dir`
  (`genius-pro → genius` exception honored); `None` for unknown tags.

### `toolshop/lyrics_metrics.py`
- `populate_song_metrics(conn, song_ids=None)` — `None` = all songs (legacy);
  explicit list scopes inserts (SPEC §5.2 — incremental/rebuild pass only this
  corpus's ids, so other corpora never accumulate duplicate metrics).

### `toolshop/rhyme_miner.py`
- `get_artist_rhyme_stats(conn, artist=None, corpus="genius-pro")` and
  `get_artist_rhyme_fingerprints(conn, artist=None, corpus="genius-pro")` —
  all 4 hardcoded `corpus='genius-pro'` sites parametrized via `_corpus_where`;
  `corpus="all"`/`None` lifts the filter. Default = identical SQL to before.

### `toolshop/cli.py`
- `lyrics build-db [--corpus TAG] [--root PATH] [--db PATH]
  [--incremental | --rebuild]` — `--corpus` (default `genius-pro`) resolves
  `--root` via `corpus_dir_for` → `<data>/lyrics/<corpus_dir>`; unknown corpus
  (not in registry AND no matching dir) → `parser.error` (exit 2), never a
  silent empty build; missing corpus dir → same. Modes mutually exclusive,
  default rebuild.
- `lyrics rhymes` gains `--corpus` (default `genius-pro`; `'all'` = all corpora)
  → `get_artist_rhyme_stats`.

### `Genious_lyrics_extractor/corpus_inventory.py` (rewritten)
- argparse `--corpus <tag>` (default: all corpora) + `--db`.
- `--corpus genius-pro` → **byte-identical legacy report shape** (verified by
  `diff` below); structural counts are now corpus-scoped via JOINs so the shape
  survives a multi-corpus DB.
- Other corpora → generic block (songs/sections/lines/rhyme rows/rhyme metrics
  + per-category counts).
- License block (default mode + non-genius `--corpus`): `license_tier ×
  release_ok` matrix per corpus, TASL gap counts (missing
  creator/source_url/license_ref; releasable-with-gaps), `derived_from` counts.

## Real ingest (executed, real `data/toolshop/lyrics/lyrics.db`)

| corpus | songs | sections | lines | rhyme rows | mode |
|---|---|---|---|---|---|
| genius-pro | 1425 | 10654 | 65912 | 273801 | `--rebuild` (v1→v2 migrate-on-open fired) |
| ccmixter | 17 | 115 | 758 | 2393 | rebuild |
| gutenberg_pd | 3 | 55 | 116 | 309 | rebuild |
| hymnary | 1 | 5 | 20 | 77 | rebuild |
| lrclib | 25 | 169 | 1219 | 4058 | rebuild, then `--incremental` proof |
| mudcat-digitrad | 25 | 341 | 893 | 2713 | rebuild |
| sacred-texts | 23 | 2832 | 2832 | 45767 | rebuild |

Skipped (no song JSONs on disk — catalog/registry-only per SPEC):
`wikisource_pd` (empty dir — wave-A pilot was 429-rate-limited), `looperman`
(manual catalog only), `pdinfo` (title index only). `voclr`/`acapellas4u`/paid
packs have no corpus dirs and no adapters by design.

Incremental proof on real data:
`toolshop lyrics build-db --corpus lrclib --incremental` →
`Incremental: 25 existing 'lrclib' songs keyed` / `Ingested: 0` /
`Already present: 25` / `Rhymes computed: 0` / `Metrics computed for 0 songs`
(exit 0) — pure additive, nothing re-derived.

## corpus_inventory BEFORE (verbatim — v1 script, 2026-10-01, commit `38027c8~`)

```
=== CORPUS INVENTORY ===

Total songs: 1425

--- Solo songs by artist (1315 total) ---

  [drill_trap]
    jala                     : 199
    rasta                    : 109
    devito                   : 106
    corona                   : 92
    coby                     : 79
    buba                     : 73
    voyage                   : 67
    tng                      : 40
    jala-buba                : 20
    indodjija                : 9
    jala-buba-coby           : 1

  [pop]
    maya-berovic             : 145
    senidah                  : 82
    nikolija                 : 70
    ana-nikolic              : 68
    relja                    : 59
    henny                    : 44
    breskvica                : 40
    jala-buba                : 6
    coby                     : 3
    buba                     : 2
    jala                     : 1

--- Featured songs (110 total) ---
  rasta                     [NULL      ]: 24
  corona                    [NULL      ]: 21
  henny                     [NULL      ]: 9
  voyage                    [NULL      ]: 9
  devito                    [NULL      ]: 7
  tng                       [NULL      ]: 6
  senidah                   [NULL      ]: 5
  indodjija                 [NULL      ]: 4
  nikolija                  [NULL      ]: 3
  relja                     [NULL      ]: 3
  breskvica                 [NULL      ]: 2
  breskvica                 [drill_trap]: 6
  corona                    [drill_trap]: 2
  rasta                     [drill_trap]: 2
  ana-nikolic               [drill_trap]: 1
  devito                    [drill_trap]: 1
  henny                     [drill_trap]: 1
  nikolija                  [pop       ]: 2
  breskvica                 [pop       ]: 1
  devito                    [pop       ]: 1

--- Structural counts ---
  Sections: 10654
  Lines: 65912
  Rhyme rows: 273801
  Song rhyme metrics: 1425

--- Files on disk by category ---
  ana-nikolic-featured          : 1
  ana-nikolic-solo              : 68
  breskvica-featured            : 9
  breskvica-solo                : 40
  buba-solo                     : 75
  coby-solo                     : 82
  corona-featured               : 23
  corona-solo                   : 92
  devito-featured               : 9
  devito-solo                   : 106
  henny-featured                : 10
  henny-solo                    : 44
  indodjija-featured            : 4
  indodjija-solo                : 9
  jala-buba-coby-trio           : 1
  jala-buba-duo                 : 26
  jala-solo                     : 200
  maya-berovic-solo             : 145
  nikolija-featured             : 5
  nikolija-solo                 : 70
  rasta-featured                : 26
  rasta-solo                    : 109
  relja-featured                : 3
  relja-solo                    : 59
  senidah-featured              : 5
  senidah-solo                  : 82
  tng-featured                  : 6
  tng-solo                      : 40
  voyage-featured               : 9
  voyage-solo                   : 67

--- NULL cohort solo artists (need COHORT_MAP entry) ---
```

## corpus_inventory AFTER — `--corpus genius-pro` (verbatim diff proof)

`corpus_inventory.py --corpus genius-pro` on the 7-corpus DB, diffed against
the file above:

```
$ python Genious_lyrics_extractor/corpus_inventory.py --corpus genius-pro > inventory_after_genius.txt
$ diff inventory_before.txt inventory_after_genius.txt
(no output — IDENTICAL; exit 0)
```

**Reconciliation: genius-pro counts byte-identical — 1425 / 10654 / 65912 /
273801 / 1425 unchanged after v2 migration + 6-corpus ingest.**

## corpus_inventory AFTER — all corpora (verbatim, non-genius blocks + license)

```
=== corpus: ccmixter ===
Total songs: 17
  Sections: 115  Lines: 758  Rhyme rows: 2393  Rhyme metrics: 17
  Categories:
    acappella-by                  : 11
    acappella-pd                  : 6

=== corpus: gutenberg_pd ===
Total songs: 3
  Sections: 55  Lines: 116  Rhyme rows: 309  Rhyme metrics: 3
  Categories:
    child-ballads                 : 3

=== corpus: hymnary ===
Total songs: 1
  Sections: 5  Lines: 20  Rhyme rows: 77  Rhyme metrics: 1
  Categories:
    pre-1931                      : 1

=== corpus: lrclib ===
Total songs: 25
  Sections: 169  Lines: 1219  Rhyme rows: 4058  Rhyme metrics: 25
  Categories:
    tracks                        : 25

=== corpus: mudcat-digitrad ===
Total songs: 25
  Sections: 341  Lines: 893  Rhyme rows: 2713  Rhyme metrics: 25
  Categories:
    dt                            : 25

=== corpus: sacred-texts ===
Total songs: 23
  Sections: 2832  Lines: 2832  Rhyme rows: 45767  Rhyme metrics: 23
  Categories:
    child-ballads                 : 23

=== LICENSE / RELEASE READINESS ===

  [genius-pro]
    study-only      release_ok=no          : 1425

  [ccmixter]
    cc-by           release_ok=yes         : 11
    cc0             release_ok=yes         : 6

  [gutenberg_pd]
    pd              release_ok=yes         : 3

  [hymnary]
    pd              release_ok=yes         : 1

  [lrclib]
    study-only      release_ok=no          : 25

  [mudcat-digitrad]
    pd              release_ok=yes         : 25

  [sacred-texts]
    pd              release_ok=yes         : 23

--- TASL gaps (missing creator / source_url / license_ref) ---
  genius-pro           missing creator=1425  source_url=1425  license_ref=0  (of 1425); releasable-with-gaps: 0
  ccmixter             missing creator=0  source_url=0  license_ref=0  (of 17); releasable-with-gaps: 0
  gutenberg_pd         missing creator=0  source_url=0  license_ref=0  (of 3); releasable-with-gaps: 0
  hymnary              missing creator=0  source_url=0  license_ref=0  (of 1); releasable-with-gaps: 0
  lrclib               missing creator=25  source_url=0  license_ref=0  (of 25); releasable-with-gaps: 0
  mudcat-digitrad      missing creator=0  source_url=0  license_ref=0  (of 25); releasable-with-gaps: 0
  sacred-texts         missing creator=0  source_url=0  license_ref=0  (of 23); releasable-with-gaps: 0

--- derived_from links ---
  genius-pro          : 0
  ccmixter            : 0
  gutenberg_pd        : 0
  hymnary             : 0
  lrclib              : 0
  mudcat-digitrad     : 0
  sacred-texts        : 0
```

(The genius-pro block at the top of the all-corpora run is the byte-identical
legacy block shown above.) Evidence files committed alongside this handoff:
`wave_5/inventory_before.txt`, `inventory_after_genius.txt`,
`inventory_after_all.txt`.

## Tests

- `pytest tests/test_lyricsdb_multicorpus.py -x -q` → **15 passed** (exit 0,
  90 s — `import toolshop` eager-init dominates).
  Covers: cross-corpus duplicates kept (F9), intra-corpus dedup, corpus-scoped
  rebuild leaving other corpora byte-identical, incremental additivity run
  twice → same counts + `already_present`, fid-arm rename skip, rebuild
  replacing only its corpus, license-field ingestion, corpus defaults on
  absent license block, v1 migrate-on-open (`ensure_license_columns` adds 12
  cols + backfills `study-only`/`proprietary`/`no`, idempotent), fresh-schema
  no-op, genius default unchanged, `corpus_dir_for`, rhyme stats/fingerprints
  corpus boundaries (`genius-pro`/`pd-corp`/`all`/artist×corpus).
- `pytest tests/test_lyricsdb.py tests/test_rhyme_miner.py -x -q` →
  **140 passed, 1 skipped** (exit 0, 115 s).
- `pytest tests/test_brief_generator.py tests/test_draft_scorer.py
  tests/test_fingerprint.py tests/test_rimer_db.py -x -q` →
  **47 passed, 1 skipped** (exit 0, 413 s).
- `pytest tests/test_{flow_analyzer,collab_analysis,l3_report,lexicon,themes,
  theme_comparator,annotate,cliche_checker}.py -x -q` → **69 passed** (exit 0,
  365 s).
- Total touched-scope sweep: **271 passed, 2 skipped** — no regressions.

## CLI verification quotes

- `lyrics build-db --corpus genius-pro --rebuild` → `Done. Songs: 1425,
  Sections: 10654, Lines: 65912, Duplicates dropped: 45, Already present: 0`
  (exit 0) — matches pre-migration counts exactly.
- `lyrics build-db --corpus ccmixter` → `Songs: 17 ...` resolved root
  `data\toolshop\lyrics\ccmixter` via registry (no `--root` needed).
- `lyrics build-db --corpus nonexistent-corpus` → **exit 2**,
  `toolshop: error: Unknown corpus 'nonexistent-corpus': not in
  sources/registry.json and no directory ...lyrics\nonexistent-corpus — never
  a silent empty build.`
- `lyrics rhymes --corpus mudcat-digitrad` → only mudcat artists
  (`Traditional 19/2163`, `Woody Guthrie`, `Robert Burns`, …); `--corpus all`
  → cross-corpus artist list incl. genius-pro.

## Notes / deviations

1. **`--corpus genius-pro` inventory excludes the license block** — SPEC §8.1
   "output stays the existing report shape" + the hard "before/after must match
   exactly" constraint. Genius license info IS shown in the default all-corpora
   run's license matrix (`study-only/no` × 1425).
2. **`_scan_song_files` now skips `_`-dirs** — defensive; current corpora hold
   no ingestible JSON under `_src`/`_cache`/`_import`/`_quarantine_*`, so zero
   behavior change today; prevents a future `_`-dir from becoming a "category".
3. **ccmixter tier wrinkle (adapter data, not W5 scope):** the 6 `acappella-pd`
   items carry `license_tier='cc0'` + `license_ref='CC0-1.0'` (adapter-resolved
   per-item downgrade of the cc-by row default). SPEC §1.3 says ccMixter `lic=pd`
   items should be `LicenseRef-public-domain` — flag to W6 for the license
   audit; the DB faithfully recorded what the adapter wrote.
4. **`song_metrics` rows exist for all 1,519 songs** (scoping is by insert call,
   not corpus) — expected; `v_artist_stats` view stays `genius-pro`-scoped per
   SPEC §5.2.
5. **ensure_license_columns vendored** into `corpus_inventory.py` (pointer
   comment to `lyricsdb.py`) — the folder can't `import toolshop` (F-B1).
   `export_release.py` (W6) should vendor the same 25 lines or move the helper
   to `sources/_common.py` — not done here (outside wave-5 file scope).
6. `ingested_at` differs per rebuild (timestamp) — counts/rows identical;
   the invariant is about content, and corpus counts + category breakdowns are
   byte-identical.

## Blockers / risks for W6

- `wikisource_pd` corpus dir exists but is **empty** (wave-A sr pilot hit HTTP
  429) — release-export smoke can't cover it until fetched; the merged corpus
  tag `wikisource_pd` resolves correctly via registry when data lands.
- `export_release.py` (§8.2) is W6 scope — `ensure_license_columns` must be
  vendored/moved for it to self-heal a v1 DB (see note 5).
- `derived_from` is 0 everywhere — no adapters emit it yet; column exists.
- Other lanes' dirty files remain in the tree (MAirina_Tucc, ogcm_flip,
  scratch_*.html, `nul`, lyrics_research/, `.scratch_i6/`, submodule pointers
  `mastering_tool`/`suno_prompter`) — **not staged, not mine**.
