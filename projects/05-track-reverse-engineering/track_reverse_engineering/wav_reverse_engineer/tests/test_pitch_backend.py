import unittest
import numpy as np
from audio_analyzer.backends.pitch_torchcrepe import track_f0_torchcrepe


class TestPitchBackend(unittest.TestCase):
    def test_torchcrepe_missing_returns_empty(self):
        # Should not raise; returns empty dict if torchcrepe not installed
        audio = np.zeros(16000, dtype=float)
        res = track_f0_torchcrepe(audio, 22050)
        self.assertIsInstance(res, dict)
        # likely empty when dependency missing
        # If installed, it will contain keys


if __name__ == '__main__':
    unittest.main()
