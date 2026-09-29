# I1 handoff — W1 implementer, lyrics-sources megaplan

**Wave:** W1 (infra) · **Agent:** I1 · **Date:** 2026-09-30
**Commits:** `1adb2d1` — `feat(#062): lyrics-sources W1 — sources/ registry + vendored robots + resumable catalog + fetch dispatcher` (19 files, +4180); + a `docs(#062)` commit carrying this handoff file.
**Scope delivered:** `Genious_lyrics_extractor/sources/{__init__.py,_common.py,registry.py,catalog.py,registry.json}` + `fetch_lyrics_source.py` + `tests/test_lyrics_sources_core.py` + `tests/fixtures/lyrics_sources/`. No adapter modules (wave WA/WB scope).

## What landed (task → file)

| Task | Where | Notes |
|---|---|---|
| 1 `sources/__init__.py` + `_common.py` | `sources/` | `__init__` is docstring-only (no eager imports). `_common.py`: `RobotsPolicy` vendored from `toolshop/genius_adapter.py:43-117` generalised (`robots_url` or `base_url`, UA header); `RateLimiter` + `polite_get` (per-source ≥1.5 s pacing, `{contact}`-template UA via `TOOLSHOP_CONTACT`/`TOOLSHOP_LYRICS_UA` env, gzip, 429/`Retry-After` + MediaWiki `maxlag`/`ratelimited` backoff); `CatalogEntry`/`LicenseInfo`; `LICENSE_URL_MAP` + `LICENSE_TOKEN_INFO` + `license_from_url`/`license_policy_for`; `tasl_credit`; `load_catalog`/`save_catalog`; `write_song_json` (song JSON v2 §3.3 + `.txt`, safe `study-only`/`no` defaults, fid-collision suffix); `build_index`/`write_index` (license block rides `_index.json` — F8); `slugify`/`norm_key`/`detect_script`; `DropItem`/`EnvGateError`/`RobotsDisallowedError`; `pending_slice` resumable helpers (batch.py semantics, self-contained). |
| 2 `registry.py` | `sources/registry.py` + `registry.json` | 20 frozen rows + 4-row `cut` section verbatim from SPEC §2.1. `get()`, `validate()` (enum + uniqueness + corpus_dir==corpus_tag rule), `corpus_root()` (corpus_dir override else corpus_tag; genius is the only exception), `require_fetchable()` → `FetchPolicyError` for `fetch_policy != 'auto'` or `adapter: null`, `check_env_gate()` → `EnvGateError`, `resolve_adapter()` → clear "not implemented yet (wave WA)" error. `data_dir()` mirrors `paths.py` without importing toolshop. |
| 3 `catalog.py` | `sources/catalog.py` | `Catalog` — `_catalog.json` IS the resumable status file: `upsert_entries` (preserves terminal statuses on re-list), `mark`/`mark_entry` (flush per item), `pending(resume, category, limit, offset)`, `counts()`. Serialized rows carry the union of task fields (`source, external_id, title, artist, url, license_tier, license_ref, release_ok, fetched`) and SPEC §6.2 `CatalogEntry` fields. |
| 4 dispatcher | `fetch_lyrics_source.py` | `--source/--limit/--offset/--resume/--category/--catalog-only|--rebuild-catalog/--list`. Order of gates: `require_fetchable` (before any catalog work) → adapter resolve → `check_env_gate` → corpus dir → `iter_catalog`→merge→flush → fetch loop (`license_of`→`DropItem`→dropped, exception→failed+continue, `write_song_json`, mark `fetched`) → `write_index`. |
| 5 tests | `tests/test_lyrics_sources_core.py` | 53 tests; sys.path shim into `Genious_lyrics_extractor/`; fixtures `tests/fixtures/lyrics_sources/` (all synthetic, CC0 — `CREDITS.md`). Covers every required assert: robots gate blocks disallowed, rate limiter sleeps, resume skips completed, catalog-only/manual raises on fetch, index entries carry license fields. |
| 6 A7 verify | — | `git check-ignore -v data/toolshop/lyrics/test_probe.json` → `.gitignore:47:data/` → **covered, no .gitignore edits needed** (exit 0). |

## Deviations from task text (spec-wins resolutions)

1. **`_catalog.json`, not `_catalog.jsonl`** — the frozen SPEC (§3.1, §6.2, §6.4) names the resumable queue `_catalog.json` (a flushed JSON doc). The W1 task text's `_catalog.jsonl` predates the freeze. Entry dicts carry all task-named fields, so the intent is fully met.
2. **`--resume` semantics** — mirrors `toolshop.batch.run_batch`: `--resume` skips terminal statuses (`fetched`/`skipped`/`dropped`) and retries `failed`; without it, `fetched` entries are eligible again (refresh) but `skipped`/`dropped` are NEVER silently re-queued (adapter decisions like mudcat ©-drops are not errors).
3. **`--catalog-only` == `--rebuild-catalog`** — both flags alias the same action (SPEC §6.4 name + task name); bound by `--limit/--offset` when present.
4. **Prior-session artifacts committed:** `ORCHESTRATION/lyrics_sources/` (SPEC.md, waves_megaplan.json, waveR prompts, wave_0 handoff) was untracked work from WR/W0 — committed in `1adb2d1` per "no record ahead of code" (the frozen spec now on record with the code implementing it).
5. **Commit hygiene incident:** an earlier session had pre-staged 6 unrelated GATE-S3 files (`scripts/check_audition_serve.py`, `scripts/verify_sample_pack.py`, `scripts/ogcm_sample.py`, `tests/test_flip_sample.py`, `toolshop/flip/sample_voices.py`, `ORCHESTRATION/ogcm_flip/LEDGER.md`). First commit `e329acb` swept them in; I soft-reset and recommitted lane-only as `1adb2d1` (plus a follow-up `docs(#062)` handoff commit). Those files remain on disk, unstaged (pre-session state).

## Verification evidence (quoted)

`pytest` — exit 0:
```
$ .venv/Scripts/python.exe -m pytest tests/test_lyrics_sources_core.py -q
.....................................................                    [100%]
53 passed, 1 warning in 11.79s
```

Collection sanity — exit 0:
```
$ .venv/Scripts/python.exe -m pytest -q --collect-only
1497 tests collected in 77.91s
```

CLI smoke — exit 0 (policy refusals return 2 with clear errors):
```
$ python fetch_lyrics_source.py --list
  genius           auto          study-only     adapter=None corpus=genius-pro
  sr_wikisource    auto          pd             adapter=sr_wikisource corpus=sr-wikisource
  ... (20 rows) ...
$ python fetch_lyrics_source.py --source voclr        → rc=2
  ERROR: source 'voclr' has fetch_policy 'catalog-only' — lyric fetching is not permitted (SPEC §1.2). Use --catalog-only ...
$ python fetch_lyrics_source.py --source looperman    → rc=2 (fetch_policy 'manual')
$ python fetch_lyrics_source.py --source genius       → rc=2 (adapter=null — registry row only)
$ python fetch_lyrics_source.py --source ccmixter --catalog-only → rc=2
  ERROR: adapter 'sources/ccmixter.py' ... not implemented yet (adapter wave WA)
```

`py_compile` on all six new modules — exit 0. `git check-ignore` — see task-6 row.

## Interface contract for WA/WB adapters (as enforced)

```python
# sources/<name>.py
SOURCE_ID = "<registry id>"
def iter_catalog(limit=None, offset=0) -> Iterator[CatalogEntry]     # all policies
def license_of(entry) -> LicenseInfo                                  # auto + catalog-only
def fetch_lyrics(entry) -> dict        # song JSON v2 — ONLY for fetch_policy=='auto'
```

- Raise `sources._common.DropItem(reason)` from `license_of`/`fetch_lyrics` → `status='dropped'` + `drop_reason`; the item never reaches disk (mudcat ©-flag path).
- `license_of` may only DOWNGRADE the registry tier default; use `license_from_url()` for URL→SPDX.
- `fetch_lyrics` returns the §3.3 dict; missing license/provenance fields are back-filled from the catalog entry + registry defaults — but adapters SHOULD set them.
- `manual` modules (looperman): no `requests`/`fetch_lyrics`; iter_catalog reads a local file only — `test_named_adapters_resolve_or_defer` + the no-network contract assertion will check module shape as they land.
- `jamendo`: raise `EnvGateError` (or rely on dispatcher `check_env_gate`) when `JAMENGO_CLIENT_ID`… **`JAMENDO_CLIENT_ID`** is unset — dispatcher checks before `iter_catalog`, so the inert path is enforced even if the module forgets.

## Risks / notes for downstream waves

- **`test_named_adapters_resolve_or_defer` is intentionally tolerant now** (registry names WA modules that don't exist); it becomes strict the moment `sources/<name>.py` lands — adapters must match the contract immediately or the suite goes red.
- **`_LIMITERS`/`_ROBOTS_CACHE` are process-global** — per-source pacing persists across `polite_get` calls in one process (desired for batch runs); tests inject their own limiter/fake session instead.
- **`foreign_identifier` is the catalog's dedup identity** (`fid:` key; falls back to normalized title+url). Adapters must set it for every entry — the incremental DB pre-check (§4.3) also relies on it.
- **The dirty tree is not mine:** `MAirina_Tucc/*`, `ORCHESTRATION/ogcm_flip/*`, `mastering_tool`, `suno_prompter`, `handoffs/orchestration_ledger_lyrics_sources_20260929.md`, `lyrics_research/`, and the 6 GATE-S3 files listed above remain uncommitted — owned by other lanes/sessions.
- **Not verified on target / not pushed:** commit `1adb2d1` is local (`master` is ~176 ahead of `origin/master` — push cadence is the user's). No live network calls were made (all fetch paths mocked).
