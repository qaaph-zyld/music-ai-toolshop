# Wave 3 · F1 handoff: fixes for the wave-2 needs-fix verdict

## Tests
`60 passed in 25.07s` (`python -m pytest MAirina_Tucc\tests -q`, was 41). Includes the live smoke test.

## Numbers (reviewer's samples, real lyrics.db read-only, rebuilt index)
- 200 seeded drill anchor runs (`AABB`, seeds 0-199, 400 rhyme pairs): **0 word+extension pairs = 0.00%** (target 2% or less; before: 16%). Extra: 0 of 800 anchors with freq under 5, 0 artist-name tokens, 48 PROPN (6%, allowed by spec).
- 10 multi phrases, lane all, 20 results each (7 from the V1 handoff: `pare i novac`, `bez tebe nema`, `noćas te vidim`, `u Panameri`, `da me imaš`, `nema ljubavi`, `ne znam kako`; the handoff names only 7, so I added `sve što imam`, `ti si moja`, `kad dođe noć`):
  - max final-word repeats: **2** (cap 2; before: 18/20)
  - max first-word repeats: **3** (cap 3; before: 18/20)
  - artist names: **none** (`da senidah`/`da senida` gone)
  - PROPN finals: 0; combinations with more than one glue word: 0; every result's skeleton ends with the phrase's skeleton; all 10 phrases still return 20 results.
- Nit 1: `rhyme imaš --artist senidah --lane drill` -> "No rhymes found ... lane 'drill'" (senidah has no drill songs); `--lane all` -> znaš, naš, baš ... So they now differ.
- `lyrics.db` mtime: `2026-08-09T00:47:25.7861022+02:00`, unchanged.
- `data/mairina.db`: created by a live `mt.ps1` check and deleted; does not exist now.
- `git status --short`: from this work only `MAirina_Tucc/README.md`, `mairina/`, `mt.ps1`, `tests/` (plus the orchestrator's `MAirina_Tucc/ORCHESTRATION/`). Other listed paths belong to other sessions. No git add/commit/checkout.

## Changes
- B1 `anchors.py`: `conflict(a, b)` rejects a pair if either word ends with the other, or if tails are equal and the letters before the tail are identical. Applied while sampling each group (and against the `--seed` word). A class that cannot supply k non-conflicting words is dropped and another class is tried. The same-lemma rule is kept.
- B2 `multis.py`: max 2 results per final word, 3 per first word; at most one glue word per combination (so never two adjacent); final slot needs a content word that is not PROPN; artist-name tokens are removed from the vocabulary. The target-skeleton rule is unchanged. The full-combination beam grew to 2000 before the caps.
- `corpus.py`: `artist_tokens()` builds the denylist from `songs.primary_artist` and `target_artist` (split on spaces and hyphens, standalone `x` dropped, lowercased) plus the variants `senida senidah jalom lamelo balkaton biba`. `Index.artist_names` is used by `Index.vocab()`, so anchors, rhymes and multis all exclude it. Cache version bumped to 2.
- Nit 1: the index stores frequency per cohort and artist, so `--artist` now intersects with `--lane`.
- Nit 2: the A/B arm is drawn from its own `random.Random()` in `cli._setup`; `--rng-seed` no longer pins it.
- Nit 3: `used.read_text` decodes UTF-8 (BOM ok), falls back to cp1250 on failure, and NFC-normalizes text and candidates.
- Nit 4: anchors `MIN_FREQ` 3 -> 5.

## Tests added (fixture words only)
Conflict pairs (`nekad/ponekad`, `padnem/upadnem`, `nemirna/mirna`, `srolam/rolam`, `grabim/zgrabim`) and no false conflict on real rhymes; anchors never pair extensions across 60 seeds; a seed whose class has only an extension fails; `MIN_FREQ` 5 (`trava` freq 4); multi glue cap, PROPN/artist final ban, diversity caps (defaults and tightened), skeleton rule; artist tokens built from songs and out of the vocab, and out of anchors and rhymes; artist x lane intersection (index, rank); arm independent of `--rng-seed`, with seeded anchors still reproducible; `used` NFD and cp1250. The fixture gained `nekad`, `ponekad`, `melisa` (PROPN), `senida` (artist token), `trava` (freq 4), and its per-word line count went from 3 to 6.

## Deviations and notes
- The `x` rule: a standalone `x` token is dropped; the letter x inside names is kept.
- Extra artist-name variants beyond the corpus columns are a hard-coded list in `corpus.EXTRA_ARTIST_TOKENS` (`senida senidah jalom lamelo balkaton biba`).
- Artist-name tokens are removed from the whole vocabulary (any slot), a little stricter than "final slot" for multis, as the task asked for anchors and rhymes. The side effect is that real words that are also artist names (e.g. `corona`, `rasta`, `maya`) are excluded everywhere.
- The wave-1 deviation about `--rng-seed` pinning the arm is void.
- Not touched: nits 4, 7, 8, 10 from the review (fresh slider inside a class, `vote -3+`, inflectional classes, first-50 ordering).
