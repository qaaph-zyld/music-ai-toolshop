# Plan — next moves (written 2026-08-31, after #052)

> Executable plan. `[USER DECISION]` marks steps that need a ruling before an agent proceeds.
> State this is written against: `master` @ `48cc98d`, 0 unpushed, suite 1189 passed / 2 skipped.

## The organising judgement

The toolshop is now substantially *correct*. Over two sessions the dossier's four decorative fields
became real, a vocal-swap lane was built and verified end to end, and M5 produced a reproducible
transcription path. What has **not** happened is that any of it was used to make a track.

That was the honest gap in the last goals-vs-reality assessment (G10), and it is still the gap. So
the ordering below is deliberately not "finish the roadmap" — it is **prove the thing you asked for
works on real input, then make the corpus true, then remove the risk that could lose the corpus.**

---

## P0 — Prove the swap on a real recorded take  ⏱ hours

The lane is verified end to end, but with a **stem standing in for a recording**: instrumental and
vocal came from the same file, so alignment was handed `--offset-seconds 0` and never solved a real
problem. Alignment is also the component that measured *weakest* — on real material with a true
offset of exactly 0, aligning against the instrumental returned **+1.416 s** and correctly refused
itself as ambiguous.

Everything else in the lane is proven. This is the one path that is not.

- [ ] `[USER DECISION]` Pick a Suno track and record a take over it (16 bars is enough).
- [ ] Run: `toolshop vocal-swap run <suno>.mp3 <take>.wav --profile serbian_drill`
      — let separation run, so `--align-reference auto` uses the Suno vocal stem, which is the
      configuration that has never been exercised.
- [ ] Record what alignment reports: `offset_seconds`, `confidence`, `peak_margin`, `drift_seconds`.
      **Judge the result by ear against those numbers** — this is the calibration data that
      `DEFAULT_MIN_PEAK_MARGIN` and `DEFAULT_MIN_CONFIDENCE` currently lack.
- [ ] If it lands: the lane is done, and there is a track to show for it.
- [ ] If it misaligns: `--offset-seconds` is the escape hatch; capture the failing case as a fixture.

**Also delivers the missing min/track for the separation stage**, which the e2e run skipped.

---

## P1 — M6: make the corpus true  ⏱ ~25 h CPU + ~4 h analysis, resumable

> ⚠️ **RESIZED 2026-09-01 — this section's premise, scope and cost were all wrong. See `JOURNAL.md`
> `J-020`–`J-029` and `specs/2026-09-01-dossier-schema-v2.md`. Corrections inline below; the
> original wording is struck through so the wrong belief stays visible.**
>
> 1. **The corpus is 222 dossiers, not 444.** `*_analysis.json` also matches the `_voice_analysis.json`
>    sidecar, so the glob counted every track twice: 222 dossiers + 222 voice sidecars. PapaPedro —
>    the reason the handoff gave for revising 222 up to 444 — contributes **no dossiers at all**.
> 2. **The cost inherits the same double count.** Real audio is ~13.6 h over 221 tracks, so
>    transcription is **~13 h — an overnight, not a weekend.**
> 3. **A plain re-run would add nothing.** `beat_grid`, `structure`, `premaster` and the K-S key block
>    are emitted **only by `_basic_analysis`** (`reverse_engineering_adapter.py:52-133`), while the
>    corpus batch hard-codes `backend="advanced"` (`run_reverse_engineering_batch.py`). Verified
>    across all 222 dossiers: `sections` 0, `structure` 0, `beat_grid` 0, `premaster` 0, `lyrics` 0.
>    **M6's real blocker is a backend defect, not a batch run.**
> 4. **`sections` is *absent*, not `[]`.** The ambiguity is three-valued — never analysed / analysed
>    and empty / analysed and populated — and an empty list cannot carry that.
> 5. **The loudness-threshold `mode` is still live code**, not history:
>    `feature_extractor.py:190` reads `mode = 'major' if chroma_vals[key_idx] > 0.5 else 'minor'` —
>    chroma energy at the tonic bin against a fixed threshold. Corpus-wide that yields **215 major /
>    7 minor**.
> 6. **The corpus is German, not Balkan** — `Sa4 – Täterprofil`, `LETZTE ANSAGE`, `129ers`, `Capuz`.
>    `transcribe.py` defaults to `language="sr"` and `model="small"`, while every M5 number is a
>    `large-v3` number. Both must be pinned explicitly in any migration.
> 7. **A `--limit 20` sample run would overwrite `total_tracks`** in the corpus status file,
>    destroying the baseline a count check compares against.

~~Every field added in M1–M4 exists **only for tracks analysed since**. The existing 444-dossier corpus
still carries the `mode` that was a loudness threshold and the `sections` that were always `[]`.~~
M6 is what makes this period's work true of the corpus rather than only of future runs.

Now sized properly: transcription is **~25 h** for 28.3 h of audio at RTF ~1.13, and **reproducible**
— `temperature=0` gives byte-identical output, so a future corpus diff shows real analysis changes
rather than decoder noise. That property is what makes a regeneration worth doing at all.

- [ ] Define dossier schema v2 (adds `key`/`mode` from K-S, `structure`, `beat_grid`, `premaster`,
      and `lyrics` from M5).
- [ ] Write the migration + resumable batch on `toolshop/batch.py`'s shared pattern
      (status JSON flushed per item, `--limit/--offset`, skip-completed resume).
- [ ] Validate on a **10–20 track sample** and diff against the old dossiers before committing to 444.
- [ ] Run the full corpus overnight / across a weekend.
- [ ] **Verify counts before declaring done** — the failure mode here is a batch that "succeeds"
      having skipped half its input.

---

## P2 — G5: disaster recovery  ⏱ an afternoon + a purchase

**The largest unmitigated risk in the project, and it is not a code problem.** 15.79 GB of
irreplaceable Suno audio, single copy, on the same 2010 disk as everything else. The backup is
verified and current — and it is on that same spindle. A verified backup that dies with its source
is not disaster recovery.

This has been carried across three sessions. It is the only item here where the downside is
permanent.

- [ ] `[USER DECISION]` Choose: external drive / cloud / both.
- [ ] Extend `backup.py` to write to the chosen off-disk target.
- [ ] Add a coverage test asserting the Suno asset class appears in the manifest — the rule from
      AGENTS.md, written because `backup.py` once verified clean for a month while collecting **zero**
      Suno data.
- [ ] Restore-test one track from the off-disk copy. A backup that has never been restored is a hope.

---

## P3 — M5 coverage: close it or accept it  ⏱ ~30 min per experiment

Transcription is reproducible and fast, but covers **69%** of the vocal at 45 words/min against rap's
typical 100–200. About a third of the track yields no timings, and one 22.3 s span has untrustworthy
internal timing. Since M5 exists to feed syllables-per-bar analysis, that is a real limit.

**MEASURED 2026-08-31 — three variants, full track each. Neither hypothesis survived.**

| variant | coverage | words | max span | gaps | min/track |
|---|---|---|---|---|---|
| **A defaults (stem)** | **69.1%** | **188** (45/min) | **22.3 s** | 3 | 4.08 |
| B `vad_filter=False` | 46.4% | 127 (31/min) | 25.9 s | 4 | 6.17 |
| C full mix | 68.4% | 147 (35/min) | 51.5 s | 0 | 2.78 |

- [x] ~~`vad_filter=False`~~ — **wrong, and badly**: coverage fell 22.7 points and the run got 50%
      slower. VAD was not over-filtering; without it the decoder wanders through silence.
- [x] ~~Less aggressively separated source~~ — **wrong**: the full mix tied on coverage (68.4%) with
      *fewer* words and a **51.5 s** span. Its zero gaps are not a win — it "covers" the track by
      emitting long continuous blocks whose internal timings are unusable. Separation artefacts were
      not the problem.
- [x] A reproduced **69.1% / 188 words exactly**, re-confirming determinism across sessions.

**Diagnosis: the ceiling is the model on this material, not the plumbing.** Neither of the two
plausible mechanical causes survived contact. Remaining levers are different in kind — `initial_prompt`
priming with artist vocabulary, chunk-level retry, a different model, or fine-tuning.

- [ ] ~~**The better answer for our own tracks: forced alignment, not recognition.** … which sidesteps
      the 31% entirely.~~ **PREMISE CORRECTED 2026-09-01 — see `JOURNAL.md` `J-015`, `J-016` and
      `specs/2026-09-01-forced-alignment-feasibility.md`.** Forced alignment is still the right route,
      but **it does not sidestep the 31% by itself.** whisperX's `align()` consumes segments that
      already carry `text`, `start` *and* `end` — it **refines a segmentation, it does not produce
      one**. Fed the existing ASR segmentation, the uncovered 31% has no anchor and the gap
      propagates. The naive fix (one segment spanning the track) is arithmetically ruled out: `align()`
      has no chunking, self-attention goes quadratic, and a 249 s track needs ~10 GB of attention
      matrix on a 15.9 GB machine.
      **What it does buy, inside the covered 69%:** the words become *correct* rather than guessed,
      and timings sharpen from whisper's coarse spans to wav2vec2's ~20 ms frames — which is exactly
      what syllables-per-bar and on/off-beat placement need. Closing the 31% needs **a windowing layer
      we build**, on top of whisperX.
      Two further corrections to this section's assumptions: there is **no `sr` alignment model**
      (`hr` is the reachable proxy, and `load_align_model` raises on an unknown code, so passing
      `DEFAULT_LANGUAGE = "sr"` would crash); and **`lyrics.db` holds none of our own material** —
      1425 songs, all `corpus='genius-pro'`, `language` NULL on every row, and **no audio join key**.
      "The lyrics are already known" is true of the *artist* and false of the *database*.
      Alignment-only genuinely needs **no HF token** (verified: the alignment checkpoint is ungated,
      the gated repo is diarization) — but it does **not** avoid pip-installing `pyannote.audio`,
      which is why the recommendation is a sidecar venv. `specs/2026-07-15-oss-integration-map.md`'s
      risk row should be split accordingly: "no token" verified, "avoids heavy deps" false.
- [ ] `[USER DECISION]` Is 69% acceptable for flow-analysis v1 on the *corpus*, given our own tracks
      should go the forced-alignment route instead?

---

## P4 — Realise value already paid for  ⏱ days

Two capabilities are built and **unconsumed**:

- [ ] **Sections** have been emitted since #048; nothing reads them. T7 Sample Forge auto-sectioning
      is the payoff and is still unwired (it was deferred in #018 precisely because the dossier
      emitted none — that reason is gone).
- [ ] **flow_analyzer v2.** The beat grid (M3) and word timings (M5) now both exist, which is exactly
      what syllables-per-bar and on/off-beat placement need. Today `flow_analyzer` still derives
      "flow" from syllable counts of *text*, with no notion of when a word lands.

> **Design constraint, measured — do not skip.** `Word.probability` must **not** be used to weight or
> gate timings. The backend-default run reported **0.836 mean word probability** while dropping 43%
> of the track and looping inside a 36 s block. It measures the decoder's certainty, not its
> correctness. Use `decode_settings` + coverage for trust instead.

---

## P5 — Hygiene, opportunistic

- [x] ~~**debt 1c** (`min_silence` in `PauseRemovalStage`)~~ **FIXED 2026-08-31.** The stage
      concatenated `librosa.effects.split`'s intervals straight together, dropping *every* gap
      however short; `min_silence` was read only when building `removed_regions`, so it changed the
      report and never the audio. The report was the tell — it had always claimed
      `"kept": min(duration, max_keep)` for behaviour the code did not implement. Now: a gap below
      `min_silence` is preserved whole, one above is truncated to `max_keep`, and the retained audio
      is the original room tone rather than inserted zeros. The weakened test (`time_removed < 0.25`
      with a TODO) was restored to its intent, plus a guard asserting two `min_silence` settings
      produce different durations — the assertion whose absence let this survive.
- [ ] **Migrate the five `TOOLSHOP_DATA_DIR` resolvers** (`backup`, `remix_adapter`, `remix_cli`,
      `stems_cli`, `video_cli`) onto `toolshop/paths.py` — **each when its lane is next touched
      substantially**, per D12. Never as a repo-wide move.
- [x] ⚠️ **STALE — DO NOT ACT ON THIS ITEM. Superseded by `CHANGELOG.md` #053 item 5 the same day it
      was written, and by `pyproject.toml:29-48`, which read "protobuf must be >= 5.x. Keep it at
      7.36.0."** Pinning *down* to 4.21.2 **breaks stem separation**: `mdx_separator` imports `onnx`,
      which needs `google.protobuf.runtime_version`, absent before 5.x — the vocal-swap lane dies at
      its first stage. `classla`'s pin is the one deliberately violated. This stale paragraph misled
      the orchestrator *and* a subagent on 2026-09-01 before either checked `pyproject.toml`; see
      `JOURNAL.md` `J-002` and `J-017`. Kept, struck through, rather than deleted — the wrong belief
      stays visible. Original text follows.
      ~~`[USER DECISION]` **protobuf conflict.** **RESOLVED 2026-08-31 — pinned back to 4.21.2.**~~
      The constraints are **mutually unsatisfiable**: `classla==4.21.2`, `onnxruntime>=4.25.8`,
      `onnx-weekly>=6.31.1`. No version satisfies all three, so one is always violated — and at
      4.21.2 (the state predating the ASR install) it was already onnxruntime's. Note `ctranslate2`
      does not depend on protobuf at all, so it was never the package at risk.
      **Verified by running the work at BOTH versions**, not by reading metadata: onnxruntime parses
      a real 67 MB `.onnx` (stem separation), ctranslate2 runs real inference (identical output,
      `sr` p=1.00), classla and audio-separator import — all green either way. 4.21.2 kept because it
      honours the only *hard* pin. Recorded in `pyproject.toml`.

---

## Decisions blocking work

| # | Decision | Blocks |
|---|---|---|
| 1 | Which Suno track + who records the take | **P0 — the highest-value item here** |
| 2 | DR target: external drive / cloud / both | P2 |
| 3 | Is 69% transcription coverage acceptable for flow v1 | P3, P4 |
| 4 | protobuf: pin back, or accept the violated classla pin | P5 |

## Running elsewhere

Two defects were found in passing and are being fixed in separate sessions:

- `mastering_tool/stage_clip_limit.sh` loses 32-bit float at the limiter, so `_MASTER_32f.wav` is
  mislabeled and the 16-bit deliverable dithers already-quantized audio. **Affects every master the
  tool has produced.**
- `production_analyzer._analyze_single_file` raises `NameError` on every call; the surrounding
  `except` swallows it and `analyze_directory` silently returns zero fingerprints.
