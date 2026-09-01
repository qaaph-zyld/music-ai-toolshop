import unittest
from audio_analyzer.backends.chordino import parse_chordino_csv


class TestChordinoBackend(unittest.TestCase):
    def test_parse_simple_csv(self):
        csv_text = """
        # start,duration,label
        0.000,0.500,C:maj
        0.500,0.500,A:min
        1.000,0.500,N
        1.500,0.250,D#:maj7
        """
        res = parse_chordino_csv(csv_text)
        # N should be ignored, so expect 3 chords
        self.assertEqual(len(res), 3)
        self.assertEqual(res[0]['root'], 'C')
        self.assertEqual(res[0]['quality'], 'maj')
        self.assertAlmostEqual(res[0]['start_time'], 0.0, places=3)
        self.assertAlmostEqual(res[0]['duration'], 0.5, places=3)
        self.assertEqual(res[1]['root'], 'A')
        self.assertEqual(res[1]['quality'], 'min')
        # maj7 should map to maj in our coarse quality mapping
        self.assertEqual(res[2]['root'], 'D#')
        self.assertEqual(res[2]['quality'], 'maj')


if __name__ == '__main__':
    unittest.main()
