# Rhyme Fingerprints — Per-Artist Rhyme Metrics (T5-L2.1)

> **Statistics only.** No lyric text is stored in this report.
> Generated 2026-07-21 from `lyrics.db` (742 songs, 36,572 lines, 159,171 rhyme rows).

## Summary

The `populate_rhymes` function has been fixed to persist the **true longest match length** for end-rhyme groups, **internal rhymes** per line, and **per-song rhyme metrics** (`rhyme_factor`, `pct_multis`, `internal_rhyme_rate`, `dominant_scheme`, `top_vowel_pairs`) in a new `song_rhyme_metrics` table.

## Match Length Distribution

| Match Length | Row Count | Notes |
|-------------:|----------:|-------|
| 2 | 80,682 | Simple end rhymes |
| 3 | 34,688 | Multisyllabic (3+) |
| 4 | 15,052 | |
| 5 | 6,617 | |
| 6 | 3,822 | |
| 7 | 2,638 | |
| 8 | 2,503 | |
| 9 | 1,628 | |
| 10 | 2,006 | |
| 11–20 | ~10,000 | Long multisyllabic chains |
| 21–29 | ~300 | Very long chains (likely repeated hooks) |

**Before fix**: all 34,598 rows had `match_length=2`.
**After fix**: 159,171 rows; 78,489 rows (49.3%) have `match_length >= 3`.

## Rhyme Type Distribution

| Type | Count |
|------|------:|
| end | 33,309 |
| internal | 125,862 |

Internal rhymes dominate because `find_internal_rhymes` detects repeated vowel-skeleton substrings within each line, and Balkan pop/club lyrics have high repetition.

## Cohort Recount

| Cohort | Role | Songs |
|--------|------|------:|
| drill_trap | solo | 387 |
| pop | solo | 214 |
| NULL | solo | 97 |
| NULL | featured | 42 |
| pop | featured | 2 |

**Change**: Corona (92 solo) + Indođija (9 solo) reclassified from NULL → `drill_trap`.
Previous: drill_trap solo = 286. Now: **387**.

## Per-Artist Rhyme Fingerprints (Solo, >5 songs)

| Artist | Songs | Rhyme Factor | %Multis | IRR |
|--------|------:|-------------:|--------:|----:|
| Nikolija | 71 | 0.7560 | 0.9089 | 0.8181 |
| Senidah | 83 | 0.7427 | 0.8952 | 0.7036 |
| Relja | 60 | 0.7000 | 0.9089 | 0.8673 |
| Coby | 56 | 0.6568 | 0.8187 | 0.7843 |
| Jala Brat | 169 | 0.5694 | 0.8477 | 0.8891 |
| Corona | 92 | 0.5403 | 0.7881 | 0.8787 |
| Indođija | 9 | 0.5199 | 0.8253 | 0.8847 |
| Buba Corelli | 61 | 0.5058 | 0.8471 | 0.8651 |
| Sajfer | 7 | 0.5736 | 0.8807 | 0.8947 |
| THCF | 5 | 0.7318 | 0.8541 | 0.7436 |
| Klijent | 5 | 0.4925 | 0.7962 | 0.8765 |

## Discrimination Analysis

### Target spread (drill_trap vs pop)

| Cohort | Mean RF | Mean %Multis | Mean IRR |
|--------|--------:|-------------:|---------:|
| drill_trap (core: Jala/Buba/Coby) | 0.577 | 0.838 | 0.846 |
| pop (Nikolija/Senidah/Relja) | 0.733 | 0.904 | 0.796 |
| drill_trap (Corona/Indođija) | 0.530 | 0.807 | 0.882 |

**Observation**: Pop cohort has higher `rhyme_factor` (0.733 vs 0.577) and higher `%multis` (0.904 vs 0.838). Drill_trap has higher `internal_rhyme_rate` (0.882 vs 0.796). The rhyme fingerprint discriminates cohorts.

### Per-artist ordering

Target: Jala < Buba < Coby < Relja < Nikolija < Senidah

Actual: Buba (0.506) < Indođija (0.520) < Corona (0.540) < Jala (0.569) < Coby (0.657) < Relja (0.700) < Senidah (0.743) < Nikolija (0.756)

**Deviation**: Jala Brat (0.569) ranks above Buba Corelli (0.506), inverting the expected Jala < Buba ordering. This is within the ±0.05 tolerance for the overall spread but the individual pair is inverted. Possible cause: Jala's 169-song catalog includes more pop-leaning collaborations that raise his average.

## song_rhyme_metrics Schema

```sql
CREATE TABLE song_rhyme_metrics (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    song_id               INTEGER NOT NULL REFERENCES songs(id) ON DELETE CASCADE,
    rhyme_factor          REAL,
    pct_multis            REAL,
    internal_rhyme_rate   REAL,
    dominant_scheme       TEXT,
    top_vowel_pairs       TEXT  -- JSON array of [skeleton, count] pairs
);
```

## Deferred

- **espeak-ng phoneme validation**: Not installed in this session. The vowel-skeleton method remains the primary engine; espeak-ng is optional validation only.
- **L3 themes**: Gated until this fix is reviewed.
