# Wave 2 · V1 handoff: review of MAirina Tucc v1 (read-only)

Method: all live runs used `cli.main(..., lyrics_db=<real, ro+immutable>, data_dir=<scratch>)`, so no `mairina.db` was written under `MAirina_Tucc/data`. Large samples were taken in-process (200 seeded anchor runs per lane; 10 multi phrases). Artist-name set = tokens of every `songs.primary_artist` and `target_artist` (176 tokens) plus the obvious slugs.

## Blockers

Spec conformance is clean (see Verified claims). The two blockers are quality defects that would sink the week-1 votes; both are small fixes.

**B1. Anchor pairs rhyme a word with itself (identical rhyme).** `mairina/anchors.py:109-138` (member selection and sampling) has no stem-distinctness guard. It only blocks the same *lemma*, so `nekad/ponekad` and `grabim/zgrabim` pass.
- Evidence, the required 5 unseeded runs of `anchors --scheme AABB --lane drill`: 5 of the 10 rhyme pairs were one word plus its prefixed form: `grabim/zgrabim`, `padnem/upadnem`, `srolam/rolam`, `nekad/ponekad`, `nemirna/mirna`.
- Evidence, 200 seeded runs per lane (400 pairs each): a pair where one word is a suffix of the other = 64 (drill, 16%), 71 (all, 18%), 72 (pop, 18%). That is roughly one 4-anchor set in three.
- Same lemma twice in one set: 0 of 600 runs (the spec rule is met, but the rule is too weak).
- Fix: reject a candidate when the sound just before the rhyme tail equals that of an already-picked word in the group, or when `w.endswith(p) or p.endswith(w)`. Either is a few lines inside `members()`.

**B2. `multi` lists collapse into near-duplicates and glue-word salad.** `mairina/multis.py:64-98` (`gen`, result loop). It ranks purely by frequency and skeleton, with no diversity cap and no limit on glue words.
- Evidence (20 results each, lane all): `pare i novac` gives final word `života` in 18/20 (3 distinct finals); `bez tebe nema` gives `večeras` 16/20 (`je ne večeras`, `ne je večeras`); `noćas te vidim` gives first word `noćas` 18/20; `u Panameri` gives first word `ljubav` 16/20 (`ljubav da rekli`); `da me imaš` gives final `nikad` 9/20; `nema ljubavi` gives `dubai` 7/20 (`se da dubai`).
- The 3-word share is 16-18 of 20 in five of the ten phrases. The 1-word share is 0 of 20 everywhere (needs 4+ vowels, so this is inherent).
- Artist and collective names: `da senidah` is result #1 and `da senida` #4 for the flagship phrase `da me imaš` (2/20). `ne znam kako` gives `je/se/ne/me balkaton` (4/20). Names showed up in 2 of 10 queries. That is not "frequent" by your threshold, but it hits the headline example, so fix it with the change below.
- Fix: cap results at 2 per final word and 3 per first word; allow at most one glue word per combo and never two adjacent; exclude PROPN and artist-name tokens (a denylist built from `songs.primary_artist` and `target_artist`) from the final slot.

## Nits
1. Rare forms (freq ≤ 3) rank high because `W_FREQ*log1p` (`rank.py:19`) is tiny next to the 6.0 match bonus. `rhyme imaš --lane drill` top 4 are `klimaš cimaš otimaš uzimaš` (freq 3-5). `rhyme grade`: 6/20 (all) and 10/20 (drill) have freq ≤ 3; `rhyme lava`: 0/20 (all), 2/20 (drill); `rhyme imaš`: 1/20 (all). Anchors: freq ≤ 3 = 105/800 (13%, drill) because `MIN_FREQ = 3` (`anchors.py:17`) sits exactly at the floor. Suggest `MIN_FREQ` 5 and a frequency floor in `rank`.
2. Proper nouns in anchors (PROPN allowed by spec): 49/800 (6.1%) drill, 43/800 all, 21/800 pop. Mostly brands and places (`sauvignon`, `pérignon`, `lacoste`, `rollie`, `dubai`). Real artist-name tokens: 2/800 (drill), 6/800 (all: `toni`, `jalom`, `biba`, `lamelo`, `balkaton`). Not a blocker. Ad-lib tokens (`aha`, `brr`, `yeah`...) never appear: INTJ is outside `CONTENT_POS` (0 in anchors, multis, and the 6 rhyme lists).
3. `--artist` with `--lane` does not intersect: `corpus.py:51-53` returns the artist's total once the lane frequency is above 0. `rhyme imaš --artist senidah --lane drill` gives output identical to `--lane all`, and the shown freq is the artist total.
4. The fresh slider is inert inside a rhyme class: `rank.py:66` applies the same penalty to every candidate of the class. `fresh 0` vs `1` on `lava` shifts every score by the same amount (glava 6.91 to 5.56). It only matters across classes and in anchors.
5. `--rng-seed N` fixes the A/B arm too (`cli.py:71-72`). Someone who always passes the same seed will feed one arm only. Documented, but it biases `stats --ab`.
6. `used` silently returns 0 hits for NFD-decomposed text (`used.py:9`, no `unicodedata.normalize("NFC")`) and for cp1250 files (`errors="replace"`). Tested: the NFC file gave 3 hits; the NFD version of the same text gave 0.
7. `mt vote -3+` is caught by argparse as an option (exit 2 usage error, not the friendly exit 1). Trivial.
8. Anchor classes are often inflectional endings (`-ila`, `-ami`, `-ovac`), so the pairs are grammatical rhymes.
9. `MAirina_Tucc/data/.gitignore` is invisible to git (the root `.gitignore:47` ignores `data/`). The claimed ignore of `mairina.db` and `*.pkl` does hold: `git check-ignore -v` names `.gitignore:47:data/`.
10. Stats "first 50 votes" is ordered by the latest-vote rowid, so a re-vote moves that item to the end.

## Verified claims
- **Tests:** `pytest "D:\...\MAirina_Tucc\tests" -q` gave `41 passed, 1 warning in 24.45s`. No `mairina.db` was created (`ls MAirina_Tucc/data` showed `index_3a770ed6.pkl` only).
- **Token hygiene:** in the built index, Cyrillic forms 0; uppercase keys 0; no PUNCT/X/SYM/NUM (POS list: NOUN, VERB, ADJ, PROPN, ADV, INTJ, DET, PRON, AUX, ADP, PART, SCONJ, CCONJ); 26,753 forms. Majority lemma: `lava` gave `{'lemma': 'lav'...}`; direct SQL gave `[('lav','NOUN',12),('lava','NOUN',1)]`.
- **Not used:** `grep -rn "line_rhymes|rhyme_pairs|text_raw" mairina` found nothing. The only hits are the test fixture schema (`tests/conftest.py:20`) and a README sentence.
- **Finds, never writes:** multis are built only from `ctx.vocab()` words (`multis.py:26-38`). All 40 multi results checked end with the target skeleton and have a content-word final. The only text printed is the fixed anchors banner, and `flow` echoes the user's own file. No `text_raw` in any SELECT.
- **Vote boost:** `rank.py:70` is `W_VOTE*((up+1)/(up+down+2)-0.5)`. Live: one thumbs-down shows `votes -0.33`, which equals 2.0*(1/3-0.5).
- **A/B:** with 98 synthetic votes, `stats --ab` printed `Not enough data yet. Keep voting.`; at 100 it printed a verdict. Arms are stored in `shown.arm` and printed in every list header (`arm=learned|base`).
- **Fresh:** `--fresh 0` removes the term; `--fresh 1.5` gives `error: argument --fresh: must be between 0.0 and 1.0`.
- **Artist lens is a filter:** `--artist nosuchartist` gives `No anchors: ... Hint: relax --artist ...`, exit 0. `--artist devito,jala` returns words present in those artists.
- **Lane default:** `argparse default="all"` (`cli.py:30`); list headers show `lane=all`.
- **Keys:** `srce` tail2 `rce`; `prst` `prst` (1 nucleus: syllabic `r`); `crvene` `ene` (3 nuclei, `r` syllabic); `ljubav` `ubav` (`lj` is one sound); `džaba` `aba`; `snimaš` `imaš`, consonant key `mš`; `lava`/`spava` `ava`. All correct. Known false digraph: `injekcija` treats `nj` as one sound.
- **Vote edges:** no list gives `Error: No list to vote on yet.` (exit 1, 0 rows). Out of range (`99+`, `0+`, `1+ 99-`) gives exit 1, `Nothing was saved`, rows unchanged (all-or-nothing). Re-vote: `1+` then `1-` leaves 3 vote rows and the latest wins (`votes -0.33` shows on the next list).
- **`used`:** a UTF-8 file with diacritics found `snimaš znaš čekaš`; a second run gave `0 newly logged`; a BOM file works; a missing file gives exit 1.
- **Scope:** `git status --short` shows this work only under `MAirina_Tucc/` (`ORCHESTRATION/`, `README.md`, `mairina/`, `mt.ps1`, `tests/`). `git diff --stat -- toolshop` is empty. One untracked `toolshop/flip/sample_voices.py` (mtime 22:11, during this review) is NOT from MAirina; it belongs to another session, and I did not create it.
- **lyrics.db:** mtime `2026-08-09T00:47:25.7861022+02:00`, unchanged; no `-wal` or `-journal` files.
- **Wrapper:** `mt.ps1 --help` gave `usage: mt [-h] {anchors,rhyme,multi,vote,used,flow,stats} ...`; no `mairina.db` created.
- `MAirina_Tucc/data/mairina.db` does not exist now.

## Verdict
**needs-fix**: B1 and B2 (both small, local edits to `anchors.py` and `multis.py`). Spec conformance is otherwise complete, and after these two fixes I would approve without another full review pass (re-run the same 200-run and 10-phrase samples).
