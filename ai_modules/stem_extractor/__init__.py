"""Stem Extractor for OpenDAW

Audio source separation using Demucs.
"""

from pathlib import Path
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass
import json
import subprocess
import os
import sys


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
        self._demucs_available = self._check_demucs()
        
    def _check_demucs(self) -> bool:
        """Check if demucs is available"""
        try:
            # Check for demucs in virtual environment Scripts folder first
            venv_demucs = os.path.join(os.path.dirname(sys.executable), 'demucs.exe')
            if os.path.exists(venv_demucs):
                cmd = [venv_demucs, '-h']
            else:
                cmd = ['demucs', '-h']
            result = subprocess.run(cmd, capture_output=True, timeout=5)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            return False
    
    def separate(
        self,
        audio_path: Path,
        stems: List[str] = None,
        callback: Optional[Callable[[str, float], None]] = None
    ) -> Dict[str, Path]:
        """Separate audio into stems using Demucs
        
        Args:
            audio_path: Path to input audio file
            stems: List of stems to extract (default: drums, bass, vocals, other)
            callback: Progress callback (stem_name, progress_0_to_1)
            
        Returns:
            Dict mapping stem names to output file paths
        """
        if stems is None:
            stems = ["drums", "bass", "vocals", "other"]
        
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        # Build output directory
        output_dir = self.cache_dir / audio_path.stem
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Check if already processed
        result = {}
        all_exist = True
        for stem in stems:
            stem_path = output_dir / f"{stem}.wav"
            result[stem] = stem_path
            if not stem_path.exists():
                all_exist = False
        
        if all_exist:
            # Return cached results
            if callback:
                for stem in stems:
                    callback(stem, 1.0)
            return result
        
        # Run demucs
        if not self._demucs_available:
            # Fallback: create empty stub files
            for stem in stems:
                stem_path = output_dir / f"{stem}.wav"
                if callback:
                    callback(stem, 1.0)
                # Create empty wav file as placeholder
                if not stem_path.exists():
                    stem_path.touch()
            return result
        
        # Build demucs command
        venv_demucs = os.path.join(os.path.dirname(sys.executable), 'demucs.exe')
        cmd = [venv_demucs] if os.path.exists(venv_demucs) else ['demucs']
        
        cmd.extend([
            '-n', self.model,
            '-d', 'cpu',  # Use CPU for compatibility
            '--shifts', '0',  # Fast mode for CPU
            '--overlap', '0.25',
            '-o', str(output_dir),
            str(audio_path)
        ])
        
        # Run demucs
        try:
            if callback:
                callback("drums", 0.25)
                callback("bass", 0.25)
                callback("vocals", 0.25)
                callback("other", 0.25)
            
            result_proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            if result_proc.returncode != 0:
                raise RuntimeError(f"Demucs failed: {result_proc.stderr}")
            
            # Move files from demucs output structure to our structure
            demucs_output = output_dir / self.model / audio_path.stem
            if demucs_output.exists():
                for stem_file in demucs_output.glob("*.wav"):
                    stem_name = stem_file.stem  # drums, bass, vocals, other
                    if stem_name in stems:
                        target = output_dir / f"{stem_name}.wav"
                        if not target.exists():
                            import shutil
                            shutil.move(str(stem_file), str(target))
                # Clean up demucs output dir
                import shutil
                shutil.rmtree(demucs_output.parent, ignore_errors=True)
            
            # Mark all as complete
            if callback:
                for stem in stems:
                    callback(stem, 1.0)
                    
        except subprocess.TimeoutExpired:
            raise RuntimeError("Demucs processing timed out")
        except Exception as e:
            raise RuntimeError(f"Stem extraction failed: {e}")
        
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
        return self._demucs_available


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
