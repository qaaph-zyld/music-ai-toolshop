"""Utility functions for audio analysis."""

import os
import numpy as np
import json
from typing import Dict, Any, List, Optional, Union
from dataclasses import asdict, is_dataclass
import hashlib

def ensure_dir(directory: str) -> None:
    """Ensure that a directory exists, create it if it doesn't."""
    os.makedirs(directory, exist_ok=True)

def get_file_hash(file_path: str, block_size: int = 65536) -> str:
    """Calculate the MD5 hash of a file."""
    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        buf = f.read(block_size)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(block_size)
    return hasher.hexdigest()

def save_analysis_results(results: Dict[str, Any], output_path: str) -> None:
    """
    Save analysis results to a JSON file.
    
    Args:
        results: Dictionary containing analysis results
        output_path: Path to save the JSON file
    """
    # Convert any dataclass instances to dictionaries
    def convert_dataclasses(obj):
        if is_dataclass(obj):
            return asdict(obj)
        elif isinstance(obj, (list, tuple)):
            return [convert_dataclasses(x) for x in obj]
        elif isinstance(obj, dict):
            return {k: convert_dataclasses(v) for k, v in obj.items()}
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return obj
    
    # Ensure the output directory exists
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    # Convert and save
    with open(output_path, 'w') as f:
        json.dump(convert_dataclasses(results), f, indent=2)

def load_analysis_results(file_path: str) -> Dict[str, Any]:
    """
    Load analysis results from a JSON file.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        Dictionary containing the loaded results
    """
    with open(file_path, 'r') as f:
        return json.load(f)

def time_to_samples(time_sec: float, sample_rate: int) -> int:
    """Convert time in seconds to number of samples."""
    return int(round(time_sec * sample_rate))

def samples_to_time(samples: int, sample_rate: int) -> float:
    """Convert number of samples to time in seconds."""
    return float(samples) / sample_rate

def normalize_audio(audio: np.ndarray, target_level: float = -3.0) -> np.ndarray:
    """
    Normalize audio to a target level in dB.
    
    Args:
        audio: Input audio data
        target_level: Target level in dB (default: -3.0)
        
    Returns:
        Normalized audio data
    """
    if len(audio) == 0:
        return audio
    
    # Calculate current peak level in dB
    current_peak = np.max(np.abs(audio))
    if current_peak == 0:
        return audio
    
    current_level_db = 20 * np.log10(current_peak)
    
    # Calculate required gain
    gain = 10 ** ((target_level - current_level_db) / 20.0)
    
    # Apply gain
    return audio * gain

def split_audio(audio: np.ndarray, sample_rate: int, segment_duration: float = 30.0) -> List[np.ndarray]:
    """
    Split audio into fixed-duration segments.
    
    Args:
        audio: Input audio data
        sample_rate: Sample rate in Hz
        segment_duration: Duration of each segment in seconds (default: 30.0)
        
    Returns:
        List of audio segments
    """
    if len(audio) == 0:
        return []
    
    samples_per_segment = int(segment_duration * sample_rate)
    num_segments = int(np.ceil(len(audio) / samples_per_segment))
    
    segments = []
    for i in range(num_segments):
        start = i * samples_per_segment
        end = min((i + 1) * samples_per_segment, len(audio))
        segments.append(audio[start:end])
    
    return segments

def smooth_audio(audio: np.ndarray, window_size: int = 5) -> np.ndarray:
    """
    Apply a simple moving average filter to smooth the audio signal.
    
    Args:
        audio: Input audio data
        window_size: Size of the smoothing window (must be odd)
        
    Returns:
        Smoothed audio data
    """
    if window_size < 1 or window_size % 2 == 0:
        raise ValueError("Window size must be a positive odd integer")
    
    if len(audio) < window_size:
        return audio
    
    # Pad the signal to handle boundaries
    padding = window_size // 2
    padded = np.pad(audio, (padding, padding), mode='edge')
    
    # Apply moving average
    kernel = np.ones(window_size) / window_size
    smoothed = np.convolve(padded, kernel, mode='valid')
    
    return smoothed

def detect_silence(audio: np.ndarray, sample_rate: int, threshold_db: float = -50.0, 
                 min_silence_duration: float = 0.5) -> List[Dict[str, float]]:
    """
    Detect silent segments in the audio.
    
    Args:
        audio: Input audio data
        sample_rate: Sample rate in Hz
        threshold_db: Threshold in dB below which audio is considered silent
        min_silence_duration: Minimum duration of silence to detect (in seconds)
        
    Returns:
        List of dictionaries with 'start' and 'end' times of silent segments
    """
    if len(audio) == 0:
        return []
    
    # Convert threshold to linear scale
    threshold = 10 ** (threshold_db / 20.0)
    
    # Calculate frame energy
    frame_length = int(0.01 * sample_rate)  # 10ms frames
    hop_length = frame_length // 2
    
    # Calculate energy per frame
    energy = np.array([
        np.mean(np.abs(audio[i:i+frame_length] ** 2))
        for i in range(0, len(audio) - frame_length + 1, hop_length)
    ])
    
    # Find silent frames
    silent_frames = energy < threshold
    
    # Convert to time segments
    silent_segments = []
    in_silence = False
    start_idx = 0
    
    for i, is_silent in enumerate(silent_frames):
        if is_silent and not in_silence:
            start_idx = i
            in_silence = True
        elif not is_silent and in_silence:
            end_idx = i
            duration = (end_idx - start_idx) * (hop_length / sample_rate)
            if duration >= min_silence_duration:
                start_time = start_idx * (hop_length / sample_rate)
                end_time = end_idx * (hop_length / sample_rate)
                silent_segments.append({
                    'start': start_time,
                    'end': end_time,
                    'duration': duration
                })
            in_silence = False
    
    # Handle case where the audio ends with silence
    if in_silence:
        duration = (len(silent_frames) - start_idx) * (hop_length / sample_rate)
        if duration >= min_silence_duration:
            start_time = start_idx * (hop_length / sample_rate)
            end_time = len(silent_frames) * (hop_length / sample_rate)
            silent_segments.append({
                'start': start_time,
                'end': end_time,
                'duration': duration
            })
    
    return silent_segments
