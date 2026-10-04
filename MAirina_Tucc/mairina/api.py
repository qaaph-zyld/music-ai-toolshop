"""Local Flask API over the MAirina engine — the rimer-ui front end talks to it.

Thin adapter only: every number, list and tag comes from the same engine
functions the CLI calls (same arm/vote logging, same corpus guards). The app
binds 127.0.0.1:8000 — the Vite dev proxy targets it — and answers JSON on
every path, including errors (never an HTML page). Corpus-dependent routes
return 503 when the corpus index could not be built at startup; the app itself
always starts. The engine finds and analyses; it never writes lyric lines.

Hardening (wave 3S): only the 127.0.0.1 / localhost Host headers are served
(DNS rebinding) and requests the browser marks "Sec-Fetch-Site: cross-site" are
refused; every free-text input has a size cap checked before any analysis; the
corpus atlas is built once in a background thread at startup, never inside a
request; error bodies never carry an absolute path or a traceback.
"""

from __future__ import annotations

import logging
import os
import random
import re
import sqlite3
import threading
import time
from pathlib import Path

from flask import Flask, current_app, jsonify, request
from werkzeug.exceptions import HTTPException, SecurityError

from mairina import DATA_DIR, DEFAULT_LYRICS_DB, LANES, anchors as anchors_mod, corpus, devices
from mairina import atlas as atlas_mod, bans, comparisons, dialect as dialect_mod, fingerprint, hints
from mairina import multis as multis_mod, rank, rules, targets
from mairina import used as used_mod, votes
from mairina.cli import _create_app_db, _open_app_db, _pack

HOST, PORT = "127.0.0.1", 8000
MAX_TEXT_CHARS = 20_000        # a draft's whole text; bigger is a client bug, not a lyric
MAX_TEXT_LINES = 300           # lines of an xray / star / used draft (the pairwise passes are O(n^2))
MAX_LINE_CHARS = 500           # one lyric line of a draft, and the rhyme 'line' (analysis is ~O(n^2) in it)
MAX_WORD_CHARS = 200           # word / phrase / seed / theme
MAX_ARTISTS = 20
MAX_ARTIST_CHARS = 64
MAX_TAGS = 20
MAX_TAG_CHARS = 64
MAX_VOTE_ITEMS = 256
MAX_EXCLUDE = 64               # words a swap excludes (one anchor set, plus slack)
DIALECTS = ("all", "ekavica")
SQLITE_MAX_INT = 2**63 - 1
TRUSTED_HOSTS = ("127.0.0.1", "localhost")      # Werkzeug ignores the port when matching
ATLAS_WARMING = "Corpus atlas is warming up (first run ~20 s) - retry shortly"
ATLAS_RETRY_SECS = 30.0        # a failed warm-up is retried (single-flight) after this long
MAX_RESULTS = 20               # the contract has no page size — the CLI default
USED_DAYS = 14                 # `mt used` default window


class ApiError(Exception):
    """Abort with a JSON ``{error: message}`` at ``status`` (never an HTML page)."""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


# --- request validation -----------------------------------------------------

def _state() -> dict:
    return current_app.extensions["mairina"]


def _index():
    """The corpus index loaded at startup, or a 503 corpus error."""
    st = _state()
    if st["index"] is None:
        raise ApiError(503, st["corpus_error"] or "corpus index unavailable")
    return st["index"]


def _body() -> dict:
    try:
        data = request.get_json(silent=True)
    except RecursionError:                      # absurdly nested JSON: not a ValueError, so not "silent"
        raise ApiError(400, "expected a JSON object body (nested too deeply)") from None
    if not isinstance(data, dict):
        raise ApiError(400, "expected a JSON object body")
    return data


def _capped(v: str, key: str, max_chars: int | None) -> str:
    if max_chars is not None and len(v) > max_chars:
        raise ApiError(413, f"'{key}' too long ({len(v)} chars, max {max_chars})")
    return v


def _req_str(d: dict, key: str, max_chars: int | None = None) -> str:
    v = d.get(key)
    if not isinstance(v, str) or not v.strip():
        raise ApiError(400, f"'{key}' is required (non-empty string)")
    return _capped(v.strip(), key, max_chars)


def _opt_str(v, key: str, max_chars: int | None = None):
    if v is None:
        return None
    if not isinstance(v, str):
        raise ApiError(400, f"'{key}' must be a string or null")
    return _capped(v.strip(), key, max_chars) or None


def _req_text(d: dict, key: str = "text") -> str:
    """A draft: capped in characters, lines and per-line width BEFORE any analysis runs."""
    v = _req_str(d, key, MAX_TEXT_CHARS)
    lines = v.splitlines()
    if len(lines) > MAX_TEXT_LINES:
        raise ApiError(413, f"'{key}' has too many lines ({len(lines)}, max {MAX_TEXT_LINES})")
    longest = max(map(len, lines))
    if longest > MAX_LINE_CHARS:
        raise ApiError(413, f"'{key}' has a line of {longest} chars (max {MAX_LINE_CHARS} per line)")
    return v


def _draft_id(v):
    """The opaque UI draft identity: a string or null (never coerced from a number/list)."""
    if v is not None and not isinstance(v, str):
        raise ApiError(400, "'draft_id' must be a string or null")
    return v


def _tags(v):
    """None, or a list of up to MAX_TAGS strings of up to MAX_TAG_CHARS each."""
    if v is None:
        return None
    if not isinstance(v, list):
        raise ApiError(400, "'tags' must be a list of strings")
    if len(v) > MAX_TAGS:
        raise ApiError(400, f"too many tags ({len(v)}, max {MAX_TAGS})")
    for i, t in enumerate(v):
        if not isinstance(t, str):
            raise ApiError(400, f"tags[{i}] must be a string")
        _capped(t, f"tags[{i}]", MAX_TAG_CHARS)
    return v


def _int(v, key: str, lo: int, hi: int, required: bool = False):
    if v is None:
        if required:
            raise ApiError(400, f"'{key}' is required (integer {lo}-{hi})")
        return None
    if isinstance(v, bool) or not isinstance(v, int):
        raise ApiError(400, f"'{key}' must be an integer")
    if not lo <= v <= hi:
        raise ApiError(400, f"'{key}' must be between {lo} and {hi}")
    return v


def _lane(v) -> str:
    v = "all" if v in (None, "") else v
    if v not in LANES:
        raise ApiError(400, f"Unknown lane '{v}' (use {', '.join(LANES)}).")
    return v


def _section(v) -> str:
    v = "strofa" if v in (None, "") else v
    if v not in targets.SECTION_TYPES:
        raise ApiError(400, f"Unknown section '{v}' (use {', '.join(targets.SECTION_TYPES)}).")
    return v


def _mode(v) -> str:
    v = "rhyme" if v in (None, "") else v
    if v not in anchors_mod.MODES:
        raise ApiError(400, f"Unknown mode '{v}' (use {', '.join(anchors_mod.MODES)}).")
    return v


def _dialect(v) -> str:
    v = "all" if v in (None, "") else v
    if v not in DIALECTS:
        raise ApiError(400, f"Unknown dialect '{v}' (use {', '.join(DIALECTS)}).")
    return v


def _written(v):
    """The editor's lyric lines (anchor seeding): a list of up to 64 strings,
    each capped like a lyric line; null when the user asks for fresh anchors."""
    if v is None:
        return None
    if not isinstance(v, list) or not all(isinstance(t, str) for t in v):
        raise ApiError(400, "'written' must be a list of strings (the editor lines)")
    if len(v) > 64:
        raise ApiError(413, f"'written' has too many lines ({len(v)}, max 64)")
    return [_capped(t, "written", MAX_LINE_CHARS) for t in v]


def _exclude(v) -> frozenset:
    """Words a swap must not return: a list of up to MAX_EXCLUDE strings."""
    if v is None:
        return frozenset()
    if not isinstance(v, list) or len(v) > MAX_EXCLUDE:
        raise ApiError(400, f"'exclude' must be a list of up to {MAX_EXCLUDE} words")
    out = set()
    for i, w in enumerate(v):
        if not isinstance(w, str):
            raise ApiError(400, f"exclude[{i}] must be a string")
        if nw := _capped(w.strip().lower(), f"exclude[{i}]", MAX_WORD_CHARS):
            out.add(nw)
    return frozenset(out)


def _blocked(con, dialect: str) -> frozenset:
    """User bans plus (dialect=ekavica) every ijekavian corpus form."""
    out = bans.list_bans(con)
    if dialect == "ekavica":
        out |= _state()["ijekavian"]
    return frozenset(out)


def _fresh(v) -> float:
    if v is None:
        return 0.5
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise ApiError(400, "'fresh' must be a number between 0.0 and 1.0")
    if not 0.0 <= v <= 1.0:
        raise ApiError(400, "'fresh' must be between 0.0 and 1.0")
    return float(v)


def _artists(v) -> tuple:
    """'devito,jala' or ['devito','jala'] -> ('devito', 'jala'); null/'' -> ().
    At most MAX_ARTISTS names of MAX_ARTIST_CHARS each (every distinct set caches a vocabulary)."""
    if v in (None, ""):
        return ()
    if isinstance(v, str):
        names = tuple(x.strip() for x in v.split(",") if x.strip())
    elif isinstance(v, list):
        names = tuple(str(x).strip() for x in v if str(x).strip())
    else:
        raise ApiError(400, "'artist' must be a comma-separated string, a list, or null")
    if len(names) > MAX_ARTISTS:
        raise ApiError(400, f"too many artists ({len(names)}, max {MAX_ARTISTS})")
    for name in names:
        _capped(name, "artist", MAX_ARTIST_CHARS)
    return names


def _scheme(v) -> str:
    v = "AABB" if v in (None, "") else v
    if not isinstance(v, str) or len(v) > 64 or not any(c.isalpha() for c in v):
        raise ApiError(400, "'scheme' must be letters (e.g. 'AABB')")
    return v


_EXPECTED_AT = re.compile(r"\s*Expected at:.*$", re.S)
_DRIVE_PATH = re.compile(r"[A-Za-z]:[\\/][^:\"'<>|?*()\r\n]*")
_UNC_PATH = re.compile(r"\\\\[^\s\"'<>|?*()]+")


def _scrub(msg: str, known_paths=()) -> str:
    """An engine message without absolute paths: the CLI prints 'Expected at: <path>';
    the API tells the browser what is wrong, never where on disk."""
    msg = _EXPECTED_AT.sub("", str(msg))
    for p in sorted({str(p) for p in known_paths if p}, key=len, reverse=True):
        msg = msg.replace(p, "<path>")
    msg = _UNC_PATH.sub("<path>", _DRIVE_PATH.sub("<path>", msg))
    return msg.strip() or "corpus index unavailable"


def _clean(msg: str) -> str:
    return _scrub(msg, _state()["paths"])


class _AtlasWarmup:
    """Builds (or loads from its cache) the corpus atlas once, in a background thread.

    A cold build is a ~20 s pass over lyrics.db, so no request may start one. Requests
    read ``poll()``: ``warming`` -> 503, ``ready`` -> the blob, ``failed`` -> degrade
    (a failed build is retried, single-flight, once ``retry_after`` seconds have passed),
    ``disabled`` -> the corpus is down and there is nothing to build.
    """

    def __init__(self, load, enabled: bool = True, retry_after: float = ATLAS_RETRY_SECS):
        self._load = load
        self.retry_after = retry_after
        self._lock = threading.Lock()
        self._done = threading.Event()
        self._blob = None
        self._error = None
        self._failed_at = 0.0
        self._running = False
        self._status = "warming" if enabled else "disabled"
        if not enabled:
            self._done.set()

    @property
    def status(self) -> str:
        return self._status

    def start(self) -> None:
        """Start the build unless one is running or finished (single-flight)."""
        with self._lock:
            if self._running or self._status in ("ready", "disabled"):
                return
            self._running, self._status = True, "warming"
            self._done.clear()
            threading.Thread(target=self._run, name="mairina-atlas-warmup", daemon=True).start()

    def _run(self) -> None:
        blob, error = None, None
        try:
            blob = self._load()
        except corpus.DbUnavailable as exc:
            error = str(exc)
        except Exception as exc:                                  # noqa: BLE001 - never kill the app
            logging.getLogger(__name__).exception("atlas warm-up failed")
            error = f"the corpus atlas could not be built ({type(exc).__name__})"
        with self._lock:
            self._running = False
            if blob is not None:
                self._status, self._blob, self._error = "ready", blob, None
            else:
                self._status, self._error, self._failed_at = "failed", error, time.monotonic()
            self._done.set()

    def poll(self):
        """(status, blob, error) now; kicks off a retry of an old failure."""
        with self._lock:
            retry = (self._status == "failed"
                     and time.monotonic() - self._failed_at >= self.retry_after)
        if retry:
            self.start()
        with self._lock:
            return self._status, self._blob, self._error

    def wait(self, timeout: float | None = None) -> bool:
        """Block until the current build finished (tests / `serve` smoke checks)."""
        return self._done.wait(timeout)


def _atlas_blob():
    """(status, blob, error) of the startup atlas; callers decide how to degrade."""
    return _state()["atlas"].poll()


def _priors(blob, lane: str):
    """Atlas priors for the fingerprint, or None when the atlas is unavailable
    (same degradation as the CLI: plain means instead of shrunk)."""
    return atlas_mod.lane_numeric(blob, lane) if blob is not None else None


def _trange(t):
    """targets.Target -> {lo, median, hi, approx} or null."""
    if t is None:
        return None
    return {"lo": t[0], "median": t[1], "hi": t[2], "approx": bool(getattr(t, "approx", False))}


def _star_json(r: dict) -> dict:
    """The contract Star object (internal file/feats fields stay server-side)."""
    return {"id": r["id"], "ts": r["ts"], "line_no": r["line_no"],
            "text": r["text"], "lane": r["lane"], "tags": r["tags"]}


# --- app factory ------------------------------------------------------------

def create_app(lyrics_db=None, data_dir=None) -> Flask:
    """Build the app. The corpus index is loaded once here; a missing, unannotated or
    unreadable lyrics.db is remembered, and corpus routes answer 503. The device atlas
    (a ~20 s corpus pass on a cold cache) is built once in a background thread started
    here: /api/me and /api/atlas answer 503 until it is ready, /api/xray just leaves its
    vs-star column null. Both are startup snapshots (restart after lyrics.db changes)."""
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 512 * 1024
    app.config["TRUSTED_HOSTS"] = list(TRUSTED_HOSTS)      # DNS rebinding: any other Host is refused
    app.json.ensure_ascii = False

    db_path = Path(lyrics_db or DEFAULT_LYRICS_DB)
    ddir = Path(data_dir or DATA_DIR)
    paths = (db_path, os.path.abspath(db_path), ddir, os.path.abspath(ddir))
    try:
        index = corpus.load_index(db_path, ddir)
        gazetteer = devices.load_gazetteer(str(db_path))
        corpus_error = None
    except corpus.DbUnavailable as exc:
        index, gazetteer, corpus_error = None, frozenset(), _scrub(exc, paths)
    except (sqlite3.Error, OSError) as exc:                  # unreadable / corrupt lyrics.db or cache
        app.logger.warning("corpus unavailable at startup: %r", exc)
        index, gazetteer = None, frozenset()
        corpus_error = f"lyrics.db could not be read ({type(exc).__name__}: {_scrub(exc, paths)})"
    warm = _AtlasWarmup(lambda: atlas_mod.load(db_path, ddir, notify=False),
                        enabled=index is not None)
    app.extensions["mairina"] = {"lyrics_db": db_path, "data_dir": ddir, "index": index,
                                 "gazetteer": gazetteer, "corpus_error": corpus_error,
                                 "paths": paths, "atlas": warm,
                                 "ijekavian": (frozenset(dialect_mod.ijekavian(index.forms))
                                             if index is not None else frozenset())}
    if index is not None:
        warm.start()                                          # never inside a request

    # -- request guards: JSON everywhere, never an HTML page --------------------
    @app.before_request
    def _refuse_cross_site():
        # Browsers label the request; a page on another site must not drive this API
        # (this also keeps GET /api/compare, which logs a list, from being a CSRF write).
        if request.headers.get("Sec-Fetch-Site", "").strip().lower() == "cross-site":
            raise ApiError(403, "cross-site requests are not allowed")

    @app.errorhandler(SecurityError)
    def _untrusted_host(_exc: SecurityError):
        return jsonify(error="Host header not allowed: this API serves 127.0.0.1 and localhost only"), 403

    @app.errorhandler(ApiError)
    def _api_error(exc: ApiError):
        return jsonify(error=str(exc)), exc.status

    @app.errorhandler(votes.VoteError)
    def _vote_error(exc: votes.VoteError):
        return jsonify(error=str(exc)), 400

    @app.errorhandler(corpus.DbUnavailable)
    def _corpus_error(exc: corpus.DbUnavailable):
        return jsonify(error=_clean(str(exc))), 503

    @app.errorhandler(HTTPException)
    def _http_error(exc: HTTPException):
        if 300 <= (exc.code or 500) < 400:
            return exc                       # redirects keep their Location header
        return jsonify(error=exc.description or exc.name), exc.code or 500

    @app.errorhandler(Exception)
    def _internal_error(exc: Exception):
        app.logger.exception("unhandled API error")
        return jsonify(error="internal server error"), 500

    # -- list endpoints -------------------------------------------------------

    @app.post("/api/anchors")
    def api_anchors():
        d = _body()
        lane, mode, section = _lane(d.get("lane")), _mode(d.get("mode")), _section(d.get("section"))
        fresh, artists = _fresh(d.get("fresh")), _artists(d.get("artist"))
        scheme, lines, seed = _scheme(d.get("scheme")), _int(d.get("lines"), "lines", 1, 64), _opt_str(d.get("seed"), "seed", MAX_WORD_CHARS)
        dialect, written = _dialect(d.get("dialect")), _written(d.get("written"))
        index = _index()
        st = _state()
        # Written lines keep their own end-word (locked) and seed their group's
        # class: the first non-empty line of each group fixes its rhyme family.
        n_lines = len(written) if written else lines
        letters = anchors_mod.parse_scheme(scheme, n_lines)
        group_seeds, locked = {}, {}
        for i, txt in enumerate(written or [], 1):
            toks = used_mod.tokenize(txt)
            if not toks or i > len(letters):
                continue
            locked[i] = toks[-1]
            group_seeds.setdefault(letters[i - 1], toks[-1])
        warns: list = []
        con = _create_app_db(st["data_dir"])
        try:
            blocked = _blocked(con, dialect)
            arm = votes.assign_arm(random.Random())
            boosts = votes.boosts(con) if arm == "learned" else None
            try:
                res = anchors_mod.anchors(index, scheme, n_lines, lane, mode, seed, fresh,
                                          artists, random.Random(), boosts, blocked=blocked,
                                          exclude=frozenset(locked.values()),
                                          group_seeds=group_seeds, warnings=warns,
                                          locked_lines=frozenset(locked))
            except anchors_mod.NoAnchors:
                res = []
            packed = [(a.word, a.score, {"kind": f"anchor-{a.mode}", "group": a.group,
                                         "key": a.key, "features": a.features,
                                         "meta": {"freq": a.freq, "upos": a.upos, "lemma": a.lemma}})
                      for a in res]
            lid = votes.log_shown(con, "anchor", f"{scheme}/{mode}/{seed or ''}", arm, packed)
        finally:
            con.close()
        trange = targets.target(lane, section, st["lyrics_db"], cache_dir=st["data_dir"])
        items = [{"n": a.line, "group": a.group, "word": a.word, "upos": a.upos,
                  "cls": a.key, "freq": a.freq,
                  "why": rank.explain(rank.Scored(a.word, a.score, a.features,
                                                 f"anchor-{a.mode}",
                                                 {"freq": a.freq, "upos": a.upos, "lemma": a.lemma}))}
                 for a in res]
        for n, w in locked.items():
            e = index.forms.get(w) or {}
            items.append({"n": n, "group": letters[n - 1], "word": w,
                          "upos": e.get("upos"), "cls": anchors_mod.class_key(w, mode),
                          "freq": e.get("freq", 0), "why": "your word", "locked": True})
        items.sort(key=lambda x: x["n"])
        out = {"list_id": lid, "arm": arm, "target": _trange(trange), "items": items}
        if warns:
            out["warnings"] = warns
        return jsonify(**out)

    @app.post("/api/anchors/swap")
    def api_anchor_swap():
        d = _body()
        cls = _req_str(d, "cls", MAX_WORD_CHARS)
        mode, lane, fresh = _mode(d.get("mode")), _lane(d.get("lane")), _fresh(d.get("fresh"))
        artists, dialect = _artists(d.get("artist")), _dialect(d.get("dialect"))
        group = _opt_str(d.get("group"), "group", 8)
        index = _index()
        con = _create_app_db(_state()["data_dir"])
        try:
            blocked = _blocked(con, dialect)
            arm = votes.assign_arm(random.Random())
            boosts = votes.boosts(con) if arm == "learned" else None
            a = anchors_mod.swap(index, cls, mode, lane, fresh, artists,
                                 _exclude(d.get("exclude")), random.Random(), boosts, blocked)
            lid = None
            if a is not None:
                lid = votes.log_shown(con, "anchor-swap", cls, arm,
                                      [(a.word, a.score, {"kind": f"anchor-{a.mode}",
                                                          "group": group or "", "key": a.key,
                                                          "features": a.features,
                                                          "meta": {"freq": a.freq, "upos": a.upos,
                                                                   "lemma": a.lemma}})])
        finally:
            con.close()
        item = None
        if a is not None:
            item = {"word": a.word, "upos": a.upos, "cls": a.key, "freq": a.freq,
                    "group": group, "why": rank.explain(rank.Scored(a.word, a.score, a.features,
                                                                    f"anchor-{a.mode}",
                                                                    {"freq": a.freq, "upos": a.upos,
                                                                     "lemma": a.lemma}))}
        return jsonify(item=item, list_id=lid)

    @app.post("/api/rhyme")
    def api_rhyme():
        d = _body()
        word = _req_str(d, "word", MAX_WORD_CHARS)
        line = _opt_str(d.get("line"), "line", MAX_LINE_CHARS)
        target_syl = _int(d.get("target"), "target", 1, 99)
        if target_syl is not None and not line:
            raise ApiError(400, "'target' needs 'line' (the target is for the line being written).")
        lane, fresh, artists = _lane(d.get("lane")), _fresh(d.get("fresh")), _artists(d.get("artist"))
        dialect = _dialect(d.get("dialect"))
        index = _index()
        con = _create_app_db(_state()["data_dir"])
        try:
            blocked = _blocked(con, dialect)
            arm = votes.assign_arm(random.Random())
            boosts = votes.boosts(con) if arm == "learned" else None
            ctx = rank.Ctx(index, lane, fresh, artists, boosts, line, target_syl, blocked)
            res = rank.rank(word, ctx.vocab(), ctx)[:MAX_RESULTS]
            lid = votes.log_shown(con, "rhyme", word, arm, [_pack(s) for s in res])
        finally:
            con.close()
        items = [{"n": i, "word": s.candidate, "score": s.score,
                  "kind": s.kind, "why": rank.explain(s)} for i, s in enumerate(res, 1)]
        return jsonify(list_id=lid, arm=arm, query=word, items=items)

    @app.post("/api/multi")
    def api_multi():
        d = _body()
        phrase = _req_str(d, "phrase", MAX_WORD_CHARS)
        lane = _lane(d.get("lane"))
        dialect = _dialect(d.get("dialect"))
        index = _index()
        con = _create_app_db(_state()["data_dir"])
        try:
            blocked = _blocked(con, dialect)
            arm = votes.assign_arm(random.Random())
            boosts = votes.boosts(con) if arm == "learned" else None
            res = multis_mod.multis(index, phrase, lane, MAX_RESULTS, 0.5, (), boosts, blocked)
            lid = votes.log_shown(con, "multi", phrase, arm, [_pack(s) for s in res])
        finally:
            con.close()
        items = [{"n": i, "phrase": s.candidate, "score": s.score,
                  "why": rank.explain(s)} for i, s in enumerate(res, 1)]
        return jsonify(list_id=lid, arm=arm, query=phrase, items=items)

    # -- xray ------------------------------------------------------------------

    @app.post("/api/xray")
    def api_xray():
        d = _body()
        text = _req_text(d)
        lane, section = _lane(d.get("lane")), _section(d.get("section"))
        index = _index()
        st = _state()
        lines = fingerprint.lyric_lines_from_text(text)
        if not lines:
            return jsonify(lines=[])
        trange = _trange(targets.target(lane, section, st["lyrics_db"], cache_dir=st["data_dir"]))
        cons_thr = targets.cons_thresholds(lane, st["lyrics_db"], st["data_dir"])
        rep = devices.analyze_verse(lines, st["gazetteer"], index)

        app_db = _open_app_db(st["data_dir"])
        try:
            muted = hints.muted(app_db) if app_db else []
            star_rows = fingerprint.stars(app_db, lane) if app_db else []
        finally:
            if app_db:
                app_db.close()
        fp = None
        atlas_status, atlas_blob, _err = _atlas_blob()
        if atlas_status != "warming" and len(star_rows) >= fingerprint.MIN_STARS_FOR_XRAY:
            fp = fingerprint.fingerprint(None, lane, _priors(atlas_blob, lane), rows=star_rows)

        line_hints: dict[int, list] = {}
        for h in rules.verse_hints(lines, index=index):
            if h["rule_id"] in muted:
                continue
            line_hints.setdefault(h["line"], []).append(
                {"rule_id": h["rule_id"], "label": rules.SHORT_LABELS.get(h["rule_id"], h["rule_id"])})

        out = []
        for lr in rep.lines:
            kinds = devices.device_kinds(lr.devices)
            out.append({
                "n": lr.n, "text": lr.text, "syl": lr.syllables, "target": trange,
                "rhyme": lr.rhyme_letter or "-",
                "cons": devices.gauge_level(lr.cons_density, cons_thr),
                "cons_density": lr.cons_density,
                "allit": "alliteration" in kinds,
                "assonance": next((t["span"] for t in lr.devices
                                   if t["kind"] == "internal_rhyme"), None),
                "devices": [{"kind": t["kind"], "span": t["span"], "confidence": t["confidence"]}
                            for t in lr.devices],
                "hints": line_hints.get(lr.n, []),
                "vs_star": fingerprint.vs_star_phrase(lr.text, fp) if fp else None,
            })
        return jsonify(lines=out)

    # -- learning write endpoints ------------------------------------------------

    @app.post("/api/vote")
    def api_vote():
        d = _body()
        lid = _int(d.get("list_id"), "list_id", 1, 2**31 - 1, required=True)
        items = d.get("items")
        if not isinstance(items, list) or len(items) > MAX_VOTE_ITEMS:
            raise ApiError(400, f"'items' must be a list of up to {MAX_VOTE_ITEMS} [n, +1|-1] pairs")
        pairs, seen = [], set()
        for i, it in enumerate(items):
            if not isinstance(it, (list, tuple)) or len(it) != 2:
                raise ApiError(400, f"items[{i}] must be [item_number, +1|-1]")
            n, v = it
            if isinstance(n, bool) or not isinstance(n, int) or n < 1:
                raise ApiError(400, f"items[{i}][0] must be a positive item number")
            if isinstance(v, bool) or v not in (1, -1):
                raise ApiError(400, f"items[{i}][1] must be +1 or -1")
            if n in seen:
                raise ApiError(400, f"items[{i}]: item {n} is listed twice (one vote per item)")
            seen.add(n)
            pairs.append((n, v))
        con = votes.connect(_state()["data_dir"] / "mairina.db")
        try:
            if votes.list_rows(con, lid) is None:
                raise ApiError(404, f"Unknown list_id {lid}: no such shown list "
                                    "(nothing was voted).")
            votes.cast_votes(con, pairs, lid)
        finally:
            con.close()
        return jsonify(ok=True)

    @app.post("/api/star")
    def api_star():
        d = _body()
        text = _req_text(d)
        line_no = _int(d.get("line_no"), "line_no", 1, 10_000, required=True)
        lane = _lane(d.get("lane"))
        tags = _tags(d.get("tags"))
        draft_id = _draft_id(d.get("draft_id"))
        if draft_id is not None:
            fingerprint.draft_key(draft_id, text)        # validates; never a path
        st = _state()
        con = _create_app_db(st["data_dir"])
        try:
            rec = fingerprint.star_text(con, text, line_no, lane, tags, draft_id,
                                        context=(st["gazetteer"], st["index"]))
        finally:
            con.close()
        return jsonify(**_star_json(rec))

    @app.delete("/api/star/<int:sid>")
    def api_unstar(sid: int):
        if sid > SQLITE_MAX_INT:
            raise ApiError(404, "No such star.")
        con = _open_app_db(_state()["data_dir"], write=True)
        try:
            removed = bool(con) and fingerprint.unstar(con, sid)
        finally:
            if con:
                con.close()
        if not removed:
            raise ApiError(404, f"No star #{sid}.")
        return jsonify(ok=True)

    @app.get("/api/stars")
    def api_stars():
        lane = _lane(request.args.get("lane"))
        con = _open_app_db(_state()["data_dir"])
        try:
            rows = fingerprint.stars(con, None if lane == "all" else lane) if con else []
        finally:
            if con:
                con.close()
        return jsonify(items=[_star_json(r) for r in rows])

    @app.post("/api/hint-vote")
    def api_hint_vote():
        d = _body()
        rid = _req_str(d, "rule_id")
        v = d.get("vote")
        if isinstance(v, bool) or not isinstance(v, int) or v not in (-1, 0, 1):
            raise ApiError(400, "'vote' must be +1, -1 or 0 (reset)")
        con = _create_app_db(_state()["data_dir"])
        try:
            if v == 0:
                hints.reset(con, rid)
            else:
                hints.vote(con, rid, v)
            up, down = hints.counts(con).get(rid, (0, 0))
            muted = rid in hints.muted(con)
        finally:
            con.close()
        return jsonify(rule_id=rid, up=up, down=down, muted=muted)

    @app.post("/api/used")
    def api_used():
        d = _body()
        text = _req_text(d)
        source = fingerprint.draft_key(_draft_id(d.get("draft_id")), text)
        con = _create_app_db(_state()["data_dir"])
        try:
            hits = used_mod.scan_text(text, USED_DAYS, con)
            for h in hits:
                votes.mark_used(con, h, source)
        finally:
            con.close()
        return jsonify(count=len(hits), hits=hits)

    # -- read-only stats/reference endpoints ---------------------------------------

    @app.get("/api/me")
    def api_me():
        lane = _lane(request.args.get("lane"))
        st = _state()
        atlas_status, atlas_blob, _err = _atlas_blob()
        if atlas_status == "warming":
            raise ApiError(503, ATLAS_WARMING)
        con = _open_app_db(st["data_dir"])
        try:
            rows = fingerprint.stars(con, lane) if con else []
        finally:
            if con:
                con.close()
        priors = _priors(atlas_blob, lane) if rows else None
        fp = fingerprint.fingerprint(None, lane, priors, rows=rows)
        numeric = {f: {"mean": v["mean"], "shrunk": v["shrunk"],
                       "lane_mu": v["mu"], "lane_sigma": v["sigma"]}
                   for f, v in fp["numeric"].items()}
        return jsonify(n=fp["n"], low_confidence=fp["low_confidence"], numeric=numeric,
                       tag_rates=fp["tag_rates"], kind_rates=fp["kind_rates"])

    @app.get("/api/atlas")
    def api_atlas():
        lane = _lane(request.args.get("lane"))
        artists = {a.lower() for a in _artists(request.args.get("artist"))}
        _index()
        atlas_status, blob, atlas_err = _atlas_blob()
        if atlas_status == "warming":
            raise ApiError(503, ATLAS_WARMING)
        if blob is None:
            raise ApiError(503, _clean(atlas_err or "corpus atlas unavailable"))

        def row(scope: str, s: dict) -> dict:
            n = s["n_lines"] or 0
            rate = lambda k: (100.0 * s["counts"][k] / n) if n else 0.0   # noqa: E731
            return {"scope": scope, "lines": n, "simile": rate("simile"),
                    "anaphora": rate("anaphora"), "allit": rate("allit"),
                    "internal": rate("internal"), "code_switch": rate("code_switch"),
                    "name_drop": rate("name_drop"), "multi_pct": rate("multi"),
                    "cons": s["cons_mean"], "med_syl": s["median_syl"]}

        lanes = [row(f"lane {ln}", s) for ln, s in (blob.get("lanes") or {}).items()
                 if lane == "all" or ln == lane]
        arts = [row(slug, s) for slug, s in (blob.get("artists") or {}).items()
                if not artists or slug.lower() in artists]
        return jsonify(lanes=lanes, artists=arts)

    @app.get("/api/compare")
    def api_compare():
        lane = _lane(request.args.get("lane"))
        artists = _artists(request.args.get("artist"))
        theme_raw = _opt_str(request.args.get("theme"), "theme", MAX_WORD_CHARS)
        theme = None
        if theme_raw:
            words = used_mod.tokenize(theme_raw)
            if len(words) != 1:
                raise ApiError(400, "'theme' takes exactly one word.")
            theme = words[0]
        index = _index()
        st = _state()
        dialect = _dialect(request.args.get("dialect"))
        con = _create_app_db(st["data_dir"])
        try:
            blocked = _blocked(con, dialect)
            counts = comparisons.collect(st["lyrics_db"], lane, artists, theme, index, blocked)
            arm = votes.assign_arm(random.Random())
            boosts = votes.boosts(con) if arm == "learned" else None
            res = comparisons.rank_words(counts, index, lane, artists, 0.5, boosts, blocked)[:MAX_RESULTS]
            lid = votes.log_shown(con, "compare", f"lane={lane},theme={theme or ''}", arm,
                                  [_pack(s) for s in res])
        finally:
            con.close()
        items = [{"n": i, "word": s.candidate, "count": s.meta["count"],
                  "score": s.score, "why": rank.explain(s)} for i, s in enumerate(res, 1)]
        return jsonify(list_id=lid, arm=arm, items=items)

    # -- word bans ---------------------------------------------------------------

    @app.post("/api/ban")
    def api_ban():
        word = _req_str(_body(), "word", bans.MAX_WORD_LEN)
        con = _create_app_db(_state()["data_dir"])
        try:
            w = bans.ban(con, word)
        finally:
            con.close()
        return jsonify(ok=True, word=w)

    @app.delete("/api/ban/<word>")
    def api_unban(word: str):
        w = _capped(word.strip().lower(), "word", bans.MAX_WORD_LEN)
        con = _create_app_db(_state()["data_dir"])
        try:
            removed = bans.unban(con, w)
        finally:
            con.close()
        if not removed:
            raise ApiError(404, f"'{w}' is not banned.")
        return jsonify(ok=True, word=w)

    @app.get("/api/bans")
    def api_bans():
        con = _open_app_db(_state()["data_dir"])
        try:
            items = bans.list_with_ts(con) if con else []
        finally:
            if con:
                con.close()
        return jsonify(items=items)

    @app.get("/api/stats")
    def api_stats():
        con = _create_app_db(_state()["data_dir"])
        try:
            st = votes.stats(con)
            muted = hints.muted(con)
        finally:
            con.close()
        lists = sum(v["lists"] for v in st["by_kind"].values())
        arms = {arm: {"votes": a["votes"], "up_rate": a["rate"]}
                for arm, a in st["arms"].items()}
        if not st["ab_ready"]:
            ab = f"not enough data ({st['votes']}/{votes.AB_MIN_VOTES})"
        else:
            l, b = st["arms"]["learned"]["rate"], st["arms"]["base"]["rate"]
            ab = ("learned beats base" if l is not None and b is not None and l > b
                  else "learned does not beat base (yet)")
        return jsonify(votes=st["votes"], up=st["up"], down=st["down"],
                       up_rate=st["rate"], used=st["used_candidates"], lists=lists,
                       arms=arms, ab=ab, muted=muted)

    return app


# --- serving ------------------------------------------------------------------

def serve(app: Flask, host: str = HOST, port: int = PORT) -> None:
    """Run the dev server. Refuses anything but 127.0.0.1:8000 before binding —
    MAirina is a single-user local API and must never be exposed. The Werkzeug debugger
    (a remote-code console) stays off even when FLASK_DEBUG=1 is in the environment, and
    no .env / .flaskenv file is loaded."""
    if host != HOST or port != PORT:
        raise ValueError(f"MAirina serves only {HOST}:{PORT} (got {host}:{port}) — "
                         "it is a local single-user API, never expose it.")
    app.run(host=HOST, port=PORT, debug=False, use_debugger=False, use_reloader=False,
            load_dotenv=False, threaded=True)


def run(lyrics_db=None, data_dir=None) -> int:
    """`mt serve`: build the app and serve it on 127.0.0.1:8000."""
    serve(create_app(lyrics_db, data_dir))
    return 0


if __name__ == "__main__":
    run()
