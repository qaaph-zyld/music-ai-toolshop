# Research Findings: Video LoRA & Character Consistency for Identity-Preserving Video Generation

## Scope
- Question: How do you train a LoRA directly on a video diffusion model (not just image) to maintain a specific person's identity across cinematic video clips? What are the latest techniques for identity-preserving video generation?
- Boundaries: Included — CogVideoX LoRA training, DreamBooth for video, ConsisID, MagicMirror, StableAnimator, Concat-ID, Gloria, IP-Adapter FaceID for video, face-swap post-processing (FaceFusion, ReActor), training data requirements, VRAM, training time, identity preservation quality. Excluded — text-to-image only methods, pure style transfer.
- Time spent: ~15 minutes
- Date accessed: 2026-08-20

---

## 1. CogVideoX LoRA Training (Diffusers Official)

CogVideoX is the primary open-source video diffusion model with official LoRA training support from HuggingFace Diffusers. Two scripts are provided: `train_cogvideox_lora.py` (text-to-video) and `train_cogvideox_image_to_video_lora.py` (image-to-video), both using the PEFT library backend ([Diffusers CogVideoX README](https://github.com/huggingface/diffusers/blob/main/examples/cogvideo/README.md) — accessed 2026-08-20).

### Training Data Requirements
- **Official recommendation**: 100 videos, 4000 training steps for best results ([Diffusers CogVideoX docs](https://huggingface.co/docs/diffusers/en/training/cogvideox) — accessed 2026-08-20)
- **Diffusers team experimentation**: 50 videos of a similar concept, 1500–2000 steps works well; 25 videos and 2000 steps also produced acceptable results
- **CogVideoX authors' guidance**: If videos are quite similar, 100 samples suffice; otherwise 600–700 needed ([CogVideo Issue #731](https://github.com/THUDM/CogVideo/issues/731) — accessed 2026-08-20)
- **Video format**: 480×720 resolution, 8 FPS, max 49 frames per clip (CogVideoX); CogVideoX 1.5 supports 81 frames at 768×1360
- **Prompt augmentation**: CogVideoX works best with long, descriptive LLM-augmented prompts (50–100 words). Recommended: MiniCPM-V-2.6 for VLM captioning + Llama-3.1-8B for augmentation. Official recommendation is ChatGLM
- **Data preparation**: Videos + captions in CSV or HuggingFace dataset format, with `--caption_column` and `--video_column` arguments

### VRAM Requirements (Official Hardware Table)
| Model | Training Type | Resolution (F×H×W) | VRAM |
|-------|--------------|---------------------|------|
| CogVideoX-2b | LoRA (rank128) | 49×480×720 | 16GB (RTX 4080) |
| CogVideoX-5b | LoRA (rank128) | 49×480×720 | 24GB (RTX 4090) |
| CogVideoX1.5-5b | LoRA (rank128) | 81×768×1360 | 35GB (A100) |
| CogVideoX-2b | Full SFT | 49×480×720 | 36GB (A100) |
| CogVideoX-5b | Full SFT | 49×480×720 | 42GB (A100) |

Source: ([CogVideo Finetune README](https://github.com/zai-org/CogVideo/blob/main/finetune/README.md) — accessed 2026-08-20)

### Key Hyperparameters
- **LoRA rank**: 64 recommended (rank 128 default); rank 4 too low, rank 16/32 works if base model already generates well on training captions
- **LoRA alpha**: Set to `rank` or `rank // 2` (original repo uses alpha=1, which Diffusers team found unsuitable)
- **Learning rate**: 1e-3, cosine_with_restarts scheduler, 200 warmup steps
- **Mixed precision**: fp16 for 2B model, bf16 for 5B model
- **Batch size**: 1 per GPU (video frames multiply memory)
- **Optimizer**: Adam (betas 0.9, 0.95); 8-bit Adam available via `--use_8bit_adam`

### Memory-Optimized Training: cogvideox-factory
The jointly maintained [cogvideox-factory](https://github.com/a-r-r-o-w/cogvideox-factory) repository provides memory-optimized finetuning scripts supporting:
- CPUOffloadOptimizer from torchao (optimizer step on CPU)
- Low-bit optimizers from bitsandbytes
- DeepSpeed Zero2
- Pre-computation of latents and embeddings (removes VAE/T5 from training memory)
- Enables training under 24GB VRAM

Source: ([cogvideox-factory](https://github.com/zhipuch/cogvideox-factory) — accessed 2026-08-20)

### HuggingFace Finetrainers
The [finetrainers](https://github.com/huggingface/finetrainers) library supports CogVideoX-5b LoRA with as low as **18GB VRAM** (FP8 weights, gradient checkpointing, pre-computation, rank 128, 49×512×768). Also supports LTX-Video (5GB), HunyuanVideo (32GB), and Wan models. Features DDP, FSDP-2, multiple attention backends (flash, flex, sage, xformers).

Source: ([HuggingFace Finetrainers](https://github.com/huggingface/finetrainers/) — accessed 2026-08-20)

---

## 2. Wan 2.1/2.2 LoRA Training (musubi-tuner)

Wan 2.1/2.2 is the other major open-source video model family with active LoRA training support via [musubi-tuner](https://github.com/kohya-ss/musubi-tuner) (kohya-ss).

### Key Features
- fp8 support and block swap: inference of 720×1280×81 frames with 24GB VRAM, training with 720×1280 images with 24GB VRAM
- Supports Wan 2.1 (T2V 1.3B, T2V 14B, I2V 14B) and Wan 2.2 (14B dual-expert MoE)
- Wan 2.2 uses Mixture-of-Experts: two separate experts (high-noise for composition/motion, low-noise for texture/identity) gated by timestep boundary (0.875 for T2V, 0.9 for I2V)
- For Wan 2.2, train two LoRAs per concept — one per expert — and load both at inference

Source: ([musubi-tuner Wan docs](https://github.com/kohya-ss/musubi-tuner/blob/main/docs/wan.md) — accessed 2026-08-20)

### Community Training Findings (Character/Identity LoRA)
- **Dataset**: 10–20 quality clips of 2–5 seconds each for Wan 2.1; 18 images sufficient for character LoRA (images can work for characters since Wan was pretrained on images then video)
- **Training steps**: 2000–4000 typical; 2400 steps with 38 epochs reported as optimal by one practitioner
- **Learning rate**: 2e-5 (lower than community defaults of 1e-4+); CAME optimizer with LoRAPlus (ratio 4) reported as superior
- **Network dimension**: 32–64 for characters; 128 rarely necessary
- **Resolution**: 480×272 for motion training (VRAM/time); 1280×720 native for image-based character training
- **Clip frames**: 8–16 frames per training sample; 12 is reasonable compromise

Sources: ([musubi-tuner Issue #275](https://github.com/kohya-ss/musubi-tuner/issues/275) — accessed 2026-08-20), ([Civitai WAN2.1 LoRA workflow](https://civitai.com/articles/17385) — accessed 2026-08-20)

### lora-gym: Production Training Pipeline
[alvdansen/lora-gym](https://github.com/alvdansen/lora-gym) provides 18 training templates for every Wan model variant across Modal (serverless), RunPod (bare metal), and local GPU. Supports optional `--merge` for speed LoRAs (Lightning, CausVid). Key finding: lower learning rates (2e-5 to 8e-5) consistently outperform community defaults (1e-4+).

Source: ([lora-gym](https://github.com/alvdansen/lora-gym) — accessed 2026-08-20)

---

## 3. LTX-2.3 IC-LoRA (Identity-Consistent LoRA)

LTX 2.3 introduces **IC-LoRA** (Identity-Consistent LoRA), a specialized LoRA variant for identity preservation that uses reference image + audio conditioning at inference rather than text trigger tokens.

### IC-LoRA vs Standard LoRA
| Aspect | Standard LoRA | IC-LoRA |
|--------|--------------|---------|
| Activation | Text trigger token | Reference image + audio at inference |
| What it learns | Style, concept, motion pattern | Identity mapping from reference to output |
| Dataset type | Video clips + text captions | Video clips + paired reference frames/audio |
| Training steps | 1000–2000 typical | 4000–6000 for identity (rank 128) |
| Training complexity | Lower | Higher — paired data required |

### Dataset Requirements for IC-LoRA
- **Minimum viable**: 30–50 video clips of the subject
- Each clip: 3–10 seconds, consistent lighting, face clearly visible
- Paired reference frames for each clip (first frame or held portrait)
- For voice identity: 5–10 audio reference clips, 5–15 seconds each
- Rank 128 recommended (vs 32 for standard LoRA) — gives capacity for detailed identity features

### Identity Drift Behavior
- Identity consistency holds well for 5–20 second clips
- For longer sequences, drift accumulates — character may look subtly different at second 25 vs second 5
- Practical fix: generate in segments, cut at natural edit points
- Longer generation windows maintaining identity is still an open research problem

Source: ([CrePal LTX 2.3 IC-LoRA Guide](https://crepal.ai/blog/aivideo/ltx-2-3-ic-lora-guide/) — accessed 2026-08-20)

---

## 4. ConsisID (CVPR 2025 Highlight)

[ConsisID](https://github.com/PKU-YuanGroup/ConsisID) is a **tuning-free** DiT-based identity-preserving text-to-video model. It does not require per-identity finetuning — instead, it uses frequency decomposition of facial features injected into the DiT architecture.

### Technical Approach
- **Frequency decomposition**: Facial features decomposed into low-frequency (global: profile, proportions) and high-frequency (intrinsic: identity markers unaffected by pose)
- **Global facial extractor**: Encodes reference image + facial key points into latent space → injected into shallow layers (addresses DiT's lack of U-Net skip connections)
- **Local facial extractor**: Dual-tower feature extractor captures high-frequency details → integrated into transformer blocks (addresses DiT's limited high-frequency perception)
- **Hierarchical training strategy**: Transforms vanilla pre-trained video model into IPT2V model
- Built on CogVideoX DiT backbone

### Usage
- Input: reference image (half-body or full-body preferred) + text prompt
- Output: 720×480 identity-preserving video
- Uses face models: face_helper_1, face_helper_2, face_clip_model, face_main_model, EVA transform
- Inference: 50 steps, guidance_scale 6.0

### Quality
- Outperforms ID-Animator (which can only generate talking-head-like videos with poor ID preservation)
- First tuning-free DiT-based IPT2V model
- Limitations: video smoothness and face dynamics still challenging (noted by MagicMirror paper)

Sources: ([ConsisID GitHub](https://github.com/PKU-YuanGroup/ConsisID) — accessed 2026-08-20), ([ConsisID Paper](https://arxiv.org/abs/2411.17440v3) — accessed 2026-08-20), ([ConsisID Project Page](https://pku-yuangroup.github.io/ConsisID/) — accessed 2026-08-20)

---

## 5. MagicMirror (ICCV 2025)

[MagicMirror](https://github.com/dvlab-research/magicmirror) generates identity-preserved videos with cinematic-level quality and dynamic motion. Built on CogVideoX Video DiT framework.

### Technical Approach
- **Dual-branch facial feature extractor**: Captures both identity features (ArcFace) and structural features (CLIP image encoder)
- **Conditioned Adaptive Normalization (CAN)**: Lightweight adapter that incorporates identity conditions as distribution prior into mm-DiT's layer-wise modulation. Uses dedicated adaptive normalization module for facial modality
- **Two-stage training strategy**: 
  - Stage 1 (image pre-training): LAION-Face + SFHQ + FFHQ datasets with PhotoMaker-V2 for synthetic ID pairs
  - Stage 2 (video post-training): Pexels + Mixkit datasets with synthesized image data as references
- **Zero-shot**: No per-identity finetuning required
- Minimal parameters added (lightweight adapter)

### Key Advantage
- Balances identity consistency with natural motion (avoids "static copy-paste" problem of ID-Animator and Magic-Me)
- Single-stage framework (vs two-stage image+I2V approaches that struggle with longer sequences)

Source: ([MagicMirror Paper](https://arxiv.org/html/2501.03931v1) — accessed 2026-08-20), ([MagicMirror ICCV 2025](https://openaccess.thecvf.com/content/ICCV2025/html/Zhang_MagicMirror_ID-Preserved_Video_Generation_in_Video_Diffusion_Transformers_ICCV_2025_paper.html) — accessed 2026-08-20)

---

## 6. StableAnimator (CVPR 2025)

[StableAnimator](https://github.com/francis-rings/stableanimator) is the first end-to-end ID-preserving video diffusion framework for human image animation — synthesizes high-quality videos **without any post-processing** (no FaceFusion, no GFP-GAN, no CodeFormer).

### Technical Approach
- **Input**: Reference image + sequence of poses
- **Global content-aware Face Encoder**: Face embeddings refined by interacting with image embeddings
- **Distribution-aware ID Adapter**: Prevents interference from temporal layers while preserving ID via distribution alignment (means and variances of face/image embeddings aligned)
- **HJB equation-based optimization at inference**: Hamilton-Jacobi-Bellman equation solved during denoising to constrain path toward optimal ID consistency. Integrated into diffusion denoising process — no training of diffusion components needed
- Built on video diffusion model backbone

### Resolution
- 576×1024 or 512×512
- Mixed-resolution training (512×512 in `rec` folder, 576×1024 in `vec` folder)

### Key Advantage
- Eliminates reliance on face-swapping post-processing tools entirely
- Outperforms ControlNeXt (which suffers face/body distortion even with face swapping tools)

Source: ([StableAnimator GitHub](https://github.com/francis-rings/stableanimator) — accessed 2026-08-20), ([StableAnimator Paper](https://arxiv.org/abs/2411.17697v2) — accessed 2026-08-20)

---

## 7. Concat-ID (ICCV 2025 Workshop)

[Concat-ID](https://github.com/ML-GSAI/Concat-ID) is a unified framework for identity-preserving video generation that requires **no extra modules or parameters** — uses inherent 3D self-attention mechanisms.

### Technical Approach
- VAEs extract image features → concatenated with video latents along sequence dimension
- Relies exclusively on 3D self-attention (inherent in video generation models) to incorporate identity
- **Cross-video pairing strategy**: Novel training data construction for balancing identity consistency and facial editability
- **Multi-stage training regimen**: Stage 1 on ~600K 49-frame videos → Stage 2 on ~700K 81-frame videos → fine-tune on ~200K cross-video pairs (cosine similarity threshold 0.87–0.97)
- AdaLN module (~14M parameters, negligible) for processing conditional reference images at different timesteps

### Supported Backbones
- CogVideoX-5B (single + multi-identity)
- Wan2.1-T2V-1.3B (single identity, improved with AdaLN)

### Key Advantage
- Simplest architecture — no face encoders, no adapters, no extra parameters beyond tiny AdaLN
- Supports multi-identity generation and multi-subject scenarios (virtual try-on, background-controllable)
- Pre-training model offers better identity consistency but lower editability (trade-off tunable)

Source: ([Concat-ID GitHub](https://github.com/ML-GSAI/Concat-ID) — accessed 2026-08-20), ([Concat-ID Paper](https://arxiv.org/html/2503.14151) — accessed 2026-08-20)

---

## 8. Gloria (CVPR 2026)

[Gloria](https://yyvhang.github.io/Gloria_Page/) generates **long-duration** character videos (>10 minutes) with consistent multi-view appearance and expressive identity — the longest-duration identity-preserving video generation method.

### Technical Approach
- **Content Anchors**: Compact set of anchor frames representing character's visual attributes (global scene, multiple viewpoints, various expressions)
- **Superset Content Anchoring**: Provides intra- and extra-training clip cues to prevent copy-paste artifacts
- **RoPE as Weak Condition**: Encodes positional offsets to distinguish multiple anchors, avoiding multi-reference conflicts
- **Scalable anchor extraction pipeline**: Automated extraction from massive video datasets
- Anchor tokens concatenated with video tokens for direct self-attention participation

### Key Advantage
- Only method demonstrating >10 minute videos without noticeable identity drift
- Supports multi-view appearance consistency and expression transitions
- Model-agnostic: demonstrated on both HunyuanVideo and WanVideo 2.1 (720p)

Source: ([Gloria Project Page](https://yyvhang.github.io/Gloria_Page/) — accessed 2026-08-20), ([Gloria Paper](https://arxiv.org/abs/2603.29931v1) — accessed 2026-08-20)

---

## 9. DualReal (ICCV 2025)

[DualReal](https://github.com/wenc-k/DualReal) addresses the fundamental conflict between identity and motion training — the first framework to use **adaptive joint training** instead of isolated identity/motion customization.

### Problem Solved
- Isolated training paradigm causes mutual performance deterioration: motion customization undermines identity priors and vice versa
- Optimal identity fidelity occurs unpredictably as motion training steps increase — no universal step count minimizes degradation

### Technical Approach
- **Dual-aware Adaptation**: Dynamically switches between identity and motion training steps. Non-training dimension frozen via gradient masking to prevent knowledge leakage
- **StageBlender Controller**: Coordinates denoising-stage progression and DiT layer-depth to guide identity (fine-grained) vs motion (coarse-grained) at adaptive granularity
- 1000 training steps per test case, γ=0.5 (50% chance of motion training per step), lr 1e-3, AdamW
- Output: 49 frames at 480×720

### Results
- Improves CLIP-I by 21.7% and DINO-I by 31.8% on average over baselines
- Top performance on nearly all motion metrics
- Baselines tested: MotionBooth, CogVideoX LoRA, CogVideoX full finetuning, DreamVideo

Source: ([DualReal GitHub](https://github.com/wenc-k/DualReal) — accessed 2026-08-20), ([DualReal Paper](https://arxiv.org/html/2505.02192v1) — accessed 2026-08-20)

---

## 10. 3DreamBooth (2026)

[3DreamBooth](https://ko-lani.github.io/3DreamBooth/) decouples spatial geometry from temporal motion through a 1-frame optimization paradigm, baking 3D prior without exhaustive video-based training.

### Technical Approach
- **3DreamBooth**: 1-frame spatial optimization with `[v]` identifier token — learns spatial identity from multi-view images
- **3Dapter**: Visual conditioning module acting as dynamic selective router, queries view-specific geometric hints via multi-view joint attention with shared weights
- Pre-trained in single-view mode, then extended to multi-view with shared weights
- Model-agnostic: demonstrated on HunyuanVideo and WanVideo 2.1 (720p)

### Results
- 3Dapter + 3DreamBooth (multi-view): CLIP-I 0.887, DINO-I 0.742, Overall 4.57 (outperforms VACE and Phantom)

Source: ([3DreamBooth Project Page](https://ko-lani.github.io/3DreamBooth/) — accessed 2026-08-20)

---

## 11. FantasyID (2025)

FantasyID enhances face knowledge of pre-trained video DiT models by incorporating 3D facial geometry prior.

### Technical Approach
- 3D facial geometry prior (DECA) ensures plausible facial structures
- Multi-view face augmentation prevents "copy-paste" shortcuts
- Layer-aware adaptive injection mechanism — selectively injects fused 2D+3D features into individual DiT layers (lower layers for structure, upper for details)
- Built on DiT backbone

Source: ([FantasyID Paper](https://arxiv.org/html/2502.13995v1) — accessed 2026-08-20)

---

## 12. IP-Adapter FaceID for Video

IP-Adapter FaceID uses face ID embedding from a face recognition model (ArcFace/InsightFace) instead of CLIP image embedding, combined with LoRA for improved ID consistency.

### Architecture
- IP-Adapter-FaceID = IP-Adapter model + LoRA (LoRA needed because ID embedding is harder to learn than CLIP embedding)
- FaceID-Plus V2: Shortcut structure with Q-Former, 50% CLIP embedding dropout during training
- FaceID-Portrait: Simplified for portrait-only training (ID embedding easier to learn with focused dataset)

### Video Application
- **AnimateDiff + IP-Adapter FaceID**: Established workflow in ComfyUI for vid2vid with identity preservation. Stack: AnimateDiff V3 + ControlNet + IPAdapter FaceID + FaceDetailer + ESRGAN upscale + frame interpolation
- **IPAdapterWAN**: ComfyUI extension adapting IP-Adapter for Wan 2.1 and other UNet-based video models. Uses SigLIP2 so400m vision encoder with time-conditioned resampler (Perceiver-style cross-attention compresses variable-length sequences to 64 fixed queries). Timestep scheduling for fine-grained control over when identity conditioning is active during denoising. Weight ~0.5 recommended starting point
- **Anchor-frame workflow**: IPAdapter FaceID at weight 0.8 on every keyframe + ReActor Face Detailer for similarity verification (>0.6 threshold). Last frame of clip N becomes first frame of clip N+1 via img2img at denoise 0.25

Sources: ([IP-Adapter GitHub](https://github.com/tencent-ailab/IP-Adapter) — accessed 2026-08-20), ([IPAdapterWAN GitHub](https://github.com/kaaskoek232/IPAdapterWAN) — accessed 2026-08-20), ([Dre Dyson Temporal Consistency Guide](https://dredyson.com/how-i-mastered-temporal-consistency-in-ai-video-generation-a-complete-step-by-step-fix-guide-for-maintaining-character-identity-across-clips-using-comfyui-ipadapter-faceid-and-anchor-fram/) — accessed 2026-08-20)

---

## 13. Face-Swap Post-Processing

### FaceFusion 3.6
- **Industry leading** open-source face manipulation platform (MIT license)
- Python pipeline wrapping InsightFace's `inswapper_128.onnx` with RetinaFace/YOLOFace detection, GFPGAN/CodeFormer/GPEN restoration, frame-by-frame video processing
- v3.6: improved temporal coherence, LivePortrait handoff for lip-sync, cleaner Gradio UI
- Face resolution: up to 512 with GFPGAN chain
- No watermark, CLI/programmatic API

Source: ([FaceFusion](https://www.github.com/facefusion/facefusion) — accessed 2026-08-20), ([Face Swap Tools Guide](https://www.facefusion.co/best-ai-face-swap-tools) — accessed 2026-08-20)

### ComfyUI ReActor
- Default ComfyUI face swap node (open source, SFW-only with nudity detection)
- v0.7.0: New ReActor Core — no InsightFace required, no C++ Build Tools required, Numpy 2.x friendly
- Swap engine: `inswapper_128.onnx` (128×128 output — raw swaps look soft until face restore model stacked)
- Supports HyperSwap models from FaceFusion Labs (native 512 resolution)
- **ReActorFaceBoost**: Restores and scales swapped face before pasting (via inswapper algorithms)
- **Video performance**: Frame-by-frame processing; 81 frames at 22 min on RTX 4090 (improved from earlier regression)
- Recommended chain: `retinaface_resnet50` detection → `inswapper_128` swap → `GPEN-BFR-512` restore (visibility 0.7–0.8) → RealESRGAN upscale → frame interpolation

Source: ([ComfyUI-ReActor](https://github.com/Gourieff/ComfyUI-ReActor) — accessed 2026-08-20), ([Atlas Cloud Tutorial](https://www.atlascloud.ai/blog/guides/comfyui-face-swap) — accessed 2026-08-20)

### The 128px Problem
Nearly every consumer face-swap tool uses InsightFace's `inswapper_128.onnx`, outputting 128×128 face crops. When composited into 1080p video, upscaling smears skin texture → "plastic/sticker" look. Fix: chain GFPGAN 1.4, CodeFormer (w=0.5–0.7), or GPEN as face enhancer.

Source: ([Face Swap Tools Guide](https://www.facefusion.co/best-ai-face-swap-tools) — accessed 2026-08-20)

### Wan-Animate (Wan 2.1 VACE)
- Open-weight video diffusion family specialized for driving still character with reference video
- Covers face swap, full-body motion transfer, and lip-sync simultaneously
- 720p–1080p video quality
- ComfyUI workflows widely shared
- Best 2025–2026 video face swap quality

Source: ([Face Swap Tools Guide](https://www.facefusion.co/best-ai-face-swap-tools) — accessed 2026-08-20)

---

## 14. Production Pipeline: Talking-Head Character Consistency (Wan 2.1 + LTX-2)

A production pipeline for character-consistent talking-head generation using LoRA, documented by Yaswanth Karnati:

### Data Preparation Pipeline
1. **Scene splitting**: PySceneDetect for raw footage → remove short clips
2. **Character filtering**: InsightFace/RetinaFace face detection + embedding extraction → cosine similarity matching against reference image (~85% recall)
3. **Shot classification**: Preserve viewpoint balance and framing diversity
4. **Captioning**: Qwen2.5-Omni/Gemini Flash with unique trigger word per character
5. **Latent precomputation**: Video latents + text embeddings cached before training

### Three-Stage LoRA (Improved over Single-Stage)
Splits training across timestep ranges:
- **Stage 1 (high noise)**: Structure/composition adapter
- **Stage 2 (mid noise)**: Motion adapter
- **Stage 3 (low noise)**: Fine detail/identity adapter (boosted to 1.3× scale at inference for sharper lip definition)

### Inference Tuning
- Audio guidance: 5.0 → 3.5 (curbs over-articulation)
- Motion frames: 9 → 15 (smoother transitions)
- Text guidance: 1.0 → 0.8 (better identity)
- Sample steps: 40 → 50 (higher quality)

### Finding
LTX-2 gave more flexible, production-friendly setup than Wan 2.1 for character-specific generation, with better support for LoRA adaptation.

Source: ([Medium: Building Video Models That Remember](https://medium.com/@karnati.yaswanth/getting-past-the-first-frame-building-video-models-that-remember-31f03d0710e1) — accessed 2026-08-20)

---

## Existing Solutions / Tools

| Name | URL | Tech Stack | License | Stars/Popularity | Key Features | Gaps |
|------|-----|------------|---------|-------------------|--------------|------|
| CogVideoX LoRA (Diffusers) | [GitHub](https://github.com/huggingface/diffusers/tree/main/examples/cogvideo) | PyTorch, Diffusers, PEFT | Apache 2.0 | Very high (Diffusers) | Official T2V + I2V LoRA, 16GB VRAM min | Only tested on 2B model; limited features |
| cogvideox-factory | [GitHub](https://github.com/a-r-r-o-w/cogvideox-factory) | PyTorch, TorchAO, DeepSpeed | Apache 2.0 | Moderate | Memory-optimized, <24GB VRAM, multi-resolution | Community-maintained |
| Finetrainers | [GitHub](https://github.com/huggingface/finetrainers) | PyTorch, FSDP-2 | Apache 2.0 | High (HF official) | Multi-model (CogVideoX, LTX, Hunyuan, Wan), 18GB min | Work-in-progress |
| musubi-tuner | [GitHub](https://github.com/kohya-ss/musubi-tuner) | PyTorch, Kohya | Apache 2.0 | Very high (kohya) | Wan 2.1/2.2, HunyuanVideo, fp8, block swap | Unofficial, complex config |
| lora-gym | [GitHub](https://github.com/alvdansen/lora-gym) | Python, Modal/RunPod | Open | Growing | 18 Wan templates, triple-platform, --merge | Wan-only currently |
| ConsisID | [GitHub](https://github.com/PKU-YuanGroup/ConsisID) | PyTorch, Diffusers | Apache 2.0 | High (CVPR 2025) | Tuning-free, frequency decomposition, DiT | Smoothness/face dynamics issues |
| MagicMirror | [GitHub](https://github.com/dvlab-research/magicmirror) | PyTorch, CogVideoX | TBD (ICCV 2025) | Moderate | Zero-shot, CAN adapter, dual-branch facial | Code release pending |
| StableAnimator | [GitHub](https://github.com/francis-rings/stableanimator) | PyTorch | TBD (CVPR 2025) | Moderate | End-to-end, no post-processing, HJB optimization | Pose-driven only (not T2V) |
| Concat-ID | [GitHub](https://github.com/ML-GSAI/Concat-ID) | PyTorch, CogVideoX/Wan | MIT | Moderate | No extra params, multi-identity, multi-subject | Body structure issues (fingers) |
| Gloria | [Page](https://yyvhang.github.io/Gloria_Page/) | PyTorch | TBD (CVPR 2026) | New | >10 min videos, content anchors, multi-view | Code not yet public |
| DualReal | [GitHub](https://github.com/wenc-k/DualReal) | PyTorch, CogVideoX | TBD (ICCV 2025) | Moderate | Joint identity+motion training | Research-focused |
| 3DreamBooth | [Page](https://ko-lani.github.io/3DreamBooth/) | PyTorch | TBD (2026) | New | 3D prior, 1-frame optimization, multi-view | Early stage |
| FantasyID | [Paper](https://arxiv.org/html/2502.13995v1) | PyTorch, DiT | TBD | Low | 3D facial geometry prior, layer-aware injection | Code availability TBD |
| IP-Adapter FaceID | [GitHub](https://github.com/tencent-ailab/IP-Adapter) | PyTorch | Apache 2.0 | Very high | ArcFace ID embedding + LoRA, video via AnimateDiff | Image-focused, video needs adapters |
| IPAdapterWAN | [GitHub](https://github.com/kaaskoek232/IPAdapterWAN) | ComfyUI, Wan 2.1 | Open | Low | Wan 2.1 + AnimateDiff support, timestep scheduling | Community extension |
| FaceFusion 3.6 | [GitHub](https://www.github.com/facefusion/facefusion) | Python, InsightFace | MIT | Very high | Full pipeline, temporal coherence, lip-sync | 128px native, frame-by-frame |
| ComfyUI ReActor | [GitHub](https://github.com/Gourieff/ComfyUI-ReActor) | ComfyUI, InsightFace | Open | High | ComfyUI integration, face boost, HyperSwap | 128px native, Python 3.13 issues |
| Wan-Animate | ComfyUI workflows | Wan 2.1 VACE | Open weights | Growing | 720p–1080p, face+body+lip-sync | Requires ComfyUI expertise |

---

## Summary: Training Data Requirements Comparison

| Method | Min. Data | Data Type | Training Steps | VRAM | Identity Quality |
|--------|-----------|-----------|----------------|------|------------------|
| CogVideoX LoRA | 25–100 clips | Video clips + captions | 1500–4000 | 16–24GB | Good (concept-level) |
| Wan 2.1 LoRA | 10–20 clips/images | Video or images | 2000–4000 | 24GB | Good (character-level) |
| LTX IC-LoRA | 30–50 clips | Paired video + reference | 4000–6000 | 24GB+ | Strong (identity-focused) |
| ConsisID | None (tuning-free) | Reference image at inference | N/A (pre-trained) | ~24GB inference | Good (face-focused) |
| MagicMirror | None (zero-shot) | Reference image at inference | N/A (pre-trained) | ~24GB inference | Strong (cinematic) |
| StableAnimator | None (pre-trained) | Reference image + pose sequence | N/A | ~24GB inference | Strong (no post-processing) |
| Concat-ID | None (pre-trained) | Reference image at inference | N/A | ~24GB inference | Good (multi-identity) |
| DualReal | Identity images + motion videos | Per-subject training | ~1000 | ~24GB | Very strong (joint ID+motion) |
| FaceFusion/ReActor | 1 reference image | Face swap post-processing | N/A | 8–24GB | Moderate (128px limit) |

---

## Open Questions

1. **Identity vs motion trade-off**: All methods struggle with balancing identity preservation and natural motion. DualReal addresses this via joint training but requires per-subject training. Which approach (tuning-free vs joint training) is more practical for production?
2. **Long-video identity drift**: Only Gloria demonstrates >10 minute consistency. How do other methods degrade over longer sequences? What is the practical clip length limit before drift becomes noticeable?
3. **Multi-identity generation**: Concat-ID supports multi-identity, but quality and scalability to 3+ identities in a single frame is unclear.
4. **Training data quality vs quantity**: Community consensus favors quality over quantity (15–30 clips), but the optimal dataset composition (angles, lighting, expressions, backgrounds) for identity LoRA is not well-documented.
5. **Wan 2.2 MoE training**: The dual-expert architecture requires training two LoRAs per concept. How does this affect training time and cost? Is the quality improvement over Wan 2.1 significant?
6. **Face-swap vs generation-native identity**: When is post-processing (FaceFusion/ReActor) preferable to generation-native identity preservation? The 128px limitation of face-swap vs the computational cost of identity-conditioned generation.
7. **Code availability**: MagicMirror, Gloria, and FantasyID have not fully released code/models as of access date. When will these be available for testing?
8. **VRAM for production training**: Most VRAM figures are for minimal configurations. What are realistic VRAM requirements for high-quality identity LoRA training at production resolution (720p+)?

---

## Sources

- [Diffusers CogVideoX README](https://github.com/huggingface/diffusers/blob/main/examples/cogvideo/README.md) — Training scripts, hyperparameters, data prep
- [Diffusers CogVideoX Docs](https://huggingface.co/docs/diffusers/en/training/cogvideox) — Official training guide, VRAM, steps
- [CogVideo Finetune README](https://github.com/zai-org/CogVideo/blob/main/finetune/README.md) — Official hardware requirements table
- [CogVideo Issue #731](https://github.com/THUDM/CogVideo/issues/731) — Community VRAM issues, data quantity guidance
- [cogvideox-factory](https://github.com/a-r-r-o-w/cogvideox-factory) — Memory-optimized finetuning scripts
- [HuggingFace Finetrainers](https://github.com/huggingface/finetrainers/) — Multi-model training library, VRAM table
- [musubi-tuner Wan docs](https://github.com/kohya-ss/musubi-tuner/blob/main/docs/wan.md) — Wan 2.1/2.2 LoRA training
- [musubi-tuner Issue #275](https://github.com/kohya-ss/musubi-tuner/issues/275) — Character training tips, hyperparameters
- [Civitai WAN2.1 LoRA workflow](https://civitai.com/articles/17385) — 18-image character LoRA workflow
- [lora-gym](https://github.com/alvdansen/lora-gym) — 18 Wan training templates, production pipeline
- [CrePal LTX 2.3 IC-LoRA Guide](https://crepal.ai/blog/aivideo/ltx-2-3-ic-lora-guide/) — IC-LoRA vs standard LoRA, identity drift
- [CrePal LTX 2.3 LoRA Migration](https://crepal.ai/blog/aivideo/ltx-2-3-lora-migration-retrain/) — Dataset requirements, hardware, hyperparameters
- [LTX Blog: Build LoRA Dataset](https://ltx.io/blog/build-the-dataset-lora) — Dataset preparation best practices
- [Apatero: Wan 2.2 LoRA Guide](https://apatero.com/blog/train-wan-22-loras-best-practices-2025) — Video LoRA training best practices
- [ConsisID GitHub](https://github.com/PKU-YuanGroup/ConsisID) — Tuning-free IPT2V, frequency decomposition
- [ConsisID Paper](https://arxiv.org/abs/2411.17440v3) — Technical details, frequency analysis
- [ConsisID Project Page](https://pku-yuangroup.github.io/ConsisID/) — Visual results, overview
- [MagicMirror Paper](https://arxiv.org/html/2501.03931v1) — CAN adapter, dual-branch facial, two-stage training
- [MagicMirror ICCV 2025](https://openaccess.thecvf.com/content/ICCV2025/html/Zhang_MagicMirror_ID-Preserved_Video_Generation_in_Video_Diffusion_Transformers_ICCV_2025_paper.html) — Official publication
- [StableAnimator GitHub](https://github.com/francis-rings/stableanimator) — End-to-end ID-preserving animation
- [StableAnimator Paper](https://arxiv.org/abs/2411.17697v2) — HJB optimization, distribution-aware ID adapter
- [Concat-ID GitHub](https://github.com/ML-GSAI/Concat-ID) — No-extra-params IPT2V, multi-identity
- [Concat-ID Paper](https://arxiv.org/html/2503.14151) — VAE concatenation, cross-video pairing
- [Gloria Project Page](https://yyvhang.github.io/Gloria_Page/) — Content anchors, >10 min videos
- [Gloria Paper](https://arxiv.org/abs/2603.29931v1) — Superset Content Anchoring, RoPE as Weak Condition
- [DualReal GitHub](https://github.com/wenc-k/DualReal) — Joint identity+motion training
- [DualReal Paper](https://arxiv.org/html/2505.02192v1) — Dual-aware Adaptation, StageBlender Controller
- [3DreamBooth Project Page](https://ko-lani.github.io/3DreamBooth/) — 3D prior, 1-frame optimization
- [FantasyID Paper](https://arxiv.org/html/2502.13995v1) — 3D facial geometry, layer-aware injection
- [IP-Adapter GitHub](https://github.com/tencent-ailab/IP-Adapter) — FaceID architecture, ArcFace + LoRA
- [IPAdapterWAN GitHub](https://github.com/kaaskoek232/IPAdapterWAN) — Wan 2.1 IP-Adapter, timestep scheduling
- [Dre Dyson Temporal Consistency Guide](https://dredyson.com/how-i-mastered-temporal-consistency-in-ai-video-generation-a-complete-step-by-step-fix-guide-for-maintaining-character-identity-across-clips-using-comfyui-ipadapter-faceid-and-anchor-fram/) — Anchor-frame workflow, 8GB VRAM
- [FaceFusion](https://www.github.com/facefusion/facefusion) — Industry leading face manipulation platform
- [Face Swap Tools Guide](https://www.facefusion.co/best-ai-face-swap-tools) — Comprehensive tool comparison, 128px problem
- [ComfyUI-ReActor](https://github.com/Gourieff/ComfyUI-ReActor) — ComfyUI face swap node, HyperSwap support
- [Atlas Cloud ComfyUI Tutorial](https://www.atlascloud.ai/blog/guides/comfyui-face-swap) — ReActor setup, video workflow, settings
- [Medium: Building Video Models That Remember](https://medium.com/@karnati.yaswanth/getting-past-the-first-frame-building-video-models-that-remember-31f03d0710e1) — Production pipeline, three-stage LoRA, Wan vs LTX
- [Diffusers DreamBooth docs](https://huggingface.co/docs/diffusers/main/en/training/dreambooth) — DreamBooth + LoRA training reference
