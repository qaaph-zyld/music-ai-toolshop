"""Rebuild lyrics.db from all batch folders."""
import sys
import os

# Patch platform.platform to avoid audio_separator hang on Windows
import platform
_orig_platform = platform.platform
platform.platform = lambda *a, **kw: 'Windows-11-10.0.22631-SP0'

from pathlib import Path
from toolshop.lyricsdb import build_database, DEFAULT_DB_PATH

root = Path(r"D:\MusicData\toolshop\lyrics\genius")
db_path = DEFAULT_DB_PATH

print(f"Building lyrics database...")
print(f"  Corpus root: {root}")
print(f"  Database:     {db_path}")

summary = build_database(root=root, db_path=db_path)
print(f"\nDone. Songs: {summary['songs_ingested']}, "
      f"Sections: {summary['sections_ingested']}, "
      f"Lines: {summary['lines_ingested']}")
