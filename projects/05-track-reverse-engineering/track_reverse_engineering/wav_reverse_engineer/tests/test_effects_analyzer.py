"""NOT COLLECTED. The repo's `pytest.ini` sets `testpaths = tests`, so nothing
in this directory runs. Do not read a passing suite as covering this package.

This file's RT60 assertion was `assertIn('rt60_seconds', res)` - a presence check
that passes on any number - which is how an estimator returning the track's own
duration survived a 221-track corpus run. The real tests are in the repo's
`tests/test_effects_analyzer.py`. See CHANGELOG #056 / JOURNAL.md J-063.
"""

import unittest
import numpy as np

from audio_analyzer.effects_analyzer import analyze_effects, loudness_metrics


class TestEffectsAnalyzer(unittest.TestCase):
    def test_analyze_effects_basic(self):
        # Use a short impulse-like signal to ensure functions don't crash
        sr = 22050
        y = np.zeros(sr, dtype=float)
        y[0] = 1.0
        res = analyze_effects(y, sr)
        self.assertIsInstance(res, dict)
        # Core keys should exist
        self.assertIn('rt60_seconds', res)
        self.assertIn('spectral_tilt_db_per_decade', res)
        self.assertIn('thd_ratio', res)
        self.assertIn('compression_index', res)
        # Loudness keys may or may not exist depending on pyloudnorm
        # So we don't assert their presence, only that no exception occurred


if __name__ == '__main__':
    unittest.main()
