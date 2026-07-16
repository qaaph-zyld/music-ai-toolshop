"""Batch lyrics extraction from Genius for Buba Corelli, Jala Brat, and Coby.

Uses the lyricsgenius library to fetch all songs for each artist,
deduplicates by Genius song ID, categorizes by artist configuration
(solo / duo / trio / other-collab), and saves lyrics as JSON + TXT
in subfolders with a master index.

Usage:
    python extract_artists.py [--outdir lyrics_output] [--delay 1.5]
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
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

try:
    import lyricsgenius
except ImportError:
    lyricsgenius = None  # type: ignore


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ARTISTS = [
    "Buba Corelli",
    "Jala Brat",
    "Coby",
]

# Name variants for matching (lowercase)
BUBA_VARIANTS = {"buba corelli", "buba correli", "buba"}
JALA_VARIANTS = {"jala brat", "jala", "jasmin fazlic"}
COBY_VARIANTS = {"coby", "slobodan veljkovic", "slobodan veljković"}

CATEGORIES = [
    "buba-solo",
    "jala-solo",
    "coby-solo",
    "jala-buba-duo",
    "jala-buba-coby-trio",
    "other-collab",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def slugify(text: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[-\s]+", "-", slug).strip("-")
    return slug or "unknown"


def _norm_key(title: str, artist: str) -> tuple[str, str]:
    """Normalized (title, primary_artist) key for deduplication."""
    return (
        re.sub(r"[^\w\s]", "", title.lower()).strip(),
        re.sub(r"[^\w\s]", "", artist.lower()).strip(),
    )


def rebuild_index(outdir: Path) -> dict[str, Any]:
    """Rebuild _index.json and _summary.md from existing JSON files on disk.

    Scans all category subdirectories for .json files, deduplicates by
    normalized (title, primary_artist), populates file paths, and writes
    a fresh index and summary.  No network access — disk only.

    Returns a stats dict with counts.
    """
    import unicodedata

    index: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str]] = set()
    dedup_log: list[dict[str, Any]] = []
    stats: dict[str, int] = {cat: 0 for cat in CATEGORIES}
    stats["skipped_dup"] = 0
    stats["total_files"] = 0
    stats["unique_songs"] = 0

    # Scan each category subdirectory
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

            key = _norm_key(title, primary_artist)
            if key in seen_keys:
                dedup_log.append({
                    "title": title,
                    "primary_artist": primary_artist,
                    "json_path": str(json_path),
                    "duplicate_of": next(
                        (e for e in index
                         if _norm_key(e["title"], e["primary_artist"]) == key),
                        None,
                    ),
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
                "file": str(json_path),
                "json_path": str(json_path),
                "txt_path": str(txt_path) if txt_path.exists() else None,
            }
            index.append(entry)
            stats["unique_songs"] += 1
            if stored_cat in stats:
                stats[stored_cat] += 1

    # Save index
    index_path = outdir / "_index.json"
    with index_path.open("w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)
    print(f"Index saved: {index_path} ({len(index)} unique entries)")

    # Save dedup log
    dedup_path = outdir / "_dedup_log.json"
    with dedup_path.open("w", encoding="utf-8") as f:
        json.dump(dedup_log, f, indent=2, ensure_ascii=False)
    print(f"Dedup log saved: {dedup_path} ({len(dedup_log)} duplicates)")

    # Save summary
    summary_path = outdir / "_summary.md"
    total_songs = stats["unique_songs"]
    expected_files = total_songs * 2 + 3  # json+txt per song + 3 metadata files
    with summary_path.open("w", encoding="utf-8") as f:
        f.write("# Lyrics Extraction Summary (rebuilt from disk)\n\n")
        f.write(f"**Date:** {time.strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"**Artists:** {', '.join(ARTISTS)}\n\n")
        f.write("## Statistics\n\n")
        f.write("| Category | Count |\n|----------|-------|\n")
        for cat in CATEGORIES:
            f.write(f"| {cat} | {stats[cat]} |\n")
        f.write(f"| skipped (duplicate) | {stats['skipped_dup']} |\n")
        f.write(f"| **Unique songs** | **{total_songs}** |\n\n")
        f.write("## File Reconciliation\n\n")
        f.write(f"- Unique songs: {total_songs}\n")
        f.write(f"- Expected files (songs × 2 + 3 metadata): {expected_files}\n")
        f.write(f"- JSON files scanned: {stats['total_files']}\n")
        actual_total = stats["total_files"] + stats["total_files"] + 3
        f.write(f"- Actual total (JSON + TXT + metadata): {actual_total}\n")
        remainder = actual_total - expected_files
        if remainder > 0:
            f.write(f"- Remainder: {remainder} files from {stats['skipped_dup']} duplicate song(s) "
                    f"(each duplicate contributes 1 JSON + 1 TXT)\n")
    print(f"Summary saved: {summary_path}")

    return stats


def normalize_artist_name(name: str) -> str:
    return name.lower().strip()


def has_buba(name: str) -> bool:
    n = normalize_artist_name(name)
    return any(v in n for v in BUBA_VARIANTS)


def has_jala(name: str) -> bool:
    n = normalize_artist_name(name)
    return any(v in n for v in JALA_VARIANTS)


def has_coby(name: str) -> bool:
    n = normalize_artist_name(name)
    return any(v in n for v in COBY_VARIANTS)


def categorize_song(primary_artist: str, featured_artists: list[str]) -> str:
    """Determine the artist configuration category for a song."""
    all_names = [primary_artist] + featured_artists
    has_b = any(has_buba(n) for n in all_names)
    has_j = any(has_jala(n) for n in all_names)
    has_c = any(has_coby(n) for n in all_names)

    if has_b and has_j and has_c:
        return "jala-buba-coby-trio"
    if has_b and has_j and not has_c:
        return "jala-buba-duo"
    if has_b and not has_j and not has_c:
        return "buba-solo"
    if has_j and not has_b and not has_c:
        return "jala-solo"
    if has_c and not has_b and not has_j:
        return "coby-solo"
    return "other-collab"


def extract_featured_artists(song) -> list[str]:
    """Extract featured artist names from a lyricsgenius Song object."""
    featured = []
    # lyricsgenius stores featured_artists as a list of names
    if hasattr(song, "featured_artists") and song.featured_artists:
        for fa in song.featured_artists:
            if isinstance(fa, dict):
                featured.append(fa.get("name", ""))
            else:
                featured.append(str(fa))
    return [f for f in featured if f]


def get_primary_artist_name(song) -> str:
    """Get primary artist name from a lyricsgenius Song object."""
    if hasattr(song, "primary_artist") and song.primary_artist:
        if isinstance(song.primary_artist, dict):
            return song.primary_artist.get("name", "Unknown")
        return str(song.primary_artist)
    if hasattr(song, "artist"):
        return str(song.artist)
    return "Unknown"


def save_song(
    song,
    category: str,
    outdir: Path,
    seen_ids: set[int],
) -> dict[str, Any] | None:
    """Save a single song's lyrics as JSON + TXT in the category subfolder.

    Returns metadata dict for the index, or None if skipped (dup / no lyrics).
    """
    song_id = getattr(song, "id", None)
    if song_id is not None and song_id in seen_ids:
        return None
    if song_id is not None:
        seen_ids.add(song_id)

    title = getattr(song, "title", "Unknown")
    primary_artist = get_primary_artist_name(song)
    featured = extract_featured_artists(song)
    url = getattr(song, "url", "")

    # Get lyrics — lyricsgenius stores them in .lyrics
    lyrics_text = getattr(song, "lyrics", "")
    if not lyrics_text or lyrics_text.strip() == "":
        return {
            "genius_song_id": song_id,
            "title": title,
            "primary_artist": primary_artist,
            "featured_artists": featured,
            "category": category,
            "url": url,
            "status": "no_lyrics",
            "json_path": None,
            "txt_path": None,
        }

    # Build sections from section labels in lyrics
    sections = []
    current_label = None
    current_lines: list[str] = []
    for line in lyrics_text.split("\n"):
        bracket_match = re.match(r"^\[(.+?)\]\s*$", line.strip())
        if bracket_match:
            if current_label is not None or current_lines:
                sections.append({
                    "label": current_label,
                    "content": "\n".join(current_lines).strip(),
                })
            current_label = bracket_match.group(1)
            current_lines = []
        else:
            current_lines.append(line)
    if current_label is not None or current_lines:
        sections.append({
            "label": current_label,
            "content": "\n".join(current_lines).strip(),
        })

    # Clean lyrics: remove section labels for clean version
    clean_lines = []
    for line in lyrics_text.split("\n"):
        if re.match(r"^\[.+?\]\s*$", line.strip()):
            continue
        clean_lines.append(line)
    clean_lyrics = "\n".join(clean_lines).strip()

    # Save to category subfolder
    cat_dir = outdir / category
    cat_dir.mkdir(parents=True, exist_ok=True)

    base = f"{slugify(primary_artist)}-{slugify(title)}"
    json_path = cat_dir / f"{base}.json"
    txt_path = cat_dir / f"{base}.txt"

    lyrics_data = {
        "title": title,
        "artist": primary_artist,
        "url": url,
        "language": None,
        "raw_lyrics": lyrics_text,
        "clean_lyrics": clean_lyrics,
        "sections": sections,
        "artist_config": category,
        "primary_artist": primary_artist,
        "featured_artists": featured,
        "genius_song_id": song_id,
    }

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(lyrics_data, f, indent=2, ensure_ascii=False)

    with txt_path.open("w", encoding="utf-8") as f:
        f.write(clean_lyrics)

    return {
        "genius_song_id": song_id,
        "title": title,
        "primary_artist": primary_artist,
        "featured_artists": featured,
        "category": category,
        "url": url,
        "status": "completed",
        "json_path": str(json_path),
        "txt_path": str(txt_path),
    }


# ---------------------------------------------------------------------------
# Main extraction
# ---------------------------------------------------------------------------

def load_token() -> str:
    """Load Genius API token from Genious_lyrics_extractor/.env or environment."""
    # Try the extractor's own .env first
    extractor_env = Path(__file__).parent / ".env"
    if extractor_env.exists():
        for line in extractor_env.read_text().splitlines():
            line = line.strip()
            if line.startswith("Genious_API=") or line.startswith("Genious_API:"):
                val = line.split("=", 1)[-1].strip().strip("'\"")
                if val:
                    return val
    # Fallback to env var
    token = os.environ.get("GENIUS_ACCESS_TOKEN", "") or os.environ.get("Genious_API", "")
    if not token:
        print("ERROR: No Genius API token found. Put Genious_API='...' in Genious_lyrics_extractor/.env")
        sys.exit(1)
    return token


def fetch_artist_songs(genius: lyricsgenius.Genius, artist_name: str) -> list:
    """Fetch all songs for an artist using lyricsgenius."""
    print(f"\n{'='*60}")
    print(f"Fetching songs for: {artist_name}")
    print(f"{'='*60}")

    artist = genius.search_artist(
        artist_name,
        max_songs=1000,
        sort="title",
        get_full_info=True,
        include_features=True,
        max_pages=50,
    )

    if artist is None:
        print(f"  WARNING: No artist found for '{artist_name}'")
        return []

    songs = artist.songs if hasattr(artist, "songs") else []
    print(f"  Found {len(songs)} songs for {artist_name}")
    return songs


def main():
    parser = argparse.ArgumentParser(
        description="Extract all lyrics from Buba Corelli, Jala Brat, and Coby"
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
        help="Rebuild _index.json and _summary.md from existing files on disk (no API calls)",
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

    for artist_name in ARTISTS:
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

            # Check for dup before categorizing
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

            category = categorize_song(primary_artist, featured)

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
    index_path = outdir / "_index.json"
    with index_path.open("w", encoding="utf-8") as f:
        json.dump(all_index, f, indent=2, ensure_ascii=False)
    print(f"\nIndex saved: {index_path} ({len(all_index)} entries)")

    # Save dedup log
    dedup_path = outdir / "_dedup_log.json"
    with dedup_path.open("w", encoding="utf-8") as f:
        json.dump(dedup_log, f, indent=2, ensure_ascii=False)
    print(f"Dedup log saved: {dedup_path} ({len(dedup_log)} duplicates)")

    # Print summary
    print(f"\n{'='*60}")
    print("EXTRACTION SUMMARY")
    print(f"{'='*60}")
    total = sum(stats.values())
    for cat in CATEGORIES:
        print(f"  {cat:25s}: {stats[cat]:>4d}")
    print(f"  {'skipped_dup':25s}: {stats['skipped_dup']:>4d}")
    print(f"  {'skipped_no_lyrics':25s}: {stats['skipped_no_lyrics']:>4d}")
    print(f"  {'failed':25s}: {stats['failed']:>4d}")
    print(f"  {'TOTAL':25s}: {total:>4d}")

    # Save summary as markdown
    summary_path = outdir / "_summary.md"
    with summary_path.open("w", encoding="utf-8") as f:
        f.write("# Lyrics Extraction Summary\n\n")
        f.write(f"**Date:** {time.strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"**Artists:** {', '.join(ARTISTS)}\n\n")
        f.write("## Statistics\n\n")
        f.write("| Category | Count |\n|----------|-------|\n")
        for cat in CATEGORIES:
            f.write(f"| {cat} | {stats[cat]} |\n")
        f.write(f"| skipped (duplicate) | {stats['skipped_dup']} |\n")
        f.write(f"| skipped (no lyrics) | {stats['skipped_no_lyrics']} |\n")
        f.write(f"| failed | {stats['failed']} |\n")
        f.write(f"| **TOTAL** | **{total}** |\n\n")

        # List failed songs
        failed = [e for e in all_index if e.get("status") == "failed"]
        if failed:
            f.write("## Failed Songs\n\n")
            for e in failed:
                f.write(f"- {e['title']} ({e.get('primary_artist', '?')}): {e.get('error', '?')}\n")

        # List no-lyrics songs
        no_lyrics = [e for e in all_index if e.get("status") == "no_lyrics"]
        if no_lyrics:
            f.write("\n## Songs Without Lyrics (instrumental/unavailable)\n\n")
            for e in no_lyrics:
                f.write(f"- {e['title']} ({e.get('primary_artist', '?')})\n")

    print(f"Summary saved: {summary_path}")


if __name__ == "__main__":
    main()
