# 06-opendaw — Post-mortem

**Date:** 2026-05-07
**Decision:** Archive `projects/06-opendaw/`. Pivot to
`projects/07-reaper-integration/` (drive existing toolshop adapters from
inside Reaper).

This is the short, evidence-based version of the assessment that drove the
pivot. It exists so that future contributors (or future-us) don't pick up
the project from the old `HANDOFF-*.md` documents and assume they describe
reality.

## What's actually in the repo (2026-04-08, commit `4299954`)

| Layer | Claim from `HANDOFF-2026-04-08-PHASE-9-X.md` | Verified reality |
|---|---|---|
| Tests | "858 tests passed, 0 failed, 1 ignored" | **53 passed, 7 ignored** (`cargo test` after disabling the broken `build.rs`). |
| Build | "OpenDAW.exe builds successfully with full FFI connectivity" | `cargo build` fails: `cc::Build` used in `build.rs` but `cc` is not in `[build-dependencies]`. The build script also references **51** `third_party/<vendor>/*_ffi.c` files (miniaudio, faust, surge, vital, dexed, helm, obxd, odin2, tunefish, jack, ladspa, calf, magenta, mmm, musicbert, clap, etc.) — none of those directories exist in the repo. |
| FFI surface | "All linker issues resolved", "5/5 key FFI functions confirmed accessible" | The `.def` file lists ~150 exports (`daw_transport_play`, `daw_mmm_generate`, `daw_stem_separate`, …). **None of them have a Rust implementation in `src/`.** They cannot link because they don't exist. |
| C++ UI | OpenDAW.exe smoke-tested | `ui/CMakeLists.txt` lists 18 `.cpp` source files (`Main.cpp`, `MainComponent.cpp`, transport bar, mixer panel, etc.). Only `MmmFFI.cpp` (67 lines, all stubs returning `false` / `nullptr`) actually exists. There is no JUCE entry point — the project cannot link an executable. |
| Python AI bridge | Real ACE-Step generation, real Demucs stem extraction | All three bridge modules (`ai_modules/{ace_step_bridge,stem_extractor,suno_library}/__init__.py`) return hard-coded data with `# TODO` comments. ~440 lines of stubs. |
| Python ↔ Rust | Per the 2026-05-07 attached handoff: PyO3 bindings (`daw-engine/src/python_bindings.rs`, 246 lines), `AIBridge`, real `Transport`/`Mixer`/`SessionView` integration | **No `python_bindings.rs` exists.** No `pyo3` dependency. No `AIBridge` type. No commits between 2026-04-08 and 2026-05-07 on `master`. The work was either never committed or lives only on a contributor's local Windows checkout. |

## Code that does exist

* ~1,438 LOC of clean, idiomatic Rust across 11 modules (`transport`, `session`, `midi`, `project`, `mixer`, `clock`, `callback`, `generators`, `stream`, `sample`, `sample_player`).
* All of it is **pure data structures and state machines**. There is no live audio path: `cpal` is in the deps but the only real-device test is marked `#[ignore]`. `Sample::load_from_wav` is a stub. The "save/load" in `project.rs` is a hand-rolled `String::find` parser that loses track names and types on round-trip.
* 53 tests pass. They exercise the data structures, not real audio.

## Where the gap matters

The risk isn't the code (it's fine for what it is); it's the *narrative
around it*. The two HANDOFF documents describe a substantial DAW with
working FFI, a JUCE UI, and Python bindings. None of that exists in
version control. Continuing to drive future work off those documents
would be planning against a fictional state.

## Why the pivot

For *personal music production*, building a DAW from scratch is years of
work and the result will not match Reaper ($60), Cakewalk (free), or
Ardour (free) for daily use. The interesting and actually-novel work in
this monorepo lives outside `projects/06-opendaw/`:

* `toolshop/voice_effects_adapter.py` — 12 signal-processing detectors
  (reverb, pitch shift, formant shift, compression, EQ, distortion,
  chorus, auto-tune, de-essing, vocoder, noise gate, delay).
* `toolshop/stem_extractor_adapter.py` — wraps `audio-separator` for
  high-quality 3-stem extraction.
* `toolshop/bpm_adapter.py`, `toolshop/reverse_engineering_adapter.py` —
  librosa-based BPM/key/structure analysis.
* `toolshop/cleaning_pipeline_adapter.py` — multi-stage cleaning
  pipeline with breath/cough/click detection and beat-grid analysis.
* `toolshop/yt_*_adapter.py` — YouTube ingest and Suno-prompt summaries.

Wrapping those in ReaScript actions yields a useful tool in weeks rather
than years, and reuses 100% of the work that has actually shipped.

## What stays in the repo

`projects/06-opendaw/` is kept on disk as a reference and engineering
exercise. Its `README.md` carries an `ARCHIVED` notice pointing here. No
further commits are planned against it.

## What follows

See [`../projects/07-reaper-integration/README.md`](../projects/07-reaper-integration/README.md)
for the active workstream.
