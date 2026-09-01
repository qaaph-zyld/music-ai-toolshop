"""
Audio Reverse Engineering Toolkit

This package provides tools for analyzing and reverse engineering WAV audio files.
"""

__version__ = "0.1.0"

# Import main components
from .audio_processor import AudioProcessor
from .feature_extractor import FeatureExtractor
from .visualizer import AudioVisualizer

__all__ = ['AudioProcessor', 'FeatureExtractor', 'AudioVisualizer']
