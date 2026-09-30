# I7 handoff — wave B: hymnary + sacred_texts adapters

**Agent:** I7 (lyrics-sources megaplan, wave B) · **Closed by:** orchestrator
(agent session ended before commit; all work verified in-session before
committing).
**Lane scope:** `sources/hymnary.py`, `sources/sacred_texts.py`,
`tests/test_lyrics_sources_{hymnary,sacred_texts}.py`, 9 fixtures,
`data/toolshop/lyrics/{hymnary,sacred-texts}/` (uncommitted corpus), this
handoff.

## Delivered

- `sources/hymnary.py` (687 ln) — CSV-primary + HTML-fallback per GATE 0:
  `iter_catalog()` consumed the hymnary CSV export path (catalog built OK —
  527 pre-1931-filtered entries); `fetch_lyrics()` parses `/text/` pages.
  **Pre-1931 date gate enforced** — items whose instance cannot resolve to a
  pre-1931 publication are dropped (`date-unresolved`/post-1930 classes),
  plus a `_quarantine_bad_query/` trail for audit.
- `sources/sacred_texts.py` (390 ln) — static-page adapter for the
  sacred-texts.com Child Ballads mirror (SvelteKit `chapterContent.contentHtml`
  extraction, latin-1 mojibake handling per fixture).
- Tests: `test_lyrics_sources_hymnary.py` **22 tests**, `test_lyrics_sources_sacred_texts.py`
  **16 tests** — incl. the 1930/1931 boundary gate and date-unresolved drops.
- 9 committed fixtures (hymnary CSV + 5 synthetic /text/ pages; 3 sacred-texts
  page shells incl. one real PD excerpt) — provenance rows in CREDITS.md.

## Verification (exit codes + key output, verified at commit)

```
python -m pytest tests/test_lyrics_sources_{hymnary,sacred_texts}.py -m "not slow" -q
→ 38 passed (combined w/ wikisource run: 56 passed incl. wikisource 18) (exit 0)
```

### Pilots (live, this machine)

- **sacred-texts** — `fetch_lyrics_source.py --source sacred_texts --limit 25 --resume`
  → catalog **305 entries**; **23 fetched** (`child-ballads/*.json+.txt`),
  2 dropped, 280 pending. Spot-check: `traditional-babylon-or-the-bonnie-banks-o-fordie.json`
  = Child 14, `license=LicenseRef-public-domain`, `release_ok=yes`, 123
  sections, real ballad text.
- **hymnary** — catalog via CSV export: **527 entries** (pre-1931 filter
  applied at catalog stage); page fetch → **1 fetched** then hymnary.org
  returned **HTTP 403** on subsequent `/text/` requests (bot-block consistent
  with R2 §6 — widgets 403'd to the researcher too). Per GATE 0 decision the
  fetch path is **deferred-with-error**: catalog + 1 verified parse stand;
  remaining 522 pending resume whenever the block lifts or spacing lengthens.

## Deviations / notes

- Hymnary CSV export path WORKED for the catalog (contradicting R2's 403 on
  widgets — the export endpoint is distinct); only per-page text fetch 403s.
- `corpus_dir` for sacred_texts = `sacred-texts` (dash) per registry row.
- `_quarantine_bad_query/` = 3 items parked for audit rather than silently
  dropped — an I7 defensive choice beyond SPEC.

## Commit

`feat(#068)` + `docs(#068)` — hashes recorded in the ledger.
