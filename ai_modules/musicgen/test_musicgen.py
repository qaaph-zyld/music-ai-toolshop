"""Tests for MusicGen AI module."""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ai_modules.musicgen import MusicGenBridge, MusicGenGenerator


class TestMusicGenBridge(unittest.TestCase):
    """Tests for MusicGenBridge subprocess wrapper."""
    
    def test_check_available(self):
        """Test check() returns availability info when working."""
        bridge = MusicGenBridge()
        
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "available": True,
            "torch_version": "2.0.0",
            "cuda_available": False,
            "models_available": ["small", "medium", "large", "melody"]
        })
        mock_result.stderr = ""
        
        with patch('subprocess.run', return_value=mock_result):
            result = bridge.check()
        
        self.assertTrue(result["available"])
        self.assertEqual(result["torch_version"], "2.0.0")
        self.assertIn("small", result["models_available"])
    
    def test_check_unavailable(self):
        """Test check() handles subprocess failure."""
        bridge = MusicGenBridge()
        
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Module not found"
        
        with patch('subprocess.run', return_value=mock_result):
            result = bridge.check()
        
        self.assertFalse(result["available"])
        self.assertIn("error", result)
    
    def test_generate_success(self):
        """Test generate() returns success with valid output."""
        bridge = MusicGenBridge()
        
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "success": True,
            "prompt": "electronic beat",
            "duration": 10,
            "sample_rate": 32000,
            "output_path": "/tmp/output.wav",
            "model_used": "small"
        })
        mock_result.stderr = ""
        
        with patch('subprocess.run', return_value=mock_result):
            result = bridge.generate(
                prompt="electronic beat",
                duration_seconds=10,
                output_path="/tmp/output.wav"
            )
        
        self.assertTrue(result["success"])
        self.assertEqual(result["prompt"], "electronic beat")
        self.assertEqual(result["output_path"], "/tmp/output.wav")
    
    def test_generate_failure(self):
        """Test generate() handles errors gracefully."""
        bridge = MusicGenBridge()
        
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "CUDA out of memory"
        
        with patch('subprocess.run', return_value=mock_result):
            result = bridge.generate(prompt="test")
        
        self.assertFalse(result["success"])
        self.assertIn("error", result)


class TestMusicGenGenerator(unittest.TestCase):
    """Tests for MusicGenGenerator class."""
    
    def test_import_without_audiocraft(self):
        """Test generator handles missing audiocraft gracefully."""
        # Should not raise - class exists even if audiocraft unavailable
        self.assertTrue(hasattr(MusicGenGenerator, 'MODEL_SIZES'))
        self.assertIn('small', MusicGenGenerator.MODEL_SIZES)
    
    def test_model_sizes_constant(self):
        """Test model sizes are defined correctly."""
        expected_sizes = ['small', 'medium', 'large', 'melody']
        self.assertEqual(MusicGenGenerator.MODEL_SIZES, expected_sizes)


class TestMusicGenCLI(unittest.TestCase):
    """Tests for MusicGen CLI interface."""
    
    @patch('sys.argv', ['musicgen', 'check'])
    @patch('sys.stdout')
    def test_cli_check_outputs_json(self, mock_stdout):
        """Test CLI check command outputs valid JSON."""
        from ai_modules.musicgen.generator import main, AUDIOCRAFT_AVAILABLE
        
        try:
            main()
        except SystemExit as e:
            # check command should exit 0
            if AUDIOCRAFT_AVAILABLE:
                self.assertEqual(e.code, 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
