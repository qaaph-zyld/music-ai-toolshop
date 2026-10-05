"""Audition review — commented listening pages for ear-test gates.

Three subcommands:

    serve   localhost static server over a pack root. Every served .html page
            gets a verdict+comment widget injected beside each <audio> element
            AT SERVE TIME (files on disk are never touched — release-manifest
            hashes and agent-curated pages stay intact). Comments POSTed by
            the widget append to <root>/_audition_comments/<page-slug>.jsonl.
    page    generate an index.html listing every audio file in a pack dir
            (for NEW packs only — never run against agent-curated indexes
            like flip_sample/, it would overwrite them).
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
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

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

def generate_index(pack_dir: Path, title: str, note: str = "") -> Path:
    """Write pack_dir/index.html listing every media file (recursive, sorted)."""
    files = sorted(
        p for p in pack_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in MEDIA_EXTS
    )
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
    out = pack_dir / "index.html"
    out.write_text(html, encoding="utf-8")
    return out


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

    g = sub.add_parser("page", help="generate index.html for a NEW pack dir")
    g.add_argument("--dir", type=Path, required=True)
    g.add_argument("--title", required=True)
    g.add_argument("--note", default="")

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
        out = generate_index(args.dir.resolve(), args.title, args.note)
        print(f"wrote {out}")
        return 0
    return print_comments(args.root.resolve(), args.page)


if __name__ == "__main__":
    raise SystemExit(main())
