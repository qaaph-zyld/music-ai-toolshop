"""Dialect filter (ekavica), persistent word bans, and written-line anchor flows.

Fixture notes (conftest): song 3 adds 'vreme' x6 + 'vrijeme' x6 — an ekavian /
ijekavian twin pair sharing rhyme class 'eme'. 'vrijeme' is a lexicon pair, so
the flag does not depend on frequencies. Rhyme class 'ava' holds the lemmas
lava / glava / spavati (form 'spava').
"""

from __future__ import annotations

import random
import sqlite3

import pytest

from mairina import anchors as anchors_mod, bans, dialect, rank
from mairina import api


@pytest.fixture()
def client(corpus_db, data_dir):
    app = api.create_app(lyrics_db=corpus_db, data_dir=data_dir)
    assert app.extensions["mairina"]["atlas"].wait(60)       # the atlas warms in the background
    return app.test_client()


def _words(resp):
    return [it["word"] for it in resp.get_json()["items"]]


# --- dialect detection ---------------------------------------------------------

def test_ijekavian_flags_fixture_twin(index):
    flagged = dialect.ijekavian(index.forms)
    assert "vrijeme" in flagged                    # lexicon pair vreme/vrijeme
    for ekav in ("vreme", "lava", "spava", "glava", "gazda", "pade", "nekad"):
        assert ekav not in flagged


def test_reason_is_explainable(index):
    r = dialect._reason("vrijeme", index.forms, frozenset({"vrijeme"}))
    assert r == "lexicon"
    assert dialect._reason("vreme", index.forms, frozenset()) is None


def test_ctx_vocab_applies_blocked(index):
    ctx = rank.Ctx(index, "all", 0.5, (), None, blocked=frozenset({"vrijeme"}))
    v = ctx.vocab()
    assert "vrijeme" not in v and "vreme" in v


# --- bans store -----------------------------------------------------------------

def _con(tmp_path):
    return sqlite3.connect(str(tmp_path / "mairina.db"))


def test_ban_roundtrip_and_idempotence(tmp_path):
    con = _con(tmp_path)
    assert bans.list_bans(con) == set()            # table does not exist yet
    assert bans.ban(con, " Volio ") == "volio"     # normalized
    assert bans.ban(con, "volio") == "volio"       # idempotent
    assert bans.list_bans(con) == {"volio"}
    assert bans.list_with_ts(con)[0]["word"] == "volio"
    assert bans.unban(con, "volio") is True
    assert bans.unban(con, "volio") is False       # already gone
    con.close()


def test_ban_rejects_bad_words(tmp_path):
    con = _con(tmp_path)
    for bad in ("", "   ", "dve reci", "x" * (bans.MAX_WORD_LEN + 1)):
        with pytest.raises(Exception):
            bans.ban(con, bad)
    con.close()


# --- anchors: seeds, locks, fallback, swap -------------------------------------

def test_seeded_group_keeps_lock_free_and_rhymes(index):
    res = anchors_mod.anchors(index, "AABB", 4, "all", "rhyme", None, 0.5, (),
                              random.Random(7), None,
                              group_seeds={"A": "spava"}, locked_lines=frozenset({1}))
    by_line = {a.line: a for a in res}
    assert sorted(by_line) == [2, 3, 4]            # the written row gets no pick
    assert by_line[2].key == "ava"                 # spava's own class
    assert by_line[2].word in {"lava", "glava"} and by_line[2].word != "spava"
    assert by_line[3].group == by_line[4].group == "B"


def test_thin_seed_falls_back_with_warning(index):
    warns = []
    res = anchors_mod.anchors(index, "AABB", 4, "all", "rhyme", None, 0.5, (),
                              random.Random(7), None,
                              group_seeds={"A": "gazda"}, locked_lines=frozenset({1}),
                              warnings=warns)
    assert warns and "gazda" in warns[0]           # 'azda' has no partners
    a2 = next(a for a in res if a.line == 2)
    assert a2.word != "gazda" and a2.key != "azda"


def test_all_lines_written_generates_nothing(index):
    res = anchors_mod.anchors(index, "AABB", 4, "all", "rhyme", None, 0.5, (),
                              random.Random(7), None,
                              group_seeds={"A": "spava", "B": "gazda"},
                              locked_lines=frozenset({1, 2, 3, 4}))
    assert res == []


def test_swap_same_class_and_exhaustion(index):
    a = anchors_mod.swap(index, "ava", "rhyme", "all", 0.5, (),
                         frozenset({"lava"}), random.Random(1))
    assert a is not None and a.key == "ava" and a.word in {"glava", "spava"}
    assert anchors_mod.swap(index, "ava", "rhyme", "all", 0.5, (),
                            frozenset({"lava", "glava", "spava"}), random.Random(1)) is None
    assert anchors_mod.swap(index, "ava", "rhyme", "all", 0.5, (),
                            frozenset({"lava"}), random.Random(1),
                            blocked=frozenset({"glava", "spava"})) is None


# --- API: dialect, bans, written -----------------------------------------------

def test_rhyme_dialect_toggle(client):
    payload = {"word": "vreme", "lane": "all", "dialect": "all"}
    assert "vrijeme" in _words(client.post("/api/rhyme", json=payload))
    payload["dialect"] = "ekavica"
    assert "vrijeme" not in _words(client.post("/api/rhyme", json=payload))
    assert "vreme" not in _words(client.post("/api/rhyme", json=payload))


def test_dialect_and_written_validation(client):
    r = client.post("/api/rhyme", json={"word": "lava", "dialect": "ijekavica"})
    assert r.status_code == 400 and "dialect" in r.get_json()["error"]
    r = client.post("/api/anchors", json={"written": "not-a-list"})
    assert r.status_code == 400
    r = client.post("/api/anchors", json={"written": ["x"] * 65})
    assert r.status_code == 413


def test_anchors_written_locks_and_seeds(client):
    resp = client.post("/api/anchors", json={
        "scheme": "AABB", "lines": 4, "lane": "all", "mode": "rhyme",
        "written": ["kad padne mrak svi spava", "", "", ""]})
    assert resp.status_code == 200
    items = resp.get_json()["items"]
    assert len(items) == 4 and [it["n"] for it in items] == [1, 2, 3, 4]
    first = items[0]
    assert first["word"] == "spava" and first.get("locked") is True
    assert first["group"] == "A" and first["cls"] == "ava"
    second = items[1]
    assert second["group"] == "A" and second["word"] in {"lava", "glava"}
    assert not second.get("locked")


def test_swap_endpoint(client):
    r = client.post("/api/anchors/swap", json={
        "cls": "ava", "mode": "rhyme", "lane": "all", "exclude": ["lava"]})
    assert r.status_code == 200
    body = r.get_json()
    assert body["item"]["word"] in {"glava", "spava"} and body["item"]["cls"] == "ava"
    r = client.post("/api/anchors/swap", json={
        "cls": "ava", "mode": "rhyme", "lane": "all",
        "exclude": ["lava", "glava", "spava"]})
    assert r.get_json()["item"] is None            # class exhausted
    r = client.post("/api/anchors/swap", json={"lane": "all"})
    assert r.status_code == 400                    # cls is required


def test_ban_endpoints_and_propagation(client):
    assert client.post("/api/ban", json={"word": "dve reci"}).status_code == 400
    r = client.post("/api/ban", json={"word": "Glava"})
    assert r.status_code == 200 and r.get_json()["word"] == "glava"
    bans_body = client.get("/api/bans").get_json()["items"]
    assert [b["word"] for b in bans_body] == ["glava"]
    payload = {"word": "lava", "lane": "all"}
    assert "glava" not in _words(client.post("/api/rhyme", json=payload))
    swap = client.post("/api/anchors/swap", json={
        "cls": "ava", "mode": "rhyme", "lane": "all", "exclude": ["lava"]})
    assert swap.get_json()["item"]["word"] == "spava"   # glava banned away
    assert client.delete("/api/ban/glava").status_code == 200
    assert client.delete("/api/ban/glava").status_code == 404   # not banned anymore
    assert "glava" in _words(client.post("/api/rhyme", json=payload))
