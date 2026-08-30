# H2 — Dossier v2: horizon plan + M1

**Date:** 2026-08-31 · **Author:** orchestrator
**Goal:** G1 — the keystone. *"The dossier is THE unit of knowledge the whole suite consumes."*
**Predecessor:** H1 CLOSED 2026-08-30 (#046). Roadmap v2 §H2, six milestones, one session each.

---

## Sequence, and why this order

| # | Milestone | Why here |
|---|---|---|
| **M1** | **K-S key/mode + chords with confidence** | **Fixes an active defect that is corrupting existing data.** No new dependencies. Smallest, highest-confidence win — start where the evidence is strongest. |
| M2 | Structure segmentation (self-similarity/novelty) | Unblocks T7 Sample Forge auto-sections, deferred since #018. Feeds M1's "chords grouped per section". |
| M3 | Beat grid + downbeats (JSON + MIDI click) | Independent; feeds T9's E5 universal pack. |
| M4 | Loudness/dynamics/spectral profile | Aligns with `mastering_tool`'s PREMASTER_ACCEPTANCE_SPEC — and S4 (#043) just produced real evidence about that spec's own gates (D11). |
| M5 | Lyrics via faster-whisper (int8 CPU) | Biggest new dependency and the largest install; do it once the cheap wins are banked. Also delivers T4-v1. |
| M6 | `dossier.json` schema v2 + recipe.md v2, regenerate 222 | Last by necessity — it serialises whatever M1–M5 produce. |

**M6 is the horizon's exit**, not M1. Nothing here is "done" until 222 dossiers regenerate against a
v2 schema.

---

## M1 — Krumhansl-Schmuckler key/mode

### The defect, measured (2026-08-31, 8 real tracks, 45 s each)

`toolshop/bpm_adapter.py` lines 48–56:

```python
chroma_mean = np.mean(chroma, axis=1)
key_idx = int(np.argmax(chroma_mean))          # defect 1
mode = "major" if chroma_mean[key_idx] > 0.5 else "minor"   # defect 2
```

**Defect 1 — tonic by loudness.** `argmax` of mean chroma returns the most energetic pitch class,
which is the tonic only by coincidence; in a lot of material it is the fifth or the third. There is no
key profile involved at all.

**Defect 2 — mode from absolute magnitude.** Modality is a *relationship* between scale degrees,
above all the third. This tests how loud the peak bin is. Measured across 8 tracks:

| Observation | Result |
|---|---|
| Reported `major` | **7 of 8** |
| Peak chroma range | 0.471 – 0.854 |
| The single `minor` | peak 0.471 — minor because it fell under an arbitrary threshold |
| A third-comparison heuristic disagrees | on **4 of 8**, calling them minor |

So `mode` is effectively **"major unless the peak happens to be low"** — a near-constant, not a
detection. For a catalogue that is overwhelmingly drill/trap (near-universally minor), reporting 7/8
as major is wrong in the direction that matters most. This is the roadmap's "G major vs Gm" defect.

**Note:** `toolshop/cleaning_stages.py::_detect_key` is a **second, independent** implementation whose
mode logic compares the minor third against the major third — crude, but musically meaningful. The
*better* heuristic already exists in the repo; the dossier path uses the worse one.

### Tasks

**1. K-S implementation.** Krumhansl-Schmuckler: correlate the normalised chroma vector against the
24 rotated major/minor profiles, take the best correlation. Return key, mode, **and a confidence**
(the roadmap asks for confidence fields, and a correlation score is one honestly).
Pure numpy — no new dependency.

**2. Report the runner-up.** K-S's classic weakness is relative-major/minor confusion (C major vs
A minor share a pitch-class set). Where the top two correlations are close, that is information the
dossier should carry, not hide. Emit `alternate_key` + the margin.

**3. Kill the duplicate.** One key detector, used by both paths. `cleaning_stages._detect_key` becomes
a call into it (per the D12 rule: fix the class, not the instance).

**4. Tests against known ground truth.** Synthesised material in known keys (a C-major triad/scale
must return C major, an A-minor one A minor), plus a relative-major/minor pair to pin the
disambiguation. **Not** "it returns something" — assertions against a known answer.

**5. Measure the change on real tracks.** Re-run the 8-track sample and report how many keys and modes
move. Expect a large mode swing; report it as measured, not as "improved" — I cannot claim accuracy
without ground truth for those tracks, and I will not.

**6. Close out.** CHANGELOG #047, STATUS, suite (bar: **991 passed / 2 skipped / 0 failed**), `doctor`
PASS, `closeout` (declaring the concurrent session's untracked files).

### Explicitly not claimed

Ground truth for the 8 sample tracks does not exist here. K-S is a well-established method and the
current code is demonstrably broken, but **"K-S output differs from the old output" is not the same
as "K-S is right"**. The honest deliverable is: a defensible algorithm, real tests against synthetic
ground truth, and a measured diff — not an accuracy claim I cannot support.

Chords-per-section is deferred to M2, which supplies the sections.
