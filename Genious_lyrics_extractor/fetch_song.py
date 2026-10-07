"""Targeted single-song fetch from Genius by song id.

For recovering individual songs the roster fetcher lost or skipped —
e.g. Lacku id 5446636 ("Tenzija"), whose file was overwritten by a slug
collision before the id-suffix guard landed in ``save_song``.

Usage:
    python fetch_song.py --song-id 5446636 --category lacku-solo
        [--outdir <lyrics>/genius] [--delay 1.5] [--dry-run]
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

try:
    import lyricsgenius
except ImportError:
    lyricsgenius = None  # type: ignore

from extract_artists import load_token, save_song, get_primary_artist_name


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch one Genius song by id")
    _data_dir = os.environ.get(
        "TOOLSHOP_DATA_DIR",
        str(Path(__file__).resolve().parent.parent / "data" / "toolshop"),
    )
    parser.add_argument("--song-id", type=int, required=True,
                        help="Genius song id (e.g. 5446636)")
    parser.add_argument("--category", required=True,
                        help="Corpus subfolder to save into (e.g. lacku-solo)")
    parser.add_argument("--outdir", type=Path,
                        default=Path(_data_dir) / "lyrics" / "genius",
                        help="Corpus root (default: <data>/lyrics/genius)")
    parser.add_argument("--delay", type=float, default=1.5,
                        help="Delay between requests in seconds")
    parser.add_argument("--dry-run", action="store_true",
                        help="Resolve and print metadata only; do not save")
    args = parser.parse_args()

    if lyricsgenius is None:
        print("lyricsgenius is required. Install with: pip install lyricsgenius")
        sys.exit(1)

    token = load_token()
    genius = lyricsgenius.Genius(
        token,
        sleep_time=args.delay,
        skip_non_songs=True,
        excluded_terms=["(Remix)", "(Instrumental)"],
        remove_section_headers=False,
        timeout=30,
    )

    song = genius.song(args.song_id)
    if song is None:
        print(f"ERROR: genius.song({args.song_id}) returned None")
        sys.exit(1)

    sid = getattr(song, "id", None) or (getattr(song, "_body", None) or {}).get("id")
    title = getattr(song, "title", "?")
    artist = get_primary_artist_name(song)
    print(f"Resolved: id={sid} '{title}' — {artist}")

    if args.dry_run:
        return

    entry = save_song(song, args.category, args.outdir, seen_ids=set())
    if entry is None:
        print("ERROR: save_song returned None (skipped)")
        sys.exit(1)
    print(f"Saved ({entry['status']}): {entry.get('json_path')}")


if __name__ == "__main__":
    main()
