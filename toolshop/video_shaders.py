"""Audio-reactive shader renderer using ModernGL.

Renders fragment shaders offscreen with uniforms derived from audio features.
Outputs PNG frame sequences that are piped to FFmpeg for video encoding.
Uses moderngl.create_standalone_context() for headless rendering (no window).
"""

from __future__ import annotations

import math
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import moderngl
    import numpy as np
    from PIL import Image

    _HAS_MODERNGL = True
except ImportError:
    _HAS_MODERNGL = False
    moderngl = None  # type: ignore
    np = None  # type: ignore
    Image = None  # type: ignore

from .video_compose import check_ffmpeg


_VERTEX_SHADER = """
#version 330
in vec2 in_vert;
out vec2 v_uv;
void main() {
    v_uv = in_vert * 0.5 + 0.5;
    gl_Position = vec4(in_vert, 0.0, 1.0);
}
"""

SHADER_PRESETS: Dict[str, str] = {
    "neon_grid": """
#version 330
uniform float u_time;
uniform float u_bass;
uniform float u_treble;
uniform float u_onset;
uniform float u_tempo;
uniform float u_beat_phase;
uniform vec2 u_resolution;
out vec4 fragColor;

void main() {
    vec2 uv = gl_FragCoord.xy / u_resolution.xy;
    vec2 grid = abs(fract(uv * 20.0 + u_time * 0.1) - 0.5);
    float line = smoothstep(0.45, 0.5, max(grid.x, grid.y));
    vec3 col = vec3(0.05, 0.0, 0.1);
    col += vec3(0.8, 0.2, 1.0) * line * (0.5 + u_bass);
    col += vec3(0.2, 0.8, 1.0) * line * (0.3 + u_treble);
    float beat = sin(u_beat_phase * 3.14159) * u_onset;
    col += vec3(1.0, 0.3, 0.8) * beat * 0.3;
    fragColor = vec4(col, 1.0);
}
""",
    "plasma": """
#version 330
uniform float u_time;
uniform float u_bass;
uniform float u_treble;
uniform float u_onset;
uniform float u_tempo;
uniform float u_beat_phase;
uniform vec2 u_resolution;
out vec4 fragColor;

void main() {
    vec2 uv = gl_FragCoord.xy / u_resolution.xy;
    float t = u_time * 0.5;
    float v = sin(uv.x * 10.0 + t) + sin(uv.y * 10.0 + t * 1.3);
    v += sin((uv.x + uv.y) * 8.0 + t * 0.7) * u_bass;
    v += sin(uv.x * 15.0 - t * 2.0) * u_treble * 0.5;
    v *= 0.5;
    vec3 col = vec3(
        0.5 + 0.5 * sin(v * 3.14159 + u_time),
        0.5 + 0.5 * sin(v * 3.14159 + u_time + 2.094),
        0.5 + 0.5 * sin(v * 3.14159 + u_time + 4.188)
    );
    col *= 0.5 + u_bass * 0.5;
    fragColor = vec4(col, 1.0);
}
""",
    "spectrum_bars": """
#version 330
uniform float u_time;
uniform float u_bass;
uniform float u_treble;
uniform float u_onset;
uniform float u_tempo;
uniform float u_beat_phase;
uniform vec2 u_resolution;
out vec4 fragColor;

void main() {
    vec2 uv = gl_FragCoord.xy / u_resolution.xy;
    float bar = floor(uv.x * 32.0) / 32.0;
    float height = 0.1 + abs(sin(bar * 20.0 + u_time * 2.0)) * u_bass;
    height += abs(sin(bar * 50.0 + u_time * 5.0)) * u_treble * 0.3;
    float bar_draw = step(uv.y, height);
    vec3 col = vec3(bar + 0.2, 1.0 - bar, 0.5 + bar * 0.5) * bar_draw;
    col += vec3(0.02, 0.02, 0.05);
    fragColor = vec4(col, 1.0);
}
""",
    "particle_swirl": """
#version 330
uniform float u_time;
uniform float u_bass;
uniform float u_treble;
uniform float u_onset;
uniform float u_tempo;
uniform float u_beat_phase;
uniform vec2 u_resolution;
out vec4 fragColor;

void main() {
    vec2 uv = (gl_FragCoord.xy / u_resolution.xy) * 2.0 - 1.0;
    float r = length(uv);
    float a = atan(uv.y, uv.x);
    float swirl = sin(a * 5.0 + r * 10.0 - u_time * 2.0 + u_bass * 5.0);
    float particles = pow(max(0.0, swirl), 8.0) * (1.0 - r);
    vec3 col = vec3(0.0);
    col += vec3(0.3, 0.6, 1.0) * particles * (0.5 + u_treble);
    col += vec3(1.0, 0.4, 0.2) * particles * u_bass * 0.5;
    col += vec3(0.1, 0.0, 0.15) * (1.0 - r);
    fragColor = vec4(col, 1.0);
}
""",
}


def _check_moderngl() -> None:
    if not _HAS_MODERNGL:
        raise RuntimeError(
            "moderngl is required for shader rendering. "
            "Install with: pip install moderngl Pillow numpy"
        )


def _build_uniforms(
    features: Dict[str, Any], frame_idx: int, fps: int, n_frames: int
) -> Dict[str, float]:
    """Build uniform values from audio features for a given frame."""
    time = frame_idx / fps

    rms_env = features.get("rms_env", [])
    onset_strength = features.get("onset_strength", [])
    spec_centroid = features.get("spectral_centroid", [])
    tempo = features.get("tempo", 0.0)

    # Map RMS to bass (low freq energy proxy)
    bass = float(rms_env[frame_idx % len(rms_env)]) if rms_env else 0.0
    # Map spectral centroid to treble
    treble = 0.0
    if spec_centroid:
        sc = spec_centroid[frame_idx % len(spec_centroid)]
        treble = min(float(sc) / 8000.0, 1.0)
    # Onset strength
    onset = float(onset_strength[frame_idx % len(onset_strength)]) if onset_strength else 0.0
    # Beat phase: oscillates 0..1 at tempo
    beat_phase = 0.0
    if tempo > 0:
        beat_period = 60.0 / tempo
        beat_phase = (time % beat_period) / beat_period

    return {
        "u_time": time,
        "u_bass": bass,
        "u_treble": treble,
        "u_onset": onset,
        "u_tempo": tempo,
        "u_beat_phase": beat_phase,
    }


def render_shader_to_frames(
    preset: str,
    features: Dict[str, Any],
    output_dir: Path,
    width: int = 1280,
    height: int = 720,
    fps: int = 30,
    n_frames: int = 100,
) -> List[Path]:
    """Render a shader preset to a sequence of PNG frames.

    Args:
        preset: Shader preset name (neon_grid, plasma, spectrum_bars, particle_swirl).
        features: Audio features dict from video_features.extract_features.
        output_dir: Directory to write PNG frames.
        width: Frame width in pixels.
        height: Frame height in pixels.
        fps: Frames per second.
        n_frames: Total number of frames to render.

    Returns:
        List of paths to generated PNG files.
    """
    _check_moderngl()
    if preset not in SHADER_PRESETS:
        raise KeyError(f"Unknown shader preset: {preset}")

    output_dir.mkdir(parents=True, exist_ok=True)

    ctx = moderngl.create_standalone_context()
    prog = ctx.program(vertex_shader=_VERTEX_SHADER, fragment_shader=SHADER_PRESETS[preset])

    # Full-screen quad
    vertices = np.array([-1, -1, 1, -1, -1, 1, -1, 1, 1, -1, 1, 1], dtype="f2")
    vbo = ctx.buffer(vertices.tobytes())
    vao = ctx.vertex_array(prog, [(vbo, "2f", "in_vert")])

    fbo = ctx.framebuffer(
        color_attachments=[ctx.texture((width, height), 4)],
    )
    fbo.use()

    frame_paths: List[Path] = []
    for i in range(n_frames):
        uniforms = _build_uniforms(features, i, fps, n_frames)
        for name, value in uniforms.items():
            if name in prog:
                prog[name].value = value
        if "u_resolution" in prog:
            prog["u_resolution"].value = (width, height)

        vao.render(mode=moderngl.TRIANGLES)

        raw = fbo.read(components=4, alignment=1)
        img = Image.frombytes("RGBA", (width, height), raw)
        frame_path = output_dir / f"frame_{i:05d}.png"
        img.save(str(frame_path))
        frame_paths.append(frame_path)

    return frame_paths


def render_shader_video(
    preset: str,
    features: Dict[str, Any],
    output: Path,
    width: int = 1280,
    height: int = 720,
    fps: int = 30,
    n_frames: int = 100,
    audio: Optional[Path] = None,
    frames_dir: Optional[Path] = None,
) -> Path:
    """Render a shader preset to a video file via FFmpeg.

    Args:
        preset: Shader preset name.
        features: Audio features dict.
        output: Path for output MP4.
        width: Frame width.
        height: Frame height.
        fps: Frames per second.
        n_frames: Total frames to render.
        audio: Optional audio file to mux.
        frames_dir: Directory for intermediate PNG frames.

    Returns:
        Path to output video.
    """
    _check_moderngl()
    if preset not in SHADER_PRESETS:
        raise KeyError(f"Unknown shader preset: {preset}")

    check_ffmpeg(required=True)

    inter_dir = frames_dir or output.parent / "shader_frames"
    frame_paths = render_shader_to_frames(
        preset=preset,
        features=features,
        output_dir=inter_dir,
        width=width,
        height=height,
        fps=fps,
        n_frames=n_frames,
    )

    if not frame_paths:
        raise RuntimeError("No frames rendered")

    # Encode frames to video
    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-i", str(inter_dir / "frame_%05d.png"),
        "-c:v", "libx264", "-crf", "18",
        "-pix_fmt", "yuv420p",
    ]

    if audio:
        cmd.extend(["-i", str(audio), "-c:a", "aac", "-shortest"])
    else:
        cmd.extend(["-c:a", "none"])

    cmd.append(str(output))
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"FFmpeg failed (exit {result.returncode}): {stderr}")

    return output
