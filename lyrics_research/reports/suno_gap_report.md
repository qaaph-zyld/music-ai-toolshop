# Suno Gap Report: AI-Generated vs Professional Lyrics

**Generated:** 2026-07-30  
**Suno corpus:** 3426 total liked tracks, 3381 with lyrics  
**Genius corpus:** {'NULL_featured': 93, 'drill_trap_featured': 13, 'drill_trap_solo': 795, 'pop_featured': 4, 'pop_solo': 520}  
**DB:** `D:\Projects\Music-AI-Toolshop\data\toolshop\lyrics\lyrics.db`

---

## L1 — Structure

| Metric | Suno AI | Genius Drill (solo) | Genius Pop (solo) |
|--------|---------|---------------------|--------------------|
| Songs analyzed | 3381 | 795 | 520 |
| Avg sections/song | 12.5548 | 6.2 | 7.29 |
| Median sections/song | 8 | 6 | 7.0 |
| Avg lines/song | 61.6021 | 49.12 | 40.77 |
| Median lines/song | 53 | 48 | 40.0 |

### Section Type Distribution

| Type | Suno % | Drill % | Pop % |
|------|--------|---------|-------|
| bridge | 1.6% | 2.2% | 3.0% |
| hook | 0.9% | 2.1% | 0.0% |
| instrumental | 1.2% | 0.1% | 0.7% |
| interlude | 0.1% | 0.1% | 0.0% |
| intro | 2.8% | 5.5% | 2.6% |
| other | 8.0% | 1.3% | 0.6% |
| outro | 2.4% | 2.5% | 2.9% |
| postrefren | 0.3% | 6.6% | 6.5% |
| prerefren | 1.5% | 10.5% | 16.2% |
| refren | 4.6% | 30.7% | 29.3% |
| spoken | 0.1% | 0.0% | 2.4% |
| strofa | 6.3% | 27.7% | 24.4% |
| tekst | 0.0% | 10.6% | 11.3% |

## L2 — Rhyme Metrics

| Metric | Suno AI (median) | Suno AI (mean) | Drill (median) | Pop (median) |
|--------|------------------|-----------------|-----------------|---------------|
| Rhyme Factor | 0.5038 | 0.4824 | 0.5974 | 0.7771 |
| % Multisyllabic | 1.0909 | 1.0996 | 0.8571 | 0.9167 |
| Internal Rhyme Rate | 2.1296 | 2.9391 | 0.8837 | 0.8386 |

### Rhyme Scheme Distribution (Suno)

| Scheme | Count | % |
|--------|-------|---|
| HAABCCDCBCDCACCCCECECECEIFBGCDJDKBLFFBMGNDOCECECECE | 112 | 3.3% |
| AAKBLCACMCNCDEBBEEFEBEBEEEBEDDODGHPHGQRASIAIGJCJDJAJDDDDEFEBBFEEBE | 38 | 1.1% |
| AFGHBICDCDCDCDBJKEEALCDCDCDCDDDCCDDCCCDCDCDCDDDCCDDCC | 36 | 1.1% |
| ABCDEDEDFDEAGHIHBHJPEQGIKILDMDMDFDENKNJNRNSNTNHBLOFOEOKOCDUDEDFDEDEDBDVDD | 35 | 1.0% |
| AOBCDEFBGBHIJAJBPDQKCADREFFSKCADTEFFCHDLFCBUBGIMHFVNCJMWEDNEHXKCADLFCBYZ | 32 | 1.0% |
| free | 28 | 0.8% |
| ABBCDEEBFGFABHIABBCEDEGGJHGKGEHDCABBC | 26 | 0.8% |
| AAAABBKCCCDEFGGCFGGHHIGDEJJFCCCDEFGDEFGGHHIFGGHHI | 26 | 0.8% |
| NAAAABCDDCCBBBBBCBBOEFGHGPIQJCJAKKKIREFGHGSTLUMMLVW | 24 | 0.7% |
| AAAABBBBBBCDCDEFFFGGGHGGGHKCLDDAAIIJJHGEFFFGGGHGGGH | 24 | 0.7% |

### Genius Drill Top Schemes

- **free**: 3
- **AAAAAAAAAAAABCBDCBEBAAAAAAAABCBD**: 2
- **AABIJKCCBBBBBBBBDDDEFFFFGGHHBBBBBBBBDDDEE**: 2
- **AAAAAAAAABHBIJCKCAAAAAAAAADDEEFFGGAAAAAAAAA**: 2
- **AAAABCAADDDDDDDDEEDDAAAAAAAABCAA**: 2

## L3 — Lexical Metrics

| Metric | Suno AI | Genius Drill (solo) | Genius Pop (solo) |
|--------|---------|---------------------|--------------------|
| TTR (type-token ratio) | 0.5174 | 0.0883 | 0.0735 |
| Avg syllables/line | 9.41 | 11.57 | 10.37 |
| Avg words/line | N/A | 6.92 | 6.23 |
| Total words (corpus) | 1464812 | 269640 | 131971 |

### Top-50 Vocabulary Comparison

| Rank | Suno Term | Suno Freq | Drill Term | Drill Freq | Pop Term | Pop Freq |
|------|-----------|-----------|------------|------------|----------|----------|
| 1 | i | 19582 | da | 7330 | da | 4271 |
| 2 | da | 16515 | je | 6736 | je | 2968 |
| 3 | me | 14250 | i | 4795 | i | 2634 |
| 4 | je | 13268 | u | 4489 | ne | 2308 |
| 5 | you | 12027 | mi | 4202 | me | 2304 |
| 6 | ne | 11978 | na | 4193 | mi | 2240 |
| 7 | a | 10926 | a | 3553 | u | 2240 |
| 8 | to | 9316 | ne | 3461 | se | 2199 |
| 9 | the | 9233 | se | 3419 | ti | 2160 |
| 10 | u | 9225 | sam | 2958 | a | 1751 |
| 11 | se | 8710 | me | 2939 | na | 1698 |
| 12 | s | 8656 | ja | 2792 | ja | 1645 |
| 13 | db | 7716 | ti | 2689 | sam | 1513 |
| 14 | female | 7614 | sve | 2311 | sve | 1342 |
| 15 | mi | 7536 | to | 2211 | te | 1254 |
| 16 | chorus | 7245 | si | 1920 | to | 1175 |
| 17 | na | 7179 | samo | 1835 | si | 1156 |
| 18 | b | 7131 | kô | 1774 | samo | 982 |
| 19 | sam | 6885 | o | 1719 | kad | 949 |
| 20 | in | 6816 | te | 1575 | sto | 862 |
| 21 | male | 6753 | za | 1571 | o | 832 |
| 22 | verse | 6751 | bi | 1404 | za | 821 |
| 23 | on | 6360 | kad | 1396 | kô | 759 |
| 24 | and | 6358 | sa | 1270 | tebe | 655 |
| 25 | ti | 6327 | sto | 1264 | kao | 619 |
| 26 | ja | 5955 | ko | 1202 | bi | 590 |
| 27 | sve | 5838 | ona | 1149 | sa | 580 |
| 28 | it | 5801 | kao | 1135 | do | 556 |
| 29 | bass | 5795 | su | 1122 | od | 535 |
| 30 | kick | 5539 | s | 1088 | znam | 512 |
| 31 | t | 4789 | tu | 988 | nije | 509 |
| 32 | pa | 4499 | mala | 915 | sta | 497 |
| 33 | vox | 4349 | od | 909 | mene | 482 |
| 34 | bv | 4320 | jer | 890 | al | 471 |
| 35 | si | 3931 | sta | 886 | s | 466 |
| 36 | bar | 3809 | yeah | 878 | su | 453 |
| 37 | do | 3771 | la | 852 | moj | 453 |
| 38 | my | 3683 | znam | 842 | tu | 442 |
| 39 | ko | 3646 | moj | 773 | ma | 439 |
| 40 | ich | 3575 | al | 772 | bez | 405 |
| 41 | vocal | 3516 | nije | 747 | ko | 402 |
| 42 | samo | 3417 | nema | 732 | nisam | 386 |
| 43 | te | 3416 | nisam | 730 | jer | 384 |
| 44 | that | 3355 | pa | 705 | pa | 382 |
| 45 | fx | 3312 | sad | 697 | srce | 380 |
| 46 | kad | 3229 | kada | 688 | kada | 372 |
| 47 | die | 3228 | smo | 677 | nema | 365 |
| 48 | bars | 3197 | mene | 636 | gde | 361 |
| 49 | al | 3124 | do | 621 | oh | 347 |
| 50 | nema | 3051 | moja | 580 | jos | 336 |

## L4 — Slang & Distinctiveness Overlap

Suno vocabulary overlaps with **673** drill-distinctive terms and **545** pop-distinctive terms from the Genius slang lexicon.

| Metric | Value |
|--------|-------|
| Drill-distinctive overlap (weighted %) | 8.88% |
| Pop-distinctive overlap (weighted %) | 4.57% |
| Drill overlap (unique terms) | 673 |
| Pop overlap (unique terms) | 545 |

### Top Drill-Distinctive Terms Found in Suno

- **in** (freq: 6816)
- **ich** (freq: 3575)
- **can** (freq: 2925)
- **no** (freq: 2874)
- **like** (freq: 2539)
- **mich** (freq: 2437)
- **du** (freq: 2394)
- **mmm** (freq: 2270)
- **one** (freq: 2009)
- **so** (freq: 1962)
- **know** (freq: 1853)
- **und** (freq: 1758)
- **but** (freq: 1611)
- **love** (freq: 1582)
- **das** (freq: 1579)
- **ist** (freq: 1444)
- **just** (freq: 1400)
- **take** (freq: 1347)
- **go** (freq: 1346)
- **nicht** (freq: 1308)

### Top Pop-Distinctive Terms Found in Suno

- **na** (freq: 7179)
- **samo** (freq: 3417)
- **te** (freq: 3416)
- **sto** (freq: 2083)
- **so** (freq: 1962)
- **clap** (freq: 1949)
- **ay** (freq: 1796)
- **bez** (freq: 1492)
- **take** (freq: 1347)
- **re** (freq: 1317)
- **gas** (freq: 1023)
- **said** (freq: 1022)
- **grad** (freq: 1016)
- **ooh** (freq: 1015)
- **put** (freq: 945)
- **keep** (freq: 829)
- **say** (freq: 826)
- **by** (freq: 809)
- **kraj** (freq: 728)
- **off** (freq: 665)

---

## Summary & Key Gaps

### Structure
- Suno avg sections/song: **12.5548** vs Genius drill: **6.2**, pop: **7.29**
- Suno avg lines/song: **61.6021** vs Genius drill: **49.12**, pop: **40.77**

### Rhyme Craft
- Suno RF median: **0.5038** vs Drill: **0.5974**, Pop: **0.7771**
- Suno %multis median: **1.0909** vs Drill: **0.8571**, Pop: **0.9167**
- Suno IRR median: **2.1296** vs Drill: **0.8837**, Pop: **0.8386**

### Lexical
- Suno TTR: **0.5174** vs Drill: **0.0883**, Pop: **0.0735**
- Suno syl/line: **9.41** vs Drill: **11.57**, Pop: **10.37**

### Slang
- Drill overlap: **8.88%** (weighted), **673** unique terms
- Pop overlap: **4.57%** (weighted), **545** unique terms
