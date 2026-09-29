# Wave 1 · I1 · Implement MAirina Tucc v1

You are the IMPLEMENTER. Build exactly what the spec says. Do not add features, change scope, or write any lyric lines. The product rule is: **the tool finds, it never writes.**

## Read first
- The spec (canonical): `D:\Projects\Music-AI-Toolshop\docs\superpowers\specs\2026-09-29-mairina-anchors-design.md`. Read all of it.
- Reuse, don't copy:
  - `D:\Projects\Music-AI-Toolshop\toolshop\syllables.py` (`count_line`, `count_syllables`)
  - `D:\Projects\Music-AI-Toolshop\toolshop\rhyme_miner.py` (`vowel_skeleton`)

  Import them as `toolshop.*`. The package imports fine from the toolshop venv.
- Python: `D:\Projects\Music-AI-Toolshop\.venv\Scripts\python.exe`. Use the standard library, plus the existing `toolshop` package. **No new dependencies. No pip install.**

## Build: everything under `D:\Projects\Music-AI-Toolshop\MAirina_Tucc\`
- `mairina/`: `__init__.py`, `__main__.py`, `cli.py`, `corpus.py`, `keys.py`, `rank.py`, `anchors.py`, `multis.py`, `votes.py`, `used.py`, `flow.py`, following the interfaces in spec §5
- `tests/`: `conftest.py` (tiny SQLite fixture corpus with hand-written words, **no real lyrics**; adds `MAirina_Tucc/` to `sys.path`), unit tests per spec §7, and one live smoke test that is skipped when `lyrics.db` is missing
- `mt.ps1`: runs `python -m mairina @args` with the toolshop venv python and `PYTHONPATH` set to `MAirina_Tucc`; it uses absolute paths
- `data/.gitignore`: ignores `mairina.db` and index cache files
- `README.md`: MAirina v1 usage (the commands in spec §3), where the data comes from, the week-1 test

## Hard rules
- `lyrics.db` (`D:\Projects\Music-AI-Toolshop\data\toolshop\lyrics\lyrics.db`) is opened **only** as sqlite URI `file:<posix path>?mode=ro&immutable=1` with `uri=True`. Never write to it. Another session may be using it.
- Apply the token hygiene from spec §4:
  - `source_script='latin'` only
  - drop the POS tags PUNCT, X, SYM and NUM
  - lowercase the keys
  - store the majority lemma and POS per form
- **Do not use `line_rhymes` or `rhyme_pairs`** (both are dropped in the spec).
- `multis` outputs combinations of vocabulary words only. It must never emit or store corpus lines.
- Never modify anything outside `MAirina_Tucc/`. In particular, leave alone `toolshop/`, `rimer-ui/`, `rimer-sr/`, the PRD and spec documents, the ORCHESTRATION prompts, and any other session's files. The repo has 14 uncommitted paths from other sessions; don't touch or stage them.
- **Do not run git commit, add, checkout, switch or stash.** The orchestrator commits.
- The CLI never prompts (no `input()`). Output is UTF-8-safe on a cp1252 console: reconfigure stdout or set errors='replace'.
- Keep files focused: roughly under 250 lines each.

## Verify before reporting (absolute paths)
1. `& "D:\Projects\Music-AI-Toolshop\.venv\Scripts\python.exe" -m pytest "D:\Projects\Music-AI-Toolshop\MAirina_Tucc\tests" -q`. All must pass.
2. Live runs through `mt.ps1` against the real DB:
   - `anchors --scheme AABB --lane drill --rng-seed 1`
   - `rhyme imaš --lane drill`, which must list `snimaš` in the top 10 with a score breakdown
   - `multi "da me imaš"`
   - `vote 1+`, then `stats`
   - `flow` on a small temp file you write under `MAirina_Tucc/data/` and delete afterwards

   For each run, record the first 10 lines of output.
3. Record `lyrics.db`'s modified time before and after; it must be unchanged.
4. `git -C D:\Projects\Music-AI-Toolshop status --short`. The only new paths should be under `MAirina_Tucc/`.

## Handoff
Write `D:\Projects\Music-AI-Toolshop\MAirina_Tucc\ORCHESTRATION\mairina_v1\wave1\I1_handoff.md` containing:
- the files created, with line counts
- the exact pytest summary line
- the live output excerpts
- the modified time of `lyrics.db` before and after
- the git status output
- deviations from the spec, and why
- anything left undone

Your final message: that same summary in 400 words or fewer.
