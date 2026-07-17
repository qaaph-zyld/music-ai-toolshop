# Genius Corpus Baseline Report (T5-L1.1 Rebuild)

> **Generated**: 2026-07-17
> **Corpus**: `genius-pro` (742 songs after dedup, 5493 sections, 36572 lines)
> **Source**: `D:\MusicData\toolshop\lyrics\genius\` — 749 files on disk, 7 cross-batch duplicates dropped
> **Database**: `D:\MusicData\toolshop\lyrics\lyrics.db`
> **Cohorts**: drill_trap (Buba Corelli, Jala Brat, Coby) · pop (Nikolija, Senidah, Relja)
> **Featured songs**: 44 (excluded from baselines) · Solo: 698

## Corpus Inventory

| Category | Role | Genre Cohort | Songs |
|----------|------|-------------|-------|
| buba-solo | solo | — | 16 |
| buba-solo | solo | drill_trap | 59 |
| coby-solo | solo | — | 24 |
| coby-solo | solo | drill_trap | 56 |
| coby-solo | solo | pop | 2 |
| corona-featured | featured | — | 23 |
| corona-solo | solo | — | 92 |
| indodjija-featured | featured | — | 4 |
| indodjija-solo | solo | — | 9 |
| jala-buba-coby-trio | solo | drill_trap | 1 |
| jala-buba-duo | solo | — | 19 |
| jala-buba-duo | solo | drill_trap | 8 |
| jala-solo | solo | — | 38 |
| jala-solo | solo | drill_trap | 162 |
| nikolija-featured | featured | — | 5 |
| nikolija-featured | featured | pop | 2 |
| nikolija-solo | solo | pop | 71 |
| relja-featured | featured | — | 5 |
| relja-solo | solo | pop | 59 |
| senidah-featured | featured | — | 5 |
| senidah-solo | solo | pop | 82 |

**Dedup**: 7 cross-batch duplicates dropped. See `_dedup_log.json` for details.

## Drill/Trap Cohort Baseline

| Artist | Songs | Avg Words | TTR | Avg Lines | Syl/Line | Hook Repetition | Eng Loanword % |
|--------|-------|-----------|-----|-----------|----------|-----------------|----------------|
| Jala Brat | 169 | 382.7 | 0.4731 | 52.2 | 12.22 | 0.1486 | 0.0643 |
| Buba Corelli | 61 | 398.2 | 0.4889 | 55.8 | 12.65 | 0.1149 | 0.0637 |
| Coby | 56 | 250.8 | 0.4316 | 40.7 | 10.16 | 0.1528 | 0.0477 |

**Key observations**:
- Jala Brat remains the most prolific writer (169 solo songs, 382.7 avg words).
- Buba Corelli has the highest TTR (0.4889) — most lexically diverse per song.
- Coby has the lowest avg words (250.8) and syllables/line (10.16) — shorter, punchier songs.
- Coby has the highest hook repetition ratio (0.1528) — more repeated lines per song.
- English loanword rates are similar across all three (4.8–6.4%), consistent with the Balkan drill/trap style.

### Top-20 Words: Buba Corelli

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
| sa | 154 |
| samo | 150 |
### Top-20 Words: Jala Brat

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
| kô | 758 |
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
### Top-20 Words: Coby

| Word | Count |
|------|-------|
| da | 407 |
| je | 384 |
| to | 309 |
| ja | 263 |
| se | 227 |
| i | 221 |
| u | 218 |
| sta | 198 |
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
## Pop Cohort Baseline

| Artist | Songs | Avg Words | TTR | Avg Lines | Syl/Line | Hook Repetition | Eng Loanword % |
|--------|-------|-----------|-----|-----------|----------|-----------------|----------------|
| Senidah | 83 | 237.3 | 0.3831 | 44.9 | 8.73 | 0.2372 | 0.0834 |
| Nikolija | 71 | 279.7 | 0.3910 | 45.4 | 10.48 | 0.2419 | 0.0585 |
| Relja | 60 | 326.0 | 0.4245 | 48.1 | 11.55 | 0.2105 | 0.0596 |

**Key observations**:
- Senidah has the most solo songs (83) but the lowest avg words (237.3) — concise, focused writing.
- Relja has the highest TTR (0.4245) in the pop cohort — most lexically diverse.
- Nikolija has the highest hook repetition ratio (0.2419) — significantly more repetitive hooks than the drill/trap cohort.
- Senidah has the highest English loanword rate (8.3%) — more anglicisms than the drill/trap artists.
- All pop-cohort artists have lower syllables/line (8.7–11.6) vs drill/trap (10.2–12.7) — less dense flow.
- Hook repetition is notably higher in pop (0.21–0.24) vs drill/trap (0.11–0.15) — pop relies more on catchy repetition.

### Top-20 Words: Senidah

| Word | Count |
|------|-------|
| u | 497 |
| da | 459 |
| me | 393 |
| i | 309 |
| se | 297 |
| to | 284 |
| ja | 276 |
| ti | 264 |
| ne | 260 |
| a | 260 |
| je | 252 |
| sve | 231 |
| o | 213 |
| mi | 191 |
| do | 181 |
| na | 178 |
| te | 176 |
| kô | 150 |
| ro | 144 |
| kad | 137 |
### Top-20 Words: Nikolija

| Word | Count |
|------|-------|
| da | 545 |
| mi | 404 |
| je | 404 |
| i | 380 |
| ne | 361 |
| me | 342 |
| ti | 331 |
| u | 315 |
| se | 247 |
| na | 234 |
| a | 233 |
| sam | 231 |
| ja | 201 |
| sve | 198 |
| si | 179 |
| te | 170 |
| kad | 159 |
| to | 155 |
| samo | 151 |
| kao | 147 |
### Top-20 Words: Relja

| Word | Count |
|------|-------|
| da | 703 |
| je | 446 |
| i | 368 |
| mi | 319 |
| se | 319 |
| ne | 292 |
| u | 265 |
| a | 254 |
| samo | 247 |
| na | 233 |
| sam | 231 |
| me | 215 |
| si | 192 |
| sve | 187 |
| te | 185 |
| ti | 170 |
| ja | 163 |
| sto | 143 |
| kô | 141 |
| kad | 139 |
## Section Type Distribution

| Type | Count | % |
|------|-------|---|
| refren | 1615 | 29.4% |
| strofa | 1516 | 27.6% |
| prerefren | 657 | 12.0% |
| tekst | 546 | 9.9% |
| postrefren | 412 | 7.5% |
| intro | 243 | 4.4% |
| outro | 149 | 2.7% |
| bridge | 136 | 2.5% |
| hook | 114 | 2.1% |
| other | 49 | 0.9% |
| spoken | 38 | 0.7% |
| instrumental | 14 | 0.3% |
| interlude | 4 | 0.1% |

**`other` sections**: 49 (0.9%) — well under the 10% target.
The `tekst` type captures song-title placeholder labels (e.g., "Tekst pesme 'Hakimi'") that Genius uses for non-structured lyrics.

## Syllables Per Line Distribution

| Bucket | Count |
|--------|-------|
| 0-2 | 389 |
| 13+ | 15017 |
| 3-5 | 1946 |
| 6-8 | 6930 |
| 9-12 | 12290 |

## Cross-Cohort Comparison

| Metric | Drill/Trap (avg) | Pop (avg) |
|--------|------------------|-----------|
| Avg Words | 343.9 | 281.0 |
| TTR | 0.4645 | 0.3995 |
| Syl/Line | 11.68 | 10.25 |
| Hook Repetition | 0.1388 | 0.2299 |
| Eng Loanword % | 0.0586 | 0.0672 |

**Summary**: Drill/trap is denser (more syllables/line, more words/song) with lower hook repetition — the flow is more about lyrical density than catchiness. Pop is the inverse: shorter lines, higher hook repetition, more English loanwords. TTR is comparable between cohorts, suggesting both genres maintain similar lexical diversity despite different structural approaches.

## Datasette Browsing

The database can be browsed with Datasette (dev-only, not a project dependency):

```powershell
pip install datasette
datasette D:\MusicData\toolshop\lyrics\lyrics.db
```

Tables available: `songs`, `sections`, `lines`, `song_metrics`, `line_rhymes`, plus the `v_artist_stats` view.
New columns: `songs.role`, `songs.target_artist`, `songs.genre_cohort`.
