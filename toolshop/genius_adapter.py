"""Genius API client and robots.txt policy handler.

Fetches song pages from Genius, respecting robots.txt rules.
Uses the Genius search API to locate song URLs by title/artist.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

try:
    import requests

    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False


def _check_requests() -> None:
    if not _HAS_REQUESTS:
        raise RuntimeError(
            "requests is required for Genius API access. "
            "Install with: pip install requests"
        )


@dataclass
class SongSearchResult:
    """Result of a Genius API song search."""

    title: str
    artist: str
    url: str
    id: int


class RobotsPolicy:
    """Check Genius robots.txt before fetching pages."""

    def __init__(
        self,
        robots_url: str = "https://genius.com/robots.txt",
        timeout: float = 10.0,
    ) -> None:
        _check_requests()
        self._robots_url = robots_url
        self._timeout = timeout
        self._disallowed: list[str] = []
        self._loaded = False

    def _load(self) -> None:
        """Fetch and parse robots.txt once.

        Only applies disallow rules from the ``User-agent: *`` section
        (or a section matching our user-agent). Rules targeting specific
        AI bots (ChatGPT, ClaudeBot, etc.) are ignored.
        """
        try:
            resp = requests.get(self._robots_url, timeout=self._timeout)
            resp.raise_for_status()
        except requests.RequestException:
            # If robots.txt is unreachable, be conservative and allow
            self._loaded = True
            return

        # Parse robots.txt into per-user-agent groups
        current_agents: list[str] = []
        applies_to_us = False

        for line in resp.text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            lower = line.lower()

            if lower.startswith("user-agent:"):
                agent = line[len("user-agent:"):].strip().lower()
                if current_agents and current_agents[-1] != agent:
                    # New group — reset
                    current_agents = []
                    applies_to_us = False
                current_agents.append(agent)
                if agent == "*" or "toolshop" in agent:
                    applies_to_us = True
                continue

            if lower.startswith("disallow:"):
                if applies_to_us:
                    path = line[len("disallow:"):].strip()
                    if path:
                        self._disallowed.append(path)

        self._loaded = True

    def can_fetch(self, path: str) -> bool:
        """Check if a URL path is allowed by robots.txt.

        Args:
            path: URL path (e.g. /Maya-berovic-pravo-vreme-lyrics).

        Returns:
            True if fetching is allowed, False if disallowed.
        """
        if not self._loaded:
            self._load()

        for disallowed in self._disallowed:
            if path.startswith(disallowed):
                return False
        return True


class GeniusClient:
    """Genius API client for song search and HTML page fetching."""

    BASE_API = "https://api.genius.com"
    BASE_WEB = "https://genius.com"

    def __init__(
        self,
        access_token: Optional[str] = None,
        timeout: float = 15.0,
        delay_seconds: float = 1.5,
        proxy: Optional[str] = None,
    ) -> None:
        _check_requests()
        self._token = access_token or os.environ.get("GENIUS_ACCESS_TOKEN", "")
        self._timeout = timeout
        self._delay = delay_seconds
        self._session = requests.Session()
        if proxy:
            self._session.proxies = {"http": proxy, "https": proxy}
        self._robots = RobotsPolicy()

    def _auth_headers(self) -> Dict[str, str]:
        if not self._token:
            raise RuntimeError(
                "GENIUS_ACCESS_TOKEN is not set. "
                "Provide it via env var or constructor argument."
            )
        return {"Authorization": f"Bearer {self._token}"}

    def _respect_delay(self) -> None:
        if self._delay > 0:
            time.sleep(self._delay)

    def search_song(self, title: str, artist: str = "") -> SongSearchResult:
        """Search Genius for a song by title and optional artist.

        Args:
            title: Song title.
            artist: Artist name (improves match accuracy).

        Returns:
            SongSearchResult with title, artist, url, and id.

        Raises:
            RuntimeError if no results found or API error.
        """
        query = f"{title} {artist}".strip()
        url = f"{self.BASE_API}/search"
        params = {"q": query}

        resp = self._session.get(
            url,
            params=params,
            headers=self._auth_headers(),
            timeout=self._timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        hits = data.get("response", {}).get("hits", [])
        if not hits:
            raise RuntimeError(f"No results found for '{query}'")

        # Find first hit that is a song
        for hit in hits:
            result = hit.get("result")
            if not result:
                continue
            if hit.get("type") == "song" or result.get("primary_artist"):
                return SongSearchResult(
                    title=result.get("title", "Unknown"),
                    artist=result.get("primary_artist", {}).get("name", "Unknown"),
                    url=result.get("url", ""),
                    id=result.get("id", 0),
                )

        raise RuntimeError(f"No song results found for '{query}'")

    def get_song_page(self, url: str) -> str:
        """Fetch the HTML content of a Genius song page.

        Checks robots.txt before fetching. Enforces request delay.

        Args:
            url: Full Genius song page URL.

        Returns:
            HTML text of the page.

        Raises:
            RuntimeError if robots.txt disallows or fetch fails.
        """
        parsed = urlparse(url)
        if not self._robots.can_fetch(parsed.path):
            raise RuntimeError(
                f"robots.txt disallows fetching {parsed.path}. "
                "Aborting to respect Genius crawl rules."
            )

        self._respect_delay()

        resp = self._session.get(url, timeout=self._timeout)
        resp.raise_for_status()
        return resp.text

    def fetch_lyrics(
        self,
        url: str,
        strip_section_labels: bool = False,
    ) -> Dict[str, Any]:
        """Fetch a Genius song page and parse lyrics.

        Convenience method combining robots check, HTML fetch, and parsing.

        Args:
            url: Full Genius song page URL.
            strip_section_labels: If True, remove [Chorus] etc. from clean lyrics.

        Returns:
            ParsedLyrics dict (see genius_parser.ParsedLyrics.to_dict).
        """
        from .genius_parser import GeniusLyricsParser

        html = self.get_song_page(url)
        parser = GeniusLyricsParser(strip_section_labels=strip_section_labels)
        parsed = parser.parse(html, url=url)
        return parsed.to_dict()


def slugify(text: str) -> str:
    """Convert text to a filesystem-safe slug."""
    import re

    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[-\s]+", "-", slug).strip("-")
    return slug or "unknown"


def save_lyrics(
    lyrics_data: Dict[str, Any],
    output_dir: str | Path,
) -> tuple[Path, Path]:
    """Save lyrics as JSON and TXT files.

    Args:
        lyrics_data: Dict from ParsedLyrics.to_dict() or fetch_lyrics().
        output_dir: Directory to write files into.

    Returns:
        Tuple of (json_path, txt_path).
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    artist = lyrics_data.get("artist", "Unknown")
    title = lyrics_data.get("title", "Unknown")
    base = f"{slugify(artist)}-{slugify(title)}"

    json_path = out / f"{base}.json"
    txt_path = out / f"{base}.txt"

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(lyrics_data, f, indent=2, ensure_ascii=False)

    with txt_path.open("w", encoding="utf-8") as f:
        f.write(lyrics_data.get("clean_lyrics", ""))

    return json_path, txt_path
