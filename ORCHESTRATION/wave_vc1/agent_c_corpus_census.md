# Agent C - Corpus Census (Bonez MC / RAF Camora / Gzuz)

Database: D:\Projects	rack_inventory	racks.db (SQLite, audio_files table, 106,502 rows)
All SQL run via python3 + sqlite3 stdlib, sys.stdout.reconfigure(encoding='utf-8', errors='replace'), PYTHONIOENCODING=utf-8.

## Funnel per artist

Method: for each artist substring (bonez / camora / gzuz), filtered `audio_files` where `present=1`.

**Step A** — `path LIKE '%sub%'` (directory OR filename match, coarse count from orchestrator brief).
**Step B** — `name LIKE '%sub%'` (filename only — this is the Q2 signal, see below).
**Step C** — Step B AND name excludes literal markers `instrumental`, `type beat`, `acapella`, `a cappella`, `karaoke`, `stem` (the filter the orchestrator's coarse pass used).
**Step C2 (correction found by this agent)** — Step C minus 3 additional false-negative classes discovered by manually inspecting the Step-C survivor list:
  - misspelled "Instrumetal" (typo for Instrumental) — SQL: `name LIKE '%instrumetal%'`
  - hyphenated "type-beat"/"typebeat" (space-based `%type beat%` doesn't match hyphens) — SQL: `name LIKE '%type-beat%' OR name LIKE '%typebeat%'`
  - filename-suffix stems `_bass` / `_drums` / `_other` / `_vocals` / `_instrumental` / `_inst` (Demucs/Spleeter-style split outputs whose filename doesn't contain the word "stem") — detected via Python endswith check on the base filename (documented in script, not raw SQL, since SQLite LIKE can't easily anchor a suffix with wildcard-safe underscore).
**Step D** — Step C2 split by `duration_seconds >= 60` / `< 60` / `IS NULL` (NULL reported, not dropped).
**Step E** — dedupe the `duration_seconds >= 60` subset by `COALESCE-style` key: `file_hash` if non-NULL, else `name||size_bytes`.

### Bonez MC (substring `bonez`)
| Step | SQL condition | Count |
|---|---|---|
| A (path) | `present=1 AND path LIKE '%bonez%'` | 105 |
| B (name) | `present=1 AND name LIKE '%bonez%'` | 90 |
| C (literal markers excluded) | + NOT LIKE instrumental/type beat/acapella/a cappella/karaoke/stem | 18 |
| C2 (+ typo/hyphen/stem-suffix correction) | dropped 8 more (see evidence below) | 10 |
| D: duration >= 60 | | 8 |
| D: duration < 60 | | 0 |
| D: duration IS NULL (reported, not dropped) | | 2 |
| E: distinct usable (file_hash else name+size) | | **8** |

C2 dropped rows (evidence): `Bonez MC - Das ist Bonez💀 (Instrumetal)` (id 29159, duplicated 3x more at ids 69955/93560/93590 — 4 copies total of the same mislabeled instrumental), `RAF Camora & Bonez MC - REALITÄT (Anthrazit RR) #05_bass/_drums/_other` (ids 67305-67307, split stems of the one production track), `alles-umsonst-raf-camora-type-beat--bonez-mc-type-beat_TK12706358.mp3` (id 67556, a purchased "type beat" instrumental, hyphenated).

NULL-duration rows (reported, not silently dropped): `03. Hassen ist leicht (feat. Bonez MC...)` (flac, Kontra K album), `Bonez Mc x The Cratez - Honda Civic` (mp3, in `Mastering_Toolshop/external_examples`).

Final usable set (8): all 8 are **mp3**, all are **Kontra K album tracks featuring Bonez MC** or a Camora/Bonez collab — see Q3 for feature-vs-solo split (7 of 8 are `(Feat. ...)` credits on someone else's track).

### RAF Camora (substring `camora`)
| Step | SQL condition | Count |
|---|---|---|
| A (path) | `present=1 AND path LIKE '%camora%'` | 600 |
| B (name) | `present=1 AND name LIKE '%camora%'` | 124 |
| C (literal markers excluded) | | 27 |
| C2 (+ correction) | dropped 4 (the same REALITÄT stems `_bass/_drums/_other` + the same hyphenated type-beat file) | 23 |
| D: duration >= 60 | | 5 |
| D: duration < 60 | | 0 |
| D: duration IS NULL (reported, not dropped) | | 18 |
| E: distinct usable | | **5** |

**Critical finding on the 18 NULL-duration rows**: they are not missing metadata on real songs — `file_type` breakdown of the Step-C set is `production=9, sample=18` (query below). All 18 sample-type rows are individual drum/guitar/bass **loop files** from `D:\SAMPLOVI ZA MATRE\Raf Camora Drum Kit\Raf Camora Loops\` (a producer sample pack branded with his name, duplicated once more under `...\strassen\Raf Camora Drum Kit\...` — 9 unique loops × 2 copies = 18), e.g. `raf camora afrotrap guitar 132 bpm Gm.wav`, `Raf Camora Guitar Loop 100_Bm.wav`. These are **not RAF Camora audio** — they never had a chance to pass the duration filter because they are 1-4 bar instrumental loops, not songs.

SQL: `SELECT file_type, COUNT(*) FROM audio_files WHERE present=1 AND name LIKE '%camora%' AND name NOT LIKE '%instrumental%' AND name NOT LIKE '%type beat%' AND name NOT LIKE '%acapella%' AND name NOT LIKE '%a cappella%' AND name NOT LIKE '%karaoke%' AND name NOT LIKE '%stem%' GROUP BY file_type` → `[('production', 9), ('sample', 18)]`.

Final usable set (5): all **mp3**, all are tracks where RAF Camora is a featured/collab artist on someone else's release (Kontra K album tracks, or the Bonez-Camora collab single) — see Q3.

### Gzuz (substring `gzuz`)
| Step | SQL condition | Count |
|---|---|---|
| A (path) | `present=1 AND path LIKE '%gzuz%'` | 58 |
| B (name) | `present=1 AND name LIKE '%gzuz%'` | 50 |
| C (literal markers excluded) | | 3 |
| C2 (+ correction) | dropped 1 (`gzuz-187-strasenbande-type-beat-gazoline_3847391`, hyphenated type-beat) | 2 |
| D: duration >= 60 | | 0 |
| D: duration < 60 | | 0 |
| D: duration IS NULL (reported, not dropped) | | 2 |
| E: distinct usable | | **0** |

Gzuz has **zero** qualifying full-mix files under the duration>=60 rule, purely because both remaining candidates have `duration_seconds IS NULL` in the catalogue (never analyzed), not because they fail the length test. The two NULL-duration candidates: `09. Setz Dich (Feat. AK Ausser Kontrolle & Gzuz)` (mp3, 10.7MB, Kontra K album — feature) and `GZUZ - KEINER KANN MICH FICKEN!` (mp3, 5.7MB, `D:\DESKTOP2026\KHANS\` — appears to be Gzuz as primary artist by filename, but duration is unverified by this agent; **do not treat as confirmed usable** without running duration analysis, which is out of scope here per read-only/no-audio-touch instructions).

## Q2 false positives

SQL per artist:
```sql
SELECT COUNT(*) FROM audio_files WHERE present=1 AND path LIKE '%sub%';   -- Step A
SELECT COUNT(*) FROM audio_files WHERE present=1 AND name LIKE '%sub%';   -- Step B
SELECT path, parent_dir, name FROM audio_files
WHERE present=1 AND path LIKE '%sub%' AND name NOT LIKE '%sub%' LIMIT 5;  -- examples
```

| Artist | path LIKE (A) | name LIKE (B) | diff = directory-only match | % false positive of A |
|---|---|---|---|---|
| Bonez MC | 105 | 90 | 15 | 14% |
| RAF Camora | 600 | 124 | 476 | 79% |
| Gzuz | 58 | 50 | 8 | 14% |

**Bonez MC** (15 dir-only matches) — all 15 are legitimate: they live in a folder named `...\Kontra K\03 - Collaborations Albums\with Bonez MC\Auf Teufel Komm Raus (EP) (2013)\...`, one directory level names the collab, but individual track filenames (`01. Wenn der Tag anbricht.mp3`, `02. Verdammt Ja!!.mp3`, ...) don't repeat "Bonez" per-track. Example paths:
- `D:\Kontra K\03 - Collaborations Albums\with Bonez MC\Auf Teufel Komm Raus (EP) (2013)\01. Wenn der Tag anbricht.mp3`
- `D:\Kontra K\03 - Collaborations Albums\with Bonez MC\Auf Teufel Komm Raus (EP) (2013)\02. Verdammt Ja!!.mp3`
- `D:\Kontra K\03 - Collaborations Albums\with Bonez MC\Auf Teufel Komm Raus (EP) (2013)\03. Du willst N Banger (Feat. Skinny AL, Blokkmonsta & Rako)mp3.mp3`
- `D:\Kontra K\03 - Collaborations Albums\with Bonez MC\Auf Teufel Komm Raus (EP) (2013)\04. Ich seh dich.mp3`
- `D:\Kontra K\03 - Collaborations Albums\with Bonez MC\Auf Teufel Komm Raus (EP) (2013)\05. Auf Stop!.mp3`

These are a genuine Bonez MC/Kontra K collab EP and are real candidates for the "features" bucket, but they were excluded from the Step B/C/D/E funnel above (name-based) because the artist name isn't in the filename — worth flagging as an **undercount** in the Q1 funnel: name-only matching misses whole-album/whole-EP collab directories where only the folder is tagged. This agent did not fold them back into Q1 to stay consistent with the orchestrator's name-based method, but they exist and are audio.

**RAF Camora** (476 dir-only matches, 79% of the raw 600) — this is almost entirely one thing: `D:\SAMPLOVI ZA MATRE\Raf Camora Drum Kit\...`, a third-party producer sample pack of 808s/drums/loops branded with his name, containing generically-named one-shots (`808 (1).wav` … `808 (5).wav`, etc.) that have nothing to do with actual RAF Camora recordings. Example paths:
- `D:\SAMPLOVI ZA MATRE\Raf Camora Drum Kit\808s & Bass\808 (1).wav`
- `D:\SAMPLOVI ZA MATRE\Raf Camora Drum Kit\808s & Bass\808 (2).wav`
- `D:\SAMPLOVI ZA MATRE\Raf Camora Drum Kit\808s & Bass\808 (3).wav`
- `D:\SAMPLOVI ZA MATRE\Raf Camora Drum Kit\808s & Bass\808 (4).wav`
- `D:\SAMPLOVI ZA MATRE\Raf Camora Drum Kit\808s & Bass\808 (5).wav`

This confirms the orchestrator's suspicion: the coarse `path LIKE` count of 600 for RAF Camora is dominated by a sample-pack directory, not his own audio. `file_type` for these rows is `sample` throughout (verified above in Q1).

**Gzuz** (8 dir-only matches) — from `D:\SAMPLOVI ZA MATRE\[FREE] RAF CAMORA SAMPLE PACK - 500 PS (BONEZ MC, Maxwell, LX, GZUZ,187, JUl )\...`, another producer sample pack whose folder name lists multiple artists (including Gzuz) as a style reference; the actual `.wav` filenames are generic beat/loop names (`AUTOBAHN Bpm 137 Gminor.wav`, `HAMBURG Bpm 136 G#Minor.wav`, ...) unrelated to Gzuz vocals. Example paths:
- `D:\SAMPLOVI ZA MATRE\[FREE] RAF CAMORA SAMPLE PACK - 500 PS (...GZUZ...)\500 PS Bpm 140 Cminor.wav`
- `D:\SAMPLOVI ZA MATRE\[FREE] RAF CAMORA SAMPLE PACK - 500 PS (...GZUZ...)\AUTOBAHN Bpm 137 Gminor.wav`
- `D:\SAMPLOVI ZA MATRE\[FREE] RAF CAMORA SAMPLE PACK - 500 PS (...GZUZ...)\GOTHAM CITY Bpm 140 Dminor.wav`
- `D:\SAMPLOVI ZA MATRE\[FREE] RAF CAMORA SAMPLE PACK - 500 PS (...GZUZ...)\HAMBURG Bpm 136 G#Minor.wav`
- `D:\SAMPLOVI ZA MATRE\[FREE] RAF CAMORA SAMPLE PACK - 500 PS (...GZUZ...)\KULSYRE Bpm 132 Eminor.wav`

## Q3 features vs solo

Classification universe = Step C2 set from Q1 (name-matched, marker/typo/stem-suffix excluded, **all durations included** — not just the >=60s subset, so the sample-pack loop files are visible too).

Method: for each track name, find `(...)` groups; if a group contains a feat-word (`feat.`/`ft.`/`featuring`, case-insensitive) AND the artist substring, the match is classified `feat_only` if the artist name does NOT also appear outside any feat-group; `solo_or_primary` if the artist substring appears outside a feat-group (main title/artist-tag position, including cases with no parentheses at all); `both` if it appears in both places; `ambiguous` otherwise. Control check: `"18. Straßenkinder (Feat. Aslan DPK & Bonez MC)"` → substring `bonez` only appears inside `(Feat. ...)` → correctly classified `feat_only`. `"RAF Camora & Bonez MC - REALITÄT..."` → substring appears outside any parens → correctly classified `solo_or_primary`. Classifier validated on non-empty control cases before trusting empty/zero results elsewhere in this report.

SQL base (per artist, `sub` = bonez/camora/gzuz):
```sql
SELECT id, name FROM audio_files
WHERE present=1 AND name LIKE '%sub%'
  AND name NOT LIKE '%instrumental%' AND name NOT LIKE '%type beat%'
  AND name NOT LIKE '%acapella%' AND name NOT LIKE '%a cappella%'
  AND name NOT LIKE '%karaoke%' AND name NOT LIKE '%stem%';
-- then Python: drop instrumetal/type-beat/typebeat/stem-suffix, classify remainder
```

| Artist | universe (C2) | feat_only | solo_or_primary | both / ambiguous |
|---|---|---|---|---|
| Bonez MC | 10 | **8** | 2 | 0 |
| RAF Camora | 23 | **4** | 19 | 0 |
| Gzuz | 2 | **1** | 1 | 0 |

**Bonez MC**: 8 of 10 name-matched files are `(Feat. Bonez MC ...)` credits on someone else's track (all Kontra K album cuts). The 2 `solo_or_primary` are the RAF Camora/Bonez collab single `REALITÄT` (a two-way collab, not solo) and `Bonez Mc x The Cratez - Honda Civic` (a genuine Bonez-primary track, but `duration_seconds IS NULL` — unverified length).

**RAF Camora**: 19 of 23 classify `solo_or_primary` by the text rule, but **this number is misleading** — 18 of those 19 are the `Raf Camora Drum Kit` sample-pack loop files identified in Q1/Q2 (`file_type='sample'`, filenames like `raf camora afrotrap guitar 132 bpm Gm.wav`), which are not RAF Camora recordings at all, just artist-branded producer loops. Excluding the sample pack, the real `solo_or_primary` count for RAF Camora is **1** (`REALITÄT`, a Bonez collab), and `feat_only` is 4. So of RAF Camora's 5 real usable full-mix files (Step E from Q1), 4/5 are features on other artists' tracks and 1/5 is a two-way collab single — **zero solo RAF Camora full mixes** exist in this catalogue.

**Gzuz**: 1 `feat_only` (Kontra K track) and 1 `solo_or_primary` (`GZUZ - KEINER KANN MICH FICKEN!`, duration unverified/NULL).

**Bottom line for chain-matching purposes**: across all three artists, the catalogue contains essentially no verified solo full-mix reference — nearly everything usable is a "feat." credit on another artist's (mostly Kontra K's) production, meaning any vocal chain measured from these files reflects the mixing engineer of the *host* track, not necessarily a chain specific to Bonez MC / RAF Camora / Gzuz.

## Q4 format ceiling

SQL (union of all 10 unique usable ids across the three artists' Step-E sets from Q1: `66340,66815,66855,66903,66934,66946,66980,67000,67031,67233`):
```sql
SELECT id, name, extension, size_bytes, duration_seconds, bpm, key
FROM audio_files WHERE id IN (66340,66815,66855,66903,66934,66946,66980,67000,67031,67233) ORDER BY id;

SELECT extension, COUNT(*), SUM(size_bytes)
FROM audio_files WHERE id IN (...same ids...) GROUP BY extension;
```
Result: `[('mp3', 10, 85251551)]` — **100% of the usable set is MP3.** No wav/flac/aiff/alac present. Combined size 85,251,551 bytes (~81.3 MiB) across 10 files.

Estimated bitrate (size_bytes×8/1000/duration_seconds, computed in Python since the DB has no bitrate column): 9 of 10 files sit at ~320-323 kbps (near-max MP3 CBR/VBR), 1 file (`REALITÄT`, id 66340) at ~192 kbps. `bpm` and `key` are NULL for all 10 rows (never analyzed).

**Ceiling this imposes**: MP3 at 192-320 kbps low-pass filters content above roughly 16-20.5 kHz (LAME encoder cutoff scales with bitrate; 320 kbps ≈ 20.5 kHz cutoff, 192 kbps ≈ ~19 kHz cutoff) and applies lossy frequency-domain quantization throughout the audible band, especially in the pre-masking/post-masking transient regions. This means **no claim can be made about true high-frequency processing** (de-essing thresholds above ~19 kHz, "air band" shelving above 15-16 kHz, exact sibilance content) from this reference set — any measurement of a chain's HF character from these files reflects MP3 encoding artifacts convolved with the original chain, not the original chain alone. Additionally, since every file is a "Feat." credit on someone else's (mostly Kontra K's) mix (see Q3), any chain inferred is that of the host mix engineer, compounding the ceiling: this reference set can at best support coarse/qualitative statements (relative loudness, rough EQ tilt, presence/absence of obvious effects like reverb tails or pitch correction) and cannot support precise chain-replication claims.

## Q5 own dry takes

**This is the binding constraint for the whole exercise: real, plausible dry/unprocessed vocal takes exist, but they belong to unrelated personal/demo projects (ZELDI, GGxMONSTAH, "plakala"/TAMILA) -- none are Bonez MC / RAF Camora / Gzuz material.** Any chain built from Q1-Q4's reference set can only be applied to these takes, never validated against the artists own dry stems (which do not exist on this PC -- see Q1 for why: everything usable is a finished MP3 from someone elses mix).

### Catalogue query (as specified)
```sql
SELECT COUNT(*) FROM audio_files
WHERE present=1 AND file_type='production' AND name LIKE '%term%';
```
| term | count |
|---|---|
| vocal | 137 |
| vox | 19 |
| acapella | 0 |
| dry | 7 |
| raw | 12 |
| take | 98 |
| combined OR (5 terms, excl. acapella) | 273 |

Empty-result check (rule: prove a probe can return non-empty before trusting a zero): name LIKE '%acapella%' with no file_type/present filter returns 16 rows (all file_type='sample', e.g. 303-Lil-Scrappy-Ft_-Lil-Jon-Gangsta-Gangsta-Clean-Acapella-86-Gm_2), so the acapella term itself works -- the file_type='production' AND name LIKE '%acapella%' count of 0 is a genuine finding (no acapella-tagged file in this catalogue is classified as production; they are all in commercial sample packs).

The 273-row combined set is dominated by directories that are not own-dry-take material: 92 rows are Distro Kidea\Old school vox (a commercial vocal-chant sample pack -- checked contents, e.g. "1 1 2 2 3 3 hit it.wav", "1 2 1 2, I am the dominating.wav" -- duplicated at two backup locations), plus various Stems/STEMecci folders (AI-separated stems, not raw takes) and Counter-Strike game sound files (dryfire_pistol.wav etc -- false positives from the word "dry").

### Directories named by the orchestrator
```sql
-- catalogue coverage check
SELECT COUNT(*) FROM audio_files WHERE path LIKE '%music_toolshop_v2%';  -- 0 (control: '%D:\Projects%' -> 8872, proves LIKE works)
SELECT COUNT(*) FROM audio_files WHERE path LIKE '%Music-AI-Toolshop%';  -- 8412
SELECT COUNT(*) FROM audio_files WHERE path LIKE '%vocal_swap%';        -- 0
```
D:\Projects\music_toolshop_v2 is entirely unindexed in tracks.db (0 of 106,502 rows) and the Music-AI-Toolshop\data\toolshop\vocal_swap folder is unindexed too, even though the parent Music-AI-Toolshop tree has 8,412 indexed rows -- the catalogue has a coverage gap for these two specific paths. This agent therefore inspected them directly on disk (find, os.stat, and RIFF-header parsing -- file size/format/duration only, no audio decoded or played) rather than relying on the DB. Separately, the DB is also stale for parts of D:\Projects it does claim to cover: D:\Projects\Mastering_Toolshop no longer exists on disk at all (verified: find returns "No such file or directory") yet the catalogue still lists about 5 files there as present=1; likewise D:\Projects\Music-AI-Toolshop\Stemmeca_alatkka (33 catalogued rows, all present=1) no longer exists -- the real content is at D:\Projects\Music-AI-Toolshop\data\toolshop\Stemmeca_alatkka (verified identical filenames/sizes by direct listing). Do not trust present=1 alone for paths under D:\Projects; this agent cross-checked every load-bearing candidate below directly on disk.

### Candidates found by direct filesystem inspection

| # | Path | Format (RIFF header, no decode) | Duration | Assessment |
|---|---|---|---|---|
| 1 | D:\Projects\music_toolshop_v2\data\ZELDI x ZA OVAJ GRAD\record 1 Project\Samples\Recorded\Main Vokal 000N [timestamp].wav (39 files) | 32-bit float PCM, 44.1kHz, mono | 1.05s-166.07s each; total 893.8s (14.9 min), dominated by 2 full-length takes (163.91s, 166.07s) plus 37 short comp/punch-in takes | Best candidate: genuine DRY unprocessed take. Ableton Lives default "Samples\Recorded" location plus the [YYYY-MM-DD HHMMSS] naming plus 32-bit float mono is exactly what a live vocal recording produces before any bounce/processing. Recorded 2026-08-26 (1 week before today, 2026-09-02) -- most recent of the three projects found. An .als Ableton project (record 1 [2026-08-26 231038].als) and a rendered instrumental (G-Funk - Zeldi (Without Lead Vocal).wav) sit alongside it, confirming this is a real, current in-progress song. Also has stems\ZELDI - ZA OVAJ GRAD - vocals.wav (Demucs-style separated stem, NOT dry -- do not confuse with the Recorded takes). |
| 2 | D:\2026\GGxMONSTAH Project\Samples\Recorded\Main Vokal 000N [timestamp].wav (9 files, 2026-05-06) | not re-parsed individually (same pattern confirmed via directory listing) | not measured (out of scope once #3 below covers the same session) | Same Ableton raw-take pattern as #1, older session (about 4 months earlier). |
| 3 | D:\2026\GGxMONSTAH Project\GGxMONSTAH_MIXREADY_mono_dry.wav | PCM (not float), 24-bit, 44.1kHz, mono | 156.73s | Strong candidate: consolidated/comped dry take, explicitly labeled "MIXREADY dry". This is a bounced, edited-down single dry vocal (not raw multi-take snippets) -- ideal shape for chain application. Sibling files in the same folder show the full pipeline: GGxMONSTAH vokals.wav (32-bit float stereo, same 156.73s -- pre-bounce), GGxMONSTAH_FX_reverb_wet.wav (wet/processed comparison), GGxMONSTAH_MASTERED_stereo.wav (final master), GGxMONSTAH_PREVIEW_with_pinknoise.wav. Catalogue also lists a duplicate at D:\Projects\Mastering_Toolshop\GGxMONSTAH_MIXREADY_mono_dry.wav and ..._stereo_dry.wav, but that directory no longer exists on disk (verified) -- use the D:\2026\GGxMONSTAH Project copy. |
| 4 | D:\TAMILA\Project_1 plakala dry 030325\Project_1 plakala dry vokal 104.wav | 32-bit float, 44.1kHz, stereo | 243.85s | Plausible dry take -- explicitly named "dry vokal", 104 bpm, consolidated from 23 raw punch-in files in the sibling Audio folder (untitled_2025-03-03 HH-MM-SS_Insert 9.wav, same Ableton-recording pattern, dated 2025-03-03 -- older, about 18 months before today). Near-duplicate plakala t1v1.wav (243.73s) in the same folder is very likely an earlier comp/version of the same take. |
| 5 | D:\TAMILA\bgb040125 vokal.wav | not re-verified via header (catalogue duration used) | 153.32s (matches bgb040125.mp3 / bgb040125 V2.mp3 at 154.2-154.3s almost exactly) | Ambiguous -- duration essentially equals the finished mixs duration, which is consistent with either (a) the original tracked dry vocal that the mix was built from, or (b) a vocal stem extracted post-hoc from the finished mix. Cannot distinguish without listening (out of scope/prohibited here). Treat as unverified. |
| 6 | D:\Projects\Music-AI-Toolshop\data\toolshop\vocal_swap\_inputs\ZELDI_vocals_trimmed_to_nova.wav | PCM, 16-bit, 44.1kHz, stereo | 183.76s | Likely already-processed, not dry -- 16-bit stereo export (vs the 32-bit float mono of genuine raw takes above) and the filename ("_trimmed_to_nova") implies it was prepared as an input for a voice-conversion/swap tool, i.e. downstream of whatever vocal chain already exists on it. Lives in this projects own vocal_swap/_inputs folder -- relevant to know about, but not a "dry" reference. |
| 7 | D:\Projects\music_toolshop_v2\data\PE3 BAZOOKA MIX MIXALL ( ZA POPA) -vocal.wav | 32-bit float, 44.1kHz, stereo | 225.88s | Filename ("MIX MIXALL") implies this is a vocal already carrying mix processing, not dry. Unverified without listening. |
| 8 | D:\Projects\music_toolshop_v2\data\Na tebe sam bebo slaeb\vokali 1 na tebe sam bebo slab - vocal.mp3 | mp3 (lossy) | not parsed (mp3) | Lossy-compressed exported vocal alongside a finished "... - MixAll.mp3" in the same folder -- almost certainly an already-mixed/exported vocal, not a dry take. |

### Bottom line for Q5
The best usable dry-take candidates are #1 (ZELDI Main Vokal raw multi-takes, most recent, mono 32-bit float, about 14.9 min total across 39 files including two approximately 2:44 full performances) and #3 (GGxMONSTAH_MIXREADY_mono_dry.wav, a clean single consolidated dry take, 156.73s, 24-bit mono). #4 (plakala dry vokal 104, 243.85s stereo) is a third, older, plausible option. **None of these are Bonez MC / RAF Camora / Gzuz vocals** -- they are the users own (or a collaborators) home-recorded takes for unrelated songs (ZELDI, GGxMONSTAH, "plakala"). This confirms the orchestrators framing: a chain measured from the Q1-Q4 reference set (mostly other artists MP3 mixes featuring these three artists) would have to be applied to one of these dry takes to be useful -- there is no way to derive a chain from the target artists own isolated vocals, because no such isolated vocals exist on this PC.

## Q6 footprint

SQL:
```sql
SELECT SUM(duration_seconds), COUNT(*) FROM audio_files
WHERE id IN (66340,66815,66855,66903,66934,66946,66980,67233,67000,67031);
```
Result: `count=10, total_duration_seconds=2255.83` (**37.6 minutes**) -- this is the union of the three artists' Step-E usable sets from Q1 (10 unique files after removing the 2 files shared between Bonez MC and RAF Camora: `07. Gut Böse (Feat. Bonez MC, Nizi & Raf Camora)` and `07. Plem Plem (Feat. Raf Camora & Bonez MC)`).

Per-artist breakdown:
| Artist | usable files | total duration |
|---|---|---|
| Bonez MC | 8 | 1832.2s (30.5 min) |
| RAF Camora | 5 | 1243.8s (20.7 min) |
| Gzuz | 0 | 0s |

No separation was run to produce this number -- it is a straight `SUM(duration_seconds)` over the catalogue's already-stored metadata for the 10 file ids identified in Q1. No audio was decoded, played, or processed by this agent at any point in this census.

**Compute note (not a benchmark, just context for whoever plans the next step):** the orchestrator's brief states Demucs on this machine is CPU-only. 37.6 minutes of source material, if it were ever run through source separation, is a small-to-moderate CPU-Demucs job (typically several-times-realtime on CPU, i.e., on the order of tens of minutes to a few hours depending on model/settings) -- but this agent did not benchmark or run anything; this is stated only so the next wave can size the job before starting it, not as a recommendation to do so.

## Uncertainties

1. **Catalogue staleness under `D:\Projects`**: confirmed two cases where `present=1` rows point at files/directories that no longer exist (`D:\Projects\Mastering_Toolshop` entirely gone; `D:\Projects\Music-AI-Toolshop\Stemmeca_alatkka\...` gone, content moved to `...\data	oolshop\Stemmeca_alatkka\...`). The catalogue also has zero coverage of `D:\Projects\music_toolshop_v2` and `...\Music-AI-Toolshop\data	oolshopocal_swap`. This means any count in this report that relies on the DB's `present` flag for paths under `D:\Projects` (essentially all of Q1-Q4, and the catalogue-query half of Q5) should be treated as a lower/rough bound for that tree specifically, not a guarantee of current existence -- a fresh `sync.py` run would be needed to confirm. Paths outside `D:\Projects` (the bulk of Q1-Q4's actual hits, e.g. `D:\Kontra K\...`, `D:\SAMPLOVI ZA MATRE\...`, `D:\INSTRUMENTALI\...`) were not found to be stale in this agent's spot checks, but were not exhaustively re-verified file-by-file.

2. **Gzuz usable count of 0 may be an undercount, not a true zero.** The two Gzuz candidates that survive Step C2 both have `duration_seconds IS NULL` (never analyzed), not `duration_seconds < 60`. One of them, `GZUZ - KEINER KANN MICH FICKEN!.mp3` (5.7MB, `D:\DESKTOP2026\KHANS\`), reads as a plausible Gzuz-primary track by filename alone. This agent did not run any duration/BPM analysis (out of scope, no audio touched), so this cannot be resolved without either running the catalogue's own `analyze.py` (a separate, larger operation outside this agent's remit) or a metadata-only header parse (which this agent already demonstrated is safe and did for other files in Q5 -- could be repeated here in a follow-up if useful).

3. **Q3 classifier is a name-pattern heuristic**, not semantic understanding -- it was validated against 2 control cases (see Q3) but was not run against the full 106,502-row table, only the small per-artist Step-C2 sets, so its edge-case behavior on more unusual naming (e.g., "feat" spelled out without punctuation, non-English feature markers) is unverified beyond what appeared in these particular ~10-27 row sets.

4. **The RAF Camora `solo_or_primary` correction (19 -> 1 real track)** relied on manually recognizing the `D:\SAMPLOVI ZA MATRE\Raf Camora Drum Kit\` directory as a producer sample pack by inspecting file names and the `file_type` column; this agent did not verify licensing/provenance of that pack, only that it is clearly not RAF Camora's own vocal/song material.

5. **Bitrate estimates in Q4** were computed by this agent from `size_bytes` and `duration_seconds` (simple division), not read from any embedded bitrate/ID3 metadata field -- the catalogue schema has no bitrate column. This is an approximation (assumes near-constant bitrate and ignores container/ID3 overhead, which is small relative to file size here) rather than an authoritative reading.

6. **Q5 file #5 (`bgb040125 vokal.wav`) and #6-#8 remain genuinely ambiguous** (dry vs. already-processed) -- this agent deliberately did not decode or listen to any audio to resolve them, per the read-only/no-audio-touch instruction, so these are flagged as open questions for whichever downstream step needs a definitive dry/wet classification.

7. **Duplicate copies not fully deduplicated across drives**: e.g. the ZELDI project's raw takes were found only via direct filesystem inspection (catalogue has zero rows for that tree), so this agent cannot rule out additional copies of the same "Main Vokal" session existing elsewhere on the PC outside the three directories the orchestrator named -- only those three plus the two catalogue-derived leads (TAMILA, GGxMONSTAH via `D:6\`) were checked.
