# T5-L2.1 — Rhyme Persistence Fix + Fingerprint Validation (the skipped L2 gate)

> **Authored 2026-07-21** by orchestrator after the L1.1 spot-check exposed a fingerprint-defeating
> defect in the out-of-band L2 rhyme miner. Parent spec: `specs/2026-07-17-lyric-intelligence-strategy.md`
> (phase L2). Obey `AGENTS.md`. **Bounded FIX + the validation gate L2 skipped — no new features.**
> **L3 (themes) stays gated until this validates.**

## Why this session exists

L2 (`toolshop/rhyme_miner.py`, commit 4347c6a) shipped out of band with no review. The engine
primitives are sound (orchestrator by-ear check found real assonance: *maker/shake/Miyake*,
*cold/sport*). **But `populate_rhymes()` persists only `find_rhymes(texts, min_match=2)` output** —
so `line_rhymes` is **34,598 rows of exclusively `match_length=2`, `rhyme_type='end'`**. The functions
`multisyllabic_rhymes()`, `find_internal_rhymes()`, `rhyme_factor()`, `infer_scheme()` exist but their
output is **never stored**. Consequence (verified 2026-07-21):

| artist | rhyme% | multis | avg_len |
|---|---|---|---|
| Jala Brat | 95% | 0 | 2.00 |
| Buba Corelli | 94% | 0 | 2.00 |
| Coby | 95% | 0 | 2.00 |
| Senidah/Nikolija/Relja | 95–96% | 0 | 2.00 |

With ~5 vowels, any two lines share a 2-vowel ending by chance → the metric **saturates and cannot
discriminate any artist from any other**. Multisyllabic chains — the strategy's stated "heart of Balkan
rap craft" — are computed and thrown away. This is exactly what L2's exit gate ("rhyme fingerprint per
artist, sanity-checked by ear") was meant to catch.

### The engine is already correct — the fix is persistence, not algorithm (orchestrator-verified 2026-07-21)

`rhyme_factor()` (`rhyme_miner.py:178`) is soundly implemented (longest-match-per-line, normalized by
total syllables) but **`populate_rhymes` never calls it**. Running it live over the corpus already
discriminates cleanly — so the fix is low-risk wiring, and these are the **validation targets** the
coder's per-artist fingerprint must reproduce (±0.05, 15-song samples):

| cohort | artist | mean rhyme_factor |
|---|---|---|
| drill_trap | Jala Brat | **0.44** (lowest — most varied) |
| drill_trap | Buba Corelli | 0.60 |
| drill_trap | Coby | 0.64 |
| pop | Relja | 0.64 |
| pop | Nikolija | 0.77 |
| pop | Senidah | 0.77 |

Pop rhymes denser than drill; Jala is the clear outlier. **If the rebuilt fingerprint does not show this
spread, the fix is wrong — do not close.**

### Exact code anchors (read these before editing)
- `populate_rhymes(conn, song_id)` — `rhyme_miner.py:322`. Currently: one `find_rhymes(texts, min_match=2)`
  call, stores all rows at `match_length=2`. **This is the only function that writes `line_rhymes`.**
- `rhyme_factor(lines) -> float` — `rhyme_miner.py:178`. Correct; **call it per song, persist the result.**
- `multisyllabic_rhymes(lines, min_length=3)` — `rhyme_miner.py:262`. Returns len≥3 groups; never called.
- `find_internal_rhymes(line, min_match=2)` — `rhyme_miner.py:131`. Per-line internal; never called.
- `infer_scheme(groups, n_lines) -> str` — `rhyme_miner.py:217`. Needs end-rhyme groups per section.
- Caveat: at `min_length=3`, song-wide grouping still runs ~82–87% of lines into some multi (mild
  saturation). `rhyme_factor` is the headline discriminator; go deeper on `match_length` (record 4/5+
  too) and, if %multi stays saturated, note per-section/adjacency locality as an L3-era sharpening —
  do NOT expand scope to a locality rewrite here.

## Task 1: Fix `populate_rhymes` persistence (TDD) — `toolshop/rhyme_miner.py`
- [ ] Record the **true match length** per rhyme group, not a fixed 2. Remove/raise the `min_match=2`
      floor so 3- and 4+-syllable end-rhyme chains are stored with their actual `match_length`.
- [ ] **Persist internal rhymes** via `find_internal_rhymes()` → rows with `rhyme_type='internal'`
      and correct `position`.
- [ ] **Persist per-song aggregates** the engine already computes: extend `song_metrics` (or a new
      `song_rhyme_metrics` table) with `rhyme_factor` (Malmi), `pct_multis` (share of matches len≥3),
      `internal_rhyme_rate`, `dominant_scheme` (from `infer_scheme`), `top_vowel_pairs` JSON.
- [ ] TDD: a hand-built fixture song containing a known 4-syllable multi and a known internal rhyme
      yields a `match_length>=4` row + an `internal` row; `rhyme_factor` matches a hand calculation.
      Synthetic fixtures only — no real lyrics.

## Task 2: Reclassify Corona + Indođija → `drill_trap` (user-confirmed by ear 2026-07-21)
- [ ] Update `COHORT_MAP` in `toolshop/lyricsdb.py`: add `"Corona": "drill_trap"`,
      `"Indođija": "drill_trap"` (also handle the ASCII/variant spelling `"Indodjija"`). Update the
      "NULL (unconfirmed)" comment. This moves 101 solo songs (Corona 92 + Indođija 9) into the rap
      reference → drill_trap solo grows 286 → 387.

## Task 3: Recompute over the full corpus
- [ ] Re-run `build-db` (or a targeted re-`populate_rhymes` + cohort UPDATE) so `line_rhymes` and the
      per-song rhyme metrics reflect the fix across all 742 songs, and Corona/Indođija land in drill_trap.
      No re-fetch from Genius.

## Task 4: The validation gate (this is the L2 exit criterion, finally run)
- [ ] Per-artist rhyme fingerprint table: `rhyme_factor`, `%multis`, `internal_rhyme_rate`,
      top vowel-pairs, `dominant_scheme` — for each drill_trap and pop artist.
- [ ] **Prove discrimination:** the artists must NO LONGER sit flat at ~95%/2.00. The per-artist mean
      rhyme_factor must reproduce the orchestrator-verified spread (Jala ~0.44 < Buba ~0.60 < Coby ~0.64
      < Nikolija/Senidah ~0.77), within ±0.05. If they don't separate, the fix is incomplete — do not close.
- [ ] By-ear check: 20 hand-picked rhyme pairs incl. multis read as real rhymes. espeak-ng sample IF
      installed; else document "espeak-ng not on this box, phonemizer validation deferred" (it's
      validation-only, not blocking).
- [ ] Write `lyrics_research/reports/2026-07-21_rhyme_fingerprints.md` (statistics only).

## Task 5: Fix CI to actually exercise lyrics tests
- [ ] `.github/workflows/*.yml` installs `.[audio]` only; the lyrics tests call `cyrtranslit`
      (lazy-imported in `normalize_text`) at runtime, so **they likely fail in CI while passing locally**
      (local has `.[lyrics]`). Add `.[lyrics]` to the CI install step and re-establish the TRUE baseline.
- [ ] Report the honest post-fix CI failure list (expect: the ~10 numpy `test_cleaning_pipeline`
      failures and nothing lyrics-related). Run URL in handoff — no "green" claims.

## Task 6: Deps, docs, commits, handoff
- [ ] **License-ledger entry for `phonemizer`** — it was added out of band (commit 252d890) without one;
      add per integration-map policy. (datasette is dev-only; note it.)
- [ ] CHANGELOG + PROJECTS_INDEX (drill_trap now includes Corona/Indođija; rhyme fingerprint live).
- [ ] Commits: (a) `fix(lyrics): persist multis/internal/rhyme-factor in populate_rhymes`,
      (b) `feat(lyrics): Corona/Indođija → drill_trap + fingerprint report`,
      (c) `ci: install lyrics extra so rhyme/normalization tests run`, (d) `docs: changelog + ledger`.
      Push. CI URL in handoff.
- [ ] Handoff `d:\Projects\.windsurf\handoffs\<ts>_music-ai-toolshop-t5l2-1.md`: match_length
      distribution before/after, per-artist fingerprint spread (proof of discrimination), cohort recount,
      CI baseline, commit hashes, deviations.

## Verification checklist
- [ ] `line_rhymes` shows a **match_length distribution beyond 2** (multis present) + `internal` rows
- [ ] Per-artist `rhyme_factor` and `%multis` **differ measurably** across the 6+2 artists (no more flat 95%)
- [ ] Corona + Indođija in `drill_trap`; drill_trap solo = 387; pop unchanged
- [ ] CI installs `.[lyrics]`; true baseline documented; no NEW failures beyond the numpy debt
- [ ] phonemizer in license ledger; repo clean; no lyric lines in repo; rhyme data only in MusicData
- [ ] Fingerprint report written; L2 exit gate genuinely satisfied

---

## Copy-Paste Bootstrap Prompt

```text
FRAMEWORK BOOTSTRAP (v11) — Execute in order:
1. Read `ai_dev_meta_layer/framework_loader.md` and load core memories + soul.
2. Read `D:\Projects\Music-AI-Toolshop\AGENTS.md`.
3. WAIT FOR MY TASK.
4. Run: python scripts/session_brief.py "T5-L2.1: rhyme persistence fix + fingerprint validation" --files "Music-AI-Toolshop/docs/superpowers/plans/2026-07-21-t5l2-1-rhyme-persistence-fix.md"
5. Load the KBs the brief names.
6. Draft a short plan from the plan file, get approval, then execute task-by-task.
7. After completion, run `python scripts/session_end.py --status completed --duration <min> --helpful <skill>`.

MY TASK: Execute D:\Projects\Music-AI-Toolshop\docs\superpowers\plans\2026-07-21-t5l2-1-rhyme-persistence-fix.md
exactly as written. This is a BOUNDED FIX + the L2 validation gate that was skipped — NO new features
(no themes/L3, no flow-analyzer work). Hard rules: rhyme data + lyrics.db in D:\MusicData, never the repo;
synthetic test fixtures only; reports are statistics-only; no re-fetch from Genius. The session is NOT done
until the per-artist fingerprint DEMONSTRABLY discriminates (artists must not sit flat at ~95%/len-2) and
match_length shows multis. Corona + Indođija → drill_trap (user confirmed they rap). CI: add the lyrics
extra so the tests actually run; paste the CI run URL in the handoff — never claim green.

WHEN DONE — REPORT BACK: create d:\Projects\.windsurf\handoffs\<yyyy-MM-dd_HHmm>_music-ai-toolshop-t5l2-1.md
with the match_length distribution before/after, the per-artist fingerprint spread proving discrimination,
cohort recount (drill_trap solo → 387), CI baseline + run URL, commit hashes, deviations. After review,
L3 (themes) is released.

OPEN FILES: Music-AI-Toolshop/docs/superpowers/plans/2026-07-21-t5l2-1-rhyme-persistence-fix.md
```
