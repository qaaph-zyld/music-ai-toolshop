# Goals vs Reality — 2026-08-31

**Author:** Orchestrator · **Evidence:** re-run locally this session, not relayed
**Measures:** `2026-08-19-goals-v2.md` (G0–G11) against what is actually true today
**Baseline:** the 2026-08-19 assessment, twelve days and 16 commits ago

---

## The headline

Twelve days ago the dossier — the artefact the goals call *"the unit of knowledge the whole suite
consumes"* — had **four fields that were decorative**. Not missing: present, plausible-looking, and
wrong. Nothing in the test suite or the health check could see it.

| field | what it actually was |
|---|---|
| `mode` | `chroma_mean[key] > 0.5` — how loud one bin is. Returned "major" for **7 of 8** tracks |
| `sections` | an invalid librosa call inside a silent `except` — **`[]` for every track ever analysed**, with `verse`/`chorus` labels from `i % 2` underneath |
| `beat_grid` | computed on every run and **thrown away**; only a count survived |
| premaster gates | **none of the six** measurable acceptance gates existed |

All four are now real, and each carries its own uncertainty. That is the single most important change
in the period, and it was invisible from the outside.

---

## Goal-by-goal

### G0 — Consolidated, honest baseline · ✅ **MET**

`closeout` mechanism live, `doctor` **Overall: PASS** on every check, every lane recorded, backup
verified at age 0d, and `ai_modules/` resolved by explicit decision (D6). **Every line of code in the
repo is now either exercised by the suite or explicitly shelved** — which was not true at any earlier
point in the project's history.

*Caveat, stated rather than hidden:* `closeout` reports a dirty tree, and it is not this work. A
concurrent session has been writing into the repo throughout and has modified a tracked file. All
staging here was by explicit path, never `git add -A`.

### G1 — Trustworthy analysis core · **H1 CLOSED · H2 four-sixths done · NOT yet met**

H1 (M1–M6) closed after being open since July. H2 milestones M1–M4 shipped. **M5 (faster-whisper
lyrics) and M6 (schema v2 + regenerate the corpus) are not started.**

G1's definition of done says *"dossier emits key, structure, beats, chords **and timed lyrics** with
confidence fields"*. Timed lyrics are M5. **G1 is not met, and will not be until M5 and M6 land.**

The honest sub-status:

| | |
|---|---|
| `doctor` OK with all models present | ✅ #041 |
| key, structure, beats, premaster with confidence | ✅ #047–#050 |
| timed lyrics | ❌ M5 |
| section boundaries feed Sample Forge automatically | ⚠️ **unblocked but unwired** — #048 made the dossier emit sections; nothing consumes them yet |
| measured min/track per stage | 🟡 partial — stems and mastering measured; the new dossier stages are not |

### G2 — Closed creation loop · **AHEAD, and untouched this period**

L1–L5 remain shipped. L6, the stalled orchestration waves 3–4, and the loop actually closing are all
where they were on 2026-08-19. No progress, no regression. Deliberate: the keystone took priority
(D5).

### G3 — Studio breadth, research-gated · **partially closed**

`ai_modules` opened generation ungated; that is now resolved — two modules removed, two shelved to
G9, two moved into `toolshop/`. melody-carrier gained a dependency extra and a `--require-advanced`
guard (#039). Mix chains (E2) unstarted; **R1 re-verified: pedalboard PR #476 is still open**, so VST3
on Windows still cannot be trusted.

### G4 — Session Bridge · **NOT STARTED, but materially cheaper**

E5 needs stems + marker MIDI + click. **The click now exists** (`--click-midi`, #049) and so does the
beat grid it derives from. The dependency that made E5 expensive is gone.

### G5 — Fleet and true DR · **NOT STARTED — and the DR gap is now precisely quantified**

The backup went from 28 days stale and covering the wrong asset set, to verified daily and provably
carrying what matters. But it is **still on the same physical disk as the source**, which is the
2010 Seagate holding everything. The Suno catalogue (3,426 tracks, 15.79 GB) is preserved locally and
is single-copy.

**This is the largest remaining unmitigated risk in the project.** It is not a Q2 nicety.

### G6 — Library intelligence at scale · **PARTIAL, unchanged**

Lyrics side done. Audio side — CLAP embeddings, similarity search, chromaprint dedup — untouched.

### G7 — Restoration + chains as daily tools · **NOT STARTED, but seeded**

`toolshop/production_analyzer` (moved out of `ai_modules` in D6) reverse-engineers processing chains
from variants. It imports, its 7 tests pass, and it is the natural seed for T8 when that lane opens.

### G8 — Platform and discipline hardening · **materially improved**

The gate has now been **run and passed at the end of every session in this period** — the criterion
was "ten consecutive sessions" and this is a real start on it. `AGENTS.md` gained three new rule
sections, each written against a failure that actually happened: **Lane discipline** (mislabelled
commits, uncollected tests, undeclarable fallbacks, backups verified by exit code), **Measurement
discipline** (warm up and repeat the baseline; verify at the scope of the claim; fix the class not the
instance; kill the watcher with the process), and **Package layout** (D12).

Model mirror + checksums now exist (#041). CI remains billing-locked; the local-pytest gate is the
formal substitute.

### G9 — GPU-tier readiness · **ON TRACK, shelf grew**

`musicgen` and `lora_finetuning` are now *on* the shelf rather than sitting in the tree violating the
CPU-only lock. R3 re-verified: ACE-Step 1.5 2B runs under 4 GB VRAM.

### G10 — Compounding daily use · **the honest gap**

This period made the tools *more correct*. It did not make them more *used*. No track was made with
them. The corpus did not grow. `G10` is the goal that ultimately matters and it is the one with no
evidence of movement — which is worth saying plainly rather than burying under twelve green
milestones.

### G11 — Visual delivery · **NOT STARTED, unchanged**

---

## What the numbers say

| | 2026-08-19 | 2026-08-31 |
|---|---|---|
| `toolshop doctor` | **FAIL** (model cache + backup) | **PASS**, every check |
| Test suite | 963 passed | **1067 passed**, 0 failed |
| Backup | 28d stale, **zero Suno coverage** | age 0d, verified, 6,925 files |
| Suno tracks local | 37 of 3,426 | **3,426 of 3,426** (15.79 GB, 0 failures) |
| Tracked files | 2,256 | 1,885 |
| Dossier fields that are real | 0 of 4 | **4 of 4** |
| Open decisions | D5–D12 | **none** |

---

## The pattern worth carrying forward

Six times in this period the same failure shape appeared, and it is the most useful thing learned:

> **A narrow check passes honestly, and a broad claim is drawn from it.**

- A 30 s clip showed a **1.40× speedup**; the full track showed **1.00×**. Cold cache, not compute (#042).
- One test file was clean, so debt 13b was declared fixed. **Six** modules had the bug (#044).
- The project resolved in the registry, so it was "registered". `session_brief` still could not see it — **three** maps, not one (#045).
- Two key detectors were found and fixed. There were **four**, and the missed one was the dossier itself (#047).
- `ai_modules/vocal_cleanup` was recommended for absorption on the strength of a promising signature. **It had never executed once** (#051).

Three of those shipped as false claims before being caught. The last two did not, because by then the
habit had changed from *checking the change* to *checking the claim*.

**The two rules that came out of it are now in AGENTS.md and are the durable output of this period —
more so than any single milestone.**

---

## What I would do next, in order

1. **G5's DR gap.** 15.79 GB of irreplaceable audio, single copy, on a 2010 disk. Everything else here
   is recoverable; that is not.
2. **M5 + M6**, to finish what G1 actually requires. M6 in particular: every field added this period
   exists only for tracks analysed *from now on* — the 444-dossier corpus still carries the old,
   partly-fabricated values.
3. **Wire the sections into Sample Forge.** #018's deferral is unblocked but unconsumed; the value is
   not realised until something reads them.
4. **G10.** Make something with it.
