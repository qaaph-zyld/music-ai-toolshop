"""
Simple FastAPI microservice for headless analysis.
Install with extras: pip install -e .[api]
Run: uvicorn wav_reverse_engineer.api.app:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse

from ..audio_analyzer.audio_processor import AudioProcessor
from ..audio_analyzer.feature_extractor import FeatureExtractor
from ..audio_analyzer.effects_analyzer import analyze_effects
from ..audio_analyzer.instrument_recognizer import InstrumentRecognizer
from ..audio_analyzer.source_separation import separate_hpss
from ..audio_analyzer.backends.essentia_metrics import compute_essentia_metrics
from ..audio_analyzer.backends.chordino import detect_chords_chordino
from ..audio_analyzer.backends.pitch_torchcrepe import track_f0_torchcrepe
from ..audio_analyzer.backends.basic_pitch_backend import transcribe_basic_pitch
from ..audio_analyzer.backends.demucs_backend import separate_demucs

app = FastAPI(title="WAV Reverse Engineering API", version="0.1.0")


def _to_builtin(x):
    try:
        import numpy as _np  # local import
        if isinstance(x, (_np.floating, _np.integer, _np.bool_)):
            return x.item()
        if isinstance(x, _np.ndarray):
            return x.tolist()
    except Exception:
        pass
    if isinstance(x, list):
        return [_to_builtin(v) for v in x]
    if isinstance(x, tuple):
        return tuple(_to_builtin(v) for v in x)
    if isinstance(x, dict):
        return {k: _to_builtin(v) for k, v in x.items()}
    return x


@app.post("/analyze")
async def analyze(
    file: UploadFile = File(...),
    effects: bool = Form(False),
    instruments: bool = Form(False),
    essentia: bool = Form(False),
    chord_backend: str = Form("simple"),
    pitch_backend: str = Form("yin"),
    notes_backend: str = Form("librosa"),
    separate: str = Form("none"),  # none|hpss|demucs
    demucs_model: str = Form("htdemucs"),
    demucs_device: str = Form("auto"),  # auto|cpu|cuda
    demucs_chunk: float | None = Form(None),
):
    # Save upload to temp
    suffix = f".{file.filename.split('.')[-1].lower()}" if file.filename else ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        temp_path = tmp.name

    try:
        ap = AudioProcessor()
        y, sr = ap.load_audio(temp_path, target_sr=22050, mono=True)
        fe = FeatureExtractor()
        features = fe.extract_features(y, sr)
        if essentia:
            try:
                ess = compute_essentia_metrics(y, sr)
                if ess:
                    features.update(ess)
            except Exception:
                pass
        # Chords
        chords_list = []
        if chord_backend == 'chordino':
            try:
                chords_list = detect_chords_chordino(temp_path)
            except Exception:
                chords_list = []
        if chords_list:
            features['chords'] = chords_list
            # cannot easily compute progression without mapping to DetectedChord here; keep as is
        else:
            chords = fe.detect_chords(y, sr)
            features['chords'] = [{
                'root': ch.root.name,
                'quality': ch.quality,
                'confidence': ch.confidence,
                'start_time': ch.start_time,
                'duration': ch.duration
            } for ch in chords]
            features['chord_progression'] = FeatureExtractor.summarize_chord_progression(chords)
        # Notes
        notes = []
        if notes_backend == 'basic_pitch':
            try:
                notes = transcribe_basic_pitch(y, sr)
            except Exception:
                notes = []
        if not notes:
            features['notes'] = fe.detect_notes(y, sr)
        else:
            features['notes'] = notes
        if effects:
            try:
                features['effects'] = analyze_effects(y, sr)
            except Exception as e:
                features['effects_error'] = str(e)
        if instruments:
            recog = InstrumentRecognizer()
            features['instruments'] = recog.recognize(y, sr)

        # Pitch
        if pitch_backend == 'torchcrepe':
            try:
                f0 = track_f0_torchcrepe(y, sr)
                if f0:
                    features['pitch_track'] = f0
            except Exception:
                pass
        elif pitch_backend == 'yin':
            try:
                import numpy as _np
                import librosa as _lb
                _yin = _lb.pyin(y=y, fmin=50.0, fmax=1100.0, sr=sr, frame_length=2048, hop_length=256)
                if isinstance(_yin, tuple):
                    f0_arr = _yin[0]
                else:
                    f0_arr = _yin
                f0_arr = _np.asarray(f0_arr)
                n = int(f0_arr.shape[0])
                times = _np.arange(n) * (256.0 / float(sr))
                features['pitch_track'] = {
                    'times': times.tolist(),
                    'f0_hz': _np.nan_to_num(f0_arr, nan=0.0).tolist(),
                    'sample_rate': sr,
                    'hop_length': 256
                }
            except Exception:
                pass

        # Separation
        if separate and separate != 'none':
            try:
                if separate == 'hpss':
                    stems = separate_hpss(y)
                    if stems:
                        features['stems'] = [k for k in stems.keys() if k != 'sample_rate']
                elif separate == 'demucs':
                    stems = separate_demucs(temp_path, model_name=demucs_model, device=demucs_device, chunk_seconds=demucs_chunk)
                    if stems:
                        features['stems'] = [k for k in stems.keys() if k != 'sample_rate']
            except Exception:
                pass
        return JSONResponse(_to_builtin(features))
    finally:
        try:
            os.unlink(temp_path)
        except Exception:
            pass


@app.post("/analyze-youtube")
async def analyze_youtube(
    url: str = Form(...),
    effects: bool = Form(False),
    instruments: bool = Form(False),
    essentia: bool = Form(False),
    chord_backend: str = Form("simple"),
    pitch_backend: str = Form("yin"),
    notes_backend: str = Form("librosa"),
    separate: str = Form("none"),
    keep_audio: bool = Form(False),
):
    """
    Analyze audio from a YouTube URL.
    
    Downloads the audio, runs analysis, and returns features + video metadata.
    """
    try:
        from ..audio_analyzer.youtube_ingestion import YouTubeIngestion
    except ImportError:
        return JSONResponse(
            {"error": "yt-dlp is required. Install with: pip install yt-dlp"},
            status_code=500
        )
    
    temp_dir = tempfile.mkdtemp(prefix="yt_analyze_")
    audio_path = None
    
    try:
        # Download audio from YouTube
        yt = YouTubeIngestion(output_dir=temp_dir, keep_files=True)
        audio_path, video_info = yt.download_audio(url)
        
        # Run analysis
        ap = AudioProcessor()
        y, sr = ap.load_audio(audio_path, target_sr=22050, mono=True)
        fe = FeatureExtractor()
        features = fe.extract_features(y, sr)
        
        # Add video metadata
        features['youtube'] = {
            'id': video_info.get('id', ''),
            'title': video_info.get('title', 'Unknown'),
            'duration': video_info.get('duration', 0),
            'uploader': video_info.get('uploader', 'Unknown'),
            'url': url,
        }
        
        if essentia:
            try:
                ess = compute_essentia_metrics(y, sr)
                if ess:
                    features.update(ess)
            except Exception:
                pass
        
        # Chords
        chords_list = []
        if chord_backend == 'chordino':
            try:
                chords_list = detect_chords_chordino(audio_path)
            except Exception:
                chords_list = []
        if chords_list:
            features['chords'] = chords_list
        else:
            chords = fe.detect_chords(y, sr)
            features['chords'] = [{
                'root': ch.root.name,
                'quality': ch.quality,
                'confidence': ch.confidence,
                'start_time': ch.start_time,
                'duration': ch.duration
            } for ch in chords]
            features['chord_progression'] = FeatureExtractor.summarize_chord_progression(chords)
        
        # Notes
        notes = []
        if notes_backend == 'basic_pitch':
            try:
                notes = transcribe_basic_pitch(y, sr)
            except Exception:
                notes = []
        if not notes:
            features['notes'] = fe.detect_notes(y, sr)
        else:
            features['notes'] = notes
        
        if effects:
            try:
                features['effects'] = analyze_effects(y, sr)
            except Exception as e:
                features['effects_error'] = str(e)
        
        if instruments:
            recog = InstrumentRecognizer()
            features['instruments'] = recog.recognize(y, sr)
        
        # Pitch tracking
        if pitch_backend == 'torchcrepe':
            try:
                f0 = track_f0_torchcrepe(y, sr)
                if f0:
                    features['pitch_track'] = f0
            except Exception:
                pass
        elif pitch_backend == 'yin':
            try:
                import numpy as _np
                import librosa as _lb
                _yin = _lb.pyin(y=y, fmin=50.0, fmax=1100.0, sr=sr, frame_length=2048, hop_length=256)
                if isinstance(_yin, tuple):
                    f0_arr = _yin[0]
                else:
                    f0_arr = _yin
                f0_arr = _np.asarray(f0_arr)
                n = int(f0_arr.shape[0])
                times = _np.arange(n) * (256.0 / float(sr))
                features['pitch_track'] = {
                    'times': times.tolist(),
                    'f0_hz': _np.nan_to_num(f0_arr, nan=0.0).tolist(),
                    'sample_rate': sr,
                    'hop_length': 256
                }
            except Exception:
                pass
        
        # Separation
        if separate and separate != 'none':
            try:
                if separate == 'hpss':
                    stems = separate_hpss(y)
                    if stems:
                        features['stems'] = [k for k in stems.keys() if k != 'sample_rate']
                elif separate == 'demucs':
                    stems = separate_demucs(audio_path, model_name='htdemucs')
                    if stems:
                        features['stems'] = [k for k in stems.keys() if k != 'sample_rate']
            except Exception:
                pass
        
        return JSONResponse(_to_builtin(features))
        
    except Exception as e:
        return JSONResponse(
            {"error": f"Failed to analyze YouTube video: {str(e)}"},
            status_code=500
        )
    finally:
        # Cleanup
        if not keep_audio:
            try:
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass
