"""Verify a rendered sample pack (O1 check for GATE S3).

For every WAV matching --glob under --dir: parses as audio, is stereo at the
expected sample rate, duration within [--min-s, --max-s], integrated loudness
within --lufs ± --lufs-tol, true peak <= --tp-max dBTP, and no clipped
(|x| >= 0.999) samples. Exits 0 when every check passes.

Usage:
    python scripts/verify_sample_pack.py --dir <pack dir> --glob "s3_*.wav" \
        --min-files 4 --min-s 15 --max-s 45 --lufs -16 --lufs-tol 1.0 --tp-max -1.0
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from toolshop.flip import master  # noqa: E402


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(prog="verify_sample_pack")
    p.add_argument("--dir", required=True, help="pack directory")
    p.add_argument("--glob", default="*.wav", help="file pattern within --dir")
    p.add_argument("--min-files", type=int, default=4)
    p.add_argument("--min-s", type=float, default=15.0)
    p.add_argument("--max-s", type=float, default=45.0)
    p.add_argument("--sr", type=int, default=44100)
    p.add_argument("--lufs", type=float, default=-16.0)
    p.add_argument("--lufs-tol", type=float, default=1.0)
    p.add_argument("--tp-max", type=float, default=-1.0)
    args = p.parse_args()

    root = Path(args.dir)
    files = sorted(root.glob(args.glob))
    ok = True

    if len(files) < args.min_files:
        print(f"FAIL  only {len(files)} file(s) match '{args.glob}' "
              f"(need >= {args.min_files})", flush=True)
        ok = False

    for f in files:
        rel = f.name
        try:
            y, sr = sf.read(str(f), always_2d=True)
        except Exception as exc:
            print(f"FAIL  {rel}: unreadable ({exc})")
            ok = False
            continue
        dur = y.shape[0] / sr
        chans = y.shape[1]
        lufs = master.integrated_lufs(y, sr)
        tp = master.true_peak_dbfs(y, sr)
        clipped = bool((np.abs(y) >= 0.999).any())
        problems = []
        if sr != args.sr:
            problems.append(f"sr {sr} != {args.sr}")
        if chans != 2:
            problems.append(f"{chans}ch != stereo")
        if not (args.min_s <= dur <= args.max_s):
            problems.append(f"dur {dur:.1f}s not in [{args.min_s}, {args.max_s}]")
        if not (args.lufs - args.lufs_tol <= lufs <= args.lufs + args.lufs_tol):
            problems.append(f"lufs {lufs:.2f} outside {args.lufs}±{args.lufs_tol}")
        if tp > args.tp_max:
            problems.append(f"tp {tp:.2f} > {args.tp_max}")
        if clipped:
            problems.append("clipped samples")
        status = "PASS" if not problems else "FAIL"
        ok &= not problems
        print(f"{status}  {rel}  {dur:.1f}s {sr}Hz {chans}ch "
              f"{lufs:.2f}LUFS tp={tp:.2f}dBTP"
              + (f"  [{'; '.join(problems)}]" if problems else ""), flush=True)

    print("verify_sample_pack: " + ("PASS" if ok and files else "FAIL"))
    return 0 if ok and files else 1


if __name__ == "__main__":
    raise SystemExit(main())
