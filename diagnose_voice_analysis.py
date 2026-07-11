r"""Diagnostic: test voice_effects_adapter.analyze_voice on a specific track."""
import sys
import time
from pathlib import Path

sys.path.insert(0, r"d:\Projects\Music-AI-Toolshop")

from toolshop import voice_effects_adapter

track = Path(r"d:\Projects\Tools\yt_extractor\downloads\CrhymeTV\2010-12-08 - Sa4 - Täterprofil [eryRCHmXItY].mp3")
out_dir = Path(r"d:\Projects\Music-AI-Toolshop\results\crhymetv_re\diagnose_voice")
out_dir.mkdir(parents=True, exist_ok=True)

print(f"Starting voice analysis on {track.name}")
start = time.time()
try:
    result = voice_effects_adapter.analyze_voice(track, export_json=True, output_dir=out_dir)
    elapsed = time.time() - start
    print(f"Voice analysis completed in {elapsed:.1f}s")
    print(f"Effects detected: {result.get('effects_detected', [])}")
except Exception as e:
    import traceback
    print(f"FAILED: {e}")
    traceback.print_exc()
