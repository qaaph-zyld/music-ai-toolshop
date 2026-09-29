# MAirina Tucc v1

Anchor sets and a rhyme finder that learns your taste. **The tool finds, it never writes**: you write every line.

Spec: `docs/superpowers/specs/2026-09-29-mairina-anchors-design.md`.

## Run

```powershell
& "D:\Projects\Music-AI-Toolshop\MAirina_Tucc\mt.ps1" <command> [options]
```

`mt.ps1` uses the toolshop venv (`.venv\Scripts\python.exe`) and sets `PYTHONPATH` to `MAirina_Tucc`. Nothing is installed and the CLI never prompts.

## Commands

| Command | What it does |
|---|---|
| `anchors --scheme AABB --lines 4 --lane drill [--mode rhyme\|assonance\|consonance] [--seed panamera] [--fresh 0.5] [--artist devito] [--rng-seed N]` | One end-word per line, grouped by rhyme scheme. You write each line to land on its anchor. Without `--rng-seed`, every run differs. `--seed` fixes group A's rhyme class (the seed word itself is not offered). If `--lines` differs from the scheme length, the scheme cycles with new letters. |
| `rhyme <word> [--lane] [--fresh] [--artist] [--max 20]` | Numbered, ranked rhyme list. Each item shows a score breakdown (match kind and length, log frequency, fresh penalty, vote and used boosts). |
| `multi "<ending phrase>" [--lane] [--max 20]` | 1-3-word combinations from the corpus vocabulary whose vowel skeleton ends with the phrase's (`da me imaš` -> `aeia`). Glue words (`da se me te je u na sa mi ti ne`) only in non-final slots and at most one per combination; the final word is a content word, never a proper noun or artist name. Every adjacent word pair must be an attested corpus bigram (the two words stood directly next to each other in one line, after token hygiene), so fewer than `--max` results is normal and there is no fallback. At most 2 results share a final word and 3 share a first word. Words only, never corpus lines. |
| `vote 3+ 5- 7+` | Thumbs up/down on items of the **last list shown**. Re-voting an item replaces the earlier vote. |
| `used <lyrics.txt> [--days 14]` | Scans a text file you wrote and logs which recently shown suggestions ended up in it. The strongest signal. |
| `flow <lyrics.txt> [--lane]` | Syllables per line against your own median and the lane median. `[Section]` headers and blank lines are skipped. |
| `stats [--ab]` | Up-rate, used rate, counts by kind. `--ab` compares the two ranking arms (needs 100 votes). |

Shared options: `--lane drill|pop|all` (default `all`, which includes the 93 songs with no cohort); `--artist a,b` (hard filter on `songs.target_artist`, intersected with `--lane`: words are counted only in that artist's songs of that lane); `--fresh 0.0-1.0` (default 0.5; higher penalises overused rhyme classes).

Exit codes: `0` ok (also for an empty result, which prints a reason and a hint), `1` bad vote input or missing text file, `2` `lyrics.db` missing or unreadable (the message names the expected path).

## Where the data comes from

- `data\toolshop\lyrics\lyrics.db` (1,425 Genius songs), opened only as `file:...?mode=ro&immutable=1`. It is never written.
- Token hygiene: `source_script='latin'` only; POS `PUNCT`, `X`, `SYM`, `NUM` dropped; keys lowercased; majority lemma and POS per form.
- The word index (including the word-pair set, never lines) is cached in `MAirina_Tucc\data\index_*.pkl` and rebuilt when `lyrics.db`'s modified time changes (first run takes several seconds).
- Votes, shown lists and "used" hits live in `MAirina_Tucc\data\mairina.db` (created on first use). Both files are git-ignored.
- `line_rhymes` and `rhyme_pairs` are deliberately not used (sparse, mostly chorus repeats).
- Reused code: `toolshop.syllables.count_line` and `toolshop.rhyme_miner.vowel_skeleton`. Known limitation: toolshop's `[a-zA-Z]` regex splits words at diacritics, which leaves vowels correct.

## Ranking A/B

Artist-name tokens (from `songs.primary_artist` / `target_artist`) are kept out of anchors, rhymes and multis, and anchors never pair a word with its own prefixed/suffixed extension (`nekad`/`ponekad`). Anchors are common Serbian words only: frequency of at least 5, no proper nouns, no forms with q/w/x/y or a doubled vowel (`taboo`, `woo`). `rhyme` and `multi` keep the wider vocabulary.

Every list is assigned 50/50 to arm `learned` (vote and used boosts applied) or `base` (same score without them). The arm is drawn from its own RNG, so `--rng-seed` never pins it, and is stored with each shown item. After 100 votes, `stats --ab` compares the up-rate per arm.

## The week-1 test

Terminal only. `mt stats` tracks it; you decide keep or kill.

| Assumption | Pass condition |
|---|---|
| Writing toward anchors helps | 2+ verses written from anchor sets and you say "keep" |
| Corpus words sound like today | Of the first 50 votes cast, 40%+ are up |
| Phrase multis are usable | Of the first 20 `multi` lists, 10+ get an up-vote or a "used" hit |
| The ranking learns | After 100+ votes, arm `learned` has a higher up-rate than `base` |

## Tests

```powershell
& "D:\Projects\Music-AI-Toolshop\.venv\Scripts\python.exe" -m pytest "D:\Projects\Music-AI-Toolshop\MAirina_Tucc\tests" -q
```

Unit tests run on a tiny hand-written fixture corpus. The live smoke test is skipped when `lyrics.db` is missing.
