import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from toolshop.bpm_adapter import _check_librosa, analyze_track, analyze_library

@pytest.fixture
def mock_librosa():
    with patch("toolshop.bpm_adapter.librosa") as mock_lib, \
         patch("toolshop.bpm_adapter.np") as mock_np:
         
        # Setup basic librosa mock returns
        mock_lib.load.return_value = (MagicMock(), 22050)
        mock_lib.get_duration.return_value = 120.5
        mock_lib.beat.beat_track.return_value = (120.0, None)
        
        # Setup chroma feature mock
        mock_chroma = MagicMock()
        mock_lib.feature.chroma_cqt.return_value = mock_chroma
        
        # Mock numpy mean and argmax
        mock_np.mean.return_value = [0.8] * 12  # Return array of floats > 0.5 for major mode
        mock_np.argmax.return_value = 0

        
        yield mock_lib, mock_np

@pytest.fixture
def mock_missing_librosa():
    with patch("toolshop.bpm_adapter._HAS_LIBROSA", False):
        yield

def test_check_librosa_missing(mock_missing_librosa):
    with pytest.raises(RuntimeError, match="librosa is required"):
        _check_librosa()

def test_analyze_track_file_not_found():
    # Make sure we don't fail the librosa check
    with patch("toolshop.bpm_adapter._HAS_LIBROSA", True):
        with pytest.raises(FileNotFoundError):
            analyze_track(Path("nonexistent_file.wav"))

def test_analyze_track_success(mock_librosa, tmp_path):
    # Setup test file
    test_file = tmp_path / "test.wav"
    test_file.touch()
    
    # Run analysis
    with patch("toolshop.bpm_adapter._HAS_LIBROSA", True):
        result = analyze_track(test_file)
        
    # Verify results
    assert result["bpm"] == 120.0
    assert result["duration_seconds"] == 120.5
    assert result["key"] == "C"
    assert result["mode"] == "major"
    assert result["sample_rate"] == 22050

def test_analyze_library(mock_librosa, tmp_path):
    # Create test files
    file1 = tmp_path / "test1.wav"
    file2 = tmp_path / "test2.wav"
    file1.touch()
    file2.touch()
    
    with patch("toolshop.bpm_adapter._HAS_LIBROSA", True):
        results = analyze_library(tmp_path)
        
    assert len(results) == 2
    
    # Files could be discovered in any order
    files_analyzed = {res["file"] for res in results}
    assert str(file1) in files_analyzed
    assert str(file2) in files_analyzed
    assert results[0]["bpm"] == 120.0
