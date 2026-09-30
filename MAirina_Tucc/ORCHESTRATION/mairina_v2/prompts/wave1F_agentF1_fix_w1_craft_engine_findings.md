FRAMEWORK BOOTSTRAP (v13.0) — Execute in order:

1. Read `ai_dev_meta_layer/framework_loader.md` — loads core memories, soul, conventions, and layer model.
2. Detect project from open files / cwd; load matching AGENTS.md.
3. WAIT FOR MY TASK.
4. Call `start_session` MCP tool or run: python scripts/session.py brief "MAirina v2 wave 1F - fix adversarial review findings in the craft engine" --files "D:/Projects/.workspace_archive/reviews/2026-09-30_mairina_v2_w1.md, D:/Projects/Music-AI-Toolshop/MAirina_Tucc/mairina/devices.py, D:/Projects/Music-AI-Toolshop/MAirina_Tucc/mairina/rules.py, D:/Projects/Music-AI-Toolshop/MAirina_Tucc/mairina/rank.py, D:/Projects/Music-AI-Toolshop/MAirina_Tucc/mairina/cli.py, D:/Projects/Music-AI-Toolshop/MAirina_Tucc/mairina/phonetics.py, D:/Projects/Music-AI-Toolshop/MAirina_Tucc/mairina/targets.py".
   Load ONLY the KBs the brief names. Note the "Do NOT load" list. Skills auto-activate natively.
5. Draft a plan. Do NOT start coding until approved.
6. After completion: python scripts/session.py end --status completed --duration <min> --helpful <skill>.

WAIT FOR MY TASK.

MY TASK: 1. PRE-APPROVED: this task is already planned and approved by the user and the orchestrator (Claude). Skip bootstrap step 5 (plan approval) and implement directly. Read the review report first: D:\Projects\.workspace_archive\reviews\2026-09-30_mairina_v2_w1.md, then your own previous handoff MAirina_Tucc\ORCHESTRATION\mairina_v2\wave1\D1_handoff.md.
2. H1 rhyme letters (devices.py ~line 244): stop using toolshop find_rhymes(min_match=2) for line letters. Derive letters from keys.tail_key(last_word_of_line, n): two lines share a letter if their tail2 matches, OR their tail1 matches and is >= 2 characters (vowel + coda, e.g. 'aš'). Required result on the user's verse: lines 1/3 = A (lava/spava), line 2 = '-', lines 4/5/6 = B (znaš/imaš/snimaš).
3. H2 name_drop (devices.py ~line 48-61): do not split multi-word entities into single tokens. Keep multi-word entities as phrases (match as phrases in the line). For single-token entries, DROP any whose lowercase form has corpus majority UPOS != PROPN and frequency >= 20 (compute from tokens via the existing index). Required: 'mala' and 'niko' are never tagged name_drop; brands like gucci, porsche, bmw, sarajevo still are.
4. H3 lexicons: move MAirina_Tucc\data\lexicons\ to MAirina_Tucc\lexicons\ (outside the gitignored data/ dir), update every path and PROVENANCE.md. If any lexicon file is missing at runtime, disable only that rule, print one 'Note:' line to stderr, and continue (never crash). Verify with: git -C D:\Projects\Music-AI-Toolshop check-ignore -v MAirina_Tucc/lexicons/cliches.txt  -> must print NOTHING.
5. M1 tests must never write the real MAirina_Tucc\data\: pass cache_dir everywhere (cli.py ~106 and ~194 call targets.target without it). Add a test that snapshots the real data\ directory listing before and after running the xray/rhyme/anchors test paths and asserts it is unchanged. After your changes, delete the stray MAirina_Tucc\data\targets_a17f8d26.pkl (created by an earlier test run).
6. M2 simile: apply the 'ko' = 'who' check at ANY position (next token is a VERB/AUX by index UPOS, or the line ends with '?'), not only line-initial. Recognise the curly apostrophe U+2019 in k’o / ka’o. 'kao da' and 'kao što' get confidence low. Tests: 'pitaj ko je gazda' and 'ne znam ko me zove' -> no simile; 'hladna ko led', 'k’o mafija' -> simile.
7. M3 anaphora: the span is the SHARED opening text; require at least one non-stopword in the shared opening; extend the stoplist with pronouns/conjunctions/particles (ja, ti, on, ona, mi, vi, oni, ne, sve, to, taj, ta, ovo, i, a, ali, pa, kad, jer, da). Tests: 'Da se vratim / Da se sakrijem' -> no anaphora; 'Laku noć ... / Laku noć ...' -> anaphora with span 'Laku noć'.
8. M4 alliteration: exclude CLITICS and 'ne' before measuring. Required: on the user's verse line 6 the 'allit' flag no longer comes from se+snimaš.
9. M5 rank shaping: keep match-kind ordering intact - total shaping weight (gap + dom-class) must be <= 0.6, OR sort by match tier (perfect-2 > perfect-1 > assonance) before score. Add: if the line already exceeds the target, show a 'over target' note in why; '--target' without '--line' prints a clear error (exit 1). Test: with --line and --target, no assonance candidate ranks above any perfect-1 candidate.
10. M6 rules: self_rhyme requires a shared stem >= 4 letters or the same lemma (znaš/znam, lava/laka must NOT fire). Remove Serbian homographs from english_tokens.txt (at least: do, no, so, to, me, i, a, on, pa, sam) and add a test 'Ide do kuće, no ti si tu' -> no code_switch.
11. LOW (do all): multisyllabic tag = longest common vowel-suffix (the verse lines 5/6 must report the longest shared tail, >= 'aeia'); internal rhymes non-overlapping; consonance density excludes clitics from BOTH numerator and denominator and the gauge uses corpus-lane quantiles (so it does not saturate); digraph exception list for prefix boundaries (nadživeti, podžupan, nadživiš, injekcija, konjunkcija, tanjug not needed); targets: if a lane x section has n < 30 lines fall back to the lane all-sections range and mark it '~'; drop dialect_pairs rows where both sides are identical and drop ambiguous 'med,mijed'.
12. CORPUS SCOPE (new, required): lyrics.db now holds 7 corpora (genius-pro + English/other: ccmixter, gutenberg_pd, hymnary, lrclib, mudcat-digitrad, sacred-texts). Add one constant CORPORA = ('genius-pro',) in corpus.py and apply it to EVERY query that reads songs/lines/tokens/entities (vocabulary index, bigrams, gazetteer, targets, flow lane medians). Fixture test: an English-corpus song in the fixture DB never contributes a form, bigram, gazetteer entry or target.
13. EMPTY-INDEX GUARD (new, required): lyrics.db was rebuilt and currently has tokens = 0 (agent D0 is restoring them in parallel). If the allowed corpora have token coverage below 90% of their non-empty lines, raise a clear CorpusNotAnnotated error: 'lyrics.db has no CLASSLA tokens for genius-pro - run: toolshop lyrics annotate --resume'. Never build or cache an empty/partial index, and never overwrite an existing good index_*.pkl with a worse one. Leave MAirina_Tucc\data\index_3a770ed6.pre-rebuild-20260930.pkl untouched. Test both paths with fixtures.
14. CONCURRENT WRITER (new, required): the immutable=1 URI assumes nobody writes the file. Before building any cache, refuse if lyrics.db-wal or lyrics.db-journal exists; record mtime+size before and after the build and, if they changed, discard the result and retry once, then error. Fixture test for the 'changed during build' path.
15. IDs CHANGED: genius-pro song/line ids were renumbered (now 1426+). Make sure nothing in mairina.db or any cache stores song/line ids across rebuilds (caches must key on DB mtime+size).
16. VERIFY (absolute paths, Cwd D:\Projects\Music-AI-Toolshop): (1) "D:\Projects\Music-AI-Toolshop\.venv\Scripts\python.exe" -X utf8 -m pytest "D:\Projects\Music-AI-Toolshop\MAirina_Tucc\tests" -q -p no:cacheprovider -> all pass (fixture-based; runs now). (2) BEFORE D0 finishes: `mt xray` on the verse must fail cleanly with the CorpusNotAnnotated message (paste it). (3) AFTER the user/D0 confirms annotation is done: mt xray on the user's verse (temp file OUTSIDE the repo, e.g. %TEMP%\verse.txt) with --lane drill --section strofa -> letters A,-,A,B,B,B; no name_drop on mala/niko; simile on line 1; `mt rhyme imaš --lane drill` still lists snimaš in the top 10. (4) list MAirina_Tucc\data\ before and after the test run - identical. (5) git check-ignore on MAirina_Tucc/lexicons/* prints nothing. (6) INVARIANT (replaces the old fixed-mtime check): record lyrics.db mtime+size immediately before and after YOUR test + live runs - they must be equal (MAirina never writes it).
17. The user's verse for all checks:
Usne crvene ko lava –
s tobom uvek ludilo
(niko ne pomisli da spava)
Separe je naš, najluđi smo – znaš
Mala, mogla si da me imaš,
u Panameri da se snimaš
18. HANDOFF content: per finding ID (H1..M6, L, CORPUS, GUARD, WRITER, IDs) what you changed (file:line) and the test that proves it; exact pytest summary line; full xray output for the verse; the before/after data\ listing; git check-ignore output; lyrics.db mtime; git status --short (your paths only); deviations and anything not done. Then reply exactly: 'WAVE 1F DONE - handoff at <path>' plus the pytest summary line. Do not start wave 2.
OPEN FILES: D:/Projects/.workspace_archive/reviews/2026-09-30_mairina_v2_w1.md, D:/Projects/Music-AI-Toolshop/MAirina_Tucc/mairina/devices.py, D:/Projects/Music-AI-Toolshop/MAirina_Tucc/mairina/rules.py, D:/Projects/Music-AI-Toolshop/MAirina_Tucc/mairina/rank.py, D:/Projects/Music-AI-Toolshop/MAirina_Tucc/mairina/cli.py, D:/Projects/Music-AI-Toolshop/MAirina_Tucc/mairina/phonetics.py, D:/Projects/Music-AI-Toolshop/MAirina_Tucc/mairina/targets.py

OUTPUT: Write your handoff to: MAirina_Tucc/ORCHESTRATION/mairina_v2/wave1F/F1_handoff.md

CONSTRAINTS:
- You MAY create/modify files, but ONLY under D:\Projects\Music-AI-Toolshop\MAirina_Tucc\ (the handoff file is inside it). Never touch toolshop\, rimer-ui\, other projects, or other sessions' uncommitted files in this repo.
- Product rule: the tool FINDS and ANALYZES; it NEVER writes or completes lyric lines. All tags advisory; hints never block; no lazy/suffix-rhyme rule.
- lyrics.db (D:\Projects\Music-AI-Toolshop\data\toolshop\lyrics\lyrics.db) is opened ONLY as sqlite URI file:D:/Projects/Music-AI-Toolshop/data/toolshop/lyrics/lyrics.db?mode=ro&immutable=1 (uri=True). Never write to it.
- Standard library + the existing toolshop package only. No pip or npm installs.
- No git add/commit/checkout/switch/stash/reset - the orchestrator (Claude) commits after verifying.
- Absolute paths in every command. Work in the foreground; never start background jobs and end your turn waiting on them.
- CLI never prompts (no input()). Output UTF-8 safe on a cp1252 console.
- Tests must not write the real MAirina_Tucc\data\; delete any MAirina_Tucc\data\mairina.db you create.

CONTEXT BUDGET: 200k — stay within this window. Do not load raw file dumps;
read summaries and targeted sections only.

HANDOFF: When done, return the file path and a 1-2 sentence summary.
