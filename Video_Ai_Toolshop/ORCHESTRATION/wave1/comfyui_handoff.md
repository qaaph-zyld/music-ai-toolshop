# Wave 1 — ComfyUI Workflow Designer Handoff

**Agent:** comfyui
**Wave:** 1
**Status:** COMPLETE
**Date:** 2026-08-20

## Deliverables

- `workflows/wan22_i2v_basic.json` — Basic Wan 2.2 I2V workflow (reference image → 5s 720P/24fps clip)
- `workflows/wan22_camera_control.json` — Camera control workflow (WanCameraEmbedding, dolly_forward)
- `workflows/wan22_controlnet_stacking.json` — ControlNet stacking (Depth 0.75 + OpenPose 0.65)

## Workflow Details

### Basic I2V (`wan22_i2v_basic.json`)
- CheckpointLoaderSimple → LoadImage → CLIPTextEncode (pos/neg) → WanImageToVideo → VAEDecode → SaveAnimatedWEBP
- Settings: 1280×704, 121 frames (5s@24fps), 40 steps, CFG 7.5, flow_shift 5.0
- Negative prompt includes motion-specific: "He is speaking. Talking. mouth moving"

### Camera Control (`wan22_camera_control.json`)
- Adds WanCameraEmbedding node with `camera_type: dolly_forward`
- flow_shift increased to 8.0 for more motion room
- motion_scale: 1.0 (adjustable)

### ControlNet Stacking (`wan22_controlnet_stacking.json`)
- DepthAnythingPreprocessor → ControlNet (strength 0.75)
- OpenPosePreprocessor → ControlNet (strength 0.65)
- Both applied to positive conditioning before WanImageToVideo
- VRAM: 16-24GB for 2 ControlNets at 768×768

## Key Decisions

- **ComfyUI version:** Pin to v0.3.22 (workflow JSON breaks across versions)
- **Resolution:** 1280×704 (Wan 2.2 14B native) — note: camera control on 24GB VRAM limited to 640×640
- **Output format:** Animated WebP (ComfyUI native) → convert to MP4 with FFmpeg
- **Negative prompts:** Include motion-specific negatives to suppress unwanted talking/mouth movement

## Validation

Before using workflows in production:
1. Load in ComfyUI
2. Check all nodes resolve (no red errors)
3. Validate against `/object_info` endpoint: `curl http://localhost:8188/object_info | python -m json.tool`
4. If nodes missing, install via ComfyUI Manager

## Next Steps (Wave 4)

- Load workflows into ComfyUI on RunPod instance
- Connect reference images (from Wave 3) as LoadImage inputs
- Optionally load Track B LoRAs via LoraLoader nodes
- Generate video clips
