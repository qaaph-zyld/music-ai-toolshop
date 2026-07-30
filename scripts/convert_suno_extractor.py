#!/usr/bin/env python3
"""Convert suno_extractor JSONs to toolshop-compatible metadata files.

Reads all liked songs from d:\\Projects\\suno_extractor\\suno_songs\\*.json,
deduplicates by URL (last write wins — later extractions have cleaner lyrics),
cleans UI noise from lyrics, and writes <clip_id>_metadata.json files to
<repo>/data/toolshop/suno/ in the format toolshop suno export-text expects.
"""

from __future__ import annotations

import glob
import json
import re
from pathlib import Path

SOURCE_DIR = Path(r"d:\Projects\suno_extractor\suno_songs")
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "toolshop" / "suno"

# Regex to find the start of actual lyrics content
_LYRICS_START_RE = re.compile(r"\[(Verse|Intro|Chorus|Bridge|Male|Female|Outro|Hook|Pre|Post|Drop|Spoken)", re.IGNORECASE)


def _extract_clip_id(url: str) -> str | None:
    """Extract clip UUID from suno.com/song/<uuid> URL."""
    if not url:
        return None
    # URL format: https://suno.com/song/<uuid>
    match = re.search(r"suno\.com/song/([a-f0-9\-]+)", url)
    if match:
        return match.group(1)
    return None


def _clean_lyrics(raw: str) -> str:
    """Strip UI scraping noise from lyrics.

    Early extractions have navigation/notifications text before the actual
    lyrics start at [Verse 1], [Intro], [Chorus], etc.
    """
    if not raw:
        return ""

    match = _LYRICS_START_RE.search(raw)
    if match:
        return raw[match.start():]

    # No section marker found — could be clean lyrics or pure noise
    # If it contains typical UI noise markers, try to salvage
    if any(marker in raw for marker in ["Home\nCreate\n", "Notifications\n", "Credits\nAccount"]):
        # Try to find any bracketed section marker we might have missed
        bracket_idx = raw.find("[")
        if bracket_idx > 0:
            return raw[bracket_idx:]

    return raw


def _extract_description(song: dict) -> str:
    """Extract style/description from the song dict.

    Some extractions put it in 'plays', others in 'description'.
    """
    plays = song.get("plays", "")
    if plays and len(plays) > 20:
        return plays
    desc = song.get("description", "")
    if desc:
        return desc
    return ""


def main():
    json_files = sorted(glob.glob(str(SOURCE_DIR / "*.json")))
    if not json_files:
        print(f"No JSON files found in {SOURCE_DIR}")
        return

    # Deduplicate by URL — last write wins (later extractions have cleaner lyrics)
    songs_by_url: dict[str, dict] = {}
    for fpath in json_files:
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        for song in data.get("songs", []):
            url = song.get("url", "")
            if url:
                songs_by_url[url] = song

    print(f"Found {len(songs_by_url)} unique songs across {len(json_files)} JSON files")
    print(f"Output: {OUTPUT_DIR.resolve()}\n")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    saved = 0
    skipped = 0
    no_id = 0

    for i, (url, song) in enumerate(songs_by_url.items(), 1):
        clip_id = _extract_clip_id(url)
        if not clip_id:
            no_id += 1
            continue

        out_path = OUTPUT_DIR / f"{clip_id}_metadata.json"
        if out_path.exists():
            skipped += 1
            continue

        title = song.get("title", "") or f"Song {clip_id[:8]}"
        lyrics = _clean_lyrics(song.get("lyrics", ""))
        description = _extract_description(song)
        tags = song.get("tags", [])

        metadata = {
            "id": clip_id,
            "title": title,
            "is_liked": True,
            "handle": "Hardcore_Pop",
            "display_name": title,
            "created_at": song.get("created_at", ""),
            "metadata": {
                "prompt": lyrics,
                "tags": description,
            },
            "tags": tags,
            "duration": song.get("duration", ""),
            "url": url,
            "image_url": song.get("image_url", ""),
        }

        with out_path.open("w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        saved += 1
        print(f"  [{i}/{len(songs_by_url)}] Saved: {title[:60]}")

    print(f"\nDone: {saved} saved, {skipped} skipped (already existed), {no_id} skipped (no clip ID)")
    total_files = len(list(OUTPUT_DIR.glob("*_metadata.json")))
    print(f"Total metadata files in {OUTPUT_DIR}: {total_files}")


if __name__ == "__main__":
    main()
