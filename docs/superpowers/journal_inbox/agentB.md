# Journal fragment — Wave 1 Agent B (M6 / dossier schema v2 design)

> Reserved range `J-020`–`J-029`. Merge into `../JOURNAL.md`, then delete this file.
> Written 2026-09-01. All evidence first-hand unless tagged.

### J-020 — The "444-dossier corpus" does not exist; it is 222, double-counted by a glob · 2026-09-01 · M6
**Status:** refuted — **first-hand, this session**
**Expected:** 444 dossiers, per `HANDOFF-2026-08-31.md:165`, `plans/2026-09-01-next-moves.md:44`,
`STATUS.md:30` and `CHANGELOG.md:263`. The handoff states it as measured: *"444 dossiers with live
source audio … (The roadmap says '222'; the real count including PapaPedro is 444.)"*
**Found:** there are **222** track dossiers, all in `results/crhymetv_re/per_track/`. The 444 is the
count of files matching `*_analysis.json`, which also matches the **`_voice_analysis.json` sidecar**
written next to each dossier. 222 dossiers + 221 voice sidecars + 1 duplicate voice sidecar under
`diagnose_voice/` = exactly 444. **PapaPedro contributes nothing** — it has 687 source mp3s and only
3 analysed directories, none of them dossiers (`results/papapedro_re/per_beat/`, per-beat output).
**Evidence:** first-hand.
```
$ find results/crhymetv_re -name "*_analysis.json" | wc -l
444
$ find results/crhymetv_re/per_track -name "*_analysis.json" -not -name "*_voice_analysis.json" | wc -l
222
$ find results/crhymetv_re/per_track -name "*_voice_analysis.json" | wc -l
221
$ ls results/crhymetv_re/diagnose_voice
2010-12-08 - Sa4 - Täterprofil [eryRCHmXItY]_voice_analysis.json
$ ls results/crhymetv_re/per_track | wc -l
222
$ ls "D:/Projects/Tools/yt_extractor/downloads/PapaPedro Beats" | wc -l   # 687 .mp3
$ ls results/papapedro_re/per_beat | wc -l
3
```
**Consequence:** M6's scope halves. The regeneration target is **222 tracks**, and the count
verification must assert 222 → 222, not 444 → 444. Written into
`specs/2026-09-01-dossier-schema-v2.md`. **The generalisable lesson is the glob:** `*_analysis.json`
is a suffix, and `_voice_analysis.json` ends with it. Any corpus count must be re-derivable from a
`--not-name` exclusion or from the batch status file, never from a bare suffix glob.

### J-021 — The 28.3 h / ~25 h CPU estimate inherits the same double count, to 3 significant figures · 2026-09-01 · M6
**Status:** refuted — **first-hand, this session**
**Expected:** 28.3 h of audio ⇒ ~25 h CPU at RTF ~1.13 (`STATUS.md:30`, `CHANGELOG.md:263`,
`plans/2026-09-01-next-moves.md:42`).
**Found:** the real audio is **13.58 h** for the 221 completed tracks. Doubling it and adding the one
track that has no voice sidecar reproduces the published figure **exactly**:
`2 × 13.5839 h + 4062 s = 28.2961 h ≈ "28.3 h"`. The single-count total is **14.71 h**, so
transcription at RTF 1.13 is **~16.6 h**, not ~25 h — and ~15.4 h if the 67.7-minute documentary is
excluded, which it should be.
**Evidence:** first-hand, summing `duration_seconds` over `results/crhymetv_re/catalogue.csv`
(221 rows) and reading the skipped track's duration from `batch_status.json`:
```
221 completed = 48902.0 s = 13.5839 h
double-count model: 2*48902 + 4062 = 28.2961 h   <- matches published 28.3
single-count model:   48902 + 4062 = 14.7122 h
RTF 1.13 on single-count -> 16.62 h CPU
```
**Consequence:** the cost line in the M6 spec is stated as **~16.6 h transcription**, derived
first-hand, with the ~25 h relayed figure tagged `unverified — source: docs/superpowers/STATUS.md`
and marked superseded. A weekend slot is no longer required; a single overnight covers it.

### J-022 — `batch_status.json` and the filesystem disagree; the status file is not authoritative · 2026-09-01 · M6
**Status:** verified — **first-hand, this session**
**Expected:** the resumable batch's status JSON is the record of what was produced, so a
skip-completed resume and a count check can both read it.
**Found:** the one non-completed track — `2023_02_07_Komm_wir_schreiben_Geschichte_Dokumenta_BKGeueSkWXQ`,
a 4062 s (67.7 min) documentary — is recorded as `"status": "skipped_long"` with
`"analysis_json": null`. **An `_analysis.json` exists on disk for it anyway**, 464 bytes, from an
earlier run under an older schema. So a resume driven by the status file would re-analyse a track
that has output, and a count driven by the filesystem would count a track the status file says was
skipped. The two disagree by one, in opposite directions.
**Evidence:** first-hand.
```
$ python - <<'PY'   # batch_status.json
Counter({'completed': 221, 'skipped_long': 1});  errors: 0;  total_tracks: 222
skipped record: analysis_json=null, voice_json=null, stems=null, recipe_md=null
PY
$ ls "results/crhymetv_re/per_track/2023_02_07_Komm_wir_schreiben_Geschichte_Dokumenta_BKGeueSkWXQ/"
2023-02-07 - ,,Komm, wir schreiben Geschichte＂ ... [BKGeueSkWXQ]_analysis.json   # 464 bytes
stems
```
Also: `catalogue.csv` has **221** rows against **222** per_track directories — a third count that
disagrees with both.
**Consequence:** the M6 count verification is specified to reconcile **three** sources (input
enumeration, status JSON, filesystem) and to fail loudly on any pairwise disagreement, rather than
trusting one. This is the concrete instance of the failure mode `next-moves.md` names — *"a batch
that succeeds having skipped half its input"* — already present in the corpus at n=1.

### J-023 — The corpus holds two v1 schema variants, not one · 2026-09-01 · M6
**Status:** verified — **first-hand, this session**
**Expected:** one legacy dossier shape to migrate from.
**Found:** exactly two, and they differ by seven optional field groups, not by version. The 221
normal dossiers have **18** keys (`analysis_backend: "wav_reverse_engineer"`) and add `tuning_offset`,
`onset_strength`, `effects`, `instruments`, `chord_progression`, `notes`, `separation` on top of an
11-key core. The skipped documentary's 464-byte file has only that 11-key core
(`analysis_backend: "basic_librosa"`). **Neither carries a version marker of any kind** — the only
discriminator available at read time is `analysis_backend`, which describes the *engine*, not the
*schema*, and would become ambiguous the moment a v2 file used the same engine.
**Evidence:** first-hand, key-set census over all 222 dossiers — 2 distinct key-sets, sizes 18 (×221)
and 11 (×1); full listing in J-026 and in the spec's §Schema v1 As-Is.
**Consequence:** v1 detection in the spec is by **absence of the `schema_version` key**, which is
sound precisely because no existing file has one; and the optional field groups are carried through
the migration as-is rather than being treated as required, since 1 of 222 files legitimately lacks
all seven.

### J-024 — The four "real" dossier fields are emitted only by the *fallback* backend; the default emits none of them · 2026-09-01 · M6
**Status:** verified — **first-hand, this session. This is the finding that resizes M6.**
**Expected:** M1–M4 made `key`/`mode`, `structure`, `beat_grid` and `premaster` real in the dossier,
so regenerating the corpus with the current code would produce them (`STATUS.md` H2-M4: *"Dossier now
carries four real fields"*).
**Found:** `toolshop/reverse_engineering_adapter.py` has **two** emitters and the new fields are in
the wrong one.
- `_basic_analysis` (`analysis_backend: "basic_librosa"`) emits `beat_grid`, `structure`,
  `premaster`, and K-S `key`/`mode`/`key_confidence`/`key_alternate`/`key_margin` —
  `reverse_engineering_adapter.py:116-134`.
- `_advanced_analysis` (`analysis_backend: "wav_reverse_engineer"`) emits **none** of them and takes
  `key`/`mode` straight from the external package — `reverse_engineering_adapter.py:158-159`.
- `analyze_track` prefers advanced whenever it imports (`:246`, `use_advanced = _WAV_RE_AVAILABLE and
  backend != "basic"`), the CLI defaults `--backend advanced` (`cli.py:300-303`), and the corpus batch
  **hard-codes** `backend="advanced"` (`run_reverse_engineering_batch.py:215`).

Corpus census agrees: **221 of 222 dossiers are `wav_reverse_engineer`**, 1 is `basic_librosa` — and
that one is the 464-byte skipped-documentary file, i.e. the fallback ran there by accident.
**Evidence:** first-hand; `file:line` above, plus a census of `analysis_backend` over all 222
dossiers: `{'wav_reverse_engineer': 221, 'basic_librosa': 1}`.
**Consequence:** **M6 cannot be a re-run of the existing pipeline.** Running the batch as-is over the
corpus would reproduce the same v1 dossier with new timestamps and zero new fields. The spec's
migration therefore has a prerequisite that the plan did not name: either port the four field groups
into `_advanced_analysis`, or have the migration compute them itself and merge. Recorded as **Open
Question 1** in `specs/2026-09-01-dossier-schema-v2.md`.

### J-025 — The H2-M1 key fix never reached the dossier's default path; the loudness-threshold `mode` is still live code · 2026-09-01 · M6
**Status:** verified — **first-hand, this session. Qualifies the "all four share one detector" claim.**
**Expected:** `STATUS.md` H2-M1: *"FOUR implementations, not two … All four now share one detector."*
**Found:** the implementation actually used for every corpus dossier was not among the four that were
fixed. `_advanced_analysis` calls `FeatureExtractor.extract_features`, whose `_estimate_key` still
reads, at
`projects/05-track-reverse-engineering/track_reverse_engineering/wav_reverse_engineer/audio_analyzer/feature_extractor.py:185-190`:

    key_idx = np.argmax(chroma_vals)
    ...
    mode = 'major' if chroma_vals[key_idx] > 0.5 else 'minor'

That is the exact defect H2-M1 was raised to remove — tonic by loudest chroma bin, mode by a
magnitude threshold — and it is still the code path the dossier uses by default.
**Evidence:** first-hand, `file:line` above. Corpus-scale confirmation, stronger than the 7-of-8
sample the milestone was written from: over all 222 dossiers, **`mode` is `major` on 215 and `minor`
on 7 — 96.8% major** on a German rap/hip-hop catalogue (all 221 catalogue rows describe the material
as "German rap / hip-hop"). The 7 "minor" tracks are the ones whose loudest chroma bin happened to
fall below 0.5.
**Consequence:** the `mode` collision in schema v2 is not a naming problem, it is a **live defect**.
The spec resolves it by preserving the old value under `legacy_mode_loudness_threshold` with an
explicit provenance tag, never by reinterpreting it in place. Downstream artefacts already built on
it — `catalogue.csv` (`key`,`mode` columns), `recipe.md`, `suno_prompts.md` — are wrong for the same
reason and must be regenerated after the migration.

### J-026 — `sections` is not `[]` in the corpus; it is absent, and there are only two v1 key-sets · 2026-09-01 · M6
**Status:** refuted — **first-hand, this session**
**Expected:** *"the `sections` that were always `[]`"* — `plans/2026-09-01-next-moves.md:45`,
`HANDOFF-2026-08-31.md:169`, and the task framing "distinguish analysed-but-empty from never-analysed".
**Found:** **no dossier in the corpus has a `sections` key at all.** A census of every key in all 222
dossiers returns exactly two key-sets, 18 keys and 11 keys, and `sections` is in neither:

    sections: {'<MISSING>': 222}
    distinct key-sets: 2
      221 x 18 keys: analysis_backend, beat_count, bpm, chord_progression, duration_seconds,
                     effects, file, harmonic_ratio, instruments, key, mode, notes,
                     onset_strength, sample_rate, separation, spectral_bandwidth,
                     spectral_centroid, tuning_offset
        1 x 11 keys: analysis_backend, beat_count, bpm, duration_seconds, file, harmonic_ratio,
                     key, mode, sample_rate, spectral_bandwidth, spectral_centroid

The `[]` was real in the *code* — `librosa.segment.agglomerative(chroma, k=None)` raising into a bare
`except Exception: return []`, per #048 — but that dead segmenter lived on a path the corpus batch
never took (see J-024), so the empty list was never even serialised.
**Evidence:** first-hand, census over `results/crhymetv_re/per_track/*/*_analysis.json` (222 files,
0 unreadable).
**Consequence:** the ambiguity to design against is **three**-valued, not two: *key absent* (never
analysed), *`[]`* (the historical failure signature, present in no file but reachable from older
code), and *populated*. The spec makes v2 carry `structure.status` in
`{analysed, none_detected, not_attempted, failed}` with a `reason`, so an empty `segments` list is
never load-bearing on its own.

### J-027 — `find_vocal_stem` cannot see the corpus stems; and only 140 of 222 tracks have any · 2026-09-01 · M6
**Status:** verified — **first-hand, this session**
**Expected:** the M5 transcriber would find each corpus track's vocal stem, since the corpus has stems.
**Found:** it returns `None` for every corpus track under default search. `find_vocal_stem`
(`toolshop/transcribe.py:292-337`) searches the audio file's own parent, sibling `*stem*`
directories, and `paths.subdir("stems")`. The corpus audio lives at
`D:\Projects\Tools\yt_extractor\downloads\CrhymeTV\`; its stems live under
`results/crhymetv_re/per_track/<slug>/stems/` — not a sibling, and `data/toolshop/stems` contains
only `karaoke/`. Passing `search_dirs` explicitly works.
**Evidence:** first-hand, run in the venv:

    src exists: True
    default search  -> None
    explicit search -> ...\per_track\2010_12_08_Sa4_T_terprofil_eryRCHmXItY\stems\
                       2010-12-08 - Sa4 - Täterprofil [eryRCHmXItY]_(Vocals)_UVR-MDX-NET-Voc_FT.wav

Separately, a stem census: **140 tracks have a non-empty `stems/` with a vocal file, 81 have no
`stems/` directory, 1 has an empty one** — so 82 of 222 have no stem to transcribe from and would
silently fall back to the full mix. (This matches AGENTS.md's "140/222 with stems" — first-hand
confirmation of a previously relayed number.)
**Consequence:** the migration must pass `search_dirs=[<per_track>/<slug>/stems]` explicitly, and
must record `lyrics.source` (`vocal_stem` | `full_mix`) per track — the corpus will be **mixed
provenance**, which makes any corpus-level coverage statistic uninterpretable unless split by source.
`--require-stem` would refuse 82 tracks rather than degrade them, which is the honest default for a
sample run and the wrong one for the full corpus.

### J-028 — The transcriber's default language is `sr`; the corpus is German · 2026-09-01 · M6
**Status:** verified — **first-hand, this session**
**Expected:** decode settings measured in M5 would carry over to the corpus run unchanged.
**Found:** `DEFAULT_LANGUAGE: Optional[str] = "sr"` (`toolshop/transcribe.py:97`), chosen because
auto-detect picked `"hr" at p=0.31` on *Serbian* material — the user's own tracks. The regeneration
corpus is **CrhymeTV, German rap**: all 221 catalogue rows carry `German rap / hip-hop` in
`suno_prompt`, and the artists are Sa4, 129ers, Capuz. Running the corpus at the module default would
force Serbian decoding on 222 German tracks. `DEFAULT_MODEL` is also `"small"` (`transcribe.py:89`),
while the ~25 h / RTF 1.13 figure was measured on `large-v3` — a second default that does not match
the plan's own cost basis.
**Evidence:** first-hand — `transcribe.py:89` and `:97`, and a count over `catalogue.csv`:
`sum('German' in r['suno_prompt']) = 221 / 221`.
**Consequence:** the spec pins `language="de"` and `model="large-v3"` for this corpus **explicitly in
the migration's recorded `decode_settings`**, not as a module default change, and makes the sample
protocol's stop-criteria include a language-probability floor. The generalisable point:
`decode_settings` being recorded per track (M5's own design) is what makes this catchable at all —
but only if someone reads them, so the count-verification report prints the distinct
`decode_settings` seen across the run.

### J-029 — `run_batch`'s `total_tracks` is rewritten by any `--limit` run, so a 20-track sample corrupts the corpus status file · 2026-09-01 · M6
**Status:** verified — **first-hand, this session**
**Expected:** `--limit` is a safe way to run a sample against the same output directory before
committing to the full corpus, since resume is keyed by source path.
**Found:** `discover_files` applies `limit`/`offset` *before* `run_batch` sees the list
(`toolshop/batch.py:54-65`), `run_batch` sets `total = len(files)` (`:129`), and
`load_or_create_status` unconditionally overwrites the stored value with it:
`status["total_tracks"] = total` (`:77`). A `--limit 20` run against an existing
`batch_status.json` therefore rewrites `total_tracks` from 222 to **20**, destroying the very number
a count check would compare against. Two further sharp edges in the same function: `--offset` shifts
the *display* index only (`run_batch(offset=...)`, `:141`), so the slice actually processed is
recorded nowhere; and `status["last_completed_index"] = idx` is set on the **failure** path too
(`:170-176`), so the name is wrong whenever anything fails.
**Evidence:** first-hand, `file:line` above in `toolshop/batch.py`.
**Consequence:** the spec requires the sample run to use a **separate status path and output root**,
never the corpus one, and specifies that the count verification derive its expected total by
**re-enumerating the input directory**, never by reading `total_tracks` from the status file.
