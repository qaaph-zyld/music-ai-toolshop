"""Audition review — commented listening pages for ear-test gates.

Subcommands:

    serve   localhost static server over a pack root. Every served .html page
            gets a verdict+comment widget injected beside each <audio> element
            AT SERVE TIME (files on disk are never touched — release-manifest
            hashes and agent-curated pages stay intact). Comments POSTed by
            the widget append to <root>/_audition_comments/<page-slug>.jsonl.
            Also serves GET /__audition__/songs — every pack under the root
            that has an audition.json (the root itself is never a pack).
    page    generate an index.html listing every audio file in a pack dir.
            With a pack-local audition.json the page gets the grouped listen
            state page (legend, TODO box, colour-coded rows ordered by group,
            live repaint on audition:saved / >50% played). Without one the
            output is the legacy flat table — and an existing index.html is
            never overwritten without --force (curated pages stay curated).
    round   open a new listen round: prepend a listen-state group for
            --prefix, flip previous listen groups to heard, rewrite
            audition.json, regenerate the page. Refuses a prefix that
            already matches files claimed by an earlier round's group.
    check   GET the page (expect 200) plus a Range probe (expect 206) for
            every <audio> in a listen group — catches a wedged server that
            still answers comments but returns nothing for files.
    comments read back a pack's comment log as a table.

Typical use (ear-test gate):
    python scripts/audition_review.py serve --root <stems> --port 8778
    # open http://127.0.0.1:8778/<pack>/ — same paths as the :8777 static
    # server, plus comment widgets on every player.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from html import escape
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

REPO = Path(__file__).resolve().parent.parent
DEFAULT_ROOT = REPO / "Stemmeca_alatkka" / "stems"
COMMENTS_DIR = "_audition_comments"
VERDICTS = ("pick", "ok", "flag", "reject")
MAX_BODY = 65536
MEDIA_EXTS = (".wav", ".mp3", ".flac", ".ogg")
SCRIPT_TAG = '<script src="/__audition__/comments.js"></script>'

WIDGET_JS = r"""// audition_review widget — verdict + comment per <audio>, logged server-side.
(function () {
  "use strict";
  var VERDICTS = ["", "pick", "ok", "flag", "reject"];
  var page = window.location.pathname;
  function key(audio) { return audio.getAttribute("src") || ""; }
  function mk(tag, cls) { var e = document.createElement(tag); if (cls) e.className = cls; return e; }
  function attach(audio) {
    var box = mk("div", "audrev");
    box.style.cssText = "margin:.3em 0 .9em;display:flex;gap:.5em;align-items:flex-start;font-size:13px";
    var sel = mk("select");
    VERDICTS.forEach(function (v) {
      var o = mk("option"); o.value = v; o.textContent = v || "—"; sel.appendChild(o);
    });
    var ta = mk("textarea");
    ta.rows = 2; ta.placeholder = "comment…";
    ta.style.cssText = "flex:1;min-width:200px;background:#1c1c22;color:#eee;border:1px solid #444;padding:4px";
    var btn = mk("button"); btn.textContent = "save";
    var st = mk("span"); st.style.cssText = "color:#8c8;white-space:nowrap";
    var it = { k: key(audio), sel: sel, ta: ta, sent: "" };
    function fail() { st.textContent = "save FAILED"; st.style.color = "#c66"; }
    function save() {
      it.sent = ta.value;
      fetch("/__audition__/comment", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ page: page, audio: it.k, verdict: sel.value, comment: ta.value })
      }).then(function (r) {
        if (!r.ok) return fail();
        st.textContent = "saved " + new Date().toTimeString().slice(0, 8);
        st.style.color = "#8c8";
        document.dispatchEvent(new CustomEvent("audition:saved",
          { detail: { audio: it.k, verdict: sel.value } }));
      }).catch(fail);
    }
    // picking a verdict IS the decision — persist it now, not on "save"
    sel.addEventListener("change", save);
    // comment persists when focus leaves the box (the button saves if clicked)
    ta.addEventListener("blur", function (e) {
      if (e.relatedTarget !== btn && ta.value !== it.sent) save();
    });
    btn.onclick = save;
    box.appendChild(sel); box.appendChild(ta); box.appendChild(btn); box.appendChild(st);
    audio.parentNode.insertBefore(box, audio.nextSibling);
    return it;
  }
  window.addEventListener("DOMContentLoaded", function () {
    var items = Array.prototype.map.call(document.querySelectorAll("audio"), attach);
    if (!items.length) return;
    fetch("/__audition__/comments?page=" + encodeURIComponent(page))
      .then(function (r) { return r.ok ? r.json() : {}; })
      .then(function (m) {
        items.forEach(function (it) {
          var c = m[it.k];
          if (c) { it.sel.value = c.verdict || ""; it.ta.value = it.sent = c.comment || ""; }
        });
      }).catch(function () {});
  });
})();
"""


# ---- per-pack config (audition.json) ------------------------------------ #
# {"title","artist","song","todo","groups":[{"prefix","state","label"}]}
# state: listen | heard | rej | ref — colours/labels exactly as the interim
# .scratch/mojgrad_sync/build_page.py produced for Moj Grad.

CONFIG_NAME = "audition.json"
CATCH_ALL = {"prefix": "", "state": "ref", "label": "source / reference"}

PAGE_STYLE = """
tr.g-listen td { background: #10301a } tr.g-listen td:first-child { border-left: 8px solid #3ccf5a }
tr.g-heard td { background: #2e2a0e } tr.g-heard td:first-child { border-left: 8px solid #e6c229 }
tr.g-rej td { background: #33121290 } tr.g-rej td:first-child { border-left: 8px solid #e04848 } tr.g-rej { opacity: .55 }
tr.g-ref td { background: #18181d } tr.g-ref td:first-child { border-left: 8px solid #555 }
td:first-child::before { content: attr(data-tag); display: block; font-size: 11px; font-weight: 700; letter-spacing: .05em; margin-bottom: .2em }
tr.g-listen td:first-child::before { color: #3ccf5a } tr.g-heard td:first-child::before { color: #e6c229 }
tr.g-rej td:first-child::before { color: #e04848 } tr.g-ref td:first-child::before { color: #888 }
.legend span { display: inline-block; padding: .25em .7em; margin: 0 .5em .4em 0; border-radius: 3px; font-weight: 600 }
.todo { border: 2px solid #3ccf5a; padding: .6em 1em; border-radius: 4px; background: #10301a; max-width: 60em }
"""

PAGE_LEGEND = (
    '<div class="legend"><span style="background:#3ccf5a;color:#000">green = LISTEN NOW</span>'
    '<span style="background:#e6c229;color:#000">yellow = listened / done</span>'
    '<span style="background:#e04848;color:#000">red = rejected</span>'
    '<span style="background:#555">grey = source / reference</span></div>')

# Live-state repaint: a saved "reject" -> red "rejected by you"; any saved
# verdict/comment or >50% played (localStorage "played:<path><src>") -> yellow
# "listened - <verdict>"; rej groups stay red. Repaints on the widget's
# "audition:saved" event (autosave — no save click any more).
PAGE_SCRIPT = """<script>
(function () {
  var GROUPS = __GROUPS__, saved = {};
  function grp(src) { for (var i = 0; i < GROUPS.length; i++) if (src.indexOf(GROUPS[i][0]) === 0) return GROUPS[i]; return ["", "ref", "source / reference"]; }
  function key(src) { return "played:" + location.pathname + src; }
  function played(src) { try { return localStorage.getItem(key(src)) === "1"; } catch (e) { return false; } }
  function paint() {
    document.querySelectorAll("audio").forEach(function (a) {
      var src = a.getAttribute("src") || "", row = a.closest("tr"), g = grp(src), st = g[1], tag = g[2], c = saved[src];
      if (c && c.verdict === "reject") { st = "rej"; tag = "rejected by you"; }
      else if (st !== "rej" && ((c && (c.verdict || c.comment)) || played(src))) {
        st = "heard"; tag = (c && c.verdict) ? ("listened - " + c.verdict) : (st === "heard" ? tag : "listened");
      }
      row.className = "g-" + st; row.cells[0].setAttribute("data-tag", tag);
    });
  }
  function load() {
    fetch("/__audition__/comments?page=" + encodeURIComponent(location.pathname))
      .then(function (r) { return r.ok ? r.json() : {}; }).then(function (m) { saved = m || {}; paint(); }).catch(paint);
  }
  window.addEventListener("DOMContentLoaded", function () {
    paint(); load();
    document.querySelectorAll("audio").forEach(function (a) {
      a.addEventListener("timeupdate", function () {
        if (a.duration && a.currentTime / a.duration >= 0.5 && !played(a.getAttribute("src"))) {
          try { localStorage.setItem(key(a.getAttribute("src")), "1"); } catch (e) {}
          paint();
        }
      });
    });
    document.addEventListener("audition:saved", function () { load(); });
  });
})();
</script>"""


def _load_config(pack_dir: Path) -> dict | None:
    """Return the pack's audition.json, or None for a legacy flat pack."""
    p = pack_dir / CONFIG_NAME
    if not p.is_file():
        return None
    cfg = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(cfg.get("groups"), list):
        raise ValueError(f"{p}: 'groups' must be a list")
    return cfg


def _match_group(cfg: dict, src: str) -> dict:
    """First group whose prefix matches src wins; unmatched -> ref."""
    for g in cfg["groups"]:
        if src.startswith(g.get("prefix", "")):
            return g
    return CATCH_ALL


def _slug(relpath: str) -> str:
    """Map a URL path to a safe jsonl filename stem."""
    s = re.sub(r"[^A-Za-z0-9_-]+", "_", relpath.strip("/")).strip("_")
    return s or "index"


def _log_path(root: Path, page: str) -> Path:
    return root / COMMENTS_DIR / f"{_slug(page)}.jsonl"


def _read_log(root: Path, page: str) -> dict:
    """Latest entry per audio src for a page slug."""
    out = {}
    log = _log_path(root, page)
    if log.is_file():
        for line in log.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    continue
                out[e.get("audio", "")] = e
    return out


class AuditionHandler(SimpleHTTPRequestHandler):
    """Static files + comment endpoints + .html widget injection."""

    def log_message(self, fmt, *args):  # quieter logs; errors still shown
        if "/__audition__/" not in (str(args[0]) if args else ""):
            super().log_message(fmt, *args)

    # ---- helpers ------------------------------------------------------- #
    @property
    def _root(self) -> Path:
        return Path(self.directory)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")

    def _send_bytes(self, data: bytes, ctype: str, code: int = 200):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self._cors()
        self.end_headers()
        return io.BytesIO(data)

    # ---- GET ----------------------------------------------------------- #
    def send_head(self):  # noqa: C901 - small dispatch
        url = urlparse(self.path)
        route = url.path
        if route == "/__audition__/comments.js":
            return self._send_bytes(WIDGET_JS.encode("utf-8"),
                                  "application/javascript; charset=utf-8")
        if route == "/__audition__/comments":
            page = parse_qs(url.query).get("page", [""])[0]
            data = json.dumps(_read_log(self._root, page),
                              ensure_ascii=False).encode("utf-8")
            return self._send_bytes(data, "application/json; charset=utf-8")
        if route == "/__audition__/songs":
            data = json.dumps(_song_list(self._root),
                              ensure_ascii=False).encode("utf-8")
            return self._send_bytes(data, "application/json; charset=utf-8")
        fs_path = Path(self.translate_path(self.path))
        if fs_path.is_dir():
            if not route.endswith("/"):
                return super().send_head()  # let it 301-redirect first
            for name in ("index.html", "index.htm"):
                cand = fs_path / name
                if cand.is_file():
                    return self._serve_html_transformed(cand)
        elif fs_path.is_file():
            if fs_path.suffix.lower() == ".html":
                return self._serve_html_transformed(fs_path)
            return self._serve_file(fs_path)
        return super().send_head()

    # ---- Range-aware static files ------------------------------------- #
    # stdlib send_head ignores Range, which leaves <audio> with no seek bar.
    RANGE_RE = re.compile(r"bytes=(\d*)-(\d*)")

    def _serve_file(self, fs_path: Path):
        """Serve a static file, honoring a single 'Range: bytes=...' request."""
        try:
            size = fs_path.stat().st_size
        except OSError:
            return super().send_head()
        start, end = 0, size - 1
        code = 200
        rng = self.headers.get("Range")
        if rng:
            m = self.RANGE_RE.fullmatch(rng.strip())
            if not m or (not m.group(1) and not m.group(2)):
                return self.send_error(416, "invalid range")
            if m.group(1):
                start = int(m.group(1))
                end = int(m.group(2)) if m.group(2) else size - 1
            else:  # suffix range: last N bytes
                start = max(0, size - int(m.group(2)))
            if start >= size or start > end:
                return self.send_error(416, "unsatisfiable range")
            end = min(end, size - 1)
            code = 206
        with fs_path.open("rb") as fh:
            fh.seek(start)
            data = fh.read(end - start + 1)
        self.send_response(code)
        self.send_header("Content-Type", self.guess_type(str(fs_path)))
        self.send_header("Accept-Ranges", "bytes")
        if code == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(len(data)))
        self._cors()
        self.end_headers()
        return io.BytesIO(data)

    def _serve_html_transformed(self, fs_path: Path):
        try:
            text = fs_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return super().send_head()  # unreadable as utf-8 → serve raw
        if SCRIPT_TAG not in text:
            if "</body>" in text:
                text = text.replace("</body>", SCRIPT_TAG + "</body>", 1)
            else:
                text += SCRIPT_TAG
        return self._send_bytes(text.encode("utf-8"),
                                "text/html; charset=utf-8")

    # ---- POST/OPTIONS -------------------------------------------------- #
    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        if urlparse(self.path).path != "/__audition__/comment":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length <= 0 or length > MAX_BODY:
            self.send_error(400, "bad or missing Content-Length")
            return
        try:
            body = json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.send_error(400, "invalid JSON")
            return
        page = str(body.get("page", ""))
        audio = str(body.get("audio", ""))
        verdict = str(body.get("verdict", ""))
        comment = str(body.get("comment", ""))
        if not audio or (not verdict and not comment):
            self.send_error(400, "need audio plus a verdict or comment")
            return
        if verdict and verdict not in VERDICTS:
            self.send_error(400, f"verdict must be one of {VERDICTS}")
            return
        entry = {"ts_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                 "audio": audio, "verdict": verdict, "comment": comment}
        log = _log_path(self._root, page)
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self.send_response(204)
        self._cors()
        self.end_headers()


# ---- page generator ---------------------------------------------------- #

def _media_files(pack_dir: Path) -> list[Path]:
    return sorted(
        p for p in pack_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in MEDIA_EXTS
    )


def _ordered_rows(pack_dir: Path, cfg: dict) -> str:
    """<tr> rows: group order (config order), alphabetical inside a group."""
    files = _media_files(pack_dir)
    rows, claimed = [], set()
    for g in cfg["groups"]:
        for p in files:
            rel = p.relative_to(pack_dir).as_posix()
            if rel in claimed or not rel.startswith(g.get("prefix", "")):
                continue
            claimed.add(rel)
            rows.append((g, rel))
    for p in files:  # unmatched -> implicit ref group, alphabetical, last
        rel = p.relative_to(pack_dir).as_posix()
        if rel not in claimed:
            rows.append((CATCH_ALL, rel))
    return "".join(
        f'<tr class="g-{g["state"]}"><td data-tag="'
        f'{escape(g.get("label", ""), quote=True)}">{escape(rel)}</td>'
        f'<td><audio controls preload="none" '
        f'src="{escape(rel, quote=True)}"></audio></td></tr>\n'
        for g, rel in rows
    )


def _render_config_page(pack_dir: Path, cfg: dict, title: str) -> str:
    rows = _ordered_rows(pack_dir, cfg)
    groups_js = [[g.get("prefix", ""), g.get("state", "ref"),
                  g.get("label", "")] for g in cfg["groups"]]
    groups_js.append(["", "ref", CATCH_ALL["label"]])
    script = PAGE_SCRIPT.replace("__GROUPS__", json.dumps(groups_js))
    meta = " — ".join(x for x in (cfg.get("artist"), cfg.get("song")) if x)
    todo = cfg.get("todo", "")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{escape(title)}</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 2em; background: #101014; color: #e8e8ee; }}
a {{ color: #9ec1ff }} table {{ border-collapse: collapse; margin: 1em 0 }}
td, th {{ border: 1px solid #444; padding: .3em .7em }}
{PAGE_STYLE}</style></head><body>
<h1>{escape(title)}</h1>
{f'<p>{escape(meta)}</p>' if meta else ''}
{PAGE_LEGEND}
{f'<div class="todo">{todo}</div>' if todo else ''}
<table>
{rows}</table>
{script}
</body></html>
"""


def generate_index(pack_dir: Path, title: str | None = None,
                   note: str = "", force: bool = False) -> Path:
    """Write pack_dir/index.html.

    With an audition.json in the pack: grouped, colour-coded listen page
    (always regenerated — the pack declared itself tool-managed). Without
    one: the legacy flat table, and an existing index.html is never
    overwritten unless force=True (curated pages are not ours to rewrite).
    """
    out = pack_dir / "index.html"
    cfg = _load_config(pack_dir)
    if cfg is None and out.is_file() and not force:
        raise FileExistsError(
            f"{out} exists and the pack has no {CONFIG_NAME}; "
            "refusing to overwrite a possibly curated page (use --force)")
    if cfg is not None:
        title = cfg.get("title") or title or pack_dir.name
        html = _render_config_page(pack_dir, cfg, title)
    else:
        if title is None:
            raise ValueError(
                f"--title is required when {pack_dir} has no {CONFIG_NAME}")
        files = _media_files(pack_dir)
        rows = "".join(
            f'<tr><td>{p.relative_to(pack_dir).as_posix()}</td>'
            f'<td><audio controls preload="none" '
            f'src="{p.relative_to(pack_dir).as_posix()}"></audio></td></tr>\n'
            for p in files
        )
        html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{title}</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 2em; background: #101014; color: #e8e8ee; }}
a {{ color: #9ec1ff }} table {{ border-collapse: collapse; margin: 1em 0 }}
td, th {{ border: 1px solid #444; padding: .3em .7em }}
</style></head><body>
<h1>{title}</h1>
{f"<p>{note}</p>" if note else ""}
<table>
{rows}</table>
</body></html>
"""
    out.write_text(html, encoding="utf-8")
    return out


# ---- songs listing ------------------------------------------------------- #

def _song_list(root: Path) -> list[dict]:
    """Every dir under root holding an audition.json. '/' is never a pack."""
    out = []
    for cfg_path in sorted(root.rglob(CONFIG_NAME)):
        pack = cfg_path.parent
        if pack == root or COMMENTS_DIR in pack.parts:
            continue
        rel = pack.relative_to(root).as_posix()
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError, UnicodeDecodeError):
            cfg = {}
        listen = sum(
            1 for p in _media_files(pack)
            if _match_group(cfg, p.relative_to(pack).as_posix())["state"]
            == "listen"
        )
        log = _log_path(root, "/" + rel + "/")
        latest = None
        if log.is_file():
            for line in log.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    ts = json.loads(line).get("ts_utc")
                except json.JSONDecodeError:
                    continue
                if ts and (latest is None or ts > latest):
                    latest = ts
        out.append({"slug": _slug("/" + rel + "/"),
                    "title": cfg.get("title", rel),
                    "artist": cfg.get("artist", ""),
                    "song": cfg.get("song", ""),
                    "link": f"/{rel}/",
                    "listen_files": listen,
                    "latest_ts_utc": latest})
    return out


# ---- round / check ------------------------------------------------------- #

def round_pack(pack_dir: Path, prefix: str, label: str, todo: str) -> int:
    """Open a new listen round. Non-zero exit on any refusal."""
    cfg_path = pack_dir / CONFIG_NAME
    if not cfg_path.is_file():
        print(f"FAIL  {cfg_path} missing — create {CONFIG_NAME} first")
        return 2
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    groups = cfg["groups"]
    if any(g.get("prefix") == prefix for g in groups):
        print(f"FAIL  prefix {prefix!r} is already a group in {CONFIG_NAME}")
        return 2
    matched = [p for p in _media_files(pack_dir)
               if p.relative_to(pack_dir).as_posix().startswith(prefix)]
    if not matched:
        print(f"FAIL  no files in {pack_dir} match prefix {prefix!r} — "
              "render the round's files first")
        return 2
    # A prefix reuse once let a check pass with zero new work (_PREV_v2_
    # matched an old rejected file): refuse if any matched file is already
    # claimed by an existing named group (the "" catch-all claims nothing).
    for p in matched:
        rel = p.relative_to(pack_dir).as_posix()
        for g in groups:
            if g.get("prefix") and rel.startswith(g["prefix"]):
                print(f"FAIL  {rel} already belongs to group "
                      f"{g['prefix']!r} — prefix reuse")
                return 2
    for g in groups:
        if g.get("state") == "listen":
            g["state"] = "heard"
            g["label"] = "listened - " + re.sub(
                r"(?i)^\s*LISTEN NOW\s*-\s*", "", g.get("label", ""))
    groups.insert(0, {"prefix": prefix, "state": "listen", "label": label})
    if not any(g.get("prefix") == "" for g in groups):
        groups.append(dict(CATCH_ALL))
    cfg["groups"] = groups
    cfg["todo"] = todo
    cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    out = generate_index(pack_dir)
    print(f"round opened: prefix {prefix!r} -> listen ({len(matched)} files), "
          f"page {out}")
    return 0


def check_page(root: Path, page: str, port: int,
               timeout: float = 10.0) -> int:
    """GET the page (200) + Range-probe every listen-group file (206).

    Catches the 2026-10-06 failure: a wedged server that answered comment
    endpoints 200 but returned an empty reply for every file.
    """
    page = page.strip("/")
    base = f"http://127.0.0.1:{port}/{page}/"
    ok = True

    def _status(url: str, headers: dict | None = None):
        req = urllib.request.Request(url, headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()
        except (urllib.error.URLError, OSError) as e:
            return 0, str(e).encode()

    code, body = _status(base)
    ok &= code == 200
    print(f"{'PASS' if code == 200 else 'FAIL'}  {base}  http={code}")
    if code != 200:
        return 1
    cfg = _load_config(root / page)
    prefixes = [g.get("prefix", "") for g in (cfg or {}).get("groups", [])
                if g.get("state") == "listen"]
    srcs = re.findall(r'<audio[^>]+src="([^"]+)"',
                      body.decode("utf-8", errors="replace"))
    targets = [s for s in srcs
               if any(s.startswith(px) for px in prefixes)]
    if not targets:
        print("note: no listen-group files to probe"
              + ("" if cfg else f" (no {CONFIG_NAME})"))
    for s in targets:
        url = urljoin(base, s)
        code, _ = _status(url, {"Range": "bytes=0-99"})
        ok &= code == 206
        print(f"{'PASS' if code == 206 else 'FAIL'}  {url}  "
              f"range={code}")
    return 0 if ok else 1


def print_comments(root: Path, page: str | None) -> int:
    logs = ([_log_path(root, page)] if page
            else sorted((root / COMMENTS_DIR).glob("*.jsonl")))
    shown = 0
    for log in logs:
        if not log.is_file():
            print(f"(no log) {log}")
            continue
        for line in log.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            e = json.loads(line)
            print(f"{log.stem}  {e['ts_utc']}  {e['audio']}  "
                  f"[{e['verdict'] or '—'}]  {e['comment']}")
            shown += 1
    if not shown:
        print("no comments logged")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(prog="audition_review")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("serve", help="static + comment server on 127.0.0.1")
    s.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    s.add_argument("--port", type=int, default=8778)

    g = sub.add_parser("page", help="generate index.html for a pack dir")
    g.add_argument("--dir", type=Path, required=True)
    g.add_argument("--title", default=None,
                   help="required unless the pack has audition.json")
    g.add_argument("--note", default="")
    g.add_argument("--force", action="store_true",
                   help="overwrite an existing index.html in a config-less pack")

    r = sub.add_parser("round", help="new listen round for a configured pack")
    r.add_argument("--dir", type=Path, required=True)
    r.add_argument("--prefix", required=True,
                   help="filename prefix of this round's files, never reused")
    r.add_argument("--label", required=True)
    r.add_argument("--todo", default="", help="html shown in the LISTEN NOW box")

    k = sub.add_parser("check", help="page 200 + range-206 probe per listen file")
    k.add_argument("--page", required=True,
                   help="pack path under the served root, e.g. mojgrad_khansovac_122")
    k.add_argument("--port", type=int, default=8778)
    k.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    k.add_argument("--timeout", type=float, default=10.0)

    c = sub.add_parser("comments", help="read back logged comments")
    c.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    c.add_argument("--page", default=None, help="page path slug, e.g. flip_sample")

    args = p.parse_args()

    if args.cmd == "serve":
        root = args.root.resolve()
        handler = lambda *a, **kw: AuditionHandler(*a, directory=str(root), **kw)  # noqa: E731
        httpd = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
        print(f"audition_review serving {root} at http://127.0.0.1:{args.port}/")
        print(f"comment logs -> {root / COMMENTS_DIR}/")
        httpd.serve_forever()
        return 0
    if args.cmd == "page":
        try:
            out = generate_index(args.dir.resolve(), args.title, args.note,
                                 force=args.force)
        except (FileExistsError, ValueError) as e:
            print(f"refused: {e}")
            return 2
        print(f"wrote {out}")
        return 0
    if args.cmd == "round":
        return round_pack(args.dir.resolve(), args.prefix, args.label,
                          args.todo)
    if args.cmd == "check":
        return check_page(args.root.resolve(), args.page, args.port,
                          args.timeout)
    return print_comments(args.root.resolve(), args.page)


if __name__ == "__main__":
    raise SystemExit(main())
