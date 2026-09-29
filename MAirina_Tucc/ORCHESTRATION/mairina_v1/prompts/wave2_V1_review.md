# Wave 2 · V1 · Review MAirina Tucc v1 (read-only)

You are the REVIEWER. **Read-only.** Do not edit, create, stage or commit any file, with two exceptions: your handoff file, and temp files under `C:\Users\015ZCS\AppData\Local\Temp\claude\D--Projects\192b31e8-7d89-4cfb-a025-36d702159423\scratchpad\review_mairina\`.
- Set the environment variable so any `mairina.db` goes to scratch: run commands from scratch copies or tolerate `MAirina_Tucc/data/mairina.db` being created. If one gets created, **delete it at the end.** It must not exist when you finish.
- `lyrics.db` may be opened only as `file:D:/Projects/Music-AI-Toolshop/data/toolshop/lyrics/lyrics.db?mode=ro&immutable=1`.

## Inputs
- **Spec (canonical):** `D:\Projects\Music-AI-Toolshop\docs\superpowers\specs\2026-09-29-mairina-anchors-design.md`
- **Code:** `D:\Projects\Music-AI-Toolshop\MAirina_Tucc\` (`mairina/`, `tests/`, `mt.ps1`, `README.md`)
- **Implementer's handoff:** `...\MAirina_Tucc\ORCHESTRATION\mairina_v1\wave1\I1_handoff.md`. Don't trust it; verify it.
- **Python:** `D:\Projects\Music-AI-Toolshop\.venv\Scripts\python.exe`

## Verify independently
1. `pytest "D:\Projects\Music-AI-Toolshop\MAirina_Tucc\tests" -q`. Quote the summary.
2. **Spec conformance, per module in §5:**
   - token hygiene: Latin only; no PUNCT/X/SYM/NUM; lowercase; majority lemma
   - `line_rhymes` and `rhyme_pairs` are not used
   - the A/B arms are recorded, and `stats --ab` says "not enough data" below 100 votes
   - the vote boost formula
   - the fresh slider
   - the artist lens as a filter
   - the `--lane` default is `all`
3. **The product rule: the tool finds, it never writes.** No code path generates text beyond combining vocabulary words. `multi` never emits corpus lines. Grep for any stored or printed `text_raw`.
4. **Quality problems that would sink the week-1 test.** Run these live and judge them:
   - `mt anchors --scheme AABB --lane drill` (5 runs without a seed)
   - `mt rhyme imaš`, `mt rhyme lava`, `mt rhyme grade`
   - `mt multi "da me imaš"`, `mt multi "u Panameri"`

   Check specifically:
   - (a) whether **artist names or other proper nouns** (e.g. `senidah`, `jala`, `devito`, and the names in `songs.target_artist` or `primary_artist`) appear as anchors, rhymes or multi words. **Treat this as a blocker if frequent.**
   - (b) rare junk forms (freq ≤ 3), onomatopoeia and ad-lib tokens (`aha`, `jeah`, `brr`)
   - (c) the same lemma appearing twice in one anchor set
   - (d) the balance between the 1-word, 2-word and 3-word combinations in multi

   Quantify each: how many of 20 results.
5. Correctness of `tail_key`, `consonant_key` and syllabic `r`, checked on your own examples: `srce`, `prst`, `crvene`, `ljubav`, `džaba`, `snimaš`.
6. `vote` and `used` edge cases: no previous list; an index out of range; re-voting; `used` on a file with diacritics.
7. Scope: `git -C D:\Projects\Music-AI-Toolshop status --short`. Only paths under `MAirina_Tucc/` may be new from this work. `toolshop/` must be unmodified: check `git diff --stat -- toolshop`.
8. `lyrics.db`'s modified time must still be `2026-08-09T00:47:25.7861022+02:00`.

## Handoff
Write `D:\Projects\Music-AI-Toolshop\MAirina_Tucc\ORCHESTRATION\mairina_v1\wave2\V1_handoff.md` with these sections:
- **Blockers:** each with `file:line`, evidence, and a suggested fix
- **Nits**
- **Verified claims:** each with the command used and a short output quote
- **Verdict:** `approved` or `needs-fix`

Your final message: the same content in 500 words or fewer.
