"""CLI handler for the `toolshop melody-carrier` command.

Subcommands:
    extract   - Stage 1: Extract stems, analyze track, convert to MIDI
    render    - Stage 2: Render carrier WAVs and generate Suno prompts
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict

from . import extractor
from . import renderer


def add_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the `melody-carrier` subcommand on the given subparsers."""
    mc_parser = subparsers.add_parser(
        "melody-carrier",
        help="Melody carrier generator: extract musical DNA and render carrier WAVs for Suno cover mode",
    )

    mc_subparsers = mc_parser.add_subparsers(dest="mc_command")
    mc_subparsers.required = True

    # extract
    extract_parser = mc_subparsers.add_parser(
        "extract",
        help="Stage 1: Extract stems, analyze track, convert to MIDI files",
    )
    extract_parser.add_argument(
        "input",
        type=Path,
        help="Path to input WAV file",
    )
    extract_parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output directory (stage1/ subdirectory will be created inside)",
    )
    extract_parser.add_argument(
        "--genre",
        type=str,
        required=True,
        help="Genre tag for Suno prompt (e.g., 'drill', 'lofi')",
    )
    extract_parser.add_argument(
        "--preset",
        type=str,
        default="4stem",
        choices=["4stem", "6stem"],
        help="Stem separation preset (default: 4stem)",
    )
    extract_parser.add_argument(
        "--require-advanced",
        action="store_true",
        help="Fail instead of silently falling back to the librosa heuristics. "
        "Requires basic-pitch (melody), autochord (chords) and adtof-pytorch (drums); "
        "install with the 'melody' extra.",
    )

    # render
    render_parser = mc_subparsers.add_parser(
        "render",
        help="Stage 2: Render carrier WAVs and generate Suno prompts from Stage 1 MIDI",
    )
    render_parser.add_argument(
        "dir",
        type=Path,
        help="Working directory containing stage1/ subdirectory from extract",
    )
    render_parser.add_argument(
        "--instruments",
        type=str,
        default="",
        help="Instrument substitutions: 'piano:cathedral organ,guitar:synth lead'",
    )
    render_parser.add_argument(
        "--fidelity",
        type=str,
        default="medium",
        choices=["low", "medium", "high"],
        help="Audio Influence fidelity level (default: medium)",
    )


def run(args: argparse.Namespace) -> int:
    """Execute the `melody-carrier` subcommand."""
    cmd = getattr(args, "mc_command", None)

    if cmd == "extract":
        return _cmd_extract(args)
    elif cmd == "render":
        return _cmd_render(args)
    else:
        print(f"Error: Unknown melody-carrier subcommand: {cmd}", file=sys.stderr)
        return 1


# Advanced backends, in the order the extractor reaches for them. A missing one is
# not an error by default — the extractor degrades to librosa heuristics and records
# which path it took. `--require-advanced` turns that degradation into a hard failure.
ADVANCED_BACKENDS = {
    "melody": ("basic_pitch", "basic-pitch"),
    "chords": ("autochord", "autochord"),
    "drums": ("adtof_pytorch", "adtof-pytorch"),
}


def missing_advanced_backends() -> Dict[str, str]:
    """Return ``{stage: pip name}`` for each advanced backend that will not import."""
    import importlib

    missing: Dict[str, str] = {}
    for stage, (module, pip_name) in ADVANCED_BACKENDS.items():
        try:
            importlib.import_module(module)
        except Exception:
            missing[stage] = pip_name
    return missing


def _cmd_extract(args: argparse.Namespace) -> int:
    """Handle the `extract` subcommand."""
    require_advanced = getattr(args, "require_advanced", False)

    # Pre-flight: fail before spending minutes on stem separation, not after.
    if require_advanced:
        missing = missing_advanced_backends()
        if missing:
            print(
                "Error: --require-advanced was given but these backends are not installed:",
                file=sys.stderr,
            )
            for stage, pip_name in sorted(missing.items()):
                print(f"    {stage:8s} needs {pip_name}", file=sys.stderr)
            print(
                "\nInstall them with:  pip install -e .[melody]\n"
                "Or drop --require-advanced to run on the librosa fallbacks.",
                file=sys.stderr,
            )
            return 1

    try:
        result = extractor.extract(
            input_wav=args.input,
            output_dir=args.output,
            genre=args.genre,
            preset=args.preset,
        )

        # Belt and braces: a backend can import and still fail at runtime, and the
        # extractor records the path it actually took. Trust the record, not the import.
        tools = (result.get("analysis") or {}).get("extraction_tools") or {}
        if require_advanced:
            fell_back = {k: v for k, v in tools.items() if isinstance(v, str) and "fallback" in v}
            if fell_back:
                print(
                    "Error: --require-advanced was given but these stages fell back at runtime:",
                    file=sys.stderr,
                )
                for stage, tool in sorted(fell_back.items()):
                    print(f"    {stage:8s} used {tool}", file=sys.stderr)
                return 1

        stage1_dir = result.get("stage1_dir", "unknown")
        midi_files = result.get("midi_files", {})

        print(f"Stage 1 extraction complete.")
        print(f"  Output directory: {stage1_dir}")
        print(f"  MIDI files created:")
        for name, path in midi_files.items():
            print(f"    {name}: {path}")

        if tools:
            print(f"  Extraction backends:")
            for stage, tool in sorted(tools.items()):
                marker = "  (fallback)" if isinstance(tool, str) and "fallback" in tool else ""
                print(f"    {stage}: {tool}{marker}")

        return 0

    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def _cmd_render(args: argparse.Namespace) -> int:
    """Handle the `render` subcommand."""
    try:
        result = renderer.render(
            work_dir=args.dir,
            instruments=args.instruments,
            fidelity=args.fidelity,
        )

        carriers = result.get("carriers", {})
        prompts = result.get("prompts", {})
        fidelity_pct = result.get("fidelity_pct", 0)

        print(f"Stage 2 rendering complete.")
        print(f"  Carriers created: {len(carriers)}")
        for name, path in carriers.items():
            print(f"    {name}: {path}")
        print(f"  Prompts generated: {len(prompts)}")
        for name, path in prompts.items():
            print(f"    {name}: {path}")
        print(f"  Fidelity: {fidelity_pct}%")

        return 0

    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
