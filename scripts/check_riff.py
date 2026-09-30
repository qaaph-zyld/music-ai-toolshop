"""O5 — GATE S4 riff-density check.

Reads ``audition_s4/manifest.json`` (written by ``ogcm_sample.py --pack s4``)
and exits 0 only when the riff is dense/continuous enough to be a plausible
"recognizable melody" candidate — the failure axes that sank S3:

- coverage      >= 0.6    (S3 motif left ~75% of the loop silent)
- n_notes       >= 8
- notes_per_s   >= 1.5    (S3 kept 0.93)
- max_leap_st   <= 12     (no octave-error jumps)
- snapped_notes == 0      (transpose, never scale_lock)
- source tonic transposed by ``transpose_st`` lands on D minor

Usage:
    python scripts/check_riff.py [--manifest .../audition_s4/manifest.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = (REPO / "Stemmeca_alatkka" / "stems" / "flip_sample"
                    / "audition_s4" / "manifest.json")

MIN_COVERAGE = 0.6
MIN_NOTES = 8
MIN_NOTES_PER_S = 1.5
MAX_LEAP_ST = 12
DM_TONIC_PC = 2          # D


def main(argv=None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    args = ap.parse_args(argv)

    mpath = Path(args.manifest)
    manifest = json.loads(mpath.read_text(encoding="utf-8"))
    s4 = manifest.get("s4", {})
    stats = s4.get("riff_stats", {})
    src = s4.get("source_key", {})
    transpose_st = s4.get("transpose_st", 0)

    landed_pc = (src.get("tonic_pc", 0) + transpose_st) % 12
    landed_ok = (landed_pc == DM_TONIC_PC and src.get("mode") == "minor")

    checks = [
        ("coverage >= 0.6", stats.get("coverage", 0.0) >= MIN_COVERAGE,
         stats.get("coverage")),
        ("n_notes >= 8", stats.get("n_notes", 0) >= MIN_NOTES,
         stats.get("n_notes")),
        ("notes_per_s >= 1.5", stats.get("notes_per_s", 0.0) >= MIN_NOTES_PER_S,
         stats.get("notes_per_s")),
        ("max_leap_st <= 12", stats.get("max_leap_st", 99) <= MAX_LEAP_ST,
         stats.get("max_leap_st")),
        ("snapped_notes == 0", s4.get("snapped_notes", -1) == 0,
         s4.get("snapped_notes")),
        ("source tonic + transpose_st == D minor", landed_ok,
         f"{src.get('tonic')} {src.get('mode')} {transpose_st:+d} -> "
         f"pc{landed_pc}"),
    ]

    ok = True
    print(f"[check_riff] {mpath}")
    for label, passed, val in checks:
        ok &= bool(passed)
        print(f"  {'PASS' if passed else 'FAIL'}  {label:45s} got={val}")
    print("O5:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
