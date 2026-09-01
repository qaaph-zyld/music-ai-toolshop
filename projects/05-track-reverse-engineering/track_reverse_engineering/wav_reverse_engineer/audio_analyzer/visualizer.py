"""
Visualization module for audio analysis results.
"""

import os
import numpy as np
import matplotlib.pyplot as plt
import librosa.display
from typing import Optional, Tuple, List, Dict, Any
from pathlib import Path

class AudioVisualizer:
    """
    Handles visualization of audio data and analysis results.
    """
    
    @staticmethod
    def plot_waveform(audio_data: np.ndarray,
                     sample_rate: int,
                     title: str = 'Waveform',
                     output_path: Optional[str] = None,
                     show: bool = True) -> None:
        """
        Plot the waveform of the audio signal.
        
        Args:
            audio_data: Input audio data
            sample_rate: Sample rate in Hz
            title: Plot title
            output_path: Path to save the plot (optional)
            show: Whether to display the plot
        """
        plt.figure(figsize=(14, 5))
        librosa.display.waveshow(audio_data, sr=sample_rate)
        plt.title(title)
        plt.xlabel('Time (s)')
        plt.ylabel('Amplitude')
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
        if show:
            plt.show()
        plt.close()
    
    @staticmethod
    def plot_spectrogram(audio_data: np.ndarray,
                        sample_rate: int,
                        hop_length: int = 512,
                        n_fft: int = 2048,
                        title: str = 'Spectrogram',
                        output_path: Optional[str] = None,
                        show: bool = True) -> None:
        """
        Plot the spectrogram of the audio signal.
        
        Args:
            audio_data: Input audio data
            sample_rate: Sample rate in Hz
            hop_length: Number of samples between frames
            n_fft: FFT window size
            title: Plot title
            output_path: Path to save the plot (optional)
            show: Whether to display the plot
        """
        # Compute spectrogram
        D = np.abs(librosa.stft(audio_data, n_fft=n_fft, hop_length=hop_length))
        DB = librosa.amplitude_to_db(D, ref=np.max)
        
        # Plot
        plt.figure(figsize=(14, 5))
        librosa.display.specshow(DB, 
                               sr=sample_rate, 
                               hop_length=hop_length, 
                               x_axis='time', 
                               y_axis='log')
        plt.colorbar(format='%+2.0f dB')
        plt.title(title)
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
        if show:
            plt.show()
        plt.close()
    
    @staticmethod
    def plot_mel_spectrogram(audio_data: np.ndarray,
                           sample_rate: int,
                           hop_length: int = 512,
                           n_fft: int = 2048,
                           n_mels: int = 128,
                           title: str = 'Mel Spectrogram',
                           output_path: Optional[str] = None,
                           show: bool = True) -> None:
        """
        Plot the mel-scaled spectrogram of the audio signal.
        
        Args:
            audio_data: Input audio data
            sample_rate: Sample rate in Hz
            hop_length: Number of samples between frames
            n_fft: FFT window size
            n_mels: Number of mel bands
            title: Plot title
            output_path: Path to save the plot (optional)
            show: Whether to display the plot
        """
        # Compute mel-scaled spectrogram
        S = librosa.feature.melspectrogram(
            y=audio_data, 
            sr=sample_rate, 
            n_fft=n_fft, 
            hop_length=hop_length, 
            n_mels=n_mels
        )
        S_DB = librosa.power_to_db(S, ref=np.max)
        
        # Plot
        plt.figure(figsize=(14, 5))
        librosa.display.specshow(
            S_DB, 
            sr=sample_rate, 
            hop_length=hop_length, 
            x_axis='time', 
            y_axis='mel'
        )
        plt.colorbar(format='%+2.0f dB')
        plt.title(title)
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
        if show:
            plt.show()
        plt.close()
    
    @staticmethod
    def plot_chroma(audio_data: np.ndarray,
                   sample_rate: int,
                   hop_length: int = 512,
                   n_fft: int = 2048,
                   title: str = 'Chroma Feature',
                   output_path: Optional[str] = None,
                   show: bool = True) -> None:
        """
        Plot the chroma feature of the audio signal.
        
        Args:
            audio_data: Input audio data
            sample_rate: Sample rate in Hz
            hop_length: Number of samples between frames
            n_fft: FFT window size
            title: Plot title
            output_path: Path to save the plot (optional)
            show: Whether to display the plot
        """
        # Compute chroma feature
        chroma = librosa.feature.chroma_stft(
            y=audio_data, 
            sr=sample_rate, 
            n_fft=n_fft, 
            hop_length=hop_length
        )
        
        # Plot
        plt.figure(figsize=(14, 5))
        librosa.display.specshow(
            chroma, 
            x_axis='time', 
            y_axis='chroma', 
            hop_length=hop_length,
            cmap='coolwarm'
        )
        plt.colorbar()
        plt.title(title)
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
        if show:
            plt.show()
        plt.close()
    
    @staticmethod
    def plot_beat_tracking(audio_data: np.ndarray,
                          sample_rate: int,
                          hop_length: int = 512,
                          title: str = 'Beat Tracking',
                          output_path: Optional[str] = None,
                          show: bool = True) -> None:
        """
        Plot the beat tracking results.
        
        Args:
            audio_data: Input audio data
            sample_rate: Sample rate in Hz
            hop_length: Number of samples between frames
            title: Plot title
            output_path: Path to save the plot (optional)
            show: Whether to display the plot
        """
        # Compute tempo and beat frames
        tempo, beat_frames = librosa.beat.beat_track(
            y=audio_data, 
            sr=sample_rate, 
            hop_length=hop_length
        )
        # Coerce tempo to a scalar float robustly (handles numpy arrays/0-d arrays)
        try:
            tempo_scalar = float(np.asarray(tempo).reshape(-1)[0])
        except Exception:
            try:
                tempo_scalar = float(tempo)
            except Exception:
                tempo_scalar = 0.0
        
        # Compute onset envelope
        onset_env = librosa.onset.onset_strength(
            y=audio_data, 
            sr=sample_rate, 
            hop_length=hop_length
        )
        
        # Convert frames to time
        times = librosa.times_like(onset_env, sr=sample_rate, hop_length=hop_length)
        
        # Plot
        plt.figure(figsize=(14, 5))
        denom = float(np.max(onset_env)) if np.max(onset_env) > 0 else 1.0
        plt.plot(times, onset_env / denom, label='Onset strength')
        plt.vlines(
            times[beat_frames], 
            0, 1, 
            alpha=0.5, 
            color='r', 
            linestyle='--', 
            label='Beats'
        )
        plt.title(f'Beat Tracking (Tempo: {tempo_scalar:.2f} BPM)')
        plt.xlabel('Time (s)')
        plt.ylabel('Normalized Strength')
        plt.legend()
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
        if show:
            plt.show()
        plt.close()
    
    @staticmethod
    def plot_pitch_tracking(audio_data: np.ndarray,
                           sample_rate: int,
                           fmin: float = 65.41,  # C2
                           fmax: float = 2093.0,  # C7
                           title: str = 'Pitch Tracking',
                           output_path: Optional[str] = None,
                           show: bool = True) -> None:
        """
        Plot the pitch tracking results.
        
        Args:
            audio_data: Input audio data
            sample_rate: Sample rate in Hz
            fmin: Minimum frequency to detect (Hz)
            fmax: Maximum frequency to detect (Hz)
            title: Plot title
            output_path: Path to save the plot (optional)
            show: Whether to display the plot
        """
        # Estimate pitch using YIN
        f0 = librosa.yin(
            y=audio_data, 
            fmin=fmin, 
            fmax=fmax, 
            sr=sample_rate
        )
        
        # Create time array
        times = librosa.times_like(f0, sr=sample_rate)
        
        # Convert to MIDI note numbers
        midi_notes = 12 * (np.log2(f0 / 440.0)) + 69
        
        # Plot
        plt.figure(figsize=(14, 5))
        plt.plot(times, midi_notes, label='Pitch (MIDI note number)')
        plt.title(title)
        plt.xlabel('Time (s)')
        plt.ylabel('MIDI Note Number')
        plt.yticks(
            range(int(np.nanmin(midi_notes)), int(np.nanmax(midi_notes)) + 1, 2)
        )
        plt.legend()
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
        if show:
            plt.show()
        plt.close()
    
    @staticmethod
    def plot_feature_comparison(features: Dict[str, Any],
                              title: str = 'Feature Comparison',
                              output_path: Optional[str] = None,
                              show: bool = True) -> None:
        """
        Plot a comparison of different audio features.
        
        Args:
            features: Dictionary of feature names and their values
            title: Plot title
            output_path: Path to save the plot (optional)
            show: Whether to display the plot
        """
        # Filter out non-numeric features
        numeric_features = {
            k: v for k, v in features.items() 
            if isinstance(v, (int, float, np.number))
        }
        
        if not numeric_features:
            print("No numeric features to plot.")
            return
        
        # Sort features by value for better visualization
        sorted_features = dict(
            sorted(numeric_features.items(), key=lambda x: x[1], reverse=True)
        )
        
        # Plot
        plt.figure(figsize=(12, 6))
        plt.bar(
            range(len(sorted_features)),
            list(sorted_features.values()),
            tick_label=list(sorted_features.keys())
        )
        plt.title(title)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
        if show:
            plt.show()
        plt.close()
    
    @staticmethod
    def generate_analysis_report(audio_data: np.ndarray,
                               sample_rate: int,
                               output_dir: str,
                               prefix: str = 'analysis') -> Dict[str, str]:
        """
        Generate a comprehensive analysis report with multiple visualizations.
        
        Args:
            audio_data: Input audio data
            sample_rate: Sample rate in Hz
            output_dir: Directory to save the report
            prefix: Prefix for output filenames
            
        Returns:
            Dictionary with paths to generated visualizations
        """
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Dictionary to store paths to generated files
        report = {}
        
        # Generate visualizations
        waveform_path = os.path.join(output_dir, f"{prefix}_waveform.png")
        AudioVisualizer.plot_waveform(
            audio_data, sample_rate, 
            title=f'{prefix} - Waveform',
            output_path=waveform_path,
            show=False
        )
        report['waveform'] = waveform_path
        
        spectrogram_path = os.path.join(output_dir, f"{prefix}_spectrogram.png")
        AudioVisualizer.plot_spectrogram(
            audio_data, sample_rate,
            title=f'{prefix} - Spectrogram',
            output_path=spectrogram_path,
            show=False
        )
        report['spectrogram'] = spectrogram_path
        
        mel_path = os.path.join(output_dir, f"{prefix}_mel_spectrogram.png")
        AudioVisualizer.plot_mel_spectrogram(
            audio_data, sample_rate,
            title=f'{prefix} - Mel Spectrogram',
            output_path=mel_path,
            show=False
        )
        report['mel_spectrogram'] = mel_path
        
        chroma_path = os.path.join(output_dir, f"{prefix}_chroma.png")
        AudioVisualizer.plot_chroma(
            audio_data, sample_rate,
            title=f'{prefix} - Chroma Feature',
            output_path=chroma_path,
            show=False
        )
        report['chroma'] = chroma_path
        
        beat_path = os.path.join(output_dir, f"{prefix}_beat_tracking.png")
        AudioVisualizer.plot_beat_tracking(
            audio_data, sample_rate,
            title=f'{prefix} - Beat Tracking',
            output_path=beat_path,
            show=False
        )
        report['beat_tracking'] = beat_path
        
        pitch_path = os.path.join(output_dir, f"{prefix}_pitch_tracking.png")
        AudioVisualizer.plot_pitch_tracking(
            audio_data, sample_rate,
            title=f'{prefix} - Pitch Tracking',
            output_path=pitch_path,
            show=False
        )
        report['pitch_tracking'] = pitch_path
        
        return report
