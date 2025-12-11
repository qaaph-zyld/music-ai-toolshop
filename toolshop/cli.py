"""CLI entrypoint for the music-ai-toolshop.

Subcommands:
    suno      - Suno library sync and listing
    analyze   - BPM/key analysis for audio files
    yt        - YouTube search, info, summarize, download
    track     - Track reverse engineering / structure analysis
"""

import argparse
import json
from pathlib import Path
from typing import Optional, Sequence

from . import suno_adapter
from . import bpm_adapter
from . import yt_scraper_adapter
from . import yt_summarizer_adapter
from . import reverse_engineering_adapter


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="toolshop",
        description=(
            "Music AI toolshop to orchestrate Suno, audio analysis, "
            "YouTube tools, and track reverse engineering."
        ),
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = True

    # =========================================================================
    # SUNO COMMANDS
    # =========================================================================
    suno_parser = subparsers.add_parser("suno", help="Suno library tools")
    suno_subparsers = suno_parser.add_subparsers(dest="suno_command")
    suno_subparsers.required = True

    sync_parser = suno_subparsers.add_parser(
        "sync-liked", help="Sync liked Suno tracks into local library"
    )
    sync_parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("suno_library"),
        help="Destination directory for downloaded clips.",
    )
    sync_parser.add_argument(
        "--no-wav",
        action="store_true",
        help="Disable conversion of audio files to WAV.",
    )
    sync_parser.add_argument(
        "--keep-original",
        action="store_true",
        help="Keep original compressed audio files after WAV conversion.",
    )
    sync_parser.add_argument(
        "--workers",
        type=int,
        default=5,
        help="Number of parallel download workers.",
    )

    list_parser = suno_subparsers.add_parser(
        "list", help="List tracks from local Suno library"
    )
    list_parser.add_argument(
        "--root",
        type=Path,
        default=Path("suno_library"),
        help="Root directory of the local Suno library.",
    )

    # =========================================================================
    # ANALYZE (BPM/KEY) COMMANDS
    # =========================================================================
    analyze_parser = subparsers.add_parser(
        "analyze", help="BPM/key audio analysis tools"
    )
    analyze_subparsers = analyze_parser.add_subparsers(dest="analyze_command")
    analyze_subparsers.required = True

    # analyze bpm-key <file>
    bpm_file_parser = analyze_subparsers.add_parser(
        "bpm-key", help="Analyze a single audio file for BPM and key"
    )
    bpm_file_parser.add_argument(
        "file", type=Path, help="Path to audio file (WAV recommended)"
    )
    bpm_file_parser.add_argument(
        "--json", action="store_true", help="Output as JSON"
    )

    # analyze library <root>
    bpm_lib_parser = analyze_subparsers.add_parser(
        "library", help="Analyze all audio files in a directory for BPM/key"
    )
    bpm_lib_parser.add_argument(
        "root", type=Path, help="Root directory to scan"
    )
    bpm_lib_parser.add_argument(
        "--ext",
        type=str,
        default="wav",
        help="File extension(s) to include, comma-separated (default: wav)",
    )
    bpm_lib_parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output JSON file for results",
    )

    # =========================================================================
    # YOUTUBE COMMANDS
    # =========================================================================
    yt_parser = subparsers.add_parser(
        "yt", help="YouTube scraping and summarization tools"
    )
    yt_subparsers = yt_parser.add_subparsers(dest="yt_command")
    yt_subparsers.required = True

    # yt search <query>
    yt_search_parser = yt_subparsers.add_parser(
        "search", help="Search YouTube for videos"
    )
    yt_search_parser.add_argument("query", type=str, help="Search query")
    yt_search_parser.add_argument(
        "--limit", type=int, default=10, help="Max results (default 10)"
    )
    yt_search_parser.add_argument(
        "--json", action="store_true", help="Output as JSON"
    )

    # yt info <video_id_or_url>
    yt_info_parser = yt_subparsers.add_parser(
        "info", help="Get metadata for a YouTube video"
    )
    yt_info_parser.add_argument(
        "video", type=str, help="YouTube video ID or URL"
    )
    yt_info_parser.add_argument(
        "--json", action="store_true", help="Output as JSON"
    )

    # yt summarize <url>
    yt_summarize_parser = yt_subparsers.add_parser(
        "summarize", help="Generate a Suno-ready prompt from a YouTube video"
    )
    yt_summarize_parser.add_argument("url", type=str, help="YouTube video URL")
    yt_summarize_parser.add_argument(
        "--for",
        dest="for_type",
        type=str,
        default="prompt",
        choices=["prompt", "keywords"],
        help="Output type: 'prompt' for Suno prompt, 'keywords' for music keywords",
    )
    yt_summarize_parser.add_argument(
        "--json", action="store_true", help="Output as JSON"
    )

    # yt download <url>
    yt_download_parser = yt_subparsers.add_parser(
        "download", help="Download audio from a YouTube video"
    )
    yt_download_parser.add_argument("url", type=str, help="YouTube video URL")
    yt_download_parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("yt_downloads"),
        help="Output directory",
    )
    yt_download_parser.add_argument(
        "--format",
        type=str,
        default="wav",
        help="Audio format (default: wav)",
    )

    # =========================================================================
    # TRACK REVERSE ENGINEERING COMMANDS
    # =========================================================================
    track_parser = subparsers.add_parser(
        "track", help="Track reverse engineering / structure analysis"
    )
    track_subparsers = track_parser.add_subparsers(dest="track_command")
    track_subparsers.required = True

    # track analyze <file>
    track_analyze_parser = track_subparsers.add_parser(
        "analyze", help="Analyze a track for structure, key, BPM, chords, etc."
    )
    track_analyze_parser.add_argument(
        "file", type=Path, help="Path to audio file"
    )
    track_analyze_parser.add_argument(
        "--export-json", action="store_true", help="Export results to JSON file"
    )
    track_analyze_parser.add_argument(
        "--output-dir", type=Path, default=None, help="Output directory for JSON"
    )
    track_analyze_parser.add_argument(
        "--effects", action="store_true", help="Run effects analysis (if available)"
    )
    track_analyze_parser.add_argument(
        "--instruments",
        action="store_true",
        help="Run instrument recognition (if available)",
    )
    track_analyze_parser.add_argument(
        "--summary", action="store_true", help="Print human-readable summary"
    )

    return parser


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    # =========================================================================
    # SUNO
    # =========================================================================
    if args.command == "suno":
        if args.suno_command == "sync-liked":
            suno_adapter.sync_liked(
                output_dir=args.output_dir,
                convert_to_wav=not args.no_wav,
                delete_original_after_wav=not args.keep_original,
                max_workers=args.workers,
            )
        elif args.suno_command == "list":
            suno_adapter.list_library(root=args.root)
        else:
            parser.error("Unknown 'suno' subcommand.")

    # =========================================================================
    # ANALYZE (BPM/KEY)
    # =========================================================================
    elif args.command == "analyze":
        if args.analyze_command == "bpm-key":
            result = bpm_adapter.analyze_track(args.file)
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"File: {result['file']}")
                print(f"BPM: {result['bpm']}")
                print(f"Key: {result['key']} {result['mode']}")
                print(f"Duration: {result['duration_seconds']}s")
        elif args.analyze_command == "library":
            extensions = [e.strip() for e in args.ext.split(",")]
            bpm_adapter.analyze_library(
                root=args.root,
                extensions=extensions,
                output_json=args.output,
            )
        else:
            parser.error("Unknown 'analyze' subcommand.")

    # =========================================================================
    # YOUTUBE
    # =========================================================================
    elif args.command == "yt":
        if args.yt_command == "search":
            results = yt_scraper_adapter.search(args.query, limit=args.limit)
            if args.json:
                print(json.dumps(results, indent=2))
            else:
                for v in results:
                    duration = v.get("duration") or "?"
                    print(f"{v['id']}\t{duration}s\t{v['title']}")
        elif args.yt_command == "info":
            info = yt_scraper_adapter.get_info(args.video)
            if args.json:
                print(json.dumps(info, indent=2))
            else:
                print(f"Title: {info['title']}")
                print(f"Channel: {info['channel']}")
                print(f"Duration: {info['duration']}s")
                print(f"Views: {info.get('view_count', 'N/A')}")
                print(f"Tags: {', '.join(info.get('tags', [])[:10])}")
        elif args.yt_command == "summarize":
            if args.for_type == "prompt":
                summary = yt_summarizer_adapter.summarize_for_prompt(args.url)
                if args.json:
                    print(json.dumps({"prompt": summary}))
                else:
                    print(summary)
            else:  # keywords
                keywords = yt_summarizer_adapter.extract_music_keywords(args.url)
                if args.json:
                    print(json.dumps(keywords, indent=2))
                else:
                    print(f"Title: {keywords['title']}")
                    print(f"Genres: {', '.join(keywords['genre_hints'])}")
                    print(f"Moods: {', '.join(keywords['mood_hints'])}")
                    print(f"Instruments: {', '.join(keywords['instrument_hints'])}")
        elif args.yt_command == "download":
            path = yt_scraper_adapter.download_audio(
                args.url, output_dir=args.output_dir, format=args.format
            )
            print(f"Downloaded: {path}")
        else:
            parser.error("Unknown 'yt' subcommand.")

    # =========================================================================
    # TRACK REVERSE ENGINEERING
    # =========================================================================
    elif args.command == "track":
        if args.track_command == "analyze":
            result = reverse_engineering_adapter.analyze_track(
                path=args.file,
                export_json=args.export_json,
                output_dir=args.output_dir,
                effects=args.effects,
                instruments=args.instruments,
            )
            if args.summary:
                reverse_engineering_adapter.print_summary(result)
            else:
                print(json.dumps(result, indent=2, default=str))
        else:
            parser.error("Unknown 'track' subcommand.")

    else:
        parser.error(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
