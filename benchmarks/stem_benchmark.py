"""Benchmark stem-separation presets on CPU.

Generates a short synthetic test track, runs each requested preset, and writes a
Markdown report to the data root.

Usage:
    python benchmarks/stem_benchmark.py --duration 30 --presets karaoke full-vocals 4stem
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List

import numpy as np
import soundfile as sf

# Add repo root to path so the uninstalled package can be imported.
_repo_root = Path(__file__).resolve().parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from toolshop import stem_models, stems_cli


def generate_test_signal(path: Path, duration: float = 10.0, sr: int = 44100) -> Path:
    """Create a synthetic stereo track with drums, bass, vocals-ish content."""
    samples = int(duration * sr)
    t = np.linspace(0, duration, samples)

    # Kick-ish pulses.
    kick = np.zeros(samples)
    for beat in np.arange(0, duration, 60 / 120):
        start = int(beat * sr)
        end = min(start + int(0.05 * sr), samples)
        kick[start:end] = np.sin(2 * np.pi * 60 * t[start:end]) * np.exp(-30 * np.linspace(0, 1, end - start))

    # Bass saw.
    bass = np.sin(2 * np.pi * 80 * t) * (np.sign(np.sin(2 * np.pi * 2 * t)) * 0.5 + 0.5)

    # Vocal-ish whistle/harmonics.
    melody = np.sin(2 * np.pi * 440 * t) * 0.3
    melody += np.sin(2 * np.pi * 880 * t) * 0.15

    mix = kick + bass + melody
    mix = mix / (np.max(np.abs(mix)) + 1e-8)
    stereo = np.column_stack([mix, mix * 0.9])

    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(path, stereo, sr)
    return path


class _Args:
    preset: str = "karaoke"
    path: Path = Path("dummy")
    out: Path | None = None
    data_root: Path | None = None
    format: str | None = None
    device: str = "cpu"
    model_file_dir: Path | None = None
    limit: int = 0
    offset: int = 0
    no_resume: bool = False
    json: bool = False
    list_models: bool = False


def benchmark_preset(
    input_path: Path,
    preset_id: str,
    data_root: Path,
) -> Dict[str, float | str]:
    """Run a single preset and return timing/result metadata."""
    out_dir = data_root / "benchmarks" / preset_id
    out_dir.mkdir(parents=True, exist_ok=True)

    args = _Args()
    args.preset = preset_id
    args.path = input_path
    args.out = out_dir
    args.data_root = data_root
    args.format = "wav"
    args.device = "cpu"

    start = time.time()
    code = stems_cli.run(args)
    elapsed = time.time() - start

    return {
        "preset": preset_id,
        "status": "ok" if code == 0 else "failed",
        "elapsed_seconds": round(elapsed, 2),
        "output_dir": str(out_dir),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark stem presets on CPU")
    parser.add_argument(
        "--duration",
        type=float,
        default=30.0,
        help="Duration of the synthetic test track in seconds",
    )
    parser.add_argument(
        "--presets",
        nargs="+",
        default=["karaoke", "full-vocals"],
        choices=list(stem_models.list_presets()),
        help="Presets to benchmark",
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path(os.environ.get("TOOLSHOP_DATA_DIR", r"D:\MusicData\toolshop")),
        help="Data root for outputs",
    )
    args = parser.parse_args()

    data_root = args.data_root.expanduser().resolve()
    test_file = data_root / "benchmarks" / "synthetic_test.wav"
    generate_test_signal(test_file, duration=args.duration)

    results: List[Dict[str, float | str]] = []
    for preset_id in args.presets:
        print(f"Benchmarking {preset_id}...")
        result = benchmark_preset(test_file, preset_id, data_root)
        results.append(result)
        print(f"  {result['status']} in {result['elapsed_seconds']}s")

    report_path = data_root / "benchmarks" / "stem_benchmark_report.json"
    report_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    md_lines = [
        "# Stem Separation CPU Benchmark",
        "",
        f"Test track: `{test_file}` ({args.duration}s, 44.1kHz stereo)",
        "",
        "| preset | status | elapsed_seconds | output_dir |",
        "|--------|--------|-----------------|------------|",
    ]
    for r in results:
        md_lines.append(
            f"| {r['preset']} | {r['status']} | {r['elapsed_seconds']} | `{r['output_dir']}` |"
        )
    md_lines.extend(["", f"JSON report: `{report_path}`"])

    md_path = data_root / "benchmarks" / "stem_benchmark_report.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    print(f"\nReport written to {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
