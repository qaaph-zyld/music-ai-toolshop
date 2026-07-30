"""Fetch only Henny (last remaining batch 3 artist)."""
from __future__ import annotations
import os, sys, json
from pathlib import Path
from typing import Any

try:
    import lyricsgenius
except ImportError:
    lyricsgenius = None

from extract_artists import (
    load_token, save_song, get_primary_artist_name,
    extract_featured_artists, fetch_artist_songs,
)

ARTIST_CFG = {
    "name": "Henny",
    "folder": "henny",
    "variants": {"henny", "miloš stojković", "milos stojkovic"},
}

def normalize_name(name: str) -> str:
    return name.lower().strip()

def is_primary_match(primary_artist: str, variants: set[str]) -> bool:
    n = normalize_name(primary_artist)
    return any(v in n for v in variants)

def categorize_song(primary_artist: str) -> str:
    if is_primary_match(primary_artist, ARTIST_CFG["variants"]):
        return f"{ARTIST_CFG['folder']}-solo"
    return f"{ARTIST_CFG['folder']}-featured"

def main():
    token = load_token()
    outdir = Path(os.environ.get("TOOLSHOP_DATA_DIR", str(Path(__file__).resolve().parent.parent / "data" / "toolshop"))) / "lyrics" / "genius"
    outdir.mkdir(parents=True, exist_ok=True)

    if lyricsgenius is None:
        print("lyricsgenius is required.")
        sys.exit(1)

    genius = lyricsgenius.Genius(
        token, sleep_time=1.5, skip_non_songs=True,
        excluded_terms=["(Remix)", "(Instrumental)"],
        remove_section_headers=False, timeout=30,
    )

    seen_ids: set[int] = set()
    all_index: list[dict[str, Any]] = []
    stats = {"henny-solo": 0, "henny-featured": 0, "skipped_dup": 0, "skipped_no_lyrics": 0, "failed": 0}

    artist_name = ARTIST_CFG["name"]
    try:
        songs = fetch_artist_songs(genius, artist_name)
    except Exception as e:
        print(f"  ERROR fetching {artist_name}: {e}")
        return

    for i, song in enumerate(songs, 1):
        song_id = getattr(song, "id", None)
        title = getattr(song, "title", "Unknown")
        primary_artist = get_primary_artist_name(song)
        featured = extract_featured_artists(song)

        if song_id is not None and song_id in seen_ids:
            stats["skipped_dup"] += 1
            print(f"  [{i}/{len(songs)}] SKIP (dup): {title}")
            continue

        category = categorize_song(primary_artist)
        try:
            entry = save_song(song, category, outdir, seen_ids)
            if entry is None:
                stats["skipped_dup"] += 1
                continue
            all_index.append(entry)
            if entry["status"] == "completed":
                stats[category] += 1
                print(f"  [{i}/{len(songs)}] OK ({category}): {title}")
            else:
                stats["skipped_no_lyrics"] += 1
                print(f"  [{i}/{len(songs)}] NO LYRICS: {title}")
        except Exception as e:
            stats["failed"] += 1
            print(f"  [{i}/{len(songs)}] FAIL: {title} — {e}")

    index_path = outdir / "_index_henny.json"
    with index_path.open("w", encoding="utf-8") as f:
        json.dump(all_index, f, indent=2, ensure_ascii=False)
    print(f"\nIndex saved: {index_path} ({len(all_index)} entries)")
    print(f"\nHenny: solo={stats['henny-solo']}, featured={stats['henny-featured']}, dup={stats['skipped_dup']}, no_lyrics={stats['skipped_no_lyrics']}, failed={stats['failed']}")

if __name__ == "__main__":
    main()
