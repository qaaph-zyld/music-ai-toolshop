"""Per-song Serbian-language audit for lyrics.db (lyrics-sr lane).

Scores every song's ``text_norm`` lines with a cheap lexicon vote —
Serbian function words + diacritic-token presence vs English function
words — and emits a per-song verdict: ``sr`` | ``en`` | ``ambiguous``.

Report-only by default: ``audit_languages`` returns the per-song rows and
a summary; ``apply_languages`` writes ``songs.language`` for confident
verdicts only (ambiguous rows stay untouched for eyeballing).

Why a lexicon vote and not a model: ~3,400 songs, language is binary
(sr/en), and both sides are function-word dense — the vote is decisive
except for short/instrumental/interleaved songs, which are exactly the
ones we want flagged ambiguous.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from toolshop.lyricsdb import DEFAULT_DB_PATH

# ── Lexicons ──────────────────────────────────────────────────────────
# ASCII-folded (normalize_text already strips diacritics in text_norm, so
# "jos"/"vec"/"moze" cover both spellings). Function words only — content
# anglicisms (baby/love/night) are constant in sr rap and must not count.

_SR_WORDS = frozenset(
    """i u na je se da ne za mi ti smo sam su me te ga mu joj kao sve od do
    po koji koja koje ali jos kad nema sad vec ovde tu moj moja moje tvoj
    tvoja bio bila bili bila biti moze mozeš hoce hoces necu neces zivot
    nocas sutra nikad uvek svaka svaki svako nego jer ako pa tek samo kod
    nije nismo nisu jesi jesi li onda ovaj ova ovo taj to toga njega nju
    njemu njoj njima nama vama njima takav kakav ovdje tamo vise manje
    preko ispod pre posle izmedju prema protiv uz bez kroz radi stvarno
    bas malo puno svuda nigde igde niko neko svako nikom nikoga ciji cija
    koliko zato ipak bar bas tako ovako onako nikad nikada""".split()
)

_EN_WORDS = frozenset(
    """the and of is are was were will would with not it its this that
    these those be been have has had don't i'm it's you're he's she's
    he she his her what when where how why if then than there can can't
    could couldn't should shouldn't they them their we our us you your
    yours do does didn't doesn't won't ain't gonna wanna gotta let lets
    about into over under between through during before after again once
    here out off up down very really just only even still also too so
    more most other some such no nor own same""".split()
)

_SR_DIACRITIC_RE = re.compile(r"[čćšžđČĆŠŽĐ]")
_WORD_RE = re.compile(r"[a-zA-ZčćšžđČĆŠŽĐ]+")

MIN_TOKENS = 30
SR_THRESHOLD = 0.05
EN_THRESHOLD = -0.02


def _score_song(text: str) -> Dict[str, Any]:
    """Vote on one song's text. Positive score → Serbian."""
    tokens = _WORD_RE.findall(text.lower()) if text else []
    total = len(tokens)
    if total == 0:
        return {"tokens": 0, "sr_hits": 0, "en_hits": 0, "diacritic": 0, "score": 0.0}
    diacritic = sum(1 for t in tokens if _SR_DIACRITIC_RE.search(t))
    sr_hits = sum(1 for t in tokens if t in _SR_WORDS) + diacritic
    en_hits = sum(1 for t in tokens if t in _EN_WORDS)
    return {
        "tokens": total,
        "sr_hits": sr_hits,
        "en_hits": en_hits,
        "diacritic": diacritic,
        "score": round((sr_hits - en_hits) / total, 4),
    }


def _verdict(stats: Dict[str, Any]) -> str:
    if stats["tokens"] < MIN_TOKENS:
        return "ambiguous"
    if stats["score"] >= SR_THRESHOLD:
        return "sr"
    if stats["score"] <= EN_THRESHOLD:
        return "en"
    return "ambiguous"


def audit_languages(
    db_path: Optional[Any] = None,
    corpora: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Score every song in *corpora* (default: all) and return per-song verdicts."""
    db_path = Path(db_path or DEFAULT_DB_PATH)
    conn = sqlite3.connect(str(db_path))

    sql = (
        "SELECT s.id, s.title, s.primary_artist, s.corpus, l.text_norm "
        "FROM songs s "
        "JOIN sections sec ON sec.song_id = s.id "
        "JOIN lines l ON l.section_id = sec.id "
        "WHERE l.text_norm IS NOT NULL AND l.text_norm != '' "
        "ORDER BY s.id"
    )
    params: List[Any] = []
    if corpora:
        ph = ",".join("?" for _ in corpora)
        sql = sql.replace("ORDER BY s.id", f"AND s.corpus IN ({ph}) ORDER BY s.id")
        params.extend(corpora)

    per_song: Dict[int, Dict[str, Any]] = {}
    for song_id, title, artist, corpus, text_norm in conn.execute(sql, params):
        rec = per_song.setdefault(
            song_id,
            {"song_id": song_id, "title": title, "artist": artist, "corpus": corpus,
             "current_language": None, "text": []},
        )
        rec["text"].append(text_norm or "")

    lang_rows = conn.execute("SELECT id, language FROM songs").fetchall()
    conn.close()
    lang_map = {sid: lang for sid, lang in lang_rows}

    results: List[Dict[str, Any]] = []
    summary = {"sr": 0, "en": 0, "ambiguous": 0}
    for song_id, rec in per_song.items():
        text = " ".join(rec.pop("text"))
        stats = _score_song(text)
        verdict = _verdict(stats)
        summary[verdict] += 1
        results.append({
            "song_id": song_id,
            "corpus": rec["corpus"],
            "artist": rec["artist"],
            "title": rec["title"],
            "current_language": lang_map.get(song_id),
            **stats,
            "verdict": verdict,
        })

    results.sort(key=lambda r: r["song_id"])
    return {"songs": results, "summary": summary}


def apply_languages(
    db_path: Optional[Any] = None,
    corpora: Optional[List[str]] = None,
    dry_run: bool = True,
) -> Dict[str, Any]:
    """Write ``songs.language`` for confident verdicts ('sr'/'en').

    Ambiguous songs are left untouched. ``dry_run=True`` returns what
    *would* change without writing.
    """
    db_path = Path(db_path or DEFAULT_DB_PATH)
    report = audit_languages(db_path, corpora)
    updates = [
        (s["verdict"], s["song_id"])
        for s in report["songs"]
        if s["verdict"] in ("sr", "en") and s["current_language"] != s["verdict"]
    ]
    if dry_run:
        return {"dry_run": True, "would_update": len(updates), "summary": report["summary"]}

    conn = sqlite3.connect(str(db_path))
    conn.executemany("UPDATE songs SET language = ? WHERE id = ?", updates)
    conn.commit()
    conn.close()
    return {
        "dry_run": False,
        "updated": len(updates),
        "summary": report["summary"],
    }
