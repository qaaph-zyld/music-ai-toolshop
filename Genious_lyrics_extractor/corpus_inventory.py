"""Multi-corpus inventory for handoff — license-tiered release readiness.

Usage:
    corpus_inventory.py                     # all corpora in lyrics.db
    corpus_inventory.py --corpus genius-pro # legacy report shape (unchanged)
    corpus_inventory.py --corpus ccmixter   # generic per-corpus block + license
    corpus_inventory.py --db <path>         # non-default DB

``--corpus genius-pro`` prints exactly the report the v1 script produced
(SPEC §8.1) — same sections, same order, same counts. Structural counts are
now corpus-scoped via JOINs so the shape holds on a multi-corpus DB.
"""

import argparse
import sqlite3
import sys
from pathlib import Path

# ── Vendored migrate-on-open (SPEC §4.2) ──────────────────────────────
# Mirror of toolshop.lyricsdb.ensure_license_columns — folder scripts must not
# `import toolshop` (eager package __init__ ≈70s cold, megaplan F-B1).
# Keep in sync with toolshop/lyricsdb.py::_LICENSE_COLUMNS.
_LICENSE_COLUMNS = {
    "license_tier": "TEXT NOT NULL DEFAULT 'study-only'",
    "license_ref": "TEXT",
    "license_url": "TEXT",
    "release_ok": "TEXT NOT NULL DEFAULT 'no'",
    "creator": "TEXT",
    "creator_url": "TEXT",
    "source_url": "TEXT",
    "copyright_notice": "TEXT",
    "modified_note": "TEXT",
    "foreign_identifier": "TEXT",
    "script": "TEXT",
    "derived_from": "TEXT",
}


def _ensure_license_columns(conn: sqlite3.Connection) -> int:
    """Add §4.1 license columns to a v1-shaped DB + backfill genius rows.
    Returns rows backfilled (0 on a fresh or migrated DB)."""
    existing = {row[1] for row in conn.execute("PRAGMA table_info(songs)")}
    if not existing:
        return 0
    for col, clause in _LICENSE_COLUMNS.items():
        if col not in existing:
            conn.execute(f"ALTER TABLE songs ADD COLUMN {col} {clause}")
    cur = conn.execute(
        """UPDATE songs SET license_tier='study-only',
                            license_ref='proprietary',
                            release_ok='no'
           WHERE corpus='genius-pro' AND license_ref IS NULL"""
    )
    n = cur.rowcount if cur.rowcount is not None else 0
    conn.commit()
    return n


# ── Reports ───────────────────────────────────────────────────────────

def report_genius_pro(cur: sqlite3.Cursor) -> None:
    """Legacy genius-pro report — byte-identical shape to the v1 script."""
    total = cur.execute(
        "SELECT COUNT(*) FROM songs WHERE corpus='genius-pro'"
    ).fetchone()[0]
    print("=== CORPUS INVENTORY ===\n")
    print(f"Total songs: {total}")

    rows = cur.execute("""
        SELECT target_artist, genre_cohort, COUNT(*) as cnt
        FROM songs WHERE corpus='genius-pro' AND role='solo'
        GROUP BY target_artist, genre_cohort
        ORDER BY genre_cohort, cnt DESC
    """).fetchall()

    print(f"\n--- Solo songs by artist ({sum(r[2] for r in rows)} total) ---")
    current_cohort = None
    for artist, cohort, count in rows:
        if cohort != current_cohort:
            current_cohort = cohort
            print(f"\n  [{cohort or 'NULL'}]")
        print(f"    {artist:25s}: {count}")

    feat = cur.execute("""
        SELECT target_artist, genre_cohort, COUNT(*)
        FROM songs WHERE corpus='genius-pro' AND role='featured'
        GROUP BY target_artist, genre_cohort
        ORDER BY genre_cohort, COUNT(*) DESC
    """).fetchall()
    print(f"\n--- Featured songs ({sum(r[2] for r in feat)} total) ---")
    for artist, cohort, count in feat:
        print(f"  {artist:25s} [{cohort or 'NULL':10s}]: {count}")

    # Structural counts — corpus-scoped via JOIN (identical numbers on a
    # genius-only DB; unchanged after multi-corpus ingest).
    sections = cur.execute("""
        SELECT COUNT(*) FROM sections se
        JOIN songs s ON se.song_id = s.id WHERE s.corpus='genius-pro'
    """).fetchone()[0]
    lines = cur.execute("""
        SELECT COUNT(*) FROM lines l
        JOIN sections se ON l.section_id = se.id
        JOIN songs s ON se.song_id = s.id WHERE s.corpus='genius-pro'
    """).fetchone()[0]
    rhymes = cur.execute("""
        SELECT COUNT(*) FROM line_rhymes lr
        JOIN songs s ON lr.song_id = s.id WHERE s.corpus='genius-pro'
    """).fetchone()[0]
    song_metrics = cur.execute("""
        SELECT COUNT(*) FROM song_rhyme_metrics srm
        JOIN songs s ON srm.song_id = s.id WHERE s.corpus='genius-pro'
    """).fetchone()[0]
    print(f"\n--- Structural counts ---")
    print(f"  Sections: {sections}")
    print(f"  Lines: {lines}")
    print(f"  Rhyme rows: {rhymes}")
    print(f"  Song rhyme metrics: {song_metrics}")

    print(f"\n--- Files on disk by category ---")
    rows = cur.execute("""
        SELECT category, COUNT(*) FROM songs WHERE corpus='genius-pro'
        GROUP BY category ORDER BY category
    """).fetchall()
    for cat, count in rows:
        print(f"  {cat:30s}: {count}")

    null_solo = cur.execute("""
        SELECT target_artist, COUNT(*) FROM songs
        WHERE corpus='genius-pro' AND role='solo' AND genre_cohort IS NULL
        GROUP BY target_artist ORDER BY COUNT(*) DESC
    """).fetchall()
    print(f"\n--- NULL cohort solo artists (need COHORT_MAP entry) ---")
    for artist, count in null_solo:
        print(f"  {artist:25s}: {count}")


def report_corpus(cur: sqlite3.Cursor, corpus: str) -> None:
    """Generic per-corpus block (SPEC §8.1): songs/sections/lines/rhymes +
    per-category counts."""
    total = cur.execute(
        "SELECT COUNT(*) FROM songs WHERE corpus=?", (corpus,)
    ).fetchone()[0]
    print(f"\n=== corpus: {corpus} ===")
    print(f"Total songs: {total}")

    sections = cur.execute("""
        SELECT COUNT(*) FROM sections se
        JOIN songs s ON se.song_id = s.id WHERE s.corpus=?
    """, (corpus,)).fetchone()[0]
    lines = cur.execute("""
        SELECT COUNT(*) FROM lines l
        JOIN sections se ON l.section_id = se.id
        JOIN songs s ON se.song_id = s.id WHERE s.corpus=?
    """, (corpus,)).fetchone()[0]
    rhymes = cur.execute("""
        SELECT COUNT(*) FROM line_rhymes lr
        JOIN songs s ON lr.song_id = s.id WHERE s.corpus=?
    """, (corpus,)).fetchone()[0]
    song_metrics = cur.execute("""
        SELECT COUNT(*) FROM song_rhyme_metrics srm
        JOIN songs s ON srm.song_id = s.id WHERE s.corpus=?
    """, (corpus,)).fetchone()[0]
    print(f"  Sections: {sections}  Lines: {lines}  "
          f"Rhyme rows: {rhymes}  Rhyme metrics: {song_metrics}")

    cats = cur.execute("""
        SELECT category, COUNT(*) FROM songs WHERE corpus=?
        GROUP BY category ORDER BY category
    """, (corpus,)).fetchall()
    print(f"  Categories:")
    for cat, count in cats:
        print(f"    {cat or 'NULL':30s}: {count}")


def report_license(cur: sqlite3.Cursor, corpora: list) -> None:
    """License/release-readiness block (SPEC §8.1): license_tier × release_ok
    matrix, TASL gap counts, derived_from link counts — per corpus."""
    print(f"\n=== LICENSE / RELEASE READINESS ===")
    matrix = cur.execute("""
        SELECT corpus, license_tier, release_ok, COUNT(*)
        FROM songs GROUP BY corpus, license_tier, release_ok
        ORDER BY corpus, license_tier, release_ok
    """).fetchall()
    by_corpus = {}
    for corpus, tier, ok, n in matrix:
        if corpus in corpora:
            by_corpus.setdefault(corpus, []).append((tier, ok, n))
    for corpus in corpora:
        print(f"\n  [{corpus}]")
        for tier, ok, n in by_corpus.get(corpus, []):
            print(f"    {tier or 'NULL':15s} release_ok={ok or 'NULL':12s}: {n}")
        if not by_corpus.get(corpus):
            print(f"    (no rows)")

    # TASL gaps — release-critical fields among release_ok items + overall.
    print(f"\n--- TASL gaps (missing creator / source_url / license_ref) ---")
    for corpus in corpora:
        total = cur.execute(
            "SELECT COUNT(*) FROM songs WHERE corpus=?", (corpus,)
        ).fetchone()[0]
        gaps = cur.execute("""
            SELECT
                SUM(CASE WHEN creator IS NULL OR creator='' THEN 1 ELSE 0 END),
                SUM(CASE WHEN source_url IS NULL OR source_url='' THEN 1 ELSE 0 END),
                SUM(CASE WHEN license_ref IS NULL OR license_ref='' THEN 1 ELSE 0 END)
            FROM songs WHERE corpus=?
        """, (corpus,)).fetchone()
        rel_gaps = cur.execute("""
            SELECT COUNT(*) FROM songs
            WHERE corpus=? AND release_ok IN ('yes','conditional')
              AND (creator IS NULL OR creator=''
                   OR source_url IS NULL OR source_url=''
                   OR license_ref IS NULL OR license_ref='')
        """, (corpus,)).fetchone()[0]
        print(f"  {corpus:20s} missing creator={gaps[0] or 0}  "
              f"source_url={gaps[1] or 0}  license_ref={gaps[2] or 0}  "
              f"(of {total}); releasable-with-gaps: {rel_gaps}")

    derived = cur.execute("""
        SELECT corpus, COUNT(*) FROM songs
        WHERE derived_from IS NOT NULL GROUP BY corpus
    """).fetchall()
    derived = {c: n for c, n in derived if c in corpora}
    print(f"\n--- derived_from links ---")
    for corpus in corpora:
        print(f"  {corpus:20s}: {derived.get(corpus, 0)}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Multi-corpus lyrics.db inventory")
    ap.add_argument(
        "--corpus", default=None,
        help="Corpus tag (default: all corpora in the DB; 'genius-pro' = legacy report)",
    )
    ap.add_argument("--db", type=Path, default=None, help="lyrics.db path")
    args = ap.parse_args()

    db_path = args.db or (
        Path(__file__).resolve().parent.parent
        / "data" / "toolshop" / "lyrics" / "lyrics.db"
    )
    conn = sqlite3.connect(db_path)
    _ensure_license_columns(conn)  # migrate-on-open for v1-shaped DBs
    cur = conn.cursor()

    if args.corpus:
        corpora = [args.corpus]
    else:
        corpora = [r[0] for r in cur.execute(
            "SELECT DISTINCT corpus FROM songs ORDER BY corpus"
        ).fetchall()]
        # genius-pro first — its block carries the report header.
        corpora.sort(key=lambda c: (c != "genius-pro", c))
        if not corpora:
            print("=== CORPUS INVENTORY ===\n\n(no songs in DB)")
            conn.close()
            return

    # Per-corpus blocks: genius-pro keeps the legacy shape verbatim.
    for corpus in corpora:
        if corpus == "genius-pro":
            report_genius_pro(cur)
        else:
            report_corpus(cur, corpus)

    # License block: for the all-corpora report, and for any non-genius
    # --corpus selection. --corpus genius-pro stays the pure legacy shape.
    if args.corpus is None or args.corpus != "genius-pro":
        report_license(cur, corpora)

    conn.close()


if __name__ == "__main__":
    main()
