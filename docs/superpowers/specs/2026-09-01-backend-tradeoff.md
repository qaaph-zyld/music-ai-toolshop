# Spec — `_advanced_analysis` vs `_basic_analysis`: what the advanced backend actually buys

> Design/decision note. Written 2026-09-01 by Wave 2 Agent C, following up J-020–J-029.
> **Read-only investigation. No code was written, no analysis or batch job was run, nothing under
> `data/` or `results/` was modified.**
> Every number is first-hand from the corpus and the source unless tagged
> `unverified — source: <path>`, per AGENTS.md.
>
> Companion findings: `docs/superpowers/journal_inbox/agentC.md`, entries **J-040**–**J-049**.
> Prerequisite reading: `specs/2026-09-01-dossier-schema-v2.md` (Wave 1), whose **Open Question 1**
> this note answers.

---

## Recommendation

**Option (a), narrowed — port the four field-groups into `_advanced_analysis`, and switch off three
of the five advanced capability flags at the same time.** Call it **(a′)**.

The premise behind the question was that advanced is the "richer backend" and basic the fallback, so
the choice is between richness and the new fields. **That premise does not survive the corpus.** Of
the seven fields only advanced emits, one is a literal constant, two are near-constants produced by
defects, and a fourth is a restatement of `duration_seconds`. The honest headline is the one the brief
invited:

> **The advanced backend provides substantially less than assumed. Its unique output is one useful
> block (`chord_progression`), two useful scalars (`tuning_offset`, `onset_strength`), two useful
> `effects` sub-fields — and four field-groups that carry no information about the track.**

But that is *not* an argument for option (c). Advanced's small real yield is still non-zero, it is
already on disk for 221 tracks, and — decisively — `chord_progression` is the evidence that refutes
the `mode` defect (J-043). Meanwhile `_basic_analysis` today contains a live `NameError` in all three
of its error handlers (J-046) and has produced **zero** corpus dossiers (J-040), so (c) is a switch to
unexercised code, not to a validated path.

### What (a′) is, concretely

| Change | Why |
|---|---|
| Add `beat_grid`, `structure`, `premaster` and the K-S key block to `_advanced_analysis` | One emitter produces everything; fixes the CLI and every future run, not just M6 (Wave 1's own recommendation) |
| K-S key reads `features["chroma"]`, which is **already computed and currently discarded** | Zero extra compute — J-048 |
| Stop passing `separation="hpss"` | 221/221 identical constant — J-041 |
| Stop passing `instruments=True` | ML path dead, heuristic bug-driven, 82.4% identical label set — J-042 |
| Stop passing `notes=True` | 22.9% floor artefact, constant duration, loudness-as-confidence — J-044 |
| Keep `chords=True` and `effects=True` | The chord block is musically plausible and refutes `mode`; 2 of 6 `effects` fields are sound |
| Drop `effects.rt60_seconds` at the schema level, or tag it | r = 0.946 with `duration_seconds`; median 200 s — J-045 |
| Fix `logger` (one import line) **before** anything else | Live `NameError`; the ported stages need working handlers — J-046 |

### What it costs — stated plainly

1. **It edits the emitter the corpus batch actually uses.** `_advanced_analysis` is the higher-blast-radius
   of the two. Mitigation: the change is purely additive at the top level — no v1 key changes name,
   position or type, so the four consumers Wave 1 enumerated
   (`generate_crhymetv_catalogue.py:234`, `run_reverse_engineering_batch.py:126,171`,
   `toolshop/bpm_adapter.py:96`, `toolshop/cli.py:1570`) keep working.
2. **Two of the four ported stages are genuinely new compute and are unmeasured.** `key` is free and
   `beat_grid` near-free (J-048), but `structure.segment_track` and `premaster.analyze_premaster` are
   additive. AGENTS.md requires a measured min/track on this machine before merge. **There is none,
   and I did not produce one** — see Cost.
3. **It leaves the vendored `feature_extractor.py` untouched**, which is Wave 1's Open Question 2
   recommendation: stop *using* the broken `key`/`mode`, do not patch upstream. The consequence is
   that the broken code stays live for any other caller of `wav_reverse_engineer`.
4. **Dropping `instruments` invalidates a field already published downstream.**
   `run_reverse_engineering_batch.py:224` writes instrument labels into all 221 `recipe.md` files.
   Those are already stale from the `mode` defect and are in the v2 spec's Stage C regeneration; this
   adds one more reason, not a new job.
5. **`chord_progression` is kept as a carried-forward descriptor, not as ground truth.** It uses the
   same fixed `> 0.5` chroma threshold as the broken `mode`, and its "minor" label actually means
   "major third *and* minor third both present" (`feature_extractor.py:225-233`). It is better than
   `mode` and musically plausible; it is not a chord recogniser we should trust downstream.
6. **The savings from dropping three flags are unmeasured.** J-049 shows the structural reason they
   should be large (a whole HPSS pass, a full-track `librosa.pyin`, and up to 5228 `librosa.yin` calls
   per track), but **how much** is not established and must not be quoted as if it were.

### Rejected, with the reason

**(b) Run both backends and merge — rejected, and it is not the cheap option it appears to be.**
It pays advanced's measured ~10 h (J-047) *plus* basic's unmeasured cost, to obtain field-groups that
J-041/J-042/J-044/J-045 show carry no information. Worse: **both emitters produce `key` and `mode`,
with the same names, the same two-element value set, and contradictory semantics.** A merge must
choose — which means (b) reproduces the exact §4 collision the v2 spec spent a section resolving,
except now inside the migration step where it is invisible. (a′) makes that choice once, in one place,
in code.

**(c) Switch the batch to `basic` — rejected as stated, though closest to right in spirit.**
It is the option most aligned with the evidence about what advanced is worth, and if the only goal
were the four new fields it would win. It loses `chord_progression` (the one block that both carries
signal and refutes `mode`), `tuning_offset`, `onset_strength`, `effects.spectral_tilt_db_per_decade`
and `effects.loudness_range`. And it cannot be taken today at any price: J-046 puts a `NameError` in
all three of `_basic_analysis`'s error handlers, J-040 shows no corpus file was ever produced by the
current version, and the two tests that touch the path mock the function out entirely. **Its cost is
also unknown**, so it cannot even be argued on speed.

---

## Field-Level Diff

Established two ways, because **the two ways disagree and the disagreement matters** (J-040).

### On disk — and why it is the wrong diff

The corpus's single `basic_librosa` dossier is **pre-M1 output**: 11 keys, 464 bytes, written
`2026-07-15T21:35:04`, with no `beat_grid`, `structure`, `premaster` or `key_confidence`. **No file in
the corpus was produced by the `_basic_analysis` that exists today.** The on-disk side-by-side
therefore compares current-advanced against a stale fallback, and reports basic as a strict subset:

```
$ census over results/crhymetv_re/per_track/*/*_analysis.json   (222 files, 0 unreadable,
                                                                 *_voice_analysis.json excluded)
advanced: 221   basic: 1
only advanced : ['chord_progression','effects','instruments','notes',
                 'onset_strength','separation','tuning_offset']
only basic    : []
```

### In code today — the diff that decides the question

`toolshop/reverse_engineering_adapter.py`, `_basic_analysis` `:52-133` vs `_advanced_analysis`
`:137-210`.

**Shared (10 keys, both emit):** `file`, `duration_seconds`, `sample_rate`, `bpm`, `beat_count`,
`key`, `mode`, `spectral_centroid`, `spectral_bandwidth`, `harmonic_ratio`, `analysis_backend`.
*Same names, not the same provenance* — see the note below.

**Only `_advanced_analysis` (7):**

| Field | Real? | Evidence |
|---|---|---|
| `chord_progression` | **yes** — carry forward | 24 distinct chord names, 85.0% minor, `n` per track 0/12/145 (min/med/max), 9 tracks empty |
| `tuning_offset` | **yes** | `librosa.estimate_tuning`; 40 distinct values, range −0.38 → +0.22 |
| `onset_strength` | **yes** | mean onset envelope; range 1.19 → 2.34 |
| `effects` (6 sub-fields) | **2 of 6** | see Quality Signals |
| `notes` | **no** | 22.9% of 191,339 notes are the fmin floor; `duration` is the literal `0.1` for all of them — J-044 |
| `instruments` | **no** | ML path not installed; heuristic's vocal test has a `pyin` tuple bug; 82.4% share one label set — J-042 |
| `separation` | **no** | 221/221 byte-identical constant; the separated audio is discarded — J-041 |

**Only `_basic_analysis` (6):** `beat_grid`, `structure`, `premaster`, `key_confidence`,
`key_alternate`, `key_margin` — i.e. exactly the M1–M4 work, which is J-024 restated.

### The shared fields are not equivalent

Same key name, different quality on both sides:

| Field | `_advanced_analysis` | `_basic_analysis` |
|---|---|---|
| `key` | `argmax(chroma_mean)` (`feature_extractor.py:185-188`) — agrees with the backend's own modal chord root on **88/212** | Krumhansl-Schmuckler with confidence, margin and alternate |
| `mode` | `chroma_vals[key_idx] > 0.5` (`:190`) — **214 major / 7 minor**, contradicted by its own chords on 170/212 | K-S mode, gated on `key_method` being recorded (v2 spec §4) |
| `bpm` | plain `librosa.beat.beat_track` (`:120-122`) | `beatgrid.analyze_beats` — grid, downbeats, bar count, phase confidence retained |

So advanced is not "richer" on the shared fields either. On the three that matter musically it is
strictly worse, and one of them is a known live defect.

---

## What `wav_reverse_engineer` Actually Produces

The batch passes `effects=True, instruments=True, chords=True, notes=True, separation="hpss"`
(`run_reverse_engineering_batch.py:210-214`). **The brief's instruction to check the dossiers rather
than the flags is what this section is: all five flags are on, all five produce output, and three of
them produce output that is the same on every track.**

| Flag | Populated? | What it actually is |
|---|---|---|
| `separation="hpss"` | 221/221, **1 distinct value** | `separate_hpss` splits the audio, the adapter keeps `list(stems.keys())` and drops the arrays (`reverse_engineering_adapter.py:196-199`). Every dossier reads `{"method":"hpss","stems":["harmonic","percussive"]}`. A full HPSS pass to serialise a literal. |
| `instruments=True` | 221/221 populated, 1–4 labels | `panns_inference` is **not installed** → silent fall-through to a 5-label heuristic (`instrument_recognizer.py:6-13, 50-54`). Nothing in the dossier records that the ML path was skipped — the silent-fallback failure AGENTS.md's declarable-fallback rule exists for. 182/221 (82.4%) return the identical set `{drums/percussion, guitar/piano, vocals}`. |
| `notes=True` | 221/221, median 777 notes | Onset times (real) + a per-onset single-frame `librosa.yin` pitch that piles up at the floor + `duration = 0.1` hard-coded + `confidence` = segment loudness. |
| `chords=True` | 212/221 non-empty, 9 empty | Per-frame chroma template match, `>0.5` threshold, merged and filtered at 0.25 s. **The one advanced block with real per-track variation and musical plausibility.** |
| `effects=True` | 221/221, all 6 sub-fields | 2 sound, 1 a duration proxy, 2 dimensionally incoherent, 1 superseded by `premaster`. |

**And the cost is not spread across five distinct analyses.** Within one `_advanced_analysis` call the
backend runs **HPSS three times** and **CQT chroma three times** over the same audio, plus a full-track
`librosa.pyin` at `hop_length=256` — the most expensive single call in the backend — solely to compute
the `voiced_ratio` that J-042 proves is broken (J-049).

---

## Quality Signals & Suspicious Distributions

The brief's rule — *a distribution nearly constant across 221 different songs is evidence of a bug, not
a finding about music* — found four more instances beyond the 215/7 `mode` split.

### 1. `mode` is refuted by the same dossier's own chord block

`mode` and `chord_progression` are computed from the same `chroma_cqt` with the same `> 0.5` threshold
inside the same module. They give opposite answers:

```
mode field:        major 214 / minor 7          (96.8% major)
chord entries:     minor 3315 / major 585       (85.0% minor)
per-track minor chord fraction:  p25 0.706  med 0.909  p75 1.000
tracks whose chords are 100% minor:  70 / 212

per track, `mode` vs that track's own chord majority:   agrees 42   disagrees 170  (80.2%)
modal chord root == `key` field:                        88 / 212    (41.5%)
```

85% minor is the musically expected answer for a German drill/rap catalogue. 96.8% major is not. This
is corpus-scale, first-hand confirmation of J-025 **using the backend's own output as the control** —
stronger than the 7-of-8 sample H2-M1 was written from. J-043.

### 2. `effects.rt60_seconds` is `duration_seconds` in disguise

```
pearson(duration_seconds, rt60_seconds)  = 0.9458
spearman(duration_seconds, rt60_seconds) = 0.7923
rt60/duration ratio: min 0.346  med 1.183  max 2.316
rt60_seconds:  min 3.35   med 200.13   p95 611.08   max 3441.9   seconds
tracks with rt60 > 20 s: 219 / 221
```

A median RT60 of **200 seconds** is physically impossible — the most reverberant spaces ever measured
are ~15 s. `estimate_rt60` runs Schroeder backward integration over the whole song
(`effects_analyzer.py:21-38`); Schroeder integration requires an impulse response, and on a continuous
musical signal the EDC slope is set by track length. This is the near-constant test in its
*proportional* form: not one value repeated, but one value that is a linear function of a field the
dossier already has. J-045.

### 3. `instruments` — a near-constant produced by a verified arithmetic bug

`librosa.pyin` returns a 3-tuple; `instrument_recognizer.py:39` calls `np.isfinite(f0)` on the tuple,
which coerces to `(3, N)` with rows 2 and 3 finite everywhere. So
`voiced_ratio == (true_ratio + 2)/3`, floored at 0.667, and the vocals score
`min(1.0, 0.3 + 0.7 · voiced_ratio)` cannot fall below **0.7667**. Verified on a synthetic 50%-voiced
signal in `.venv`:

```
voiced_ratio AS WRITTEN     = 0.8401
voiced_ratio IF f0[0] USED  = 0.5202        (0.5202 + 2)/3 = 0.8401  exactly
theoretical floor 0.3+0.7*(2/3) = 0.7667
```

The corpus matches the prediction with no exceptions: `score[vocals]` **min = 0.80697** across 217
tracks — not one below the floor — and 82.4% of the corpus returns the same three labels. J-042.

### 4. `notes` — a quarter of the corpus is the detector's floor

```
total notes: 191339
C2 (== fmin 65.41 Hz): 43766 = 22.87% of all notes
tracks whose modal pitch is C2: 186 / 221
per-track C2 fraction: p25 0.157  med 0.232  p75 0.302  max 0.550
note frequency p05 = 65.237 Hz          <-- the 5th percentile IS the floor
frequencies at or below fmin: 35242 / 191339
note `duration` values seen: {0.1: 191339}     <-- one value, 191,339 times
```

The most literal near-constant in the corpus: a field with 191,339 samples and one distinct value.
J-044.

### 5. `effects`, field by field

| Sub-field | Verdict | Basis |
|---|---|---|
| `rt60_seconds` | **defective** | r = 0.946 with duration; med 200 s |
| `thd_ratio` | **dimensionally incoherent** | takes the loudest bin of a song's mean spectrum as "f0" and calls bins at 2f0…5f0 distortion — on music those are other notes. Median **0.512**; no released master has 51% THD |
| `compression_index` | **dimensionally incoherent** | `(1/crest)·(1/(var+1e-6))` (`effects_analyzer.py:76-84`) — unnormalised, units of inverse variance, range 4.47 → 194.68, p95 34.5 |
| `loudness_lufs` | **superseded** | real BS.1770, but measured on the **22.05 kHz mono downmix** `AudioProcessor.load_audio` returns (`audio_processor.py:34-40`); med −12.6. `toolshop/premaster.py:111-119` computes this correctly from the stereo file |
| `spectral_tilt_db_per_decade` | **sound, keep** | med −22.9, range −29.6 → −9.7 |
| `loudness_range` | **sound, keep** | med 6.3, range 1.08 → 23.3 |

### Fields that pass the test

For contrast — these vary properly across 221 songs and are not suspicious: `bpm` (69.8 → 184.6),
`spectral_centroid` (1248 → 3458), `spectral_bandwidth`, `harmonic_ratio` (0.21 → 0.96, 45 distinct
values at 2 dp), `tuning_offset` (40 distinct values), `onset_strength` (1.19 → 2.34),
`chord_progression`, and `key` — whose *distribution* across 12 pitch classes is unremarkable
(D 30, G 26, F# 26, …, B 6). **Note that `key` passes the distribution test and is still wrong**
(it agrees with its own chord roots on 41.5% of tracks): a plausible distribution is not evidence of
correctness, only an absent one is evidence of a defect.

---

## Cost

### Advanced — measured, from existing artifacts

The batch logs carry no timestamps and `batch_status.json` records no per-item timing (only
`started`, `finished`, and one aggregate `duration_seconds: 43708.1` spanning 2026-07-07 → 2026-07-16
across resumed sessions — not a per-track figure). But the `batch_offset141` run used `--no-stems` and
each track writes `<stem>_analysis.json` then `<stem>_voice_analysis.json`, so **differencing the two
file mtimes isolates the two stages**. 81 tracks, mtimes monotonic:

```
=== derived from file mtimes, results/crhymetv_re/batch_offset141 run (--no-stems), n=80 ===
advanced analysis    min 31.8   p25 93.5    med 114.2   mean 169.9   p95 547.5   max 1177.4   s
voice/effects        min 71.5   p25 211.3   med 249.1   mean 370.2   p95 1177.7  max 2497.5   s
RTF advanced         min 0.6    p25 0.6     med 0.7     p95 0.9      max 1.0     x
RTF voice/effects    med 1.5                                                     x
span: 12.10 h for 81 tracks  ->  8.96 min/track wall
longest track: dur 1632.2 s -> adv 1177.4 s (RTF 0.721)
```

**At RTF ≈ 0.7 against the corpus's 14.71 h of audio (J-021), `_advanced_analysis` alone is ≈ 10 h** —
comparable to, not negligible against, the ~13 h lyrics stage.

**This is a derivation from a production run, not a benchmark, and must not be quoted as one.** No
warm-up was discarded, no baseline was repeated, concurrent machine load is unknown, and each interval
includes the JSON write, `recipe.md` generation and a status flush. Treat it as an **upper bound on
advanced analysis, good to roughly ±20%**. It does satisfy one AGENTS.md check: the RTF is stable
across a 22× duration range (7 s → 1632 s) and holds on the 27-minute track, so it is not a
clip-inflated number.

### Basic — no measurement exists, and none is derivable

J-040 establishes that no corpus artifact was ever produced by the current `_basic_analysis`, so there
is nothing to difference. The 30–45 s/track figure is
`unverified — source: docs/superpowers/HANDOFF-2026-08-31.md:172`.

**I did not run it.** The brief forbids running analysis jobs, and presenting an estimate as a
measurement is the J-000g error. **What would have to be run**, stated so the next session can execute
it without re-deriving the design:

- Time `beatgrid.analyze_beats`, `structure.segment_track`, `premaster.analyze_premaster` and
  `key_detection.detect_key_from_chroma` **individually** over a stratified handful of corpus tracks
  in `.venv` — the per-stage split is what decides whether `structure` or `premaster` dominates, and
  `premaster` gate 5 is O(duration) with a heavy constant (`premaster.py:171-181`).
- Use the v2 spec §8.1 strata, and include the 1632 s track — a short-input measurement exaggerates
  anything with fixed overhead (AGENTS.md).
- Discard a warm-up run and repeat the baseline at the end; if the two baselines disagree by more than
  ~10%, the machine is not a stable instrument and no timing conclusion holds.
- Run it alone. Nothing else that measures time may run beside it.
- Also measure `_advanced_analysis` **with `separation`/`instruments`/`notes` off** — (a′) claims a
  saving there on structural grounds (J-049) and the claim is currently unmeasured.

**The one cost statement that is safe today:** advanced ≈ 0.7× realtime ≈ 10 h corpus-wide; basic
unknown; the delta between them unknown. That is enough to eliminate **(b)** — which pays both — and
not enough to choose between (a′) and (c) on speed alone. **(a′) is chosen on evidence quality, not
on cost.**

---

## Risks of Each Option

### (a′) — port into `_advanced_analysis`, narrow the flags · **recommended**

| Risk | Severity | Mitigation |
|---|---|---|
| Edits the emitter the corpus batch actually uses | medium | Purely additive at the top level; no v1 key changes name, position or type. Wave 1 §8.3's key-set identity check (`set(v1) − set(v2) − set(v2.legacy) == {}`) catches any drop |
| `structure` + `premaster` cost is unmeasured | **high — blocks merge** | AGENTS.md requires a measured min/track. Obtain it per Cost before the corpus run, not after |
| `logger` `NameError` (J-046) also breaks the ported handlers | high | One import line. **Must land first**, with a test that exercises a *raising* stage rather than mocking `_basic_analysis` away as both current tests do |
| Two emitters still drift | medium | (a′) reduces the divergence but does not remove `_basic_analysis`. Follow-on: make basic a thin subset of advanced, or delete it |
| `chord_progression` kept but only semi-trustworthy | low | Carry as descriptor, tag its provenance, never treat as ground truth. Its `min` label means "major third and minor third both present", not "minor chord" |
| Dropping `instruments` breaks a published field | low | 221 `recipe.md` files cite it; they are already stale from `mode` and already in the v2 Stage C regeneration |
| Vendored `feature_extractor.py` stays broken for other callers | low, accepted | Wave 1 Open Question 2's recommendation. Record it; do not patch upstream |

### (b) — run both and merge · **rejected**

| Risk | Severity |
|---|---|
| **Reproduces the §4 `key`/`mode` collision inside the merge step**, where it is invisible — both emitters produce both fields with the same names, the same value set and contradictory semantics | **decisive** |
| Pays advanced's measured ~10 h *plus* basic's unmeasured cost, for field-groups shown to carry no information | high |
| Permanently two emitters, two provenances, and a merge rule that must be maintained | high |
| The merged dossier's `analysis_backend` becomes meaningless — the only v1 schema discriminator (v2 spec §2.1a) | medium |

Its one genuine advantage — no edit to the emitter the batch uses — does not survive the collision.

### (c) — switch the batch to `basic` · **rejected as stated**

| Risk | Severity |
|---|---|
| `_basic_analysis`'s three error handlers all raise `NameError` (J-046); both tests that touch the path mock the function out | **decisive today**; one import line to fix |
| Zero corpus-scale exercise — no dossier was ever produced by the current version (J-040) | high |
| Loses `chord_progression`, the one advanced block with real signal **and** the evidence that refutes `mode` | high |
| Loses `tuning_offset`, `onset_strength`, `spectral_tilt_db_per_decade`, `loudness_range` | medium |
| Cost unknown, so it cannot even be justified on speed | medium |

If the `logger` fix lands, `_basic_analysis` gains real test coverage, and the user decides the chord
block is not worth an emitter edit, **(c) becomes defensible** — it is the option most consistent with
"advanced provides less than assumed". It is rejected on the balance of those three conditions being
unmet today, not on principle.

---

## What this changes in the Wave 1 spec

- **Open Question 1 is answered: (a), narrowed to (a′).** Wave 1 recommended (a) on the grounds of
  "one place, fixes the CLI and any future run too". That reasoning holds and is strengthened by
  J-048 — the K-S key port is free because `_advanced_analysis` already computes and discards exactly
  the 12-bin mean chroma `key_detection.detect_key_from_chroma` requires.
- **Open Question 2 is unchanged and confirmed:** do not patch the vendored
  `feature_extractor.py:190`; stop using its `key`/`mode`. (a′) does that.
- **New, not in the Wave 1 spec:** `separation`, `instruments` and `notes` should not carry into v2,
  and `effects` should carry only `spectral_tilt_db_per_decade` and `loudness_range`
  (`loudness_lufs` is superseded by `premaster`'s stereo measurement). This shrinks the v2 schema
  relative to §3.2's "carried through unchanged" list, which currently carries all seven forward.
- **New blocker, ahead of everything else:** the `logger` `NameError` (J-046). It is one line, but it
  is in the fallback path of the function every option touches.
