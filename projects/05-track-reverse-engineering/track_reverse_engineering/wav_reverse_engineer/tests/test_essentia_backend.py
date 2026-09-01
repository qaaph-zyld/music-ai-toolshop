import unittest
import numpy as np

from audio_analyzer.backends.essentia_metrics import compute_essentia_metrics


class TestEssentiaBackend(unittest.TestCase):
    def test_graceful_missing(self):
        # Should return a dict regardless of Essentia availability
        y = np.zeros(22050, dtype=float)
        res = compute_essentia_metrics(y, 22050)
        self.assertIsInstance(res, dict)
        # Keys may be present if Essentia is installed; otherwise empty dict


if __name__ == '__main__':
    unittest.main()
