# Production Expansion Strategy — Restore, Chains, Session Bridge

**Date:** 2026-07-17 · **Status:** Adopted at strategy review (orchestrator session)
**Parent docs:** `2026-07-15-longterm-roadmap-v2.md` (backlog of record — this spec ADDS lanes, changes no locked decision) · `2026-07-15-oss-integration-map.md` (this spec extends it, §5 below)
**Prompted by user questions:** AI plugins? Automatic cleaning of tracks of any impurities? AI + data science with Ableton/FL/open-source DAW components? How to expand the production toolshop?

---

## 0. Answers first (the strategy in five lines)

1. **Automatic cleaning → YES, flagship new lane: T8 RESTORE ("Track Doctor")** — diagnose impurities as data, then auto-treat with measured before/after proof. CPU-cheap, high daily value, feeds every other tool.
2. **"AI plugins" → reframed, not rejected:** we do not author real-time VST plugins (C++/JUCE detour that fights CPU-only + Python monorepo + AI-coder execution). We get the same musical outcome by **hosting plugins and DSP inside Python offline** (pedalboard = JUCE-as-a-library) with analysis-driven parameter decisions. *The pipeline is the plugin.* Revisit triggers in §6.
3. **Ableton/FL integration → decision-gated, universal-first: T9 SESSION BRIDGE** — export any dossier as a DAW-ready session: labeled stems + tempo/markers/click/chords. Universal pack works in every DAW on day one; a native writer (Ableton `.als` / REAPER `.RPP`) follows once the user states which DAW is actually in daily use ([D1]).
4. **Open-source DAW components → use them as libraries, not apps:** pedalboard now, DawDreamer evaluated later. open_DAW stays parked; T9 delivers its promised "open dossier as session template" without building a DAW.
5. **Sequencing discipline unchanged:** M6 backups stays the top production priority (corpus keeps doubling with zero backups). The E-wave below slots in after it, one session per integration, measured min/track per merge, per existing policy.

---

## 1. T8 RESTORE — "Track Doctor" (new tool lane)

**Goal:** any file or folder → impurity diagnosis as data → automatic, non-destructive cleaning chain → verified before/after report. "Any impurities" for our actual material means:

| Source material | Typical impurities |
|---|---|
| Suno masters (2,633) | codec shelf/shimmer, harsh sibilance, loudness inconsistency, occasional dropouts |
| YouTube rips (CrhymeTV etc.) | lossy-codec artifacts, clipping, loudness-war squash, spectral cutoff |
| Old Balkan recordings / archive | 50 Hz hum + harmonics, hiss, clicks/pops, narrow bandwidth, mono issues |
| Video/voice recordings (bratijanje, notes) | room noise, wind, plosives, DC offset, low SNR speech |

**Design principle (eval-first policy §1.5):** never clean blind. Stage 1 measures, Stage 2 treats what was measured, Stage 3 re-measures and proves the delta.

### E1 — Diagnose (first session; plan ready: `plans/2026-07-17-e1-restore-diagnose.md`)
- `toolshop restore diagnose <file|folder>` → per-track `impurities.json` + human report + severity grading + suggested treatment chain.
- Metrics (all numpy/scipy/librosa/pyloudnorm — seconds per track): clipping ratio + clip-run lengths, DC offset, spectral cutoff (codec provenance), hum score (50/100/150 Hz vs neighborhood), broadband noise floor, click/pop count, sibilance ratio, low-mid mud ratio, stereo correlation + side/mid balance, silence/dropout map, LUFS-I / LRA / sample-peak / PLR.
- Batch-engine integration (resumable, status JSON) → overnight **library-wide impurity sweep** = a new data-science asset in the catalogue (query "dirtiest 50 tracks", impurity distributions per source).

### E3 — Treat v1 (after E2 chains core)
- Chain stages mapped from diagnosis: **DeepFilterNet 3** (speech/vocal denoise — *vocal stems and voice recordings ONLY; it is a speech model and will eat music on full mixes*), **noisereduce** (gentle spectral gating for music hiss), **de-hum** (scipy iirnotch comb at mains harmonics — build, small), **de-clip** (ffmpeg `adeclip` — wrap), de-ess / surgical EQ / gate via pedalboard stages.
- Presets by source: `suno-prep` (premaster prep for mastering_tool), `yt-rip`, `archive`, `voice-note`.
- Non-destructive always: originals untouched (data rule), outputs under `D:\MusicData\toolshop\restored\<track>\` with manifest + before/after metric diff rendered from E1 metrics.

### E4 — Heavy tier (decision-gated [D4])
- **UVR de-reverb / de-echo / de-noise models** (e.g. `UVR-DeEcho-DeReverb`, VR arch) through the **existing python-audio-separator stack** — removes baked-in reverb/echo from rips; CPU-heavy → overnight batch tier only. Verify exact model names/weights at adoption; mirror per policy §1.3.

**Relationship to T4:** T4 stays the *vocal* lab (detectors, vocal cleaning, transcription). T8 is *full-program* restoration; T8 reuses T4's cleaning-stage pattern and the existing `cleaning_stages.py` experience. The ~10 numpy test failures in `test_cleaning_pipeline.py` (debt item 1) get fixed in their own mini-session as already planned — E1 must not add to them.

**Why this lane earns its place:** cleaner inputs → better stems (T1), more trustworthy dossiers (T2), better whisper transcripts (T4/H2), calmer premasters (T3). It is the tool that raises every other tool's floor.

---

## 2. Chains Core — offline FX chains as a platform capability (T0, not a lane)

**E2 session.** A small `toolshop/chains` module: YAML-defined chain spec → **pedalboard** render, offline, with measured cost. Pedalboard gives us the JUCE engine as a pip package: built-in FX, **VST3 hosting** (free third-party plugins become scriptable stages), and **Rubber Band** time-stretch/pitch-shift. Already in the OSS map for T7 — promoted here to a shared core capability consumed by T8 (treat chains), T4 (vocal chains), T7 (sample processing), T3 (experimental premaster prep).

This is the honest implementation of "AI plugins": the AI/data-science part is *choosing the parameters from analysis* (E1 metrics, dossier data), the DSP part is proven OSS. Later, the same chain specs could be ported into a real-time shell if a genuine need appears (§6).

**DawDreamer** (DAW-as-a-Python-library: full graph engine, sample-accurate automation, Faust integration, GPLv3) is the **EVALUATE** step after pedalboard proves the pattern — only if we hit a wall needing automation curves or multi-bus graphs. Do not adopt both in one wave.

---

## 3. T9 SESSION BRIDGE — dossier → DAW session (new thin lane)

**Goal:** one command turns an analyzed track into a session a DAW opens ready-to-work: `toolshop bridge export <track> [--daw universal|reaper|ableton]`.

### E5 — Universal pack (no DAW dependency, works everywhere)
- Labeled stems (`<key>_<bpm>_<section>_<n>` naming — same convention as T7), section markers as a **MIDI file with markers + tempo map + click track**, cue sheet, chords-as-MIDI (once H2 lands), `SESSION_README.md` with the dossier summary.
- Consumes dossier v1 fields today (BPM, sections); upgrades **for free** as H2 delivers beat grid, trustworthy key, per-section chords. No new deps.

### E6 — Native writer ([D1] RESOLVED 2026-07-17: user runs **FL Studio 21 + Ableton Live 12 Suite**, both verified installed; own open_DAW project exists)
| DAW | Integration surface | Verdict |
|---|---|---|
| **Ableton Live 12 Suite** (installed) | `.als` = gzipped XML → template writer authored against the user's Live 12; alternative/add-on: remote control via **AbletonOSC + pylive** (MIT, Live 11+ so 12 is fine); M4L available via Suite but out of scope | ✅ **CHOSEN native target** — E6 = `.als` template writer (offline/batch fits toolshop DNA); AbletonOSC as optional interactive E6.1 later |
| **FL Studio 21** (installed) | Weakest surface: Python API is MIDI-controller scripting only; `.flp` proprietary (pyflp reads, write fragile) | ❌ no native writer — FL is served by the universal pack (drag-drop stems + marker/tempo MIDI import fine); this is FL's ceiling, not a priority call |
| REAPER | `.RPP` plain text (trivial writer) | ❌ dropped — not in the user's stable |
| **open_DAW** (own project — verified 2026-07-17: Rust audio engine w/ mixer/MIDI/transport/session save-load + JUCE UI + unwired Python AI bridge) | T9's universal pack **is designed as its session-import format** — the "open dossier as session template" promised at park time | stays parked (G4 unchanged); when/if revived at the H4 review, E5 output is its ready-made interchange target, zero extra investment now |

E6 risk note: Live 12 must open a generated `.als` — the writer works by substituting into a template
project saved from the user's own Live 12 (audio refs, tempo, locators, track names), never by
synthesizing XML from scratch; first milestone of E6 is "Live 12 opens a 2-track generated session".

---

## 4. What we are deliberately NOT building (and why)

1. **Real-time VST/AU plugin authoring** — new C++/Rust toolchain, real-time DSP + GUI discipline, per-host debugging; months of sessions for one plugin; real-time ML inference on this CPU is marginal. Parked with triggers (§6).
2. **A DAW** (open_DAW stays parked per roadmap G4).
3. **FL Studio native automation** — no real surface to build on (see table above).
4. **Real-time monitoring/live processing** of any kind — offline/batch is our lane; it is where CPU-only wins.
5. **New web UIs** — Datasette (already adopted for T5) browses E1's impurity tables too; G2 unchanged.

---

## 5. OSS Integration Map addendum (extends `2026-07-15-oss-integration-map.md` §2; all "verify wheel/license at adoption" per policy)

| Tech | Verdict | For | Notes |
|---|---|---|---|
| **pyloudnorm** | ➕ INTEGRATE | T8-E1 | MIT; ITU-R BS.1770 loudness in pure Python; fallback: parse ffmpeg `ebur128` |
| scipy notch/comb de-hum, click detector | 🔨 BUILD (small) | T8-E1/E3 | ~100 lines each + synthetic-fixture tests |
| ffmpeg `adeclip`, `astats`, `ebur128`, `silencedetect` | ✅ KEEP/WRAP | T8 | ffmpeg already at `D:\Projects\ffmpeg_portable` |
| **DeepFilterNet 3** | (already mapped T4) | T8-E3 | scope guard: speech/vocal material only |
| **noisereduce** | (already mapped T4) | T8-E3 | music-safe light denoise |
| **UVR DeEcho/DeReverb/DeNoise weights** | ➕ INTEGRATE | T8-E4 | via existing audio-separator adapter; overnight tier; mirror + checksums |
| **pedalboard** | (already mapped T7) → promote to **core chains** | E2 | GPLv3 (ledger); VST3 hosting + Rubber Band included |
| **DawDreamer** | 🧪 EVALUATE (after E2) | chains v2 | GPLv3; graph/automation/Faust; adopt only on proven need |
| **AbletonOSC + pylive** | 🧪 EVALUATE (gated [D1]) | T9-E6 | MIT; Live 11+; remote-control alternative to `.als` writing |
| **pyflp** | 👀 WATCH | — | read-side FLP inspection only; no write path |
| `.RPP` / `.als` template writers | 🔨 BUILD (gated [D1]) | T9-E6 | RPP = plain text (small); ALS = gzipped XML from pinned template (medium) |
| Bertom Denoiser-class free VST3s | 👀 WATCH | E2+ | free real-time denoise VSTs become scriptable through pedalboard chains if useful |

License ledger additions on adoption: pyloudnorm (MIT), DawDreamer (GPLv3), AbletonOSC/pylive (MIT), pyflp (GPLv3 — verify). GPL items follow the existing personal-use rule.

---

## 6. Decision gates — ALL RESOLVED 2026-07-17 (user + delegated orchestrator calls)

- **[D1] DECIDED:** user runs FL Studio 21 + Ableton Live 12 Suite (verified installed). Native target = **Ableton** (`.als` template writer; AbletonOSC optional later). FL via universal pack only. open_DAW stays parked; E5 pack doubles as its future session format (see §3 table).
- **[D2] DECIDED (delegated to orchestrator): M6 backups before E1.** Grounds: zero backups; D: is a 2010-era laptop HDD (ST9640423AS); C: is a separate physical disk so Tier-1 cross-disk backup needs no new hardware. Plan ready: `plans/2026-07-17-h1m6-backups-data-governance.md`.
- **[D3] DECIDED: real-time-plugin authoring stays parked.** Revisit triggers unchanged: daily real-time DAW mixing · live-performance need · GPU windfall (G1). Any trigger → nih-plug/JUCE wrap of proven chain specs.
- **[D4] DECIDED (user): E4 heavy de-reverb waits until E3 presets prove daily value.** Re-evaluate at the post-E3 review with real usage evidence, not before.

## 7. E-wave sequencing (slots into the existing board; one session each)

```
M6 backups (plan ready)  →  E1 restore-diagnose (plan ready)  →  E2 chains-core  →  E3 restore-treat-v1
                                                                                  ↘  E5 bridge-universal
E4 heavy-de-reverb (post-E3 review, per D4)                                          E6 .als writer for Live 12 (per D1)
```
- E1 plan is written and executable now. E2–E6 plans get authored one-at-a-time as sessions are picked up (roadmap convention).
- H2 (Dossier v2) remains the next *horizon*; the E-wave interleaves with it — E-sessions are independent evenings, same rule as M2/M4.
- **matchering reference-match** (T3 bridge, already mapped) becomes the natural finisher after E3: restore → master-toward-reference → verified deliverable = the complete "production toolshop" chain the user asked for.

## 8. Risks

| Risk | Mitigation |
|---|---|
| DFN3 applied to full mixes destroys music content | Hard scope guard in preset definitions (vocal/voice sources only); music denoise via noisereduce/UVR-DeNoise |
| Integration sprawl (the standing risk, now +pedalboard etc.) | Unchanged policy: one integration per session, adapter + mocked tests + measured min/track to merge |
| Metric thresholds mislabel healthy tracks as impure | Thresholds are named constants + synthetic-fixture tests; severity is graded, never auto-destructive; treat step is opt-in per preset |
| `.als` format drift across Live versions | Pin template to user's Live version ([D1]); prefer AbletonOSC path if writing proves brittle |
| GPL accumulation (pedalboard, DawDreamer, phonemizer…) | Existing ledger + adapter isolation; personal use unaffected |
| E-wave distracts from H1 close-out (M6/M2/M3/M4) | M6 stays first in the recommended sequence; E-sessions are additive evenings, not replacements |
