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
from toolshop.flip import bed_lanes  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
STEMS = REPO / "Stemmeca_alatkka" / "stems"
MIDI_DIR = STEMS / "flip_bed_lanes" / "midi"
FELT_BPM = 89.1


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
