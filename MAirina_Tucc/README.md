# MAirina Tucc v2

Anchor sets, a rhyme finder that learns your taste, and a craft engine that measures every line. **The tool finds and analyzes, it never writes**: you write every line.

Spec: `docs/superpowers/specs/2026-09-29-mairina-anchors-design.md`.

## Run

```powershell
& "D:\Projects\Music-AI-Toolshop\MAirina_Tucc\mt.ps1" <command> [options]
```

`mt.ps1` uses the toolshop venv (`.venv\Scripts\python.exe`) and sets `PYTHONPATH` to `MAirina_Tucc`. Nothing is installed and the CLI never prompts.

## Commands

| Command | What it does |
|---|---|
| `anchors --scheme AABB --lines 4 --lane drill [--section strofa] [--mode rhyme\|assonance\|consonance] [--seed panamera] [--fresh 0.5] [--artist devito] [--rng-seed N]` | One end-word per line, grouped by rhyme scheme. You write each line to land on its anchor. Each row shows the lane's syllable target range (`syl p25–p75`) for `--section`. Without `--rng-seed`, every run differs. `--seed` fixes group A's rhyme class (the seed word itself is not offered). If `--lines` differs from the scheme length, the scheme cycles with new letters. |
| `rhyme <word> [--lane] [--fresh] [--artist] [--max 20] [--line "<text>"] [--target N]` | Numbered, ranked rhyme list. Each item shows a score breakdown (match kind and length, log frequency, fresh penalty, vote and used boosts). With `--line`/`--target` the breakdown gains `gap` (candidate syllables vs. what the line still needs) and `dom-class` (shares the line's dominant consonant class). |
| `multi "<ending phrase>" [--lane] [--max 20]` | 1-3-word combinations from the corpus vocabulary whose vowel skeleton ends with the phrase's (`da me imaš` -> `aeia`). Glue words (`da se me te je u na sa mi ti ne`) only in non-final slots and at most one per combination; the final word is a content word, never a proper noun or artist name. Every adjacent word pair must be an attested corpus bigram (the two words stood directly next to each other in one line, after token hygiene), so fewer than `--max` results is normal and there is no fallback. At most 2 results share a final word and 3 share a first word. Words only, never corpus lines. |
| `vote 3+ 5- 7+` | Thumbs up/down on items of the **last list shown**. Re-voting an item replaces the earlier vote. |
| `used <lyrics.txt> [--days 14]` | Scans a text file you wrote and logs which recently shown suggestions ended up in it. The strongest signal. |
| `flow <lyrics.txt> [--lane]` | Syllables per line against your own median and the lane median. `[Section]` headers and blank lines are skipped. |
| `xray <lyrics.txt> [--lane] [--section]` | One compact advisory row per line: syllables vs. the lane target range (`~` marks a small-n lane-wide fallback), rhyme-scheme letter, consonance gauge (lane quantiles), and device tags — alliteration (`allit ✓` = strong only: at least two content-word onsets with the same phoneme within 4 words, clitics and `ne` excluded; weaker same-class matches stay a low-confidence tag in the analysis but never set the flag), consonance, internal/multisyllabic rhyme, simile, anaphora, epistrophe, epizeuxis, anadiplosis, code-switch, name-drop, hook-repeat — plus soft hint flags (dialect mixing, cliché/calque, abstract stacking, self-rhyme). Advisory only; nothing blocks. Runs degraded (no targets/gazetteer) when `lyrics.db` is missing; fails cleanly when it exists but has no CLASSLA tokens. |
| `star <lyrics.txt> <line_no> [--tag T]... [--lane]` | Stars one of your own lines. `line_no` is the number `xray` prints for it (blank lines and `[Section]` headers are not counted). Tags are free text; `metaphor`, `double-meaning`, `wordplay` and `punchline` are the usual ones and are **only ever set by you**, never detected. Stores the line, lane, tags and a feature snapshot (syllables, words, consonance density, end-rhyme tail, longest multisyllabic rhyme, alliteration, device kinds) in `mairina.db`. Starring the same line again updates that star instead of counting it twice. |
| `stars [--lane]` / `unstar <id>` | List your stars / remove one (unknown id: exit 1). |
| `me [--lane]` | Your fingerprint: per feature your mean, the **shrunk** mean `(n*mean + 8*lane_mean) / (n + 8)` against the corpus lane (so few stars lean on the lane), the lane mean and spread, plus tag and device rates. Says `low confidence (<10 stars)` under 10 stars. A star counts for `--lane L` when it was starred with that lane; `all` pools every star. |
| `hint-vote <rule_id> +\|-\|reset` | Thumbs on an `xray` hint rule (`cliche`, `calque`, `abstract_stack`, `dialect_mix`, `self_rhyme`). A rule with 3 or more down-votes and no up-vote is **muted**: `xray` stops showing it and `stats` lists it; `reset` forgets the votes and unmutes. |
| `atlas [--lane] [--artist a,b]` | Device rates per 100 corpus lines for the lane (simile, anaphora, strong alliteration, internal rhyme, code-switch, name-drop), the share of lines in a multisyllabic rhyme, mean consonance density and median syllables; one extra row per requested artist (artists under 30 lines have no row). **Statistics only - no lyric line is ever printed or cached.** First run reads the whole corpus (about 20 s), then it is cached. |
| `compare [--lane] [--artist] [--theme <word>] [--fresh] [--max]` | The single words that follow simile markers in the corpus (`ko lava` -> `lava`), ranked by how often they are used, lane frequency and the fresh slider; votes apply (`vote 3+` works on this list). Uses the same `ko` = "who" exclusion as `xray`; `kao da/što` and a line-initial `ko` are skipped; the theme word itself is never an answer; pronouns, determiners and pronoun-like adjectives (`sve`, `svaki`, `nijedna`, `moj`, `taj`, `sam`, `ceo`, ... - matched on form and lemma, see `comparisons.STOPWORDS`) are never answers. Words only, never phrases or lines. |
| `stats [--ab]` | Up-rate, used rate, counts by kind (incl. `compare`), and any muted hint rules. `--ab` compares the two ranking arms (needs 100 votes). |

`xray` additionally appends `vs★ <largest deviation>` to every row once the lane has at least 3 stars (e.g. `shorter than your ★ lines: 6 vs 9 syllables`; alliteration is left out there because the row already shows `allit ✓` and a yes/no feature scores about +-1 sigma on every line, which would outrank the real deviations), and omits muted hint rules.

Shared options: `--lane drill|pop|all` (default `all`, which includes the 93 songs with no cohort); `--artist a,b` (hard filter on `songs.target_artist`, intersected with `--lane`: words are counted only in that artist's songs of that lane); `--fresh 0.0-1.0` (default 0.5; higher penalises overused rhyme classes).

Exit codes: `0` ok (also for an empty result, which prints a reason and a hint), `1` bad vote input, missing text file, a `star` line number out of range, an unknown `unstar` id, a malformed hint rule id or `--theme` with more than one word, or `rhyme --target` without `--line`, `2` `lyrics.db` missing/unreadable, or present but unannotated (`CorpusNotAnnotated` — run `toolshop lyrics annotate --resume`).

## Where the data comes from

- `data\toolshop\lyrics\lyrics.db`, opened only as `file:...?mode=ro&immutable=1`. It is never written. The db holds several corpora; MAirina reads only `corpus='genius-pro'` (the Serbian rap corpus) — every query filters on it.
- Token hygiene: `source_script='latin'` only; POS `PUNCT`, `X`, `SYM`, `NUM` dropped; keys lowercased; majority lemma and POS per form.
- The word index (including the word-pair set, never lines) is cached in `MAirina_Tucc\data\index_*.pkl` and rebuilt when `lyrics.db`'s modified time or size changes (first run takes several seconds). A build refuses while a `-wal`/`-journal` file exists, discards a result if the db changed mid-build, and raises `CorpusNotAnnotated` when token coverage is below 90% — a partial index is never built or cached.
- Votes, shown lists, "used" hits, stars and hint votes live in `MAirina_Tucc\data\mairina.db` (created on first use by `vote`/`star`/`hint-vote`/`stats`/list commands; `xray`, `stars`, `me` only read it if it exists). Both files are git-ignored. `atlas` is cached in `data\atlas_*.pkl` (stats only). No song/line ids are ever stored in caches or mairina.db — caches re-key on db mtime+size, so id renumbering on rebuild is safe.
- `line_rhymes` and `rhyme_pairs` are deliberately not used (sparse, mostly chorus repeats).
- Name-drop gazetteer (entities + artist names) drops ad-lib/filler noise: entries under 3 letters in total, one token repeated (`a a a`, `yeah yeah`), or made only of interjections (corpus majority UPOS `INTJ`) and ad-libs (`yeah`, `hey`, `ja`, `la`, ...). Real names and brands are untouched.
- Rule lexicons live in `MAirina_Tucc\lexicons\` (see `PROVENANCE.md` — copied from `lyrics_popper`, originals untouched). A missing lexicon file disables only its own rule with a `Note:` on stderr.
- Reused code: `toolshop.syllables.count_line` and `toolshop.rhyme_miner` (`find_internal_rhymes`, `multisyllabic_rhymes`, `vowel_skeleton`, `find_rhymes`). Known limitation: toolshop's `[a-zA-Z]` regex splits words at diacritics, which leaves vowels correct.

## Craft engine (v2)

`mairina/phonetics.py` maps Serbian Latin to phoneme units (`lj`/`nj`/`dž` are single units, syllabic `r` is a nucleus) and consonant classes (plosive/sibilant/liquid/nasal/other) with voicing pairs; clitics carry no stress and are de-weighted everywhere. `mairina/devices.py` tags mechanical sound patterns and figures per line (`advisory: true` always); `mairina/rules.py` emits soft hints with stable `rule_id`s; `mairina/targets.py` caches p25/median/p75 syllable counts per lane × section type (`strofa`, `refren`, `prerefren`, `postrefren`, `hook`, `bridge`). Deliberately not implemented: metaphor, wordplay, double meaning, chiasmus, hyperbole, polyptoton, stress prediction, lazy-rhyme rules. The learning and reference layer sits on top: `mairina/fingerprint.py` keeps your stars and turns them into a shrunk-mean fingerprint (`compare` reports the largest deviations of a line in plain words), `mairina/hints.py` stores thumbs on hint rules and mutes a rule after 3 down-votes and no up-vote, `mairina/atlas.py` counts the same devices over the corpus lines per lane and artist (statistics only, cached as `data\atlas_*.pkl`, also the prior the fingerprint shrinks toward) and `mairina/comparisons.py` collects the single words that follow simile markers. New tables in `mairina.db` (`stars`, `hint_votes`) are created with `IF NOT EXISTS`; the v1 tables are never touched.

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
