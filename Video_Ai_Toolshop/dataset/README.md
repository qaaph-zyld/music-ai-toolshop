# Dataset Curation Guide

## Overview

This guide covers preparing your photos for SDXL DreamBooth LoRA training on free-tier GPUs (Kaggle P100 / Colab T4 16GB).

## Step 1: Photo Selection

From your 50+ photos, select **25-30 best images**:

### Essential (10-15 images)
- Front-facing, 3/4 angle, side profile
- Sharp, well-lit, face clearly visible
- Subject fills 60-80% of frame
- Natural expressions

### Supporting (10-15 images)
- Different expressions (smiling, serious, surprised)
- Different lighting (indoor, outdoor, studio)
- Different backgrounds and outfits
- Varied head positions

### Edge Cases (5 images)
- Unusual angles (from above, from below)
- Varied distances (close-up to full body)
- Different hair styles or facial hair if applicable

### Reject Criteria
- Motion blur
- Poor exposure (too dark/too bright)
- Watermarks or timestamps
- Heavy Instagram-style filters
- Age inconsistency (use photos from same time period)
- Near-duplicate poses

## Step 2: Cropping and Formatting

```python
from PIL import Image
import os

input_dir = "dataset/raw"
output_dir = "dataset/processed"
os.makedirs(output_dir, exist_ok=True)

target_w, target_h = 1024, 576  # 16:9 matching Wan 2.2 aspect ratio

for filename in os.listdir(input_dir):
    if not filename.lower().endswith(('.jpg', '.jpeg', '.png')):
        continue
    
    img = Image.open(os.path.join(input_dir, filename))
    
    # Center crop to 16:9 aspect ratio
    current_ratio = img.width / img.height
    target_ratio = target_w / target_h
    
    if current_ratio > target_ratio:
        # Image is wider — crop width
        new_width = int(img.height * target_ratio)
        left = (img.width - new_width) // 2
        img = img.crop((left, 0, left + new_width, img.height))
    else:
        # Image is taller — crop height
        new_height = int(img.width / target_ratio)
        top = (img.height - new_height) // 2
        img = img.crop((0, top, img.width, top + new_height))
    
    # Resize to target
    img = img.resize((target_w, target_h), Image.LANCZOS)
    
    # Save as PNG
    name = os.path.splitext(filename)[0]
    img.save(os.path.join(output_dir, f"{name}.png"), "PNG")
    
print(f"Processed images saved to {output_dir}")
```

**Format:** PNG (lossless)
**Resolution:** 1024×576 (16:9)
**Face position:** Centered in frame

## Step 3: Captioning

Every image needs a text file with the same name (e.g., `photo_001.png` → `photo_001.txt`):

```
ohwx person, [physical description], [pose/expression], [clothing], [setting], [lighting]
```

### Caption Template

```
ohwx person, [gender] with [hair] and [eyes], [expression], wearing [clothing], in [setting], [lighting description]
```

### Example Captions

```
ohwx person, man with short dark hair and brown eyes, smiling warmly, wearing casual blue shirt, in modern coffee shop, soft natural lighting from window
ohwx person, man with short dark hair and brown eyes, serious expression, wearing black leather jacket, on city street at night, neon lighting
ohwx person, man with short dark hair and brown eyes, looking at camera, wearing white t-shirt, in studio with gray backdrop, three-point studio lighting
```

### Auto-Captioning Tools

1. **Florence-2** (recommended): `pip install transformers`
```python
from transformers import AutoProcessor, AutoModelForCausalLM
import torch

model = AutoModelForCausalLM.from_pretrained("microsoft/Florence-2-large", trust_remote_code=True)
processor = AutoProcessor.from_pretrained("microsoft/Florence-2-large", trust_remote_code=True)

# Generate detailed caption
inputs = processor(images=image, text="<MORE_DETAILED_CAPTION>", return_tensors="pt")
generated = model.generate(**inputs, max_new_tokens=200)
caption = processor.batch_decode(generated, skip_special_tokens=True)[0]
```

2. **BLIP-2**: Simpler but less detailed
3. **JoyCaption**: Best quality but requires separate installation
4. **Manual refinement**: Always review and edit auto-generated captions

### Trigger Word

Use a unique trigger word that won't conflict with common terms:
- `ohwx person` (common in community)
- Or a custom token like `zjk person`

Use the **same trigger word** in every caption and in every generation prompt.

## Step 4: Directory Structure for Training

```
dataset/
├── raw/                    # Original photos (gitignored)
├── processed/              # Cropped 1024×576 PNGs (gitignored)
│   ├── photo_001.png
│   ├── photo_001.txt       # Caption
│   ├── photo_002.png
│   ├── photo_002.txt
│   └── ...
└── dataset_config.toml     # Kohya_ss training config
```

### Kohya_ss Dataset Config (`dataset_config.toml`)

```toml
[general]
resolution = [1024, 576]
shuffle_caption = true
keep_tokens = 1

[[datasets]]
batch_size = 1
enable_bucket = false

  [[datasets.subsets]]
  image_dir = "/workspace/dataset/processed"
  caption_extension = ".txt"
  num_repeats = 10
```

## Step 5: Video Clips (Track B Only)

If pursuing Track B (Wan 2.2 video LoRA), also collect:

- **10-20 short video clips**, 2-5 seconds each
- Face clearly visible throughout
- Varied actions: talking, walking, turning head, different expressions
- Resolution: 480×720 or higher
- Consistent lighting within each clip
- Format: MP4 (H.264)

Store in `dataset/video_clips/`

## Step 6: Upload to Cloud

```bash
# Upload processed dataset to RunPod
scp -r dataset/processed/ root@<runpod-ip>:/workspace/dataset/
scp dataset/dataset_config.toml root@<runpod-ip>:/workspace/dataset/
```

## Validation Checklist

- [ ] 25-30 images selected
- [ ] All images cropped to 1024×576
- [ ] All images have corresponding .txt caption files
- [ ] All captions start with trigger word (`ohwx person`)
- [ ] No duplicate poses
- [ ] Varied lighting, backgrounds, expressions
- [ ] `dataset_config.toml` created
- [ ] (Track B only) 10-20 video clips collected
