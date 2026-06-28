"""
Feature extraction module for analyzing audio and extracting musical features.
"""

import numpy as np
import librosa
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

class NoteName(Enum):
    C = 0
    C_SHARP = 1
    D = 2
    D_SHARP = 3
    E = 4
    F = 5
    F_SHARP = 6
    G = 7
    G_SHARP = 8
    A = 9
    A_SHARP = 10
    B = 11

@dataclass
class DetectedChord:
    root: NoteName
    quality: str  # 'maj', 'min', 'dim', 'aug', etc.
    confidence: float
    start_time: float
    duration: float

class FeatureExtractor:
    """
    Extracts musical and acoustic features from audio data.
    """
    
    @staticmethod
    def extract_features(audio_data: np.ndarray, 
                        sample_rate: int,
                        hop_length: int = 512,
                        n_fft: int = 2048) -> Dict[str, Any]:
        """
        Extract a comprehensive set of audio features.
        
        Args:
            audio_data: Input audio data
            sample_rate: Sample rate in Hz
            hop_length: Number of samples between frames
            n_fft: FFT window size
            
        Returns:
            Dictionary containing extracted features
        """
        features = {}
        
        # Basic features
        features.update(FeatureExtractor._extract_basic_features(audio_data, sample_rate))
        
        # Spectral features
        features.update(FeatureExtractor._extract_spectral_features(
            audio_data, sample_rate, hop_length, n_fft))
            
        # Rhythmic features
        features.update(FeatureExtractor._extract_rhythmic_features(
            audio_data, sample_rate, hop_length))
            
        # Harmonic features
        features.update(FeatureExtractor._extract_harmonic_features(
            audio_data, sample_rate))
            
        return features
    
    @staticmethod
    def _extract_basic_features(audio_data: np.ndarray, 
                              sample_rate: int) -> Dict[str, Any]:
        """Extract basic audio features."""
        return {
            'duration': librosa.get_duration(y=audio_data, sr=sample_rate),
            'sample_rate': sample_rate,
            'samples': len(audio_data),
            'rms_energy': np.sqrt(np.mean(audio_data**2)),
            'zero_crossing_rate': np.mean(librosa.feature.zero_crossing_rate(audio_data)[0])
        }
    
    @staticmethod
    def _extract_spectral_features(audio_data: np.ndarray,
                                 sample_rate: int,
                                 hop_length: int,
                                 n_fft: int) -> Dict[str, Any]:
        """Extract spectral features."""
        # Compute spectrogram
        S = np.abs(librosa.stft(audio_data, n_fft=n_fft, hop_length=hop_length))
        
        # Spectral centroid and bandwidth
        spectral_centroid = librosa.feature.spectral_centroid(
            y=audio_data, sr=sample_rate, n_fft=n_fft, hop_length=hop_length)
        spectral_bandwidth = librosa.feature.spectral_bandwidth(
            y=audio_data, sr=sample_rate, n_fft=n_fft, hop_length=hop_length)
        
        # Spectral contrast
        spectral_contrast = librosa.feature.spectral_contrast(
            y=audio_data, sr=sample_rate, n_fft=n_fft, hop_length=hop_length)
        
        # MFCCs
        mfcc = librosa.feature.mfcc(
            y=audio_data, sr=sample_rate, n_mfcc=20, n_fft=n_fft, hop_length=hop_length)
        
        return {
            'spectral_centroid': np.mean(spectral_centroid[0]),
            'spectral_bandwidth': np.mean(spectral_bandwidth[0]),
            'spectral_contrast': np.mean(spectral_contrast, axis=1).tolist(),
            'mfcc': np.mean(mfcc, axis=1).tolist(),
            'spectral_rolloff': np.mean(librosa.feature.spectral_rolloff(
                y=audio_data, sr=sample_rate, n_fft=n_fft, hop_length=hop_length)[0])
        }
    
    @staticmethod
    def _extract_rhythmic_features(audio_data: np.ndarray,
                                 sample_rate: int,
                                 hop_length: int) -> Dict[str, Any]:
        """Extract rhythmic features like tempo and beat information."""
        # Estimate tempo and beat frames
        tempo, beat_frames = librosa.beat.beat_track(
            y=audio_data, sr=sample_rate, hop_length=hop_length)
        
        # Get onset envelope
        onset_env = librosa.onset.onset_strength(
            y=audio_data, sr=sample_rate, hop_length=hop_length)
        
        # Get onset times
        onset_times = librosa.times_like(onset_env, sr=sample_rate, hop_length=hop_length)
        
        beat_times = librosa.frames_to_time(beat_frames, sr=sample_rate, hop_length=hop_length)
        # Robust scalar coercion for numpy 2.x / librosa 0.11 returns
        try:
            tempo_scalar = float(np.asarray(tempo).reshape(-1)[0])
        except Exception:
            tempo_scalar = float(tempo) if hasattr(tempo, "__float__") else 0.0
        return {
            'tempo': tempo_scalar,
            'beat_count': len(beat_frames),
            'beats_per_second': len(beat_frames) / (len(audio_data) / sample_rate),
            'onset_strength': float(np.asarray(np.mean(onset_env)).reshape(-1)[0]),
            'onset_times': onset_times.tolist(),
            'beat_times': beat_times.tolist()
        }
    
    @staticmethod
    def _extract_harmonic_features(audio_data: np.ndarray,
                                 sample_rate: int) -> Dict[str, Any]:
        """Extract harmonic and pitch-related features."""
        # Harmonic and percussive separation
        y_harmonic, y_percussive = librosa.effects.hpss(audio_data)
        
        # Estimate tuning
        tuning = librosa.estimate_tuning(y=audio_data, sr=sample_rate)
        
        # Chroma features
        chroma = librosa.feature.chroma_cqt(y=audio_data, sr=sample_rate)
        
        # Estimate key and mode
        key, mode = FeatureExtractor._estimate_key(audio_data, sample_rate)
        
        return {
            'harmonic_ratio': np.mean(y_harmonic**2) / (np.mean(y_harmonic**2) + np.mean(y_percussive**2) + 1e-10),
            'tuning_offset': float(tuning),
            'chroma': np.mean(chroma, axis=1).tolist(),
            'key': key,
            'mode': mode,
            'pitch_centroid': float(np.mean(librosa.feature.spectral_centroid(
                y=y_harmonic, sr=sample_rate)))
        }
    
    @staticmethod
    def _estimate_key(audio_data: np.ndarray, sample_rate: int) -> Tuple[str, str]:
        """Estimate the musical key and mode of the audio."""
        # Get chroma features
        chroma = librosa.feature.chroma_cqt(y=audio_data, sr=sample_rate)
        
        # Get the most prominent chroma
        chroma_vals = np.mean(chroma, axis=1)
        key_idx = np.argmax(chroma_vals)
        
        # Simple key estimation (can be improved with more sophisticated methods)
        keys = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        
        # Simple mode estimation (major/minor)
        # This is a basic estimation - a more sophisticated approach would analyze the full harmonic content
        mode = 'major' if chroma_vals[key_idx] > 0.5 else 'minor'
        
        return keys[key_idx], mode
    
    @staticmethod
    def detect_chords(audio_data: np.ndarray, 
                     sample_rate: int,
                     hop_length: int = 512) -> List[DetectedChord]:
        """
        Detect chords in the audio.
        
        Args:
            audio_data: Input audio data
            sample_rate: Sample rate in Hz
            hop_length: Number of samples between frames
            
        Returns:
            List of detected chords with timings and confidences
        """
        # This is a simplified implementation - a full chord detection system would be more complex
        chroma = librosa.feature.chroma_cqt(y=audio_data, sr=sample_rate, hop_length=hop_length)
        
        # Simple chord template matching (in a real implementation, this would be more sophisticated)
        chords = []
        frame_times = librosa.times_like(chroma[0], sr=sample_rate, hop_length=hop_length)
        
        for i in range(chroma.shape[1]):
            # Find the most prominent chroma (simplified)
            chroma_frame = chroma[:, i]
            root_idx = np.argmax(chroma_frame)
            
            # Simple chord quality detection (major/minor)
            third_idx = (root_idx + 4) % 12  # Major third
            fifth_idx = (root_idx + 7) % 12  # Perfect fifth
            
            third_present = chroma_frame[third_idx] > 0.5
            fifth_present = chroma_frame[fifth_idx] > 0.5
            
            if third_present and fifth_present:
                # Check if minor third is also present (suggests a more complex chord)
                minor_third_idx = (root_idx + 3) % 12
                if chroma_frame[minor_third_idx] > 0.5:
                    quality = 'min'  # Could be more specific (e.g., m7, m9, etc.)
                else:
                    quality = 'maj'  # Could be more specific (e.g., maj7, 6, etc.)
                
                # Calculate confidence (simplified)
                confidence = np.mean([
                    chroma_frame[root_idx],
                    chroma_frame[third_idx],
                    chroma_frame[fifth_idx]
                ])
                
                # Add chord to list
                chord = DetectedChord(
                    root=NoteName(root_idx),
                    quality=quality,
                    confidence=float(confidence),
                    start_time=float(frame_times[i]),
                    duration=float(hop_length / sample_rate)
                )
                chords.append(chord)
        
        return chords
    
    @staticmethod
    def detect_notes(audio_data: np.ndarray, 
                    sample_rate: int,
                    fmin: float = 65.41,  # C2
                    fmax: float = 2093.0,  # C7
                    threshold: float = 0.5) -> List[Dict[str, float]]:
        """
        Detect individual notes in the audio.
        
        Args:
            audio_data: Input audio data
            sample_rate: Sample rate in Hz
            fmin: Minimum frequency to detect (Hz)
            fmax: Maximum frequency to detect (Hz)
            threshold: Detection threshold (0-1)
            
        Returns:
            List of detected notes with pitch, start time, duration, and confidence
        """
        # Use librosa's onset detection
        onset_frames = librosa.onset.onset_detect(
            y=audio_data, sr=sample_rate, units='frames')
        onset_times = librosa.frames_to_time(
            onset_frames, sr=sample_rate)
        
        # Estimate pitch for each onset
        notes = []
        for i, time in enumerate(onset_times):
            # Get a segment around the onset
            start_sample = int(time * sample_rate)
            end_sample = min(start_sample + 2048, len(audio_data))
            
            if end_sample <= start_sample:
                continue
                
            segment = audio_data[start_sample:end_sample]
            
            # Estimate pitch using YIN algorithm
            f0 = librosa.yin(
                y=segment,
                fmin=fmin,
                fmax=fmax,
                sr=sample_rate
            )
            
            if len(f0) > 0 and not np.isnan(f0[0]) and f0[0] > 0:
                # Convert frequency to note name and octave
                note_num = 12 * (np.log2(f0[0] / 440.0)) + 69
                note_name = librosa.midi_to_note(int(round(note_num)))
                
                # Calculate confidence (simplified)
                confidence = np.mean(np.abs(segment)) * 2  # Simple energy-based confidence
                
                # Add note to list
                notes.append({
                    'pitch': note_name,
                    'frequency': float(f0[0]),
                    'start_time': float(time),
                    'duration': 0.1,  # Default duration, could be improved
                    'confidence': float(np.clip(confidence, 0, 1))
                })
        
        return notes

    @staticmethod
    def summarize_chord_progression(chords: List[DetectedChord], min_duration: float = 0.25) -> List[Dict[str, Any]]:
        """Summarize a list of DetectedChord into a compact chord progression."""
        if not chords:
            return []
        keys = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        entries: List[Dict[str, Any]] = []
        prev = None
        for ch in sorted(chords, key=lambda c: c.start_time):
            name = f"{keys[ch.root.value]}{'' if ch.quality=='maj' else 'm'}"
            if prev and prev['name'] == name:
                prev['duration'] += ch.duration
                prev['confidence'] = max(prev['confidence'], ch.confidence)
                prev['end_time'] = ch.start_time + ch.duration
            else:
                prev = {
                    'name': name,
                    'start_time': ch.start_time,
                    'duration': ch.duration,
                    'end_time': ch.start_time + ch.duration,
                    'confidence': ch.confidence
                }
                entries.append(prev)
        entries = [e for e in entries if e['duration'] >= min_duration]
        return entries
