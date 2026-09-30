# I3 handoff — wave A: wikisource_pd (sr+en) + gutenberg_pd adapters

**Agent:** I3 (lyrics-sources megaplan, wave A) · **Closed by:** orchestrator
(agent session ended before commit; work verified in-session, one parser bug
found + fixed by orchestrator before commit).
**Lane scope:** `sources/{wikisource_pd,gutenberg_pd}.py`,
`tests/test_lyrics_sources_{wikisource,gutenberg}.py`, 9 fixtures,
`registry.json` merge, `data/toolshop/lyrics/{wikisource_pd,gutenberg_pd}/`
(uncommitted), this handoff.

## Delivered

- `sources/wikisource_pd.py` (625 ln) — merged sr+en corpus per wave-A
  prompt: MediaWiki `action=parse&prop=wikitext` (NOT extracts) category walk,
  `maxlag=5`, ≤50 titles/req, serial + descriptive UA (SPEC §9; R2 §3
  etiquette). Per-page license-template scan (`scan_license_templates`) —
  `non-pd` drops, `by-sa` → `conditional`. Frozen sr categories
  (zenske/epske/lirske/vuk-zbirke/erlangen/ostalo) + six en categories.
- **Normalization (F4, mandatory):** `raw_lyrics` byte-for-byte Cyrillic +
  `script:"cyrillic-original"`; `clean_lyrics` = `cyrtranslit.to_latin(..,'sr')`
  + diacritic fold identical to `lyricsdb.normalize_text`; section labels
  fold to `Strofa` so `lyricsdb._parse_section_label` doesn't misclassify.
- `sources/gutenberg_pd.py` (626→659 ln post-fix) — curated WORKS table
  (Child I–V #44969/47692/62474/63116/71104, Songs of the West #56625,
  Elizabethan #27129, Yorkshire #47607, Old Ballads #7535, Bundle of
  Ballads #2831). Texts fetched via the **aleph.gutenberg.org mirror**
  dir-listing (PG main is human-only for bulk — R2; mirror resolves
  `{n}-8.txt` variants; TLS verify disabled on the aleph session only —
  corporate TLS interception breaks it; documented deviation).
  Kind-dispatched splitters: `sotw` (`No. N TITLE` heads), `child`
  (ballad № + CAPS title, `A.`/`B.`… variants), `caps` (verse-probe gated).
- Registry: `sr_wikisource`+`en_wikisource` → `wikisource_pd` single merged
  row (19 total); `gutenberg-pd` → `gutenberg_pd` corpus_tag fix. Test
  asserts amended 20→19 in both catalog test files.
- Tests: `test_lyrics_sources_wikisource.py` **18**, `test_lyrics_sources_gutenberg.py` **15**.
- 9 committed fixtures (6 MediaWiki-shaped JSON incl. real PD Serbian stanza
  «Два бора и јела» + en PD ballad; 3 PG excerpts w/ real PD text) —
  provenance in CREDITS.md.

## Orchestrator-found bug fixed pre-commit (double-spacing)

PG texts run ~60% blank lines (double-spaced OCR layout): every verse line
is followed by one blank, stanza breaks use runs ≥2. The splitters treated
*any* blank as a stanza break, so each stanza block captured only its
printed number — `fetch_lyrics` then dropped everything `too-short`
(pilot: 25/25 dropped, 0 fetched).

**Fix (orchestrator, this session):** `split_songs` now runs
`_squeeze_interline_blanks` (blank fraction >0.45 ⇒ collapse single blanks
between content lines, collapse runs ≥2 to one separator) and drops
`* * *` ornament dividers via `_DIVIDER_RE` before dispatch.

After: Child vol. I parses **125 variant-songs** with real bodies (was 0);
`The Cruel Mother [B]` → `Strofa 1: "She sat down below a thorn, / Fine
flowers in the valley, …"` verbatim.

## Verification (exit codes + key output)

```
pytest tests/test_lyrics_sources_{wikisource,gutenberg}.py -m "not slow" -q
→ 33 passed (exit 0)
```

- Normalization verbatim: `test_latin_fold` asserts
  `_latin(EXPECTED_SR_RAW) == EXPECTED_SR_CLEAN`;
  `test_sr_song_normalization_verbatim` asserts `clean_lyrics` folded-Latin
  + `script=="cyrillic-original"` on the real PD stanza fixture.
- License gate: non-PD template → dropped; `by-sa` → `conditional` rows.
- Gutenberg pilot (orchestrator-run, this session): catalog **243 entries**;
  `The Elfin Knight [B/C/D]` fetched OK post-fix; the 25 pre-fix
  `too-short` drops are stale catalog marks — cleared by the next
  `iter_catalog` rebuild (deterministic ids).
- Wikisource pilot: sr.wikisource.org rate-limited the IP (HTTP 429 on bare
  `meta=siteinfo` probe) during the session; re-probe returned 200 and the
  catalog walk was launched — multi-minute by design (~10.7k sr pages,
  serial ≥1.5 s). Result appended to the ledger when it lands; `--resume`
  makes it safe either way.

## Deviations

- Registry merged sr+en into one row (prompt-directed); corpus dir =
  `wikisource_pd`. If per-language split is ever wanted, the adapter's
  `_walk_sr`/`_walk_en` arms are already separate generators.
- aleph session has `verify=False` (TLS interception) — scoped to that
  session only; mirrors the constraint documented in `_session()`.
- 25 stale `too-short` drops in `_catalog.json` from the pre-fix pilot —
  cosmetic, self-heals on catalog rebuild.

## Commit

`feat(#069)` + `docs(#069)` — hashes recorded in the ledger.
