"""Smoke tests for the Flask server."""
from __future__ import annotations

import pytest

import server


@pytest.fixture
def client():
    server.app.config["TESTING"] = True
    with server.app.test_client() as client:
        yield client


def test_health_endpoint(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True
    assert "repos" in data


def test_tools_endpoint(client):
    resp = client.get("/api/tools")
    assert resp.status_code == 200
    tools = resp.get_json()
    assert len(tools) == 6
    ids = {t["id"] for t in tools}
    assert ids == {
        "stem_extractor",
        "vocal_restore",
        "clap_match",
        "vocal_qc",
        "neutone_preview",
        "master_bus_preview",
    }


def test_index_page(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Music AI Toolshop" in resp.data
