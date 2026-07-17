"""Batch 2 lyrics extraction from Genius for Relja, Senidah, Corona, Nikolija, Indodjija.

Uses the lyricsgenius library to fetch all songs for each artist (including
featured appearances), categorizes by solo vs featured, and saves lyrics as
JSON + TXT in subfolders with a master index.

Usage:
    python extract_batch2.py [--outdir D:/MusicData/toolshop/lyrics/genius] [--delay 1.5]
    python extract_batch2.py --rebuild --outdir D:/MusicData/toolshop/lyrics/genius
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


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ARTISTS = [
    {
        "name": "Relja Popović",
        "folder": "relja",
        "variants": {"relja popović", "relja", "drima", "relja popovic"},
    },
    {
        "name": "Senidah",
        "folder": "senidah",
        "variants": {"senidah", "senida hajdarpašić", "senida hajdarpasic"},
    },
    {
        "name": "Corona",
        "folder": "corona",
        "variants": {"corona", "predrag miljković", "predrag miljkovic"},
    },
    {
        "name": "Nikolija",
        "folder": "nikolija",
        "variants": {"nikolija", "nikolija jovanović", "nikolija jovanovic"},
    },
    {
        "name": "Indodjija",
        "folder": "indodjija",
        "variants": {"indodjija", "indođija", "indodjia"},
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def normalize_name(name: str) -> str:
    return name.lower().strip()


def is_primary_match(primary_artist: str, variants: set[str]) -> bool:
    """Check if the primary artist name matches any of the artist's variants."""
    n = normalize_name(primary_artist)
    return any(v in n for v in variants)


def categorize_song(primary_artist: str, artist_cfg: dict) -> str:
    """Return '{folder}-solo' or '{folder}-featured'."""
    if is_primary_match(primary_artist, artist_cfg["variants"]):
        return f"{artist_cfg['folder']}-solo"
    return f"{artist_cfg['folder']}-featured"


# ---------------------------------------------------------------------------
# Rebuild index from disk
# ---------------------------------------------------------------------------

CATEGORIES = [f"{a['folder']}-solo" for a in ARTISTS] + [
    f"{a['folder']}-featured" for a in ARTISTS
]


def rebuild_index(outdir: Path) -> dict[str, int]:
    """Rebuild _index_batch2.json and _summary_batch2.md from existing files on disk."""
    index: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str]] = set()
    dedup_log: list[dict[str, Any]] = []
    stats: dict[str, int] = {cat: 0 for cat in CATEGORIES}
    stats["skipped_dup"] = 0
    stats["total_files"] = 0
    stats["unique_songs"] = 0

    for cat in CATEGORIES:
        cat_dir = outdir / cat
        if not cat_dir.exists():
            continue
        for json_path in sorted(cat_dir.glob("*.json")):
            stats["total_files"] += 1
            try:
                data = json.loads(json_path.read_text(encoding="utf-8"))
            except Exception as e:
                print(f"  WARNING: Could not read {json_path}: {e}")
                continue

            title = data.get("title", "Unknown")
            primary_artist = data.get("primary_artist", data.get("artist", "Unknown"))
            featured = data.get("featured_artists", [])
            url = data.get("url", "")
            song_id = data.get("genius_song_id")
            stored_cat = data.get("artist_config", cat)

            key = (
                re.sub(r"[^\w\s]", "", title.lower()).strip(),
                re.sub(r"[^\w\s]", "", primary_artist.lower()).strip(),
            )
            if key in seen_keys:
                dedup_log.append({
                    "title": title,
                    "primary_artist": primary_artist,
                    "json_path": str(json_path),
                })
                stats["skipped_dup"] += 1
                continue
            seen_keys.add(key)

            txt_path = json_path.with_suffix(".txt")
            entry = {
                "genius_song_id": song_id,
                "title": title,
                "primary_artist": primary_artist,
                "featured_artists": featured,
                "category": stored_cat,
                "url": url,
                "status": "completed",
                "json_path": str(json_path),
                "txt_path": str(txt_path) if txt_path.exists() else None,
            }
            index.append(entry)
            stats["unique_songs"] += 1
            if stored_cat in stats:
                stats[stored_cat] += 1

    index_path = outdir / "_index_batch2.json"
    with index_path.open("w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)
    print(f"Index saved: {index_path} ({len(index)} unique entries)")

    dedup_path = outdir / "_dedup_log_batch2.json"
    with dedup_path.open("w", encoding="utf-8") as f:
        json.dump(dedup_log, f, indent=2, ensure_ascii=False)
    print(f"Dedup log saved: {dedup_path} ({len(dedup_log)} duplicates)")

    summary_path = outdir / "_summary_batch2.md"
    with summary_path.open("w", encoding="utf-8") as f:
        f.write("# Batch 2 Lyrics Extraction Summary (rebuilt from disk)\n\n")
        f.write(f"**Date:** {time.strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"**Artists:** {', '.join(a['name'] for a in ARTISTS)}\n\n")
        f.write("## Statistics\n\n")
        f.write("| Category | Count |\n|----------|-------|\n")
        for cat in CATEGORIES:
            f.write(f"| {cat} | {stats[cat]} |\n")
        f.write(f"| skipped (duplicate) | {stats['skipped_dup']} |\n")
        f.write(f"| **Unique songs** | **{stats['unique_songs']}** |\n")
    print(f"Summary saved: {summary_path}")

    return stats


# ---------------------------------------------------------------------------
# Main extraction
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Extract lyrics from Genius for Relja, Senidah, Corona, Nikolija, Indodjija (batch 2)"
    )
    _data_dir = os.environ.get(
        "TOOLSHOP_DATA_DIR", r"D:\MusicData\toolshop"
    )
    _default_outdir = Path(_data_dir) / "lyrics" / "genius"
    parser.add_argument(
        "--outdir",
        type=Path,
        default=_default_outdir,
        help=f"Output directory (default: {_default_outdir})",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.5,
        help="Delay between requests in seconds (default: 1.5)",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Rebuild _index_batch2.json and _summary_batch2.md from existing files on disk (no API calls)",
    )
    args = parser.parse_args()

    if args.rebuild:
        outdir = args.outdir
        outdir.mkdir(parents=True, exist_ok=True)
        stats = rebuild_index(outdir)
        print(f"\nRebuild complete: {stats['unique_songs']} unique songs, "
              f"{stats['skipped_dup']} duplicates, {stats['total_files']} JSON files")
        return

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
    dedup_log: list[dict[str, Any]] = []
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
                dedup_log.append({
                    "genius_song_id": song_id,
                    "title": title,
                    "primary_artist": primary_artist,
                    "skipped_from": artist_name,
                })
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
                all_index.append({
                    "genius_song_id": song_id,
                    "title": title,
                    "primary_artist": primary_artist,
                    "category": category,
                    "status": "failed",
                    "error": str(e),
                    "json_path": None,
                    "txt_path": None,
                })

    # Save index
    index_path = outdir / "_index_batch2.json"
    with index_path.open("w", encoding="utf-8") as f:
        json.dump(all_index, f, indent=2, ensure_ascii=False)
    print(f"\nIndex saved: {index_path} ({len(all_index)} entries)")

    # Save dedup log
    dedup_path = outdir / "_dedup_log_batch2.json"
    with dedup_path.open("w", encoding="utf-8") as f:
        json.dump(dedup_log, f, indent=2, ensure_ascii=False)
    print(f"Dedup log saved: {dedup_path} ({len(dedup_log)} duplicates)")

    # Print summary
    print(f"\n{'='*60}")
    print("BATCH 2 EXTRACTION SUMMARY")
    print(f"{'='*60}")
    total = sum(stats.values())
    for cat in CATEGORIES:
        print(f"  {cat:25s}: {stats[cat]:>4d}")
    print(f"  {'skipped_dup':25s}: {stats['skipped_dup']:>4d}")
    print(f"  {'skipped_no_lyrics':25s}: {stats['skipped_no_lyrics']:>4d}")
    print(f"  {'failed':25s}: {stats['failed']:>4d}")
    print(f"  {'TOTAL':25s}: {total:>4d}")

    # Save summary as markdown
    summary_path = outdir / "_summary_batch2.md"
    with summary_path.open("w", encoding="utf-8") as f:
        f.write("# Batch 2 Lyrics Extraction Summary\n\n")
        f.write(f"**Date:** {time.strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"**Artists:** {', '.join(a['name'] for a in ARTISTS)}\n\n")
        f.write("## Statistics\n\n")
        f.write("| Category | Count |\n|----------|-------|\n")
        for cat in CATEGORIES:
            f.write(f"| {cat} | {stats[cat]} |\n")
        f.write(f"| skipped (duplicate) | {stats['skipped_dup']} |\n")
        f.write(f"| skipped (no lyrics) | {stats['skipped_no_lyrics']} |\n")
        f.write(f"| failed | {stats['failed']} |\n")
        f.write(f"| **TOTAL** | **{total}** |\n\n")

        failed = [e for e in all_index if e.get("status") == "failed"]
        if failed:
            f.write("## Failed Songs\n\n")
            for e in failed:
                f.write(f"- {e['title']} ({e.get('primary_artist', '?')}): {e.get('error', '?')}\n")

        no_lyrics = [e for e in all_index if e.get("status") == "no_lyrics"]
        if no_lyrics:
            f.write("\n## Songs Without Lyrics (instrumental/unavailable)\n\n")
            for e in no_lyrics:
                f.write(f"- {e['title']} ({e.get('primary_artist', '?')})\n")

    print(f"Summary saved: {summary_path}")


if __name__ == "__main__":
    main()
