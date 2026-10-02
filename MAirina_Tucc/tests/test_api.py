"""The local Flask API (mairina.api) against the fixture corpus and a tmp data dir.

Every response shape is pinned field-for-field against rimer-ui/src/types.ts.
No test writes the real MAirina_Tucc\\data\\ or the real lyrics.db.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
from urllib.parse import quote

import pytest

from mairina import DATA_DIR, api, corpus, votes

VERSE = ("usne crvene ko lava\n"          # mid-line 'ko' -> simile tag
         "s tobom uvek glava\n"           # rhyme partner of lava
         "niko ne pomisli da spava\n")


def _dir_state(path):
    """{name: (size, mtime_ns)} — the data-dir guard, same as the CLI tests."""
    return {p.name: (p.stat().st_size, p.stat().st_mtime_ns) for p in path.iterdir()}


@pytest.fixture()
def client(corpus_db, data_dir):
    app = api.create_app(lyrics_db=corpus_db, data_dir=data_dir)
    assert app.extensions["mairina"]["atlas"].wait(60)       # the atlas warms in the background
    return app.test_client()


def _json_error(resp, status):
    assert resp.status_code == status
    assert resp.mimetype == "application/json"
    body = resp.get_json()
    assert set(body) == {"error"} and body["error"]
    assert b"<html" not in resp.data.lower()


# --- list endpoints -----------------------------------------------------------

def test_anchors_happy_and_exact_shape(client):
    resp = client.post("/api/anchors", json={
        "scheme": "AAAA", "lines": 2, "lane": "all", "mode": "rhyme",
        "seed": None, "fresh": 0.5, "artist": None, "section": "strofa"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert set(body) == {"list_id", "arm", "target", "items"}
    assert body["arm"] in votes.ARMS and isinstance(body["list_id"], int)
    assert body["target"] is None or set(body["target"]) == {"lo", "median", "hi", "approx"}
    assert len(body["items"]) == 2                      # 'glava' + 'lava' class has 2 lemmas
    for it in body["items"]:
        assert set(it) == {"n", "group", "word", "upos", "cls", "freq", "why"}
        assert it["group"] == "A" and it["word"] and it["why"]


def test_anchors_validation_and_empty_result(client):
    _json_error(client.post("/api/anchors", json={"lane": "bogus"}), 400)
    _json_error(client.post("/api/anchors", json={"scheme": "1234!", "lane": "drill"}), 400)
    _json_error(client.post("/api/anchors", json={"scheme": "AABB", "lines": 0}), 400)
    _json_error(client.post("/api/anchors", json={"fresh": 2.0}), 400)
    resp = client.post("/api/anchors", json={"scheme": "AABB", "lines": 2,
                                             "lane": "all", "mode": "rhyme", "seed": "zzzzx"})
    assert resp.status_code == 200                      # NoAnchors -> an empty list, not an error
    body = resp.get_json()
    assert body["items"] == [] and isinstance(body["list_id"], int)


def test_rhyme_happy_and_exact_shape(client):
    resp = client.post("/api/rhyme", json={"word": "lava", "line": None, "target": None,
                                           "lane": "drill", "fresh": 0.5, "artist": None})
    assert resp.status_code == 200
    body = resp.get_json()
    assert set(body) == {"list_id", "arm", "query", "items"}
    assert body["query"] == "lava" and body["arm"] in votes.ARMS
    assert body["items"]                                # spava/glava rhyme with lava
    for it in body["items"]:
        assert set(it) == {"n", "word", "score", "kind", "why"}
        assert " " not in it["word"]


def test_rhyme_errors(client):
    _json_error(client.post("/api/rhyme", json={"lane": "drill"}), 400)          # no word
    _json_error(client.post("/api/rhyme", json={"word": "lava", "target": 9}), 400)  # target sans line
    _json_error(client.post("/api/rhyme", json={"word": "lava", "fresh": "x"}), 400)


def test_multi_happy_and_error(client):
    resp = client.post("/api/multi", json={"phrase": "me imaš", "lane": "all"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert set(body) == {"list_id", "arm", "query", "items"}
    assert body["query"] == "me imaš"
    for it in body["items"]:
        assert set(it) == {"n", "phrase", "score", "why"}
    _json_error(client.post("/api/multi", json={"lane": "all"}), 400)            # no phrase


def test_compare_happy_single_words_and_errors(client):
    resp = client.get("/api/compare?lane=drill")
    assert resp.status_code == 200
    body = resp.get_json()
    assert set(body) == {"list_id", "arm", "items"}
    for it in body["items"]:
        assert set(it) == {"n", "word", "count", "score", "why"}
        assert isinstance(it["word"], str) and " " not in it["word"]   # single words only
    _json_error(client.get("/api/compare?lane=bogus"), 400)
    _json_error(client.get("/api/compare?lane=drill&theme=" + quote("dve reči")), 400)
                                        # theme takes exactly one word


def test_injection_strings_are_safe(client):
    evil = "x' OR '1'='1' --"
    resp = client.post("/api/rhyme", json={"word": evil, "lane": "all", "artist": evil})
    assert resp.status_code == 200 and resp.get_json()["items"] == []
    resp = client.get("/api/atlas?lane=drill&artist=" + quote(evil))
    assert resp.status_code == 200 and resp.get_json()["artists"] == []
    resp = client.post("/api/star", json={"text": "lava pada\nglava stara", "line_no": 1,
                                          "lane": "all", "tags": [], "draft_id": "../" + evil})
    assert resp.status_code == 200                       # opaque id, never a path


# --- xray ---------------------------------------------------------------------

XRAY_KEYS = {"n", "text", "syl", "target", "rhyme", "cons", "cons_density",
             "allit", "assonance", "devices", "hints", "vs_star"}


def test_xray_happy_and_exact_shape(client):
    resp = client.post("/api/xray", json={"text": VERSE, "lane": "drill", "section": "strofa"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert set(body) == {"lines"} and len(body["lines"]) == 3
    for ln in body["lines"]:
        assert set(ln) == XRAY_KEYS
        assert ln["rhyme"] in ("A", "-") and isinstance(ln["syl"], int)
        assert isinstance(ln["cons"], int) and 0 <= ln["cons"] <= 3
        assert isinstance(ln["cons_density"], float)
        assert ln["allit"] is False and ln["vs_star"] is None       # no stars yet
        assert ln["target"] is None                                 # fixture has no 'strofa'
        for d in ln["devices"]:
            assert set(d) == {"kind", "span", "confidence"}
        for h in ln["hints"]:
            assert set(h) == {"rule_id", "label"}
    first = body["lines"][0]
    assert any(d["kind"] == "simile" for d in first["devices"])     # 'ko lava' is a simile
    assert body["lines"][0]["rhyme"] == "A" and body["lines"][1]["rhyme"] == "A"   # lava/glava
    assert body["lines"][2]["rhyme"] == "A"                         # spava joins the group


def test_xray_errors(client):
    _json_error(client.post("/api/xray", json={"lane": "drill"}), 400)     # no text
    _json_error(client.post("/api/xray", json={"text": "lava", "lane": "bogus"}), 400)
    _json_error(client.post("/api/xray", json={"text": "lava", "section": "bogus"}), 400)
    _json_error(client.post("/api/xray", json={"text": "x" * (api.MAX_TEXT_CHARS + 1)}), 413)


def test_xray_vs_star_column_after_three_stars(client):
    for n in (1, 2, 3):
        client.post("/api/star", json={"text": VERSE, "line_no": n,
                                       "lane": "all", "tags": [], "draft_id": "d1"})
    resp = client.post("/api/xray", json={"text": VERSE, "lane": "drill", "section": None})
    lines = resp.get_json()["lines"]
    assert all(ln["vs_star"] and "(n=3)" in ln["vs_star"] for ln in lines)


# --- votes, stars, hints, used --------------------------------------------------

def _make_list(client):
    resp = client.post("/api/rhyme", json={"word": "lava", "lane": "all"})
    assert resp.status_code == 200
    return resp.get_json()["list_id"]


def test_vote_targets_the_exact_list(client, data_dir):
    # two DIFFERENT lists: a rhyme list and a multi list share no candidate
    r1 = client.post("/api/rhyme", json={"word": "lava", "lane": "all"}).get_json()
    r2 = client.post("/api/multi", json={"phrase": "me imaš", "lane": "all"}).get_json()
    lid1, lid2 = r1["list_id"], r2["list_id"]
    assert lid2 != lid1
    cand1, cands2 = r1["items"][0]["word"], {it["phrase"] for it in r2["items"]}
    assert cand1 not in cands2
    resp = client.post("/api/vote", json={"list_id": lid1, "items": [[1, 1]]})
    assert resp.status_code == 200 and resp.get_json() == {"ok": True}   # stale list honored
    con = sqlite3.connect(str(data_dir / "mairina.db"))
    try:                                      # the vote row points at list 1's item, not list 2's
        rows = con.execute("SELECT s.list_id, s.rank, s.candidate, v.vote FROM votes v "
                           "JOIN shown s ON s.id = v.shown_id").fetchall()
    finally:
        con.close()
    assert rows == [(lid1, 1, cand1, 1)]
    _json_error(client.post("/api/vote", json={"list_id": 99999, "items": [[1, 1]]}), 404)
    _json_error(client.post("/api/vote", json={"list_id": lid2, "items": [[999, 1]]}), 400)
    _json_error(client.post("/api/vote", json={"list_id": lid2, "items": [[1, 0]]}), 400)
    _json_error(client.post("/api/vote", json={"items": [[1, 1]]}), 400)


def test_star_round_trip_idempotent_and_shape(client):
    star = {"text": "lava pada\nglava stara\nspava mirno", "line_no": 1,
            "lane": "all", "tags": ["punchline"], "draft_id": "draft-1"}
    r1 = client.post("/api/star", json=star)
    assert r1.status_code == 200
    b1 = r1.get_json()
    assert set(b1) == {"id", "ts", "line_no", "text", "lane", "tags"}
    assert b1["text"] == "lava pada" and b1["lane"] == "all" and b1["tags"] == ["punchline"]

    star2 = dict(star, tags=["wordplay"])
    r2 = client.post("/api/star", json=star2)
    assert r2.status_code == 200
    b2 = r2.get_json()
    assert b2["id"] == b1["id"]                           # same draft+text+lane -> update
    assert b2["tags"] == ["punchline", "wordplay"]        # tags merge, order kept

    resp = client.get("/api/stars")
    items = resp.get_json()["items"]
    assert len(items) == 1 and set(items[0]) == {"id", "ts", "line_no", "text", "lane", "tags"}

    resp = client.delete(f"/api/star/{b1['id']}")
    assert resp.get_json() == {"ok": True}
    _json_error(client.delete(f"/api/star/{b1['id']}"), 404)


def test_star_errors_and_draft_id_never_a_path(client, data_dir):
    _json_error(client.post("/api/star", json={"text": "lava", "line_no": 9, "lane": "all"}), 400)
    _json_error(client.post("/api/star", json={"text": "lava", "line_no": 1,
                                               "lane": "all", "tags": "x"}), 400)
    _json_error(client.post("/api/star", json={"text": "x" * (api.MAX_TEXT_CHARS + 1),
                                               "line_no": 1, "lane": "all"}), 413)
    resp = client.post("/api/star", json={"text": "lava pada\nglava stara", "line_no": 1,
                                          "lane": "drill", "tags": [],
                                          "draft_id": "../../evil/../../x"})
    assert resp.status_code == 200
    con = sqlite3.connect(str(data_dir / "mairina.db"))
    try:
        file_val = con.execute("SELECT file FROM stars").fetchone()[0]
    finally:
        con.close()
    assert file_val == "draft:../../evil/../../x"         # stored verbatim, never resolved


def test_hint_vote_cycle_and_errors(client):
    for _ in range(3):
        resp = client.post("/api/hint-vote", json={"rule_id": "cliche", "vote": -1})
    body = resp.get_json()
    assert set(body) == {"rule_id", "up", "down", "muted"}
    assert body == {"rule_id": "cliche", "up": 0, "down": 3, "muted": True}
    resp = client.post("/api/hint-vote", json={"rule_id": "cliche", "vote": 0})
    assert resp.get_json() == {"rule_id": "cliche", "up": 0, "down": 0, "muted": False}
    _json_error(client.post("/api/hint-vote", json={"rule_id": "bogus", "vote": 1}), 400)
    _json_error(client.post("/api/hint-vote", json={"rule_id": "cliche", "vote": 5}), 400)


def test_used_round_trip_and_idempotent_draft(client, data_dir):
    _make_list(client)                                    # rhyme 'lava' shows spava/glava
    resp = client.post("/api/used", json={"text": "glava je spava danas", "draft_id": "d7"})
    body = resp.get_json()
    assert set(body) == {"count", "hits"}
    assert body["count"] == len(body["hits"]) and body["count"] >= 2

    def used_rows() -> int:
        con = sqlite3.connect(str(data_dir / "mairina.db"))
        try:
            return con.execute("SELECT COUNT(*) FROM used").fetchone()[0]
        finally:
            con.close()

    n1 = used_rows()
    again = client.post("/api/used", json={"text": "glava je spava danas", "draft_id": "d7"})
    assert again.get_json() == body                       # same hits, stable draft id
    assert used_rows() == n1                              # and no new 'used' rows
    _json_error(client.post("/api/used", json={}), 400)


# --- stats / me / atlas ---------------------------------------------------------

def test_stats_exact_shape(client):
    _make_list(client)
    client.post("/api/used", json={"text": "glava je spava", "draft_id": "d1"})
    resp = client.get("/api/stats")
    body = resp.get_json()
    assert set(body) == {"votes", "up", "down", "up_rate", "used", "lists",
                       "arms", "ab", "muted"}
    assert body["lists"] >= 1 and isinstance(body["used"], int)
    assert set(body["arms"]) == {"learned", "base"}
    for a in body["arms"].values():
        assert set(a) == {"votes", "up_rate"}
    assert isinstance(body["ab"], str) and "not enough data" in body["ab"]
    assert body["muted"] == []


def test_me_exact_shape_and_lane_error(client, data_dir):
    for n in (1, 2, 3):
        client.post("/api/star", json={"text": VERSE, "line_no": n,
                                       "lane": "all", "tags": ["punchline"], "draft_id": "d1"})
    resp = client.get("/api/me?lane=drill")
    body = resp.get_json()
    assert set(body) == {"n", "low_confidence", "numeric", "tag_rates", "kind_rates"}
    assert body["n"] == 3 and body["low_confidence"] is True
    assert body["tag_rates"] == {"punchline": 1.0}
    for v in body["numeric"].values():
        assert set(v) == {"mean", "shrunk", "lane_mu", "lane_sigma"}
    _json_error(client.get("/api/me?lane=bogus"), 400)


ATLAS_ROW = {"scope", "lines", "simile", "anaphora", "allit", "internal",
             "code_switch", "name_drop", "multi_pct", "cons", "med_syl"}


def test_atlas_stats_only_and_exact_shape(client):
    resp = client.get("/api/atlas?lane=drill")
    body = resp.get_json()
    assert set(body) == {"lanes", "artists"}
    assert len(body["lanes"]) == 1 and body["lanes"][0]["scope"] == "lane drill"
    for r in body["lanes"] + body["artists"]:
        assert set(r) == ATLAS_ROW
    # stats only: no fixture line text may appear anywhere in the payload
    payload = json.dumps(body)
    assert "Da Ekipa" not in payload and "thelion" not in payload
    resp = client.get("/api/atlas?lane=all")
    assert len(resp.get_json()["lanes"]) == 3             # drill, pop, all
    _json_error(client.get("/api/atlas?lane=bogus"), 400)


# --- protocol-level errors --------------------------------------------------------

def test_malformed_json_unknown_route_and_method(client):
    resp = client.post("/api/xray", data="{not json", content_type="application/json")
    _json_error(resp, 400)
    _json_error(client.get("/api/does-not-exist"), 404)
    _json_error(client.get("/api/vote"), 405)
    _json_error(client.get("/api/star/not-a-number"), 404)


def test_corpus_down_app_still_serves(corpus_db, tmp_path):
    bare = tmp_path / "bare.db"
    shutil.copy(corpus_db, bare)
    con = sqlite3.connect(str(bare))
    con.execute("DELETE FROM tokens")
    con.commit()
    con.close()
    app = api.create_app(lyrics_db=bare, data_dir=tmp_path / "d")     # CorpusNotAnnotated
    c = app.test_client()
    _json_error(c.get("/api/atlas?lane=drill"), 503)
    r = c.post("/api/xray", json={"text": "lava pada", "lane": "all"})
    _json_error(r, 503)
    assert "CLASSLA" in r.get_json()["error"]
    _json_error(c.post("/api/anchors", json={"lane": "all"}), 503)
    assert c.get("/api/stats").status_code == 200                      # app db works anyway


def test_missing_db_still_serves_state_routes(tmp_path):
    app = api.create_app(lyrics_db=tmp_path / "gone" / "lyrics.db", data_dir=tmp_path / "d")
    c = app.test_client()
    _json_error(c.get("/api/compare?lane=drill"), 503)
    assert c.get("/api/stats").status_code == 200
    assert c.get("/api/stars").get_json() == {"items": []}
    resp = c.post("/api/star", json={"text": "lava pada", "line_no": 1, "lane": "all"})
    assert resp.status_code == 200                                     # degraded like the CLI


def test_non_localhost_bind_is_refused(tmp_path):
    app = api.create_app(lyrics_db=tmp_path / "gone.db", data_dir=tmp_path / "d")
    with pytest.raises(ValueError):
        api.serve(app, host="0.0.0.0")
    with pytest.raises(ValueError):
        api.serve(app, host="127.0.0.1", port=9000)


# --- invariants -------------------------------------------------------------------

def test_real_data_dir_untouched(client):
    before = _dir_state(DATA_DIR)
    client.post("/api/anchors", json={"scheme": "AAAA", "lines": 2, "lane": "all"})
    client.post("/api/xray", json={"text": VERSE, "lane": "drill"})
    client.post("/api/star", json={"text": VERSE, "line_no": 1, "lane": "all", "draft_id": "d"})
    client.get("/api/stats")
    assert _dir_state(DATA_DIR) == before


def test_corpus_db_is_read_only(client, corpus_db):
    st0 = corpus_db.stat()
    client.post("/api/rhyme", json={"word": "lava", "lane": "all"})
    client.post("/api/xray", json={"text": VERSE, "lane": "drill"})
    client.get("/api/atlas?lane=drill")
    client.get("/api/compare?lane=drill")
    st1 = corpus_db.stat()
    assert (st0.st_mtime_ns, st0.st_size) == (st1.st_mtime_ns, st1.st_size)
