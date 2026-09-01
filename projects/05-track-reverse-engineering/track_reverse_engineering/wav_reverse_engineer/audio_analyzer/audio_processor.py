"""
Audio processing module for loading and manipulating audio files.
"""

import os
import numpy as np
import librosa
import soundfile as sf
from typing import Tuple, Optional, Dict, Any

class AudioProcessor:
    """
    Handles audio file loading, preprocessing, and basic analysis.
    """
    
    @staticmethod
    def load_audio(file_path: str, 
                  target_sr: int = 22050, 
                  mono: bool = True) -> Tuple[np.ndarray, int]:
        """
        Load an audio file and return the audio data and sample rate.
        
        Args:
            file_path: Path to the audio file
            target_sr: Target sample rate (default: 22050)
            mono: Convert to mono if True
            
        Returns:
            Tuple of (audio_data, sample_rate)
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Audio file not found: {file_path}")
            
        try:
            # Load audio file
            audio, sr = librosa.load(
                file_path,
                sr=target_sr,
                mono=mono,
                res_type='kaiser_fast'
            )
            return audio, sr
            
        except Exception as e:
            raise Exception(f"Error loading audio file {file_path}: {str(e)}")
    
    @staticmethod
    def get_audio_info(audio_data: np.ndarray, sample_rate: int) -> Dict[str, Any]:
        """
        Get basic information about the audio data.
        
        Args:
            audio_data: Audio data array
            sample_rate: Sample rate in Hz
            
        Returns:
            Dictionary containing audio information
        """
        duration = librosa.get_duration(y=audio_data, sr=sample_rate)
        
        return {
            'duration_seconds': duration,
            'sample_rate': sample_rate,
            'channels': 1 if len(audio_data.shape) == 1 else audio_data.shape[0],
            'samples': audio_data.shape[-1],
            'bit_depth': audio_data.dtype.itemsize * 8,
            'rms_energy': np.sqrt(np.mean(audio_data**2)),
            'peak_amplitude': np.max(np.abs(audio_data))
        }
    
    @staticmethod
    def resample_audio(audio_data: np.ndarray, 
                      original_sr: int, 
                      target_sr: int) -> np.ndarray:
        """
        Resample audio data to a target sample rate.
        
        Args:
            audio_data: Input audio data
            original_sr: Original sample rate
            target_sr: Target sample rate
            
        Returns:
            Resampled audio data
        """
        if original_sr == target_sr:
            return audio_data
            
        return librosa.resample(
            y=audio_data,
            orig_sr=original_sr,
            target_sr=target_sr,
            res_type='kaiser_fast'
        )
    
    @staticmethod
    def normalize_audio(audio_data: np.ndarray, target_level: float = -3.0) -> np.ndarray:
        """
        Normalize audio to a target peak level in dB.
        
        Args:
            audio_data: Input audio data
            target_level: Target peak level in dB (default: -3.0)
            
        Returns:
            Normalized audio data
        """
        if len(audio_data) == 0:
            return audio_data
            
        max_sample = np.max(np.abs(audio_data))
        if max_sample == 0:
            return audio_data
            
        # Convert target level from dB to linear scale
        target_linear = 10 ** (target_level / 20.0)
        
        # Calculate scaling factor
        scaling_factor = target_linear / max_sample
        
        # Apply scaling
        return audio_data * scaling_factor

    @staticmethod
    def trim_silence(audio_data: np.ndarray, 
                    top_db: float = 30, 
                    frame_length: int = 2048,
                    hop_length: int = 512) -> np.ndarray:
        """
        Trim leading and trailing silence from audio.
        
        Args:
            audio_data: Input audio data
            top_db: The threshold (in decibels) below reference to consider as silence
            frame_length: Number of samples per analysis frame
            hop_length: Number of samples between frames
            
        Returns:
            Trimmed audio data
        """
        if len(audio_data) == 0:
            return audio_data
            
        # Trim both leading and trailing silence
        trimmed_audio, _ = librosa.effects.trim(
            y=audio_data,
            top_db=top_db,
            frame_length=frame_length,
            hop_length=hop_length
        )
        
        return trimmed_audio

    @staticmethod
    def save_audio(audio_data: np.ndarray, 
                  sample_rate: int, 
                  output_path: str,
                  format: str = 'wav') -> None:
        """
        Save audio data to a file.
        
        Args:
            audio_data: Audio data to save
            sample_rate: Sample rate in Hz
            output_path: Output file path
            format: Output format (default: 'wav')
        """
        try:
            sf.write(
                file=output_path,
                data=audio_data.T if len(audio_data.shape) > 1 else audio_data,
                samplerate=sample_rate,
                format=format
            )
        except Exception as e:
            raise Exception(f"Error saving audio to {output_path}: {str(e)}")
