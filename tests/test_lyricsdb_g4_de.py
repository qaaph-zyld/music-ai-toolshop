"""G4 lane — German corpus (``genius-de``) ingest behavior.

Covers: cohort maps, umlaut/ß ASCII fold, German section labels, the
language-aware syllable dispatch (exact ``language == 'de'``), the
``populate_rhymes`` skip for de rows, and the word-boundary cohort
fallback for short (<=4 char) COHORT_MAP keys.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from toolshop.lyricsdb import (
    COHORT_MAP,
    _FOLDER_COHORT_MAP,
    build_database,
    normalize_text,
    parse_section_label,
)


def _song(title: str, artist: str, lines: list, **kw) -> dict:
    body = "\n".join(lines)
    song = {
        "title": title,
        "artist": artist,
        "primary_artist": artist,
        "featured_artists": [],
        "url": "",
        "language": None,
        "raw_lyrics": body,
        "clean_lyrics": body,
        "sections": [{"label": None, "content": body}],
    }
    song.update(kw)
    return song


def _write(root: Path, category: str, filename: str, song: dict) -> Path:
    cat = root / category
    cat.mkdir(parents=True, exist_ok=True)
    p = cat / filename
    p.write_text(json.dumps(song, ensure_ascii=False), encoding="utf-8")
    return p


def _rows(db: Path, sql: str, params=()):
    conn = sqlite3.connect(db)
    out = conn.execute(sql, params).fetchall()
    conn.close()
    return out


# ── ASCII fold: German chars ──────────────────────────────────────────

def test_fold_umlauts_and_eszett():
    assert normalize_text("Straße") == "strasse"
    assert normalize_text("schön") == "schoen"
    assert normalize_text("für") == "fuer"
    assert normalize_text("Häuser") == "haeuser"


def test_fold_serbian_unchanged():
    assert normalize_text("Zdravo čoveče, đak šeta") == "zdravo covece, djak seta"


# ── German section labels ─────────────────────────────────────────────

def test_german_section_labels():
    assert parse_section_label("Strophe 1").type == "strofa"
    assert parse_section_label("Strophe 1").type_number == 1
    assert parse_section_label("Zwischenspiel").type == "interlude"
    assert parse_section_label("Post-Refrain").type == "postrefren"
    assert parse_section_label("Nachrefrain").type == "postrefren"


# ── Cohort maps ───────────────────────────────────────────────────────

def test_german_cohort_entries():
    for name in ("Bonez MC", "RAF Camora", "GZUZ", "LX", "Sa4",
                 "Maxwell", "187 Strassenbande", "Capuz"):
        assert COHORT_MAP[name] == "german_drill", name


def test_german_folder_cohort_entries():
    for folder in ("bonez-mc", "raf-camora", "gzuz", "lx", "sa4",
                   "maxwell", "187-strassenbande", "capuz"):
        assert _FOLDER_COHORT_MAP[folder] == "german_drill", folder


# ── Word-boundary fallback for short keys ─────────────────────────────

def test_short_key_no_substring_match(tmp_path):
    """'Fox' (3 chars) must NOT tag 'Fleet Foxes' as drill_trap."""
    root = tmp_path / "genius"
    _write(root, "fleetfoxes-solo", "ff-song.json",
           _song("Song X", "Fleet Foxes", ["neka linija"]))
    db = tmp_path / "t.db"
    build_database(root=root, db_path=db, corpus="genius-pro")
    assert _rows(db, "SELECT genre_cohort FROM songs")[0][0] is None


def test_short_key_word_boundary_match(tmp_path):
    """'Fox' at a word boundary still matches: 'Samantha Fox' -> drill_trap."""
    root = tmp_path / "genius"
    _write(root, "samfox-solo", "sf-song.json",
           _song("Song Y", "Samantha Fox", ["neka linija"]))
    db = tmp_path / "t.db"
    build_database(root=root, db_path=db, corpus="genius-pro")
    assert _rows(db, "SELECT genre_cohort FROM songs")[0][0] == "drill_trap"


def test_long_key_substring_still_matches(tmp_path):
    """Long keys keep substring behavior: 'Bonez MC & RAF Camora' -> german_drill."""
    root = tmp_path / "genius-de"
    _write(root, "x-solo", "x-duo.json",
           _song("Z", "Bonez MC & RAF Camora", ["eine zeile"], language="de"))
    db = tmp_path / "t.db"
    build_database(root=root, db_path=db, corpus="genius-de")
    assert _rows(db, "SELECT genre_cohort FROM songs")[0][0] == "german_drill"


# ── Language dispatch (syllables) ─────────────────────────────────────

def _line_syllables(db: Path, title: str) -> int:
    rows = _rows(
        db,
        """SELECT l.syllable_count FROM lines l
           JOIN sections s ON l.section_id = s.id
           JOIN songs g ON s.song_id = g.id
           WHERE g.title = ?""",
        (title,),
    )
    assert len(rows) == 1
    return rows[0][0]


def test_de_language_uses_german_counter(tmp_path):
    """'Auto fährt': de -> 3 (au|o + ä), sr -> 4 (a,u,o + a)."""
    root = tmp_path / "genius-de"
    _write(root, "bonez-mc-solo", "b-auto.json",
           _song("Auto", "Bonez MC", ["Auto fährt"], language="de"))
    db = tmp_path / "t.db"
    build_database(root=root, db_path=db, corpus="genius-de")
    assert _line_syllables(db, "Auto") == 3


def test_none_language_keeps_serbian_counter(tmp_path):
    """language=None (legacy genius-pro rows) must NOT take the de path."""
    root = tmp_path / "genius"
    _write(root, "a-solo", "a-auto.json",
           _song("Auto", "Niko", ["Auto fährt"]))  # language None
    db = tmp_path / "t.db"
    build_database(root=root, db_path=db, corpus="genius-pro")
    assert _line_syllables(db, "Auto") == 4  # a,u,o + a — Serbian per-vowel


# ── Rhyme skip for de rows ────────────────────────────────────────────

def _rhyme_rows_for_corpus(db: Path, corpus: str) -> int:
    rows = _rows(
        db,
        """SELECT COUNT(*) FROM line_rhymes lr
           JOIN lines l ON lr.line_id = l.id
           JOIN sections s ON l.section_id = s.id
           JOIN songs g ON s.song_id = g.id
           WHERE g.corpus = ?""",
        (corpus,),
    )
    return rows[0][0]


def test_de_rows_produce_no_line_rhymes(tmp_path):
    """German rows: metrics run but populate_rhymes is skipped."""
    root = tmp_path / "genius-de"
    _write(root, "bonez-mc-solo", "b-mama.json",
           _song("Mama DE", "Bonez MC", ["geht nach hause mama",
                                         "ruft schon wieder mama"],
                  language="de", genius_song_id=5001))
    db = tmp_path / "t.db"
    build_database(root=root, db_path=db, corpus="genius-de")
    assert _rhyme_rows_for_corpus(db, "genius-de") == 0
    # ...and metrics still ran for the song.
    rows = _rows(db,
                 "SELECT COUNT(*) FROM song_metrics sm "
                 "JOIN songs g ON sm.song_id = g.id WHERE g.corpus='genius-de'")
    assert rows[0][0] == 1


def test_serbian_rows_still_get_line_rhymes(tmp_path):
    """Control: identical lyric content with language=None does get rhymes."""
    root = tmp_path / "genius"
    _write(root, "a-solo", "a-mama.json",
           _song("Mama SR", "Niko", ["ide kuća mama",
                                     "zove se mama"]))
    db = tmp_path / "t.db"
    build_database(root=root, db_path=db, corpus="genius-pro")
    assert _rhyme_rows_for_corpus(db, "genius-pro") >= 1


# ── End-to-end row shape ──────────────────────────────────────────────

def test_genius_de_row_shape(tmp_path):
    root = tmp_path / "genius-de"
    _write(root, "gzuz-solo", "gzuz-lied.json",
           _song("Lied", "GZUZ", ["Zeit läuft schnell auf der Strasse"],
                  language="de", genius_song_id=6001))
    db = tmp_path / "t.db"
    build_database(root=root, db_path=db, corpus="genius-de")
    row = _rows(
        db,
        "SELECT corpus, language, genre_cohort, role, target_artist, "
        "license_tier, release_ok, foreign_identifier FROM songs")[0]
    assert row[0] == "genius-de"
    assert row[1] == "de"
    assert row[2] == "german_drill"
    assert row[3] == "solo"
    assert row[4] == "gzuz"
    assert row[5] == "study-only"
    assert row[6] == "no"
    assert row[7] == "6001"
