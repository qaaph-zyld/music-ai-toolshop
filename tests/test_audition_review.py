"""Tests for scripts/audition_review.py — commented listening pages.

Spin up a real server on an ephemeral port against a tmp pack root and
exercise the full POST -> JSONL -> GET-comments round trip, the .html
widget injection, static passthrough, and input guards.
"""

from __future__ import annotations

import json
import re
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
    check_page,
    generate_index,
    print_comments,
    round_pack,
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


def _get_range(url: str, path: str, rng: str):
    req = urllib.request.Request(f"{url}{path}", headers={"Range": rng})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


class TestRangeRequests:
    """<audio> seeking needs Range support — stdlib http.server has none."""

    def test_prefix_range(self, server, pack_root):
        base, _ = server
        code, hdrs, body = _get_range(base, "/a.wav", "bytes=0-7")
        assert code == 206
        assert hdrs["Content-Range"] == "bytes 0-7/16"
        assert hdrs["Accept-Ranges"] == "bytes"
        assert body == (pack_root / "a.wav").read_bytes()[:8]

    def test_open_ended_range(self, server, pack_root):
        base, _ = server
        code, hdrs, body = _get_range(base, "/a.wav", "bytes=8-")
        assert code == 206
        assert hdrs["Content-Range"] == "bytes 8-15/16"
        assert body == (pack_root / "a.wav").read_bytes()[8:]

    def test_suffix_range(self, server, pack_root):
        base, _ = server
        code, hdrs, body = _get_range(base, "/a.wav", "bytes=-4")
        assert code == 206
        assert hdrs["Content-Range"] == "bytes 12-15/16"
        assert body == (pack_root / "a.wav").read_bytes()[-4:]

    def test_full_get_advertises_ranges(self, server, pack_root):
        base, _ = server
        req = urllib.request.Request(f"{base}/a.wav")
        with urllib.request.urlopen(req, timeout=5) as r:
            assert r.status == 200
            assert r.headers["Accept-Ranges"] == "bytes"
            assert r.read() == (pack_root / "a.wav").read_bytes()

    def test_unsatisfiable_range_416(self, server):
        base, _ = server
        code, _, _ = _get_range(base, "/a.wav", "bytes=999-")
        assert code == 416

    def test_range_on_nested_file(self, server, pack_root):
        base, _ = server
        code, _, body = _get_range(base, "/sub/b.wav", "bytes=0-3")
        assert code == 206
        assert body == (pack_root / "sub" / "b.wav").read_bytes()[:4]


def _widget_js(server) -> str:
    base, _ = server
    _, body = _get(base, "/__audition__/comments.js")
    return body.decode("utf-8")


def _handler_body(js: str, name: str) -> str:
    m = re.search(r"function %s\(\)\s*\{(.*?)\n    \}" % name, js, re.S)
    assert m, f"handler function {name}() not found in widget JS"
    return m.group(1)


class TestWidgetAutosave:
    """2026-10-05: a 'pick' chosen in the dropdown was lost — only the save
    button POSTed. A verdict change must persist itself."""

    def test_verdict_change_posts_full_payload(self, server):
        js = _widget_js(server)
        m = re.search(r'sel\.addEventListener\("change",\s*(\w+)\)', js)
        assert m, "verdict <select> has no change listener"
        body = _handler_body(js, m.group(1))
        assert '"/__audition__/comment"' in body and '"POST"' in body
        assert "verdict: sel.value" in body and "comment: ta.value" in body

    def test_change_reports_status(self, server):
        js = _widget_js(server)
        name = re.search(r'sel\.addEventListener\("change",\s*(\w+)\)', js)
        body = _handler_body(js, name.group(1))
        assert '"saved "' in body
        assert "save FAILED" in js

    def test_save_button_and_blur_share_the_handler(self, server):
        js = _widget_js(server)
        name = re.search(r'sel\.addEventListener\("change",\s*(\w+)\)',
                         js).group(1)
        assert f"btn.onclick = {name};" in js
        blur = re.search(r'ta\.addEventListener\("blur",.*?\n    \}\);',
                         js, re.S)
        assert blur, "comment <textarea> has no blur listener"
        assert f"{name}()" in blur.group(0)

    def test_single_post_path(self, server):
        """One save function — no second, divergent payload builder."""
        assert _widget_js(server).count('"/__audition__/comment"') == 1


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


# ---------------------------------------------------------------------------
# v2 — per-pack audition.json: grouped coloured pages, round, check, songs
# ---------------------------------------------------------------------------

AUDITION_CFG = {
    "title": "Test Song — review",
    "artist": "Tester",
    "song": "Test Song",
    "todo": "<b>listen to the green rows</b>",
    "groups": [
        {"prefix": "_NEW_", "state": "listen", "label": "LISTEN NOW - round 2"},
        {"prefix": "_OLD_", "state": "heard", "label": "listened - round 1"},
        {"prefix": "_BAD_", "state": "rej", "label": "rejected - round 0"},
        {"prefix": "", "state": "ref", "label": "source / reference"},
    ],
}
CFG_FILES = ("_NEW_2_b.mp3", "_NEW_1_a.mp3", "_OLD_1.mp3",
             "_BAD_1.mp3", "src_take.mp3")


@pytest.fixture()
def cfg_pack(tmp_path):
    """Pack dir with audition.json + one file per group (two for listen)."""
    (tmp_path / "audition.json").write_text(
        json.dumps(AUDITION_CFG, ensure_ascii=False), encoding="utf-8")
    for name in CFG_FILES:
        (tmp_path / name).write_bytes(b"RIFF" + name.encode())
    return tmp_path


@pytest.fixture()
def serve_root():
    """Factory: serve an arbitrary root on an ephemeral port."""
    httpds = []

    def _serve(root: Path):
        handler = lambda *a, **kw: AuditionHandler(  # noqa: E731
            *a, directory=str(root), **kw)
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()
        httpds.append(httpd)
        return f"http://127.0.0.1:{httpd.server_address[1]}", httpd

    yield _serve
    for h in httpds:
        h.shutdown()


def _srcs(html: str):
    return re.findall(r'<audio[^>]+src="([^"]+)"', html)


class TestConfigPage:
    def test_rows_grouped_then_alphabetical(self, cfg_pack):
        html = generate_index(cfg_pack).read_text(encoding="utf-8")
        assert _srcs(html) == ["_NEW_1_a.mp3", "_NEW_2_b.mp3",
                               "_OLD_1.mp3", "_BAD_1.mp3", "src_take.mp3"]

    def test_state_class_and_tag_per_row(self, cfg_pack):
        html = generate_index(cfg_pack).read_text(encoding="utf-8")
        rows = re.findall(
            r'<tr class="g-(\w+)"><td data-tag="([^"]*)">([^<]+)</td>', html)
        assert [r[0] for r in rows] == ["listen", "listen",
                                        "heard", "rej", "ref"]
        assert rows[3][1] == "rejected - round 0"
        assert rows[4][1] == "source / reference"

    def test_legend_todo_and_title(self, cfg_pack):
        html = generate_index(cfg_pack).read_text(encoding="utf-8")
        assert 'class="legend"' in html
        assert html.count("</span>") >= 4  # the four colour chips
        assert 'class="todo"' in html and "green rows" in html
        assert "Test Song — review" in html and "Tester" in html

    def test_groups_and_repaint_event_embedded(self, cfg_pack):
        html = generate_index(cfg_pack).read_text(encoding="utf-8")
        assert "_NEW_" in html                      # GROUPS injected into JS
        assert "audition:saved" in html             # repaint trigger
        assert "played:" in html                    # >50% rule
        assert "rejected by you" in html

    def test_config_pack_regenerates_freely(self, cfg_pack):
        generate_index(cfg_pack)
        assert generate_index(cfg_pack).is_file()

    def test_no_section_no_banner(self, cfg_pack):
        html = generate_index(cfg_pack).read_text(encoding="utf-8")
        assert 'class="g-section"' not in html

    def test_section_banner_once_per_segment(self, tmp_path):
        cfg = {"title": "t", "groups": [
            {"prefix": "_A_", "state": "listen", "label": "vox",
             "section": "2 · hook"},
            {"prefix": "_B_", "state": "listen", "label": "bed",
             "section": "2 · hook"},
            {"prefix": "_C_", "state": "listen", "label": "vox",
             "section": "3 · verse"},
            {"prefix": "_D_", "state": "ref", "label": "ref"},
        ]}
        (tmp_path / "audition.json").write_text(
            json.dumps(cfg), encoding="utf-8")
        for n in ("_A_1.mp3", "_B_1.mp3", "_C_1.mp3", "_D_1.mp3"):
            (tmp_path / n).write_bytes(b"RIFF")
        html = generate_index(tmp_path).read_text(encoding="utf-8")
        heads = re.findall(
            r'<tr class="g-section"><td colspan="2">([^<]+)</td></tr>', html)
        assert heads == ["2 · hook", "3 · verse"]  # shared banner emitted once
        # banner sits before its first candidate row
        assert html.index("2 · hook") < html.index("_A_1.mp3")
        assert html.index("_B_1.mp3") < html.index("3 · verse") \
            < html.index("_C_1.mp3")

    def test_section_escaped(self, tmp_path):
        cfg = {"title": "t", "groups": [
            {"prefix": "_A_", "state": "listen", "label": "x",
             "section": "a<b>&\""},
        ]}
        (tmp_path / "audition.json").write_text(
            json.dumps(cfg), encoding="utf-8")
        (tmp_path / "_A_1.mp3").write_bytes(b"RIFF")
        html = generate_index(tmp_path).read_text(encoding="utf-8")
        assert "a&lt;b&gt;&amp;&quot;" in html


class TestNoConfigUnchanged:
    def test_legacy_output_byte_identical(self, tmp_path):
        (tmp_path / "x.wav").write_bytes(b"x")
        html = generate_index(tmp_path, "T", "n").read_text(encoding="utf-8")
        expected = (
            '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
            '<title>T</title>\n<style>\n'
            'body { font-family: system-ui, sans-serif; margin: 2em; '
            'background: #101014; color: #e8e8ee; }\n'
            'a { color: #9ec1ff } table { border-collapse: collapse; '
            'margin: 1em 0 }\n'
            'td, th { border: 1px solid #444; padding: .3em .7em }\n'
            '</style></head><body>\n<h1>T</h1>\n<p>n</p>\n<table>\n'
            '<tr><td>x.wav</td>'
            '<td><audio controls preload="none" src="x.wav"></audio></td>'
            '</tr>\n</table>\n</body></html>\n'
        )
        assert html == expected

    def test_existing_index_refused_without_config_or_force(self, tmp_path):
        (tmp_path / "index.html").write_text("<html>curated</html>",
                                             encoding="utf-8")
        (tmp_path / "x.wav").write_bytes(b"x")
        with pytest.raises(FileExistsError):
            generate_index(tmp_path, "T")
        assert (tmp_path / "index.html").read_text(
            encoding="utf-8") == "<html>curated</html>"
        generate_index(tmp_path, "T", force=True)  # escape hatch
        assert "curated" not in (tmp_path / "index.html").read_text(
            encoding="utf-8")


class TestRound:
    def test_flips_listen_to_heard_and_prepends(self, cfg_pack):
        (cfg_pack / "_R3_1_a.mp3").write_bytes(b"RIFF-r3")
        assert round_pack(cfg_pack, "_R3_", "LISTEN NOW - r3", "<b>t</b>") == 0
        cfg = json.loads(
            (cfg_pack / "audition.json").read_text(encoding="utf-8"))
        assert cfg["groups"][0] == {"prefix": "_R3_", "state": "listen",
                                    "label": "LISTEN NOW - r3"}
        assert cfg["groups"][1]["state"] == "heard"
        assert cfg["groups"][1]["label"] == "listened - round 2"
        assert cfg["todo"] == "<b>t</b>"
        html = (cfg_pack / "index.html").read_text(encoding="utf-8")
        assert "_R3_1_a.mp3" in html

    def test_reused_prefix_on_old_files_refused(self, cfg_pack):
        # _BAD_1.mp3 is already claimed by the rej group — the _PREV_v2_
        # incident: a reused prefix can pass a check with zero new work.
        assert round_pack(cfg_pack, "_BAD_", "x", "y") != 0
        assert round_pack(cfg_pack, "_BAD", "x", "y") != 0
        cfg = json.loads(
            (cfg_pack / "audition.json").read_text(encoding="utf-8"))
        assert cfg["groups"][0]["prefix"] == "_NEW_"  # untouched

    def test_prefix_already_in_config_refused(self, cfg_pack):
        assert round_pack(cfg_pack, "_NEW_", "x", "y") != 0

    def test_no_matching_files_refused(self, cfg_pack):
        assert round_pack(cfg_pack, "_ZERO_", "x", "y") != 0

    def test_missing_config_refused(self, tmp_path):
        (tmp_path / "_A_1.mp3").write_bytes(b"RIFF")
        assert round_pack(tmp_path, "_A_", "x", "y") != 0

    def test_section_arg_lands_on_new_group(self, cfg_pack):
        (cfg_pack / "_R4_1.mp3").write_bytes(b"RIFF-r4")
        assert round_pack(cfg_pack, "_R4_", "LISTEN NOW - r4", "",
                          section="4 · bridge") == 0
        cfg = json.loads(
            (cfg_pack / "audition.json").read_text(encoding="utf-8"))
        assert cfg["groups"][0] == {"prefix": "_R4_", "state": "listen",
                                    "label": "LISTEN NOW - r4",
                                    "section": "4 · bridge"}
        html = (cfg_pack / "index.html").read_text(encoding="utf-8")
        assert 'class="g-section"' in html and "4 · bridge" in html


@pytest.fixture()
def songs_root(tmp_path):
    p1 = tmp_path / "p1"
    p1.mkdir()
    (p1 / "audition.json").write_text(
        json.dumps(AUDITION_CFG, ensure_ascii=False), encoding="utf-8")
    for name in CFG_FILES:
        (p1 / name).write_bytes(b"RIFF" + name.encode())
    (tmp_path / "p2").mkdir()
    (tmp_path / "p2" / "x.mp3").write_bytes(b"RIFF")  # no config -> not a song
    (tmp_path / "index.html").write_text("<html>curated</html>",
                                         encoding="utf-8")
    logs = tmp_path / COMMENTS_DIR
    logs.mkdir()
    (logs / "p1.jsonl").write_text(json.dumps(
        {"ts_utc": "2026-10-06T01:02:03+00:00", "audio": "_NEW_1_a.mp3",
         "verdict": "pick", "comment": ""}) + "\n", encoding="utf-8")
    return tmp_path


class TestSongsEndpoint:
    def test_lists_only_configured_packs(self, serve_root, songs_root):
        base, _ = serve_root(songs_root)
        code, body = _get(base, "/__audition__/songs")
        assert code == 200
        songs = json.loads(body)
        assert [s["slug"] for s in songs] == ["p1"]
        s = songs[0]
        assert s["title"] == "Test Song — review"
        assert s["artist"] == "Tester"
        assert s["link"] == "/p1/"
        assert s["listen_files"] == 2
        assert s["latest_ts_utc"] == "2026-10-06T01:02:03+00:00"

    def test_root_config_is_not_a_pack(self, serve_root, songs_root):
        (songs_root / "audition.json").write_text(
            json.dumps(AUDITION_CFG), encoding="utf-8")
        base, _ = serve_root(songs_root)
        _, body = _get(base, "/__audition__/songs")
        assert all(s["link"] != "/" for s in json.loads(body))


class TestCheckSubcommand:
    def test_ok_when_page_200_and_listen_files_206(self, serve_root,
                                                   songs_root):
        generate_index(songs_root / "p1")
        base, _ = serve_root(songs_root)
        port = int(base.rsplit(":", 1)[1])
        assert check_page(songs_root, "p1", port) == 0

    def test_fails_when_listen_file_missing(self, serve_root, songs_root):
        generate_index(songs_root / "p1")
        (songs_root / "p1" / "_NEW_1_a.mp3").unlink()
        base, _ = serve_root(songs_root)
        port = int(base.rsplit(":", 1)[1])
        assert check_page(songs_root, "p1", port) != 0


class TestWidgetSavedEvent:
    def test_save_dispatches_audition_saved(self, server):
        js = _widget_js(server)
        body = _handler_body(js, "save")
        assert 'CustomEvent("audition:saved"' in body
        assert "detail:" in body and "verdict" in body
        assert "document.dispatchEvent" in body


class TestFrozenContract:
    def test_jsonl_schema_unchanged(self, server, pack_root):
        _post_comment(server, verdict="ok", comment="c")
        entry = json.loads(
            (pack_root / COMMENTS_DIR / "pack.jsonl")
            .read_text(encoding="utf-8").splitlines()[0])
        assert set(entry) == {"ts_utc", "audio", "verdict", "comment"}
