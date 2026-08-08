"""Setup helper for the LoRA fine-tuning pipeline.

Checks for MSST, dependencies, and pretrained checkpoints.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


def check_python() -> bool:
    ver = sys.version_info
    ok = ver >= (3, 10)
    print(f"Python {ver.major}.{ver.minor}.{ver.micro}: {'OK' if ok else 'FAIL (need >=3.10)'}")
    return ok


def check_torch() -> bool:
    try:
        import torch
        cuda = torch.cuda.is_available()
        device = torch.cuda.get_device_name(0) if cuda else "CPU only"
        vram = torch.cuda.get_device_properties(0).total_mem / 1e9 if cuda else 0
        print(f"PyTorch {torch.__version__}: OK (CUDA: {cuda}, {device}" + (f", {vram:.1f}GB VRAM)" if cuda else ")"))
        return True
    except ImportError:
        print("PyTorch: NOT INSTALLED")
        return False


def check_msst(msst_root: Path | None = None) -> bool:
    if msst_root is None:
        from .train import find_msst_root
        msst_root = find_msst_root()

    if msst_root and msst_root.exists() and (msst_root / "train.py").exists():
        print(f"MSST: OK ({msst_root})")
        return True
    else:
        print(f"MSST: NOT FOUND (expected at {msst_root or 'auto-detect'})")
        print("  Clone: git clone https://github.com/ZFTurbo/Music-Source-Separation-Training.git")
        return False


def check_dependencies() -> list[str]:
    missing = []
    deps = {
        "soundfile": "soundfile",
        "numpy": "numpy",
        "yaml": "pyyaml",
        "pedalboard": "pedalboard",
        "audiomentations": "audiomentations",
    }
    for module, package in deps.items():
        try:
            __import__(module)
            print(f"  {package}: OK")
        except ImportError:
            print(f"  {package}: MISSING")
            missing.append(package)
    return missing


def check_checkpoint(checkpoint_path: str) -> bool:
    p = Path(checkpoint_path)
    if p.exists():
        size_mb = p.stat().st_size / 1e6
        print(f"Pretrained checkpoint: OK ({p}, {size_mb:.1f}MB)")
        return True
    else:
        print(f"Pretrained checkpoint: NOT FOUND ({p})")
        print("  Download: https://github.com/ZFTurbo/Music-Source-Separation-Training/releases/download/v1.0.12/model_bs_roformer_ep_17_sdr_9.6568.ckpt")
        return False


def main():
    print("=" * 60)
    print("LoRA Fine-Tuning Pipeline — Environment Check")
    print("=" * 60)
    print()

    ok = True
    ok &= check_python()
    print()
    ok &= check_torch()
    print()
    print("Dependencies:")
    missing = check_dependencies()
    if missing:
        print(f"  Install missing: pip install {' '.join(missing)}")
        ok = False
    print()

    msst_root = Path(os.environ.get("MSST_ROOT", ""))
    ok &= check_msst(msst_root if msst_root.exists() else None)
    print()

    ok &= check_checkpoint("weights/model_bs_roformer_ep_17_sdr_9.6568.ckpt")
    print()

    print("=" * 60)
    if ok:
        print("All checks passed! Ready to train.")
    else:
        print("Some checks failed. See above for fix instructions.")
    print("=" * 60)

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
