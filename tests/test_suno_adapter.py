import pytest
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock
import json

from toolshop.suno_adapter import sync_liked, list_library, export_text

def test_sync_liked_placeholder():
    """Test that sync_liked raises RuntimeError with proper message"""
    with pytest.raises(RuntimeError, match="Suno sync has been decoupled"):
        sync_liked(Path("output"))

def test_list_library_no_directory(capsys):
    """Test list_library when directory doesn't exist"""
    list_library(Path("nonexistent"))
    captured = capsys.readouterr()
    assert "No Suno library found at nonexistent" in captured.out

def test_list_library_empty_directory(tmp_path, capsys):
    """Test list_library when directory exists but has no metadata files"""
    list_library(tmp_path)
    captured = capsys.readouterr()
    assert f"No metadata JSON files found under {tmp_path}" in captured.out

def test_list_library_with_metadata(tmp_path, capsys):
    """Test list_library with valid metadata files"""
    # Create test metadata files
    metadata1 = {
        "title": "Test Song 1",
        "id": "clip123",
        "tags": ["pop", "electronic"]
    }
    metadata2 = {
        "title": "Test Song 2", 
        "clip_id": "clip456"
    }
    
    # Create directory structure
    date_dir1 = tmp_path / "2024-01-01"
    date_dir1.mkdir()
    date_dir2 = tmp_path / "2024-01-02"
    date_dir2.mkdir()
    
    # Write metadata files
    (date_dir1 / "clip123_metadata.json").write_text(json.dumps(metadata1))
    (date_dir2 / "clip456_metadata.json").write_text(json.dumps(metadata2))
    
    list_library(tmp_path)
    captured = capsys.readouterr()
    
    lines = captured.out.strip().split('\n')
    assert len(lines) == 2
    assert "clip123" in lines[0]
    assert "2024-01-01" in lines[0]
    assert "Test Song 1" in lines[0]
    assert "clip456" in lines[1]
    assert "2024-01-02" in lines[1]
    assert "Test Song 2" in lines[1]

def test_list_library_with_invalid_metadata(tmp_path, capsys):
    """Test list_library handles invalid JSON gracefully"""
    # Create invalid JSON file
    invalid_file = tmp_path / "invalid_metadata.json"
    invalid_file.write_text("{ invalid json")
    
    # Create valid file
    valid_metadata = {"title": "Valid Song", "id": "valid123"}
    date_dir = tmp_path / "2024-01-01"
    date_dir.mkdir()
    (date_dir / "valid123_metadata.json").write_text(json.dumps(valid_metadata))
    
    list_library(tmp_path)
    captured = capsys.readouterr()
    
    assert "valid123" in captured.out
    assert "Valid Song" in captured.out

def test_list_library_missing_fields(tmp_path, capsys):
    """Test list_library handles missing fields gracefully"""
    metadata = {"some_field": "value"}  # Missing title and id
    
    date_dir = tmp_path / "2024-01-01"
    date_dir.mkdir()
    (date_dir / "unknown_metadata.json").write_text(json.dumps(metadata))
    
    list_library(tmp_path)
    captured = capsys.readouterr()
    
    lines = captured.out.strip().split('\n')
    assert "unknown" in lines[0]  # Uses filename as id
    assert "2024-01-01" in lines[0]
    assert "Untitled" in lines[0]  # Default title

def test_export_text_no_directory(tmp_path, capsys):
    """Test export_text when directory doesn't exist"""
    export_text(tmp_path, Path("output.json"), Path("output.txt"))
    
    captured = capsys.readouterr()
    assert "Exported 0 liked tracks to" in captured.out
    assert "Plain-text export written to" in captured.out

def test_export_text_with_files(tmp_path, capsys):
    """Test export_text with actual metadata files"""
    # Create test structure
    date_dir = tmp_path / "2024-01-01"
    date_dir.mkdir()
    
    # Create metadata file with liked track
    metadata = {
        "title": "Test Song",
        "id": "test123",
        "handle": "testuser",
        "is_liked": True,
        "metadata": {
            "prompt": "Test lyrics content",
            "tags": "pop, electronic"
        }
    }
    (date_dir / "test123_metadata.json").write_text(json.dumps(metadata))
    
    # Create non-liked track (should be ignored)
    metadata2 = {
        "title": "Unliked Song",
        "id": "test456", 
        "is_liked": False
    }
    (date_dir / "test456_metadata.json").write_text(json.dumps(metadata2))
    
    output_json = tmp_path / "export.json"
    output_txt = tmp_path / "export.txt"
    
    export_text(tmp_path, output_json, output_txt)
    
    captured = capsys.readouterr()
    assert "Exported 1 liked tracks to" in captured.out
    
    # Check JSON export structure
    assert output_json.exists()
    json_data = json.loads(output_json.read_text())
    assert json_data["total_liked_songs"] == 1
    assert len(json_data["songs"]) == 1
    
    song = json_data["songs"][0]
    assert song["title"] == "Test Song"
    assert song["id"] == "test123"
    assert song["lyrics"] == "Test lyrics content"
    assert song["description"] == "pop, electronic"
    
    # Check text export
    assert output_txt.exists()
    txt_content = output_txt.read_text()
    assert "# testuser - Test Song" in txt_content
    assert "[DESCRIPTION]" in txt_content
    assert "pop, electronic" in txt_content
    assert "[LYRICS]" in txt_content
    assert "Test lyrics content" in txt_content
