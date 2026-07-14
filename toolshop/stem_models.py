"""Model registry and preset definitions for stem extraction.

Keeps model metadata, output-name semantics, and presets in one place so the
adapters can map raw filenames to canonical stem names without substring guessing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Literal, Optional, Tuple


@dataclass
class StemModel:
    """A single separation model."""

    id: str
    backend: Literal["audio-separator", "demucs"]
    # Filename or identifier expected by the backend.
    model_file: str
    # Canonical stem names this model can produce.
    stems: List[str]
    # Ordered mapping rules: (substring_in_filename, canonical_stem). The first
    # rule whose pattern is found (case-insensitive) in a raw output filename
    # claims that output. List from most-specific to least-specific.
    output_patterns: List[Tuple[str, str]]
    quality_tier: Literal["fast", "hq"]
    cpu_min_per_track: Optional[float] = None
    vram_gb: Optional[float] = None
    license: Optional[str] = None
    source: Optional[str] = None
    # Format the backend can write directly (audio-separator supports flac/wav).
    default_output_format: str = "wav"


@dataclass
class PresetStep:
    """One model invocation inside a preset pipeline."""

    model_id: str
    # "source" means the original input file; otherwise a stem produced by a
    # previous step.
    input: str
    # Expected canonical outputs from this step.
    outputs: List[str]
    # Optional aliases: raw model stem name -> canonical name declared in
    # `outputs` (e.g. {"vocals": "main_vocals"}).
    aliases: Dict[str, str] = field(default_factory=dict)


@dataclass
class Preset:
    """A named separation recipe."""

    id: str
    description: str
    steps: List[PresetStep]
    output_format: str = "flac"
    device: Literal["cpu", "gpu"] = "cpu"


MODELS: Dict[str, StemModel] = {
    "uvr-mdx-net-voc-ft": StemModel(
        id="uvr-mdx-net-voc-ft",
        backend="audio-separator",
        model_file="UVR-MDX-NET-Voc_FT.onnx",
        stems=["instrumental", "vocals"],
        output_patterns=[
            ("Instrumental", "instrumental"),
            ("Vocals", "vocals"),
        ],
        quality_tier="fast",
        cpu_min_per_track=None,
        vram_gb=None,
        license="UVR",
        source="https://github.com/Anjok07/ultimatevocalremovergui",
    ),
    "bs-roformer-317": StemModel(
        id="bs-roformer-317",
        backend="audio-separator",
        model_file="model_bs_roformer_ep_317_sdr_12.9755.ckpt",
        stems=["instrumental", "main_vocals"],
        output_patterns=[
            ("Instrumental", "instrumental"),
            ("Vocals", "main_vocals"),
        ],
        quality_tier="hq",
        cpu_min_per_track=None,
        vram_gb=None,
        license="MIT/BSD",
        source="https://github.com/TRvlvr/model_repo",
    ),
    "mel-band-roformer-karaoke": StemModel(
        id="mel-band-roformer-karaoke",
        backend="audio-separator",
        model_file="mel_band_roformer_karaoke_aufr33_viperx_sdr_10.1956.ckpt",
        stems=["main_vocals", "backing_vocals"],
        output_patterns=[
            # Used as a second pass on a vocal track: the "Instrumental" output
            # is the backing layer, the "Vocals" output is the lead vocal.
            ("Instrumental", "backing_vocals"),
            ("Vocals", "main_vocals"),
        ],
        quality_tier="hq",
        cpu_min_per_track=None,
        vram_gb=None,
        license="MIT",
        source="https://github.com/RVC-Boss/GPT-SoVITS",
    ),
    "uvr-bve-4b": StemModel(
        id="uvr-bve-4b",
        backend="audio-separator",
        model_file="UVR-BVE-4B_SN-44100-1.pth",
        stems=["main_vocals", "backing_vocals"],
        output_patterns=[
            # UVR-BVE emits "Instrumental" and "Vocals" filenames even on a
            # vocal input. In this pass "Instrumental" is the backing layer and
            # "Vocals" is the lead vocal.
            ("Instrumental", "backing_vocals"),
            ("Vocals", "main_vocals"),
        ],
        quality_tier="fast",
        cpu_min_per_track=None,
        vram_gb=None,
        license="UVR",
        source="https://github.com/Anjok07/ultimatevocalremovergui",
    ),
    "htdemucs": StemModel(
        id="htdemucs",
        backend="demucs",
        model_file="htdemucs",
        stems=["drums", "bass", "other", "vocals"],
        output_patterns=[
            ("drums", "drums"),
            ("bass", "bass"),
            ("other", "other"),
            ("vocals", "vocals"),
        ],
        quality_tier="hq",
        cpu_min_per_track=None,
        vram_gb=None,
        license="MIT",
        source="https://github.com/facebookresearch/demucs",
    ),
    "htdemucs_6s": StemModel(
        id="htdemucs_6s",
        backend="demucs",
        model_file="htdemucs_6s",
        stems=["drums", "bass", "other", "vocals", "guitar", "piano"],
        output_patterns=[
            ("drums", "drums"),
            ("bass", "bass"),
            ("other", "other"),
            ("vocals", "vocals"),
            ("guitar", "guitar"),
            ("piano", "piano"),
        ],
        quality_tier="hq",
        cpu_min_per_track=None,
        vram_gb=None,
        license="MIT",
        source="https://github.com/facebookresearch/demucs",
    ),
}


PRESETS: Dict[str, Preset] = {
    "karaoke": Preset(
        id="karaoke",
        description="Fast 2-stem: instrumental + main vocals (MDX-Net).",
        steps=[
            PresetStep(
                model_id="uvr-mdx-net-voc-ft",
                input="source",
                outputs=["instrumental", "main_vocals"],
                aliases={"vocals": "main_vocals"},
            ),
        ],
    ),
    "vocals-hq": Preset(
        id="vocals-hq",
        description="High-quality 2-stem: instrumental + main vocals (BS-Roformer).",
        steps=[
            PresetStep(
                model_id="bs-roformer-317",
                input="source",
                outputs=["instrumental", "main_vocals"],
            ),
        ],
    ),
    "full-vocals": Preset(
        id="full-vocals",
        description="2-pass vocals: instrumental + main vocals + backing vocals (fast).",
        steps=[
            PresetStep(
                model_id="uvr-mdx-net-voc-ft",
                input="source",
                outputs=["instrumental", "vocals"],
            ),
            PresetStep(
                model_id="uvr-bve-4b",
                input="vocals",
                outputs=["main_vocals", "backing_vocals"],
            ),
        ],
    ),
    "full-vocals-hq": Preset(
        id="full-vocals-hq",
        description="2-pass vocals HQ: instrumental + main vocals + backing vocals (Roformer).",
        steps=[
            PresetStep(
                model_id="bs-roformer-317",
                input="source",
                outputs=["instrumental", "main_vocals"],
            ),
            PresetStep(
                model_id="mel-band-roformer-karaoke",
                input="main_vocals",
                outputs=["main_vocals", "backing_vocals"],
            ),
        ],
    ),
    "4stem": Preset(
        id="4stem",
        description="Demucs 4-stem: drums, bass, other, vocals.",
        steps=[
            PresetStep(
                model_id="htdemucs",
                input="source",
                outputs=["drums", "bass", "other", "vocals"],
            ),
        ],
    ),
    "6stem": Preset(
        id="6stem",
        description="Demucs 6-stem: drums, bass, other, vocals, guitar, piano.",
        steps=[
            PresetStep(
                model_id="htdemucs_6s",
                input="source",
                outputs=["drums", "bass", "other", "vocals", "guitar", "piano"],
            ),
        ],
    ),
}


def get_model(model_id: str) -> StemModel:
    """Return a model by id or raise KeyError."""
    try:
        return MODELS[model_id]
    except KeyError as exc:
        raise KeyError(f"Unknown stem model: {model_id}") from exc


def get_preset(preset_id: str) -> Preset:
    """Return a preset by id or raise KeyError."""
    try:
        return PRESETS[preset_id]
    except KeyError as exc:
        raise KeyError(f"Unknown preset: {preset_id}") from exc


def list_presets() -> List[str]:
    """Return sorted preset ids."""
    return sorted(PRESETS.keys())


def list_models() -> List[str]:
    """Return sorted model ids."""
    return sorted(MODELS.keys())


def resolve_outputs(outputs: List[str], model: StemModel) -> Dict[str, str]:
    """Map raw backend output filenames to canonical stem names.

    Rules are applied in order; the first matching rule claims an output.
    Returns only the stems that were matched.
    """
    resolved: Dict[str, str] = {}
    used: set = set()
    for pattern, stem in model.output_patterns:
        for raw in outputs:
            if raw in used:
                continue
            if pattern.lower() in Path(raw).name.lower():
                resolved[stem] = raw
                used.add(raw)
                break
    return resolved


def expected_model_files() -> List[str]:
    """Return all model filenames required by the registry."""
    return [model.model_file for model in MODELS.values()]


def get_model_by_file(filename: str) -> StemModel:
    """Return the model that owns the given model filename."""
    for model in MODELS.values():
        if model.model_file == filename:
            return model
    raise KeyError(f"Unknown model file: {filename}")


def check_model_cache(cache_root: Path) -> Dict[str, Any]:
    """Compare the model cache against the registry.

    Returns a dict with:
        - present: list of expected files found.
        - missing: list of expected files not found.
        - orphans: list of files in cache not referenced by the registry.
        - complete: True if no expected files are missing.
        - path: cache root path.

    Demucs backend models are excluded because Demucs downloads them on first
    run into its own cache. Known audio-separator metadata files are ignored as
    orphans.
    """
    ignored_orphans = {
        "download_checks.json",
        "mdx_model_data.json",
        "vr_model_data.json",
    }
    expected = {
        m.model_file for m in MODELS.values() if m.backend == "audio-separator"
    }
    present: List[str] = []
    missing: List[str] = []

    if not cache_root.exists():
        return {
            "present": present,
            "missing": sorted(expected),
            "orphans": [],
            "complete": False,
            "path": str(cache_root),
        }

    found_files = {p.name for p in cache_root.iterdir() if p.is_file()}
    for name in sorted(expected):
        if name in found_files:
            present.append(name)
        else:
            missing.append(name)
    orphans = sorted((found_files - expected) - ignored_orphans)

    return {
        "present": present,
        "missing": missing,
        "orphans": orphans,
        "complete": not missing,
        "path": str(cache_root),
    }
