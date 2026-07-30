"""FFmpeg compositing for music video generation.

All FFmpeg calls via subprocess.run (not ffmpeg-python wrapper).
Provides showwaves, Ken Burns, beat-cut concat, crossfade, ASS overlay,
and full pipeline orchestration.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def check_ffmpeg(required: bool = False) -> bool:
    """Check if ffmpeg is available on the system.

    Args:
        required: If True, raise RuntimeError when ffmpeg is missing.

    Returns:
        True if ffmpeg is found, False otherwise.
    """
    found = shutil.which("ffmpeg") is not None
    if required and not found:
        raise RuntimeError(
            "ffmpeg not found on PATH. Install ffmpeg or add it to PATH."
        )
    return found


def _run_ffmpeg(cmd: List[str]) -> None:
    """Run an ffmpeg command and check for errors."""
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"FFmpeg failed (exit {result.returncode}): {stderr}")


def _build_showwaves_cmd(
    audio: Path, output: Path, size: str = "1280x720", fps: int = 30, mode: str = "cline"
) -> List[str]:
    """Build ffmpeg command for showwaves visualization."""
    return [
        "ffmpeg", "-y",
        "-i", str(audio),
        "-filter_complex",
        f"[0:a]showwaves=s={size}:mode={mode}:rate={fps},format=yuv420p[v]",
        "-map", "[v]", "-map", "0:a",
        "-c:v", "libx264", "-crf", "18",
        "-c:a", "aac",
        "-shortest",
        str(output),
    ]


def render_showwaves(
    audio: Path, output: Path, size: str = "1280x720", fps: int = 30, mode: str = "cline"
) -> Path:
    """Render an audio waveform visualization video.

    Args:
        audio: Path to audio file.
        output: Path for output MP4.
        size: Video resolution (WxH).
        fps: Frames per second.
        mode: showwaves mode (cline, line, p2p, center).

    Returns:
        Path to output file.
    """
    check_ffmpeg(required=True)
    cmd = _build_showwaves_cmd(audio, output, size, fps, mode)
    _run_ffmpeg(cmd)
    return output


def _build_ken_burns_cmd(
    image: Path,
    audio: Path,
    output: Path,
    size: str = "1280x720",
    fps: int = 30,
    zoom: float = 1.5,
) -> List[str]:
    """Build ffmpeg command for Ken Burns effect (slow zoom on static image)."""
    total_frames = 99999  # -shortest will handle actual duration
    return [
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(image),
        "-i", str(audio),
        "-vf",
        f"scale={size}:force_original_aspect_ratio=increase,"
        f"crop={size},"
        f"zoompan=z='min(zoom+0.0015,{zoom})':d={total_frames}:s={size}:fps={fps}",
        "-c:v", "libx264", "-tune", "stillimage",
        "-c:a", "aac",
        "-shortest",
        str(output),
    ]


def render_ken_burns(
    image: Path,
    audio: Path,
    output: Path,
    size: str = "1280x720",
    fps: int = 30,
    zoom: float = 1.5,
) -> Path:
    """Render a Ken Burns (slow zoom) video from a static image + audio.

    Args:
        image: Path to image file (JPG/PNG).
        audio: Path to audio file.
        output: Path for output MP4.
        size: Video resolution (WxH).
        fps: Frames per second.
        zoom: Maximum zoom factor.

    Returns:
        Path to output file.
    """
    check_ffmpeg(required=True)
    cmd = _build_ken_burns_cmd(image, audio, output, size, fps, zoom)
    _run_ffmpeg(cmd)
    return output


def concat_beat_cuts(
    clips: List[Path],
    audio: Path,
    output: Path,
    concat_list: Optional[Path] = None,
) -> Path:
    """Concatenate pre-split clips at beat boundaries.

    Args:
        clips: List of clip file paths in order.
        audio: Path to source audio file.
        output: Path for output MP4.
        concat_list: Optional path for the concat list file.

    Returns:
        Path to output file.
    """
    check_ffmpeg(required=True)

    if concat_list is None:
        concat_list = output.parent / "concat.txt"

    lines = [f"file '{os.path.basename(str(c))}'" for c in clips]
    concat_list.write_text("\n".join(lines) + "\n", encoding="utf-8")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_list),
        "-i", str(audio),
        "-c:v", "libx264", "-crf", "18",
        "-c:a", "aac",
        "-shortest",
        str(output),
    ]
    _run_ffmpeg(cmd)
    return output


def crossfade_clips(
    clip_a: Path, clip_b: Path, output: Path, offset: float = 3.0, duration: float = 0.5
) -> Path:
    """Crossfade two clips with xfade filter.

    Args:
        clip_a: First clip path.
        clip_b: Second clip path.
        output: Path for output MP4.
        offset: Start time of crossfade in seconds.
        duration: Crossfade duration in seconds.

    Returns:
        Path to output file.
    """
    check_ffmpeg(required=True)
    cmd = [
        "ffmpeg", "-y",
        "-i", str(clip_a),
        "-i", str(clip_b),
        "-filter_complex",
        f"[0:v][1:v]xfade=transition=fade:duration={duration}:offset={offset}",
        "-c:v", "libx264", "-crf", "18",
        "-c:a", "aac",
        str(output),
    ]
    _run_ffmpeg(cmd)
    return output


def _build_overlay_ass_cmd(
    video: Path, ass_file: Path, output: Path
) -> List[str]:
    """Build ffmpeg command for ASS subtitle overlay."""
    ass_path_escaped = str(ass_file).replace("\\", "/").replace(":", "\\:")
    return [
        "ffmpeg", "-y",
        "-i", str(video),
        "-vf", f"ass='{ass_path_escaped}'",
        "-c:v", "libx264", "-crf", "18",
        "-c:a", "copy",
        str(output),
    ]


def overlay_ass(video: Path, ass_file: Path, output: Path) -> Path:
    """Burn in ASS subtitles onto a video.

    Args:
        video: Path to base video.
        ass_file: Path to .ass subtitle file.
        output: Path for output MP4.

    Returns:
        Path to output file.
    """
    check_ffmpeg(required=True)
    cmd = _build_overlay_ass_cmd(video, ass_file, output)
    _run_ffmpeg(cmd)
    return output


def compose_pipeline(
    features_path: Path,
    audio: Path,
    output: Path,
    background: str = "showwaves",
    ass_file: Optional[Path] = None,
    image: Optional[Path] = None,
    size: str = "1280x720",
    fps: int = 30,
    intermediate_dir: Optional[Path] = None,
) -> Path:
    """Full compositing pipeline: background → optional ASS overlay → output.

    Args:
        features_path: Path to features JSON (from video_features.extract_features).
        audio: Path to source audio file.
        output: Path for final output MP4.
        background: Background type: 'showwaves', 'ken_burns', 'image:PATH', or 'shader:PRESET'.
        ass_file: Optional ASS subtitle file for lyric burn-in.
        image: Image path for ken_burns background (required if background='ken_burns').
        size: Video resolution (WxH).
        fps: Frames per second.
        intermediate_dir: Directory for intermediate files (default: output.parent).

    Returns:
        Path to final output file.
    """
    check_ffmpeg(required=True)

    if not features_path.exists():
        raise FileNotFoundError(f"Features file not found: {features_path}")

    features = json.loads(features_path.read_text(encoding="utf-8"))
    inter_dir = intermediate_dir or output.parent
    inter_dir.mkdir(parents=True, exist_ok=True)

    base_video = inter_dir / "base_video.mp4"

    if background == "showwaves":
        render_showwaves(audio, base_video, size=size, fps=fps)
    elif background == "ken_burns":
        if image is None:
            raise ValueError("ken_burns background requires --image")
        render_ken_burns(image, audio, base_video, size=size, fps=fps)
    elif background.startswith("image:"):
        image_path = Path(background.split(":", 1)[1])
        render_ken_burns(image_path, audio, base_video, size=size, fps=fps)
    elif background.startswith("shader:"):
        preset = background.split(":", 1)[1]
        from .video_shaders import render_shader_video
        duration = features.get("duration", 30.0)
        n_frames = int(duration * fps)
        w, h = size.split("x")
        render_shader_video(
            preset=preset,
            features=features,
            output=base_video,
            width=int(w),
            height=int(h),
            fps=fps,
            n_frames=n_frames,
            audio=audio,
        )
    else:
        raise ValueError(f"Unknown background type: {background}")

    if ass_file and ass_file.exists():
        overlay_ass(base_video, ass_file, output)
    else:
        # Just copy the base video as output
        import shutil as _shutil
        _shutil.copy2(base_video, output)

    return output
