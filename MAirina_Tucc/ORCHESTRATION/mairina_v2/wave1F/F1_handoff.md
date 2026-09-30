# Wave 1F handoff — adversarial-review fixes in the craft engine

Date: 2026-09-30. Review fixed: `D:\Projects\.workspace_archive\reviews\2026-09-30_mairina_v2_w1.md`.
Prior handoff: `ORCHESTRATION\mairina_v2\wave1\D1_handoff.md`.
Scope: only `MAirina_Tucc\`. No commits (orchestrator commits after verifying).

**pytest: `144 passed, 2 skipped, 1 warning in 45.94s`** (the 2 skips are `test_live_smoke` —
the corpus is mid-rebuild; they auto-skip via `check_annotated` until annotation lands).

Command run (cwd `D:\Projects\Music-AI-Toolshop`):
`D:\Projects\Music-AI-Toolshop\.venv\Scripts\python.exe -X utf8 -m pytest D:\Projects\Music-AI-Toolshop\MAirina_Tucc\tests -q -p no:cacheprovider`

## Per finding

### H1 — rhyme letters from tail keys (devices.py `_rhyme_letters`, ~line 326)
Line letters no longer come from `toolshop.find_rhymes`. Each line's last token
maps to `keys.tail_key(w, 2)` / `tail_key(w, 1)` (nucleus + coda, onset excluded):
two lines share a letter when tail2 matches, or tail1 matches with len >= 2 —
which is exactly how monosyllabic `znaš` (tail `aš`) joins `imaš`/`snimaš`.
Union-find groups pairs transitively; singletons stay `-`.
Proven by `test_multisyllabic_rhyme_and_rhyme_letters` and `test_the_task_verse`
(both assert `[A, None, A, B, B, B]`) and the live xray run below.

### H2 — name_drop (devices.py `load_gazetteer` ~63, `_split_gazetteer` ~100, `_name_drops` ~238)
Multi-word entities are stored and matched **as phrases** (`_add` no longer
splits into tokens; `test_gazetteer_from_fixture_db` asserts `acme corp`/`tabak
mala` present and `acme`/`mala` absent). Single-token entries are dropped at
match time when the index says `freq >= NAME_MIN_FREQ (20)` and majority
UPOS != PROPN — `mala`, `niko`, `glava` suppressed; `melisa` (PROPN) and `gucci`
(unknown) still tag. Test: `test_name_drop_filters_common_words_and_keeps_phrases`.

### H3 — lexicons live in `MAirina_Tucc\lexicons\` (rules.py `LEX_DIR`, ~21; devices.py `_english_tokens` ~51)
Moved out of the gitignored `data\`. `git check-ignore -v MAirina_Tucc/lexicons/cliches.txt`
prints nothing (exit 1). A missing file disables only its own rule and prints one
`Note:` line to stderr (`_missing`, `_text_list`, `_concrete`, `_dialect`,
`_english_tokens`). Tests: `test_missing_lexicon_files_disable_only_their_rules`,
`test_missing_single_lexicon_disables_only_its_rule`. `PROVENANCE.md` documents
the move and the wave-1F content edits; README updated.

### M1 — tests never write real `data\` (cli.py `_cmd_anchors` ~106, `_cmd_xray` ~198-199)
`targets.target` / `targets.cons_thresholds` now take `cache_dir=data_dir`
everywhere; the fixture `data_dir` is a tmp dir. Regression:
`test_tests_never_write_the_real_data_dir` snapshots `DATA_DIR` before/after
xray+rhyme+anchors+flow. Stray `data\targets_a17f8d26.pkl` deleted; no
`mairina.db` exists under `MAirina_Tucc\data\`.

### M2 — simile `ko` disambiguation (devices.py `_similes`/`_ko_is_who`, ~172-210)
The who-check applies at **any** position: aux/verb next token (fixture VERB via
index UPOS), clitic-skip lookahead (`ko me zove`), line-final `?`. Curly `’`
(U+2019) is normalised, so `k’o`/`ka’o` match. `kao da` / `kao što` keep the tag
at `low` confidence. Tests: `test_ko_who_check_at_any_position`
(`pitaj ko je gazda`, `ne znam ko me zove` -> no simile; `hladna ko led`,
`k’o mafija` -> simile).

### M3 — anaphora (devices.py `analyze_verse` ~401, `ANAPHORA_STOP` ~34)
The span is the **shared opening text** (surface casing kept via `token_spans`);
it must contain >= 1 non-stopword. Stoplist = clitics + ja/ti/on/ona/ono/mi/vi/
oni/one/ne/sve/to/taj/ta/ovo/i/a/ali/pa/kad/jer/da. `Da se vratim / Da se
sakrijem` -> none; `Laku noć …` -> span `Laku noć`.
Test: `test_anaphora_shared_opening_needs_a_content_word`.

### M4 — alliteration excludes clitics + `ne` (devices.py `_alliteration` ~136)
`sala šalju` still fires (weak, same class); `u Panameri da se snimaš` no longer
flags `se+snimaš` (`se` filtered, `s` occurs once). Test:
`test_the_task_verse` asserts no alliteration on line 6.

### M5 — rank tiers (rank.py `TIER` ~31, `rank()` ~115, `explain` ~142)
Sort key is `(TIER[kind], -score, candidate)` — perfect-3 > perfect-2 >
perfect-1 > assonance > consonance; shaping terms (gap/dom-class/freq/fresh)
only reorder inside a tier, so assonance can never outrank perfect-1.
Over-target lines add a `over target` note to each candidate's why
(`rank()` ~120). `--target` without `--line` exits 1 with a clear message
(cli.py ~116). Tests: `test_match_tier_beats_shaping_terms`,
`test_rhyme_target_needs_line`, `test_rhyme_over_target_note`.

### M6 — self_rhyme + code_switch (rules.py `_self_rhyme` ~118; lexicons\english_tokens.txt)
Self-rhyme fires on identical end word, a shared stem >= 4 letters, or a shared
lemma when both words are >= 5 chars — `znaš`/`znam` (stem 3) and `lava`/`laka`
(stem 2) no longer fire; `padalima`/`padama` still does.
Test: `test_self_rhyme_needs_a_real_shared_stem`.
`english_tokens.txt` dropped the Serbian homographs do/no/so/as (to/me/i/a/on/
pa/sam were already absent or removed): `Ide do kuće, no ti si tu` -> no
code_switch, `money`/`cash` still fire. Test: `test_code_switch_and_name_drop`.

### L — low-severity batch
- **multisyllabic tag** = longest shared vowel-skeleton suffix, grouped by
  union-find (`_multi_suffixes` ~349): verse lines 5/6 report `iaeia`.
- **internal rhymes non-overlapping** (`_maximal_internal_rhymes` ~213): only
  the longest skeleton class is kept, and overlapping occurrences are dropped —
  `u panameri da se snimas` (self-overlapping `aeia`) -> none; `mira pita` -> `ia`.
  Test: `test_internal_rhyme_keeps_only_maximal_non_overlapping_echoes`.
- **consonance density** excludes clitics from numerator AND denominator
  (`consonance_density` ~110); the gauge is driven by per-lane corpus quantiles
  `targets.cons_thresholds` (cli.py ~199, ~218) with `GAUGE_STEPS` as offline
  fallback — no saturation.
- **digraph exceptions**: `keys.NO_DIGRAPH_WORDS` = {nadživeti, nadživiš,
  podžupan, injekcija, konjunkcija}; `units()`/`_units()` keep d+ž / n+j as two
  letters there (keys.py ~21, ~40; phonetics.py ~49). `nadživeti` = 4 nuclei,
  `injekcija` = 4. Tests: `test_digraph_exceptions_split_prefix_boundaries`,
  `test_prefix_boundary_digraphs_stay_two_letters`.
- **targets min-n**: `MIN_N = 30`; a lane x section cell below it falls back to
  the lane pooled range and is marked `approx` (Target.approx, `fmt_range`
  prints `~`, e.g. `10–10~`). Tests: `test_small_n_falls_back_to_lane_range_marked_approx`.
- **dialect pairs**: `dialect_pairs.csv` 95 -> 48 rows (47 dropped: identical
  values + ambiguous `med,mijed`); `_dialect` also skips identical pairs at
  load. Tests: `test_lexicons_loaded`, `test_dialect_mix_is_verse_level`
  (`med`/`mijed` cannot fake a mix).

### CORPUS — corpus scope (corpus.py `CORPORA` ~23, `_corpus_sql` ~37)
`CORPORA = ("genius-pro",)` is applied to every songs/lines/tokens/entities
read: index `_build` (~158), `artist_tokens` (~147), gazetteer entities +
artist names (devices.py ~85-93), targets `_query` (~56), `flow.lane_median`
(~28). Fixture song 5 (gutenberg_pd, pop cohort, syl 3) proves it: no forms, no
bigrams, no gazetteer entry, no target/median leak.
Tests: `test_only_genius_pro_corpus_is_indexed`, `test_corpus_scope_excludes_english_lines`,
gazetteer asserts in `test_gazetteer_from_fixture_db`; `flow` pop median stays 7.

### GUARD — empty-index guard (corpus.py `check_annotated` ~42)
Before building the index or the targets blob, coverage = allowed-corpus lines
with >=1 token / non-empty allowed-corpus lines must reach `MIN_TOKEN_COVERAGE
= 0.9`; otherwise `CorpusNotAnnotated` (a `DbUnavailable` subclass) is raised —
never builds or caches a partial index, and a failed rebuild never overwrites a
good cache. `mt xray` re-raises it instead of degrading (cli.py ~202) -> exit 2.
Message (live, verified): `Error: lyrics.db has no CLASSLA tokens for genius-pro - run: toolshop lyrics annotate --resume`
Tests: `test_unannotated_corpus_raises_and_keeps_good_cache`,
`test_rebuild_never_overwrites_a_good_cache`, `test_xray_fails_cleanly_on_unannotated_db`,
`test_unannotated_db_raises_instead_of_caching` (targets).

### WRITER — concurrent writer (corpus.py `build_guarded` ~62)
`load_index` and `targets._blob` both build inside `build_guarded`: refuses when
`lyrics.db-wal`/`-journal` exists; stats mtime+size before and after the build;
on change it discards the result, retries once, then raises `DbUnavailable`.
Observed live today: `Note: lyrics.db is being written (lyrics.db-wal present)
- retry when the writer finishes` while D0 was rebuilding.
Tests: `test_build_guarded_refuses_wal_and_retries_on_change`,
`test_load_index_retries_when_db_changes_mid_build`.

### IDs — no persistent song/line ids
Index cache and targets blob key on db path + `mtime_ns` + `size`; the stored
payload contains forms/artists/bigrams/sections only — no `songs`/`line_id`
values are persisted (`_build` keeps `s.id` only to count `n_songs`).
`mairina.db` (votes.py schema) stores only candidates/list-local ids.
So the genius-pro id renumbering (1426+) is safe — first run after the rebuild
re-keys on the new file signature anyway. `CACHE_VERSION` bumped 3 -> 4,
`BLOB_VERSION` = 2. Test: `test_cache_is_keyed_on_mtime_and_size` +
`test_current_cache_version_stores_bigrams` (`"songs" not in blob["forms"]["lava"]`).

## Live verification (real `D:\Projects\Music-AI-Toolshop\data\toolshop\lyrics\lyrics.db`)

lyrics.db is being rebuilt by D0 — `lyrics.db-wal` present, `tokens` empty for
genius-pro. Two observations, both correct:

1. Writer guard fired first (xray degraded, still advisory, exit 0):

```
Note: lyrics.db is being written (lyrics.db-wal present) - retry when the writer finishes — running without lane targets and gazetteer.
X-ray 6 lines  lane=drill section=strofa (advisory only — you write)
1 | syl 8 | rhyme A | cons ▮▮▯ | ≈simile(ko)
2 | syl 7 | rhyme - | cons ▮▮▯
3 | syl 9 | rhyme A | cons ▮▮▮
4 | syl 10 | rhyme B | cons ▮▮▮ | allit ✓ | ≈internal_rhyme(ea)
5 | syl 9 | rhyme B | cons ▮▮▯ | allit ✓ | ≈internal_rhyme(ia) | ≈multisyllabic_rhyme(iaeia)
6 | syl 9 | rhyme B | cons ▮▮▮ | ≈multisyllabic_rhyme(iaeia)
```

Gate results, all confirmed on the real verse file (`%TEMP%\verse.txt`):
letters `A,-,A,B,B,B` ✓; simile `ko` on line 1 ✓; no `name_drop` (mala, niko,
panameri all clean) ✓; line 6 has no `allit` (se+snimaš suppressed) ✓;
multisyllabic `iaeia` on lines 5/6 ✓.

2. `check_annotated` on the real db right now raises exactly:

```
CorpusNotAnnotated: lyrics.db has no CLASSLA tokens for genius-pro - run: toolshop lyrics annotate --resume
```

(through `mt xray` this exits 2 — proven by `test_xray_fails_cleanly_on_unannotated_db`.)

## Invariants

- `data\` listing before tests: `index_3a770ed6.pkl`,
  `index_3a770ed6.pre-rebuild-20260930.pkl`, `targets_3a770ed6.pkl`
  (after deleting the stray `targets_a17f8d26.pkl`).
  After the full test run + live runs: identical, no `mairina.db`.
- lyrics.db before: `mtime_ns 1790799478373048900, size 67166208`.
  After: `mtime_ns 1790799478373048900, size 67166208` — MAirina never wrote it
  (the `-wal` file belongs to D0's concurrent writer, not to us).
- `git -C D:\Projects\Music-AI-Toolshop check-ignore -v MAirina_Tucc/lexicons/cliches.txt`
  -> no output (exit 1): lexicons are tracked.
- `git status --short -- MAirina_Tucc` (only this task's paths; orchestrator commits):

```
 M MAirina_Tucc/README.md
 M MAirina_Tucc/mairina/__init__.py
 M MAirina_Tucc/mairina/cli.py
 M MAirina_Tucc/mairina/corpus.py
 M MAirina_Tucc/mairina/flow.py
 M MAirina_Tucc/mairina/keys.py
 M MAirina_Tucc/mairina/rank.py
 M MAirina_Tucc/mairina/used.py
 M MAirina_Tucc/tests/conftest.py
 M MAirina_Tucc/tests/test_cli_flow_used.py
 M MAirina_Tucc/tests/test_keys_corpus.py
 M MAirina_Tucc/tests/test_live_smoke.py
 M MAirina_Tucc/tests/test_rank_anchors_multis.py
?? MAirina_Tucc/lexicons/
?? MAirina_Tucc/mairina/devices.py
?? MAirina_Tucc/mairina/phonetics.py
?? MAirina_Tucc/mairina/rules.py
?? MAirina_Tucc/mairina/targets.py
?? MAirina_Tucc/tests/test_devices.py
?? MAirina_Tucc/tests/test_phonetics.py
?? MAirina_Tucc/tests/test_rules.py
?? MAirina_Tucc/tests/test_targets.py
?? MAirina_Tucc/tests/test_xray.py
```

## Deviations / not done

- **Post-annotation live checks pending**: `mt xray` with targets+gazetteer and
  `mt rhyme imaš --lane drill` (expect `snimaš` top-10) can only run once D0
  finishes annotating and the `-wal` file clears. Both are covered by live smoke
  tests that auto-skip until then (`test_live_rhyme_imas_has_snimas_in_top_10`),
  and the rhyme ordering is proven on the fixture corpus. The fixture verse
  already verifies the same letters/tags the live run shows.
- `xray` on an actively-written db degrades with a `being written` Note (exit 0)
  rather than the CorpusNotAnnotated error — the wal check intentionally wins
  over the coverage check; when the writer finishes without annotation,
  CorpusNotAnnotated fires (exit 2) as specced.
- `No lazy-rhyme / suffix-rhyme rule` retained per product constraints.
