"""Utility functions for file scanning and path handling"""
import os
import re
from pathlib import Path
from datetime import datetime
from typing import List


AUDIO_EXTENSIONS = {'.mp3', '.wav', '.flac', '.m4a', '.ogg', '.aac'}


def sanitize_filename(filename: str) -> str:
    """Remove or replace problematic characters in filenames"""
    name = re.sub(r'[<>:"/\\|?*]', '_', filename)
    name = name.strip('. ')
    return name or 'untitled'


def scan_audio_files(folder_path: str) -> List[str]:
    """Recursively scan folder for audio files"""
    audio_files = []
    try:
        for root, _, files in os.walk(folder_path):
            for file in files:
                if Path(file).suffix.lower() in AUDIO_EXTENSIONS:
                    audio_files.append(os.path.join(root, file))
    except Exception as e:
        print(f"Error scanning folder: {e}")
    return audio_files


def get_unique_output_dir(base_path: str, name: str) -> str:
    """Create unique output directory, append timestamp if exists"""
    target = os.path.join(base_path, name)
    if not os.path.exists(target):
        return target
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(base_path, f"{name}_{timestamp}")


def format_duration(seconds: float) -> str:
    """Format duration in seconds to HH:MM:SS"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"


def ensure_dir(path: str) -> None:
    """Ensure directory exists, create if necessary"""
    os.makedirs(path, exist_ok=True)
