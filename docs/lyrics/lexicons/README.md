# Lyrics Popper Lexicons

Seed wordlists for the QC slop-detector and the songwriting pipeline. Each list is a starting cut — expand per the process notes below.

## Files

| File | Purpose | Maps to |
|------|---------|---------|
| `calques.txt` | Banned English-translated idioms | Anti-Slop Playbook §A1; Constitution Art. 1.4 |
| `cliches.txt` | Banned globalized pop clichés | Anti-Slop Playbook §B4; Constitution Art. 4.2 |
| `abstract_nouns.txt` | Nouns that count as abstract for concreteness-density | Constitution Art. 2.1–2.3 |
| `concrete_nouns.csv` | Concrete sensory nouns grouped by theme | Craft KB Module 3.1 |
| `dialect_pairs.csv` | Ekavica ↔ Ijekavica pairs for consistency checks | Constitution Art. 1.1–1.2; Craft KB Module 1.1 |
| `slang_turcizmi.csv` | Slang and turcizmi with register/region tags | Constitution Art. 4.3; Craft KB Module 1.4 |

## Format

- `.txt` files: one entry per line, lowercase, Latin script, UTF-8. Lines starting with `#` are comments.
- `.csv` files: header row, comma-separated, UTF-8. The first column is the lookup term.

## Expansion process

1. When a new slop pattern appears in a QC or human-gate report, add the offending phrase to the matching list.
2. When a new persona needs a regional word, add it to `slang_turcizmi.csv` with the correct `register` and `region`.
3. Run `tests/test_lexicons.py` to ensure the files still parse cleanly.
