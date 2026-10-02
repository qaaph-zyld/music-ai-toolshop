"""Stars on the user's own lines and the personal fingerprint built from them.

A star stores the user's own line, its lane, free tags (metaphor, double-meaning,
wordplay, punchline or any text - tags are NEVER auto-detected) and a snapshot of
mechanically measured features. The fingerprint is the shrunk mean of those
features toward the corpus lane prior (empirical Bayes, k = 8):

    shrunk = (n * x_bar + K * mu_lane) / (n + K)

``compare`` then reports the largest deviations of a line from that fingerprint,
in plain words. The shrunk mean and the lane's spread only rank the deviations
(z-scores); the words always quote the user's own raw star mean, the number the
user can check against their stars. It only measures: it never suggests or writes
a line.

A star saved with lane 'all' belongs to every lane's view; a lane-specific star
belongs to its own lane (and to 'all') only.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
import unicodedata
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
MAX_DRAFT_ID_LEN = 200        # an opaque UI draft identity, never a filesystem path
FEATS_VERSION = 1             # stamped into every new star snapshot; rows without it are version 0
COMPARE_FEATURES = ("syllables", "words", "cons_density", "end_tail", "allit")


def ensure(con) -> None:
    """Create the stars table if missing (v1 tables are never touched)."""
    con.executescript(STAR_SCHEMA)


def _has_table(con) -> bool:
    return con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='stars'"
                       ).fetchone() is not None


def lyric_lines_from_text(text: str) -> list[str]:
    """The lyric lines `mt xray` numbers, straight from text (no file)."""
    lines = [raw.strip() for raw in unicodedata.normalize("NFC", text).splitlines()]
    return [l for l in lines if l and not (l.startswith("[") and l.endswith("]"))]


def lyric_lines(path: Path | str) -> list[str]:
    """The lyric lines `mt xray` numbers: blank lines and [Section] headers skipped."""
    return lyric_lines_from_text(used_mod.read_text(path))


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
    feats["feats_version"] = FEATS_VERSION
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
    feats = json.loads(r[7])
    feats.setdefault("feats_version", 0)           # snapshots from before versioning
    return {"id": r[0], "ts": r[1], "file": r[2], "line_no": r[3], "text": r[4], "lane": r[5],
            "tags": json.loads(r[6]), "feats": feats}


_COLS = "id, ts, file, line_no, text, lane, tags_json, feats_json"


def _check_line(lines: list[str], line_no: int, where: str) -> None:
    """Shared star() guards: the lyric-line number must exist and hold a word."""
    if not 1 <= line_no <= len(lines):
        raise VoteError(f"Line {line_no} is out of range: {where} has {len(lines)} "
                        "lyric line(s) (blank lines and [Section] headers are not numbered).")
    if not tokenize(lines[line_no - 1]):
        raise VoteError(f"Line {line_no} has no words ('{lines[line_no - 1][:30]}'): "
                        "a star needs at least one word to measure.")


def _store_star(con, lines: list[str], file_key: str, where: str, line_no: int,
                lane: str, tags: list[str], gazetteer, index) -> dict:
    """Analyse `lines`, snapshot lyric line `line_no` and upsert it under
    (file_key, text, lane). Returns the stored row plus ``updated: bool``."""
    _check_line(lines, line_no, where)
    lr = devices.analyze_verse(lines, gazetteer, index).lines[line_no - 1]
    feats = snapshot(lr)
    ensure(con)
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


def star(con, path: Path | str, line_no: int, lane: str = "all", tags=(),
         lyrics_db=None, data_dir=None) -> dict:
    """Star lyric line ``line_no`` (the number `mt xray` prints) of the user's file.

    Starring the same text of the same file in the same lane again updates that
    star (tags merge) instead of counting the line twice. Returns the stored row
    plus ``updated: bool``. A line with no word in it ('...', '123') is rejected.
    """
    if lane not in LANES:
        raise VoteError(f"Unknown lane '{lane}' (use {', '.join(LANES)}).")
    tags = normalize_tags(tags)
    lines = lyric_lines(path)
    gazetteer, index = _context(lyrics_db, data_dir)
    return _store_star(con, lines, str(Path(path).resolve()), Path(path).name,
                       line_no, lane, tags, gazetteer, index)


def draft_key(draft_id, text: str) -> str:
    """The ``file`` column key for a text draft: ``draft:<id>`` or ``text:<sha1[:16]>``.

    ``draft_id`` is the caller's opaque draft identity (a UI localStorage key);
    it is validated here and NEVER treated as a filesystem path.
    """
    if draft_id is not None:
        draft_id = str(draft_id).strip()
        if not draft_id or len(draft_id) > MAX_DRAFT_ID_LEN:
            raise VoteError(f"draft_id must be 1-{MAX_DRAFT_ID_LEN} characters.")
        return f"draft:{draft_id}"
    return "text:" + hashlib.sha1(
        unicodedata.normalize("NFC", text).encode("utf-8")).hexdigest()[:16]


def star_text(con, text: str, line_no: int, lane: str = "all", tags=(),
              draft_id=None, lyrics_db=None, data_dir=None, context=None) -> dict:
    """``star`` for the API: the draft arrives as text, not as a file.

    ``draft_id`` is the caller's opaque draft identity (a UI localStorage key); it is
    stored in the ``file`` column as ``draft:<id>`` and is NEVER treated as a path.
    Without it the draft key is ``text:<sha1 of the draft>`` — stable for identical
    text, so re-starring the same line still updates instead of duplicating.
    ``context`` may pass a preloaded ``(gazetteer, index)``; None loads like the CLI.
    """
    if lane not in LANES:
        raise VoteError(f"Unknown lane '{lane}' (use {', '.join(LANES)}).")
    tags = normalize_tags(tags)
    file_key = draft_key(draft_id, text)
    lines = lyric_lines_from_text(text)
    if context is None:
        gazetteer, index = _context(lyrics_db, data_dir)
    else:
        gazetteer, index = context
    return _store_star(con, lines, file_key, "the draft", line_no, lane, tags,
                       gazetteer, index)


def stars(con, lane: str | None = None) -> list[dict]:
    """Stored stars, oldest first. ``lane`` None or 'all' pools every star; a specific
    lane returns that lane's stars plus those saved with lane 'all' (they fit every
    lane), never another specific lane's."""
    if not _has_table(con):
        return []
    if lane and lane != "all":
        rows = con.execute(f"SELECT {_COLS} FROM stars WHERE lane IN (?, 'all') ORDER BY id",
                           (lane,))
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
    """One deviation in plain words. It quotes the user's RAW star mean (``mean``), never
    the shrunk value (that only ranks), and says which way the line sits against it.
    Fewer than ``LOW_CONFIDENCE_N`` stars: the actual n is appended, e.g. ' (n=3)'."""
    mean, below = nf["mean"], x < nf["mean"]
    if feature == "syllables":
        text = f"{'shorter' if below else 'longer'} than your ★ lines: {x:g} vs {_n(mean)} syllables"
    elif feature == "words":
        text = f"{'fewer' if below else 'more'} words than your ★ lines: {x:g} vs {_n(mean)}"
    elif feature == "cons_density":
        text = f"{'sparser' if below else 'denser'} consonance than your ★ lines: {x:.2f} vs {mean:.2f}"
    elif feature == "end_tail":
        text = (f"{'shorter' if below else 'longer'} end-rhyme tail than your ★ lines: "
                f"{x:g} vs {_n(mean)} letters")
    elif below:
        text = f"no alliteration here; your ★ lines run ~{mean:.0%} alliterative"
    else:
        text = f"alliteration here; your ★ lines run only ~{mean:.0%} alliterative"
    return text + (f" (n={nf['n']})" if nf["n"] < LOW_CONFIDENCE_N else "")


def deviations(text: str, fp: dict, skip=()) -> list[tuple[str, float, str]]:
    """``[(feature, z, phrase)]`` sorted by |z| desc, only |z| >= MIN_Z. z is the line's
    distance from the shrunk mean in lane standard deviations (ranking only: the phrase
    quotes the raw star mean). The raw and the shrunk mean must agree on which side the
    line sits: a line between them (or equal to the raw mean) would make the sentence
    contradict the ranking, so it is left out. ``skip`` names features to leave out
    (the xray row already shows ``allit`` itself)."""
    if not fp or not fp.get("n"):
        return []
    vals = _values(text)
    out = []
    for f in COMPARE_FEATURES:
        nf = fp["numeric"].get(f)
        if not nf or f in skip:
            continue
        z = (vals[f] - nf["shrunk"]) / nf["sigma"]
        if abs(z) >= MIN_Z and (vals[f] - nf["mean"]) * z > 0:
            out.append((f, z, _phrase(f, vals[f], nf)))
    out.sort(key=lambda t: (-abs(t[1]), t[0]))
    return out


def compare(text: str, fp: dict, top: int = 3, skip=()) -> list[str]:
    """The ``top`` largest deviations of ``text`` from the fingerprint, in plain words."""
    return [phrase for _f, _z, phrase in deviations(text, fp, skip)[:top]]


def vs_star_phrase(text: str, fp: dict) -> str:
    """The xray/API vs★ cell: the top-1 deviation (allit excluded — the row shows
    it) or the low-n aware 'close to your ★ lines' fallback. Quotes raw means."""
    top = compare(text, fp, top=1, skip=("allit",))
    near = "close to your ★ lines" + (f" (n={fp['n']})" if fp["low_confidence"] else "")
    return top[0] if top else near


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
