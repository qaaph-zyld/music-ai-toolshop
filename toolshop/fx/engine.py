"""Engine — render FXChains through pedalboard-hosted VST3 plugins.

Builtin stages reuse ``mastering_tool.tools.chain_dsl`` field names and the
``pedalboard_exec`` executor: each builtin stage is wrapped as a one-stage
``Chain`` so the existing validation (``UnsupportedParameterError`` for
params pedalboard cannot honour) is reused rather than reimplemented.

Plugin stages call ``pedalboard.load_plugin`` with the registry-resolved
path and, for shell members (Waves), ``plugin_name``. **Never bare-load a
shell package** — measured on this machine to hang >3 minutes.

Input files are always resampled to the chain's sample rate; hard-failing on
44.1 kHz source audio would reject most real-world files.
"""

from __future__ import annotations

import dataclasses
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from toolshop import paths
from .chain import BUILTIN_STAGES, ChainSpecError, FXChain, FXStage

try:
    import pedalboard  # type: ignore
    _HAS_PEDALBOARD = True
except ImportError:  # pragma: no cover
    pedalboard = None  # type: ignore
    _HAS_PEDALBOARD = False

TAIL_SECONDS = 0.5
DEFAULT_INIT_TIMEOUT = 120.0
DRY_FLOOR_DB = -80.0


def _require_pedalboard() -> None:
    if not _HAS_PEDALBOARD:
        raise RuntimeError("pedalboard is required: pip install pedalboard")


class DryRenderError(RuntimeError):
    """assert_wet fired: the rendered output is indistinguishable from input.

    On Windows some VST3s have been observed to load, expose parameters, and
    return the dry signal unchanged (pedalboard #321). This error exists so a
    batch job surfaces that failure instead of silently "processing" files.
    """


def _db(v: float) -> float:
    return float(20 * np.log10(max(abs(v), 1e-12)))


# ---------------------------------------------------------------------------
# Stage construction
# ---------------------------------------------------------------------------

def _builtin_board(stage: FXStage, sample_rate: float) -> "pedalboard.Plugin":
    """Build a one-stage pedalboard via the chain_dsl executor."""
    from mastering_tool.tools.chain_dsl.schema import (  # noqa: WPS433
        Chain, Compressor, Clipper, Deesser, EQ, EQBand, HPF, Limiter,
    )
    from mastering_tool.tools.chain_dsl.executors import (  # noqa: WPS433
        pedalboard_exec,
    )

    stage_cls = {
        "hpf": HPF, "eq": EQ, "deesser": Deesser,
        "comp": Compressor, "clip": Clipper, "limit": Limiter,
    }[stage.builtin or ""]

    kwargs = dict(stage.params)
    if stage.builtin == "eq":
        bands = kwargs.pop("bands", [])
        kwargs["bands"] = [
            b if isinstance(b, EQBand) else EQBand(**b) for b in bands
        ]
    kwargs["bypass"] = False
    try:
        stage_obj = stage_cls(**kwargs)
    except TypeError as exc:
        valid = [f.name for f in dataclasses.fields(stage_cls) if f.name != "bypass"]
        raise ChainSpecError(
            f"builtin {stage.builtin!r}: bad params {exc}. Valid: {', '.join(valid)}"
        ) from exc
    chain = Chain(sample_rate=sample_rate, **{stage.builtin: stage_obj})
    return pedalboard_exec.build_pedalboard(chain)


def load_plugin_stage(
    stage: FXStage,
    entry: Dict[str, Any],
    init_timeout: float = DEFAULT_INIT_TIMEOUT,
) -> "pedalboard.Plugin":
    """load_plugin for one resolved registry entry."""
    _require_pedalboard()
    kwargs: Dict[str, Any] = {"initialization_timeout": init_timeout}
    plugin_name = stage.plugin_name or entry.get("plugin_name")
    if plugin_name:
        kwargs["plugin_name"] = plugin_name
    try:
        return pedalboard.load_plugin(entry["path"], **kwargs)
    except Exception as exc:
        raise ChainSpecError(
            f"failed to load {entry['name']!r} ({entry['path']}): "
            f"{exc.__class__.__name__}: {exc}"
        ) from exc


def set_plugin_params(plugin: Any, params: Dict[str, Any]) -> None:
    """Set named params on a loaded plugin; unknown names are hard errors."""
    available = set(getattr(plugin, "parameters", {}) or {})
    unknown = [k for k in params if k not in available]
    if unknown:
        raise ChainSpecError(
            f"unknown param(s) {unknown}; "
            f"valid: {sorted(available)[:40]}"
        )
    for key, value in params.items():
        setattr(plugin, key, value)


def build_stage(
    stage: FXStage,
    entry: Optional[Dict[str, Any]],
    sample_rate: float,
) -> "pedalboard.Plugin":
    """Construct the pedalboard Plugin (or nested board) for one stage."""
    if stage.builtin:
        return _builtin_board(stage, sample_rate)
    assert entry is not None
    plugin = load_plugin_stage(stage, entry)
    set_plugin_params(plugin, stage.params)
    return plugin


def build_board(
    chain: FXChain,
    reg: Dict[str, Any],
    cache: Optional[Dict[str, Any]] = None,
) -> "pedalboard.Pedalboard":
    """Assemble the Pedalboard for a chain; ``cache`` reuses plugin instances
    across files in a batch (stages marked ``stateful`` are never cached)."""
    _require_pedalboard()
    from .registry import find_plugin

    cache = cache if cache is not None else {}
    plugins: List[Any] = []
    for stage in chain.stages:
        if stage.bypass:
            continue
        if stage.builtin:
            plugins.append(_builtin_board(stage, chain.sample_rate))
            continue

        entry = find_plugin(reg, stage.plugin or "")
        key = f"{entry['path']}|{stage.plugin_name or entry.get('plugin_name') or ''}"
        if stage.stateful or key not in cache:
            cache[key] = load_plugin_stage(stage, entry)
        plugin = cache[key]
        set_plugin_params(plugin, stage.params)
        plugins.append(plugin)
    return pedalboard.Pedalboard(plugins)


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render(
    chain: FXChain,
    reg: Dict[str, Any],
    audio: np.ndarray,
    cache: Optional[Dict[str, Any]] = None,
) -> np.ndarray:
    """Render ``audio`` (n_samples[, n_ch] float32) through the chain.

    The input is padded with TAIL_SECONDS of silence so delays and reverb
    tails are captured rather than truncated.
    """
    _require_pedalboard()
    sr = int(chain.sample_rate)
    board = build_board(chain, reg, cache)

    tail = np.zeros((int(sr * TAIL_SECONDS),) + audio.shape[1:], dtype=audio.dtype)
    padded = np.concatenate([audio.astype(np.float32), tail], axis=0)
    wet = board(padded, sr, reset=True)

    if chain.assert_wet and chain.stages and any(s.active() for s in chain.stages):
        n = min(len(padded), len(wet))
        delta = np.max(np.abs(
            wet[:n].astype(np.float64) - padded[:n].astype(np.float64)
        ))
        if _db(float(delta)) <= DRY_FLOOR_DB:
            raise DryRenderError(
                f"chain {chain.name!r} rendered dry audio "
                f"(max|delta| {_db(float(delta)):.1f} dBFS <= {DRY_FLOOR_DB})"
            )
    return wet


def render_file(
    chain: FXChain,
    reg: Dict[str, Any],
    input_path: Path | str,
    output_path: Path | str,
    cache: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Load audio, resample to chain SR, render, write float32 WAV.

    Returns a result dict with render evidence (delta in dBFS, wall time).
    """
    _require_pedalboard()
    import librosa  # noqa: WPS433
    import soundfile as sf  # noqa: WPS433

    sr = int(chain.sample_rate)
    audio, file_sr = sf.read(str(input_path), dtype="float32", always_2d=True)
    if file_sr != sr:
        audio = librosa.resample(
            audio.T, orig_sr=file_sr, target_sr=sr
        ).T.astype(np.float32)

    t0 = time.monotonic()
    wet = render(chain, reg, audio, cache)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(out), wet, sr, subtype="FLOAT")

    n = min(len(audio), len(wet))
    delta_db = _db(float(np.max(np.abs(
        wet[:n] - np.concatenate(
            [audio, np.zeros((len(wet) - len(audio), audio.shape[1]), np.float32)],
            axis=0)[:n]
    )))) if n else float("-inf")

    return {
        "status": "completed",
        "input": str(input_path),
        "output": str(out),
        "chain": chain.name,
        "in_sr": file_sr,
        "render_s": round(time.monotonic() - t0, 3),
        "max_abs_delta_db": round(delta_db, 2),
    }
