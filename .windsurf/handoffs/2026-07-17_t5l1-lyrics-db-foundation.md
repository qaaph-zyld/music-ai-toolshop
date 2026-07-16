# Handoff: T5-L1 Lyric Intelligence Foundation

**Date:** 2026-07-17
**Session:** T5-L1 lyrics.db foundation
**Status:** Complete — all 6 tasks done, pushed to `master`

## Commits

| Hash | Message |
|------|---------|
| `1625c43` | feat(lyrics): Serbian syllable counter |
| `6df2d10` | feat(lyrics): lyrics.db schema + corpus loader |
| `edc8bca` | feat(lyrics): baseline metrics + stats CLI + corpus report |
| `191e3f3` | docs: changelog + index + license ledger + plan ticks |

**Push:** `9054bf0..191e3f3 master -> master`
**CI:** https://github.com/qaaph-zyld/music-ai-toolshop/actions/runs/29541578614 — conclusion: failure (same 10 known `test_cleaning_pipeline.py` failures, no new failures)

## Ingest Reconciliation

- 386 JSON files on disk → **385 songs ingested** (1 cross-folder duplicate dropped)
- Duplicate: "Dandara*" (jala-buba-duo) vs "Dandara" (jala-solo), same primary_artist "Jala Brat"
- Dedup key strips non-alphanumeric chars so "Dandara*" matches "Dandara"
- 2,701 sections, 19,780 lines, 385 song_metrics rows
- All lines have non-null `syllable_count`

## Dedup Evidence

```
dropped: title="Dandara*" primary_artist="Jala Brat" source=jala-buba-duo/jala-brat-dandara.json
kept:    title="Dandara"  primary_artist="Jala Brat" source=jala-solo/jala-brat-dandara.json
```

## Pytest Tail

```
10 failed, 214 passed, 10 warnings in 22.69s
```

All 10 failures are in `test_cleaning_pipeline.py` (known baseline — pre-existing).
New tests: 80 passed (50 syllables + 30 lyricsdb).

## Stats Output (summary)

```
Artist                    Songs   Avg W    TTR  Avg L  Syl/L  HookR   Eng%
Jala Brat                   169   382.7 0.4736   52.2  12.22 0.1485 0.0642
Buba Corelli                 61   398.2 0.4898   55.8  12.65 0.1154 0.0637
Coby                         56   250.8 0.4318   40.7  10.16 0.1528 0.0477
```

Section types: other=1030, refren=759, strofa=754, hook=67, prerefren=34, intro=30, outro=14, bridge=13

Syllables/line: 0-2=168, 3-5=812, 6-8=3251, 9-12=6433, 13+=9116

## Deviations from Plan

1. **Dedup key enhanced**: Plan specified normalized (title, primary_artist) for dedup. Implementation strips non-alphanumeric chars to catch title variants like "Dandara*" vs "Dandara". Without this, the cross-folder duplicate would not have been caught.
2. **Test fixture cleanup**: Replaced two test words ("patrone", "diskoteka") that matched real corpus words with synthetic equivalents ("babone", "kamineto") to satisfy the "no real lyric lines in repo" rule.
3. **cyrtranslit diacritics**: `cyrtranslit.to_latin(text, "sr")` preserves Serbian diacritics (č, ć, š, ž, đ) in the transliterated output. This is correct behavior — `text_norm` contains diacritics, not stripped ASCII.

## Blockers

None. All tasks complete.

## Files Created/Modified

**New:**
- `toolshop/syllables.py`
- `toolshop/lyricsdb.py`
- `toolshop/lyrics_metrics.py`
- `tests/test_syllables.py`
- `tests/test_lyricsdb.py`
- `tests/fixtures/lyrics_min/` (4 files: _index.json + 3 synthetic songs)
- `lyrics_research/reports/2026-07-17_genius_corpus_baseline.md`

**Modified:**
- `toolshop/cli.py` (build-db + stats subcommands)
- `pyproject.toml` (cyrtranslit in lyrics extra)
- `CHANGELOG.md`
- `PROJECTS_INDEX.md`
- `docs/superpowers/STATUS.md`
- `docs/superpowers/plans/2026-07-17-t5l1-lyrics-db-foundation.md`
- `docs/superpowers/specs/2026-07-15-oss-integration-map.md` (license ledger)

## Next Steps (L2+)

- Rhyme mining (deferred from this session)
- Flow analyzer v1 (syllable density per bar, flow pattern detection)
- Refine section label parser (1,030 "other" sections — many likely non-standard labels)
- Datasette dev browsing setup
- Cross-artist collaboration analysis (duo/trio songs)
