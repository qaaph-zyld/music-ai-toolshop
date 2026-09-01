import subprocess
import shutil
from typing import List, Dict, Optional, Tuple

_NOTE_TO_INDEX = {
    'C': 0, 'B#': 0,
    'C#': 1, 'Db': 1,
    'D': 2,
    'D#': 3, 'Eb': 3,
    'E': 4, 'Fb': 4,
    'F': 5, 'E#': 5,
    'F#': 6, 'Gb': 6,
    'G': 7,
    'G#': 8, 'Ab': 8,
    'A': 9,
    'A#': 10, 'Bb': 10,
    'B': 11, 'Cb': 11,
}
_INDEX_TO_NOTE = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']


def _parse_label(label: str) -> Optional[Tuple[int, str]]:
    label = label.strip()
    if not label or label.upper() == 'N':
        return None
    # common forms: C:maj, A:min, D#:maj7, F:min7, etc.
    if ':' in label:
        root, qual = label.split(':', 1)
    else:
        root, qual = label, 'maj'
    root = root.strip()
    qual = qual.lower().strip()
    if root not in _NOTE_TO_INDEX:
        return None
    idx = _NOTE_TO_INDEX[root]
    quality = 'min' if 'min' in qual else 'maj'
    return idx, quality


def parse_chordino_csv(csv_text: str) -> List[Dict]:
    chords: List[Dict] = []
    for line in csv_text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = [p.strip() for p in line.split(',')]
        if len(parts) < 3:
            continue
        try:
            start = float(parts[0])
            dur = float(parts[1])
        except ValueError:
            continue
        label = parts[2]
        parsed = _parse_label(label)
        if not parsed:
            continue
        idx, quality = parsed
        chords.append({
            'root': _INDEX_TO_NOTE[idx],
            'quality': quality,
            'confidence': 0.0,
            'start_time': start,
            'duration': dur,
        })
    return chords


def detect_chords_chordino(file_path: str, sonic_annotator_bin: Optional[str] = None) -> List[Dict]:
    """Run Chordino (via Sonic Annotator) and return chord segments.
    Requires Sonic Annotator and the Chordino Vamp plugin installed.
    """
    bin_name = sonic_annotator_bin or 'sonic-annotator'
    if not shutil.which(bin_name):
        return []
    # Use csv stdout to avoid temp files
    cmd = [bin_name, '-d', 'vamp:nnls-chroma:chordino:chords', '-w', 'csv', '--csv-stdout', file_path]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        csv_text = proc.stdout
    except subprocess.CalledProcessError:
        return []
    return parse_chordino_csv(csv_text)
