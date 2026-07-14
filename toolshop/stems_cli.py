"""Handler for the unified `toolshop stems` command."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import batch, stem_extractor_adapter, stem_models

logger = logging.getLogger(__name__)


def _default_data_root() -> Path:
    return Path(os.environ.get("TOOLSHOP_DATA_DIR", r"D:\MusicData\toolshop"))


def _toolshop_version() -> str:
    """Read version from pyproject.toml or return a fallback."""
    try:
        import tomllib  # Python 3.11+
    except ImportError:  # pragma: no cover
        return "unknown"
    repo_root = Path(__file__).resolve().parent.parent
    pyproject = repo_root / "pyproject.toml"
    if not pyproject.exists():
        return "unknown"
    try:
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        return data.get("project", {}).get("version", "unknown")
    except Exception:
        return "unknown"


def _file_hash(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.name.encode("utf-8"))
    try:
        h.update(str(path.stat().st_size).encode("utf-8"))
    except Exception:
        pass
    return h.hexdigest()[:16]


def _write_manifest(
    source: Path,
    output_dir: Path,
    result: Dict[str, Any],
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "version": _toolshop_version(),
        "created": datetime.now().isoformat(),
        "source": str(source),
        "source_hash": _file_hash(source),
        "preset": result.get("preset"),
        "models": result.get("models_used", []),
        "gpu_used": result.get("gpu_used", False),
        "output_format": result.get("output_format", "wav"),
        "stems": result.get("stems", {}),
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
    return manifest_path


def _build_output_dir(
    path: Path,
    preset_id: str,
    output_dir: Optional[Path],
    data_root: Optional[Path],
) -> Path:
    if output_dir:
        return output_dir
    root = data_root or _default_data_root()
    slug = batch.safe_slug(path.name)
    return root / "stems" / preset_id / slug


def _process_one(
    input_path: Path,
    *,
    preset_id: str,
    output_dir: Path,
    device: str,
    output_format: Optional[str],
    model_file_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    use_gpu = device == "gpu"
    if use_gpu:
        logging.warning(
            "GPU separation requested but this machine's GT 640 is unsupported; "
            "falling back to CPU."
        )
        use_gpu = False

    preset = stem_models.get_preset(preset_id)
    first_model = stem_models.get_model(preset.steps[0].model_id)

    if first_model.backend == "demucs":
        from . import demucs_adapter

        result = demucs_adapter.separate(
            input_file=input_path,
            model_id=first_model.id,
            output_dir=output_dir,
            output_format=output_format or "flac",
            device="cuda" if use_gpu else "cpu",
        )
    else:
        result = stem_extractor_adapter.extract_stems_preset(
            input_file=input_path,
            preset_id=preset_id,
            output_dir=output_dir,
            use_gpu=use_gpu,
            output_format=output_format,
            model_file_dir=model_file_dir,
        )

    result["preset"] = preset_id
    result["status"] = "completed"
    _write_manifest(input_path, output_dir, result)
    return result


def _process_one_for_batch(input_path: Path, args: Any) -> Dict[str, Any]:
    output_dir = _build_output_dir(
        input_path, args.preset, args.out, args.data_root
    )
    return _process_one(
        input_path,
        preset_id=args.preset,
        output_dir=output_dir,
        device=args.device,
        output_format=args.format,
        model_file_dir=args.model_file_dir,
    )


def _list_models() -> None:
    print("Available presets:")
    for preset_id in stem_models.list_presets():
        preset = stem_models.get_preset(preset_id)
        print(f"  {preset_id:<18} {preset.description}")
    print()
    print("Registered models:")
    for model_id in stem_models.list_models():
        model = stem_models.get_model(model_id)
        installed = "?"
        print(f"  {model_id:<25} backend={model.backend:<16} file={model.model_file} installed={installed}")


def _print_result(result: Dict[str, Any]) -> None:
    print(f"Extracted stems from {result['input_file']}")
    print(f"  Preset: {result.get('preset')}")
    print(f"  Output: {result.get('output_dir')}")
    print(f"  Format: {result.get('output_format')}")
    print(f"  GPU: {result.get('gpu_used')}")
    for stem_name, stem_path in result.get("stems", {}).items():
        if stem_path:
            print(f"  {stem_name}: {Path(stem_path).name}")


def run(args: Any) -> int:
    """Entry point for `toolshop stems`."""
    if args.list_models:
        _list_models()
        return 0

    preset_id = args.preset
    try:
        stem_models.get_preset(preset_id)
    except KeyError:
        print(f"Unknown preset: {preset_id}", file=sys.stderr)
        print(f"Run 'toolshop stems --list-models' to see presets.", file=sys.stderr)
        return 1

    input_path = Path(args.path)
    if not input_path.exists():
        print(f"Path not found: {input_path}", file=sys.stderr)
        return 1

    if input_path.is_file():
        output_dir = _build_output_dir(
            input_path, preset_id, args.out, args.data_root
        )
        result = _process_one(
            input_path,
            preset_id=preset_id,
            output_dir=output_dir,
            device=args.device,
            output_format=args.format,
            model_file_dir=args.model_file_dir,
        )
        if args.json:
            print(json.dumps(result, indent=2, default=str))
        else:
            _print_result(result)
        return 0

    # Directory / batch mode.
    files = batch.discover_files(
        input_path,
        extensions=["wav", "mp3", "flac"],
        limit=args.limit or 0,
        offset=args.offset or 0,
    )
    if not files:
        print(f"No audio files found in {input_path}", file=sys.stderr)
        return 1

    output_root = args.out or _default_data_root() / "stems" / preset_id
    status = batch.run_batch(
        files=files,
        output_dir=output_root,
        process=lambda p: _process_one_for_batch(p, args),
        resume=args.resume,
        offset=args.offset or 0,
        description=f"stems/{preset_id}",
    )

    completed = sum(1 for t in status.get("tracks", []) if t["status"] == "completed")
    failed = sum(1 for t in status.get("tracks", []) if t["status"] == "failed")
    print(f"Batch complete: {completed} completed, {failed} failed.")
    return 0 if failed == 0 else 1
