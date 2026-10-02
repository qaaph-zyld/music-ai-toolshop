"""Resumable batch rendering — thin adapter over ``toolshop.batch``.

Each file renders through the chain via ``engine.render_file`` into
``<output_dir>/<slug>.wav``; plugin instances are cached across files unless
a stage is marked ``stateful``. Failed files are retried on the next run
(batch.py semantics); completed files are skipped.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from toolshop import batch as batch_mod
from .chain import FXChain
from . import engine

DEFAULT_EXTENSIONS = ["wav", "mp3", "flac", "m4a", "ogg"]


def run_fx_batch(
    chain: FXChain,
    reg: Dict[str, Any],
    input_dir: Path,
    output_dir: Path,
    *,
    extensions: Optional[List[str]] = None,
    limit: int = 0,
    offset: int = 0,
    resume: bool = True,
) -> Dict[str, Any]:
    """Render every audio file under ``input_dir`` through ``chain``."""
    files = batch_mod.discover_files(
        input_dir, extensions or DEFAULT_EXTENSIONS, limit=limit, offset=offset
    )
    cache: Dict[str, Any] = {}

    def process(file_path: Path) -> Dict[str, Any]:
        out = output_dir / f"{batch_mod.safe_slug(file_path.name)}.wav"
        result = engine.render_file(chain, reg, file_path, out, cache=cache)
        result["status"] = "completed"
        return result

    return batch_mod.run_batch(
        files,
        output_dir,
        process,
        resume=resume,
        offset=offset,
        description=f"fx:{chain.name}",
    )
