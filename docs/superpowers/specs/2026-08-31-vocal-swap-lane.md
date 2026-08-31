# Vocal-swap lane — design

**Status:** built, tested, **not yet verified on real material end to end**
**Code:** `toolshop/vocal_swap/` · **CLI:** `toolshop vocal-swap` · **CHANGELOG:** #052

## The job

Two tracks in, one mastered track out: a Suno track whose AI vocal is replaced by the artist's own
recording.

```
suno track (full mix)  +  vocal take
   → instrumental        (stem separation, or supplied)
   → vocal prep          (optional cleaning, HPF, edge fade)
   → align               (offset; drift and ambiguity checked)
   → mix                 (LUFS-matched sum, optional ducking, headroom preserved)
   → premaster gates     (M4 — refuses to master a broken premaster)
   → master              (mastering_tool/master_pipeline_v3.sh via WSL)
   → verify              (measured LUFS/TP vs the profile's own targets)
```

## Why staged, and why resumable

Separation costs tens of minutes; mastering is a separate process in another OS. A single function
that redid separation whenever a mix balance changed would not be usable. Every stage writes an
artifact and a manifest entry (`manifest.json`, flushed per stage, written atomically via
`.tmp` + `replace`), and a rerun reuses any stage whose recorded outputs still exist on disk. This
is `toolshop/batch.py`'s resume discipline applied to the stages of one track.

`preflight` is deliberately **never** resumed: the environment can change between runs, and that is
what preflight exists to catch.

## The three refusals

A pipeline that always emits a file is not robust — it is quiet. This one stops at:

| stage | condition | override |
|---|---|---|
| preflight | unreadable input, empty file, preset with no instrumental, unknown profile, missing package, unusable WSL | fix it, or `--skip-master` for the WSL case |
| align | alignment untrustworthy (low confidence, ambiguous peak, or measured drift) | `--offset-seconds`, or drop `--require-alignment` |
| premaster | M4 gates return FAIL | `--master-on-gate-fail` |

Preflight reports **all** problems in one message. Five mistakes should cost one run, not five.

## Alignment — the part that is genuinely hard

### What you align *against* matters more than how

MEASURED 2026-08-31 on real Serbian material (`Srpskki Istocnicci - Borba 015`, 4:09), where the
**true offset is exactly 0** because the instrumental and the vocal were separated from one file:

| reference | offset returned | confidence | margin | verdict |
|---|---|---|---|---|
| instrumental | **+1.416 s — wrong** | 0.107 | 0.005 | ambiguous, **refused** |
| another vocal of the same performance | 0.000 s — correct | 1.000 | 0.789 | trustworthy |

A rap vocal's onsets do not track an instrumental's: the vocal places syllables between the beats
and falls silent for whole sections, so the shared rhythmic structure the correlation depends on is
thin. The estimator got it wrong by 1.4 s — **and said so**, which is the system working.

The fix costs nothing: separation already produces the Suno track's *own* vocal stem, and two vocals
of the same song share syllable placement directly. `align_reference` defaults to `auto`, which uses
that stem when it exists and falls back to the instrumental with a warning attached to the stage
message.

**Caveat, stated plainly:** the vocal-vs-vocal row above compares two separations of the *same*
performance (they differ by 0.0045 peak), so it demonstrates the absence of systematic bias, **not**
that the method works on two genuinely different takes. No such pair exists in the corpus yet. The
reference actually used is always recorded in the manifest.


Two cases hide behind "align the vocal":

1. **Same-instrumental take** — one constant offset fixes it.
2. **Independent performance** — no offset can fix it; it needs stretching or re-recording.

This module solves (1) and *detects* (2). Three numbers are reported, and all three are needed:

### `confidence` — peak correlation of onset envelopes

Onset envelopes rather than waveforms, because a vocal and an instrumental share no waveform
structure; what they share is rhythm. Hop 512 at 22050 Hz gives ~11.6 ms resolution.

### `peak_margin` — gap to the best *distinct* rival peak

**Confidence alone is a trap on periodic music.** MEASURED 2026-08-31, a 120 BPM click train
displaced 0.75 s:

| lag | correlation | |
|---|---|---|
| −11 frames | **0.9173** | ← winner |
| −54 | 0.9135 | |
| +11 | 0.9012 | |
| **−32** | 0.8972 | ← **the true offset** |

The peaks sit one beat apart and the wrong one won by 0.02, at a confidence of 0.92. Rap
instrumentals are strongly periodic, so this is the *normal* case, and it is precisely how a vocal
ends up a bar out. A small margin means "several placements fit equally well" — declare the offset
instead of trusting one.

### `drift_seconds` — head and tail aligned separately

Tempo comparison cannot do this job. MEASURED: `librosa.beat.beat_track` read two click trains of
**identical rhythm** (140 vs 70 BPM — the same performance at half time) as 143.55 and 69.84, a
**2.7% error on identical material**. Any tolerance tight enough to catch a real mismatch rejects
good takes. Drift measurement resolves ~12 ms instead:

| tempo difference | confidence | drift | caught by |
|---|---|---|---|
| 0.2% | **0.491 — passes** | −70 ms | **drift only** |
| 0.4% | 0.215 | −116 ms | both |
| 1.0% | 0.091 | −302 ms | both |
| 2.0% | 0.131 | unmeasurable | confidence only |

The two instruments cover different bands and neither covers both. Between them every case in the
sweep ends `trustworthy = False`.

Drift needs ≥12 s of material and both window correlations above 0.25; below that it reports
`None` and `mismatch_basis` falls back to `"tempo"` — reported as unknown, never as zero.

## Mix

Gain staging is in **LUFS, not peaks**: a compressed vocal and a sparse instrumental can share a
peak and be 6 dB apart perceptually. The vocal is placed a stated number of LU relative to the
instrumental (default +1.5, a starting point to bracket per track, the same caveat
`family_policy.sh` attaches to its genre presets).

The bus is left at **−6 dBFS with no compression or limiting**. The mastering chain expects headroom
and an intact crest factor; anything done here to make the premaster sound finished is work the
limiter then fights, and it would fail M4's own crest and PSR gates.

A vocal longer than the instrumental **extends** the output and reports `vocal_overhang_seconds`.
Silently truncating a take is worse than a tail of silence.

Silence is handled explicitly: if either source measures −inf LUFS, the vocal gain stays at 0 dB and
says so in the record, rather than applying an infinite gain.

### The edge-fade finding

`sosfiltfilt` pads by reflection, so a take ending mid-waveform rings at the pad boundary. MEASURED:
a 1 kHz tone at exactly 0.300 peak returned from an 80 Hz high-pass at **0.449 in its final 11
samples**, while the interior was correct to five figures. Bus gain is peak-driven, so that
inaudible artefact set the whole premaster 3.5 dB low. The fade is sized from the cutoff (two
periods — 25 ms at 80 Hz), because a flat 5 ms fade still left +1.0 dB.

## Mastering bridge

The engine is `master_pipeline_v3.sh`, not the tray EXE — the EXE is a GUI wrapper around it.

Path translation is the whole risk: the script runs inside WSL, and a Windows path handed to it
fails deep inside ffmpeg with an error that looks like an audio problem. `to_wsl_path` converts once
at the boundary and is idempotent; `check_environment` proves WSL, ffmpeg and the script's
translated path are all reachable *before* a long run starts.

**A zero exit code with no deliverable is treated as failure.** "Succeeded and produced nothing" is
the failure mode that would otherwise be reported as success.

`verify_master` measures the delivered 16-bit file and compares it to the profile's targets:
`pass` within 1.0 LU and under the true-peak ceiling, `flag` within 2.0 LU, `fail` beyond. The
targets table mirrors `family_policy.sh` only to fail fast on a typo — the script stays the
authority.

## Verified end to end

`Srpskki Istocnicci - Borba 015` (4:09), `serbian_drill` profile, offset declared 0:

| stage | time | result |
|---|---|---|
| preflight | 0.0 s | ok |
| mix | 12.3 s | vocal +1.8 dB to sit +1.5 LU over the instrumental |
| premaster | 6.1 s | **FLAG** — phase, peak, crest and DC all PASS; only PSR 9.03 (spec ≥ 11) |
| master | 116.7 s | 32f / 16-bit / 320 MP3 delivered |
| verify | 2.7 s | **pass** — **−8.698 LUFS** vs target −8.5, TP **−1.371 dBTP** under the −1.0 ceiling |

**~138 s/track excluding separation.** The swap itself is not an overnight job; only the separation
stage in front of it is. Sample peak landed at **−6.023 dBFS** against the −6.0 bus target, so gain
staging is accurate on real audio and not only on tones.

PSR 9.03 sits with the 8.98 and 8.16 measured on the S4 premasters in #050, where the conclusion was
that the *material* is under-dynamic rather than the chain. That is upstream of this lane.

## Open / not verified

- **The take was a stem standing in for a recording.** Instrumental and vocal came from one file, so
  the alignment stage was handed a declared offset rather than solving a real one. **Aligning two
  genuinely different performances is the one path still unverified on real input** — and it is the
  path `--align-reference` exists for.
- **No min/track number for the separation stage** under this lane; it was skipped via
  `--instrumental`. The registry's standing figure is ~30 min/track for the default MDX preset.
- `DEFAULT_MIN_PEAK_MARGIN` and `DEFAULT_MIN_CONFIDENCE` are **reporting thresholds, not calibrated
  ones** — no labelled set of real takes exists yet. Both numbers are always emitted so a caller can
  judge directly.
- Ducking defaults to off. It is implemented with a per-sample Python envelope follower, which is
  fine at these lengths but is the first thing to vectorise if it is ever used by default.
- Time-stretch uses librosa's phase vocoder — adequate for small corrections, audibly poor beyond
  about ±6%. It is opt-in (`--allow-time-stretch`) and only acts when drift was actually detected.
