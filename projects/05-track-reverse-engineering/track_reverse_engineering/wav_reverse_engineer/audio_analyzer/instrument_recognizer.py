import numpy as np
import librosa
from typing import List, Dict, Any


class InstrumentRecognizer:
    def __init__(self):
        self._panns = None
        try:
            import torch  # noqa: F401
            from panns_inference import AudioTagging
            self._panns = AudioTagging(checkpoint_path=None, device='cpu')
        except Exception:
            self._panns = None

    def _panns_predict(self, audio: np.ndarray, sr: int, top_k: int = 5) -> List[Dict[str, Any]]:
        if self._panns is None:
            return []
        import librosa
        x = librosa.resample(audio, orig_sr=sr, target_sr=32000)
        x = x[None, :]  # (batch, time)
        clipwise_output, embedding = self._panns.inference(x)
        labels = self._panns.labels
        scores = clipwise_output[0]
        idxs = np.argsort(scores)[::-1][:top_k]
        return [{"label": labels[i], "score": float(scores[i])} for i in idxs]

    def _heuristic_predict(self, audio: np.ndarray, sr: int) -> List[Dict[str, Any]]:
        y_h, y_p = librosa.effects.hpss(audio)
        perc_ratio = float(np.mean(np.abs(y_p)) / (np.mean(np.abs(audio)) + 1e-9))
        harm_ratio = float(np.mean(np.abs(y_h)) / (np.mean(np.abs(audio)) + 1e-9))
        onset_env = librosa.onset.onset_strength(y=audio, sr=sr)
        onset_rate = float(len(librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr)) / (len(audio) / sr + 1e-9))
        centroid = float(np.mean(librosa.feature.spectral_centroid(y=audio, sr=sr)))
        rolloff = float(np.mean(librosa.feature.spectral_rolloff(y=audio, sr=sr)))
        f0 = librosa.pyin(audio, fmin=80, fmax=1000, sr=sr, frame_length=2048, hop_length=256)
        voiced = np.isfinite(f0)
        voiced_ratio = float(np.mean(voiced)) if f0 is not None else 0.0
        tags = []
        if perc_ratio > 0.6 or onset_rate > 3.0:
            tags.append(("drums/percussion", 0.8 * perc_ratio + 0.2 * min(onset_rate / 6.0, 1.0)))
        if harm_ratio > 0.6 and centroid < 3000:
            tags.append(("guitar/piano", min(1.0, 0.5 + 0.5 * harm_ratio)))
        if harm_ratio > 0.5 and voiced_ratio > 0.2:
            tags.append(("vocals", min(1.0, 0.3 + 0.7 * voiced_ratio)))
        if harm_ratio > 0.5 and centroid < 1500 and rolloff < 4000:
            tags.append(("bass", min(1.0, 0.4 + 0.6 * (1.0 - centroid / 5000.0))))
        if not tags:
            tags = [("unknown", 0.5)]
        tags = sorted(tags, key=lambda x: x[1], reverse=True)
        return [{"label": k, "score": float(v)} for k, v in tags[:5]]

    def recognize(self, audio: np.ndarray, sr: int, top_k: int = 5) -> List[Dict[str, Any]]:
        res = self._panns_predict(audio, sr, top_k=top_k)
        if res:
            return res
        return self._heuristic_predict(audio, sr)
