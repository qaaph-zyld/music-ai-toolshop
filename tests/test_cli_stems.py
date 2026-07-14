from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from toolshop.cli import build_parser
from toolshop import stems_cli


@pytest.fixture
def mock_extract():
    def side_effect(*args, **kwargs):
        output_dir = kwargs.get("output_dir", Path("out"))
        return {
            "input_file": str(kwargs.get("input_file", "test.wav")),
            "output_dir": str(output_dir),
            "preset": kwargs.get("preset_id", "karaoke"),
            "stems": {
                "instrumental": str(output_dir / "test_Instrumental.wav"),
                "main_vocals": str(output_dir / "test_Vocals.wav"),
            },
            "models_used": ["uvr-mdx-net-voc-ft"],
            "gpu_used": False,
            "output_format": kwargs.get("output_format", "flac"),
        }

    with patch.object(stems_cli.stem_extractor_adapter, "extract_stems_preset") as mock:
        mock.side_effect = side_effect
        yield mock


def test_stems_parser_single_file():
    parser = build_parser()
    args = parser.parse_args(["stems", "song.wav", "--preset", "karaoke", "--device", "cpu"])
    assert args.command == "stems"
    assert args.path == Path("song.wav")
    assert args.preset == "karaoke"
    assert args.device == "cpu"


def test_stems_parser_batch_options():
    parser = build_parser()
    args = parser.parse_args(
        ["stems", "folder", "--preset", "full-vocals", "--limit", "10", "--offset", "5"]
    )
    assert args.command == "stems"
    assert args.path == Path("folder")
    assert args.limit == 10
    assert args.offset == 5


def test_stems_single_file_json(mock_extract, tmp_path):
    parser = build_parser()
    input_file = tmp_path / "test.wav"
    input_file.touch()

    args = parser.parse_args(["stems", str(input_file), "--json"])
    assert stems_cli.run(args) == 0
    mock_extract.assert_called_once()


def test_stems_list_models(capsys):
    parser = build_parser()
    args = parser.parse_args(["stems", "dummy", "--list-models"])
    assert stems_cli.run(args) == 0
    captured = capsys.readouterr()
    assert "karaoke" in captured.out
    assert "uvr-mdx-net-voc-ft" in captured.out
