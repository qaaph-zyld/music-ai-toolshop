import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_audio_separator():
    """Mock audio_separator import and the Separator class."""
    mock_separator_class = MagicMock()

    with patch.dict(
        "sys.modules",
        {"audio_separator.separator": MagicMock(Separator=mock_separator_class)},
    ):
        # Force reimport to pick up the mock.
        for mod in list(sys.modules):
            if mod.startswith("toolshop.stem_extractor_adapter"):
                del sys.modules[mod]
        yield mock_separator_class


@pytest.fixture
def mock_missing_audio_separator():
    # Store original module if it exists.
    orig_module = sys.modules.pop("audio_separator.separator", None)
    orig_has_attr = "toolshop.stem_extractor_adapter" in sys.modules

    # Remove the adapter module to force reimport.
    if "toolshop.stem_extractor_adapter" in sys.modules:
        del sys.modules["toolshop.stem_extractor_adapter"]

    # Create a module that raises ImportError when accessed.
    import types

    error_module = types.ModuleType("audio_separator")
    error_module.separator = None
    sys.modules["audio_separator"] = error_module

    yield

    # Restore original state.
    if orig_module:
        sys.modules["audio_separator.separator"] = orig_module
    if orig_has_attr and "toolshop.stem_extractor_adapter" in sys.modules:
        del sys.modules["toolshop.stem_extractor_adapter"]


def test_check_audio_separator_missing(mock_missing_audio_separator):
    from toolshop.stem_extractor_adapter import _check_audio_separator

    with pytest.raises(RuntimeError, match="audio-separator is required"):
        _check_audio_separator()


def test_extract_stems_file_not_found():
    with patch.dict(
        "sys.modules", {"audio_separator.separator": MagicMock(Separator=MagicMock())}
    ):
        for mod in list(sys.modules):
            if mod.startswith("toolshop.stem_extractor_adapter"):
                del sys.modules[mod]

        from toolshop.stem_extractor_adapter import extract_stems

        with pytest.raises(FileNotFoundError):
            extract_stems(Path("nonexistent.wav"))


def _make_separator(outputs: list[str]) -> MagicMock:
    sep = MagicMock()
    sep.separate.return_value = outputs
    return sep


def test_extract_stems_high_quality(mock_audio_separator, tmp_path):
    from toolshop.stem_extractor_adapter import extract_stems

    # Realistic output filenames for the two passes in full-vocals-hq preset.
    pass1_outputs = [
        "song_(Instrumental)_bsroformer.wav",
        "song_(Vocals)_bsroformer.wav",
    ]
    pass2_outputs = [
        "song_(Vocals)_karaoke.wav",
        "song_(Instrumental)_karaoke.wav",
    ]

    mock_audio_separator.side_effect = [
        _make_separator(pass1_outputs),
        _make_separator(pass2_outputs),
    ]

    test_file = tmp_path / "test.wav"
    test_file.touch()
    output_dir = tmp_path / "output"

    result = extract_stems(test_file, output_dir, use_gpu=True, high_quality=True)

    assert mock_audio_separator.call_count == 2
    assert result["input_file"] == str(test_file)
    assert result["output_dir"] == str(output_dir)
    assert result["gpu_used"] is True
    assert result["quality_mode"] == "high"

    stems = result["stems"]
    assert set(stems.keys()) == {"instrumental", "main_vocals", "backing_vocals"}
    assert all(Path(stems[k]).exists() is False for k in stems)  # mocked files
    assert "bsroformer" in stems["instrumental"].lower()
    assert "karaoke" in stems["main_vocals"].lower()
    assert "karaoke" in stems["backing_vocals"].lower()


def test_extract_stems_fast_mode(mock_audio_separator, tmp_path):
    """Regression test for the fast-mode filename mapping bug.

    The old code looked for 'backing' or 'other' in UVR-BVE pass-2 outputs,
    which always returned None because UVR-BVE emits (Vocals)/(Instrumental)
    filenames. The registry now maps those to main_vocals/backing_vocals.
    """
    from toolshop.stem_extractor_adapter import extract_stems

    pass1_outputs = [
        "song_(Instrumental)_UVR-MDX-NET-Voc_FT.wav",
        "song_(Vocals)_UVR-MDX-NET-Voc_FT.wav",
    ]
    pass2_outputs = [
        "song_(Vocals)_UVR-BVE-4B_SN-44100-1.wav",
        "song_(Instrumental)_UVR-BVE-4B_SN-44100-1.wav",
    ]

    mock_audio_separator.side_effect = [
        _make_separator(pass1_outputs),
        _make_separator(pass2_outputs),
    ]

    test_file = tmp_path / "test.wav"
    test_file.touch()
    output_dir = tmp_path / "output"

    result = extract_stems(test_file, output_dir, use_gpu=False, high_quality=False)

    assert mock_audio_separator.call_count == 2
    assert result["quality_mode"] == "fast"

    stems = result["stems"]
    assert set(stems.keys()) == {"instrumental", "main_vocals", "backing_vocals"}
    assert stems["instrumental"] is not None
    assert stems["main_vocals"] is not None
    assert stems["backing_vocals"] is not None
    assert "bve" in stems["backing_vocals"].lower()


def test_extract_stems_preset_karaoke(mock_audio_separator, tmp_path):
    from toolshop.stem_extractor_adapter import extract_stems_preset

    outputs = [
        "song_(Instrumental)_UVR-MDX-NET-Voc_FT.wav",
        "song_(Vocals)_UVR-MDX-NET-Voc_FT.wav",
    ]
    mock_audio_separator.side_effect = [_make_separator(outputs)]

    test_file = tmp_path / "test.wav"
    test_file.touch()

    result = extract_stems_preset(
        test_file, preset_id="karaoke", output_dir=tmp_path / "out", use_gpu=False
    )

    assert mock_audio_separator.call_count == 1
    assert result["preset"] == "karaoke"
    assert set(result["stems"].keys()) == {"instrumental", "main_vocals"}
