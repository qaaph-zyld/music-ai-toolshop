# Orchestrator Synthesis: Music Toolshop v2

**Date:** 2026-08-08  
**Synthesized from:** 5 research handoff reports (3,396 lines total)  
**Target genres:** Tech House, Drill, Hip-Hop  
**Purpose:** Unified implementation plan from cross-report synthesis

---

## Source Reports

| # | Topic | File | Lines |
|---|-------|------|-------|
| 1 | Golden Reference Spectral Curves | `researcher_golden_reference_spectral_curves_20260806_202200.md` | 342 |
| 2 | Agentic AI for Genre Decisions | `researcher_agentic_genre_decisions_20260806_202200.md` | 998 |
| 3 | LoRA Fine-Tuning Pipeline | `plans/lora-finetuning-pipeline-503968.md` + `ai_modules/lora_finetuning/` | 529 + code |
| 4 | Real-Time Edge Deployment | `researcher_realtime_edge_deployment_20260806_202200.md` | 588 |
| 5 | Advanced Evaluation Metrics | `researcher_advanced_evaluation_metrics_20260806_202200.md` | 939 |

---

## 1. Executive Summary

Five parallel research threads investigated the full pipeline for genre-specific AI audio processing: mastering references, agentic DAW control, model fine-tuning, edge deployment, and evaluation metrics. The key architectural decision emerging from synthesis is a **three-layer closed-loop system** combining deterministic measurement (Phantom MCP), LLM-based genre-specific decision-making (Claude with forced tool_use), and DAW execution (REAPER MCP) — with LoRA-adapted BS-RoFormer for separation and a multi-metric evaluation suite weighted per genre.

**Cross-cutting findings:**
- All three genres share strong sub-bass management needs but differ in distribution: Tech House emphasizes 60–250 Hz (bass > sub), Drill emphasizes 35–100 Hz (sliding 808), Hip-Hop emphasizes 60–80 Hz (kick body) + 808 harmonics
- Genre profiles for Tech House and Drill **do not exist** in any discovered system — they must be created from Golden Reference data
- No single metric is sufficient for evaluation — SDR is best for vocals, SI-SAR for drums/bass, Fullness/Bleedless for richness/cleanliness trade-off, Zimtohrli for psychoacoustic quality
- WSA + TensorRT compound speedup is theoretically 89x but **practically blocked** (FlexAttention ONNX export not ready); use torch.compile + CUDA graphs instead
- LoRA fine-tuning on RTX 3090 (24GB) is feasible at ~10–14GB VRAM with batch_size=1 + AMP + flash attention

---

## 2. Genre-Specific Target Profiles

### 2.1 Tech House

| Parameter | Target | Source |
|-----------|--------|--------|
| Integrated LUFS (club) | -11.35 median | TrackSensei 563-track corpus |
| Integrated LUFS (streaming) | -14 | Spotify/YouTube/Tidal |
| True peak (club) | +1.23 dBTP median | TrackSensei |
| True peak (streaming) | -1 dBTP | Platform spec |
| Bass band energy | 60–250 Hz > sub band (20–60 Hz) | TrackSensei: 5/6 electronic styles |
| Stereo width | Narrow lows, mono below 120 Hz | TrackSensei |
| Sidechain ducking | 6–12 dB depth, 100–200 ms recovery at 122–128 BPM | Report 2 |
| Spectral centroid | ~2–3 kHz (warm) | Report 2 |

**Golden Reference construction:** 20–30 commercially released tracks, loudness-normalized to -14 LUFS, compute per-bin median + P25/P75 LTAS, apply cepstral smoothing for key removal.

### 2.2 Drill

| Parameter | Target | Source |
|-----------|--------|--------|
| Integrated LUFS | -14 (Spotify) | MixMasterAI |
| Natural competitive loudness | -9 to -7 LUFS (6 dB hotter than Spotify) | MixMasterAI |
| True peak | -1 dBTP | Platform spec |
| Dynamic range | 6–10 LU | MixMasterAI |
| 808 fundamental | 40–60 Hz (median 49.5 Hz / G1) | arXiv TR-808 paper |
| 808 harmonics | Saturation at 2f0, 3f0, 4f0 for speaker translation | Peak Studios |
| 808 hi-cut post-saturation | 300–400 Hz | Peak Studios |
| Vocal tone | Dark — no 3–5 kHz boost | MixMasterAI |
| Kick vs 808 | Kick leads (unlike trap where 808 leads) | MixMasterAI |
| Spectral centroid | ~2–2.5 kHz (dark) | Report 2 |

### 2.3 Hip-Hop

| Parameter | Target | Source |
|-----------|--------|--------|
| Integrated LUFS | -14 (Spotify/YouTube), -16 (Apple Music) | MixMasterAI |
| True peak | -1 dBTP | Platform spec |
| Dynamic range | 7–10 LU | MixMasterAI |
| Kick body | 60–80 Hz full | MixMasterAI |
| Vocal presence | 2–4 kHz boost 1–2 dB, 3–6 kHz 1–3 dB above instrumental | TrackSensei, Report 2 |
| Vocal air | 10–14 kHz shelf +1–2 dB | TrackSensei |
| EQ curve | "Smiley face" — pronounced lows/highs, scooped mids | Peak Studios |
| Compression | Serial: Stage 1 (3:1, 10–20 ms attack), Stage 2 (4:1, 1–5 ms attack) | TrackSensei |
| Mono below | 150 Hz | Phantom hip-hop profile |
| Spectral centroid | ~2.5–3.5 kHz (bright vocals) | Report 2 |

### 2.4 Genre Profile JSONs (for Phantom-style schema)

**Tech House:**
```json
{
  "genre": "tech-house",
  "loudness": { "lufs_range": [-11.0, -9.0], "crest_factor_range": [4.0, 8.0], "true_peak_max_dbtp": 1.0 },
  "frequency": { "bands": { "31_hz": 3.0, "62_hz": 5.0, "125_hz": 4.0, "250_hz": 2.0, "500_hz": 0.0, "1000_hz": -1.0, "2000_hz": 0.0, "4000_hz": 1.0, "8000_hz": 1.0, "16000_hz": 0.0 } },
  "stereo": { "width": "moderate", "mono_below_hz": 120.0 },
  "processing_notes": "Four-on-the-floor kick. Sidechain bass to kick: 4:1-8:1, 0.1ms attack, 150-200ms release, 6-12dB GR. Bass owns 80-200Hz, kick owns 40-80Hz. Narrow stereo for low end."
}
```

**Drill:**
```json
{
  "genre": "drill",
  "loudness": { "lufs_range": [-14.0, -9.0], "crest_factor_range": [6.0, 10.0], "true_peak_max_dbtp": -1.0 },
  "frequency": { "bands": { "31_hz": 3.0, "62_hz": 5.0, "125_hz": 3.0, "250_hz": 1.0, "500_hz": 0.0, "1000_hz": 0.0, "2000_hz": -1.0, "4000_hz": -1.0, "8000_hz": 1.0, "16000_hz": 0.0 } },
  "stereo": { "width": "moderate", "mono_below_hz": 100.0 },
  "processing_notes": "Kick leads. 808 fundamental 40-60Hz with saturation for harmonics. Dark vocal tone (no 3-5kHz boost). Rolling hi-hats 8-12kHz. 808 hi-cut post-saturation at 300-400Hz. Sliding 808 patterns."
}
```

**Hip-Hop** (from Phantom's existing profile):
```json
{
  "genre": "hip-hop",
  "loudness": { "lufs_range": [-10.0, -7.0], "crest_factor_range": [5.0, 9.0], "true_peak_max_dbtp": -1.0 },
  "frequency": { "bands": { "31_hz": 4.0, "62_hz": 4.0, "125_hz": 3.0, "250_hz": 1.0, "500_hz": -1.0, "1000_hz": 0.0, "2000_hz": 1.0, "4000_hz": 2.0, "8000_hz": 1.0, "16000_hz": 0.0 } },
  "stereo": { "width": "moderate", "mono_below_hz": 150.0 },
  "processing_notes": "Sub-bass is the foundation. 808s or deep kicks drive the low end. Vocals must cut through clearly -- presence boost at 3-5kHz. Snares and hi-hats provide rhythmic crispness. Keep the mix dry and upfront."
}
```

---

## 3. System Architecture

### 3.1 Three-Layer Closed-Loop Agent

```
┌──────────────────────────────────────────────────────────────┐
│                     AGENT ORCHESTRATOR                        │
│                                                              │
│  1. Load genre profile (JSON: LUFS, frequency, dynamics,     │
│     stereo, processing notes)                                │
│  2. MEASURE: Call measurement MCP tools on rendered audio    │
│  3. COMPARE: Compute deviations from genre profile targets   │
│  4. DECIDE: LLM reads deviations + hints → DSP adjustments   │
│  5. EXECUTE: Call DAW-control MCP tools to apply changes     │
│  6. RENDER: Call DAW render tool → new WAV                   │
│  7. RE-MEASURE: Call measurement MCP tools on new WAV        │
│  8. VERIFY: Check convergence criteria                       │
│     ├── All metrics within tolerance → DONE                  │
│     ├── Max iterations (5) reached → STOP, report            │
│     ├── Noise floor gate triggered → STOP, converged         │
│     └── PASS/RED tripwire triggered → ABORT, report error    │
│  9. EVIDENCE LOG: Record every measurement, decision, tool   │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│              MEASUREMENT MCP SERVER (Phantom)                 │
│  Tools: analyze_spectrum, analyze_loudness,                  │
│         analyze_dynamics, analyze_stereo,                    │
│         detect_problems, multi_stem_masking,                 │
│         compare_to_profile, full_diagnostic                  │
│  Returns: Pydantic JSON with typed fields + deviations       │
│  Engine: Essentia (10-25x faster than librosa)               │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│              DAW-CONTROL MCP SERVER (REAPER MCP)              │
│  Tools: add_fx, set_fx_parameter, setup_sidechain,           │
│         engine_mix(style), engine_master(style),             │
│         engine_fix_mix(style), render_project,               │
│         bounce_stems, set_track_volume                        │
│  Profiles: 35 style profiles (xDarkzx)                       │
│  Key feature: hint field in every analysis result            │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│              SUBJECTIVE LAYER (Optional, Advisory)            │
│  music-perception-mcp listen_subjective(path, question?)     │
│  → Audio LLM holistic judgement (ADVISORY ONLY, never gates) │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 3.2 Key Design Principles

1. **Deterministic/subjective split** (from music-perception-mcp): Deterministic measurements (Spearman ρ≈1.0) gate loops and verify convergence. Subjective assessments (audio LLM, 0.46–0.64 correlation with human mood) are advisory only.

2. **`hint` field pattern** (from xDarkzx ReaperMCP): Every analysis tool returns a human-readable hint telling the AI what to do next, eliminating complex prompt engineering.

3. **Forced `tool_use`** (from MixMaster AI): LLM calls use temperature 0.2, forced tool_choice, always include `reasoning` field for auditability.

4. **Noise-floor-gated iterate** (from Sonoscope): If change between iterations falls below measurement nondeterminism floor, loop stops. Prevents infinite loops.

5. **Evidence logging** (from Audio-Mind): Record every measurement, decision, and tool call as structured JSON for post-hoc debugging.

### 3.3 Convergence Criteria

| Criterion | Value |
|-----------|-------|
| LUFS tolerance | ±0.5 dB |
| True peak tolerance | ±0.2 dBTP |
| Spectral centroid tolerance | ±100 Hz |
| Max iterations | 5 |
| Diminishing returns threshold | <20% improvement between iterations |
| Hard quality gates | Clipping, NaN/Inf, silence → immediate abort |

---

## 4. Separation & Training Pipeline

### 4.1 Model Selection

| Use Case | Model | Runtime | Hardware | RTF | Quality |
|----------|-------|---------|----------|-----|---------|
| Studio (max quality) | htdemucs_ft | PyTorch CUDA FP16 + compile | RTX 3090+ | ~0.03 | 9.00 SDR |
| Live/real-time | htdemucs | TensorRT FP16 | RTX 3090+ | 0.028 | 8.36 SDR |
| Desktop (NVIDIA) | htdemucs | ONNX Runtime CUDA | RTX 3060+ | ~0.07 | 8.36 SDR |
| Desktop (CPU) | htdemucs | ONNX Runtime CPU | 6-core+ | ~0.12–0.25 | 8.36 SDR |
| Genre-adapted | BS-RoFormer + LoRA | PyTorch CUDA FP16 | RTX 3090 | ~0.03 | TBD (fine-tuned) |

### 4.2 LoRA Fine-Tuning Configuration

**YAML config (from MSST):**
```yaml
lora:
  r: 8                    # Rank: 4, 8, or 16
  lora_alpha: 16          # Scaling: alpha/r = 2
  lora_dropout: 0.05      # Regularization for small datasets
  merge_weights: False    # Set True only for deployment
  enable_lora: [True, False, True]  # Q and V projections, skip K

model:
  dim: 384
  depth: 8
  stereo: true
  num_stems: 4
  flash_attn: true
  chunk_size: 485100      # ~11 seconds at 44.1kHz

training:
  batch_size: 1
  gradient_accumulation_steps: 8
  use_amp: true
  lr: 1e-5                # Stage 1; 5e-6 for Stage 2
  patience: 3
```

### 4.3 Two-Stage Curriculum

| Stage | Data | LoRA | LR | Purpose |
|-------|------|------|----|---------|
| 1 — General Adaptation | Clean genre-specific stems | Yes (Q/V) | 1e-5 | Adapt to genre spectral characteristics |
| 2 — Mastered Audio | Mastered/degraded mixtures (Type 6) | Yes (continued) | 5e-6 | Handle production effects specific to genre |

**Key insight**: Train on mastered mixtures with degraded stems as targets (CPJKU approach). The model learns to predict degraded stems from mastered mixture — what you actually want for commercial audio.

### 4.4 Loss Function Combination (Recommended)

| Loss | Weight | Rationale |
|------|--------|-----------|
| Multi-Resolution STFT | 1.0 | Transient detail (drums, percussion) |
| L1 time-domain | 1.0 | Baseline reconstruction quality |
| LogWMSE | 0.5 | Perceptual weighting, handles mastered dynamics |
| Robust quantile-masked MSE (q=0.95) | — | Reduces outlier sensitivity from production artifacts |

### 4.5 Data Requirements

| Item | Minimum | Ideal |
|------|---------|-------|
| Tracks per genre | 50–200 | 500+ |
| Segment length | 10–30 seconds | Full tracks |
| Format | 44.1kHz, stereo, WAV | 44.1kHz, stereo, lossless |
| Stems | vocals, drums, bass, other | + guitar, piano (6-stem) |
| Augmentation | MSST built-in (pitch shift, EQ, distortion, mixup) | + torch-audiomentations |

### 4.6 Compute Requirements (RTX 3090, 24GB)

| Configuration | VRAM | Feasible? | Training Time |
|--------------|------|-----------|---------------|
| LoRA, dim=384, batch=1 | ~10–14 GB | ✅ Comfortable | ~1.5–3h/epoch (100 tracks) |
| LoRA, dim=384, batch=2 | ~16–20 GB | ✅ With AMP | ~1–2h/epoch |
| LoRA, dim=512, batch=1 | ~16–20 GB | ✅ With AMP | ~2–4h/epoch |
| Full FT, dim=512, batch=1 | ~28–35 GB | ❌ Needs >24GB | — |

**With early stopping (patience=3):** likely converges in 20–40 epochs → 30–120 hours total (1.5–5 days).

### 4.7 Implementation Status

A working LoRA fine-tuning pipeline has been implemented at `ai_modules/lora_finetuning/`:
- `configs/stage1_genre_clean.yaml` — Stage 1 config
- `configs/stage2_mastered.yaml` — Stage 2 config
- `scripts/prepare_dataset.py` — Dataset organization (Type 1 + mastering degradation to Type 6)
- `scripts/train.py` — Training launcher wrapping MSST train.py
- `scripts/evaluate.py` — Validation + inference with TTA
- `scripts/run_pipeline.py` — Full automated 2-stage pipeline
- `scripts/setup_check.py` — Environment verification

---

## 5. Deployment Pipeline

### 5.1 Conversion: PyTorch → ONNX → TensorRT

**HTDemucs (demucs-onnx, recommended):**
```bash
pip install 'demucs-onnx[export]'
demucs-onnx export htdemucs_6s out/htdemucs_6s.onnx
# Then: trtexec --onnx=htdemucs_6s.onnx --fp16 --saveEngine=demucs_6s.trt
```

**Four export blockers patched:**
1. `torch.stft` → Conv1d with precomputed DFT kernels
2. `fractions.Fraction` → `float()`
3. `random.randrange` → hardcoded 0
4. `aten::_native_multi_head_attention` → nn.MultiheadAttention

**Parity:** 2.42×10⁻⁴ max abs diff vs PyTorch fp32.

**BS-RoFormer (MSST pipeline):**
```bash
python export_to_onnx.py --model_type bs_roformer --config_path config.yaml --checkpoint_path model.ckpt --output_path model.onnx
python export_to_tensorrt.py --onnx_path model.onnx --model_type bs_roformer --config_path config.yaml --output_path model.engine --fp16
```

**Critical:** STFT/ISTFT must be extracted from `BSRoformer.forward()` — model accepts spectrograms, not raw audio.

### 5.2 WSA + TensorRT: Blocked

| Blocker | Status |
|---------|--------|
| FlexAttention ONNX export | PR #7534 in progress, vmap errors open |
| TensorRT custom sparse attention | Not supported by TRT fused attention |
| BS-RoFormer TRT performance | 2x SLOWER than PyTorch (Tile op bottleneck) |

**Workaround:** Use torch.compile + CUDA graphs + FP16 (Option B from Report 4). Preserves full 44.5x WSA benefit. Requires PyTorch runtime (~2GB install).

### 5.3 Minimum Viable Configuration

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| GPU VRAM | 3 GB | 7 GB+ |
| GPU Compute | 2 TFLOPS FP32 | 10+ TFLOPS FP16 |
| CPU | Modern 6-core | 8+ core |
| RAM | 4 GB | 8 GB |
| Storage | 53 MB (htdemucs_6s fp16) | 260 MB (full fp32 ONNX) |

**Real-time thresholds:** RTX 3090+ TRT = RTF 0.028 ✅ | CPU ONNX = RTF 0.12 ✅ | WASM = RTF 1.3 ❌

---

## 6. Evaluation Framework

### 6.1 Metric Comparison

| Metric | Domain | Phase-sensitive | Silence support | Perceptual | Semantic | Best for |
|--------|--------|----------------|-----------------|------------|----------|----------|
| SDR | Waveform | Yes | No | No | No | Vocals |
| SI-SAR | Waveform | Yes | No | No | No | Drums, bass |
| Fullness | Mel-dB | No | Yes | Partial | No | Instrumental richness |
| Bleedless | Mel-dB | No | Yes | Partial | No | Vocal cleanliness |
| LogWMSE | Freq-weighted | No | Yes | Partial | No | Training loss |
| MMSNR | Mel spectrogram | No | Yes | Partial | No | Phase-insensitive eval |
| Zimtohrli | Gammatone/NSIM | No | Yes | Yes | No | Psychoacoustic quality |
| FAD-CLAP | CLAP embeddings | No | Yes | Yes | Yes | Semantic correctness |

### 6.2 Genre-Specific Evaluation Weights

**Tech House:**
| Metric | Weight | Config |
|--------|--------|--------|
| SDR | 0.15 | Standard |
| Bleedless (vocals) | 0.20 | n_fft=4096, n_mels=512 |
| Fullness (bass) | 0.20 | f_min=20, f_max=250 |
| Fullness (drums) | 0.15 | n_fft=2048, n_mels=256 |
| MMSNR | 0.15 | 3 configs, f_max=24000 |
| Zimtohrli | 0.10 | 48kHz |
| FAD-CLAP | 0.05 | CLAP-LAION-music |

**Sub-metrics:** Bass Clarity Index (Fullness 20–250 Hz), Kick Punch Metric (transient energy 50–100 Hz), Cross-stem Bleed (bass into drums below 120 Hz)

**Drill:**
| Metric | Weight | Config |
|--------|--------|--------|
| SDR | 0.10 | Standard |
| Bleedless (vocals) | 0.25 | n_fft=4096, n_mels=512 |
| Fullness (bass/808) | 0.25 | n_fft=8192, f_min=20, f_max=120 |
| MMSNR | 0.15 | 3 configs |
| Zimtohrli | 0.10 | 48kHz |
| LogWMSE | 0.10 | 44100Hz, with mixture |
| FAD-CLAP | 0.05 | CLAP-LAION-music |

**Sub-metrics:** 808 Weight Index (Fullness 20–120 Hz, n_fft=8192), 808 Sustain Metric (decay time 30–80 Hz), Vocal Isolation Score (drum/808 bleed into vocals)

**Hip-Hop:**
| Metric | Weight | Config |
|--------|--------|--------|
| SDR (vocals) | 0.20 | Standard |
| SI-SAR (drums) | 0.15 | Scale-invariant |
| SI-SAR (bass) | 0.15 | Scale-invariant |
| Bleedless (vocals) | 0.15 | n_fft=4096, n_mels=512 |
| Fullness (drums) | 0.10 | n_fft=2048, n_mels=256 |
| Fullness (vocals) | 0.10 | n_fft=4096, n_mels=512 |
| MMSNR | 0.10 | 3 configs |
| Zimtohrli | 0.05 | 48kHz |

**Sub-metrics:** Vocal Presence Index (vocal/instrumental energy 200 Hz–4 kHz), Drum Transient Preservation (onset cross-correlation), Kick-Snare Balance (40–120 Hz vs 150–400 Hz)

### 6.3 Dependencies

```
torch>=2.0
torchaudio>=2.0
numpy
librosa
soundfile
scipy
torch-log-wmse>=0.3.1
zimtohrli>=0.2.1
laion-clap
transformers
auraloss
museval
```

### 6.4 Module Structure

```
evaluation/
├── metrics/
│   ├── sdr.py                 # SDR, SI-SDR, SI-SAR
│   ├── fullness_bleedless.py  # Fullness & Bleedless
│   ├── log_wmse.py            # LogWMSE wrapper
│   ├── mmsnr.py               # Multi-Mel-SNR
│   ├── zimtohrli.py           # Zimtohrli wrapper
│   └── fad_clap.py            # FAD-CLAP
├── genres/
│   ├── base.py                # Base GenreProfile
│   ├── tech_house.py          # Tech House + sub-metrics
│   ├── drill.py               # Drill + sub-metrics
│   └── hip_hop.py             # Hip-Hop + sub-metrics
├── suite.py                   # GenreEvaluationSuite orchestrator
├── report.py                  # Report generation
└── run_evaluation.py          # CLI entry point
```

---

## 7. Implementation Roadmap

### Phase 1: Foundation (Weeks 1–2)

| Task | Dependency | Status |
|------|-----------|--------|
| Create genre profile JSONs (Tech House, Drill, Hip-Hop) | Golden Reference data from Report 1 | Pending |
| Build Golden Reference curve construction pipeline | Essentia/librosa, 20–30 tracks per genre | Pending |
| Set up MSST framework (clone, configure, download checkpoint) | — | Pending |
| Verify LoRA pipeline module imports | `ai_modules/lora_finetuning/` | ✅ Done |

### Phase 2: Separation & Training (Weeks 2–4)

| Task | Dependency | Status |
|------|-----------|--------|
| Source genre-specific stems (50–200 tracks per genre) | Splice, Beatport, MoisesDB | Pending |
| Prepare datasets (Type 1 clean, Type 6 mastered) | `scripts/prepare_dataset.py` | Pending |
| Run Stage 1 LoRA training (clean genre adaptation) | RTX 3090, ~1.5–3h/epoch | Pending |
| Run Stage 2 LoRA training (mastered audio) | Stage 1 checkpoint | Pending |
| Evaluate separation quality with genre-specific suite | Evaluation module | Pending |

### Phase 3: Evaluation Framework (Weeks 2–3, parallel)

| Task | Dependency | Status |
|------|-----------|--------|
| Implement core metrics (SDR, Fullness/Bleedless, LogWMSE, MMSNR) | torch, librosa, torch-log-wmse | Pending |
| Implement Zimtohrli and FAD-CLAP wrappers | zimtohrli, laion-clap | Pending |
| Implement genre profiles with sub-metrics | Phase 1 genre profiles | Pending |
| Build suite orchestrator and report generator | Core metrics + genre profiles | Pending |
| Validate against MUSDB18-HQ with known SDR scores | museval | Pending |

### Phase 4: Agentic System (Weeks 3–5)

| Task | Dependency | Status |
|------|-----------|--------|
| Deploy Phantom MCP server (measurement layer) | Essentia, genre profiles | Pending |
| Deploy xDarkzx ReaperMCP (execution layer) | REAPER installed | Pending |
| Implement closed-loop orchestrator | Both MCP servers running | Pending |
| Add genre-specific measurement extensions | Sidechain depth, 808 H/F ratio, vocal presence | Pending |
| Add subjective advisory layer (music-perception-mcp) | Gemini API | Pending |
| Implement evidence logging | Audio-Mind pattern | Pending |

### Phase 5: Deployment Optimization (Weeks 4–5)

| Task | Dependency | Status |
|------|-----------|--------|
| Export models to ONNX (demucs-onnx / MSST) | Trained LoRA checkpoints | Pending |
| Build TensorRT FP16 engines | ONNX models, trtexec | Pending |
| Benchmark on target hardware tiers | RTX 3090, RTX 3060, CPU | Pending |
| Implement WSA via torch.compile (Option B) | smulelabs/windowed-roformer | Pending |
| Configure minimum viable deployment | Per Report 4 decision matrix | Pending |

---

## 8. Open Questions

1. **Genre-specific stem sourcing**: Where to source Tech House / Drill / Hip-Hop tracks with known stems? Options: Splice remix packs, Beatport stems, MoisesDB, artist-provided multitracks. A targeted research prompt may be needed.

2. **Optimal LoRA rank**: r=8 is the default, but r=16 or r=32 may capture more genre-specific spectral characteristics. Needs empirical validation during Phase 2.

3. **ONNX/TensorRT export with LoRA**: MSST supports export, but LoRA weight merging during export needs verification. Test during Phase 5.

4. **Mastered audio target definition**: Should targets be degraded/mastered stems (CPJKU approach) or clean stems? For commercial audio separation, degraded stems as targets is more practical — confirmed by Report 3.

5. **WSA + TRT timeline**: FlexAttention ONNX export (PR #7534) likely 6–12 months from production-ready. Revisit compound speedup at that time.

6. **808 saturation measurement**: The hardest proxy to implement — requires isolating 808 stem, detecting fundamental (pyin/piptrack), computing harmonic ratio. Not available in any existing MCP tool. Must be custom-built.

7. **Genre profiles for Phantom**: Tech House and Drill profiles don't exist in any discovered system. Must be created from Golden Reference data and validated.

---

## 9. Consolidated Source Index

### Repositories
| Repo | URL | Report |
|------|-----|--------|
| ZFTurbo/Music-Source-Separation-Training (MSST) | github.com/ZFTurbo/Music-Source-Separation-Training | 3, 5 |
| CPJKU/music-source-restoration | github.com/CPJKU/music-source-restoration | 3 |
| smulelabs/windowed-roformer | github.com/smulelabs/windowed-roformer | 4 |
| MansfieldPlumbing/Demucs_v4_TRT | huggingface.co/MansfieldPlumbing | 4 |
| StemSplit/demucs-onnx | github.com/StemSplit/demucs-onnx | 4 |
| ZFTurbo/MSS_ONNX_TensorRT | github.com/ZFTurbo/MSS_ONNX_TensorRT | 4 |
| fadelabs/phantom | github.com/fadelabs/phantom | 2 |
| xDarkzx/Reaper-MCP | github.com/xDarkzx/Reaper-MCP | 2 |
| AnqiPinku/music-perception-mcp | github.com/AnqiPinku/music-perception-mcp | 2 |
| axiomantic/sonoscope | github.com/axiomantic/sonoscope | 2 |
| Tanzil-Ahmed/mixmaster-ai | github.com/Tanzil-Ahmed/mixmaster-ai | 2 |
| sergree/matchering | github.com/sergee/matchering | 1 |
| iver56/torch-audiomentations | github.com/iver56/torch-audiomentations | 3 |
| yongyang/MSRKit | github.com/yongyizang/MSRKit | 5 |
| google/zimtohrli | github.com/google/zimtohrli | 5 |
| crlandsc/torch-log-wmse | github.com/crlandsc/torch-log-wmse | 5 |

### Papers
| Paper | arXiv | Report |
|-------|-------|--------|
| Windowed Sink Attention | 2510.25745 | 4, 5 |
| MSR ICASSP Challenge summary | 2601.04343 | 5 |
| MSRBennch benchmark | 2510.10995 | 5 |
| Zimtohrli psychoacoustic metric | 2509.26133 | 5 |
| 2025 Metrics Bake-off | 2507.06917 | 5 |
| MSST framework paper | 2607.23395 | 3 |
| CPJKU MSR 3-stage curriculum | 2603.04032 | 3 |
| Loss functions study | 2202.07968 | 3 |
| TR-808 harmonic constraints | 2502.07524 | 2 |
| Audio-Mind auditable framework | 2605.28480 | 2 |

### Key Industry Sources
| Source | URL | Report |
|--------|-----|--------|
| TrackSensei 563-track analysis | tracksensei.com | 1, 2 |
| MixMasterAI drill mastering | mixmasterai.co/mastering/drill/spotify | 1 |
| MixMasterAI hip-hop mastering | mixmasterai.co/mastering/hip-hop | 1 |
| Matchering PR #82 (multi-reference) | github.com/sergree/matchering/pull/82 | 1 |
| Essentia MusicExtractor | essentia.upf.edu | 1 |
| librosa documentation | librosa.org | 1, 5 |

---

## 10. Next Actions

1. **Source genre-specific stems** — dispatch a targeted research prompt for stem dataset sourcing (Splice, Beatport, MoisesDB genre breakdown)
2. **Build Golden Reference curves** — implement the median + P25/P75 pipeline from Report 1 using Essentia
3. **Create genre profile JSONs** — encode the targets from Section 2 into Phantom-compatible format
4. **Begin LoRA training** — once stems are sourced, run the 2-stage pipeline via `ai_modules/lora_finetuning/`
5. **Build evaluation module** — implement the metrics and genre profiles from Section 6
6. **Deploy agentic system** — set up Phantom + REAPER MCP servers and implement the closed-loop orchestrator
