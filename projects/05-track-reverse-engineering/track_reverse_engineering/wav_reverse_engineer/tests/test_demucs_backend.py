import unittest
from audio_analyzer.backends.demucs_backend import separate_demucs


class TestDemucsBackend(unittest.TestCase):
    def test_missing_dep_returns_empty(self):
        # Should not raise and should return empty dict when Demucs is not installed
        res = separate_demucs('nonexistent.wav')
        self.assertIsInstance(res, dict)
        self.assertEqual(res.get('sample_rate', None), None)


if __name__ == '__main__':
    unittest.main()
