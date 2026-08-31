"""ACE-Step Bridge for OpenDAW

Integration with ACE-Step AI music generation.
Uses algorithmic composition for pattern generation.
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import json
import random


@dataclass
class MIDIClip:
    """MIDI clip data structure"""
    notes: List[Dict[str, Any]]
    tempo: int
    key: str
    bars: int


@dataclass
class AudioClip:
    """Audio clip data structure"""
    audio_data: bytes
    sample_rate: int
    duration_seconds: float


# Musical scales (semitone offsets from root)
SCALES = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "mixolydian": [0, 2, 4, 5, 7, 9, 10],
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
}

# Note names to MIDI note numbers
NOTE_BASE = {"C": 60, "C#": 61, "Db": 61, "D": 62, "D#": 63, "Eb": 63,
             "E": 64, "F": 65, "F#": 66, "Gb": 66, "G": 67, "G#": 68,
             "Ab": 68, "A": 69, "A#": 70, "Bb": 70, "B": 71}

# Style presets with rhythm patterns and note densities
STYLE_PRESETS = {
    "electronic": {
        "scale": "minor",
        "octaves": [0, 1, 2],
        "density": 0.6,
        "rhythm_patterns": [
            [1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0],  # Eighth notes
            [1.0, 0.5, 0.5, 0.0, 1.0, 0.5, 0.5, 0.0],  # Syncopated
        ]
    },
    "house": {
        "scale": "minor",
        "octaves": [-1, 0, 1],
        "density": 0.7,
        "rhythm_patterns": [
            [1.0, 0.25, 0.25, 0.5, 1.0, 0.25, 0.25, 0.5],
        ]
    },
    "techno": {
        "scale": "minor",
        "octaves": [-2, -1, 0],
        "density": 0.5,
        "rhythm_patterns": [
            [1.0, 0.0, 0.5, 0.0, 1.0, 0.0, 0.5, 0.0],
        ]
    },
    "ambient": {
        "scale": "major",
        "octaves": [0, 1, 2, 3],
        "density": 0.3,
        "rhythm_patterns": [
            [2.0, 0.0, 1.0, 0.0, 2.0, 0.0, 1.0, 0.0],
        ]
    },
    "jazz": {
        "scale": "dorian",
        "octaves": [0, 1],
        "density": 0.5,
        "rhythm_patterns": [
            [1.5, 0.5, 1.0, 1.0, 0.5, 0.5, 1.0, 1.0],
        ]
    }
}


class ACEStepBridge:
    """Bridge to ACE-Step AI music generation"""
    
    def __init__(self, api_endpoint: Optional[str] = None):
        self.api_endpoint = api_endpoint or "http://localhost:8080"
        
    def _parse_key(self, key: str) -> tuple:
        """Parse key string into root note and scale type"""
        # Handle keys like "C", "F#m", "Bb major", "A minor"
        key = key.strip()
        
        # Extract root note
        if len(key) >= 2 and key[1] in '#b':
            root = key[:2]
            remainder = key[2:].lower()
        else:
            root = key[0]
            remainder = key[1:].lower()
        
        # Determine scale
        if 'm' in remainder and 'maj' not in remainder:
            scale_type = "minor"
        elif 'phrygian' in remainder:
            scale_type = "phrygian"
        elif 'dorian' in remainder:
            scale_type = "dorian"
        elif 'mixolydian' in remainder:
            scale_type = "mixolydian"
        else:
            scale_type = "major"
        
        return root, scale_type
    
    def _generate_notes(self, style: str, tempo: int, key: str, bars: int) -> List[Dict[str, Any]]:
        """Generate notes based on style and parameters"""
        root, scale_type = self._parse_key(key)
        base_note = NOTE_BASE.get(root, 60)
        scale_intervals = SCALES.get(scale_type, SCALES["major"])
        
        # Get style preset or default to electronic
        preset = STYLE_PRESETS.get(style.lower(), STYLE_PRESETS["electronic"])
        
        notes = []
        random.seed(hash(f"{style}{tempo}{key}{bars}"))  # Deterministic for same params
        
        # Generate notes for each bar
        for bar in range(bars):
            bar_start = bar * 4.0  # 4 beats per bar
            
            # Select rhythm pattern
            rhythm = random.choice(preset["rhythm_patterns"])
            step_duration = 0.5  # Eighth note
            
            # Generate notes based on rhythm
            for i, velocity_factor in enumerate(rhythm):
                if velocity_factor > 0 and random.random() < preset["density"]:
                    beat = bar_start + (i * step_duration)
                    
                    # Select note from scale
                    octave_offset = random.choice(preset["octaves"]) * 12
                    scale_degree = random.randint(0, len(scale_intervals) - 1)
                    pitch = base_note + scale_intervals[scale_degree] + octave_offset
                    
                    # Clamp to valid MIDI range
                    pitch = max(0, min(127, pitch))
                    
                    velocity = int(60 + (velocity_factor * 40) + random.randint(-10, 10))
                    velocity = max(1, min(127, velocity))
                    
                    duration = step_duration * random.choice([0.5, 1.0, 1.5])
                    
                    notes.append({
                        "pitch": pitch,
                        "velocity": velocity,
                        "start": beat,
                        "duration": duration
                    })
        
        return notes
    
    def generate_pattern(
        self,
        style: str,
        tempo: int,
        key: str,
        bars: int,
        variation: float = 0.5
    ) -> MIDIClip:
        """Generate MIDI pattern via ACE-Step
        
        Args:
            style: Musical style/genre (electronic, house, techno, ambient, jazz)
            tempo: BPM
            key: Musical key (e.g., "C", "F#m", "Bb minor")
            bars: Number of bars to generate
            variation: Amount of variation (0.0-1.0)
            
        Returns:
            MIDIClip with generated notes
        """
        notes = self._generate_notes(style, tempo, key, bars)
        
        # If no notes generated (density too low), add at least one note
        if not notes:
            root, scale_type = self._parse_key(key)
            base_note = NOTE_BASE.get(root, 60)
            notes.append({
                "pitch": base_note,
                "velocity": 100,
                "start": 0.0,
                "duration": 1.0
            })
        
        return MIDIClip(
            notes=notes,
            tempo=tempo,
            key=key,
            bars=bars
        )
    
    def generate_audio(
        self,
        prompt: str,
        duration_seconds: float,
        style_tags: List[str]
    ) -> AudioClip:
        """Generate audio via ACE-Step
        
        Args:
            prompt: Text description of desired audio
            duration_seconds: Length of audio to generate
            style_tags: Style descriptors
            
        Returns:
            AudioClip with generated audio
        """
        # TODO: Implement actual ACE-Step API call
        # For now, return stub
        return AudioClip(
            audio_data=b"",
            sample_rate=48000,
            duration_seconds=duration_seconds
        )
    
    def generate_variation(
        self,
        existing_clip: MIDIClip,
        variation_amount: float = 0.3
    ) -> MIDIClip:
        """Generate variation of existing MIDI pattern
        
        Args:
            existing_clip: Original MIDI clip
            variation_amount: How much to vary (0.0-1.0)
            
        Returns:
            New MIDIClip with variations
        """
        # TODO: Implement variation logic
        return existing_clip
    
    def is_available(self) -> bool:
        """Check if ACE-Step service is available"""
        # TODO: Implement health check
        return True


def generate_to_daw_clip(
    style: str,
    tempo: int,
    key: str,
    bars: int
) -> Dict[str, Any]:
    """Convenience function for DAW integration
    
    Returns JSON-serializable dict for Rust bridge
    """
    bridge = ACEStepBridge()
    clip = bridge.generate_pattern(style, tempo, key, bars)
    
    return {
        "type": "midi_clip",
        "notes": clip.notes,
        "tempo": clip.tempo,
        "key": clip.key,
        "bars": clip.bars
    }


if __name__ == "__main__":
    # Test the bridge
    bridge = ACEStepBridge()
    clip = bridge.generate_pattern("electronic", 120, "C", 4)
    print(f"Generated clip: {json.dumps(clip.__dict__, indent=2)}")
