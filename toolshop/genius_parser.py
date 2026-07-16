"""Genius lyrics HTML parser.

Extracts and normalizes lyrics from Genius song page HTML using BeautifulSoup.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

try:
    from bs4 import BeautifulSoup

    _HAS_BS4 = True
except ImportError:
    _HAS_BS4 = False


def _check_bs4() -> None:
    if not _HAS_BS4:
        raise RuntimeError(
            "beautifulsoup4 is required for lyrics parsing. "
            "Install with: pip install beautifulsoup4"
        )


@dataclass
class Section:
    """A labelled section of lyrics (e.g. Verse 1, Chorus)."""

    label: Optional[str]
    content: str


@dataclass
class ParsedLyrics:
    """Structured result of parsing a Genius song page."""

    title: str
    artist: str
    url: str
    language: Optional[str] = None
    raw_lyrics: str = ""
    clean_lyrics: str = ""
    sections: List[Section] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "artist": self.artist,
            "url": self.url,
            "language": self.language,
            "raw_lyrics": self.raw_lyrics,
            "clean_lyrics": self.clean_lyrics,
            "sections": [
                {"label": s.label, "content": s.content} for s in self.sections
            ],
        }


_SECTION_LABEL_RE = re.compile(r"^\[(.+?)\]\s*$")


class GeniusLyricsParser:
    """Parse Genius song page HTML into structured lyrics."""

    def __init__(self, strip_section_labels: bool = False) -> None:
        self.strip_section_labels = strip_section_labels

    def parse(
        self,
        html: str,
        url: str = "",
        title: Optional[str] = None,
        artist: Optional[str] = None,
    ) -> ParsedLyrics:
        """Parse HTML and return a ParsedLyrics object.

        Args:
            html: Raw HTML of the Genius song page.
            url: The source URL (stored in output).
            title: Override for song title (otherwise extracted from HTML).
            artist: Override for artist (otherwise extracted from HTML).

        Returns:
            ParsedLyrics with raw, clean, and sectioned lyrics.
        """
        _check_bs4()
        soup = BeautifulSoup(html, "html.parser")

        if title is None:
            title = self._extract_title(soup)
        if artist is None:
            artist = self._extract_artist(soup)

        raw_lyrics = self._extract_lyrics_text(soup)
        sections = self._split_sections(raw_lyrics)
        clean_lyrics = self._clean_text(raw_lyrics, strip_labels=self.strip_section_labels)

        return ParsedLyrics(
            title=title,
            artist=artist,
            url=url,
            raw_lyrics=raw_lyrics,
            clean_lyrics=clean_lyrics,
            sections=sections,
        )

    # ------------------------------------------------------------------
    # Internal extraction helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_title(soup: BeautifulSoup) -> str:
        h1 = soup.find("h1")
        if h1:
            text = h1.get_text(strip=True)
            # Genius titles are often "Title Lyrics" — strip trailing "Lyrics"
            if text.lower().endswith(" lyrics"):
                text = text[: -len(" lyrics")].strip()
            return text
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            # og:title format: "Artist (Ft. ...) – Title"
            content = og_title["content"]
            if "\u2013" in content or " - " in content:
                sep = "\u2013" if "\u2013" in content else " - "
                parts = content.rsplit(sep, 1)
                if len(parts) == 2:
                    return parts[1].strip()
            return content
        return "Unknown"

    @staticmethod
    def _extract_artist(soup: BeautifulSoup) -> str:
        a = soup.find("a", attrs={"data-artist_id": True})
        if a:
            return a.get_text(strip=True)
        # Try og:title meta tag: format is "Artist (Ft. ...) – Title"
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            content = og_title["content"]
            # Use en-dash (\u2013) or hyphen as separator
            sep = None
            if "\u2013" in content:
                sep = "\u2013"
            elif " - " in content:
                sep = " - "
            if sep:
                parts = content.rsplit(sep, 1)
                if len(parts) == 2:
                    artist_part = parts[0].strip()
                    # Remove featuring info in parentheses for cleaner name
                    # e.g. "Maya Berović (Ft. Buba Corelli)" -> "Maya Berović"
                    paren_idx = artist_part.find(" (Ft.")
                    if paren_idx == -1:
                        paren_idx = artist_part.find(" (ft.")
                    if paren_idx != -1:
                        artist_part = artist_part[:paren_idx].strip()
                    return artist_part
        # Fallback: h2 (often contains title, not artist — use with caution)
        return "Unknown"

    @staticmethod
    def _extract_lyrics_text(soup: BeautifulSoup) -> str:
        """Extract raw lyrics text from the page, preserving line breaks."""
        # Current Genius layout: div[data-lyrics-container="true"]
        containers = soup.find_all("div", attrs={"data-lyrics-container": "true"})
        if not containers:
            # Fallback: older div.lyrics pattern
            containers = soup.find_all("div", class_="lyrics")

        if not containers:
            raise RuntimeError(
                "No lyrics container found. The page structure may have changed."
            )

        parts: List[str] = []
        for c in containers:
            text = c.get_text(separator="\n")
            parts.append(text)

        raw = "\n".join(parts).strip()
        # Strip Genius header junk: leading "N Contributors" and "Title Lyrics" lines
        raw = GeniusLyricsParser._strip_header_junk(raw)
        return raw

    @staticmethod
    def _strip_header_junk(raw: str) -> str:
        """Remove leading Genius metadata lines (contributors count, title echo)."""
        lines = raw.split("\n")
        skip = 0
        for line in lines:
            stripped = line.strip()
            if not stripped:
                skip += 1
                continue
            # Match "N Contributors" pattern
            if re.match(r"^\d+\s+Contributors?$", stripped, re.IGNORECASE):
                skip += 1
                continue
            # Match "Title Lyrics" echo (ends with "Lyrics" and has no section bracket)
            if stripped.lower().endswith(" lyrics") and not stripped.startswith("["):
                skip += 1
                continue
            # Match "N Embed" pattern (sometimes appears)
            if re.match(r"^\d+\s+Embed$", stripped, re.IGNORECASE):
                skip += 1
                continue
            break
        return "\n".join(lines[skip:])

    @staticmethod
    def _split_sections(raw: str) -> List[Section]:
        """Split raw lyrics into sections based on [Label] markers."""
        lines = raw.split("\n")
        sections: List[Section] = []
        current_label: Optional[str] = None
        current_lines: List[str] = []

        for line in lines:
            stripped = line.strip()
            match = _SECTION_LABEL_RE.match(stripped)
            if match:
                if current_lines:
                    sections.append(
                        Section(label=current_label, content="\n".join(current_lines).strip())
                    )
                    current_lines = []
                current_label = match.group(1).strip()
            else:
                current_lines.append(line)

        if current_lines:
            sections.append(
                Section(label=current_label, content="\n".join(current_lines).strip())
            )

        return sections

    @staticmethod
    def _clean_text(raw: str, strip_labels: bool = False) -> str:
        """Normalize whitespace and optionally strip section labels.

        Args:
            raw: Raw lyrics text.
            strip_labels: If True, remove [Chorus], [Verse 1], etc.

        Returns:
            Cleaned lyrics text.
        """
        lines = raw.split("\n")
        cleaned: List[str] = []
        for line in lines:
            stripped = line.strip()
            if strip_labels and _SECTION_LABEL_RE.match(stripped):
                continue
            # Normalize internal whitespace but preserve the line
            normalized = re.sub(r"[ \t]+", " ", stripped)
            if normalized:
                cleaned.append(normalized)

        return "\n".join(cleaned)
