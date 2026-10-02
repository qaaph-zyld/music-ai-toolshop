"""Wave 3S: API security/robustness hardening (findings H1-H3, M1-M4, L1-L4).

Every test here was written to fail against the pre-3S api.py first. Tests that
only pin behaviour which was already correct say so in their docstring.
No test writes the real MAirina_Tucc\\data\\ or the real lyrics.db.
"""

from __future__ import annotations

import re
import sqlite3
import threading
import time

import pytest

from mairina import api, atlas, corpus, devices, rank, votes

VERSE = ("usne crvene ko lava\n"
         "s tobom uvek glava\n"
         "niko ne pomisli da spava\n")
WARMING = "Corpus atlas is warming up (first run ~20 s) - retry shortly"
DRIVE_PATH = re.compile(r"[A-Za-z]:[\\/]")


def _make_app(corpus_db, data_dir):
    """create_app, then wait for the startup atlas warm-up (when this build has one)."""
    app = api.create_app(lyrics_db=corpus_db, data_dir=data_dir)
    warm = app.extensions["mairina"].get("atlas")
    if warm is not None:
        assert warm.wait(60), "atlas warm-up did not finish"
    return app


@pytest.fixture()
def app(corpus_db, data_dir):
    return _make_app(corpus_db, data_dir)


@pytest.fixture()
def client(app):
    return app.test_client()


def _json_error(resp, status):
    statuses = status if isinstance(status, tuple) else (status,)
    assert resp.status_code in statuses, (resp.status_code, resp.data[:200])
    assert resp.mimetype == "application/json"
    body = resp.get_json()
    assert set(body) == {"error"} and body["error"]
    assert b"<html" not in resp.data.lower()
    return body["error"]


def _shown_count(data_dir) -> int:
    """How many lists the server has logged (a list with no items still counts)."""
    db = data_dir / "mairina.db"
    if not db.is_file():
        return 0
    con = sqlite3.connect(str(db))
    try:
        ids = {r[0] for r in con.execute("SELECT DISTINCT list_id FROM shown")}
        has_lists = con.execute("SELECT 1 FROM sqlite_master WHERE name='lists'").fetchone()
        if has_lists:
            ids |= {r[0] for r in con.execute("SELECT list_id FROM lists")}
        return len(ids)
    finally:
        con.close()


def _rows(data_dir, sql, *args):
    con = sqlite3.connect(str(data_dir / "mairina.db"))
    try:
        return con.execute(sql, args).fetchall()
    finally:
        con.close()


def _make_list(client, word="lava"):
    resp = client.post("/api/rhyme", json={"word": word, "lane": "all"})
    assert resp.status_code == 200
    return resp.get_json()["list_id"]


# --- H1: DNS rebinding / cross-site -------------------------------------------

@pytest.mark.parametrize("host", ["evil.test:8000", "evil.test", "127.0.0.1.evil.test:8000",
                                  "localhost.evil.test"])
def test_h1_foreign_host_header_is_rejected_with_json(client, data_dir, host):
    for method, path, kw in (("get", "/api/stats", {}),
                             ("get", "/api/compare?lane=drill", {}),
                             ("post", "/api/rhyme", {"json": {"word": "lava", "lane": "all"}})):
        resp = getattr(client, method)(path, headers={"Host": host}, **kw)
        _json_error(resp, (400, 403))
    assert _shown_count(data_dir) == 0                    # nothing was logged by the rejected calls


@pytest.mark.parametrize("host", ["127.0.0.1:8000", "127.0.0.1", "localhost:8000", "localhost"])
def test_h1_local_host_headers_are_served(client, host):
    assert client.get("/api/stats", headers={"Host": host}).status_code == 200


def test_h1_cross_site_fetch_metadata_is_forbidden(client, data_dir):
    for method, path, kw in (("get", "/api/stats", {}),
                             ("post", "/api/rhyme", {"json": {"word": "lava", "lane": "all"}})):
        resp = getattr(client, method)(path, headers={"Sec-Fetch-Site": "cross-site"}, **kw)
        _json_error(resp, 403)
    assert _shown_count(data_dir) == 0


@pytest.mark.parametrize("site", ["same-origin", "none", "same-site", None])
def test_h1_non_cross_site_requests_pass(client, site):
    headers = {"Sec-Fetch-Site": site} if site else {}
    resp = client.post("/api/rhyme", json={"word": "lava", "lane": "all"}, headers=headers)
    assert resp.status_code == 200


def test_h1_vite_proxy_style_request_still_works(client):
    """The Vite proxy (changeOrigin) forwards Host 127.0.0.1:8000 and an application/json body."""
    resp = client.post("/api/rhyme", json={"word": "lava", "lane": "all"},
                       headers={"Host": "127.0.0.1:8000", "Sec-Fetch-Site": "same-origin",
                                "Origin": "http://localhost:5173"})
    assert resp.status_code == 200 and resp.get_json()["items"]


# --- H2: input caps -------------------------------------------------------------

def test_h2_word_phrase_seed_cap_200_chars(client):
    ok, long_ = "x" * 200, "x" * 201
    assert client.post("/api/rhyme", json={"word": ok, "lane": "all"}).status_code == 200
    _json_error(client.post("/api/rhyme", json={"word": long_}), 413)
    assert client.post("/api/multi", json={"phrase": ok, "lane": "all"}).status_code == 200
    _json_error(client.post("/api/multi", json={"phrase": long_}), 413)
    assert client.post("/api/anchors", json={"seed": ok, "lane": "all"}).status_code == 200
    _json_error(client.post("/api/anchors", json={"seed": long_}), 413)
    _json_error(client.get("/api/compare?lane=drill&theme=" + long_), 413)


def test_h2_rhyme_line_cap_500_chars(client):
    assert client.post("/api/rhyme", json={"word": "lava", "line": "x " * 250}).status_code == 200
    _json_error(client.post("/api/rhyme", json={"word": "lava", "line": "x" * 501}), 413)


@pytest.mark.parametrize("path,extra", [("/api/xray", {}),
                                        ("/api/star", {"line_no": 1}),
                                        ("/api/used", {})])
def test_h2_text_line_count_cap_300(client, path, extra):
    ok = "\n".join(["lava pada"] * 300)
    assert client.post(path, json={"text": ok, **extra}).status_code == 200
    _json_error(client.post(path, json={"text": ok + "\nlava pada", **extra}), 413)
    t0 = time.perf_counter()
    _json_error(client.post(path, json={"text": "a\n" * 10000, **extra}), 413)
    assert time.perf_counter() - t0 < 2.0                  # refused before any analysis


@pytest.mark.parametrize("path,extra", [("/api/xray", {}),
                                        ("/api/star", {"line_no": 1}),
                                        ("/api/used", {})])
def test_h2_single_very_long_line_is_refused_not_ground_through(client, path, extra):
    """One 19,999-char line used to take ~30 s in /api/xray (quadratic analysis)."""
    t0 = time.perf_counter()
    _json_error(client.post(path, json={"text": "lava " * 3999, **extra}), 413)
    assert time.perf_counter() - t0 < 2.0


def test_h2_worst_admitted_xray_input_is_fast(client):
    """300 lines at the per-line cap, and 40 max-width lines (the 20k-char ceiling)."""
    text_a = "\n".join(["lava pada glava stara spava mirno " * 4] * 140)[:20000]
    lines_b = ["ko lava na glava " * 29] * 40
    for text in (text_a, "\n".join(lines_b)):
        t0 = time.perf_counter()
        resp = client.post("/api/xray", json={"text": text, "lane": "all"})
        assert resp.status_code == 200
        assert time.perf_counter() - t0 < 5.0


def test_h2_rhyme_line_level_values_are_computed_once_per_request(client, monkeypatch):
    """rank.features_for used to recount the syllables and dominant class of `line` per candidate."""
    line = "ko lava na glava"
    seen = {"count_line": 0, "dominant_class": 0}
    real_count, real_dom = rank.count_line, rank.phonetics.dominant_class

    def count_line(text):
        seen["count_line"] += text == line
        return real_count(text)

    def dominant_class(text):
        seen["dominant_class"] += text == line
        return real_dom(text)

    monkeypatch.setattr(rank, "count_line", count_line)
    monkeypatch.setattr(rank.phonetics, "dominant_class", dominant_class)
    resp = client.post("/api/rhyme", json={"word": "lava", "lane": "all", "line": line, "target": 12})
    assert resp.status_code == 200 and len(resp.get_json()["items"]) >= 2
    assert seen == {"count_line": 1, "dominant_class": 1}


def test_h2_artists_tags_caps(client):
    twenty = [f"a{i}" for i in range(20)]
    assert client.post("/api/rhyme", json={"word": "lava", "artist": twenty}).status_code == 200
    _json_error(client.post("/api/rhyme", json={"word": "lava", "artist": twenty + ["x"]}), 400)
    _json_error(client.post("/api/rhyme", json={"word": "lava", "artist": ",".join(twenty + ["x"])}), 400)
    _json_error(client.get("/api/atlas?lane=all&artist=" + ",".join(twenty + ["x"])), 400)
    _json_error(client.post("/api/rhyme", json={"word": "lava", "artist": ["x" * 65]}), 413)

    star = {"text": "lava pada\nglava stara", "line_no": 1, "lane": "all"}
    ok_tags = [f"t{i}" for i in range(20)]
    assert client.post("/api/star", json={**star, "tags": ok_tags}).status_code == 200
    _json_error(client.post("/api/star", json={**star, "tags": ok_tags + ["extra"]}), 400)
    assert client.post("/api/star", json={**star, "tags": ["t" * 40]}).status_code == 200
    _json_error(client.post("/api/star", json={**star, "tags": ["t" * 65]}), 413)


# --- H3: the atlas is warmed once, in the background ----------------------------

def test_h3_atlas_load_concurrent_callers_scan_once(corpus_db, tmp_path, monkeypatch):
    real, calls = atlas._scan, []

    def slow_scan(*a):
        calls.append(1)
        time.sleep(0.3)
        return real(*a)

    monkeypatch.setattr(atlas, "_scan", slow_scan)
    got = []
    threads = [threading.Thread(
        target=lambda: got.append(atlas.load(corpus_db, tmp_path / "cache", notify=False)))
        for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(30)
    assert len(got) == 5 and all(b == got[0] for b in got)
    assert len(calls) == 1


def test_h3_atlas_warms_in_background_503_then_200_exactly_one_build(
        corpus_db, data_dir, monkeypatch):
    real, gate, calls = atlas.load, threading.Event(), []

    def slow_load(*a, **kw):
        calls.append(threading.current_thread().name)
        assert gate.wait(10), "gate never opened"
        return real(*a, **kw)

    monkeypatch.setattr(atlas, "load", slow_load)
    t0 = time.perf_counter()
    app = api.create_app(lyrics_db=corpus_db, data_dir=data_dir)
    assert time.perf_counter() - t0 < 5                    # startup never waits for the atlas
    client = app.test_client()

    # three stars so xray would want the atlas priors
    for n in (1, 2, 3):
        assert client.post("/api/star", json={"text": VERSE, "line_no": n, "lane": "all",
                                              "draft_id": "d1"}).status_code == 200
    out = []

    def hit(method, path, **kw):
        out.append((path, getattr(client, method)(path, **kw)))

    jobs = [("get", "/api/me?lane=all", {}), ("get", "/api/atlas?lane=all", {}),
            ("post", "/api/xray", {"json": {"text": VERSE, "lane": "drill"}})] * 3
    threads = [threading.Thread(target=hit, args=(m, p), kwargs=kw) for m, p, kw in jobs]
    for t in threads:
        t.start()
    for t in threads:
        t.join(8)
    assert not any(t.is_alive() for t in threads), "a request blocked on the atlas build"
    for path, resp in out:
        if path.startswith("/api/xray"):
            assert resp.status_code == 200
            assert all(ln["vs_star"] is None for ln in resp.get_json()["lines"])
        else:
            assert _json_error(resp, 503) == WARMING
    assert len(calls) == 1 and calls[0] != threading.main_thread().name

    gate.set()
    assert app.extensions["mairina"]["atlas"].wait(30)
    assert client.get("/api/me?lane=all").status_code == 200
    assert client.get("/api/atlas?lane=all").status_code == 200
    xr = client.post("/api/xray", json={"text": VERSE, "lane": "drill"}).get_json()["lines"]
    assert all(ln["vs_star"] for ln in xr)                 # priors available again
    assert len(calls) == 1                                  # requests never rebuild


def test_h3_a_failed_warmup_degrades_then_retries(corpus_db, data_dir, monkeypatch):
    real, state = atlas.load, {"fail": True}

    def flaky(*a, **kw):
        if state["fail"]:
            raise corpus.DbUnavailable("lyrics.db is being written (lyrics.db-journal present) - "
                                       "retry when the writer finishes")
        return real(*a, **kw)

    monkeypatch.setattr(atlas, "load", flaky)
    app = _make_app(corpus_db, data_dir)
    client = app.test_client()
    assert client.get("/api/me?lane=all").status_code == 200    # degrades to plain means
    assert "being written" in _json_error(client.get("/api/atlas?lane=all"), 503)
    state["fail"] = False
    app.extensions["mairina"]["atlas"].retry_after = 0
    resp = client.get("/api/atlas?lane=all")                    # triggers the retry
    assert resp.status_code in (200, 503)
    assert app.extensions["mairina"]["atlas"].wait(30)
    assert client.get("/api/atlas?lane=all").status_code == 200


# --- M1: serve() never runs the debugger ----------------------------------------

def test_m1_serve_disables_debugger_even_with_flask_debug_env(tmp_path, monkeypatch):
    import werkzeug.serving as serving

    seen = {}

    def fake_run_simple(host, port, application, **options):
        seen.update(host=host, port=port, **options)

    monkeypatch.setattr(serving, "run_simple", fake_run_simple)
    monkeypatch.setenv("FLASK_DEBUG", "1")
    app = api.create_app(lyrics_db=tmp_path / "gone.db", data_dir=tmp_path / "d")
    api.serve(app)
    assert (seen["host"], seen["port"]) == ("127.0.0.1", 8000)
    assert seen["use_debugger"] is False and seen["use_reloader"] is False
    assert seen["threaded"] is True
    assert app.debug is False


def test_m1_serve_passes_explicit_safe_run_options(tmp_path, monkeypatch):
    app = api.create_app(lyrics_db=tmp_path / "gone.db", data_dir=tmp_path / "d")
    seen = {}
    monkeypatch.setattr(app, "run", lambda *a, **kw: seen.update(kw))
    monkeypatch.setenv("FLASK_DEBUG", "1")
    api.serve(app)
    assert seen == {"host": "127.0.0.1", "port": 8000, "debug": False, "use_debugger": False,
                    "use_reloader": False, "load_dotenv": False, "threaded": True}


# --- M2: list ids are allocated atomically and never reused ----------------------

class _RacyCon:
    """Connection proxy: makes the first two threads that read MAX(list_id) wait for each
    other (with a timeout), so an unlocked allocate-then-insert is forced to collide."""

    def __init__(self, con, barrier):
        self._con, self._barrier = con, barrier

    def execute(self, sql, *a):
        cur = self._con.execute(sql, *a)
        if "MAX(list_id)" in sql:
            try:
                self._barrier.wait(timeout=1.0)
            except threading.BrokenBarrierError:
                pass
        return cur

    def __getattr__(self, name):
        return getattr(self._con, name)


def test_m2_concurrent_log_shown_gets_distinct_ids(tmp_path):
    db = tmp_path / "m.db"
    votes.connect(db).close()
    barrier = threading.Barrier(2)
    ids, errors = [], []

    def worker(tag):
        con = votes.connect(db)
        try:
            ids.append(votes.log_shown(_RacyCon(con, barrier), "rhyme", tag, "base",
                                       [(f"w{tag}", 1.0, {})]))
        except Exception as exc:                            # noqa: BLE001
            errors.append(exc)
        finally:
            con.close()

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(30)
    assert not errors, errors
    assert len(ids) == 2 and len(set(ids)) == 2


def test_m2_many_threads_log_distinct_lists(tmp_path):
    db = tmp_path / "m.db"
    votes.connect(db).close()
    ids, errors = [], []
    ready = threading.Barrier(5)

    def worker(i):
        try:
            con = votes.connect(db)
            try:
                ready.wait(30)
                for k in range(6):
                    ids.append(votes.log_shown(con, "rhyme", f"{i}-{k}", "base",
                                               [(f"w{i}-{k}", 1.0, {}), (f"v{i}-{k}", 0.5, {})]))
            finally:
                con.close()
        except Exception as exc:                            # noqa: BLE001
            errors.append(repr(exc))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(60)
    assert not errors, errors
    assert len(ids) == 30 and len(set(ids)) == 30
    con = sqlite3.connect(str(db))
    try:                                                    # every list keeps exactly its own 2 rows
        assert {n for _lid, n in con.execute(
            "SELECT list_id, COUNT(*) FROM shown GROUP BY list_id")} == {2}
    finally:
        con.close()


def test_m2_empty_list_id_is_never_reused(client, data_dir):
    empty = client.post("/api/anchors", json={"scheme": "AABB", "lines": 2, "lane": "all",
                                              "mode": "rhyme", "seed": "zzzzx"})
    assert empty.status_code == 200 and empty.get_json()["items"] == []
    empty_id = empty.get_json()["list_id"]
    nxt = _make_list(client)
    assert nxt != empty_id and nxt > empty_id
    # a vote aimed at the empty list must not land on the next list
    resp = client.post("/api/vote", json={"list_id": empty_id, "items": [[1, 1]]})
    _json_error(resp, (400, 404))
    assert _rows(data_dir, "SELECT COUNT(*) FROM votes")[0][0] == 0


def test_m2_empty_list_survives_for_later_lists_in_the_cli_numbering(tmp_path):
    db = tmp_path / "m.db"
    con = votes.connect(db)
    try:
        a = votes.log_shown(con, "anchor", "q", "base", [])
        b = votes.log_shown(con, "rhyme", "q", "base", [("w", 1.0, {})])
        c = votes.log_shown(con, "anchor", "q", "base", [])
        d = votes.log_shown(con, "rhyme", "q", "base", [("w", 1.0, {})])
        assert len({a, b, c, d}) == 4 and a < b < c < d
    finally:
        con.close()


def test_m2_legacy_db_without_lists_table_keeps_counting_up(tmp_path):
    """A mairina.db from before 3S (shown rows, no lists table) must not reuse its ids."""
    db = tmp_path / "old.db"
    con = sqlite3.connect(str(db))
    con.executescript("""
        CREATE TABLE shown(id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, list_id INTEGER NOT NULL,
          arm TEXT NOT NULL, ranker_version TEXT NOT NULL, kind TEXT NOT NULL, query TEXT,
          candidate TEXT NOT NULL, rank INTEGER NOT NULL, score REAL, features_json TEXT);
        CREATE TABLE votes(shown_id INTEGER NOT NULL, vote INTEGER NOT NULL, ts TEXT NOT NULL);
        CREATE TABLE used(candidate TEXT NOT NULL, source_file TEXT, ts TEXT NOT NULL);
        INSERT INTO shown(ts,list_id,arm,ranker_version,kind,query,candidate,rank)
          VALUES ('t',7,'base','v2','rhyme','q','old',1);""")
    con.commit()
    con.close()
    con = votes.connect(db)
    try:
        assert votes.log_shown(con, "rhyme", "q", "base", [("new", 1.0, {})]) == 8
    finally:
        con.close()


# --- M3: GET /api/compare writes `shown` rows ------------------------------------

def test_m3_cross_site_get_compare_writes_nothing(client, data_dir):
    resp = client.get("/api/compare?lane=drill", headers={"Sec-Fetch-Site": "cross-site"})
    _json_error(resp, 403)
    assert _shown_count(data_dir) == 0
    ok = client.get("/api/compare?lane=drill", headers={"Sec-Fetch-Site": "same-origin"})
    assert ok.status_code == 200 and _shown_count(data_dir) >= 1


# --- M4: stronger protocol tests --------------------------------------------------

def test_m4_duplicate_vote_items_are_rejected_without_writing(client, data_dir):
    lid = _make_list(client)
    _json_error(client.post("/api/vote", json={"list_id": lid, "items": [[1, 1], [1, -1]]}), 400)
    _json_error(client.post("/api/vote", json={"list_id": lid, "items": [[1, 1], [1, 1]]}), 400)
    assert _rows(data_dir, "SELECT COUNT(*) FROM votes")[0][0] == 0
    assert client.post("/api/vote", json={"list_id": lid, "items": [[1, 1], [2, -1]]}).status_code == 200


def test_m4_text_plain_post_is_400_and_has_no_side_effects(client, data_dir):
    """Already correct before 3S (pinned): a CORS-simple POST cannot reach the engine."""
    for path in ("/api/rhyme", "/api/anchors", "/api/multi", "/api/star", "/api/vote",
                 "/api/hint-vote", "/api/used", "/api/xray"):
        resp = client.post(path, data='{"word": "lava", "phrase": "x", "text": "lava", '
                                      '"rule_id": "cliche", "vote": -1}',
                           content_type="text/plain")
        _json_error(resp, 400)
    assert _shown_count(data_dir) == 0
    assert not (data_dir / "mairina.db").is_file() or _rows(
        data_dir, "SELECT COUNT(*) FROM hint_votes")[0][0] == 0


@pytest.mark.parametrize("raw", ["[]", "null", "[1,2]", '"str"', "42", "true"],
                         ids=["empty-array", "null", "array", "string", "number", "bool"])
def test_m4_non_object_json_bodies_are_400(client, raw):
    """Already correct before 3S (pinned)."""
    _json_error(client.post("/api/rhyme", data=raw, content_type="application/json"), 400)


@pytest.mark.parametrize("fresh", ["NaN", "Infinity", "-Infinity", "-0.1", "1.1"])
def test_m4_nan_and_out_of_range_fresh_are_400(client, data_dir, fresh):
    """Already correct before 3S (pinned): Python's json accepts the NaN literal."""
    resp = client.post("/api/rhyme", data='{"word": "lava", "fresh": %s}' % fresh,
                       content_type="application/json")
    _json_error(resp, 400)
    assert _shown_count(data_dir) == 0


def test_m4_forced_engine_exception_is_a_clean_500(client, monkeypatch):
    def boom(*a, **kw):
        raise RuntimeError(r"boom while reading D:\secret\dir\file.py line 7")

    monkeypatch.setattr(rank, "rank", boom)
    resp = client.post("/api/rhyme", json={"word": "lava", "lane": "all"})
    _json_error(resp, 500)
    for needle in (b"Traceback", b"D:\\", b"boom", b"secret", b"File \""):
        assert needle not in resp.data
    monkeypatch.undo()
    monkeypatch.setattr(devices, "analyze_verse", boom)
    resp = client.post("/api/xray", json={"text": VERSE, "lane": "all"})
    _json_error(resp, 500)
    assert b"Traceback" not in resp.data and b"D:\\" not in resp.data


# --- L1: error bodies never carry an absolute path --------------------------------

def test_l1_503_bodies_carry_no_absolute_paths(tmp_path):
    gone = tmp_path / "gone" / "lyrics.db"
    c = api.create_app(lyrics_db=gone, data_dir=tmp_path / "d").test_client()
    for method, path, kw in (("get", "/api/compare?lane=drill", {}),
                             ("get", "/api/atlas?lane=drill", {}),
                             ("post", "/api/xray", {"json": {"text": "lava pada", "lane": "all"}}),
                             ("post", "/api/rhyme", {"json": {"word": "lava"}}),
                             ("post", "/api/anchors", {"json": {"lane": "all"}}),
                             ("post", "/api/multi", {"json": {"phrase": "lava"}})):
        resp = getattr(c, method)(path, **kw)
        err = _json_error(resp, 503)
        assert not DRIVE_PATH.search(resp.get_data(as_text=True)), resp.data
        assert str(tmp_path) not in resp.get_data(as_text=True)
        assert "Expected at" not in err and "lyrics.db" in err


def test_l1_other_dbunavailable_messages_are_scrubbed_too(tmp_path, monkeypatch):
    def changed(*a, **kw):
        raise corpus.DbUnavailable(r"lyrics.db changed during the build (D:\x y\lyrics.db) - retry")

    monkeypatch.setattr(corpus, "load_index", changed)
    c = api.create_app(lyrics_db=tmp_path / "x.db", data_dir=tmp_path / "d").test_client()
    resp = c.post("/api/rhyme", json={"word": "lava"})
    _json_error(resp, 503)
    assert not DRIVE_PATH.search(resp.get_data(as_text=True)), resp.data


# --- L2: absurd ids and nesting ---------------------------------------------------

@pytest.mark.parametrize("sid", [10 ** 30, 2 ** 63, 2 ** 63 - 1])
def test_l2_delete_star_with_huge_id_is_404(client, sid):
    _json_error(client.delete(f"/api/star/{sid}"), 404)
    client.post("/api/star", json={"text": VERSE, "line_no": 1})     # now a mairina.db exists
    _json_error(client.delete(f"/api/star/{sid}"), 404)


@pytest.mark.parametrize("raw", ["[" * 200_000, '{"a":' * 100_000, "[" * 200_000 + "]" * 200_000],
                         ids=["open-arrays", "open-objects", "balanced-arrays"])
def test_l2_deeply_nested_json_is_400(client, raw):
    _json_error(client.post("/api/rhyme", data=raw, content_type="application/json"), 400)


# --- L3: draft_id and tags must be strings ----------------------------------------

@pytest.mark.parametrize("bad", [123, 1.5, True, ["a"], {"a": 1}])
def test_l3_non_string_draft_id_is_400(client, data_dir, bad):
    star = {"text": "lava pada\nglava stara", "line_no": 1, "lane": "all", "draft_id": bad}
    _json_error(client.post("/api/star", json=star), 400)
    _json_error(client.post("/api/used", json={"text": "lava pada", "draft_id": bad}), 400)
    assert not (data_dir / "mairina.db").is_file() or _rows(
        data_dir, "SELECT COUNT(*) FROM stars")[0][0] == 0


@pytest.mark.parametrize("bad", [[1], [None], [["a"]], [{"a": 1}], ["ok", 2], [True]])
def test_l3_non_string_tags_are_400(client, data_dir, bad):
    star = {"text": "lava pada\nglava stara", "line_no": 1, "lane": "all", "tags": bad}
    _json_error(client.post("/api/star", json=star), 400)
    assert not (data_dir / "mairina.db").is_file() or _rows(
        data_dir, "SELECT COUNT(*) FROM stars")[0][0] == 0


def test_l3_string_tags_and_draft_id_still_work(client):
    star = {"text": "lava pada\nglava stara", "line_no": 1, "lane": "all",
            "tags": ["Punchline"], "draft_id": "d-1"}
    resp = client.post("/api/star", json=star)
    assert resp.status_code == 200 and resp.get_json()["tags"] == ["punchline"]


# --- L4: an unreadable corpus never stops the app from starting --------------------

def test_l4_corrupt_lyrics_db_starts_and_serves_503(tmp_path):
    bad = tmp_path / "lyrics.db"
    bad.write_bytes(b"this is not a sqlite database " * 200)
    app = api.create_app(lyrics_db=bad, data_dir=tmp_path / "d")
    c = app.test_client()
    resp = c.post("/api/rhyme", json={"word": "lava"})
    _json_error(resp, 503)
    assert not DRIVE_PATH.search(resp.get_data(as_text=True))
    _json_error(c.get("/api/atlas?lane=all"), 503)
    assert c.get("/api/stats").status_code == 200
    assert c.get("/api/me?lane=all").status_code == 200


@pytest.mark.parametrize("exc", [sqlite3.OperationalError("unable to open database file"),
                                 sqlite3.DatabaseError("database disk image is malformed"),
                                 PermissionError(13, "Permission denied", r"D:\secret\index.pkl"),
                                 FileNotFoundError(2, "No such file", r"D:\secret\cache")])
def test_l4_sqlite_and_os_errors_at_startup_degrade_like_dbunavailable(tmp_path, monkeypatch, exc):
    def boom(*a, **kw):
        raise exc

    monkeypatch.setattr(corpus, "load_index", boom)
    app = api.create_app(lyrics_db=tmp_path / "x.db", data_dir=tmp_path / "d")
    c = app.test_client()
    resp = c.post("/api/rhyme", json={"word": "lava"})
    _json_error(resp, 503)
    assert b"secret" not in resp.data and not DRIVE_PATH.search(resp.get_data(as_text=True))
    assert c.get("/api/stats").status_code == 200


def test_l4_gazetteer_failure_at_startup_degrades_too(corpus_db, tmp_path, monkeypatch):
    def boom(*a, **kw):
        raise sqlite3.DatabaseError("malformed")

    monkeypatch.setattr(devices, "load_gazetteer", boom)
    app = api.create_app(lyrics_db=corpus_db, data_dir=tmp_path / "d")
    _json_error(app.test_client().post("/api/rhyme", json={"word": "lava"}), 503)


def test_corpus_down_does_not_start_an_atlas_warmup(tmp_path):
    bare = tmp_path / "bare.db"
    app = api.create_app(lyrics_db=bare, data_dir=tmp_path / "d")
    warm = app.extensions["mairina"].get("atlas")
    assert warm is None or warm.status == "disabled"
    assert not list((tmp_path / "d").glob("atlas_*.pkl")) if (tmp_path / "d").exists() else True
