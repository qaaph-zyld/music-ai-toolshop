# Wave 1 — Dataset Curator Handoff

**Agent:** dataset
**Wave:** 1
**Status:** COMPLETE
**Date:** 2026-08-20

## Deliverables

- `dataset/README.md` — Complete dataset curation guide with:
  - Photo selection criteria (25-30 images, essential/supporting/edge case breakdown)
  - Cropping script (Python/PIL) to 1024×576 (16:9 matching Wan 2.2 aspect ratio)
  - Captioning guide with template, examples, and auto-captioning tools (Florence-2, BLIP-2, JoyCaption)
  - Kohya_ss dataset config TOML
  - Video clip collection guide (Track B)
  - Upload instructions for RunPod
  - Validation checklist

## Key Decisions

- **Resolution:** 1024×576 (16:9) — matches Wan 2.2 I2V input aspect ratio, avoids resize quality loss
- **Trigger word:** `ohwx person` (community standard, unlikely to conflict)
- **Caption format:** One .txt file per image, same basename
- **Format:** PNG (lossless)

## Next Steps (Wave 2)

User must:
1. Place 25-30 selected photos in `dataset/raw/`
2. Run the cropping script to generate `dataset/processed/`
3. Write or auto-generate captions for each image
4. Upload `dataset/processed/` + captions to RunPod A100 instance
