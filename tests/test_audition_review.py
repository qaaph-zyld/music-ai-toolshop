"""Tests for scripts/audition_review.py — commented listening pages.

Spin up a real server on an ephemeral port against a tmp pack root and
exercise the full POST -> JSONL -> GET-comments round trip, the .html
widget injection, static passthrough, and input guards.
"""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from scripts.audition_review import (
    AuditionHandler,
    COMMENTS_DIR,
    VERDICTS,
    _slug,
    generate_index,
    print_comments,
)

HTML_PAGE = """<!doctype html><html><body>
<audio controls src="a.wav"></audio>
<audio controls src="sub/b.wav"></audio>
</body></html>
"""


@pytest.fixture()
def pack_root(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "index.html").write_text(HTML_PAGE, encoding="utf-8")
    (tmp_path / "a.wav").write_bytes(b"RIFFfakewav-aaaa")
    (tmp_path / "sub" / "b.wav").write_bytes(b"RIFFfakewav-bbbb")
    return tmp_path


@pytest.fixture()
def server(pack_root):
    handler = lambda *a, **kw: AuditionHandler(  # noqa: E731
        *a, directory=str(pack_root), **kw)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}", httpd
    httpd.shutdown()
    t.join(timeout=5)


def _post(url: str, payload: dict) -> int:
    req = urllib.request.Request(
        f"{url}/__audition__/comment",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


def _get(url: str, path: str):
    with urllib.request.urlopen(f"{url}{path}", timeout=5) as r:
        return r.status, r.read()


def _post_comment(server, audio="a.wav", verdict="pick", comment="good one"):
    base, _ = server
    return _post(base, {"page": "/pack/", "audio": audio,
                        "verdict": verdict, "comment": comment})


class TestServer:
    def test_binds_localhost_only(self, server):
        _, httpd = server
        assert httpd.server_address[0] == "127.0.0.1"

    def test_html_injected_disk_untouched(self, server, pack_root):
        base, _ = server
        code, body = _get(base, "/index.html")
        assert code == 200
        assert b"/__audition__/comments.js" in body
        # the file on disk is not modified
        assert "comments.js" not in (
            pack_root / "index.html").read_text(encoding="utf-8")

    def test_wav_passthrough_identical(self, server, pack_root):
        base, _ = server
        code, body = _get(base, "/a.wav")
        assert code == 200
        assert body == (pack_root / "a.wav").read_bytes()

    def test_directory_index_injected(self, server):
        """Directory URLs (/pack/) serve index.html — must also inject."""
        base, _ = server
        code, body = _get(base, "/")
        assert code == 200
        assert b"/__audition__/comments.js" in body

    def test_widget_js_served(self, server):
        base, _ = server
        code, body = _get(base, "/__audition__/comments.js")
        assert code == 200 and b"fetch" in body


class TestCommentLog:
    def test_post_appends_one_jsonl(self, server, pack_root):
        assert _post_comment(server) == 204
        log = pack_root / COMMENTS_DIR / "pack.jsonl"
        lines = log.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1
        e = json.loads(lines[0])
        assert e["audio"] == "a.wav" and e["verdict"] == "pick"
        assert e["comment"] == "good one" and "ts_utc" in e

    def test_comments_get_roundtrip(self, server):
        base, _ = server
        _post_comment(server, verdict="flag", comment="harsh 808")
        code, body = _get(base, "/__audition__/comments?page=/pack/")
        assert code == 200
        m = json.loads(body)
        assert m["a.wav"]["verdict"] == "flag"
        assert m["a.wav"]["comment"] == "harsh 808"

    def test_latest_comment_wins_on_read(self, server):
        base, _ = server
        _post_comment(server, verdict="flag", comment="first")
        _post_comment(server, verdict="pick", comment="changed mind")
        _, body = _get(base, "/__audition__/comments?page=/pack/")
        m = json.loads(body)
        assert m["a.wav"]["verdict"] == "pick"

    def test_utf8_comment(self, server, pack_root):
        _post_comment(server, comment="čudan zvuk — ššš")
        log = pack_root / COMMENTS_DIR / "pack.jsonl"
        assert "čudan zvuk" in log.read_text(encoding="utf-8")

    def test_pages_isolated_by_slug(self, server, pack_root):
        base, _ = server
        _post(base, {"page": "/pack_a/", "audio": "x.wav",
                     "verdict": "ok", "comment": ""})
        _post(base, {"page": "/pack_b/", "audio": "x.wav",
                     "verdict": "reject", "comment": ""})
        _, body_a = _get(base, "/__audition__/comments?page=/pack_a/")
        _, body_b = _get(base, "/__audition__/comments?page=/pack_b/")
        assert json.loads(body_a)["x.wav"]["verdict"] == "ok"
        assert json.loads(body_b)["x.wav"]["verdict"] == "reject"


class TestGuards:
    def test_traversal_slug_sanitized(self, server, pack_root):
        base, _ = server
        code = _post(base, {"page": "/../../evil/", "audio": "a.wav",
                            "verdict": "ok", "comment": ""})
        assert code == 204
        logs = list((pack_root / COMMENTS_DIR).glob("*.jsonl"))
        assert len(logs) == 1
        assert logs[0].parent == pack_root / COMMENTS_DIR
        assert ".." not in logs[0].name

    def test_missing_audio_rejected(self, server):
        base, _ = server
        assert _post(base, {"page": "/p/", "audio": "",
                            "verdict": "ok", "comment": "x"}) == 400

    def test_empty_verdict_and_comment_rejected(self, server):
        base, _ = server
        assert _post(base, {"page": "/p/", "audio": "a.wav",
                            "verdict": "", "comment": ""}) == 400

    def test_bad_verdict_rejected(self, server):
        base, _ = server
        assert _post(base, {"page": "/p/", "audio": "a.wav",
                            "verdict": "hax", "comment": ""}) == 400

    def test_oversized_body_rejected(self, server):
        base, _ = server
        assert _post(base, {"page": "/p/", "audio": "a.wav",
                            "verdict": "ok",
                            "comment": "x" * 70000}) == 400

    def test_unknown_post_route_404(self, server):
        base, _ = server
        req = urllib.request.Request(
            f"{base}/__audition__/nope", data=b"{}",
            headers={"Content-Type": "application/json"}, method="POST")
        with pytest.raises(urllib.error.HTTPError) as ei:
            urllib.request.urlopen(req, timeout=5)
        assert ei.value.code == 404


class TestSlug:
    def test_basic(self):
        assert _slug("/flip_sample/") == "flip_sample"

    def test_nested(self):
        assert _slug("/beats/nachtfahrt_flip/") == "beats_nachtfahrt_flip"

    def test_empty(self):
        assert _slug("/") == "index"

    def test_traversal_safe(self):
        s = _slug("/../../etc/passwd")
        assert "/" not in s and ".." not in s


class TestPageGenerator:
    def test_one_audio_per_media(self, tmp_path):
        (tmp_path / "x.wav").write_bytes(b"x")
        (tmp_path / "sub").mkdir()
        (tmp_path / "sub" / "y.mp3").write_bytes(b"y")
        (tmp_path / "note.txt").write_text("n")
        out = generate_index(tmp_path, "T", "note")
        html = out.read_text(encoding="utf-8")
        assert html.count("<audio") == 2
        assert 'src="x.wav"' in html and 'src="sub/y.mp3"' in html
        assert "note.txt" not in html


class TestCommentsReader:
    def test_prints_entries(self, pack_root, capsys):
        log = pack_root / COMMENTS_DIR / "pack.jsonl"
        log.parent.mkdir()
        log.write_text(json.dumps(
            {"ts_utc": "t", "audio": "a.wav", "verdict": "pick",
             "comment": "yes"}, ensure_ascii=False) + "\n", encoding="utf-8")
        assert print_comments(pack_root, "pack") == 0
        out = capsys.readouterr().out
        assert "a.wav" in out and "pick" in out
