"""Thumbs on xray hints. A rule with >= 3 down-votes and no up-vote is muted
for this user: xray stops showing it and `mt stats` lists it. Hints stay
advisory text with a stable ``rule_id`` (see ``rules``); this module only
stores the user's reaction. No model, no auto-tuning: 'reset' is the undo.
"""

from __future__ import annotations

import re

from mairina import rules
from mairina.votes import VoteError, now_iso

HINT_SCHEMA = """
CREATE TABLE IF NOT EXISTS hint_votes(
  rule_id TEXT NOT NULL, vote INTEGER NOT NULL, ts TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_hint_votes_rule ON hint_votes(rule_id);
"""
MUTE_AFTER_DOWN = 3
MAX_RULE_ID_LEN = 64
_RULE = re.compile(r"^[\w-]+$")


def ensure(con) -> None:
    """Create the hint_votes table if missing (v1 tables are never touched)."""
    con.executescript(HINT_SCHEMA)


def _has_table(con) -> bool:
    return con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='hint_votes'"
                       ).fetchone() is not None


def _check_rule(rule_id: str) -> str:
    rid = (rule_id or "").strip()
    if not _RULE.match(rid):
        raise VoteError(f"Bad rule id '{rule_id}': use letters, digits, '_' or '-' only.")
    return rid


def _check_votable(rule_id: str) -> str:
    """A rule id a vote may be stored under: well-formed, at most 64 chars and a rule
    that exists in ``rules.RULE_IDS``. (``reset`` only needs it well-formed, so votes
    stored under an id that no longer exists can still be cleared.)"""
    rid = _check_rule(rule_id)
    if len(rid) > MAX_RULE_ID_LEN:
        raise VoteError(f"Rule id too long ({len(rid)} chars, max {MAX_RULE_ID_LEN}).")
    if rid not in rules.RULE_IDS:
        raise VoteError(f"Unknown hint rule '{rid}'. Known rules: "
                        f"{', '.join(sorted(rules.RULE_IDS))}.")
    return rid


def vote(con, rule_id: str, v: int) -> tuple[int, int]:
    """Record +1/-1 for a known rule. Returns the rule's new cumulative (up, down)."""
    rid = _check_votable(rule_id)
    if v not in (1, -1):
        raise VoteError("A hint vote is + or - (or 'reset').")
    ensure(con)
    con.execute("INSERT INTO hint_votes(rule_id, vote, ts) VALUES (?,?,?)", (rid, v, now_iso()))
    con.commit()
    return counts(con).get(rid, (0, 0))


def reset(con, rule_id: str) -> int:
    """Forget every vote on the rule (unmutes it). Returns how many rows went."""
    rid = _check_rule(rule_id)
    if not _has_table(con):
        return 0
    n = con.execute("DELETE FROM hint_votes WHERE rule_id=?", (rid,)).rowcount
    con.commit()
    return n


def counts(con) -> dict[str, tuple[int, int]]:
    """{rule_id: (up, down)}, cumulative. Tolerates a db without the table."""
    if not _has_table(con):
        return {}
    return {rid: (up or 0, down or 0) for rid, up, down in con.execute(
        "SELECT rule_id, SUM(vote > 0), SUM(vote < 0) FROM hint_votes GROUP BY rule_id")}


def muted(con) -> list[str]:
    """Rule ids with >= 3 down-votes and 0 up-votes, sorted."""
    return sorted(rid for rid, (up, down) in counts(con).items()
                  if down >= MUTE_AFTER_DOWN and up == 0)
