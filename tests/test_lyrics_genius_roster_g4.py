"""roster_g4.json integrity + --language plumbing (G4 lane, German corpus).

All tests use fake Genius objects — no network, no token required.
"""

import json
import sys
from pathlib import Path

import pytest

_extractor_dir = Path(__file__).resolve().parent.parent / "Genious_lyrics_extractor"
if str(_extractor_dir) not in sys.path:
    sys.path.insert(0, str(_extractor_dir))

import extract_artists
import extract_roster


ROSTER_PATH = _extractor_dir / "roster_g4.json"
EXPECTED_FOLDERS = {
    "bonez-mc", "raf-camora", "gzuz", "lx", "sa4",
    "maxwell", "187-strassenbande", "capuz",
}


# ---------------------------------------------------------------------------
# roster_g4.json shape
# ---------------------------------------------------------------------------

def _roster():
    return json.loads(ROSTER_PATH.read_text(encoding="utf-8"))["artists"]


def test_roster_has_eight_artists():
    artists = _roster()
    assert len(artists) == 8
    assert {a["folder"] for a in artists} == EXPECTED_FOLDERS


def test_roster_all_german_drill():
    for a in _roster():
        assert a["cohort"] == "german_drill", a["name"]


def test_roster_variants_nonempty_and_unique_folders():
    artists = _roster()
    folders = [a["folder"] for a in artists]
    assert len(set(folders)) == len(folders)
    for a in artists:
        assert a["name"].strip()
        assert isinstance(a["variants"], list) and a["variants"]
        assert "genius_artist_id" in a  # None until GATE G4-ROSTER pins it


# ---------------------------------------------------------------------------
# --language plumbing
# ---------------------------------------------------------------------------

class _FakeSong:
    """lyricsgenius 3.x Song shape: id in _body, not .id."""

    def __init__(self, id, title, primary, featured=None, lyrics="la\nla", url="u"):
        self._body = {"id": id}
        self.title = title
        self.primary_artist = {"name": primary}
        self.featured_artists = [{"name": f} for f in (featured or [])]
        self.lyrics = lyrics
        self.url = url


class _FakeArtist:
    def __init__(self, name, id, songs):
        self.name = name
        self._body = {"id": id}
        self.songs = songs


class _FakeGenius:
    def __init__(self, *a, **kw):
        self._artist = None

    def search_artist(self, *a, **kw):
        return self._artist


def _run(monkeypatch, tmp_path, argv, artist):
    fake = _FakeGenius()
    fake._artist = artist

    class _Module:
        Genius = staticmethod(lambda *a, **kw: fake)

    monkeypatch.setattr(extract_roster, "lyricsgenius", _Module)
    monkeypatch.setattr(extract_roster, "load_token", lambda: "fake-token")
    monkeypatch.setattr(extract_artists, "load_token", lambda: "fake-token")
    monkeypatch.setattr(sys, "argv", argv)
    extract_roster.main()


def test_language_flag_stamps_de(monkeypatch, tmp_path):
    roster = [{"name": "GZUZ", "folder": "gzuz", "cohort": "german_drill",
               "variants": ["gzuz"], "genius_artist_id": None}]
    roster_p = tmp_path / "roster.json"
    roster_p.write_text(json.dumps({"artists": roster}), encoding="utf-8")
    outdir = tmp_path / "genius-de"
    _run(monkeypatch, tmp_path, [
        "extract_roster.py", "--roster", str(roster_p),
        "--outdir", str(outdir), "--language", "de",
    ], _FakeArtist("GZUZ", 11, [_FakeSong(1, "Lied", "GZUZ")]))
    saved = json.loads(
        (outdir / "gzuz-solo" / "gzuz-lied.json").read_text(encoding="utf-8"))
    assert saved["language"] == "de"


def test_language_default_stays_none(monkeypatch, tmp_path):
    """Without --language the saved JSON keeps language=None (genius-pro behavior)."""
    roster = [{"name": "Fox", "folder": "fox", "cohort": "drill_trap",
               "variants": ["fox"], "genius_artist_id": None}]
    roster_p = tmp_path / "roster.json"
    roster_p.write_text(json.dumps({"artists": roster}), encoding="utf-8")
    outdir = tmp_path / "genius"
    _run(monkeypatch, tmp_path, [
        "extract_roster.py", "--roster", str(roster_p),
        "--outdir", str(outdir),
    ], _FakeArtist("Fox", 9, [_FakeSong(1, "Pesma", "Fox")]))
    saved = json.loads(
        (outdir / "fox-solo" / "fox-pesma.json").read_text(encoding="utf-8"))
    assert saved["language"] is None
