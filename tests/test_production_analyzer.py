"""Tests for Production Analyzer AI module."""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import numpy as np

# Add parent to path
# (D6, #051) No sys.path hack needed - the module now lives in the toolshop package.

from toolshop.production_analyzer import (
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
        from toolshop.production_analyzer.classifier import FeatureVector
        
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
        from toolshop.production_analyzer.classifier import SKLEARN_AVAILABLE
        
        # Just verify the flag exists - actual functionality depends on sklearn
        self.assertIsInstance(SKLEARN_AVAILABLE, bool)
    
    def test_module_imports_cleanly(self):
        """Test entire module imports without errors."""
        # Re-import to verify no import-time errors
        from toolshop.production_analyzer import BatchAnalyzer, ChainClassifier
        
        self.assertTrue(callable(BatchAnalyzer))
        self.assertTrue(callable(ChainClassifier))


try:
    import librosa as _librosa
    import soundfile as _sf
    _HAS_AUDIO = True
except ImportError:  # pragma: no cover - environment without the audio deps
    _HAS_AUDIO = False


@unittest.skipUnless(_HAS_AUDIO, "requires librosa + soundfile")
class TestAnalyzeSingleFile(unittest.TestCase):
    """`_analyze_single_file` against a real WAV.

    Every other test in this module works on dataclasses and mocks, so the
    feature-extraction path was never executed. That is why a typo in it -
    ``np.mean(flatness)`` where ``np.mean(flatness_data)`` was meant, an
    UnboundLocalError on every call - survived adoption into `toolshop/` in
    #051: the broad ``except Exception`` turned it into a silent ``None`` and
    `analyze_directory` just returned an empty list for every input.
    """

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="toolshop_prodanalyzer_"))
        self.addCleanup(shutil.rmtree, self._tmp, True)
        # Own database, so the test never writes to the shared data directory.
        self.analyzer = BatchAnalyzer(db_path=str(self._tmp / "test.db"))

    def _write_wav(self, name="test_master.wav", seconds=0.5, sr=22050):
        """A short, spectrally non-degenerate signal: two tones plus a little noise."""
        t = np.linspace(0, seconds, int(sr * seconds), endpoint=False)
        y = 0.3 * np.sin(2 * np.pi * 220 * t) + 0.1 * np.sin(2 * np.pi * 3500 * t)
        y += 0.01 * np.random.default_rng(0).standard_normal(t.shape)
        path = self._tmp / name
        _sf.write(str(path), y.astype(np.float32), sr)
        return path

    def test_returns_fingerprint_with_finite_flatness(self):
        fp = self.analyzer._analyze_single_file(str(self._write_wav()))

        self.assertIsNotNone(
            fp, "feature extraction raised and the try/except swallowed it"
        )
        self.assertIsInstance(fp, AudioFingerprint)
        self.assertTrue(np.isfinite(fp.flatness))
        # Spectral flatness is a geometric/arithmetic mean ratio: (0, 1].
        self.assertGreater(fp.flatness, 0.0)
        self.assertLessEqual(fp.flatness, 1.0)

    def test_every_feature_is_finite(self):
        """Guards the whole family, not only the one variable that was wrong."""
        fp = self.analyzer._analyze_single_file(str(self._write_wav()))
        self.assertIsNotNone(fp)

        for field in (
            "centroid", "rolloff", "flux", "flatness", "crest_factor",
            "rms_db", "peak_db", "lufs_estimate", "zcr", "bandwidth",
            "duration_sec",
        ):
            with self.subTest(field=field):
                value = getattr(fp, field)
                self.assertIsInstance(value, float)
                self.assertTrue(np.isfinite(value), f"{field} is not finite: {value}")

        self.assertEqual(fp.sample_rate, 22050)
        self.assertAlmostEqual(fp.duration_sec, 0.5, places=2)
        self.assertEqual(fp.variant_type, "master")

    def test_analyze_directory_yields_a_fingerprint(self):
        """The user-visible symptom of the bug: zero fingerprints for every input."""
        self._write_wav("song_mixdown.wav")

        fingerprints = self.analyzer.analyze_directory(str(self._tmp))

        self.assertEqual(len(fingerprints), 1)
        self.assertEqual(fingerprints[0].variant_type, "mix")
        self.assertTrue(np.isfinite(fingerprints[0].flatness))


if __name__ == '__main__':
    unittest.main(verbosity=2)
