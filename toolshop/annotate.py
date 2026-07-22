"""CLASSLA annotation — lemma/POS/NER over lyrics lines.

Feeds ``text_raw`` (not ``text_norm``) to ``classla.Pipeline('sr', type='nonstandard')``.
The stripped-Latin majority caps lemma/POS/NER below CLASSLA's headline 97.9% —
an accepted L3 ceiling, not a bug.  Cyrillic-source lines get full accuracy.

Tables populated: ``tokens``, ``entities``.
Resumable: skips lines already present in ``tokens``.
"""

from __future__ import annotations

import math
import re
import sqlite3
import sys
from typing import Any, Dict, List, Optional

from toolshop.lyricsdb import DEFAULT_DB_PATH

_CYRILLIC_CHAR_RE = re.compile(r"[А-Яа-яЁё]")


def _classify_source_script(text: str) -> str:
    """Return 'cyrillic' or 'latin' based on script detection.

    Uses its own regex (without space) — the shared ``_has_cyrillic``
    includes space in its character class, which would false-positive
    on any Latin string containing spaces.
    """
    if text and _CYRILLIC_CHAR_RE.search(text):
        return "cyrillic"
    return "latin"


def _token_row_builder(
    line_id: int,
    ordinal: int,
    token: Any,
    source_script: str,
) -> Dict[str, Any]:
    """Build a token row dict from a CLASSLA word token.

    ``token`` is expected to have ``.text``, ``.upos``, ``.lemma``, ``.feats``.
    """
    feats = token.feats if hasattr(token, "feats") else None
    if feats is None:
        feats = "_"
    return {
        "line_id": line_id,
        "ordinal": ordinal,
        "form": token.text,
        "lemma": token.lemma,
        "upos": token.upos or "_",
        "feats": feats,
        "is_oov": 0,
        "source_script": source_script,
    }


def _ner_extractor(
    doc: Any,
    song_id: int,
    section_id: int,
    line_id: int,
) -> List[Dict[str, Any]]:
    """Extract NER entities from a CLASSLA doc.

    CLASSLA NER produces entities at the sentence level.  We iterate
    ``doc.ents`` (or ``doc.iter_words()`` with ``.ner`` attribute depending
    on pipeline version) and collect typed entities.
    """
    entities: List[Dict[str, Any]] = []

    # Stanza/CLASSLA docs have .ents for named entities
    if hasattr(doc, "ents") and doc.ents:
        for ent in doc.ents:
            entities.append({
                "song_id": song_id,
                "section_id": section_id,
                "line_id": line_id,
                "text": ent.text,
                "ner_type": ent.type,
            })
        return entities

    # Fallback: scan words for NER tags (nonstandard pipeline may use per-word ner)
    if not hasattr(doc, "iter_words"):
        return entities

    current_ent: Optional[List[str]] = None
    current_type: Optional[str] = None
    for word in doc.iter_words():
        ner = getattr(word, "ner", None) or getattr(word, "entity", None)
        if ner and ner != "O":
            # Stanza NER format: "B-PER", "I-PER", etc.
            parts = ner.split("-", 1)
            prefix = parts[0]
            ent_type = parts[1] if len(parts) > 1 else "MISC"
            if prefix == "B" or (current_ent and ent_type != current_type):
                if current_ent and current_type:
                    entities.append({
                        "song_id": song_id,
                        "section_id": section_id,
                        "line_id": line_id,
                        "text": " ".join(current_ent),
                        "ner_type": current_type,
                    })
                current_ent = [word.text]
                current_type = ent_type
            elif prefix == "I" and current_ent and ent_type == current_type:
                current_ent.append(word.text)
            else:
                if current_ent and current_type:
                    entities.append({
                        "song_id": song_id,
                        "section_id": section_id,
                        "line_id": line_id,
                        "text": " ".join(current_ent),
                        "ner_type": current_type,
                    })
                current_ent = [word.text]
                current_type = ent_type
        else:
            if current_ent and current_type:
                entities.append({
                    "song_id": song_id,
                    "section_id": section_id,
                    "line_id": line_id,
                    "text": " ".join(current_ent),
                    "ner_type": current_type,
                })
                current_ent = None
                current_type = None

    # Flush trailing entity
    if current_ent and current_type:
        entities.append({
            "song_id": song_id,
            "section_id": section_id,
            "line_id": line_id,
            "text": " ".join(current_ent),
            "ner_type": current_type,
        })

    return entities


def _get_annotated_line_ids(conn: sqlite3.Connection) -> set[int]:
    """Return set of line_ids already in tokens table."""
    rows = conn.execute("SELECT DISTINCT line_id FROM tokens").fetchall()
    return {r[0] for r in rows}


def annotate_lines(
    conn: sqlite3.Connection,
    db_path: Optional[Any] = None,
    resume: bool = True,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """Run CLASSLA annotation over all lines, populating tokens + entities.

    Args:
        conn: SQLite connection to lyrics.db.
        db_path: Unused (kept for API compat). Conn is used directly.
        resume: If True, skip lines already annotated.
        limit: If set, only annotate this many new lines.

    Returns:
        Summary dict with counts.
    """
    import classla

    # Build pipeline
    nlp = classla.Pipeline("sr", type="nonstandard")

    # Determine which lines to annotate
    already_done: set[int] = set()
    if resume:
        already_done = _get_annotated_line_ids(conn)

    # Fetch all lines with their section/song context
    rows = conn.execute(
        """SELECT l.id, l.text_raw, l.section_id, s.song_id
           FROM lines l
           JOIN sections s ON l.section_id = s.id
           WHERE l.text_raw IS NOT NULL AND l.text_raw != ''
           ORDER BY l.id"""
    ).fetchall()

    to_annotate = [
        (r[0], r[1], r[2], r[3]) for r in rows if r[0] not in already_done
    ]

    if limit:
        to_annotate = to_annotate[:limit]

    total = len(to_annotate)
    print(f"  Lines to annotate: {total} (skipped {len(already_done)} already done)")

    if total == 0:
        print("  Nothing to annotate.")
        return {"lines_annotated": 0, "tokens_inserted": 0, "entities_inserted": 0}

    tokens_inserted = 0
    entities_inserted = 0
    lines_done = 0

    for line_id, text_raw, section_id, song_id in to_annotate:
        source_script = _classify_source_script(text_raw)

        try:
            doc = nlp(text_raw)
        except Exception as exc:
            print(f"  WARN: CLASSLA failed on line {line_id}: {exc}")
            continue

        # Insert tokens
        for ordinal, word in enumerate(doc.iter_words(), start=1):
            row = _token_row_builder(line_id, ordinal, word, source_script)
            conn.execute(
                """INSERT INTO tokens (line_id, ordinal, form, lemma, upos, feats, is_oov, source_script)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    row["line_id"], row["ordinal"], row["form"], row["lemma"],
                    row["upos"], row["feats"], row["is_oov"], row["source_script"],
                ),
            )
            tokens_inserted += 1

        # Insert entities
        ents = _ner_extractor(doc, song_id, section_id, line_id)
        for ent in ents:
            conn.execute(
                """INSERT INTO entities (song_id, section_id, line_id, text, ner_type)
                   VALUES (?, ?, ?, ?, ?)""",
                (ent["song_id"], ent["section_id"], ent["line_id"], ent["text"], ent["ner_type"]),
            )
            entities_inserted += 1

        lines_done += 1
        if lines_done % 500 == 0:
            conn.commit()
            print(f"  Progress: {lines_done}/{total} lines ({tokens_inserted} tokens, {entities_inserted} entities)")

    conn.commit()
    print(f"  Done: {lines_done} lines, {tokens_inserted} tokens, {entities_inserted} entities")
    return {
        "lines_annotated": lines_done,
        "tokens_inserted": tokens_inserted,
        "entities_inserted": entities_inserted,
    }


def coverage_summary(conn: sqlite3.Connection) -> Dict[str, Any]:
    """Print and return annotation coverage split by source_script."""
    total_lines = conn.execute("SELECT count(*) FROM lines WHERE text_raw IS NOT NULL AND text_raw != ''").fetchone()[0]
    annotated_lines = conn.execute("SELECT count(DISTINCT line_id) FROM tokens").fetchone()[0]

    print(f"\n=== Annotation Coverage ===")
    print(f"  Total lines (non-empty): {total_lines}")
    print(f"  Annotated lines:         {annotated_lines}")
    pct = (annotated_lines / total_lines * 100) if total_lines else 0
    print(f"  Coverage:                {pct:.1f}%")

    # Per source-script
    script_rows = conn.execute(
        """SELECT source_script, count(*) as token_count,
                  count(DISTINCT line_id) as line_count
           FROM tokens GROUP BY source_script"""
    ).fetchall()

    script_stats = {}
    for script, tok_count, line_count in script_rows:
        script_stats[script] = {"tokens": tok_count, "lines": line_count}
        print(f"  {script}: {tok_count} tokens across {line_count} lines")

    # OOV rate
    oov_count = conn.execute("SELECT count(*) FROM tokens WHERE is_oov = 1").fetchone()[0]
    total_tokens = conn.execute("SELECT count(*) FROM tokens").fetchone()[0]
    oov_pct = (oov_count / total_tokens * 100) if total_tokens else 0
    print(f"  OOV tokens:              {oov_count} ({oov_pct:.1f}%)")

    # Entity count
    ent_count = conn.execute("SELECT count(*) FROM entities").fetchone()[0]
    print(f"  Entities:                {ent_count}")

    # Per-script entity breakdown
    ent_type_rows = conn.execute(
        """SELECT ner_type, count(*) FROM entities GROUP BY ner_type ORDER BY count(*) DESC"""
    ).fetchall()
    for etype, ecount in ent_type_rows:
        print(f"    {etype}: {ecount}")

    return {
        "total_lines": total_lines,
        "annotated_lines": annotated_lines,
        "coverage_pct": pct,
        "by_script": script_stats,
        "oov_count": oov_count,
        "oov_pct": oov_pct,
        "entity_count": ent_count,
    }


def _wipe_l3_tables(conn: sqlite3.Connection) -> None:
    """Clear L3 annotation tables for a fresh run."""
    conn.execute("DELETE FROM tokens")
    conn.execute("DELETE FROM entities")
    conn.commit()


def run_annotation(
    db_path: Optional[Any] = None,
    resume: bool = True,
    limit: Optional[int] = None,
    fresh: bool = False,
) -> Dict[str, Any]:
    """CLI entry point: run CLASSLA annotation on lyrics.db."""
    from pathlib import Path

    if db_path is None:
        db_path = DEFAULT_DB_PATH
    db_path = Path(db_path)

    if not db_path.exists():
        print(f"Database not found: {db_path}")
        print("Run 'toolshop lyrics build-db' first.")
        return {}

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    if fresh:
        print("  Wiping existing annotation tables...")
        _wipe_l3_tables(conn)

    print(f"  Database: {db_path}")
    summary = annotate_lines(conn, db_path, resume=resume, limit=limit)
    coverage = coverage_summary(conn)

    conn.close()
    return {**summary, "coverage": coverage}
