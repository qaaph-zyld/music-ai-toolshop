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
