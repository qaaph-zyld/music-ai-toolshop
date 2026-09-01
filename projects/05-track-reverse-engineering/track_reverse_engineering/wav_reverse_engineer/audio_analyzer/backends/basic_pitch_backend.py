import os
import tempfile
from typing import List, Dict, Any

import numpy as np


def transcribe_basic_pitch(audio: np.ndarray, sr: int) -> List[Dict[str, Any]]:
    """Transcribe notes using Spotify Basic Pitch if installed.
    Returns empty list if package is unavailable or any error occurs.
    """
    try:
        from basic_pitch.inference import predict_and_save
        import soundfile as sf
        import pretty_midi
    except Exception:
        return []

    try:
        # Write to a temporary wav for the inference helper
        with tempfile.TemporaryDirectory() as td:
            wav_path = os.path.join(td, "input.wav")
            sf.write(wav_path, audio.astype(np.float32), sr)
            out_dir = os.path.join(td, "out")
            os.makedirs(out_dir, exist_ok=True)
            # Basic Pitch helper will emit a MIDI file we can parse
            predict_and_save([wav_path], out_dir, save_midi=True, save_npy=False, sonify_midi=False)
            # Find midi
            midis = [f for f in os.listdir(out_dir) if f.lower().endswith(".mid") or f.lower().endswith(".midi")]
            if not midis:
                return []
            midi_path = os.path.join(out_dir, midis[0])
            pm = pretty_midi.PrettyMIDI(midi_path)
            notes: List[Dict[str, Any]] = []
            for inst in pm.instruments:
                for n in inst.notes:
                    freq = 440.0 * (2 ** ((n.pitch - 69) / 12.0))
                    notes.append({
                        "pitch": pretty_midi.note_number_to_name(n.pitch),
                        "frequency": float(freq),
                        "start_time": float(n.start),
                        "duration": float(n.end - n.start),
                        "confidence": 1.0  # Basic Pitch does not expose confidence per note in MIDI
                    })
            # Sort by time
            notes.sort(key=lambda x: x["start_time"]) 
            return notes
    except Exception:
        return []
