"""Vowel-skeleton rhyme miner for Serbian lyrics.

Implements the Raplyzer method (Malmi): convert text to vowel skeletons,
find matching vowel sequences to detect end/internal rhymes, multisyllabic
chains, and compute rhyme density factors.

Serbian orthography is nearly phonetic — vowel skeletons can be extracted
directly from normalized Latin text without a phonemizer. espeak-ng is used
only for optional validation.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from toolshop.syllables import count_syllables, _VOWELS

# ── Vowel skeleton extraction ─────────────────────────────────────────

_WORD_RE = re.compile(r"[a-zA-Z]+")


def _word_skeleton(word: str) -> str:
    """Extract vowel skeleton from a single word.

    Nuclei = vowels (aeiou) + syllabic r (r with no adjacent vowel).
    Diacritics are stripped to base vowels where possible.
    """
    if not word:
        return ""

    w = word.lower()
    letters = [c for c in w if c.isalpha()]
    if not letters:
        return ""

    # Map diacritics to base vowels
    _DIACRITIC_MAP = {
        "č": "c", "ć": "c", "š": "s", "ž": "z", "đ": "d",
        "á": "a", "à": "a", "ä": "a", "â": "a",
        "é": "e", "è": "e", "ë": "e", "ê": "e",
        "í": "i", "ì": "i", "ï": "i", "î": "i",
        "ó": "o", "ò": "o", "ö": "o", "ô": "o",
        "ú": "u", "ù": "u", "ü": "u", "û": "u",
        "ŕ": "r",
    }
    letters = [_DIACRITIC_MAP.get(c, c) for c in letters]

    skeleton = []
    for i, ch in enumerate(letters):
        if ch in _VOWELS:
            skeleton.append(ch)
        elif ch == "r":
            left_is_vowel = i > 0 and letters[i - 1] in _VOWELS
            right_is_vowel = i < len(letters) - 1 and letters[i + 1] in _VOWELS
            if not left_is_vowel and not right_is_vowel:
                skeleton.append("r")
    return "".join(skeleton)


def vowel_skeleton(text: str) -> str:
    """Extract the vowel skeleton from a line of text.

    Concatenates per-word skeletons: "babone" → "aoe", "da da da" → "aaa".
    """
    if not text or not text.strip():
        return ""
    return "".join(_word_skeleton(m.group()) for m in _WORD_RE.finditer(text))


# ── End rhyme extraction ──────────────────────────────────────────────

def extract_end_rhyme(text: str, n_syllables: int = 2) -> str:
    """Extract the last N vowel-syllables from a line as the end-rhyme key."""
    skel = vowel_skeleton(text)
    if not skel or n_syllables <= 0:
        return ""
    return skel[-n_syllables:] if len(skel) >= n_syllables else skel


# ── Rhyme matching ────────────────────────────────────────────────────

@dataclass
class RhymeMatch:
    """A group of rhyming lines or positions within lines."""

    line_indices: List[int]
    vowel_skeleton: str
    match_length: int
    rhyme_type: str  # 'end' or 'internal'
    position: str = "end"  # 'end', 'internal'


def find_rhymes(
    lines: List[str], min_match: int = 2
) -> List[RhymeMatch]:
    """Find lines with matching end-rhyme vowel skeletons.

    Groups lines by their end-rhyme skeleton (last ``min_match`` syllables).
    Only returns groups with 2+ lines.

    Args:
        lines: List of lyric lines (normalized text).
        min_match: Minimum number of matching syllables for a rhyme.

    Returns:
        List of RhymeMatch objects, one per rhyme group with 2+ members.
    """
    groups: Dict[str, List[int]] = {}
    for i, line in enumerate(lines):
        key = extract_end_rhyme(line, n_syllables=min_match)
        if not key or len(key) < min_match:
            continue
        groups.setdefault(key, []).append(i)

    matches: List[RhymeMatch] = []
    for skel, indices in groups.items():
        if len(indices) >= 2:
            matches.append(RhymeMatch(
                line_indices=indices,
                vowel_skeleton=skel,
                match_length=min_match,
                rhyme_type="end",
                position="end",
            ))
    return matches


def find_internal_rhymes(
    line: str, min_match: int = 2
) -> List[RhymeMatch]:
    """Find internal rhymes within a single line.

    Looks for repeated vowel-skeleton substrings of length >= min_match
    within the line's full skeleton.

    Args:
        line: A single lyric line.
        min_match: Minimum syllable count for a rhyme match.

    Returns:
        List of RhymeMatch objects for internal rhyme pairs.
    """
    skel = vowel_skeleton(line)
    if len(skel) < min_match * 2:
        return []

    # Find all substrings of length >= min_match that appear 2+ times
    matches: List[RhymeMatch] = []
    seen: set[str] = set()

    # Try all substring lengths from longest to shortest
    max_len = len(skel) // 2
    for length in range(max_len, min_match - 1, -1):
        positions: Dict[str, List[int]] = {}
        for start in range(len(skel) - length + 1):
            substr = skel[start:start + length]
            positions.setdefault(substr, []).append(start)

        for substr, poses in positions.items():
            if len(poses) >= 2 and substr not in seen:
                seen.add(substr)
                matches.append(RhymeMatch(
                    line_indices=poses,
                    vowel_skeleton=substr,
                    match_length=length,
                    rhyme_type="internal",
                    position="internal",
                ))

    return matches


# ── Rhyme factor (Malmi-style density) ────────────────────────────────

def rhyme_factor(lines: List[str]) -> float:
    """Compute the rhyme factor (density) for a set of lines.

    Following Malmi's Raplyzer: rhyme_factor = total_rhymed_syllables /
    total_syllables. For each rhyme group, the rhymed syllables are the
    match_length × number_of_lines_in_group. Total syllables is the sum
    of all vowel-skeleton lengths across all lines.

    Returns:
        Float between 0.0 and 1.0.
    """
    if not lines:
        return 0.0

    total_syllables = sum(len(vowel_skeleton(line)) for line in lines)
    if total_syllables == 0:
        return 0.0

    # Find all end-rhyme groups at different match lengths
    # Use the longest match per line group
    rhymed_syllables = 0
    matched_lines: set[int] = set()

    # Try from longest possible match down to 2
    max_skel = max((len(vowel_skeleton(l)) for l in lines), default=0)
    for match_len in range(max_skel, 1, -1):
        groups = find_rhymes(lines, min_match=match_len)
        for group in groups:
            # Only count lines not already matched at a longer length
            new_lines = [i for i in group.line_indices if i not in matched_lines]
            if len(new_lines) >= 2:
                rhymed_syllables += match_len * len(new_lines)
                matched_lines.update(new_lines)

    return round(rhymed_syllables / total_syllables, 4)


# ── Scheme inference ──────────────────────────────────────────────────

def infer_scheme(groups: List[RhymeMatch], n_lines: int) -> str:
    """Infer the rhyme scheme from rhyme groups.

    Assigns letters A, B, C, ... to rhyme groups in order of first
    appearance. Lines not in any group get sequential letters.

    Args:
        groups: List of RhymeMatch objects for end rhymes.
        n_lines: Total number of lines in the section.

    Returns:
        Scheme string like "AABB", "ABAB", "AAA", "free", "AABC".
    """
    if not groups or n_lines == 0:
        return "free" if n_lines > 0 else ""

    # Build line → group-letter mapping
    line_letter: Dict[int, str] = {}
    next_letter = ord("A")

    # Sort groups by first line index for consistent lettering
    sorted_groups = sorted(groups, key=lambda g: min(g.line_indices))

    for group in sorted_groups:
        letter = chr(next_letter)
        next_letter += 1
        for idx in group.line_indices:
            if idx not in line_letter:
                line_letter[idx] = letter

    # Build scheme string
    scheme = []
    for i in range(n_lines):
        if i in line_letter:
            scheme.append(line_letter[i])
        else:
            # Assign a new unique letter to unrhymed lines
            scheme.append(chr(next_letter))
            next_letter += 1

    return "".join(scheme)


# ── Multisyllabic rhymes ──────────────────────────────────────────────

def multisyllabic_rhymes(
    lines: List[str], min_length: int = 3
) -> List[RhymeMatch]:
    """Find multisyllabic rhyme chains (3+ syllable matches).

    Groups lines by their full end-rhyme skeleton of length >= min_length.
    Only returns groups with 2+ lines.

    Args:
        lines: List of lyric lines.
        min_length: Minimum syllable count for multisyllabic rhymes.

    Returns:
        List of RhymeMatch objects for multisyllabic rhyme groups.
    """
    groups: Dict[str, List[int]] = {}
    for i, line in enumerate(lines):
        skel = vowel_skeleton(line)
        if len(skel) < min_length:
            continue
        # Use the last min_length syllables as the key
        key = skel[-min_length:]
        groups.setdefault(key, []).append(i)

    matches: List[RhymeMatch] = []
    for skel, indices in groups.items():
        if len(indices) >= 2:
            matches.append(RhymeMatch(
                line_indices=indices,
                vowel_skeleton=skel,
                match_length=min_length,
                rhyme_type="end",
                position="end",
            ))
    return matches


# ── espeak-ng validation ──────────────────────────────────────────────

def validate_with_espeak(word: str) -> str:
    """Phonemize a word using espeak-ng Serbian voice.

    Requires espeak-ng installed on the system and the ``phonemizer``
    Python package.

    Args:
        word: A single word to phonemize.

    Returns:
        IPA phoneme string from espeak-ng.

    Raises:
        RuntimeError: If espeak-ng is not available.
    """
    from phonemizer.phonemize import phonemize
    return phonemize(word, language="sr", backend="espeak")


# ── DB integration: populate line_rhymes table ────────────────────────

def populate_rhymes(conn, song_id: int) -> int:
    """Compute and store end-rhyme and internal-rhyme groups for a song.

    Persists the true longest match length for each end-rhyme group,
    internal rhymes per line, and per-song rhyme metrics in
    ``song_rhyme_metrics``.

    Args:
        conn: sqlite3.Connection to the lyrics database.
        song_id: The song ID to process.

    Returns:
        Number of rhyme rows inserted.
    """
    cursor = conn.cursor()

    # Fetch all lines for this song, ordered by section ordinal and line ordinal
    cursor.execute(
        """SELECT l.id, l.text_norm
           FROM lines l
           JOIN sections s ON l.section_id = s.id
           WHERE s.song_id = ?
           ORDER BY s.ordinal, l.ordinal""",
        (song_id,),
    )
    rows = cursor.fetchall()
    if not rows:
        return 0

    line_ids = [r[0] for r in rows]
    texts = [r[1] or "" for r in rows]
    total_lines = len(texts)

    inserted = 0

    # ── End rhymes: longest match first (mirrors rhyme_factor logic) ──
    matched_lines: set[int] = set()
    end_rhyme_rows: List[Dict] = []
    group_idx = 0

    max_skel = max((len(vowel_skeleton(t)) for t in texts), default=0)
    for match_len in range(max_skel, 1, -1):
        groups = find_rhymes(texts, min_match=match_len)
        for group in groups:
            new_lines = [i for i in group.line_indices if i not in matched_lines]
            if len(new_lines) >= 2:
                for line_idx in new_lines:
                    conn.execute(
                        """INSERT INTO line_rhymes
                           (song_id, line_id, rhyme_group, rhyme_type,
                            vowel_skeleton, match_length, position)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (
                            song_id,
                            line_ids[line_idx],
                            group_idx,
                            "end",
                            group.vowel_skeleton,
                            match_len,
                            "end",
                        ),
                    )
                    end_rhyme_rows.append({
                        "line_idx": line_idx,
                        "match_length": match_len,
                        "vowel_skeleton": group.vowel_skeleton,
                    })
                    inserted += 1
                matched_lines.update(new_lines)
                group_idx += 1

    # ── Internal rhymes ──
    internal_lines: set[int] = set()
    for i, text in enumerate(texts):
        internal_matches = find_internal_rhymes(text, min_match=2)
        for im in internal_matches:
            conn.execute(
                """INSERT INTO line_rhymes
                   (song_id, line_id, rhyme_group, rhyme_type,
                    vowel_skeleton, match_length, position)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    song_id,
                    line_ids[i],
                    group_idx,
                    "internal",
                    im.vowel_skeleton,
                    im.match_length,
                    "internal",
                ),
            )
            internal_lines.add(i)
            inserted += 1
            group_idx += 1

    # ── Per-song rhyme metrics ──
    rf = rhyme_factor(texts)

    if end_rhyme_rows:
        multi_count = sum(1 for r in end_rhyme_rows if r["match_length"] >= 3)
        pct_multis = round(multi_count / len(end_rhyme_rows), 4)
    else:
        pct_multis = 0.0

    internal_rhyme_rate = round(len(internal_lines) / total_lines, 4) if total_lines else 0.0

    end_groups_for_scheme = find_rhymes(texts, min_match=2)
    scheme = infer_scheme(end_groups_for_scheme, total_lines)

    skel_counts = Counter(r["vowel_skeleton"] for r in end_rhyme_rows)
    top_vowel_pairs = json.dumps(skel_counts.most_common(5))

    conn.execute(
        """INSERT INTO song_rhyme_metrics
           (song_id, rhyme_factor, pct_multis, internal_rhyme_rate,
            dominant_scheme, top_vowel_pairs)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (song_id, rf, pct_multis, internal_rhyme_rate, scheme, top_vowel_pairs),
    )

    return inserted


def get_artist_rhyme_stats(conn, artist: Optional[str] = None) -> List[Dict]:
    """Return per-artist rhyme statistics from the line_rhymes table.

    ``multisyllabic_count`` counts end-rhyme rows only (match_length >= 3).
    """
    cursor = conn.cursor()
    if artist:
        cursor.execute(
            """SELECT
                s.primary_artist,
                count(DISTINCT lr.song_id) as songs_with_rhymes,
                count(*) as total_rhyme_lines,
                round(avg(lr.match_length), 2) as avg_match_length,
                count(CASE WHEN lr.match_length >= 3 AND lr.rhyme_type = 'end' THEN 1 END) as multisyllabic_count
               FROM line_rhymes lr
               JOIN songs s ON lr.song_id = s.id
               WHERE s.primary_artist = ? AND s.corpus = 'genius-pro'
               GROUP BY s.primary_artist
               ORDER BY total_rhyme_lines DESC""",
            (artist,),
        )
    else:
        cursor.execute(
            """SELECT
                s.primary_artist,
                count(DISTINCT lr.song_id) as songs_with_rhymes,
                count(*) as total_rhyme_lines,
                round(avg(lr.match_length), 2) as avg_match_length,
                count(CASE WHEN lr.match_length >= 3 AND lr.rhyme_type = 'end' THEN 1 END) as multisyllabic_count
               FROM line_rhymes lr
               JOIN songs s ON lr.song_id = s.id
               WHERE s.corpus = 'genius-pro'
               GROUP BY s.primary_artist
               ORDER BY total_rhyme_lines DESC"""
        )

    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_artist_rhyme_fingerprints(conn, artist: Optional[str] = None) -> List[Dict]:
    """Return per-artist rhyme fingerprints from song_rhyme_metrics.

    Includes avg rhyme_factor, avg pct_multis, avg internal_rhyme_rate,
    dominant scheme distribution, and top vowel pairs.
    """
    cursor = conn.cursor()
    if artist:
        cursor.execute(
            """SELECT
                s.primary_artist,
                count(*) as song_count,
                round(avg(srm.rhyme_factor), 4) as avg_rhyme_factor,
                round(avg(srm.pct_multis), 4) as avg_pct_multis,
                round(avg(srm.internal_rhyme_rate), 4) as avg_internal_rhyme_rate
               FROM song_rhyme_metrics srm
               JOIN songs s ON srm.song_id = s.id
               WHERE s.primary_artist = ? AND s.corpus = 'genius-pro'
                 AND s.role = 'solo'
               GROUP BY s.primary_artist
               ORDER BY avg_rhyme_factor DESC""",
            (artist,),
        )
    else:
        cursor.execute(
            """SELECT
                s.primary_artist,
                count(*) as song_count,
                round(avg(srm.rhyme_factor), 4) as avg_rhyme_factor,
                round(avg(srm.pct_multis), 4) as avg_pct_multis,
                round(avg(srm.internal_rhyme_rate), 4) as avg_internal_rhyme_rate
               FROM song_rhyme_metrics srm
               JOIN songs s ON srm.song_id = s.id
               WHERE s.corpus = 'genius-pro'
                 AND s.role = 'solo'
               GROUP BY s.primary_artist
               ORDER BY avg_rhyme_factor DESC"""
        )

    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]
