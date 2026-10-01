# Wave 2R Handoff (R2) - review fixes M1-M4, L6, L8-L10

**Status: DONE.** No git operations. Only `MAirina_Tucc\mairina\` and `MAirina_Tucc\tests\` touched (plus this file). lyrics.db read-only through the existing guards; live runs used a `%TEMP%` data dir.

## pytest

`"D:\Projects\Music-AI-Toolshop\.venv\Scripts\python.exe" -X utf8 -m pytest "D:\Projects\Music-AI-Toolshop\MAirina_Tucc\tests" -q -p no:cacheprovider -rs`

```
220 passed, 1 warning in 169.13s (0:02:49)
```

0 skipped (205 baseline + 15 new). The warning is the old `requests`/urllib3 one.

## Per finding: change (file) + test

**M1 vs-star honesty.** `fingerprint._phrase` now quotes the raw star mean (`nf["mean"]`), never `shrunk`; direction word is `x < mean`; appends ` (n=<nf n>)` when n < `LOW_CONFIDENCE_N` (10). `deviations` still z-scores against `shrunk`/`sigma` (ranking only). `cli._cmd_xray` fallback is now `close to your ★ lines (n=3)` under 10 stars. `mt me` unchanged (raw mean, shrunk, lane mu, sigma).
Tests (`test_stars_fingerprint.py`): `test_phrases_quote_the_raw_star_mean_and_the_shrunk_value_only_ranks` (every feature, shrunk text asserted absent, z still shrunk-based), `test_phrases_carry_the_actual_n_below_ten_stars_and_none_from_ten` (n=1,3,9 flagged; 10, 40 not), xray `(n=3)` assertions in `test_xray_adds_vs_star_only_from_three_stars`; existing compare tests updated for the suffix and for `mean=0.7, shrunk=0.7` in the alliteration case.

**M2 token-less stars.** `fingerprint.star` raises `VoteError("Line N has no words ...")` when `tokenize(line)` is empty, before any analysis or write (exit 1 via the CLI). Test: `test_stars_on_wordless_lines_are_rejected_and_nothing_is_stored` (`...`, `123`, `— —`; 0 rows; a real line still stars).

**M3 lane 'all'.** `fingerprint.stars` for a specific lane is now `WHERE lane IN (?, 'all')`; `None`/`all` still pool everything. `me`, `stars`, `xray` all go through it. Test: `test_a_star_saved_with_the_default_lane_counts_in_every_lane_view` (default-lane stars in `me/stars/xray --lane drill`; a pop-only star excluded from drill, included in pop).

**M4 atlas simile.** `atlas._line_hits` counts a simile only when some simile tag has confidence != low (same rule as `comparisons.collect`); `ATLAS_VERSION` 2 -> 3. Internal-rhyme and multi untouched. Tests: `test_atlas_simile_rate_counts_non_low_confidence_similes_only` (5-line corpus: `kao da`, line-initial `ko` not counted; also checks compare agrees), `test_a_version_2_atlas_cache_is_rebuilt`; mini-corpus count 9 -> 8 and version pin 2 -> 3 in the existing tests.

**L6 gazetteer noise.** `devices.is_noise_entry(entry)`: (1) < 3 letters total; (2) one token repeated AND (token <= 3 letters OR in ADLIB); (3) every token in ADLIB or <= 2 letters. Misleading "never match all three" comment rewritten (rules are alternatives). Corpus INTJ tags are no longer consulted, so the `forms` argument is gone (call site in `_prepared_gazetteer` updated). Tests (`test_devices.py`): `test_noise_entries_are_recognised_and_real_names_survive` (bora bora, pelle pelle, aisha, eazy, amore, chérie, okay survive), `test_repeated_token_is_noise_only_when_short_or_an_adlib`, `test_all_tokens_noise_rule_needs_every_token_adlib_or_two_letters_at_most`, the never-a-name-drop test, and `test_gazetteer_from_fixture_db` (new fixture entities Bora Bora, Pelle Pelle, Aisha, Eazy in `conftest.py`).

**L8 tests.** `test_cli_flow_used.py`: `_dir_state()` compares name -> (size, mtime_ns) before/after instead of names only. `test_star_fingerprint_compare_round_trip_through_the_atlas`: the vacuous `is not None` is now an assertion that the deviation phrases quote the stars' own raw means (computed independently from the stored feats) and end with `(n=3)`.

**L9 hint-vote.** `rules.RULE_IDS` (frozenset of the five ids); `hints.vote` accepts only well-formed ids of at most 64 chars that are in `RULE_IDS`, else `VoteError` (exit 1, nothing stored, known ids listed). `reset` stays format-only so stray old votes can be cleared. The old "saved anyway" Note is gone. Tests (`test_hints.py`): `test_unknown_overlong_and_malformed_rule_ids_exit_1_and_store_nothing` (replaces the old save-with-note test), `test_reset_still_accepts_any_well_formed_id_so_stray_votes_can_be_cleared`, `test_only_rules_that_exist_can_be_voted_on`, `test_rule_ids_are_every_rule_the_hints_can_emit` (RULE_IDS == RULE_* constants == SHORT_LABELS == ids a verse can emit).

**L10 compare + feats version.** `comparisons._comparison_word` drops tokens under 3 letters or with no nucleus (`MIN_WORD_LETTERS`, `phonetics.syllables`). New `cli.COMPARE_HINT` = `Hint: relax --artist or --theme, or try --lane all.` for the empty compare result (no `--mode`, no `--fresh`; rhyme/anchors/multi keep `HINT`). `fingerprint.FEATS_VERSION = 1`: `snapshot()` stamps `feats["feats_version"]`; `_row()` reads rows without it as 0 (no migration). Tests: `test_fragments_are_never_comparison_words`, `test_comparison_word_fragment_filter_units`, the compare empty-hint assertions in `test_compare_cli_theme_artist_max_and_errors`, `test_new_star_snapshots_carry_the_feats_version_and_old_rows_read_as_zero`.

## Live (real lyrics.db, data dir `%TEMP%\mairina_2r_8vx_xp9d`)

Verse stars 1, 5, 6 with the default lane (`lane=all`):

```
$ mt me --lane drill
Your fingerprint  lane=drill  n=3 starred line(s)  - low confidence (<10 stars)
feature        your mean   shrunk  lane mu   sigma
syllables           8.67    10.80    11.60    4.21
words               5.00     6.40     6.92    2.62
cons_density        0.86     1.11     1.21    0.52
end_tail            3.67     3.45     3.36    0.82
multi_len           3.33     3.28     3.26    3.80
allit               0.33     0.44     0.48    0.50

$ mt xray <verse> --lane drill
1 | syl 8 (10-15) | rhyme A | cons ▯▯▯ | ≈simile(ko) | vs★ fewer words than your ★ lines: 4 vs 5 (n=3)
2 | syl 7 (10-15) | rhyme - | cons ▯▯▯ | vs★ fewer words than your ★ lines: 4 vs 5 (n=3)
3 | syl 9 (10-15) | rhyme A | cons ▮▯▯ | vs★ shorter end-rhyme tail than your ★ lines: 3 vs 3.7 letters (n=3)
4 | ... | vs★ longer end-rhyme tail than your ★ lines: 4 vs 3.7 letters (n=3)
5 | ... | vs★ longer end-rhyme tail than your ★ lines: 4 vs 3.7 letters (n=3)
6 | ... | vs★ longer end-rhyme tail than your ★ lines: 4 vs 3.7 letters (n=3)
```

(Raw means: words 5.00, end_tail 3.67; the shrunk 6.40 / 3.45 are never quoted.) No syllables phrase fires on this verse; the unit-test form is `shorter than your ★ lines: 2 vs 8 syllables (n=3)`.

Errors, all exit 1, nothing stored (`mt stars` afterwards still lists exactly the 3 stars):
```
mt star <file with ...> 1  -> Error: Line 1 has no words ('...'): a star needs at least one word to measure.
mt star <file> 2 ('123')   -> exit 1;  mt star <file> 3 ('— —') -> exit 1
mt hint-vote bogus -       -> Error: Unknown hint rule 'bogus'. Known rules: abstract_stack, calque, cliche, dialect_mix, self_rhyme.
```
`hint-vote cliche +` then `reset` still work (1 up / 1 vote removed).

`mt compare --lane drill --max 10` (arm base, fresh 0.5): identical to wave 2F (no fragment was in the top 10):
```
  1. led 2.93 12x | 2. lud 2.89 11x | 3. san 2.49 7x | 4. para 2.27 6x | 5. mali 2.25 7x
  6. pravi 2.10 5x | 7. nož 2.06 5x | 8. bog 2.04 4x | 9. magija 2.02 7x | 10. vino 1.94 5x
```
Over the whole drill lane the filter removed 4 of 1108 words: `la` (3x), `bmw` (3x), `lo`, `ap`, `ye`, `uv`, `go`, `ng` (1x each); none under 3 letters or without a nucleus remain. Kept syllabic-r words: `krv`, `vrh`, `smrt`.

`mt atlas --lane drill --artist devito,jala` (rebuilt for v3):
```
scope                  lines  simile  anaph  allit  intern  code-sw   name  multi%   cons  med-syl
lane drill             39052     5.2   10.8   48.4    65.0      5.1   18.4    62.7   1.21       12
artist devito           5277     2.5   11.6   47.4    63.4      3.4   15.5    60.9   1.13       11
artist jala            10547     5.8    9.5   48.8    69.6      5.5   21.0    63.7   1.24       13
```
vs wave 2F: simile 5.7 -> 5.2 (devito 3.0 -> 2.5, jala 6.6 -> 5.8: the low-confidence `kao da` / line-initial `ko` lines are out); name 18.3 -> 18.4 (devito 16.2 -> 15.5, jala 20.6 -> 21.0: the narrower noise rules keep names like `bora bora` that were dropped). Everything else identical.

Empty compare: `mt compare --lane drill --artist nobody` -> `Hint: relax --artist or --theme, or try --lane all.`

## Invariants

- lyrics.db: before = after = **78,524,416 bytes, mtime_ns 1790810143258653900**; the whole `data\toolshop\lyrics\` listing (names, sizes, mtimes, incl. `-shm`/`-wal`) identical before/after, checked after the live runs and again after the final suite run.
- `MAirina_Tucc\data\` before = after (names, sizes, mtimes, SHA1): `.gitignore`, `index_3a770ed6.pkl`, `index_3a770ed6.pre-rebuild-20260930.pkl` (not touched), `targets_3a770ed6.pkl`. The full suite and the live runs leave it identical (live runs wrote only to the `%TEMP%` data dir).
- `git status --short -- MAirina_Tucc`: my changes are only the 7 source and 6 test files below; `D2_handoff.md`, `Q2_handoff.md` and `prompts\wave3_D3_api_v14.md` were already dirty from other sessions.

## Files changed

Source: `mairina\fingerprint.py`, `mairina\cli.py`, `mairina\atlas.py`, `mairina\comparisons.py`, `mairina\devices.py`, `mairina\hints.py`, `mairina\rules.py`.
Tests (+15): `tests\test_stars_fingerprint.py`, `tests\test_hints.py`, `tests\test_devices.py`, `tests\test_atlas_compare.py`, `tests\test_cli_flow_used.py`, `tests\conftest.py` (4 fixture entities).

## Deviations / judgement calls

1. **vs-star direction rule.** The spec says quote the raw mean and z-score on the shrunk one. Direction needs a choice: I say `shorter/longer` against the raw mean, and a deviation is only phrased when the raw and the shrunk mean agree on which side the line sits (`(x - mean) * z > 0`). A line between them, or equal to the raw mean, gets no sentence (it would read `longer ...: 9 vs 8` beside a below-prior z). Seen on the fixture: a 9-syllable line vs stars averaging 8 with shrunk 9.45.
2. **`8.0` formatting.** The spec's example reads `6 vs 8.0`; I kept the existing `_n()` formatting (`8`, `3.7`), which an existing test pins.
3. **`(n=..)` on the "close to" fallback** in xray is my addition for consistency (low-n disclosure on every vs-star cell).
4. **`is_noise_entry` lost its `forms` argument.** With the INTJ rule reduced to "every token is an ad-lib or <= 2 letters" the corpus UPOS is never needed; keeping the argument would have been dead.
5. **"No vowel" means no nucleus**: a syllabic `r` counts (`krv`, `smrt`, `vrh` stay). Side effect to be aware of: `bmw` (3x in the drill lane, a legitimate brand comparison) is dropped by the no-vowel rule, as the spec literally requires. Say so if you want an exception.
6. `hint-vote` still creates `mairina.db` before validating (as `star` does); a rejected vote stores no row.
7. **README is stale and was NOT touched** (hard rule: files only under `mairina\` and `tests\`). Needs: line 28 (a default-lane star now counts in every lane view), line 34 (vs-star examples now quote the raw mean and carry `(n=3)`; sign-agreement rule), line 47 (new noise rules, no INTJ rule), line 29 (hint-vote accepts only the five known ids), line 30 (simile rate excludes low-confidence similes), line 31 (compare drops fragments). Also stars saved before this wave have no `feats_version`.
