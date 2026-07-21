# OSS Integration Map — AI & Data-Science Tech for the Toolshop

**Date:** 2026-07-15 · **Companion to:** `2026-07-15-longterm-roadmap-v2.md` (horizons/milestones live there; this spec says *which technology* plugs into each tool and what we build ourselves).
**Method:** web-verified 2026-07-15 against our locked constraints: CPU-only, Windows 10 + WSL2, Python 3.11 venv, 16 GB RAM. Policy: **integrate existing OSS first; build only glue, domain logic, and what doesn't exist.**

---

## 1. Integration Policy (applies to every adoption)

1. **Adapter pattern** — every external package/binary gets a thin `toolshop/*_adapter.py` with a stable return contract + mocked tests. No tool imports a third-party API directly from CLI code.
2. **WSL sidecar pattern** — Linux-only tech (essentia, keyfinder-cli, some Vamp hosts) runs via `wsl -d Ubuntu bash -c ...` exactly like mastering_tool already does. One helper in core: `run_wsl(cmd)`.
3. **Model mirroring** — every model checkpoint is copied to `D:\MusicData\toolshop\models\` with a checksum manifest at download time. *Rationale: the default BS-Roformer download source vanished in 2026-06 when the hosting Hugging Face account was deleted.* Doctor verifies the mirror.
4. **CPU budget rule** (roadmap §5.1) — each integration lands with a measured min/track figure; anything >15 min goes behind the overnight batch engine.
5. **Eval-first** — model-based features (separation, chords, beats, key) are compared on a small private ground-truth set before becoming defaults (see §4 Eval Harness).
6. **License ledger** (§6) — GPL-family deps are fine for personal use; the ledger exists so nothing surprises us if we ever distribute.

## 2. Integration Map by Tool

### T1 Stem Tool — *keep the stack, add resilience + objectivity*
| Tech | Verdict | Notes |
|---|---|---|
| python-audio-separator | ✅ KEEP | Active upstream; wraps UVR MDX/VR/Roformer families |
| demucs (htdemucs/6s) | ✅ KEEP | Via existing `demucs_adapter` |
| bs-roformer-infer / melband-roformer-infer | 👀 WATCH | New (2026-07) inference-only pkgs; adopt only if audio-separator becomes a liability |
| **museval** (sigsep) | ➕ INTEGRATE | SDR/SIR/SAR scoring of presets against our own known-stem pairs (Suno vocal/instrumental exports) → turns H1-M3 "CPU optimization" into measured engineering |
| Model mirror + checksums | 🔨 BUILD (small) | Policy #3; extend doctor |

### T2 Dossier Tool — *the biggest upgrade surface*
| Capability | Tech | Verdict | CPU reality |
|---|---|---|---|
| Beats + downbeats | **beat_this (CPJKU)** ONNX model via onnxruntime | ➕ INTEGRATE | ISMIR-2024 accuracy, no madmom needed (DBN post-proc optional); seconds–minutes per track. Fallback: librosa (present) |
| Structure (fast tier) | **pychorus** + own novelty/self-similarity segmenter (librosa) | ➕ INTEGRATE + 🔨 BUILD | Seconds per track; labels via heuristics (energy/vocal-presence per section) |
| Structure (HQ tier) | **all-in-one (allin1)** reusing our cached Demucs stems | ➕ INTEGRATE (H4) | Its cost is the internal demix step — we already have stems for 140+ tracks; run only on pre-separated tracks |
| Chords (baseline) | **Chordino** (NNLS Vamp plugin) via sonic-annotator CLI | ➕ WRAP | CPU-trivial, battle-tested; WSL if Windows Vamp hosting misbehaves |
| Chords (neural) | **BTC** (bidirectional transformer) and/or **crema** (602-class vocab, inversions) | 🧪 EVALUATE | Torch CPU offline is fine; pick by eval on German-rap/Balkan material |
| Key/mode | Krumhansl-Schmuckler on librosa chroma | 🔨 BUILD (small) | Planned in roadmap (fixes the "G major vs Gm" defect); validate against Chordino root stats; optional keyfinder-cli (WSL) cross-check |
| Melody/bass → MIDI | **basic-pitch** (Spotify) | ➕ INTEGRATE | ONNX backend is the Windows default — ideal; Apache-2.0 |
| Instruments/tags | **PANNs** (panns-inference) + CLAP zero-shot (see T5) | ➕ INTEGRATE | Replaces the current 3-bucket instrument guess with 527-class AudioSet tags |
| Lyrics (timed) | **faster-whisper** (int8) + **whisperX** forced alignment | ➕ INTEGRATE | CPU int8 documented path; <100 ms word timestamps; German strong, Serbian usable (multilingual); run on vocal stem |

### T3 Remastering Tool — *one big add*
| Tech | Verdict | Notes |
|---|---|---|
| **matchering 2.0** | ➕ INTEGRATE | Active (2025-11). New `reference-match` mode alongside the profile pipeline: master toward any reference track's RMS/FR/peak/stereo. `matchering_xcheck.py` already exists in mastering_tool — promote it to a first-class mode + batch CLI |
| Airwindows LV2, ffmpeg loudnorm/ebur128 | ✅ KEEP | Present |
| ViSQOL et al. | ❌ SKIP | C++ build friction, low marginal value over existing LUFS/DR verification |

### T4 Vocal Lab
| Tech | Verdict | Notes |
|---|---|---|
| **DeepFilterNet 3** (`deep-filter` prebuilt Windows binary) | ➕ WRAP | SOTA-class speech denoise on CPU; new cleaning stage before whisper + for noisy vocal stems; 48 kHz WAV in/out — resample around it |
| **noisereduce** (spectral gating) | ➕ INTEGRATE | Pip-only light alternative for musical breath/hiss where DFN is too aggressive |
| faster-whisper / whisperX | (as T2) | Shared adapter |
| parselmouth/Praat, 12 FX detectors, cleaning pipeline | ✅ KEEP | Present |
| RVC / so-vits voice conversion | ⏸ PARK | GPU-gated |

### T5 Library Intelligence — *the data-science core*
| Tech | Verdict | Notes |
|---|---|---|
| SQLite (catalogue of dossiers) | ✅ KEEP/BUILD schema | Roadmap H3 |
| **DuckDB** | ➕ INTEGRATE | Analytics engine over sqlite/CSV/parquet — joins, window functions, instant aggregation for taste/catalogue reports |
| **Datasette** | ➕ INTEGRATE | Zero-effort local web browser over the catalogue DB; instant "explore my library" UI before any custom dashboard |
| **CLAP** (`laion/larger_clap_music`, transformers, CPU) | ➕ INTEGRATE | Overnight embedding batch → (a) similarity "more like this", (b) **zero-shot text search**: "dark aggressive trap, 808-heavy" over your 2,855+ tracks |
| Vector search | 🔨 BUILD (trivial) → sqlite-vec later | At ~3k tracks numpy cosine over an embeddings table is instant; adopt **sqlite-vec** (alpha, Mozilla Builders) only if the corpus grows 10× |
| **Chromaprint/pyacoustid** (`fpcalc.exe`) | ➕ INTEGRATE | Exact/near-duplicate detection across Suno library (the 510-zero-size cleanup showed the need) |
| **Panako** (or audfprint) | ➕ WRAP (H4) | Sample/interpolation detection robust to pitch/tempo shifts — "where does this loop appear?" |
| **UMAP + HDBSCAN + plotly** | ➕ INTEGRATE (H4) | 2-D "map of my music" from CLAP embeddings, clustered; classic DS, pure CPU |
| beets | ❌ NOT ADOPTED | Healthy project, but metadata/tagging-centric — would fight the dossier catalogue. Borrow ideas (chromasearch, plugin model); optionally use one-off for Suno file/tag hygiene |

### T6 Creation Bridge
| Tech | Verdict | Notes |
|---|---|---|
| **phonemizer + espeak-ng** | ➕ INTEGRATE | Phoneme output for **Serbian AND German** → real rhyme/assonance detection beyond spelling; feeds rimer (MAirina) and lyric briefs |
| **Flow analyzer** | 🔨 BUILD (flagship) | No OSS does this: whisperX word timings × beat_this grid → syllables/bar, on/off-beat placement, rhyme-scheme density, flow fingerprint per artist/section. Uniquely ours |
| LLM for briefs/tagging | ✅ USE EXISTING | Claude in chat/IDE sessions (already in workflow). No local LLM now: 7–8B Q4 via llama.cpp fits 16 GB RAM but adds little over Claude access. Revisit only for offline bulk labeling |
| Suno automation | ⏸ PARK | No official API; keep the downloader |
| Dossier-diff (recreate-and-compare) | 🔨 BUILD | Planned H3; pure pandas/numpy over dossier.json pairs |

### T7 Sample Forge
| Tech | Verdict | Notes |
|---|---|---|
| **pedalboard** (Spotify) | ✅ ADOPTED | In use via `toolshop remix` for Rubber Band time-stretch/pitch-shift and offline FX chains. VST3 hosting available for future expansion. GPLv3; recorded in license ledger. |
| librosa onsets + own slicing/naming logic | 🔨 BUILD | Section loops + one-shots from stems; core of the tool |
| aubio | ❌ SKIP | Stale wheels; librosa covers onsets |

## 3. The Build-Ourselves List (everything else is integration)
1. K-S key/mode detector (~100 lines + eval) — T2
2. Novelty/self-similarity structure segmenter + section labeler (fast tier) — T2
3. Flow analyzer (word-timings × beat-grid) — T6 flagship, genuinely novel
4. Rhyme/assonance analyzer on phonemizer output (sr/de) — T6, feeds rimer
5. Dossier schema/renderer, dossier-diff scorer — T2/T6
6. Catalogue schema, queries, reports; embeddings table + numpy search — T5
7. Sample Forge slicing/naming/pack-manifest logic — T7
8. Model mirror + checksum manifests; WSL sidecar helper; eval ground-truth set — core
9. All adapters, presets, batch glue — core discipline, not product

## 4. Eval Harness (new cross-cutting asset, seeds in H1)
- **Stems:** museval SDR/SIR/SAR on 5–10 tracks where we hold true pairs (Suno vocal/instrumental exports, own recordings) → ranks presets/models objectively; gates H1-M3 optimization claims.
- **MIR:** mir_eval + a hand-labeled mini set (10 tracks: BPM, downbeats, key, 8 chords each, section boundaries) — one evening of labeling, then every T2 upgrade is measurable.
- Results land in the catalogue DB → Datasette/DuckDB dashboards; regressions visible.

## 5. Sequencing (slots into roadmap v2 horizons)
- **H1 (now):** model mirroring + doctor check · museval harness seed · *(unchanged M1–M6)*
- **H2 (Dossier v2):** beat_this ONNX · K-S key · Chordino baseline + BTC/crema eval · basic-pitch MIDI · faster-whisper+whisperX lyrics · PANNs tags · pychorus/novelty structure · DeepFilterNet pre-clean · mir_eval mini-set
- **H3 (Integration):** matchering reference-match mode · CLAP embedding batch + text/similarity search · DuckDB + Datasette over catalogue · chromaprint dedup · pedalboard into Sample Forge · phonemizer rhyme module · flow analyzer v1 · dossier-diff
- **H4 (Surfaces/Frontier):** allin1 HQ structure (stem-cache reuse) · Panako sample detection · UMAP/HDBSCAN library map · watchdog watch-folders · sqlite-vec if scale demands · Streamlit dashboard (per G2)

## 6. License Ledger (personal use: all fine; matters only if we distribute)
- **GPL-family (flag):** matchering (GPLv3) · pedalboard (GPLv3, JUCE/VST3 SDK) · phonemizer + espeak-ng (GPLv3) · Chordino/Vamp (GPL) · Panako (AGPLv3) · chromaprint fpcalc (LGPL; AcoustID service free for non-commercial) · datasette (Apache-2.0; dev-only browsing, not a runtime dependency)
- **Permissive:** demucs (MIT) · audio-separator (MIT — *individual UVR/Roformer model weights carry their own terms; check per model if ever commercial*) · basic-pitch (Apache-2.0) · faster-whisper (MIT) · whisperX (BSD) · DeepFilterNet (MIT/Apache dual) · CLAP (Apache-2.0 code; check checkpoint cards) · beat_this (MIT-style; verify) · DuckDB (MIT) · Datasette (Apache-2.0) · sqlite-vec (MIT/Apache) · museval/mir_eval (MIT) · umap/hdbscan (BSD) · noisereduce (MIT) · panns-inference (MIT) · cyrtranslit (MIT)
- Rule: record exact license + model-card terms in the registry entry at adoption time; "verify on adoption" for anything marked above.

## 7. Risks
| Risk | Mitigation |
|---|---|
| Model hosting rot (proven: 2026-06 HF deletion) | Mirror + checksums, doctor check (§1.3) |
| whisperX/pyannote pulls heavy deps; pyannote needs HF token | Use alignment-only path (no diarization) unless needed; pin versions in lock |
| Chord/structure accuracy on dense trap/Balkan mixes | Eval harness before default-swap; confidence fields; keep Chordino baseline |
| sqlite-vec is alpha | Numpy search first; adopt later behind adapter |
| GPL if we ever ship binaries | Ledger + adapter isolation makes swaps possible |
| Integration sprawl (16+ new deps) | One integration per session, adapter+tests+measured cost required to merge (policy #1/#4) |
