# Wave 1 · I1 handoff: MAirina Tucc v1 implemented

## Files created (all under `MAirina_Tucc/`, line counts)
- `mairina/`: `__init__.py` 23, `__main__.py` 5, `cli.py` 223, `corpus.py` 142, `keys.py` 76, `rank.py` 126, `anchors.py` 145, `multis.py` 99, `votes.py` 153, `used.py` 34, `flow.py` 62
- `tests/`: `conftest.py` 87, `test_keys_corpus.py` 93, `test_rank_anchors_multis.py` 129, `test_cli_flow_used.py` 144, `test_live_smoke.py` 32
- `mt.ps1` 7, `README.md` 61, `data/.gitignore` 5

## pytest summary line
`41 passed in 22.26s` (`python -m pytest MAirina_Tucc\tests -q`, run last after all edits)

## Live runs through `mt.ps1` (real lyrics.db; first 10 lines each)
`anchors --scheme AABB --lane drill --rng-seed 1`
```
Anchors AABB (rhyme)  lane=drill fresh=0.5 arm=learned ranker=v1 list=#1
Write each line so that it ends on its anchor. The tool never writes lines.
  1. [A] uradio           VERB  class -io  freq 15
  2. [A] dio              NOUN  class -io  freq 9
  3. [B] sinana           PROPN class -ana  freq 3
  4. [B] marijana         PROPN class -ana  freq 21
```
`rhyme imaš --lane drill` (snimaš is #5, with a score breakdown)
```
Rhymes for 'imaš'  lane=drill fresh=0.5 arm=base ranker=v1 list=#2
  1. klimaš             5.79  perfect-2 +6.00 | freq(5) +0.36 | fresh -0.57
  2. cimaš              5.71  perfect-2 +6.00 | freq(3) +0.28 | fresh -0.57
  3. otimaš             5.71  perfect-2 +6.00 | freq(3) +0.28 | fresh -0.57
  4. uzimaš             5.71  perfect-2 +6.00 | freq(3) +0.28 | fresh -0.57
  5. snimaš             5.57  perfect-2 +6.00 | freq(1) +0.14 | fresh -0.57
  6. znaš               3.52  perfect-1 +3.00 | freq(375) +1.19 | fresh -0.67
  7. baš                3.51  perfect-1 +3.00 | freq(341) +1.17 | fresh -0.66
  8. moraš              3.39  perfect-1 +3.00 | freq(85) +0.89 | fresh -0.50
  9. nemaš              3.39  perfect-1 +3.00 | freq(87) +0.90 | fresh -0.51
```
`multi "da me imaš"`
```
Multis for 'da me imaš'  lane=all fresh=0.5 arm=learned ranker=v1 list=#3
  1. da senidah                     0.53  words -0.40 | freq(384) +1.19 | fresh -0.26
  2. da ekipa                       0.44  words -0.40 | freq(702) +1.31 | fresh -0.47
  3. na ekipa                       0.35  words -0.40 | freq(466) +1.23 | fresh -0.47
  4. da senida                      0.24  words -0.40 | freq(415) +1.21 | fresh -0.56
  5. da je igra                     0.23  words -0.80 | freq(2736) +1.58 | fresh -0.55
  6. da je sipaj                    0.23  words -0.80 | freq(2747) +1.58 | fresh -0.55
  7. da jedina                      0.20  words -0.40 | freq(895) +1.36 | fresh -0.77
  8. da velika                      0.19  words -0.40 | freq(384) +1.19 | fresh -0.60
  9. da nervira                     0.18  words -0.40 | freq(470) +1.23 | fresh -0.65
```
`vote 1+` then `stats`
```
Saved 1 vote(s) on list #3 (multi).
---
Shown: anchor 1 lists/4 items, multi 1 lists/20 items, rhyme 1 lists/20 items
Votes: 1 (up 1, down 0) up-rate 100%
First 50 votes: 1/50 cast, up-rate 100% (pass: 40% or more)
Used: 0 of 44 distinct shown suggestions (0%)
Multi lists (first 20): 1 seen, 1 with an up-vote or used hit (pass: 10 of 20)
Run 'stats --ab' for the learned-vs-base test.
```
`flow` on a temp file (nonsense syllables, written and deleted under `data/`)
```
Flow: 3 lines | your median 4 syl | lane 'drill' median 12 syl
 line  syl  vs-you  vs-lane  text
    2    4      +0       -8  ba be bi bo
    3    4      +0       -8  da te snimas
    5    8      +4       -4  ba be bi bo bu ba be bi
```
(`stats --ab` with 1 vote prints "Not enough data yet. Keep voting.") The verification `data/mairina.db` was deleted afterwards so week-1 stats start clean. The word-index cache `data/index_3a770ed6.pkl` was left in place (git-ignored).

## lyrics.db modified time
- Before: `2026-08-09T00:47:25.7861022+02:00`
- After all runs: `2026-08-09T00:47:25.7861022+02:00` (size 67,096,576, unchanged, no `-wal`/`-journal` files). Unchanged.

## git status (`git -C D:\Projects\Music-AI-Toolshop status --short`)
My paths: `?? MAirina_Tucc/README.md`, `?? MAirina_Tucc/mairina/`, `?? MAirina_Tucc/mt.ps1`, `?? MAirina_Tucc/tests/`. `?? MAirina_Tucc/ORCHESTRATION/` is the orchestrator's. Everything else in the listing (` M ORCHESTRATION/...`, `? mastering_tool`, `? suno_prompter`, `?? ORCHESTRATION/...`, `?? handoffs/...`, `?? lyrics_research/...`) belongs to other sessions, plus one new path that appeared during the run, `?? toolshop/flip/sample_voices.py`, which is not mine. I ran no git add/commit/checkout/switch/stash.

## Deviations from the spec, and why
1. `MAirina_Tucc/data/.gitignore` exists but is **not visible to git**: the repo root `.gitignore` line 47 (`data/`) ignores the whole directory. The orchestrator must run `git add -f MAirina_Tucc/data/.gitignore` if it wants the file tracked; `mairina.db` and the caches are already ignored by the root rule.
2. `tests/` use `cli.main(..., lyrics_db=, data_dir=)` keyword overrides (no extra CLI flags) so tests never touch real data.
3. `--rng-seed` also fixes the A/B arm assignment, which makes a given seed reproducible. Without it, the arm is random 50/50. The arm is printed in each list header.
4. Re-voting an item replaces the earlier vote (the latest vote per shown item counts in boosts and stats). The spec is silent here.
5. `--seed` word is excluded from the anchors it fixes the class for. If `--lines` differs from the scheme length, the scheme cycles with new letters. Both are documented in the README.
6. Ranking constants (all in `rank.py`): perfect rhyme 3.0 per matched nucleus, assonance 1.5, consonance 1.0, freq 0.2*log(1+f), fresh 2.0*slider*class overuse, vote boost 2.0*((up+1)/(up+down+2)-0.5), used 1.5. `multis` internal beam and per-skeleton caps (60 and 40) keep 3-word search fast.
7. Live `stats` counts "first 50 votes" and the multi criterion as specified; "used rate" = distinct used candidates / distinct shown candidates.

## Observations for review
- Anchor quality: PROPN is allowed by the spec, so low-frequency proper nouns appear (`sinana`, freq 3). Consider raising `MIN_FREQ` or excluding PROPN if the user dislikes them.
- `multi` results are ranked by frequency per the spec. The result is skeleton-only matches (`da senidah`, `da je igra`), with no consonant similarity, so word-salad risk is exactly what the week-1 test measures.
- Cold start: the first command after `lyrics.db` changes builds the index (~8 s); later commands take ~3 s.

## Left undone
Nothing from the task list. Phase 2 items (UI, Hunspell fallback, line_rhymes) are out of scope per spec §8.
