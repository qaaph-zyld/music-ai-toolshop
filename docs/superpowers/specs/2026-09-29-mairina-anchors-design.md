# MAirina Tucc v1: anchor sets and a rhyme finder that learns

**Date:** 2026-09-29 · **Status:** design approved by the user; spec awaiting review
**Home:** `MAirina_Tucc/mairina/` (a Python package inside Music-AI-Toolshop, run with `Music-AI-Toolshop\.venv`)
**Origin:** a `/brainstorming` + `/idea-refine` session. The approved plan is mirrored in `D:\Projects\.workspace_archive\plans\mairina-anchors-v1-9b41e2.md`.

---

## 1. Problem statement

**How might we** give the songwriter a skeleton of words that belong together, and a side panel that learns their taste, so every line they write lands on something that sounds like the Balkan scene today?

**Why now:** in lyrics_popper, the user's native ear rejected every line the AI wrote, including 9 attempts at one refren line. The user's rule for this tool: **the AI finds; it never writes.** The user writes every line.

## 2. Users and success

- **User:** one Serbian/Balkan producer-songwriter (drill/trap and pop-folk/club), writing in Latin script with diacritics.
- **Success in week 1** (terminal only). `mt stats` tracks it, and the user decides keep or kill:

| Assumption | Pass condition |
|---|---|
| Writing toward anchor words helps rather than boxing the writer in | 2 or more verses written from anchor sets; the user says "keep" |
| Corpus words sound like today | Of the first 50 **votes cast**, 40% or more are 👍 (👍 rate = up ÷ (up + down), counted per vote) |
| Phrase multis are usable, not word salad | Of the first 20 `mt multi` lists, 10 or more get at least one 👍 or a "used" hit |
| The ranking learns from votes | After 100 or more votes, lists served in arm `learned` have a higher 👍 rate than lists in arm `base` (see §5 `votes.py`) |

## 3. What it does (user-facing)

| Command | Purpose |
|---|---|
| `mt anchors --scheme AABB --lines 4 --lane drill [--mode rhyme\|assonance\|consonance] [--seed panamera] [--fresh 0.0–1.0] [--artist devito] [--rng-seed N]` | One end-word per line, grouped by rhyme scheme. The user writes each line to land on its anchor. Without `--rng-seed`, repeated runs give different sets. |
| `mt rhyme <word> [--lane] [--fresh] [--artist] [--max 20]` | A numbered, ranked rhyme list. Each item has a short score breakdown ("why"). |
| `mt multi "<ending phrase>" [--lane] [--max 20]` | Phrase-level multi-syllable rhymes: 1–3-word combinations whose vowel skeleton ends with the skeleton of the given phrase. |
| `mt vote 3+ 5- 7+` | 👍/👎 on items from the last list shown. |
| `mt used <lyrics.txt>` | Scans any text file the user wrote and logs which shown suggestions ended up in it (the strongest signal). |
| `mt flow <lyrics.txt>` | Syllables per line, shown against the user's own median and the lane median. |
| `mt stats [--ab]` | 👍 rate, "used" rate, counts by kind, and the ranking A/B test. |

**Shared options:**
- `--lane` takes `drill` (songs with cohort `drill_trap`), `pop`, or `all`. **The default is `all`**, which also includes the 93 songs with no cohort.
- `--artist` takes one or more `songs.target_artist` slugs, comma-separated (e.g. `devito,jala`).
- `--fresh` defaults to `0.5`.

The command is non-interactive: it never prompts. It runs through the wrapper `MAirina_Tucc/mt.ps1`, which uses the toolshop venv and sets `PYTHONPATH` to `MAirina_Tucc`.

## 4. Data sources and facts

- **`data/toolshop/lyrics/lyrics.db`**: 1,425 Genius songs, 16 artists, cohorts `drill_trap` and `pop`. It is opened **only** as `file:…?mode=ro&immutable=1`. It is never written, because another session may be using it.
  - `tokens` (501k; `form` keeps diacritics; `lemma`, `upos`) → the vocabulary and the anchor source.
  - `lines.syllable_count` → the lane median for `flow`.
  - `songs.genre_cohort`, `songs.target_artist` → the lane and the artist lens.
  - **Token hygiene:**
    - Keep only `source_script='latin'`. This drops 7,840 Cyrillic tokens that would otherwise pair words with their own Cyrillic twins.
    - Drop the POS tags `PUNCT`, `X`, `SYM` and `NUM`.
    - Lowercase the index keys (32.8k lowercase forms).
    - When a form has several lemmas or POS tags (2,253 forms have more than one POS; `lava` can be `lav` or `lava`), store the **majority** (most frequent) lemma and POS.
- **`line_rhymes` is not used in v1.** The co-rhyme pairs it yields (about 12.9k after removing chorus repeats) are largely the same data as `rhyme_pairs`, and they are sparse: `snimaš` has no partners. Revisit only if votes show that frequency-based ranking is weak.
- **`rhyme_pairs` is not used as a source.** Its top rows are repeated chorus lines (`ajde / sve`, 12 "matching" vowels). Its words have diacritics stripped (`imas`, `znas`), and it is sparse (`imaš` appears in only 2 pairs).
- **Reused toolshop code (imported, not copied):**
  - `toolshop.syllables.count_line` / `count_syllables`
  - `toolshop.rhyme_miner.vowel_skeleton`

  Known limitation: its `[a-zA-Z]` word regex splits words at letters with diacritics, so `vowel_skeleton("imaš")` gives `ia`. The vowel skeleton is still correct: `da me imaš` → `aeia`. We record it and don't fix it, because it isn't our module.

## 5. Architecture

Each module has one job and is testable on its own.

| Module | What it does | Interface (sketch) |
|---|---|---|
| `corpus.py` | Builds and caches the word index, applying the §4 token hygiene. The cache lives in `MAirina_Tucc/data/`. It is rebuilt when `lyrics.db`'s modified time changes. A missing DB → a clear error naming the expected path. Tokens join to songs through `lines` → `sections` → `songs`. | `load_index(db_path=None) -> Index` with `forms[form] = {lemma, upos, freq, freq_by_cohort, freq_by_artist, n_songs}` |
| `keys.py` | Rhyme keys:<br>• `tail_key(word, n=2)`: from the n-th vowel nucleus from the end, keeping consonants; lowercase; `lj`/`nj`/`dž` count as single sounds; syllabic `r` counts as a nucleus. So `imaš` / `snimaš` → `imaš`, and `lava` / `spava` → `ava`.<br>• `vowel_key(text)`: via `vowel_skeleton`.<br>• `consonant_key(word, n=2)`: the consonants of `tail_key(word, n)` in order, with vowels removed and digraphs kept whole (`snimaš` → `mš`). Words that share it but differ in vowels are consonance matches. | pure functions |
| `rank.py` | A transparent linear score. It returns `(candidate, score, features)` where `features` shows each term's contribution.<br>Terms: the kind and length of the match (a perfect tail beats a vowel-only one; longer is better); log frequency in the lane; **fresh** (the slider scales a penalty on rhyme classes that are overused across the corpus); a vote boost of `(up+1)/(up+down+2) − 0.5`; a boost for "used". The **artist lens** is a hard filter. The weights are constants in one place. | `rank(target, candidates, ctx) -> list[Scored]` |
| `anchors.py` | Maps the scheme to groups (AABB → A,A,B,B). Per group, it picks a rhyme class (tail key, vowel key or consonant key, depending on the mode) with at least k distinct lemmas in the lane. It picks content words only (NOUN/VERB/ADJ/PROPN/ADV), never two forms of the same lemma, and never repeats a word across groups. `--seed` fixes group A's class. It is deterministic when given `--rng-seed`. | `anchors(scheme, lines, lane, mode, seed, fresh, artist) -> list[Anchor]` |
| `multis.py` | Takes the target vowel skeleton of the phrase and returns 1–3-word combinations from the lane's vocabulary whose concatenated skeleton **ends with** the target.<br>Glue words (a fixed list of the most common function words: `da, se, me, te, je, u, na, sa, mi, ti, ne`) are allowed only in non-final slots. The final word must be a content word.<br>Ranked by frequency, capped at `--max`. **Vocabulary words only; never corpus lines.** | `multis(phrase, lane, max) -> list[Combo]` |
| `votes.py` | Its own SQLite file, `MAirina_Tucc/data/mairina.db` (git-ignored).<br>Tables: `shown(id, ts, list_id, arm, ranker_version, kind, query, candidate, rank, score, features_json)`, `votes(shown_id, vote, ts)`, `used(candidate, source_file, ts)`.<br>`last_list()` resolves the item numbers used by `mt vote`.<br>**The A/B arms:** each list is assigned at random, 50/50, to arm `learned` (vote and "used" boosts applied) or arm `base` (the same score without those boosts). The arm is recorded in `shown.arm`. `mt stats --ab` compares the 👍 rate per arm, and prints "not enough data" below 100 votes. | `log_shown`, `vote`, `mark_used`, `boosts(candidates)` |
| `used.py` | Tokenizes a text file (Latin with diacritics) and matches it against candidates shown in the last N days (default 14). | `scan(path, days) -> list[str]` |
| `flow.py` | `count_line` per line; the user's median over the file; the lane median from `lines.syllable_count`. | `flow(path, lane) -> table` |
| `cli.py`, `__main__.py` | argparse subcommands. UTF-8 output that is safe on a cp1252 console. | `python -m mairina …` |

**Data flow:** the CLI builds a context (lane, fresh, artist) → `corpus.load_index` → `keys` → candidates → assign an arm → `rank` (with `votes.boosts` only in arm `learned`) → printed list → `votes.log_shown`. `mt vote` and `mt used` write only to `mairina.db`.

## 6. Error handling

- `lyrics.db` missing or locked → a clear message with the expected path; exit code 2. The immutable URI avoids lock waits.
- An empty result (a rare class, or a strict artist lens) → print the reason and one hint (relax `--artist`, lower `--fresh`, or try `--mode assonance`); exit code 0.
- `mt vote` with no previous list or an item number out of range → a message; exit code 1. Nothing is written.
- `mairina.db` is created on first use. The schema is created if missing and never migrated destructively.

## 7. Testing

- A `tests/conftest.py` fixture builds a **tiny SQLite corpus** with the same schema subset (songs, sections, lines, tokens, including `tokens.source_script`). It holds hand-written words, not lyrics: `imaš, snimaš, znaš, lava, spava, separe, grade, …` across 2 cohorts and 2 artists.
- **Unit tests:**
  - tail keys (`imaš/snimaš`, `lava/spava`, digraphs, syllabic `r` as in `srce`/`prst`)
  - AABB → 2 groups with distinct lemmas and no repeated words
  - seed sets group A
  - `multi "da me imaš"` → every result's skeleton ends in `aeia`, and the final word is a content word
  - `corpus` drops Cyrillic, PUNCT and NUM tokens, and picks the majority lemma
  - arm assignment is recorded, and `stats --ab` reports "not enough data" below 100 votes
  - votes change the order deterministically
  - `used` finds words shown earlier
  - `flow` counts
  - the error paths
- **A live smoke test**, skipped if `lyrics.db` is missing:
  - `anchors --scheme AABB --lane drill` gives 4 anchors
  - `rhyme imaš` has `snimaš` in the top 10
- **Run:** `& "D:\Projects\Music-AI-Toolshop\.venv\Scripts\python.exe" -m pytest "D:\Projects\Music-AI-Toolshop\MAirina_Tucc\tests" -q`
  - `tests/conftest.py` inserts `MAirina_Tucc/` into `sys.path`, so `import mairina` works without installing it. The repo's `pytest.ini` `testpaths = tests` doesn't interfere, because the test path is given explicitly.

## 8. Not in v1, and why

| Not doing | Why |
|---|---|
| The React UI and FastAPI; restoring the `rimer-sr` submodule from GitHub `0bfeb03` | Phase 2, only if week 1 says "keep". `rimer-ui`'s panel is the target then. |
| The Hunspell dictionary fallback | 31k real forms is enough to test "real artists first". It returns with `rimer-sr`. |
| A co-rhyme boost from `line_rhymes` | Sparse, and largely duplicates `rhyme_pairs` (see §4). Revisit if frequency-based ranking proves weak. |
| Any AI-generated text | The user's rule: it finds, never writes. |
| A trained model for ranking | Transparent weights plus vote boosts first. Consider a model after 300 or more votes, and only if the A/B test plateaus. |
| Suno export, Cyrillic, MIDI | The PRD's phase 3. |
| Fixing toolshop's regex | Not our module. Vowels are unaffected. |
| Writing to `lyrics.db` or `toolshop/` | Shared with other sessions. MAirina is a read-only consumer. |

## 9. Open questions (for after week 1)

- Should "used" words also feed a personal allow-list (like lyrics_popper's `approved_vocab.txt`)?
- Should the artist lens become a named taste profile ("my Devito + Jala mix")?
