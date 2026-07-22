"""BERTopic themes per section.

Assembles per-section docs from ``text_norm`` (skip sections < min_section_lines),
embeds with ``paraphrase-multilingual-MiniLM-L12-v2``, fits ONE BERTopic model
over ALL sections (so topics are comparable across cohorts), populates
``topics`` + ``section_topics``, computes per-artist and per-cohort theme mix.

Embeddings use ``text_norm`` (MiniLM is diacritic-robust).
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any, Dict, List, Optional

from toolshop.lyricsdb import DEFAULT_DB_PATH


def assemble_section_docs(
    conn: sqlite3.Connection,
    min_section_lines: int = 2,
) -> List[Dict[str, Any]]:
    """Assemble per-section documents from text_norm.

    Args:
        conn: SQLite connection.
        min_section_lines: Skip sections with fewer lines than this.

    Returns:
        List of dicts with section_id, song_id, text, and metadata.
    """
    # Get sections with enough lines
    rows = conn.execute(
        """SELECT sec.id, sec.song_id, sec.type,
                  count(l.id) as line_count,
                  group_concat(l.text_norm, '\n') as text
           FROM sections sec
           JOIN lines l ON l.section_id = sec.id
           WHERE l.text_norm IS NOT NULL AND l.text_norm != ''
           GROUP BY sec.id
           HAVING line_count >= ?
           ORDER BY sec.id""",
        (min_section_lines,),
    ).fetchall()

    docs = []
    for row in rows:
        docs.append({
            "section_id": row[0],
            "song_id": row[1],
            "section_type": row[2],
            "text": row[4] or "",
        })

    return docs


def _wipe_topic_tables(conn: sqlite3.Connection) -> None:
    """Clear topic tables for a fresh run."""
    conn.execute("DELETE FROM section_topics")
    conn.execute("DELETE FROM topics")
    conn.commit()


def fit_topics(
    conn: sqlite3.Connection,
    min_section_lines: int = 2,
    seed: int = 42,
) -> Dict[str, Any]:
    """Fit BERTopic model over all sections, populate topics + section_topics.

    Returns summary dict with topic count, size distribution, and per-cohort mix.
    """
    from bertopic import BERTopic
    from sentence_transformers import SentenceTransformer

    # Assemble docs
    docs_data = assemble_section_docs(conn, min_section_lines)
    if not docs_data:
        print("  No sections meet the minimum line threshold.")
        return {"topic_count": 0, "sections_processed": 0}

    docs = [d["text"] for d in docs_data]
    section_ids = [d["section_id"] for d in docs_data]
    song_ids = [d["song_id"] for d in docs_data]

    print(f"  Sections to process: {len(docs)}")

    # Embed with MiniLM
    print(f"  Loading sentence transformer model...")
    model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    print(f"  Embedding {len(docs)} sections...")
    embeddings = model.encode(docs, show_progress_bar=True)

    # Fit BERTopic
    print(f"  Fitting BERTopic model (seed={seed})...")
    import umap
    umap_model = umap.UMAP(n_neighbors=15, n_components=5, metric="cosine", random_state=seed)
    topic_model = BERTopic(
        language=None,  # we provide our own embeddings
        min_topic_size=10,
        calculate_probabilities=False,
        umap_model=umap_model,
        verbose=True,
    )
    topics, probs = topic_model.fit_transform(docs, embeddings)

    # Wipe and populate
    _wipe_topic_tables(conn)

    # Get topic info
    topic_info = topic_model.get_topic_info()
    topic_count = len(topic_info[topic_info.Topic != -1])

    print(f"  Topics found: {topic_count}")
    print(f"  Size distribution:")
    for _, row in topic_info.iterrows():
        tid = int(row["Topic"])
        size = int(row["Count"])
        name = row["Name"]
        if tid == -1:
            print(f"    -1 (outliers): {size}")
        else:
            print(f"    {tid}: {name} ({size})")

    # Populate topics table
    for _, row in topic_info.iterrows():
        tid = int(row["Topic"])
        if tid == -1:
            continue
        size = int(row["Count"])
        name = str(row["Name"])

        # Get top terms for this topic
        top_terms_list = topic_model.get_topic(tid)
        if top_terms_list:
            top_terms = json.dumps(
                [term for term, score in top_terms_list[:10]],
                ensure_ascii=False,
            )
        else:
            top_terms = "[]"

        # Find exemplar section (first section assigned to this topic)
        exemplar_sid = None
        for i, t in enumerate(topics):
            if t == tid:
                exemplar_sid = section_ids[i]
                break

        conn.execute(
            """INSERT INTO topics (topic_id, label, top_terms, size, exemplar_section_id)
               VALUES (?, ?, ?, ?, ?)""",
            (tid, name, top_terms, size, exemplar_sid),
        )

    # Populate section_topics
    for i, tid in enumerate(topics):
        if tid == -1:
            continue
        prob = float(probs[i]) if probs is not None else 1.0
        conn.execute(
            """INSERT OR REPLACE INTO section_topics (section_id, topic_id, probability)
               VALUES (?, ?, ?)""",
            (section_ids[i], int(tid), prob),
        )

    conn.commit()

    # Compute per-cohort theme mix
    cohort_mix = compute_cohort_mix(conn)

    return {
        "topic_count": topic_count,
        "sections_processed": len(docs),
        "cohort_mix": cohort_mix,
    }


def compute_cohort_mix(conn: sqlite3.Connection) -> Dict[str, Any]:
    """Compute per-cohort and per-artist theme mix (share of sections per topic)."""
    # Per-cohort
    cohort_rows = conn.execute(
        """SELECT s.genre_cohort, st.topic_id, count(*) as section_count
           FROM section_topics st
           JOIN sections sec ON st.section_id = sec.id
           JOIN songs s ON sec.song_id = s.id
           WHERE s.role = 'solo' AND s.genre_cohort IS NOT NULL
           GROUP BY s.genre_cohort, st.topic_id
           ORDER BY s.genre_cohort, section_count DESC"""
    ).fetchall()

    # Total sections per cohort
    cohort_totals = {}
    for cohort, tid, count in cohort_rows:
        cohort_totals[cohort] = cohort_totals.get(cohort, 0) + count

    mix = {}
    for cohort, tid, count in cohort_rows:
        if cohort not in mix:
            mix[cohort] = []
        total = cohort_totals[cohort]
        share = count / total if total else 0.0
        mix[cohort].append({
            "topic_id": tid,
            "section_count": count,
            "share": share,
        })

    # Print summary
    print(f"\n=== Per-Cohort Theme Mix ===")
    for cohort, topics in mix.items():
        print(f"\n  {cohort} ({cohort_totals[cohort]} sections):")
        for t in topics[:5]:
            print(f"    topic {t['topic_id']}: {t['section_count']} sections ({t['share']:.1%})")

    # Per-artist
    artist_rows = conn.execute(
        """SELECT s.primary_artist, st.topic_id, count(*) as section_count
           FROM section_topics st
           JOIN sections sec ON st.section_id = sec.id
           JOIN songs s ON sec.song_id = s.id
           WHERE s.role = 'solo' AND s.genre_cohort IS NOT NULL
           GROUP BY s.primary_artist, st.topic_id
           ORDER BY s.primary_artist, section_count DESC"""
    ).fetchall()

    artist_totals = {}
    for artist, tid, count in artist_rows:
        artist_totals[artist] = artist_totals.get(artist, 0) + count

    artist_mix = {}
    for artist, tid, count in artist_rows:
        if artist not in artist_mix:
            artist_mix[artist] = []
        total = artist_totals[artist]
        share = count / total if total else 0.0
        artist_mix[artist].append({
            "topic_id": tid,
            "section_count": count,
            "share": share,
        })

    return {"cohort_mix": mix, "artist_mix": artist_mix}


def run_themes(
    db_path: Optional[Any] = None,
    min_section_lines: int = 2,
    seed: int = 42,
) -> Dict[str, Any]:
    """CLI entry point: fit BERTopic themes on lyrics.db."""
    from pathlib import Path

    if db_path is None:
        db_path = DEFAULT_DB_PATH
    db_path = Path(db_path)

    if not db_path.exists():
        print(f"Database not found: {db_path}")
        print("Run 'toolshop lyrics build-db' first.")
        return {}

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=ON")

    print(f"  Database: {db_path}")
    print(f"  Min section lines: {min_section_lines}")
    print(f"  Seed: {seed}")

    summary = fit_topics(conn, min_section_lines=min_section_lines, seed=seed)

    conn.close()
    return summary
