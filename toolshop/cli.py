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
import sys
from pathlib import Path
from typing import Optional, Sequence

# Allow the mastering_tool git submodule to be imported when running from a checkout.
_repo_root = Path(__file__).resolve().parent.parent
if (_repo_root / "mastering_tool").is_dir() and str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from . import suno_adapter
from . import bpm_adapter
from . import yt_scraper_adapter
from . import yt_summarizer_adapter
from . import reverse_engineering_adapter
from . import voice_effects_adapter
from mastering_tool.tools.vocal_doctor import diagnose_and_recommend
from . import stem_extractor_adapter
from . import cleaning_pipeline_adapter
from . import doctor as doctor_module


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
        "--chords", action="store_true", help="Run chord detection (if available)"
    )
    track_analyze_parser.add_argument(
        "--notes", action="store_true", help="Run note transcription (if available)"
    )
    track_analyze_parser.add_argument(
        "--separation",
        choices=["hpss"],
        default=None,
        help="Source separation backend (hpss only in this integration)",
    )
    track_analyze_parser.add_argument(
        "--backend",
        choices=["advanced", "basic"],
        default="advanced",
        help="Analysis backend to use (advanced uses wav_reverse_engineer)",
    )
    track_analyze_parser.add_argument(
        "--summary", action="store_true", help="Print human-readable summary"
    )

    # track batch <dir>
    track_batch_parser = track_subparsers.add_parser(
        "batch", help="Batch analyze multiple audio files in a directory"
    )
    track_batch_parser.add_argument(
        "directory", type=Path, help="Directory containing audio files"
    )
    track_batch_parser.add_argument(
        "--ext",
        default="wav,mp3,flac",
        help="Comma-separated list of audio extensions to include",
    )
    track_batch_parser.add_argument(
        "--recursive", action="store_true", help="Scan subdirectories recursively"
    )
    track_batch_parser.add_argument(
        "--output",
        type=Path,
        default=Path("batch_analysis.json"),
        help="Output JSON file for aggregated results",
    )
    track_batch_parser.add_argument(
        "--effects", action="store_true", help="Run effects analysis"
    )
    track_batch_parser.add_argument(
        "--instruments", action="store_true", help="Run instrument recognition"
    )
    track_batch_parser.add_argument(
        "--chords", action="store_true", help="Run chord detection"
    )
    track_batch_parser.add_argument(
        "--notes", action="store_true", help="Run note transcription"
    )
    track_batch_parser.add_argument(
        "--separation",
        choices=["hpss"],
        default=None,
        help="Source separation backend",
    )
    track_batch_parser.add_argument(
        "--backend",
        choices=["advanced", "basic"],
        default="advanced",
        help="Analysis backend",
    )

    # track yt-analyze <url>
    track_yt_parser = track_subparsers.add_parser(
        "yt-analyze", help="Download a YouTube video and analyze its audio"
    )
    track_yt_parser.add_argument("url", type=str, help="YouTube URL or video ID")
    track_yt_parser.add_argument(
        "--output-dir", type=Path, default=Path("yt_downloads"), help="Directory for downloaded audio"
    )
    track_yt_parser.add_argument(
        "--keep-audio", action="store_true", help="Keep the downloaded audio file after analysis"
    )
    track_yt_parser.add_argument(
        "--export-json", action="store_true", help="Export results to JSON file"
    )
    track_yt_parser.add_argument(
        "--effects", action="store_true", help="Run effects analysis"
    )
    track_yt_parser.add_argument(
        "--instruments", action="store_true", help="Run instrument recognition"
    )
    track_yt_parser.add_argument(
        "--chords", action="store_true", help="Run chord detection"
    )
    track_yt_parser.add_argument(
        "--notes", action="store_true", help="Run note transcription"
    )
    track_yt_parser.add_argument(
        "--separation",
        choices=["hpss"],
        default=None,
        help="Source separation backend",
    )
    track_yt_parser.add_argument(
        "--backend",
        choices=["advanced", "basic"],
        default="advanced",
        help="Analysis backend",
    )
    track_yt_parser.add_argument(
        "--summary", action="store_true", help="Print human-readable summary"
    )

    # track visualize <file>
    track_viz_parser = track_subparsers.add_parser(
        "visualize", help="Generate visualizations for a track"
    )
    track_viz_parser.add_argument("file", type=Path, help="Path to audio file")
    track_viz_parser.add_argument(
        "--output-dir", type=Path, default=Path("track_visuals"), help="Directory for plots"
    )
    track_viz_parser.add_argument(
        "--waveform", action="store_true", help="Render waveform plot"
    )
    track_viz_parser.add_argument(
        "--spectrogram", action="store_true", help="Render spectrogram plot"
    )
    track_viz_parser.add_argument(
        "--mel", action="store_true", help="Render mel spectrogram plot"
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

    # voice doctor <file> [--emit-chain out.yaml]
    voice_doctor_parser = voice_subparsers.add_parser(
        "doctor", help="Vocal Doctor: diagnose and recommend a processing chain"
    )
    voice_doctor_parser.add_argument(
        "file", type=Path, help="Path to vocal stem (WAV recommended)"
    )
    voice_doctor_parser.add_argument(
        "--emit-chain", type=Path, default=None, help="Write recommended chain YAML to this path"
    )
    voice_doctor_parser.add_argument(
        "--json", action="store_true", help="Output diagnosis and recommendations as JSON"
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
    # STEMS (v1 unified command)
    # =========================================================================
    stems_parser = subparsers.add_parser(
        "stems",
        help="Unified stem extraction: any wav/mp3 (or folder) in, stems out",
    )
    stems_parser.add_argument(
        "path",
        type=Path,
        help="Audio file or directory to process",
    )
    stems_parser.add_argument(
        "--preset",
        type=str,
        default="karaoke",
        choices=["karaoke", "vocals-hq", "full-vocals", "full-vocals-hq", "4stem", "6stem"],
        help="Separation preset (default: karaoke)",
    )
    stems_parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output directory (default: <TOOLSHOP_DATA_DIR>/stems/<preset>/<slug>)",
    )
    stems_parser.add_argument(
        "--data-root",
        type=Path,
        default=None,
        help="Data root used when --out is not provided",
    )
    stems_parser.add_argument(
        "--format",
        type=str,
        default=None,
        choices=["flac", "wav"],
        help="Output format (default: flac for stems, wav for legacy stem extract)",
    )
    stems_parser.add_argument(
        "--device",
        type=str,
        default="cpu",
        choices=["cpu", "gpu"],
        help="Device for inference (default: cpu)",
    )
    stems_parser.add_argument(
        "--model-file-dir",
        type=Path,
        default=None,
        help="Directory for downloaded separation models",
    )
    stems_parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Maximum tracks to process in batch mode (0 = all)",
    )
    stems_parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Number of tracks to skip in batch mode",
    )
    stems_parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Ignore existing batch_status.json and reprocess all files",
    )
    stems_parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    stems_parser.add_argument(
        "--list-models",
        action="store_true",
        help="List available presets and models, then exit",
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

    # =========================================================================
    # DOCTOR
    # =========================================================================
    doctor_parser = subparsers.add_parser(
        "doctor", help="Check environment and dependencies"
    )
    doctor_parser.add_argument(
        "--json", type=Path, default=None, help="Write JSON report to this file"
    )

    # =========================================================================
    # LYRICS (Genius) COMMANDS
    # =========================================================================
    lyrics_parser = subparsers.add_parser(
        "lyrics", help="Genius lyrics fetch, search, and analysis tools"
    )
    lyrics_subparsers = lyrics_parser.add_subparsers(dest="lyrics_command")
    lyrics_subparsers.required = True

    # lyrics fetch --url <url>
    lyrics_fetch_parser = lyrics_subparsers.add_parser(
        "fetch", help="Fetch lyrics from a Genius song page URL"
    )
    lyrics_fetch_parser.add_argument(
        "--url", type=str, required=True, help="Genius song page URL"
    )
    lyrics_fetch_parser.add_argument(
        "--outdir",
        type=Path,
        default=Path("lyrics_output"),
        help="Output directory for JSON + TXT files (default: lyrics_output)",
    )
    lyrics_fetch_parser.add_argument(
        "--strip-sections",
        action="store_true",
        help="Remove [Chorus], [Verse 1], etc. from clean lyrics",
    )

    # lyrics search --title "Song" --artist "Artist"
    lyrics_search_parser = lyrics_subparsers.add_parser(
        "search", help="Search Genius for a song and fetch its lyrics"
    )
    lyrics_search_parser.add_argument(
        "--title", type=str, required=True, help="Song title"
    )
    lyrics_search_parser.add_argument(
        "--artist", type=str, default="", help="Artist name (improves match)"
    )
    lyrics_search_parser.add_argument(
        "--outdir",
        type=Path,
        default=Path("lyrics_output"),
        help="Output directory for JSON + TXT files (default: lyrics_output)",
    )
    lyrics_search_parser.add_argument(
        "--strip-sections",
        action="store_true",
        help="Remove [Chorus], [Verse 1], etc. from clean lyrics",
    )

    # lyrics analyze --input <json>
    lyrics_analyze_parser = lyrics_subparsers.add_parser(
        "analyze", help="Analyze a previously fetched lyrics JSON file"
    )
    lyrics_analyze_parser.add_argument(
        "--input", type=Path, required=True, help="Path to lyrics JSON file"
    )
    lyrics_analyze_parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Save analysis report as JSON to this path",
    )

    # lyrics build-db [--root PATH] [--db PATH]
    lyrics_build_db_parser = lyrics_subparsers.add_parser(
        "build-db", help="Build lyrics SQLite database from Genius corpus"
    )
    lyrics_build_db_parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Corpus root directory (default: D:\\MusicData\\toolshop\\lyrics\\genius)",
    )
    lyrics_build_db_parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help="Database path (default: D:\\MusicData\\toolshop\\lyrics\\lyrics.db)",
    )

    # lyrics stats [--artist NAME] [--json] [--db PATH]
    lyrics_stats_parser = lyrics_subparsers.add_parser(
        "stats", help="Show per-artist lyrics statistics from the database"
    )
    lyrics_stats_parser.add_argument(
        "--artist", type=str, default=None, help="Filter to a specific artist"
    )
    lyrics_stats_parser.add_argument(
        "--json", action="store_true", help="Output as JSON instead of table"
    )
    lyrics_stats_parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help="Database path (default: D:\\MusicData\\toolshop\\lyrics\\lyrics.db)",
    )

    # lyrics rhymes [--artist NAME] [--song ID] [--json] [--db PATH]
    lyrics_rhymes_parser = lyrics_subparsers.add_parser(
        "rhymes", help="Show rhyme analysis from the database"
    )
    lyrics_rhymes_parser.add_argument(
        "--artist", type=str, default=None, help="Filter to a specific artist"
    )
    lyrics_rhymes_parser.add_argument(
        "--song", type=int, default=None, help="Filter to a specific song ID"
    )
    lyrics_rhymes_parser.add_argument(
        "--json", action="store_true", help="Output as JSON instead of table"
    )
    lyrics_rhymes_parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help="Database path (default: D:\\MusicData\\toolshop\\lyrics\\lyrics.db)",
    )

    # lyrics flow [--artist NAME] [--song ID] [--json] [--db PATH]
    lyrics_flow_parser = lyrics_subparsers.add_parser(
        "flow", help="Show flow analysis (syllable density, patterns) from the database"
    )
    lyrics_flow_parser.add_argument(
        "--artist", type=str, default=None, help="Filter to a specific artist"
    )
    lyrics_flow_parser.add_argument(
        "--song", type=int, default=None, help="Filter to a specific song ID"
    )
    lyrics_flow_parser.add_argument(
        "--json", action="store_true", help="Output as JSON instead of table"
    )
    lyrics_flow_parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help="Database path (default: D:\\MusicData\\toolshop\\lyrics\\lyrics.db)",
    )

    # lyrics collab [--artist NAME] [--json] [--db PATH]
    lyrics_collab_parser = lyrics_subparsers.add_parser(
        "collab", help="Show cross-artist collaboration analysis"
    )
    lyrics_collab_parser.add_argument(
        "--artist", type=str, default=None, help="Filter to a specific artist"
    )
    lyrics_collab_parser.add_argument(
        "--json", action="store_true", help="Output as JSON instead of table"
    )
    lyrics_collab_parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help="Database path (default: D:\\MusicData\\toolshop\\lyrics\\lyrics.db)",
    )

    return parser


def _print_doctor_summary(result: dict) -> None:
    """Print a human-readable summary of the Vocal Doctor result."""
    diagnosis = result["diagnosis"]
    print("\n" + "=" * 60)
    print("  VOCAL DOCTOR REPORT")
    print("=" * 60)
    print(f"  File:     {diagnosis.get('filename', diagnosis.get('file'))}")
    print(f"  Duration: {diagnosis.get('duration_seconds')}s")
    print(
        f"  Voice:    {'Detected' if diagnosis.get('voice_detected') else 'Not detected'}"
    )
    if diagnosis.get("fundamental_frequency_hz"):
        print(f"  F0:       {diagnosis['fundamental_frequency_hz']}Hz")

    metrics = diagnosis.get("metrics", {})
    loudness = metrics.get("loudness", {})
    if loudness.get("integrated_lufs") is not None:
        print(f"  LUFS:     {loudness['integrated_lufs']:.1f}")
    if loudness.get("loudness_range") is not None:
        print(f"  LRA:      {loudness['loudness_range']:.1f} dB")

    print("\n  Recommendations:")
    print("  " + "-" * 56)
    for r in result.get("recommendations", []):
        conf = r.get("confidence", 0)
        bar = "#" * int(conf * 20)
        print(f"  [{conf:.0%}] {bar:<20} {r['rule']}")
        print(f"        Problem: {r['problem']}")
        print(f"        Action:  {r['chain_action']}")
        for ev in r.get("evidence", [])[:2]:
            print(f"        > {ev}")
        print()

    print("=" * 60)


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
                chords=args.chords,
                notes=args.notes,
                separation=args.separation,
                backend=args.backend,
            )
            if args.summary:
                reverse_engineering_adapter.print_summary(result)
            else:
                print(json.dumps(result, indent=2, default=str))

        elif args.track_command == "batch":
            extensions = [e.strip().lstrip(".") for e in args.ext.split(",")]
            files = []
            if args.recursive:
                for ext in extensions:
                    files.extend(args.directory.rglob(f"*.{ext}"))
            else:
                for ext in extensions:
                    files.extend(args.directory.glob(f"*.{ext}"))
            files = sorted(files)

            if not files:
                parser.error(
                    f"No audio files found in {args.directory} with extensions {extensions}"
                )

            results = []
            for audio_path in files:
                try:
                    result = reverse_engineering_adapter.analyze_track(
                        path=audio_path,
                        effects=args.effects,
                        instruments=args.instruments,
                        chords=args.chords,
                        notes=args.notes,
                        separation=args.separation,
                        backend=args.backend,
                    )
                    results.append(result)
                except Exception as exc:
                    results.append({"file": str(audio_path), "error": str(exc)})

            batch_report = {
                "directory": str(args.directory),
                "files_analyzed": len(results),
                "results": results,
            }
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("w", encoding="utf-8") as f:
                json.dump(batch_report, f, indent=2, default=str)
            print(f"Batch analysis saved to {args.output} ({len(results)} tracks)")

        elif args.track_command == "yt-analyze":
            audio_path = yt_scraper_adapter.download_audio(args.url, args.output_dir)
            try:
                result = reverse_engineering_adapter.analyze_track(
                    path=audio_path,
                    export_json=args.export_json,
                    output_dir=args.output_dir,
                    effects=args.effects,
                    instruments=args.instruments,
                    chords=args.chords,
                    notes=args.notes,
                    separation=args.separation,
                    backend=args.backend,
                )
                if args.summary:
                    reverse_engineering_adapter.print_summary(result)
                else:
                    print(json.dumps(result, indent=2, default=str))
            finally:
                if not args.keep_audio and audio_path.exists():
                    audio_path.unlink()

        elif args.track_command == "visualize":
            try:
                from wav_reverse_engineer.audio_analyzer.audio_processor import AudioProcessor
                from wav_reverse_engineer.audio_analyzer.visualizer import AudioVisualizer
            except Exception as exc:
                parser.error(
                    f"Visualization requires the wav_reverse_engineer package: {exc}"
                )

            audio, sr = AudioProcessor.load_audio(str(args.file), target_sr=22050, mono=True)
            args.output_dir.mkdir(parents=True, exist_ok=True)
            stem = args.file.stem

            selected = args.waveform or args.spectrogram or args.mel
            if args.waveform or not selected:
                output = args.output_dir / f"{stem}_waveform.png"
                AudioVisualizer.plot_waveform(
                    audio, sr, title=f"{args.file.name} - Waveform",
                    output_path=str(output), show=False,
                )
                print(f"Waveform saved to {output}")
            if args.spectrogram or not selected:
                output = args.output_dir / f"{stem}_spectrogram.png"
                AudioVisualizer.plot_spectrogram(
                    audio, sr, title=f"{args.file.name} - Spectrogram",
                    output_path=str(output), show=False,
                )
                print(f"Spectrogram saved to {output}")
            if args.mel or not selected:
                output = args.output_dir / f"{stem}_mel_spectrogram.png"
                AudioVisualizer.plot_mel_spectrogram(
                    audio, sr, title=f"{args.file.name} - Mel Spectrogram",
                    output_path=str(output), show=False,
                )
                print(f"Mel spectrogram saved to {output}")

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
        elif args.voice_command == "doctor":
            result = diagnose_and_recommend(args.file)
            if args.emit_chain:
                chain = result["chain"]
                from mastering_tool.tools.chain_dsl.schema import Chain
                Chain.from_dict(chain).to_yaml(args.emit_chain)
            if args.json:
                print(json.dumps(result, indent=2, default=str))
            else:
                _print_doctor_summary(result)
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
    # STEMS (v1 unified command)
    # =========================================================================
    elif args.command == "stems":
        from . import stems_cli

        code = stems_cli.run(args)
        if code != 0:
            raise SystemExit(code)

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

    # =========================================================================
    # DOCTOR
    # =========================================================================
    elif args.command == "doctor":
        code = doctor_module.main(["--json", str(args.json)] if args.json else [])
        if code != 0:
            raise SystemExit(code)

    # =========================================================================
    # LYRICS (Genius)
    # =========================================================================
    elif args.command == "lyrics":
        from . import genius_adapter
        from . import lyrics_analyzer as lyrics_analyzer_mod

        if args.lyrics_command == "fetch":
            print(f"Fetching lyrics from {args.url}...")
            client = genius_adapter.GeniusClient()
            lyrics_data = client.fetch_lyrics(
                url=args.url,
                strip_section_labels=args.strip_sections,
            )
            json_path, txt_path = genius_adapter.save_lyrics(lyrics_data, args.outdir)
            print(f"\n✓ Lyrics fetched:")
            print(f"  Title:   {lyrics_data['title']}")
            print(f"  Artist:  {lyrics_data['artist']}")
            print(f"  Lines:   {lyrics_data['clean_lyrics'].count(chr(10)) + 1}")
            print(f"  JSON:    {json_path}")
            print(f"  TXT:     {txt_path}")

        elif args.lyrics_command == "search":
            print(f"Searching Genius for '{args.title}' by '{args.artist}'...")
            client = genius_adapter.GeniusClient()
            result = client.search_song(args.title, args.artist)
            print(f"Found: {result.title} — {result.artist} ({result.url})")
            lyrics_data = client.fetch_lyrics(
                url=result.url,
                strip_section_labels=args.strip_sections,
            )
            json_path, txt_path = genius_adapter.save_lyrics(lyrics_data, args.outdir)
            print(f"\n✓ Lyrics fetched:")
            print(f"  Title:   {lyrics_data['title']}")
            print(f"  Artist:  {lyrics_data['artist']}")
            print(f"  Lines:   {lyrics_data['clean_lyrics'].count(chr(10)) + 1}")
            print(f"  JSON:    {json_path}")
            print(f"  TXT:     {txt_path}")

        elif args.lyrics_command == "analyze":
            stats = lyrics_analyzer_mod.analyze_file(args.input)
            lyrics_analyzer_mod.print_report(stats)
            if args.report:
                lyrics_analyzer_mod.save_report(stats, args.report)
                print(f"\n  Report saved to: {args.report}")

        elif args.lyrics_command == "build-db":
            from toolshop.lyricsdb import build_database, DEFAULT_DB_PATH
            root = args.root or Path(r"D:\MusicData\toolshop\lyrics\genius")
            db_path = args.db or DEFAULT_DB_PATH
            print(f"Building lyrics database...")
            print(f"  Corpus root: {root}")
            print(f"  Database:     {db_path}")
            summary = build_database(root=root, db_path=db_path)
            print(f"\nDone. Songs: {summary['songs_ingested']}, "
                  f"Sections: {summary['sections_ingested']}, "
                  f"Lines: {summary['lines_ingested']}, "
                  f"Duplicates dropped: {summary['duplicates_dropped']}")

        elif args.lyrics_command == "stats":
            import json as json_mod
            import sqlite3
            from toolshop.lyricsdb import DEFAULT_DB_PATH
            from toolshop.lyrics_metrics import (
                get_artist_stats, get_top_words_for_artist,
                get_section_type_distribution, get_syllable_distribution,
            )
            db_path = args.db or DEFAULT_DB_PATH
            if not db_path.exists():
                print(f"Database not found: {db_path}")
                print("Run 'toolshop lyrics build-db' first.")
                return
            conn = sqlite3.connect(db_path)
            artists = get_artist_stats(conn, artist=args.artist)
            if args.json:
                print(json_mod.dumps(artists, indent=2, ensure_ascii=False))
            else:
                if not artists:
                    print(f"No data found for artist: {args.artist}")
                    conn.close()
                    return
                print(f"\n{'Artist':<25} {'Songs':>5} {'Avg W':>7} {'TTR':>6} "
                      f"{'Avg L':>6} {'Syl/L':>6} {'HookR':>6} {'Eng%':>6}")
                print("-" * 80)
                for a in artists:
                    print(f"{a['primary_artist']:<25} {a['song_count']:>5} "
                          f"{a['avg_total_words']:>7.1f} {a['avg_ttr']:>6.4f} "
                          f"{a['avg_line_count']:>6.1f} {a['avg_syllables_per_line']:>6.2f} "
                          f"{a['avg_hook_repetition_ratio']:>6.4f} {a['avg_english_loanword_rate']:>6.4f}")
                if not args.artist:
                    print(f"\nSection type distribution:")
                    for s in get_section_type_distribution(conn):
                        print(f"  {s['type']:<15} {s['count']}")
                    print(f"\nSyllables/line distribution:")
                    for s in get_syllable_distribution(conn):
                        print(f"  {s['bucket']:<8} {s['count']}")
                else:
                    print(f"\nTop 20 words for {args.artist}:")
                    for word, count in get_top_words_for_artist(conn, args.artist, 20):
                        print(f"  {word:>15s}  {count}")
            conn.close()

        elif args.lyrics_command == "rhymes":
            import json as json_mod
            import sqlite3
            from toolshop.lyricsdb import DEFAULT_DB_PATH
            from toolshop.rhyme_miner import get_artist_rhyme_stats
            db_path = args.db or DEFAULT_DB_PATH
            if not db_path.exists():
                print(f"Database not found: {db_path}")
                print("Run 'toolshop lyrics build-db' first.")
                return
            conn = sqlite3.connect(db_path)
            stats = get_artist_rhyme_stats(conn, artist=args.artist)
            if args.json:
                print(json_mod.dumps(stats, indent=2, ensure_ascii=False))
            else:
                if not stats:
                    print(f"No rhyme data found for artist: {args.artist}")
                    conn.close()
                    return
                print(f"\n{'Artist':<25} {'Songs':>5} {'Rhyme Lines':>12} "
                      f"{'Avg Match':>10} {'Multi-Syl':>10}")
                print("-" * 70)
                for s in stats:
                    print(f"{s['primary_artist']:<25} {s['songs_with_rhymes']:>5} "
                          f"{s['total_rhyme_lines']:>12} {s['avg_match_length']:>10.2f} "
                          f"{s['multisyllabic_count']:>10}")
            conn.close()

        elif args.lyrics_command == "flow":
            import json as json_mod
            import sqlite3
            from toolshop.lyricsdb import DEFAULT_DB_PATH
            from toolshop.flow_analyzer import artist_flow_summary, flow_profile
            db_path = args.db or DEFAULT_DB_PATH
            if not db_path.exists():
                print(f"Database not found: {db_path}")
                print("Run 'toolshop lyrics build-db' first.")
                return
            conn = sqlite3.connect(db_path)
            if args.song:
                profile = flow_profile(conn, args.song)
                if args.json:
                    print(json_mod.dumps(profile, indent=2, ensure_ascii=False))
                else:
                    print(f"\nFlow Profile for Song ID {args.song}")
                    print(f"  Title: {profile.get('title', '?')}")
                    print(f"  Artist: {profile.get('artist', '?')}")
                    print(f"  Avg syllables/line: {profile.get('avg_syllables_per_line', 0):.2f}")
                    print(f"  Syllable density: {profile.get('syllable_density', 0):.4f}")
                    print(f"  Speed variation (CV): {profile.get('speed_variation', 0):.4f}")
                    print(f"  Pattern: {profile.get('pattern', 'unknown')}")
                    print(f"  Sections:")
                    for sec in profile.get("sections", []):
                        print(f"    {sec['type']:<15} syl/line={sec['avg_syllables']:.2f}  "
                              f"lines={sec['line_count']}")
            else:
                stats = artist_flow_summary(conn, artist=args.artist)
                if args.json:
                    print(json_mod.dumps(stats, indent=2, ensure_ascii=False))
                else:
                    if not stats:
                        print(f"No flow data found for artist: {args.artist}")
                        conn.close()
                        return
                    print(f"\n{'Artist':<25} {'Songs':>5} {'Avg Syl/L':>10} "
                          f"{'Density':>10} {'SpeedVar':>10} {'Pattern':>10}")
                    print("-" * 75)
                    for s in stats:
                        print(f"{s['primary_artist']:<25} {s['song_count']:>5} "
                              f"{s['avg_syllables_per_line']:>10.2f} "
                              f"{s['avg_density']:>10.4f} "
                              f"{s['avg_speed_variation']:>10.4f} "
                              f"{s['dominant_pattern']:>10}")
            conn.close()

        elif args.lyrics_command == "collab":
            import json as json_mod
            import sqlite3
            from toolshop.lyricsdb import DEFAULT_DB_PATH
            from toolshop.collab_analysis import artist_collab_summary
            db_path = args.db or DEFAULT_DB_PATH
            if not db_path.exists():
                print(f"Database not found: {db_path}")
                print("Run 'toolshop lyrics build-db' first.")
                return
            conn = sqlite3.connect(db_path)
            stats = artist_collab_summary(conn, artist=args.artist)
            if args.json:
                print(json_mod.dumps(stats, indent=2, ensure_ascii=False))
            else:
                if not stats:
                    print("No collaboration data found.")
                    conn.close()
                    return
                print(f"\n{'Artist':<25} {'Collab Songs':>12} {'Solo Songs':>10} "
                      f"{'Avg Syl/L':>10} {'Avg TTR':>10}")
                print("-" * 70)
                for s in stats:
                    print(f"{s['primary_artist']:<25} {s['collab_song_count']:>12} "
                          f"{s['solo_song_count']:>10} "
                          f"{s.get('avg_syllables_per_line', 0):>10.2f} "
                          f"{s.get('avg_ttr', 0):>10.4f}")
            conn.close()

        else:
            parser.error("Unknown 'lyrics' subcommand.")

    else:
        parser.error(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
