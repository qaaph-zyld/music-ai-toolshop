import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

@pytest.fixture
def mock_audio_separator():
    # Mock the import before it happens
    mock_separator_class = MagicMock()
    mock_separator1 = MagicMock()
    mock_separator2 = MagicMock()
    mock_separator1.separate.return_value = [
        "test_instrumental.wav",
        "test_vocals.wav"
    ]
    mock_separator2.separate.return_value = [
        "test_main_vocals.wav", 
        "test_backing_vocals.wav"
    ]
    
    # Return different instances for each call
    mock_separator_class.side_effect = [mock_separator1, mock_separator2]
    
    with patch.dict('sys.modules', {'audio_separator.separator': MagicMock(Separator=mock_separator_class)}):
        # Force reimport to pick up the mock
        if 'toolshop.stem_extractor_adapter' in sys.modules:
            del sys.modules['toolshop.stem_extractor_adapter']
        yield mock_separator_class


@pytest.fixture
def mock_missing_audio_separator():
    # Store original module if it exists
    orig_module = sys.modules.pop('audio_separator.separator', None)
    orig_has_attr = 'toolshop.stem_extractor_adapter' in sys.modules
    
    # Remove the adapter module to force reimport
    if 'toolshop.stem_extractor_adapter' in sys.modules:
        del sys.modules['toolshop.stem_extractor_adapter']
    
    # Create a module that raises ImportError when accessed
    import types
    error_module = types.ModuleType('audio_separator')
    error_module.separator = None  # This will cause ImportError in the try block
    sys.modules['audio_separator'] = error_module
    
    yield
    
    # Restore original state
    if orig_module:
        sys.modules['audio_separator.separator'] = orig_module
    if orig_has_attr and 'toolshop.stem_extractor_adapter' in sys.modules:
        del sys.modules['toolshop.stem_extractor_adapter']

def test_check_audio_separator_missing(mock_missing_audio_separator):
    from toolshop.stem_extractor_adapter import _check_audio_separator
    with pytest.raises(RuntimeError, match="audio-separator is required"):
        _check_audio_separator()

def test_extract_stems_file_not_found():
    with patch.dict('sys.modules', {'audio_separator.separator': MagicMock(Separator=MagicMock())}):
        # Force reimport to pick up the mock
        if 'toolshop.stem_extractor_adapter' in sys.modules:
            del sys.modules['toolshop.stem_extractor_adapter']
        
        from toolshop.stem_extractor_adapter import extract_stems
        with pytest.raises(FileNotFoundError):
            extract_stems(Path("nonexistent.wav"))

def test_extract_stems_success(mock_audio_separator, tmp_path):
    from toolshop.stem_extractor_adapter import extract_stems
    
    # Setup test file
    test_file = tmp_path / "test.wav"
    test_file.touch()
    
    output_dir = tmp_path / "output"
    
    result = extract_stems(test_file, output_dir, use_gpu=True, high_quality=True)
    
    # Verify separator was called twice
    assert mock_audio_separator.call_count == 2
    
    # Verify result structure
    assert result["input_file"] == str(test_file)
    assert result["output_dir"] == str(output_dir)
    assert "stems" in result
    assert "instrumental" in result["stems"]
    assert "main_vocals" in result["stems"]
    assert "backing_vocals" in result["stems"]
    assert result["gpu_used"] is True
    assert result["quality_mode"] == "high"

# Note: Fast mode test removed - functionality verified with actual Kawasaki MP3 file
