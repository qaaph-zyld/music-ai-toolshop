"""Ableton Live Remote Script — TCP bridge server (port 9878).

This script runs *inside* Ableton Live's Python runtime as a MIDI Remote
Script.  It opens a TCP server on 127.0.0.1:9878 — the same length-prefixed
JSON-RPC 2.0 protocol as the FL bridge on :9876, so the existing
``toolshop.daw.client.DAWClient`` talks to it unchanged::

    client = DAWClient(port=9878)
    client.call("transport.play")

Installation
------------
1. Create the directory::

       %APPDATA%\\Ableton\\Live 12.x\\Preferences\\User Remote Scripts\\ToolshopLive\\

2. Copy this file into it as ``__init__.py`` (Live requires the Remote
   Script module to be named ``__init__.py`` inside its own folder).

3. Restart Live → Preferences → Link/Tempo/MIDI → Control Surface →
   pick ``ToolshopLive``.  No Input/Output ports need to be assigned.

4. Check Live's log / the script output for
   ``[ToolshopLive] TCP server listening on 127.0.0.1:9878``.

Threading model
---------------
- TCP ``accept()`` + read loop run on a background daemon thread.
- Incoming commands are queued; ``schedule_message`` drains the queue on
  Live's main thread — the Live Object Model is **not thread-safe**, so all
  Song/Track/Device access happens inside scheduled callbacks.
- Responses are sent from that same main-thread callback.

Method surface
--------------
Names mirror the FL bridge where semantics match:

- ``system.ping``, ``system.status``
- ``transport.play|stop|record|set_tempo|get_tempo|get_state|
  set_metronome|get_position|get_time_signature|set_time_signature``
- ``mixer.get_state|set_volume|set_pan|mute|solo``
- ``mixer.get_fx_params|set_fx_param``  (→ Live device parameters)
- ``tracks.list``
- ``scenes.list|fire``
- ``clips.list|fire|stop``
- ``devices.list|get_params|set_param`` (by index or name)
- ``plugins.get_param_count|get_param|get_param_name|set_param``
  (FL-compatible; the client sends ``param_index=``, so both ``param_index``
  and the legacy ``param`` kwarg are accepted)
"""

from __future__ import annotations

import json
import socket
import struct
import threading
import traceback
from typing import Any, Dict, List, Optional, Tuple

# Ableton ships its own embedded Python with _Framework available only
# inside Live; importing outside Live must not explode (tests exercise the
# protocol layer with a stub base class).
try:
    from _Framework.ControlSurface import ControlSurface
    LIVE_API_AVAILABLE = True
except ImportError:
    LIVE_API_AVAILABLE = False

    class ControlSurface:  # type: ignore[no-redef]
        """Stub base so the module imports outside Live for tests."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self._scheduled: List[Any] = []

        def schedule_message(self, delay: int, callback: Any) -> None:
            # In tests, run inline — no Live main thread exists.
            callback()

        def show_message(self, msg: str) -> None:
            print(f"[ToolshopLive] {msg}")

        def disconnect(self) -> None:
            pass


HOST = "127.0.0.1"
PORT = 9878
MAX_FRAME_BYTES = 1_048_576  # 1 MiB


class ToolshopLive(ControlSurface):
    """Live Remote Script with embedded TCP JSON-RPC bridge."""

    def __init__(self, c_instance: Any = None) -> None:
        super().__init__(c_instance) if c_instance is not None else super().__init__()
        self._c_instance = c_instance
        self._server_sock: Optional[socket.socket] = None
        self._client_sock: Optional[socket.socket] = None
        self._server_thread: Optional[threading.Thread] = None
        self._cmd_queue: List[Tuple[str, Dict[str, Any], Any]] = []
        self._queue_lock = threading.Lock()
        self._running = False
        if LIVE_API_AVAILABLE:
            self._start()

    # ------------------------------------------------------------------
    # Live lifecycle
    # ------------------------------------------------------------------

    def _start(self) -> None:
        self._running = True
        self._start_server()
        self.log_message_safe(f"[ToolshopLive] TCP server listening on {HOST}:{PORT}")

    def disconnect(self) -> None:
        """Called by Live when the control surface is unloaded."""
        self._running = False
        self._stop_server()
        try:
            super().disconnect()
        except Exception:
            pass

    def log_message_safe(self, msg: str) -> None:
        try:
            self.log_message(msg)  # type: ignore[attr-defined]
        except Exception:
            try:
                self.show_message(msg)
            except Exception:
                print(msg)

    # ------------------------------------------------------------------
    # TCP server — background thread
    # ------------------------------------------------------------------

    def _start_server(self) -> None:
        self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_sock.bind((HOST, PORT))
        self._server_sock.listen(1)
        self._server_sock.settimeout(0.5)
        self._server_thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._server_thread.start()

    def _stop_server(self) -> None:
        for sock in (self._server_sock, self._client_sock):
            if sock:
                try:
                    sock.close()
                except OSError:
                    pass
        self._server_sock = None
        self._client_sock = None
        if self._server_thread:
            self._server_thread.join(timeout=2.0)
            self._server_thread = None

    def _accept_loop(self) -> None:
        while self._running:
            try:
                if self._server_sock is None:
                    break
                client, addr = self._server_sock.accept()
                if self._client_sock:
                    try:
                        self._client_sock.close()
                    except OSError:
                        pass
                self._client_sock = client
                self.log_message_safe(f"[ToolshopLive] client connected: {addr}")
                self._read_loop(client)
            except socket.timeout:
                continue
            except OSError:
                break

    def _read_loop(self, sock: socket.socket) -> None:
        while self._running:
            msg = self._read_frame(sock)
            if msg is None:
                self.log_message_safe("[ToolshopLive] client disconnected")
                self._client_sock = None
                return
            with self._queue_lock:
                self._cmd_queue.append(
                    (msg.get("method", ""), msg.get("params", {}) or {},
                     msg.get("id"))
                )
            # Drain on Live's main thread ASAP (schedule_message ticks ≈ 100ms).
            self.schedule_message(0, self._drain_commands)

    def _drain_commands(self) -> None:
        """Runs on Live's main thread — safe to touch the Song."""
        with self._queue_lock:
            commands = list(self._cmd_queue)
            self._cmd_queue.clear()
        for method, params, msg_id in commands:
            self._send_response(self._dispatch(method, params, msg_id))

    # ------------------------------------------------------------------
    # Framing (identical to the FL bridge)
    # ------------------------------------------------------------------

    @staticmethod
    def _read_frame(sock: socket.socket) -> Optional[Dict[str, Any]]:
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
        if self._client_sock is None:
            return
        try:
            payload = json.dumps(response, ensure_ascii=False).encode("utf-8")
            self._client_sock.sendall(struct.pack(">I", len(payload)) + payload)
        except OSError:
            self._client_sock = None

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def _song(self) -> Any:
        if not LIVE_API_AVAILABLE or self._c_instance is None:
            raise RuntimeError("Live API not available (running outside Live?)")
        return self._c_instance.song()

    def _dispatch(
        self, method: str, params: Dict[str, Any], msg_id: Any
    ) -> Dict[str, Any]:
        try:
            handler = self._get_handler(method)
            if handler is None:
                return {"jsonrpc": "2.0", "id": msg_id, "error": {
                    "code": -32601, "message": f"Method not found: {method}"}}
            result = handler(**params) if params else handler()
            return {"jsonrpc": "2.0", "id": msg_id, "result": result}
        except TypeError as exc:
            return {"jsonrpc": "2.0", "id": msg_id, "error": {
                "code": -32602, "message": f"Invalid params: {exc}"}}
        except Exception as exc:
            self.log_message_safe(
                f"[ToolshopLive] error in {method}: {exc}\n{traceback.format_exc()}")
            return {"jsonrpc": "2.0", "id": msg_id, "error": {
                "code": -32000, "message": str(exc)}}

    def _get_handler(self, method: str):
        handlers = {
            "system.ping": self._sys_ping,
            "system.status": self._sys_status,
            "transport.play": self._t_play,
            "transport.stop": self._t_stop,
            "transport.record": self._t_record,
            "transport.set_tempo": self._t_set_tempo,
            "transport.get_tempo": self._t_get_tempo,
            "transport.get_state": self._t_get_state,
            "transport.set_metronome": self._t_set_metronome,
            "transport.get_position": self._t_get_position,
            "transport.get_time_signature": self._t_get_time_sig,
            "transport.set_time_signature": self._t_set_time_sig,
            "mixer.get_state": self._mixer_get_state,
            "mixer.set_volume": self._mixer_set_volume,
            "mixer.set_pan": self._mixer_set_pan,
            "mixer.mute": self._mixer_mute,
            "mixer.solo": self._mixer_solo,
            "mixer.get_fx_params": self._mixer_get_fx_params,
            "mixer.set_fx_param": self._mixer_set_fx_param,
            "tracks.list": self._tracks_list,
            "scenes.list": self._scenes_list,
            "scenes.fire": self._scenes_fire,
            "clips.list": self._clips_list,
            "clips.fire": self._clips_fire,
            "clips.stop": self._clips_stop,
            "devices.list": self._devices_list,
            "devices.get_params": self._devices_get_params,
            "devices.set_param": self._devices_set_param,
            # FL-compatible plugin aliases → device params
            "plugins.get_param_count": self._plugins_get_param_count,
            "plugins.get_param": self._plugins_get_param,
            "plugins.get_param_name": self._plugins_get_param_name,
            "plugins.set_param": self._plugins_set_param,
        }
        return handlers.get(method)

    # ------------------------------------------------------------------
    # System
    # ------------------------------------------------------------------

    def _sys_ping(self) -> Dict[str, Any]:
        return {"ok": True}

    def _sys_status(self) -> Dict[str, Any]:
        info: Dict[str, Any] = {
            "bridge": "ToolshopLive",
            "connected": self._client_sock is not None,
        }
        if LIVE_API_AVAILABLE and self._c_instance is not None:
            song = self._song()
            info.update({
                "tempo": song.tempo,
                "playing": song.is_playing,
                "recording": song.record_mode,
                "metronome": song.metronome,
                "track_count": len(song.tracks),
                "scene_count": len(song.scenes),
            })
        return info

    # ------------------------------------------------------------------
    # Transport
    # ------------------------------------------------------------------

    def _t_play(self) -> Dict[str, Any]:
        song = self._song()
        song.start_playing()
        return {"playing": True}

    def _t_stop(self) -> Dict[str, Any]:
        song = self._song()
        song.stop_playing()
        return {"playing": False}

    def _t_record(self) -> Dict[str, Any]:
        song = self._song()
        song.record_mode = True
        return {"recording": True}

    def _t_set_tempo(self, bpm: float) -> Dict[str, Any]:
        song = self._song()
        song.tempo = float(bpm)
        return {"tempo": song.tempo}

    def _t_get_tempo(self) -> Dict[str, Any]:
        return {"tempo": self._song().tempo}

    def _t_get_state(self) -> Dict[str, Any]:
        song = self._song()
        return {
            "playing": song.is_playing,
            "recording": song.record_mode,
            "tempo": song.tempo,
            "metronome": song.metronome,
            "position_seconds": song.current_song_time,
        }

    def _t_set_metronome(self, enabled: bool) -> Dict[str, Any]:
        song = self._song()
        song.metronome = bool(enabled)
        return {"metronome": song.metronome}

    def _t_get_position(self) -> Dict[str, Any]:
        song = self._song()
        return {
            "song_pos_seconds": song.current_song_time,
            "song_length_seconds": song.song_length,
            "loop_start": song.loop_start,
            "loop_length": song.loop_length,
        }

    def _t_get_time_sig(self) -> Dict[str, Any]:
        song = self._song()
        return {"numerator": song.signature_numerator,
                "denominator": song.signature_denominator}

    def _t_set_time_sig(self, numerator: int, denominator: int) -> Dict[str, Any]:
        song = self._song()
        song.signature_numerator = int(numerator)
        song.signature_denominator = int(denominator)
        return {"numerator": numerator, "denominator": denominator}

    # ------------------------------------------------------------------
    # Mixer / tracks
    # ------------------------------------------------------------------

    def _track(self, index: int) -> Any:
        tracks = self._song().tracks
        if not (0 <= index < len(tracks)):
            raise IndexError(f"track {index} out of range (0..{len(tracks) - 1})")
        return tracks[index]

    def _track_info(self, index: int, track: Any) -> Dict[str, Any]:
        return {
            "index": index,
            "name": track.name,
            "volume": track.mixer_device.volume.value,
            "pan": track.mixer_device.panning.value,
            "muted": track.mute,
            "soloed": track.solo,
            "armed": getattr(track, "arm", False),
            "device_count": len(track.devices),
        }

    def _mixer_get_state(self) -> Dict[str, Any]:
        tracks = list(self._song().tracks)
        return {
            "track_count": len(tracks),
            "tracks": [self._track_info(i, t) for i, t in enumerate(tracks)],
        }

    def _tracks_list(self) -> Dict[str, Any]:
        return self._mixer_get_state()

    def _mixer_set_volume(self, track: int, level: float) -> Dict[str, Any]:
        t = self._track(track)
        t.mixer_device.volume.value = max(0.0, min(1.0, float(level)))
        return {"track": track, "volume": t.mixer_device.volume.value}

    def _mixer_set_pan(self, track: int, pan: float) -> Dict[str, Any]:
        t = self._track(track)
        t.mixer_device.panning.value = max(-1.0, min(1.0, float(pan)))
        return {"track": track, "pan": t.mixer_device.panning.value}

    def _mixer_mute(self, track: int, muted: bool = True) -> Dict[str, Any]:
        t = self._track(track)
        t.mute = bool(muted)
        return {"track": track, "muted": t.mute}

    def _mixer_solo(self, track: int, soloed: bool = True) -> Dict[str, Any]:
        t = self._track(track)
        t.solo = bool(soloed)
        return {"track": track, "soloed": t.solo}

    # ------------------------------------------------------------------
    # Scenes / clips
    # ------------------------------------------------------------------

    def _scenes_list(self) -> Dict[str, Any]:
        scenes = self._song().scenes
        return {"scene_count": len(scenes),
                "scenes": [{"index": i, "name": s.name}
                           for i, s in enumerate(scenes)]}

    def _scenes_fire(self, index: int) -> Dict[str, Any]:
        scenes = self._song().scenes
        if not (0 <= index < len(scenes)):
            raise IndexError(f"scene {index} out of range")
        scenes[index].fire()
        return {"scene": index, "fired": True}

    def _clips_list(self, track: int) -> Dict[str, Any]:
        t = self._track(track)
        slots = []
        for i, slot in enumerate(t.clip_slots):
            slots.append({
                "index": i,
                "has_clip": slot.has_clip,
                "name": slot.clip.name if slot.has_clip else None,
                "playing": getattr(slot, "is_playing", False),
            })
        return {"track": track, "clip_slots": slots}

    def _clips_fire(self, track: int, slot: int) -> Dict[str, Any]:
        t = self._track(track)
        if not (0 <= slot < len(t.clip_slots)):
            raise IndexError(f"clip slot {slot} out of range")
        t.clip_slots[slot].fire()
        return {"track": track, "slot": slot, "fired": True}

    def _clips_stop(self, track: int) -> Dict[str, Any]:
        self._track(track).stop_all_clips()
        return {"track": track, "stopped": True}

    # ------------------------------------------------------------------
    # Devices (plugins.get_* aliases map here — Live calls FX "devices")
    # ------------------------------------------------------------------

    def _device(self, track: int, device: int) -> Any:
        t = self._track(track)
        if not (0 <= device < len(t.devices)):
            raise IndexError(
                f"device {device} out of range on track {track} "
                f"(0..{len(t.devices) - 1})")
        return t.devices[device]

    def _devices_list(self, track: int) -> Dict[str, Any]:
        t = self._track(track)
        return {
            "track": track,
            "devices": [{
                "index": i,
                "name": d.name,
                "class_name": getattr(d, "class_name", ""),
                "param_count": len(d.parameters),
                "enabled": d.parameters[0].value > 0 if len(d.parameters) else None,
            } for i, d in enumerate(t.devices)],
        }

    @staticmethod
    def _param_list(device: Any) -> List[Dict[str, Any]]:
        return [{
            "index": i,
            "name": p.name,
            "value": p.value,
            "min": p.min,
            "max": p.max,
            "enabled": p.is_enabled,
        } for i, p in enumerate(device.parameters)]

    def _devices_get_params(self, track: int, device: int) -> Dict[str, Any]:
        d = self._device(track, device)
        params = self._param_list(d)
        return {"track": track, "device": device, "name": d.name,
                "param_count": len(params), "params": params}

    def _devices_set_param(
        self, track: int, device: int, value: float,
        param_index: Optional[int] = None, param_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        d = self._device(track, device)
        if param_name is not None:
            matches = [p for p in d.parameters
                       if p.name.lower() == param_name.lower()]
            if not matches:
                raise ValueError(
                    f"no parameter named {param_name!r} on {d.name!r}")
            p = matches[0]
            idx = list(d.parameters).index(p)
        elif param_index is not None:
            if not (0 <= param_index < len(d.parameters)):
                raise IndexError(f"param {param_index} out of range")
            p = d.parameters[param_index]
            idx = param_index
        else:
            raise ValueError("param_index or param_name required")
        p.value = max(p.min, min(p.max, float(value)))
        return {"track": track, "device": device, "param": idx,
                "name": p.name, "value": p.value}

    # FL-bridge-compatible aliases: mixer slot N == device N on the track
    def _mixer_get_fx_params(self, track: int, slot: int = 0) -> Dict[str, Any]:
        result = self._devices_get_params(track, slot)
        result["slot"] = result.pop("device")
        return result

    def _mixer_set_fx_param(
        self, track: int, slot: int, param_index: int, value: float
    ) -> Dict[str, Any]:
        return self._devices_set_param(
            track=track, device=slot, param_index=param_index, value=value)

    def _plugins_get_param_count(self, track: int, slot: int = 0) -> Dict[str, Any]:
        return {"param_count": len(self._device(track, slot).parameters)}

    @staticmethod
    def _resolve_param_index(
        param_index: Optional[int], param: Optional[int]
    ) -> int:
        """FL/client convention is ``param_index``; ``param`` is the legacy name."""
        idx = param_index if param_index is not None else param
        if idx is None:
            raise ValueError("param_index required")
        return idx

    def _plugins_get_param(
        self, track: int, slot: int,
        param_index: Optional[int] = None, param: Optional[int] = None,
    ) -> Dict[str, Any]:
        idx = self._resolve_param_index(param_index, param)
        p = self._device(track, slot).parameters[idx]
        return {"name": p.name, "value": p.value}

    def _plugins_get_param_name(
        self, track: int, slot: int, param_index: int
    ) -> Dict[str, Any]:
        p = self._device(track, slot).parameters[param_index]
        return {"name": p.name, "param": param_index}

    def _plugins_set_param(
        self, track: int, slot: int, value: float,
        param_index: Optional[int] = None, param: Optional[int] = None,
    ) -> Dict[str, Any]:
        idx = self._resolve_param_index(param_index, param)
        return self._devices_set_param(
            track=track, device=slot, param_index=idx, value=value)


def create_instance(c_instance: Any) -> ToolshopLive:
    """Live calls this factory to instantiate the Remote Script."""
    return ToolshopLive(c_instance)
