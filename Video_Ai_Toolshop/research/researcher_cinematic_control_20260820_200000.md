# Research Findings: Cinematic Control in AI Video Generation

## Scope
- **Question:** How do you achieve cinematic camera movements, film lighting, depth of field, and professional composition in AI video generation? What control mechanisms exist (ControlNet for video, camera LoRAs, motion modules, prompt engineering for cinematic output)?
- **Boundaries:** Included — Camera control in CogVideoX, AnimateDiff motion LoRAs, ControlNet for video (OpenPose, Depth, Canny, HED), LiON-LoRA camera control, DimensionX, prompt engineering for cinematic style, ComfyUI workflows for cinematic video. Excluded — basic text-to-video without control, pre-2024 methods.
- **Time spent:** ~15 minutes
- **Date accessed:** 2026-08-20

---

## Key Findings

### 1. Camera Control in CogVideoX

- **AC3D (Snap Research)** — Plücker-conditioned ControlNet architecture built on CogVideoX. Provides 3D camera control for video diffusion transformers. Pre-trained checkpoints for CogVideoX-2B (48GB VRAM) and CogVideoX-5B (80GB VRAM). Improves camera control quality by analyzing and fixing issues in Plücker embedding conditioning. ([AC3D GitHub](https://github.com/snap-research/ac3d) — accessed 2026-08-20)

- **CamTrol-CogVideoX** — Training-free camera control for CogVideoX via diffusers. Two-stage process: (1) explicit 3D point cloud rendering with camera trajectory, (2) layout prior of noisy latents guides generation. Supports zoom, tilt, pan, pedestal, truck, roll, and complex combined trajectories. No fine-tuning required — plug-and-play. ([CamTrol-CogVideoX GitHub](https://github.com/LAARRRY/CamTrol-CogVideoX-Diffusers) — accessed 2026-08-20)

- **NimVideo CogVideoX LoRA** — Prompt-controlled camera movement LoRA for CogVideoX-5B. Controls 6 directions: left, right, up, down, zoom_in, zoom_out. Triggered via prompt text (e.g., "Camera is moving to the left"). Simple to use with diffusers pipeline. ([NimVideo HuggingFace](https://huggingface.co/NimVideo/cogvideox1.5-5b-prompt-camera-motion) — accessed 2026-08-20)

- **Time-to-Move (TTM)** — Plug-and-play camera control for CogVideoX, Wan 2.2, and SVD. Accepted to ICLR 2026. Includes a camera-control GUI using Apple's Depth Pro for metric depth estimation. Uses "tweak-index" and "tstrong-index" parameters to balance motion fidelity vs. video diversity. ([TTM GitHub](https://github.com/time-to-move/TTM) — accessed 2026-08-20)

### 2. AnimateDiff Motion LoRAs (Pan, Zoom, Dolly)

- **MotionLoRA v1.5.3** — Official lightweight fine-tuning technique for AnimateDiff motion modules. Provides 8 camera movement LoRAs: Zoom In, Zoom Out, Pan Left, Pan Right, Tilt Up, Tilt Down, Rolling Clockwise, Rolling Anticlockwise. Each LoRA is ~19M parameters / 74MB storage. Triggered via prompt keywords (e.g., `<lora:v2_lora_ZoomIn:1>Zoom In`). Multiple LoRAs can be combined (e.g., pan left + zoom in = dolly zoom effect). ([AnimateDiff MotionLoRA HuggingFace](https://huggingface.co/guoyww/animatediff-motion-lora-v1-5-3) — accessed 2026-08-20)

- **Motion Module Architecture** — Plug-and-play motion module trained on WebVid-10M learns transferable motion priors. Inserted into personalized T2I models to create animation generators. Domain adapter aligns visual distribution; motion module focuses on motion patterns only. ([AnimateDiff Paper (arXiv:2307.04725)](https://arxiv.org/pdf/2307.04725) — accessed 2026-08-20)

- **Civitai Motion LoRA Wiki** — Community documentation confirms Motion LoRAs work with AnimateDiff v2 module. Combining LoRAs creates complex cinematic effects. Trigger words and LoRA offset strings required in prompt. ([Civitai AnimateDiff Wiki](https://wiki.civitai.com/wiki/AnimateDiff) — accessed 2026-08-20)

### 3. ControlNet for Video (OpenPose, Depth, Canny, HED)

- **ControlVideo (ICLR 2024)** — Adapts ControlNet to video without fine-tuning. Supports canny edges, depth maps, and human poses (OpenPose). Uses cross-frame interaction and interleaved-frame smoother for temporal consistency. Supports long video generation. Built on SD1.5 + ControlNet 1.0/1.1. ([ControlVideo GitHub](https://github.com/YBYBZhang/ControlVideo) — accessed 2026-08-20)

- **Wan 2.1/2.2 Fun Control** — ControlNet-inspired framework for Wan model family. Extracts Depth, Canny, or OpenPose passes from input video to guide generation. 1.3B and 14B parameter variants. Compatible with standard ControlNet preprocessor modules. Multi-modal control: pose, depth, canny edge, and trajectory control. ([RunComfy Wan 2.1 Fun](https://www.runcomfy.com/comfyui-workflows/wan-2-1-fun-controlnet-ai-video-generation-with-depth-canny-openpose-control) — accessed 2026-08-20)

- **ControlNet Stacking for Video** — Professional workflows combine 2-3 ControlNets simultaneously:
  - **Depth** (strength 0.7-0.8): spatial relationships, camera movement, scene establishment
  - **Pose/OpenPose** (strength 0.6-0.7): character skeleton, action consistency
  - **Canny/Edge** (strength 0.4-0.6): structural preservation, prevents scene drift
  - VRAM: 12-16GB for 2 ControlNets at 512×512; 16-24GB for 3 ControlNets at 768×768
  - ([Apatero ControlNet Stacking Guide](https://apatero.com/blog/video-controlnet-stacking-depth-pose-edge-advanced-guide-2025) — accessed 2026-08-20)

- **ControlNeXt** — Efficient alternative to ControlNet for video. Replaces heavy parallel branch with lightweight convolutional network. Reduces trainable parameters by up to 90%. Uses Cross Normalization instead of zero-convolution for faster, stable training. Seamlessly integrates with LoRA weights for style alteration. ([ControlNeXt (arXiv:2408.06070)](https://arxiv.org/html/2408.06070v1) — accessed 2026-08-20)

- **LTX-2 ControlNet** — IC LoRA-based ControlNet conditioning for LTX-2 video model. Supports depth, canny, and pose control paths. Two-stage architecture with latent upscaling. Unified audio-visual latent space for synchronized output. ([RunComfy LTX-2 ControlNet](https://www.runcomfy.com/comfyui-workflows/ltx-2-controlnet-in-comfyui-depth-controlled-video-workflow) — accessed 2026-08-20)

- **SDXL ControlNet-Union** — Single model supporting depth, canny, openpose, softedge, and normal conditioning. Eliminates need for separate ControlNet models per type. Also supports IP-Adapter feedback for motion-warped frame conditioning. ([controlnetvideo GitHub](https://github.com/un1tz3r0/controlnetvideo) — accessed 2026-08-20)

### 4. LiON-LoRA Camera Control

- **LiON-LoRA (ICCV 2025)** — Novel framework rethinking LoRA fusion for video diffusion. Three core principles:
  1. **Linear scalability** — Scaling token integrated into DiT linearly adjusts motion amplitude for cameras and objects
  2. **Orthogonality** — LoRA features from shallow VDM layers exhibit low correlation, enabling decoupled low-level controllability
  3. **Norm consistency** — Normalizes output norms across layers to stabilize fusion of complex camera motion combinations
  - Extends to temporal generation using static-camera videos, unifying spatial (3D) and temporal (4D) controllability
  - Outperforms SOTA in trajectory control accuracy and motion strength adjustment with minimal training data
  - ([LiON-LoRA ICCV Paper](https://openaccess.thecvf.com/content/ICCV2025/papers/Zhang_LiON-LoRA_Rethinking_LoRA_Fusion_to_Unify_Controllable_Spatial_and_Temporal_ICCV_2025_paper.pdf) — accessed 2026-08-20)

### 5. DimensionX

- **DimensionX (ICCV 2025)** — Framework for generating 3D and 4D scenes from a single image using controllable video diffusion. Key innovation: **ST-Director** decouples spatial and temporal factors via dimension-aware LoRAs:
  - **S-Director** — Trained on spatial-variant datasets (camera moves, scene static). 12 fundamental camera LoRA modules covering 6 DoF (both directions), plus 4 orbit LoRAs (up, down, left, right)
  - **T-Director** — Trained on temporal-variant datasets (camera static, scene evolves)
  - Training-free dimension-aware composition for hybrid control
  - Trajectory-aware mechanism for 3D generation; identity-preserving denoising for 4D
  - All checkpoints open-sourced (Oct 2025): S-Director, T-Director, 360° orbit model, training pipeline, datasets
  - ([DimensionX GitHub](https://github.com/wenqsun/DimensionX) — accessed 2026-08-20)

### 6. CameraCtrl (Foundational Method)

- **CameraCtrl (ICLR 2025)** — Foundational camera control method for video diffusion. Uses **Plücker embeddings** as camera pose representation: for each pixel (u,v), embedding is p = (o × d, d) ∈ ℝ⁶, where o is camera center and d is direction vector. Plug-and-play camera module trained on top of T2V model. Best results with RealEstate10K dataset (diverse camera poses, similar appearance to base model). Implemented on AnimateDiffV3 and SVD. ([CameraCtrl arXiv](https://arxiv.org/html/2404.02101v1) — accessed 2026-08-20)

### 7. Prompt Engineering for Cinematic Style

- **Five Pillars Framework** — Every effective cinematic prompt contains: Camera (movement, angle, lens), Lighting (source, quality, direction, color), Subject (physical appearance, action), Environment (setting, atmosphere), Technical Style (film stock, DOF, grain, color grading). Specific terms outperform vague emotional language. ([Neural4D Cinematic Prompts Guide](https://blog.neural4d.com/text-to-video/cinematic-ai-video-prompts/) — accessed 2026-08-20)

- **Lens Language** — AI models interpret focal lengths as biasing descriptors:
  - 16-24mm (wide): exaggerated depth, environmental context
  - 35-50mm (standard): natural perspective, closest to human vision
  - 85-135mm (telephoto): compressed depth, subject isolation
  - 200mm+: extreme compression, layered backgrounds
  - "35mm anamorphic" triggers oval bokeh, horizontal lens flares, wider field of view
  - ([Sora 2 Cinematic Guide](https://videoai.me/blog/sora-2-cinematic-video-creation) — accessed 2026-08-20)

- **Lighting Cues** — Most impactful single element for realism:
  - Source: "backlit window with warm morning sun," "neon sign reflecting off wet pavement"
  - Quality: soft diffusion vs. hard shadows
  - Direction: rim light, side-lit, top-down, underexposure from below
  - Named patterns: "Rembrandt lighting," "chiaroscuro," "golden hour," "three-point studio lighting"
  - Atmospheric effects: volumetric fog, god rays, dust particles, smoke
  - ([Seedance 2.0 Cinematic Guide](https://www.vidau.ai/seedance-2-0-the-best-guide-to-creating-cinematic-ai-video/) — accessed 2026-08-20)

- **Anamorphic Flare Prompting** — Prompt the *cause*, not the *effect*:
  - ❌ "add blue streaks" → 40% higher quality control failure rate
  - ✅ "bright pinpoint practical light" + "thin volumetric haze" + "coated anamorphic glass" + "2.39:1 cinema scope"
  - Low-angle shots + wide aspect ratios trigger anamorphic association in model
  - ([Hailuo AI Anamorphic Guide](https://blog.hailuoai.video/knowledge/prompt-anamorphic-flares-film-looks) — accessed 2026-08-20)

- **Iterative Subtractive Approach** — Start with minimalist prompt (core subject + single style descriptor), add motion/detail keywords one at a time, generate after each addition to isolate effects. ([Hailuo AI Cinematic Guide](https://hailuoai.video/pages/knowledge/cinematic-ai-video-prompts-guide) — accessed 2026-08-20)

- **Image-to-Video Pipeline for Consistency** — Generate high-quality static image first (Master Reference), then use I2V with only camera motion prompt changes. Locks environment, lighting, and subject while handling temporal animation. Prevents "motion collapse" (subject warping/melting). ([Hailuo AI Cinematic Guide](https://hailuoai.video/pages/knowledge/cinematic-ai-video-prompts-guide) — accessed 2026-08-20)

- **Technical Style Keywords That Work:**
  - Film grain: "subtle 35mm film grain" (specify "subtle" not "heavy")
  - Aspect ratio: "2.35:1 anamorphic" or "2.39:1 cinema scope"
  - Color grading: "teal and orange grade," "muted desaturated palette"
  - DOF: "shallow depth of field," "f/1.4 aperture"
  - Film stocks: "Kodak Portra 400," "fine film grain"
  - Avoid: "best," "high quality" (statistically diluted); use "photorealistic," "8k resolution render"
  - ([Neural4D Guide](https://blog.neural4d.com/text-to-video/cinematic-ai-video-prompts/) — accessed 2026-08-20)

### 8. ComfyUI Workflows for Cinematic Video

- **Wan 2.2 14B Fun Camera Control** — ComfyUI workflow with WanCameraEmbedding node for camera path construction. Two-pass denoise: high-noise phase (establish motion/structure/parallax) → low-noise phase (refine details, reduce flicker). Optional LightX2V 4-Step LoRA for speed. ~84% VRAM on RTX 4090D 24GB at 640×640. ([Comfy.org Wan 2.2 Camera Control](https://comfy.org/workflows/video_wan2_2_14B_fun_camera-9dac2dae8bfc/) — accessed 2026-08-20)

- **Wan 2.2 14B Fun Control** — Multi-modal controlled video generation supporting pose, depth, canny edge, and trajectory control. Wan22FunControlToVideo node fuses text prompt with control streams. Supports multi-resolution (512/768/1024), 81 frames at 16 FPS. ([Comfy.org Wan 2.2 Fun Control](https://comfy.org/workflows/video_wan2_2_14B_fun_control-67a816af8a73/) — accessed 2026-08-20)

- **Seedance 2.0 Reference-to-Video** — ComfyUI workflow: LoadImage → ByteDance2ReferenceNode → SaveVideo. Combines identity lock with prompt-driven motion/lighting. Camera cues (dolly-in, slow pan left) and style hints (35mm, shallow DOF) in prompt. ([Comfy.org Seedance 2.0 R2V](https://comfy.org/workflows/api_seedance2_0_r2v-64f4db9e3e33/) — accessed 2026-08-20)

- **Cinematic Annotate Video** — Automated workflow: LoadImage → GeminiImage2Node (analyzes scene, generates camera-path markup "Nano Banana 2" style) → GeminiNode (formats to Seedance 2.0 motion spec) → ByteDance2ReferenceNode → SaveVideo. Auto-writes director-style camera paths from a single frame. ([Comfy.org Cinematic Annotate](https://comfy.org/workflows/0136284ecc19-0136284ecc19/) — accessed 2026-08-20)

- **Cinematography Prompt Builder Node** — ComfyUI custom node (ArchAi3D) with dropdown selectors for camera_angle, depth_of_field (Auto/Shallow/Extreme Shallow/Deep), style_mood (Cinematic/Dramatic/Documentary/etc.), camera_movement, photography_quality. Structured prompt construction for consistent cinematic output. ([Comfy.icu Cinematography Prompt Builder](https://comfy.icu/node/ArchAi3D_Cinematography_Prompt_Builder) — accessed 2026-08-20)

- **Wan 2.2 Day-0 ComfyUI Support** — Native support for Wan2.2 in ComfyUI with cinematic aesthetic control. Professional camera language supporting multi-dimensional visual controls (lighting, color, composition). High-noise and low-noise expert models divided by denoising timesteps. ([Comfy.org Wan 2.2 Blog](https://blog.comfy.org/p/wan22-day-0-support-in-comfyui) — accessed 2026-08-20)

---

## Existing Solutions / Tools

| Name | URL | Tech Stack | License | Stars/Popularity | Key Features | Gaps |
|------|-----|------------|---------|-------------------|--------------|------|
| AC3D | [GitHub](https://github.com/snap-research/ac3d) | CogVideoX, Plücker ControlNet | Research | New | 3D camera control for video DiT, 2B/5B variants | High VRAM (48-80GB), research code |
| CamTrol | [GitHub](https://github.com/LAARRRY/CamTrol) | SVD, CogVideoX, diffusers | MIT | 34★ | Training-free, point cloud 3D, complex trajectories | Unofficial implementation, SVD-focused |
| CameraCtrl | [GitHub](https://github.com/hehao13/CameraCtrl) | AnimateDiffV3, SVD, Plücker | Research | Active | Plug-and-play camera module, trajectory parameterization | Requires training data, SD1.5-based |
| AnimateDiff MotionLoRA | [HuggingFace](https://huggingface.co/guoyww/animatediff-motion-lora-v1-5-3) | AnimateDiff v2/v3 | Open | Widely used | 8 camera LoRAs, combinable, 74MB each | Limited to SD1.5, basic movements |
| LiON-LoRA | [ICCV Paper](https://openaccess.thecvf.com/content/ICCV2025/papers/Zhang_LiON-LoRA_Rethinking_LoRA_Fusion_to_Unify_Controllable_Spatial_and_Temporal_ICCV_2025_paper.pdf) | Video DiT, LoRA fusion | Research | ICCV 2025 | Linear scalability, orthogonality, norm consistency, 4D | Academic, no public code yet |
| DimensionX | [GitHub](https://github.com/wenqsun/DimensionX) | Video diffusion, LoRA | Open | ICCV 2025 | 12 camera + 4 orbit LoRAs, 3D/4D scenes, ST-Director | Focused on scene reconstruction |
| ControlVideo | [GitHub](https://github.com/YBYBZhang/ControlVideo) | SD1.5, ControlNet | Open | ICLR 2024 | Training-free, canny/depth/pose, long video | SD1.5 only, limited resolution |
| Wan 2.2 Fun Control | [Comfy.org](https://comfy.org/workflows/video_wan2_2_14B_fun_control-67a816af8a73/) | Wan 2.2, ComfyUI | Open | Active | Pose/depth/canny/trajectory, 14B, multi-resolution | High VRAM for 14B |
| TTM (Time-to-Move) | [GitHub](https://github.com/time-to-move/TTM) | Wan 2.2, CogVideoX, SVD | Open | ICLR 2026 | Plug-and-play, camera GUI, Depth Pro | New, limited community |
| NimVideo CogVideoX LoRA | [HuggingFace](https://huggingface.co/NimVideo/cogvideox1.5-5b-prompt-camera-motion) | CogVideoX-5B, LoRA | Open | New | 6-direction prompt-controlled camera | Limited to 6 basic directions |
| ControlNeXt | [arXiv](https://arxiv.org/html/2408.06070v1) | Various base models | Research | Active | 90% fewer params, Cross Norm, LoRA compatible | Newer, less community adoption |
| LTX-2 ControlNet | [RunComfy](https://www.runcomfy.com/comfyui-workflows/ltx-2-controlnet-in-comfyui-depth-controlled-video-workflow) | LTX-2, IC LoRA, ComfyUI | Open | Active | Audio-visual sync, depth/canny/pose, latent upscaling | LTX-specific |
| Seedance 2.0 R2V | [Comfy.org](https://comfy.org/workflows/api_seedance2_0_r2v-64f4db9e3e33/) | Seedance 2.0, ComfyUI | Commercial | Active | Identity lock, prompt-driven motion/lighting | Commercial model |
| Cinematic Annotate | [Comfy.org](https://comfy.org/workflows/0136284ecc19-0136284ecc19/) | Gemini + Seedance 2.0 | Mixed | New | Auto camera-path from image analysis | Requires Gemini API |

---

## Open Questions

- **LiON-LoRA code availability** — Paper published at ICCV 2025 but no public code repository found as of access date. Project page referenced at `https://fuchengsu.github.io/lionlora.github.io/` but not verified.
- **HED/SoftEdge for video** — HED and soft edge ControlNets are mentioned in SDXL ControlNet-Union models but dedicated video-specific HED workflows are sparse; most video ControlNet work focuses on Depth, Canny, and OpenPose.
- **ComfyUI integration of AC3D** — AC3D provides CogVideoX ControlNet checkpoints but no native ComfyUI nodes were found; would require custom node development.
- **Wan 2.2 camera embedding API** — WanCameraEmbedding node exists in ComfyUI but documentation on custom trajectory definition (beyond preset pan/zoom/rotation) is limited.
- **Combining prompt engineering with structural control** — Best practices for stacking prompt-driven cinematic style (film grain, anamorphic) alongside ControlNet structural guidance (depth, pose) are not well documented; the two approaches are typically discussed separately.
- **VRAM requirements for production** — Most advanced methods (AC3D 5B, Wan 2.2 14B, LiON-LoRA) require 24-80GB VRAM, limiting accessibility; FP8 quantization helps but quality trade-offs are not fully characterized.

---

## Sources

- [AC3D GitHub Repository](https://github.com/snap-research/ac3d) — Plücker-conditioned ControlNet for CogVideoX camera control
- [CamTrol Project Page](https://lifedecoder.github.io/CamTrol/) — Training-free camera control via 3D point cloud
- [CamTrol-CogVideoX GitHub](https://github.com/LAARRRY/CamTrol-CogVideoX-Diffusers) — Diffusers-based CogVideoX implementation
- [CamTrol Paper (arXiv:2406.10126)](https://arxiv.org/html/2406.10126v1) — Two-stage training-free camera control
- [CameraCtrl arXiv](https://arxiv.org/html/2404.02101v1) — Plücker embeddings for camera pose representation
- [CameraCtrl GitHub](https://github.com/hehao13/CameraCtrl) — Implementation on AnimateDiffV3 and SVD
- [AnimateDiff Paper (arXiv:2307.04725)](https://arxiv.org/pdf/2307.04725) — Motion module and MotionLoRA framework
- [AnimateDiff MotionLoRA v1.5.3](https://huggingface.co/guoyww/animatediff-motion-lora-v1-5-3) — 8 camera movement LoRAs
- [Civitai AnimateDiff Wiki](https://wiki.civitai.com/wiki/AnimateDiff) — Community docs for Motion LoRAs
- [AnimateDiff Motion Guide](https://andyhtu.com/understanding-motion-and-lora-models-for-animatediff/) — Trigger words and LoRA offsets
- [ControlVideo GitHub](https://github.com/YBYBZhang/ControlVideo) — Training-free ControlNet for video (ICLR 2024)
- [ControlVideo Project Page](https://controlvideov1.github.io/) — Depth, canny, pose visualizations
- [Wan 2.1 Fun ControlNet](https://www.runcomfy.com/comfyui-workflows/wan-2-1-fun-controlnet-ai-video-generation-with-depth-canny-openpose-control) — ComfyUI workflow for Wan 2.1 Fun
- [ControlNet Stacking Guide](https://apatero.com/blog/video-controlnet-stacking-depth-pose-edge-advanced-guide-2025) — Multi-ControlNet VRAM and strength settings
- [Video ControlNet Complete Guide](https://apatero.com/blog/video-controlnet-explained-pose-depth-edge-control-2025) — CogVideoX + DWPose + depth/edge
- [ControlNeXt (arXiv:2408.06070)](https://arxiv.org/html/2408.06070v1) — Efficient ControlNet alternative with Cross Normalization
- [controlnetvideo GitHub](https://github.com/un1tz3r0/controlnetvideo) — SDXL ControlNet-Union with depth/canny/openpose/softedge/normal
- [LTX-2 ControlNet Workflow](https://www.runcomfy.com/comfyui-workflows/ltx-2-controlnet-in-comfyui-depth-controlled-video-workflow) — IC LoRA conditioning for LTX-2
- [LiON-LoRA ICCV 2025 Paper](https://openaccess.thecvf.com/content/ICCV2025/papers/Zhang_LiON-LoRA_Rethinking_LoRA_Fusion_to_Unify_Controllable_Spatial_and_Temporal_ICCV_2025_paper.pdf) — Linear scalability, orthogonality, norm consistency
- [LiON-LoRA ICCV HTML](https://openaccess.thecvf.com/content/ICCV2025/html/Zhang_LiON-LoRA_Rethinking_LoRA_Fusion_to_Unify_Controllable_Spatial_and_Temporal_ICCV_2025_paper.html) — Abstract and metadata
- [DimensionX GitHub](https://github.com/wenqsun/DimensionX) — ST-Director, 12+4 camera LoRAs, 3D/4D scenes
- [DimensionX arXiv](https://arxiv.org/html/2411.04928v1) — Decoupled spatial/temporal video diffusion
- [DimensionX ICCV 2025](https://openaccess.thecvf.com/content/ICCV2025/html/Sun_DimensionX_Create_Any_3D_and_4D_Scenes_from_a_Single_ICCV_2025_paper.html) — Conference proceedings
- [NimVideo CogVideoX LoRA](https://huggingface.co/NimVideo/cogvideox1.5-5b-prompt-camera-motion) — 6-direction prompt camera control
- [Time-to-Move GitHub](https://github.com/time-to-move/TTM) — Plug-and-play camera control, ICLR 2026
- [Neural4D Cinematic Prompts](https://blog.neural4d.com/text-to-video/cinematic-ai-video-prompts/) — Five pillars of cinematic prompting
- [Sora 2 Cinematic Guide](https://videoai.me/blog/sora-2-cinematic-video-creation) — Lens language, lighting setups, focal lengths
- [Seedance 2.0 Cinematic Guide](https://www.vidau.ai/seedance-2-0-the-best-guide-to-creating-cinematic-ai-video/) — Layered prompt structure, motion realism
- [Hailuo AI Anamorphic Guide](https://blog.hailuoai.video/knowledge/prompt-anamorphic-flares-film-looks) — Physics-first prompting for anamorphic effects
- [Hailuo AI Cinematic Guide](https://hailuoai.video/pages/knowledge/cinematic-ai-video-prompts-guide) — Iterative subtractive approach, I2V pipeline
- [Comfy.org Wan 2.2 Camera Control](https://comfy.org/workflows/video_wan2_2_14B_fun_camera-9dac2dae8bfc/) — WanCameraEmbedding workflow
- [Comfy.org Wan 2.2 Fun Control](https://comfy.org/workflows/video_wan2_2_14B_fun_control-67a816af8a73/) — Multi-modal control workflow
- [Comfy.org Wan 2.2 Day-0 Blog](https://blog.comfy.org/p/wan22-day-0-support-in-comfyui) — Native ComfyUI support, cinematic aesthetic
- [Comfy.org Wan 2.2 Fun Blog](https://blog.comfy.org/p/comfyui-wan22-fun-inp-support) — Fun Control + LightX2V LoRA
- [Comfy.org Seedance 2.0 R2V](https://comfy.org/workflows/api_seedance2_0_r2v-64f4db9e3e33/) — Reference-to-video cinematic workflow
- [Comfy.org Cinematic Annotate](https://comfy.org/workflows/0136284ecc19-0136284ecc19/) — Auto camera-path from image analysis
- [Comfy.icu Cinematography Prompt Builder](https://comfy.icu/node/ArchAi3D_Cinematography_Prompt_Builder) — Structured prompt node with DOF/mood/movement
- [Next Diffusion Wan 2.2 Tutorial](https://www.nextdiffusion.ai/tutorials/exploring-the-new-wan22-image-to-video-generation-model-in-comfyui) — FP8 setup guide
- [LinkedIn Wan 2.2 Camera LoRA](https://www.linkedin.com/posts/ognjen-toholj-5068829_generativeai-wan2-comfyui-activity-7398355192175443968-DadO) — Custom orbit LoRA for Wan 2.2 14B
