import os
from typing import Dict, Any, Optional
import numpy as np


def separate_demucs(file_path: str, model_name: str = 'htdemucs', device: str = 'auto', chunk_seconds: Optional[float] = None) -> Dict[str, Any]:
    """Separate sources using Demucs if installed. Returns dict of stems or empty dict.
    This is a best-effort wrapper and will return {} if Demucs is unavailable.
    """
    try:
        import torch  # noqa: F401
        from demucs.pretrained import get_model
        from demucs.apply import apply_model
        from demucs.audio import AudioFile
    except Exception:
        return {}

    try:
        model = get_model(model_name)
        if device == 'auto':
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
        model.to(device)
        wav = AudioFile(file_path).read(streams=0, samplerate=model.samplerate, channels=2)
        if not isinstance(wav, np.ndarray):
            wav = np.asarray(wav)
        # wav shape: (channels, time)
        with torch.no_grad():
            if chunk_seconds and chunk_seconds > 0:
                seg = int(round(chunk_seconds * model.samplerate))
                total = wav.shape[-1]
                outs = []
                for start in range(0, total, seg):
                    end = min(start + seg, total)
                    chunk = wav[:, start:end]
                    if chunk.size == 0:
                        continue
                    out_chunk = apply_model(model, torch.from_numpy(chunk)[None], device=device)[0]
                    outs.append(out_chunk)
                if not outs:
                    return {}
                out = torch.cat(outs, dim=-1)
            else:
                out = apply_model(model, torch.from_numpy(wav)[None], device=device)[0]
        stems = {}
        for i, name in enumerate(model.sources):
            mono = out[i].mean(0).cpu().numpy()
            stems[name] = mono
        stems['sample_rate'] = model.samplerate
        return stems
    except Exception:
        return {}
