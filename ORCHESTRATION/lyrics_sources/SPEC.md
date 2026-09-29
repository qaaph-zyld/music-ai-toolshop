# SPEC — lyrics-sources: license-tiered corpus expansion (W0 design freeze)

**Status:** draft for GATE 0 user review. Freezes the license model, registry schema,
corpus layout, `lyricsdb` migration, `build_database` signature, adapter contract,
test conventions, and export contract for waves W1/WA/W5/W6.

**Inputs:** megaplan `d:/Projects/.workspace_archive/plans/lyrics-sources-megaplan.md`;
WR handoffs R1 (ccMixter/CC), R2 (PD text), R3 (gray audit), R4 (standards) in
`d:/Projects/.workspace_archive/handoffs/researcher_lyrsrc_*_20260929_2355.md`;
verified code facts cited as `file:line`.

**GATE R roster (user-confirmed, binding):**

| Lane | Sources |
|---|---|
| AUTO-FETCH | `sr_wikisource` (MediaWiki API `categorymembers` walk over `Категорија:Народне песме` tree, ~10k+ poem pages; XML dump is the documented bulk fallback — NOT implemented now), `en_wikisource`, `gutenberg_pd` (catalog-first via PG offline catalog; `robot/harvest` or mirror for text — site is human-only for bulk), `mudcat_digitrad` (one-shot zip ~7,800 songs, MUST drop ©-flagged items), `hymnary` (CSV exports + pre-1931 filter), `sacred_texts` (Child ballads mirror), `ccmixter` (polite auto-fetch ≥1.5 s + descriptive contact UA — user waived robots-strict based on the site's documented open-API declaration), `jamendo` (env-gated `JAMENDO_CLIENT_ID` — ships inert until key exists) |
| TITLES | `pdinfo` (PD title index; feeds wikisource lookups) |
| STUDY-ONLY AUTO | `lrclib` (keyless API; `plainLyrics` + `syncedLyrics` + `lyricsfile` YAML per-line ms timings) |
| MANUAL | `looperman` — metadata catalog only, NO fetch path (ToS bans scraping AND ML training) |
| CATALOG-ONLY | `voclr`, `acapellas4u` — registry rows only |
| REGISTRY-ONLY | 6 paid packs: `techhousemarket`, `loopmasters`, `splice`, `vocalfy`, `studiotronnic`, `weaponsounds` — `paid-rf`, future audio lane |
| CUT | `musixmatch`, `fma`, `wikimedia_commons`, `contemplator` — not in registry except `cut` section noting why |

---

## 1. License model

### 1.1 `license_tier` enum (ours — no OSS precedent, per R4 §5)

Frozen set of 9 values. Tier is the *policy bucket*; per-item license is resolved
separately (§1.3).

| `license_tier` | `fetch_policy` | `release_ok` default | Binding sources (GATE R) |
|---|---|---|---|
| `pd` | auto | `yes` | sr_wikisource, en_wikisource, gutenberg_pd, mudcat_digitrad (post-filter), hymnary (pre-1931 only), sacred_texts, pdinfo (title facts) |
| `cc0` | auto | `yes` | (reserved — no current source; jamendo `cc0` tracks if any) |
| `cc-by` | auto | `yes` — attribution required, credit line emitted per item (§8) | ccmixter (`lic=by`), jamendo CC-BY tracks |
| `cc-by-sa` | auto | `conditional` | ccmixter/jamendo opt-in items; SA on a released recording is murky → per-item user decision (megaplan draft) |
| `cc-by-nc` | auto | `no` | ccmixter (`lic=nc`, ~70% of pells per R1 §1), jamendo NC tracks — study/edit only |
| `paid-rf` | manual | `yes` (when owned) | 6 paid packs — registry rows only, future audio lane |
| `uploader-terms` | manual | `no` (default; per-item upgrade only on documented per-uploader grant) | looperman |
| `study-only` | auto | `no` | genius-pro (existing corpus), lrclib |
| `uncleared` | catalog-only | `no` | voclr, acapellas4u |

### 1.2 `fetch_policy` enum

Three values (megaplan draft preserved):

- **`auto`** — adapter ships `iter_catalog()` + `license_of()` + `fetch_lyrics()`;
  unattended polite fetching permitted within the source's `politeness` params (§2).
- **`catalog-only`** — adapter may ship `iter_catalog()` + `license_of()` ONLY.
  `fetch_lyrics` must not exist in the module. Covers sources whose catalog metadata
  may be harvested (pdinfo title lists) or may be harvested later (voclr/a4u — this
  wave ships `adapter: null`, registry rows only, per GATE R).
- **`manual`** — NO automated HTTP of any kind. Catalog is a hand-maintained local
  file under `data/`; the adapter, if present, ships `iter_catalog()` that reads that
  file only (looperman). Sources with no adapter (`adapter: null` — paid packs) are
  pure registry rows.

### 1.3 Per-item license fields — Openverse names verbatim (R4 §3/§5)

Stored on every song JSON, every `_index.json` entry, and (the DB subset) on
`songs` rows. R4 verdict: planned `{license_tier, license_ref, release_ok}` suffices
**only with the TASL tuple added** — without it we cannot emit a correct CC-BY credit
line later, which is the exact failure `release_ok` exists to prevent (R4 §5).

| Field | Content | Source of convention |
|---|---|---|
| `license` | SPDX-style token: `CC-BY-2.5` / `CC-BY-3.0` / `CC-BY-4.0` / `CC-BY-SA-*` / `CC-BY-NC-*` / `CC-BY-NC-SA-*` / `CC-BY-ND-*` / `CC0-1.0` / `LicenseRef-<slug>` / `proprietary` / `unknown` | SPDX + HF dataset-card convention (R4 §2) |
| `license_url` | deed/legal URL (ccMixter returns it per-upload; CC deeds derivable from token via constants table; PD items → Wikisource license-template URL or `publicdomain/mark/1.0` when the source marks it) | Openverse `license_url`, Croissant deed-URL-as-identifier (R4 §1.6/§3) |
| `creator`, `creator_url` | TASL **A**uthor — uploader/transcriber display name + profile URL | Openverse tuple (R4 §4) |
| `source_url` | TASL **S**ource — canonical landing page for the item (Openverse `foreign_landing_url`) | R4 §3/§4 |
| `copyright_notice` | licensor-supplied notice, when given | CC TASL guidance (R4 §4) |
| `modified_note` | adaptation/derivation note — also records user decisions flipping `conditional→yes` | CC TASL guidance (R4 §4) |
| `foreign_identifier` | upstream ID (ccMixter `upload_id`, Wikisource `pageid`, DigiTrad `SongID`, PG ebook #, LRCLIB `id`) | Openverse `foreign_identifier` (R4 §3) |
| `license_tier`, `release_ok` | our policy fields (§1.1) | megaplan draft |
| `derived_from` | optional link to another corpus item (PD original ↔ cover) — nice-to-have | megaplan F9 |

**PD convention (decision — no standard PD SPDX id exists, R4 §2):** use
`LicenseRef-public-domain` for PD-status items (pre-1931 publication, folk-traditional,
Wikisource PD transcriptions, DigiTrad trad items). NOT `CC0-1.0` — that is reserved
for true CC0 dedications (R4 §2: "use CC0-1.0 only for true dedications"); NOT `PDM`
(opaque). ccMixter `lic=pd` items map to `LicenseRef-public-domain` (R1 §3: they are
PD dedications, and ccMixter has no CC0). `LicenseRef-sampling-plus-1.0` covers the
ccMixter Sampling+ license (tier `study-only`, `release_ok=no` — text-release posture
murky).

**Attribution is computed, not stored** (Openverse pattern, R4 §3): a `tasl_credit()`
helper in `sources/_common.py` renders the credit line from the stored tuple at export
time; no `attribution` text field is persisted.

**Copyrighted text is a first-class state, not an exception** (R4 §5, WASABI
precedent): genius-pro and lrclib items carry `license: proprietary`,
`license_tier: study-only`, `release_ok: no`.

---

## 2. `source_registry.json` — schema and committed contents

**Location:** `Genious_lyrics_extractor/sources/registry.json` — committed config,
contains no lyric content (megaplan Context §: "source_registry.json is config and IS
committed"; `data/` boundary verified via `.gitignore:47`).

```jsonc
{
  "version": 1,
  "sources": [
    {
      "id": "ccmixter",                    // registry + adapter module id (sources/<id>.py)
      "name": "ccMixter",
      "base_url": "https://ccmixter.org",
      "license_tier": "cc-by",             // dominant/default tier; license_of() resolves per item
      "fetch_policy": "auto",              // auto | catalog-only | manual
      "adapter": "ccmixter",               // module name, or null = registry row only
      "corpus_tag": "ccmixter",            // songs.corpus value + default corpus dir name; null for non-lyric rows
      "corpus_dir": "ccmixter",            // OPTIONAL; default = corpus_tag. Only genius-pro sets it ("genius").
      "license_ref_default": "CC-BY-4.0",  // fallback when item license unresolved
      "env_gate": null,                    // OPTIONAL: env var required (jamendo: "JAMENDO_CLIENT_ID")
      "categories": ["acappella-by", "acappella-pd", "acappella-nc", "acappella-sa"],
      "politeness": {                      // OPTIONAL request params for auto sources
        "min_interval_s": 1.5,
        "user_agent": "toolshop-lyrics/<version> (+contact: <user-supplied>)"
      },
      "notes": "free-text"
    }
  ],
  "cut": [
    { "id": "musixmatch",        "reason": "free tier returns only ~30% lyric previews; synced lyrics paywalled from $49/mo (R3 §5)" },
    { "id": "fma",               "reason": "API permanently shut down; never exposed lyric fields (R1 §5)" },
    { "id": "wikimedia_commons", "reason": "vocal-music cat ~134 files; descriptions carry no lyric text (R1 §6)" },
    { "id": "contemplator",      "reason": "site-layer © + re-host restrictions; index value only (R2 §6)" }
  ]
}
```

### 2.1 Registry rows (frozen)

| id | tier | fetch_policy | adapter | corpus_tag | license_ref_default | notes |
|---|---|---|---|---|---|---|
| `genius` | study-only | auto | null | `genius-pro` | `proprietary` | Existing corpus. `corpus_dir: "genius"` — the ONE legacy exception (dir `lyrics/genius/`, tag `genius-pro`, lyricsdb.py:30). Fetched via `toolshop lyrics fetch/search` + extractor batch scripts, not sources/. |
| `sr_wikisource` | pd | auto | `sr_wikisource` | `sr-wikisource` | `LicenseRef-public-domain` | ~10k+ poem pages (R2 §1). politeness: ≥1.5 s serial, descriptive contact UA (mandatory — IP-block otherwise, R2 §3), `maxlag=5`, batch ≤50 titles/req, gzip. |
| `en_wikisource` | pd | auto | `en_wikisource` | `en-wikisource` | `LicenseRef-public-domain` | Secondary arm, ~300-500 song/hymn pages + collections (R2 §2). Same politeness block. |
| `gutenberg_pd` | pd | auto | `gutenberg_pd` | `gutenberg-pd` | `LicenseRef-public-domain` | Catalog-first via offline catalog (PD data); text via `robot/harvest` or mirror — NEVER scrape `/ebooks/` or `/files/` pages (R2 §4). |
| `mudcat_digitrad` | pd | auto | `mudcat_digitrad` | `mudcat-digitrad` | `LicenseRef-public-domain` | One-shot zip (7.32 MB, ~7,800 songs); drop ©-flagged items at catalog stage; charter not-for-profit → corpus/internal use (R2 §6). No per-song-page crawl (Crawl-delay 10 + AI-bot bans). |
| `hymnary` | pd | auto | `hymnary` | `hymnary` | `LicenseRef-public-domain` | CSV exports (`&export=csv`) + pre-1931 instance filter. Export path unverified — widgets page 403'd to researcher fetcher; verify manually before adapter build (R2 §6; GATE 0 Q3). |
| `sacred_texts` | pd | auto | `sacred_texts` | `sacred-texts` | `LicenseRef-public-domain` | Child ballads mirror, static HTML, light scrape ≥1.5 s (R2 §6). |
| `ccmixter` | cc-by | auto | `ccmixter` | `ccmixter` | `CC-BY-4.0` | `tags=acappella` × `lic=by`+`pd` default lane; ~45-60% lyric yield (R1 §2). politeness ≥1.5 s + descriptive contact UA — GATE R waived robots-strict per open-API declaration (t.ccmixter.org/about). |
| `jamendo` | cc-by | auto | `jamendo` | `jamendo` | `CC-BY-4.0` | `env_gate: JAMENDO_CLIENT_ID` — ships inert. ~35k req/mo, error 6 on rate-limit (R1 §5). |
| `lrclib` | study-only | auto | `lrclib` | `lrclib` | `proprietary` | Keyless; `/api/get-cached` preferred; `plainLyrics`/`syncedLyrics`/`lyricsfile` captured. politeness 200-500 ms + honor 429 `Retry-After` (R3 §4). |
| `pdinfo` | pd | catalog-only | `pdinfo` | `pdinfo` | `LicenseRef-public-domain` | Title index only — no lyrics exist on the site (R2 §5). Emits CatalogEntries, no song JSONs. |
| `looperman` | uploader-terms | manual | `looperman` | `looperman` | `proprietary` | Adapter reads hand-maintained `data/toolshop/lyrics/looperman/_catalog.json` ONLY. No HTTP anywhere — ToS bans scraping AND ML training verbatim (R3 §1). |
| `voclr` | uncleared | catalog-only | null | `voclr` | `proprietary` | Registry row only (GATE R). Public listing metadata exists but content is commercial rips — no fetch ever (R3 §2). |
| `acapellas4u` | uncleared | catalog-only | null | `acapellas4u` | `proprietary` | Same pattern (R3 §3). |
| `techhousemarket` | paid-rf | manual | null | null | `proprietary` | Registry row preserves future audio lane (R3 §6). |
| `loopmasters` | paid-rf | manual | null | null | `proprietary` | " |
| `splice` | paid-rf | manual | null | null | `proprietary` | " |
| `vocalfy` | paid-rf | manual | null | null | `proprietary` | " |
| `studiotronnic` | paid-rf | manual | null | null | `proprietary` | " |
| `weaponsounds` | paid-rf | manual | null | null | `proprietary` | " |

---

## 3. Corpus dir layout + category scheme

### 3.1 Layout

```
data/toolshop/lyrics/                  # data/ boundary — .gitignore:47, never committed
  <corpus_dir>/                        # corpus_dir == corpus_tag; exception: genius-pro → "genius"
    _catalog.json                      # adapter work queue: CatalogEntry + per-item status
                                       #   (resumable batch pattern — AGENTS.md "Batch jobs")
    _index.json                        # rebuilt by build_unified_index() from song JSONs
    _dedup_log.json                    # dropped intra-scan duplicates (existing behavior)
    _summary.md                        # optional human summary
    <category>/                        # collection slug (see 3.2)
      <slug>.json                      # song JSON v2 (schema in 3.3)
      <slug>.txt                       # optional clean-lyrics text (existing convention)
```

`_catalog.json` is persisted per corpus under `data/` (never committed): each entry
carries `status` (`pending|fetched|skipped|failed|dropped`), `drop_reason`, and the
catalog metadata — this IS the resumable-batch status file (AGENTS.md: batch jobs use
status JSON per item, `--limit/--offset`, skip-completed).

### 3.2 Category scheme — DECISION: no `-solo` suffix required

`_derive_role_and_target` (lyricsdb.py:83-99) falls through to `("solo", dirname)` for
non-suffixed names. That default is **accepted as the contract for non-artist corpora**:

- New corpus dirs MUST NOT use `-featured`/`-duo`/`-trio` (artist-configuration
  semantics, genius-only); `-solo` is permitted but discouraged as noise.
- `role='solo'` is a harmless constant for folk/CC corpora; `target_artist=<dirname>`
  gives `corpus_inventory` a natural collection-grouping key (corpus_inventory.py:16-19
  already groups by `target_artist`).
- `songs.category` (lyricsdb.py:412) stores the slug regardless — grouping works even
  if a future corpus needs real artist dirs.

**Frozen category slugs per corpus** (mirrored in registry `categories`):

| corpus | categories | basis |
|---|---|---|
| `sr-wikisource` | `zenske` (Женске, 7,306), `epske` (епске, 2,508), `lirske` (лирске, 740), `vuk-zbirke` (Karadžić per-collection pages incl. SANU), `erlangen` (216), `ostalo` (everything else in the `Народне песме` tree) | R2 §1 verified category sizes |
| `en-wikisource` | `folk-songs` (96), `ballads` (154+2 subcats), `traditional-ballads` (37), `song-books` (56), `hymns` (19+9 subcats), `poetry-collections` (515) | R2 §2 |
| `gutenberg-pd` | `child-ballads`, `songs-of-the-west`, `elizabethan`, `yorkshire`, `misc` | R2 §4 work list |
| `mudcat-digitrad` | `dt` (flat single bucket; per-song `@tags` preserved in `meta`) | R2 §6 |
| `hymnary` | `pre-1931` (only the releasable subset reaches disk) | R2 §6 |
| `sacred-texts` | `child-ballads` | R2 §6 |
| `ccmixter` | `acappella-by`, `acappella-pd` (release-safe), `acappella-nc`, `acappella-sa` (study tiers) — license-classed so the disk layout itself is release-auditable | R1 §3 license classes |
| `jamendo` | `by`, `cc0`, `by-sa`, `by-nc`, `by-nd`, `other` — license-classed | R1 §5 `license_ccurl` |
| `lrclib` | `tracks` (no natural split; all study-only anyway) | R3 §4 |
| `pdinfo` | none — catalog-only, emits `_catalog.json` entries, no song dirs | R2 §5 |
| `looperman` | none — hand-maintained `_catalog.json` only | R3 §1 |

### 3.3 Song JSON v2 (superset of README.md:93-103 + extract_artists.py:329-341)

```jsonc
{
  // ── existing fields (genius files unchanged) ──
  "title": "…", "artist": "…", "primary_artist": "…",
  "featured_artists": ["…"],
  "category": "zenske",              // new sources; genius files keep "artist_config"
  "url": "…", "language": "sr",
  "raw_lyrics": "…", "clean_lyrics": "…",
  "sections": [{"label": null, "content": "…"}],

  // ── new license/provenance block ──
  "corpus": "sr-wikisource",
  "source": "sr_wikisource",          // registry id
  "foreign_identifier": "12345",      // upstream id
  "source_url": "https://sr.wikisource.org/wiki/…",   // TASL Source
  "creator": "…", "creator_url": null,                 // TASL Author
  "copyright_notice": null,           // when supplied by source
  "modified_note": null,              // adaptations / user release decisions
  "license": "LicenseRef-public-domain",
  "license_url": "https://creativecommons.org/publicdomain/mark/1.0/",
  "license_tier": "pd",
  "release_ok": "yes",                // yes | conditional | no
  "derived_from": null,               // optional cross-corpus link (F9)

  // ── optional per-source fields ──
  "script": "cyrillic",               // sr corpora: raw_lyrics keeps original script
  "synced_lyrics": "[00:12.34]…",     // lrclib LRC
  "lyricsfile": "- start_ms: …",      // lrclib YAML per-line ms
  "meta": {"…": "…"}                  // source extras (Openverse meta_data pattern)
}
```

**NOT NULL note:** `songs.primary_artist` is `NOT NULL` (lyricsdb.py:414) — folk/PD
items have no artist, so adapters MUST emit a non-empty display string:
`'Narodna pesma'` (sr folk), `'Traditional'` (en/mudcat/child), the hymnal/collection
name, or the uploader name (ccmixter: `creator` = `user_real_name` → `primary_artist`).

**License rides the index** (megaplan F8): `_insert_song` joins `_index.json` by
basename (lyricsdb.py:840, 679-689). `build_unified_index` (lyricsdb.py:621-630) is
extended to copy the license block + `source`/`foreign_identifier`/`script`/
`derived_from` from each song JSON into its index entry; `_insert_song` reads them
from `index_entry` with `song_data` fallback — the same pattern as `primary_artist`
(lyricsdb.py:677-681).

---

## 4. `lyricsdb.py` migration

### 4.1 DECISION: option (a) — columns on `songs`, not a side table

License data is 1:1 with songs and participates in nearly every read path (release
export filters, corpus stats); a `song_licenses` side table buys nothing but a
permanent join and a second upsert path. `ALTER TABLE` + backfill is idempotent and
leaves every v1 column byte-identical (megaplan success criterion 2). `_insert_song`
stays a single INSERT (lyricsdb.py:707-726).

**New columns on `songs`** (added to `_SCHEMA_SQL` CREATE for fresh DBs AND to the
migrate guard for existing DBs — both paths converge to identical shape):

```sql
license_tier     TEXT NOT NULL DEFAULT 'study-only',  -- safe default: never auto-release
license_ref      TEXT,                                 -- stores the `license` SPDX token
license_url      TEXT,
release_ok       TEXT NOT NULL DEFAULT 'no',           -- safe default
creator          TEXT,
creator_url      TEXT,
source_url       TEXT,
copyright_notice TEXT,
modified_note    TEXT,
foreign_identifier TEXT,
script           TEXT,                                 -- 'cyrillic'|'latin', NULL elsewhere
derived_from     TEXT                                  -- optional cross-corpus link
```

(`license` as a column name is avoided for clarity; the song-JSON field `license`
maps to DB column `license_ref` — documented in `_insert_song`. `source` column is
skipped: `corpus` ↔ registry id is already 1:1.)

### 4.2 Migrate-on-open guard

`ensure_license_columns(conn)`:

1. `PRAGMA table_info(songs)` → for each missing column, `ALTER TABLE songs ADD COLUMN`.
2. Backfill genius rows: `UPDATE songs SET license_tier='study-only',
   license_ref='proprietary', release_ok='no' WHERE license_tier IS NULL` — or
   corpus-scoped to `corpus='genius-pro'`. `proprietary`, not `unknown`: status is
   known-copyrighted (R4 §5 / WASABI precedent).
3. Called by `build_database` after `_create_schema` (lyricsdb.py:828), and by
   `export_release.py` / `corpus_inventory.py` on open — any reader of license fields
   self-heals an old DB. Idempotent; safe under concurrent open.

### 4.3 Corpus-scoped dedup — DECISION: in-Python SELECT pre-check, no norm columns

`songs` has no UNIQUE constraint (lyricsdb.py:409-423) and stores no normalized key.
**Do NOT add `title_norm`/`artist_norm` columns.** Rationale:

- Normalization is single-sourced in `normalize_text` (:371-391 — NFC → cyrtranslit →
  ASCII-fold → lower) + `_dedup_key` (:396-403). Stored norm columns drift the moment
  folding rules change (e.g. јекавica handling for Karadžić-era text, R2 §1).
- The pre-check is one indexed `SELECT title, primary_artist, foreign_identifier FROM
  songs WHERE corpus = ?`; ~10-15k rows per corpus is trivial in memory.
- Corpus-scoping is natural in the WHERE clause — **cross-corpus duplicates are
  CORRECT** (PD original + modern cover must coexist, megaplan F9); `derived_from`
  preserves the optional link.

Incremental-mode pre-check: seed `seen_keys` from the corpus SELECT (normalized
through `_dedup_key`) plus a `foreign_identifier` set; a scanned file is skipped when
its dedup key OR its `foreign_identifier` already exists in the corpus — the fid arm
catches upstream title edits/renames.

---

## 5. `build_database` signature + CLI

### 5.1 Signature

```python
def build_database(
    root: Path,
    db_path: Optional[Path] = None,
    corpus: Optional[str] = None,
    incremental: bool = False,
) -> Dict[str, Any]:
```

- `corpus` — songs.corpus value. `None` → `CORPUS_TAG` (`'genius-pro'`,
  lyricsdb.py:30) for back-compat. Threaded through `_insert_song` in place of the
  hardcoded tag (lyricsdb.py:713). Registry resolves `corpus → corpus_dir → root`.
- Per-corpus license defaults (`license_tier`/`license_ref`/`license_url`/
  `release_ok`) resolved once per build from registry `license_tier`+
  `license_ref_default`, falling back to a builtin
  `{'genius-pro': ('study-only','proprietary',None,'no')}` map — lyricsdb keeps zero
  dependency on the extractor folder.

### 5.2 Mode semantics — exact behavior

**`incremental=False` (default) = corpus-scoped rebuild** — replaces today's
whole-DB `unlink` (lyricsdb.py:822-823):

1. `DELETE FROM songs WHERE corpus = ?` — FK `ON DELETE CASCADE` wipes that corpus's
   sections (:427), lines (:437), song_metrics (:447), line_rhymes (:467), tokens
   (:494), entities (:509-511), section_topics (:539), song_rhyme_metrics (:481).
   `PRAGMA foreign_keys=ON` already set at :827. **Other corpora are never touched** —
   this is what makes a multi-corpus DB viable (the old unlink would nuke everything).
2. Ingest every `<root>/<category>/*.json` via the existing scan path
   (`_scan_song_files` :652-663, `build_unified_index` :574-644, dedup :839-858).
3. Never calls `db_path.unlink()`.

**`incremental=True` = additive-only — never drops existing rows, of any corpus:**

1. No DELETE, no unlink. `_create_schema` (all `IF NOT EXISTS`) +
   `ensure_license_columns` run on the existing DB.
2. Corpus-scoped pre-check (§4.3): files whose dedup key or `foreign_identifier`
   already exists in `corpus` are skipped and counted `already_present`.
   Intra-scan dedup (`seen_keys`) unchanged.
3. Sections/lines inserted only for new songs (existing flow :860-864). Metrics and
   rhymes computed **only for newly inserted song ids** — `populate_rhymes(conn,
   song_id)` is already per-song (:880-881 calls it per id), but
   `populate_song_metrics(conn)` iterates ALL songs and inserts unconditionally
   (lyrics_metrics.py:129-160) → **spec change: it gains an optional
   `song_ids: list[int] = None` param**; incremental passes new ids, rebuild passes
   the corpus's ids. `create_artist_views` is idempotent (`CREATE VIEW IF NOT
   EXISTS`) and stays genius-scoped (`corpus='genius-pro'` hardcoded at
   lyrics_metrics.py:181 — acceptable; new corpora are reported via
   `corpus_inventory`, §8).
4. Re-fetching an upstream-changed item = corpus-scoped rebuild, not incremental
   (keeps semantics simple; flag in handoff if a `--refresh` mode is wanted later).

**Summary dict additions:** `corpus`, `incremental`, `already_present`,
`license_backfilled` count.

### 5.3 CLI — `toolshop lyrics build-db`

```
toolshop lyrics build-db [--corpus TAG] [--root PATH] [--db PATH] [--incremental | --rebuild]
```

- `--corpus` (new, default `genius-pro`): resolves `--root` via registry
  `corpus_dir` convention when `--root` absent (`<data>/lyrics/<corpus_dir>`;
  genius → `lyrics/genius`). Current `--root`/`--db` flags unchanged
  (cli.py:909-924, dispatch cli.py:2221-2232).
- `--incremental` → additive mode; `--rebuild` → explicit corpus-scoped rebuild
  (the default when neither is given); mutually exclusive.
- Unknown `--corpus` (not in registry, no matching dir) → error exit, never a
  silent empty build.

---

## 6. Adapter interface contract — `Genious_lyrics_extractor/sources/`

### 6.1 Hard rules

- **No `import toolshop`** anywhere in the folder — eager init costs ~70 s and drags
  the full dependency chain (megaplan F-B1). Shared code lives in
  `sources/_common.py`.
- `RobotsPolicy` vendored from `toolshop/genius_adapter.py:43-117` (~75 lines,
  generic `robots_url` param) into `_common.py`; kept verbatim.
- UTF-8 everywhere, `ensure_ascii=False` JSON writes (AGENTS.md; extract_artists.py:343-347).
- Resumable batch pattern: `_catalog.json` status per item, `--limit/--offset`,
  skip-completed (AGENTS.md "Batch jobs").

### 6.2 `_common.py` exports

- `RobotsPolicy` (vendored).
- `polite_get(url, source_id, **kw)` — `requests` wrapper enforcing the registry
  `politeness` block: `min_interval_s` pacing, descriptive contact `User-Agent`
  (MediaWiki IP-blocks without it, R2 §3), gzip, retry with exponential backoff on
  `429`+`Retry-After` (LRCLIB, R3 §4) and `maxlag`/`ratelimited` errors (R2 §3).
- `CatalogEntry` dataclass: `source_id, foreign_identifier, title, creator,
  creator_url, source_url, url, license, license_url, category, status
  ('pending'|'fetched'|'skipped'|'failed'|'dropped'), drop_reason, meta: dict`.
- `LicenseInfo` dataclass: `license, license_url, license_tier, release_ok,
  copyright_notice`.
- `LICENSE_URL_MAP` — URL-fragment → SPDX token table, the Openverse
  `constants.py` normalization pattern (R4 §1.1): `licenses/by/4.0 → CC-BY-4.0`,
  `publicdomain/mark/1.0 → LicenseRef-public-domain`, ccMixter `sampling+/1.0 →
  LicenseRef-sampling-plus-1.0`, etc. `license_of()` implementations MUST route
  through it rather than trusting free-text license names.
- `tasl_credit(song_or_entry) -> str` — computed credit line (§1.3).
- `load_catalog`/`save_catalog` (per-corpus `_catalog.json`), `write_song_json`,
  `slugify` (extract_artists.py:63-66 pattern), `detect_script` (cyrillic detection
  equivalent to lyricsdb `_has_cyrillic`).

### 6.3 Module contract

```python
# sources/<name>.py
SOURCE_ID = "ccmixter"

def iter_catalog(limit=None, offset=0) -> Iterator[CatalogEntry]: ...
def license_of(entry: CatalogEntry) -> LicenseInfo: ...   # may only DOWNGRADE vs tier default
def fetch_lyrics(entry: CatalogEntry) -> dict: ...        # returns song JSON v2 (§3.3)
```

| fetch_policy | Required symbols | Forbidden |
|---|---|---|
| `auto` | `iter_catalog`, `license_of`, `fetch_lyrics` | — |
| `catalog-only` | `iter_catalog`, `license_of` | **`fetch_lyrics` must not exist** |
| `manual` | `iter_catalog` (reads local file ONLY) | `fetch_lyrics`; any HTTP import/call |

**`license_of` may only downgrade** the registry tier default (e.g. mudcat ©-flag →
drop; ccmixter `ccplus` flag → keep `by` tier, note in `copyright_notice`), never
upgrade — upgrades are recorded user decisions on items, not adapter logic.

**looperman.py literally contains no lyric-fetch function and no network code** —
`iter_catalog()` parses `data/toolshop/lyrics/looperman/_catalog.json`
(hand-maintained from browser-visible fields: title/uploader/BPM/key/genre/usage,
R3 §1). The ToS clause bans both scraping and ML training verbatim, so the module
must not even import `requests` (enforced by test, §7).

**Env gate:** jamendo imports cleanly; `iter_catalog`/`fetch_lyrics` raise a
dedicated `EnvGateError` (or yield nothing per runner flag) when
`JAMENDO_CLIENT_ID` is unset — adapter ships inert (GATE R).

### 6.4 Runner — `fetch_lyrics_source.py` (W1)

```
python fetch_lyrics_source.py --source ccmixter [--limit N] [--offset N] [--category X] [--rebuild-catalog]
```

Loads registry → resolves adapter → `iter_catalog` persists `_catalog.json` → for
each `pending` entry: `license_of` (status `dropped` + `drop_reason` when filtered)
→ `fetch_lyrics` → `write_song_json` into `<corpus>/<category>/` → status `fetched`.
Errors → status `failed` + continue (skip-completed resume). `--rebuild-catalog`
re-runs catalog listing without fetching. Refuses to run for
`fetch_policy != 'auto'` sources — their adapters have no `fetch_lyrics` by
contract.

---

## 7. Test conventions

- Tests live in `tests/test_lyrics_sources_*.py` (`pytest.ini testpaths=tests` —
  verified) with a `sys.path` shim into `Genious_lyrics_extractor/` in a local
  `conftest.py` or fixture (`sources_path` fixture).
- **Committed fixtures ONLY from cleared sources** (pd/cc0/cc-by items — each
  fixture carries its own TASL block; a `tests/fixtures/lyrics_sources/CREDITS.md`
  lists fixture provenance). Gray-source fixtures = **synthetic structure, no lyric
  text** — fabricated metadata matching the real schema (megaplan F5; R3: gray lyric
  text is uploader © and ML-banned for looperman).
- Live fetches → `@pytest.mark.slow` (marker exists in pytest.ini); network tests
  must degrade gracefully offline (F5 proxy-failure fallback).
- **Contract tests (required):**
  1. Registry loads; every row's `license_tier`/`fetch_policy` in enum; every
     `adapter != null` resolves to an importable `sources/<adapter>.py`.
  2. `fetch_policy='auto'` modules expose all three functions; `catalog-only`/
     `manual` modules: `assert not hasattr(mod, 'fetch_lyrics')`; `manual` modules:
     source text contains no `requests`/`http`/`urlopen` (looperman enforcement).
  3. `license_of` mapping tables per source: ccmixter URL→SPDX (by/2.5,3.0,4.0,
     nc→CC-BY-NC-*, sampling+→LicenseRef), mudcat ©-flag → dropped, hymnary
     year ≤1930 filter, gutenberg boilerplate strip.
  4. Migration test on a v1-schema fixture DB: columns added, genius rows backfilled
     `study-only`/`proprietary`/`no`, v1 columns byte-identical, counts unchanged.
  5. Incremental test: insert → rebuild → same song skipped (`already_present`);
     same `(title, artist)` in a second corpus → both rows kept (F9).
  6. Export test: `--release-cleared` emits only `release_ok='yes'` rows; audit of
     emitted tree finds zero `conditional`/`no`; every emitted item has a TASL
     credit line.

---

## 8. Reconciliation & export contract

### 8.1 `corpus_inventory.py` extension (W5)

Currently hardcodes `corpus='genius-pro'` (corpus_inventory.py:10, 16, 33, 55, 64).
Extend with `--corpus <tag>` (default: all corpora):

- Per corpus: songs/sections/lines/rhyme rows + per-category counts.
- License block: `license_tier × release_ok` matrix, count of items missing TASL
  fields (release-readiness gap report), `derived_from` link counts.
- `--corpus genius-pro` output stays the existing report shape.

### 8.2 `export_release.py` (new, `Genious_lyrics_extractor/export_release.py`, W5)

```
python export_release.py --release-cleared --outdir <dir> [--corpus X] [--include-conditional]
```

- Opens lyrics.db via `ensure_license_columns` + loads `registry.json`.
- `SELECT … FROM songs WHERE release_ok = 'yes'` (+`'conditional'` ONLY behind the
  explicit flag). Emits `<outdir>/<corpus>/<category>/<slug>.json` + `.txt`
  (clean_lyrics) — a folder-level release tree, not a DB.
- **`CREDITS.md`** — one computed TASL credit line per item (`tasl_credit`), grouped
  by corpus/license. Attribution is generated at serve time (R4 §3) — any item
  missing `creator`/`source_url` lands in the manifest's gap list.
- **`RELEASE_MANIFEST.json`** — counts, license histogram, per-item
  `{title, creator, license, license_url, source_url, song_id}` rows, and a
  `pending_decision` list of `conditional` items.
- **Conditional semantics:** `release_ok='conditional'` is NEVER emitted by
  `--release-cleared` alone; `--include-conditional` emits only items carrying a
  `modified_note` recording the user's decision — items without one are skipped and
  reported (megaplan: per-item user decision for cc-by-sa).
- **`release_ok='no'` is never emitted** — enforced by the §7 export test's audit
  assertion.

---

## 9. Per-source ingest notes (binding on adapters)

- **ccmixter:** default lane `tags=acappella` × `lic=by` + `lic=pd` (release-safe);
  `lic=nc`/`sa`/`byncsa` opt-in for the study tiers (R1 §2-3: BY+PD ≈1,507 items,
  ~45-60% lyric yield → ~650-750 release-safe pells). Lyrics live in
  `upload_description_plain`/`_html` under informal headers (`Lyric:`, `WORDS`,
  `LYRICS/SPOKEN WORD:`) — header-detection extraction, drop items with no lyric
  block (`status: dropped`, `drop_reason: 'no-lyric-text'`). `license_url` → SPDX via
  `LICENSE_URL_MAP` (by/2.5, 3.0, 4.0; `lic=pd` → `LicenseRef-public-domain`;
  `sampling+/1.0` → `LicenseRef-sampling-plus-1.0` = study-only). `file_page_url` →
  `source_url`, `user_real_name` → `creator`, `upload_id` → `foreign_identifier`.
  politeness ≥1.5 s + descriptive contact UA (GATE R waived robots-strict — open-API
  declaration; `MLBot` remains banned, never spoof).
- **sr_wikisource:** `list=categorymembers` recursion (`cmtype=subcat`) under
  `Категорија:Народне песме` ∪ 14 `Збирка-Вук` book cats ∪ `Ерлангенски рукопис`;
  dedup cross-category by `pageid`. **`action=parse&prop=wikitext`, NOT
  `prop=extracts`** — poem bodies are bare wikitext lines; extracts return ~nothing
  (R2 §1 verified caveat). Strip `{{templates}}`, `<pages index=…>` transclusion
  tags, trailing `== Види још ==`/see-also sections; book/TOC pages are indexes, not
  lyric text; SANU volumes: poem body only, skip editorial apparatus; **scan each
  page's `{{…}}` license template before ingest** (R2 §1). `raw_lyrics` keeps the
  original script + `script` field (`'cyrillic'|'latin'` via `detect_script`);
  `clean_lyrics` = `cyrtranslit.to_latin(…, 'sr')` + diacritic fold — matches
  `normalize_text` (lyricsdb.py:371-391) so file text and `lines.text_norm` agree.
  `primary_artist='Narodna pesma'` (NOT NULL, lyricsdb.py:414). maxlag=5, contact UA,
  ≤50 titles/req, serial ≥1.5 s. XML dump = documented bulk fallback, NOT
  implemented now (GATE R).
- **en_wikisource:** same MediaWiki machinery; categories per §3.2. **Do not chase
  Child ballads there** — Part pages are `{{migrate to}}` placeholders (R2 §2); Child
  comes from gutenberg/sacred-texts instead.
- **gutenberg_pd:** catalog-first — download the PG offline catalog (public-domain
  catalog data) → filter by bookshelf/LoCC + curated list (Child vols #44969,
  #47692, …, #71104; Songs of the West #56625; Elizabethan song-books; Yorkshire
  ballads, R2 §4). Text fetch via `robot/harvest` endpoint or a private mirror
  ONLY — `/ebooks/` + `/files/` scraping = IP block (robot_access.html). Strip PG
  header/footer boilerplate + transcriber notes (legally strippable — plain PD once
  the trademark is detached, R2 §4).
- **mudcat_digitrad:** fetch `download.cfm` zip ONCE (~7.8k songs); parse per-song
  records (lyrics + source line + `@tags` + filename). **Drop at catalog stage any
  entry flagged ©** (the charter's "otherwise noted" items — R2 §6): they never
  reach disk. Keep trad/PD-source items → `pd`/`LicenseRef-public-domain`/`yes`;
  source line + `@tags` → `meta`. Charter is not-for-profit → corpus/internal
  release use only; manifest note required (GATE 0 Q4). No per-song-page crawling
  (Crawl-delay 10, AI-bot UAs hard-blocked).
- **hymnary:** catalog via CSV exports (`&export=csv` / dataset downloads); per-text
  "Representative Text" may come from a MODERN hymnal instance (R2 §6 example showed
  2013) → resolve the publication year of the specific instance and emit only
  ≤1930 texts; post-1930 instances never reach disk. Export path unverified (widgets
  page 403'd to researcher) — manual verification precedes adapter work (GATE 0 Q3).
- **sacred_texts:** Child ballads mirror (`neu/eng/child/chtitle.htm` index →
  per-ballad pages); static light scrape ≥1.5 s; PD texts only.
- **jamendo:** `env_gate: JAMENDO_CLIENT_ID` — ships inert (§6.3). When keyed:
  `tracks` endpoint `include=lyrics` + `license_ccurl` per track (→ `LICENSE_URL_MAP`),
  `limit`≤200 + `offset`, ~35k req/mo, error code 6 = rate-limit → backoff (R1 §5).
  Lyric fill-rate unverified (GATE 0 Q2).
- **lrclib:** lookup API, not a browsable corpus → `iter_catalog` reads a local seed
  file (CSV/JSON of `artist,title,album,duration` rows — e.g. exported genius-pro
  metadata or user-supplied list). Prefer `/api/get-cached` (deterministic) then
  `/api/get` (±2 s duration tolerance). Capture `plainLyrics` → raw/clean,
  `syncedLyrics` → `synced_lyrics` (LRC), `lyricsfile` → `lyricsfile` (YAML per-line
  ms — richer than LRC for the alignment lane, R3 §4). `license: proprietary`,
  tier `study-only`, `release_ok: no` — lyric text remains songwriters' ©.
  200-500 ms spacing, honor `Retry-After`.
- **pdinfo:** fetch the ~50 static A–Z/genre/year list pages ONCE, cache under
  `data/`; emit `CatalogEntry` per title (`title`, `creator`, list provenance in
  `meta`). Titles are uncopyrightable facts (US Copyright Office Circular 33,
  R2 §5) but each row's PD claim = "a pre-1930 source exists somewhere" — NOT
  documentation → `meta.pd_claim: 'unverified'`; feeds wikisource/gutenberg
  title lookups. No `fetch_lyrics` — no lyrics exist to fetch.
- **looperman:** `iter_catalog()` reads `data/toolshop/lyrics/looperman/_catalog.json`
  (hand-maintained: title/uploader/date/BPM/key/genre/usage/description-free).
  No HTTP, no `fetch_lyrics`, no lyric text anywhere in the lane (R3 §1 ToS bans
  scraping AND ML training).
- **voclr / acapellas4u / paid packs:** registry rows only this wave — no adapter
  modules (GATE R). `corpus_tag` reserved for voclr/a4u for a possible future
  catalog adapter; paid packs `corpus_tag: null` (audio lane).

---

## 10. Assumption register + open questions

| # | Assumption | Status |
|---|---|---|
| A1 | ccMixter pell descriptions carry usable lyric text | **RESOLVED** — R1 §2: ~45-60% usable (n=60, 4 slices); ~650-750 release-safe pells extrapolated |
| A2 | sr.wikisource PD folk corpus traversable at volume | **RESOLVED** — R2 §1: ~10k+ poem pages, live-verified counts |
| A3 | Looperman/rip-sites = catalog-only | **RESOLVED** — R3 §§1-3: ToS/credit-gate/rip-content confirmed |
| A4 | LRCLIB open API + synced lyrics | **RESOLVED** — R3 §4: keyless, +`lyricsfile` YAML bonus |
| A5 | Existing `_index.json` + song JSON suffices with license fields | **RESOLVED by this spec** — R4 §5: suffices WITH TASL tuple; schema frozen in §3.3 |
| A6 | MediaWiki API needs no key | **RESOLVED** — R2 §3: keyless; contact UA mandatory, maxlag, serial |
| A7 | `data/` + gitignore covers new corpus dirs | **RESOLVED (verified early)** — `.gitignore:47` `data/`; `git check-ignore data/toolshop/lyrics/test_probe.json` → ignored |

**Open questions for GATE 0 — all RESOLVED 2026-09-29 (user approved all recommendations):**

1. Category scheme: non-artist dirs carry NO `-solo` suffix — **CONFIRMED** (§3.2 frozen).
2. Jamendo lyric fill-rate unknown — **CONFIRMED**: inert env-gated adapter; fills when `JAMENDO_CLIENT_ID` supplied.
3. Hymnary CSV path — **RESOLVED as CSV-primary + HTML fallback**: pilot run decides which path works; both fail → defer-with-error, never a fragile forced scraper.
4. Mudcat unflagged items — **CONFIRMED**: `release_ok=yes` + manifest note documenting the DT not-for-profit charter context.
5. `conditional→yes` mechanism — **CONFIRMED**: per-item `modified_note` decision field (§8.2), no separate decisions file.
6. Dedup: in-Python corpus-scoped pre-check, no norm columns — **CONFIRMED** (§4.3 frozen).
7. Genius registry row + `corpus_dir: "genius"` exception — **CONFIRMED** (§2.1).
8. `incremental` skips `foreign_identifier` matches, `--refresh` deferred — **CONFIRMED** (§5.2).

---

## Appendix — file change map by wave

| Wave | Files |
|---|---|
| W1 | `Genious_lyrics_extractor/sources/{_common.py, registry.py, catalog.py, fetch_lyrics_source.py}` + `sources/registry.json` + `tests/test_lyrics_sources_core.py` |
| WA | `sources/{ccmixter, sr_wikisource (or shared wikisource base), en_wikisource, pdinfo, looperman}.py` + per-source tests + bounded pilots; later adapter waves: `gutenberg_pd, mudcat_digitrad, hymnary, sacred_texts, jamendo, lrclib` |
| W5 | `toolshop/lyricsdb.py` (§4-5), `toolshop/lyrics_metrics.py` (`song_ids` param), `toolshop/rhyme_miner.py` (`--corpus` flag — corpus hardcoded at :463/478/504/520 per megaplan F-B2), `toolshop/cli.py` (§5.3 flags), `Genious_lyrics_extractor/{corpus_inventory.py ext, export_release.py}` |
| W6 | review report, license audit, release-export smoke, STATUS/CHANGELOG, `toolshop closeout` |
