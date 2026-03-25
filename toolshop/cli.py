"""CLI entrypoint for the music-ai-toolshop.

Subcommands:
    suno      - Suno library sync and listing
    analyze   - BPM/key analysis for audio files
    yt        - YouTube search, info, summarize, download
    track     - Track reverse engineering / structure analysis
    clean     - Audio cleaning and track preparation tools
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
from . import voice_effects_adapter
from . import stem_extractor_adapter
from . import cleaning_pipeline_adapter


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

    # suno analyze - batch BPM/key analysis of Suno library
    suno_analyze_parser = suno_subparsers.add_parser(
        "analyze", help="Batch-analyze Suno library for BPM/key"
    )
    suno_analyze_parser.add_argument(
        "--root",
        type=Path,
        default=Path("suno_library"),
        help="Root directory of the local Suno library.",
    )
    suno_analyze_parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output JSON file for results (default: <root>/bpm_key_analysis.json)",
    )
    suno_analyze_parser.add_argument(
        "--ext",
        type=str,
        default="wav,mp3",
        help="File extensions to analyze, comma-separated (default: wav,mp3)",
    )

    # suno export-text - export lyrics/descriptions from liked tracks
    suno_export_parser = suno_subparsers.add_parser(
        "export-text",
        help="Export lyrics and descriptions from liked Suno tracks",
    )
    suno_export_parser.add_argument(
        "--root",
        type=Path,
        default=Path("suno_library"),
        help="Root directory of the local Suno library.",
    )
    suno_export_parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Path to JSON export file (default: <root>/lyrics_export.json)",
    )
    suno_export_parser.add_argument(
        "--txt-out",
        type=Path,
        default=None,
        help="Path to plain-text export file (default: <root>/lyrics_export.txt)",
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
    bpm_file_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # analyze library <root>
    bpm_lib_parser = analyze_subparsers.add_parser(
        "library", help="Analyze all audio files in a directory for BPM/key"
    )
    bpm_lib_parser.add_argument("root", type=Path, help="Root directory to scan")
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
    yt_search_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # yt info <video_id_or_url>
    yt_info_parser = yt_subparsers.add_parser(
        "info", help="Get metadata for a YouTube video"
    )
    yt_info_parser.add_argument("video", type=str, help="YouTube video ID or URL")
    yt_info_parser.add_argument("--json", action="store_true", help="Output as JSON")

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

    # yt analyze <url> - download + analyze in one step
    yt_analyze_parser = yt_subparsers.add_parser(
        "analyze", help="Download YouTube audio and analyze BPM/key in one step"
    )
    yt_analyze_parser.add_argument("url", type=str, help="YouTube video URL")
    yt_analyze_parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("yt_downloads"),
        help="Output directory for downloaded audio",
    )
    yt_analyze_parser.add_argument(
        "--full",
        action="store_true",
        help="Run full track analysis (chords, structure) instead of just BPM/key",
    )
    yt_analyze_parser.add_argument("--json", action="store_true", help="Output as JSON")

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
    track_analyze_parser.add_argument("file", type=Path, help="Path to audio file")
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

    # =========================================================================
    # VOICE EFFECTS ANALYSIS COMMANDS
    # =========================================================================
    voice_parser = subparsers.add_parser(
        "voice", help="Voice effects detection and analysis"
    )
    voice_subparsers = voice_parser.add_subparsers(dest="voice_command")
    voice_subparsers.required = True

    # voice analyze <file>
    voice_analyze_parser = voice_subparsers.add_parser(
        "analyze", help="Analyze a voice recording for applied effects and processing"
    )
    voice_analyze_parser.add_argument(
        "file", type=Path, help="Path to audio file (WAV recommended)"
    )
    voice_analyze_parser.add_argument(
        "--json", action="store_true", help="Output as JSON"
    )
    voice_analyze_parser.add_argument(
        "--summary", action="store_true", help="Print human-readable summary (default)"
    )
    voice_analyze_parser.add_argument(
        "--export-json", action="store_true", help="Export results to JSON file"
    )
    voice_analyze_parser.add_argument(
        "--output-dir", type=Path, default=None, help="Output directory for JSON export"
    )

    # =========================================================================
    # STEM EXTRACTOR COMMANDS
    # =========================================================================
    stem_parser = subparsers.add_parser("stem", help="Stem extraction tools")
    stem_subparsers = stem_parser.add_subparsers(dest="stem_command")
    stem_subparsers.required = True

    # stem extract - extract stems from audio file
    stem_extract_parser = stem_subparsers.add_parser(
        "extract", help="Extract instrumentals, main vocals, and backing vocals"
    )
    stem_extract_parser.add_argument(
        "file",
        type=Path,
        help="Input audio file to process",
    )
    stem_extract_parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("separated_tracks"),
        help="Output directory for extracted stems",
    )
    stem_extract_parser.add_argument(
        "--cpu",
        action="store_true",
        help="Use CPU instead of GPU (slower but no VRAM required)",
    )
    stem_extract_parser.add_argument(
        "--fast",
        action="store_true",
        help="Use fast mode (MDX-Net models) instead of high quality (Roformer)",
    )
    stem_extract_parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format",
    )

    # =========================================================================
    # CLEANING COMMANDS
    # =========================================================================
    clean_parser = subparsers.add_parser(
        "clean", help="Audio cleaning and track preparation tools"
    )
    clean_subparsers = clean_parser.add_subparsers(dest="clean_command")
    clean_subparsers.required = True

    # clean pipeline <file> - full cleaning pipeline
    clean_pipeline_parser = clean_subparsers.add_parser(
        "pipeline", help="Run full cleaning pipeline on audio file"
    )
    clean_pipeline_parser.add_argument(
        "file", type=Path, help="Path to audio file to clean"
    )
    clean_pipeline_parser.add_argument(
        "--config", "-c", type=Path, help="Pipeline configuration YAML file"
    )
    clean_pipeline_parser.add_argument(
        "--output", "-o", type=Path, help="Output file path"
    )
    clean_pipeline_parser.add_argument(
        "--report", "-r", type=Path, help="Save processing report to JSON file"
    )

    # clean pause-remove <file> - remove pauses
    clean_pause_parser = clean_subparsers.add_parser(
        "pause-remove", help="Remove long pauses and silences from audio"
    )
    clean_pause_parser.add_argument("file", type=Path, help="Path to audio file")
    clean_pause_parser.add_argument(
        "--threshold",
        "-t",
        type=float,
        default=-40,
        help="Silence threshold in dB (default: -40)",
    )
    clean_pause_parser.add_argument(
        "--min-silence",
        type=float,
        default=0.3,
        help="Minimum silence to remove in seconds (default: 0.3)",
    )
    clean_pause_parser.add_argument(
        "--output", "-o", type=Path, help="Output file path"
    )

    # clean breath-detect <file> - detect and attenuate breaths
    clean_breath_parser = clean_subparsers.add_parser(
        "breath-detect", help="Detect and attenuate breath sounds"
    )
    clean_breath_parser.add_argument("file", type=Path, help="Path to audio file")
    clean_breath_parser.add_argument(
        "--attenuation",
        "-a",
        type=float,
        default=15,
        help="Attenuation in dB (default: 15)",
    )
    clean_breath_parser.add_argument(
        "--method",
        "-m",
        type=str,
        default="combined",
        choices=["frequency", "energy", "combined"],
        help="Detection method (default: combined)",
    )
    clean_breath_parser.add_argument(
        "--output", "-o", type=Path, help="Output file path"
    )

    # clean event-detect <file> - detect and remove events
    clean_event_parser = clean_subparsers.add_parser(
        "event-detect", help="Detect and remove discrete events (coughs, clicks, pops)"
    )
    clean_event_parser.add_argument("file", type=Path, help="Path to audio file")
    clean_event_parser.add_argument(
        "--detect",
        "-d",
        type=str,
        nargs="+",
        choices=["coughs", "clicks", "pops"],
        default=["coughs", "clicks", "pops"],
        help="Event types to detect (default: all)",
    )
    clean_event_parser.add_argument(
        "--confidence",
        "-c",
        type=float,
        default=0.7,
        help="Detection confidence threshold (default: 0.7)",
    )
    clean_event_parser.add_argument(
        "--output", "-o", type=Path, help="Output file path"
    )

    # clean beat-align <file> - analyze beats
    clean_beat_parser = clean_subparsers.add_parser(
        "beat-align", help="Analyze beats and optionally align to tempo grid"
    )
    clean_beat_parser.add_argument("file", type=Path, help="Path to audio file")
    clean_beat_parser.add_argument(
        "--mode",
        "-m",
        type=str,
        default="analyze",
        choices=["analyze", "align"],
        help="Analysis or alignment mode (default: analyze)",
    )
    clean_beat_parser.add_argument(
        "--target-bpm", "-b", type=float, help="Target BPM for alignment"
    )
    clean_beat_parser.add_argument(
        "--report", "-r", type=Path, help="Save beat report to JSON"
    )

    # clean config-template - generate config template
    clean_config_parser = clean_subparsers.add_parser(
        "config-template", help="Generate a default pipeline configuration file"
    )
    clean_config_parser.add_argument(
        "--output",
        "-o",
        type=Path,
        required=True,
        help="Output file path for config template",
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
        elif args.suno_command == "analyze":
            extensions = [e.strip() for e in args.ext.split(",")]
            output_json = args.output or (args.root / "bpm_key_analysis.json")
            print(f"Analyzing Suno library at {args.root}...")
            bpm_adapter.analyze_library(
                root=args.root,
                extensions=extensions,
                output_json=output_json,
            )
        elif args.suno_command == "export-text":
            json_out = args.json_out or (args.root / "lyrics_export.json")
            txt_out = args.txt_out or (args.root / "lyrics_export.txt")
            print(
                f"Exporting lyrics/descriptions from liked tracks under {args.root}..."
            )
            suno_adapter.export_text(
                root=args.root,
                output_json=json_out,
                output_txt=txt_out,
            )
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
        elif args.yt_command == "analyze":
            # Download + analyze in one step
            print(f"Downloading audio from {args.url}...")
            audio_path = yt_scraper_adapter.download_audio(
                args.url, output_dir=args.output_dir, format="wav"
            )
            print(f"Downloaded: {audio_path}")
            print("Analyzing...")
            if args.full:
                result = reverse_engineering_adapter.analyze_track(path=audio_path)
            else:
                result = bpm_adapter.analyze_track(audio_path)
            if args.json:
                print(json.dumps(result, indent=2, default=str))
            else:
                print(f"\nFile: {result['file']}")
                print(f"BPM: {result['bpm']}")
                print(f"Key: {result['key']} {result.get('mode', '')}")
                if result.get("duration_seconds"):
                    print(f"Duration: {result['duration_seconds']}s")
                if result.get("chord_progression"):
                    print(f"Chords: {len(result['chord_progression'])} detected")
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

    # =========================================================================
    # VOICE EFFECTS ANALYSIS
    # =========================================================================
    elif args.command == "voice":
        if args.voice_command == "analyze":
            result = voice_effects_adapter.analyze_voice(
                path=args.file,
                export_json=args.export_json,
                output_dir=args.output_dir,
            )
            if args.json:
                print(json.dumps(result, indent=2, default=str))
            else:
                voice_effects_adapter.print_voice_summary(result)
        else:
            parser.error("Unknown 'voice' subcommand.")

    # =========================================================================
    # STEM EXTRACTOR
    # =========================================================================
    elif args.command == "stem":
        if args.stem_command == "extract":
            result = stem_extractor_adapter.extract_stems(
                input_file=args.file,
                output_dir=args.output_dir,
                use_gpu=not args.cpu,
                high_quality=not args.fast,
            )
            if args.json:
                print(json.dumps(result, indent=2, default=str))
            else:
                print(f"✓ Extracted stems from {args.file.name}")
                print(f"  Output directory: {result['output_dir']}")
                print(f"  Quality mode: {result['quality_mode']}")
                print(f"  GPU used: {result['gpu_used']}")
                for stem_type, stem_file in result["stems"].items():
                    if stem_file:
                        print(f"  {stem_type}: {Path(stem_file).name}")
        else:
            parser.error("Unknown 'stem' subcommand.")

    # =========================================================================
    # CLEANING COMMANDS
    # =========================================================================
    elif args.command == "clean":
        if args.clean_command == "pipeline":
            config = None
            if args.config:
                config = cleaning_pipeline_adapter.load_config(args.config)
            else:
                config = cleaning_pipeline_adapter.get_default_config()

            pipeline = cleaning_pipeline_adapter.AudioCleaningPipeline(config)
            summary = pipeline.process(
                str(args.file), str(args.output) if args.output else None
            )

            print(f"\n✓ Audio cleaning complete!")
            print(f"  Output: {summary['output_file']}")
            print(f"  Duration: {summary['duration']:.2f}s")
            print(f"  Stages applied: {summary['stages_applied']}")
            print(f"  BPM: {summary.get('original_bpm', 'N/A')}")
            print(f"  Key: {summary.get('original_key', 'N/A')}")

            print("\n  Stage results:")
            for i, stage_report in enumerate(summary["stage_reports"], 1):
                stage_name = stage_report.get("stage", f"Stage {i}")
                status = stage_report.get("status", "unknown")
                print(f"    {i}. {stage_name}: {status}")

                if "breaths_detected" in stage_report:
                    print(
                        f"       - Breaths detected: {stage_report['breaths_detected']}"
                    )
                if "events_detected" in stage_report:
                    print(
                        f"       - Events detected: {stage_report['events_detected']}"
                    )
                if "time_removed" in stage_report:
                    print(f"       - Time removed: {stage_report['time_removed']:.2f}s")

            if args.report:
                with open(args.report, "w") as f:
                    json.dump(summary, f, indent=2)
                print(f"\n  Report saved to: {args.report}")

        elif args.clean_command == "pause-remove":
            config = cleaning_pipeline_adapter.get_default_config()
            config["stages"] = {
                "preprocessing": config["stages"]["preprocessing"],
                "pause_removal": {
                    "min_silence": args.min_silence,
                    "max_keep": 0.5,
                    "threshold_db": args.threshold,
                    "crossfade_ms": 10,
                },
            }

            pipeline = cleaning_pipeline_adapter.AudioCleaningPipeline(config)
            summary = pipeline.process(
                str(args.file), str(args.output) if args.output else None
            )

            pause_report = (
                summary["stage_reports"][1] if len(summary["stage_reports"]) > 1 else {}
            )

            print(f"\n✓ Pause removal complete!")
            print(f"  Time removed: {pause_report.get('time_removed', 0):.2f}s")
            print(f"  Segments kept: {pause_report.get('segments_kept', 0)}")
            print(f"  Output: {summary['output_file']}")

        elif args.clean_command == "breath-detect":
            config = cleaning_pipeline_adapter.get_default_config()
            config["stages"] = {
                "preprocessing": config["stages"]["preprocessing"],
                "breath_detection": {
                    "method": args.method,
                    "attenuation_db": args.attenuation,
                    "frequency_range": [200, 2000],
                    "min_breath_duration": 0.1,
                    "max_breath_duration": 0.8,
                },
            }

            pipeline = cleaning_pipeline_adapter.AudioCleaningPipeline(config)
            summary = pipeline.process(
                str(args.file), str(args.output) if args.output else None
            )

            breath_report = (
                summary["stage_reports"][1] if len(summary["stage_reports"]) > 1 else {}
            )

            print(f"\n✓ Breath detection complete!")
            print(f"  Breaths detected: {breath_report.get('breaths_detected', 0)}")
            print(f"  Method: {breath_report.get('method', args.method)}")
            print(f"  Attenuation: {args.attenuation}dB")
            print(f"  Output: {summary['output_file']}")

            if breath_report.get("detections"):
                print(f"\n  Detection details:")
                for det in breath_report["detections"][:5]:
                    print(
                        f"    - {det['start']:.2f}s to {det['end']:.2f}s "
                        f"(confidence: {det['confidence']:.2f})"
                    )

        elif args.clean_command == "event-detect":
            config = cleaning_pipeline_adapter.get_default_config()
            config["stages"] = {
                "preprocessing": config["stages"]["preprocessing"],
                "event_detection": {
                    "detect_coughs": "coughs" in args.detect,
                    "detect_clicks": "clicks" in args.detect,
                    "detect_pops": "pops" in args.detect,
                    "confidence_threshold": args.confidence,
                },
            }

            pipeline = cleaning_pipeline_adapter.AudioCleaningPipeline(config)
            summary = pipeline.process(
                str(args.file), str(args.output) if args.output else None
            )

            event_report = (
                summary["stage_reports"][1] if len(summary["stage_reports"]) > 1 else {}
            )

            print(f"\n✓ Event detection complete!")
            print(f"  Total events: {event_report.get('events_detected', 0)}")
            print(f"  Coughs: {event_report.get('coughs', 0)}")
            print(f"  Clicks: {event_report.get('clicks', 0)}")
            print(f"  Pops: {event_report.get('pops', 0)}")
            print(f"  Output: {summary['output_file']}")

        elif args.clean_command == "beat-align":
            config = cleaning_pipeline_adapter.get_default_config()
            config["stages"] = {
                "preprocessing": config["stages"]["preprocessing"],
                "beat_alignment": {"mode": args.mode, "target_bpm": args.target_bpm},
            }

            pipeline = cleaning_pipeline_adapter.AudioCleaningPipeline(config)
            summary = pipeline.process(str(args.file))

            beat_report = (
                summary["stage_reports"][1] if len(summary["stage_reports"]) > 1 else {}
            )
            metadata = (
                summary.get("stage_reports", [{}])[0]
                if summary.get("stage_reports")
                else {}
            )

            print(f"\n✓ Beat analysis complete!")
            print(f"  Mode: {beat_report.get('mode', args.mode)}")
            print(f"  BPM: {beat_report.get('bpm', metadata.get('bpm', 'N/A'))}")
            print(f"  Beat count: {beat_report.get('beat_count', 'N/A')}")

            if beat_report.get("tempo_stability"):
                print(
                    f"  Tempo stability: {beat_report['tempo_stability']:.2f} BPM std"
                )

            if args.report:
                beat_data = {
                    "bpm": beat_report.get("bpm"),
                    "beat_count": beat_report.get("beat_count"),
                    "tempo_stability": beat_report.get("tempo_stability"),
                    "original_key": summary.get("original_key"),
                }
                with open(args.report, "w") as f:
                    json.dump(beat_data, f, indent=2)
                print(f"\n  Report saved to: {args.report}")

        elif args.clean_command == "config-template":
            config = cleaning_pipeline_adapter.get_default_config()
            import yaml

            with open(args.output, "w") as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
            print(f"✓ Configuration template saved to: {args.output}")
            print(
                f"\nEdit this file and use with: "
                f"toolshop clean pipeline audio.wav --config {args.output}"
            )
        else:
            parser.error("Unknown 'clean' subcommand.")

    else:
        parser.error(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
