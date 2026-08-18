"""Tests for Production Analyzer AI module."""
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import numpy as np

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ai_modules.production_analyzer import (
    BatchAnalyzer, 
    ChainClassifier, 
    ProcessingChain,
    AudioFingerprint
)


class TestChainClassifier(unittest.TestCase):
    """Tests for ChainClassifier ML component."""
    
    def test_instantiation(self):
        """Test classifier can be instantiated."""
        classifier = ChainClassifier()
        self.assertIsNotNone(classifier)
    
    def test_processing_chain_dataclass(self):
        """Test ProcessingChain data structure."""
        chain = ProcessingChain(
            chain_id="test_001",
            name="Bright Pop",
            description="A bright pop mix chain",
            eq_profile="bright",
            compression_style="transparent",
            spatial_processing="wide",
            loudness_target="-14 LUFS",
            confidence=0.85,
            example_tracks=["track1.wav", "track2.wav"]
        )
        
        self.assertEqual(chain.chain_id, "test_001")
        self.assertEqual(chain.name, "Bright Pop")
        self.assertEqual(chain.confidence, 0.85)
        self.assertEqual(len(chain.example_tracks), 2)


class TestBatchAnalyzer(unittest.TestCase):
    """Tests for BatchAnalyzer component."""
    
    def test_instantiation(self):
        """Test analyzer can be instantiated."""
        analyzer = BatchAnalyzer()
        self.assertIsNotNone(analyzer)
    
    def test_audio_fingerprint_structure(self):
        """Test AudioFingerprint data structure exists."""
        # Create a mock fingerprint with actual dataclass fields
        fingerprint = AudioFingerprint(
            file_path="test.wav",
            track_name="Test Track",
            variant_type="master",
            centroid=2000.0,
            rolloff=8000.0,
            flux=0.1,
            flatness=0.5,
            crest_factor=10.0,
            rms_db=-20.0,
            peak_db=-1.0,
            lufs_estimate=-14.0,
            zcr=0.1,
            bandwidth=4000.0,
            sample_rate=48000,
            duration_sec=30.0,
            parent_id=None
        )
        
        self.assertEqual(fingerprint.file_path, "test.wav")
        self.assertEqual(fingerprint.track_name, "Test Track")
        self.assertEqual(fingerprint.duration_sec, 30.0)


class TestFeatureVector(unittest.TestCase):
    """Tests for feature vector operations."""
    
    def test_feature_vector_creation(self):
        """Test FeatureVector dataclass from classifier."""
        from ai_modules.production_analyzer.classifier import FeatureVector
        
        vector = FeatureVector(
            centroid_norm=0.5,
            rolloff_norm=0.7,
            flatness=0.3,
            crest_factor_norm=0.6,
            rms_db_norm=0.4,
            lufs_db_norm=0.8,
            zcr=0.1,
            bandwidth_norm=0.6
        )
        
        self.assertEqual(vector.centroid_norm, 0.5)
        self.assertEqual(vector.lufs_db_norm, 0.8)


class TestGracefulDegradation(unittest.TestCase):
    """Tests for graceful handling of missing dependencies."""
    
    def test_classifier_without_sklearn(self):
        """Test classifier works (at least instantiates) without sklearn."""
        # Import should work even if sklearn not available
        from ai_modules.production_analyzer.classifier import SKLEARN_AVAILABLE
        
        # Just verify the flag exists - actual functionality depends on sklearn
        self.assertIsInstance(SKLEARN_AVAILABLE, bool)
    
    def test_module_imports_cleanly(self):
        """Test entire module imports without errors."""
        # Re-import to verify no import-time errors
        from ai_modules.production_analyzer import BatchAnalyzer, ChainClassifier
        
        self.assertTrue(callable(BatchAnalyzer))
        self.assertTrue(callable(ChainClassifier))


if __name__ == '__main__':
    unittest.main(verbosity=2)
