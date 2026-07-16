# Genius Corpus Baseline Report

> **Generated**: 2026-07-17
> **Corpus**: `genius-pro` (385 songs after dedup, 2,701 sections, 19,780 lines)
> **Source**: `D:\MusicData\toolshop\lyrics\genius\` — 386 files on disk, 1 cross-folder duplicate dropped
> **Database**: `D:\MusicData\toolshop\lyrics\lyrics.db`

## Corpus Inventory

| Category | Files on disk | Songs ingested |
|----------|--------------|----------------|
| buba-solo | 75 | 75 |
| coby-solo | 82 | 82 |
| jala-solo | 201 | 200 |
| jala-buba-duo | 27 | 27 |
| jala-buba-coby-trio | 1 | 1 |
| **Total** | **386** | **385** |

**Dedup**: 1 cross-folder duplicate dropped — "Dandara*" (jala-buba-duo) vs "Dandara" (jala-solo), same primary_artist "Jala Brat". Dedup key strips non-alphanumeric chars, so "Dandara*" matches "Dandara". The jala-solo copy won (first in sort order).

## Per-Artist Baseline (tracked artists)

| Artist | Songs | Avg Words | TTR | Avg Lines | Syl/Line | Hook Repetition | Eng Loanword % |
|--------|-------|-----------|-----|-----------|----------|-----------------|----------------|
| Jala Brat | 169 | 382.7 | 0.4736 | 52.2 | 12.22 | 0.1485 | 0.0642 |
| Buba Corelli | 61 | 398.2 | 0.4898 | 55.8 | 12.65 | 0.1154 | 0.0637 |
| Coby | 56 | 250.8 | 0.4318 | 40.7 | 10.16 | 0.1528 | 0.0477 |

**Key observations**:
- Jala Brat has the largest output (169 songs, 382.7 avg words) — the most prolific writer in the corpus.
- Buba Corelli has the highest TTR (0.4898) — most lexically diverse per song.
- Coby has the lowest avg words (250.8) and syllables/line (10.16) — shorter, punchier songs.
- Coby has the highest hook repetition ratio (0.1528) — more repeated lines per song.
- English loanword rates are similar across all three (4.8–6.4%), consistent with the Balkan drill/trap style.

## Top-20 Words Per Artist

### Buba Corelli

| Word | Count |
|------|-------|
| da | 728 |
| je | 486 |
| se | 431 |
| u | 422 |
| ti | 422 |
| ne | 405 |
| mi | 397 |
| i | 373 |
| na | 365 |
| ja | 339 |
| me | 246 |
| a | 242 |
| te | 235 |
| sam | 226 |
| o | 217 |
| si | 204 |
| to | 177 |
| bi | 161 |
| sa | 153 |
| samo | 150 |

### Jala Brat

| Word | Count |
|------|-------|
| je | 1611 |
| da | 1606 |
| i | 1178 |
| u | 1117 |
| na | 1051 |
| mi | 1021 |
| ne | 880 |
| a | 764 |
| me | 759 |
| se | 752 |
| sam | 633 |
| ti | 626 |
| ja | 520 |
| si | 518 |
| sve | 512 |
| to | 440 |
| bi | 395 |
| za | 390 |
| te | 374 |

### Coby

| Word | Count |
|------|-------|
| da | 407 |
| je | 384 |
| to | 309 |
| ja | 263 |
| se | 227 |
| i | 221 |
| u | 218 |
| sam | 180 |
| mi | 178 |
| me | 162 |
| a | 160 |
| ti | 124 |
| ne | 124 |
| o | 115 |
| pije | 112 |
| samo | 107 |
| si | 103 |
| mami | 102 |
| na | 98 |

## Section Type Distribution

| Type | Count |
|------|-------|
| other | 1030 |
| refren | 759 |
| strofa | 754 |
| hook | 67 |
| prerefren | 34 |
| intro | 30 |
| outro | 14 |
| bridge | 13 |

**Note**: 1,030 sections classified as "other" — these are labels that don't map to the standard set (refren/strofa/bridge/intro/outro/prerefren/hook). Many likely use non-standard Serbian or mixed-language labels. L2+ work can refine the label parser to capture more types.

## Syllables Per Line Distribution

| Bucket | Count |
|--------|-------|
| 0-2 | 168 |
| 3-5 | 812 |
| 6-8 | 3251 |
| 9-12 | 6433 |
| 13+ | 9116 |

The majority of lines (46%) have 13+ syllables, consistent with the dense, fast-flowing style of Balkan drill/trap. The 9-12 bucket (33%) is the second most common.

## Datasette Browsing

The database can be browsed with Datasette (dev-only, not a project dependency):

```powershell
pip install datasette
datasette D:\MusicData\toolshop\lyrics\lyrics.db
```

Tables available: `songs`, `sections`, `lines`, `song_metrics`, plus the `v_artist_stats` view.
