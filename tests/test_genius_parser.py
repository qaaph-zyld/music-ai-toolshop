"""Tests for genius_parser.GeniusLyricsParser."""

import pytest

from toolshop.genius_parser import (
    GeniusLyricsParser,
    ParsedLyrics,
    Section,
)


SAMPLE_HTML = """
<html>
<head>
  <meta property="og:title" content="Maya Berovic (Ft. Buba Corelli) \u2013 Pravo Vreme" />
</head>
<body>
  <h1>Pravo Vreme Lyrics</h1>
  <div data-lyrics-container="true">
2 Contributors
Pravo Vreme Lyrics
[Verse 1]
Prva linija teksta
Druga linija teksta

[Chorus]
Ovo je refren
Ovo je drugi red
  </div>
  <div data-lyrics-container="true">
[Verse 2]
Treci verse linija
  </div>
</body>
</html>
"""


SAMPLE_HTML_OLD = """
<html>
<body>
  <h1>Old Song</h1>
  <div class="lyrics">
[Verse 1]
Old style lyrics line 1
Old style lyrics line 2
  </div>
</body>
</html>
"""


SAMPLE_HTML_NO_LYRICS = """
<html><body><h1>No Lyrics</h1></body></html>
"""


def test_parse_basic():
    """Test basic parsing with data-lyrics-container."""
    parser = GeniusLyricsParser()
    result = parser.parse(SAMPLE_HTML, url="https://genius.com/test")

    assert isinstance(result, ParsedLyrics)
    assert result.title == "Pravo Vreme"
    assert result.artist == "Maya Berovic"
    assert result.url == "https://genius.com/test"
    assert "Prva linija teksta" in result.raw_lyrics
    assert "Ovo je refren" in result.raw_lyrics
    assert "Treci verse linija" in result.raw_lyrics
    # Header junk should be stripped
    assert "2 Contributors" not in result.raw_lyrics
    assert "Pravo Vreme Lyrics" not in result.raw_lyrics


def test_parse_strips_lyrics_suffix_from_title():
    """Test that 'Lyrics' suffix is stripped from h1 title."""
    parser = GeniusLyricsParser()
    result = parser.parse(SAMPLE_HTML)
    assert not result.title.lower().endswith("lyrics")


def test_parse_sections():
    """Test that sections are correctly split by [Label] markers."""
    parser = GeniusLyricsParser()
    result = parser.parse(SAMPLE_HTML)

    labels = [s.label for s in result.sections]
    assert "Verse 1" in labels
    assert "Chorus" in labels
    assert "Verse 2" in labels

    verse1 = next(s for s in result.sections if s.label == "Verse 1")
    assert "Prva linija teksta" in verse1.content
    assert "Druga linija teksta" in verse1.content


def test_parse_clean_lyrics_preserves_labels():
    """Test that clean lyrics preserve section labels by default."""
    parser = GeniusLyricsParser(strip_section_labels=False)
    result = parser.parse(SAMPLE_HTML)

    assert "[Verse 1]" in result.clean_lyrics
    assert "[Chorus]" in result.clean_lyrics
    assert "Prva linija teksta" in result.clean_lyrics


def test_parse_clean_lyrics_strips_labels():
    """Test that clean lyrics strip section labels when configured."""
    parser = GeniusLyricsParser(strip_section_labels=True)
    result = parser.parse(SAMPLE_HTML)

    assert "[Verse 1]" not in result.clean_lyrics
    assert "[Chorus]" not in result.clean_lyrics
    assert "Prva linija teksta" in result.clean_lyrics


def test_parse_fallback_old_div():
    """Test fallback to div.lyrics when data-lyrics-container not found."""
    parser = GeniusLyricsParser()
    result = parser.parse(SAMPLE_HTML_OLD)

    assert result.title == "Old Song"
    assert "Old style lyrics line 1" in result.raw_lyrics
    assert "Old style lyrics line 2" in result.raw_lyrics


def test_parse_no_lyrics_raises():
    """Test that missing lyrics containers raise RuntimeError."""
    parser = GeniusLyricsParser()
    with pytest.raises(RuntimeError, match="No lyrics container"):
        parser.parse(SAMPLE_HTML_NO_LYRICS)


def test_parse_with_explicit_title_artist():
    """Test that explicit title/artist overrides HTML extraction."""
    parser = GeniusLyricsParser()
    result = parser.parse(
        SAMPLE_HTML,
        title="Custom Title",
        artist="Custom Artist",
    )
    assert result.title == "Custom Title"
    assert result.artist == "Custom Artist"


def test_to_dict():
    """Test ParsedLyrics.to_dict serialization."""
    parser = GeniusLyricsParser()
    result = parser.parse(SAMPLE_HTML, url="https://genius.com/test")
    d = result.to_dict()

    assert d["title"] == "Pravo Vreme"
    assert d["artist"] == "Maya Berovic"
    assert d["url"] == "https://genius.com/test"
    assert isinstance(d["sections"], list)
    assert all("label" in s and "content" in s for s in d["sections"])
