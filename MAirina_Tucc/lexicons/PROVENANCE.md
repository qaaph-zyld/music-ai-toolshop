# Lexicon provenance

These files live in `MAirina_Tucc\lexicons\` — outside the gitignored `data/`
directory, so a fresh checkout has them (moved from `data\lexicons` in wave 1F).
They are **copies, not synced mirrors**. They were copied once from
`D:\Projects\lyrics_popper\` on 2026-09-29 for MAirina Tucc v2 (wave 1, the craft
engine). The originals remain the property of the lyrics_popper project; do not
edit them there from this repo, and do not auto-sync changes back or forth.

Wave-1F edits to the copies: `dialect_pairs.csv` dropped identical-value rows
and the ambiguous `med,mijed`; `english_tokens.txt` dropped the Serbian
homographs `do`, `no`, `so`, `as` (they were false `code_switch` hits).

| File | Source | Used by |
|---|---|---|
| `calques.txt` | `lyrics_popper\data\lexicons\calques.txt` | `mairina/rules.py` (`calque` hint) |
| `cliches.txt` | `lyrics_popper\data\lexicons\cliches.txt` | `mairina/rules.py` (`cliche` hint) |
| `abstract_nouns.txt` | `lyrics_popper\data\lexicons\abstract_nouns.txt` | `mairina/rules.py` (`abstract_stack` hint) |
| `concrete_nouns.csv` | `lyrics_popper\data\lexicons\concrete_nouns.csv` | `mairina/rules.py` (`abstract_stack` hint) |
| `dialect_pairs.csv` | `lyrics_popper\data\lexicons\dialect_pairs.csv` | `mairina/rules.py` (`dialect_mix` hint) |
| `english_tokens.txt` | `ENGLISH_TOKENS` set, `lyrics_popper\scripts\qc.py` lines ~46-68 | `mairina/devices.py` (`code_switch` tag) |

Formats match `lyrics_popper\scripts\qc.py::load_lexicons`: text lists are one
lowercase entry per line with `#` comments; `concrete_nouns.csv` uses its first
column; `dialect_pairs.csv` columns are `ekavica,ijekavica`.
