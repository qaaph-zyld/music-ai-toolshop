import os
import io
import zipfile
import json
import tempfile
from pathlib import Path

import numpy as np
import librosa
import streamlit as st
import altair as alt
import pandas as pd
import matplotlib.pyplot as plt
import librosa.display as ld

# Ensure we can import the local package
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from audio_analyzer.audio_processor import AudioProcessor
from audio_analyzer.feature_extractor import FeatureExtractor, DetectedChord, NoteName
from audio_analyzer.visualizer import AudioVisualizer
from audio_analyzer.effects_analyzer import analyze_effects
from audio_analyzer.source_separation import separate_hpss, separate_spleeter, export_stems
from audio_analyzer.instrument_recognizer import InstrumentRecognizer
from audio_analyzer.backends.chordino import detect_chords_chordino
from audio_analyzer.backends.pitch_torchcrepe import track_f0_torchcrepe
from audio_analyzer.backends.demucs_backend import separate_demucs
from audio_analyzer.backends.essentia_metrics import compute_essentia_metrics
from audio_analyzer.backends.basic_pitch_backend import transcribe_basic_pitch
from audio_analyzer.youtube_ingestion import YouTubeIngestion

st.set_page_config(page_title="WAV Reverse Engineering Tool", layout="wide")
st.title("WAV Reverse Engineering Tool")
st.write("Analyze and reverse engineer WAV audio tracks: chords, tempo, key, instruments, effects, and stems.")


def _to_builtin(obj):
    if isinstance(obj, (np.floating, np.integer, np.bool_)):
        return obj.item()
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, list):
        return [_to_builtin(x) for x in obj]
    if isinstance(obj, tuple):
        return tuple(_to_builtin(x) for x in obj)
    if isinstance(obj, dict):
        return {k: _to_builtin(v) for k, v in obj.items()}
    return obj

uploaded_file = st.file_uploader("Upload an audio file (WAV/MP3)", type=["wav", "mp3", "flac", "ogg"])
youtube_url = st.text_input("Or paste a YouTube URL", "")

col1, col2, col3 = st.columns(3)
with col1:
    run_effects = st.checkbox("Advanced Effects", value=True)
with col2:
    run_instruments = st.checkbox("Instrument Recognition", value=True)
with col3:
    separation_method = st.selectbox(
        "Source Separation",
        ["none", "hpss", "spleeter2", "spleeter4", "spleeter5", "demucs"],
        index=1
    )

col4, col5, col6 = st.columns(3)
with col4:
    chord_backend = st.selectbox("Chord Backend", ["simple", "chordino"], index=0)
with col5:
    pitch_backend = st.selectbox("Pitch Backend", ["yin", "torchcrepe"], index=0)
with col6:
    use_essentia = st.checkbox("Essentia metrics", value=False)

# Notes backend selector
notes_backend = st.selectbox("Notes Backend", ["librosa", "basic_pitch"], index=0)
demucs_model = st.selectbox("Demucs Model", ["htdemucs", "htdemucs_ft", "hdemucs_mmi", "htdemucs_6s"], index=0)
demucs_device = st.selectbox("Demucs Device", ["auto", "cpu", "cuda"], index=0)
demucs_chunk = st.number_input("Demucs chunk seconds (0 = full)", min_value=0.0, max_value=120.0, value=0.0, step=1.0)

analyze_btn = st.button("Analyze")

if analyze_btn and (uploaded_file or youtube_url.strip()):
    with st.spinner("Processing audio..."):
        temp_path = None
        audio_bytes = None
        video_info = None

        if uploaded_file:
            suffix = f".{uploaded_file.name.split('.')[-1].lower()}"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(uploaded_file.read())
                temp_path = tmp.name
            try:
                audio_bytes = Path(temp_path).read_bytes()
            except Exception:
                pass
        else:
            url = youtube_url.strip()
            try:
                yt = YouTubeIngestion(output_dir=tempfile.gettempdir(), keep_files=True)
                temp_path, video_info = yt.download_audio(url)
                try:
                    audio_bytes = Path(temp_path).read_bytes()
                except Exception:
                    pass
            except Exception as e:
                st.error(f"Failed to download or process YouTube URL: {e}")
                temp_path = None

        if not temp_path:
            st.stop()

        if audio_bytes:
            st.audio(audio_bytes)

        if video_info:
            st.subheader("YouTube Metadata")
            vcols = st.columns(2)
            vcols[0].write(f"Title: {video_info.get('title', 'Unknown')}")
            vcols[0].write(f"Uploader: {video_info.get('uploader', 'Unknown')}")
            vcols[1].write(f"Duration: {video_info.get('duration', 0)} s")
            views = video_info.get('view_count')
            if views is not None:
                vcols[1].write(f"Views: {views}")

        ap = AudioProcessor()
        audio, sr = ap.load_audio(temp_path, target_sr=22050, mono=True)

        fe = FeatureExtractor()
        features = fe.extract_features(audio, sr)
        if video_info:
            features['youtube'] = video_info
        if use_essentia:
            try:
                ess = compute_essentia_metrics(audio, sr)
                if ess:
                    features.update(ess)
            except Exception:
                pass

        st.subheader("Key Metrics")
        km_cols = st.columns(4)
        km_cols[0].metric("Tempo (BPM)", f"{features.get('tempo', 0):.1f}")
        key_display = f"{features.get('essentia_key', features.get('key','?'))} {features.get('essentia_mode', features.get('mode',''))}".strip()
        km_cols[1].metric("Key", key_display)
        km_cols[2].metric("Duration (s)", f"{features.get('duration', 0):.2f}")
        km_cols[3].metric("RMS", f"{features.get('rms_energy', 0):.4f}")

        st.subheader("Chords and Notes")
        chords_for_summary = []
        if chord_backend == 'chordino':
            chordino_chords = detect_chords_chordino(temp_path)
            simple_chords = fe.detect_chords(audio, sr)
            features['chords_chordino'] = chordino_chords
            features['chords_simple'] = [{
                'root': ch.root.name,
                'quality': ch.quality,
                'confidence': ch.confidence,
                'start_time': ch.start_time,
                'duration': ch.duration
            } for ch in simple_chords]
            st.write("Chordino vs Simple (first 20 rows)")
            c1, c2 = st.columns(2)
            with c1:
                st.caption("Chordino")
                st.dataframe(pd.DataFrame(chordino_chords)[:20])
            with c2:
                st.caption("Simple")
                st.dataframe(pd.DataFrame(features['chords_simple'])[:20])
            # Choose Chordino if available for progression; otherwise simple
            if chordino_chords:
                # Convert to DetectedChord for summarization
                note_names = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
                for ch in chordino_chords:
                    try:
                        idx = note_names.index(ch['root'])
                    except ValueError:
                        continue
                    chords_for_summary.append(DetectedChord(
                        root=NoteName(idx),
                        quality='min' if ch.get('quality','maj') == 'min' else 'maj',
                        confidence=float(ch.get('confidence', 0.0)),
                        start_time=float(ch.get('start_time', 0.0)),
                        duration=float(ch.get('duration', 0.0))
                    ))
                features['chords'] = chordino_chords
            else:
                features['chords'] = features['chords_simple']
                chords_for_summary = simple_chords
        else:
            chords = fe.detect_chords(audio, sr)
            features['chords'] = [{
                'root': ch.root.name,
                'quality': ch.quality,
                'confidence': ch.confidence,
                'start_time': ch.start_time,
                'duration': ch.duration
            } for ch in chords]
            chords_for_summary = chords
        progression = FeatureExtractor.summarize_chord_progression(chords_for_summary)
        features['chord_progression'] = progression
        st.write("Chord progression (condensed):")
        st.dataframe(progression)

        notes = []
        if notes_backend == 'basic_pitch':
            try:
                notes = transcribe_basic_pitch(audio, sr)
            except Exception:
                notes = []
        if not notes:
            notes = fe.detect_notes(audio, sr)
        features['notes'] = notes
        with st.expander("Detected notes"):
            st.dataframe(notes)

        if run_effects:
            st.subheader("Effects Analysis")
            try:
                eff = analyze_effects(audio, sr)
                features['effects'] = eff
                st.json(eff)
            except Exception as e:
                st.warning(f"Effects analysis failed: {e}")
                features['effects_error'] = str(e)

        if run_instruments:
            st.subheader("Instrument Recognition")
            recog = InstrumentRecognizer()
            inst = recog.recognize(audio, sr)
            features['instruments'] = inst
            st.table(inst)

        # Optional pitch tracking for visualization
        if pitch_backend == 'torchcrepe':
            try:
                f0 = track_f0_torchcrepe(audio, sr)
                if f0:
                    features['pitch_track'] = f0
            except Exception:
                pass
        elif pitch_backend == 'yin':
            try:
                _yin = librosa.pyin(
                    y=audio, fmin=50.0, fmax=1100.0, sr=sr, frame_length=2048, hop_length=256
                )
                if isinstance(_yin, tuple):
                    f0 = _yin[0]
                else:
                    f0 = _yin
                f0 = np.asarray(f0)
                n = int(f0.shape[0])
                times = np.arange(n) * (256.0 / float(sr))
                features['pitch_track'] = {
                    'times': times.tolist(),
                    'f0_hz': np.nan_to_num(f0, nan=0.0).tolist(),
                    'sample_rate': sr,
                    'hop_length': 256
                }
            except Exception:
                pass

        # Separation
        stems_paths = None
        if separation_method != 'none':
            st.subheader("Source Separation")
            if separation_method == 'hpss':
                stems = separate_hpss(audio)
                stems_sr = sr
            elif separation_method == 'demucs':
                stems = separate_demucs(temp_path, model_name=demucs_model, device=demucs_device, chunk_seconds=(demucs_chunk or None)) or {}
                stems_sr = stems.get('sample_rate', sr)
            else:
                try:
                    stems_count = int(separation_method.replace('spleeter', ''))
                except Exception:
                    stems_count = 2
                stems = separate_spleeter(temp_path, stems=stems_count) or {}
                stems_sr = stems.get('sample_rate', sr)
            if stems:
                features['stems'] = [k for k in stems.keys() if k != 'sample_rate']
                stems_dir = os.path.join(tempfile.gettempdir(), 'wav_re_separation')
                stems_paths = export_stems(stems, stems_sr, stems_dir, prefix=Path(temp_path).stem)
                features['stems_paths'] = stems_paths
                st.write("Exported stems:")
                for name, path in stems_paths.items():
                    st.write(f"- {name}: {path}")
                # Offer zipped stems download
                try:
                    buf = io.BytesIO()
                    with zipfile.ZipFile(buf, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                        for name, path in stems_paths.items():
                            if isinstance(path, str) and os.path.isfile(path):
                                zf.write(path, arcname=os.path.basename(path))
                    st.download_button("Download stems.zip", data=buf.getvalue(), file_name="stems.zip", mime="application/zip")
                except Exception:
                    pass
            else:
                st.info("Spleeter not available or separation failed; try HPSS.")

        # Visualizations
        st.subheader("Visualizations")
        vis_dir = os.path.join(tempfile.gettempdir(), 'wav_re_vis')
        os.makedirs(vis_dir, exist_ok=True)
        vis = AudioVisualizer()
        report_paths = vis.generate_analysis_report(audio, sr, output_dir=vis_dir, prefix=Path(temp_path).stem)
        cols = st.columns(2)
        cols[0].image(report_paths['waveform'], caption='Waveform', use_container_width=True)
        cols[1].image(report_paths['spectrogram'], caption='Spectrogram', use_container_width=True)
        cols = st.columns(2)
        cols[0].image(report_paths['mel_spectrogram'], caption='Mel Spectrogram', use_container_width=True)
        cols[1].image(report_paths['chroma'], caption='Chroma', use_container_width=True)
        st.image(report_paths['beat_tracking'], caption='Beat Tracking', use_container_width=True)
        st.image(report_paths['pitch_tracking'], caption='Pitch Tracking (YIN)', use_container_width=True)
        if features.get('pitch_track'):
            try:
                df = pd.DataFrame({
                    'time_s': features['pitch_track'].get('times', []),
                    'f0_hz': features['pitch_track'].get('f0_hz', [])
                })
                chart = alt.Chart(df).mark_line().encode(x='time_s:Q', y='f0_hz:Q').properties(height=200)
                st.altair_chart(chart, use_container_width=True)
            except Exception:
                pass

        if features.get('pitch_track'):
            try:
                S = librosa.feature.melspectrogram(y=audio, sr=sr, n_mels=128, hop_length=256)
                Sdb = librosa.power_to_db(S, ref=np.max)
                fig, ax = plt.subplots(figsize=(8, 3))
                ld.specshow(Sdb, x_axis='time', y_axis='mel', sr=sr, hop_length=256, ax=ax)
                t = np.asarray(features['pitch_track'].get('times', []), dtype=float)
                f0 = np.asarray(features['pitch_track'].get('f0_hz', []), dtype=float)
                f0 = np.where(np.asarray(f0) > 0, f0, np.nan)
                ax.plot(t, f0, color='w', linewidth=1.0, alpha=0.9)
                ax.set_title('Mel Spectrogram with Pitch Track')
                st.pyplot(fig, clear_figure=True)
            except Exception:
                pass

        # Download JSON
        st.subheader("Download Results")
        json_bytes = json.dumps(_to_builtin(features), indent=2).encode('utf-8')
        st.download_button("Download analysis.json", data=json_bytes, file_name="analysis.json", mime="application/json")

        # Optional evaluation (beats/chords)
        st.subheader("Evaluation (optional)")
        col_e1, col_e2 = st.columns(2)
        with col_e1:
            beat_ref = st.file_uploader("Reference beat times (.txt, one time per line)", type=["txt"], key="beatref")
            if beat_ref is not None:
                try:
                    txt = beat_ref.read().decode('utf-8', errors='ignore')
                    ref_times = [float(x.strip()) for x in txt.splitlines() if x.strip()]
                    from evaluation.harness import evaluate_beats
                    est_times = features.get('beat_times', [])
                    scores = evaluate_beats(ref_times, est_times)
                    if scores:
                        st.json(scores)
                    else:
                        st.info("No evaluation scores available (mir_eval missing or empty inputs).")
                except Exception as _e:
                    st.warning(f"Beat evaluation failed: {_e}")
        with col_e2:
            chord_ref = st.file_uploader("Reference chords CSV (start_time,duration,root,quality)", type=["csv"], key="chordref")
            if chord_ref is not None:
                try:
                    dfc = pd.read_csv(chord_ref)
                    cols_req = {'start_time','duration','root','quality'}
                    if cols_req.issubset(set(map(str, dfc.columns))):
                        ref = dfc[list(cols_req)].to_dict(orient='records')
                        from evaluation.harness import evaluate_chords
                        est = features.get('chords', [])
                        scores = evaluate_chords(ref, est)
                        if scores:
                            st.json(scores)
                        else:
                            st.info("No evaluation scores available (mir_eval missing or empty inputs).")
                    else:
                        st.info("CSV must include columns: start_time,duration,root,quality")
                except Exception as _e:
                    st.warning(f"Chord evaluation failed: {_e}")

        # Cleanup temp file left on disk
        # (Keep for reproducibility during session)
