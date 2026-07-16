# T5-L1 Lyric Intelligence Foundation — lyrics.db + baseline stats complete

## Plan task completion

- [x] **Task 2:** Serbian syllable counter (`toolshop/syllables.py`) — TDD
  - Evidence: `50 passed in 2.76s` — `python -m pytest tests/test_syllables.py -v`
  - Commit: `1625c43`
- [x] **Task 1:** Schema + loader (`toolshop/lyricsdb.py`) — TDD
  - Evidence: `30 passed in 13.15s` — `python -m pytest tests/test_lyricsdb.py -v`
  - Commit: `6df2d10`
- [x] **Task 3:** Baseline metrics (`toolshop/lyrics_metrics.py`) + `song_metrics` table
  - Evidence: `Metrics computed for 385 songs` — wired into `build_database()`, all 80 tests pass
  - Commit: `edc8bca`
- [x] **Task 4:** CLI `build-db`/`stats` + baseline report
  - Evidence: `toolshop lyrics build-db` produced 385 songs, 2,701 sections, 19,780 lines; `toolshop lyrics stats` produces per-artist table + distributions
  - Report: `D:\Projects\Music-AI-Toolshop\lyrics_research\reports\2026-07-17_genius_corpus_baseline.md`
  - Commit: `edc8bca`
- [x] **Task 5:** Deps (`cyrtranslit` + license-ledger), docs, commits, push
  - Evidence: `cyrtranslit>=1.2` added to `pyproject.toml` lyrics extra; MIT added to license ledger; CHANGELOG + PROJECTS_INDEX updated; pushed `9054bf0..191e3f3 master -> master`
  - CI: https://github.com/qaaph-zyld/music-ai-toolshop/actions/runs/29541578614 — conclusion: failure (same 10 known `test_cleaning_pipeline.py`, no new failures)
  - Commit: `191e3f3`
- [x] **Task 6:** Handoff file
  - Evidence: This file
  - Commit: `305eb63`

## Evidence / logs

```text
# Syllable tests
50 passed in 2.76s

# LyricsDB tests
30 passed in 13.15s

# Full suite
10 failed, 214 passed, 10 warnings in 22.69s
# (10 failures = known baseline test_cleaning_pipeline.py, pre-existing)

# build-db output
Building lyrics database...
  Corpus root: D:\MusicData\toolshop\lyrics\genius
  Database:     D:\MusicData\toolshop\lyrics\lyrics.db
  Metrics computed for 385 songs
  Ingested: 385 songs, 2701 sections, 19780 lines
  Duplicates dropped: 1
  Skipped: 0

Done. Songs: 385, Sections: 2701, Lines: 19780, Duplicates dropped: 1

# stats output (summary)
Artist                    Songs   Avg W    TTR  Avg L  Syl/L  HookR   Eng%
Jala Brat                   169   382.7 0.4736   52.2  12.22 0.1485 0.0642
Buba Corelli                 61   398.2 0.4898   55.8  12.65 0.1154 0.0637
Coby                         56   250.8 0.4318   40.7  10.16 0.1528 0.0477

Section types: other=1030, refren=759, strofa=754, hook=67, prerefren=34, intro=30, outro=14, bridge=13
Syllables/line: 0-2=168, 3-5=812, 6-8=3251, 9-12=6433, 13+=9116

# Dedup evidence
dropped: title="Dandara*" primary_artist="Jala Brat" source=jala-buba-duo/jala-brat-dandara.json
kept:    title="Dandara"  primary_artist="Jala Brat" source=jala-solo/jala-brat-dandara.json

# git grep clean (no real lyric lines in repo)
git grep -c "diskoteka" -> exit 1 (no matches)
git grep -c "patrone"  -> exit 1 (no matches)

# Push
9054bf0..191e3f3 master -> master
191e3f3..305eb63 master -> master
```

## Files changed

- `D:\Projects\Music-AI-Toolshop\toolshop\syllables.py` — Serbian syllable counter (vowels + syllabic-r)
- `D:\Projects\Music-AI-Toolshop\toolshop\lyricsdb.py` — SQLite schema, section label parser, text normalization, corpus loader with dedup
- `D:\Projects\Music-AI-Toolshop\toolshop\lyrics_metrics.py` — per-song metrics (TTR, hook repetition, English loanword rate), per-artist SQL views
- `D:\Projects\Music-AI-Toolshop\toolshop\cli.py` — added `lyrics build-db` and `lyrics stats` subcommands
- `D:\Projects\Music-AI-Toolshop\tests\test_syllables.py` — 50 TDD tests for syllable counter
- `D:\Projects\Music-AI-Toolshop\tests\test_lyricsdb.py` — 30 TDD tests for schema, loader, dedup, normalization
- `D:\Projects\Music-AI-Toolshop\tests\fixtures\lyrics_min\` — 4 synthetic fixture files (3 songs + _index.json)
- `D:\Projects\Music-AI-Toolshop\lyrics_research\reports\2026-07-17_genius_corpus_baseline.md` — baseline report with per-artist stats
- `D:\Projects\Music-AI-Toolshop\pyproject.toml` — `cyrtranslit>=1.2` added to lyrics extra
- `D:\Projects\Music-AI-Toolshop\CHANGELOG.md` — Answer #015 entry
- `D:\Projects\Music-AI-Toolshop\PROJECTS_INDEX.md` — genius-lyrics row updated
- `D:\Projects\Music-AI-Toolshop\docs\superpowers\STATUS.md` — T5-L1 status update
- `D:\Projects\Music-AI-Toolshop\docs\superpowers\plans\2026-07-17-t5l1-lyrics-db-foundation.md` — plan ticks
- `D:\Projects\Music-AI-Toolshop\docs\superpowers\specs\2026-07-15-oss-integration-map.md` — cyrtranslit (MIT) added to license ledger

## Deviations from plan

- **Dedup key enhanced**: Plan specified normalized (title, primary_artist) for dedup. Implementation strips non-alphanumeric chars to catch title variants like "Dandara*" vs "Dandara". Without this, the cross-folder duplicate would not have been caught.
- **Test fixture cleanup**: Replaced two test words ("patrone", "diskoteka") that matched real corpus words with synthetic equivalents ("babone", "kamineto") to satisfy the "no real lyric lines in repo" rule.
- **cyrtranslit diacritics**: `cyrtranslit.to_latin(text, "sr")` preserves Serbian diacritics (č, ć, š, ž, đ) in the transliterated output. This is correct behavior — `text_norm` contains diacritics, not stripped ASCII.

## Open blockers

None. All tasks complete.

## Next steps

1. Rhyme mining (deferred from T5-L1 plan)
2. Flow analyzer v1 — syllable density per bar, flow pattern detection
3. Refine section label parser — 1,030 "other" sections likely use non-standard labels
4. Cross-artist collaboration analysis (duo/trio songs)
5. Datasette dev browsing setup (`pip install datasette && datasette D:\MusicData\toolshop\lyrics\lyrics.db`)
