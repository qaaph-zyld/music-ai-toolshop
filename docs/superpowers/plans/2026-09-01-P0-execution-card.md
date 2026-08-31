# P0 execution card — prove the swap on a real recorded take

> **Ready to fire.** Every command below was checked against the live CLI surface on 2026-09-01
> (`toolshop vocal-swap run --help`), not copied from a plan — `J-002` is what happens when a plan is
> trusted over the code. The only missing input is **a recorded take**.
> Journal range reserved for this run: **`J-030`–`J-039`**.

## Why this is still the highest-value item

The lane is verified end to end, but with a **stem standing in for a recording** — instrumental and
vocal came from the same file, so alignment was handed `--offset-seconds 0` and never solved a real
problem. Alignment is also the component that measured *weakest*: on real material with a true offset
of exactly 0, aligning against the instrumental returned **+1.416 s** and correctly refused itself
(`J-000c`). Everything else in the lane is proven. **This is the one path that is not**, and it is
the difference between a lane that works and a track that exists.

## Before recording — the thing that killed the last attempt

`Na tebe sam` failed for a reason worth internalising, because it is a **recording** decision, not a
software one, and no flag can rescue it:

- Its tempos **matched exactly** — 129.2 BPM instrumental, 129.2 vocal.
- Its arrangements did not. The take sang across **150.56 s** where the Suno vocal sang across
  **185.48 s**. Per-window lags after applying the offset ran `-0.09 / -15.09 / +8.10 / -13.56 / -6.25`
  seconds: the opening aligned and everything after it drifted apart.
- **No offset and no uniform stretch can fix that.** The 1.232 ratio needed would compress the
  delivery 23%, far past the ~6% a phase vocoder survives.

> `unverified — source: CHANGELOG.md #053, item 2.`

**So: record over the Suno track you intend to use, following its arrangement — same sections, same
number of bars, same entry points.** Matching tempo is not sufficient. Sixteen bars is enough; a
whole take is not required for this to count as proof.

## The run

Do **not** pass `--instrumental`. Letting separation run is the point twice over: it is the
configuration `--align-reference auto` has never been exercised in (auto prefers the separated Suno
**vocal** stem, which is the reliable reference), and it is the only way to collect the **separation
min/track** figure the last e2e run skipped.

```bash
cd /d/Projects/Music-AI-Toolshop && ./.venv/Scripts/python.exe -m toolshop.cli vocal-swap run "<suno>.mp3" "<take>.wav" --profile serbian_drill --align-reference auto --json
```

Time it. Expect roughly **4–5 min for separation** plus **~2.5 min** for everything downstream.

> Separation measured at 3.9–4.5 min/track on the `karaoke` preset; downstream ~138 s/track.
> `unverified — source: CHANGELOG.md #053 and docs/superpowers/STATUS.md.`

**If the take starts more than 30 s after the Suno vocal**, widen the search — `--max-offset`
defaults to **30**, and an offset outside that window cannot be found, only mis-found.

## What to capture — this is the deliverable, not the audio

`DEFAULT_MIN_PEAK_MARGIN` and `DEFAULT_MIN_CONFIDENCE` are currently **uncalibrated against a real
recorded take**. This run is the calibration data. Record every number, then **judge the result by
ear and write down whether the numbers agreed with your ears.** That correspondence is the whole
point; a passing number that sounds wrong is the finding, and so is a refused number that sounded
fine.

| Capture | From | Why it matters |
|---|---|---|
| `offset_seconds` | alignment | The answer itself. |
| `peak_margin` | alignment | **Carries the verdict**, not confidence — `J-000a`. On `Na tebe sam` it read 0.0009, i.e. picking at random. |
| `confidence` | alignment | Kept for the record. It peaked **0.9173 on the wrong lag** in the click-train test. |
| `drift_seconds` | alignment | The only thing that catches a 0.2% tempo difference; confidence reads 0.491 (passing) while the take drifts 70 ms. |
| `tempo_confidence` | beat tracking | Below **0.30** the tempo is the tracker's prior, not data — `beat_track` returned 117.4538 for two unrelated stems *and* a synthetic 120 BPM grid. |
| which reference was used | alignment | Whether `auto` actually got the vocal stem or fell back and warned. |
| separation wall time | your stopwatch | The missing min/track. Full track only — a clip result exaggerates fixed overhead (`J-000g`). |
| 6 premaster gate verdicts | M4 gates | PSR is the one that flags; the fix for a low PSR is **upstream in the mix**, not in mastering. |
| master verdict, LUFS, dBTP | verify stage | Target −8.5 LUFS `serbian_drill`, ceiling −1.0 dBTP. |

## Then

- **If it lands** — the lane is done, the alignment thresholds have their first real calibration
  point, and there is a track to play. Write `J-030` with the numbers and your ear's verdict side by
  side.
- **If it misaligns** — `--offset-seconds <n>` is the escape hatch; measure the offset by hand and
  pass it. Then **capture the failing case as a fixture**, because a real take that defeats the
  estimator is worth more to this repo than one that doesn't. Write it up as a refuted expectation.
- Either way: `J-030`+ in `docs/superpowers/JOURNAL.md`, and a CHANGELOG entry only once the code
  and the record match.
