"""Model registry and preset definitions for stem extraction.

Keeps model metadata, output-name semantics, and presets in one place so the
adapters can map raw filenames to canonical stem names without substring guessing.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

# Version-controlled record of what each model file should hash to. Small enough
# to be code rather than data, and it must survive a cache wipe — the whole point
# of M2 was to stop depending on a third-party release page staying reachable.
MODEL_MANIFEST_PATH = Path(__file__).resolve().parent.parent / "docs" / "model_manifest.json"


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
        # MEASURED 2026-08-30 on this machine (CPU-only, i7-4770 class):
        # 26.06 min for a 2.85 min track = **9.14x realtime**. Well past the 15
        # min/track governance threshold, so `vocals-hq` is an overnight-batch
        # preset, not an interactive one. Scale by track length, not by this number.
        cpu_min_per_track=26.1,
        vram_gb=None,
        # Weight licence UNVERIFIED (checked 2026-08-20). The BS-RoFormer
        # *architecture* (lucidrains) is MIT, and UVR's own GUI and UVR-team models
        # are MIT-with-credit — but UVR's terms explicitly do NOT extend to
        # third-party models it merely redistributes (viperx/Kim/Demucs each carry
        # their own). The viperx weight author has not clearly declared terms, so
        # this is recorded as unverified rather than asserted as MIT.
        license="unverified — see source; architecture MIT (lucidrains), weight terms undeclared",
        source="https://github.com/TRvlvr/model_repo/releases/download/all_public_uvr_models/model_bs_roformer_ep_317_sdr_12.9755.ckpt",
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
        # NOT YET MEASURED. The `full-vocals-hq` run was stopped after the
        # bs-roformer first pass so it would not hold up close-out. What is known:
        # this preset runs bs-roformer (26.06 min measured) *plus* this 870 MB
        # model, so full-vocals-hq is **>26 min/track** and almost certainly ~50.
        # That is a lower bound, not a measurement - finish it before quoting a figure.
        cpu_min_per_track=None,
        vram_gb=None,
        # CORRECTED 2026-08-20. The previous entry claimed
        # source="https://github.com/RVC-Boss/GPT-SoVITS", license="MIT".
        # GPT-SoVITS is a text-to-speech project and is not where this model comes
        # from; `audio-separator`'s own download_checks.json resolves it to the
        # TRvlvr release below, and the weights are by aufr33 + viperx. The MIT
        # claim appears to have been inherited from that wrong attribution.
        # See the bs-roformer-317 note above for why "unverified" is the honest value.
        license="unverified — see source; weights by aufr33/viperx, terms undeclared",
        source="https://github.com/TRvlvr/model_repo/releases/download/all_public_uvr_models/mel_band_roformer_karaoke_aufr33_viperx_sdr_10.1956.ckpt",
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
        # MEASURED 2026-08-30 (8 logical cores, CPU-only), CONTROLLED - warm-up
        # discarded, baseline repeated (2.0% drift), 30 s clip:
        #   jobs=0 -> 30.2 s / 29.6 s
        #   jobs=4 -> 24.6 s   = 1.22x  (the computed default)
        # ~0.82x realtime, so a 3 min track is ~2.5 min - comfortably interactive,
        # unlike the RoFormer presets at ~9x. Stem correlation 0.986-0.9995.
        # NOTE: an earlier UNCONTROLLED sweep reported 2.97x and ~1.9 min. That
        # baseline was cold-cache inflated; these are the trustworthy figures.
        cpu_min_per_track=2.5,
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
    orphans, as are per-model companion configs (RoFormer checkpoints ship a
    sidecar ``.yaml`` describing the architecture; it is part of the model, not
    stray junk).
    """
    ignored_orphans = {
        "download_checks.json",
        "mdx_model_data.json",
        "vr_model_data.json",
    }
    # Config extensions that count as a companion when they resolve to an expected
    # model's stem. The two RoFormer models use *different* naming conventions,
    # confirmed against real downloads on 2026-08-20:
    #   model_bs_roformer_ep_317_sdr_12.9755.yaml          -> same stem
    #   mel_band_roformer_karaoke_..._sdr_10.1956_config.yaml -> stem + "_config"
    companion_suffixes = {".yaml", ".yml", ".json"}
    companion_stem_affixes = ("_config",)
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
    expected_stems = {Path(name).stem for name in expected}

    def _is_companion(name: str) -> bool:
        path = Path(name)
        if path.suffix.lower() not in companion_suffixes:
            return False
        stem = path.stem
        if stem in expected_stems:
            return True
        for affix in companion_stem_affixes:
            if stem.endswith(affix) and stem[: -len(affix)] in expected_stems:
                return True
        return False

    orphans = sorted(
        name
        for name in (found_files - expected) - ignored_orphans
        if not _is_companion(name)
    )

    return {
        "present": present,
        "missing": missing,
        "orphans": orphans,
        "complete": not missing,
        "path": str(cache_root),
    }


# ---------------------------------------------------------------- model integrity
#
# Presence is not integrity. The backup verified "clean" for a month while
# collecting the wrong asset set (assessment F1b); the same trap applies here, so
# the cache is checked by hash, not by filename.


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    """Return the SHA-256 of a file, read in chunks (these are ~600-900 MB)."""
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            digest.update(block)
    return digest.hexdigest()


def build_model_manifest(cache_root: Path) -> Dict[str, Any]:
    """Hash every audio-separator model present in the cache.

    Companion configs are included too: a RoFormer checkpoint without its sidecar
    ``.yaml`` will not load, so the pair is what needs recording.
    """
    expected = {
        m.model_file: m for m in MODELS.values() if m.backend == "audio-separator"
    }
    entries: Dict[str, Any] = {}
    for name, model in sorted(expected.items()):
        path = cache_root / name
        if not path.exists():
            continue
        entries[name] = {
            "model_id": model.id,
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
            "license": model.license,
            "source": model.source,
        }
        # Both companion conventions seen in the wild (see check_model_cache).
        for companion in (
            path.with_suffix(".yaml"),
            path.with_name(path.stem + "_config.yaml"),
        ):
            if companion.exists():
                entries[companion.name] = {
                    "model_id": model.id,
                    "companion_of": name,
                    "size_bytes": companion.stat().st_size,
                    "sha256": sha256_file(companion),
                }
    return {"models": entries}


def verify_model_cache(
    cache_root: Path, manifest: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Verify cached model files against recorded hashes.

    Returns ``verified`` / ``missing`` / ``corrupt`` / ``unrecorded`` and an ``ok``
    flag. ``corrupt`` is the case that a presence-only check cannot see: a file
    that is there, is the right name, and is wrong.
    """
    if manifest is None:
        if not MODEL_MANIFEST_PATH.exists():
            return {
                "ok": False,
                "reason": f"no manifest at {MODEL_MANIFEST_PATH}",
                "verified": [],
                "missing": [],
                "corrupt": [],
                "unrecorded": [],
            }
        manifest = json.loads(MODEL_MANIFEST_PATH.read_text(encoding="utf-8"))

    recorded = manifest.get("models", {})
    verified: List[str] = []
    missing: List[str] = []
    corrupt: List[str] = []

    for name, entry in sorted(recorded.items()):
        path = cache_root / name
        if not path.exists():
            missing.append(name)
            continue
        if path.stat().st_size != entry.get("size_bytes"):
            corrupt.append(name)
            continue
        if sha256_file(path) != entry.get("sha256"):
            corrupt.append(name)
            continue
        verified.append(name)

    expected_files = {
        m.model_file for m in MODELS.values() if m.backend == "audio-separator"
    }
    unrecorded = sorted(
        n for n in expected_files if n not in recorded and (cache_root / n).exists()
    )

    return {
        "ok": not missing and not corrupt and not unrecorded,
        "reason": "ok" if not (missing or corrupt or unrecorded) else "see fields",
        "verified": verified,
        "missing": missing,
        "corrupt": corrupt,
        "unrecorded": unrecorded,
        "path": str(cache_root),
    }
