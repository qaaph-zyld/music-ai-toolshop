"""O6 — GATE S5b wail pitch-contour check.

Reads ``audition_s5/manifest.json`` and ``contour.npz`` (written by
``ogcm_sample.py --pack s5``) and exits 0 only when ALL of these hold:

- voiced coverage inside phrases >= 0.6
- octave_jumps == 0            (adjacent voiced frames jumping >= 10 st)
- in_key_ratio  >= 0.8         (share of note segments whose median MIDI,
                                after the -4 transpose, is a D-minor pitch
                                class; thresholds are NOT loosened here)
- source_audio_in_output is false (and no chop/REF file in the manifest)
- bpm in [102.5, 107]          (1.15-1.20 x the record's 89.1 felt BPM)
- every stat in the manifest's ``contour_stats`` matches a recomputation from
  ``contour.npz`` within 1 %   (the verifier does not trust the manifest)

If in_key_ratio fails, the offending note segments are listed.

Usage:
    python scripts/check_contour.py [--manifest .../audition_s5/manifest.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from toolshop.flip import sample_voices as sv  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = (REPO / "Stemmeca_alatkka" / "stems" / "flip_sample"
                    / "audition_s5" / "manifest.json")

MIN_COVERAGE = 0.6
MAX_OCTAVE_JUMPS = 0
MIN_IN_KEY = 0.8
BPM_LO, BPM_HI = 102.5, 107.0
REL_TOL = 0.01


def _close(a, b, rel: float = REL_TOL) -> bool:
    if a is None or b is None:
        return a is b
    return abs(float(a) - float(b)) <= rel * max(abs(float(a)),
                                                 abs(float(b))) + 1e-9


def main(argv=None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    args = ap.parse_args(argv)

    mpath = Path(args.manifest)
    npz_path = mpath.parent / "contour.npz"
    manifest = json.loads(mpath.read_text(encoding="utf-8"))
    print(f"[check_contour] {mpath}")
    if not npz_path.is_file():
        print(f"  FAIL  contour.npz missing next to the manifest: {npz_path}")
        print("O6: FAIL")
        return 1
    d = np.load(str(npz_path))
    contour = sv.contour_from_arrays(d["times"], d["f0_hz"], d["rms"],
                                     float(d["hop_s"]))
    st = sv.contour_stats(contour)
    man = manifest.get("contour_stats", {})

    files = [r.get("file", "") for r in manifest.get("files", [])]
    bad_files = [f for f in files
                 if "chop" in f.lower()
                 or Path(f).stem.upper().endswith("_REF")]
    bpm = manifest.get("bpm")

    mism = []
    for k, mv in man.items():
        if k in st and isinstance(mv, (int, float)) and not isinstance(mv, bool):
            if not _close(mv, st[k]):
                mism.append(f"{k}: manifest={mv} recomputed={st[k]}")
    if not man:
        mism.append("manifest has no contour_stats")

    # npz internal consistency: native f0 + transpose == stored f0
    consistent = True
    detail = "n/a"
    if "f0_hz_native" in d.files and "transpose_st" in d.files:
        nat = sv._hz_to_midi(d["f0_hz_native"]) + float(d["transpose_st"])
        cur = sv._hz_to_midi(d["f0_hz"])
        both = np.isfinite(nat) & np.isfinite(cur)
        consistent = bool(np.array_equal(np.isfinite(nat), np.isfinite(cur))
                          and (not both.any()
                               or float(np.max(np.abs(nat[both] - cur[both])))
                               < 1e-6))
        detail = f"transpose_st={float(d['transpose_st']):+g}"

    checks = [
        ("voiced coverage in phrases >= 0.6 (recomputed)",
         st["voiced_coverage_in_phrases"] >= MIN_COVERAGE,
         st["voiced_coverage_in_phrases"]),
        ("octave_jumps == 0 (recomputed)",
         st["octave_jumps"] == MAX_OCTAVE_JUMPS, st["octave_jumps"]),
        ("in_key_ratio >= 0.8 (recomputed)",
         st["in_key_ratio"] >= MIN_IN_KEY,
         f"{st['in_key_ratio']} ({st['n_segments_in_key']}/"
         f"{st['n_segments']} segments)"),
        ("source_audio_in_output is false",
         manifest.get("source_audio_in_output") is False
         and not bad_files,
         f"{manifest.get('source_audio_in_output')!r}, "
         f"chop/REF files: {bad_files or 'none'}"),
        ("bpm in [102.5, 107]",
         isinstance(bpm, (int, float)) and BPM_LO <= bpm <= BPM_HI, bpm),
        ("recomputed stats match manifest within 1 %",
         not mism, "all match" if not mism else "; ".join(mism)),
        ("npz native f0 + transpose == stored f0", consistent, detail),
    ]

    ok = True
    for label, passed, val in checks:
        ok &= bool(passed)
        print(f"  {'PASS' if passed else 'FAIL'}  {label:50s} got={val}")

    if st["in_key_ratio"] < MIN_IN_KEY:
        keyset = {p % 12 for p in sv.D_MINOR_PCS}
        print("  offending segments (median MIDI pitch class not in D minor):")
        for s in sv.note_segments(contour):
            m = int(round(s["median_midi"]))
            if m % 12 not in keyset:
                print(f"    t={s['start_s']:.3f}-{s['end_s']:.3f} s  "
                      f"{sv.note_name(m)} (median {s['median_midi']:.2f})")
    print("O6:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
