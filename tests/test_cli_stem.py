import pytest
from unittest.mock import patch, MagicMock
import sys

def test_stem_command_parsing():
    """Test that stem command arguments are parsed correctly"""
    from toolshop.cli import build_parser
    
    parser = build_parser()
    
    # Test basic stem extract command
    args = parser.parse_args(['stem', 'extract', 'test.wav'])
    assert args.command == 'stem'
    assert args.stem_command == 'extract'
    assert args.file.name == 'test.wav'
    assert args.output_dir.name == 'separated_tracks'
    assert args.cpu is False
    assert args.fast is False
    assert args.json is False

def test_stem_command_with_options():
    """Test stem command with all options"""
    from toolshop.cli import build_parser
    
    parser = build_parser()
    
    args = parser.parse_args([
        'stem', 'extract', 'test.wav',
        '--output-dir', 'output',
        '--cpu',
        '--fast',
        '--json'
    ])
    
    assert args.command == 'stem'
    assert args.stem_command == 'extract'
    assert args.file.name == 'test.wav'
    assert args.output_dir.name == 'output'
    assert args.cpu is True
    assert args.fast is True
    assert args.json is True
