"""Stock footage search adapters for Pexels and Pixabay.

Provides unified search and download for royalty-free stock video clips.
API keys are read from environment variables: PEXELS_API_KEY, PIXABAY_API_KEY.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import httpx

    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False


def _check_httpx() -> None:
    if not _HAS_HTTPX:
        raise RuntimeError(
            "httpx is required for stock footage search. "
            "Install with: pip install httpx"
        )


def _get_api_key(source: str) -> str:
    """Get API key from environment for the given source."""
    if source == "pexels":
        key = os.environ.get("PEXELS_API_KEY")
    elif source == "pixabay":
        key = os.environ.get("PIXABAY_API_KEY")
    else:
        raise ValueError(f"Unknown stock source: {source}")

    if not key:
        raise RuntimeError(
            f"API key not set for {source}. "
            f"Set {source.upper()}_API_KEY environment variable."
        )
    return key


def search_pexels(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Search Pexels for stock videos.

    Args:
        query: Search query string.
        limit: Maximum number of results.

    Returns:
        List of dicts with source, id, url, image, duration, width, height.
    """
    _check_httpx()
    api_key = _get_api_key("pexels")

    with httpx.Client(timeout=30.0) as client:
        response = client.get(
            "https://api.pexels.com/videos/search",
            params={"query": query, "per_page": limit},
            headers={"Authorization": api_key},
        )

    if response.status_code != 200:
        raise RuntimeError(f"Pexels API error: {response.status_code}")

    data = response.json()
    results: List[Dict[str, Any]] = []
    for video in data.get("videos", []):
        results.append({
            "source": "pexels",
            "id": video.get("id"),
            "url": video.get("url", ""),
            "image": video.get("image", ""),
            "duration": video.get("duration", 0),
            "width": video.get("width", 0),
            "height": video.get("height", 0),
        })

    return results


def search_pixabay(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Search Pixabay for stock videos.

    Args:
        query: Search query string.
        limit: Maximum number of results.

    Returns:
        List of dicts with source, id, url, duration, tags.
    """
    _check_httpx()
    api_key = _get_api_key("pixabay")

    with httpx.Client(timeout=30.0) as client:
        response = client.get(
            "https://pixabay.com/api/videos/",
            params={"key": api_key, "q": query, "per_page": limit},
        )

    if response.status_code != 200:
        raise RuntimeError(f"Pixabay API error: {response.status_code}")

    data = response.json()
    results: List[Dict[str, Any]] = []
    for hit in data.get("hits", []):
        videos = hit.get("videos", {})
        large = videos.get("large", {})
        medium = videos.get("medium", {})
        url = large.get("url") or medium.get("url", "")
        results.append({
            "source": "pixabay",
            "id": hit.get("id"),
            "url": url,
            "duration": hit.get("duration", 0),
            "tags": hit.get("tags", ""),
            "width": large.get("width", 0),
            "height": large.get("height", 0),
        })

    return results


def search_stock(
    query: str,
    source: str = "both",
    limit: int = 5,
    output_dir: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Search stock footage from one or both sources.

    Args:
        query: Search query string.
        source: 'pexels', 'pixabay', or 'both'.
        limit: Max results per source.
        output_dir: If provided, download clips to this directory.

    Returns:
        Combined list of stock clip metadata.
    """
    results: List[Dict[str, Any]] = []

    if source in ("pexels", "both"):
        results.extend(search_pexels(query, limit))
    if source in ("pixabay", "both"):
        results.extend(search_pixabay(query, limit))

    if output_dir and results:
        output_dir.mkdir(parents=True, exist_ok=True)
        for clip in results:
            if clip.get("url"):
                out_path = output_dir / f"{clip['source']}_{clip['id']}.mp4"
                try:
                    download_clip(clip["url"], out_path)
                    clip["local_path"] = str(out_path)
                except RuntimeError:
                    clip["local_path"] = None

    return results


def download_clip(url: str, output: Path) -> Path:
    """Download a stock video clip.

    Args:
        url: Direct URL to the video file.
        output: Output file path.

    Returns:
        Path to downloaded file.
    """
    _check_httpx()

    with httpx.Client(timeout=60.0) as client:
        response = client.get(url)

    if response.status_code != 200:
        raise RuntimeError(f"Download failed: HTTP {response.status_code}")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(response.content)

    return output
