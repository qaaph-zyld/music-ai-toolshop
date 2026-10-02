"""mairina.db: what was shown, what was voted, what got used, and the A/B arms."""

from __future__ import annotations

import json
import random
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

from mairina import DATA_DIR, RANKER_VERSION

ARMS = ("learned", "base")
AB_MIN_VOTES = 100

SCHEMA = """
CREATE TABLE IF NOT EXISTS shown(
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, list_id INTEGER NOT NULL,
  arm TEXT NOT NULL, ranker_version TEXT NOT NULL, kind TEXT NOT NULL, query TEXT,
  candidate TEXT NOT NULL, rank INTEGER NOT NULL, score REAL, features_json TEXT);
CREATE TABLE IF NOT EXISTS lists(
  list_id INTEGER PRIMARY KEY, ts TEXT NOT NULL, kind TEXT NOT NULL, arm TEXT, query TEXT);
CREATE TABLE IF NOT EXISTS votes(shown_id INTEGER NOT NULL, vote INTEGER NOT NULL, ts TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS used(candidate TEXT NOT NULL, source_file TEXT, ts TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_shown_list ON shown(list_id);
CREATE INDEX IF NOT EXISTS idx_votes_shown ON votes(shown_id);
"""
# Only the latest vote per shown item counts (re-voting replaces).
_LATEST = "SELECT v.rowid AS vid, v.shown_id, v.vote FROM votes v WHERE v.rowid IN (SELECT MAX(rowid) FROM votes GROUP BY shown_id)"


class VoteError(Exception):
    """Bad `mt vote` input (CLI exit code 1); nothing is written."""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(path: Path | str | None = None) -> sqlite3.Connection:
    p = Path(path) if path else DATA_DIR / "mairina.db"
    p.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(p))
    con.executescript(SCHEMA)
    return con


def assign_arm(rng: random.Random | None = None) -> str:
    return (rng or random).choice(ARMS)


# One list id per call, even when several request threads (or the CLI in another process)
# log at once: the lock serialises threads, BEGIN IMMEDIATE serialises processes.
_LIST_LOCK = threading.Lock()


def log_shown(con, kind: str, query: str, arm: str, items, ts: str | None = None) -> int:
    """items: iterable of (candidate, score, features). Returns the new list_id.

    The id is allocated and the rows inserted in one write transaction, so two callers
    never share an id. A header row in ``lists`` is written even when ``items`` is empty,
    so an id that was handed out (an empty list) is never reused by the next list.
    """
    ts = ts or now_iso()
    rows = [(ts, i, arm, RANKER_VERSION, kind, query, cand, float(score),
             json.dumps(feats, ensure_ascii=False)) for i, (cand, score, feats) in enumerate(items, 1)]
    with _LIST_LOCK:
        if con.in_transaction:
            con.commit()
        con.execute("BEGIN IMMEDIATE")
        try:
            list_id = con.execute(
                "SELECT MAX(COALESCE((SELECT MAX(list_id) FROM shown), 0),"
                " COALESCE((SELECT MAX(list_id) FROM lists), 0))").fetchone()[0] + 1
            con.execute("INSERT INTO lists(list_id, ts, kind, arm, query) VALUES (?,?,?,?,?)",
                        (list_id, ts, kind, arm, query))
            con.executemany(
                "INSERT INTO shown(ts,list_id,arm,ranker_version,kind,query,candidate,rank,score,features_json)"
                " VALUES (?,?,?,?,?,?,?,?,?,?)",
                [(r[0], list_id, r[2], r[3], r[4], r[5], r[6], r[1], r[7], r[8]) for r in rows])
            con.commit()
        except BaseException:
            con.rollback()
            raise
    return list_id


def last_list(con):
    """(list_id, kind, [(n, shown_id, candidate)]) for the newest list, or None."""
    row = con.execute("SELECT list_id, kind FROM shown ORDER BY id DESC LIMIT 1").fetchone()
    if not row:
        return None
    rows = con.execute("SELECT rank, id, candidate FROM shown WHERE list_id=? ORDER BY rank", (row[0],)).fetchall()
    return row[0], row[1], rows


def list_rows(con, list_id: int):
    """(list_id, kind, [(n, shown_id, candidate)]) for one list, or None when the id was
    never handed out. A list that was logged empty comes back with no items."""
    rows = con.execute("SELECT rank, id, candidate FROM shown WHERE list_id=? ORDER BY rank",
                       (list_id,)).fetchall()
    if rows:
        kind = con.execute("SELECT kind FROM shown WHERE id=?", (rows[0][1],)).fetchone()[0]
        return list_id, kind, rows
    header = con.execute("SELECT kind FROM lists WHERE list_id=?", (list_id,)).fetchone()
    return (list_id, header[0], []) if header else None


def cast_votes(con, pairs, list_id=None) -> int:
    """pairs: [(item_number, +1|-1)]. With ``list_id`` the vote lands on exactly that
    list (unknown/stale ids are an error); omitted means the newest list, as the CLI
    has always done. All-or-nothing."""
    if list_id is None:
        target = last_list(con)
        if target is None:
            raise VoteError("No list to vote on yet. Run anchors, rhyme or multi first.")
    else:
        target = list_rows(con, list_id)
        if target is None:
            raise VoteError(f"Unknown list #{list_id}. The lists shown are numbered "
                            "in each response's list_id.")
    by_n = {n: sid for n, sid, _ in target[2]}
    if pairs and not by_n:
        raise VoteError(f"List #{target[0]} is empty: there is nothing to vote on. Nothing was saved.")
    bad = [n for n, _ in pairs if n not in by_n]
    if bad:
        raise VoteError(f"Item number(s) out of range: {', '.join(map(str, bad))} "
                        f"(list #{target[0]} has 1-{len(by_n)}). Nothing was saved.")
    ts = now_iso()
    con.executemany("INSERT INTO votes(shown_id, vote, ts) VALUES (?,?,?)",
                    [(by_n[n], v, ts) for n, v in pairs])
    con.commit()
    return len(pairs)


def mark_used(con, candidate: str, source_file: str, ts: str | None = None) -> bool:
    """Record a 'used' hit once per (candidate, file). True if newly recorded."""
    if con.execute("SELECT 1 FROM used WHERE candidate=? AND source_file=?", (candidate, source_file)).fetchone():
        return False
    con.execute("INSERT INTO used(candidate, source_file, ts) VALUES (?,?,?)",
                (candidate, source_file, ts or now_iso()))
    con.commit()
    return True


def boosts(con, candidates=None) -> dict[str, tuple[int, int, int]]:
    """{candidate: (up, down, used_count)} for candidates with any history."""
    out: dict[str, list[int]] = {}
    q = f"SELECT s.candidate, SUM(l.vote > 0), SUM(l.vote < 0) FROM ({_LATEST}) l JOIN shown s ON s.id = l.shown_id GROUP BY s.candidate"
    for cand, up, down in con.execute(q):
        out[cand] = [up or 0, down or 0, 0]
    for cand, n in con.execute("SELECT candidate, COUNT(*) FROM used GROUP BY candidate"):
        out.setdefault(cand, [0, 0, 0])[2] = n
    if candidates is not None:
        wanted = set(candidates)
        out = {k: v for k, v in out.items() if k in wanted}
    return {k: tuple(v) for k, v in out.items()}


def _rate(up: int, down: int):
    return None if up + down == 0 else up / (up + down)


def stats(con) -> dict:
    """Week-1 numbers (spec section 2) plus per-arm tallies."""
    votes = con.execute(f"SELECT l.vote, s.arm, s.kind, s.list_id, s.candidate FROM ({_LATEST}) l "
                        "JOIN shown s ON s.id = l.shown_id ORDER BY l.vid").fetchall()
    up = sum(1 for v in votes if v[0] > 0)
    down = len(votes) - up
    first = votes[:50]
    f_up = sum(1 for v in first if v[0] > 0)
    shown_lists = con.execute("SELECT kind, COUNT(DISTINCT list_id), COUNT(*) FROM shown GROUP BY kind").fetchall()
    shown_cands = con.execute("SELECT COUNT(DISTINCT candidate) FROM shown").fetchone()[0]
    used_cands = con.execute("SELECT COUNT(DISTINCT u.candidate) FROM used u "
                             "WHERE u.candidate IN (SELECT candidate FROM shown)").fetchone()[0]
    used_set = {r[0] for r in con.execute("SELECT DISTINCT candidate FROM used")}
    voted_up = {v[3] for v in votes if v[0] > 0}
    multi_lists = [r[0] for r in con.execute(
        "SELECT DISTINCT list_id FROM shown WHERE kind='multi' ORDER BY list_id LIMIT 20")]
    hits = 0
    for lid in multi_lists:
        cands = {r[0] for r in con.execute("SELECT candidate FROM shown WHERE list_id=?", (lid,))}
        if lid in voted_up or cands & used_set:
            hits += 1
    arms = {}
    for arm in ARMS:
        av = [v for v in votes if v[1] == arm]
        a_up = sum(1 for v in av if v[0] > 0)
        lists = con.execute("SELECT COUNT(DISTINCT list_id) FROM shown WHERE arm=?", (arm,)).fetchone()[0]
        arms[arm] = {"lists": lists, "votes": len(av), "up": a_up, "rate": _rate(a_up, len(av) - a_up)}
    return {
        "votes": len(votes), "up": up, "down": down, "rate": _rate(up, down),
        "first50_votes": len(first), "first50_rate": _rate(f_up, len(first) - f_up),
        "by_kind": {k: {"lists": n_l, "items": n_i} for k, n_l, n_i in shown_lists},
        "shown_candidates": shown_cands, "used_candidates": used_cands,
        "used_rate": (used_cands / shown_cands) if shown_cands else None,
        "multi_lists": len(multi_lists), "multi_hits": hits, "arms": arms,
        "ab_ready": len(votes) >= AB_MIN_VOTES,
    }
