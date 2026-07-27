"""TCP client for communicating with the FL Studio bridge script.

Sends JSON-RPC 2.0 commands over a TCP socket to the FL Studio device script
running inside the DAW.  The bridge script listens on 127.0.0.1:9876 by default
and dispatches commands to FL's Python API on the main thread.

Protocol
--------
Each message is a length-prefixed JSON frame::

    <4-byte big-endian length><UTF-8 JSON payload>

The JSON payload follows JSON-RPC 2.0::

    {"jsonrpc": "2.0", "id": 1, "method": "transport.play", "params": {}}

Responses use the same framing::

    {"jsonrpc": "2.0", "id": 1, "result": {"playing": true}}
    {"jsonrpc": "2.0", "id": 1, "error": {"code": -32603, "message": "..."}}
"""

from __future__ import annotations

import json
import socket
import struct
import threading
import time
from typing import Any, Callable, Dict, Optional

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9876
DEFAULT_TIMEOUT = 5.0  # seconds

# JSON-RPC error codes
ERR_PARSE_ERROR = -32700
ERR_INVALID_REQUEST = -32600
ERR_METHOD_NOT_FOUND = -32601
ERR_INVALID_PARAMS = -32602
ERR_INTERNAL = -32603
ERR_DAW_ERROR = -32000


class DAWConnectionError(Exception):
    """Raised when the TCP connection to the DAW bridge is not available."""


class DAWTimeoutError(Exception):
    """Raised when a command times out waiting for a response."""


class DAWServerError(Exception):
    """Raised when the DAW bridge returns a JSON-RPC error response."""

    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


class DAWClient:
    """Synchronous TCP client for the FL Studio bridge.

    Parameters
    ----------
    host : str
        TCP host (default ``127.0.0.1``).
    port : int
        TCP port (default ``9876``).
    timeout : float
        Per-command timeout in seconds (default ``5.0``).
    """

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self._sock: Optional[socket.socket] = None
        self._id_counter = 0
        self._id_lock = threading.Lock()
        self._push_listeners: list[Callable[[Dict[str, Any]], None]] = []

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """Open a TCP connection to the DAW bridge.

        Raises
        ------
        DAWConnectionError
            If the connection cannot be established.
        """
        if self._sock is not None:
            return  # already connected
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.settimeout(self.timeout)
            self._sock.connect((self.host, self.port))
        except (OSError, ConnectionRefusedError) as exc:
            self._sock = None
            raise DAWConnectionError(
                f"Cannot connect to DAW bridge at {self.host}:{self.port}. "
                f"Is FL Studio running with the ToolshopDAW script enabled? "
                f"({exc})"
            ) from exc

    def disconnect(self) -> None:
        """Close the TCP connection."""
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            finally:
                self._sock = None

    def is_connected(self) -> bool:
        """Return ``True`` if the TCP socket is open."""
        return self._sock is not None

    def __enter__(self) -> "DAWClient":
        self.connect()
        return self

    def __exit__(self, *exc: Any) -> None:
        self.disconnect()

    # ------------------------------------------------------------------
    # Push events
    # ------------------------------------------------------------------

    def add_push_listener(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Register a callback for push events from the DAW."""
        self._push_listeners.append(callback)

    def _notify_push(self, event: Dict[str, Any]) -> None:
        for cb in self._push_listeners:
            try:
                cb(event)
            except Exception:
                pass  # listener errors should not crash the client

    # ------------------------------------------------------------------
    # Low-level framing
    # ------------------------------------------------------------------

    @staticmethod
    def _encode(message: Dict[str, Any]) -> bytes:
        """Encode a JSON dict as a length-prefixed frame."""
        payload = json.dumps(message, ensure_ascii=False).encode("utf-8")
        length = struct.pack(">I", len(payload))
        return length + payload

    @staticmethod
    def _decode_frame(sock: socket.socket) -> Optional[Dict[str, Any]]:
        """Read one length-prefixed JSON frame from *sock*.

        Returns ``None`` if the connection was closed cleanly.
        """
        # Read 4-byte length header
        header = b""
        while len(header) < 4:
            chunk = sock.recv(4 - len(header))
            if not chunk:
                return None
            header += chunk

        (total_len,) = struct.unpack(">I", header)
        if total_len == 0:
            return {}

        # Read payload
        payload = b""
        while len(payload) < total_len:
            chunk = sock.recv(min(total_len - len(payload), 65536))
            if not chunk:
                return None
            payload += chunk

        return json.loads(payload.decode("utf-8"))

    def _next_id(self) -> int:
        with self._id_lock:
            self._id_counter += 1
            return self._id_counter

    # ------------------------------------------------------------------
    # Command interface
    # ------------------------------------------------------------------

    def call(self, method: str, **params: Any) -> Any:
        """Send a JSON-RPC command and return the result.

        Parameters
        ----------
        method : str
            Dotted method name, e.g. ``"transport.play"``.
        **params : Any
            Keyword parameters for the method.

        Returns
        -------
        Any
            The ``result`` field from the JSON-RPC response.

        Raises
        ------
        DAWConnectionError
            If not connected or the connection drops.
        DAWTimeoutError
            If no response within ``self.timeout``.
        DAWServerError
            If the bridge returns a JSON-RPC error.
        """
        if self._sock is None:
            raise DAWConnectionError("Not connected. Call connect() first.")

        msg_id = self._next_id()
        request = {
            "jsonrpc": "2.0",
            "id": msg_id,
            "method": method,
            "params": params,
        }
        frame = self._encode(request)

        try:
            self._sock.sendall(frame)
        except OSError as exc:
            self._sock = None
            raise DAWConnectionError(f"Failed to send command: {exc}") from exc

        # Read response — skip push events (id=None) until we get our reply
        deadline = time.monotonic() + self.timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise DAWTimeoutError(
                    f"Timed out waiting for response to '{method}' "
                    f"after {self.timeout}s"
                )
            self._sock.settimeout(remaining)
            try:
                response = self._decode_frame(self._sock)
            except socket.timeout:
                raise DAWTimeoutError(
                    f"Timed out waiting for response to '{method}' "
                    f"after {self.timeout}s"
                )
            except (OSError, json.JSONDecodeError) as exc:
                self._sock = None
                raise DAWConnectionError(f"Connection lost: {exc}") from exc

            if response is None:
                self._sock = None
                raise DAWConnectionError("Connection closed by DAW bridge.")

            # Push events have no "id" field
            if response.get("id") is None:
                self._notify_push(response)
                continue

            if response.get("id") != msg_id:
                # Stale response for a different request — skip
                continue

            if "error" in response:
                err = response["error"]
                raise DAWServerError(
                    err.get("code", ERR_INTERNAL),
                    err.get("message", "Unknown error"),
                )

            return response.get("result")

    def call_optional(self, method: str, **params: Any) -> Optional[Any]:
        """Like :meth:`call` but returns ``None`` on connection error."""
        try:
            return self.call(method, **params)
        except (DAWConnectionError, DAWTimeoutError):
            return None

    # ------------------------------------------------------------------
    # Convenience: ping/status
    # ------------------------------------------------------------------

    def ping(self) -> bool:
        """Return ``True`` if the bridge responds to a ping."""
        result = self.call_optional("system.ping")
        return result is not None and result.get("ok") is True

    def status(self) -> Dict[str, Any]:
        """Return DAW status (version, tempo, playing state, etc.)."""
        return self.call("system.status")  # type: ignore[return-value]
