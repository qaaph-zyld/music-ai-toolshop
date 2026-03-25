import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from toolshop.yt_scraper_adapter import search, get_info, download_audio


def test_search_basic():
    """Test search function with mocked results"""
    with patch("toolshop.yt_scraper_adapter.yt_dlp.YoutubeDL") as mock_ydl_class:
        mock_ydl = MagicMock()
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl

        # Mock search results - yt_dlp returns a dict with entries list
        mock_result = {
            "entries": [
                {
                    "id": "test123",
                    "title": "Test Song",
                    "duration": 180,
                    "channel": "Test Channel",
                    "view_count": 1000000,
                    "tags": ["music", "test"],
                }
            ]
        }
        mock_ydl.extract_info.return_value = mock_result

        results = search("test query", limit=5)

        assert len(results) == 1
        assert results[0]["id"] == "test123"
        assert results[0]["title"] == "Test Song"
        assert results[0]["duration"] == 180


def test_search_with_limit():
    """Test search function respects limit parameter"""
    with patch("toolshop.yt_scraper_adapter.yt_dlp.YoutubeDL") as mock_ydl_class:
        mock_ydl = MagicMock()
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl

        # Mock results - ytsearch3:query returns exactly 3 results
        mock_result = {
            "entries": [{"id": f"test{i}", "title": f"Test Song {i}"} for i in range(3)]
        }
        mock_ydl.extract_info.return_value = mock_result

        results = search("test query", limit=3)

        assert len(results) == 3
        assert results[0]["id"] == "test0"
        assert results[2]["id"] == "test2"

        # Verify the search URL was constructed correctly
        mock_ydl.extract_info.assert_called_once_with(
            "ytsearch3:test query", download=False
        )


def test_get_info_success():
    """Test get_info with valid video"""
    with patch("toolshop.yt_scraper_adapter.yt_dlp.YoutubeDL") as mock_ydl_class:
        mock_ydl = MagicMock()
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl

        mock_info = {
            "id": "test123",
            "title": "Test Song",
            "duration": 180,
            "channel": "Test Channel",
            "view_count": 1000000,
            "tags": ["music", "test"],
            "upload_date": "20240101",
        }

        mock_ydl.extract_info.return_value = mock_info

        result = get_info("test123")

        assert result["id"] == "test123"
        assert result["title"] == "Test Song"
        assert result["duration"] == 180
        assert result["channel"] == "Test Channel"


def test_get_info_missing_fields():
    """Test get_info handles missing optional fields gracefully"""
    with patch("toolshop.yt_scraper_adapter.yt_dlp.YoutubeDL") as mock_ydl_class:
        mock_ydl = MagicMock()
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl

        # Minimal info
        mock_info = {"id": "test123", "title": "Test Song"}

        mock_ydl.extract_info.return_value = mock_info

        result = get_info("test123")

        assert result["id"] == "test123"
        assert result["title"] == "Test Song"
        assert result.get("duration") is None
        assert result.get("channel") is None


def test_download_audio_success(tmp_path):
    """Test download_audio successful download"""
    with patch("toolshop.yt_scraper_adapter.yt_dlp.YoutubeDL") as mock_ydl_class:
        mock_ydl = MagicMock()
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl

        # Create a fake downloaded file
        expected_path = tmp_path / "test_song.wav"
        expected_path.touch()

        # Mock the download call
        mock_ydl.download.return_value = None

        result = download_audio("http://youtube.com/watch?v=test123", tmp_path, "wav")

        assert result == expected_path


def test_download_audio_default_format(tmp_path):
    """Test download_audio uses default format when not specified"""
    with patch("toolshop.yt_scraper_adapter.yt_dlp.YoutubeDL") as mock_ydl_class:
        mock_ydl = MagicMock()
        mock_ydl_class.return_value.__enter__.return_value = mock_ydl

        # Create a fake downloaded file with default format
        expected_path = tmp_path / "test_song.wav"
        expected_path.touch()

        mock_ydl.download.return_value = None

        # Call without format parameter
        result = download_audio("http://youtube.com/watch?v=test123", tmp_path)

        assert result == expected_path


@patch("toolshop.yt_scraper_adapter.yt_dlp")
def test_download_error_handling(mock_yt_dlp, tmp_path):
    """Test download_audio handles errors gracefully"""
    mock_yt_dlp.YoutubeDL.side_effect = Exception("Download failed")

    with pytest.raises(Exception, match="Download failed"):
        download_audio("http://youtube.com/watch?v=test123", tmp_path)
