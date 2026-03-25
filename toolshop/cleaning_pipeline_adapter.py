"""Audio cleaning pipeline controller and CLI integration."""

import click
import yaml
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np

from .cleaning_stages import (
    PreprocessingStage,
    PauseRemovalStage,
    BreathDetectionStage,
    EventDetectionStage,
    BeatAlignmentStage,
    FinalAssemblyStage,
    StageResult,
)


class AudioCleaningPipeline:
    """Main pipeline controller that orchestrates all cleaning stages."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.stages = self._initialize_stages()

    def _initialize_stages(self) -> List:
        """Initialize all stages based on configuration."""
        stages = []
        stage_configs = self.config.get("stages", {})

        # Always include preprocessing
        prep_config = stage_configs.get("preprocessing", {})
        stages.append(
            PreprocessingStage(
                target_sr=prep_config.get("target_sample_rate", 44100),
                normalize=prep_config.get("normalize_input", True),
            )
        )

        # Pause removal
        if "pause_removal" in stage_configs:
            pause_config = stage_configs["pause_removal"]
            stages.append(
                PauseRemovalStage(
                    min_silence=pause_config.get("min_silence", 0.3),
                    max_keep=pause_config.get("max_keep", 0.5),
                    threshold_db=pause_config.get("threshold_db", -40),
                    crossfade_ms=pause_config.get("crossfade_ms", 10),
                )
            )

        # Breath detection
        if "breath_detection" in stage_configs:
            breath_config = stage_configs["breath_detection"]
            stages.append(
                BreathDetectionStage(
                    method=breath_config.get("method", "combined"),
                    attenuation_db=breath_config.get("attenuation_db", 15),
                    frequency_range=tuple(
                        breath_config.get("frequency_range", [200, 2000])
                    ),
                    min_breath_duration=breath_config.get("min_breath_duration", 0.1),
                    max_breath_duration=breath_config.get("max_breath_duration", 0.8),
                )
            )

        # Event detection
        if "event_detection" in stage_configs:
            event_config = stage_configs["event_detection"]
            stages.append(
                EventDetectionStage(
                    detect_coughs=event_config.get("detect_coughs", True),
                    detect_clicks=event_config.get("detect_clicks", True),
                    detect_pops=event_config.get("detect_pops", True),
                    confidence_threshold=event_config.get("confidence_threshold", 0.7),
                )
            )

        # Beat alignment
        if "beat_alignment" in stage_configs:
            beat_config = stage_configs["beat_alignment"]
            stages.append(
                BeatAlignmentStage(
                    mode=beat_config.get("mode", "analyze"),
                    target_bpm=beat_config.get("target_bpm"),
                )
            )

        return stages

    def process(self, input_path: str, output_path: Optional[str] = None) -> Dict:
        """Run the full pipeline on an audio file."""
        # Validate input
        input_path = Path(input_path)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        # Run stages
        result = None
        all_reports = []

        for i, stage in enumerate(self.stages):
            stage_name = stage.__class__.__name__

            if i == 0:  # Preprocessing stage takes path
                result = stage.process(str(input_path))
            else:
                result = stage.process(result)

            all_reports.append(result.report)

        # Final assembly
        final_config = self.config.get("final_assembly", {})
        final_stage = FinalAssemblyStage(
            target_lufs=final_config.get("target_lufs", -16.0),
            output_format=final_config.get("output_format", "wav"),
        )

        output_file, summary = final_stage.process(result, all_reports)

        # Move to requested output path if specified
        if output_path:
            import shutil

            shutil.move(output_file, output_path)
            summary["output_file"] = output_path

        return summary


def load_config(config_path: str) -> Dict[str, Any]:
    """Load pipeline configuration from YAML file."""
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def get_default_config() -> Dict[str, Any]:
    """Get default pipeline configuration."""
    return {
        "stages": {
            "preprocessing": {"target_sample_rate": 44100, "normalize_input": True},
            "pause_removal": {
                "min_silence": 0.3,
                "max_keep": 0.5,
                "threshold_db": -40,
                "crossfade_ms": 10,
            },
            "breath_detection": {
                "method": "combined",
                "attenuation_db": 15,
                "frequency_range": [200, 2000],
                "min_breath_duration": 0.1,
                "max_breath_duration": 0.8,
            },
            "event_detection": {
                "detect_coughs": True,
                "detect_clicks": True,
                "detect_pops": True,
                "confidence_threshold": 0.7,
            },
            "beat_alignment": {"mode": "analyze", "target_bpm": None},
        },
        "final_assembly": {"target_lufs": -16.0, "output_format": "wav"},
    }


# CLI Commands
@click.group(name="clean")
def clean_cli():
    """Audio cleaning and track preparation tools."""
    pass


@clean_cli.command(name="pipeline")
@click.argument("input_file", type=click.Path(exists=True))
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    help="Pipeline configuration YAML file",
)
@click.option("--output", "-o", type=click.Path(), help="Output file path")
@click.option(
    "--report", "-r", type=click.Path(), help="Save processing report to JSON file"
)
def pipeline_cmd(input_file, config, output, report):
    """Run full cleaning pipeline on audio file."""
    # Load configuration
    if config:
        pipeline_config = load_config(config)
    else:
        pipeline_config = get_default_config()

    # Run pipeline
    pipeline = AudioCleaningPipeline(pipeline_config)
    summary = pipeline.process(input_file, output)

    # Display results
    click.echo(f"\n✓ Audio cleaning complete!")
    click.echo(f"  Output: {summary['output_file']}")
    click.echo(f"  Duration: {summary['duration']:.2f}s")
    click.echo(f"  Stages applied: {summary['stages_applied']}")
    click.echo(f"  BPM: {summary.get('original_bpm', 'N/A')}")
    click.echo(f"  Key: {summary.get('original_key', 'N/A')}")

    # Show stage details
    click.echo("\n  Stage results:")
    for i, stage_report in enumerate(summary["stage_reports"], 1):
        stage_name = stage_report.get("stage", f"Stage {i}")
        status = stage_report.get("status", "unknown")
        click.echo(f"    {i}. {stage_name}: {status}")

        # Show specific metrics for certain stages
        if "breaths_detected" in stage_report:
            click.echo(f"       - Breaths detected: {stage_report['breaths_detected']}")
        if "events_detected" in stage_report:
            click.echo(f"       - Events detected: {stage_report['events_detected']}")
        if "time_removed" in stage_report:
            click.echo(f"       - Time removed: {stage_report['time_removed']:.2f}s")

    # Save report if requested
    if report:
        with open(report, "w") as f:
            json.dump(summary, f, indent=2)
        click.echo(f"\n  Report saved to: {report}")


@clean_cli.command(name="pause-remove")
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--threshold", "-t", default=-40, help="Silence threshold in dB")
@click.option("--min-silence", default=0.3, help="Minimum silence to remove (seconds)")
@click.option("--output", "-o", type=click.Path(), help="Output file path")
def pause_remove_cmd(input_file, threshold, min_silence, output):
    """Remove long pauses and silences from audio."""
    config = get_default_config()
    config["stages"] = {
        "preprocessing": config["stages"]["preprocessing"],
        "pause_removal": {
            "min_silence": min_silence,
            "max_keep": 0.5,
            "threshold_db": threshold,
            "crossfade_ms": 10,
        },
    }

    pipeline = AudioCleaningPipeline(config)
    summary = pipeline.process(input_file, output)

    pause_report = (
        summary["stage_reports"][1] if len(summary["stage_reports"]) > 1 else {}
    )

    click.echo(f"\n✓ Pause removal complete!")
    click.echo(f"  Time removed: {pause_report.get('time_removed', 0):.2f}s")
    click.echo(f"  Segments kept: {pause_report.get('segments_kept', 0)}")
    click.echo(f"  Output: {summary['output_file']}")


@clean_cli.command(name="breath-detect")
@click.argument("input_file", type=click.Path(exists=True))
@click.option("--attenuation", "-a", default=15, help="Attenuation in dB")
@click.option(
    "--method",
    "-m",
    type=click.Choice(["frequency", "energy", "combined"]),
    default="combined",
    help="Detection method",
)
@click.option("--output", "-o", type=click.Path(), help="Output file path")
def breath_detect_cmd(input_file, attenuation, method, output):
    """Detect and attenuate breath sounds."""
    config = get_default_config()
    config["stages"] = {
        "preprocessing": config["stages"]["preprocessing"],
        "breath_detection": {
            "method": method,
            "attenuation_db": attenuation,
            "frequency_range": [200, 2000],
            "min_breath_duration": 0.1,
            "max_breath_duration": 0.8,
        },
    }

    pipeline = AudioCleaningPipeline(config)
    summary = pipeline.process(input_file, output)

    breath_report = (
        summary["stage_reports"][1] if len(summary["stage_reports"]) > 1 else {}
    )

    click.echo(f"\n✓ Breath detection complete!")
    click.echo(f"  Breaths detected: {breath_report.get('breaths_detected', 0)}")
    click.echo(f"  Method: {breath_report.get('method', method)}")
    click.echo(f"  Attenuation: {attenuation}dB")
    click.echo(f"  Output: {summary['output_file']}")

    if breath_report.get("detections"):
        click.echo(f"\n  Detection details:")
        for det in breath_report["detections"][:5]:  # Show first 5
            click.echo(
                f"    - {det['start']:.2f}s to {det['end']:.2f}s "
                f"(confidence: {det['confidence']:.2f})"
            )


@clean_cli.command(name="event-detect")
@click.argument("input_file", type=click.Path(exists=True))
@click.option(
    "--detect",
    "-d",
    multiple=True,
    type=click.Choice(["coughs", "clicks", "pops"]),
    default=["coughs", "clicks", "pops"],
    help="Event types to detect",
)
@click.option("--confidence", "-c", default=0.7, help="Detection confidence threshold")
@click.option("--output", "-o", type=click.Path(), help="Output file path")
def event_detect_cmd(input_file, detect, confidence, output):
    """Detect and remove discrete events (coughs, clicks, pops)."""
    config = get_default_config()
    config["stages"] = {
        "preprocessing": config["stages"]["preprocessing"],
        "event_detection": {
            "detect_coughs": "coughs" in detect,
            "detect_clicks": "clicks" in detect,
            "detect_pops": "pops" in detect,
            "confidence_threshold": confidence,
        },
    }

    pipeline = AudioCleaningPipeline(config)
    summary = pipeline.process(input_file, output)

    event_report = (
        summary["stage_reports"][1] if len(summary["stage_reports"]) > 1 else {}
    )

    click.echo(f"\n✓ Event detection complete!")
    click.echo(f"  Total events: {event_report.get('events_detected', 0)}")
    click.echo(f"  Coughs: {event_report.get('coughs', 0)}")
    click.echo(f"  Clicks: {event_report.get('clicks', 0)}")
    click.echo(f"  Pops: {event_report.get('pops', 0)}")
    click.echo(f"  Output: {summary['output_file']}")


@clean_cli.command(name="beat-align")
@click.argument("input_file", type=click.Path(exists=True))
@click.option(
    "--mode",
    "-m",
    type=click.Choice(["analyze", "align"]),
    default="analyze",
    help="Analysis or alignment mode",
)
@click.option("--target-bpm", "-b", type=float, help="Target BPM for alignment")
@click.option("--report", "-r", type=click.Path(), help="Save beat report to JSON")
def beat_align_cmd(input_file, mode, target_bpm, report):
    """Analyze beats and optionally align to tempo grid."""
    config = get_default_config()
    config["stages"] = {
        "preprocessing": config["stages"]["preprocessing"],
        "beat_alignment": {"mode": mode, "target_bpm": target_bpm},
    }

    pipeline = AudioCleaningPipeline(config)
    summary = pipeline.process(input_file)

    beat_report = (
        summary["stage_reports"][1] if len(summary["stage_reports"]) > 1 else {}
    )
    metadata = (
        summary.get("stage_reports", [{}])[0] if summary.get("stage_reports") else {}
    )

    click.echo(f"\n✓ Beat analysis complete!")
    click.echo(f"  Mode: {beat_report.get('mode', mode)}")
    click.echo(f"  BPM: {beat_report.get('bpm', metadata.get('bpm', 'N/A'))}")
    click.echo(f"  Beat count: {beat_report.get('beat_count', 'N/A')}")

    if beat_report.get("tempo_stability"):
        click.echo(f"  Tempo stability: {beat_report['tempo_stability']:.2f} BPM std")

    if report:
        beat_data = {
            "bpm": beat_report.get("bpm"),
            "beat_count": beat_report.get("beat_count"),
            "tempo_stability": beat_report.get("tempo_stability"),
            "original_key": summary.get("original_key"),
        }
        with open(report, "w") as f:
            json.dump(beat_data, f, indent=2)
        click.echo(f"\n  Report saved to: {report}")


@clean_cli.command(name="config-template")
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    required=True,
    help="Output file path for config template",
)
def config_template_cmd(output):
    """Generate a default pipeline configuration file."""
    config = get_default_config()

    with open(output, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    click.echo(f"✓ Configuration template saved to: {output}")
    click.echo(
        f"\nEdit this file and use with: toolshop clean pipeline audio.wav --config {output}"
    )
