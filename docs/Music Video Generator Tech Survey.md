# Music Video Generator Technology Survey

**For:** Music-AI-Toolshop (Python 3.11 CLI) — new music-video module  
**Hardware baseline:** Intel i7-4770 (4C/8T), 16 GB DDR3, NVIDIA GT 640 2 GB (unusable for modern AI), Windows 10 64-bit  
**Survey date:** July 2026  
**Scope:** Open-source AI video synthesis, procedural/algorithmic visuals, hybrid compositing pipelines, and GPU upgrade paths

---

## Executive Summary

On the current machine, **full local AI text-to-video is not practical**. Modern open video models need at least ~8–14 GB VRAM for usable inference; the GT 640’s 2 GB Kepler silicon cannot run them, and CPU-only paths (ONNX/OpenVINO/quantized) for diffusion video are either nonexistent or unusably slow for a CLI product.

The practical path for Music-AI-Toolshop is a **hybrid architecture**:

1. **Local (today, zero GPU upgrade):** librosa beat/onset features → procedural shaders / MilkDrop-style visuals / Pillow+cairo lyric layers → FFmpeg compositing → optional stock footage montage.
2. **Cloud AI clips (today, pay-per-use):** Replicate / Modal / RunPod for short image-to-video or text-to-video B-roll (seconds, not full tracks).
3. **Local AI (after GPU upgrade):** LTX-Video (best consumer efficiency), AnimateDiff + Deforum (audio-reactive), CogVideoX-2B quantized, or HunyuanVideo 1.5 on ≥14–16 GB VRAM.

**Top practical picks under current constraints**

| Category | #1 | #2 | #3 |
|---|---|---|---|
| AI video (usable now) | [Replicate](https://replicate.com/pricing) (Python API, WAN i2v) | [Modal](https://modal.com/pricing) ($30/mo free credits) | [LTX-Video](https://github.com/Lightricks/LTX-Video) (best post-upgrade local) |
| Procedural visuals | [ModernGL](https://github.com/moderngl/moderngl) + GLSL | [projectM](https://github.com/projectM-visualizer/projectm) / [Butterchurn](https://github.com/jberg/butterchurn) | [py5](https://github.com/py5coding/py5) |
| Compositing / lyrics | FFmpeg + [ffmpeg-python](https://github.com/kkroening/ffmpeg-python) | [MoviePy](https://github.com/Zulko/moviepy) | [mugen](https://github.com/scherroman/mugen) / ASS karaoke |
| Full project to study | [mugen](https://github.com/scherroman/mugen) | [Lyriks](https://github.com/simon0302010/Lyriks) | [tammy](https://github.com/fresh-creations/tammy) |

---

## Hardware Reality Check

| Resource | Current | Implication for music video AI |
|---|---|---|
| GPU | GT 640, 2 GB, Kepler ~2012 | No CUDA compute capability for modern PyTorch video models; treat as **display-only** |
| RAM | 16 GB DDR3 | Tight for model weights + OS + browser; CPU offload of multi-GB models will thrash |
| CPU | i7-4770 Haswell | Fine for FFmpeg, librosa, procedural OpenGL, MoviePy; slow for any CPU diffusion |
| Storage | 112 GB SSD + HDDs | AI video weights alone are often 10–60+ GB — prefer HDD for weights, SSD for working cache |
| PSU (assumed) | 400–500 W OEM | Safe-ish for **RTX 4060 Ti 16GB (165 W TDP)** with PSU check; **RTX 3060 12GB needs ~550 W system**; **RTX 3090 350 W TGP is not feasible** without PSU + case upgrade |

**Bottom line:** Ship a great **local procedural + FFmpeg + cloud AI** module first. Treat local AI video as a Phase-2 optional backend behind a GPU gate.

---

## 1. AI Video Synthesis (Cloud + Local)

### 1.1 Text-to-Video / Image-to-Video Models

#### Stable Video Diffusion (SVD)

| Field | Detail |
|---|---|
| **Name / URL** | Stable Video Diffusion — [HF model card](https://huggingface.co/stabilityai/stable-video-diffusion-img2vid-xt), [Stability generative-models](https://github.com/Stability-AI/generative-models) |
| **License** | Stability AI community/commercial license (not pure MIT for weights); code repo often MIT |
| **Last update** | SVD family released late 2023; Stability generative-models still sees commits into 2025 (incl. SV4D lineage) |
| **Hardware** | Community/quantization guides: ~**8 GB FP16**, ~5 GB Q8, ~3.5 GB Q4 model footprint; real inference needs more for VAE/temporal cache. Official timings: ~100–180 s for a short clip on **A100 80 GB** |
| **Python** | Diffusers / Stability scripts; ComfyUI nodes widely available |
| **Music-video relevance** | **Image-to-video only** (no native text control on classic SVD). Good for animating album art / stills. No native audio conditioning |
| **Cloud vs local** | Cloud easy (Replicate etc.). Local needs **≥8–12 GB modern NVIDIA**. **Not runnable on GT 640 / CPU realistically** |
| **Maturity** | Production-used in hobby pipelines; superseded in quality by newer DiT video models but still a standard i2v building block |

#### AnimateDiff

| Field | Detail |
|---|---|
| **Name / URL** | [guoyww/AnimateDiff](https://github.com/guoyww/AnimateDiff) |
| **License** | Apache-2.0 |
| **Last update** | Official repo last major README activity ~**Jul 2024**; ecosystem (ComfyUI-AnimateDiff) remains active |
| **Hardware** | SD 1.5 motion modules ~1.5–1.7 GB; SDXL-Beta inference often **~13 GB VRAM** for 1024²×16 frames. Usable from ~6–12 GB with optimizations |
| **Python** | Native PyTorch; best UX via **ComfyUI** or A1111 |
| **Music-video relevance** | Excellent with **audio-reactive ComfyUI workflows** (frequency masks, BPM-driven strength). MotionLoRAs (zoom/pan/tilt/roll ~74 MB each) map well to camera moves on beats |
| **Cloud vs local** | Needs GPU upgrade for local; common on RunPod/Colab |
| **Maturity** | Mature community standard for short SD animations; not SOTA photoreal video |

#### CogVideoX

| Field | Detail |
|---|---|
| **Name / URL** | [THUDM/CogVideo](https://github.com/THUDM/CogVideo) (zai-org/CogVideo) |
| **License** | Code + CogVideoX-2B: **Apache-2.0**; CogVideoX-5B: separate CogVideoX LICENSE |
| **Last update** | Active through 2025 (LoRA/diffusers updates into early 2025+) |
| **Hardware** | Official table (highly relevant): **CogVideoX-2B** diffusers FP16 from **~4 GB***, INT8 from **~3.6 GB***; **5B** from **~5 GB*** / INT8 **~4.4 GB*** with memory tricks. SAT full precision is much higher (18–76 GB). ~5 s video can take **~550–1000 s** on H100/A100 |
| **Python** | Diffusers + SAT; Python 3.10–3.12 |
| **Music-video relevance** | Strong T2V + I2V; no native audio-reactive path — sync externally |
| **Cloud vs local** | Quantized 2B is the most plausible “consumer GPU” open T2V; still **not** for GT 640 / pure CPU |
| **Maturity** | Production-grade open release; commercial API variants exist (QingYing) |

\*Minimums assume aggressive offload/tiling; expect higher VRAM in practice.

#### Open-Sora

| Field | Detail |
|---|---|
| **Name / URL** | [hpcaitech/Open-Sora](https://github.com/hpcaitech/Open-Sora) |
| **License** | Apache-2.0 |
| **Last update** | Active (v1.3 Feb 2025; v2.0 Mar 2025; README commits into 2026) |
| **Hardware** | Research-oriented; peak memory tables often on H100-class. Supports offload; multi-second clips at 144p–720p historically |
| **Python** | PyTorch training/inference stack |
| **Music-video relevance** | General T2V/I2V research platform; not audio-native |
| **Cloud vs local** | Cloud/multi-GPU realistic; poor fit for 16 GB dual-channel Haswell desktop without heavy compromise |
| **Maturity** | Active research codebase; version fragmentation (v1.x branches vs main) |

#### LTX-Video (Lightricks) — strongest local-efficiency candidate

| Field | Detail |
|---|---|
| **Name / URL** | [Lightricks/LTX-Video](https://github.com/Lightricks/LTX-Video), [HF LTX-Video](https://huggingface.co/Lightricks/LTX-Video) |
| **License** | OpenRail-M (commercial-capable terms for newer checkpoints) |
| **Last update** | Very active through **2025** (v0.9.x series; README fixes May 2025) |
| **Hardware** | Marketed real-time on H100 at **1216×704 @ 30 FPS**. Community **LTX-VideoQ8**: **720×480×121 in under a minute on RTX 4060 8 GB**. Distilled LoRA path claims **~1 GB** adapter VRAM in specific configs; full quality models need more |
| **Python** | `inference.py` + YAML configs; first-class **ComfyUI** workflows |
| **Music-video relevance** | Fast iteration for short clips; good i2v for still→motion B-roll. Pair with external beat cutting |
| **Cloud vs local** | Best “after upgrade” local model for constrained consumer GPUs; also hostable on Modal/RunPod |
| **Maturity** | Rapidly maturing productized open model; strong ComfyUI ecosystem |

#### HunyuanVideo / HunyuanVideo 1.5

| Field | Detail |
|---|---|
| **Name / URL** | [Tencent-Hunyuan/HunyuanVideo](https://github.com/Tencent-Hunyuan/HunyuanVideo) |
| **License** | Apache-2.0 (commonly reported for the open release; confirm LICENSE.txt in repo) |
| **Last update** | Repo activity into **2026**; **1.5** consumer-focused release reported **1 Dec 2025** |
| **Hardware** | Guides claim **~14 GB VRAM minimum** for 1.5 (8.3B params); RTX 4070 Ti 16 GB ~15–20 min for 5 s @ moderate settings; RTX 4090 ~8–12 min @ 720p. Weights **>30 GB** disk. CUDA 12.1+, Python ≥3.10. Windows: WSL2 recommended |
| **Python** | `sample_video.py`, Gradio, ComfyUI community support |
| **Music-video relevance** | High visual quality T2V; **no native audio**; post-sync required |
| **Cloud vs local** | Local only after **≥14–16 GB** GPU + large disk; otherwise cloud |
| **Maturity** | Leading open quality tier in late 2025; heavy |

#### Mochi-1 (Genmo)

| Field | Detail |
|---|---|
| **Name / URL** | [genmoai/mochi](https://github.com/genmoai/mochi) |
| **License** | Apache-2.0 |
| **Last update** | Preview era late 2024; ComfyUI consumer path noted Nov 2024 |
| **Hardware** | Official single-GPU ~**60 GB**; ComfyUI path “**<20 GB**”; recommends **H100**. `cpu_offload=True` exists but is not a 16 GB desktop solution |
| **Python** | Composable Python API (`MochiSingleGPUPipeline`) |
| **Music-video relevance** | Strong motion quality; short clips (~31 frames examples); no audio-native |
| **Cloud vs local** | Cloud/H100 class; not for current PC |
| **Maturity** | High-quality open release; hardware-hungry |

#### ModelScope Text-to-Video

| Field | Detail |
|---|---|
| **Name / URL** | [modelscope/modelscope](https://github.com/modelscope/modelscope) + Damou T2V lineage |
| **License** | Apache-2.0 (framework); model cards vary |
| **Last update** | Framework maintained; classic T2V models are older generation vs 2025 DiTs |
| **Hardware** | Older T2V often targeted multi-GB GPU; not competitive with LTX/CogVideoX today |
| **Python** | ModelScope pipelines |
| **Music-video relevance** | Historical reference; prefer newer models |
| **Cloud vs local** | HF/ModelScope hubs |
| **Maturity** | Stable but largely superseded |

#### Ovi (open video+audio generation)

| Field | Detail |
|---|---|
| **Name / URL** | [Ovi project](https://aaxwaz.github.io/Ovi/), ComfyUI ports circulating |
| **License** | Check project page/repo at use time (emerging 2025) |
| **Last update** | Public demos/tutorials from late 2025 |
| **Hardware** | Modern GPU required (treat like other DiT video stacks) |
| **Python** | ComfyUI-centric workflows |
| **Music-video relevance** | Generates **video with sound** (dialogue/SFX/ambience) — interesting, but **not the same as syncing to an existing track** |
| **Cloud vs local** | GPU/cloud |
| **Maturity** | Emerging; watch carefully before depending on it |

### 1.2 Image-to-Video & Frame Interpolation

| Name | URL | License | Update | Hardware | Python | MV relevance | Local on your HW? | Maturity |
|---|---|---|---|---|---|---|---|---|
| **RIFE** | [Practical-RIFE](https://github.com/hzwer/Practical-RIFE) | MIT-family (check repo) | Actively used community standard | GPU preferred; lighter than generative T2V; CPU possible but slow | PyTorch CLI | Smooth slow-mo between keyframes / beat holds | **Maybe CPU** for offline; GPU better | Mature |
| **FILM** | [google-research/frame-interpolation](https://github.com/google-research/frame-interpolation) | Apache-2.0 | Research release | GPU-oriented TF/JAX stack | Python research code | High-quality frame interp | Poor on CPU-only | Mature research |
| **AMT** | [MCG-NKU/AMT](https://github.com/MCG-NKU/AMT) | Check repo | Research | GPU | PyTorch | All-in-one multi-frame interp | Needs GPU | Research/usable |
| **SVD / LTX i2v** | see above | — | — | ≥8 GB VRAM class | Diffusers/Comfy | Animate still album art | Needs upgrade/cloud | Production hobby |

**Practical pattern:** Generate sparse keyframes (stock, procedural, or cloud AI) → interpolate with RIFE → cut on beats with FFmpeg.

### 1.3 Audio-Reactive AI Video

There is **no widely adopted open model** that cleanly does `audio_file + text → full music video` at SOTA quality end-to-end in 2026. What exists:

| Approach | How it works | Fit |
|---|---|---|
| **Deforum + audio** | [sd-webui-deforum](https://github.com/deforum-art/sd-webui-deforum) (AGPL-3.0) drives camera/prompt strength from audio; 3D mode peaks ~**6.4 GB** VRAM, `--lowvram` ~**3.8 GB** | Best classic local audio-reactive SD path **if** you have a mid GPU |
| **ComfyUI + AnimateDiff + audio nodes** | SaltAI-style audio → masks/strength from FFT/BPM | Best modular hobby pipeline |
| **Tammy** | [fresh-creations/tammy](https://github.com/fresh-creations/tammy) — BPM/instrument-steered prompt transitions (Spleeter + SD/VQGAN) | Study/fork; small project (MIT, ~14★) |
| **music2video** | [joeljang/music2video](https://github.com/joeljang/music2video) — Wav2CLIP + VQGAN-CLIP | Older aesthetic; MIT; GPU |
| **External sync** | librosa features → cut cloud AI clips on onsets | **Recommended for your CLI** |

### 1.4 Cloud API Options (Python CLI friendly)

#### Replicate

| Field | Detail |
|---|---|
| **URL** | [Pricing](https://replicate.com/pricing), [Python client](https://replicate.com/docs/get-started/python) |
| **License** | Platform ToS; models have own licenses |
| **Python** | `pip install replicate` + `REPLICATE_API_TOKEN` — ideal thin adapter |
| **Free tier** | **No meaningful free tier stated** on pricing page; pure usage billing |
| **Video pricing examples** | WAN 2.1 i2v **$0.09/s @ 480p**, **$0.25/s @ 720p** (as listed) |
| **Hardware rental** | T4 **$0.81/hr**, L40S **$3.51/hr**, A100 80GB **$5.04/hr**, H100 **$5.49/hr** |
| **MV relevance** | Best “call a model by name from argparse” experience |
| **Maturity** | Production SaaS |

#### Modal

| Field | Detail |
|---|---|
| **URL** | [Pricing](https://modal.com/pricing) |
| **Python** | First-class Python SDK; deploy functions with GPU decorators |
| **Free tier** | **Starter: $0 base + $30/month free credits**, 3 seats, 10 GPU concurrency |
| **GPU rates (examples)** | T4 **$0.000164/s**, L4 **$0.000222/s**, A10 **$0.000306/s**, A100 40GB **$0.000583/s**, H100 **$0.001097/s** |
| **MV relevance** | Best for **custom** pipelines (your own LTX/CogVideo container) orchestrated from CLI |
| **Maturity** | Production serverless |

#### RunPod

| Field | Detail |
|---|---|
| **URL** | [runpod.io/pricing](https://www.runpod.io/pricing) |
| **Python** | REST + community SDKs; good for long pods / ComfyUI templates |
| **Free tier** | **No standing free tier**; occasional signup credits (~$10 reported by third parties); startup grants exist |
| **Pricing shape** | Community pods often **~$0.27–0.40/hr** class for mid/high consumer GPUs (varies) |
| **MV relevance** | Cheap ComfyUI box for batch jobs |
| **Maturity** | Production GPU cloud |

#### Hugging Face Inference Providers

| Field | Detail |
|---|---|
| **URL** | [Rate limits / billing](https://huggingface.co/docs/api-inference/en/rate-limits) |
| **Python** | `huggingface_hub.InferenceClient` |
| **Free tier** | Free users **~$0.10/month** credits (subject to change); PRO **$2/month** |
| **Note** | As of mid-2025, `hf-inference` leans CPU for small tasks; heavy video usually routes to paid providers |
| **MV relevance** | Light experiments only on free credits |
| **Maturity** | Production, but free quota is tiny for video |

#### Google Colab

| Field | Detail |
|---|---|
| **URL** | [Colab plans](https://colab.research.google.com/signup) |
| **Python** | Notebooks; awkward as a headless CLI backend (drive mounts, session limits) |
| **Free tier** | Free GPU intermittently (T4-class), strict caps/queues |
| **MV relevance** | Prototyping only, not productized CLI dependency |
| **Maturity** | Mature but unreliable free tier |

### 1.5 Local CPU Feasibility (ONNX / OpenVINO / Quantization)

| Workload | CPU-only on i7-4770 + 16 GB? | Notes |
|---|---|---|
| Full T2V diffusion (SVD, CogVideoX, LTX, Hunyuan, Mochi) | **No** | Even quantized weights exceed practical RAM/time; no llama.cpp-class video runtime that makes this product-viable |
| AnimateDiff / SD video | **No** for real songs | Minutes-to-hours per second of video if it runs at all |
| RIFE / simple interp | **Barely** | Possible offline at low res |
| Wav2Lip | **Slow but possible** | Older GAN; quality/dataset caveats |
| Procedural GLSL / FFmpeg / librosa | **Yes — primary path** | This is where your hardware wins |

**Conclusion:** Do not plan ONNX-CPU AI video as a product feature. Plan **cloud adapters + local procedural**.

---

## 2. Procedural / Algorithmic Visual Synthesis

### 2.1 Audio-Reactive Graphics Frameworks

#### projectM (MilkDrop-compatible)

| Field | Detail |
|---|---|
| **Name / URL** | [projectM-visualizer/projectm](https://github.com/projectM-visualizer/projectm) |
| **License** | **LGPL-2.1** |
| **Last update** | libprojectM **4.1.4** (Jan 2025); under active development |
| **Hardware** | OpenGL; runs on modest GPUs including older ones for classic presets |
| **Python** | C++ lib; bindings/frontends vary — orchestrate via subprocess/CLI frontend or custom binding |
| **MV relevance** | **Native beat detection + FFT → presets**. Ideal music visualizer DNA |
| **Cloud vs local** | Local |
| **Maturity** | Mature library; some end-user frontends lag |

#### Butterchurn

| Field | Detail |
|---|---|
| **Name / URL** | [jberg/butterchurn](https://github.com/jberg/butterchurn) (~1.7k★) |
| **License** | **MIT** |
| **Last update** | Established WebGL2 port; ecosystem integrations (Webamp, etc.) |
| **Hardware** | WebGL2 GPU (even weak discrete/iGPU often OK for 720p) |
| **Python** | JS/WebAudio — drive via headless Chromium/Playwright capture, or use as design reference |
| **MV relevance** | MilkDrop presets in browser; great look, extra glue for offline MP4 |
| **Local** | Yes on your HW for visualization; capture pipeline needed |
| **Maturity** | Mature |

#### py5 (Processing for Python)

| Field | Detail |
|---|---|
| **Name / URL** | [py5coding/py5](https://github.com/py5coding/py5) |
| **License** | **LGPL-2.1** |
| **Hardware** | CPU/GPU via Processing/Java stack |
| **Python** | **Native Python API** — excellent CLI fit |
| **MV relevance** | Code-driven motion graphics; feed librosa arrays as parameters |
| **Local** | Yes |
| **Maturity** | Actively maintained Processing successor for Python |

#### TouchDesigner

| Field | Detail |
|---|---|
| **Name / URL** | [Derivative docs — Python](https://docs.derivative.ca/Python) |
| **License** | Proprietary; free Non-Commercial |
| **Python** | Embedded **Python 3.11** (`td` module), OSC I/O |
| **MV relevance** | Industry VJ tool; audio CHOPs, TOPs, movie out |
| **Local** | Yes, but not a pure open-source dependency; hard to ship inside Toolshop |
| **Maturity** | Production |

#### Hydra

| Field | Detail |
|---|---|
| **Name / URL** | [ojack/hydra](https://github.com/ojack/hydra) |
| **License** | Check repo (live-coding visuals) |
| **Python** | Browser JS; audio via Meyda FFT (`a.fft[i]`) |
| **MV relevance** | Beautiful live shaders; capture via browser |
| **Local** | Yes (Chrome + WebGL) |
| **Maturity** | Popular experimental livecoding tool |

#### openFrameworks / Cinder / vvvv / Kodelife

| Tool | Python from CLI? | Notes |
|---|---|---|
| openFrameworks | Weak (C++); OSC possible | Heavy C++ creative coding |
| Cinder | C++ | Same |
| vvvv | .NET/visual; free gamma options vary | Windows-friendly VJ, not pythonic |
| Kodelife | Shader IDE | Great for authoring GLSL, not batch CLI |

**Recommendation:** Prefer **py5 + ModernGL shaders + projectM** over shipping TouchDesigner/Resolume as hard deps. Optionally support OSC out to Resolume for power users.

### 2.2 Shader-Based Visualization (Headless on Windows)

#### ModernGL

| Field | Detail |
|---|---|
| **Name / URL** | [moderngl/moderngl](https://github.com/moderngl/moderngl) |
| **License** | MIT |
| **Python** | Native; render to FBO → numpy → imageio/FFmpeg |
| **Headless Windows** | Use OSMesa/EGL where available, or hidden window + `moderngl-window`; GT 640 can still run simple fragment shaders |
| **MV relevance** | Map RMS/onset/band energy uniforms → GLSL |
| **Maturity** | Mature |

#### VisPy

| Field | Detail |
|---|---|
| **Name / URL** | [vispy/vispy](https://github.com/vispy/vispy) |
| **License** | BSD-style |
| **Python** | High-level OpenGL |
| **MV relevance** | Scientific/gl visuals; audio spectrum meshes common in demos |
| **Maturity** | Mature core; some APIs still evolving |

**Headless capture recipe (Windows):**
1. Render N frames offscreen (ModernGL FBO) at 1280×720.
2. Pipe raw RGB frames to `ffmpeg -f rawvideo -pix_fmt rgb24 ...`.
3. Mux with source wav/mp3.

Even the GT 640 can do simple raymarched/plasma/spectrum shaders at 30–60 FPS offline; complexity is the limit, not “AI VRAM.”

### 2.3 Generative Art Libraries (Python)

| Library | License | Role | Runs on your HW? |
|---|---|---|---|
| **Pillow** | HPND | Text, overlays, Ken Burns stills | Yes |
| **pycairo** | LGPL/MPL | Vector typography, shapes | Yes |
| **matplotlib.animation** | PSF | Debug plots / simple viz | Yes (slow) |
| **MoviePy** | MIT | Timeline editing, text clips | Yes |
| **vidgear** | Apache-2.0 | High-perf capture/stream pipelines | Yes |
| **OpenCV** | Apache-2.0 | Optical flow, blends, particles | Yes |
| **Skia** | BSD-3 | High-quality 2D (Python bindings less turnkey) | Possible |
| **Manim Community** | MIT | Motion graphics / kinetic type | Yes (CPU OK for lyrics) |

### 2.4 VJ Software & OBS

| Tool | Control from Python CLI | Notes |
|---|---|---|
| **Resolume** | OSC / REST (Arena) | Pro VJ; paid; great live, overkill to ship |
| **OBS Studio + obs-websocket** | [obs-websocket](https://github.com/obsproject/obs-websocket) (GPL-2.0) + [obs-websocket-py](https://github.com/Elektordi/obs-websocket-py) | Scene switch, record, sources — good for “press record on a composed scene” |
| **Magic Music Visualizer** | Limited scripting | Consumer visualizer |
| **Veejay** | Linux-oriented | Less ideal on Win10 |

**OBS pattern:** Toolshop renders layer clips → OBS scene collection → `obs-websocket-py` starts recording → stop → take file. Useful but optional; pure FFmpeg is more automatable/headless.

---

## 3. Hybrid Pipeline & Compositing

### 3.1 Video Compositing in Python

#### FFmpeg (+ ffmpeg-python / subprocess)

| Field | Detail |
|---|---|
| **Name / URL** | FFmpeg; [kkroening/ffmpeg-python](https://github.com/kkroening/ffmpeg-python) (Apache-2.0; maintenance slower — many teams shell out) |
| **Hardware** | CPU encode fine on i7-4770 (x264); optional NVENC N/A on GT 640 |
| **MV relevance** | **Primary compositor**: concat, xfade, overlay, ass, zoompan, loudnorm |
| **Maturity** | Industry standard |

#### MoviePy

| Field | Detail |
|---|---|
| **Name / URL** | [Zulko/moviepy](https://github.com/Zulko/moviepy) |
| **License** | MIT |
| **Python** | Native timeline API |
| **MV relevance** | Fast prototyping of layer stacks, text, audio set |
| **Caveat** | Slower/heavier than raw FFmpeg for long 1080p jobs |
| **Maturity** | Very widely used; v2 modernization ongoing in ecosystem |

#### vidgear

| Field | Detail |
|---|---|
| **Name / URL** | [abhiTronix/vidgear](https://github.com/abhiTronix/vidgear) |
| **License** | Apache-2.0 |
| **Python** | WriteGear/NetGear/StreamGear |
| **MV relevance** | Robust writer/stabilizer pipelines; less “creative edit” than MoviePy |
| **Maturity** | Actively maintained |

#### OpenCV / PyAV

| Library | URL | Role |
|---|---|---|
| opencv-python | opencv.org | Frame-level FX, optical flow, histogram beats |
| PyAV | [PyAV-Org/PyAV](https://github.com/PyAV-Org/PyAV) | Pythonic libav bindings; precise packet/frame control |

### 3.2 Audio Features → Visual Parameters (librosa already in Toolshop)

Suggested mapping table for the adapter module:

| Feature (librosa) | Visual parameter |
|---|---|
| `beat_track` / `tempo` | Cut points, strobe period, camera cut rate |
| `onset_detect` / `onset_strength` | Flash opacity, glitch intensity, hard cuts |
| `rms` / `stft` band energy | Shader uniforms, zoom depth, particle birth rate |
| `chroma` / key (you already detect) | Color palette hue rotates by pitch class |
| `spectral_centroid` | Brightness / high-pass visual noise |
| Stem RMS (Demucs you already have) | Per-stem layers (kick→flash, vocal→lyric emphasis, other→bg motion) |
| Sections (novelty / agglomerative) | Scene changes / prompt changes |

Export a sidecar JSON:

```json
{
  "tempo": 128.0,
  "beats": [0.52, 0.98, 1.45],
  "onsets": [0.12, 0.55],
  "sections": [{"start": 0.0, "end": 15.2, "label": "verse"}],
  "rms_env": {"hop_s": 0.02, "values": [0.1, 0.2]}
}
```

### 3.3 Lyric Video Generation

| Project | URL | License | Notes |
|---|---|---|---|
| **Lyriks** | [simon0302010/Lyriks](https://github.com/simon0302010/Lyriks) | GPL-3.0 | Whisper + Demucs + pysubs2/FFmpeg; Python 3.11; updated 2025; **closest modern CLI lyric tool** |
| **Karaoke-Music-Vid-Generator** | [danielrosehill/...](https://github.com/danielrosehill/Karaoke-Music-Vid-Generator) | n/s | ASS `\kf` karaoke, Ken Burns, waveform; uses OpenAI API |
| **karaoke-generator** | [nomadkaraoke/karaoke-generator](https://github.com/nomadkaraoke/karaoke-generator) | n/s | Archived Jul 2025 → successor karaoke-gen |
| **Manim** | [ManimCommunity/manim](https://github.com/ManimCommunity/manim) | MIT | Kinetic typography |
| **ASS + FFmpeg** | libass | — | Production karaoke highlighting without heavy deps |

**Recommended Toolshop path:**  
Your lyrics intelligence (timestamps if available) → generate **ASS** → `ffmpeg -vf ass=lyrics.ass` over procedural/stock background. Avoid GPL contamination if Toolshop is non-GPL: reimplement ASS writer (format is documented) rather than depending on GPL Lyriks code.

### 3.4 Stock Footage / Image APIs

| API | URL | Auth | Notes |
|---|---|---|---|
| **Pexels** | [pexels.com/api](https://www.pexels.com/api/) | Free API key | Photos + **videos**; attribution guidelines |
| **Pixabay** | [pixabay.com/api/docs](https://pixabay.com/api/docs/) | Free API key | Images + videos; Content License |
| **Unsplash** | [unsplash.com/documentation](https://unsplash.com/documentation) | Free API key | **Images only** (great for Ken Burns) |

CLI pattern: search by theme tags from your BERTopic themes → download → beat-aligned montage via **mugen**-style sampling.

### 3.5 FFmpeg Filter Chains for Beat-Synced Music Videos

**Beat hard-cuts (pre-split clips at beat timestamps, then):**
```bash
ffmpeg -f concat -safe 0 -i beats.txt -i song.wav -c:v libx264 -crf 18 -c:a aac -shortest out.mp4
```

**Crossfade between two clips:**
```bash
ffmpeg -i a.mp4 -i b.mp4 -filter_complex "[0:v][1:v]xfade=transition=fade:duration=0.25:offset=3.75" out.mp4
```

**Audio-reactive zoom (static image Ken Burns driven by envelope — approximate with zoompan):**
```bash
ffmpeg -loop 1 -i cover.jpg -i song.wav \
  -vf "zoompan=z='min(zoom+0.0015,1.5)':d=125:s=1280x720:fps=25" \
  -c:v libx264 -tune stillimage -c:a aac -shortest out.mp4
```

**Lyric burn-in:**
```bash
ffmpeg -i base.mp4 -vf "ass=lyrics.ass" -c:a copy out.mp4
```

**Overlay spectrum / waveform (pre-rendered transparent WebM/PNG sequence):**
```bash
ffmpeg -i base.mp4 -i overlay.mov -filter_complex "overlay=0:0:format=auto" -c:a copy out.mp4
```

**EQ-style visual using `showfreqs` / `showwaves` (quick procedural):**
```bash
ffmpeg -i song.wav -filter_complex "[0:a]showwaves=s=1280x720:mode=cline:rate=25,format=yuv420p[v]" -map "[v]" -map 0:a out.mp4
```

---

## 4. GPU Upgrade Path

### 4.1 Minimum GPU for “reasonable” local AI video

| Goal | Minimum realistic GPU | Why |
|---|---|---|
| Deforum / SD 1.5 AnimateDiff hobby | **8 GB** (RTX 3060 8GB / 4060 8GB) | lowvram paths exist |
| SVD / LTX consumer clips | **8–12 GB** | LTX-Q8 shown on 4060 8GB; SVD ~8GB FP16 class |
| Comfortable AnimateDiff SDXL / Hunyuan 1.5 | **14–16 GB** | Hunyuan 1.5 guides cite **14 GB min** |
| Comfortable multi-model ComfyUI | **16–24 GB** | room for VAE + ControlNet + video model |

**“10+ FPS generation”** for diffusion video is **not** like game FPS. Even LTX “real-time” claims are H100-class at full HD. On consumer cards, think **seconds-to-minutes per short clip**, not interactive 10 FPS denoising — except highly distilled/quantized LTX paths.

### 4.2 Value comparison (2025–2026)

| GPU | VRAM | TDP / power notes | AI video fit | PSU vs your ~400–500 W OEM |
|---|---|---|---|---|
| **RTX 3060 12GB** | 12 GB | **~170 W** TDP; Nvidia often cites **550 W** system PSU | Sweet used-market VRAM/$ for SD/AnimateDiff/LTX | **Borderline** — plan **PSU upgrade to 550–650 W** |
| **RTX 4060 Ti 16GB** | 16 GB | **~165 W** TDP; often **~550–650 W** system rec. | **Best upgrade for your case**: 16 GB + low power + Ada efficiency | **Most feasible** if PSU is healthy 500 W+ quality unit; still verify rails/connectors |
| **Used RTX 3090 24GB** | 24 GB | **~350 W** TGP; system often **750–850 W+** | Best VRAM for heavy models | **Not feasible** on 400–500 W OEM without full PSU + cooling + PCIe power cables |

### 4.3 Will the i7-4770 bottleneck a modern GPU?

- **For diffusion inference:** Usually **GPU-bound**. PCIe 3.0 x16 has enough bandwidth for typical UNet/DiT inference; Haswell will not erase an RTX 4060 Ti’s value.
- **For data loading / video encode / many small jobs:** CPU and **dual-channel DDR3-1600** can show up as overhead.
- **For training / fine-tunes:** CPU/RAM age hurts more; stick to inference + LoRA on cloud if needed.

### 4.4 Power supply guidance

| Upgrade | Feasible on 400–500 W OEM? |
|---|---|
| RTX 4060 Ti 16GB (165 W) | **Maybe**, if PSU is quality 80+ and has required PCIe power cable; prefer measuring/upgrading to **650 W 80+ Bronze/Gold** |
| RTX 3060 12GB (170 W) | Treat **550 W as minimum system**, 650 W happier |
| RTX 3090 (350 W) | **No** without **≥750–850 W** quality PSU and case airflow |

Also check: PCIe power connectors (6/8-pin), physical card length vs case, and that the GT 640’s slot is PCIe x16 electrically.

---

## 5. Existing Open-Source Music Video Generators (Study / Fork)

| Project | URL | License | Stars (approx) | Status | Why it matters |
|---|---|---|---|---|---|
| **mugen** | [scherroman/mugen](https://github.com/scherroman/mugen) | MIT | ~236 | v1.0.0 (2023) | **Closest architectural cousin**: CLI + librosa + moviepy beat montage from source videos |
| **Lyriks** | [simon0302010/Lyriks](https://github.com/simon0302010/Lyriks) | GPL-3.0 | small | Active 2025 | Lyric/karaoke CLI; Demucs+Whisper+FFmpeg — mirrors your stems/lyrics stack |
| **tammy** | [fresh-creations/tammy](https://github.com/fresh-creations/tammy) | MIT | ~14 | Niche | Full generative MV pipeline with BPM/instrument steering |
| **music2video** | [joeljang/music2video](https://github.com/joeljang/music2video) | MIT | ~236 | Older | Audio-text fused CLIP video; paper-backed |
| **Karaoke-Music-Vid-Generator** | [danielrosehill/...](https://github.com/danielrosehill/Karaoke-Music-Vid-Generator) | n/s | tiny | 2025 | ASS karaoke + waveform + Ken Burns template |
| **karaoke-generator** | [nomadkaraoke/karaoke-generator](https://github.com/nomadkaraoke/karaoke-generator) | n/s | ~52 | **Archived** 2025 | Pipeline ideas; successor karaoke-gen |
| **Deforum** | [deforum-art/sd-webui-deforum](https://github.com/deforum-art/sd-webui-deforum) | AGPL-3.0 | large ecosystem | 2024 releases | Audio-reactive SD animation reference |
| **ComfyUI** | [comfyanonymous/ComfyUI](https://github.com/comfyanonymous/ComfyUI) | GPL-3.0 | very large | Very active | Workflow host for LTX/AnimateDiff — optional external backend, license caution |

---

## 6. Recommended Architecture (Hybrid)

Text diagram for Music-AI-Toolshop:

```
                        Music-AI-Toolshop CLI (argparse)
                                   |
         +-------------------------+--------------------------+
         |                         |                          |
         v                         v                          v
 [audio_features]           [lyrics_intel]              [theme/NER]
  librosa beats              timestamps/ASS              BERTopic tags
  onsets, RMS, bands         rhyme/flow hooks            stock queries
  Demucs stem energies              |                          |
         |                          |                          |
         +-------------+------------+------------+-------------+
                       |                         |
                       v                         v
            +--------------------+     +----------------------+
            | visual_backends    |     | ai_clip_backends     |
            | (local, always-on) |     | (optional/cloud/GPU) |
            +--------------------+     +----------------------+
            | moderngl shaders   |     | replicate.Client     |
            | py5 sketches       |     | modal.Function       |
            | projectM capture   |     | runpod job           |
            | pillow/cairo text  |     | local_comfy (future) |
            | ffmpeg showwaves   |     | LTX / AnimateDiff    |
            +---------+----------+     +----------+-----------+
                      |                           |
                      v                           v
                 layer clips/          short AI B-roll clips
                 png sequences              (2–5s each)
                      |                           |
                      +-------------+-------------+
                                    v
                         [compose_adapter]
                    moviepy preview OR ffmpeg graph
                    - beat concat / xfade
                    - overlay lyrics ASS
                    - mix stems/master audio
                    - color grade / loudnorm
                                    |
                                    v
                              music_video.mp4
                                    |
                         pytest w/ mocked backends
```

### Suggested module layout (matches Toolshop pattern)

```
music_video/
  adapters/
    features.py          # thin wrap over existing librosa/Demucs
    stock_pexels.py
    stock_pixabay.py
    replicate_video.py
    modal_video.py
    shader_render.py     # ModernGL
    lyrics_ass.py
    ffmpeg_compose.py
  cli.py                 # argparse subcommands
  pipeline.py            # orchestration only
  tests/
    test_features_map.py
    test_ass_writer.py
    test_ffmpeg_graph.py
    test_replicate_adapter.py  # mocked HTTP
```

### Phased delivery

| Phase | Deliverable | Hardware |
|---|---|---|
| **P0** | Beat-synced FFmpeg montage from stock + `showwaves` + ASS lyrics | Current PC |
| **P1** | ModernGL/py5 audio-reactive backgrounds; theme→Pexels search | Current PC |
| **P2** | Replicate/Modal adapters for 2–4 s AI B-roll inserts on section changes | Current PC + API $ |
| **P3** | Optional local Comfy/LTX backend behind `--device cuda` | After 4060 Ti 16GB (or similar) |

---

## 7. Top 3 Recommendations by Category

### AI Video Synthesis
1. **Modal ($30 free credits) + custom LTX/WAN jobs** — best control and monthly free compute for experiments ([Modal pricing](https://modal.com/pricing)).
2. **Replicate Python client** — fastest path to ship `toolshop video ai-clip` with WAN/SVD-class models ([Replicate](https://replicate.com/docs/get-started/python)).
3. **LTX-Video (post-upgrade)** — best open local efficiency story on 8–16 GB cards ([LTX-Video](https://github.com/Lightricks/LTX-Video)).

### Procedural Visuals
1. **ModernGL + GLSL uniforms from librosa** — pure Python, headless-ish, works on weak GPU.
2. **projectM / Butterchurn aesthetics** — proven music-visual language ([projectM](https://github.com/projectM-visualizer/projectm), [Butterchurn](https://github.com/jberg/butterchurn)).
3. **py5** — rapid Processing-style motion graphics in Python ([py5](https://github.com/py5coding/py5)).

### Hybrid Compositing
1. **FFmpeg as system of record** (invoke via subprocess; optional ffmpeg-python).
2. **MoviePy for tests/prototypes** ([moviepy](https://github.com/Zulko/moviepy)).
3. **mugen concepts** for source-video beat montage ([mugen](https://github.com/scherroman/mugen)).

### Lyrics
1. **ASS generator + libass/FFmpeg** (license-clean, CPU-cheap).
2. **Manim** for premium kinetic type segments.
3. Study **Lyriks** workflows; avoid GPL copy-paste if Toolshop license differs.

### GPU Upgrade
1. **RTX 4060 Ti 16GB** — best balance of VRAM, power, Ada efficiency for your PSU era.
2. **Used RTX 3060 12GB** — budget VRAM if paired with **650 W PSU**.
3. **Skip 3090** until PSU/case rebuild; use cloud 24 GB instead.

---

## 8. Decision Matrix vs Your Constraints

| Capability | On current HW | With 4060 Ti 16GB | Cloud only |
|---|---|---|---|
| Full-song AI T2V | No | Partial (slow, short clips stitched) | Yes ($$) |
| Audio-reactive shaders | **Yes** | Yes | N/A |
| Lyric videos | **Yes** | Yes | Optional Whisper cloud |
| Stock beat montage | **Yes** | Yes | N/A |
| AnimateDiff music clips | No | **Yes** | Yes |
| Hunyuan-quality clips | No | Stretch/slow | Yes |
| Productized CLI UX | **Yes (hybrid)** | Yes | Yes |

---

## 9. License Watchouts for Toolshop Integration

| Dependency | License | Integration note |
|---|---|---|
| AnimateDiff, Open-Sora, Mochi, CogVideoX-2B code | Apache-2.0 | Generally CLI-friendly |
| Deforum, ComfyUI, Lyriks | **AGPL/GPL** | Keep as **optional external tools**, not linked libraries, if you need permissive licensing |
| projectM, py5 | LGPL-2.1 | Dynamic linking / subprocess usually OK; read obligations |
| SVD / LTX weights | Stability / OpenRail-M style | Follow model Acceptable Use + commercial terms |
| MoviePy, mugen, butterchurn, ffmpeg-python | MIT/Apache | Safe defaults |
| FFmpeg | LGPL/GPL build-dependent | Prefer LGPL builds; avoid enabling GPL-only libs if shipping binaries |

---

## 10. Concrete “Start This Week” Stack

```text
pip install moviepy opencv-python-headless moderngl pillow pycairo \
            ffmpeg-python httpx replicate  # + your existing librosa/demucs
# system: ffmpeg with libass, libx264
```

**MVP command sketch:**
```bash
toolshop video generate \
  --audio track.wav \
  --lyrics track.lrc \
  --style procedural:neon_grid \
  --stock-query "cyberpunk city night" \
  --ai-broll replicate:wan-i2v-480p \
  --cuts beats \
  --out out/mv.mp4
```

Where:
- `--style procedural:*` always works offline.
- `--stock-query` uses Pexels/Pixabay keys.
- `--ai-broll` no-ops with a warning if no API key / budget.
- `--device cuda` later enables local LTX.

---

## Sources (selected primary references)

Inline citations throughout are drawn from primary project pages and docs, including:

- [Stable Video Diffusion model card](https://huggingface.co/stabilityai/stable-video-diffusion-img2vid-xt)
- [AnimateDiff](https://github.com/guoyww/AnimateDiff)
- [CogVideo / CogVideoX](https://github.com/THUDM/CogVideo)
- [Open-Sora](https://github.com/hpcaitech/Open-Sora)
- [LTX-Video](https://github.com/Lightricks/LTX-Video)
- [HunyuanVideo](https://github.com/Tencent-Hunyuan/HunyuanVideo) and [HunyuanVideo 1.5 consumer guide](https://apatero.com/blog/hunyuanvideo-15-complete-guide-consumer-gpu-2025)
- [Mochi](https://github.com/genmoai/mochi)
- [Replicate pricing](https://replicate.com/pricing) / [Python quickstart](https://replicate.com/docs/get-started/python)
- [Modal pricing](https://modal.com/pricing)
- [HF Inference billing](https://huggingface.co/docs/api-inference/en/rate-limits)
- [projectM](https://github.com/projectM-visualizer/projectm), [Butterchurn](https://github.com/jberg/butterchurn), [ModernGL](https://github.com/moderngl/moderngl), [py5](https://github.com/py5coding/py5)
- [MoviePy](https://github.com/Zulko/moviepy), [vidgear](https://github.com/abhiTronix/vidgear), [ffmpeg-python](https://github.com/kkroening/ffmpeg-python)
- [mugen](https://github.com/scherroman/mugen), [tammy](https://github.com/fresh-creations/tammy), [music2video](https://github.com/joeljang/music2video), [Lyriks](https://github.com/simon0302010/Lyriks)
- [Pexels API](https://www.pexels.com/api/), [Pixabay API](https://pixabay.com/api/docs/), [Unsplash API](https://unsplash.com/documentation)
- GPU power: [RTX 3060 PSU guidance](https://gamesreq.com/what-power-supply-do-i-need-for-rtx-3060-chose-right-one/), [RTX 3090 350 W class reporting](https://wccftech.com/nvidia-rtx-3090-gpu-tgp-350w/), [RTX 4060 Ti 16GB ~165 W](https://www.notebookcheck.net/NVIDIA-GeForce-RTX-4060-Ti-16G-Benchmarks-and-Specs.806215.0.html)

---

*Survey prepared for Music-AI-Toolshop music-video module planning, July 2026. Re-check cloud prices and model VRAM tables before purchase — both move quickly.*
