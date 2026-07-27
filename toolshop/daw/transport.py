"""Transport control — play, stop, tempo, metronome, recording, time signature.

These functions wrap :class:`toolshop.daw.client.DAWClient` calls to provide
a clean, typed interface for transport operations.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .client import DAWClient


def play(client: DAWClient) -> Dict[str, Any]:
    """Start playback."""
    return client.call("transport.play")  # type: ignore[return-value]


def stop(client: DAWClient) -> Dict[str, Any]:
    """Stop playback."""
    return client.call("transport.stop")  # type: ignore[return-value]


def set_tempo(client: DAWClient, bpm: float) -> Dict[str, Any]:
    """Set the project tempo in BPM."""
    if bpm <= 0 or bpm > 1000:
        raise ValueError(f"BPM must be between 0 and 1000, got {bpm}")
    return client.call("transport.set_tempo", bpm=bpm)  # type: ignore[return-value]


def get_tempo(client: DAWClient) -> Dict[str, Any]:
    """Get the current project tempo."""
    return client.call("transport.get_tempo")  # type: ignore[return-value]


def get_state(client: DAWClient) -> Dict[str, Any]:
    """Get full transport state (playing, tempo, metronome, position, recording)."""
    return client.call("transport.get_state")  # type: ignore[return-value]


def set_metronome(client: DAWClient, enabled: bool) -> Dict[str, Any]:
    """Enable or disable the metronome."""
    return client.call("transport.set_metronome", enabled=enabled)  # type: ignore[return-value]


def record(client: DAWClient) -> Dict[str, Any]:
    """Start recording."""
    return client.call("transport.record")  # type: ignore[return-value]


def get_time_signature(client: DAWClient) -> Dict[str, Any]:
    """Get the current time signature."""
    return client.call("transport.get_time_signature")  # type: ignore[return-value]


def set_time_signature(
    client: DAWClient, numerator: int, denominator: int
) -> Dict[str, Any]:
    """Set the time signature (e.g. 4/4, 3/4, 6/8)."""
    if numerator <= 0 or denominator <= 0:
        raise ValueError("Numerator and denominator must be positive")
    return client.call(  # type: ignore[return-value]
        "transport.set_time_signature",
        numerator=numerator,
        denominator=denominator,
    )


def get_position(client: DAWClient) -> Dict[str, Any]:
    """Get the current playback position (seconds, beats, song length)."""
    return client.call("transport.get_position")  # type: ignore[return-value]
