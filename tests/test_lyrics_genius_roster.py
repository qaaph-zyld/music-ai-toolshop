"""Tests for Genious_lyrics_extractor/extract_roster.py (P3 roster batch).

All tests use fake Genius objects — no network, no token required.
"""

import json
import sys
from pathlib import Path

import pytest

_extractor_dir = Path(__file__).resolve().parent.parent / "Genious_lyrics_extractor"
if str(_extractor_dir) not in sys.path:
    sys.path.insert(0, str(_extractor_dir))

import extract_roster


# ---------------------------------------------------------------------------
# Fixtures / fakes
# ---------------------------------------------------------------------------

ROSTER = [
    {"name": "Fox", "folder": "fox", "cohort": "drill_trap",
     "variants": ["fox", "branko kljaić"]},
    {"name": "Surreal", "folder": "surreal", "cohort": "drill_trap",
     "variants": ["surreal", "filip arsenijević"]},
    {"name": "Zera", "folder": "zera", "cohort": "drill_trap",
     "variants": ["zera", "marina pezerović"]},
    {"name": "Zoi", "folder": "zoi", "cohort": "pop",
     "variants": ["zoi", "sara šekularac"]},
]


class FakeSong:
    def __init__(self, id, title, primary, featured=None, lyrics="la\nla", url="u"):
        self.id = id
        self.title = title
        self.primary_artist = {"name": primary}
        self.featured_artists = [{"name": f} for f in (featured or [])]
        self.lyrics = lyrics
        self.url = url


class FakeArtist:
    def __init__(self, name, id, songs):
        self.name = name
        self.id = id
        self.songs = songs


class FakeGenius:
    """Stands in for lyricsgenius.Genius; scriptable resolution."""

    def __init__(self, *a, **kw):
        self._artist = None

    def set_artist(self, artist):
        self._artist = artist

    def search_artist(self, *a, **kw):
        return self._artist

    def search_artists(self, name, per_page=5):
        return {"sections": [{"hits": [{"result": {"id": self._artist.id, "name": self._artist.name}}]}]}


def _fake_lyricsgenius(monkeypatch, artist):
    fake = FakeGenius()
    fake.set_artist(artist)

    class FakeModule:
        Genius = staticmethod(lambda *a, **kw: fake)

    monkeypatch.setattr(extract_roster, "lyricsgenius", FakeModule)
    monkeypatch.setattr(extract_roster, "load_token", lambda: "fake-token")
    return fake


def _roster_file(tmp_path, roster=ROSTER):
    p = tmp_path / "roster.json"
    p.write_text(json.dumps({"artists": roster}), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# categorize_song
# ---------------------------------------------------------------------------

FOX = ROSTER[0]
SURREAL = ROSTER[1]
ZERA = ROSTER[2]
ZOI = ROSTER[3]


def test_categorize_solo():
    assert extract_roster.categorize_song("Fox", [], ROSTER, FOX) == "fox-solo"


def test_categorize_solo_nonroster_feature():
    # Non-roster featured artist doesn't break the solo tag
    assert extract_roster.categorize_song("Fox", ["Rasta"], ROSTER, FOX) == "fox-solo"


def test_categorize_featured():
    # Song primarily by non-roster artist, fetched artist is featured
    assert extract_roster.categorize_song("Rasta", ["Fox"], ROSTER, FOX) == "fox-featured"


def test_categorize_duo_sorted():
    # two roster artists on one song -> sorted-folder duo dir
    assert extract_roster.categorize_song("Fox", ["Surreal"], ROSTER, FOX) == "fox-surreal-duo"
    assert extract_roster.categorize_song("Surreal", ["Fox"], ROSTER, SURREAL) == "fox-surreal-duo"


def test_categorize_trio():
    assert extract_roster.categorize_song(
        "Fox", ["Surreal", "Zera"], ROSTER, FOX
    ) == "fox-surreal-zera-trio"


def test_categorize_other_collab():
    # Fetched artist absent from both fields -> other-collab
    assert extract_roster.categorize_song("Rasta", ["Jala Brat"], ROSTER, FOX) == "other-collab"


def test_categorize_cross_cohort_duo():
    assert extract_roster.categorize_song("Zoi", ["Zera"], ROSTER, ZOI) == "zera-zoi-duo"


# ---------------------------------------------------------------------------
# resolved_name_matches
# ---------------------------------------------------------------------------

def test_resolved_exact():
    assert extract_roster.resolved_name_matches("Fox", FOX)


def test_resolved_variant():
    assert extract_roster.resolved_name_matches("Branko Kljaić", FOX)


def test_resolved_mismatch_diacritic():
    # Žera (different artist) must NOT satisfy Zera's variants
    zera = {"name": "Zera", "folder": "zera", "cohort": "drill_trap",
            "variants": ["zera", "marina pezerović"]}
    assert not extract_roster.resolved_name_matches("Žera", zera)


def test_resolved_word_boundary_generic_names():
    # Word-boundary: 'Fox' matches 'Fox in Socks' but NOT 'Fleet Foxes'
    assert extract_roster.resolved_name_matches("Fox in Socks", FOX)
    assert not extract_roster.resolved_name_matches("Fleet Foxes", FOX)
    assert not extract_roster.resolved_name_matches("Foxes", FOX)
    assert not extract_roster.resolved_name_matches("Totally Different", FOX)


# ---------------------------------------------------------------------------
# status roundtrip
# ---------------------------------------------------------------------------

def test_status_roundtrip(tmp_path):
    p = tmp_path / "_fetch_status_g3.json"
    st = {"artists": {"fox": {"status": "done", "done_song_ids": [1, 2]}}}
    extract_roster.save_status(p, st)
    loaded = extract_roster.load_status(p)
    assert loaded["artists"]["fox"]["status"] == "done"
    assert loaded["artists"]["fox"]["done_song_ids"] == [1, 2]


def test_status_missing_file(tmp_path):
    assert extract_roster.load_status(tmp_path / "nope.json") == {"artists": {}}


# ---------------------------------------------------------------------------
# end-to-end fetch loop (mocked)
# ---------------------------------------------------------------------------

def _run_main(monkeypatch, tmp_path, argv):
    import extract_artists
    monkeypatch.setattr(extract_artists, "load_token", lambda: "fake-token")
    monkeypatch.setattr(extract_roster, "load_token", lambda: "fake-token")
    monkeypatch.setattr(sys, "argv", argv)
    extract_roster.main()


def test_main_writes_songs_and_status(monkeypatch, tmp_path):
    artist = FakeArtist("Fox", 4242, [
        FakeSong(1, "Trep Bog", "Fox"),
        FakeSong(2, "Ja Sam U Gasu", "Fox", featured=["Surreal"]),
        FakeSong(3, "Someone Else Song", "Rasta", featured=["Fox"]),
        FakeSong(4, "Empty Track", "Fox", lyrics=""),
    ])
    _fake_lyricsgenius(monkeypatch, artist)
    roster_p = _roster_file(tmp_path)
    outdir = tmp_path / "genius"
    _run_main(monkeypatch, tmp_path, [
        "extract_roster.py", "--roster", str(roster_p),
        "--outdir", str(outdir), "--artist", "Fox",
    ])

    assert (outdir / "fox-solo").is_dir()
    assert (outdir / "fox-solo" / "fox-trep-bog.json").exists()
    assert (outdir / "fox-surreal-duo" / "fox-ja-sam-u-gasu.json").exists()
    assert (outdir / "fox-featured").is_dir()
    # no-lyrics song -> index entry only, no files
    assert not (outdir / "fox-solo" / "fox-empty-track.json").exists()

    st = json.loads((outdir / "_fetch_status_g3.json").read_text(encoding="utf-8"))
    e = st["artists"]["fox"]
    assert e["status"] == "done"
    assert e["genius_artist_id"] == 4242
    assert set(e["done_song_ids"]) == {1, 2, 3, 4}


def test_main_resolve_mismatch_skips(monkeypatch, tmp_path):
    artist = FakeArtist("Žera", 999, [FakeSong(1, "X", "Žera")])
    _fake_lyricsgenius(monkeypatch, artist)
    roster_p = _roster_file(tmp_path, [r for r in ROSTER if r["name"] == "Zera"])
    outdir = tmp_path / "genius"
    _run_main(monkeypatch, tmp_path, [
        "extract_roster.py", "--roster", str(roster_p),
        "--outdir", str(outdir), "--artist", "Zera",
    ])
    st = json.loads((outdir / "_fetch_status_g3.json").read_text(encoding="utf-8"))
    assert st["artists"]["zera"]["status"] == "resolve_mismatch"
    assert st["artists"]["zera"]["resolved_name"] == "Žera"
    assert not list(outdir.glob("*/"))  # nothing written except status/summary


def test_main_resume_skips_done_ids(monkeypatch, tmp_path):
    artist = FakeArtist("Fox", 7, [
        FakeSong(1, "A", "Fox"),
        FakeSong(2, "B", "Fox"),
    ])
    _fake_lyricsgenius(monkeypatch, artist)
    roster_p = _roster_file(tmp_path)
    outdir = tmp_path / "genius"
    # Pre-seed status: song 1 already done
    outdir.mkdir(parents=True)
    (outdir / "_fetch_status_g3.json").write_text(json.dumps({
        "artists": {"fox": {"status": "in_progress", "done_song_ids": [1]}}
    }), encoding="utf-8")

    _run_main(monkeypatch, tmp_path, [
        "extract_roster.py", "--roster", str(roster_p),
        "--outdir", str(outdir), "--artist", "Fox", "--resume",
    ])
    assert not (outdir / "fox-solo" / "fox-a.json").exists()
    assert (outdir / "fox-solo" / "fox-b.json").exists()
    st = json.loads((outdir / "_fetch_status_g3.json").read_text(encoding="utf-8"))
    assert st["artists"]["fox"]["status"] == "done"


def test_main_limit_marks_in_progress(monkeypatch, tmp_path):
    artist = FakeArtist("Fox", 7, [FakeSong(i, f"S{i}", "Fox") for i in range(5)])
    _fake_lyricsgenius(monkeypatch, artist)
    roster_p = _roster_file(tmp_path)
    outdir = tmp_path / "genius"
    _run_main(monkeypatch, tmp_path, [
        "extract_roster.py", "--roster", str(roster_p),
        "--outdir", str(outdir), "--artist", "Fox", "--limit", "2",
    ])
    st = json.loads((outdir / "_fetch_status_g3.json").read_text(encoding="utf-8"))
    assert st["artists"]["fox"]["status"] == "in_progress"
    assert len(list((outdir / "fox-solo").glob("*.json"))) == 2


def test_dry_run_no_fetch(monkeypatch, tmp_path, capsys):
    artist = FakeArtist("Fox", 4242, [FakeSong(1, "A", "Fox")])
    _fake_lyricsgenius(monkeypatch, artist)
    roster_p = _roster_file(tmp_path, ROSTER)
    outdir = tmp_path / "genius"
    _run_main(monkeypatch, tmp_path, [
        "extract_roster.py", "--roster", str(roster_p),
        "--outdir", str(outdir), "--artist", "Fox", "--dry-run",
    ])
    out = capsys.readouterr().out
    assert "DRY RUN" in out
    assert "id=4242" in out
    assert not outdir.exists() or not list(outdir.rglob("*.json"))
