import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from toolshop.reverse_engineering_adapter import analyze_track


def test_analyze_track_file_not_found():
    """Test analyze_track when file doesn't exist"""
    with pytest.raises(FileNotFoundError):
        analyze_track(Path("nonexistent.wav"))


@patch.dict('sys.modules', {'librosa': MagicMock(), 'numpy': MagicMock()})
def test_analyze_track_basic_structure(tmp_path):
    """Test analyze_track basic structure with mocked dependencies"""
    # Mock the imports within the function
    with patch('toolshop.reverse_engineering_adapter._basic_analysis') as mock_analysis:
        mock_analysis.return_value = {
            'file': 'test.wav',
            'duration_seconds': 120.0,
            'tempo': 120.0,
            'key_signature': 'C major',
            'spectral_features': {'centroid': 2000.0},
            'structure_analysis': {'sections': 4}
        }
        
        test_file = tmp_path / "test.wav"
        test_file.touch()
        
        result = analyze_track(test_file)
        
        # Check basic structure exists
        assert "file" in result
        assert "duration_seconds" in result
        assert "tempo" in result
        assert "key_signature" in result
        assert "spectral_features" in result
        assert "structure_analysis" in result


def test_analyze_track_with_instruments(tmp_path):
    """Test analyze_track with instrument detection enabled"""
    with patch('toolshop.reverse_engineering_adapter._basic_analysis') as mock_analysis:
        mock_analysis.return_value = {
            'file': 'test.wav',
            'duration_seconds': 120.0,
            'tempo': 120.0,
            'key_signature': 'C major',
            'spectral_features': {'centroid': 2000.0},
            'structure_analysis': {'sections': 4},
            'instrument_detection': {'piano': 0.8, 'drums': 0.6}
        }
        
        test_file = tmp_path / "test.wav"
        test_file.touch()
        
        result = analyze_track(test_file, instruments=True)
        
        # Should have instrument analysis
        assert "instrument_detection" in result


def test_analyze_track_with_effects(tmp_path):
    """Test analyze_track with effects detection enabled"""
    with patch('toolshop.reverse_engineering_adapter._basic_analysis') as mock_analysis:
        mock_analysis.return_value = {
            'file': 'test.wav',
            'duration_seconds': 120.0,
            'tempo': 120.0,
            'key_signature': 'C major',
            'spectral_features': {'centroid': 2000.0},
            'structure_analysis': {'sections': 4},
            'effects_detection': {'reverb': 0.7, 'compression': 0.5}
        }
        
        test_file = tmp_path / "test.wav"
        test_file.touch()
        
        result = analyze_track(test_file, effects=True)
        
        # Should have effects analysis
        assert "effects_detection" in result


def test_analyze_track_export_json(tmp_path):
    """Test analyze_track with JSON export"""
    with patch('toolshop.reverse_engineering_adapter._basic_analysis') as mock_analysis:
        mock_analysis.return_value = {
            'file': str(tmp_path / "test.wav"),
            'duration_seconds': 120.0,
            'tempo': 120.0,
            'key_signature': 'C major',
            'spectral_features': {'centroid': 2000.0},
            'structure_analysis': {'sections': 4}
        }
        
        test_file = tmp_path / "test.wav"
        test_file.touch()
        output_json = tmp_path / "output.json"
        
        result = analyze_track(test_file, export_json=output_json)
        
        # Check that JSON file was created (note: it creates test_analysis.json by default)
        expected_file = tmp_path / "test_analysis.json"
        assert expected_file.exists()
        
        # Should still return the analysis result
        assert "file" in result
        assert result["file"] == str(test_file)
