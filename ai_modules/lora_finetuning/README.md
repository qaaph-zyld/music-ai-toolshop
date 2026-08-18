# LoRA Fine-Tuning Pipeline for BS-RoFormer / Demucs on Mastered Commercial Audio

Genre-specific LoRA adaptation of music source separation models using the [MSST](https://github.com/ZFTurbo/Music-Source-Separation-Training) framework.

## Overview

This pipeline implements a 2-stage curriculum for fine-tuning BS-RoFormer on genre-specific mastered commercial audio (Tech House, Drill, Hip-Hop):

- **Stage 1** — General genre adaptation on clean stems with LoRA
- **Stage 2** — Mastered audio adaptation with continued LoRA fine-tuning

## Prerequisites

### 1. Clone MSST

```bash
git clone https://github.com/ZFTurbo/Music-Source-Separation-Training.git
set MSST_ROOT=C:\path\to\Music-Source-Separation-Training
```

### 2. Install MSST dependencies

```bash
cd Music-Source-Separation-Training
pip install -r requirements.txt
```

### 3. Install pipeline dependencies

```bash
pip install -r ai_modules/lora_finetuning/requirements.txt
```

### 4. Download pretrained checkpoint

Download [model_bs_roformer_ep_17_sdr_9.6568.ckpt](https://github.com/ZFTurbo/Music-Source-Separation-Training/releases/download/v1.0.12/model_bs_roformer_ep_17_sdr_9.6568.ckpt) and place it in the `weights/` directory inside your MSST root.

### 5. Verify environment

```bash
python -m ai_modules.lora_finetuning.scripts.setup_check
```

## Dataset Preparation

### Raw stem format

Organize your genre-specific tracks as:

```
raw_stems/
├── Artist1 - Track1/
│   ├── vocals.wav
│   ├── drums.wav
│   ├── bass.wav
│   └── other.wav
├── Artist2 - Track2/
│   └── ...
```

All WAVs should be stereo, 44.1kHz, float32.

### Prepare datasets

```bash
# Step 1: Organize into Type 1 (MUSDB format) with train/val split
python -m ai_modules.lora_finetuning.scripts.prepare_dataset organize \
    --source raw_stems/ \
    --output dataset_clean/ \
    --train-split 0.8

# Step 2: Create mastered dataset (Type 6) with degradation pipeline
python -m ai_modules.lora_finetuning.scripts.prepare_dataset master \
    --clean-dir dataset_clean/ \
    --output dataset_mastered/

# Step 3: Validate
python -m ai_modules.lora_finetuning.scripts.prepare_dataset validate \
    --dataset-dir dataset_clean/ --type 1
python -m ai_modules.lora_finetuning.scripts.prepare_dataset validate \
    --dataset-dir dataset_mastered/ --type 6
```

## Training

### Stage 1 — Clean Genre Adaptation

```bash
python -m ai_modules.lora_finetuning.scripts.train \
    --stage 1 \
    --data-path dataset_clean/train \
    --valid-path dataset_clean/val \
    --results-path results/stage1/ \
    --device-ids 0 \
    --metrics sdr si_sdr log_wmse
```

### Stage 2 — Mastered Audio Adaptation

```bash
python -m ai_modules.lora_finetuning.scripts.train \
    --stage 2 \
    --data-path dataset_mastered/train \
    --valid-path dataset_mastered/val \
    --results-path results/stage2/ \
    --lora-checkpoint results/stage1/lora_best.ckpt \
    --device-ids 0 \
    --metrics sdr si_sdr log_wmse
```

### Full Pipeline (automated)

```bash
python -m ai_modules.lora_finetuning.scripts.run_pipeline \
    --source-dir raw_stems/ \
    --work-dir pipeline_output/ \
    --device-ids 0
```

## Evaluation

```bash
python -m ai_modules.lora_finetuning.scripts.evaluate validate \
    --valid-path dataset_mastered/val \
    --base-checkpoint weights/model_bs_roformer_ep_17_sdr_9.6568.ckpt \
    --lora-checkpoint results/stage2/lora_best.ckpt \
    --store-dir eval_results/ \
    --metrics sdr si_sdr log_wmse aura_stft aura_mrstft \
    --use-tta
```

## Inference

```bash
python -m ai_modules.lora_finetuning.scripts.evaluate infer \
    --input-folder path/to/tracks/ \
    --base-checkpoint weights/model_bs_roformer_ep_17_sdr_9.6568.ckpt \
    --lora-checkpoint results/stage2/lora_best.ckpt \
    --store-dir inference_results/
```

## Configuration

### LoRA Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `r` | 8 | Rank of low-rank adaptation. Try 16 or 32 for more capacity |
| `lora_alpha` | 16 | Scaling factor. alpha/r should be >1 |
| `lora_dropout` | 0.05 | Dropout for regularization. Increase for small datasets |
| `enable_lora` | [True, False, True] | Apply to Q and V attention projections (skip K) |

### Memory Optimization for 24GB GPUs

- `use_amp: true` — mixed precision (default)
- `use_torch_checkpoint: True` — gradient checkpointing
- `batch_size: 1` + `gradient_accumulation_steps: 8` — effective batch 8
- `flash_attn: true` — flash attention (default)

### Loss Functions

BS-RoFormer uses its internal loss by default (L1 + multi-resolution STFT). The config includes:
- Multi-resolution STFT with windows: 4096, 2048, 1024, 512, 256
- Robust quantile-masked MSE (q=0.95)
- Coarse loss clipping
- EMA momentum 0.999

For mastered audio, the CPJKU MSR Challenge combination is recommended:
- Masked SI-SNR + Multi-res STFT + L1 + low-amplitude penalty

## Data Requirements

| Metric | Minimum | Recommended |
|--------|---------|-------------|
| Tracks | 50 | 200+ |
| Sample rate | 44.1kHz | 44.1kHz |
| Channels | Stereo | Stereo |
| Duration | Full tracks | Full tracks |

MSST's built-in augmentation includes: pitch shift, EQ, distortion, loudness randomization, channel shuffle, polarity inversion, mixup, time stretch, and Gaussian noise.

## File Structure

```
ai_modules/lora_finetuning/
├── __init__.py
├── requirements.txt
├── README.md
├── configs/
│   ├── stage1_genre_clean.yaml    # Stage 1 config (clean stems)
│   └── stage2_mastered.yaml       # Stage 2 config (mastered audio)
└── scripts/
    ├── __init__.py
    ├── prepare_dataset.py          # Dataset organization + mastering
    ├── train.py                    # Training launcher
    ├── evaluate.py                 # Validation + inference launcher
    ├── run_pipeline.py             # Full automated pipeline
    └── setup_check.py              # Environment verification
```

## Research Sources

- [MSST Framework](https://github.com/ZFTurbo/Music-Source-Separation-Training)
- [MSST Paper](https://arxiv.org/html/2607.23395)
- [MSST LoRA Documentation](https://github.com/ZFTurbo/Music-Source-Separation-Training/blob/main/docs/LoRA.md)
- [CPJKU MSR Challenge Paper](https://arxiv.org/html/2603.04032)
- [CPJKU MSR GitHub](https://github.com/CPJKU/music-source-restoration)
- [LoRA Hyperparameters Guide](https://mbrenndoerfer.com/writing/lora-hyperparameters-rank-alpha-target-modules)
- [Loss Functions for MSS](https://ar5iv.labs.arxiv.org/html/2202.07968)
- [Transfer Learning in MSS](https://ar5iv.labs.arxiv.org/html/2010.12650)
- [torch-audiomentations](https://github.com/iver56/torch-audiomentations)
