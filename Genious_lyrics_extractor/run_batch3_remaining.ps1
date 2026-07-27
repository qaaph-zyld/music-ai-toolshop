$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"
python "d:\Projects\Music-AI-Toolshop\Genious_lyrics_extractor\extract_batch3_remaining.py" --outdir "D:\MusicData\toolshop\lyrics\genius" --delay 1.5 2>&1 | Out-File -Encoding utf8 "D:\MusicData\toolshop\lyrics\genius\_batch3_remaining_log.txt"
