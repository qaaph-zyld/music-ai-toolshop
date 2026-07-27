"""FL Studio MIDI device script — TCP bridge server.

This script runs *inside* FL Studio's Python runtime as a MIDI controller
script.  It opens a TCP server on 127.0.0.1:9876, receives JSON-RPC commands
from the toolshop DAW client, and dispatches them to FL Studio's built-in
Python API modules (``transport``, ``mixer``, ``channels``, ``patterns``,
``playlist``, ``plugins``).

Installation
------------
1. Copy this file to::

       %USERPROFILE%\Documents\Image-Line\FL Studio\Settings\Hardware\ToolshopDAW\device_ToolshopDAW.py

2. In FL Studio: Options → MIDI Settings → Input → pick any device row →
   set **Controller type** = ``ToolshopDAW`` → click **Enable**.

3. The script auto-starts the TCP server on init.  You should see
   ``[ToolshopDAW] TCP server listening on 127.0.0.1:9876`` in the Script
   output console (View → Script).

Threading model
---------------
- TCP ``accept()`` loop runs on a background thread started in ``OnInit()``.
- Incoming commands are queued into ``self._cmd_queue``.
- ``OnIdle()`` drains the queue and executes commands on FL's main thread.
- This is critical: FL's API is **not thread-safe** — all calls must happen
  on the main thread via ``OnIdle()``.

Push events
-----------
- ``OnRefresh()`` sends a ``transport.tick`` push event.
- ``OnProjectLoad()`` sends a ``project.load`` push event.
"""

from __future__ import annotations

import json
import socket
import struct
import threading
import traceback
from typing import Any, Dict, Optional, Tuple

# FL Studio API modules — these are injected by FL's runtime
try:
    import transport
    import mixer
    import channels
    import patterns
    import playlist
    import plugins
    import device
    import general
    import arrangement
    import ui
    import piano_roll
    FL_API_AVAILABLE = True
except ImportError:
    FL_API_AVAILABLE = False

# FL MIDI script base class
try:
    from fl_classes import TLight_MidiControllerScript
    BASE_CLASS = TLight_MidiControllerScript
except ImportError:
    # Fallback for older FL versions or testing outside FL
    class TLight_MidiControllerScript:  # type: ignore[no-redef]
        pass
    BASE_CLASS = TLight_MidiControllerScript


HOST = "127.0.0.1"
PORT = 9876
MAX_FRAME_BYTES = 1_048_576  # 1 MiB


class ToolshopDAW(TLight_MidiControllerScript):
    """FL Studio MIDI device script with embedded TCP bridge."""

    def __init__(self) -> None:
        super().__init__()
        self._server_sock: Optional[socket.socket] = None
        self._client_sock: Optional[socket.socket] = None
        self._server_thread: Optional[threading.Thread] = None
        self._cmd_queue: list[Tuple[str, Dict[str, Any], int]] = []
        self._queue_lock = threading.Lock()
        self._running = False
        self._next_id = 0

    # ------------------------------------------------------------------
    # FL lifecycle hooks
    # ------------------------------------------------------------------

    def OnInit(self) -> None:
        """Called by FL when the script is loaded."""
        if not FL_API_AVAILABLE:
            print("[ToolshopDAW] FL API modules not available — running in test mode")
            return

        self._running = True
        self._start_server()
        print(f"[ToolshopDAW] TCP server listening on {HOST}:{PORT}")

    def OnDeInit(self) -> None:
        """Called by FL when the script is unloaded."""
        self._running = False
        self._stop_server()
        print("[ToolshopDAW] TCP server stopped")

    def OnIdle(self) -> None:
        """Called by FL on every idle tick — drain command queue here."""
        with self._queue_lock:
            commands = list(self._cmd_queue)
            self._cmd_queue.clear()

        for method, params, msg_id in commands:
            response = self._dispatch(method, params, msg_id)
            self._send_response(response)

    def OnRefresh(self, flag: int) -> None:
        """Called by FL when the UI needs refresh — send push event."""
        if self._client_sock and self._running:
            self._send_response({
                "jsonrpc": "2.0",
                "id": None,
                "method": "transport.tick",
                "params": {"flag": flag},
            })

    def OnProjectLoad(self, status: int) -> None:
        """Called by FL when a project is loaded."""
        if self._client_sock and self._running:
            self._send_response({
                "jsonrpc": "2.0",
                "id": None,
                "method": "project.load",
                "params": {"status": status},
            })

    # ------------------------------------------------------------------
    # TCP server
    # ------------------------------------------------------------------

    def _start_server(self) -> None:
        """Start the TCP server on a background thread."""
        self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_sock.bind((HOST, PORT))
        self._server_sock.listen(1)
        self._server_sock.settimeout(0.5)

        self._server_thread = threading.Thread(
            target=self._accept_loop, daemon=True
        )
        self._server_thread.start()

    def _stop_server(self) -> None:
        """Stop the TCP server and close all sockets."""
        if self._server_sock:
            try:
                self._server_sock.close()
            except OSError:
                pass
            self._server_sock = None

        if self._client_sock:
            try:
                self._client_sock.close()
            except OSError:
                pass
            self._client_sock = None

        if self._server_thread:
            self._server_thread.join(timeout=2.0)
            self._server_thread = None

    def _accept_loop(self) -> None:
        """Background thread: accept connections and read commands."""
        while self._running:
            try:
                if self._server_sock is None:
                    break
                client, addr = self._server_sock.accept()
                # Close any existing client connection
                if self._client_sock:
                    try:
                        self._client_sock.close()
                    except OSError:
                        pass
                self._client_sock = client
                print(f"[ToolshopDAW] Client connected from {addr}")
                self._read_loop(client)
            except socket.timeout:
                continue
            except OSError:
                break  # server socket closed

    def _read_loop(self, sock: socket.socket) -> None:
        """Read frames from the client and queue commands."""
        while self._running:
            msg = self._read_frame(sock)
            if msg is None:
                print("[ToolshopDAW] Client disconnected")
                self._client_sock = None
                return

            msg_id = msg.get("id")
            method = msg.get("method", "")
            params = msg.get("params", {})

            with self._queue_lock:
                self._cmd_queue.append((method, params, msg_id))

    # ------------------------------------------------------------------
    # Framing
    # ------------------------------------------------------------------

    @staticmethod
    def _read_frame(sock: socket.socket) -> Optional[Dict[str, Any]]:
        """Read one length-prefixed JSON frame. Returns None on EOF."""
        try:
            header = b""
            while len(header) < 4:
                chunk = sock.recv(4 - len(header))
                if not chunk:
                    return None
                header += chunk

            (total_len,) = struct.unpack(">I", header)
            if total_len == 0:
                return {}
            if total_len > MAX_FRAME_BYTES:
                print(f"[ToolshopDAW] Frame too large: {total_len} bytes")
                return None

            payload = b""
            while len(payload) < total_len:
                chunk = sock.recv(min(total_len - len(payload), 65536))
                if not chunk:
                    return None
                payload += chunk

            return json.loads(payload.decode("utf-8"))
        except (OSError, json.JSONDecodeError, struct.error):
            return None

    def _send_response(self, response: Dict[str, Any]) -> None:
        """Send a JSON-RPC response frame to the connected client."""
        if self._client_sock is None:
            return
        try:
            payload = json.dumps(response, ensure_ascii=False).encode("utf-8")
            length = struct.pack(">I", len(payload))
            self._client_sock.sendall(length + payload)
        except OSError:
            self._client_sock = None

    # ------------------------------------------------------------------
    # Command dispatch
    # ------------------------------------------------------------------

    def _dispatch(
        self, method: str, params: Dict[str, Any], msg_id: Optional[int]
    ) -> Dict[str, Any]:
        """Execute a command and return a JSON-RPC response dict."""
        try:
            handler = self._get_handler(method)
            if handler is None:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}",
                    },
                }
            result = handler(**params) if params else handler()
            return {"jsonrpc": "2.0", "id": msg_id, "result": result}
        except TypeError as exc:
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32602, "message": f"Invalid params: {exc}"},
            }
        except Exception as exc:
            tb = traceback.format_exc()
            print(f"[ToolshopDAW] Error in {method}: {exc}\n{tb}")
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32000, "message": str(exc)},
            }

    def _get_handler(self, method: str):
        """Return the handler function for a dotted method name."""
        handlers = {
            # System
            "system.ping": self._sys_ping,
            "system.status": self._sys_status,
            # Transport
            "transport.play": self._transport_play,
            "transport.stop": self._transport_stop,
            "transport.set_tempo": self._transport_set_tempo,
            "transport.get_tempo": self._transport_get_tempo,
            "transport.get_state": self._transport_get_state,
            "transport.set_metronome": self._transport_set_metronome,
            "transport.record": self._transport_record,
            "transport.get_time_signature": self._transport_get_time_sig,
            "transport.set_time_signature": self._transport_set_time_sig,
            "transport.get_position": self._transport_get_position,
            # Mixer
            "mixer.get_state": self._mixer_get_state,
            "mixer.set_volume": self._mixer_set_volume,
            "mixer.set_pan": self._mixer_set_pan,
            "mixer.mute": self._mixer_mute,
            "mixer.solo": self._mixer_solo,
            "mixer.route": self._mixer_route,
            "mixer.add_fx": self._mixer_add_fx,
            "mixer.get_fx_params": self._mixer_get_fx_params,
            "mixer.set_fx_param": self._mixer_set_fx_param,
            # Channels
            "channels.list": self._channels_list,
            "channels.get_step": self._channels_get_step,
            "channels.set_step": self._channels_set_step,
            "channels.add": self._channels_add,
            "channels.rename": self._channels_rename,
            "channels.set_color": self._channels_set_color,
            "channels.get_step_pattern": self._channels_get_step_pattern,
            "channels.set_step_pattern": self._channels_set_step_pattern,
            # Patterns
            "patterns.list": self._patterns_list,
            "patterns.create": self._patterns_create,
            "patterns.rename": self._patterns_rename,
            "patterns.clone": self._patterns_clone,
            # Playlist
            "playlist.get_track_names": self._playlist_get_track_names,
            # Piano roll
            "pianoroll.add_notes": self._pianoroll_add_notes,
            "pianoroll.clear_notes": self._pianoroll_clear_notes,
            "pianoroll.get_notes": self._pianoroll_get_notes,
            "pianoroll.quantize": self._pianoroll_quantize,
            "pianoroll.transpose": self._pianoroll_transpose,
            "pianoroll.humanize": self._pianoroll_humanize,
            # Plugins
            "plugins.get_param": self._plugins_get_param,
            "plugins.set_param": self._plugins_set_param,
            "plugins.get_param_count": self._plugins_get_param_count,
            "plugins.get_param_name": self._plugins_get_param_name,
        }
        return handlers.get(method)

    # ------------------------------------------------------------------
    # System handlers
    # ------------------------------------------------------------------

    def _sys_ping(self) -> Dict[str, Any]:
        return {"ok": True}

    def _sys_status(self) -> Dict[str, Any]:
        info: Dict[str, Any] = {
            "bridge": "ToolshopDAW",
            "connected": self._client_sock is not None,
        }
        if FL_API_AVAILABLE:
            info["fl_version"] = general.getVersion()
            info["tempo"] = transport.getTempo()
            info["playing"] = transport.getPlayMode() > 0
            info["metronome"] = transport.isMetronomeEnabled()
        return info

    # ------------------------------------------------------------------
    # Transport handlers
    # ------------------------------------------------------------------

    def _transport_play(self) -> Dict[str, Any]:
        transport.start()
        return {"playing": True}

    def _transport_stop(self) -> Dict[str, Any]:
        transport.stop()
        return {"playing": False}

    def _transport_set_tempo(self, bpm: float) -> Dict[str, Any]:
        transport.setTempo(bpm)
        return {"tempo": bpm}

    def _transport_get_tempo(self) -> Dict[str, Any]:
        return {"tempo": transport.getTempo()}

    def _transport_get_state(self) -> Dict[str, Any]:
        return {
            "playing": transport.getPlayMode() > 0,
            "tempo": transport.getTempo(),
            "metronome": transport.isMetronomeEnabled(),
            "position": transport.getSongPos(0),  # 0 = seconds
            "recording": transport.isRecording(),
        }

    def _transport_set_metronome(self, enabled: bool) -> Dict[str, Any]:
        current = transport.isMetronomeEnabled()
        if enabled != current:
            transport.toggleMetronome()
        return {"metronome": enabled}

    def _transport_record(self) -> Dict[str, Any]:
        transport.record()
        return {"recording": True}

    def _transport_get_time_sig(self) -> Dict[str, Any]:
        return {
            "numerator": transport.getTimeSigNum(),
            "denominator": transport.getTimeSigDen(),
        }

    def _transport_set_time_sig(self, numerator: int, denominator: int) -> Dict[str, Any]:
        transport.setTimeSig(numerator, denominator, 0)  # 0 = immediate
        return {"numerator": numerator, "denominator": denominator}

    def _transport_get_position(self) -> Dict[str, Any]:
        return {
            "song_pos_seconds": transport.getSongPos(0),
            "song_pos_beats": transport.getSongPos(1),
            "song_length_seconds": transport.getSongLength(0),
        }

    # ------------------------------------------------------------------
    # Mixer handlers
    # ------------------------------------------------------------------

    def _mixer_get_state(self) -> Dict[str, Any]:
        track_count = mixer.getTrackNum()
        tracks = []
        for i in range(track_count):
            tracks.append({
                "index": i,
                "name": mixer.getTrackName(i),
                "volume": mixer.getTrackVolume(i),
                "pan": mixer.getTrackPan(i),
                "muted": mixer.isTrackMuted(i),
                "soloed": mixer.isTrackSolo(i),
            })
        return {"track_count": track_count, "tracks": tracks}

    def _mixer_set_volume(self, track: int, level: float) -> Dict[str, Any]:
        mixer.setTrackVolume(track, level)
        return {"track": track, "volume": level}

    def _mixer_set_pan(self, track: int, pan: float) -> Dict[str, Any]:
        mixer.setTrackPan(track, pan)
        return {"track": track, "pan": pan}

    def _mixer_mute(self, track: int, muted: bool = True) -> Dict[str, Any]:
        mixer.muteTrack(track)
        return {"track": track, "muted": muted}

    def _mixer_solo(self, track: int, soloed: bool = True) -> Dict[str, Any]:
        mixer.soloTrack(track)
        return {"track": track, "soloed": soloed}

    def _mixer_route(self, track: int, to_track: int) -> Dict[str, Any]:
        mixer.routeTrack(track, to_track)
        return {"track": track, "routed_to": to_track}

    def _mixer_add_fx(self, track: int, plugin_name: str) -> Dict[str, Any]:
        slot = mixer.getPluginSlotCount(track)
        mixer.setPluginSlotName(track, slot, plugin_name)
        return {"track": track, "plugin": plugin_name, "slot": slot}

    def _mixer_get_fx_params(self, track: int, slot: int = 0) -> Dict[str, Any]:
        param_count = plugins.getPluginSlotParamCount(track, slot)
        params = []
        for i in range(param_count):
            params.append({
                "index": i,
                "name": plugins.getPluginSlotParamName(track, slot, i),
                "value": plugins.getPluginSlotParamValue(track, slot, i),
            })
        return {"track": track, "slot": slot, "param_count": param_count, "params": params}

    def _mixer_set_fx_param(
        self, track: int, slot: int, param_index: int, value: float
    ) -> Dict[str, Any]:
        plugins.setPluginSlotParamValue(track, slot, param_index, value)
        return {"track": track, "slot": slot, "param": param_index, "value": value}

    # ------------------------------------------------------------------
    # Channels handlers
    # ------------------------------------------------------------------

    def _channels_list(self) -> Dict[str, Any]:
        count = channels.channelCount()
        ch_list = []
        for i in range(count):
            ch_list.append({
                "index": i,
                "name": channels.getChannelName(i),
                "color": channels.getChannelColor(i),
                "volume": channels.getChannelVolume(i),
                "pan": channels.getChannelPan(i),
                "midi_chan": channels.getChannelMidiIn(i),
            })
        return {"channel_count": count, "channels": ch_list}

    def _channels_get_step(self, channel: int, step: int) -> Dict[str, Any]:
        active = channels.getGridBit(channel, step)
        return {"channel": channel, "step": step, "active": bool(active)}

    def _channels_set_step(self, channel: int, step: int, active: bool) -> Dict[str, Any]:
        channels.setGridBit(channel, step, int(active))
        return {"channel": channel, "step": step, "active": active}

    def _channels_add(self, name: str = "", channel_type: str = "sampler") -> Dict[str, Any]:
        idx = channels.createChannel()
        if name:
            channels.setChannelName(idx, name)
        return {"index": idx, "name": name or f"Channel {idx}", "type": channel_type}

    def _channels_rename(self, index: int, name: str) -> Dict[str, Any]:
        channels.setChannelName(index, name)
        return {"index": index, "name": name}

    def _channels_set_color(self, index: int, color: int) -> Dict[str, Any]:
        channels.setChannelColor(index, color)
        return {"index": index, "color": color}

    def _channels_get_step_pattern(self, channel: int, length: int = 16) -> Dict[str, Any]:
        steps = []
        for s in range(length):
            steps.append(bool(channels.getGridBit(channel, s)))
        return {"channel": channel, "length": length, "steps": steps}

    def _channels_set_step_pattern(self, channel: int, steps: list) -> Dict[str, Any]:
        for s, active in enumerate(steps):
            channels.setGridBit(channel, s, int(active))
        return {"channel": channel, "steps_set": len(steps)}

    # ------------------------------------------------------------------
    # Patterns handlers
    # ------------------------------------------------------------------

    def _patterns_list(self) -> Dict[str, Any]:
        count = patterns.getPatternCount()
        pat_list = []
        for i in range(1, count + 1):
            pat_list.append({
                "index": i,
                "name": patterns.getPatternName(i),
                "length": patterns.getPatternLength(i),
            })
        return {"pattern_count": count, "patterns": pat_list}

    def _patterns_create(self, name: str = "") -> Dict[str, Any]:
        idx = patterns.createPattern()
        if name:
            patterns.setPatternName(idx, name)
        return {"index": idx, "name": name or f"Pattern {idx}"}

    def _patterns_rename(self, index: int, name: str) -> Dict[str, Any]:
        patterns.setPatternName(index, name)
        return {"index": index, "name": name}

    def _patterns_clone(self, index: int, name: str = "") -> Dict[str, Any]:
        new_idx = patterns.clonePattern(index)
        if name:
            patterns.setPatternName(new_idx, name)
        return {"index": new_idx, "source": index, "name": name or f"Pattern {new_idx}"}

    # ------------------------------------------------------------------
    # Playlist handlers
    # ------------------------------------------------------------------

    def _playlist_get_track_names(self) -> Dict[str, Any]:
        count = playlist.getTrackCount()
        names = []
        for i in range(count):
            names.append({
                "index": i,
                "name": playlist.getTrackName(i),
            })
        return {"track_count": count, "tracks": names}

    # ------------------------------------------------------------------
    # Piano roll handlers
    # ------------------------------------------------------------------

    def _pianoroll_add_notes(self, pattern: int, notes: list) -> Dict[str, Any]:
        patterns.jumpToPattern(pattern)
        added = 0
        for n in notes:
            note = n.get("note", 60)
            pos = n.get("position", 0)
            length = n.get("length", 16)
            vel = n.get("velocity", 100)
            piano_roll.addNote(note, pos, length, vel)
            added += 1
        return {"pattern": pattern, "notes_added": added}

    def _pianoroll_clear_notes(self, pattern: int) -> Dict[str, Any]:
        patterns.jumpToPattern(pattern)
        piano_roll.clearNotes()
        return {"pattern": pattern, "cleared": True}

    def _pianoroll_get_notes(self, pattern: int) -> Dict[str, Any]:
        patterns.jumpToPattern(pattern)
        count = piano_roll.getNoteCount()
        notes = []
        for i in range(count):
            note_data = piano_roll.getNoteByIndex(i)
            notes.append({
                "index": i,
                "note": note_data[0],
                "position": note_data[1],
                "length": note_data[2],
                "velocity": note_data[3],
            })
        return {"pattern": pattern, "note_count": count, "notes": notes}

    def _pianoroll_quantize(self, pattern: int, grid: int = 16) -> Dict[str, Any]:
        patterns.jumpToPattern(pattern)
        piano_roll.quantize(grid)
        return {"pattern": pattern, "grid": grid}

    def _pianoroll_transpose(self, pattern: int, semitones: int) -> Dict[str, Any]:
        patterns.jumpToPattern(pattern)
        piano_roll.transpose(semitones)
        return {"pattern": pattern, "semitones": semitones}

    def _pianoroll_humanize(
        self, pattern: int, amount: float = 0.3, seed: int = 42
    ) -> Dict[str, Any]:
        patterns.jumpToPattern(pattern)
        piano_roll.humanize(amount, seed)
        return {"pattern": pattern, "amount": amount, "seed": seed}

    # ------------------------------------------------------------------
    # Plugin handlers
    # ------------------------------------------------------------------

    def _plugins_get_param(
        self, track: int, slot: int, param_index: int
    ) -> Dict[str, Any]:
        value = plugins.getPluginSlotParamValue(track, slot, param_index)
        return {"track": track, "slot": slot, "param": param_index, "value": value}

    def _plugins_set_param(
        self, track: int, slot: int, param_index: int, value: float
    ) -> Dict[str, Any]:
        plugins.setPluginSlotParamValue(track, slot, param_index, value)
        return {"track": track, "slot": slot, "param": param_index, "value": value}

    def _plugins_get_param_count(self, track: int, slot: int) -> Dict[str, Any]:
        count = plugins.getPluginSlotParamCount(track, slot)
        return {"track": track, "slot": slot, "param_count": count}

    def _plugins_get_param_name(
        self, track: int, slot: int, param_index: int
    ) -> Dict[str, Any]:
        name = plugins.getPluginSlotParamName(track, slot, param_index)
        return {"track": track, "slot": slot, "param": param_index, "name": name}


# FL Studio entry point
def OnRefresh(flag: int) -> None:
    pass  # handled by instance


def OnInit() -> None:
    pass  # handled by instance


def OnDeInit() -> None:
    pass  # handled by instance


# Global instance — FL creates this automatically when the script is loaded
_instance: Optional[ToolshopDAW] = None


def CreateInstance() -> ToolshopDAW:
    global _instance
    _instance = ToolshopDAW()
    return _instance
