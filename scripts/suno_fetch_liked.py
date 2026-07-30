#!/usr/bin/env python3
"""Fetch liked Suno clips' metadata (lyrics + descriptions) via Suno's internal API.

Auto-extracts Bearer token from Chrome (remote debugging port 9222).
Saves <clip_id>_metadata.json files in toolshop-compatible format so that
`toolshop suno list` and `toolshop suno export-text` can process them.

No audio download — lyrics and style descriptions only.

Usage:
    # Auto-extract token from Chrome (must be running with --remote-debugging-port=9222):
    python scripts/suno_fetch_liked.py

    # Manual token:
    python scripts/suno_fetch_liked.py --token "ey..."

Setup:
    1. Start Chrome: chrome.exe --remote-debugging-port=9222
    2. Login to suno.com
    3. Navigate to liked songs page
    4. Run this script
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import time
from pathlib import Path

import requests

BASE_API = "https://studio-api.prod.suno.com/api"
PAGE_SIZE = 100
DELAY_BETWEEN_PAGES = 0.3
MAX_RETRIES = 5
MAX_BACKOFF = 60
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "toolshop" / "suno"


def _make_browser_token() -> str:
    """Generate a browser-token payload similar to the Suno web client."""
    payload = json.dumps({"timestamp": int(time.time() * 1000)})
    encoded = base64.b64encode(payload.encode("utf-8")).decode("ascii")
    return json.dumps({"token": encoded})


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://suno.com/playlist/liked",
        "Origin": "https://suno.com",
        "browser-token": _make_browser_token(),
    }


def _backoff(attempt: int) -> None:
    wait = min(2 ** attempt, MAX_BACKOFF)
    print(f"  Retrying in {wait}s (attempt {attempt + 1}/{MAX_RETRIES})...")
    time.sleep(wait)


def extract_token_from_chrome(port: int = 9222) -> str | None:
    """Extract __session cookie from Chrome via Selenium remote debugging."""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
    except ImportError:
        print("Selenium not installed. Use --token instead.")
        return None

    try:
        options = Options()
        options.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
        driver = webdriver.Chrome(options=options)

        cookies = driver.get_cookies()
        session_token = None
        for c in cookies:
            if c["name"] == "__session":
                session_token = c["value"]
                break

        driver.quit()

        if not session_token:
            print(f"No __session cookie found. Make sure you're logged into suno.com on Chrome port {port}.")
            return None

        print(f"Token extracted from Chrome (port {port}): {len(session_token)} chars")
        return session_token
    except Exception as e:
        print(f"Failed to connect to Chrome on port {port}: {e}")
        print("Make sure Chrome is running with --remote-debugging-port=9222")
        return None


def _has_lyrics(filepath: Path) -> bool:
    """Check if an existing metadata file already has lyrics."""
    try:
        with filepath.open("r", encoding="utf-8") as f:
            data = json.load(f)
        prompt = data.get("metadata", {}).get("prompt", "")
        return bool(prompt and prompt.strip())
    except (json.JSONDecodeError, KeyError, OSError):
        return False


def save_clip_metadata(clip: dict, output_dir: Path) -> str:
    """Save a single clip's metadata as <clip_id>_metadata.json.

    Returns 'saved', 'updated', or 'skipped'.
    """
    clip_id = clip.get("id", "unknown")
    filename = f"{clip_id}_metadata.json"
    filepath = output_dir / filename

    action = "saved"
    if filepath.exists():
        if _has_lyrics(filepath):
            return "skipped"
        action = "updated"

    metadata = {
        "id": clip_id,
        "title": clip.get("title") or clip.get("display_name") or "Untitled",
        "is_liked": clip.get("is_liked", True),
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

    return action


def fetch_and_save_liked(token: str, output_dir: Path, max_pages: int = 0) -> None:
    """Paginate through POST /feed/v3, saving clips as we go."""
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(pool_connections=1, pool_maxsize=1, max_retries=0)
    session.mount("https://", adapter)

    cursor = None
    page = 0
    total_saved = 0
    total_skipped = 0
    total_updated = 0
    seen_ids: set[str] = set()

    while True:
        if max_pages and page >= max_pages:
            print(f"\nReached max_pages limit ({max_pages})")
            break

        payload = {"type": "liked", "limit": PAGE_SIZE}
        if cursor:
            payload["cursor"] = cursor

        for attempt in range(MAX_RETRIES):
            try:
                resp = session.post(
                    f"{BASE_API}/feed/v3",
                    headers=_headers(token),
                    json=payload,
                    timeout=30,
                )
                if resp.status_code in (401, 403):
                    print(f"\n  Auth error (HTTP {resp.status_code}). Token expired.")
                    return
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
            print(f"  Giving up after {MAX_RETRIES} attempts at page {page + 1}")
            break

        clips = data.get("clips", [])
        if not clips:
            break

        page_saved = 0
        page_skipped = 0
        page_updated = 0
        new_count = 0

        for clip in clips:
            clip_id = clip.get("id")
            if not clip_id or clip_id in seen_ids:
                continue
            if not clip.get("is_liked"):
                continue
            seen_ids.add(clip_id)
            new_count += 1

            action = save_clip_metadata(clip, output_dir)
            if action == "saved":
                page_saved += 1
            elif action == "updated":
                page_updated += 1
            else:
                page_skipped += 1

        total_saved += page_saved
        total_skipped += page_skipped
        total_updated += page_updated

        total = total_saved + total_skipped + total_updated
        print(
            f"  Page {page + 1}: +{new_count} clips "
            f"(saved={page_saved}, updated={page_updated}, skipped={page_skipped}) "
            f"| Total: {total} ({total_saved} saved, {total_updated} updated, {total_skipped} skipped)"
        )

        has_more = data.get("has_more", False)
        cursor = data.get("next_cursor") or data.get("cursor")

        if not has_more or not cursor:
            print("  No more pages.")
            break

        page += 1
        time.sleep(DELAY_BETWEEN_PAGES)

    total = total_saved + total_skipped + total_updated
    print(f"\nDone: {total} clips processed")
    print(f"  Saved (new): {total_saved}")
    print(f"  Updated (had empty lyrics): {total_updated}")
    print(f"  Skipped (already had lyrics): {total_skipped}")
    print(f"Total metadata files in {output_dir}: {len(list(output_dir.glob('*_metadata.json')))}")


def main():
    parser = argparse.ArgumentParser(
        description="Fetch liked Suno clips' metadata (lyrics + descriptions only, no audio)"
    )
    parser.add_argument("--token", "-t", type=str, default=None,
                        help="Bearer token (or auto-extract from Chrome)")
    parser.add_argument("--output", "-o", type=Path, default=OUTPUT_DIR,
                        help="Output directory for metadata JSONs")
    parser.add_argument("--port", type=int, default=9222,
                        help="Chrome remote debugging port (for auto-token)")
    parser.add_argument("--max-pages", type=int, default=0,
                        help="Max pages to fetch (0 = unlimited, for testing)")
    args = parser.parse_args()

    token = args.token or os.environ.get("SUNO_TOKEN", "")
    if not token:
        print("No token provided. Auto-extracting from Chrome...")
        token = extract_token_from_chrome(args.port)
        if not token:
            print("\nFailed to get token. Options:")
            print("  1. Start Chrome: chrome.exe --remote-debugging-port=9222")
            print("  2. Login to suno.com, then re-run this script")
            print("  3. Or pass token manually: --token \"ey...\"")
            return

    args.output.mkdir(parents=True, exist_ok=True)

    print(f"\nFetching liked Suno clips...")
    print(f"Output: {args.output.resolve()}")
    print(f"Page size: {PAGE_SIZE}, delay: {DELAY_BETWEEN_PAGES}s\n")

    fetch_and_save_liked(token, args.output, max_pages=args.max_pages)


if __name__ == "__main__":
    main()
