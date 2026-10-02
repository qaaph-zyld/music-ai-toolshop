"""Plugin registry — filesystem scan of the installed plugin arsenal.

**The registry never loads a plugin.** Scanning is pure filesystem: it walks
the standard VST2/VST3 roots (shared with ``toolshop.daw.plugins``) plus the
Waves ``Plug-Ins V*`` bundle directory. Bare-loading a plugin package just to
enumerate it is unsafe — measured on this machine, ``load_plugin`` on
WaveShell 14.12 hangs for minutes (license check / plugin enumeration), so
Waves plugins are enumerated from their ``*.bundle`` directory names and
resolved to shell + ``plugin_name`` at render time instead.

Registry record fields:

- ``name``          display name ("FabFilter Pro-Q 3", "API-2500")
- ``path``          the file pedalboard should load
- ``format``        ``vst3`` | ``vst2`` | ``vst3-shell``
- ``plugin_name``   selector inside a multi-plugin package (Waves)
- ``shell``         e.g. ``"waves"`` when ``path`` is a shell package
- ``hostable``      False for formats pedalboard cannot host (vst2)
- ``vendor``        best-effort guess from the containing directory
- ``probe``         filled in by ``probe.py`` (status, params, verdict)
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from toolshop.daw import plugins as daw_plugins
from toolshop import paths

REGISTRY_NAME = "plugin_registry.json"
REGISTRY_VERSION = 1

_PLUGIN_EXTS = {".vst3", ".dll", ".fxb"}

# Waves ships one .bundle directory per plugin under Plug-Ins V<N>; the
# matching WaveShell .vst3/.dll is the file a host actually loads.
_WAVES_BUNDLE_DIR = Path(r"C:\Program Files (x86)\Waves\Plug-Ins V14")
_WAVES_SHELL_RE = re.compile(r"^waveshell\d+-vst3 .*_x64\.vst3$", re.IGNORECASE)

#: Directories that hold vendor bundles rather than single plugin files —
#: their children are directories (or .vst3 bundles) we descend into anyway
#: via rglob, so no special-casing is needed.


def _vendor_guess(path: Path, root: Path) -> Optional[str]:
    """Best-effort vendor from the first directory level under the scan root."""
    try:
        rel = path.relative_to(root)
    except ValueError:
        return None
    if len(rel.parts) > 1:
        return rel.parts[0]
    return None


def registry_path() -> Path:
    """Absolute path to the registry JSON (untracked data dir)."""
    return paths.subdir("fx") / REGISTRY_NAME


def _scan_entry(path: Path, root: Path) -> Dict[str, Any]:
    fmt = path.suffix.lower().lstrip(".")
    if fmt == "dll" or fmt == "fxb":
        fmt = "vst2"
    return {
        "name": path.stem,
        "path": str(path),
        "format": fmt,
        "vendor": _vendor_guess(path, root),
        "shell": None,
        "plugin_name": None,
        "size": path.stat().st_size,
        "mtime": path.stat().st_mtime,
        "hostable": fmt == "vst3",
        "host_note": None if fmt == "vst3" else "vst2 needs a VST2 host (deferred)",
        "probe": None,
        "source": "dir-scan",
    }


def _waves_shell_path(roots: List[Path]) -> Optional[Path]:
    """Find the newest WaveShell VST3 on disk (e.g. WaveShell1-VST3 14.12_x64)."""
    best: Optional[Path] = None
    for root in roots:
        if not root.is_dir():
            continue
        for item in root.glob("WaveShell*-VST3*.vst3"):
            if best is None or item.name.lower() > best.name.lower():
                best = item
    return best


def _scan_waves(shell: Path, bundle_dir: Path = _WAVES_BUNDLE_DIR) -> List[Dict[str, Any]]:
    """Enumerate Waves plugins from the Plug-Ins bundle dir — no shell load."""
    if not bundle_dir.is_dir():
        return []
    entries: List[Dict[str, Any]] = []
    for bundle in sorted(bundle_dir.glob("*.bundle")):
        entries.append({
            "name": bundle.stem,
            "path": str(shell),
            "format": "vst3-shell",
            "vendor": "Waves",
            "shell": "waves",
            "plugin_name": bundle.stem,
            "size": shell.stat().st_size,
            "mtime": shell.stat().st_mtime,
            "hostable": True,
            "host_note": "waveShell member — load with plugin_name only",
            "probe": None,
            "source": "waves-bundles",
        })
    return entries


def scan(
    roots: Optional[List[Path]] = None,
    waves_bundle_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Walk the plugin roots and return the registry dict (does not write).

    Entries are deduplicated by (name, path). Waves bundles become
    ``vst3-shell`` entries pointing at the newest WaveShell found in the
    scanned roots; if no shell is present, Waves entries are skipped.

    ``roots``/``waves_bundle_dir`` overrides exist for tests.
    """
    roots = [
        p for p in (roots if roots is not None else daw_plugins.plugin_directories())
        if p.is_dir()
    ]
    plugins: List[Dict[str, Any]] = []
    seen = set()

    for root in roots:
        for item in sorted(root.rglob("*")):
            try:
                rel_parts = item.relative_to(root).parts
            except ValueError:
                continue
            # A .vst3 is a bundle DIRECTORY on Windows; the actual binary
            # lives at Contents/<arch>/<name>.vst3 inside it. Register the
            # outer bundle, skip everything nested inside any bundle.
            if any(p.lower().endswith(".vst3") for p in rel_parts[:-1]):
                continue
            if item.is_dir():
                if item.suffix.lower() != ".vst3":
                    continue
            elif item.suffix.lower() not in _PLUGIN_EXTS:
                continue
            entry = _scan_entry(item, root)
            key = (entry["name"].lower(), entry["path"].lower())
            if key in seen:
                continue
            seen.add(key)
            if _WAVES_SHELL_RE.match(item.name):
                # The shell itself is not a usable plugin entry — its members
                # are enumerated separately from the bundle directory.
                entry["shell"] = "waves"
                entry["hostable"] = False
                entry["host_note"] = "waveShell package — load members via plugin_name"
            plugins.append(entry)

    shell = _waves_shell_path(roots)
    if shell is not None:
        plugins.extend(
            _scan_waves(shell, waves_bundle_dir or _WAVES_BUNDLE_DIR)
        )

    plugins.sort(key=lambda p: (p["name"].lower(), p["path"].lower()))
    return {
        "version": REGISTRY_VERSION,
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "scan_roots": [str(p) for p in roots],
        "plugins": plugins,
    }


def write(reg: Optional[Dict[str, Any]] = None) -> Path:
    """Scan (or take a supplied registry dict) and write the registry JSON."""
    reg = scan() if reg is None else reg
    out = registry_path()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(reg, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


def load() -> Dict[str, Any]:
    """Load the registry JSON; scan fresh if missing."""
    path = registry_path()
    if not path.exists():
        return scan()
    return json.loads(path.read_text(encoding="utf-8"))


def save(reg: Dict[str, Any]) -> Path:
    """Write a registry dict (e.g. after merging probe results)."""
    out = registry_path()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(reg, indent=2, ensure_ascii=False), encoding="utf-8")
    return out


def find_plugin(reg: Dict[str, Any], name: str) -> Dict[str, Any]:
    """Resolve a chain ``plugin:`` name to a registry entry.

    Accepts the entry ``name`` exactly (case-insensitive), or
    ``"<vendor>/<name>"`` for disambiguation. Raises ``PluginNotFoundError``
    listing close matches when nothing resolves.
    """
    plugins = reg.get("plugins", [])
    query = name.strip()

    if "/" in query:
        vendor, _, leaf = query.partition("/")
        vend, leaf = vendor.strip().lower(), leaf.strip().lower()
        hits = [
            p for p in plugins
            if p["name"].lower() == leaf
            and (p.get("vendor") or "").lower() == vend
        ]
    else:
        hits = [p for p in plugins if p["name"].lower() == query.lower()]

    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        # Prefer hostable entries, then vst3 over vst2.
        hostable = [h for h in hits if h.get("hostable")]
        pool = hostable or hits
        pool.sort(key=lambda p: (p["format"] != "vst3", len(p["path"])))
        return pool[0]

    names = sorted({p["name"] for p in plugins})
    close = [n for n in names if query.lower() in n.lower() or n.lower() in query.lower()]
    raise PluginNotFoundError(
        f"plugin not found in registry: {name!r}. "
        f"{'Close matches: ' + ', '.join(close[:10]) if close else 'Run `toolshop fx scan` first.'}"
    )


class PluginNotFoundError(KeyError):
    """A chain named a plugin that is not in the registry."""
