# T5-L2.1 Independent Verification Report

> **Statistics only.** No lyric text is stored in this report.
> Generated 2026-07-22 from `lyrics.db` (D:\MusicData\toolshop\lyrics\lyrics.db, 14.5 MB).
> Verification session: READ-ONLY. No product code, DB, or `populate_rhymes` was modified.

## VERDICT: **PASS**

All four verification tasks succeed. The rhyme fingerprint discriminates cohorts, persistence is intact, and persisted metrics match the engine to 0.000000.

---

## Task 1: Reproduced Fingerprints

Query: `get_artist_rhyme_fingerprints(conn)` — per-artist avg `rhyme_factor`, `pct_multis`, `internal_rhyme_rate` from `song_rhyme_metrics` (solo, `genius-pro` corpus).

### Core target artists (matching baseline report)

| Artist | Songs | Rhyme Factor | %Multis | IRR | Baseline RF | Match? |
|--------|------:|-------------:|--------:|----:|------------:|:------:|
| Nikolija | 71 | 0.7560 | 0.9089 | 0.8181 | 0.7560 | ✓ |
| Senidah | 83 | 0.7427 | 0.8952 | 0.7036 | 0.7427 | ✓ |
| Relja | 60 | 0.7000 | 0.9089 | 0.8673 | 0.7000 | ✓ |
| Coby | 56 | 0.6568 | 0.8187 | 0.7843 | 0.6568 | ✓ |
| Jala Brat | 169 | 0.5694 | 0.8477 | 0.8891 | 0.5694 | ✓ |
| Corona | 92 | 0.5403 | 0.7881 | 0.8787 | 0.5403 | ✓ |
| Indođija | 9 | 0.5199 | 0.8253 | 0.8847 | 0.5199 | ✓ |
| Buba Corelli | 61 | 0.5058 | 0.8471 | 0.8651 | 0.5058 | ✓ |
| Sajfer | 7 | 0.5736 | 0.8807 | 0.8947 | 0.5736 | ✓ |
| THCF | 5 | 0.7318 | 0.8541 | 0.7436 | 0.7318 | ✓ |
| Klijent | 5 | 0.4925 | 0.7962 | 0.8765 | 0.4925 | ✓ |

**All 11 baseline artists reproduce exactly.** No number drifted.

### Claimed spread confirmation

- **Pop cohort (Nikolija/Senidah/Relja):** RF 0.7000–0.7560 → claimed "0.70–0.76" ✓
- **Drill cohort (Coby/Jala/Corona/Indođija/Buba):** RF 0.5058–0.6568 → claimed "0.51–0.66" ✓

---

## Task 2: Discrimination Proof

Query: per-cohort `rhyme_factor` distribution from `song_rhyme_metrics` (solo, `genius-pro`).

### Per-cohort statistics

| Cohort | n | min | median | mean | max | stdev |
|--------|--:|----:|-------:|-----:|----:|------:|
| drill_trap | 387 | 0.0000 | 0.5628 | 0.5639 | 0.9914 | 0.1663 |
| pop | 214 | 0.3703 | 0.7399 | 0.7351 | 1.0000 | 0.1206 |

### Separation metrics

| Metric | Value |
|--------|------:|
| Cohen's d (pop − drill) | **1.1786** |
| Pop median − Drill median | **0.1771** |
| Drill songs above pop median | 52/387 (13.4%) |
| Pop songs below drill median | 19/214 (8.9%) |

**Assessment:** Cohen's d = 1.18 is a **large effect size** (>0.8 threshold). The median gap of 0.177 is non-trivial. Overlap is limited: only 13.4% of drill songs exceed the pop median, and only 8.9% of pop songs fall below the drill median. This is clearly distinguishable from the old "everyone at ~95%" saturation defect.

**DISCRIMINATION: PASS**

---

## Task 3: Persistence Integrity

### song_rhyme_metrics

| Metric | Value | Expected | Match? |
|--------|------:|---------:|:------:|
| Row count | 742 | ~742 | ✓ |

### line_rhymes

| Metric | Value | Expected | Match? |
|--------|------:|---------:|:------:|
| Total rows | 159,171 | 159,171 | ✓ |
| End rhymes | 33,309 | 33,309 | ✓ |
| Internal rhymes | 125,862 | 125,862 | ✓ |

### Match length distribution

| Match Length | Count | % |
|-------------:|------:|----:|
| 2 | 80,682 | 50.7% |
| 3 | 34,688 | 21.8% |
| 4 | 15,052 | 9.5% |
| 5 | 6,617 | 4.2% |
| 6 | 3,822 | 2.4% |
| 7 | 2,638 | 1.7% |
| 8 | 2,503 | 1.6% |
| 9 | 1,628 | 1.0% |
| 10 | 2,006 | 1.3% |
| 11–20 | ~10,000 | ~6.3% |
| 21–29 | ~309 | ~0.2% |

**match_length ≥ 3: 78,489 (49.3%)** — claimed ~49.3% ✓

**Before fix** (per #017): all 34,598 rows had `match_length=2`.
**After fix**: 159,171 rows with match_length ranging 2–29; 49.3% are multisyllabic (≥3).

**PERSISTENCE: PASS**

---

## Task 4: Persisted == Engine

Method: sampled 15 random songs (seed=42) from `song_rhyme_metrics`. For each song, fetched `text_norm` lines ordered by section/line ordinal, recomputed `rhyme_factor` and `pct_multis` using the `rhyme_miner` engine (same logic as `populate_rhymes`), and diffed against persisted values.

| song_id | Persisted RF | Engine RF | \|dRF\| | Persisted %M | Engine %M | \|d%M\| |
|--------:|-------------:|----------:|--------:|-------------:|----------:|--------:|
| 655 | 0.7359 | 0.7359 | 0.0000 | 0.9683 | 0.9683 | 0.0000 |
| 115 | 0.9221 | 0.9221 | 0.0000 | 1.0000 | 1.0000 | 0.0000 |
| 26 | 0.5709 | 0.5709 | 0.0000 | 1.0000 | 1.0000 | 0.0000 |
| 282 | 0.5942 | 0.5942 | 0.0000 | 1.0000 | 1.0000 | 0.0000 |
| 251 | 0.6702 | 0.6702 | 0.0000 | 0.9091 | 0.9091 | 0.0000 |
| 229 | 0.4209 | 0.4209 | 0.0000 | 0.8333 | 0.8333 | 0.0000 |
| 143 | 0.4400 | 0.4400 | 0.0000 | 0.8571 | 0.8571 | 0.0000 |
| 105 | 0.1728 | 0.1728 | 0.0000 | 0.3333 | 0.3333 | 0.0000 |
| 693 | 0.7980 | 0.7980 | 0.0000 | 0.8826 | 0.8826 | 0.0000 |
| 559 | 0.7184 | 0.7184 | 0.0000 | 0.8571 | 0.8571 | 0.0000 |
| 90 | 0.8336 | 0.8336 | 0.0000 | 0.9500 | 0.9500 | 0.0000 |
| 605 | 0.6733 | 0.6733 | 0.0000 | 0.8710 | 0.8710 | 0.0000 |
| 433 | 0.6048 | 0.6048 | 0.0000 | 0.7714 | 0.7714 | 0.0000 |
| 33 | 0.4778 | 0.4778 | 0.0000 | 0.8361 | 0.8361 | 0.0000 |
| 31 | 0.3444 | 0.3444 | 0.0000 | 0.7529 | 0.7529 | 0.0000 |

**Max abs diff (rhyme_factor): 0.000000**
**Max abs diff (pct_multis): 0.000000**

**PERSISTED == ENGINE: PASS** — perfect match across all 15 sampled songs. No pre-fold `text_norm` drift.

---

## Summary

| Task | Result |
|------|:------:|
| 1. Fingerprints reproduced | PASS |
| 2. Discrimination proven (Cohen's d = 1.18) | PASS |
| 3. Persistence integrity (742 rows, 49.3% multis, 125,862 internal) | PASS |
| 4. Persisted == engine (max diff 0.000000) | PASS |

**VERDICT: L2.1 VERIFIED PASS (independent re-run 2026-07-22)**

The L3 themes gate is confirmed OPEN.
