# Wave 4 · Q1 handoff: Serbian-orthography anchors and attested-bigram multis

## Tests
`87 passed in 32.91s` (`python -m pytest MAirina_Tucc\tests -q`, was 60). Includes the live smoke test.

## Live checks (real lyrics.db, read-only)
- 20 unseeded `mt.ps1 anchors --scheme AABB --lane drill` runs: 80 anchors, **0 PROPN, 0 non-orthographic** (78 distinct words; sample: baca, faca, emotivna, naivna, grijeh, osmijeh, hoću ...). Total 95.7 s for the 20 runs; the first run rebuilt the index (10.9 s).
- Index: 26,753 forms, **93,539 distinct attested bigrams** (word pairs only). Cache version 2 -> 3.
- Multi, same 10 phrases as wave 3, lane all, `--max 20`. For every phrase: 20 results, every result's skeleton ends with the phrase's skeleton, every adjacent pair is an attested bigram, max final-word repeat 2, max first-word repeat 3, max 1 glue word, 0 PROPN finals, 0 artist names, about 0.4 s each. Top 5 verbatim:

| Phrase | n | Top 5 |
|---|---|---|
| pare i novac | 20 | kaže mi kompas / kaže ti koštaš / pare mi kompas / dalje ti koštaš / kaže mi mozak |
| bez tebe nema | 20 | sve se večeras / sve je nesrećna / vreme je nepar / vreme je svežanj / vreme je jecaj |
| noćas te vidim | 20 | noćas je hibrid / noćas je imidž / noćas se smirit / pola je hibrid / pola je imidž |
| u Panameri | 20 | ljubav na sentiš / ljubav na mečki / tu da zalečim / ljubav da spremni / sutra na sentiš |
| da me imaš | 20 | da jedina / brate rizla / da treniram / znam ne skidaj / znam se kristal |
| nema ljubavi | 20 | sve da ubaciš / sve da udariš / gde da ubaciš / sve da ugasi / gledaju da stigô |
| ne znam kako | 20 | je standardno / je maraton / je lagano / se lagano / nema ravnog |
| sve što imam | 20 | je bodigard / je otišla / se pomicat / je boginja / ne dolivaj |
| ti si moja | 20 | ti kišobran / vidim odraz / vidim odmah / vidim noćas / svi mi kompas |
| kad dođe noć | 20 | na pogrešnoj / na pogrešnom / samo dečko / samo nemoj / samo jednom |

(Wave 3 word salad such as `da sve kišobran` is gone: each adjacent pair now occurs in the corpus.)
- `mt.ps1 multi "da me imaš"` through the wrapper works (top: da jedina, brate rizla, da treniram).
- `lyrics.db` modified time: `2026-08-09T00:47:25.7861022+02:00`, unchanged (67,096,576 bytes, no `-wal`/`-journal`).
- `data/mairina.db` (created by the live runs) deleted; it does not exist now.
- `git status --short`: my work touches only `MAirina_Tucc/mairina/{anchors,corpus,keys,multis}.py`, `MAirina_Tucc/tests/{conftest,test_cli_flow_used,test_keys_corpus,test_rank_anchors_multis}.py` and and `MAirina_Tucc/README.md` (edited after the status snapshot, so the snapshot lists the eight code and test files). The other modified/untracked paths (`ORCHESTRATION/...`, `scripts/ogcm_sample.py`, `tests/test_flip_sample.py`, `toolshop/flip/sample_voices.py`, `lyrics_research/...`, `mastering_tool`, `suno_prompter`) belong to other sessions. No git add/commit/checkout.

## Changes
- **Fix 1** `keys.is_serbian_orthography(word)`: false for any of q, w, x, y or a doubled vowel (aa, ee, ii, oo, uu). `anchors.py`: `ANCHOR_POS = CONTENT_POS - {PROPN}`, and `_classes` skips forms failing the helper. `rhyme` and `multi` are unchanged (PROPN and such forms still rhyme).
- **Fix 2** `corpus.py`: `_build` now reads tokens `ORDER BY line_id, ordinal` and records `(prev, word)` when the previous kept token is in the same line with ordinal exactly one lower (after token hygiene: Latin only, no PUNCT/X/SYM/NUM, lowercased; a dropped token in between breaks the pair). `Index.bigrams` (frozenset of 2-tuples) is cached; `Index.predecessors()` derives next-word -> previous-words. `CACHE_VERSION = 3`.
- `multis.py` reworked: it builds combinations backwards from each final word using only words attested directly before the next word, so a 2-word result needs (w1,w2) and a 3-word result needs (w1,w2) and (w2,w3). 1-word results are unaffected. All earlier rules stay: skeleton suffix match, content non-PROPN final, one glue word, artist names out, caps 2 per final and 3 per first. No fallback: fewer results are shown when fewer survive. The per-skeleton cap of 40 words was dropped because the bigram lookup already bounds the search.
- `anchors.py` also retries a greedy sample (12 tries) when a conflict dead-ends it. This was needed for the seeded case, where a single unlucky pick failed a valid class.

## Tests added or changed (fixture words only)
- Orthography helper (rejects taboo, woo, kaboo, xilofon, quiz, yeah, aaa, beer, skiing, zoo, duu; accepts lava, imaš, srce, prst, džaba, ljubav, nemirna).
- Anchors: `taboo`, `kaboo`, `boo`, `woo` never appear across 80 runs while normal words do; a seed whose class holds only excluded words fails; with the helper patched off they return. PROPN `melisa` never appears and returns only if `ANCHOR_POS` is widened. Rhyme lists still contain the PROPN and the non-orthographic word.
- Bigrams: `da ekipa` attested from `Da Ekipa` (case-folded); `grade snimaš` (PUNCT between) and `pade snimaš` (Cyrillic between) not attested; `ekipa sade` (consecutive lines) not attested; pairs are 2-tuples of single words.
- Multi: `na ekipa` rejected, `da ekipa` kept; 3-word `grad sef snimaš` kept, `kan sef snimaš` rejected (one pair unattested); `grad te snimaš` kept (one glue word); `da te snimaš` rejected (two glue words) although both pairs are attested; fewer than 20 results with no padding; diversity caps still hold.
- Cache: bumping `CACHE_VERSION` rebuilds the index from the same file; the current cache holds bigrams; a version-2 style blob is rebuilt.
- Fixture: added words `na`, `ekipa`, `grad`, `sef`, `kan`, `taboo`, `kaboo`, `boo`, `woo`, and 7 multi-token lines in song 1. Test data changes: `snimaš` freq 12 -> 17.

## Notes
- `mt.ps1 ... | Select-Object -First N` reports exit -1 because the pipe closes early; it is not a tool error.
- Bigram lookups are corpus-wide, not lane-specific; the lane still filters which words may be used.
