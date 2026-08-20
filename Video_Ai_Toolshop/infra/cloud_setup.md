# Cloud Environment Setup — RunPod A100 80GB

## Overview

This document covers setting up a RunPod A100 80GB instance with all tools needed for the cinematic AI video pipeline.

## 1. RunPod Template Creation

### Base Template

1. Go to [RunPod](https://runpod.io) → Templates → New Template
2. **Base image:** `runpod/pytorch:2.4.0-py3.11-cuda12.4-dev-ubuntu22.04`
3. **GPU:** A100 80GB (or RTX 4090 24GB for budget)
4. **Disk:** 100GB system + 200GB persistent volume
5. **Environment variables:**
   ```
   HF_TOKEN=<your-huggingface-token>
   ```
6. **Ports:** 8188 (ComfyUI), 7860 (Gradio), 22 (SSH)

### Persistent Volume Mount

Mount a 200GB persistent volume at `/workspace/models` for model weight storage.

**Cost:** $0.10/GB/month = $20/month for 200GB

## 2. Initial Setup Script

```bash
#!/bin/bash
# Run this on first boot of the RunPod instance

# System packages
apt-get update && apt-get install -y \
    git git-lfs ffmpeg libsm6 libxext6 libxrender-dev libgl1 \
    pkg-config libcairo2-dev

# Python packages (base)
pip install --upgrade pip
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
pip install transformers diffusers accelerate safetensors
pip install huggingface_hub

# Kohya_ss (Flux LoRA training)
cd /workspace
git clone https://github.com/kohya-ss/sd-scripts.git
cd sd-scripts
pip install -r requirements.txt
pip install lion-pytorch prodigyopt

# ComfyUI
cd /workspace
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI
pip install -r requirements.txt
# Pin version to avoid workflow JSON breakage
git checkout v0.3.22  # Use a specific stable tag

# ComfyUI Manager (for custom nodes)
cd /workspace/ComfyUI/custom_nodes
git clone https://github.com/ltdrdata/ComfyUI-Manager.git

# Essential ComfyUI nodes for video pipeline
git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git
git clone https://github.com/Kosinkadink/ComfyUI-Frame-Interpolation.git  # RIFE
git clone https://github.com/ssnl/ComfyUI_Frame_Interpolation.git  # Alternative RIFE
git clone https://github.com/city96/ComfyUI-GGUF.git  # For quantized models

# Wan 2.2 nodes (if not native in ComfyUI)
git clone https://github.com/kijai/ComfyUI-WanVideoWrapper.git

# Post-processing tools
pip install gfpgan realesrgan basicsr
cd /workspace
git clone https://github.com/xinntao/Real-ESRGAN.git
cd Real-ESRGAN
pip install -r requirements.txt
python setup.py develop

cd /workspace
git clone https://github.com/TencentARC/GFPGAN.git
cd GFPGAN
pip install -r requirements.txt
python setup.py develop

# RIFE frame interpolation
cd /workspace
git clone https://github.com/megvii-research/ECCV2022-RIFE.git rife
cd rife
pip install -r requirements.txt

# FaceFusion (backup identity correction)
cd /workspace
git clone https://github.com/facefusion/facefusion.git
cd facefusion
python install.py --onnxruntime cuda --skip-conda

# Finetrainers (alternative LoRA training — fallback for Wan 2.2)
cd /workspace
git clone https://github.com/a-r-r-o-w/finetrainers.git
cd finetrainers
pip install -r requirements.txt

# musubi-tuner (primary for Wan 2.2 dual-expert LoRA training)
cd /workspace
git clone https://github.com/kohya-ss/musubi-tuner.git
cd musubi-tuner
pip install -r requirements.txt

# HuggingFace login
huggingface-cli login --token $HF_TOKEN

echo "Setup complete!"
```

## 3. Model Downloads

```bash
#!/bin/bash
# Download model weights to persistent volume

mkdir -p /workspace/models

# Wan 2.2 I2V A14B (primary video model — ~55GB)
huggingface-cli download Wan-AI/Wan2.2-I2V-A14B --local-dir /workspace/models/Wan2.2-I2V-A14B

# Wan 2.2 TI2V 5B (budget option for 24GB VRAM — ~20GB)
huggingface-cli download Wan-AI/Wan2.2-TI2V-5B --local-dir /workspace/models/Wan2.2-TI2V-5B

# Flux.1-dev (image generation — ~24GB, non-commercial)
huggingface-cli download black-forest-labs/FLUX.1-dev --local-dir /workspace/models/FLUX.1-dev

# Flux.1-schnell (commercial alternative — ~24GB)
huggingface-cli download black-forest-labs/FLUX.1-schnell --local-dir /workspace/models/FLUX.1-schnell

# LightX2V LoRA (4-step speed optimization)
# Check ComfyUI community for latest LightX2V checkpoints

echo "Model downloads complete!"
echo "Total disk usage:"
du -sh /workspace/models/*
```

## 4. Model Weight Storage Strategy

| Model | Size | Location | Monthly Cost |
|-------|------|----------|--------------|
| Wan 2.2 I2V-A14B | ~55GB | `/workspace/models/Wan2.2-I2V-A14B` | $5.50 |
| Wan 2.2 TI2V-5B | ~20GB | `/workspace/models/Wan2.2-TI2V-5B` | $2.00 |
| Flux.1-dev | ~24GB | `/workspace/models/FLUX.1-dev` | $2.40 |
| LoRA weights | ~300-500MB each | `/workspace/models/lora/` | ~$0.05 |
| **Total** | ~100GB | Persistent volume | **~$10-12/month** |

### Alternative: Download Each Session
- Free (no persistent storage cost)
- ~30 min download time per session
- Use `huggingface-cli download` with `--local-dir` to cache

## 5. GPU Selection Guide

| GPU | VRAM | Cost/hr | Best For |
|-----|------|---------|----------|
| A100 80GB | 80GB | $1.39 | Wan 2.2 14B full quality, LoRA training |
| A100 40GB | 40GB | $1.09 | Wan 2.2 5B, Flux LoRA training |
| RTX 4090 | 24GB | $0.69 | Wan 2.2 5B (with CPU offload), post-processing |
| H100 80GB | 80GB | $2.89 | Fastest generation (LTX-Video real-time) |

### Recommended Setup
- **Training (Wave 2):** A100 80GB — $1.39/hr
- **Generation (Wave 3-4):** A100 80GB — $1.39/hr
- **Post-processing (Wave 5):** RTX 4090 — $0.69/hr

## 6. Data Privacy

- Use **private pods** (not community pods)
- Delete dataset from `/workspace/dataset/` after training
- Wipe persistent volume after project completion:
  ```bash
  rm -rf /workspace/dataset/processed/
  rm -rf /workspace/output/
  ```
- LoRA weights are safe to keep (they don't contain original photos)

## 7. ComfyUI Launch

```bash
cd /workspace/ComfyUI
python main.py --listen 0.0.0.0 --port 8188 --enable-cors-header "*"
```

Access via RunPod's port forwarding: `https://<pod-id>-8188.proxy.runpod.net`

## 8. Verification Commands

```bash
# Check GPU
nvidia-smi

# Check model downloads
ls -la /workspace/models/

# Check ComfyUI
curl http://localhost:8188/system_stats

# Check ComfyUI object_info (for workflow validation)
curl http://localhost:8188/object_info | python -m json.tool | head -50

# Check Kohya_ss
python /workspace/sd-scripts/flux_train_network.py --help

# Check GFPGAN
python -c "from gfpgan import GFPGANer; print('GFPGAN OK')"

# Check Real-ESRGAN
python -c "from realesrgan import RealESRGANer; print('Real-ESRGAN OK')"
```
