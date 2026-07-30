"""Batch 3 continuation: fetch remaining 5 artists (Rasta, Maya Berovic, Ana Nikolic, Breskvica, Henny).

Devito, TNG, and Voyage were already fetched in the first run.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

try:
    import lyricsgenius
except ImportError:
    lyricsgenius = None  # type: ignore

from extract_artists import (
    slugify,
    load_token,
    save_song,
    get_primary_artist_name,
    extract_featured_artists,
    fetch_artist_songs,
)


ARTISTS = [
    {
        "name": "Rasta",
        "folder": "rasta",
        "variants": {"rasta", "stefan đurić", "stefan duric", "stefan djuric"},
    },
    {
        "name": "Maya Berović",
        "folder": "maya-berovic",
        "variants": {
            "maya berović", "maya berovic", "maja berović", "maja berovic", "maya",
        },
    },
    {
        "name": "Ana Nikolić",
        "folder": "ana-nikolic",
        "variants": {"ana nikolić", "ana nikolic", "ana nikolich"},
    },
    {
        "name": "Breskvica",
        "folder": "breskvica",
        "variants": {
            "breskvica", "anđela ignjatović", "andjela ignjatovic",
            "andela ignjatovic",
        },
    },
    {
        "name": "Henny",
        "folder": "henny",
        "variants": {"henny", "miloš stojković", "milos stojkovic"},
    },
]

CATEGORIES = [f"{a['folder']}-solo" for a in ARTISTS] + [
    f"{a['folder']}-featured" for a in ARTISTS
]


def normalize_name(name: str) -> str:
    return name.lower().strip()


def is_primary_match(primary_artist: str, variants: set[str]) -> bool:
    n = normalize_name(primary_artist)
    return any(v in n for v in variants)


def categorize_song(primary_artist: str, artist_cfg: dict) -> str:
    if is_primary_match(primary_artist, artist_cfg["variants"]):
        return f"{artist_cfg['folder']}-solo"
    return f"{artist_cfg['folder']}-featured"


def main():
    parser = argparse.ArgumentParser(
        description="Batch 3 continuation: fetch remaining 5 artists"
    )
    _data_dir = os.environ.get("TOOLSHOP_DATA_DIR", str(Path(__file__).resolve().parent.parent / "data" / "toolshop"))
    _default_outdir = Path(_data_dir) / "lyrics" / "genius"
    parser.add_argument("--outdir", type=Path, default=_default_outdir)
    parser.add_argument("--delay", type=float, default=1.5)
    args = parser.parse_args()

    token = load_token()
    outdir = args.outdir
    outdir.mkdir(parents=True, exist_ok=True)

    if lyricsgenius is None:
        print("lyricsgenius is required. Install with: pip install lyricsgenius")
        sys.exit(1)

    genius = lyricsgenius.Genius(
        token,
        sleep_time=args.delay,
        skip_non_songs=True,
        excluded_terms=["(Remix)", "(Instrumental)"],
        remove_section_headers=False,
        timeout=30,
    )

    seen_ids: set[int] = set()
    all_index: list[dict[str, Any]] = []
    stats: dict[str, int] = {cat: 0 for cat in CATEGORIES}
    stats["skipped_dup"] = 0
    stats["skipped_no_lyrics"] = 0
    stats["failed"] = 0

    for artist_cfg in ARTISTS:
        artist_name = artist_cfg["name"]
        try:
            songs = fetch_artist_songs(genius, artist_name)
        except Exception as e:
            print(f"  ERROR fetching {artist_name}: {e}")
            continue

        for i, song in enumerate(songs, 1):
            song_id = getattr(song, "id", None)
            title = getattr(song, "title", "Unknown")
            primary_artist = get_primary_artist_name(song)
            featured = extract_featured_artists(song)

            if song_id is not None and song_id in seen_ids:
                stats["skipped_dup"] += 1
                print(f"  [{i}/{len(songs)}] SKIP (dup): {title}")
                continue

            category = categorize_song(primary_artist, artist_cfg)

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

    # Save partial index
    index_path = outdir / "_index_batch3_remaining.json"
    with index_path.open("w", encoding="utf-8") as f:
        json.dump(all_index, f, indent=2, ensure_ascii=False)
    print(f"\nIndex saved: {index_path} ({len(all_index)} entries)")

    print(f"\n{'='*60}")
    print("BATCH 3 REMAINING EXTRACTION SUMMARY")
    print(f"{'='*60}")
    total = sum(stats.values())
    for cat in CATEGORIES:
        print(f"  {cat:25s}: {stats[cat]:>4d}")
    print(f"  {'skipped_dup':25s}: {stats['skipped_dup']:>4d}")
    print(f"  {'skipped_no_lyrics':25s}: {stats['skipped_no_lyrics']:>4d}")
    print(f"  {'failed':25s}: {stats['failed']:>4d}")
    print(f"  {'TOTAL':25s}: {total:>4d}")


if __name__ == "__main__":
    main()
