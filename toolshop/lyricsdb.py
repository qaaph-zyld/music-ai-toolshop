"""SQLite lyrics database — schema, loader, and section label parser.

Tables: ``songs``, ``sections``, ``lines``.  Full rebuild each run.
``lyrics.db`` lives under ``TOOLSHOP_DATA_DIR`` (default ``D:\\MusicData\\toolshop``),
never inside the repo.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from toolshop.syllables import count_line, count_syllables

# ── Constants ─────────────────────────────────────────────────────────

_DEFAULT_DATA_DIR = Path(r"D:\MusicData\toolshop")
_DB_SUBDIR = "lyrics"
_DB_FILENAME = "lyrics.db"

DEFAULT_DB_PATH = _DEFAULT_DATA_DIR / _DB_SUBDIR / _DB_FILENAME

CORPUS_TAG = "genius-pro"

# Section type mapping (English → Serbian canonical, plus Serbian canonicals).
_TYPE_MAP: Dict[str, str] = {
    # Refren / chorus
    "refren": "refren",
    "chorus": "refren",
    "refrain": "refren",
    "ref": "refren",
    # Strofa / verse
    "strofa": "strofa",
    "verse": "strofa",
    "couplet": "strofa",
    "vers": "strofa",
    "part": "strofa",
    "stofa": "strofa",  # typo
    # Bridge
    "bridge": "bridge",
    "brigde": "bridge",  # typo
    "prelaz": "bridge",
    "prijelaz": "bridge",
    "most": "bridge",
    # Intro
    "intro": "intro",
    "uvod": "intro",
    # Outro
    "outro": "outro",
    "završetak": "outro",
    # Prerefren
    "prerefren": "prerefren",
    "predrefren": "prerefren",
    "pred-refren": "prerefren",
    "pred-refren": "prerefren",
    "pre-chorus": "prerefren",
    "pre-refren": "prerefren",
    "pre-hook": "prerefren",
    # Postrefren (new)
    "postrefren": "postrefren",
    "post-refren": "postrefren",
    "post-refren": "postrefren",
    "post-refern": "postrefren",  # typo
    "post-chorus": "postrefren",
    "post-hook": "postrefren",
    # Hook
    "hook": "hook",
    # Spoken (new)
    "izgovoreno": "spoken",
    "improvizacija": "spoken",
    # Instrumental (new — multi-word, handled separately)
    # Interlude (new — multi-word, handled separately)
}

_VALID_TYPES = frozenset(
    set(_TYPE_MAP.values()) | {"instrumental", "interlude"}
)

# Multi-word type phrases (checked before single-word parsing).
# Listed longest-first to avoid prefix collisions.
_MULTIWORD_TYPE_MAP: List[Tuple[str, str]] = [
    ("instrumentalna pauza", "instrumental"),
    ("tekst iz isječka", "interlude"),
]


# ── Section label parser ──────────────────────────────────────────────

# Matches the type-word portion: "Strofa", "Pre-Chorus", "Pred-Refren", etc.
_TYPE_WORD_RE = re.compile(r"^(?P<type_word>[A-Za-z\u00C0-\u024F-]+)\s*(?P<num>\d+)?", re.IGNORECASE)


@dataclass
class ParsedLabel:
    """Result of parsing a section label."""

    type: str
    type_number: Optional[int]
    performers: List[str] = field(default_factory=list)


def _split_performers(text: str) -> List[str]:
    """Split performer text on '&', ',', 'and'."""
    if not text or not text.strip():
        return []
    parts = re.split(r"[&,]", text)
    return [p.strip() for p in parts if p.strip()]


def _parse_standard_label(text: str) -> ParsedLabel:
    """Parse a standard label: 'Type', 'Type N', 'Type: Performers',
    'Type N: Performers', 'Type - Performers', 'Type N - Performers',
    'Type:', 'Type N:'.
    """
    if not text or not text.strip():
        return ParsedLabel(type="other", type_number=None, performers=[])

    text = text.strip()
    performers: List[str] = []
    remainder = text

    # Check for colon separator first (handles trailing colon too).
    if ":" in text:
        parts = text.split(":", 1)
        remainder = parts[0].strip()
        performer_text = parts[1].strip()
        if performer_text:
            performers = _split_performers(performer_text)
    # Check for " - " separator (not hyphenated type words like "Pre-Chorus").
    elif " - " in text:
        parts = text.split(" - ", 1)
        remainder = parts[0].strip()
        performer_text = parts[1].strip()
        if performer_text:
            performers = _split_performers(performer_text)

    # Extract type word and optional number from remainder.
    m = _TYPE_WORD_RE.match(remainder)
    if not m:
        return ParsedLabel(type="other", type_number=None, performers=performers)

    type_word = m.group("type_word").lower()
    type_number = int(m.group("num")) if m.group("num") else None
    section_type = _TYPE_MAP.get(type_word, "other")

    return ParsedLabel(type=section_type, type_number=type_number, performers=performers)


def parse_section_label(label: str) -> ParsedLabel:
    """Parse a section label into type, number, and performers.

    Handles standard format ("Strofa 2: Jala Brat"), reversed format
    ("Buba Corelli:Refren"), slash compounds ("Refrain/Refren: Performer"),
    dash separator ("Refren - Jala Brat"), trailing colon ("Refren:"),
    multi-word types ("Instrumentalna pauza"), and common typos.
    """
    if not label or not label.strip():
        return ParsedLabel(type="other", type_number=None, performers=[])

    text = label.strip()
    text_lower = text.lower()

    # 1. Multi-word type phrases (checked first, longest match).
    for phrase, section_type in _MULTIWORD_TYPE_MAP:
        if text_lower.startswith(phrase):
            rest = text[len(phrase):].strip()
            performers: List[str] = []
            if rest.startswith(":"):
                performers = _split_performers(rest[1:].strip())
            elif rest.startswith(" - "):
                performers = _split_performers(rest[3:].strip())
            return ParsedLabel(type=section_type, type_number=None, performers=performers)

    # 2. Slash compound: "Type1/Type2: performers" — take first known type.
    if "/" in text:
        slash_parts = text.split("/", 1)
        first_result = _parse_standard_label(slash_parts[0].strip())
        if first_result.type != "other":
            # Extract performers from after the slash (may contain colon).
            after_slash = slash_parts[1].strip()
            if ":" in after_slash:
                performer_text = after_slash.split(":", 1)[1].strip()
                first_result.performers = _split_performers(performer_text)
            return first_result

    # 3. Reversed format: "Artist:Type" or "Artist:Type N".
    if ":" in text:
        colon_parts = text.split(":", 1)
        left = colon_parts[0].strip()
        right = colon_parts[1].strip()
        if right:
            right_result = _parse_standard_label(right)
            left_result = _parse_standard_label(left)
            if right_result.type != "other" and left_result.type == "other":
                right_result.performers = [left]
                return right_result

    # 4. Standard parsing.
    return _parse_standard_label(text)


# ── Text normalization ────────────────────────────────────────────────

_CYRILLIC_RE = re.compile(r"[А-Яа-я Ёё]")


def _has_cyrillic(text: str) -> bool:
    return bool(_CYRILLIC_RE.search(text))


def normalize_text(text: str) -> str:
    """Normalize text: NFC → cyrtranslit (if Cyrillic) → lowercase.

    ``text_raw`` is kept verbatim; this function produces ``text_norm``.
    """
    if not text:
        return ""

    # NFC normalization
    result = unicodedata.normalize("NFC", text)

    # Transliterate Cyrillic → Latin (Serbian variant)
    if _has_cyrillic(result):
        import cyrtranslit
        result = cyrtranslit.to_latin(result, "sr")

    return result.lower()


# ── Normalization key for dedup ───────────────────────────────────────

def _dedup_key(title: str, primary_artist: str) -> Tuple[str, str]:
    """Normalized (title, primary_artist) for dedup.

    Strips non-alphanumeric chars so "Dandara*" matches "Dandara".
    """
    norm_title = re.sub(r"[^a-z0-9]", "", normalize_text(title))
    norm_artist = re.sub(r"[^a-z0-9]", "", normalize_text(primary_artist))
    return (norm_title, norm_artist)


# ── Schema ────────────────────────────────────────────────────────────

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS songs (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    corpus           TEXT    NOT NULL DEFAULT 'genius-pro',
    category         TEXT,
    title            TEXT    NOT NULL,
    primary_artist   TEXT    NOT NULL,
    featured_artists TEXT,   -- JSON array
    url              TEXT,
    language         TEXT,
    source_path      TEXT,
    ingested_at      TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS sections (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    song_id     INTEGER NOT NULL REFERENCES songs(id) ON DELETE CASCADE,
    ordinal     INTEGER NOT NULL,
    type        TEXT    NOT NULL,
    type_number INTEGER,
    label_raw   TEXT,
    performers  TEXT    -- JSON array
);

CREATE TABLE IF NOT EXISTS lines (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    section_id     INTEGER NOT NULL REFERENCES sections(id) ON DELETE CASCADE,
    ordinal        INTEGER NOT NULL,
    text_raw       TEXT,
    text_norm      TEXT,
    word_count     INTEGER,
    syllable_count INTEGER
);

CREATE TABLE IF NOT EXISTS song_metrics (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    song_id               INTEGER NOT NULL REFERENCES songs(id) ON DELETE CASCADE,
    total_words           INTEGER,
    unique_words          INTEGER,
    ttr                   REAL,
    line_count            INTEGER,
    avg_words_per_line    REAL,
    avg_syllables_per_line REAL,
    hook_repetition_max   INTEGER,
    hook_repetition_ratio REAL,
    english_loanword_rate REAL,
    section_type_counts   TEXT  -- JSON
);

CREATE INDEX IF NOT EXISTS idx_sections_song ON sections(song_id);
CREATE INDEX IF NOT EXISTS idx_lines_section ON lines(section_id);
CREATE INDEX IF NOT EXISTS idx_songs_artist ON songs(primary_artist);
CREATE INDEX IF NOT EXISTS idx_song_metrics_song ON song_metrics(song_id);

CREATE TABLE IF NOT EXISTS line_rhymes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    song_id         INTEGER NOT NULL REFERENCES songs(id) ON DELETE CASCADE,
    line_id         INTEGER NOT NULL REFERENCES lines(id) ON DELETE CASCADE,
    rhyme_group     INTEGER NOT NULL,
    rhyme_type      TEXT    NOT NULL,
    vowel_skeleton  TEXT    NOT NULL,
    match_length    INTEGER NOT NULL,
    position        TEXT    NOT NULL DEFAULT 'end'
);

CREATE INDEX IF NOT EXISTS idx_line_rhymes_song ON line_rhymes(song_id);
CREATE INDEX IF NOT EXISTS idx_line_rhymes_line ON line_rhymes(line_id);
"""


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA_SQL)


# ── Loader ────────────────────────────────────────────────────────────

def _load_index(root: Path) -> Dict[str, Dict[str, Any]]:
    """Load _index.json and return a dict keyed by JSON basename."""
    index_path = root / "_index.json"
    if not index_path.exists():
        return {}

    with index_path.open("r", encoding="utf-8") as f:
        entries = json.load(f)

    # Index is a list of dicts; key by basename of json_path
    result: Dict[str, Dict[str, Any]] = {}
    for entry in entries:
        json_path = entry.get("json_path") or entry.get("file") or ""
        basename = Path(json_path).name
        result[basename] = entry
    return result


def _scan_song_files(root: Path) -> List[Tuple[str, Path]]:
    """Scan <root>/<category>/*.json (excluding _* files). Returns (category, path) tuples."""
    songs: List[Tuple[str, Path]] = []
    for category_dir in sorted(root.iterdir()):
        if not category_dir.is_dir():
            continue
        category = category_dir.name
        for json_file in sorted(category_dir.glob("*.json")):
            if json_file.name.startswith("_"):
                continue
            songs.append((category, json_file))
    return songs


def _insert_song(
    conn: sqlite3.Connection,
    category: str,
    song_data: Dict[str, Any],
    source_path: str,
    index_entry: Optional[Dict[str, Any]],
    ingested_at: str,
) -> int:
    """Insert a song and return its id."""
    title = song_data.get("title", "")
    # primary_artist from index entry, fallback to song's artist field
    primary_artist = ""
    if index_entry:
        primary_artist = index_entry.get("primary_artist", "")
    if not primary_artist:
        primary_artist = song_data.get("artist", "")

    featured_artists = []
    if index_entry:
        featured_artists = index_entry.get("featured_artists", [])

    url = song_data.get("url", "")
    if index_entry and not url:
        url = index_entry.get("url", "")

    language = song_data.get("language", "")

    cursor = conn.execute(
        """INSERT INTO songs (corpus, category, title, primary_artist,
           featured_artists, url, language, source_path, ingested_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            CORPUS_TAG,
            category,
            title,
            primary_artist,
            json.dumps(featured_artists, ensure_ascii=False),
            url,
            language,
            source_path,
            ingested_at,
        ),
    )
    return cursor.lastrowid


def _insert_sections(
    conn: sqlite3.Connection,
    song_id: int,
    sections: List[Dict[str, Any]],
) -> int:
    """Insert all sections and lines for a song. Returns section count."""
    for ordinal, section in enumerate(sections, start=1):
        label_raw = section.get("label") or ""
        content = section.get("content", "")

        parsed = parse_section_label(label_raw)

        cursor = conn.execute(
            """INSERT INTO sections (song_id, ordinal, type, type_number, label_raw, performers)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                song_id,
                ordinal,
                parsed.type,
                parsed.type_number,
                label_raw,
                json.dumps(parsed.performers, ensure_ascii=False),
            ),
        )
        section_id = cursor.lastrowid

        # Insert lines
        lines = [l for l in content.split("\n") if l.strip()]
        for line_ordinal, line_text in enumerate(lines, start=1):
            text_norm = normalize_text(line_text)
            word_count = len(re.findall(r"\b\w+\b", text_norm))
            syl_count = count_line(line_text)
            conn.execute(
                """INSERT INTO lines (section_id, ordinal, text_raw, text_norm, word_count, syllable_count)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (section_id, line_ordinal, line_text, text_norm, word_count, syl_count),
            )

    return len(sections)


def build_database(
    root: Path,
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Build the lyrics database from a corpus root.

    Full rebuild: drops and recreates all tables.  Scans ``<root>/<category>/*.json``,
    joins ``_index.json`` by basename for metadata, deduplicates by
    normalized ``(title, primary_artist)``.

    Args:
        root: Corpus root directory (e.g. ``D:\\MusicData\\toolshop\\lyrics\\genius``).
        db_path: Path for the SQLite database. Defaults to ``DEFAULT_DB_PATH``.

    Returns:
        Summary dict with keys:
            - songs_ingested: int
            - duplicates_dropped: int
            - songs_skipped: int
            - sections_ingested: int
            - lines_ingested: int
            - dedup_log: list of dicts with title/primary_artist/source_path
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    ingested_at = datetime.now(timezone.utc).isoformat()

    # Load index for metadata join
    index = _load_index(root)

    # Scan song files
    song_files = _scan_song_files(root)

    # Dedup tracking
    seen_keys: Dict[Tuple[str, str], str] = {}  # key → source_path (first seen)
    dedup_log: List[Dict[str, str]] = []
    duplicates_dropped = 0
    songs_skipped = 0
    songs_ingested = 0
    sections_ingested = 0
    lines_ingested = 0

    # Remove existing DB for clean rebuild
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    _create_schema(conn)

    for category, json_file in song_files:
        try:
            with json_file.open("r", encoding="utf-8") as f:
                song_data = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            print(f"  SKIP (parse error): {json_file} — {exc}")
            songs_skipped += 1
            continue

        title = song_data.get("title", "")
        index_entry = index.get(json_file.name)
        primary_artist = ""
        if index_entry:
            primary_artist = index_entry.get("primary_artist", "")
        if not primary_artist:
            primary_artist = song_data.get("artist", "")

        key = _dedup_key(title, primary_artist)
        if key in seen_keys:
            duplicates_dropped += 1
            dedup_log.append({
                "title": title,
                "primary_artist": primary_artist,
                "source_path": str(json_file),
                "duplicate_of": seen_keys[key],
            })
            continue

        seen_keys[key] = str(json_file)

        song_id = _insert_song(
            conn, category, song_data, str(json_file), index_entry, ingested_at
        )
        sections = song_data.get("sections", [])
        sec_count = _insert_sections(conn, song_id, sections)
        songs_ingested += 1
        sections_ingested += sec_count

    # Count lines
    cursor = conn.execute("SELECT count(*) FROM lines")
    lines_ingested = cursor.fetchone()[0]

    # Populate song_metrics table and create artist views
    from toolshop.lyrics_metrics import populate_song_metrics, create_artist_views
    metrics_count = populate_song_metrics(conn)
    create_artist_views(conn)

    # Populate line_rhymes table
    from toolshop.rhyme_miner import populate_rhymes
    rhyme_count = 0
    for row in conn.execute("SELECT id FROM songs"):
        rhyme_count += populate_rhymes(conn, row[0])
    print(f"  Rhymes computed: {rhyme_count} rhyme rows across {songs_ingested} songs")

    conn.commit()
    conn.close()

    print(f"  Metrics computed for {metrics_count} songs")

    summary = {
        "songs_ingested": songs_ingested,
        "duplicates_dropped": duplicates_dropped,
        "songs_skipped": songs_skipped,
        "sections_ingested": sections_ingested,
        "lines_ingested": lines_ingested,
        "dedup_log": dedup_log,
    }

    print(f"  Ingested: {songs_ingested} songs, {sections_ingested} sections, {lines_ingested} lines")
    print(f"  Duplicates dropped: {duplicates_dropped}")
    print(f"  Skipped: {songs_skipped}")

    return summary
