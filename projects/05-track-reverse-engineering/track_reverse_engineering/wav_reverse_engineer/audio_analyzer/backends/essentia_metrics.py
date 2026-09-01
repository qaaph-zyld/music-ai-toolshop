from typing import Dict, Any
import numpy as np


def compute_essentia_metrics(audio: np.ndarray, sr: int) -> Dict[str, Any]:
    """Compute key/scale and loudness using Essentia if available."""
    try:
        import essentia.standard as es
    except Exception:
        return {}

    y = audio.astype(np.float32)
    out: Dict[str, Any] = {}
    try:
        key, scale, strength = es.KeyExtractor()(y)
        out['essentia_key'] = key
        out['essentia_mode'] = scale
        out['essentia_key_strength'] = float(strength)
    except Exception:
        pass

    try:
        # Simple ITU loudness (not full EBU R128 streaming)
        lufs = float(es.Loudness()(y))
        out['loudness_itu'] = lufs
    except Exception:
        pass

    return out
