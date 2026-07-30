# Cohen's d Recompute on Expanded Corpus

**Generated:** 2026-07-30  
**DB:** `D:\Projects\Music-AI-Toolshop\data\toolshop\lyrics\lyrics.db`  
**Prior result:** d = 1.1786 on 742 songs (T5-L2.1 verification, 2026-07-22)

---

## Corpus

| Cohort | Songs | Role |
|--------|-------|------|
| drill_trap | 795 | solo |
| pop | 520 | solo |
| **Total** | **1315** | |

Expansion: 742 → 1315 songs (573 new)

## Rhyme Factor (Primary Discrimination Metric)

| Statistic | Drill Trap | Pop |
|-----------|------------|-----|
| N | 795 | 520 |
| Median | 0.5974 | 0.7771 |
| Mean | 0.5931 | 0.7598 |
| Std Dev | 0.1926 | 0.1257 |
| Min | 0.0 | 0.0 |
| Max | 1.0 | 1.0 |

**Cohen's d = 0.9841** (pop > drill, positive d means pop rhymes more densely)

**Prior d = 1.1786** on 742 songs → **Current d = 0.9841** on 1315 songs

Effect size: **large** (|d| = 0.9841)

### Overlap Analysis

- Drill songs above pop median RF (0.7771): **19.1%**
- Pop songs below drill median RF (0.5974): **90.0%**

## Secondary Metrics

| Metric | Drill median | Pop median | Cohen's d | Direction |
|--------|-------------|------------|-----------|-----------|
| % Multisyllabic | 0.8571 | 0.9167 | 0.5015 | pop > drill |
| Internal Rhyme Rate | 0.8837 | 0.8386 | -0.3527 | drill > pop |

## Verdict

The discrimination effect size **Cohen's d = 0.9841** on 1315 songs 
(confirms the prior finding of d = 1.1786).

Direction is **consistent** with L2.1: pop cohort rhymes more densely than drill_trap.
The expanded corpus (1315 vs 742 songs) preserves large-effect discrimination.
