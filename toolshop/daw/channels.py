"""Channel rack control — list, add, rename, color, step sequencer.

Wraps :class:`toolshop.daw.client.DAWClient` calls for channel operations.
"""

from __future__ import annotations

from typing import Any, Dict, List

from .client import DAWClient


def list_channels(client: DAWClient) -> Dict[str, Any]:
    """List all channels with name, color, volume, pan, MIDI channel."""
    return client.call("channels.list")  # type: ignore[return-value]


def add_channel(client: DAWClient, name: str = "", channel_type: str = "sampler") -> Dict[str, Any]:
    """Add a new channel to the channel rack.

    Args:
        name: Channel name.
        channel_type: ``"sampler"`` (default) or ``"synth"``.
    """
    return client.call(  # type: ignore[return-value]
        "channels.add", name=name, channel_type=channel_type
    )


def rename_channel(client: DAWClient, index: int, name: str) -> Dict[str, Any]:
    """Rename a channel by index."""
    return client.call(  # type: ignore[return-value]
        "channels.rename", index=index, name=name
    )


def set_color(client: DAWClient, index: int, color: int) -> Dict[str, Any]:
    """Set channel color (RGB integer, e.g. ``0xFF0000`` for red)."""
    return client.call(  # type: ignore[return-value]
        "channels.set_color", index=index, color=color
    )


def get_step(client: DAWClient, channel: int, step: int) -> Dict[str, Any]:
    """Get a single step sequencer cell state."""
    return client.call(  # type: ignore[return-value]
        "channels.get_step", channel=channel, step=step
    )


def set_step(client: DAWClient, channel: int, step: int, active: bool) -> Dict[str, Any]:
    """Set a single step sequencer cell on or off."""
    return client.call(  # type: ignore[return-value]
        "channels.set_step", channel=channel, step=step, active=active
    )


def get_step_pattern(client: DAWClient, channel: int, length: int = 16) -> Dict[str, Any]:
    """Get the full step sequencer pattern for a channel.

    Args:
        channel: Channel index.
        length: Number of steps to read (default 16).
    """
    return client.call(  # type: ignore[return-value]
        "channels.get_step_pattern", channel=channel, length=length
    )


def set_step_pattern(
    client: DAWClient, channel: int, steps: List[bool]
) -> Dict[str, Any]:
    """Set multiple step sequencer cells at once.

    Args:
        channel: Channel index.
        steps: List of booleans (True = active) for each step.
    """
    return client.call(  # type: ignore[return-value]
        "channels.set_step_pattern", channel=channel, steps=steps
    )
