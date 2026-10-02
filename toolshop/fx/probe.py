"""Probe orchestrator — runs ``probe_one`` per registry entry in a subprocess.

Each probe is a child process because a plugin crash is fatal to whatever
process hosts it; the parent survives, records the crash, and moves on.
Results merge into ``plugin_registry.json`` incrementally so an interrupted
audit resumes where it stopped (``--force`` re-probes everything).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from toolshop import paths

DEFAULT_TIMEOUT_S = 60.0
SHELL_TIMEOUT_S = 120.0  # shell packages (Waves, Kontakt) load whole collections

PROBES_NAME = "plugin_probes.json"


def probes_path() -> Path:
    return paths.subdir("fx") / PROBES_NAME


def _probed_keys(probe_db: Dict[str, Any]) -> set:
    return {
        (r.get("name", "").lower(), r.get("path", "").lower())
        for r in probe_db.get("results", [])
    }


def load_probe_db() -> Dict[str, Any]:
    p = probes_path()
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"version": 1, "results": []}


def save_probe_db(db: Dict[str, Any]) -> Path:
    p = probes_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(db, indent=2, ensure_ascii=False, default=str),
                 encoding="utf-8")
    return p


def probe_entry(entry: Dict[str, Any], timeout_s: float) -> Dict[str, Any]:
    """Run probe_one for one registry entry; never raises on plugin failure."""
    cmd = [
        sys.executable, "-m", "toolshop.fx.probe_one",
        "--path", entry["path"],
        "--seconds", "1.5",
    ]
    if entry.get("plugin_name"):
        cmd += ["--plugin-name", entry["plugin_name"]]

    env = dict(os.environ)
    root = str(paths.REPO_ROOT)
    env["PYTHONPATH"] = root + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONIOENCODING"] = "utf-8"

    t0 = time.monotonic()
    try:
        cp = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=timeout_s, cwd=root, env=env,
        )
    except subprocess.TimeoutExpired:
        return {
            "name": entry["name"], "path": entry["path"],
            "status": "timeout", "verdict": "timeout",
            "wall_s": round(time.monotonic() - t0, 3),
        }
    except Exception as exc:  # spawn-level failure
        return {
            "name": entry["name"], "path": entry["path"],
            "status": "spawn-error", "verdict": "error",
            "error": f"{exc.__class__.__name__}: {exc}",
            "wall_s": round(time.monotonic() - t0, 3),
        }

    wall = round(time.monotonic() - t0, 3)
    line = ""
    if cp.stdout:
        lines = [l for l in cp.stdout.splitlines() if l.strip()]
        line = lines[-1] if lines else ""

    if cp.returncode != 0:
        return {
            "name": entry["name"], "path": entry["path"],
            "status": "crash", "verdict": "crash",
            "returncode": cp.returncode,
            "stderr_tail": (cp.stderr or "")[-500:],
            "wall_s": wall,
        }

    try:
        result = json.loads(line)
    except json.JSONDecodeError:
        return {
            "name": entry["name"], "path": entry["path"],
            "status": "crash", "verdict": "no-output",
            "stdout_tail": (cp.stdout or "")[-500:],
            "stderr_tail": (cp.stderr or "")[-500:],
            "wall_s": wall,
        }

    result.update({
        "name": entry["name"],
        "path": entry["path"],
        "format": entry.get("format"),
        "shell": entry.get("shell"),
        "wall_s": wall,
    })
    result.setdefault("status", "probed")
    return result


def probe_all(
    reg: Dict[str, Any],
    *,
    only: Optional[str] = None,
    force: bool = False,
    limit: int = 0,
    progress: Optional[Callable[[str], None]] = print,
) -> Dict[str, Any]:
    """Probe every hostable plugin in the registry. Returns the probe DB."""
    db = load_probe_db() if not force else {"version": 1, "results": []}
    done = _probed_keys(db)

    # hostable=vst3 or vst3-shell members (probed with plugin_name);
    # shell package entries themselves are hostable=False.
    candidates: List[Dict[str, Any]] = [
        p for p in reg.get("plugins", []) if p.get("hostable")
    ]
    if only:
        candidates = [p for p in candidates if p["name"].lower() == only.lower()]
    if limit > 0:
        candidates = candidates[:limit]

    total = len(candidates)
    for idx, entry in enumerate(candidates):
        key = (entry["name"].lower(), entry["path"].lower())
        if key in done:
            if progress:
                progress(f"[{idx + 1}/{total}] SKIP probed: {entry['name']}")
            continue

        timeout = SHELL_TIMEOUT_S if entry.get("shell") else DEFAULT_TIMEOUT_S
        if progress:
            progress(f"[{idx + 1}/{total}] probe: {entry['name']}")
        result = probe_entry(entry, timeout)
        # Replace any prior result for this key (re-probe on failure retried)
        db["results"] = [
            r for r in db["results"]
            if (r.get("name", "").lower(), r.get("path", "").lower()) != key
        ]
        db["results"].append(result)
        save_probe_db(db)
        if progress:
            progress(f"    -> {result.get('verdict')} ({result.get('wall_s')}s)")

    return db


def merge_probe_into_registry(reg: Dict[str, Any], db: Dict[str, Any]) -> Dict[str, Any]:
    """Attach probe results back onto registry entries by (name, path)."""
    by_key = {
        (r.get("name", "").lower(), r.get("path", "").lower()): r
        for r in db.get("results", [])
    }
    for p in reg.get("plugins", []):
        key = (p["name"].lower(), p["path"].lower())
        if key in by_key:
            p["probe"] = by_key[key]
    return reg
