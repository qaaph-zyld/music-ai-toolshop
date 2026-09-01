import numpy as np
import librosa
from typing import Dict, Any


def track_f0_torchcrepe(audio: np.ndarray, sr: int, hop_length: int = 160, model: str = 'full') -> Dict[str, Any]:
    """Track F0 using torchcrepe if available. Returns dict with times, f0_hz, periodicity.
    Audio is resampled to 16 kHz as required by torchcrepe.
    """
    try:
        import torch
        import torchcrepe
    except Exception:
        return {}

    # Resample to 16kHz for torchcrepe
    target_sr = 16000
    if sr != target_sr:
        y = librosa.resample(audio, orig_sr=sr, target_sr=target_sr)
    else:
        y = audio

    fmin, fmax = 50.0, 1100.0
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    truncated = False
    # If running on CPU and audio is long, truncate to avoid very long runtimes
    max_seconds_cpu = 60.0
    dur = float(len(y)) / float(target_sr)
    if device == 'cpu' and dur > max_seconds_cpu:
        y = y[: int(target_sr * max_seconds_cpu)]
        truncated = True
        # Use a smaller model if caller requested full
        if model == 'full':
            model = 'tiny'
    # Prepare tensor (1, time) after any truncation
    y_t = torch.tensor(y, dtype=torch.float32).unsqueeze(0)
    try:
        with torch.no_grad():
            out = torchcrepe.predict(
                y_t, target_sr, hop_length, fmin, fmax,
                model=model, batch_size=1024, return_periodicity=True, device=device
            )
            # torchcrepe versions may return (f0, periodicity) or (f0, periodicity, extras)
            if isinstance(out, (list, tuple)):
                if len(out) >= 2:
                    f0, periodicity = out[0], out[1]
                else:
                    # Unexpected shape; fallback to zeros
                    T = int(np.ceil(len(y) / hop_length))
                    f0 = torch.zeros(1, T)
                    periodicity = torch.zeros(1, T)
            else:
                # Unexpected return type; fallback
                T = int(np.ceil(len(y) / hop_length))
                f0 = torch.zeros(1, T)
                periodicity = torch.zeros(1, T)

        f0 = f0.squeeze(0).cpu().numpy()
        periodicity = periodicity.squeeze(0).cpu().numpy()
        times = np.arange(len(f0)) * (hop_length / float(target_sr))

        return {
            'times': times.tolist(),
            'f0_hz': f0.tolist(),
            'periodicity': periodicity.tolist(),
            'sample_rate': target_sr,
            'hop_length': hop_length,
            'device': device,
            'truncated': truncated
        }
    except Exception:
        # Any failure should yield an empty dict so callers can fallback to YIN
        return {}
