"""Pre-seed the OGCM-flip wave-0 models into the toolshop model cache.

Loads each new audio-separator registry model once so the download happens in a
resumable, logged batch rather than mid-separation. Prints a per-model PASS/FAIL
summary at the end.
"""
import json
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from toolshop import stem_models  # noqa: E402
from toolshop.stem_extractor_adapter import (  # noqa: E402
    _check_audio_separator,
    _default_model_dir,
    default_mdxc_params,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

MODEL_IDS = [
    "mel-band-roformer-kim-bleedless",
    "deverb-mel-band-roformer-anvuew",
    "mdx23c-drumsep",
]


def main() -> int:
    _check_audio_separator()
    from audio_separator.separator import Separator

    model_dir = _default_model_dir()
    model_dir.mkdir(parents=True, exist_ok=True)
    results = {}

    for mid in MODEL_IDS:
        model = stem_models.get_model(mid)
        ckpt = model_dir / model.model_file
        t0 = time.time()
        if ckpt.exists():
            print(f"[skip] {mid}: {model.model_file} already cached", flush=True)
            results[mid] = "cached"
            continue
        try:
            sep = Separator(
                output_dir=str(model_dir / "_tmp_out"),
                output_format="wav",
                use_directml=False,
                model_file_dir=str(model_dir),
                mdxc_params=default_mdxc_params(),
            )
            sep.load_model(model.model_file)
            del sep
            size_mb = ckpt.stat().st_size / 1e6 if ckpt.exists() else 0
            print(f"[ok] {mid}: {model.model_file} {size_mb:.0f} MB in {time.time()-t0:.0f}s", flush=True)
            results[mid] = f"downloaded ({size_mb:.0f} MB)"
        except Exception as exc:  # noqa: BLE001 - report and continue
            print(f"[FAIL] {mid}: {exc}", flush=True)
            results[mid] = f"FAIL: {exc}"

    print(json.dumps(results, indent=2), flush=True)
    return 0 if not any(str(v).startswith("FAIL") for v in results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
