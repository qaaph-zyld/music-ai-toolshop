import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from toolshop.voice_effects_adapter import analyze_voice, print_voice_summary


def test_analyze_voice_missing_librosa():
    """Test analyze_voice when librosa is not available"""
    with patch("toolshop.voice_effects_adapter._HAS_LIBROSA", False):
        with pytest.raises(RuntimeError):
            analyze_voice(Path("test.wav"))


def test_analyze_voice_file_not_found():
    """Test analyze_voice when file doesn't exist"""
    with patch("toolshop.voice_effects_adapter._HAS_LIBROSA", True):
        with pytest.raises(FileNotFoundError):
            analyze_voice(Path("nonexistent.wav"))


@patch("toolshop.voice_effects_adapter._HAS_LIBROSA", True)
@patch("toolshop.voice_effects_adapter.librosa")
@patch("toolshop.voice_effects_adapter.np")
def test_analyze_voice_basic_structure(mock_np, mock_librosa, tmp_path):
    """Test analyze_voice basic structure with minimal mocking"""
    # Setup minimal mocks
    mock_y = MagicMock()
    mock_sr = 22050
    mock_librosa.load.return_value = (mock_y, mock_sr)
    mock_librosa.get_duration.return_value = 120.0
    
    # Create test file
    test_file = tmp_path / "test.wav"
    test_file.touch()
    
    result = analyze_voice(test_file)
    
    # Check basic structure exists
    assert "file" in result
    assert "duration_seconds" in result
    assert "dependencies_available" in result
    
    assert result["file"] == str(test_file)
    assert result["duration_seconds"] == 120.0
    assert result["dependencies_available"]["librosa"] is True


def test_print_voice_summary_basic(capsys):
    """Test print_voice_summary basic output"""
    result = {
        "file": "test.wav",
        "duration_seconds": 120.0,
        "voice_detected": True
    }
    
    print_voice_summary(result)
    captured = capsys.readouterr()
    
    assert "VOICE EFFECTS ANALYSIS REPORT" in captured.out
    assert "test.wav" in captured.out
    assert "Voice:" in captured.out
    assert "Detected" in captured.out


def test_print_voice_summary_no_voice(capsys):
    """Test print_voice_summary when no voice detected"""
    result = {
        "file": "test.wav",
        "duration_seconds": 60.0,
        "voice_detected": False
    }
    
    print_voice_summary(result)
    captured = capsys.readouterr()
    
    assert "VOICE EFFECTS ANALYSIS REPORT" in captured.out
    assert "test.wav" in captured.out
    assert "Voice:" in captured.out
    assert "Not detected" in captured.out
