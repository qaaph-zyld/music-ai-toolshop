"""CLASSLA annotation — lemma/POS/NER over lyrics lines.

Feeds ``text_raw`` (not ``text_norm``) to ``classla.Pipeline('sr', type='nonstandard')``.
The stripped-Latin majority caps lemma/POS/NER below CLASSLA's headline 97.9% —
an accepted L3 ceiling, not a bug.  Cyrillic-source lines get full accuracy.

Tables populated: ``tokens``, ``entities``.
Resumable: skips lines already present in ``tokens``.
"""

from __future__ import annotations

import json
import math
import re
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, NoReturn, Optional

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


def _write_status(path: Optional[Path], payload: Dict[str, Any]) -> None:
    """Flush progress JSON (best-effort — status is an aid, not the contract)."""
    if not path:
        return
    try:
        Path(path).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except OSError:
        pass


# Bounded commit retry against transient writer contention — a concurrent
# rimer rebuild killed SR-3 on 2026-10-13 with "database is locked" at
# annotate_lines' per-batch commit (and the status kept saying "running").
_COMMIT_RETRY_BACKOFF_S = (5, 15, 45)


def _commit_with_retry(conn: sqlite3.Connection) -> None:
    """``conn.commit()`` with bounded retries on 'database is locked'.

    One immediate attempt plus three delayed retries.  A non-lock
    ``OperationalError``, or a lock that survives the last retry, propagates.
    """
    for attempt, delay in enumerate((0, *_COMMIT_RETRY_BACKOFF_S)):
        if delay:
            time.sleep(delay)
        try:
            conn.commit()
            return
        except sqlite3.OperationalError as exc:
            if "locked" not in str(exc).lower() or attempt == len(_COMMIT_RETRY_BACKOFF_S):
                raise


def _mairina_gate(
    conn: sqlite3.Connection,
    corpora: Optional[List[str]],
    languages: Optional[List[str]],
) -> Optional[Dict[str, Any]]:
    """MAirina's coverage gate, per scoped corpus (``mairina/corpus.py
    check_annotated`` semantics).

    Denominator: lines with ``length(trim(coalesce(text_norm,''))) > 0`` on
    songs whose ``corpus`` and ``language`` are in scope (NULL-language rows
    never match).  Numerator: those lines with ``EXISTS`` a token row.
    ``pass`` = every scoped corpus at >= 90%.  ``None`` when unscoped.
    """
    if not corpora or not languages:
        return None
    lang_ph = ",".join("?" for _ in languages)
    base = (
        "FROM lines l JOIN sections sec ON sec.id = l.section_id "
        "JOIN songs s ON s.id = sec.song_id "
        "WHERE length(trim(coalesce(l.text_norm, ''))) > 0 "
        "AND s.corpus = ? AND s.language IN (" + lang_ph + ")"
    )
    gate: Dict[str, Any] = {}
    passed = True
    for corpus in corpora:
        params: List[Any] = [corpus, *languages]
        non_empty = conn.execute(f"SELECT COUNT(*) {base}", params).fetchone()[0]
        covered = conn.execute(
            f"SELECT COUNT(*) {base} "
            "AND EXISTS (SELECT 1 FROM tokens t WHERE t.line_id = l.id)",
            params,
        ).fetchone()[0]
        pct = round(covered / non_empty * 100, 1) if non_empty else 0.0
        gate[corpus] = {"non_empty": non_empty, "annotated": covered, "pct": pct}
        if pct < 90.0:
            passed = False
    gate["pass"] = passed
    return gate


def _refuse(
    status_path: Optional[Path],
    corpora: Optional[List[str]],
    languages: Optional[List[str]],
    err_type: str,
    msg: str,
) -> NoReturn:
    """Record an honest refused-to-start status and exit non-zero."""
    _write_status(status_path, {
        "finished": False,
        "updated": datetime.now().isoformat(),
        "corpora": corpora,
        "languages": languages,
        "error": f"{err_type}: {msg}",
    })
    print(f"  Annotate refused: {err_type}: {msg}")
    raise SystemExit(1)


def annotate_lines(
    conn: sqlite3.Connection,
    db_path: Optional[Any] = None,
    resume: bool = True,
    limit: Optional[int] = None,
    corpora: Optional[List[str]] = None,
    languages: Optional[List[str]] = None,
    status_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Run CLASSLA annotation over lines, populating tokens + entities.

    Args:
        conn: SQLite connection to lyrics.db.
        db_path: Unused (kept for API compat). Conn is used directly.
        resume: If True, skip lines already annotated.
        limit: If set, only annotate this many new lines.
        corpora: If set, only annotate lines whose song belongs to one of
            these corpus tags (e.g. ``["genius-pro", "lrclib"]``).
        languages: If set, only annotate lines whose song carries one of
            these ``songs.language`` tags (e.g. ``["sr"]`` — NULL-language
            rows never match and are excluded).
        status_path: If set, flush progress JSON here at each commit batch.

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

    # Fetch lines with their section/song context (optionally corpus-scoped)
    sql = (
        "SELECT l.id, l.text_raw, l.section_id, s.song_id "
        "FROM lines l "
        "JOIN sections s ON l.section_id = s.id "
        "JOIN songs sg ON sg.id = s.song_id "
        "WHERE l.text_raw IS NOT NULL AND l.text_raw != ''"
    )
    params: List[Any] = []
    if corpora:
        ph = ",".join("?" for _ in corpora)
        sql += f" AND sg.corpus IN ({ph})"
        params.extend(corpora)
    if languages:
        ph = ",".join("?" for _ in languages)
        sql += f" AND sg.language IN ({ph})"
        params.extend(languages)
    sql += " ORDER BY l.id"
    rows = conn.execute(sql, params).fetchall()

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
    lines_committed = 0

    def _commit_or_fail() -> None:
        """Bounded-retry commit; on final failure roll the pending batch back,
        flush an honest ``finished: false`` status (``lines_done`` = lines
        actually committed, so ``--resume`` truthfully continues), re-raise."""
        nonlocal lines_committed
        try:
            _commit_with_retry(conn)
        except sqlite3.OperationalError as exc:
            conn.rollback()
            _write_status(status_path, {
                "finished": False,
                "updated": datetime.now().isoformat(),
                "failed_at": datetime.now().isoformat(),
                "corpora": corpora,
                "languages": languages,
                "error": f"{type(exc).__name__}: {exc}",
                "lines_done": lines_committed,
                "lines_total": total,
                "tokens_inserted": tokens_inserted,
                "entities_inserted": entities_inserted,
            })
            raise
        lines_committed = lines_done

    _write_status(status_path, {
        "finished": False,
        "updated": datetime.now().isoformat(),
        "corpora": corpora,
        "languages": languages,
        "lines_done": 0,
        "lines_total": total,
        "tokens_inserted": 0,
        "entities_inserted": 0,
    })

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
            _commit_or_fail()
            print(f"  Progress: {lines_done}/{total} lines ({tokens_inserted} tokens, {entities_inserted} entities)")
            _write_status(status_path, {
                "finished": False,
                "updated": datetime.now().isoformat(),
                "corpora": corpora,
                "languages": languages,
                "lines_done": lines_done,
                "lines_total": total,
                "tokens_inserted": tokens_inserted,
                "entities_inserted": entities_inserted,
            })

    _commit_or_fail()
    now = datetime.now().isoformat()
    print(f"  Done: {lines_done} lines, {tokens_inserted} tokens, {entities_inserted} entities")
    _write_status(status_path, {
        "finished": True,
        "updated": now,
        "finished_at": now,
        "corpora": corpora,
        "languages": languages,
        "lines_done": lines_done,
        "lines_total": total,
        "tokens_inserted": tokens_inserted,
        "entities_inserted": entities_inserted,
        "mairina_gate": _mairina_gate(conn, corpora, languages),
    })
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

    # Per-corpus coverage (line-level; the MAirina gate reads this)
    corpus_rows = conn.execute(
        """SELECT sg.corpus,
                  count(DISTINCT l.id)  AS total,
                  count(DISTINCT CASE WHEN t.line_id IS NOT NULL THEN l.id END) AS annotated
           FROM lines l
           JOIN sections s ON l.section_id = s.id
           JOIN songs sg ON sg.id = s.song_id
           LEFT JOIN tokens t ON t.line_id = l.id
           WHERE l.text_raw IS NOT NULL AND l.text_raw != ''
           GROUP BY sg.corpus ORDER BY sg.corpus"""
    ).fetchall()
    per_corpus = {}
    if corpus_rows:
        print("  Per-corpus coverage:")
        for corpus, total_c, annotated_c in corpus_rows:
            pct_c = (annotated_c / total_c * 100) if total_c else 0
            per_corpus[corpus] = {"total": total_c, "annotated": annotated_c, "pct": round(pct_c, 1)}
            print(f"    {corpus:<20} {annotated_c:>8}/{total_c:<8} ({pct_c:.1f}%)")

    return {
        "total_lines": total_lines,
        "annotated_lines": annotated_lines,
        "coverage_pct": pct,
        "by_script": script_stats,
        "by_corpus": per_corpus,
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
    corpora: Optional[List[str]] = None,
    languages: Optional[List[str]] = None,
    status_path: Optional[Any] = None,
    busy_timeout_ms: int = 60000,
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

    if status_path is None:
        status_path = db_path.parent / "_annotate_status.json"
    else:
        status_path = Path(status_path)

    conn = sqlite3.connect(db_path)
    conn.execute(f"PRAGMA busy_timeout={int(busy_timeout_ms)}")

    # Write preflight — BEFORE loading CLASSLA, which costs ~25 s and would
    # hide a lock failure behind the model load (SR-3, 2026-10-13).  A
    # leftover -journal means a rollback-mode writer is mid-flight or died;
    # the BEGIN IMMEDIATE probe then proves we can actually take the write
    # lock within busy_timeout (covers WAL writers; a lingering -wal file is
    # not itself a writer signal).  On refusal the status JSON carries the
    # error so a dead run can never read as "still running" again.
    if Path(str(db_path) + "-journal").exists():
        conn.close()
        _refuse(status_path, corpora, languages, "DatabaseBusy",
                f"{db_path.name}-journal exists — a writer is mid-transaction "
                "or crashed; retry when it clears")
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("BEGIN IMMEDIATE")
    except sqlite3.Error as exc:
        conn.rollback()
        conn.close()
        _refuse(status_path, corpora, languages, type(exc).__name__, str(exc))
    conn.rollback()
    conn.execute("PRAGMA foreign_keys=ON")

    if fresh:
        print("  Wiping existing annotation tables...")
        _wipe_l3_tables(conn)

    print(f"  Database: {db_path}")
    if corpora:
        print(f"  Corpus scope: {', '.join(corpora)}")
    if languages:
        print(f"  Language scope: {', '.join(languages)}")
    print(f"  Status file: {status_path}")
    summary = annotate_lines(
        conn, db_path, resume=resume, limit=limit,
        corpora=corpora, languages=languages, status_path=status_path,
    )
    coverage = coverage_summary(conn)

    conn.close()
    return {**summary, "coverage": coverage}
