"""Environment health-check diagnostics for toolshop."""

import argparse
import importlib
import os
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


EXPECTED_PYTHON = (3, 11)

EXTRAS = {
    "audio": ["librosa", "numpy", "scipy"],
    "youtube": ["yt_dlp"],
    "voice": ["librosa", "numpy", "scipy", "parselmouth", "soundfile"],
    "cleaning": ["librosa", "numpy", "scipy", "soundfile", "yaml"],
    "stems": ["audio_separator", "onnxruntime", "soundfile", "demucs"],
    "track": ["librosa", "numpy", "scipy", "yt_dlp", "matplotlib", "soundfile", "pydub", "pyloudnorm", "yaml"],
}


def _python_version_ok() -> dict[str, Any]:
    major, minor = sys.version_info[:2]
    expected = ".".join(map(str, EXPECTED_PYTHON))
    actual = f"{major}.{minor}"
    return {
        "check": "python_version",
        "expected": expected,
        "actual": actual,
        "ok": (major, minor) == EXPECTED_PYTHON,
    }


def _find_ffmpeg() -> Path | None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return Path(ffmpeg)
    portable = Path(r"D:\Projects\ffmpeg_portable\ffmpeg-8.1.1-essentials_build\bin\ffmpeg.exe")
    if portable.exists():
        return portable
    env_path = Path(os.environ.get("TOOLSHOP_FFMPEG", ""))
    if env_path.exists():
        return env_path
    return None


def _ffmpeg_ok() -> dict[str, Any]:
    ffmpeg = _find_ffmpeg()
    version = None
    if ffmpeg:
        try:
            proc = subprocess.run(
                [str(ffmpeg), "-version"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            version = proc.stdout.splitlines()[0] if proc.stdout else None
        except Exception as exc:  # pragma: no cover
            version = f"error: {exc}"
    return {
        "check": "ffmpeg",
        "path": str(ffmpeg) if ffmpeg else None,
        "version": version,
        "ok": ffmpeg is not None and version is not None,
    }


def _packages_ok(extra: str) -> dict[str, Any]:
    packages = EXTRAS.get(extra, [])
    missing = []
    for name in packages:
        try:
            importlib.import_module(name)
        except Exception:
            missing.append(name)
    return {
        "check": f"packages_{extra}",
        "expected": packages,
        "missing": missing,
        "ok": not missing,
    }


def _disk_ok(drive: str = "D:") -> dict[str, Any]:
    try:
        usage = shutil.disk_usage(drive)
        free_gb = usage.free / (1024**3)
    except Exception as exc:  # pragma: no cover
        return {"check": "disk", "drive": drive, "free_gb": 0.0, "ok": False, "error": str(exc)}
    return {
        "check": "disk",
        "drive": drive,
        "free_gb": round(free_gb, 2),
        "ok": free_gb >= 15.0,
    }


def _model_cache_ok() -> dict[str, Any]:
    cache_root = Path(os.environ.get("TOOLSHOP_MODEL_DIR", Path.home() / ".cache" / "toolshop-models"))
    cache_root.mkdir(parents=True, exist_ok=True)
    return {
        "check": "model_cache",
        "path": str(cache_root),
        "ok": cache_root.exists() and cache_root.is_dir(),
    }


def run_checks() -> dict[str, Any]:
    results = [
        _python_version_ok(),
        _ffmpeg_ok(),
        _disk_ok(),
        _model_cache_ok(),
    ]
    for extra in EXTRAS:
        results.append(_packages_ok(extra))

    all_ok = all(r["ok"] for r in results)
    return {
        "ok": all_ok,
        "python": sys.executable,
        "checks": results,
    }


def print_report(report: dict[str, Any]) -> None:
    print(f"toolshop doctor ({report['python']})")
    print("-" * 50)
    for check in report["checks"]:
        status = "OK" if check["ok"] else "FAIL"
        detail = ""
        if "actual" in check and "expected" in check:
            detail = f" (expected {check['expected']}, got {check['actual']})"
        elif "missing" in check and check["missing"]:
            detail = f" missing: {', '.join(check['missing'])}"
        elif "free_gb" in check:
            detail = f" ({check['free_gb']} GB free on {check['drive']})"
        elif "path" in check and check.get("path"):
            detail = f" ({check['path']})"
        print(f"[{status}] {check['check']}{detail}")
    print("-" * 50)
    print(f"Overall: {'PASS' if report['ok'] else 'FAIL'}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check toolshop environment health.")
    parser.add_argument("--json", type=Path, help="Write JSON report to this file.")
    args = parser.parse_args(argv)

    report = run_checks()
    print_report(report)

    if args.json:
        args.json.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Report written to {args.json}")

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
