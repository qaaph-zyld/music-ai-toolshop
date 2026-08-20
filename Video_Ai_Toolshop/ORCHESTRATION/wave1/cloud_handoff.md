# Wave 1 — Cloud Environment Setup Handoff

**Agent:** cloud
**Wave:** 1
**Status:** COMPLETE
**Date:** 2026-08-20

## Deliverables

- `infra/cloud_setup.md` — Complete RunPod setup guide with:
  - RunPod template configuration (A100 80GB, disk, ports, env vars)
  - Initial setup script (installs Kohya_ss, ComfyUI, GFPGAN, Real-ESRGAN, RIFE, FaceFusion, finetrainers)
  - Model download commands (Wan 2.2 14B/5B, Flux.1-dev/schnell)
  - Model weight storage strategy with cost breakdown
  - GPU selection guide (A100 80GB vs 4090 vs H100)
  - Data privacy instructions
  - ComfyUI launch command
  - Verification commands

## Key Decisions

- **Primary GPU:** A100 80GB at $1.39/hr for training and generation
- **Budget GPU:** RTX 4090 at $0.69/hr for post-processing
- **ComfyUI version:** Pinned to v0.3.22 (workflow JSON fragility mitigation)
- **Persistent storage:** 200GB volume at $20/month for model weights
- **Privacy:** Private pods only, wipe data after project completion

## Model Storage Costs

| Model | Size | Monthly Cost |
|-------|------|--------------|
| Wan 2.2 I2V-A14B | ~55GB | $5.50 |
| Flux.1-dev | ~24GB | $2.40 |
| Wan 2.2 TI2V-5B | ~20GB | $2.00 |
| LoRA weights | ~500MB | ~$0.05 |
| **Total** | ~100GB | **~$10-12/month** |

## Next Steps (Wave 2)

1. Deploy RunPod A100 80GB instance using the template
2. Run the initial setup script
3. Download model weights
4. Upload dataset (from dataset agent)
5. Begin LoRA training
