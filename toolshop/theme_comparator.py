"""Theme Distribution Comparator (B8).

Compares the theme distribution of input lyrics against a specified cohort's
baseline using BERTopic and Jensen-Shannon Divergence.

Requires the ``[lyrics-nlp]`` extra (bertopic, sentence-transformers, scipy).
If bertopic is not installed, returns an error dict with install instructions.
"""

from __future__ import annotations

import json
import math
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from toolshop.lyricsdb import DEFAULT_DB_PATH, normalize_text, parse_section_label


def _parse_input_sections(text: str) -> List[Dict[str, Any]]:
    """Parse raw lyrics text into per-section documents.

    Mirrors the assembly logic in ``themes.assemble_section_docs`` but works
    on raw input text instead of the database.
    """
    sections: List[Dict[str, Any]] = []
    current_type = "other"
    current_lines: List[str] = []

    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue

        label_text = stripped
        if label_text.startswith("[") and label_text.endswith("]"):
            label_text = label_text[1:-1].strip()
        parsed = parse_section_label(label_text)
        if parsed.type != "other" and stripped.startswith("["):
            # Save previous section
            if current_lines:
                sections.append({
                    "section_type": current_type,
                    "text": "\n".join(current_lines),
                })
            current_type = parsed.type
            current_lines = []
        else:
            norm = normalize_text(stripped)
            if norm:
                current_lines.append(norm)

    # Don't forget the last section
    if current_lines:
        sections.append({
            "section_type": current_type,
            "text": "\n".join(current_lines),
        })

    return sections


def _compute_jsd(p: List[float], q: List[float]) -> float:
    """Compute Jensen-Shannon Divergence between two distributions.

    Falls back to a manual implementation if scipy is not available.
    """
    try:
        from scipy.spatial.distance import jensenshannon
        return float(jensenshannon(p, q))
    except ImportError:
        return _jsd_manual(p, q)


def _jsd_manual(p: List[float], q: List[float]) -> float:
    """Manual JSD implementation (natural log, returns sqrt).

    Matches ``scipy.spatial.distance.jensenshannon`` which uses
    natural log and returns the square root of the divergence.
    """
    n = len(p)
    m = [(p[i] + q[i]) / 2.0 for i in range(n)]

    def _kl(a: List[float], b: List[float]) -> float:
        total = 0.0
        for i in range(n):
            if a[i] > 0 and b[i] > 0:
                total += a[i] * math.log(a[i] / b[i])
        return total

    jsd = 0.5 * _kl(p, m) + 0.5 * _kl(q, m)
    return math.sqrt(jsd) if jsd > 0 else 0.0


def _load_cohort_distribution(
    conn: sqlite3.Connection, cohort: str
) -> Tuple[List[int], List[float], Dict[int, str]]:
    """Load cohort theme distribution from ``section_topics`` table.

    Returns:
        (topic_ids, proportions, topic_terms_map)
    """
    rows = conn.execute(
        """SELECT st.topic_id, count(*) as section_count, t.top_terms
           FROM section_topics st
           JOIN sections sec ON st.section_id = sec.id
           JOIN songs s ON sec.song_id = s.id
           LEFT JOIN topics t ON st.topic_id = t.topic_id
           WHERE s.role = 'solo' AND s.genre_cohort = ?
           GROUP BY st.topic_id
           ORDER BY section_count DESC""",
        (cohort,),
    ).fetchall()

    if not rows:
        return [], [], {}

    total = sum(r[1] for r in rows)
    topic_ids = [r[0] for r in rows]
    proportions = [r[1] / total for r in rows]
    terms_map: Dict[int, str] = {}
    for r in rows:
        terms_map[r[0]] = r[2] or "[]"

    return topic_ids, proportions, terms_map


def _compute_input_distribution(
    topics: List[int], num_topics: int
) -> List[float]:
    """Compute topic proportions from BERTopic transform output."""
    counts = [0] * num_topics
    for t in topics:
        if t != -1:
            counts[t] += 1
    total = sum(counts)
    if total == 0:
        return [0.0] * num_topics
    return [c / total for c in counts]


def compare_themes(
    input_path: Path,
    cohort: str,
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Compare input lyrics theme distribution against a cohort baseline.

    Args:
        input_path: Path to a text file with raw lyrics.
        cohort: Genre cohort to compare against (``drill_trap`` or ``pop``).
        db_path: Path to ``lyrics.db``. Defaults to ``DEFAULT_DB_PATH``.

    Returns:
        Dict with ``jsd_score``, ``over_represented``, ``under_represented``,
        ``input_distribution``, and ``cohort_distribution``.

        If bertopic is not installed, returns an error dict with install
        instructions.
    """
    text = Path(input_path).read_text(encoding="utf-8")
    sections = _parse_input_sections(text)

    if not sections:
        return {
            "error": "No sections found in input. Ensure lyrics have "
                     "section labels like [Verse], [Chorus].",
        }

    docs = [s["text"] for s in sections]

    # Load cohort distribution from DB
    db = Path(db_path) if db_path else DEFAULT_DB_PATH
    if not db.exists():
        return {
            "error": f"Database not found: {db}. "
                     "Run 'toolshop lyrics build-db' first.",
        }

    conn = sqlite3.connect(db)
    try:
        cohort_ids, cohort_props, terms_map = _load_cohort_distribution(
            conn, cohort
        )
        if not cohort_ids:
            return {
                "error": f"No theme data for cohort '{cohort}'. "
                         "Run 'toolshop lyrics themes' first.",
            }

        # Determine total number of topics from DB
        max_topic_id = conn.execute(
            "SELECT MAX(topic_id) FROM topics"
        ).fetchone()[0]
        if max_topic_id is None:
            return {
                "error": "No topics found in database. "
                         "Run 'toolshop lyrics themes' first.",
            }
        num_topics = max_topic_id + 1
    finally:
        conn.close()

    # Try to load BERTopic model and transform input
    try:
        from bertopic import BERTopic
        from sentence_transformers import SentenceTransformer
    except ImportError:
        return {
            "error": "bertopic / sentence-transformers not installed. "
                     "Install with: pip install toolshop[lyrics-nlp]",
        }

    # Load the saved BERTopic model (if it was saved during themes run)
    model_dir = db.parent / "bertopic_model"
    if not model_dir.exists():
        return {
            "error": f"BERTopic model not found at {model_dir}. "
                     "Run 'toolshop lyrics themes' first to fit and save the model.",
        }

    topic_model = BERTopic.load(str(model_dir))
    topics, probs = topic_model.transform(docs)

    # Compute input distribution aligned to DB topic IDs
    input_props = _compute_input_distribution(topics, num_topics)

    # Build aligned cohort distribution (fill zeros for topics not in cohort)
    cohort_aligned = [0.0] * num_topics
    for i, tid in enumerate(cohort_ids):
        if tid < num_topics:
            cohort_aligned[tid] = cohort_props[i]

    # Compute JSD
    jsd = _compute_jsd(input_props, cohort_aligned)

    # Identify over/under-represented themes
    over_represented: List[Dict[str, Any]] = []
    under_represented: List[Dict[str, Any]] = []

    for tid in range(num_topics):
        input_pct = input_props[tid]
        cohort_pct = cohort_aligned[tid]
        if input_pct == 0 and cohort_pct == 0:
            continue

        terms = json.loads(terms_map.get(tid, "[]"))
        entry = {
            "topic_id": tid,
            "topic_words": terms[:5] if terms else [],
            "input_pct": round(input_pct, 4),
            "cohort_pct": round(cohort_pct, 4),
        }

        if input_pct > cohort_pct + 0.02:
            over_represented.append(entry)
        elif cohort_pct > input_pct + 0.02:
            under_represented.append(entry)

    over_represented.sort(key=lambda x: x["input_pct"] - x["cohort_pct"], reverse=True)
    under_represented.sort(key=lambda x: x["cohort_pct"] - x["input_pct"], reverse=True)

    return {
        "jsd_score": round(jsd, 4),
        "cohort": cohort,
        "num_sections": len(sections),
        "over_represented": over_represented,
        "under_represented": under_represented,
        "input_distribution": [
            {"topic_id": i, "proportion": round(p, 4)}
            for i, p in enumerate(input_props) if p > 0
        ],
        "cohort_distribution": [
            {"topic_id": tid, "proportion": round(p, 4)}
            for tid, p in zip(cohort_ids, cohort_props)
        ],
    }
