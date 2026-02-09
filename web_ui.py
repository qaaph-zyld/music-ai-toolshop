#!/usr/bin/env python3
"""
Music AI Toolshop — Web UI
Upload audio files and get instant BPM, key, and spectral analysis.
Built with Streamlit + librosa.
"""

import streamlit as st
import numpy as np
import tempfile
import json
from pathlib import Path

try:
    import librosa
    import librosa.display
except ImportError:
    st.error("librosa is required. Install with: pip install librosa numpy")
    st.stop()

try:
    import plotly.graph_objects as go
    import plotly.express as px
except ImportError:
    st.error("plotly is required. Install with: pip install plotly")
    st.stop()

# ---------------------------------------------------------------------------
# Analysis functions (self-contained, no adapter imports needed for portability)
# ---------------------------------------------------------------------------

KEYS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
KEY_COLORS = {
    "C": "#FF6B6B", "C#": "#FF8E72", "D": "#FFA94D", "D#": "#FFD93D",
    "E": "#6BCB77", "F": "#4D96FF", "F#": "#6C63FF", "G": "#9B59B6",
    "G#": "#E84393", "A": "#00B894", "A#": "#0984E3", "B": "#6C5CE7"
}


def analyze_audio(y: np.ndarray, sr: int) -> dict:
    """Full analysis of audio signal."""
    duration = librosa.get_duration(y=y, sr=sr)

    # BPM
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    bpm = float(tempo)

    # Key via chroma
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    chroma_mean = np.mean(chroma, axis=1)
    key_idx = int(np.argmax(chroma_mean))
    key = KEYS[key_idx]
    mode = "major" if chroma_mean[key_idx] > 0.5 else "minor"

    # Spectral features
    spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    spectral_bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)[0]
    spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
    zero_crossings = librosa.feature.zero_crossing_rate(y)[0]

    # RMS energy
    rms = librosa.feature.rms(y=y)[0]

    # Harmonic/percussive
    y_harm, y_perc = librosa.effects.hpss(y)
    harm_energy = float(np.mean(y_harm ** 2))
    perc_energy = float(np.mean(y_perc ** 2))
    harmonic_ratio = harm_energy / (harm_energy + perc_energy + 1e-10)

    # MFCCs for timbre
    mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)

    # Onset strength
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)

    return {
        "bpm": round(bpm, 1),
        "key": key,
        "mode": mode,
        "key_confidence": round(float(chroma_mean[key_idx]), 3),
        "duration_seconds": round(duration, 2),
        "sample_rate": sr,
        "beat_count": len(beat_frames),
        "harmonic_ratio": round(harmonic_ratio, 4),
        "avg_spectral_centroid": round(float(np.mean(spectral_centroid)), 1),
        "avg_spectral_bandwidth": round(float(np.mean(spectral_bandwidth)), 1),
        "avg_rms_energy": round(float(np.mean(rms)), 6),
        # Raw arrays for plotting
        "_chroma": chroma,
        "_chroma_mean": chroma_mean,
        "_spectral_centroid": spectral_centroid,
        "_spectral_bandwidth": spectral_bandwidth,
        "_spectral_rolloff": spectral_rolloff,
        "_rms": rms,
        "_mfccs": mfccs,
        "_onset_env": onset_env,
        "_beat_frames": beat_frames,
        "_y": y,
        "_sr": sr,
    }


# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Music AI Toolshop — Audio Analyzer",
    page_icon="🎵",
    layout="wide",
)

st.markdown("""
<style>
    .block-container { padding-top: 2rem; }
    .main-title { font-size: 2.2rem; font-weight: 800; text-align: center; margin-bottom: 0;
                  background: linear-gradient(135deg, #667eea, #764ba2); -webkit-background-clip: text;
                  -webkit-text-fill-color: transparent; }
    .sub-title { text-align: center; color: #5f6368; font-size: 1.05rem; margin-bottom: 2rem; }
    .result-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;
                   padding: 1.5rem; border-radius: 1rem; text-align: center; }
    .result-card h2 { margin: 0; font-size: 2.5rem; font-weight: 800; }
    .result-card p { margin: 0; font-size: 0.85rem; opacity: 0.85; }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-title">🎵 Music AI Toolshop</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Upload an audio file → get instant BPM, key, and spectral analysis</p>', unsafe_allow_html=True)

# File upload
uploaded = st.file_uploader(
    "Drop your audio file here",
    type=["wav", "mp3", "flac", "ogg", "m4a"],
    help="Supported formats: WAV, MP3, FLAC, OGG, M4A. WAV recommended for best accuracy."
)

if uploaded is not None:
    # Save to temp file
    suffix = Path(uploaded.name).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded.read())
        tmp_path = tmp.name

    st.audio(uploaded, format=f"audio/{suffix.lstrip('.')}")

    with st.spinner("Analyzing audio..."):
        try:
            y, sr = librosa.load(tmp_path, sr=22050, mono=True)
            result = analyze_audio(y, sr)
        except Exception as e:
            st.error(f"Analysis failed: {e}")
            st.stop()

    # --- Results Cards ---
    st.divider()
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("BPM", f"{result['bpm']}")
    with c2:
        st.metric("Key", f"{result['key']} {result['mode']}")
    with c3:
        st.metric("Duration", f"{result['duration_seconds']}s")
    with c4:
        st.metric("Beats", f"{result['beat_count']}")
    with c5:
        st.metric("Harmonic", f"{result['harmonic_ratio']:.0%}")

    st.divider()

    # --- Tabs for different visualizations ---
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🎹 Chroma", "📈 Waveform & Energy", "🔬 Spectral", "🎼 MFCCs", "📋 JSON"])

    times = librosa.times_like(result["_spectral_centroid"], sr=sr)

    with tab1:
        st.subheader("Chromagram — Note Energy Over Time")
        chroma = result["_chroma"]
        fig_chroma = go.Figure(data=go.Heatmap(
            z=chroma, x=np.arange(chroma.shape[1]), y=KEYS,
            colorscale="Viridis", showscale=True
        ))
        fig_chroma.update_layout(
            xaxis_title="Time Frame", yaxis_title="Note",
            height=350, margin=dict(l=40, r=20, t=30, b=40)
        )
        st.plotly_chart(fig_chroma, use_container_width=True)

        # Chroma distribution bar
        st.subheader("Key Distribution")
        chroma_mean = result["_chroma_mean"]
        colors = [KEY_COLORS[k] for k in KEYS]
        fig_keys = go.Figure(data=go.Bar(
            x=KEYS, y=chroma_mean, marker_color=colors
        ))
        fig_keys.update_layout(
            yaxis_title="Average Energy", height=300,
            margin=dict(l=40, r=20, t=30, b=40)
        )
        st.plotly_chart(fig_keys, use_container_width=True)

    with tab2:
        st.subheader("Waveform")
        wave_times = np.linspace(0, result["duration_seconds"], len(y))
        # Downsample for plotting performance
        step = max(1, len(y) // 5000)
        fig_wave = go.Figure(data=go.Scatter(
            x=wave_times[::step], y=y[::step], mode="lines",
            line=dict(color="#667eea", width=0.5)
        ))
        fig_wave.update_layout(
            xaxis_title="Time (s)", yaxis_title="Amplitude",
            height=250, margin=dict(l=40, r=20, t=30, b=40)
        )
        st.plotly_chart(fig_wave, use_container_width=True)

        st.subheader("RMS Energy")
        rms_times = librosa.times_like(result["_rms"], sr=sr)
        fig_rms = go.Figure(data=go.Scatter(
            x=rms_times, y=result["_rms"], mode="lines",
            fill="tozeroy", line=dict(color="#764ba2")
        ))
        fig_rms.update_layout(
            xaxis_title="Time (s)", yaxis_title="RMS Energy",
            height=250, margin=dict(l=40, r=20, t=30, b=40)
        )
        st.plotly_chart(fig_rms, use_container_width=True)

    with tab3:
        st.subheader("Spectral Centroid / Bandwidth / Rolloff")
        fig_spec = go.Figure()
        fig_spec.add_trace(go.Scatter(x=times, y=result["_spectral_centroid"], name="Centroid", line=dict(color="#FF6B6B")))
        fig_spec.add_trace(go.Scatter(x=times, y=result["_spectral_bandwidth"], name="Bandwidth", line=dict(color="#4D96FF")))
        fig_spec.add_trace(go.Scatter(x=times, y=result["_spectral_rolloff"], name="Rolloff", line=dict(color="#6BCB77")))
        fig_spec.update_layout(
            xaxis_title="Time (s)", yaxis_title="Hz",
            height=400, margin=dict(l=40, r=20, t=30, b=40),
            legend=dict(orientation="h", yanchor="bottom", y=1.02)
        )
        st.plotly_chart(fig_spec, use_container_width=True)

    with tab4:
        st.subheader("MFCCs — Timbre Fingerprint")
        mfccs = result["_mfccs"]
        fig_mfcc = go.Figure(data=go.Heatmap(
            z=mfccs, colorscale="RdBu_r", showscale=True
        ))
        fig_mfcc.update_layout(
            xaxis_title="Time Frame", yaxis_title="MFCC Coefficient",
            height=350, margin=dict(l=40, r=20, t=30, b=40)
        )
        st.plotly_chart(fig_mfcc, use_container_width=True)

    with tab5:
        st.subheader("Full Analysis Results (JSON)")
        export = {k: v for k, v in result.items() if not k.startswith("_")}
        export["file"] = uploaded.name
        st.json(export)
        st.download_button(
            "Download JSON",
            data=json.dumps(export, indent=2),
            file_name=f"{Path(uploaded.name).stem}_analysis.json",
            mime="application/json"
        )

    # Suno prompt suggestion
    st.divider()
    st.subheader("🎤 Suno Prompt Suggestion")
    energy_level = "high energy" if result["avg_rms_energy"] > 0.01 else "chill"
    harmonic_desc = "melodic" if result["harmonic_ratio"] > 0.6 else "rhythmic"
    prompt = f"{result['key']} {result['mode']}, {result['bpm']} BPM, {energy_level}, {harmonic_desc}"
    st.code(prompt, language=None)
    st.caption("Use this as a starting point for Suno AI music generation.")

else:
    # Landing state
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("### 🎯 BPM Detection")
        st.markdown("Accurate tempo analysis using beat tracking algorithms.")
    with col2:
        st.markdown("### 🎹 Key Detection")
        st.markdown("Chroma-based key and mode (major/minor) estimation.")
    with col3:
        st.markdown("### 📊 Spectral Analysis")
        st.markdown("Centroid, bandwidth, MFCCs, harmonic ratio, and more.")

    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #9e9e9e; font-size: 0.85rem;">
        <strong>Music AI Toolshop</strong> by <a href="https://nkj-development.netlify.app" style="color: #667eea;">NKJ Development</a>
        · Powered by librosa + Streamlit
        · <a href="https://github.com/qaaph-zyld/music-ai-toolshop" style="color: #667eea;">GitHub</a>
    </div>
    """, unsafe_allow_html=True)
