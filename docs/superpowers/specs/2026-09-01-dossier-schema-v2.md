# Spec — Dossier schema v2 and the corpus migration (M6)

> Design only. Written 2026-09-01 by Wave 1 Agent B. **No code was written or run against the corpus.**
> Every number below is either first-hand (a command run this session, quoted) or tagged
> `unverified — source: <path>` per AGENTS.md.
>
> Companion findings: `docs/superpowers/journal_inbox/agentB.md`, entries `J-020`–`J-029`.

---

## 0. The headline, before the detail

Three things the plan assumed are not true, and each changes the design:

| Assumption | Reality (first-hand) | Effect on M6 |
|---|---|---|
| 444 dossiers | **222** — the 444 counted `_voice_analysis.json` sidecars too (J-020) | scope halves |
| ~25 h CPU for 28.3 h of audio | **14.71 h** of audio, **~13 h** transcription (J-021) | overnight, not a weekend |
| M1–M4 made the fields real; just re-run | the new fields live in the **fallback** backend only; the corpus batch hard-codes the **other** one (J-024) | **a plain re-run adds nothing** |

The third is the one that would have burned the weekend. Running the existing batch over the corpus
today reproduces the same v1 dossier with newer timestamps and zero new fields.

---

## 1. Corpus Inventory

### 1.1 What was actually found

All dossiers live in **one** place: `D:\Projects\Music-AI-Toolshop\results\crhymetv_re\per_track\`,
one directory per track.

```
$ ls results/crhymetv_re/per_track | wc -l
222
$ find results/crhymetv_re/per_track -name "*_analysis.json" -not -name "*_voice_analysis.json" | wc -l
222
$ find results/crhymetv_re/per_track -name "*_voice_analysis.json" | wc -l
221
$ find results/crhymetv_re -name "*_analysis.json" | wc -l
444          <-- the published figure; it is dossiers + voice sidecars + 1 diagnostic copy
```

**The corpus is 222 dossiers.** The `444` in `HANDOFF-2026-08-31.md:165`,
`plans/2026-09-01-next-moves.md:44`, `STATUS.md:30` and `CHANGELOG.md:263` is a glob artefact:
`*_analysis.json` is a suffix and `_voice_analysis.json` ends with it. 222 + 221 + 1 (a duplicate
under `crhymetv_re/diagnose_voice/`) = 444 exactly.

`results/papapedro_re/` contributes nothing — it holds **3** per-beat directories against 687 source
mp3s, and its output is per-beat, not dossiers. The handoff's "the real count including PapaPedro is
444" does not survive contact with the directory.

### 1.2 Three counts that disagree

| Source | Count | What it means |
|---|---|---|
| `per_track/` directories | **222** | every input got a directory |
| `_analysis.json` files | **222** | every directory got a dossier |
| `_voice_analysis.json` files | **221** | one track has no voice sidecar |
| `catalogue.csv` rows | **221** | the catalogue skipped that same track |
| `batch_status.json` `total_tracks` | **222** | `completed: 221`, `skipped_long: 1`, `errors: 0` |

The odd one out is `2023_02_07_Komm_wir_schreiben_Geschichte_Dokumenta_BKGeueSkWXQ` — a **4062 s
(67.7 min) documentary**. `batch_status.json` records it `"status": "skipped_long"` with
`"analysis_json": null`, **and an `_analysis.json` exists on disk for it anyway** (464 bytes, from an
earlier run under a different backend). The status file and the filesystem disagree by one, in
opposite directions (J-022).

This is not a curiosity. It is the failure mode `next-moves.md` names — *"a batch that succeeds
having skipped half its input"* — already present at n=1, and it is why §7 reconciles three
independent enumerations rather than trusting any one.

### 1.3 Corpus shape (first-hand, from `catalogue.csv` + a filesystem census)

| Property | Value |
|---|---|
| Tracks | 222 (221 analysed + 1 skipped documentary) |
| Audio, 221 analysed | **48 902 s = 13.58 h**; mean 3.69 min |
| Audio, incl. documentary | **14.71 h** |
| Duration range | 7.3 s → 1632 s (27 min); 6 tracks < 60 s, 8 tracks > 8 min |
| Tracks with a usable vocal stem | **140** (81 have no `stems/` dir, 1 has an empty one) |
| Non-ASCII source filenames | **53** — incl. `⚽️`, `：`, `？`, `FR€€$T¥L£`, `IŞ` |
| Non-song items (blog/vlog/trailer/snippet/doku by slug) | **33** of 221, **3.7 h** |
| Language | German rap/hip-hop — 221/221 catalogue rows say so |
| `mode` distribution | **`major` 215 / `minor` 7** (96.8% major) |
| `analysis_backend` | `wav_reverse_engineer` 221 / `basic_librosa` 1 |
| Dossiers with a `sections` key | **0** |
| Dossiers with a `schema_version` key | **0** |

---

## 2. Schema v1 As-Is

A key-set census over all 222 files returns **exactly two shapes**, and no version marker in either.

**Shape A — 221 files, 18 keys, `analysis_backend: "wav_reverse_engineer"`**

```
file, duration_seconds, sample_rate, bpm, beat_count, key, mode,
spectral_centroid, spectral_bandwidth, harmonic_ratio, tuning_offset, onset_strength,
analysis_backend,
effects{rt60_seconds, spectral_tilt_db_per_decade, thd_ratio, compression_index,
        loudness_lufs, loudness_range},
instruments[{label, score}],
chord_progression[{name, start_time, duration, end_time, confidence}],
notes[{pitch, frequency, start_time, duration, confidence}],
separation{method, stems[]}
```

**Shape B — 1 file, 11 keys, `analysis_backend: "basic_librosa"`** — shape A minus
`tuning_offset`, `onset_strength`, `effects`, `instruments`, `chord_progression`, `notes`,
`separation`. This is the skipped documentary; the fallback backend ran there by accident.

Emitters: `toolshop/reverse_engineering_adapter.py:152-210` (`_advanced_analysis`, shape A) and
`:116-134` (`_basic_analysis`, shape B's superset today).

### 2.1 Four facts about v1 that the migration must design around

**(a) There is no version marker.** The only discriminator is `analysis_backend`, which names the
*engine*, not the *schema*, and would become ambiguous the instant a v2 file used the same engine.
So: **a v1 dossier is recognised at read time by the absence of the `schema_version` key.** This is
sound precisely because a census proved no existing file has one.

**(b) `sections` is absent, not empty** (J-026). The `[]` described in `#048` and repeated through
the plan was real in *code* — `librosa.segment.agglomerative(chroma, k=None)` raising into a bare
`except Exception: return []` — but that dead segmenter sat on `_basic_analysis`, a path the corpus
batch never took. The empty list was never serialised. See §5.

**(c) `key`/`mode` come from a still-live defect** (J-025). `_advanced_analysis` does not use
`toolshop/key_detection.py`. It reads `features["key"]`/`features["mode"]` from
`FeatureExtractor.extract_features`, whose `_estimate_key` is, at
`projects/05-track-reverse-engineering/track_reverse_engineering/wav_reverse_engineer/audio_analyzer/feature_extractor.py:185-190`:

```python
key_idx = np.argmax(chroma_vals)
...
mode = 'major' if chroma_vals[key_idx] > 0.5 else 'minor'
```

Tonic by loudest chroma bin; mode by a magnitude threshold. `STATUS.md` H2-M1 states *"All four now
share one detector"* — the implementation the dossier actually uses was not among the four. The
corpus proves it at scale: **215 major / 7 minor**. See §4.

**(d) None of the four M1–M4 fields can be produced by the current default path** (J-024).
`beat_grid`, `structure`, `premaster` and the K-S key block exist only in `_basic_analysis`.
`analyze_track` prefers advanced whenever `wav_reverse_engineer` imports
(`reverse_engineering_adapter.py:246`), the CLI defaults `--backend advanced` (`cli.py:300-303`), and
`run_reverse_engineering_batch.py:215` **hard-codes** `backend="advanced"`. This is Open Question 1.

---

## 3. Schema v2 Field by Field

**Design rule: v2 is additive at the top level.** Every v1 key keeps its name, position and meaning
(except `mode` — §4), because `generate_crhymetv_catalogue.py:234`,
`run_reverse_engineering_batch.py:126,171`, `toolshop/bpm_adapter.py:96` and `toolshop/cli.py:1570`
all read the flat keys. Breaking them buys nothing M6 needs.

### 3.1 Envelope (new, required)

| Field | Type | Notes |
|---|---|---|
| `schema_version` | int, `2` | **The discriminator.** Absent ⇒ v1. Required in every v2 file. |
| `generated_at` | ISO-8601 str | |
| `generator` | obj | `{toolshop_commit, adapter, python, librosa, numpy, wav_reverse_engineer}` — a corpus diff is uninterpretable without knowing what produced each side. |
| `source` | obj | `{path, bytes, mtime, sha256}`. `sha256` of the **input audio**, so a later diff can tell "the analysis changed" from "the file changed". |
| `stages` | obj | `{<stage>: {status, reason, elapsed_seconds}}` for `key`, `beat_grid`, `structure`, `premaster`, `lyrics`. Per-stage status is what makes staged resume possible (§6.3). |

### 3.2 Carried through unchanged

`file`, `duration_seconds`, `sample_rate`, `bpm`, `beat_count`, `spectral_centroid`,
`spectral_bandwidth`, `harmonic_ratio`, `tuning_offset`, `onset_strength`, `analysis_backend`,
`effects`, `instruments`, `chord_progression`, `notes`, `separation`.

Shape B lacks the last seven. They stay **optional** in v2 — 1 of 222 files legitimately has none,
and making them required would fail that track for the wrong reason.

### 3.3 `key` / `mode` — Krumhansl-Schmuckler (M1)

| Field | Type | Source |
|---|---|---|
| `key` | str, pitch class | `key_detection.detect_key_from_chroma(...).key` |
| `mode` | `"major"` \| `"minor"` | `.mode` — **see §4 before writing this field** |
| `key_confidence` | float | `.confidence` |
| `key_alternate` | str, `"<key> <mode>"` | `.alternate_key` + `.alternate_mode` — K-S reliably confuses relative major/minor |
| `key_margin` | float | `.margin` — small margin = genuinely ambiguous |
| `key_method` | str | `"krumhansl_schmuckler"` — **required**, and the read-time proof that the value is not the old threshold |

### 3.4 `beat_grid` (M3)

`toolshop/beatgrid.py:53-65` `BeatGrid.to_dict()` verbatim: `tempo`, `beat_count`, `beat_times[]`,
`downbeat_times[]`, `bar_count`, `beats_per_bar`, `time_signature_assumed`, `downbeat_confidence`,
`median_beat_interval`, `method`. Round-trippable via `BeatGrid.from_dict` (`:67-77`), which
`cli.py:1671` already relies on for `--click-midi`.

`bpm` and `beat_count` at the top level must be **derived from this block**, not computed separately,
so a dossier can never state two different tempi.

### 3.5 `structure` (M2)

`toolshop/structure.py:260-266` output (`segments[]`, `n_segments`, `most_repeated_class`,
`duration`, `method`) **wrapped in a status envelope** — see §5. Segments carry
`{start, end, duration, segment_class, repetitions}`. No `"chorus"`/`"verse"` labels: a test in the
suite asserts they never appear, and that rule carries into v2.

### 3.6 `premaster` (M4)

`toolshop/premaster.py:213-227` output: `sample_rate`, `channels`, `integrated_lufs`,
`true_peak_dbfs_approx`, `max_short_term_lufs`, `gates[]` (each with threshold and verdict),
`verdict`, `failing_gates[]`, `flagged_gates[]`, `spec`.

Confirmed runnable on this corpus: `soundfile` 1.2.2 reads MP3, and the sample track is
`48000 Hz / 2 ch`, so the stereo phase gates (1 & 2) are measurable rather than `NOT_MEASURED`.

**But the verdict is a category error here, and v2 must say so.** The gates grade a *premaster*:
gate 3 wants sample peak ≤ −3.0 dBFS, gate 5 wants PSR ≥ 11 dB (`premaster.py:151-155`, `:184-189`).
The corpus is 222 **released, mastered, lossily-encoded YouTube rips**. Essentially all of them will
FAIL, and that FAIL carries no information. So v2 adds:

| Field | Value for this corpus |
|---|---|
| `premaster.profile` | `"reference_master"` |
| `premaster.verdict_applies` | `false` |
| `premaster.verdict` | still computed and stored, but a consumer must check `verdict_applies` first |

The *measurements* (LUFS, true peak, crest, PSR, phase correlation) remain valuable as descriptors of
a reference mix. The pass/fail does not. Open Question 3.

### 3.7 `lyrics` (M5)

The transcript is the largest block and the one most likely to be regenerated on its own, so:
**full transcript in a sidecar, summary + pointer in the dossier.** `toolshop/transcribe.py:463-468`
(`transcript_path_for`) already writes sidecars; this reuses that rather than inventing a location.
`--inline-lyrics` overrides for callers that want one file. Open Question 4.

```
"lyrics": {
  "status": "analysed" | "no_stem" | "not_attempted" | "failed",
  "reason": null | "<why>",
  "transcript_path": "<slug>/<stem>.large-v3.json",
  "backend": "faster-whisper", "model": "large-v3", "compute_type": "int8",
  "source": "vocal_stem" | "full_mix",        // never inferred - transcribe.py records it
  "source_path": "...",
  "language": "de", "language_probability": 0.97,
  "decode_settings": {...},                    // verbatim from transcribe.py:390-397
  "word_count": 188,
  "audio_duration": 249.3,
  "coverage_ratio": 0.691,                     // union of segment spans / audio_duration
  "longest_gap_seconds": 22.3,
  "gap_count": 3,
  "elapsed_seconds": 229.8, "realtime_factor": 1.09, "minutes_per_track": 3.83
}
```

`coverage_ratio`, `longest_gap_seconds` and `gap_count` are **not** in `Transcript.to_dict()` today
(`transcribe.py:261-277`); they are the numbers every M5 finding is stated in, so v2 computes and
stores them rather than leaving each reader to re-derive them.

**Two settings must be pinned explicitly in `decode_settings` for this corpus, not inherited from the
module defaults** (J-028):

- `language="de"`. `transcribe.py:97` defaults to `"sr"`, chosen for the user's Serbian material.
  The corpus is German — 221/221 catalogue rows.
- `model="large-v3"`. `transcribe.py:89` defaults to `"small"`, while every M5 number
  (RTF 1.09–1.17, 69% coverage) was measured on `large-v3`. Running `small` would make the cost
  estimate and the quality expectation both wrong.

`temperature=0.0` stays as the module default — it is the property (byte-identical output, J-000e)
that makes the whole regeneration worth doing.

### 3.8 `legacy` (new, required on every migrated track)

```
"legacy": {
  "schema_version": 1,
  "path": "<slug>/v1/<stem>_analysis.json",      // the preserved v1 file, moved not deleted
  "sha256": "...",
  "analysis_backend": "wav_reverse_engineer",
  "key": "G",
  "mode": "major",
  "mode_semantics": "chroma_magnitude_threshold",
  "mode_is_musical_mode": false,
  "note": "v1 `mode` was `chroma_mean[argmax] > 0.5` - a loudness threshold, not a musical mode.
           See feature_extractor.py:190 and JOURNAL J-025."
}
```

Every top-level v1 key that v2 does not carry forward must appear here. §8's diff enforces it as a
set identity, which is the strongest single check in this design:

```
set(v1_keys) - set(v2_keys) - set(v2["legacy"].keys()) == {}
```

### 3.9 Recognising a v1 dossier at read time

```python
def schema_version(d: dict) -> int:
    return int(d.get("schema_version", 1))     # absence == v1, proven by census
```

Nothing else. Not `analysis_backend`, not key presence — both were considered and both are ambiguous
under a v2 file (§2.1a). A reader that needs the old semantics reads `d["legacy"]`; a reader that
gets `schema_version == 1` knows `mode` is a loudness threshold and must not treat it as musical.

---

## 4. The `mode` Collision

**The problem.** v1 `mode` holds `"major"`/`"minor"` produced by `chroma_vals[argmax] > 0.5`. v2
`mode` holds `"major"`/`"minor"` produced by Krumhansl-Schmuckler. **The values are drawn from the
same two-element set and the field has the same name.** After a migration, no reader could tell which
rule produced a given value. A migration that silently reinterprets a field is worse than one that
fails, because the failure is invisible and permanent.

**Rejected options.**

| Option | Why rejected |
|---|---|
| Overwrite `mode` in place | Exactly the silent reinterpretation the task forbids. The old value is destroyed and nothing records that it ever meant something else. |
| Leave `mode` alone, add `musical_mode` | Leaves the *wrong* value under the name four call sites already read (`catalogue.csv`, `recipe.md`, `suno_prompts.md`, `bpm_adapter`). The defect keeps shipping. |
| Delete `mode` from v2 | Breaks `generate_crhymetv_catalogue.py:234` and `run_reverse_engineering_batch.py:126,171` for no gain, and destroys evidence. |

**Chosen: rename the semantics, preserve the value, and make the new value unwritable without proof.**

1. **`mode` in v2 means the K-S musical mode.** It may be written **only** when
   `key_method == "krumhansl_schmuckler"` is also written. The migration asserts this before
   serialising; if K-S did not run, the track is written with `stages.key.status = "failed"` and
   **no `mode` key at all**. A missing key is honest; a wrong one is not.
2. **The v1 value is preserved verbatim** in `legacy.mode`, alongside `legacy.mode_semantics`,
   `legacy.mode_is_musical_mode: false`, and the `file:line` of the rule that produced it.
3. **The v1 file itself is preserved**, moved to `<slug>/v1/` before v2 is written, with its sha256
   recorded. Per the data boundary: never delete, move or quarantine only.
4. **`--require-ks-key` is the guard**, following AGENTS.md's declarable-fallback rule ("recording
   which path ran is necessary but not sufficient — the user must be able to *demand* the good
   path"). With it set, any track whose K-S stage fails aborts rather than writing a v2 dossier with
   a missing mode.

**What happens to the old values, stated exactly:** they are copied into `legacy.mode`, tagged as
non-musical, and never read by anything that wants a musical mode again. They are not converted, not
reinterpreted, not deleted, and not trusted.

**Downstream consequence that must not be forgotten.** `catalogue.csv` (columns `key`, `mode`),
every `recipe.md`, and `suno_prompts.md` were all generated from the broken value — the suno prompts
literally read *"92.29 bpm, G major, German rap"* for material that is near-universally minor. These
are stale the moment the migration runs and must be regenerated in Stage C (§9). Until then they are
**wrong in a way that reads as authoritative**, which is the worst kind.

---

## 5. The `sections` Ambiguity

**First, the correction.** The framing "`sections` was always `[]`" is not what is on disk. **No
dossier has a `sections` key at all** — 222/222 missing (J-026). The `[]` lived in the dead
`_basic_analysis` segmenter, on a path the corpus batch never took.

So the states to disambiguate are **three**, not two:

| v1 state | Occurrences | What it actually means |
|---|---|---|
| key absent | 222 | the stage never ran on this file |
| `sections: []` | 0 on disk, reachable from pre-#048 code | the segmenter raised and a bare `except` returned `[]` |
| populated | 0 | — |

An empty list cannot mean both "analysed, genuinely no sections" and "never analysed" — and here it
would have had to mean a third thing as well, "raised and was swallowed". So v2 never lets the list
carry the meaning:

```
"structure": {
  "status": "analysed" | "none_detected" | "not_attempted" | "failed",
  "reason": null | "<free text>",
  "method": "beat-sync chroma + agglomerative boundaries + repetition clustering",
  "segments": [...],            // meaningful ONLY when status == "analysed"
  "n_segments": 9,
  "most_repeated_class": "B",
  "duration": 171.2
}
```

| `status` | Meaning | `segments` |
|---|---|---|
| `analysed` | segmenter ran and produced spans | non-empty, and `n_segments == len(segments)` |
| `none_detected` | segmenter ran to completion and found nothing | `[]` — *this is the only case where `[]` is a result* |
| `not_attempted` | stage disabled, or input below the segmentable floor; `reason` says which | `[]` |
| `failed` | raised; `reason` carries `<ExceptionClass>: <message>` | `[]` |

**Validation rules, checkable by machine:**
- `status == "analysed"` ⇒ `len(segments) >= 1` and `n_segments == len(segments)`.
- `status != "analysed"` ⇒ `reason` is a non-empty string. A silent non-result is invalid v2.
- Segments must tile: sorted, no gaps, no overlaps, all `duration >= 4.0 s` (the #048 sliver rule).
- No segment label may be `intro`/`verse`/`chorus`/`bridge`/`outro` — carried from #048's
  anti-fabrication test.

**Note on `structure.py`'s own contract.** Its docstring (`structure.py:163-165`) says it *"raises
rather than returning an empty list on failure. The previous implementation's silent
`except Exception: return []` is precisely how a total failure went unnoticed."* But the dossier
emitter re-introduces the swallow one level up — `reverse_engineering_adapter.py:96-98` catches
`Exception` and sets `structure_result = None`. In v2 that `None` becomes
`{"status": "failed", "reason": "<class>: <msg>"}`; the exception text is never discarded.

---

## 6. Migration Design on `batch.py`

### 6.1 Shape

New module `toolshop/dossier_migrate.py`, new CLI verb `toolshop dossier migrate`. It follows
`toolshop/stems_cli.py:206-230` — the canonical consumer of the shared pattern — rather than
inventing an idiom:

```python
files = batch.discover_files(input_dir, extensions=["mp3"],
                             limit=args.limit or 0, offset=args.offset or 0)
if not files:
    print(f"No audio files found in {input_dir}", file=sys.stderr); return 1

status = batch.run_batch(
    files=files,
    output_dir=out_root,
    process=lambda p: _migrate_one(p, args),
    status_path=args.status_path,          # explicit - see 6.2
    resume=args.resume,
    offset=args.offset or 0,
    description="dossier-v2",
)
completed = sum(1 for t in status["tracks"] if t["status"] == "completed")
failed    = sum(1 for t in status["tracks"] if t["status"] == "failed")
```

`_migrate_one` returns a dict carrying `"status"`, as `run_batch` requires
(`batch.py:115-116, 166`). Status JSON is flushed per item by `save_status`
(`batch.py:94-97`, called at `:177`). `--limit`/`--offset` are honoured by `discover_files`
(`batch.py:54-65`). Skip-completed resume is `batch.py:133-146`. All three AGENTS.md requirements are
satisfied by using the module rather than by re-implementing it — which
`run_reverse_engineering_batch.py` did (it carries its own `_norm_path`, `safe_slug`,
`load_or_create_status`, `save_status` and does **not** import `toolshop.batch`).

### 6.2 Two landmines in `batch.py` the migration must route around (J-029)

**(a) `--limit` rewrites `total_tracks`.** `discover_files` slices before `run_batch` sees the list;
`run_batch` sets `total = len(files)` (`batch.py:129`); `load_or_create_status` then overwrites the
stored value unconditionally — `status["total_tracks"] = total` (`batch.py:77`). **A `--limit 20`
sample run against an existing status file rewrites `total_tracks` from 222 to 20**, destroying the
number a count check would compare against.

> **Rule:** the sample run (§8) uses its own `--status-path` and its own output root. The corpus
> status file is never touched by a sample. And §7 never reads `total_tracks` — it re-enumerates.

**(b) `--offset` is display-only.** `run_batch(offset=...)` shifts the printed index (`batch.py:141`)
and nothing else; the slice actually processed is recorded nowhere. So the migration writes its own
`run_scope: {limit, offset, input_dir, n_files, first, last}` into the status dict before the run —
otherwise a resumed chunked run cannot prove what it covered.

*(Also noted, not routed around: `status["last_completed_index"] = idx` is set on the failure path
too (`batch.py:170-176`), so the field name is wrong whenever anything fails. Out of scope for M6 —
the count verification does not read it.)*

### 6.3 Per-stage resume — the reason for `stages`

Transcription is ~90% of the budget (§9). If a lyrics failure at track 180 forced the four cheap
stages to re-run, a night would be lost to work already done. So the unit of resume is
**(track, stage)**, not track:

1. `_migrate_one` loads any existing v2 file for the track.
2. For each stage in `--stages` (default all five), it runs only if that stage's block is absent, or
   its `status` is `failed`/`not_attempted`, or `--force-stage` names it.
3. After **each** stage, the v2 file is rewritten **atomically** (`tmp` + `os.replace`) with the new
   block and an updated `stages` entry. A kill at any point leaves a valid, partially-populated v2
   file — never a truncated one.
4. `run_batch`'s own per-item status flush then records the track-level outcome on top.

This is what makes the A/B/C staging in §9 possible, and it is why `stages` is a required envelope
field rather than a nicety.

### 6.4 Per-track flow

```
probe            sf.info(src)  -> exists / non-zero / decodable. Failure here is a
                 TERMINAL, RECORDED outcome (§7.3), never a skip.
read v1          <slug>/<stem>_analysis.json, if present. Absent is allowed (a track
                 may have no v1) and recorded as legacy: null.
preserve v1      copy -> <slug>/v1/<stem>_analysis.json, record sha256. Never delete.
load audio       librosa.load(sr=22050, mono=True) once; shared by key/beat/structure.
                 premaster re-reads the file itself - it needs the stereo pair.
stage key        key_detection.detect_key_from_chroma(chroma_mean)
stage beat_grid  beatgrid.analyze_beats(y, sr)
stage structure  structure.segment_track(y, sr)
stage premaster  premaster.analyze_premaster(path)
stage lyrics     transcribe.transcribe_file(..., search_dirs=[<slug>/stems])   <-- see below
merge            v1 carried keys + new blocks + legacy + envelope
write            atomic tmp + os.replace -> <slug>/<stem>_analysis.json
```

**The stem-discovery trap (J-027).** `find_vocal_stem` (`transcribe.py:292-337`) searches the audio
file's own parent, sibling `*stem*` dirs, and `paths.subdir("stems")`. The corpus audio is at
`D:\Projects\Tools\yt_extractor\downloads\CrhymeTV\` while its stems are at
`results/crhymetv_re/per_track/<slug>/stems/` — neither a sibling nor under `data/toolshop/stems`
(which holds only `karaoke/`). Verified first-hand in the venv:

```
default search  -> None
explicit search -> ...\per_track\<slug>\stems\...(Vocals)_UVR-MDX-NET-Voc_FT.wav
```

So `search_dirs` must be passed explicitly, or **every one of the 140 available stems is silently
missed** and the whole corpus transcribes from the full mix. And 82 tracks have no stem at all, so
`lyrics.source` must be recorded per track and any corpus-level coverage figure reported split by
source — a single blended number would be uninterpretable.

### 6.5 CLI surface

```
toolshop dossier migrate
  --input-dir  <audio dir>          # authoritative input enumeration
  --dossier-root <per_track dir>
  --status-path <file>              # REQUIRED, no default onto batch_status.json
  --limit N --offset N --no-resume
  --stages key,beat_grid,structure,premaster,lyrics
  --force-stage <name>              # re-run a stage that already succeeded
  --require-ks-key                  # abort rather than write a dossier with no mode
  --require-stem                    # refuse full-mix fallback (82 tracks would refuse)
  --model large-v3 --language de
  --inline-lyrics
  --max-duration 0                  # 0 = analyse everything, incl. the 67.7 min documentary
  --dry-run                         # plan + counts only; writes nothing
```

`--dry-run` prints the reconciliation table of §7 against the *current* state, so the operator sees
what will be touched before a 13-hour job starts.

---

## 7. Count Verification

A separate verb, `toolshop dossier verify-v2`, that can be run **without** the migration and against
a finished run. It is a deliverable, not a checklist line: the corpus already contains a status/disk
disagreement (§1.2), so a check that trusts one source would already be wrong today.

### 7.1 Three independent enumerations, none trusted

| # | Source | How |
|---|---|---|
| **INPUT** | the audio directory | `batch.discover_files(input_dir, ["mp3"], 0, 0)`, keys normalised with `batch._norm_path` (NFC + lowercase + forward slashes — 53 corpus filenames are non-ASCII, so this matters) |
| **STATUS** | the migration's status JSON | entries under `tracks[]`, keyed by `source` |
| **DISK** | the dossier tree | `per_track/*/*_analysis.json`, **explicitly excluding `*_voice_analysis.json`**, parsed, keeping those with `schema_version == 2` |

> The DISK glob exclusion is not a detail. The bare suffix glob is what produced the phantom 444
> (J-020), and the same latent bug sits in `scripts/recover_batch_status.py:17,29`
> (`track_dir.glob("*_analysis.json")` matches the voice sidecar; it currently gets the right file
> only because `_a` sorts before `_v`). Third occurrence of one class — AGENTS.md says centralise, so
> a single `iter_dossiers()` helper owns this glob and both call sites use it.

### 7.2 The six difference sets

Each is disjoint and each has exactly one interpretation:

| Set | Meaning | Verdict |
|---|---|---|
| `INPUT − STATUS` | the batch never attempted these | **FAIL — silent skip.** The named failure mode. |
| `STATUS − INPUT` | status references a source no longer in the input dir | FAIL — moved/renamed input, or wrong `--input-dir` |
| `STATUS(completed) − DISK` | status claims done, no v2 file exists | **FAIL — the status file lies** (already true at n=1 today) |
| `DISK − STATUS` | a v2 file nothing recorded writing | FAIL — untracked write / stale output |
| `STATUS(terminal, reasoned)` | failed or skipped **with an allow-listed reason** | **Expected shortfall.** Listed individually, does not fail the run. |
| `DISK(malformed)` | `schema_version != 2`, or a required key missing, or `structure.status == "analysed"` with empty `segments` | FAIL — schema violation |

**Exit 0 only when** `INPUT == STATUS == DISK ∪ terminal`, every terminal item has an allow-listed
reason **and** a corresponding failure artefact on disk, and `DISK(malformed)` is empty.

### 7.3 Legitimate failure vs silent skip — the distinguishing rule

> **A track never leaves zero trace.**

Every input either produces a v2 dossier, or a `<stem>_analysis.v2.failed.json` next to where the
dossier would go, containing `{source, sha256, attempted_at, stage, exception_class, message,
probe: {...}}`. A legitimate failure has **three** correlated records — a status entry, a failure
artefact, and a probe result. A silent skip has **none**. That asymmetry is what makes them
distinguishable at all, and it is the reason the failure artefact exists.

Allow-listed terminal reasons, each requiring recorded evidence rather than an assertion:

| Reason | Evidence the verifier re-checks itself |
|---|---|
| `source_missing` | `Path.exists()` is False **now**, at verify time |
| `zero_length` | `sf.info(p).frames == 0` |
| `decode_error` | `sf.info(p)` raises; the verifier stores the exception text it got, not the batch's |
| `duration_exceeds_max` | `sf.info(p).duration > --max-duration`, and `--max-duration` was set |

Anything else in `reason` is **not** allow-listed and fails the check. "Corrupt file" is therefore
*proved at verify time by an independent probe*, never accepted on the batch's word — the same
discipline as re-running a check before asserting a verdict.

### 7.4 What it prints when it passes

```
=== dossier v2 verification =====================================
input dir      D:\Projects\Tools\yt_extractor\downloads\CrhymeTV
status         results\crhymetv_re\migrate_v2_status.json
dossier root   results\crhymetv_re\per_track

INPUT   222   (mp3, recursive, NFC-normalised)
STATUS  222   completed 221 | failed 0 | terminal 1
DISK    222   schema_version==2: 222 | v1 remaining: 0 | malformed: 0

reconciliation
  INPUT - STATUS ................ 0
  STATUS - INPUT ................ 0
  STATUS(completed) - DISK ...... 0
  DISK - STATUS ................. 0
  malformed ..................... 0

terminal, with evidence (1)
  duration_exceeds_max  2023_02_07_Komm_wir_schreiben_Geschichte_Dokumenta_BKGeueSkWXQ
                        probe: 4062.0 s > --max-duration 3600  [re-probed OK]

stage coverage        key 222 | beat_grid 222 | structure 222 | premaster 222 | lyrics 221
lyrics source split   vocal_stem 140 | full_mix 81 | no_stem 1
decode_settings       1 distinct set across the run:
                      {language: de, model: large-v3, beam_size: 5, temperature: 0.0,
                       condition_on_previous_text: false, vad_filter: true}
legacy preserved      222 / 222   (v1 sha256 matches the copy under <slug>/v1/)

VERDICT: PASS   222 in -> 222 accounted (221 dossiers + 1 evidenced terminal)
exit 0
```

Note `stage coverage` and `decode_settings` are printed even on success. A run where half the tracks
silently fell back to `small`, or to `language=sr`, would pass every count and still be worthless
(J-028); printing the distinct settings is how that is caught.

### 7.5 What it prints when the answer is short

The plan asks "what does it report when the answer is 431?" — against a corpus of **222** the
equivalent is 222 in, 209 out. It reports this, and exits non-zero:

```
INPUT   222
STATUS  210   completed 209 | failed 1 | terminal 0
DISK    209   schema_version==2: 209 | v1 remaining: 13 | malformed: 0

reconciliation
  INPUT - STATUS ................ 12    <-- NEVER ATTEMPTED
  STATUS - INPUT ................ 0
  STATUS(completed) - DISK ...... 0
  DISK - STATUS ................. 0
  malformed ..................... 0

*** 12 inputs were never attempted. This is the silent-skip failure mode. ***
  the batch has no record of these files. They are not failures - nothing tried them.
  offset/limit at last run: offset=0 limit=210   <-- run_scope, from the status file
  first missing (sorted): 2025_02_17_FULL_HOUSE_TOUR_MONSTER_BLOGG_in9kq1q7_aw
  ... 11 more, full list -> results\crhymetv_re\verify_v2_missing.txt
  each re-probed at verify time: 12/12 exist, decode OK, non-zero length
  => not corrupt input. The run did not cover them.

*** 1 failure WITHOUT an allow-listed reason ***
  2019_11_08_Sa4_..._KsW1nT8dQ2w
    stage:    lyrics
    reason:   "RuntimeError: CT2 allocation failed"   (not in the allow-list)
    artefact: <slug>/..._analysis.v2.failed.json      present
    re-probe: file exists, 44100 Hz / 2 ch / 212.4 s, decodes OK
    => the INPUT is fine. This is a run failure and is retryable.

VERDICT: FAIL   222 in -> 209 out.  13 unaccounted: 12 never attempted, 1 unreasoned failure.
exit 2
```

The three things that make this useful rather than decorative: it separates *never attempted* from
*attempted and failed*; it **re-probes** the missing inputs itself, so "the file was corrupt" is
either proved or refuted on the spot; and it prints the run scope, so a truncated `--limit` is
visible as the cause instead of being guessed at.

### 7.6 Why this check can fail

It compares three enumerations produced by three different mechanisms and passes only when all three
agree. Run against the corpus **today** it would already fail — `STATUS` says
`analysis_json: null` for the documentary while `DISK` has a file, and `catalogue.csv` has 221 rows
against 222 directories. A check that cannot fail on today's known-inconsistent state would not be
worth writing.

---

## 8. Sample Protocol & Diff Format

### 8.1 How the sample is chosen — deliberately, not randomly

A random 20 of 222 would be ~90% ordinary 3–4 minute German rap tracks with stems, and would exercise
almost none of the paths that break. The sample is **stratified against known-awkward properties**,
each stratum identified from the corpus census, with named candidates:

| # | Stratum | Why it can break | Candidates (first-hand from `catalogue.csv`) |
|---|---|---|---|
| 1 | 2 shortest | segmenter floors, beat grid on <8 s | `2012_10_09_MUTANTEN_EICHH_RNCHEN_iiRDTie6kFU` (**7.3 s**), `2017_06_27_187_Strassenbande_Trailer_Sampler_4` (27.0 s) |
| 2 | 2 longest | premaster gate 5 is O(duration) — ~1600 BS.1770 windows on a 27 min file; whisper drift | `2025_02_17_FULL_HOUSE_TOUR_MONSTER_BLOGG` (**1632 s**), `2025_04_16_bissu_dumm_MEGALODON_REMIX` (1113 s) |
| 3 | 1 the skipped documentary | the only 11-key v1 variant, the only `skipped_long`, the status/disk disagreement | `2023_02_07_Komm_wir_schreiben_Geschichte_Dokumenta_BKGeueSkWXQ` (4062 s) |
| 4 | 3 of the 7 v1-`minor` tracks | the only tracks where the old threshold fired; most diagnostic for the K-S diff | `2024_09_19_Bonez_F_r_Mary`, `2022_04_24_Maxwell_KEIN_PLAN_Snippet`, `2026_06_07_Johnny_s_Tape_Snippet` |
| 5 | 3 non-ASCII / emoji filenames | UTF-8 path handling, `safe_slug`, `_norm_path` NFC | `Bonez - Fussballer ⚽️`, `PIRATE FR€€$T¥L£`, `Bonez MC - WTF？!` (fullwidth `？`) |
| 6 | 3 stemless | full-mix lyrics fallback; 82/222 of the corpus is in this state | any of the 82, e.g. `2023_03_02_Gzuz_Bonez_Abziehen` |
| 7 | 2 tempo extremes | beat grid + downbeat phase | 69.84 BPM `2018_08_11_BONEZ_MC_RAF_Camora_500_PS`, 184.57 BPM `2022_08_15_..._Palmen_aus_Plastik` |
| 8 | 2 with empty `top_chords` | the advanced backend already produced nothing here (9 such tracks) | from the 9 |
| 9 | 2 ordinary songs with stems | the control — if these break, everything is broken | e.g. `2010_12_08_Sa4_T_terprofil_eryRCHmXItY` |

**20 tracks, ~1.6 h of audio, of which one track is 27 min.** Estimated sample cost ~2 h wall clock —
deliberately front-loaded with the long tracks so the cost model is stressed rather than flattered
(AGENTS.md: a clip measurement exaggerates anything with fixed overhead; the reciprocal is that an
all-short sample under-projects).

Run into a **separate output root and status path**, never the corpus ones (§6.2a).

### 8.2 Stop criteria — the gate must be able to fail

Any **STOP** halts the full run until it is understood. These are not warnings.

| # | Criterion | STOP when |
|---|---|---|
| S1 | Count | any of the 20 is unaccounted by §7 — i.e. `INPUT − STATUS` non-empty, or a failure with no allow-listed reason |
| S2 | Non-destruction | any v1 file is not present under `<slug>/v1/` with a matching sha256, or any `legacy.mode` differs from the v1 `mode` |
| S3 | Key-set identity | `set(v1) − set(v2) − set(v2.legacy) ≠ {}` on any track — a v1 field was dropped without being preserved |
| S4 | Mode plausibility | **≥ 80% of the 20 come back `major`.** The v1 corpus is 96.8% major *because the rule was broken*; reproducing that skew means K-S is not actually running. The sample deliberately includes 3 of the 7 v1-minor tracks, so this is a real test, not a formality. |
| S5 | Structure | `structure.status == "failed"` on any track, or `status == "analysed"` with `n_segments < 2` on any track > 60 s. This is the field whose entire history is a silent failure. |
| S6 | Beat grid | `60 / median_beat_interval` does not reproduce `beat_grid.tempo` within 1% (the #049 cross-check), **or** top-level `bpm` moves > 2% from v1 on any track. Same audio, same tracker — a systematic tempo shift means the grid is on different input. |
| S7 | Language | `language != "de"` or `language_probability < 0.5` on more than 4 of the 20. Below that the pin is wrong and 222 useless transcripts would follow (J-028). |
| S8 | Determinism | 2 of the 20 re-run with identical settings do **not** produce a byte-identical `lyrics` block. This is the property (J-000e) that makes the whole regeneration worth doing; if it does not hold, the corpus diff is noise and there is no reason to spend the night. |
| S9 | Cost | measured min/track projects the full corpus beyond **1.5×** the §9 budget. Re-plan rather than start. |

**One criterion that changes the schema instead of stopping the run:** if `premaster.verdict == FAIL`
on ≥ 18/20, that confirms §3.6's category error empirically, and `verdict_applies: false` must be in
the schema *before* the full run — not retrofitted onto 222 files afterwards.

**Also recorded from the sample, not gated:** min/track per stage (AGENTS.md requires a measured
min/track on this machine before merge; the migration has none yet), and lyrics coverage **split by
`source`** — a blended figure across 140 stemmed and 82 stemless tracks would mean nothing.

### 8.3 Diff format

`toolshop dossier diff --v1 <dir> --v2 <dir> --out diff.md`, two levels.

**Level 1 — corpus field matrix.** One row per field, so a reviewer sees the shape of the change
before any individual track. *(The counts below are an illustration of the format — no migration has
been run. The only first-hand number in this block is `sections`: 0/222 files have the key.)*

```
field                | unchanged | changed | added | removed | absent both
---------------------+-----------+---------+-------+---------+------------
bpm                  |        20 |       0 |     0 |       0 |          0
duration_seconds     |        20 |       0 |     0 |       0 |          0
key                  |        13 |       7 |     0 |       0 |          0
mode                 |         6 |      14 |     0 |       0 |          0
key_confidence       |         0 |       0 |    20 |       0 |          0
structure            |         0 |       0 |    20 |       0 |          0
beat_grid            |         0 |       0 |    20 |       0 |          0
premaster            |         0 |       0 |    20 |       0 |          0
lyrics               |         0 |       0 |    19 |       0 |          1
chord_progression    |        18 |       0 |     0 |       0 |          2
instruments          |        19 |       0 |     0 |       0 |          1
notes                |        19 |       0 |     0 |       0 |          1
sections             |         0 |       0 |     0 |       0 |         20   <- never existed
```

Plus, for changed numeric fields, the distribution of relative change (min / median / p95 / max) —
because "7 keys changed" is a different story from "7 keys changed and all by a semitone".

**Level 2 — per-track detail**, only for tracks with a `mode`/`key`/`bpm` change or any regression.
*(Again a format illustration; the v1 values quoted — `G# minor`, 99.38 BPM for `Bonez_F_r_Mary` —
come from `catalogue.csv`, the v2 values do not, because nothing has been migrated.)*

```
### 2024_09_19_Bonez_F_r_Mary_QWTgsZ0BVh0
  key   G#  -> C#      key_confidence 0.71  key_margin 0.09  alt "D# minor"
  mode  minor -> minor  [v1 mode was a loudness threshold; agreement here is coincidence]
  bpm   99.38 -> 99.38   (0.00%)
  structure  added: 9 segments, ABCBABBAB, most_repeated B, shortest 6.2 s
  premaster  FAIL (peak -0.1 dBFS, PSR 6.2)  verdict_applies=false  [mastered rip]
  lyrics     de p=0.97 | vocal_stem | 171 words | coverage 0.66 | longest gap 18.4 s
  legacy     preserved, sha256 a91f... , v1 key "G#" mode "minor" (loudness threshold)
```

### 8.4 Change vs regression — the reviewer's rule table

This is the part that makes the diff a gate rather than a report.

| Observation | Reading |
|---|---|
| `mode` flips `major` → `minor` on many tracks | **Expected change.** #047 measured 4/8 flipping, all in that direction, on a genre that is near-universally minor. |
| `mode` stays ≥ 95% `major` | **Regression.** That is the shape of the old defect. K-S is not running (see J-024 — the wrong backend is the likely cause). |
| `key` changes on a minority of tracks | **Expected change.** K-S tonic vs `argmax(chroma)` — they agree often, not always. |
| `key` changes on ~100% of tracks | **Regression.** Total disagreement suggests a bug (pitch-class ordering, chroma axis) rather than a better estimator. |
| `key_confidence` low with small `key_margin` | **Not a regression.** K-S confusing relative major/minor is known and is *why* those fields exist. Honest uncertainty, not error. |
| `bpm` moves > 2% | **Regression.** Same file, same librosa beat tracker. |
| `duration_seconds` changes at all | **Regression.** A different decode of the same bytes. |
| `structure` absent → populated | **The intended change.** This is what M2 was for. |
| `structure` absent → `status: failed` | **Regression** — and read `reason`; the whole history of this field is a swallowed exception. |
| `premaster` FAIL on nearly everything | **Not a regression — a category error.** Mastered rips against a premaster spec. Fix the schema (§3.6), not the code. |
| `instruments` / `chord_progression` / `notes` / `effects` present in v1, absent in v2 | **Regression, always.** The migration carries them; it does not recompute or drop them. |
| Any v1 key absent from both v2 and `v2.legacy` | **Regression, always.** The machine-checkable rule; equivalent to S3. |
| `lyrics` coverage ~69% on stemmed tracks | **Expected** — the measured M5 ceiling, `unverified — source: docs/superpowers/STATUS.md` (H2-M5). Not a migration defect. |
| `lyrics` coverage on stemless tracks materially below stemmed | **Expected and must be recorded per track**, never averaged into one corpus number. |

---

## 9. Cost & Staging

### 9.1 The relayed figure and what replaces it

> **~25 h CPU for the 444 dossiers** — `unverified — source: docs/superpowers/STATUS.md` (H2-M5 row),
> repeated in `plans/2026-09-01-next-moves.md:42` and `CHANGELOG.md:263`.
> **Superseded.** It is scaled to 444 and to 28.3 h of audio, both of which are the same double count
> (J-020, J-021).

First-hand, this session:

```
221 completed tracks               = 48 902 s = 13.5839 h   (sum of catalogue.csv duration_seconds)
+ skipped documentary               =  4 062 s =  1.1283 h
corpus audio, single count          =            14.7122 h
the published figure reproduced: 2 x 13.5839 + 1.1283 = 28.2961 h ~ "28.3 h"
```

### 9.2 Composition, and which stage dominates

| Stage | Basis | Cost for 222 tracks |
|---|---|---|
| **lyrics (transcription)** | RTF 1.09–1.17 on `large-v3` — `unverified — source: docs/superpowers/STATUS.md` (H2-M5) — applied to **14.71 h** measured here | **~12.6–13.5 h** |
| key + beat_grid + structure + premaster | 30–45 s/track — `unverified — source: docs/superpowers/HANDOFF-2026-08-31.md:172`, **never measured on this machine** | ~1.9–2.8 h |
| read / preserve / merge / write | I/O bound | minutes |
| **Total** | | **~15–16 h** |

**Transcription dominates — roughly 85–90% of the budget.** Everything else together is a couple of
hours. Two caveats on the cheap stages: they are unmeasured, and `premaster`'s gate 5 loops
`meter.integrated_loudness` over 3 s windows at 1 s hop (`premaster.py:171-181`), so it is O(duration)
with a heavy constant — on the 27-minute track that is ~1600 loudness measurements, and the
per-track figure will not be flat. The 8 tracks over 8 minutes carry 1.82 h of the audio between them.

**AGENTS.md requires a measured min/track on this machine before merge. The migration has none.** The
sample run (§8) is where it is obtained; the numbers above are a plan, not a measurement.

### 9.3 Staging

Per-stage resume (§6.3) makes this three jobs instead of one:

**Stage A — cheap fields, ~2–3 h, can run in a working session.**
`--stages key,beat_grid,structure,premaster` over all 222. Delivers the four M1–M4 fields for the
whole corpus and resolves the `mode` collision the same day. Verified with §7 before Stage B starts.

**Stage B — lyrics, ~13 h, overnight, alone.**
`--stages lyrics`. Restartable at any point; a kill costs at most one track.

**Stage C — regenerate the derived artefacts.**
`catalogue.csv`, all 222 `recipe.md`, `suno_prompts.md` — all built from the broken `mode` (§4) and
stale the moment Stage A lands. Until regenerated they are wrong in a way that reads as
authoritative.

### 9.4 Measurement discipline — binding, from AGENTS.md

- **The long batch runs alone.** Nothing that measures time may run beside it: not the test suite
  (6–13 minutes), not another agent's benchmark, not a second stage of this migration. A timing
  number produced next to a 13-hour CPU job is void, and the project has already voided two
  measurement attempts this way.
- **Warm up and repeat the baseline** for the sample's min/track: discard a warm-up run, repeat the
  baseline at the end, and if the two baselines disagree by more than ~10%, the machine is not a
  stable instrument and no timing conclusion holds.
- **Validate the clip result on a full input.** The sample deliberately contains the 27-minute and
  67.7-minute files for exactly this reason.
- **Kill the watcher with the process it watches.** Use bounded polling (`for i in $(seq 1 N)`),
  never `until … sleep`; three unbounded watchers were leaked in one session.

---

## 10. Open Questions for the User

Ordered by how much they block.

1. **[BLOCKING] The migration cannot use the default backend.** The four M1–M4 fields exist only in
   `_basic_analysis`, while the corpus batch hard-codes `backend="advanced"` (J-024). Two ways
   forward: **(a)** port the four field groups into `_advanced_analysis` so one emitter produces
   everything — *recommended*, one place, and it fixes the CLI and any future run too; or **(b)** have
   `dossier_migrate` compute them itself and merge into the v1 dict, leaving the adapter alone —
   smaller blast radius, but permanently two emitters. Which?

2. **Do we touch `feature_extractor.py:190`?** The loudness-threshold rule is in
   `projects/05-track-reverse-engineering/...`, a vendored tree outside `toolshop/`. *Recommended:*
   do not patch it — stop *using* its `key`/`mode` (option 1a does that), and leave the vendored code
   as-is so we never diverge from upstream silently. Confirm.

3. **`premaster` on mastered rips.** The gates grade a premaster; the corpus is 222 mastered YouTube
   rips, which will FAIL almost universally and meaninglessly (§3.6). *Recommended:* keep the
   measurements, set `profile: "reference_master"` and `verdict_applies: false`. Alternative: omit
   the block entirely for corpus tracks. Which?

4. **Lyrics inline or sidecar?** *Recommended:* sidecar + summary/pointer in the dossier, reusing
   `transcribe.transcript_path_for`. Inline is available via `--inline-lyrics`.

5. **Decode settings for a German corpus.** Confirm `language="de"` (module default is `"sr"`) and
   `model="large-v3"` (module default is `"small"`, but every M5 number is a `large-v3` number).
   `small` would be materially faster and materially worse; `large-v3` is what the ~13 h is based on.

6. **The 82 stemless tracks.** Transcribe from the full mix — mixed-provenance corpus, `lyrics.source`
   recorded per track — or leave `lyrics.status: "no_stem"` and revisit? *Recommended:* transcribe
   from the full mix and record the source; a missing third of the corpus is worse than a labelled
   weaker third. But note P3's finding that the full mix produced *fewer words and a 51.5 s span*, so
   these transcripts will be weaker in a specific, known way.

7. **The 67.7-minute documentary.** 1.13 h — **7.7% of the whole audio budget** — and it is speech,
   not music. In or out? *Recommended:* out of the lyrics stage, in for the cheap stages, with
   `--max-duration` set so the exclusion is recorded as an evidenced terminal reason rather than a
   silent skip.

8. **The 33 non-song items** (blogs, vlogs, trailers, snippets — 3.7 h of the 13.58 h). Their key,
   structure and premaster values are not meaningful for a music corpus. Regenerate anyway for
   completeness, or mark and skip? *Recommended:* regenerate — they are cheap in the non-lyrics
   stages, and skipping them creates exactly the kind of gap §7 exists to detect.

9. **Where do v1 dossiers go?** *Recommended:* `per_track/<slug>/v1/` in place, so the pair travels
   together. Alternative: a single quarantine tree under `data/toolshop/`. Never deleted, either way.

10. **PapaPedro.** 687 source mp3s, 3 analysed directories, no dossiers — counted into the phantom 444
    but not actually part of the corpus. Out of scope for M6, or a separate follow-on? *Recommended:*
    out of scope, and correct the count in `STATUS.md`/`next-moves.md`/`CHANGELOG.md` so the 444 does
    not propagate further.
