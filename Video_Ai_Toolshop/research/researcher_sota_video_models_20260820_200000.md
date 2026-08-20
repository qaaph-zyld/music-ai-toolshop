# Research Findings: SOTA Cinematic Video Generation Models (2025-2026)

## Scope
- **Question:** What are the best open-source and accessible video generation models in 2025-2026 that produce Sora-level cinematic quality? Which support LoRA fine-tuning or identity-preserving character injection?
- **Boundaries:** Included — Wan 2.1/2.2, HunyuanVideo (1.0 + 1.5), CogVideoX-5B/1.5, Mochi-1, LTX-Video (0.9.x + LTX-2), Kling 3.0, Veo 3/3.1, Open-Sora (1.3 + 2.0), Sora 2/2 Pro, Stable Video Diffusion, AnimateDiff. Excluded — pure talking-head/avatar tools, GAN-based methods, pre-2024 models.
- **Time spent:** ~20 minutes
- **Date accessed:** 2026-08-20

---

## Key Findings

### 1. Open-Source vs. Closed-Source Quality Gap Has Narrowed Dramatically

As of mid-2026, the Artificial Analysis Video Arena (blind human preference voting) ranks **Wan 3.0** (Alibaba, open weights) at **ELO 1,247** — the #1 text-to-video model with audio, ahead of Google's Gemini Omni Flash (1,239) and all closed-source competitors. **MiniMax H3** (open weights, ELO 1,228) is #3 globally. Open-source models now match or exceed closed-source models in cinematic quality. ([Artificial Analysis T2V Leaderboard](https://artificialanalysis.ai/video/leaderboard/text-to-video) — accessed 2026-08-20)

### 2. Wan 2.2 Is the Current Open-Source Cinematic Champion (Pre-Wan 3.0)

Wan 2.2 (released Jul 28, 2025) uses a Mixture-of-Experts (MoE) architecture with 27B total params (14B active per step). The 5B dense variant (TI2V-5B) runs on a single RTX 4090 (24GB VRAM) at 720P/24fps. The 14B MoE variants require 80GB VRAM for full-quality 720P. Supports T2V, I2V, speech-to-video, and character animation/replacement (Wan-Animate-14B). LoRA training is fully supported via DiffSynth-Studio and community tools (lora-gym, musubi-tuner). ([Wan2.2 GitHub](https://github.com/wan-video/wan2.2) — accessed 2026-08-20; [Wan2.2 HuggingFace](https://huggingface.co/Wan-AI/Wan2.2-T2V-A14B) — accessed 2026-08-20)

### 3. HunyuanVideo 1.5 Brings Consumer-GPU Inference with SOTA Quality

HunyuanVideo 1.5 (released Nov 21, 2025) is an 8.3B parameter model that runs on as little as **14GB VRAM** with model offloading — a massive reduction from the original HunyuanVideo's 60GB minimum. It supports T2V and I2V at 480p–720p, 5–10 seconds, with a dedicated video super-resolution network that upscales to 1080p. Official LoRA training code released Dec 5, 2025, using the Muon optimizer. ([HunyuanVideo-1.5 GitHub](https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5) — accessed 2026-08-20; [HunyuanVideo 1.5 Technical Report](https://arxiv.org/html/2511.18870v1) — accessed 2026-08-20)

### 4. LoRA Fine-Tuning for Identity Preservation Is Mature on Multiple Models

- **Wan 2.2:** Dual-expert MoE requires training TWO LoRAs (high-noise for composition/motion, low-noise for texture/identity). Community tools (lora-gym, AI Toolkit) provide production-ready pipelines. I2V LoRAs are more effective for character consistency than T2V LoRAs. ([lora-gym GitHub](https://github.com/alvdansen/lora-gym) — accessed 2026-08-20; [Apatero Wan 2.2 LoRA Guide](https://apatero.com/blog/wan-2-2-lora-training-person-method-guide-2025) — accessed 2026-08-20)
- **HunyuanVideo:** Official LoRA training scripts for I2V effects. Community has developed identity-preserving LoRA training with DINOv3-based identity loss to prevent character drift. 10–15 images sufficient for human characters. ([HunyuanVideo-I2V GitHub](https://github.com/Tencent-Hunyuan/HunyuanVideo-I2V) — accessed 2026-08-20; [Video-Free-LoRA-Hyvideo1.5-I2V](https://github.com/Kev0208/Video-Free-LoRA-Hyvideo1.5-I2V) — accessed 2026-08-20)
- **LTX-Video:** Purpose-built for LoRA fine-tuning with IC-LoRA (In-Context LoRA) for character identity preservation. Official trainer supports standard LoRA, full fine-tuning, and IC-LoRA. 10–50 reference images sufficient. ([LTX-Video Trainer GitHub](https://github.com/lightricks/ltx-video-trainer) — accessed 2026-08-20; [LTX LoRA Training](https://ltx.io/model/capabilities/lora-training) — accessed 2026-08-20)

### 5. Closed-Source Models Still Lead in Native Audio and Multi-Shot Narratives

- **Kling 3.0** (Feb 2026): Native 4K at 60fps, up to 15s, multi-shot storyboarding (up to 6 shots), native audio in 5 languages. ELO 1,107 (T2V). API-only, no open weights. ([Kling 3.0 Guide](https://kling.ai/quickstart/klingai-video-3-model-user-guide) — accessed 2026-08-20; [HokAI Kling 3.0](https://hokai.io/hub/models/kling-3.0) — accessed 2026-08-20)
- **Veo 3.1** (Jan 2026): 4K output, 8s max, 24fps, native audio, scene extension, first/last frame control. ELO 1,092 (T2V). API via Google Cloud. ([Veo 3.1 Google AI Studio](https://aistudio.google.com/models/veo-3) — accessed 2026-08-20; [Veo 3.1 DeepMind](https://deepmind.google/models/veo/) — accessed 2026-08-20)
- **Sora 2 Pro** (Oct 2025): Up to 20s, 1080p, synced audio, character references (up to 2 per generation), video extension up to 120s total. API via OpenAI. **Note: Sora product deprecated as of Apr 26, 2026; API shuts down Sep 24, 2026.** ([Sora 2 API Docs](https://developers.openai.com/api/docs/models/sora-2-pro) — accessed 2026-08-20; [Sora 2 Launch](https://openai.com/index/sora-2/) — accessed 2026-08-20)

### 6. LTX-Video Is the Speed and Efficiency Leader

LTX-2 (announced Oct 23, 2025) generates native 4K at up to 50fps with synchronized audio in one pass. The 13B distilled model generates HD video in 10 seconds on H100. The distilled LoRA variant requires only 1GB VRAM. Supports multi-keyframe conditioning, 3D camera logic, and LoRA fine-tuning. LTX-2.5 Fast (open weights) holds ELO 1,062 on the T2V arena. ([LTX-Video GitHub](https://github.com/Lightricks/LTX-Video) — accessed 2026-08-20; [LTX-2 Blog](https://website.ltx.video/blog/introducing-ltx-2) — accessed 2026-08-20)

---

## Existing Solutions / Tools

### Open-Source / Open-Weights Models

| Name | URL | Tech Stack | License | Stars/Popularity | Key Features | Gaps |
|------|-----|------------|---------|-------------------|--------------|------|
| **Wan 2.2** | [GitHub](https://github.com/wan-video/wan2.2) | DiT, MoE, Flow Matching | Apache 2.0 | 17.2K stars | 720P/24fps, T2V+I2V+TI2V, MoE 27B (14B active), 5B dense variant runs on 4090, LoRA support, Wan-Animate for character replacement | 14B requires 80GB VRAM; 5s max; no native audio |
| **Wan 3.0** | [Artificial Analysis](https://artificialanalysis.ai/video/leaderboard/text-to-video) | DiT, MoE | Open weights | ELO 1,247 (#1 T2V) | Highest ELO of any model; Aug 2026 release | Details limited at time of research |
| **HunyuanVideo 1.0** | [GitHub](https://github.com/Tencent-Hunyuan/HunyuanVideo) | DiT, Causal 3D VAE, Flow Matching | Custom (Tencent) | 10K+ stars | 13B params, 720p/5s/16fps, outperformed Runway Gen-3 & Luma 1.6 in human eval | 60GB VRAM min; no I2V in base model; slow inference |
| **HunyuanVideo 1.5** | [GitHub](https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5) | DiT, SSTA attention, Muon optimizer | Open weights | New (Nov 2025) | 8.3B params, 14GB VRAM min, T2V+I2V, 1080p via VSR, LoRA training code released | Sparse attention & distilled model weights not yet released |
| **CogVideoX 1.5-5B** | [HuggingFace](https://huggingface.co/zai-org/CogVideoX1.5-5B) | DiT, 3D RoPE | Apache 2.0 | 6K+ stars | 1360×768, 10s at 16fps, as low as 7GB VRAM (INT8), LoRA fine-tuning | Lower cinematic quality than Wan/HunyuanVideo; English-only prompts |
| **Mochi-1** | [GitHub](https://github.com/genmoai/mochi) | AsymmDiT, AsymmVAE | Apache 2.0 | 4K+ stars | 10B params, 480p/5.4s/30fps, strong motion realism, LoRA trainer included | 480p only; no I2V; ~60GB VRAM; photoreal bias (weak on animation) |
| **LTX-Video (0.9.x / LTX-2)** | [GitHub](https://github.com/Lightricks/LTX-Video) | DiT, high-compression VAE (1:192) | Apache 2.0 | 5K+ stars | Real-time generation (2s for 5s video on H100), 4K/50fps (LTX-2), native audio, IC-LoRA for character identity, 8GB VRAM (2B model) | Lower cinematic quality than Wan/HunyuanVideo (ELO 942–1,062 depending on version) |
| **Open-Sora 2.0** | [GitHub](https://github.com/hpcaitech/Open-Sora) | DiT, Flow Matching | Apache 2.0 | 29K stars | 11B params, 768p, T2V+I2V, trained for only $200K, on-par with HunyuanVideo on VBench | Lower resolution than Wan/Hunyuan; slower inference at 768p |
| **Stable Video Diffusion** | [HuggingFace](https://huggingface.co/stabilityai/stable-video-diffusion-img2vid-xt) | UNet + attention, LDM | Community License | Widely used | I2V only, 576×1024, 25 frames, <8GB VRAM with optimizations, LoRA for camera motion | I2V only (no T2V); low resolution; short clips; older model (Nov 2023) |
| **AnimateDiff** | [GitHub](https://github.com/guoyww/AnimateDiff) | Motion module for SD 1.5/SDXL | Apache 2.0 | Widely used | Plug-and-play motion module for personalized T2I models, MotionLoRA for camera movements, works with any SD LoRA | SD 1.5 backbone (512×512 native); not a standalone video model; lower quality than DiT-based models |

### Closed-Source / API-Only Models

| Name | URL | Tech Stack | License | Key Features | Gaps |
|------|-----|------------|---------|--------------|------|
| **Kling 3.0** | [kling.ai](https://kling.ai/quickstart/klingai-video-3-model-user-guide) | MVL + DiT | Proprietary | Native 4K/60fps, 15s, multi-shot (6 shots), native audio (5 languages), element consistency, character reference | No open weights; API-only; no LoRA; expensive ($0.075–$0.14/s) |
| **Veo 3.1** | [Google AI Studio](https://aistudio.google.com/models/veo-3) | Proprietary | Proprietary | 4K output, 8s, 24fps, native audio, scene extension, first/last frame, object insertion | No open weights; API-only; no LoRA; $24/min |
| **Sora 2 / 2 Pro** | [OpenAI API](https://developers.openai.com/api/docs/models/sora-2-pro) | Proprietary | Proprietary | Up to 20s, 1080p, synced audio, character references (2 per gen), video extension (120s total) | **Deprecated Apr 2026; API shuts down Sep 24, 2026**; no open weights; no LoRA |

---

## Detailed Model Comparison Table

| Model | Max Resolution | Max Duration | FPS | Min VRAM | LoRA Support | I2V | Cinematic Quality | Open Source |
|-------|---------------|-------------|-----|----------|-------------|-----|-------------------|-------------|
| Wan 2.2 TI2V-5B | 720P (1280×704) | 5s | 24 | 24GB (4090) | ✅ (DiffSynth, lora-gym) | ✅ | ⭐⭐⭐⭐⭐ | ✅ Apache 2.0 |
| Wan 2.2 A14B | 720P (1280×720) | 5s | 24 | 80GB (with offload) | ✅ (dual-expert MoE) | ✅ | ⭐⭐⭐⭐⭐ | ✅ Apache 2.0 |
| Wan 3.0 | TBD | TBD | TBD | TBD | TBD | TBD | ⭐⭐⭐⭐⭐ (ELO 1,247) | ✅ Open weights |
| HunyuanVideo 1.0 | 720P (1280×720) | 5s (129f) | 16 | 60GB | ✅ (community + keyframe LoRA) | ✅ (separate I2V model) | ⭐⭐⭐⭐⭐ | ✅ Custom license |
| HunyuanVideo 1.5 | 720P → 1080p (VSR) | 10s | 24 | 14GB (offload) | ✅ (official, Muon optimizer) | ✅ | ⭐⭐⭐⭐⭐ | ✅ Open weights |
| CogVideoX 1.5-5B | 1360×768 | 10s | 16 | 7GB (INT8) | ✅ (diffusers LoRA) | ✅ (I2V variant) | ⭐⭐⭐⭐ | ✅ Apache 2.0 |
| Mochi-1 | 480P (848×480) | 5.4s | 30 | 60GB (H100 recommended) | ✅ (included trainer) | ❌ | ⭐⭐⭐⭐ | ✅ Apache 2.0 |
| LTX-Video 2B | 1216×704 | 2min+ | 30 | 8GB | ✅ (standard + IC-LoRA) | ✅ | ⭐⭐⭐ | ✅ Apache 2.0 |
| LTX-2 (13B) | 4K | 10s | 50 | TBD | ✅ (LoRA + IC-LoRA) | ✅ | ⭐⭐⭐⭐ | ✅ Open weights |
| Open-Sora 2.0 (11B) | 768×768 | ~5s | TBD | 52.5GB (256p, 1 GPU) | TBD | ✅ | ⭐⭐⭐⭐ | ✅ Apache 2.0 |
| SVD-XT | 576×1024 | ~4s (25f) | ~7 | <8GB (with optimizations) | ✅ (camera motion LoRA) | ✅ (I2V only) | ⭐⭐⭐ | ✅ Community License |
| AnimateDiff v3 | 1024×1024 (SDXL) | 16 frames | ~8 | ~13GB | ✅ (MotionLoRA, works with SD LoRAs) | ✅ (via init image) | ⭐⭐ | ✅ Apache 2.0 |
| Kling 3.0 | 4K (3840×2160) | 15s | 60 | N/A (API) | ❌ | ✅ | ⭐⭐⭐⭐⭐ (ELO 1,107) | ❌ Proprietary |
| Veo 3.1 | 4K | 8s | 24 | N/A (API) | ❌ | ✅ | ⭐⭐⭐⭐⭐ (ELO 1,092) | ❌ Proprietary |
| Sora 2 Pro | 1920×1080 | 20s | TBD | N/A (API) | ❌ (character refs only) | ✅ | ⭐⭐⭐⭐⭐ | ❌ Deprecated |

---

## LoRA & Identity-Preservation Character Injection — Deep Dive

### Wan 2.2 Character LoRA Training

- **MoE dual-expert architecture** requires training TWO LoRAs: high-noise expert (composition/motion) + low-noise expert (texture/identity). Both loaded at inference.
- **I2V LoRAs** are more effective for character consistency than T2V LoRAs — the reference image anchors the subject, and the LoRA adjusts temporal preservation.
- **Recommended settings:** Sigmoid timestep scheduling for person/character training, 10–30 images/clips, 3000–5000 steps, LR 0.0002, network dim 32–64, DOP (Differential Output Preservation) set to "person."
- **Tools:** lora-gym (18 templates across Modal/RunPod/local), DiffSynth-Studio, AI Toolkit, musubi-tuner.
- **Consistency ceiling:** I2V LoRA trained on same person = high consistency across clips of any length. ([lora-gym](https://github.com/alvdansen/lora-gym) — accessed 2026-08-20; [Apatero Guide](https://apatero.com/blog/wan-2-2-lora-training-person-method-guide-2025) — accessed 2026-08-20; [wan27.org Guide](https://wan27.org/blog/wan-2-2-lora-training-guide) — accessed 2026-08-20)

### HunyuanVideo Character LoRA Training

- **HunyuanVideo-I2V** ships with official LoRA training scripts for customizable effects (hair growth, embrace, etc.).
- **HunyuanVideo 1.5** released official training code (Dec 5, 2025) with LoRA support via `--use_lora` flag, Muon optimizer, FSDP, gradient checkpointing.
- **Identity-preserving LoRA:** Community developed DINOv3-based identity loss with teacher→student distillation to prevent identity drift while preserving motion priors. Uses supervised contrastive loss for same-character embedding closeness across style shifts.
- **Data requirements:** 10–15 static images sufficient for human characters (video clips only needed for unusual movement patterns).
- **Tools:** tdrussell's diffusion-pipe, Kohya-based trainers, ComfyUI integration. ([HunyuanVideo-I2V](https://github.com/Tencent-Hunyuan/HunyuanVideo-I2V) — accessed 2026-08-20; [HunyuanVideo-1.5 Training](https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5) — accessed 2026-08-20; [Video-Free-LoRA](https://github.com/Kev0208/Video-Free-LoRA-Hyvideo1.5-I2V) — accessed 2026-08-20; [Unite.AI Guide](https://www.unite.ai/how-to-train-and-use-hunyuan-video-lora-models/) — accessed 2026-08-20)

### LTX-Video IC-LoRA (In-Context LoRA)

- **IC-LoRA** is a specialized training mode for character identity preservation. Train on reference images of a character, then generate videos where that character holds appearance across scenes, angles, and lighting.
- **Standard LoRA** also supported for styles, effects, and motion patterns. Multiple LoRAs can be combined at inference (character + style).
- **Control LoRAs:** Depth map, human pose, and Canny edge control via IC-LoRA training mode.
- **Data requirements:** 10–50 reference images or short video clips.
- **Tools:** Official LTX-Video-Trainer, ComfyUI, fal.ai, Replicate. ([LTX-Video-Trainer](https://github.com/lightricks/ltx-video-trainer) — accessed 2026-08-20; [LTX LoRA Training](https://ltx.io/model/capabilities/lora-training) — accessed 2026-08-20)

### AnimateDiff MotionLoRA

- **MotionLoRA** adapts the pre-trained motion module to specific camera movements (zoom, pan, roll, etc.) with as few as 50 reference videos. Only ~30MB per model.
- **Domain Adapter LoRA** for image model fine-tuning, adjustable via LoRA scaler at inference.
- Works with **any** personalized SD 1.5/SDXL model — character LoRAs trained for static images automatically benefit from motion.
- **Limitation:** Not a standalone identity-preserving character injection system; relies on SD backbone for character identity. ([AnimateDiff GitHub](https://github.com/guoyww/AnimateDiff) — accessed 2026-08-20; [AnimateDiff Paper](https://arxiv.org/html/2307.04725) — accessed 2026-08-20)

### Sora 2 Character References (Closed-Source)

- Upload a character source video (2–4s, 720p–1080p, 16:9 or 9:16) and reuse it across generations with consistent appearance.
- Up to 2 characters per generation. Character source videos work best when matching the output aspect ratio.
- Not LoRA-based — uses reference video injection at inference time. ([Sora 2 Prompting Guide](https://developers.openai.com/cookbook/examples/sora/sora2_prompting_guide) — accessed 2026-08-20)

---

## Open Questions

1. **Wan 3.0 full specs** — Released Aug 2026 with ELO 1,247, but detailed technical specs (resolution, duration, VRAM, LoRA support) were not yet fully documented at time of research.
2. **LTX-2 full release** — Announced Oct 23, 2025 with 4K/50fps + native audio, but "model weights, code, and benchmarks will be released to the community later in 2025." Status of full open-weight release needs verification.
3. **HunyuanVideo 1.5 missing weights** — Sparse attention model, distilled model, and SR models are listed as not yet released.
4. **Wan 2.2 Animate-14B + LoRA compatibility** — Official docs note that LoRA models trained on Wan2.2 may cause "unexpected behavior" with Wan-Animate. Identity preservation via Wan-Animate vs. LoRA needs further investigation.
5. **MiniMax H3** — Ranked #3 globally (ELO 1,228, open weights, Jul 2026) but was outside the original scope. Worth investigating as a potential new SOTA open-source option.
6. **MAGI-2 Preview** (Sand.ai, open weights, ELO 1,102 on I2V arena) — Also outside original scope but appears in top open-weight rankings.
7. **Multi-language prompt support** — CogVideoX is English-only; Wan and HunyuanVideo support Chinese + English; Kling supports 5 languages. Non-English prompt performance varies significantly.

---

## Sources

- [Wan2.2 GitHub](https://github.com/wan-video/wan2.2) — Model specs, VRAM requirements, MoE architecture, model variants
- [Wan2.2 HuggingFace (T2V-A14B)](https://huggingface.co/Wan-AI/Wan2.2-T2V-A14B) — Model specs, compression ratios, performance benchmarks
- [Wan2.2 HuggingFace (TI2V-5B)](https://huggingface.co/Wan-AI/Wan2.2-TI2V-5B) — 5B dense model specs, 4090 compatibility
- [HunyuanVideo GitHub](https://github.com/Tencent/HunyuanVideo) — Original 13B model specs, VRAM requirements, human eval results
- [HunyuanVideo 1.5 GitHub](https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5) — 8.3B model specs, 14GB VRAM, LoRA training code, Muon optimizer
- [HunyuanVideo 1.5 Technical Report](https://arxiv.org/html/2511.18870v1) — Architecture details, SSTA, VSR network, progressive training
- [HunyuanVideo-I2V GitHub](https://github.com/Tencent-Hunyuan/HunyuanVideo-I2V) — I2V model, LoRA training scripts, first-frame consistency
- [CogVideoX HuggingFace (1.5-5B)](https://huggingface.co/zai-org/CogVideoX1.5-5B) — Resolution, VRAM, frame rate, LoRA support
- [CogVideo GitHub](https://github.com/zai-org/CogVideo) — Model family comparison, LoRA fine-tuning code
- [CogVideoX-5B HuggingFace](https://huggingface.co/zai-org/CogVideoX-5b) — Fine-tuning VRAM requirements, LoRA rank
- [Mochi GitHub](https://github.com/genmoai/mochi) — 10B AsymmDiT, 480p, LoRA trainer, VRAM requirements
- [Mochi Specs (Blue Lightning)](https://bluelightningtv.com/2025/08/24/genmo-mochi-1-open-source-10b-video-ai-model-480p-5-4s-specs-architecture-and-how-to-try-it/) — Detailed specs, architecture, limitations
- [LTX-Video GitHub](https://github.com/Lightricks/LTX-Video) — LTX-2 announcement, 4K/50fps, distilled models, LoRA
- [LTX-Video Paper](https://arxiv.org/html/2501.00103) — Architecture, VAE compression, real-time generation
- [LTX-Video-Trainer GitHub](https://github.com/lightricks/ltx-video-trainer) — LoRA training, IC-LoRA, full fine-tuning, control LoRAs
- [LTX LoRA Training](https://ltx.io/model/capabilities/lora-training) — IC-LoRA character identity, training data requirements
- [Open-Sora GitHub](https://github.com/hpcaitech/Open-Sora) — Open-Sora 2.0 (11B), $200K training cost, VBench scores
- [Open-Sora 2.0 Paper](https://arxiv.org/abs/2503.09642v2) — Architecture, training stages, cost breakdown
- [Open-Sora 1.3 Report](https://github.com/hpcaitech/Open-Sora/blob/main/docs/report_04.md) — 1.1B model, 360p/720p, I2V/V2V
- [Stable Video Diffusion (SVD-XT)](https://huggingface.co/stabilityai/stable-video-diffusion-img2vid-xt) — 25 frames, 576×1024, I2V only
- [SVD Paper](https://arxiv.org/html/2311.15127) — Data curation, LoRA for camera motion, multi-view prior
- [AnimateDiff GitHub](https://github.com/guoyww/AnimateDiff) — Motion module, MotionLoRA, domain adapter, SDXL beta
- [AnimateDiff Paper](https://arxiv.org/html/2307.04725) — Plug-and-play motion priors, MotionLoRA, 3-stage training
- [Kling 3.0 Guide](https://kling.ai/quickstart/klingai-video-3-model-user-guide) — 4K, 15s, multi-shot, native audio, pricing
- [Kling 3.0 Launch (PRNewswire)](https://www.prnewswire.com/news-releases/kling-ai-launches-3-0-model-ushering-in-an-era-where-everyone-can-be-a-director-302679944.html) — Feb 5, 2026 launch, capabilities overview
- [Kling 3.0 (HokAI)](https://hokai.io/hub/models/kling-3.0) — ELO 1,248, 4K/60fps, API pricing, architecture
- [Veo 3.1 (Google AI Studio)](https://aistudio.google.com/models/veo-3) — 4K, 8s, 24fps, native audio
- [Veo 3.1 (DeepMind)](https://deepmind.google/models/veo/) — MovieGenBench results, capabilities overview
- [Veo 3.1 (Cloud Docs)](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/veo/3-1-generate) — Technical specs, aspect ratios, MIME types
- [Sora 2 API Docs](https://developers.openai.com/api/docs/models/sora-2-pro) — Resolutions, pricing, deprecation notice
- [Sora 2 Prompting Guide](https://developers.openai.com/cookbook/examples/sora/sora2_prompting_guide) — Character references, 20s max, 1080p, video extension
- [Sora 2 Launch](https://openai.com/index/sora-2/) — Sep 30, 2025 launch, capabilities, deprecation note
- [Artificial Analysis T2V Leaderboard](https://artificialanalysis.ai/video/leaderboard/text-to-video) — ELO scores, rankings, open-weight vs. proprietary
- [Artificial Analysis I2V Leaderboard](https://artificialanalysis.ai/video/leaderboard/image-to-video) — I2V ELO scores
- [Video Model Comparison (Clore.ai)](https://docs.clore.ai/guides/comparisons/video-gen-comparison) — VRAM comparison table, quality ratings, use-case recommendations
- [lora-gym (Wan 2.2 LoRA Training)](https://github.com/alvdansen/lora-gym) — 18 training templates, MoE dual-expert strategy, Modal/RunPod/local
- [Wan 2.2 LoRA Person Training Guide (Apatero)](https://apatero.com/blog/wan-2-2-lora-training-person-method-guide-2025) — Sigmoid scheduling, DOP, dual-LoRA training
- [Wan 2.2 LoRA Best Practices (Apatero)](https://apatero.com/blog/train-wan-22-loras-best-practices-2025) — Dataset requirements, hyperparameters, temporal consistency
- [Wan 2.2 I2V LoRA Guide (wan27.org)](https://wan27.org/blog/wan-2-2-lora-training-guide) — T2V vs I2V LoRA comparison, consistency ceiling table
- [HunyuanVideo LoRA Guide (Unite.AI)](https://www.unite.ai/how-to-train-and-use-hunyuan-video-lora-models/) — Windows-based training, data requirements, parameters
- [HunyuanVideo Character Consistency (PixelDojo)](https://blog.pixelailabs.com/perfect-ai-character-consistency-hunyuan-video-lora-guide/) — diffusion-pipe tool, fine-tuning parameters
- [Video-Free-LoRA (Identity Loss)](https://github.com/Kev0208/Video-Free-LoRA-Hyvideo1.5-I2V) — DINOv3 identity loss, teacher-student distillation, motion collapse prevention
