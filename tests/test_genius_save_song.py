"""Tests for Genious_lyrics_extractor/extract_artists.py save_song.

Slug-collision guard (G3 closeout): two distinct songs can produce the same
<artist>-<title> filename ("Tenzija"×2, Lacku ids 7117386/5446636). A second
song for a *different* genius id must get an id-suffixed filename instead of
silently overwriting the existing file. Same id → overwrite (resume).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_extractor_dir = Path(__file__).resolve().parent.parent / "Genious_lyrics_extractor"
if str(_extractor_dir) not in sys.path:
    sys.path.insert(0, str(_extractor_dir))

from extract_artists import save_song  # noqa: E402


class FakeSong:
    """lyricsgenius 3.x Song shape: id lives in _body, not .id."""

    def __init__(self, id, title, primary, lyrics="la\nla"):
        self._body = {"id": id}
        self.title = title
        self.primary_artist = {"name": primary}
        self.featured_artists = []
        self.lyrics = lyrics
        self.url = "u"


def test_slug_collision_different_id_gets_suffix(tmp_path):
    s1 = FakeSong(7117386, "Tenzija", "Lacku", lyrics="prva")
    s2 = FakeSong(5446636, "Tenzija", "Lacku", lyrics="druga")

    e1 = save_song(s1, "lacku-solo", tmp_path, set())
    e2 = save_song(s2, "lacku-solo", tmp_path, set())

    p1 = Path(e1["json_path"])
    p2 = Path(e2["json_path"])
    assert p1.name == "lacku-tenzija.json"
    assert p2.name == "lacku-tenzija-5446636.json"
    assert p1.exists() and p2.exists()
    # original file intact — not overwritten
    assert json.loads(p1.read_text(encoding="utf-8"))["genius_song_id"] == 7117386
    assert json.loads(p2.read_text(encoding="utf-8"))["genius_song_id"] == 5446636
    # .txt sidecar follows the same name
    assert p2.with_suffix(".txt").exists()


def test_same_id_overwrites_on_resume(tmp_path):
    s1 = FakeSong(42, "Song", "Artist", lyrics="first")
    save_song(s1, "a-solo", tmp_path, set())
    # resume re-fetch of the same id → same filename, content refreshed
    s2 = FakeSong(42, "Song", "Artist", lyrics="refetched")
    e2 = save_song(s2, "a-solo", tmp_path, set())
    assert Path(e2["json_path"]).name == "artist-song.json"
    assert len(list((tmp_path / "a-solo").glob("artist-song*.json"))) == 1


def test_idless_existing_file_does_not_clobber(tmp_path):
    """Legacy file with genius_song_id=None still shields via id suffix."""
    s1 = FakeSong(None, "Tenzija", "Lacku", lyrics="idless legacy")
    e1 = save_song(s1, "lacku-solo", tmp_path, set())
    s2 = FakeSong(7, "Tenzija", "Lacku", lyrics="new id song")
    e2 = save_song(s2, "lacku-solo", tmp_path, set())
    assert Path(e2["json_path"]).name == "lacku-tenzija-7.json"
    assert Path(e1["json_path"]).exists()
