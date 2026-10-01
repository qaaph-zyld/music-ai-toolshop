"""Stars on the user's own lines and the personal fingerprint built from them.

A star stores the user's own line, its lane, free tags (metaphor, double-meaning,
wordplay, punchline or any text - tags are NEVER auto-detected) and a snapshot of
mechanically measured features. The fingerprint is the shrunk mean of those
features toward the corpus lane prior (empirical Bayes, k = 8):

    shrunk = (n * x_bar + K * mu_lane) / (n + K)

``compare`` then reports the largest deviations of a line from that fingerprint,
in plain words, as z-scores against the lane's own spread. It only measures: it
never suggests or writes a line.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from toolshop.syllables import count_line

from mairina import LANES, corpus, devices
from mairina import used as used_mod
from mairina.used import tokenize
from mairina.votes import VoteError, now_iso

STAR_SCHEMA = """
CREATE TABLE IF NOT EXISTS stars(
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, file TEXT, line_no INTEGER NOT NULL,
  text TEXT NOT NULL, lane TEXT NOT NULL, tags_json TEXT NOT NULL, feats_json TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_stars_lane ON stars(lane);
"""
SHRINK_K = 8                  # pseudo-observations of the lane prior
LOW_CONFIDENCE_N = 10         # fewer stars than this: say so
MIN_STARS_FOR_XRAY = 3        # `mt xray` shows the vs-star column from this many stars
MIN_Z = 0.5                   # smaller deviations are not worth a sentence
MAX_TAG_LEN = 40
COMPARE_FEATURES = ("syllables", "words", "cons_density", "end_tail", "allit")


def ensure(con) -> None:
    """Create the stars table if missing (v1 tables are never touched)."""
    con.executescript(STAR_SCHEMA)


def _has_table(con) -> bool:
    return con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='stars'"
                       ).fetchone() is not None


def lyric_lines(path: Path | str) -> list[str]:
    """The lyric lines `mt xray` numbers: blank lines and [Section] headers skipped."""
    lines = [raw.strip() for raw in used_mod.read_text(path).splitlines()]
    return [l for l in lines if l and not (l.startswith("[") and l.endswith("]"))]


def normalize_tags(tags) -> list[str]:
    """Lowercase, trim, collapse spaces, drop duplicates (order kept)."""
    out: list[str] = []
    for raw in tags or ():
        tag = " ".join(str(raw).lower().split())
        if not tag:
            raise VoteError("Empty tag: use e.g. --tag punchline.")
        if len(tag) > MAX_TAG_LEN:
            raise VoteError(f"Tag too long ({len(tag)} chars, max {MAX_TAG_LEN}): '{tag[:20]}...'.")
        if tag not in out:
            out.append(tag)
    return out


def snapshot(lr) -> dict:
    """Feature snapshot of one analysed line (``devices.LineReport``)."""
    kinds = sorted(devices.device_kinds(lr.devices))
    multi = max((len(d["span"]) for d in lr.devices if d["kind"] == "multisyllabic_rhyme"),
                default=0)
    feats = devices.line_features(lr.syllables, lr.cons_density, tokenize(lr.text), kinds, multi)
    feats["kinds"] = kinds
    return feats


def _context(lyrics_db, data_dir):
    """(gazetteer, index) loaded like `mt xray`, degraded when lyrics.db is unavailable."""
    try:
        gazetteer = devices.load_gazetteer(str(lyrics_db or corpus.DEFAULT_LYRICS_DB))
        return gazetteer, corpus.load_index(lyrics_db, data_dir)
    except corpus.DbUnavailable as exc:
        print(f"Note: {exc} - star features computed without the corpus gazetteer/index.",
              file=sys.stderr)
        return frozenset(), None


def _row(r) -> dict:
    return {"id": r[0], "ts": r[1], "file": r[2], "line_no": r[3], "text": r[4], "lane": r[5],
            "tags": json.loads(r[6]), "feats": json.loads(r[7])}


_COLS = "id, ts, file, line_no, text, lane, tags_json, feats_json"


def star(con, path: Path | str, line_no: int, lane: str = "all", tags=(),
         lyrics_db=None, data_dir=None) -> dict:
    """Star lyric line ``line_no`` (the number `mt xray` prints) of the user's file.

    Starring the same text of the same file in the same lane again updates that
    star (tags merge) instead of counting the line twice. Returns the stored row
    plus ``updated: bool``.
    """
    if lane not in LANES:
        raise VoteError(f"Unknown lane '{lane}' (use {', '.join(LANES)}).")
    tags = normalize_tags(tags)
    lines = lyric_lines(path)
    if not 1 <= line_no <= len(lines):
        raise VoteError(f"Line {line_no} is out of range: {Path(path).name} has {len(lines)} "
                        "lyric line(s) (blank lines and [Section] headers are not numbered).")
    gazetteer, index = _context(lyrics_db, data_dir)
    lr = devices.analyze_verse(lines, gazetteer, index).lines[line_no - 1]
    feats = snapshot(lr)
    ensure(con)
    file_key = str(Path(path).resolve())
    prev = con.execute(f"SELECT {_COLS} FROM stars WHERE file=? AND text=? AND lane=?",
                       (file_key, lr.text, lane)).fetchone()
    if prev:
        merged = list(dict.fromkeys(json.loads(prev[6]) + tags))
        con.execute("UPDATE stars SET ts=?, line_no=?, tags_json=?, feats_json=? WHERE id=?",
                    (now_iso(), line_no, json.dumps(merged, ensure_ascii=False),
                     json.dumps(feats), prev[0]))
        sid, updated = prev[0], True
    else:
        sid = con.execute(
            "INSERT INTO stars(ts, file, line_no, text, lane, tags_json, feats_json) "
            "VALUES (?,?,?,?,?,?,?)",
            (now_iso(), file_key, line_no, lr.text, lane,
             json.dumps(tags, ensure_ascii=False), json.dumps(feats))).lastrowid
        updated = False
    con.commit()
    row = _row(con.execute(f"SELECT {_COLS} FROM stars WHERE id=?", (sid,)).fetchone())
    row["updated"] = updated
    return row


def stars(con, lane: str | None = None) -> list[dict]:
    """Stored stars, oldest first. ``lane`` None or 'all' pools every star."""
    if not _has_table(con):
        return []
    if lane and lane != "all":
        rows = con.execute(f"SELECT {_COLS} FROM stars WHERE lane=? ORDER BY id", (lane,))
    else:
        rows = con.execute(f"SELECT {_COLS} FROM stars ORDER BY id")
    return [_row(r) for r in rows]


def unstar(con, star_id: int) -> bool:
    """Remove a star. False when there is no such id."""
    if not _has_table(con):
        return False
    n = con.execute("DELETE FROM stars WHERE id=?", (star_id,)).rowcount
    con.commit()
    return n > 0


def _std(xs: list[float]) -> float:
    if not xs:
        return 0.0
    m = sum(xs) / len(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / len(xs))


def fingerprint(con, lane: str = "all", priors: dict | None = None, rows: list | None = None) -> dict:
    """The personal fingerprint over the lane's stars.

    ``priors`` = ``{feature: (mu_lane, sigma_lane)}`` (``atlas.lane_numeric``). Without a
    prior the shrunk mean falls back to the plain mean; a missing or non-positive sigma
    falls back to the population std of the stars (else 1.0).
    """
    rows = stars(con, lane) if rows is None else rows
    n = len(rows)
    priors = priors or {}
    numeric: dict[str, dict] = {}
    for f in devices.NUMERIC_FEATURES:
        xs = [float(r["feats"][f]) for r in rows if f in r["feats"]]
        if not xs:
            continue
        nf, mean = len(xs), sum(xs) / len(xs)
        mu, sigma = priors.get(f, (None, None))
        shrunk = (nf * mean + SHRINK_K * mu) / (nf + SHRINK_K) if mu is not None else mean
        if sigma and sigma > 0:
            source = "lane"
        else:
            sigma, source = (_std(xs), "stars")
            if sigma <= 0:
                sigma, source = 1.0, "default"
        numeric[f] = {"n": nf, "mean": mean, "shrunk": shrunk, "mu": mu,
                      "sigma": sigma, "sigma_source": source}

    def rates(items):
        counts: dict[str, int] = {}
        for r in rows:
            for it in set(items(r)):
                counts[it] = counts.get(it, 0) + 1
        return {k: v / n for k, v in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))}

    return {"n": n, "lane": lane, "numeric": numeric,
            "tag_rates": rates(lambda r: r["tags"]),
            "kind_rates": rates(lambda r: r["feats"].get("kinds", [])),
            "allit_rate": numeric["allit"]["mean"] if "allit" in numeric else 0.0,
            "low_confidence": n < LOW_CONFIDENCE_N}


def _values(text: str) -> dict[str, float]:
    """The per-line computable features `compare` can judge (multi_len needs other lines)."""
    tokens = tokenize(text)
    return {"syllables": float(count_line(text)), "words": float(len(tokens)),
            "cons_density": devices.consonance_density(text),
            "end_tail": float(devices.end_tail_len(tokens)),
            "allit": 1.0 if devices.has_alliteration(tokens) else 0.0}


def _n(v: float) -> str:
    """9 -> '9', 10.8 -> '10.8': keep one decimal only when it says something."""
    return f"{v:.1f}".rstrip("0").rstrip(".")


def _phrase(feature: str, x: float, nf: dict) -> str:
    shrunk, below = nf["shrunk"], x < nf["shrunk"]
    if feature == "syllables":
        return f"{'shorter' if below else 'longer'} than your ★ lines: {x:g} vs {_n(shrunk)} syllables"
    if feature == "words":
        return f"{'fewer' if below else 'more'} words than your ★ lines: {x:g} vs {_n(shrunk)}"
    if feature == "cons_density":
        return f"{'sparser' if below else 'denser'} consonance than your ★ lines: {x:.2f} vs {shrunk:.2f}"
    if feature == "end_tail":
        return (f"{'shorter' if below else 'longer'} end-rhyme tail than your ★ lines: "
                f"{x:g} vs {_n(shrunk)} letters")
    # like the other phrases, quote the shrunk value the z-score was measured against
    return (f"no alliteration here; your ★ lines run ~{shrunk:.0%} alliterative" if below
            else f"alliteration here; your ★ lines run only ~{shrunk:.0%} alliterative")


def deviations(text: str, fp: dict, skip=()) -> list[tuple[str, float, str]]:
    """``[(feature, z, phrase)]`` sorted by |z| desc, only |z| >= MIN_Z. z is the line's
    distance from the shrunk mean in lane standard deviations. ``skip`` names features
    to leave out (the xray row already shows ``allit`` itself)."""
    if not fp or not fp.get("n"):
        return []
    vals = _values(text)
    out = []
    for f in COMPARE_FEATURES:
        nf = fp["numeric"].get(f)
        if not nf or f in skip:
            continue
        z = (vals[f] - nf["shrunk"]) / nf["sigma"]
        if abs(z) >= MIN_Z:
            out.append((f, z, _phrase(f, vals[f], nf)))
    out.sort(key=lambda t: (-abs(t[1]), t[0]))
    return out


def compare(text: str, fp: dict, top: int = 3, skip=()) -> list[str]:
    """The ``top`` largest deviations of ``text`` from the fingerprint, in plain words."""
    return [phrase for _f, _z, phrase in deviations(text, fp, skip)[:top]]


def render(fp: dict, lane: str) -> list[str]:
    """Printable fingerprint (numbers only; the user's own lines are not repeated)."""
    if not fp["n"]:
        return [f"No stars yet for lane '{lane}'. Star a line: mt star <file> <line_no> [--tag T]"]
    head = f"Your fingerprint  lane={lane}  n={fp['n']} starred line(s)"
    if fp["low_confidence"]:
        head += f"  - low confidence (<{LOW_CONFIDENCE_N} stars)"
    out = [head, f"{'feature':<14}{'your mean':>10}{'shrunk':>9}{'lane mu':>9}{'sigma':>8}"]
    for f in devices.NUMERIC_FEATURES:
        nf = fp["numeric"].get(f)
        if not nf:
            continue
        mu = "n/a" if nf["mu"] is None else f"{nf['mu']:.2f}"
        out.append(f"{f:<14}{nf['mean']:>10.2f}{nf['shrunk']:>9.2f}{mu:>9}{nf['sigma']:>8.2f}")
    if fp["tag_rates"]:
        out.append("tags:    " + ", ".join(f"{k} {v:.0%}" for k, v in fp["tag_rates"].items()))
    if fp["kind_rates"]:
        out.append("devices: " + ", ".join(f"{k} {v:.0%}" for k, v in fp["kind_rates"].items()))
    if any(nf["mu"] is None for nf in fp["numeric"].values()):
        out.append("(no corpus prior available: shrunk = your plain mean)")
    return out
