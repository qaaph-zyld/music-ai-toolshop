"""Plugin discovery and parameter control.

Provides functions to list installed plugins, get/set plugin parameters on
mixer track FX slots, and inspect parameter names and counts.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from .client import DAWClient


def list_plugins() -> List[Dict[str, Any]]:
    """Scan FL Studio plugin directories on disk for installed plugins.

    Searches common FL plugin locations for ``.dll``, ``.vst3``, and ``.fxb`` files.
    No DAW connection required — this is a local filesystem scan.
    """
    plugin_dirs = _get_plugin_directories()
    plugins: List[Dict[str, Any]] = []
    seen = set()

    extensions = {".dll", ".vst3", ".fxb"}
    for plugin_dir in plugin_dirs:
        if not plugin_dir.exists():
            continue
        for item in plugin_dir.rglob("*"):
            if item.suffix.lower() in extensions and item.is_file():
                name = item.stem
                if name.lower() not in seen:
                    seen.add(name.lower())
                    plugins.append({
                        "name": name,
                        "path": str(item),
                        "format": item.suffix.lower().lstrip("."),
                    })

    plugins.sort(key=lambda p: p["name"].lower())
    return plugins


def _get_plugin_directories() -> List[Path]:
    """Return common FL Studio plugin directories."""
    dirs: List[Path] = []
    user_profile = os.environ.get("USERPROFILE", "")

    # Standard FL Studio plugin folders
    candidates = [
        Path(user_profile) / "Documents" / "Image-Line" / "FL Studio" / "Presets" / "Plugin database" / "Installed",
        Path("C:/Program Files") / "VstPlugins",
        Path("C:/Program Files") / "Common Files" / "VST3",
        Path("C:/Program Files") / "Steinberg" / "VstPlugins",
        Path("C:/Program Files (x86)") / "VstPlugins",
        Path("C:/Program Files (x86)") / "Common Files" / "VST3",
        Path("C:/Program Files (x86)") / "Steinberg" / "VstPlugins",
    ]

    # FL custom plugin folder (from registry or env)
    fl_plugin_env = os.environ.get("FLSTUDIO_VST_PLUGINS", "")
    if fl_plugin_env:
        for p in fl_plugin_env.split(";"):
            p = p.strip()
            if p:
                dirs.append(Path(p))

    dirs.extend(candidates)
    return dirs


def get_param(
    client: DAWClient, track: int, slot: int, param_index: int
) -> Dict[str, Any]:
    """Get a plugin parameter value on a mixer track FX slot."""
    return client.call(  # type: ignore[return-value]
        "plugins.get_param", track=track, slot=slot, param_index=param_index
    )


def set_param(
    client: DAWClient, track: int, slot: int, param_index: int, value: float
) -> Dict[str, Any]:
    """Set a plugin parameter value on a mixer track FX slot."""
    return client.call(  # type: ignore[return-value]
        "plugins.set_param",
        track=track,
        slot=slot,
        param_index=param_index,
        value=value,
    )


def get_param_count(client: DAWClient, track: int, slot: int) -> Dict[str, Any]:
    """Get the number of parameters for a plugin on a mixer track FX slot."""
    return client.call(  # type: ignore[return-value]
        "plugins.get_param_count", track=track, slot=slot
    )


def get_param_name(
    client: DAWClient, track: int, slot: int, param_index: int
) -> Dict[str, Any]:
    """Get the name of a plugin parameter by index."""
    return client.call(  # type: ignore[return-value]
        "plugins.get_param_name", track=track, slot=slot, param_index=param_index
    )


def get_all_params(client: DAWClient, track: int, slot: int) -> List[Dict[str, Any]]:
    """Get all parameters for a plugin on a mixer track FX slot.

    Convenience function that fetches param count then iterates.
    """
    count_result = get_param_count(client, track, slot)
    count = count_result.get("param_count", 0)
    params: List[Dict[str, Any]] = []
    for i in range(count):
        name_result = get_param_name(client, track, slot, i)
        value_result = get_param(client, track, slot, i)
        params.append({
            "index": i,
            "name": name_result.get("name", f"Param {i}"),
            "value": value_result.get("value", 0.0),
        })
    return params
