"""Tests for genius_adapter module (GeniusClient, RobotsPolicy, save_lyrics)."""

import json
from unittest.mock import patch, MagicMock

import pytest

from toolshop.genius_adapter import (
    GeniusClient,
    RobotsPolicy,
    SongSearchResult,
    slugify,
    save_lyrics,
)


# ---------------------------------------------------------------------------
# RobotsPolicy
# ---------------------------------------------------------------------------


def test_robots_policy_allows_by_default():
    """Test that paths not in disallow list are allowed."""
    with patch("toolshop.genius_adapter.requests") as mock_req:
        mock_resp = MagicMock()
        mock_resp.text = "User-agent: *\nDisallow: /private/\n\nUser-agent: ChatGPT-User\nDisallow: /"
        mock_resp.raise_for_status = MagicMock()
        mock_req.get.return_value = mock_resp

        policy = RobotsPolicy()
        assert policy.can_fetch("/Maya-berovic-pravo-vreme-lyrics") is True


def test_robots_policy_blocks_disallowed():
    """Test that disallowed paths are blocked."""
    with patch("toolshop.genius_adapter.requests") as mock_req:
        mock_resp = MagicMock()
        mock_resp.text = "User-agent: *\nDisallow: /private/\n\nUser-agent: ChatGPT-User\nDisallow: /"
        mock_resp.raise_for_status = MagicMock()
        mock_req.get.return_value = mock_resp

        policy = RobotsPolicy()
        assert policy.can_fetch("/private/secret") is False


def test_robots_policy_handles_fetch_error():
    """Test that robots.txt fetch failure is conservative (allow)."""
    with patch("toolshop.genius_adapter.requests") as mock_req:
        mock_req.get.side_effect = Exception("Network error")
        mock_req.RequestException = Exception

        policy = RobotsPolicy()
        assert policy.can_fetch("/anything") is True


# ---------------------------------------------------------------------------
# GeniusClient
# ---------------------------------------------------------------------------


def test_search_song_success():
    """Test search_song with mocked API response."""
    with patch("toolshop.genius_adapter.requests") as mock_req:
        mock_session = MagicMock()
        mock_req.Session.return_value = mock_session

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "response": {
                "hits": [
                    {
                        "type": "song",
                        "result": {
                            "title": "Pravo Vreme",
                            "id": 12345,
                            "url": "https://genius.com/Maya-berovic-pravo-vreme-lyrics",
                            "primary_artist": {"name": "Maya Berovic"},
                        },
                    }
                ]
            }
        }
        mock_resp.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_resp

        client = GeniusClient(access_token="test-token", delay_seconds=0)
        result = client.search_song("Pravo Vreme", "Maya Berovic")

        assert isinstance(result, SongSearchResult)
        assert result.title == "Pravo Vreme"
        assert result.artist == "Maya Berovic"
        assert result.id == 12345
        assert "genius.com" in result.url


def test_search_song_no_results():
    """Test search_song raises when no hits found."""
    with patch("toolshop.genius_adapter.requests") as mock_req:
        mock_session = MagicMock()
        mock_req.Session.return_value = mock_session

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": {"hits": []}}
        mock_resp.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_resp

        client = GeniusClient(access_token="test-token", delay_seconds=0)

        with pytest.raises(RuntimeError, match="No results"):
            client.search_song("Nonexistent Song")


def test_search_song_no_token():
    """Test that missing token raises RuntimeError."""
    with patch("toolshop.genius_adapter.requests") as mock_req, \
         patch.dict("os.environ", {}, clear=True):
        mock_session = MagicMock()
        mock_req.Session.return_value = mock_session

        client = GeniusClient(access_token="", delay_seconds=0)

        with pytest.raises(RuntimeError, match="GENIUS_ACCESS_TOKEN"):
            client.search_song("Any Song")


def test_get_song_page_success():
    """Test get_song_page with mocked HTML response."""
    with patch("toolshop.genius_adapter.requests") as mock_req:
        mock_session = MagicMock()
        mock_req.Session.return_value = mock_session

        # RobotsPolicy uses module-level requests.get
        mock_robots_resp = MagicMock()
        mock_robots_resp.text = "User-agent: *\nDisallow: /api/*\n"
        mock_robots_resp.raise_for_status = MagicMock()
        mock_req.get.return_value = mock_robots_resp

        # GeniusClient uses session.get for the song page
        mock_page_resp = MagicMock()
        mock_page_resp.text = "<html><div data-lyrics-container='true'>Lyrics here</div></html>"
        mock_page_resp.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_page_resp

        client = GeniusClient(access_token="test-token", delay_seconds=0)
        html = client.get_song_page("https://genius.com/test-lyrics")

        assert "Lyrics here" in html


def test_get_song_page_robots_blocked():
    """Test that robots.txt disallow blocks fetching."""
    with patch("toolshop.genius_adapter.requests") as mock_req:
        mock_session = MagicMock()
        mock_req.Session.return_value = mock_session

        # RobotsPolicy uses module-level requests.get
        mock_robots_resp = MagicMock()
        mock_robots_resp.text = "User-agent: *\nDisallow: /private/\n\nUser-agent: ChatGPT-User\nDisallow: /"
        mock_robots_resp.raise_for_status = MagicMock()
        mock_req.get.return_value = mock_robots_resp

        client = GeniusClient(access_token="test-token", delay_seconds=0)

        with pytest.raises(RuntimeError, match="robots.txt disallows"):
            client.get_song_page("https://genius.com/private/secret-lyrics")


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------


def test_slugify_basic():
    """Test slugify produces filesystem-safe names."""
    assert slugify("Maya Berovic") == "maya-berovic"
    assert slugify("Pravo Vreme!") == "pravo-vreme"
    assert slugify("Test / Song?") == "test-song"


def test_slugify_empty():
    """Test slugify with empty string returns 'unknown'."""
    assert slugify("") == "unknown"


def test_save_lyrics(tmp_path):
    """Test saving lyrics as JSON and TXT."""
    lyrics_data = {
        "title": "Test Song",
        "artist": "Test Artist",
        "url": "https://genius.com/test",
        "language": "sr",
        "raw_lyrics": "[Verse 1]\nTest lyrics line",
        "clean_lyrics": "Test lyrics line",
        "sections": [{"label": "Verse 1", "content": "Test lyrics line"}],
    }

    json_path, txt_path = save_lyrics(lyrics_data, tmp_path)

    assert json_path.exists()
    assert txt_path.exists()
    assert json_path.name == "test-artist-test-song.json"
    assert txt_path.name == "test-artist-test-song.txt"

    with json_path.open("r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert loaded["title"] == "Test Song"

    with txt_path.open("r", encoding="utf-8") as f:
        txt_content = f.read()
    assert txt_content == "Test lyrics line"
