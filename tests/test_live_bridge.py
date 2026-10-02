"""Tests for the Ableton Live Remote Script bridge (port 9878).

No Ableton needed: ``live_bridge_script`` stubs ``ControlSurface`` when
_Framework is absent, and tests inject a fake ``c_instance.song()`` tree plus
monkeypatch ``LIVE_API_AVAILABLE`` to exercise handlers and the TCP roundtrip.
"""

from __future__ import annotations

import json
import socket
import struct
import time

import pytest

from toolshop.daw import live_bridge_script as lb
from toolshop.daw.client import DAWClient, DAWServerError


# ---------------------------------------------------------------------------
# Fake Live object tree
# ---------------------------------------------------------------------------

class FakeParam:
    def __init__(self, name, value=0.5, min_=0.0, max_=1.0):
        self.name = name
        self.value = value
        self.min = min_
        self.max = max_
        self.is_enabled = True


class FakeDevice:
    def __init__(self, name, params):
        self.name = name
        self.class_name = "PluginDevice"
        self.parameters = params


class FakeMixer:
    def __init__(self):
        self.volume = FakeParam("Volume", 0.85)
        self.panning = FakeParam("Pan", 0.0, -1.0, 1.0)


class FakeClipSlot:
    def __init__(self, name=None):
        self.has_clip = name is not None
        self.clip = type("C", (), {"name": name})() if name else None
        self.is_playing = False
        self.fired = False

    def fire(self):
        self.fired = True


class FakeTrack:
    def __init__(self, name, devices=None, clip_names=()):
        self.name = name
        self.mixer_device = FakeMixer()
        self.mute = False
        self.solo = False
        self.arm = False
        self.devices = devices or []
        self.clip_slots = [FakeClipSlot(n) for n in clip_names]
        self._stopped = False

    def stop_all_clips(self):
        self._stopped = True


class FakeScene:
    def __init__(self, name):
        self.name = name
        self.fired = False

    def fire(self):
        self.fired = True


class FakeSong:
    def __init__(self):
        self.tempo = 120.0
        self.is_playing = False
        self.record_mode = False
        self.metronome = False
        self.current_song_time = 0.0
        self.song_length = 300.0
        self.loop_start = 0.0
        self.loop_length = 16.0
        self.signature_numerator = 4
        self.signature_denominator = 4
        self.tracks = [
            FakeTrack("Drums", devices=[
                FakeDevice("Pro-Q 3", [FakeParam("Gain", 0.5),
                                       FakeParam("Freq", 0.7)]),
            ], clip_names=["beat A", None]),
            FakeTrack("Bass"),
        ]
        self.scenes = [FakeScene("Intro"), FakeScene("Drop")]

    def start_playing(self):
        self.is_playing = True

    def stop_playing(self):
        self.is_playing = False


class FakeCInstance:
    def __init__(self, song):
        self._song = song

    def song(self):
        return self._song


@pytest.fixture
def bridge(monkeypatch):
    monkeypatch.setattr(lb, "LIVE_API_AVAILABLE", True)
    song = FakeSong()
    b = lb.ToolshopLive(FakeCInstance(song))
    yield b, song


# ---------------------------------------------------------------------------
# Dispatch-level tests (no sockets)
# ---------------------------------------------------------------------------

def test_ping(bridge):
    b, _ = bridge
    resp = b._dispatch("system.ping", {}, 1)
    assert resp == {"jsonrpc": "2.0", "id": 1, "result": {"ok": True}}


def test_unknown_method_error(bridge):
    b, _ = bridge
    resp = b._dispatch("bogus.nope", {}, 7)
    assert resp["error"]["code"] == -32601
    assert resp["id"] == 7


def test_status_reports_song_state(bridge):
    b, song = bridge
    resp = b._dispatch("system.status", {}, 2)
    r = resp["result"]
    assert r["bridge"] == "ToolshopLive"
    assert r["tempo"] == 120.0
    assert r["track_count"] == 2
    assert r["scene_count"] == 2


def test_transport_play_stop(bridge):
    b, song = bridge
    b._dispatch("transport.play", {}, 1)
    assert song.is_playing is True
    b._dispatch("transport.stop", {}, 2)
    assert song.is_playing is False


def test_tempo_roundtrip(bridge):
    b, song = bridge
    b._dispatch("transport.set_tempo", {"bpm": 174.0}, 1)
    assert song.tempo == 174.0
    resp = b._dispatch("transport.get_tempo", {}, 2)
    assert resp["result"]["tempo"] == 174.0


def test_mixer_volume_clamped(bridge):
    b, _ = bridge
    resp = b._dispatch("mixer.set_volume", {"track": 0, "level": 1.4}, 1)
    assert resp["result"]["volume"] == 1.0  # clamped


def test_track_index_out_of_range_is_error(bridge):
    b, _ = bridge
    resp = b._dispatch("mixer.mute", {"track": 9}, 1)
    assert resp["error"]["code"] == -32000
    assert "out of range" in resp["error"]["message"]


def test_devices_list_and_params(bridge):
    b, _ = bridge
    resp = b._dispatch("devices.list", {"track": 0}, 1)
    devs = resp["result"]["devices"]
    assert devs[0]["name"] == "Pro-Q 3"
    assert devs[0]["param_count"] == 2

    resp = b._dispatch("devices.get_params", {"track": 0, "device": 0}, 2)
    names = [p["name"] for p in resp["result"]["params"]]
    assert names == ["Gain", "Freq"]


def test_devices_set_param_by_name_and_index(bridge):
    b, song = bridge
    resp = b._dispatch("devices.set_param",
                       {"track": 0, "device": 0,
                        "param_name": "gain", "value": 0.9}, 1)
    assert resp["result"]["value"] == 0.9
    assert song.tracks[0].devices[0].parameters[0].value == 0.9

    resp = b._dispatch("devices.set_param",
                       {"track": 0, "device": 0,
                        "param_index": 1, "value": 5.0}, 2)
    assert resp["result"]["value"] == 1.0  # clamped to max


def test_devices_set_param_unknown_name(bridge):
    b, _ = bridge
    resp = b._dispatch("devices.set_param",
                       {"track": 0, "device": 0,
                        "param_name": "nope", "value": 0.5}, 1)
    assert resp["error"]["code"] == -32000


def test_scenes_and_clips(bridge):
    b, song = bridge
    b._dispatch("scenes.fire", {"index": 1}, 1)
    assert song.scenes[1].fired is True

    resp = b._dispatch("clips.list", {"track": 0}, 2)
    slots = resp["result"]["clip_slots"]
    assert slots[0]["has_clip"] and slots[0]["name"] == "beat A"
    assert not slots[1]["has_clip"]

    b._dispatch("clips.fire", {"track": 0, "slot": 0}, 3)
    assert song.tracks[0].clip_slots[0].fired is True

    b._dispatch("clips.stop", {"track": 0}, 4)
    assert song.tracks[0]._stopped is True


def test_fl_compat_aliases(bridge):
    b, _ = bridge
    resp = b._dispatch("mixer.get_fx_params", {"track": 0, "slot": 0}, 1)
    assert resp["result"]["param_count"] == 2
    assert resp["result"]["slot"] == 0

    resp = b._dispatch("plugins.get_param_count", {"track": 0, "slot": 0}, 2)
    assert resp["result"]["param_count"] == 2

    resp = b._dispatch("plugins.set_param",
                       {"track": 0, "slot": 0, "param": 0, "value": 0.3}, 3)
    assert resp["result"]["value"] == 0.3


# ---------------------------------------------------------------------------
# TCP roundtrip — real DAWClient against a live bridge instance
# ---------------------------------------------------------------------------

def test_tcp_roundtrip(bridge, monkeypatch):
    b, song = bridge
    monkeypatch.setattr(lb, "PORT", 0)  # ephemeral
    b._running = True
    b._start_server()
    port = b._server_sock.getsockname()[1]
    try:
        client = DAWClient(port=port, timeout=5.0)
        client.connect()
        try:
            assert client.ping()
            assert client.call("transport.get_tempo")["tempo"] == 120.0
            client.call("transport.set_tempo", bpm=140.0)
            assert song.tempo == 140.0
            with pytest.raises(DAWServerError) as ei:
                client.call("bogus.method")
            assert ei.value.code == -32601
        finally:
            client.disconnect()
    finally:
        b.disconnect()
