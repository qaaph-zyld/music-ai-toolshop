from pathlib import Path

import pytest

from toolshop import stem_models


@pytest.mark.parametrize(
    "model_id, raw_outputs, expected",
    [
        (
            "uvr-mdx-net-voc-ft",
            ["song_(Instrumental)_UVR-MDX-NET-Voc_FT.wav", "song_(Vocals)_UVR-MDX-NET-Voc_FT.wav"],
            {"instrumental": "song_(Instrumental)_UVR-MDX-NET-Voc_FT.wav", "vocals": "song_(Vocals)_UVR-MDX-NET-Voc_FT.wav"},
        ),
        (
            "uvr-bve-4b",
            ["song_(Vocals)_UVR-BVE-4B_SN-44100-1.wav", "song_(Instrumental)_UVR-BVE-4B_SN-44100-1.wav"],
            {"main_vocals": "song_(Vocals)_UVR-BVE-4B_SN-44100-1.wav", "backing_vocals": "song_(Instrumental)_UVR-BVE-4B_SN-44100-1.wav"},
        ),
    ],
)
def test_resolve_outputs(model_id, raw_outputs, expected):
    model = stem_models.get_model(model_id)
    resolved = stem_models.resolve_outputs(raw_outputs, model)
    assert resolved == expected


def test_resolve_outputs_prioritizes_specific_patterns():
    # "test_backing_vocals.wav" contains both "vocals" and "backing_vocals";
    # the backing pattern should win if listed first.
    model = stem_models.StemModel(
        id="test",
        backend="audio-separator",
        model_file="test.pth",
        stems=["main_vocals", "backing_vocals"],
        output_patterns=[
            ("backing", "backing_vocals"),
            ("vocals", "main_vocals"),
        ],
        quality_tier="fast",
    )
    resolved = stem_models.resolve_outputs(
        ["test_main_vocals.wav", "test_backing_vocals.wav"], model
    )
    assert resolved["main_vocals"] == "test_main_vocals.wav"
    assert resolved["backing_vocals"] == "test_backing_vocals.wav"


def test_get_model_unknown():
    with pytest.raises(KeyError, match="Unknown stem model"):
        stem_models.get_model("does-not-exist")


def test_get_preset_unknown():
    with pytest.raises(KeyError, match="Unknown preset"):
        stem_models.get_preset("does-not-exist")


def test_full_vocals_preset_has_two_steps():
    preset = stem_models.get_preset("full-vocals")
    assert len(preset.steps) == 2
    assert preset.steps[0].model_id == "uvr-mdx-net-voc-ft"
    assert preset.steps[1].model_id == "uvr-bve-4b"
    assert preset.steps[1].input == "vocals"


def test_resolve_outputs_returns_absolute_paths_unchanged():
    raw = [str(Path("/tmp/song_(Instrumental)_UVR-MDX-NET-Voc_FT.wav"))]
    model = stem_models.get_model("uvr-mdx-net-voc-ft")
    resolved = stem_models.resolve_outputs(raw, model)
    assert resolved["instrumental"] == str(Path("/tmp/song_(Instrumental)_UVR-MDX-NET-Voc_FT.wav"))


def test_expected_model_files_contains_registry_models():
    files = stem_models.expected_model_files()
    assert "UVR-MDX-NET-Voc_FT.onnx" in files
    assert "htdemucs" in files


def test_check_model_cache_reports_missing(tmp_path):
    status = stem_models.check_model_cache(tmp_path)
    assert not status["complete"]
    assert "UVR-MDX-NET-Voc_FT.onnx" in status["missing"]


def test_check_model_cache_reports_present_and_orphans(tmp_path):
    present_name = "UVR-MDX-NET-Voc_FT.onnx"
    (tmp_path / present_name).touch()
    (tmp_path / "orphan.pth").touch()

    status = stem_models.check_model_cache(tmp_path)
    assert present_name in status["present"]
    assert "orphan.pth" in status["orphans"]
    assert present_name not in status["missing"]


def test_check_model_cache_complete(tmp_path):
    for name in stem_models.expected_model_files():
        if stem_models.get_model_by_file(name).backend == "demucs":
            continue
        (tmp_path / name).touch()
    status = stem_models.check_model_cache(tmp_path)
    assert status["complete"]
    assert not status["missing"]


# ------------------------------------------------------------ M2: cache integrity
#
# Presence is not integrity. The backup verified "clean" for a month while
# collecting the wrong asset set (assessment F1b); these guard the same trap here.

import json as _json

from toolshop import stem_models as _sm


def _fake_cache(tmp_path, *, with_yaml=True):
    cache = tmp_path / "models"
    cache.mkdir()
    for m in _sm.MODELS.values():
        if m.backend != "audio-separator":
            continue
        (cache / m.model_file).write_bytes(m.model_file.encode() * 8)
    if with_yaml:
        # Both conventions seen against real downloads on 2026-08-20: one model's
        # sidecar shares its stem, the other appends "_config".
        (cache / "model_bs_roformer_ep_317_sdr_12.9755.yaml").write_text("cfg", encoding="utf-8")
        (cache / "mel_band_roformer_karaoke_aufr33_viperx_sdr_10.1956_config.yaml").write_text(
            "cfg", encoding="utf-8"
        )
    return cache


def test_companion_yaml_is_not_an_orphan(tmp_path):
    """RoFormer checkpoints ship a sidecar .yaml — part of the model, not junk."""
    cache = _fake_cache(tmp_path)
    status = _sm.check_model_cache(cache)
    assert status["complete"] is True
    assert status["orphans"] == [], f"companion config reported as orphan: {status['orphans']}"


def test_unrelated_file_is_still_an_orphan(tmp_path):
    cache = _fake_cache(tmp_path)
    (cache / "some_random_thing.bin").write_bytes(b"x")
    (cache / "not_a_companion.yaml").write_text("y", encoding="utf-8")
    orphans = _sm.check_model_cache(cache)["orphans"]
    assert "some_random_thing.bin" in orphans
    assert "not_a_companion.yaml" in orphans, "a .yaml with no matching model must still be an orphan"


def test_build_manifest_records_hashes_and_licences(tmp_path):
    cache = _fake_cache(tmp_path)
    manifest = _sm.build_model_manifest(cache)
    models = manifest["models"]
    assert "model_bs_roformer_ep_317_sdr_12.9755.ckpt" in models
    entry = models["model_bs_roformer_ep_317_sdr_12.9755.ckpt"]
    assert len(entry["sha256"]) == 64
    assert entry["size_bytes"] > 0
    assert entry["license"] and entry["source"]
    # Companions are recorded alongside their model, not silently dropped -
    # and both naming conventions are covered.
    assert models["model_bs_roformer_ep_317_sdr_12.9755.yaml"]["companion_of"] == (
        "model_bs_roformer_ep_317_sdr_12.9755.ckpt"
    )
    assert models["mel_band_roformer_karaoke_aufr33_viperx_sdr_10.1956_config.yaml"][
        "companion_of"
    ] == "mel_band_roformer_karaoke_aufr33_viperx_sdr_10.1956.ckpt"


def test_verify_passes_on_an_intact_cache(tmp_path):
    cache = _fake_cache(tmp_path)
    result = _sm.verify_model_cache(cache, manifest=_sm.build_model_manifest(cache))
    assert result["ok"] is True
    assert result["corrupt"] == [] and result["missing"] == []


def test_verify_detects_a_corrupt_file_that_presence_would_miss(tmp_path):
    """The case a filename check cannot see: right name, right place, wrong bytes."""
    cache = _fake_cache(tmp_path)
    manifest = _sm.build_model_manifest(cache)
    target = cache / "model_bs_roformer_ep_317_sdr_12.9755.ckpt"
    target.write_bytes(b"corrupted-but-present" * 4)

    # A presence-only check is still happy...
    assert _sm.check_model_cache(cache)["complete"] is True
    # ...the hash check is not.
    result = _sm.verify_model_cache(cache, manifest=manifest)
    assert result["ok"] is False
    assert "model_bs_roformer_ep_317_sdr_12.9755.ckpt" in result["corrupt"]


def test_verify_reports_missing_file(tmp_path):
    cache = _fake_cache(tmp_path)
    manifest = _sm.build_model_manifest(cache)
    (cache / "model_bs_roformer_ep_317_sdr_12.9755.ckpt").unlink()
    result = _sm.verify_model_cache(cache, manifest=manifest)
    assert result["ok"] is False
    assert "model_bs_roformer_ep_317_sdr_12.9755.ckpt" in result["missing"]


def test_verify_without_a_manifest_is_not_silently_ok(tmp_path, monkeypatch):
    monkeypatch.setattr(_sm, "MODEL_MANIFEST_PATH", tmp_path / "nope.json")
    result = _sm.verify_model_cache(_fake_cache(tmp_path))
    assert result["ok"] is False
    assert "no manifest" in result["reason"]
