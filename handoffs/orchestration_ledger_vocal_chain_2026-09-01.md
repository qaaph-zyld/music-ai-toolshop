# Orchestration Ledger — Vocal Chain Reverse-Engineering

**Started**: 2026-09-01 · **Orchestrator**: Opus 5 (does not code) · **Subagents**: sonnet, read-only in Wave 1
**Waves config**: `ORCHESTRATION/waves_vocal_chain.json`
**Goal (set via `/goal`)**: A measured reference vocal yields a renderable chain spec; applying that spec to a dry take moves the re-measured parameters toward the reference in a quoted A/B table; pytest exits 0; git status clean.

## Orchestrator's own pre-wave findings (first-hand, not delegated)

| Claim | Evidence | Status |
|---|---|---|
| Reverse engineering exists, twice over | `toolshop/reverse_engineering_adapter.py`; `projects/05-track-reverse-engineering/track_reverse_engineering/wav_reverse_engineer/` | verified by read |
| Vocal-specific analysis exists and is deep | `toolshop/voice_effects_adapter.py`, 1282 lines, 12 detectors (reverb, pitch shift, formant shift, compression, EQ, distortion, chorus, autotune, de-essing, vocoder, noise gate, delay) | verified by read |
| A per-singer profile measurer exists in the other repo | `music_toolshop_v2/analysis/voice_profile.py`, ~25 measured fields split target/consequence/uncalibrated | verified by read |
| A profile for the user's own voice already exists | `music_toolshop_v2/voice_profiles/nikola.json` — but SNR -1.16 dB failed its own 30 dB threshold, so every non-F0 TARGET field is `null` | verified by read |
| **Nothing consumes voice_profile output** | grep for `voice_profile|measure_voice_profile|voice_profiles` across `pipeline/ analysis/ evaluation/` returned zero consumers | verified by grep — Agent B re-verifying at wider scope |
| The vocal DSP that ships is hardcoded | `pipeline/corrective_eq.py:145` `_vocal_chain()` is a single 100 Hz highpass | verified by read |
| The renderer's raw material is present | `pedalboard` used in `toolshop/remix_adapter.py:438` and `pipeline/corrective_eq.py` | verified by grep — Agent B confirming install |
| Reference material exists on the PC | `track_inventory/tracks.db`: present=1 path matches — bonez 105, camora 600, gzuz 58 | verified by SQL |
| ...but thins out badly under real filters | non-instrumental name matches: ~18 / ~27 / ~3, mostly `(Feat. …)` guest verses; `file_hash` NULL on most | verified by SQL — Agent C building the defensible funnel |

**The gap in one line**: the analysis half is built and the synthesis half does not exist. There is no path from a measured parameter to a rendered chain.

## Wave status

| Wave | Name | Mode | Status | Gate |
|---|---|---|---|---|
| 1 | Capability & corpus census | 3 explorers, parallel, read-only | DISPATCHED | gate_after: true |
| 2 | Chain spec + extractor + renderer | 2 implementers, sequential | BLOCKED on wave 1 gate | gate_after: true |

### Wave 1 agents
| ID | Deliverable | Output file | Status |
|---|---|---|---|
| A | Measurement inventory — renderable parameter vs label | `ORCHESTRATION/wave_vc1/agent_a_measurement_inventory.md` | running |
| B | Render inventory — DSP blocks that can consume a parameter | `ORCHESTRATION/wave_vc1/agent_b_render_inventory.md` | running |
| C | Corpus census — usable references and own dry takes | `ORCHESTRATION/wave_vc1/agent_c_corpus_census.md` | running |

## Standing risks carried into this orchestration

- **Separation contamination.** Every reference vocal must be Demucs-separated first. Demucs leaves reverb tails, bleed and its own colouration. Any measured chain is the artist's chain *plus* Demucs. The only honest comparison is like-with-like: the user's take must traverse the same separation path before comparison, or the difference is an artefact. Not yet designed.
- **A mastered reference is not a vocal bus.** Bus compression, limiting and master EQ are baked into the full mix. What gets measured is the vocal *as printed*, not the chain as set. The deliverable must be framed as "match the printed result", not "recover the plugin settings".
- **mp3-sourced references cap the high band.** De-essing and air-band claims above the codec's cutoff are unsupportable. Agent C is quantifying this.
- **The user's own profile is currently void.** `nikola.json` nulled its own target fields on an SNR failure. A usable dry take may need re-recording — the same blocker P0 already carries.
- **Prior-session lesson applied**: a count check verifies *how many*, never *what*. The wave 2 gate will be a field-by-field A/B table, not a pass count.

## Merge log
_(orchestrator re-runs load-bearing claims before merging; nothing merged yet)_

## Wave 1 — run log

| Attempt | Outcome | Detail |
|---|---|---|
| 1 | **All three agents failed** | API 429, "session limit · resets 1am (Europe/Belgrade)", model `claude-sonnet-5`. Agents A and B died mid-read; C died before its first query. `ORCHESTRATION/wave_vc1/` was **empty** — nothing was written. |
| 2 | dispatched | Same three briefs, plus an explicit **write-incrementally** instruction: create the output file after the first read and append as findings land. |

**Lesson applied (already in the record, and it just cost a full wave):** *"An agent that batches its deliverables converts any interruption into total loss. Write fragments as findings land — a durability property, not just a quality one."* The wave-1 briefs did not carry that instruction; attempt 2 does. The prior session learned this for journal fragments and the rule was not generalised to agent deliverables.

## Wave 1 · Agent A merged — measurement inventory

**Handoff**: `ORCHESTRATION/wave_vc1/agent_a_measurement_inventory.md`

### Orchestrator spot-check (re-run before merging, not accepted from the agent)

| Claim | Re-verified? | Evidence I ran myself |
|---|---|---|
| `detect_eq.hp_cutoff_estimate_hz` is a **literal hardcoded string**, not measured | **YES — confirmed** | `voice_effects_adapter.py:543` reads `result["params"]["hp_cutoff_estimate_hz"] = "~150Hz"`. The 150 is the *threshold constant* from the line above (`freqs < 150`) echoed back as if it were a result. |
| `detect_compression.estimated_ratio` is one of three hardcoded strings | **YES — confirmed** | `voice_effects_adapter.py:~477/483/489` — crest-factor buckets assign `"8:1+"`, `"4:1"`, `"2:1"`. No threshold, attack or release is ever computed. |
| `_measure_shimmer` returns dB under a field named `shimmer_percent` | **YES — confirmed** | `voice_profile.py:789-799` returns `point_process.get_shimmer_local_db()` unconverted. Docstring says "percent". **Unit bug.** |
| Every `_derive_*` constant is asserted, uncited | **YES — confirmed** | `voice_profile.py:651-700` — `f0_min * 0.75`, `clamp(1 + dr/10, 1.5, 4.0)`, `p10 + (p90-p10)*0.3`. Docstrings state the formulas; nothing states where the numbers came from. |
| Only 3 of 12 detectors emit a continuous physical magnitude (`rt60_seconds`, `thd_percent`, `delay_time_ms`) | not independently re-run | agent's table; consistent with the four confirmations above |
| `estimated_semitones` is a signed **string**, not a float | not independently re-run | agent's claim, low risk either way — a parse step |
| `premaster.py` builds **7** gates, docstring says six | not independently re-run | cosmetic; does not affect this lane |
| 5 of 8 mix-chain essentials absent (stereo width/doubling, reverb pre-delay, sidechain, retune speed, level automation) | not independently re-run | agent's gap check |

### The finding that changes the plan

**`voice_effects_adapter.py` is a classifier, not a measurer.** Its surface reads like a parameter extractor — 12 detectors, a `params` dict per detector — but the `params` are mostly *labels dressed as values*. `"~150Hz"` is the most explicit case: a constant from the test condition, returned as though it were an estimate. A caller reading `params["hp_cutoff_estimate_hz"]` gets a number-shaped string that carries **zero information about the file**.

Same shape as the four defects the previous session found: *it looks like diligence*. A `params` dict, a confidence score and an `evidence` list are exactly what a real extractor would emit.

**Consequence for Wave 2**: the extractor cannot be a thin wrapper over these detectors. They are usable as a **gate** ("is there reverb here at all, and how confident?") but not as a **source of values**. The chain spec needs its own measurement layer for anything it intends to render. That is a larger Wave 2 than the wave design assumed — and it is better to know now than to discover it when the A/B table refuses to converge.

**Not a regression, and not the agent's discovery alone**: this code was written as a detector for a human reader, and it does that honestly (`evidence` strings are real measurements). The defect is only that its output shape invites machine consumption it cannot support.

## Wave 1 · Agent B merged — render inventory

**Handoff**: `ORCHESTRATION/wave_vc1/agent_b_render_inventory.md` (338 lines)

### Orchestrator spot-check (re-run before merging)

| Claim | Re-verified? | Evidence I ran myself |
|---|---|---|
| **`mastering_tool/tools/chain_dsl/` is an already-built generic chain renderer** | **YES — confirmed** | `schema.py:23-85` defines `HPF → EQ(bands) → Deesser → Compressor → Clipper → Limiter`, all `bypass=True` by default, composed in a `Chain` dataclass. `executors/pedalboard_exec.py` has `build_pedalboard()`, `render()`, `render_file()`. |
| It is tracked, not stray submodule content | **YES — confirmed** | `git -C mastering_tool status --short tools/chain_dsl/` → empty (tracked and clean). |
| pedalboard 0.9.24 in **both** venvs | **YES — confirmed** | ran both interpreters: `MAT venv: 0.9.24`, `v2 venv: 0.9.24`. |
| `HPF.slope`, `Compressor.knee_db`, `Limiter.lookahead_ms` declared but **silently unused** | **YES — confirmed** | `pedalboard_exec.py:51-90` — `build_pedalboard` never reads any of the three. Setting `slope=24` is accepted and silently discarded. |
| `corrective_eq._vocal_chain()` / `dynamics.vocal_chain()` fully hardcoded; `apply_dynamics`'s `profile` arg dead on every branch | not independently re-run | consistent with my own earlier read of `corrective_eq.py:145` |
| Only `saturation.resolve_saturation_params()` genuinely reads a profile, with `source="profile"\|"default"` provenance | not independently re-run | agent's claim — **this is the pattern the bridge should copy** |
| `voice_profile` consumers: still zero, at the wider two-repo scope | not independently re-run | corroborates my own narrower grep; agent also cites the project's own doc saying the same |
| pedalboard auto-detects channel axis; `vocal_swap/mix.py` is samples-first vs v2's channels-first; scipy/soundfile/pyloudnorm are **not** shape-agnostic | not independently re-run | flagged as the main integration cost |

### The finding that changes the plan — again, in the opposite direction

**The renderer is not missing. It already exists, and it is the right shape.** `chain_dsl` accepts exactly the parameters a vocal chain needs — per-band EQ freq/gain/Q, de-esser freq/threshold/ratio/width, compressor threshold/ratio/attack/release/makeup — and renders them through pedalboard.

So the corrected picture, after A and B together:

| Half | Status |
|---|---|
| **Render** | **BUILT** — `chain_dsl` + pedalboard 0.9.24 in both venvs |
| **Measure** | **PARTIAL AND MISLEADING** — `voice_effects_adapter` classifies rather than measures; 3 of 12 fields are real magnitudes |
| **Bridge (measure → Chain)** | **ABSENT** — nothing constructs a `Chain` from a measured file |

This inverts the Wave 2 estimate. The expensive half is not the renderer, it is **honest measurement of the parameters `Chain` already accepts**. The target is now concrete and finite: fill `Chain`'s fields from audio.

### Defect logged (small, real, in scope)

`pedalboard_exec.build_pedalboard` silently drops three declared schema fields. AGENTS.md's rule — *"fallback paths must be declarable"* — applies: a chain that cannot honour `slope` should say so, not accept the value and ignore it. Either wire them or raise. Candidate for a Wave 2 side-fix, **not** for a silent patch.

## Wave 1 · Agent C merged — corpus census

**Handoff**: `ORCHESTRATION/wave_vc1/agent_c_corpus_census.md`

### Orchestrator spot-check (re-run before merging)

| Claim | Re-verified? | Evidence I ran myself |
|---|---|---|
| Usable full mixes: **Bonez 8, Camora 5, Gzuz 0** | **YES — reproduced exactly** | Built the marker filter independently (incl. the `Instrumetal` typo, hyphenated `type-beat`, Demucs `_bass/_drums/_other` suffixes) and got `bonez 8 / camora 5 / gzuz 0`, null-duration `2 / 8 / 2`. Landing on the same three integers from an independently written query is the strongest evidence available here. |
| 100% of the usable set is **mp3** | **YES — confirmed** | same query returned `exts=['mp3']` for both non-empty artists; `[]` for gzuz. |
| RAF Camora's 600 is dominated by a **producer sample pack** | **YES — confirmed, and larger than reported** | `path LIKE '%camora%drum%kit%'` → **486 of 600 (81%)**. Agent said 79%; the discrepancy is filter shape, not substance. Name-matched only: 124. |
| The catalogue **does not cover `D:\Projects\music_toolshop_v2`** | **YES — confirmed, with the control the agent ran** | `path LIKE '%music_toolshop_v2%'` → **0 rows**, while the control `path LIKE '%d:\projects%'` → **8,872 rows**. The probe works; the absence is real. Agent correctly proved the probe before reporting the empty result — the exact discipline J-lesson demanded. |
| **Dry takes exist**: 39 × `Main Vokal ... .wav`, 32-bit float mono, 2026-08-26 | **YES — confirmed on disk** | `ls` of `music_toolshop_v2/data/ZELDI x ZA OVAJ GRAD/record 1 Project/Samples/Recorded/` → 39 files, Ableton raw-recording naming, timestamps 2026-08-26. |
| `D:\2026\GGxMONSTAH Project\GGxMONSTAH_MIXREADY_mono_dry.wav` exists | **YES — confirmed** | 20,736,044 bytes. |
| Nearly all usable references are `(Feat. …)` credits on Kontra K albums; Camora has **zero verified solo tracks** | not independently re-run | consistent with the sample rows I saw pre-wave |

### The decision this forces

**The binding constraint I expected is resolved, and a different one replaced it.**

- **Resolved — the "apply" side is unblocked.** 39 raw 32-bit-float mono takes from 2026-08-26 exist. P0's "blocked on a person with a microphone" does **not** block this lane. There is something to apply a chain to.
- **New binding constraint — the reference corpus will not support the stated goal.**
  - **Gzuz: 0 usable references.** Not "thin" — zero. Gzuz cannot be attempted from material on this machine.
  - **RAF Camora: 5, all guest verses on another artist's albums.** A chain measured there is *Kontra K's engineer's chain*, applied to Camora's voice. Attributing it to Camora is a category error.
  - **Bonez MC: 8, same shape.**
  - **All mp3 (192–323 kbps).** Every de-essing and air-band figure is capped by the codec, and those are precisely the bands that distinguish a modern rap vocal.

### The re-scope this implies — corpus comes OFF the critical path

The three artists are **not needed to build or prove the capability**. The honest validation is the one whose answer is known in advance — the same move that settled RT60 last session:

> Take a dry take. Apply a **known** `Chain` (HPF 90 Hz, comp 3:1 @ -18 dB, de-esser 6.8 kHz). Render it. Run the extractor on the render. **Does it recover the parameters that were just set?**

If the extractor cannot recover a chain it was literally handed, it will never recover Bonez MC's — and no amount of reference material fixes that. This makes Wave 2 self-contained, cheap, and falsifiable, and it defers the corpus problem to the point where it actually bites.

**Revised Wave 2** (was: schema + extractor + renderer; now:)
| Step | Deliverable | Gate |
|---|---|---|
| D1 | `Chain` round-trip harness: known chain → render → extract → compare | recovery error per parameter, in a table |
| D2 | Measurement layer for the `Chain` fields that fail D1 | each field recovers within a stated tolerance, or is declared unrecoverable |
| D3 | Side-fix: `build_pedalboard` honours or rejects `slope`/`knee_db`/`lookahead_ms` | test asserts a set-but-ignored field raises |
| D4 | *(optional, corpus-dependent)* apply to the 13 mp3 references, confound stated in the output | — |

**Wave 2 gate is the per-parameter recovery table, not a pass count.** (J-009: a count check verifies how many, never what.)

---

## WAVE 1 GATE — APPROVED 2026-09-02

**User decisions:**
1. **Wave 2 scope** → *Bridge first, synthetic proof.* Build D1–D3. The three artists come off the critical path.
2. **Target framing** → *Defer until D1 passes.* If the extractor cannot recover a known chain, the choice of reference target is moot.

**Consequence**: the reference-corpus problem (Gzuz 0, Camora features-only, all mp3) is **not solved and not being solved yet** — deliberately deferred, not forgotten. It returns as a live blocker at D4.

### One design distinction that shapes Wave 2

The round trip has **both** the dry input and the processed output. Real-world artist cloning has **only** the processed output. These are different problems and must not be conflated:

| Mode | Available | Difficulty | Where it applies |
|---|---|---|---|
| **Differential** | dry + wet | tractable — the difference *is* the transfer function | the round-trip harness |
| **Blind** | wet only | hard — must separate the chain from the performance | Bonez MC, and everything at D4 |

**Differential is the floor.** If the extractor cannot recover a chain when handed both sides, blind recovery is hopeless and the lane should stop. D1 therefore proves differential first, and only then reports what blind would cost. Skipping this ladder is how a project spends six weeks blaming its reference corpus for an extractor defect.

## Wave 2 — dispatched

| ID | Deliverable | Mode | Status |
|---|---|---|---|
| D1 | Round-trip harness + differential extractor; per-parameter recovery table | implementer | dispatched |
| D3 | Side-fix: `build_pedalboard` silently drops `slope`/`knee_db`/`lookahead_ms` | implementer | dispatched (independent of D1) |
| D2 | Real measurement for whichever `Chain` fields fail D1 | implementer | BLOCKED on D1's recovery table |

## Wave 2 merged — D1 and D3

### D3 — chain_dsl unwired parameters

| Claim | Re-verified? | Evidence I ran myself |
|---|---|---|
| pedalboard 0.9.24 supports **none** of `slope` / `knee_db` / `lookahead_ms` | **YES — confirmed** | `dir()` on instances: `HighpassFilter` exposes only `cutoff_frequency_hz`; `Compressor` only attack/ratio/release/threshold; `Limiter` only release/threshold. Docstring pins HPF at a fixed 6 dB/oct first-order roll-off. |
| 14 tests pass | **YES** | `pytest tests/test_chain_dsl_unwired_params.py -q` → `14 passed in 0.74s` |
| The submodule's own tests are **never collected** | **YES — confirmed** | `pytest.ini:2` is `testpaths = tests`; `--collect-only \| grep -c chain_dsl` → **14**, i.e. only D3's new parent-repo tests. `mastering_tool/tools/chain_dsl/test_chain_dsl.py`'s 5 tests have never run under the parent suite. Same class as the `ai_modules/` never-run tests AGENTS.md already names. **Reported, not fixed** — widening `testpaths` is a user decision. |

Outcome: all three now raise `UnsupportedParameterError` when set to a non-default value on an **active** stage; silent at default so existing callers are unaffected. `Limiter.lookahead_ms` is genuinely honoured on the *masterbus* path (Rust `open_DAW` consumes it) — so one schema field was wired on one executor and silently dropped on the other. `open_DAW` left alone (AGENTS.md: parked, needs sign-off).

### D1 — differential round-trip harness

New subpackage `toolshop/vocal_chain/` + `tests/test_vocal_chain_roundtrip.py` (**23 passed**, verified by me).

| Claim | Re-verified? | Evidence I ran myself |
|---|---|---|
| **Compressor ratio recovers on synthetic, fails on real material** | **YES — reproduced, and it is WORSE than reported** | My own staircase: 4.0 → **4.010** (0.3%), 8.0 → **8.106** (1.3%). Same code on the real 166 s ZELDI take: 4.0 → **1.440** (64%), 8.0 → **2.499** (68.8%). |
| HPF / EQ / clipper recover on both synthetic and real | not independently re-run | D1's table; methods are principled (H1 estimator at the −3 dB point that pedalboard *defines* as its cutoff; analytic inversion of `Distortion`'s documented `tanh` model) |

#### Two things my re-run adds that D1's single data point could not show

1. **The failure worsens with ratio, in the worst possible direction.** 64% under-report at 4:1, 68.8% at 8:1 — both collapsing toward 1. Drill vocals are heavily compressed, so the method degrades exactly where this lane needs it most.
2. **D1's one consolation does not generalise.** D1 reported the absolute threshold carrying a *stable* 3.766 dB offset, with relative deltas recovering precisely (12 dB set → 12.000 recovered). On **my** staircase the threshold read **−29.79 dB for both a −18 and a −24 setting** — a 6 dB set delta recovered as **0 dB**. So threshold recovery was not merely offset on my signal, it was **non-responsive to the parameter entirely**. D1's delta result held for its specific staircase and does not survive a different one. **The "deltas recover" line must not be carried forward as a property.**

#### Verdict on the gate question

**The differential floor holds for three of four stages and fails for the compressor on real material.** That is a real, honest, load-bearing result: the frame-based RMS-in/RMS-out hinge fit assumes quasi-static input, and a sung vocal violates that continuously. This is not a tuning problem; D2 needs a different observable (attack/release-aware envelope model, or short-frame instantaneous gain-reduction), not a parameter tweak.

Blind extraction correctly **not attempted** — the floor result says it is strictly harder.

## Wave 2 verification — orchestrator's own run

```
1291 passed, 2 skipped, 39 warnings, 11 subtests passed in 1886.76s (0:31:26)
exit code 0
```

**Baseline arithmetic confirms no regressions and no surprises.** Prior session's recorded baseline was **1254 passed / 2 skipped**. Now **1291 / 2**. Delta **+37** = D1's **23** + D3's **14**, exactly. Nothing else moved: no test was silently added, removed, or converted to a skip.

(A first suite run reported exit 0 but its output file was empty — the counts here come from the second run, which wrote to a file. A verdict quoted from an empty capture would not be a verdict.)

### Targeted runs
- `pytest tests/test_vocal_chain_roundtrip.py -q` → **23 passed** in 12.36s
- `pytest tests/test_chain_dsl_unwired_params.py -q` → **14 passed** in 0.74s

### Known warning, not fixed
`tests/test_vocal_chain_roundtrip.py:350` — `PytestUnknownMarkWarning: Unknown pytest.mark.slow`. The mark is used but not registered in `pytest.ini`. It works (the test runs), but the mark is inert as a selector: `-m "not slow"` would not exclude it, so AGENTS.md's "real-model tests get `@pytest.mark.slow` and are excluded from CI" is **not actually enforced** for this file. Small, real, and worth fixing — flagged, not silently patched.

## Goal status — NOT met, and honestly so

Goal: *"a measured reference vocal yields a renderable chain spec, applying that spec to a dry take moves the re-measured parameters toward the reference in a quoted A/B table, pytest exits 0, and git status is clean."*

| Clause | Status |
|---|---|
| renderable chain spec | **partial** — `Chain` renders; HPF/EQ/clipper/makeup extract on real material; **compressor does not** |
| A/B table quoted | **met** — recovery table, orchestrator-reproduced |
| pytest exits 0 | **met** — 1291 passed, quoted above |
| git status clean | **NOT met** — nothing committed this session |

**A chain spec that cannot carry a compressor is not a vocal chain.** Compression is the single most defining stage of a modern rap vocal. The goal stands open.
