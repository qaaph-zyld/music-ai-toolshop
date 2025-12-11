"""YouTube scraping adapter.

Uses yt-dlp as a Python library for search and metadata extraction.
Can be swapped out for the yt_scraper repo once that exists.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

try:
    import yt_dlp
    _HAS_YTDLP = True
except ImportError:
    _HAS_YTDLP = False


def _check_ytdlp() -> None:
    if not _HAS_YTDLP:
        raise RuntimeError(
            "yt-dlp is required for YouTube tools. Install with: pip install yt-dlp"
        )


def search(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Search YouTube for videos matching query.

    Args:
        query: Search query string.
        limit: Max number of results (default 10).

    Returns:
        List of dicts with id, title, channel, duration, url.
    """
    _check_ytdlp()
    search_url = f"ytsearch{limit}:{query}"

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "skip_download": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(search_url, download=False)

    videos: List[Dict[str, Any]] = []
    entries = result.get("entries", []) if result else []
    
    for entry in entries:
        if not entry:
            continue
        videos.append({
            "id": entry.get("id"),
            "title": entry.get("title"),
            "channel": entry.get("channel") or entry.get("uploader"),
            "duration": entry.get("duration"),
            "url": f"https://www.youtube.com/watch?v={entry.get('id')}",
        })

    return videos


def get_info(video_id_or_url: str) -> Dict[str, Any]:
    """Get metadata for a single YouTube video.

    Args:
        video_id_or_url: YouTube video ID or full URL.

    Returns:
        Dict with title, channel, duration, description, tags, etc.
    """
    _check_ytdlp()

    # Normalize to URL
    if not video_id_or_url.startswith("http"):
        url = f"https://www.youtube.com/watch?v={video_id_or_url}"
    else:
        url = video_id_or_url

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        data = ydl.extract_info(url, download=False)

    return {
        "id": data.get("id"),
        "title": data.get("title"),
        "channel": data.get("channel") or data.get("uploader"),
        "duration": data.get("duration"),
        "description": data.get("description"),
        "tags": data.get("tags") or [],
        "view_count": data.get("view_count"),
        "upload_date": data.get("upload_date"),
        "url": url,
    }


def download_audio(
    video_id_or_url: str,
    output_dir: Path,
    format: str = "wav",
) -> Path:
    """Download audio from a YouTube video.

    Args:
        video_id_or_url: YouTube video ID or URL.
        output_dir: Directory to save downloaded audio.
        format: Output audio format (default wav).

    Returns:
        Path to downloaded audio file.
    """
    _check_ytdlp()

    if not video_id_or_url.startswith("http"):
        url = f"https://www.youtube.com/watch?v={video_id_or_url}"
    else:
        url = video_id_or_url

    output_dir.mkdir(parents=True, exist_ok=True)
    output_template = str(output_dir / "%(title)s.%(ext)s")

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": format,
        }],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    # Find the downloaded file
    for f in output_dir.glob(f"*.{format}"):
        return f

    raise RuntimeError("Download succeeded but output file not found")
