"""CLI handler for the `toolshop video` command."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Optional

from .video_features import extract_features
from .video_ass import lrc_to_ass, STYLE_PRESETS as ASS_STYLES
from .video_compose import compose_pipeline


def _default_data_root() -> Path:
    return Path(os.environ.get("TOOLSHOP_DATA_DIR", str(Path(__file__).resolve().parent.parent / "data" / "toolshop")))


def add_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the `video` subcommand on the given subparsers."""
    video_parser = subparsers.add_parser(
        "video",
        help="Music video generation: features, lyrics, compositing",
    )
    video_subparsers = video_parser.add_subparsers(dest="video_command")
    video_subparsers.required = True

    # video features --audio <file> [--output features.json] [--stems-dir DIR]
    features_parser = video_subparsers.add_parser(
        "features", help="Extract audio features to sidecar JSON"
    )
    features_parser.add_argument(
        "--audio", type=Path, required=True, help="Path to audio file (WAV/MP3)"
    )
    features_parser.add_argument(
        "--output", type=Path, default=None, help="Output JSON path (default: auto)"
    )
    features_parser.add_argument(
        "--stems-dir", type=Path, default=None, help="Stems directory for per-stem energies"
    )
    features_parser.add_argument(
        "--json", action="store_true", help="Print JSON to stdout"
    )

    # video generate --audio <file> [--lyrics LRC] [--features JSON]
    #   [--style default|neon|minimal|bold] [--background showwaves|ken_burns|image:PATH]
    #   [--image COVER.jpg] [--resolution WxH] [--fps N] [--out out.mp4]
    generate_parser = video_subparsers.add_parser(
        "generate", help="Generate a music video from audio + optional lyrics"
    )
    generate_parser.add_argument(
        "--audio", type=Path, required=True, help="Path to audio file"
    )
    generate_parser.add_argument(
        "--lyrics", type=Path, default=None, help="Path to LRC lyrics file"
    )
    generate_parser.add_argument(
        "--features", type=Path, default=None,
        help="Pre-extracted features JSON (auto-extracts if omitted)",
    )
    generate_parser.add_argument(
        "--style",
        type=str,
        default="default",
        choices=list(ASS_STYLES.keys()),
        help="Lyric style preset (default: default)",
    )
    generate_parser.add_argument(
        "--background",
        type=str,
        default="showwaves",
        help="Background: showwaves, ken_burns, or image:PATH (default: showwaves)",
    )
    generate_parser.add_argument(
        "--image", type=Path, default=None,
        help="Image for ken_burns background (JPG/PNG)",
    )
    generate_parser.add_argument(
        "--resolution", type=str, default="1280x720",
        help="Video resolution WxH (default: 1280x720)",
    )
    generate_parser.add_argument(
        "--fps", type=int, default=30, help="Frames per second (default: 30)"
    )
    generate_parser.add_argument(
        "--out", type=Path, default=None,
        help="Output MP4 path (default: TOOLSHOP_DATA_DIR/videos/<slug>.mp4)",
    )
    generate_parser.add_argument(
        "--json", action="store_true", help="Print result as JSON"
    )

    # video lyrics --lyrics LRC [--style default|neon|minimal|bold] [--output out.ass]
    lyrics_parser = video_subparsers.add_parser(
        "lyrics", help="Convert LRC lyrics to ASS subtitle file"
    )
    lyrics_parser.add_argument(
        "--lyrics", type=Path, required=True, help="Path to LRC file"
    )
    lyrics_parser.add_argument(
        "--output", type=Path, default=None, help="Output .ass path (default: auto)"
    )
    lyrics_parser.add_argument(
        "--style",
        type=str,
        default="default",
        choices=list(ASS_STYLES.keys()),
        help="Style preset (default: default)",
    )
    lyrics_parser.add_argument(
        "--resolution", type=str, default="1280x720",
        help="Video resolution WxH (default: 1280x720)",
    )

    # video stock --query "..." [--source pexels|pixabay|both] [--limit N] [--out DIR]
    stock_parser = video_subparsers.add_parser(
        "stock", help="Search stock footage (Pexels/Pixabay)"
    )
    stock_parser.add_argument(
        "--query", type=str, required=True, help="Search query"
    )
    stock_parser.add_argument(
        "--source", type=str, default="both",
        choices=["pexels", "pixabay", "both"],
        help="Stock source (default: both)",
    )
    stock_parser.add_argument(
        "--limit", type=int, default=5, help="Max results per source (default: 5)"
    )
    stock_parser.add_argument(
        "--out", type=Path, default=None, help="Output directory (default: auto)"
    )


def _resolve_output_path(audio_path: Path, args: Any) -> Path:
    """Resolve output path for generated video."""
    if args.out:
        return args.out
    slug = audio_path.stem
    return _default_data_root() / "videos" / f"{slug}.mp4"


def _parse_resolution(res: str) -> tuple[int, int]:
    """Parse 'WxH' string into (width, height)."""
    w, h = res.split("x")
    return (int(w), int(h))


def run(args: Any) -> int:
    """Execute the `toolshop video` subcommand."""
    cmd = getattr(args, "video_command", None)

    if cmd == "features":
        return _cmd_features(args)
    elif cmd == "generate":
        return _cmd_generate(args)
    elif cmd == "lyrics":
        return _cmd_lyrics(args)
    elif cmd == "stock":
        return _cmd_stock(args)
    else:
        print(f"Unknown video command: {cmd}", file=sys.stderr)
        return 1


def _cmd_features(args: Any) -> int:
    audio = args.audio
    if not audio.exists():
        print(f"Audio file not found: {audio}", file=sys.stderr)
        return 1

    output = args.output
    if output is None:
        output = _default_data_root() / "video_features" / f"{audio.stem}.json"

    try:
        result = extract_features(
            audio_path=audio,
            output_path=output,
            stems_dir=args.stems_dir,
        )
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"Features extracted: {output}")
        print(f"  Tempo: {result.get('tempo', '?')} BPM")
        print(f"  Key: {result.get('key', '?')} {result.get('mode', '?')}")
        print(f"  Duration: {result.get('duration', '?')}s")
        print(f"  Beats: {len(result.get('beats', []))}")
        print(f"  Onsets: {len(result.get('onsets', []))}")

    return 0


def _cmd_generate(args: Any) -> int:
    audio = args.audio
    if not audio.exists():
        print(f"Audio file not found: {audio}", file=sys.stderr)
        return 1

    output = _resolve_output_path(audio, args)
    output.parent.mkdir(parents=True, exist_ok=True)

    # Auto-extract features if not provided
    features_path = args.features
    if features_path is None or not features_path.exists():
        features_path = output.parent / f"{audio.stem}_features.json"
        try:
            extract_features(audio_path=audio, output_path=features_path)
        except RuntimeError as e:
            print(f"Error extracting features: {e}", file=sys.stderr)
            return 1

    # Convert lyrics if provided
    ass_file = None
    if args.lyrics and args.lyrics.exists():
        ass_file = output.parent / f"{audio.stem}_lyrics.ass"
        resolution = _parse_resolution(args.resolution)
        lrc_to_ass(
            lrc_path=args.lyrics,
            output_path=ass_file,
            style=args.style,
            resolution=resolution,
        )

    # Compose
    try:
        result = compose_pipeline(
            features_path=features_path,
            audio=audio,
            output=output,
            background=args.background,
            ass_file=ass_file,
            image=args.image,
            size=args.resolution,
            fps=args.fps,
        )
    except (RuntimeError, FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps({"output": str(result)}, indent=2))
    else:
        print(f"Video generated: {result}")

    return 0


def _cmd_lyrics(args: Any) -> int:
    if not args.lyrics.exists():
        print(f"Lyrics file not found: {args.lyrics}", file=sys.stderr)
        return 1

    output = args.output
    if output is None:
        output = args.lyrics.with_suffix(".ass")

    resolution = _parse_resolution(args.resolution)
    lrc_to_ass(
        lrc_path=args.lyrics,
        output_path=output,
        style=args.style,
        resolution=resolution,
    )

    print(f"ASS file written: {output}")
    return 0


def _cmd_stock(args: Any) -> int:
    # P1 feature — import lazily
    try:
        from .video_stock import search_stock
    except ImportError:
        print("Stock search requires httpx. Install with: pip install httpx", file=sys.stderr)
        return 1

    out_dir = args.out
    if out_dir is None:
        out_dir = _default_data_root() / "stock"

    try:
        results = search_stock(
            query=args.query,
            source=args.source,
            limit=args.limit,
            output_dir=out_dir,
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print(f"Stock search results: {len(results)} clips")
    for r in results:
        print(f"  {r.get('source', '?')}: {r.get('url', '?')}")

    return 0
