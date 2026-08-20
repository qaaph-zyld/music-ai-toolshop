# Free-Tier Cloud Setup — Kaggle P100 + Google Colab T4 + HuggingFace

## Overview

Zero-cost pipeline using free cloud GPU tiers. No RunPod, no paid services.

## 1. Account Setup

### Required Accounts (all free)
1. **Google account** — for Google Colab and Google Drive (15GB free)
2. **Kaggle account** — for Kaggle P100 GPU (30h/week free)
3. **HuggingFace account** — for model weight storage (free private repos)

### API Keys Needed
- **HuggingFace token:** Settings → Access Tokens → New token (write permission)
- **Kaggle API key:** Settings → Create New API Token → save `kaggle.json`

## 2. Google Drive Setup

```
MyDrive/
├── video_ai_toolshop/
│   ├── dataset/              # 25-30 photos + captions
│   ├── lora_weights/         # Trained LoRA files (~500MB each)
│   ├── reference_images/     # Generated cinematic images
│   ├── raw_video/            # Raw AI video clips
│   ├── processed_video/      # Post-processed clips
│   └── final/                # Assembled videos
```

**Total Drive usage:** ~3-7GB (fits in 15GB free tier)

## 3. HuggingFace Hub Setup

### Create private repo for LoRA weights
```python
from huggingface_hub import HfApi
api = HfApi()
api.create_repo(repo_id="my-sdxl-lora", repo_type="model", private=True)
api.create_repo(repo_id="my-hunyuan-lora", repo_type="model", private=True)
```

### Upload LoRA weights
```python
from huggingface_hub import upload_file
upload_file(
    path_or_fileobj="pytorch_lora_weights.safetensors",
    path_in_repo="pytorch_lora_weights.safetensors",
    repo_id="my-sdxl-lora",
    token="hf_your_token"
)
```

### Download LoRA weights in Colab
```python
from huggingface_hub import hf_hub_download
lora_path = hf_hub_download(repo_id="my-sdxl-lora", filename="pytorch_lora_weights.safetensors", token="hf_your_token")
```

## 4. Kaggle P100 Setup (Training)

### Notebook Configuration
1. Create new notebook at kaggle.com/code
2. Settings → Accelerator → **GPU P100 16GB**
3. Settings → Internet → **On**
4. Settings → Environment → **Pin to specific version** (for reproducibility)

### Kaggle Cell: Install Dependencies
```python
!pip install -q torch torchvision torchaudio
!pip install -q diffusers transformers accelerate safetensors
!pip install -q kohya-ss[sdxl]  # or clone sd-scripts
!pip install -q insightface onnxruntime-gpu  # for ArcFace validation
!pip install -q huggingface_hub
```

### Kaggle Cell: Mount Google Drive (via Kaggle dataset)
Kaggle doesn't support Google Drive mounting directly. Instead:
1. Upload dataset as a Kaggle dataset (private)
2. Or use HuggingFace Hub to transfer files

```python
# Option A: Upload dataset to Kaggle as private dataset
# kaggle datasets create -p /path/to/dataset

# Option B: Download from HuggingFace
from huggingface_hub import snapshot_download
dataset_path = snapshot_download(repo_id="my-dataset", repo_type="dataset", token="hf_your_token")
```

### Kaggle Time Management
- **30 hours/week** of P100 GPU time
- SDXL LoRA training: ~2-3 hours per iteration
- Budget: 3 iterations × 3h = 9h (well within 30h limit)
- **Tip:** Save checkpoints to HuggingFace after each epoch — Kaggle clears output on session end

## 5. Google Colab T4 Setup (Generation + Post-Processing)

### Notebook Configuration
1. Create new notebook at colab.research.google.com
2. Runtime → Change runtime type → **T4 GPU**

### Colab Cell: Install Dependencies
```python
!pip install -q torch torchvision torchaudio
!pip install -q diffusers transformers accelerate safetensors
!pip install -q gfpgan realesrgan basicsr
!pip install -q huggingface_hub
!pip install -q insightface onnxruntime-gpu
```

### Colab Cell: Mount Google Drive
```python
from google.colab import drive
drive.mount('/content/drive')
```

### Colab Session Management
- **Free Colab:** ~12h per session, may disconnect sooner
- **Save to Google Drive after EVERY clip** — don't accumulate in /content/
- **Tip:** Use `torch.cuda.empty_cache()` between generations to avoid OOM
- **Tip:** Keep notebooks small — one task per notebook (generation, post-processing)

## 6. Model Downloads (per session)

Models are NOT stored persistently — download from HuggingFace each session.

### SDXL (image generation + LoRA training)
```python
from diffusers import StableDiffusionXLPipeline
pipe = StableDiffusionXLPipeline.from_pretrained(
    "stabilityai/stable-diffusion-xl-base-1.0",
    torch_dtype=torch.float16,
    variant="fp16"
).to("cuda")
```

### HunyuanVideo 1.5 (video generation)
```python
from diffusers import HunyuanVideoPipeline
pipe = HunyuanVideoPipeline.from_pretrained(
    "tencent/HunyuanVideo-1.5",
    torch_dtype=torch.float16,
).to("cuda")
pipe.enable_model_cpu_offload()  # Required for 16GB VRAM
```

### LTX-Video 2B (fallback, 8GB VRAM)
```python
from diffusers import LTXVideoPipeline
pipe = LTXVideoPipeline.from_pretrained(
    "Lightricks/LTX-Video-2B",
    torch_dtype=torch.float16,
).to("cuda")
```

## 7. Storage Strategy

| Data | Size | Location | Persistence |
|------|------|----------|-------------|
| Dataset (25-30 photos) | ~50MB | Google Drive | Permanent |
| SDXL base model | ~7GB | HuggingFace (re-download) | Per session |
| HunyuanVideo 1.5 | ~16GB | HuggingFace (re-download) | Per session |
| LTX-Video 2B | ~4GB | HuggingFace (re-download) | Per session |
| LoRA weights | ~500MB | HuggingFace Hub | Permanent |
| Reference images | ~200MB | Google Drive | Permanent |
| Raw video clips | ~500MB-1GB | Google Drive | Temporary (delete after processing) |
| Processed clips | ~2-5GB | Google Drive | Temporary (delete after assembly) |
| **Total Drive** | ~3-7GB | | Fits in 15GB free |
| **Total HF Hub** | ~1GB | | Free private repos |

## 8. GPU Comparison

| Platform | GPU | VRAM | Hours | Speed | Best For |
|----------|-----|------|-------|-------|----------|
| Kaggle | P100 | 16GB | 30h/week | Medium | LoRA training (stable, long sessions) |
| Colab (free) | T4 | 16GB | ~12h/session | Medium | Generation, post-processing |
| Colab Pro | T4/V100 | 16-16GB | More hours | Faster | Optional upgrade ($10/mo) |

### P100 vs T4 Notes
- **P100 (Kaggle):** Pascal architecture, no fp16 tensor cores but 16GB VRAM. Good for training.
- **T4 (Colab):** Turing architecture, has fp16 tensor cores. Good for inference.
- Both support `enable_model_cpu_offload()` for HunyuanVideo 1.5 (14GB min VRAM).

## 9. Session Workflow

### Training Session (Kaggle, ~3h)
1. Open Kaggle notebook, enable P100
2. Install dependencies (5 min)
3. Download dataset from HuggingFace/Drive (5 min)
4. Run Kohya_ss SDXL LoRA training (2-3h)
5. Validate identity with ArcFace (10 min)
6. Upload LoRA to HuggingFace Hub (5 min)
7. Save notebook output

### Generation Session (Colab, ~2-4h)
1. Open Colab notebook, enable T4
2. Install dependencies (5 min)
3. Mount Google Drive (1 min)
4. Download SDXL + LoRA from HuggingFace (10 min)
5. Generate reference images (30-60 min)
6. Save to Google Drive (5 min)
7. Download HunyuanVideo 1.5 (15 min)
8. Generate video clips (10-20 min per clip)
9. Save each clip to Google Drive immediately

### Post-Processing Session (Colab, ~1-3h)
1. Open Colab notebook, enable T4
2. Install GFPGAN, Real-ESRGAN, RIFE (10 min)
3. Mount Google Drive (1 min)
4. Process each clip: GFPGAN → Real-ESRGAN → RIFE (20-40 min per clip)
5. Save processed clips to Google Drive

## 10. Cost Summary

| Component | Cost |
|-----------|------|
| Kaggle P100 GPU | $0 (30h/week free) |
| Google Colab T4 | $0 (free tier) |
| Google Drive 15GB | $0 (free tier) |
| HuggingFace Hub | $0 (free private repos) |
| DaVinci Resolve | $0 (free version) |
| Piper TTS | $0 (local, CPU) |
| Freesound SFX | $0 (attribution license) |
| YouTube Audio Library | $0 (royalty-free) |
| **Total** | **$0** |
