"""Transcribe an arbitrary window of the v2 (other) bed -> cleaned Dm MIDI.

Thin wrapper around ``ogcm_bed_spike.transcribe_region`` +
``bed_lanes.cleanup`` for ad-hoc segment picks (GATE S3: user picked the
54-67 s riff on the full instrumental, which no existing region MIDI covers).

Usage:
    python scripts/ogcm_transcribe_segment.py 54.0 67.0 \
        [--name region_54_67] [--root D --mode minor]
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
logging.getLogger("root").setLevel(logging.ERROR)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.ogcm_bed_spike import find_bed, transcribe_region  # noqa: E402
from toolshop.flip import bed_lanes, sample_voices as sv  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
STEMS = REPO / "Stemmeca_alatkka" / "stems"
MIDI_DIR = STEMS / "flip_bed_lanes" / "midi"
FELT_BPM = 89.1

_ROOT_PC = {"C": 0, "C#": 1, "DB": 1, "D": 2, "D#": 3, "EB": 3, "E": 4,
            "F": 5, "F#": 6, "GB": 6, "G": 7, "G#": 8, "AB": 8, "A": 9,
            "A#": 10, "BB": 10, "B": 11}
_MAJOR_SCALE = (0, 2, 4, 5, 7, 9, 11)
_MINOR_SCALE = (0, 2, 3, 5, 7, 8, 10)


def _scale_pcs(root: str, mode: str) -> set:
    base = _MINOR_SCALE if mode.lower().startswith("min") else _MAJOR_SCALE
    tonic = _ROOT_PC[root.upper()]
    return {(tonic + iv) % 12 for iv in base}


def _warn_if_snap(raw, root: str, mode: str) -> None:
    """S4 recurrence guard: estimate_key on RAW notes + out-of-scale ratio.

    ``bed_lanes.cleanup(root, mode)`` scale-locks every off-scale pitch to
    the nearest in-scale note — which is exactly what silently rewrote the
    F#m riff into Dm for S3. Estimate the key first and warn loudly when
    the requested scale disagrees with the data (>15% duration out).
    """
    tonic, est_mode, r = sv.estimate_key(raw)
    print(f"[key-guard] estimate_key(raw) = {sv.PC_NAMES[tonic]} {est_mode} "
          f"r={r:+.3f}  (requested snap target: {root} {mode})")
    scale = _scale_pcs(root, mode)
    total = sum(max(n.duration_s, 0.0) for n in raw) or 1.0
    out = sum(max(n.duration_s, 0.0) for n in raw if n.note % 12 not in scale)
    frac = out / total
    print(f"[key-guard] {frac * 100:.1f}% of raw note duration is outside "
          f"{root} {mode}")
    if frac > 0.15:
        print("[key-guard] *** WARNING: >15% of the transcription falls "
              "outside the requested scale — cleanup will REWRITE those "
              "pitches (scale_lock). Estimated key is "
              f"{sv.PC_NAMES[tonic]} {est_mode}; consider transcribing/"
              "packing in the native key or transposing instead of "
              "snapping (see GATE S4). ***")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("start_s", type=float)
    ap.add_argument("end_s", type=float)
    ap.add_argument("--name", default=None)
    ap.add_argument("--root", default="D")
    ap.add_argument("--mode", default="minor")
    ap.add_argument("--bed", default=str(STEMS / "v2"))
    args = ap.parse_args(argv)

    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    name = args.name or f"region_{args.start_s:g}_{args.end_s:g}"
    MIDI_DIR.mkdir(parents=True, exist_ok=True)

    bed = find_bed(Path(args.bed))
    print(f"[bed] {bed.name}")
    notes, _events = transcribe_region(bed, args.start_s, args.end_s, MIDI_DIR)
    _warn_if_snap(notes, args.root, args.mode)
    cleaned = bed_lanes.cleanup(notes, bpm=FELT_BPM, subdivision=4,
                              min_conf=0.4, min_ms=80.0,
                              root=args.root, mode=args.mode)
    raw_pm = bed_lanes.notes_to_pretty_midi(notes, bpm=FELT_BPM)
    cl_pm = bed_lanes.notes_to_pretty_midi(cleaned, bpm=FELT_BPM)
    bed_lanes.save_midi(MIDI_DIR / f"{name}_raw.mid", raw_pm)
    out = MIDI_DIR / f"{name}_cleaned_{args.root}m.mid"
    bed_lanes.save_midi(out, cl_pm)
    print(f"[region] {args.start_s}-{args.end_s}s: "
          f"{len(notes)} raw -> {len(cleaned)} cleaned notes -> {out.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
