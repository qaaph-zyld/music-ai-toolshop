"""Persistent word bans — suggestions never offer a banned word again.

Stored per-user in mairina.db (``word_bans``), beside votes/stars. Banning is
a user preference, not a corpus fact: the word still exists, still counts in
xray/used scans and stays unbannable from the footer list. ``mt unban`` (or
the x next to a ban) is the undo. Applies to anchors, rhymes, multis and
compare picks — the tool finds words; the user writes every line.
"""

from __future__ import annotations

from mairina.votes import VoteError, now_iso

BAN_SCHEMA = """
CREATE TABLE IF NOT EXISTS word_bans(
  word TEXT PRIMARY KEY, ts TEXT NOT NULL);
"""
MAX_WORD_LEN = 64


def ensure(con) -> None:
    """Create the word_bans table if missing (v1 tables are never touched)."""
    con.executescript(BAN_SCHEMA)


def _has_table(con) -> bool:
    return con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='word_bans'"
                       ).fetchone() is not None


def _check_word(word: str) -> str:
    w = (word or "").strip().lower()
    if not w:
        raise VoteError("Ban needs a word.")
    if len(w) > MAX_WORD_LEN:
        raise VoteError(f"Word too long ({len(w)} chars, max {MAX_WORD_LEN}).")
    if any(ch.isspace() for ch in w):
        raise VoteError("Ban takes one word — phrases are not ban-able.")
    return w


def ban(con, word: str) -> str:
    """Persist a ban; returns the normalized word. Idempotent."""
    w = _check_word(word)
    ensure(con)
    con.execute("INSERT OR IGNORE INTO word_bans(word, ts) VALUES (?,?)", (w, now_iso()))
    con.commit()
    return w


def unban(con, word: str) -> bool:
    """Remove a ban. Returns False when the word was not banned."""
    w = _check_word(word)
    if not _has_table(con):
        return False
    n = con.execute("DELETE FROM word_bans WHERE word=?", (w,)).rowcount
    con.commit()
    return n > 0


def list_bans(con) -> set[str]:
    """All banned words. Tolerates a db without the table."""
    if not _has_table(con):
        return set()
    return {r[0] for r in con.execute("SELECT word FROM word_bans")}


def list_with_ts(con) -> list[dict]:
    """[{word, ts}] newest-first — the footer/manage view."""
    if not _has_table(con):
        return []
    return [{"word": w, "ts": ts} for w, ts in con.execute(
        "SELECT word, ts FROM word_bans ORDER BY ts DESC")]
