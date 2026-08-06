"""Few-shot example retriever for AI lyric generation.

Reads draft lyrics, builds TF-IDF vectors, and retrieves the most
similar professional lyrics from the corpus for use as few-shot
prompt examples.

scikit-learn is imported at function level so the module is importable
without it installed.

Usage::

    from toolshop.similarity_retriever import retrieve_similar
    result = retrieve_similar(Path("draft.txt"), cohort="drill_trap", top_k=5)
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from toolshop.lyricsdb import DEFAULT_DB_PATH, normalize_text


def _load_cohort_songs(
    conn: sqlite3.Connection, cohort: str
) -> List[Dict[str, Any]]:
    """Load all song lyrics for a cohort, concatenated per song.

    Returns list of dicts with: song_id, artist, title, text (concatenated
    normalized lines), and sections (list of section dicts with lines for
    excerpt extraction).
    """
    rows = conn.execute(
        """SELECT s.id, s.primary_artist, s.title,
                  sec.type, sec.ordinal, l.text_norm
           FROM songs s
           JOIN sections sec ON sec.song_id = s.id
           JOIN lines l ON l.section_id = sec.id
           WHERE s.genre_cohort = ? AND s.role = 'solo'
           ORDER BY s.id, sec.ordinal, l.ordinal""",
        (cohort,),
    ).fetchall()

    songs: Dict[int, Dict[str, Any]] = {}
    for song_id, artist, title, sec_type, sec_ordinal, text_norm in rows:
        if song_id not in songs:
            songs[song_id] = {
                "song_id": song_id,
                "artist": artist,
                "title": title,
                "text_parts": [],
                "sections": {},
            }
        songs[song_id]["text_parts"].append(text_norm or "")
        sec_key = (sec_ordinal, sec_type)
        if sec_key not in songs[song_id]["sections"]:
            songs[song_id]["sections"][sec_key] = {
                "type": sec_type,
                "lines": [],
            }
        songs[song_id]["sections"][sec_key]["lines"].append(text_norm or "")

    result: List[Dict[str, Any]] = []
    for song in songs.values():
        song["text"] = " ".join(song["text_parts"])
        del song["text_parts"]
        result.append(song)

    return result


def _extract_excerpt(song: Dict[str, Any], n_lines: int = 4) -> str:
    """Extract the first n_lines from the most similar section.

    Picks the section with the most lines (likely the chorus or a verse)
    and returns its first n_lines.
    """
    sections = list(song["sections"].values())
    if not sections:
        return ""

    # Prefer refren/strofa sections, then longest
    def section_priority(sec: Dict) -> tuple:
        type_order = {"refren": 0, "strofa": 1, "hook": 2}
        return (type_order.get(sec["type"], 3), -len(sec["lines"]))

    sections.sort(key=section_priority)
    best = sections[0]
    lines = best["lines"][:n_lines]
    return "\n".join(lines)


def _format_few_shot_block(
    rank: int, artist: str, title: str, excerpt: str
) -> str:
    """Format a few-shot prompt example block."""
    return (
        f"--- Example {rank} ---\n"
        f"Artist: {artist}\n"
        f"Title: {title}\n"
        f"Excerpt:\n{excerpt}\n"
        f"--- End Example {rank} ---"
    )


def retrieve_similar(
    input_path: Path,
    cohort: str,
    top_k: int = 5,
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Retrieve the most similar professional lyrics for few-shot prompting.

    Args:
        input_path: Path to a plain-text lyrics file (draft or AI-generated).
        cohort: Genre cohort to search within ("drill_trap" or "pop").
        top_k: Number of similar songs to return.
        db_path: Path to lyrics.db.  Defaults to ``DEFAULT_DB_PATH``.

    Returns:
        Dict with:
            - results: list of {rank, artist, title, similarity, excerpt,
              few_shot_block}
            - cohort: the cohort searched
            - top_k: the requested number of results

    Raises:
        ImportError: If scikit-learn is not installed (raised on call, not
            on module import).
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np

    if db_path is None:
        db_path = DEFAULT_DB_PATH

    input_text = Path(input_path).read_text(encoding="utf-8")
    input_norm = normalize_text(input_text)

    conn = sqlite3.connect(str(db_path))
    songs = _load_cohort_songs(conn, cohort)
    conn.close()

    if not songs:
        return {
            "results": [],
            "cohort": cohort,
            "top_k": top_k,
        }

    # Build corpus: input + all cohort songs
    song_texts = [s["text"] for s in songs]
    corpus = [input_norm] + song_texts

    vectorizer = TfidfVectorizer(max_features=5000, ngram_range=(1, 2))
    tfidf_matrix = vectorizer.fit_transform(corpus)

    # Compute cosine similarity between input (row 0) and all songs
    input_vec = tfidf_matrix[0:1]
    song_vecs = tfidf_matrix[1:]
    sims = cosine_similarity(input_vec, song_vecs).flatten()

    # Get top-k indices
    top_indices = np.argsort(sims)[::-1][:top_k]

    results: List[Dict[str, Any]] = []
    for rank, idx in enumerate(top_indices, start=1):
        song = songs[idx]
        excerpt = _extract_excerpt(song)
        similarity = round(float(sims[idx]), 4)
        few_shot = _format_few_shot_block(
            rank, song["artist"], song["title"], excerpt
        )
        results.append({
            "rank": rank,
            "artist": song["artist"],
            "title": song["title"],
            "similarity": similarity,
            "excerpt": excerpt,
            "few_shot_block": few_shot,
        })

    return {
        "results": results,
        "cohort": cohort,
        "top_k": top_k,
    }
