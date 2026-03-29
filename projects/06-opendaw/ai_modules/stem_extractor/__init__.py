"""Stem Extractor for OpenDAW

Audio source separation using Demucs/Spleeter.
"""

from pathlib import Path
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass
import json


@dataclass
class StemResult:
    """Result of stem separation"""
    drums: Path
    bass: Path
    vocals: Path
    other: Path
    original: Path


class StemExtractor:
    """Stem separation using Demucs"""
    
    def __init__(self, model: str = "htdemucs_ft"):
        self.model = model
        self.cache_dir = Path("~/.opendaw/stem_cache").expanduser()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    def separate(
        self,
        audio_path: Path,
        stems: List[str] = None,
        callback: Optional[Callable[[str, float], None]] = None
    ) -> Dict[str, Path]:
        """Separate audio into stems
        
        Args:
            audio_path: Path to input audio file
            stems: List of stems to extract (default: drums, bass, vocals, other)
            callback: Progress callback (stem_name, progress_0_to_1)
            
        Returns:
            Dict mapping stem names to output file paths
        """
        if stems is None:
            stems = ["drums", "bass", "vocals", "other"]
        
        # TODO: Implement actual Demucs separation
        # For now, return stub paths
        result = {}
        for stem in stems:
            if callback:
                callback(stem, 1.0)
            result[stem] = self.cache_dir / f"{audio_path.stem}_{stem}.wav"
        
        return result
    
    def batch_process(
        self,
        file_list: List[Path],
        callback: Optional[Callable[[Path, Dict[str, Path]], None]] = None
    ) -> List[Dict[str, Path]]:
        """Process multiple files
        
        Args:
            file_list: List of audio files to process
            callback: Called for each completed file
            
        Returns:
            List of stem results for each file
        """
        results = []
        for file_path in file_list:
            result = self.separate(file_path)
            if callback:
                callback(file_path, result)
            results.append(result)
        return results
    
    def is_available(self) -> bool:
        """Check if stem extraction is available"""
        # TODO: Check for Demucs installation
        try:
            import demucs
            return True
        except ImportError:
            return False


def extract_to_daw_tracks(
    audio_path: str,
    progress_callback: Optional[Callable[[str, float], None]] = None
) -> Dict[str, str]:
    """Convenience function for DAW integration
    
    Args:
        audio_path: Path to audio file
        progress_callback: Progress updates
        
    Returns:
        JSON-serializable dict mapping stem names to file paths
    """
    extractor = StemExtractor()
    result = extractor.separate(Path(audio_path), callback=progress_callback)
    return {k: str(v) for k, v in result.items()}


if __name__ == "__main__":
    # Test the extractor
    extractor = StemExtractor()
    
    def progress(stem: str, prog: float):
        print(f"Extracting {stem}: {prog*100:.0f}%")
    
    result = extractor.separate(Path("test_song.wav"), callback=progress)
    print(f"Stems: {json.dumps(result, indent=2, default=str)}")
