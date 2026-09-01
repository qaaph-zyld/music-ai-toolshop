import os
from typing import Dict, Any
import numpy as np
import librosa


def separate_hpss(audio: np.ndarray) -> Dict[str, np.ndarray]:
    y_h, y_p = librosa.effects.hpss(audio)
    return {"harmonic": y_h, "percussive": y_p}


def separate_spleeter(file_path: str, stems: int = 2) -> Dict[str, Any]:
    try:
        from spleeter.separator import Separator
        from spleeter.audio.adapter import AudioAdapter
    except Exception:
        return {}
    if stems not in (2, 4, 5):
        stems = 2
    separator = Separator(f"spleeter:{stems}stems")
    audio_loader = AudioAdapter.default()
    data, sr = audio_loader.load(file_path, sample_rate=44100)
    prediction = separator.separate(data)
    out = {k: v.mean(axis=1) if v.ndim == 2 else v for k, v in prediction.items()}
    out["sample_rate"] = sr
    return out


def export_stems(stems: Dict[str, np.ndarray], sr: int, out_dir: str, prefix: str = "stems") -> Dict[str, str]:
    import soundfile as sf
    os.makedirs(out_dir, exist_ok=True)
    paths = {}
    for name, y in stems.items():
        if name == "sample_rate":
            continue
        p = os.path.join(out_dir, f"{prefix}_{name}.wav")
        sf.write(p, y, sr)
        paths[name] = p
    return paths
