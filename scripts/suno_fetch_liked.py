#!/usr/bin/env python3
"""Fetch liked Suno clips' metadata (lyrics + descriptions) via Suno's internal API.

Saves <clip_id>_metadata.json files in toolshop-compatible format so that
`toolshop suno list` and `toolshop suno export-text` can process them.

No audio download — lyrics and style descriptions only.

Usage:
    python scripts/suno_fetch_liked.py --token "ey..." --output "D:\MusicData\toolshop\suno"

Token: Open https://suno.com, log in, open browser DevTools → Network tab,
       find any request to studio-api.prod.suno.com, copy the Authorization
       header value (starts with "Bearer "). Token expires in a few hours.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import requests

BASE_API = "https://studio-api.prod.suno.com/api"
PAGE_SIZE = 20
DELAY_BETWEEN_PAGES = 2.0
MAX_RETRIES = 5
MAX_BACKOFF = 60


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://suno.com/",
    }


def _backoff(attempt: int) -> None:
    wait = min(2 ** attempt, MAX_BACKOFF)
    print(f"  Retrying in {wait}s (attempt {attempt + 1}/{MAX_RETRIES})...")
    time.sleep(wait)


def fetch_all_clips(token: str, liked_only: bool = True) -> list[dict]:
    """Paginate through POST /feed/v3 and return all (liked) clips."""
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(pool_connections=1, pool_maxsize=1, max_retries=0)
    session.mount("https://", adapter)

    clips: list[dict] = []
    cursor = None

    while True:
        payload = {
            "cursor": cursor,
            "limit": PAGE_SIZE,
            "filters": {
                "disliked": "False",
                "trashed": "False",
                "stem": {"presence": "False"},
                "fromStudioProject": {"presence": "False"},
            },
        }

        for attempt in range(MAX_RETRIES):
            try:
                resp = session.post(
                    f"{BASE_API}/feed/v3",
                    headers=_headers(token),
                    json=payload,
                    timeout=30,
                )
                if resp.status_code in (401, 403):
                    print(f"\n  Auth error (HTTP {resp.status_code}). Token expired — get a fresh token and restart.")
                    return clips
                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", 0))
                    if retry_after > 0:
                        time.sleep(retry_after + 2)
                    else:
                        _backoff(attempt)
                    continue
                if resp.status_code in (500, 502, 503, 504):
                    _backoff(attempt)
                    continue
                resp.raise_for_status()
                data = resp.json()
                break
            except requests.exceptions.Timeout:
                _backoff(attempt)
            except requests.exceptions.ConnectionError:
                _backoff(attempt)
        else:
            print(f"  Giving up after {MAX_RETRIES} attempts at cursor={cursor}")
            break

        batch = data.get("clips", [])
        if not batch:
            break

        if liked_only:
            batch = [c for c in batch if c.get("is_liked")]
        clips.extend(batch)

        print(f"  Fetched {len(clips)} liked clips so far...", end="\r")

        if not data.get("has_more", False):
            break
        cursor = data.get("next_cursor")
        if not cursor:
            break

        time.sleep(DELAY_BETWEEN_PAGES)

    print()
    return clips


def save_clip_metadata(clip: dict, output_dir: Path) -> bool:
    """Save a single clip's metadata as <clip_id>_metadata.json.

    Returns True if saved, False if skipped (already exists).
    """
    clip_id = clip.get("id", "unknown")
    filename = f"{clip_id}_metadata.json"
    filepath = output_dir / filename

    if filepath.exists():
        return False

    # Extract the fields toolshop's export_text expects
    metadata = {
        "id": clip_id,
        "title": clip.get("title") or clip.get("display_name") or "Untitled",
        "is_liked": clip.get("is_liked", False),
        "handle": clip.get("handle", ""),
        "display_name": clip.get("display_name", ""),
        "created_at": clip.get("created_at", ""),
        "model_name": clip.get("model_name", ""),
        "major_model_version": clip.get("major_model_version", ""),
        "metadata": clip.get("metadata", {}),
        "audio_url": clip.get("audio_url", ""),
        "image_url": clip.get("image_url", ""),
    }

    with filepath.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Fetch liked Suno clips' metadata (lyrics + descriptions only, no audio)"
    )
    parser.add_argument("--token", "-t", type=str, default=None,
                        help="Bearer token (or set SUNO_TOKEN env var)")
    parser.add_argument("--output", "-o", type=Path,
                        default=Path(r"D:\MusicData\toolshop\suno"),
                        help="Output directory for metadata JSONs")
    parser.add_argument("--all", action="store_true",
                        help="Fetch all clips, not just liked ones")
    args = parser.parse_args()

    token = args.token or os.environ.get("SUNO_TOKEN", "")
    if not token:
        print("No token provided. Use --token or set SUNO_TOKEN env var.")
        print("Get token from browser DevTools: Network → any request to studio-api.prod.suno.com → Authorization header")
        return

    args.output.mkdir(parents=True, exist_ok=True)

    print(f"\nFetching {'all' if args.all else 'liked'} Suno clips...")
    print(f"Output: {args.output.resolve()}\n")

    clips = fetch_all_clips(token, liked_only=not args.all)

    if not clips:
        print("No clips found. Check your token and try again.")
        return

    print(f"\nTotal clips to save: {len(clips)}")

    saved = 0
    skipped = 0
    for i, clip in enumerate(clips, 1):
        title = clip.get("title") or clip.get("display_name") or "Untitled"
        was_saved = save_clip_metadata(clip, args.output)
        if was_saved:
            saved += 1
            print(f"  [{i}/{len(clips)}] Saved: {title}")
        else:
            skipped += 1

    print(f"\nDone: {saved} saved, {skipped} skipped (already existed)")
    print(f"Total metadata files in {args.output}: {len(list(args.output.glob('*_metadata.json')))}")


if __name__ == "__main__":
    main()
