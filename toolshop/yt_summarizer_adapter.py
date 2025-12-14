"""YouTube summarization adapter.

Extracts metadata and description to generate Suno-ready prompts.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from . import yt_scraper_adapter


def get_video_context(url: str) -> Dict[str, Any]:
    """Get video metadata useful for summarization.

    Args:
        url: YouTube video URL.

    Returns:
        Dict with title, description, tags, channel info.
    """
    return yt_scraper_adapter.get_info(url)


def summarize_for_prompt(url: str, max_length: int = 200) -> str:
    """Generate a Suno-ready prompt summary from a YouTube video.

    Extracts the video title, description excerpt, and tags to create
    a compact prompt suitable for Suno music generation.

    Args:
        url: YouTube video URL.
        max_length: Maximum length of the summary (default 200 chars).

    Returns:
        A compact text string suitable for use as a Suno prompt.
    """
    info = get_video_context(url)

    title = info.get("title", "")
    description = info.get("description", "") or ""
    tags = info.get("tags", []) or []

    # Build prompt components
    parts = []

    # Clean title
    if title:
        parts.append(title)

    # Extract first meaningful line of description
    if description:
        first_line = description.split("\n")[0].strip()
        if first_line and first_line != title:
            parts.append(first_line[:100])

    # Add top tags
    if tags:
        tag_str = ", ".join(tags[:5])
        parts.append(f"Tags: {tag_str}")

    summary = " | ".join(parts)

    # Truncate if needed
    if len(summary) > max_length:
        summary = summary[: max_length - 3] + "..."

    return summary


def extract_music_keywords(url: str) -> Dict[str, Any]:
    """Extract music-relevant keywords from a YouTube video.

    Args:
        url: YouTube video URL.

    Returns:
        Dict with genre_hints, mood_hints, instrument_hints, style_hints.
    """
    info = get_video_context(url)

    title = (info.get("title") or "").lower()
    description = (info.get("description") or "").lower()
    tags = [t.lower() for t in (info.get("tags") or [])]

    # Common genre keywords
    genres = [
        "pop", "rock", "hip hop", "rap", "electronic", "edm", "house", "techno",
        "jazz", "blues", "classical", "country", "folk", "metal", "punk", "indie",
        "r&b", "soul", "reggae", "latin", "ambient", "lo-fi", "lofi", "trap",
        "dubstep", "drum and bass", "dnb", "hardcore", "hardstyle", "trance"
    ]

    # Mood keywords
    moods = [
        "happy", "sad", "energetic", "calm", "dark", "bright", "melancholic",
        "upbeat", "chill", "aggressive", "peaceful", "epic", "dreamy", "intense"
    ]

    # Instrument keywords
    instruments = [
        "guitar", "piano", "drums", "bass", "synth", "violin", "saxophone",
        "trumpet", "flute", "vocal", "vocals", "808", "strings", "orchestra"
    ]

    combined_text = f"{title} {description} {' '.join(tags)}"

    found_genres = [g for g in genres if g in combined_text]
    found_moods = [m for m in moods if m in combined_text]
    found_instruments = [i for i in instruments if i in combined_text]

    return {
        "genre_hints": found_genres[:5],
        "mood_hints": found_moods[:3],
        "instrument_hints": found_instruments[:5],
        "tags": tags[:10],
        "title": info.get("title"),
    }
