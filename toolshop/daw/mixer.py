"""Mixer control — volume, pan, mute, solo, routing, and FX.

Wraps :class:`toolshop.daw.client.DAWClient` calls for mixer operations.
"""

from __future__ import annotations

from typing import Any, Dict

from .client import DAWClient


def get_state(client: DAWClient) -> Dict[str, Any]:
    """Get full mixer state: all tracks with name, volume, pan, mute, solo."""
    return client.call("mixer.get_state")  # type: ignore[return-value]


def set_volume(client: DAWClient, track: int, level: float) -> Dict[str, Any]:
    """Set mixer track volume (0.0–1.0)."""
    return client.call("mixer.set_volume", track=track, level=level)  # type: ignore[return-value]


def set_pan(client: DAWClient, track: int, pan: float) -> Dict[str, Any]:
    """Set mixer track pan (-1.0 left to 1.0 right)."""
    return client.call("mixer.set_pan", track=track, pan=pan)  # type: ignore[return-value]


def mute(client: DAWClient, track: int, muted: bool = True) -> Dict[str, Any]:
    """Mute or unmute a mixer track."""
    return client.call("mixer.mute", track=track, muted=muted)  # type: ignore[return-value]


def solo(client: DAWClient, track: int, soloed: bool = True) -> Dict[str, Any]:
    """Solo or unsolo a mixer track."""
    return client.call("mixer.solo", track=track, soloed=soloed)  # type: ignore[return-value]


def route(client: DAWClient, track: int, to_track: int) -> Dict[str, Any]:
    """Route a mixer track to another mixer track."""
    return client.call("mixer.route", track=track, to_track=to_track)  # type: ignore[return-value]


def add_fx(client: DAWClient, track: int, plugin_name: str) -> Dict[str, Any]:
    """Add an FX plugin to a mixer track."""
    return client.call(  # type: ignore[return-value]
        "mixer.add_fx", track=track, plugin_name=plugin_name
    )


def get_fx_params(client: DAWClient, track: int, slot: int = 0) -> Dict[str, Any]:
    """Get FX parameter values for a plugin slot on a mixer track."""
    return client.call(  # type: ignore[return-value]
        "mixer.get_fx_params", track=track, slot=slot
    )


def set_fx_param(
    client: DAWClient, track: int, slot: int, param_index: int, value: float
) -> Dict[str, Any]:
    """Set a single FX parameter value on a mixer track plugin slot."""
    return client.call(  # type: ignore[return-value]
        "mixer.set_fx_param",
        track=track,
        slot=slot,
        param_index=param_index,
        value=value,
    )
