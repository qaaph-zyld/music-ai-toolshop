"""Probe a single plugin in a subprocess — run by ``probe.py``.

    python -m toolshop.fx.probe_one --path <plugin> [--plugin-name N] \
        [--seconds 1.5] [--sr 48000]

Prints exactly one line of JSON on stdout describing the outcome. The parent
isolates each probe in a subprocess because a misbehaving plugin can crash
the interpreter outright (see pedalboard's compatibility notes) — and on this
machine bare-loading WaveShell was measured to hang for minutes, so the
parent also enforces a hard timeout.

Probe signal: a level staircase of 440 Hz sines (-40/-24/-12/-6 dBFS) plus an
impulse and a short noise burst, then silence. A flat sine would pass through
a below-threshold compressor unchanged and false-report a healthy plugin as
``dry``; the staircase is designed to exercise dynamics, EQ, distortion, and
reverb tails.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any, Dict

import numpy as np


def make_probe_signal(sr: int, seconds: float = 1.5) -> np.ndarray:
    """Level staircase + impulse + noise burst + silence tail, stereo float32."""
    n = int(sr * seconds)
    t = np.arange(n) / sr
    x = np.zeros(n, dtype=np.float64)

    seg = n // 4
    levels_db = (-40.0, -24.0, -12.0, -6.0)
    for i, lvl in enumerate(levels_db):
        s = slice(i * seg, (i + 1) * seg)
        x[s] += np.sin(2 * np.pi * 440 * t[s]) * (10 ** (lvl / 20))
    # impulse at 3/4 point (latency estimate + reverb tail)
    x[int(0.8 * n)] = 0.9
    # noise burst
    rng = np.random.default_rng(7)
    b = slice(int(0.82 * n), int(0.9 * n))
    x[b] += rng.standard_normal(b.stop - b.start) * 0.05
    return np.stack([x, x], axis=1).astype(np.float32)


def _db(v: float) -> float:
    return float(20 * np.log10(max(abs(v), 1e-12)))


def probe(path: str, plugin_name: str | None, seconds: float, sr: int) -> Dict[str, Any]:
    """Load the plugin, render the probe signal, report measurements."""
    out: Dict[str, Any] = {
        "path": path,
        "plugin_name": plugin_name,
        "status": "error",
        "load_s": None,
        "param_count": 0,
        "parameters": {},
        "max_abs_delta_db": None,
        "wet_rms_dbfs": None,
        "dry_rms_dbfs": None,
        "verdict": None,
        "error": None,
    }
    try:
        import pedalboard  # noqa: WPS433 — deferred so import cost is inside the child
    except ImportError:
        out["error"] = "pedalboard not installed"
        return out

    t0 = time.monotonic()
    try:
        kwargs: Dict[str, Any] = {"initialization_timeout": 60.0}
        if plugin_name:
            kwargs["plugin_name"] = plugin_name
        plugin = pedalboard.load_plugin(path, **kwargs)
    except Exception as exc:
        out["error"] = f"{exc.__class__.__name__}: {exc}"
        out["verdict"] = "load-failed"
        out["load_s"] = round(time.monotonic() - t0, 3)
        return out
    out["load_s"] = round(time.monotonic() - t0, 3)

    try:
        params = getattr(plugin, "parameters", {}) or {}
        out["parameters"] = {k: getattr(plugin, k, None) for k in params.keys()}
        out["param_count"] = len(params)
    except Exception as exc:
        out["error"] = f"param-enum {exc.__class__.__name__}: {exc}"

    x = make_probe_signal(sr, seconds)
    try:
        t1 = time.monotonic()
        wet = plugin(x, sr, reset=True)
        out["render_s"] = round(time.monotonic() - t1, 3)
    except Exception as exc:
        out["error"] = f"render {exc.__class__.__name__}: {exc}"
        out["verdict"] = "render-failed"
        return out

    n = min(len(x), len(wet))
    dry = x[:n]
    delta = np.max(np.abs(wet[:n].astype(np.float64) - dry.astype(np.float64)))
    out["max_abs_delta_db"] = round(_db(float(delta)), 2)
    out["wet_rms_dbfs"] = round(_db(float(np.sqrt(np.mean(wet.astype(np.float64) ** 2)))), 2)
    out["dry_rms_dbfs"] = round(_db(float(np.sqrt(np.mean(dry.astype(np.float64) ** 2)))), 2)

    # >-80 dBFS of difference counts as "the plugin touched the audio".
    out["verdict"] = "ok" if out["max_abs_delta_db"] > -80.0 else "dry"
    out["status"] = "probed"
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="toolshop.fx.probe_one")
    ap.add_argument("--path", required=True)
    ap.add_argument("--plugin-name", default=None)
    ap.add_argument("--seconds", type=float, default=1.5)
    ap.add_argument("--sr", type=int, default=48000)
    args = ap.parse_args(argv)

    result = probe(args.path, args.plugin_name, args.seconds, args.sr)
    sys.stdout.write(json.dumps(result, default=str) + "\n")
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
