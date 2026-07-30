"""Tests for toolshop/video_stock.py."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from toolshop.video_stock import (
    search_pexels,
    search_pixabay,
    search_stock,
    download_clip,
    _get_api_key,
    _check_httpx,
)


def test_get_api_key_pexels():
    with patch.dict(os.environ, {"PEXELS_API_KEY": "test_key_123"}):
        assert _get_api_key("pexels") == "test_key_123"


def test_get_api_key_pixabay():
    with patch.dict(os.environ, {"PIXABAY_API_KEY": "pix_key_456"}):
        assert _get_api_key("pixabay") == "pix_key_456"


def test_get_api_key_missing():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(RuntimeError, match="API key not set"):
            _get_api_key("pexels")


def test_get_api_key_unknown_source():
    with pytest.raises(ValueError, match="Unknown stock source"):
        _get_api_key("unknown")


def test_check_httpx_missing():
    with patch("toolshop.video_stock._HAS_HTTPX", False):
        with pytest.raises(RuntimeError, match="httpx is required"):
            _check_httpx()


def test_search_pexels_mocked(tmp_path):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "videos": [
            {
                "id": 1,
                "url": "https://videos.pexels.com/video/1.mp4",
                "image": "https://images.pexels.com/1.jpg",
                "duration": 10,
                "width": 1920,
                "height": 1080,
            },
            {
                "id": 2,
                "url": "https://videos.pexels.com/video/2.mp4",
                "image": "https://images.pexels.com/2.jpg",
                "duration": 5,
                "width": 1280,
                "height": 720,
            },
        ]
    }

    with patch("toolshop.video_stock._HAS_HTTPX", True), patch(
        "toolshop.video_stock.httpx"
    ) as mock_httpx:
        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_httpx.Client.return_value.__enter__ = lambda self: mock_client
        mock_httpx.Client.return_value.__exit__ = lambda self, *a: None

        with patch.dict(os.environ, {"PEXELS_API_KEY": "test_key"}):
            results = search_pexels("neon city", limit=5)

    assert len(results) == 2
    assert results[0]["source"] == "pexels"
    assert results[0]["id"] == 1
    assert "url" in results[0]


def test_search_pexels_no_key():
    with patch("toolshop.video_stock._HAS_HTTPX", True), patch.dict(
        os.environ, {}, clear=True
    ):
        with pytest.raises(RuntimeError, match="API key not set"):
            search_pexels("test query")


def test_search_pixabay_mocked(tmp_path):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "hits": [
            {
                "id": 101,
                "videos": {
                    "large": {"url": "https://pixabay.com/video/101.mp4"},
                    "medium": {"url": "https://pixabay.com/video/101m.mp4"},
                },
                "duration": 15,
                "tags": "neon,city,night",
            },
        ]
    }

    with patch("toolshop.video_stock._HAS_HTTPX", True), patch(
        "toolshop.video_stock.httpx"
    ) as mock_httpx:
        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_httpx.Client.return_value.__enter__ = lambda self: mock_client
        mock_httpx.Client.return_value.__exit__ = lambda self, *a: None

        with patch.dict(os.environ, {"PIXABAY_API_KEY": "pix_key"}):
            results = search_pixabay("neon city", limit=5)

    assert len(results) == 1
    assert results[0]["source"] == "pixabay"
    assert results[0]["id"] == 101


def test_search_stock_both(tmp_path):
    pexels_result = [{"source": "pexels", "id": 1, "url": "https://a.com/1.mp4"}]
    pixabay_result = [{"source": "pixabay", "id": 2, "url": "https://b.com/2.mp4"}]

    with patch("toolshop.video_stock.search_pexels", return_value=pexels_result), patch(
        "toolshop.video_stock.search_pixabay", return_value=pixabay_result
    ):
        results = search_stock("neon city", source="both", limit=5)

    assert len(results) == 2
    sources = {r["source"] for r in results}
    assert sources == {"pexels", "pixabay"}


def test_search_stock_pexels_only():
    with patch("toolshop.video_stock.search_pexels", return_value=[]) as mock_pexels, patch(
        "toolshop.video_stock.search_pixabay"
    ) as mock_pixabay:
        search_stock("test", source="pexels", limit=3)

    mock_pexels.assert_called_once()
    mock_pixabay.assert_not_called()


def test_search_stock_pixabay_only():
    with patch("toolshop.video_stock.search_pexels") as mock_pexels, patch(
        "toolshop.video_stock.search_pixabay", return_value=[]
    ) as mock_pixabay:
        search_stock("test", source="pixabay", limit=3)

    mock_pixabay.assert_called_once()
    mock_pexels.assert_not_called()


def test_download_clip(tmp_path):
    url = "https://example.com/video.mp4"
    output = tmp_path / "clip.mp4"

    with patch("toolshop.video_stock._HAS_HTTPX", True), patch(
        "toolshop.video_stock.httpx"
    ) as mock_httpx:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"\x00" * 1024
        mock_client.get.return_value = mock_response
        mock_httpx.Client.return_value.__enter__ = lambda self: mock_client
        mock_httpx.Client.return_value.__exit__ = lambda self, *a: None

        result = download_clip(url, output)

    assert result == output
    assert output.exists()
    assert output.stat().st_size == 1024


def test_download_clip_failure(tmp_path):
    url = "https://example.com/bad.mp4"
    output = tmp_path / "clip.mp4"

    with patch("toolshop.video_stock._HAS_HTTPX", True), patch(
        "toolshop.video_stock.httpx"
    ) as mock_httpx:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_client.get.return_value = mock_response
        mock_httpx.Client.return_value.__enter__ = lambda self: mock_client
        mock_httpx.Client.return_value.__exit__ = lambda self, *a: None

        with pytest.raises(RuntimeError, match="Download failed"):
            download_clip(url, output)
