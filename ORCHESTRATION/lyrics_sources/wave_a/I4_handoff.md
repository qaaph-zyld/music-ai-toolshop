# I4 handoff — wave A catalog-only/manual adapters, lyrics-sources megaplan

**Wave:** WA (agent I4) · **Date:** 2026-10-01
**Scope delivered:** `Genious_lyrics_extractor/sources/{pdinfo,looperman}.py` + `tests/test_lyrics_sources_catalog.py` + 4 fixtures + CREDITS.md update + registry §2.1 verification + live pdinfo pilot.
**Commit:** see footer (staged scope = the files above + CHANGELOG + this handoff only).

## What landed (task → file)

| Task | Where | Notes |
|---|---|---|
| 1 `sources/pdinfo.py` | `sources/pdinfo.py` | `fetch_policy='catalog-only'` adapter (SPEC §6.3): `iter_catalog` harvests the 65 static list pages (best/less A–Z + 6 genre + 7 year) ONCE via `polite_get` into `data/toolshop/lyrics/pdinfo/_cache/pages/` (fetch-once, cache-forever — SPEC §9); regex parser handles both `<b>` (A–Z lists) and `<span class="b">` (genre pages) year markup; dedup-merges songs across lists on product id (→ `foreign_identifier`, e.g. `pdinfo-TP00012`); see-also rows kept as `row_kind='see-also'` alias entries; `license_of` → constant `pd`/`LicenseRef-public-domain`/`yes`. Entries carry `meta.pd_claim='unverified'` + `meta.fetch_hint='resolve-via-wikisource'`. **V/C/N/P lyric-snippet blocks are never harvested.** No `fetch_lyrics` — no lyrics exist on the site. |
| 2 `sources/looperman.py` | `sources/looperman.py` | **ZERO network code** (ToS bans scraping AND ML training, R3 §1 — BLOCKER honored). `iter_catalog(limit, offset, *, path=None, data_dir=None)` precedence: explicit `path=` file/dir → `data/toolshop/lyrics/looperman/_import/` drop-zone (`*.json/*.jsonl/*.csv`) → hand-maintained `_catalog.json` fallback (idempotent fid round-trip, SPEC §9). Emits **plain dicts** in `CatalogEntry.to_dict()` shape — does NOT import `sources._common` since that would pull `requests` into the module's import graph; `upsert_entries` accepts dicts verbatim. Uploader free-text (`description`/`lyrics`/`comment`/`notes`) refused by whitelist — never reaches the catalog. `license_of` → constant `uploader-terms`/`no`/`proprietary`. No `fetch_lyrics` symbol exists. |
| 3 registry verification | `sources/registry.json` | **All 20 rows conform to SPEC §2.1 — no drift, no edit.** voclr/acapellas4u: `uncleared`/`catalog-only`/`adapter:null`/`corpus_tag`/`proprietary`; 6 paid packs: `paid-rf`/`manual`/`adapter:null`/`corpus_tag:null`; pdinfo: `pd`/`catalog-only`/`adapter:pdinfo`; looperman: `uploader-terms`/`manual`/`adapter:looperman`. Also verified: no `sources/<id>.py` exists for any `adapter:null` row (registry-rows-only invariant — test-encoded). |
| 4 tests | `tests/test_lyrics_sources_catalog.py` | 72 tests — see "the no-network contract" below. |
| 5 pilot | `data/toolshop/lyrics/pdinfo/` | **LIVE harvest succeeded** (exit 0): `--source pdinfo --catalog-only` fetched all 65 pages at ≥1.5 s pacing → `_catalog.json` = **6,750 entries** (6,617 songs + 133 see-also; best-known 1,704 / less-known 4,959 / genre 87 / year 0 — `pd-popular-songs-<year>` pages are empty stubs today; `less-g` 404 tolerated). 65 cached page files; re-run replays offline. Gitignored — not committed. |

## Deviations from task text (SPEC-frozen resolutions)

1. **Corpus dir `pdinfo`, file `_catalog.json`** — task text said `data/toolshop/lyrics/pd_titles/_catalog.jsonl` (pre-freeze naming, same drift class as W1). The frozen SPEC (§2.1 corpus_tag `pdinfo`, §3.1 `_catalog.json`) + the already-committed registry row resolve to `lyrics/pdinfo/_catalog.json`. Followed SPEC.
2. **`fetch_hint` field name** — SPEC §9 describes the purpose ("feeds wikisource/gutenberg lookups") but doesn't name a field; implemented as `meta.fetch_hint='resolve-via-wikisource'` verbatim from the task text.
3. **looperman emits dicts, not `CatalogEntry` objects** — deliberate zero-import stance (importing `_common` pulls `requests`). Contract shape preserved: `iter_catalog` + `license_of` exist, `fetch_lyrics` doesn't; serialized rows are field-identical.
4. **looperman `_import/` drop-zone added alongside the SPEC §9 `_catalog.json` read** — task text's drop-zone and SPEC's hand-maintained-file semantics are merged via the precedence list (path → drop-zone → _catalog.json).
5. **CHANGELOG number #064, not #063** — `#063` was already used by a concurrent GATE-S3 commit subject (`497726a`); next free number taken per AGENTS.md collision rule.

## THE no-network contract test (verbatim, `tests/test_lyrics_sources_catalog.py`)

```python
class TestLoopermanNoNetwork:
    """Looperman ToS bans scraping AND ML training verbatim (R3 §1), so
    sources/looperman.py must contain zero network code — proven three ways:
    source-text scan, absent fetch_lyrics, and a fresh-interpreter import
    that must place no network stack in sys.modules."""

    _BANNED_PATTERNS = (
        r"^\s*import\s+requests\b", r"^\s*from\s+requests\b",
        r"^\s*import\s+urllib\b", r"^\s*from\s+urllib\b",
        r"^\s*import\s+urllib3\b", r"^\s*from\s+urllib3\b",
        r"^\s*import\s+http\b", r"^\s*from\s+http\b",
        r"^\s*import\s+socket\b", r"^\s*from\s+socket\b",
        r"^\s*import\s+ssl\b", r"^\s*from\s+ssl\b",
        r"^\s*import\s+httpx\b", r"^\s*from\s+httpx\b",
        r"^\s*import\s+aiohttp\b", r"^\s*from\s+aiohttp\b",
        r"^\s*import\s+ftplib\b", r"^\s*import\s+smtplib\b",
        r"\burlopen\b", r"\burlretrieve\b",
        r"\brequests\.", r"\burllib\.", r"\bhttpx\.",
        r"\bsocket\.", r"\baiohttp\.",
        r"https?://",
    )

    def test_looperman_source_contains_no_network_code(self):
        """Source-text proof: no network imports, no fetch calls, no URL
        constants. The docstring may mention the domain name but never a
        fetchable URL."""
        src = LOOPERMAN_PATH.read_text(encoding="utf-8")
        for pat in self._BANNED_PATTERNS:
            assert not re.search(pat, src, re.M), \
                f"network code found in looperman.py: {pat!r}"

    def test_looperman_has_no_fetch_lyrics(self):
        mod = importlib.import_module("sources.looperman")
        assert not hasattr(mod, "fetch_lyrics"), \
            "manual sources must not define fetch_lyrics (SPEC §6.3)"

    def test_looperman_import_pulls_no_network_stack(self):
        """Fresh-interpreter proof: importing sources.looperman must not
        add requests/urllib/http/socket/ssl to sys.modules — the module
        carries no network stack at all, not even transitively. (Delta
        measured against interpreter startup, which already holds
        urllib.parse via site hooks.)"""
        code = (
            "import sys\n"
            "before = set(sys.modules)\n"
            f"sys.path.insert(0, {str(EXTRACTOR)!r})\n"
            "import sources.looperman\n"
            "net = ('requests', 'urllib', 'urllib3', 'http', 'socket',\n"
            "       'ssl', 'httpx', 'aiohttp', 'ftplib', 'smtplib')\n"
            "bad = sorted(m for m in set(sys.modules) - before\n"
            "           if m.split('.')[0] in net)\n"
            "print(bad)\n"
            "sys.exit(1 if bad else 0)\n"
        )
        res = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, timeout=60,
        )
        assert res.returncode == 0, (
            f"network modules leaked via looperman import: "
            f"{res.stdout.strip()} / {res.stderr.strip()}")
        assert res.stdout.strip() == "[]"

    def test_iter_catalog_runs_with_sockets_blocked(self, monkeypatch):
        """Runtime proof: even if a code path somehow reached for the
        network, a blocked socket layer must not stop iter_catalog."""
        def boom(*a, **k):
            raise AssertionError("network access attempted in looperman")
        monkeypatch.setattr(socket, "create_connection", boom)
        monkeypatch.setattr(socket.socket, "connect", boom)
        entries = list(looperman.iter_catalog(path=LOOPERMAN_JSON))
        assert entries, "iter_catalog must parse the export with no network"

    def test_license_of_is_constant_policy(self):
        info = looperman.license_of({"title": "x"})
        assert info["license_tier"] == "uploader-terms"
        assert info["release_ok"] == "no"
        assert info["license"] == "proprietary"
```

## Verification evidence (quoted)

`pytest` — exit 0 (both files run together):
```
$ .venv/Scripts/python.exe -m pytest tests/test_lyrics_sources_catalog.py tests/test_lyrics_sources_core.py -q
........................................................................ [ 57%]
.....................................................                    [100%]
125 passed, 1 warning in 9.23s
```

CLI smoke — policy gate (exit codes 2 = policy refusal, 0 = ok):
```
$ fetch_lyrics_source.py --source looperman
ERROR: source 'looperman' has fetch_policy 'manual' — lyric fetching is not permitted for this source (SPEC §1.2). Use --catalog-only for catalog listing.
rc=2
$ fetch_lyrics_source.py --source looperman --catalog-only
[looperman] catalog -> ...\lyrics\looperman\_catalog.json (0 new, 0 total)
[looperman] catalog-only: {}
rc=0
```

Pilot — live PDInfo harvest, exit 0:
```
$ fetch_lyrics_source.py --source pdinfo --catalog-only
[pdinfo] catalog -> D:\Projects\Music-AI-Toolshop\data\toolshop\lyrics\pdinfo\_catalog.json (6750 new, 6750 total)
[pdinfo] catalog-only: {'pending': 6750}
```
Post-hoc spot-check (3 real rows):
```
pdinfo-RR00292  "At a Georgia Camp Meeting"  creator="Kerry Mills"  year=1897  genre="Ragtime, Music Hall"  lists=[best-a]
pdinfo-RP00293  "At A Mississipi Cabaret"    creator="Albert Gumble, A. Seymour Brown"  year=1914  lists=[best-a, genre-popular-songs]   ← cross-list dedup merged
pdinfo-xref-genre-popular-songs-vive-lamour  "Vive L'Amour"  row_kind=see-also
```

`git check-ignore -v` on `data/toolshop/lyrics/pdinfo/_catalog.json` + `data/toolshop/lyrics/looperman/_import/README.txt` → `.gitignore:47:data/` (exit 0) — corpus never committed.

## Concurrency notes for the orchestrator

- **Other WA/WB agents are live in this tree.** Untracked files NOT staged by me: `sources/{ccmixter,jamendo,lrclib}.py`, `tests/test_lyrics_sources_{ccmixter,jamendo}.py` + their fixtures. My `test_every_shipped_adapter_matches_policy` already validates their module shape as they land — it passed against them (they conform).
- **`CREDITS.md` committed with a ccmixter fixture row** (concurrent agent I2's edit — removing it would clobber their working tree; their fixture file lands in their commit). Flagged so the reviewer doesn't count it as my provenance claim.
- **`ORCHESTRATION/lyrics_sources/waves_megaplan.json` is dirty** (orchestrator's I6 rework) — left unstaged, not mine.
- **`data/toolshop/lyrics/looperman/_import/README.txt`** — drop-zone usage doc for the user (uncommitted by design).

## Risks / notes for downstream waves

- **Year pages yielded zero** — `pd-music-genres/pd-popular-songs-<1923-1929>.php` render empty tables now (verified live). 6,750 comes from best/less/genre lists alone.
- **W5 must tolerate catalog-only corpora** — `pdinfo`/`looperman` produce `_catalog.json` only (no song dirs, no `_index.json`); a corpus `build_database` sweep must skip empty corpora rather than fail.
- **`license_of` on looperman returns a plain dict** — dispatcher only calls `info.apply_to()` inside the fetch loop, which never runs for `manual` policy; documented in module.
- **pdinfo harvest is resumable via page cache** — a mid-run abort re-runs cheaply (cached pages never refetch); 404s cache as empty docs.
- **`toolshop closeout` not run** — other lanes' dirty files would make its evidence block misleading; quoted `git status`/`git log` below instead.

## Staged scope + tree state

Staged in this wave's commit: `sources/{pdinfo,looperman}.py`, `tests/test_lyrics_sources_catalog.py`, `tests/fixtures/lyrics_sources/{pdinfo_list_sample.html,pdinfo_genre_sample.html,looperman_export_sample.json,looperman_export_sample.csv,CREDITS.md}`, `CHANGELOG.md` (#064), this handoff.

Commit: `471cdf7` — `feat(#064): lyrics-sources WA I4 — pdinfo title-index adapter + looperman zero-network manual import + catalog contract tests` (10 files, +1778) + a `docs(#064)` commit carrying this handoff footer.
