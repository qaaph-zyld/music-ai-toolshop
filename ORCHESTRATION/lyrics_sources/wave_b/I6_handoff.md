# I6 handoff — wave B: mudcat_digitrad adapter (`sources/mudcat_digitrad.py`)

**Agent:** I6 (lyrics-sources megaplan, wave B) · **Session:** 2026-10-01 ·
**Lane scope:** `Genious_lyrics_extractor/sources/mudcat_digitrad.py`,
`tests/test_lyrics_sources_mudcat.py`, committed fixtures
`tests/fixtures/lyrics_sources/mudcat_digitrad_sample.ask` +
`mudcat_titles_sample.txt`, `CREDITS.md` fixture rows, `CHANGELOG.md` #067,
`data/toolshop/lyrics/mudcat-digitrad/` (uncommitted runtime corpus), this
handoff. Gutenberg (`gutenberg_pd`) is I3's lane — untouched.

## Delivered

- `Genious_lyrics_extractor/sources/mudcat_digitrad.py` (~570 lines) — full
  SPEC §6.3 `fetch_policy='auto'` contract: `SOURCE_ID`, `iter_catalog`,
  `license_of`, `fetch_lyrics`.
- **One-shot archive, fully offline after acquisition** (SPEC §9):
  `ensure_ask()` checks `_src/Z02.ASK` → `_src/DTSpring2002MSDOS.zip` →
  exactly one `polite_get` of
  `https://mudcat.org/download/DTSpring2002MSDOS.zip`, extracts
  (sanitised member names), writes `_src/_fetch_state.json` (url/sha256/bytes).
  No per-song-page requests (robots `Crawl-delay: 10` + AI-bot UA bans —
  research handoff). `polite_get` supplies the descriptive contact UA and
  bounded retry — no blind retries.
- **askSam decoder:** cp1252 + low-control-byte→`\x1c` normalisation;
  `filename[ <id>` markers delimit records (8,980 in the Spring 2002
  snapshot); title recovered positionally via caps-shout header with
  boundary + continuation checks (askSam UI script fields rejected on both
  sides); provenance tail (initials/date/`play.exe` tune key/`(Author)`
  credit) consumed with a post-date titleish-stop so next-record titles are
  not eaten; `(Author)`/`Trad.` subtitles → `creator` else `Traditional`.
- **Mandatory © filter (SPEC §9/R2 §6 — the blocker rule):** explicit
  markers only — `copyright`/`©`/`(c)`+year-or-name/`(p)`+year/
  `all rights reserved`/permission-grant phrasing (`reproduced|reprinted|
  used … permission`, `by|with the permission of`, `permission granted`) —
  scanned over the whole record region *plus* the post-`filename[`
  pre-title tail window, with propagation to the neighbouring record on the
  shared boundary. Flagged records emit `status='dropped'` +
  `drop_reason='copyright-flagged:<marker>'` **at catalog stage** — they
  never reach the fetch loop, `license_of`/`fetch_lyrics` re-raise
  `DropItem` from stored `meta.copyright_flagged` *and* the re-parsed
  archive record (three layers), and `fetch_lyrics` can never return a
  flagged song.
- Unflagged records → `license_tier='pd'`, `license='LicenseRef-public-domain'`,
  `license_url=…/publicdomain/mark/1.0/`, `release_ok='yes'`, and the
  DigiTrad not-for-profit **charter manifest note** in both
  `meta.charter_note` (catalog) and `modified_note` (song JSON, GATE 0 Q4).
- Provenance in `meta`: `dt_filename`, `tags` (`@tags`), `dt_num`,
  `child_num`, `tune`, `transcriber`, `dt_date`, `subtitle`, `source_line`,
  `title_verified`, `copyright_marker`, `copyright_snippet`.
- Duplicate `filename[` ids (25 dup pairs in the archive) get deterministic
  `~N` occurrence suffixes → `foreign_identifier` stays unique.
- Junk-title records (comma-joined initials bleed, chord charts, `CHORUS:`,
  HTML drips, truncated first-lines, `suspect`+not-in-TITLES) → dropped
  `title-unresolved`; lyric-less records → `no-lyric-text`. Conservative
  drop beats emitting a wrong title or a possibly-© text.
- `tests/test_lyrics_sources_mudcat.py` — 30 tests, fixture-driven.
- Fixtures: `mudcat_digitrad_sample.ask` (1,965 B — synthetic askSam-shaped
  binary, 10 records covering all drop classes incl. tail-© propagation,
  dup fid, cp1252 diacritics) + `mudcat_titles_sample.txt`. **All text
  self-authored** — no sourced lyrics, fabricated notices only; provenance
  rows added to `CREDITS.md`.
- CHANGELOG Answer **#067**.

## Verification (exit codes + key output, run this session)

### Tests

```
D:/Projects/Music-AI-Toolshop/.venv/Scripts/python.exe -m pytest
    D:/Projects/Music-AI-Toolshop/tests/test_lyrics_sources_mudcat.py -x -q
→ 30 passed, 1 warning in 9.00s   (exit 0)
```

Suite: contract shape + registry row, 10-record fixture parse, title/UI
rejection, diacritics, `Traditional` fallback, provenance tail, `~2` dup
suffix, all drop classes + auditable marker names, pd/yes catalog fields +
charter note + `to_dict()` schema, `limit`/`offset`, `license_of`
(pending→LicenseInfo, flagged→DropItem ×4), `fetch_lyrics` song-v2 fields
(chord strip in clean/kept in raw, stanzas, meta), **flagged-never-song
parametrised ×4**, offline guarantee (network stub raises), download-once
path (fake session zip → extract → second call zero-network), dispatcher
end-to-end (4 fetched / 6 dropped, index license fields, no © file on disk),
resume no-refetch.

Cross-lane check:
`pytest test_lyrics_sources_core.py test_lyrics_sources_catalog.py
test_lyrics_sources_mudcat.py -m "not slow" -q`
→ **153 passed, 1 failed**, exit 1 — the single failure is
`test_registry_json_committed_and_valid` expecting `len(sources)==20` vs 19:
**I3's in-flight `wikisource_pd` merge** (dirty `registry.json` +
`test_lyrics_sources_core.py`/`test_lyrics_sources_catalog.py` in this
tree belong to that lane — uncommitted, NOT staged here; their own assert
was amended to 19 at line ~146 but a second count assert at line ~706 still
expects 20). Unrelated to I6; flagged for the orchestrator.

### Pilot (live archive — real corpus data)

```
D:/Projects/Music-AI-Toolshop/.venv/Scripts/python.exe
    D:/Projects/Music-AI-Toolshop/Genious_lyrics_extractor/fetch_lyrics_source.py
    --source mudcat_digitrad --limit 25 --resume
→ exit 0

[mudcat_digitrad] catalog -> ...\lyrics\mudcat-digitrad\_catalog.json
    (8980 new, 8980 total)
[mudcat_digitrad] 25 entries to process (resume=True, corpus=...\mudcat-digitrad)
  [1/25] OK (dt): Traditional — 'ARD TAC
  [2/25] OK (dt): Words: John Frazier [1804-1852], Music, Seàn Tyrrell
         — THE 12TH OF JULY
  [3/25] OK (dt): Traditional — 16TH AVENUE
  [4/25] OK (dt): Woody Guthrie — THE 1913 MASSACRE
  ... [5..24 all OK (dt)] ...
  [25/25] OK (dt): Traditional — ABSTRACT INTELLECTUAL THOUGHT
[mudcat_digitrad] index: 25 unique songs, 0 intra-corpus dupes
[mudcat_digitrad] done: {fetched: 25, failed: 0, dropped: 0, skipped: 0}
    (catalog counts: {fetched: 25, dropped: 1830, pending: 7125})
```

**Network status:** live download verified this session — HTTP 200,
`application/x-zip-compressed`, 7,686,062 B from
`https://mudcat.org/download/DTSpring2002MSDOS.zip` (one request total).
The pilot itself ran **fully offline** — `_src/` already held the extracted
archive, so zero network during catalog/parse/fetch (the intended posture).

### Copyright-drop accounting (release gate)

- Catalog: **8,980** entries → `dropped: 1,830` total =
  **1,672 `copyright-flagged`** + 108 `title-unresolved` + 50 `no-lyric-text`.
- Marker histogram: `copyright-word` 1,270 · `copyright-sign` 296 ·
  `c-paren-year` 33 · `c-paren-name` 17 · `prev-record-trailer` 55 ·
  `permission-grant` 1.
- Known offenders verified dropped: `BLOWWIND` (Blowin' in the Wind —
  "Copyright Warner Brothers"), `SOUNDSIL` (Sound of Silence — "Copyright
  1964 and 1965 by Charing Cross Music").
- **0** flagged catalog rows carry `json_path`; **0** song JSONs on disk
  have `release_ok != 'yes'`/`license_tier != 'pd'`. The drop is enforced
  at catalog stage (never enters `pending`), in `license_of`, and in
  `fetch_lyrics`.

### Three verbatim catalog rows (from `_catalog.json`)

```json
{"source": "mudcat_digitrad", "external_id": "HARDTAC", "title": "'ARD TAC", "artist": "Traditional", "url": "https://mudcat.org/download.cfm", "license_tier": "pd", "license_ref": "LicenseRef-public-domain", "release_ok": "yes", "fetched": true, "foreign_identifier": "HARDTAC", "creator": "Traditional", "creator_url": null, "source_url": "https://mudcat.org/download.cfm", "license": "LicenseRef-public-domain", "license_url": "https://creativecommons.org/publicdomain/mark/1.0/", "copyright_notice": null, "category": "dt", "status": "fetched", "drop_reason": null, "meta": {"dt_filename": "HARDTAC", "tags": ["Australia", "sheep", "shearing", "drink"], "charter_note": "Digital Tradition not-for-profit charter item; no copyright/© marker found in the source record (Spring 2002 askSam snapshot).", "title_verified": true, "copyright_flagged": false, "tune": "HARDTAC", "transcriber": "JB", "dt_date": "oct96", "source_line": "note:\"Recorded at the home of Mr. Jack Davies, a pioneer soldier-settler | of the Leeton District, on the Murrumbidgee, N.S.W. | Mr. Davies | says he didn't write \"Ard Tac\", but adds, \"I distinctly remember | being sober the day it was written.\" (Lahey). Tune heard from Mike | Eves, Sydney FC, 1971."}, "json_path": "dt/traditional-ard-tac.json"}
{"source": "mudcat_digitrad", "external_id": "FISHFRY", "title": "(I'VE GOT) BIGGER FISH TO FRY", "artist": "Tim Woodson", "url": "https://mudcat.org/download.cfm", "license_tier": "pd", "license_ref": null, "release_ok": null, "fetched": false, "foreign_identifier": "FISHFRY", "creator": "Tim Woodson", "creator_url": null, "source_url": "https://mudcat.org/download.cfm", "license": null, "license_url": null, "copyright_notice": null, "category": "dt", "status": "dropped", "drop_reason": "copyright-flagged:c-paren-year", "meta": {"dt_filename": "FISHFRY", "tags": ["fishing", "food"], "charter_note": "…", "title_verified": true, "copyright_flagged": true, "copyright_marker": "c-paren-year", "copyright_snippet": "Tim Woodson, Music Tim Woodson, Rob Compton, Pat Stevenson (c) 1995. @fishing @food JD July01 …", "transcriber": "JD", "dt_date": "July01", "subtitle": "Tim Woodson", "source_line": "Recorded by Wildhorse Creek | Lyrics Tim Woodson, Music Tim Woodson, Rob Compton, Pat Stevenson (c) 1995."}}
{"source": "mudcat_digitrad", "external_id": "TSTROLL1", "title": "ROLLING DOWN THE TEST LANE", "artist": "Trad.", "url": "https://mudcat.org/download.cfm", "license_tier": "pd", "license_ref": "LicenseRef-public-domain", "release_ok": "yes", "fetched": false, "foreign_identifier": "TSTROLL1", "creator": "Trad.", "creator_url": null, "source_url": "https://mudcat.org/download.cfm", "license": "LicenseRef-public-domain", "license_url": "https://creativecommons.org/publicdomain/mark/1.0/", "copyright_notice": null, "category": "dt", "status": "pending", "drop_reason": null, "meta": {"dt_filename": "TSTROLL1", "tags": ["test", "demo"], "charter_note": "…", "title_verified": true, "copyright_flagged": false, "tune": "TSTROLL1", "transcriber": "TC", "dt_date": "oct97", "subtitle": "Trad.", "source_line": "note: Transcribed for the synthetic fixture suite."}}
```

(Third row is from the synthetic fixture run — a clean `pending` example;
rows 1–2 are real pilot output: one fetched PD record, one ©-dropped row.)

## Parser limitations / deferred work

- ~108 records drop `title-unresolved` — genuine junk (initials bleed,
  chord-chart headers, HTML drips, lyric-first-line headers) AND a few real
  titles not present in the `TITLES` index (the index is *not* coextensive —
  e.g. `THE BOLD FISHERMAN` parses fine but isn't listed; index membership is
  used only as a positive-verification signal, never the drop criterion for
  titleish headers).
- ~50 records drop `no-lyric-text` — mostly DT cross-reference-only records
  (`see also`/`source:` apparatus without a text body). A small number may
  hold text the note-start heuristic misfiled; conservative, revisit only if
  corpus yield matters.
- `creator` is whatever the `(…)` subtitle says — sometimes a verbose credit
  string (`Words: …, Music, …`). Cosmetic; a wave-C normalisation pass could
  split roles.
- `©`-in-trailer propagation over-drops the *neighbour* record in ambiguous
  boundary cases (55 of 1,672 flags) — deliberate conservative choice.
- Language is `en` unless a `@french`/`@german`/… tag maps one — no real
  language detection (DigiTrad is overwhelmingly English).

## Closeout evidence

- Runtime corpus `data/toolshop/lyrics/mudcat-digitrad/` (`_src/`,
  `_catalog.json`, `_index.json`, `dt/*.json`) is under the `data/` gitignore
  rule (`.gitignore:47`) — uncommitted by design.
- Commit: `0dfe9a9` `feat(#067)` (lane commit performed by orchestrator after
  the agent's final tool call was rejected at closeout — all work + tests
  verified in-session before commit; CREDITS.md staged whole, carrying
  forward-reference rows for in-flight wave-A fixtures `mw_*`/`pg_*`).

## Other lanes' dirty paths (present, NOT staged/owned by I6)

- `Genious_lyrics_extractor/sources/registry.json` (I3's `wikisource_pd`
  merge), `sources/gutenberg_pd.py`, `sources/hymnary.py`,
  `sources/sacred_texts.py`, `sources/wikisource_pd.py` — wave-A lanes.
- `tests/test_lyrics_sources_core.py`, `tests/test_lyrics_sources_catalog.py`
  — I3's amended asserts (one stale `==20` remains → their 1 failure).
- `tests/fixtures/lyrics_sources/` — hymnary/wikisource/gutenberg/sacred
  fixture files are untracked wave-A content (not staged).
- `MAirina_Tucc/*`, `ORCHESTRATION/ogcm_flip/*`,
  `ORCHESTRATION/prompts/prompts_index.md`, `mastering_tool`,
  `suno_prompter`, `waves_megaplan.json` — other lanes.
