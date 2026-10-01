"""O7 — GATE S6 pack-metadata check.

Reads ``audition_s6/manifest.json`` (written by ``ogcm_sample.py --pack s6``)
and exits 0 only when ALL of these hold:

- ``source_audio_in_output`` is exactly false   (synthesis only)
- ``drums`` is exactly false                    (Suno builds the beat)
- ``bpm`` lies in [--bpm-min, --bpm-max]        (default 102.5-107)
- ``organ_kinds`` equals the set given by ``--require-organ-kinds``
- the manifest lists at least one file and every listed file exists next to
  the manifest and is non-empty

Usage:
    python scripts/check_pack_meta.py [--manifest .../audition_s6/manifest.json]
        [--bpm-min 102.5] [--bpm-max 107]
        [--require-organ-kinds string,combo,drawbar]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = (REPO / "Stemmeca_alatkka" / "stems" / "flip_sample"
                    / "audition_s6" / "manifest.json")


def main(argv=None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    ap.add_argument("--bpm-min", type=float, default=102.5)
    ap.add_argument("--bpm-max", type=float, default=107.0)
    ap.add_argument("--require-organ-kinds", default="string,combo,drawbar",
                    help="comma-separated organ kinds the manifest must list "
                         "(set equality)")
    args = ap.parse_args(argv)

    mpath = Path(args.manifest)
    print(f"[check_pack_meta] {mpath}")
    if not mpath.is_file():
        print(f"  FAIL  manifest not found: {mpath}")
        print("O7: FAIL")
        return 1
    manifest = json.loads(mpath.read_text(encoding="utf-8"))

    required = {k.strip() for k in args.require_organ_kinds.split(",")
                if k.strip()}
    kinds = manifest.get("organ_kinds")
    kinds_set = set(kinds) if isinstance(kinds, list) else None
    bpm = manifest.get("bpm")
    bpm_ok = (isinstance(bpm, (int, float)) and not isinstance(bpm, bool)
              and args.bpm_min <= bpm <= args.bpm_max)

    files = manifest.get("files")
    rows = []
    if isinstance(files, list) and files:
        for rec in files:
            name = rec.get("file") if isinstance(rec, dict) else None
            path = mpath.parent / name if name else None
            size = path.stat().st_size if path and path.is_file() else None
            rows.append((name, size))
    missing = [n for n, s in rows if not s]
    files_ok = bool(rows) and not missing

    checks = [
        ("source_audio_in_output is false",
         manifest.get("source_audio_in_output") is False,
         repr(manifest.get("source_audio_in_output"))),
        ("drums is false", manifest.get("drums") is False,
         repr(manifest.get("drums"))),
        (f"bpm in [{args.bpm_min:g}, {args.bpm_max:g}]", bpm_ok, bpm),
        (f"organ_kinds == {sorted(required)}",
         kinds_set is not None and kinds_set == required
         and len(kinds) == len(kinds_set),
         kinds),
        ("every manifest file exists and is non-empty", files_ok,
         f"{len(rows)} files" if files_ok
         else ("no files listed" if not rows
               else f"missing/empty: {missing}")),
    ]
    ok = True
    for label, passed, val in checks:
        ok &= bool(passed)
        print(f"  {'PASS' if passed else 'FAIL'}  {label:50s} got={val}")
    print("O7:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
