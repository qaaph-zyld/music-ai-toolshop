# Wave 2 Handoff (D2) - stars/fingerprint, hint votes, device atlas, comparison finder

**Status: DONE.** Plan `plan-3507f72203af8a6c.md` implemented; suite green; live runs verified; lyrics.db and `data\` verified unchanged. No git add/commit/checkout/stash/reset was run (the orchestrator commits).

## Files (line counts)

New in `mairina\`: `fingerprint.py` 285, `hints.py` 71, `atlas.py` 242, `comparisons.py` 117.
New tests: `tests\test_stars_fingerprint.py` 340 (20 tests), `tests\test_hints.py` 142 (10), `tests\test_atlas_compare.py` 372 (18).
Modified (diff vs b1c066b): `mairina\cli.py` +192/-8, `mairina\devices.py` +119/-38, `tests\test_cli_flow_used.py` +14 (data-dir guard extended to every new command), `README.md` +12/-4 (7 new command rows, `xray` vs-star note, craft-engine paragraph, data-files line).

## pytest

`"D:\Projects\Music-AI-Toolshop\.venv\Scripts\python.exe" -X utf8 -m pytest "D:\Projects\Music-AI-Toolshop\MAirina_Tucc\tests" -q -p no:cacheprovider`

```
195 passed, 1 warning in 107.00s (0:01:46)
```

0 skipped (147 baseline + 48 new; the 2 live smoke tests ran against the real lyrics.db). The single warning is the pre-existing `requests`/urllib3 version warning.

## New tables in `data\mairina.db` (CREATE TABLE IF NOT EXISTS; `votes.SCHEMA` untouched, v1 tables never altered - a test compares their `sqlite_master` SQL)

```sql
CREATE TABLE IF NOT EXISTS stars(
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, file TEXT, line_no INTEGER NOT NULL,
  text TEXT NOT NULL, lane TEXT NOT NULL, tags_json TEXT NOT NULL, feats_json TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_stars_lane ON stars(lane);
CREATE TABLE IF NOT EXISTS hint_votes(
  rule_id TEXT NOT NULL, vote INTEGER NOT NULL, ts TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_hint_votes_rule ON hint_votes(rule_id);
```

`feats_json` = `{syllables, words, cons_density, end_tail, multi_len, allit, kinds[]}`. `end_tail` = `len(tail_key(last content word, 2))`; `multi_len` = longest `multisyllabic_rhyme` span on that line (0 if none). `line_no` = the `mt xray` row number (blank lines and `[headers]` skipped; documented in `--help` and README).

Atlas cache `data\atlas_<tag>.pkl`: `{v:1, mtime_ns, size, lanes:{drill|pop|all: {n_lines, counts{simile,anaphora,allit,internal,code_switch,name_drop,multi}, cons_mean, median_syl, numeric{feature:{mean,std,n}}}}, artists:{slug: same}}` - numbers only (artists with < 30 lines dropped).

## Live results (real lyrics.db, via `mt.ps1`)

`atlas --lane drill` (first run builds the cache: 22.5 s, stderr Note; cached afterwards):

```
Device atlas  corpus=genius-pro  rates per 100 lines (stats only - no lyrics shown)
scope                  lines  simile  anaph  allit  intern  code-sw   name  multi%   cons  med-syl
lane drill             39052     5.7   10.8   80.9    65.0      4.6   20.0    62.7   1.21       12
Artists with a row: ana-nikolic, breskvica, buba, coby, corona, devito, henny, indodjija, jala, jala-buba, jala-buba-coby, maya-berovic, nikolija, rasta, relja, senidah, tng, voyage  (use --artist)
```

Also: `lane pop 21076 lines | 3.7 | 10.7 | 73.6 | 58.9 | 2.5 | 9.3 | 56.4 | 1.12 | 10`; `--artist 'devito,jala,nobody'` gave rows devito (5277 lines, simile 3.0, cons 1.13, med 11), jala (10547, 6.6, 1.24, 13) and "artist nobody: no atlas row (unknown slug or under 30 lines)". I scanned the pickle: every leaf is None/int/float; 0 of 5000 sampled corpus lines occur in `repr(blob)`.

`compare --lane drill --max 10` (arm learned, fresh 0.5, list #1; 4.8 s):

```
  1. led                2.93   12x  simile-use +2.56 | freq(66) +0.84 | fresh -0.47
  2. lud                2.89   11x  simile-use +2.48 | freq(97) +0.92 | fresh -0.52
  3. san                2.49    7x  simile-use +2.08 | freq(102) +0.93 | fresh -0.52
  4. nijedna            2.30    6x  simile-use +1.95 | freq(62) +0.83 | fresh -0.47
  5. sve                2.29    4x  simile-use +1.61 | freq(2320) +1.55 | fresh -0.87
  6. para               2.27    6x  simile-use +1.95 | freq(148) +1.00 | fresh -0.67
  7. mali               2.25    7x  simile-use +2.08 | freq(121) +0.96 | fresh -0.79
  8. pravi              2.10    5x  simile-use +1.79 | freq(173) +1.03 | fresh -0.73
  9. nož                2.06    5x  simile-use +1.79 | freq(21) +0.62 | fresh -0.35
 10. bog                2.04    4x  simile-use +1.61 | freq(132) +0.98 | fresh -0.55
```

Verse in `%TEMP%\mairina_verse.txt` (outside the repo). Plain `xray --lane drill` (no stars): `A/-/A/B/B/B`, simile(ko) on line 1. Then `star 1 --tag metaphor --lane drill`, `star 5 --tag punchline --lane drill`, `star 6 --tag punchline --lane drill`:

```
★ #1 line 1 "Usne crvene ko lava –" [metaphor] lane=drill
★ #2 line 5 "Mala, mogla si da me imaš," [punchline] lane=drill
★ #3 line 6 "u Panameri da se snimaš" [punchline] lane=drill
```

`me --lane drill`:

```
Your fingerprint  lane=drill  n=3 starred line(s)  - low confidence (<10 stars)
feature        your mean   shrunk  lane mu   sigma
syllables           8.67    10.80    11.60    4.21
words               5.00     6.40     6.92    2.62
cons_density        0.86     1.11     1.21    0.52
end_tail            3.67     3.45     3.36    0.82
multi_len           3.33     3.28     3.26    3.80
allit               0.33     0.68     0.81    0.39
tags:    punchline 67%, metaphor 33%
devices: consonance 100%, multisyllabic_rhyme 67%, alliteration 33%, internal_rhyme 33%, simile 33%
```

Shrinkage check: syllables `(3*8.67 + 8*11.60)/11 = 10.80`.

`xray <verse> --lane drill` with the 3 stars:

```
1 | syl 8 (10–15) | rhyme A | cons ▯▯▯ | ≈simile(ko) | vs★ fewer words than your ★ lines: 4 vs 6.4
2 | syl 7 (10–15) | rhyme - | cons ▯▯▯ | vs★ fewer words than your ★ lines: 4 vs 6.4
3 | syl 9 (10–15) | rhyme A | cons ▮▯▯ | vs★ shorter end-rhyme tail than your ★ lines: 3 vs 3.4 letters
4 | syl 10 (10–15) | rhyme B | cons ▮▮▯ | allit ✓ | ≈internal_rhyme(ea) | vs★ longer end-rhyme tail than your ★ lines: 4 vs 3.4 letters
5 | syl 9 (10–15) | rhyme B | cons ▯▯▯ | allit ✓ | ≈internal_rhyme(ia) | ≈multisyllabic_rhyme(iaeia) | vs★ longer end-rhyme tail than your ★ lines: 4 vs 3.4 letters
6 | syl 9 (10–15) | rhyme B | cons ▮▯▯ | ≈multisyllabic_rhyme(iaeia) | vs★ longer end-rhyme tail than your ★ lines: 4 vs 3.4 letters
```

Then `unstar 1`, `unstar 2`, `unstar 3` ("Removed"), `stars` -> "No stars yet", `data\mairina.db` and `data\atlas_3a770ed6.pkl` deleted.

## Invariants

- **lyrics.db** (`data\toolshop\lyrics\lyrics.db`): before = after = **78,524,416 bytes, mtime ticks 639264069432586539 (2026-10-01 01:15:43 local)**; `-shm` 32,768 B and `-wal` 0 B also unchanged (whole directory listing identical). Opened only through `corpus.open_ro` / `build_guarded` (immutable read-only URI). Tests add: db mtime+size+sibling listing unchanged after atlas/compare, and writer guard (`-journal`, non-empty `-wal`) respected by both.
- **`MAirina_Tucc\data\`** before and after (names, sizes, mtimes AND SHA1 identical): `.gitignore`, `index_3a770ed6.pkl`, `index_3a770ed6.pre-rebuild-20260930.pkl` (untouched), `targets_3a770ed6.pkl`. The full suite leaves it identical too (checked after each run).
- `git -C D:\Projects\Music-AI-Toolshop status --short -- MAirina_Tucc`: only the paths listed above, plus the orchestrator's `waves.json` and wave-2 prompt file.

## Deviations from the plan

1. **`devices.py` is touched more than "extract `simile_positions`"** (all behavior-identical, 23 xray/devices tests unchanged and green): `simile_scan` (tokens + positions), `simile_positions` (the 3-tuple API), `simile_confidence`, `_similes` as a thin wrapper. Line-initial `ko` is now `marker_tok_idx == 0` instead of a character-offset test, and the text is NFC-normalised before the regex so offsets agree with `token_spans`. Also extracted `anaphora_runs` (atlas and `analyze_verse` share the exact rule) and shared feature helpers `NUMERIC_FEATURES`, `has_alliteration`, `end_tail_len`, `line_features` (fingerprint and atlas measure identically).
2. **Performance fix needed for the atlas:** `_name_drops` re-split and re-filtered the whole gazetteer on every line (profiled: 89% of `analyze_line` time; est. 185 s for the corpus). Now memoised per (gazetteer, index) with phrases indexed by first token: 22 s total. Phrase hits come out in sorted order (was set order).
3. **Starring the same file+text+lane again updates the star** (tags merge, printed `(updated)`) instead of adding a duplicate, so a repeated `mt star` cannot inflate n.
4. **Atlas skips lines containing Cyrillic and lines with no tokens** (phonetics is Latin-only): 39,052 of 39,621 `drill_trap` lines counted. It does not go through `_setup`, so `mt atlas` never creates `mairina.db`; `_setup` is used by `compare` only. Artist blobs also carry `numeric`.
5. **`compare` details:** identical lines within one song (refrains) count once; low-confidence markers (`kao da/što`, line-initial `ko`) are skipped; the `--theme` word itself is never returned; `--theme` must be one word (else exit 1).
6. **`xray` vs-star column:** top-1 deviation with `allit` excluded (the row already shows `allit ✓`, and with the corpus base rate it made every row say the same thing); `compare()` itself still ranks all five features and only reports |z| >= 0.5; a line within 0.5 sigma everywhere prints `vs★ close to your ★ lines`. The alliteration phrase quotes the shrunk rate, like the others. Numbers in phrases keep one decimal when not integer (`4 vs 6.4`). The xray header gains `muted hints: ...` when any rule is muted.
7. `hint-vote` accepts any well-formed id; an id not in `rules.SHORT_LABELS` is saved with a stderr Note (typo guard) rather than rejected. `fingerprint.fingerprint` takes an extra `rows=` argument (the CLI passes the rows it already fetched).
8. Read-only commands (`xray`, `stars`, `me`) open `mairina.db` only if it exists (read-only URI); `star`/`hint-vote`/`stats`/list commands create it.

## Observations the orchestrator should know (not changed, outside this wave's scope)

- **`allit` is a near-constant feature:** 80.9% of drill lines carry an alliteration tag (weak same-class matches included). In a 12k-line sample, 5829 tags were `high` (same phoneme) and 3692 `low` (same class), i.e. about 49% strong-only. Consider counting strong-only in the atlas/fingerprint (one-line change in `devices.has_alliteration` plus `line_features`); I kept the xray's definition so `allit ✓`, stars and atlas agree.
- **`name_drop` rate (20.0/100 lines) is inflated by gazetteer NER noise:** top spans in a drill sample were `yeah yeah`, `kol ko`, `a a`, `a a a`, `tri`, `bog`, `bože`, `bu bu bu`, `de vi to`. A `load_gazetteer` hygiene pass (drop all-clitic, repeated or single-letter-token phrases) would fix it.
- Internal-rhyme (65.0) and multisyllabic share (62.7%) are also high base rates; the atlas just reports what the wave-1 rules tag.
- `compare` top words include pronoun-like ADJ (`sve`, `nijedna`, `mali`) because the spec takes NOUN/ADJ/PROPN by index UPOS; no stoplist added.
- Atlas anaphora counts consecutive identical refrain lines (they share an opening), same as `analyze_verse`.
- PowerShell splits an unquoted `--artist a,b` into two arguments: quote it (`--artist 'a,b'`).
- The first `me`/`xray` with >= 3 stars on a lyrics.db with no atlas cache builds it (about 22 s, stderr Note); run `mt atlas` once to warm it.

## Not done

- No commit (per wave constraints); tree stays dirty-but-declared. `toolshop closeout` not run.
- Wave 3 (API) / wave 4 (UI) not started. No metaphor/wordplay/double-meaning auto-detection (tags are user-only); no stress prediction.

---

## Closeout addendum (Claude orchestrator, 2026-10-01): supersedes "No commit" above

- **Committed:** `b33f0fd` ("feat(mairina): v2 wave 2 - stars/fingerprint, hint votes, atlas, compare"). Not pushed.
- **Re-verified by the orchestrator:** 195 passed at the commit; `lyrics.db` modified time and size unchanged; `MAirina_Tucc\data\` unchanged.
- **Adversarial review:** `.workspace_archive/reviews/2026-10-01_mairina_v2_w2_w2f.md`, approved-with-fixes, 0 blockers, 0 high.
- **Correction:** the `devices.py` simile refactor was "behavior-identical" on all but 1 of 8,320 real simile-candidate lines. A line starting with a quote (`'Ko vas jebe…`) moved from medium to low confidence.
- The medium findings are fixed in wave 2R: the vs★ wording, token-less stars, lane-`all` stars, and simile counting.
