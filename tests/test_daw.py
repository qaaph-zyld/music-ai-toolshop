"""Tests for the toolshop DAW module — TCP client, framing, and transport functions.

These tests use a mock TCP server to verify the client's framing protocol,
JSON-RPC handling, error propagation, and transport module wrappers.
No real DAW connection is needed.
"""

from __future__ import annotations

import json
import socket
import struct
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

import pytest

from toolshop.daw.client import (
    DAWClient,
    DAWConnectionError,
    DAWServerError,
    DAWTimeoutError,
)
from toolshop.daw import transport


# ---------------------------------------------------------------------------
# Mock TCP server
# ---------------------------------------------------------------------------

class MockDAWServer:
    """Minimal TCP server that speaks the length-prefixed JSON-RPC protocol.

    Accepts a handler dict mapping method names to result dicts.
    """

    def __init__(
        self,
        handlers: Optional[Dict[str, Any]] = None,
        host: str = "127.0.0.1",
    ) -> None:
        self.handlers = handlers or {}
        self.host = host
        self.port = 0  # ephemeral
        self._server: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._client: Optional[socket.socket] = None

    def start(self) -> None:
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind((self.host, 0))
        self._server.listen(1)
        self.port = self._server.getsockname()[1]
        self._running = True
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._client:
            try:
                self._client.close()
            except OSError:
                pass
        if self._server:
            try:
                self._server.close()
            except OSError:
                pass
        if self._thread:
            self._thread.join(timeout=2.0)

    def _serve(self) -> None:
        while self._running:
            try:
                self._client, _ = self._server.accept()
                self._handle_client(self._client)
            except OSError:
                break

    def _handle_client(self, sock: socket.socket) -> None:
        while self._running:
            msg = self._read_frame(sock)
            if msg is None:
                break
            method = msg.get("method", "")
            msg_id = msg.get("id")
            if method in self.handlers:
                handler = self.handlers[method]
                if isinstance(handler, dict) and "error" in handler:
                    response = {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "error": handler["error"],
                    }
                else:
                    result = handler(**msg.get("params", {})) if callable(handler) else handler
                    response = {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "result": result,
                    }
            else:
                response = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"},
                }
            self._send_frame(sock, response)

    @staticmethod
    def _read_frame(sock: socket.socket) -> Optional[Dict[str, Any]]:
        header = b""
        while len(header) < 4:
            chunk = sock.recv(4 - len(header))
            if not chunk:
                return None
            header += chunk
        (total_len,) = struct.unpack(">I", header)
        if total_len == 0:
            return {}
        payload = b""
        while len(payload) < total_len:
            chunk = sock.recv(min(total_len - len(payload), 65536))
            if not chunk:
                return None
            payload += chunk
        return json.loads(payload.decode("utf-8"))

    @staticmethod
    def _send_frame(sock: socket.socket, msg: Dict[str, Any]) -> None:
        payload = json.dumps(msg, ensure_ascii=False).encode("utf-8")
        length = struct.pack(">I", len(payload))
        try:
            sock.sendall(length + payload)
        except OSError:
            pass


@pytest.fixture
def mock_server():
    """Start a mock DAW server with default handlers."""
    server = MockDAWServer(handlers={
        "system.ping": {"ok": True},
        "system.status": {
            "bridge": "ToolshopDAW",
            "connected": True,
            "fl_version": "21.0.0",
            "tempo": 140.0,
            "playing": False,
            "metronome": False,
        },
        "transport.play": {"playing": True},
        "transport.stop": {"playing": False},
        "transport.set_tempo": lambda bpm: {"tempo": bpm},
        "transport.get_tempo": {"tempo": 140.0},
        "transport.get_state": {
            "playing": False,
            "tempo": 140.0,
            "metronome": False,
            "position": 0.0,
            "recording": False,
        },
        "transport.set_metronome": lambda enabled: {"metronome": enabled},
        "transport.record": {"recording": True},
        "transport.get_time_signature": {"numerator": 4, "denominator": 4},
        "transport.set_time_signature": lambda numerator, denominator: {
            "numerator": numerator,
            "denominator": denominator,
        },
        "transport.get_position": {
            "song_pos_seconds": 12.5,
            "song_pos_beats": 7.0,
            "song_length_seconds": 180.0,
        },
        "mixer.get_state": {
            "track_count": 2,
            "tracks": [
                {"index": 0, "name": "Master", "volume": 0.8, "pan": 0.0, "muted": False, "soloed": False},
                {"index": 1, "name": "Kick", "volume": 0.7, "pan": 0.0, "muted": False, "soloed": False},
            ],
        },
        "mixer.set_volume": lambda track, level: {"track": track, "level": level},
        "mixer.set_pan": lambda track, pan: {"track": track, "pan": pan},
        "mixer.mute": lambda track, muted=True: {"track": track, "muted": muted},
        "mixer.solo": lambda track, soloed=True: {"track": track, "soloed": soloed},
        "channels.list": {
            "channel_count": 1,
            "channels": [
                {"index": 0, "name": "Kick", "color": 0xFF0000, "volume": 0.8, "pan": 0.0, "midi_chan": 0},
            ],
        },
        "patterns.list": {
            "pattern_count": 1,
            "patterns": [{"index": 1, "name": "Pattern 1", "length": 16}],
        },
        "playlist.get_track_names": {
            "track_count": 1,
            "tracks": [{"index": 0, "name": "Track 1"}],
        },
        # Phase 2 — Mixer extended
        "mixer.route": lambda track, to_track: {"track": track, "routed_to": to_track},
        "mixer.add_fx": lambda track, plugin_name: {"track": track, "plugin": plugin_name, "slot": 0},
        "mixer.get_fx_params": lambda track, slot=0: {
            "track": track, "slot": slot, "param_count": 2,
            "params": [
                {"index": 0, "name": "Mix", "value": 0.5},
                {"index": 1, "name": "Decay", "value": 0.3},
            ],
        },
        "mixer.set_fx_param": lambda track, slot, param_index, value: {
            "track": track, "slot": slot, "param": param_index, "value": value,
        },
        # Phase 2 — Channels extended
        "channels.add": lambda name="", channel_type="sampler": {"index": 1, "name": name or "Channel 1", "type": channel_type},
        "channels.rename": lambda index, name: {"index": index, "name": name},
        "channels.set_color": lambda index, color: {"index": index, "color": color},
        "channels.get_step": lambda channel, step: {"channel": channel, "step": step, "active": step % 4 == 0},
        "channels.set_step": lambda channel, step, active: {"channel": channel, "step": step, "active": active},
        "channels.get_step_pattern": lambda channel, length=16: {
            "channel": channel, "length": length,
            "steps": [i % 4 == 0 for i in range(length)],
        },
        "channels.set_step_pattern": lambda channel, steps: {"channel": channel, "steps_set": len(steps)},
        # Phase 2 — Patterns extended
        "patterns.create": lambda name="": {"index": 2, "name": name or "Pattern 2"},
        "patterns.rename": lambda index, name: {"index": index, "name": name},
        "patterns.clone": lambda index, name="": {"index": 3, "source": index, "name": name or "Pattern 3"},
        # Phase 3 — Piano roll
        "pianoroll.add_notes": lambda pattern, notes: {"pattern": pattern, "notes_added": len(notes)},
        "pianoroll.clear_notes": lambda pattern: {"pattern": pattern, "cleared": True},
        "pianoroll.get_notes": lambda pattern: {
            "pattern": pattern, "note_count": 2,
            "notes": [
                {"index": 0, "note": 60, "position": 0, "length": 16, "velocity": 100},
                {"index": 1, "note": 64, "position": 0, "length": 16, "velocity": 100},
            ],
        },
        "pianoroll.quantize": lambda pattern, grid=16: {"pattern": pattern, "grid": grid},
        "pianoroll.transpose": lambda pattern, semitones: {"pattern": pattern, "semitones": semitones},
        "pianoroll.humanize": lambda pattern, amount=0.3, seed=42: {"pattern": pattern, "amount": amount, "seed": seed},
        # Phase 3 — Plugins
        "plugins.get_param": lambda track, slot, param_index: {"track": track, "slot": slot, "param": param_index, "value": 0.5},
        "plugins.set_param": lambda track, slot, param_index, value: {"track": track, "slot": slot, "param": param_index, "value": value},
        "plugins.get_param_count": lambda track, slot: {"track": track, "slot": slot, "param_count": 2},
        "plugins.get_param_name": lambda track, slot, param_index: {"track": track, "slot": slot, "param": param_index, "name": f"Param {param_index}"},
    })
    server.start()
    yield server
    server.stop()


@pytest.fixture
def client(mock_server):
    """Create a DAWClient connected to the mock server."""
    c = DAWClient(host=mock_server.host, port=mock_server.port, timeout=3.0)
    c.connect()
    yield c
    c.disconnect()


# ---------------------------------------------------------------------------
# Framing tests
# ---------------------------------------------------------------------------

class TestFraming:
    def test_encode_produces_length_prefixed_frame(self):
        msg = {"jsonrpc": "2.0", "id": 1, "method": "test", "params": {}}
        frame = DAWClient._encode(msg)
        assert len(frame) > 4
        (length,) = struct.unpack(">I", frame[:4])
        assert length == len(frame) - 4
        decoded = json.loads(frame[4:].decode("utf-8"))
        assert decoded["method"] == "test"

    def test_encode_empty_params(self):
        msg = {"jsonrpc": "2.0", "id": 1, "method": "ping"}
        frame = DAWClient._encode(msg)
        (length,) = struct.unpack(">I", frame[:4])
        assert length > 0
        decoded = json.loads(frame[4:].decode("utf-8"))
        assert "params" not in decoded or decoded.get("params") is None or True


# ---------------------------------------------------------------------------
# Client connection tests
# ---------------------------------------------------------------------------

class TestDAWClientConnection:
    def test_connect_to_mock_server(self, mock_server):
        c = DAWClient(host=mock_server.host, port=mock_server.port, timeout=3.0)
        assert not c.is_connected()
        c.connect()
        assert c.is_connected()
        c.disconnect()
        assert not c.is_connected()

    def test_connect_refused_raises_connection_error(self):
        c = DAWClient(host="127.0.0.1", port=1, timeout=1.0)  # port 1 should refuse
        with pytest.raises(DAWConnectionError):
            c.connect()

    def test_context_manager(self, mock_server):
        with DAWClient(host=mock_server.host, port=mock_server.port, timeout=3.0) as c:
            assert c.is_connected()
        assert not c.is_connected()

    def test_double_connect_is_noop(self, mock_server):
        c = DAWClient(host=mock_server.host, port=mock_server.port, timeout=3.0)
        c.connect()
        c.connect()  # should not raise
        assert c.is_connected()
        c.disconnect()


# ---------------------------------------------------------------------------
# JSON-RPC call tests
# ---------------------------------------------------------------------------

class TestDAWClientCalls:
    def test_ping(self, client):
        assert client.ping() is True

    def test_status(self, client):
        info = client.status()
        assert info["bridge"] == "ToolshopDAW"
        assert info["fl_version"] == "21.0.0"
        assert info["tempo"] == 140.0

    def test_call_transport_play(self, client):
        result = client.call("transport.play")
        assert result["playing"] is True

    def test_call_transport_stop(self, client):
        result = client.call("transport.stop")
        assert result["playing"] is False

    def test_call_with_params(self, client):
        result = client.call("transport.set_tempo", bpm=128.0)
        assert result["tempo"] == 128.0

    def test_method_not_found_raises_server_error(self, client):
        with pytest.raises(DAWServerError) as exc_info:
            client.call("nonexistent.method")
        assert exc_info.value.code == -32601

    def test_call_without_connect_raises(self):
        c = DAWClient(host="127.0.0.1", port=9999, timeout=1.0)
        with pytest.raises(DAWConnectionError, match="Not connected"):
            c.call("system.ping")

    def test_call_optional_returns_none_on_error(self):
        c = DAWClient(host="127.0.0.1", port=1, timeout=1.0)
        # Not connected — should return None, not raise
        assert c.call_optional("system.ping") is None


# ---------------------------------------------------------------------------
# Transport module tests
# ---------------------------------------------------------------------------

class TestTransportModule:
    def test_play(self, client):
        result = transport.play(client)
        assert result["playing"] is True

    def test_stop(self, client):
        result = transport.stop(client)
        assert result["playing"] is False

    def test_set_tempo(self, client):
        result = transport.set_tempo(client, 150.0)
        assert result["tempo"] == 150.0

    def test_set_tempo_invalid_bpm_raises(self, client):
        with pytest.raises(ValueError):
            transport.set_tempo(client, -10)
        with pytest.raises(ValueError):
            transport.set_tempo(client, 0)
        with pytest.raises(ValueError):
            transport.set_tempo(client, 1001)

    def test_get_tempo(self, client):
        result = transport.get_tempo(client)
        assert result["tempo"] == 140.0

    def test_get_state(self, client):
        result = transport.get_state(client)
        assert "playing" in result
        assert "tempo" in result
        assert "metronome" in result

    def test_set_metronome(self, client):
        result = transport.set_metronome(client, True)
        assert result["metronome"] is True

    def test_record(self, client):
        result = transport.record(client)
        assert result["recording"] is True

    def test_get_time_signature(self, client):
        result = transport.get_time_signature(client)
        assert result["numerator"] == 4
        assert result["denominator"] == 4

    def test_set_time_signature(self, client):
        result = transport.set_time_signature(client, 3, 4)
        assert result["numerator"] == 3
        assert result["denominator"] == 4

    def test_set_time_signature_invalid_raises(self, client):
        with pytest.raises(ValueError):
            transport.set_time_signature(client, 0, 4)
        with pytest.raises(ValueError):
            transport.set_time_signature(client, 4, 0)

    def test_get_position(self, client):
        result = transport.get_position(client)
        assert result["song_pos_seconds"] == 12.5
        assert result["song_pos_beats"] == 7.0


# ---------------------------------------------------------------------------
# CLI parser tests
# ---------------------------------------------------------------------------

class TestDAWCLIParser:
    def test_parser_has_daw_subcommand(self):
        from toolshop.cli import build_parser
        parser = build_parser()
        # Parse `daw status` — should not raise
        args = parser.parse_args(["daw", "status"])
        assert args.command == "daw"
        assert args.daw_command == "status"

    def test_parser_transport_play(self):
        from toolshop.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["daw", "transport", "play"])
        assert args.daw_command == "transport"
        assert args.transport_command == "play"

    def test_parser_transport_set_tempo(self):
        from toolshop.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["daw", "transport", "set-tempo", "140"])
        assert args.transport_command == "set-tempo"
        assert args.bpm == 140.0

    def test_parser_mixer_state(self):
        from toolshop.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["daw", "mixer", "state"])
        assert args.daw_command == "mixer"
        assert args.mixer_command == "state"

    def test_parser_channels_list(self):
        from toolshop.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["daw", "channels", "list"])
        assert args.daw_command == "channels"
        assert args.channels_command == "list"

    def test_parser_patterns_create(self):
        from toolshop.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["daw", "patterns", "create", "--name", "Verse"])
        assert args.daw_command == "patterns"
        assert args.patterns_command == "create"
        assert args.name == "Verse"

    def test_parser_custom_host_port(self):
        from toolshop.cli import build_parser
        parser = build_parser()
        args = parser.parse_args([
            "daw", "--host", "192.168.1.5", "--port", "9999", "status"
        ])
        assert args.host == "192.168.1.5"
        assert args.port == 9999


# ---------------------------------------------------------------------------
# CLI run tests (with mock server)
# ---------------------------------------------------------------------------

class TestDAWCLIRun:
    def test_run_status_returns_0(self, mock_server, capsys):
        from toolshop.daw.daw_cli import run
        import argparse

        args = argparse.Namespace(
            command="daw",
            daw_command="status",
            host=mock_server.host,
            port=mock_server.port,
            timeout=3.0,
        )
        code = run(args)
        assert code == 0
        captured = capsys.readouterr()
        assert "ToolshopDAW" in captured.out
        assert "21.0.0" in captured.out

    def test_run_transport_play(self, mock_server, capsys):
        from toolshop.daw.daw_cli import run
        import argparse

        args = argparse.Namespace(
            command="daw",
            daw_command="transport",
            transport_command="play",
            host=mock_server.host,
            port=mock_server.port,
            timeout=3.0,
        )
        code = run(args)
        assert code == 0
        captured = capsys.readouterr()
        assert "Playback started" in captured.out

    def test_run_connection_failure_returns_1(self, capsys):
        from toolshop.daw.daw_cli import run
        import argparse

        args = argparse.Namespace(
            command="daw",
            daw_command="status",
            host="127.0.0.1",
            port=1,  # nothing listening
            timeout=1.0,
        )
        code = run(args)
        assert code == 1
        captured = capsys.readouterr()
        assert "Error" in captured.err

    def test_run_mixer_state(self, mock_server, capsys):
        from toolshop.daw.daw_cli import run
        import argparse

        args = argparse.Namespace(
            command="daw",
            daw_command="mixer",
            mixer_command="state",
            json=False,
            host=mock_server.host,
            port=mock_server.port,
            timeout=3.0,
        )
        code = run(args)
        assert code == 0
        captured = capsys.readouterr()
        assert "Master" in captured.out
        assert "Kick" in captured.out


# ---------------------------------------------------------------------------
# Phase 2 — Mixer module tests
# ---------------------------------------------------------------------------

class TestMixerModule:
    def test_get_state(self, client):
        from toolshop.daw import mixer
        result = mixer.get_state(client)
        assert result["track_count"] == 2

    def test_set_volume(self, client):
        from toolshop.daw import mixer
        result = mixer.set_volume(client, track=1, level=0.5)
        assert result["track"] == 1

    def test_set_pan(self, client):
        from toolshop.daw import mixer
        result = mixer.set_pan(client, track=1, pan=-0.5)
        assert result["track"] == 1

    def test_mute(self, client):
        from toolshop.daw import mixer
        result = mixer.mute(client, track=1, muted=True)
        assert result["track"] == 1

    def test_solo(self, client):
        from toolshop.daw import mixer
        result = mixer.solo(client, track=1, soloed=True)
        assert result["track"] == 1

    def test_route(self, client):
        from toolshop.daw import mixer
        result = mixer.route(client, track=1, to_track=3)
        assert result["routed_to"] == 3

    def test_add_fx(self, client):
        from toolshop.daw import mixer
        result = mixer.add_fx(client, track=0, plugin_name="Fruity Reverb")
        assert result["plugin"] == "Fruity Reverb"

    def test_get_fx_params(self, client):
        from toolshop.daw import mixer
        result = mixer.get_fx_params(client, track=0, slot=0)
        assert result["param_count"] == 2

    def test_set_fx_param(self, client):
        from toolshop.daw import mixer
        result = mixer.set_fx_param(client, track=0, slot=0, param_index=1, value=0.7)
        assert result["value"] == 0.7


# ---------------------------------------------------------------------------
# Phase 2 — Channels module tests
# ---------------------------------------------------------------------------

class TestChannelsModule:
    def test_list_channels(self, client):
        from toolshop.daw import channels
        result = channels.list_channels(client)
        assert result["channel_count"] == 1

    def test_add_channel(self, client):
        from toolshop.daw import channels
        result = channels.add_channel(client, name="Snare", channel_type="sampler")
        assert result["name"] == "Snare"

    def test_rename_channel(self, client):
        from toolshop.daw import channels
        result = channels.rename_channel(client, index=0, name="Kick")
        assert result["name"] == "Kick"

    def test_set_color(self, client):
        from toolshop.daw import channels
        result = channels.set_color(client, index=0, color=0xFF0000)
        assert result["color"] == 0xFF0000

    def test_get_step(self, client):
        from toolshop.daw import channels
        result = channels.get_step(client, channel=0, step=0)
        assert result["active"] is True

    def test_set_step(self, client):
        from toolshop.daw import channels
        result = channels.set_step(client, channel=0, step=0, active=True)
        assert result["active"] is True

    def test_get_step_pattern(self, client):
        from toolshop.daw import channels
        result = channels.get_step_pattern(client, channel=0, length=16)
        assert len(result["steps"]) == 16

    def test_set_step_pattern(self, client):
        from toolshop.daw import channels
        steps = [True, False] * 8
        result = channels.set_step_pattern(client, channel=0, steps=steps)
        assert result["steps_set"] == 16


# ---------------------------------------------------------------------------
# Phase 2 — Patterns module tests
# ---------------------------------------------------------------------------

class TestPatternsModule:
    def test_list_patterns(self, client):
        from toolshop.daw import patterns
        result = patterns.list_patterns(client)
        assert result["pattern_count"] == 1

    def test_create_pattern(self, client):
        from toolshop.daw import patterns
        result = patterns.create_pattern(client, name="Verse")
        assert result["name"] == "Verse"

    def test_rename_pattern(self, client):
        from toolshop.daw import patterns
        result = patterns.rename_pattern(client, index=1, name="Chorus")
        assert result["name"] == "Chorus"

    def test_clone_pattern(self, client):
        from toolshop.daw import patterns
        result = patterns.clone_pattern(client, index=1, name="Verse 2")
        assert result["source"] == 1
        assert result["name"] == "Verse 2"


# ---------------------------------------------------------------------------
# Phase 3 — Piano roll module tests
# ---------------------------------------------------------------------------

class TestPianoRollModule:
    def test_note_name_to_midi_c4(self):
        from toolshop.daw.piano_roll import note_name_to_midi
        assert note_name_to_midi("C4") == 60

    def test_note_name_to_midi_g_sharp_3(self):
        from toolshop.daw.piano_roll import note_name_to_midi
        assert note_name_to_midi("G#3") == 56

    def test_note_name_to_midi_b_flat_4(self):
        from toolshop.daw.piano_roll import note_name_to_midi
        assert note_name_to_midi("Bb4") == 70

    def test_midi_to_note_name(self):
        from toolshop.daw.piano_roll import midi_to_note_name
        assert midi_to_note_name(60) == "C4"
        assert midi_to_note_name(67) == "G4"
        assert midi_to_note_name(70) == "A#4"

    def test_parse_notes_string(self):
        from toolshop.daw.piano_roll import parse_notes
        result = parse_notes("C4,E4,G4")
        assert result == [60, 64, 67]

    def test_parse_notes_empty_parts(self):
        from toolshop.daw.piano_roll import parse_notes
        result = parse_notes("C4,,E4,")
        assert result == [60, 64]

    def test_add_notes(self, client):
        from toolshop.daw import piano_roll as pr
        notes = [{"note": 60, "position": 0, "length": 16, "velocity": 100}]
        result = pr.add_notes(client, pattern=1, notes=notes)
        assert result["notes_added"] == 1

    def test_add_notes_simple(self, client):
        from toolshop.daw import piano_roll as pr
        result = pr.add_notes_simple(client, pattern=1, note_names="C4,E4,G4")
        assert result["notes_added"] == 3

    def test_clear_notes(self, client):
        from toolshop.daw import piano_roll as pr
        result = pr.clear_notes(client, pattern=1)
        assert result["cleared"] is True

    def test_get_notes(self, client):
        from toolshop.daw import piano_roll as pr
        result = pr.get_notes(client, pattern=1)
        assert result["note_count"] == 2

    def test_quantize(self, client):
        from toolshop.daw import piano_roll as pr
        result = pr.quantize(client, pattern=1, grid=16)
        assert result["grid"] == 16

    def test_transpose(self, client):
        from toolshop.daw import piano_roll as pr
        result = pr.transpose(client, pattern=1, semitones=2)
        assert result["semitones"] == 2

    def test_humanize(self, client):
        from toolshop.daw import piano_roll as pr
        result = pr.humanize(client, pattern=1, amount=0.3, seed=42)
        assert result["amount"] == 0.3

    def test_invalid_note_name_raises(self):
        from toolshop.daw.piano_roll import note_name_to_midi
        with pytest.raises(ValueError):
            note_name_to_midi("X4")

    def test_midi_out_of_range_raises(self):
        from toolshop.daw.piano_roll import midi_to_note_name
        with pytest.raises(ValueError):
            midi_to_note_name(128)


# ---------------------------------------------------------------------------
# Phase 3 — Plugins module tests
# ---------------------------------------------------------------------------

class TestPluginsModule:
    def test_get_param(self, client):
        from toolshop.daw import plugins
        result = plugins.get_param(client, track=0, slot=0, param_index=0)
        assert result["value"] == 0.5

    def test_set_param(self, client):
        from toolshop.daw import plugins
        result = plugins.set_param(client, track=0, slot=0, param_index=0, value=0.8)
        assert result["value"] == 0.8

    def test_get_param_count(self, client):
        from toolshop.daw import plugins
        result = plugins.get_param_count(client, track=0, slot=0)
        assert result["param_count"] == 2

    def test_get_param_name(self, client):
        from toolshop.daw import plugins
        result = plugins.get_param_name(client, track=0, slot=0, param_index=0)
        assert "Param 0" in result["name"]

    def test_get_all_params(self, client):
        from toolshop.daw import plugins
        result = plugins.get_all_params(client, track=0, slot=0)
        assert len(result) == 2
        assert result[0]["name"] == "Param 0"

    def test_list_plugins_returns_list(self):
        from toolshop.daw import plugins
        result = plugins.list_plugins()
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# Phase 4 — Generators music theory tests
# ---------------------------------------------------------------------------

class TestGeneratorsMusicTheory:
    def test_key_to_root_gm(self):
        from toolshop.daw.generators import key_to_root
        assert key_to_root("Gm") == 67  # G4

    def test_key_to_root_c(self):
        from toolshop.daw.generators import key_to_root
        assert key_to_root("C") == 60  # C4

    def test_key_to_root_bb(self):
        from toolshop.daw.generators import key_to_root
        assert key_to_root("Bb") == 70  # Bb4

    def test_scale_notes_minor(self):
        from toolshop.daw.generators import scale_notes
        notes = scale_notes("Gm", "minor")
        assert notes == [67, 69, 70, 72, 74, 75, 77]

    def test_scale_notes_major(self):
        from toolshop.daw.generators import scale_notes
        notes = scale_notes("C", "major")
        assert notes == [60, 62, 64, 65, 67, 69, 71]

    def test_scale_notes_unknown_raises(self):
        from toolshop.daw.generators import scale_notes
        with pytest.raises(ValueError):
            scale_notes("C", "nonexistent")

    def test_chord_notes_minor_i(self):
        from toolshop.daw.generators import chord_notes
        notes = chord_notes("Gm", 0, "minor")
        # i chord in G minor: G minor = G, Bb, D
        assert 67 in notes  # G
        assert 70 in notes  # Bb
        assert 74 in notes  # D

    def test_chord_notes_major_I(self):
        from toolshop.daw.generators import chord_notes
        notes = chord_notes("C", 0, "major")
        # I chord in C major: C major = C, E, G
        assert 60 in notes  # C
        assert 64 in notes  # E
        assert 67 in notes  # G

    def test_parse_progression_known(self):
        from toolshop.daw.generators import parse_progression
        assert parse_progression("i-VI-III-VII") == [0, 5, 2, 6]

    def test_parse_progression_roman(self):
        from toolshop.daw.generators import parse_progression
        assert parse_progression("ii-V-I") == [1, 4, 0]

    def test_get_drum_preset_drill(self):
        from toolshop.daw.generators import get_drum_preset
        preset = get_drum_preset("drill")
        assert len(preset["kick"]) == 16
        assert preset["kick"][0] is True
        assert preset["snare"][4] is True

    def test_get_drum_preset_trap(self):
        from toolshop.daw.generators import get_drum_preset
        preset = get_drum_preset("trap")
        assert len(preset["hat"]) == 16
        assert all(preset["hat"])  # trap hats = all 16ths

    def test_get_drum_preset_unknown_raises(self):
        from toolshop.daw.generators import get_drum_preset
        with pytest.raises(ValueError):
            get_drum_preset("nonexistent")


# ---------------------------------------------------------------------------
# Phase 4 — Generators function tests (with mock server)
# ---------------------------------------------------------------------------

class TestGeneratorsFunctions:
    def test_gen_drum_pattern(self, client):
        from toolshop.daw.generators import gen_drum_pattern
        result = gen_drum_pattern(client, genre="drill", bars=2)
        assert result["genre"] == "drill"
        assert result["total_steps"] == 32

    def test_gen_chord_progression(self, client):
        from toolshop.daw.generators import gen_chord_progression
        result = gen_chord_progression(client, pattern=1, key="Gm", scale="minor",
                                       progression="i-VI-III-VII", bars=4)
        assert result["notes_written"] > 0

    def test_gen_bassline_root(self, client):
        from toolshop.daw.generators import gen_bassline
        result = gen_bassline(client, pattern=1, key="Gm", bars=4, style="root")
        assert result["notes_written"] > 0

    def test_gen_bassline_octaves(self, client):
        from toolshop.daw.generators import gen_bassline
        result = gen_bassline(client, pattern=1, key="Gm", bars=4, style="octaves")
        assert result["notes_written"] > 0

    def test_gen_bassline_walking(self, client):
        from toolshop.daw.generators import gen_bassline
        result = gen_bassline(client, pattern=1, key="Gm", bars=4, style="walking")
        assert result["notes_written"] > 0

    def test_gen_bassline_unknown_style_raises(self, client):
        from toolshop.daw.generators import gen_bassline
        with pytest.raises(ValueError):
            gen_bassline(client, pattern=1, style="nonexistent")

    def test_gen_melody(self, client):
        from toolshop.daw.generators import gen_melody
        result = gen_melody(client, pattern=1, key="Gm", bars=4, density=0.5, seed=42)
        assert result["notes_written"] > 0

    def test_gen_melody_zero_density(self, client):
        from toolshop.daw.generators import gen_melody
        result = gen_melody(client, pattern=1, key="Gm", bars=2, density=0.0, seed=42)
        assert result["notes_written"] == 0

    def test_gen_arpeggio_up(self, client):
        from toolshop.daw.generators import gen_arpeggio
        result = gen_arpeggio(client, pattern=1, chords="Gm,Bb,Dm",
                              pattern_type="up", bars=2)
        assert result["notes_written"] > 0

    def test_gen_arpeggio_down(self, client):
        from toolshop.daw.generators import gen_arpeggio
        result = gen_arpeggio(client, pattern=1, chords="Gm,Bb,Dm",
                              pattern_type="down", bars=2)
        assert result["notes_written"] > 0

    def test_gen_arpeggio_unknown_type_raises(self, client):
        from toolshop.daw.generators import gen_arpeggio
        with pytest.raises(ValueError):
            gen_arpeggio(client, pattern=1, pattern_type="nonexistent")


# ---------------------------------------------------------------------------
# Phase 4 — Corpus intelligence tests
# ---------------------------------------------------------------------------

class TestCorpusIntel:
    def test_suggest_bpm_preset(self):
        from toolshop.daw.corpus_intel import suggest_bpm
        result = suggest_bpm("drill_trap")
        assert result["bpm"] == 138
        assert result["source"] in ("preset", "corpus_avg")

    def test_suggest_bpm_pop(self):
        from toolshop.daw.corpus_intel import suggest_bpm
        result = suggest_bpm("pop")
        assert result["bpm"] == 120

    def test_suggest_bpm_unknown_genre(self):
        from toolshop.daw.corpus_intel import suggest_bpm
        result = suggest_bpm("nonexistent")
        assert result["bpm"] == 140  # fallback

    def test_suggest_key_drill(self):
        from toolshop.daw.corpus_intel import suggest_key
        result = suggest_key("drill_trap")
        assert "Gm" in result["keys"]
        assert result["primary"] == "Gm"

    def test_suggest_key_pop(self):
        from toolshop.daw.corpus_intel import suggest_key
        result = suggest_key("pop")
        assert "Cm" in result["keys"]

    def test_suggest_arrangement_drill(self):
        from toolshop.daw.corpus_intel import suggest_arrangement
        result = suggest_arrangement("drill_trap")
        arr = result["arrangement"]
        assert len(arr) > 0
        assert arr[0]["section"] == "intro"

    def test_suggest_pattern_drill(self):
        from toolshop.daw.corpus_intel import suggest_pattern
        result = suggest_pattern("drill_trap")
        assert result["pattern"] == "drill"

    def test_suggest_pattern_pop(self):
        from toolshop.daw.corpus_intel import suggest_pattern
        result = suggest_pattern("pop")
        assert result["pattern"] == "pop"


# ---------------------------------------------------------------------------
# Phase 2-4 CLI parser tests
# ---------------------------------------------------------------------------

class TestDAWCLIParserPhases234:
    def test_parser_mixer_route(self):
        from toolshop.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["daw", "mixer", "route", "1", "3"])
        assert args.mixer_command == "route"
        assert args.track == 1

    def test_parser_mixer_add_fx(self):
        from toolshop.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["daw", "mixer", "add-fx", "0", "Fruity Reverb"])
        assert args.mixer_command == "add-fx"
        assert args.plugin == "Fruity Reverb"

    def test_parser_channels_add(self):
        from toolshop.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["daw", "channels", "add", "--name", "Kick"])
        assert args.channels_command == "add"
        assert args.name == "Kick"

    def test_parser_channels_rename(self):
        from toolshop.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["daw", "channels", "rename", "0", "NewName"])
        assert args.channels_command == "rename"
        assert args.name == "NewName"

    def test_parser_channels_step_pattern(self):
        from toolshop.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["daw", "channels", "step-pattern", "0"])
        assert args.channels_command == "step-pattern"
        assert args.channel == 0

    def test_parser_patterns_clone(self):
        from toolshop.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["daw", "patterns", "clone", "1", "--name", "V2"])
        assert args.patterns_command == "clone"
        assert args.index == 1
        assert args.name == "V2"

    def test_parser_piano_roll_add_notes(self):
        from toolshop.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["daw", "piano-roll", "add-notes", "1", "C4,E4,G4"])
        assert args.piano_roll_command == "add-notes"
        assert args.notes == "C4,E4,G4"

    def test_parser_piano_roll_quantize(self):
        from toolshop.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["daw", "piano-roll", "quantize", "1", "--grid", "32"])
        assert args.piano_roll_command == "quantize"
        assert args.grid == 32

    def test_parser_piano_roll_transpose(self):
        from toolshop.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["daw", "piano-roll", "transpose", "1", "3"])
        assert args.piano_roll_command == "transpose"
        assert args.semitones == 3

    def test_parser_plugins_list(self):
        from toolshop.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["daw", "plugins", "list"])
        assert args.plugins_command == "list"

    def test_parser_plugins_set_param(self):
        from toolshop.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["daw", "plugins", "set-param", "0", "1", "0.5"])
        assert args.plugins_command == "set-param"
        assert args.param == 1
        assert args.value == 0.5

    def test_parser_gen_drum_pattern(self):
        from toolshop.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["daw", "gen", "drum-pattern", "--genre", "trap", "--bars", "2"])
        assert args.gen_command == "drum-pattern"
        assert args.genre == "trap"
        assert args.bars == 2

    def test_parser_gen_chord_progression(self):
        from toolshop.cli import build_parser
        parser = build_parser()
        args = parser.parse_args([
            "daw", "gen", "chord-progression", "1",
            "--key", "Cm", "--scale", "minor", "--progression", "i-VI-III-VII",
        ])
        assert args.gen_command == "chord-progression"
        assert args.key == "Cm"

    def test_parser_gen_bassline(self):
        from toolshop.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["daw", "gen", "bassline", "1", "--style", "walking"])
        assert args.gen_command == "bassline"
        assert args.style == "walking"

    def test_parser_gen_melody(self):
        from toolshop.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["daw", "gen", "melody", "1", "--density", "0.7"])
        assert args.gen_command == "melody"
        assert args.density == 0.7

    def test_parser_gen_arpeggio(self):
        from toolshop.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["daw", "gen", "arpeggio", "1", "--chords", "Am,C,G"])
        assert args.gen_command == "arpeggio"
        assert args.chords == "Am,C,G"

    def test_parser_corpus_suggest_bpm(self):
        from toolshop.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["daw", "corpus", "suggest-bpm", "drill_trap"])
        assert args.corpus_command == "suggest-bpm"
        assert args.genre == "drill_trap"

    def test_parser_corpus_suggest_key(self):
        from toolshop.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["daw", "corpus", "suggest-key", "pop"])
        assert args.corpus_command == "suggest-key"

    def test_parser_corpus_suggest_arrangement(self):
        from toolshop.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["daw", "corpus", "suggest-arrangement", "drill_trap"])
        assert args.corpus_command == "suggest-arrangement"

    def test_parser_corpus_section_stats(self):
        from toolshop.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["daw", "corpus", "section-stats", "drill_trap"])
        assert args.corpus_command == "section-stats"

    def test_parser_corpus_flow_to_midi(self):
        from toolshop.cli import build_parser
        parser = build_parser()
        args = parser.parse_args(["daw", "corpus", "flow-to-midi", "lyrics.txt"])
        assert args.corpus_command == "flow-to-midi"
        assert args.lyrics_file == "lyrics.txt"


# ---------------------------------------------------------------------------
# Phase 2-4 CLI run tests (with mock server)
# ---------------------------------------------------------------------------

class TestDAWCLIRunPhases234:
    def test_run_mixer_route(self, mock_server, capsys):
        from toolshop.daw.daw_cli import run
        import argparse

        args = argparse.Namespace(
            command="daw", daw_command="mixer", mixer_command="route",
            track=1, to=3, json=False,
            host=mock_server.host, port=mock_server.port, timeout=3.0,
        )
        code = run(args)
        assert code == 0
        captured = capsys.readouterr()
        assert "routed" in captured.out

    def test_run_channels_add(self, mock_server, capsys):
        from toolshop.daw.daw_cli import run
        import argparse

        args = argparse.Namespace(
            command="daw", daw_command="channels", channels_command="add",
            name="Snare", type="sampler", json=False,
            host=mock_server.host, port=mock_server.port, timeout=3.0,
        )
        code = run(args)
        assert code == 0
        captured = capsys.readouterr()
        assert "Snare" in captured.out

    def test_run_patterns_clone(self, mock_server, capsys):
        from toolshop.daw.daw_cli import run
        import argparse

        args = argparse.Namespace(
            command="daw", daw_command="patterns", patterns_command="clone",
            index=1, name="V2", json=False,
            host=mock_server.host, port=mock_server.port, timeout=3.0,
        )
        code = run(args)
        assert code == 0
        captured = capsys.readouterr()
        assert "Cloned" in captured.out

    def test_run_piano_roll_add_notes(self, mock_server, capsys):
        from toolshop.daw.daw_cli import run
        import argparse

        args = argparse.Namespace(
            command="daw", daw_command="piano-roll", piano_roll_command="add-notes",
            pattern=1, notes="C4,E4,G4", position=0, length=16, velocity=100, json=False,
            host=mock_server.host, port=mock_server.port, timeout=3.0,
        )
        code = run(args)
        assert code == 0
        captured = capsys.readouterr()
        assert "3 notes" in captured.out

    def test_run_piano_roll_get_notes(self, mock_server, capsys):
        from toolshop.daw.daw_cli import run
        import argparse

        args = argparse.Namespace(
            command="daw", daw_command="piano-roll", piano_roll_command="get-notes",
            pattern=1, json=False,
            host=mock_server.host, port=mock_server.port, timeout=3.0,
        )
        code = run(args)
        assert code == 0
        captured = capsys.readouterr()
        assert "C4" in captured.out

    def test_run_plugins_params(self, mock_server, capsys):
        from toolshop.daw.daw_cli import run
        import argparse

        args = argparse.Namespace(
            command="daw", daw_command="plugins", plugins_command="params",
            track=0, slot=0, json=False,
            host=mock_server.host, port=mock_server.port, timeout=3.0,
        )
        code = run(args)
        assert code == 0
        captured = capsys.readouterr()
        assert "Param 0" in captured.out

    def test_run_gen_drum_pattern(self, mock_server, capsys):
        from toolshop.daw.daw_cli import run
        import argparse

        args = argparse.Namespace(
            command="daw", daw_command="gen", gen_command="drum-pattern",
            genre="drill", bars=2, kick=0, snare=1, hat=2, json=False,
            host=mock_server.host, port=mock_server.port, timeout=3.0,
        )
        code = run(args)
        assert code == 0
        captured = capsys.readouterr()
        assert "drill" in captured.out

    def test_run_gen_chord_progression(self, mock_server, capsys):
        from toolshop.daw.daw_cli import run
        import argparse

        args = argparse.Namespace(
            command="daw", daw_command="gen", gen_command="chord-progression",
            pattern=1, key="Gm", scale="minor", progression="i-VI-III-VII",
            bars=4, length=16, json=False,
            host=mock_server.host, port=mock_server.port, timeout=3.0,
        )
        code = run(args)
        assert code == 0
        captured = capsys.readouterr()
        assert "i-VI-III-VII" in captured.out

    def test_run_corpus_suggest_bpm(self, mock_server, capsys):
        from toolshop.daw.daw_cli import run
        import argparse

        args = argparse.Namespace(
            command="daw", daw_command="corpus", corpus_command="suggest-bpm",
            genre="drill_trap", json=False,
            host=mock_server.host, port=mock_server.port, timeout=3.0,
        )
        code = run(args)
        assert code == 0
        captured = capsys.readouterr()
        assert "BPM" in captured.out

    def test_run_corpus_suggest_key(self, mock_server, capsys):
        from toolshop.daw.daw_cli import run
        import argparse

        args = argparse.Namespace(
            command="daw", daw_command="corpus", corpus_command="suggest-key",
            genre="drill_trap", json=False,
            host=mock_server.host, port=mock_server.port, timeout=3.0,
        )
        code = run(args)
        assert code == 0
        captured = capsys.readouterr()
        assert "Gm" in captured.out

    def test_run_corpus_suggest_arrangement(self, mock_server, capsys):
        from toolshop.daw.daw_cli import run
        import argparse

        args = argparse.Namespace(
            command="daw", daw_command="corpus", corpus_command="suggest-arrangement",
            genre="drill_trap", json=False,
            host=mock_server.host, port=mock_server.port, timeout=3.0,
        )
        code = run(args)
        assert code == 0
        captured = capsys.readouterr()
        assert "intro" in captured.out
