# I5b handoff — wave 5b: export_release.py + ccMixter pd-token fix

**Agent:** wave-5b implementer (`d4ab3b99`) · **Closed by:** orchestrator
(agent's final tool call rejected at closeout — work verified + committed
in-session).
**Lane scope:** `Genious_lyrics_extractor/export_release.py`,
`tests/test_export_release.py`, `sources/ccmixter.py` (pd-token remap),
`tests/test_lyrics_sources_ccmixter.py` (assert), `CHANGELOG.md` #071,
this handoff.

## Delivered

- `export_release.py` — SPEC §8.2 contract: `--release-cleared` reads
  lyrics.db via sqlite3 directly (no `import toolshop` — F-B1 honored),
  emits `release_ok='yes'` song JSONs to `<out>/<corpus>/<artist>-<title>.json`,
  `CREDITS.md` with per-item TASL attribution lines grouped by corpus+license
  (title — creator — source_url — license + license_url), and
  `RELEASE_MANIFEST.json` (generated_at, db_path, mode, counts_per_corpus,
  `pending_decisions` for conditional items, skipped-missing-source count).
  Default mode refuses study-only output without an explicit flag.
- ccMixter `lic=pd` remap: adapter now maps the API's
  `publicdomain/zero/1.0` report to `LicenseRef-public-domain` + PD-mark URL
  (ccMixter's pd lane is dedication-by-declaration predating CC0 — SPEC §1.3
  / R1 §3 — never `CC0-1.0`); the 6 existing `acappella-pd` song JSONs were
  repaired in place (verified: all now `LicenseRef-public-domain|pd|yes`).

## Verification (exit codes + key output)

```
pytest tests/test_{export_release,lyrics_sources_ccmixter}.py -m "not slow" -q
→ 50 passed (exit 0)
```

Live release smoke (orchestrator-run, this session):

```
export_release.py --release-cleared --out data/toolshop/lyrics/_export_smoke
→ exit 0
mode: release
emitted: 69 song JSON(s)
  ccmixter: 17 · gutenberg_pd: 3 · hymnary: 1 · mudcat-digitrad: 25 · sacred-texts: 23
pending_decisions: 0 · skipped (missing source): 0
```

**Gate proof:** `ls _export_smoke/` → `ccmixter gutenberg_pd hymnary
mudcat-digitrad sacred-texts CREDITS.md RELEASE_MANIFEST.json` — **no
genius/, no lrclib/ dir exists**. CREDITS.md carries verbatim TASL lines
(e.g. `"Geppetto V4 (Pell + Stems)" by coruscate — source:
ccmixter.org/files/Coruscate/70553 — license: CC-BY-2.5 (...)`).

## Commit

`feat(#071)` + `docs(#071)` — hashes recorded in the ledger.
