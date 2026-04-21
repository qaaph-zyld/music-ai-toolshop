"""MusicGen text-to-music generation for OpenDAW."""
from .bridge import MusicGenBridge
from .generator import MusicGenGenerator

__all__ = ['MusicGenBridge', 'MusicGenGenerator']
