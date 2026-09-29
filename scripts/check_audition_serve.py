"""Check that the audition server serves every pack file (O3 for GATE S3).

For every file matching --glob under --dir: HTTP-GET ``--base/<relpath>`` and
require status 200; also require the file's relative path to appear in the
``--index`` HTML (each file is actually linked from the audition page).

Usage:
    python scripts/check_audition_serve.py \
        --base "http://127.0.0.1:8777/flip_sample" \
        --dir "D:\\Projects\\Music-AI-Toolshop\\Stemmeca_alatkka\\stems\\flip_sample" \
        --glob "audition_s3/s3_*.wav" --index "index.html"
"""

from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(prog="check_audition_serve")
    p.add_argument("--base", required=True,
                   help="base URL the --dir is served from, e.g. http://127.0.0.1:8777/flip_sample")
    p.add_argument("--dir", required=True, help="served directory on disk")
    p.add_argument("--glob", default="audition_s3/s3_*.wav",
                   help="file pattern relative to --dir")
    p.add_argument("--index", default="index.html",
                   help="HTML file (relative to --dir) that must link each file")
    p.add_argument("--timeout", type=float, default=10.0)
    args = p.parse_args()

    root = Path(args.dir)
    files = sorted(root.glob(args.glob))
    if not files:
        print(f"FAIL  no files match '{args.glob}' under {root}")
        return 1

    index_path = root / args.index
    if not index_path.is_file():
        print(f"FAIL  index not found: {index_path}")
        return 1
    index_html = index_path.read_text(encoding="utf-8", errors="replace")

    ok = True
    for f in files:
        rel = f.relative_to(root).as_posix()
        url = f"{args.base.rstrip('/')}/{rel}"
        try:
            with urllib.request.urlopen(url, timeout=args.timeout) as resp:
                code = resp.status
        except Exception as exc:
            code = f"ERR {exc}"
        linked = rel in index_html
        good = code == 200 and linked
        ok &= good
        print(f"{'PASS' if good else 'FAIL'}  {rel}  http={code} "
              f"linked={'yes' if linked else 'NO'}", flush=True)

    print("check_audition_serve: " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
