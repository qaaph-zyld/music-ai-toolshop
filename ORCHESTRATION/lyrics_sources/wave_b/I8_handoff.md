# Handoff — Wave B, agent I8: `jamendo` (env-gated) + `lrclib` (study-only) adapters

**Date:** 2026-10-01 · **Impl commit:** `2a14177` (`feat(#066): lyrics-sources WB I8 - jamendo env-gated adapter + lrclib study-only adapter`) · **This doc:** committed immediately after (same lane) · **Python:** `.venv` 3.11.9 only · **Zero `import toolshop`** in new modules (megaplan F-B1).

## Deliverables (all committed in `2a14177`, 14 files / +1925)

| Path | Status |
|---|---|
| `Genious_lyrics_extractor/sources/jamendo.py` | NEW — env-gated adapter |
| `Genious_lyrics_extractor/sources/lrclib.py` | NEW — study-only adapter |
| `tests/test_lyrics_sources_jamendo.py` | NEW — 19 tests |
| `tests/test_lyrics_sources_lrclib.py` | NEW — 23 tests |
| `tests/fixtures/lyrics_sources/jamendo_{tracks_page,track_single,rate_limit}.json` | NEW — synthetic (`meta_fixture: true`) |
| `tests/fixtures/lyrics_sources/lrclib_{get_response,get_synced_only,instrumental,search_response}.json` | NEW — synthetic (gray source: no real lyric text, SPEC §7) |
| `tests/fixtures/lyrics_sources/lrclib_seed.{json,csv}` | NEW — synthetic seed fixtures |
| `CHANGELOG.md` | MODIFIED — Answer #066 entry |
| `data/toolshop/lyrics/lrclib/` (`_seed.json`, `_catalog.json`, `_index.json`, `tracks/*.json|.txt`) | NEW — **uncommitted** (data boundary, `.gitignore:47`) |
| `tests/fixtures/lyrics_sources/CREDITS.md` | MODIFIED — my fixture rows landed inside wave-A commit `471cdf7` (shared-file sweep while I4 was mid-commit; content verified correct in HEAD) |

## GATE R/0 decisions — honored

**jamendo is ENV-GATED.** `JAMENDO_CLIENT_ID` is absent on this machine → the adapter is inert and provably made **zero network calls**:

- `python sources/jamendo.py` → prints `jamendo: inert — register at devportal.jamendo.com for a free JAMENDO_CLIENT_ID; the adapter ships disabled until keyed (GATE R).` → **exit 0**.
- `fetch_lyrics_source.py --source jamendo --catalog-only` → `ERROR: source 'jamendo' is env-gated: set JAMENDO_CLIENT_ID to enable it (adapter ships inert until keyed, SPEC §6.3)` → **exit 2** (W1 `check_env_gate` fires before any adapter code — no request possible).
- Env gate reads `JAMENDO_CLIENT_ID` from process env **or** `Genious_lyrics_extractor/.env`: import-time `bootstrap_env()` (`os.environ.setdefault`, pure file IO — zero network) makes .env keys visible to the dispatcher's env-only gate; `resolve_adapter` runs before `check_env_gate`, so it works end-to-end.
- Keyed (untested live — no key): `/v3.0/tracks` `include=lyrics`, `license_ccurl`→SPDX via `LICENSE_URL_MAP`, license-classed categories (`by|cc0|by-sa|by-nc|by-nd|other`), TASL (creator=`artist_name`, source_url=`shareurl`), code-6 rate-limit backoff, `fetch_lyrics` re-queries by `id` and drops `no-lyric-text`/`not-found`. `license_of` can only *downgrade* the cc-by registry default (unresolvable URL → `unknown`/`study-only`/`no`).

**lrclib is study-only FOREVER.** `release_ok='no'` is enforced as a testable invariant: every catalog row and every fetched song JSON carries `license='proprietary'`, `license_tier='study-only'`, `release_ok='no'`. Verified on disk post-pilot (25/25 rows).

## Test evidence

### Run result
```
pytest tests/test_lyrics_sources_jamendo.py tests/test_lyrics_sources_lrclib.py -m "not slow" -q
→ 47 passed, 2 deselected (slow), 1 warning — exit 0 (2.86s)
pytest tests/test_lyrics_sources_lrclib.py -q -m slow
→ 1 passed, 20 deselected — exit 0 (2.33s; real /api/get-cached hit)
pytest … + tests/test_lyrics_sources_core.py -m "not slow" -q
→ 99 passed, 1 failed — the failure is ANOTHER LANE's in-flight state:
  TestStructural.test_registry_json_committed_and_valid asserts len(sources)==20
  while wave-A I3's uncommitted registry.json merge (sr+en → wikisource_pd)
  reads 19. Not I8 scope; their lane's fix was mid-edit during this session.
```

### Inert-path test (verbatim — `tests/test_lyrics_sources_jamendo.py`)
```python
class TestEnvGateInertPath:
    def test_missing_key_iter_catalog_raises_without_network(self, unkeyed):
        spy = _boom_session()
        with pytest.raises(common.EnvGateError) as ei:
            list(jamendo.iter_catalog(limit=5, session=spy))
        assert ei.value.env_var == "JAMENDO_CLIENT_ID"
        assert ei.value.source_id == "jamendo"

    def test_inert_report_exits_0_and_makes_no_requests(self, unkeyed, capsys,
                                                      monkeypatch):
        # belt-and-braces: any stray requests.get would explode
        monkeypatch.setattr(
            common, "requests",
            types.SimpleNamespace(
                get=lambda *a, **k: (_ for _ in ()).throw(
                    AssertionError("network call attempted"))))
        rc = jamendo.main([])
        out = capsys.readouterr().out
        assert rc == 0
        assert "inert" in out
        assert "devportal.jamendo.com" in out
```
(plus `test_missing_key_fetch_lyrics_raises_without_network`, `test_missing_key_iter_catalog_allow_inert_yields_nothing`, `test_status_reports_inert`, `test_dispatcher_env_gate_refuses_before_network` — all passed; every inert path carries a raise-on-`get` transport so a stray request would explode.)

### lrclib `release_ok='no'` invariant test (verbatim — `tests/test_lyrics_sources_lrclib.py`)
```python
class TestReleaseOkInvariant:
    def test_license_of_is_locked_study_only(self):
        for e in lrclib.iter_catalog(seed=FIXTURES / "lrclib_seed.json"):
            info = lrclib.license_of(e)
            assert info.license == "proprietary"
            assert info.license_tier == "study-only"
            assert info.release_ok == "no"  # FOREVER — never 'yes'

    def test_every_catalog_row_is_release_ok_no(self):
        """A lrclib catalog row with release_ok='yes' is a blocker."""
        for e in lrclib.iter_catalog(seed=FIXTURES / "lrclib_seed.json"):
            assert e.release_ok == "no", f"invariant violated: {e.title}"
            assert e.license_tier == "study-only"
            assert e.license == "proprietary"

    def test_every_fetched_song_is_release_ok_no(self, monkeypatch):
        """The invariant holds through the full fetch path, for every
        upstream record shape (full, synced-only, search hit)."""
```
(`test_every_fetched_song_is_release_ok_no` exercises get-cached→get and search paths; all passed.)

## Pilots

- **jamendo:** skipped — no key (`JAMENDO_CLIENT_ID` unset, not in `.env`). Inert state verified live (exits 0 / 2 above, zero network). To activate: register free at devportal.jamendo.com, then `fetch_lyrics_source.py --source jamendo --catalog-only --limit 50`. Lyric fill-rate still unverified (GATE 0 Q2).
- **lrclib:** **live pilot succeeded** — `_seed.json` (25 well-known rows: 15 full `artist/title/album/duration` signatures → get-cached/get, 10 artist+title → search). Command:
  `fetch_lyrics_source.py --source lrclib --limit 25` → **exit 0**:
  ```
  [lrclib] catalog -> data\toolshop\lyrics\lrclib\_catalog.json (25 new, 25 total)
  [1/25] OK (tracks): Daft Punk — One More Time   …   [25/25] OK: Eurythmics — Sweet Dreams
  [lrclib] index: 25 unique songs, 0 intra-corpus dupes
  [lrclib] done: {'fetched': 25, 'failed': 0, 'dropped': 0, 'skipped': 0}
  ```
  Post-run disk audit (this session): all 25 song JSONs `release_ok='no'`/`study-only`/`proprietary`; **25/25 carry `synced_lyrics` (LRC) AND `lyricsfile` (YAML per-line ms)** — whisperX weak-label fuel landed; `_index.json` license fields all `no`. `data/` is gitignored — corpus intentionally uncommitted.

## Deviations from task spec

1. **Pacing pinned at ≥1.5 s, not the registry's 0.5 s** — wave-B constraint ("shared >=1.5s pacing anyway") overrides the lrclib politeness note (`min_interval_s: 0.5`); adapter passes `min_interval_s=MIN_INTERVAL_S=1.5` explicitly. Registry row left untouched (frozen SPEC §2.1).
2. **Catalog `foreign_identifier` = stable `seed:` key, not the LRCLIB id** — the numeric id is unknown until fetch; stamping it on the catalog row would change the dedup key mid-flight and duplicate rows on relist. The LRCLIB id lands on the song JSON (`foreign_identifier`) + `meta.lrclib_id` per SPEC §1.3 instead.
3. **`lyricsfile` kept as its own field AND `synced_lyrics` holds the LRC** — SPEC §3.3 defines both fields; both are populated (task text said "into a synced_lyrics field" — superseded by the frozen schema's two-field split).
4. **Jamendo exits 0 only at the adapter's own entry point** (`sources/jamendo.py` main / `iter_catalog(allow_inert=True)`). Under `fetch_lyrics_source.py` the W1 `check_env_gate` contract exits **2** before adapter code — that exit code is the dispatcher's, tested and unchanged; both are zero-network.
5. **No `fetch_lyrics_source.py`/`_common.py`/`registry.py` edits** — everything stayed inside I8 scope.

## Tree state / blockers for downstream waves

- `toolshop closeout` exit **1** — FAIL on dirty tree + 6 unpushed commits, **none of which are I8 leftovers**: wave-A I3 (registry.json wikisource merge + core-test asserts), wave-B siblings I6/I7 (mudcat/hymnary/sacred_texts/wikisource/gutenberg files + fixtures + scratch_*), and unrelated lanes (MAirina_Tucc, ogcm, suno). My scope: `git status` on `sources/{jamendo,lrclib}.py`, both test files, my fixtures, CHANGELOG.md → **all clean post-commit**. Full evidence block below.
- **`nul` file at repo root** — junk from a mis-redirected Windows command (another lane); owners should delete.
- **Stray scratch files** (`scratch_*.html/py`, `wt_bog_probe.txt`, `.scratch_i6/`) — other lanes' probes; flagged for their close-outs.
- **W5 note:** lrclib corpus is ready for `build_database(corpus='lrclib', incremental=)`; `synced_lyrics`/`lyricsfile` ride the song JSONs. jamendo corpus dir will materialize on first keyed run.
- **Push state:** `2a14177` is committed but unpushed (`@{u}..HEAD` = 6 commits across lanes — push is the orchestrator's call once sibling lanes finish).

## `toolshop closeout` evidence block (verbatim, exit 1 — other lanes' dirty paths, none mine)

```
--- verdict ---
FAIL
  - working tree not clean (staged/unstaged/untracked changes)
  - unpushed commits on current branch:
2a14177 feat(#066): lyrics-sources WB I8 - jamendo env-gated adapter + lrclib study-only adapter
b5e9898 docs(#065): lyrics-sources WA I2 handoff
c72b2ee feat(#065): lyrics-sources WA I2 — ccMixter adapter ...
eea32b5 docs(#064): lyrics-sources WA I4 handoff ...
471cdf7 feat(#064): lyrics-sources WA I4 — pdinfo title-index adapter ...
497726a feat(#063): GATE S3 - simple recognizable motif ...
```

`git status --porcelain` (full output captured this session) shows: my 14 files all under `2a14177`; remaining `M`/`??` = `registry.json`, `waves_megaplan.json`, `test_lyrics_sources_{catalog,core}.py`, `sources/{wikisource_pd,gutenberg_pd,mudcat_digitrad,hymnary,sacred_texts}.py`, `tests/test_lyrics_sources_{wikisource,mudcat}.py`, sibling fixtures, `scratch_*`, `.scratch_i6/`, `nul`, MAirina_Tucc/*, ORCHESTRATION/ogcm_flip/*, lyrics_research/* — all belong to parallel in-flight lanes, declared here per close-out discipline.
