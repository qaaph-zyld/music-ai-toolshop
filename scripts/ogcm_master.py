"""OGCM flip W5 — mixdown + master + GATE F blind A/B pack (megaplan W5, F9).

Per arm: sum ``flip_renders/beat_{arm}.wav`` + ``flip_relay/vocal_{arm}.wav``
(deterministic numpy sum, recorded clip guard) -> master via
``toolshop.flip.master`` (pyloudnorm -14 LUFS ±0.3, pedalboard Limiter ->
true peak <= -1 dBTP; ``--club`` adds -9 LUFS variants) -> ADR-009 blind pack
under ``stems/flip_final/``: loudness-matched <=0.3 LU between arms, opaque
filenames, hidden keys in ``manifest.json``, verified pre-listening
(``verification.json``), plus ``GATE_F.md`` describing the pack without
revealing arm identities. ``2pac_drill_flip_whole.wav`` is copied into the
audition dir as a LABELLED reference (gain-matched only, NOT an arm).

Usage:
    python scripts/ogcm_master.py            # mix + master + GATE F pack
    python scripts/ogcm_master.py --club     # also emit -9 LUFS club masters
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from toolshop.flip import master  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
STEMS = REPO / "Stemmeca_alatkka" / "stems"
RENDERS = STEMS / "flip_renders"
RELAY = STEMS / "flip_relay"
DEFAULT_OUTDIR = STEMS / "flip_final"
REFERENCE_SRC = STEMS / "2pac_drill_flip_whole.wav"

ARMS = {
    "felt_89": {"bpm_written": 178.2, "felt_bpm": 89.1},
    "triplet_133": {"bpm_written": 133.65, "felt_bpm": 89.1},
}
SEED = 20260928  # fixed shuffle seed -> deterministic pack file order
SUBTYPE = "PCM_24"


# ---------------------------------------------------------------------------
# Mixdown
# ---------------------------------------------------------------------------

def mix_arm(arm: str, outdir: Path) -> Tuple[Path, Dict[str, Any]]:
    """Sum beat + vocal lanes -> `mix_{arm}.wav` + `mix_{arm}_events.json`."""
    beat_path = RENDERS / f"beat_{arm}.wav"
    vocal_path = RELAY / f"vocal_{arm}.wav"
    beat, sr_b = sf.read(str(beat_path), always_2d=True)
    vocal, sr_v = sf.read(str(vocal_path), always_2d=True)
    if sr_b != sr_v:
        raise ValueError(f"{arm}: sr mismatch {sr_b} vs {sr_v}")
    mix, info = master.mix_lanes(beat, vocal)
    out = outdir / f"mix_{arm}.wav"
    sf.write(str(out), mix, sr_b, subtype="FLOAT")
    info.update({
        "arm": arm,
        "beat_src": str(beat_path),
        "vocal_src": str(vocal_path),
        "out": str(out),
        "sr": sr_b,
        "duration_s": round(mix.shape[0] / float(sr_b), 3),
        "integrated_lufs": round(master.integrated_lufs(mix, sr_b), 2),
    })
    (outdir / f"mix_{arm}_events.json").write_text(
        json.dumps(info, indent=2), encoding="utf-8")
    return out, info


# ---------------------------------------------------------------------------
# Pack builder (ADR-009 blind pack)
# ---------------------------------------------------------------------------

def _apply_gain_to_ceiling(y: np.ndarray, sr: int, gain_db: float,
                           tp_ceiling: float) -> Tuple[np.ndarray, float]:
    """Apply gain_db but never let true peak exceed the ceiling; returns
    (audio, applied_gain_db)."""
    applied = gain_db
    while True:
        out = y * np.float32(10.0 ** (applied / 20.0))
        tp = master.true_peak_dbfs(out, sr)
        if tp <= tp_ceiling or applied <= -60.0:
            return out.astype(np.float32), applied
        applied -= tp - tp_ceiling  # reduce gain by the overshoot


def build_pack(outdir: Path, mastered: Dict[str, Path],
               target_lufs: float, lu_tol: float,
               tp_ceiling: float) -> Dict[str, Any]:
    """Write audition/ with opaque arm files + labelled reference; manifest."""
    aud = outdir / "audition"
    aud.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    arms = sorted(mastered)
    rng.shuffle(arms)

    # measure written masters; equalise arm copies by TRIM ONLY (gain down
    # never breaks the TP ceiling).
    measured = {}
    for arm, p in mastered.items():
        y, sr = sf.read(str(p), always_2d=True)
        measured[arm] = {"audio": y, "sr": sr,
                         "lufs": master.integrated_lufs(y, sr)}
    ref_lufs = min(m["lufs"] for m in measured.values())

    manifest: Dict[str, Any] = {
        "pack": "GATE_F_grid_arms",
        "seed": SEED,
        "target_lufs": target_lufs,
        "lu_tolerance": lu_tol,
        "tp_ceiling_dbtp": tp_ceiling,
        "arms": ARMS,
        "files": [],
    }
    for n, arm in enumerate(arms, 1):
        m = measured[arm]
        trim = min(0.0, ref_lufs - m["lufs"])  # <=0: pull louder file down
        audio = (m["audio"] * np.float32(10.0 ** (trim / 20.0))).astype(np.float32)
        fname = f"flip_{n:03d}.wav"
        sf.write(str(aud / fname), audio, m["sr"], subtype=SUBTYPE)
        manifest["files"].append({
            "file": fname,
            "arm": arm,
            "role": "arm",
            "trim_db": round(trim, 3),
            "mastered_src": str(mastered[arm]),
            "bpm_written": ARMS[arm]["bpm_written"],
        })

    # labelled reference (NOT an arm): gain-match toward target, capped by TP.
    if REFERENCE_SRC.exists():
        ry, rsr = sf.read(str(REFERENCE_SRC), always_2d=True)
        cur = master.integrated_lufs(ry, rsr)
        audio, applied = _apply_gain_to_ceiling(ry, rsr, target_lufs - cur,
                                                tp_ceiling)
        fname = "REFERENCE_prior_whole_flip.wav"
        sf.write(str(aud / fname), audio, rsr, subtype=SUBTYPE)
        manifest["files"].append({
            "file": fname,
            "arm": None,
            "role": "reference",
            "source": str(REFERENCE_SRC),
            "gain_db": round(applied, 3),
        })
    return manifest


def verify_pack(manifest: Dict[str, Any], outdir: Path) -> Dict[str, Any]:
    """ADR-009 pre-listening verification, re-measured from the written files."""
    aud = outdir / "audition"
    per_file = []
    arm_lufs = []
    for f in manifest["files"]:
        y, sr = sf.read(str(aud / f["file"]), always_2d=True)
        rec = {
            "file": f["file"],
            "role": f["role"],
            "lufs": round(master.integrated_lufs(y, sr), 2),
            "true_peak_dbtp": round(master.true_peak_dbfs(y, sr), 2),
            "sample_peak": round(float(np.abs(y).max()), 4),
            "duration_s": round(y.shape[0] / float(sr), 3),
        }
        per_file.append(rec)
        if f["role"] == "arm":
            arm_lufs.append(rec["lufs"])
    spread = max(arm_lufs) - min(arm_lufs) if arm_lufs else 0.0
    verified = {
        "per_file": per_file,
        "arm_lufs_spread": round(spread, 3),
        "lufs_spread_ok": bool(spread <= manifest["lu_tolerance"]),
        "true_peak_ok": bool(all(
            r["true_peak_dbtp"] <= manifest["tp_ceiling_dbtp"] + 0.05
            for r in per_file)),
        "no_clipping": bool(all(r["sample_peak"] <= 1.0 for r in per_file)),
        "bijection_ok": bool(
            len({f["file"] for f in manifest["files"]}) == len(manifest["files"])
            and len({f["arm"] for f in manifest["files"]
                     if f["role"] == "arm"}) == len(ARMS)),
    }
    verified["passed"] = bool(
        verified["lufs_spread_ok"] and verified["true_peak_ok"]
        and verified["no_clipping"] and verified["bijection_ok"])
    return verified


def write_gate_doc(outdir: Path, manifest: Dict, verified: Dict,
                   master_reports: Dict[str, Dict]) -> None:
    """GATE_F.md — describes the pack WITHOUT revealing which file is which arm."""
    n_arms = sum(1 for f in manifest["files"] if f["role"] == "arm")
    has_ref = any(f["role"] == "reference" for f in manifest["files"])
    ref_line = (
        "- `REFERENCE_prior_whole_flip.wav` — LABELLED sanity-floor reference "
        "(the July whole-buffer remix, gain-matched to the pack loudness; "
        "not a contestant, do not pick it).\n" if has_ref else "")
    per_file_rows = "\n".join(
        f"| `{r['file']}` | {r['duration_s']} s | {r['lufs']} | "
        f"{r['true_peak_dbtp']} |" for r in verified["per_file"])
    text = f"""# GATE F — Grid-Arm Blind A/B (OGCM drill flip)

Blind audition for the final grid decision (megaplan W5). The pack contains
**{n_arms} mastered flip renders** — each is a full mix (mined-kit drill drums +
808 + GATE C2 bed lane + relayed vocal) mastered to **{manifest['target_lufs']}
LUFS** with a true-peak ceiling of **{manifest['tp_ceiling_dbtp']} dBTP**
(`scripts/ogcm_master.py` + `toolshop/flip/master.py`; finding F9 closed).

## What you are choosing

**Which tempo grid the flip ships on** — the 178.2-written / 89.1-felt arm or
the 133.65 (exact 3:2) arm. That is the only decision; the files differ in
duration because the arms carry different bar counts (m3) — the render length
is part of the design, not a defect.

## The files

| File | Duration | Integrated LUFS | True peak (dBTP, 4x) |
|---|---|---|---|
{per_file_rows}
{ref_line}
## Honest coverage note (does not key the files)

The vocal relay (m4) placed the lead on an identical source-felt schedule on
both arms, but each beat render is shorter than the ~297 s source vocal. The
shorter render covers **3/20** lead phrases (+3 backing hook strips), the
longer covers **8/20** (+6 hook strips) — only the phrases inside each render
window were laid. Nothing was stretched to fake coverage (m4 declared
limitation; extending arrangements is a future-wave decision).

## Verification (ran on the written pack files before you listen)

- Arm-to-arm LUFS spread: **{verified['arm_lufs_spread']} LU**
  (tolerance {manifest['lu_tolerance']}) -> **{'PASS' if verified['lufs_spread_ok'] else 'FAIL'}**
- True peaks <= {manifest['tp_ceiling_dbtp']} dBTP on every file
  -> **{'PASS' if verified['true_peak_ok'] else 'FAIL'}**
- Clipping: **{'none' if verified['no_clipping'] else 'PRESENT — FAIL'}**
- File/identity bijection: **{'PASS' if verified['bijection_ok'] else 'FAIL'}**
- Overall: **{'PASS' if verified['passed'] else 'FAIL'}**

## How to pick

Listen to the two `flip_00N.wav` files (the reference is labelled, compare
against it freely). Pick the filename whose GRID you want — the ear decides
between the double-time-felt groove and the triplet-fight arm. Tell the
orchestrator your pick filename; the file→arm mapping lives in
`manifest.json` next to this file (**do not read before picking**) and every file outside
`audition/` (`mix_*.wav`, `mastered_*.wav`) is identity-named.
"""
    (outdir / "GATE_F.md").write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    ap.add_argument("--target-lufs", type=float, default=master.TARGET_LUFS)
    ap.add_argument("--club", action="store_true",
                    help="also emit -9 LUFS club masters (delivery extras)")
    ap.add_argument("--skip-pack", action="store_true")
    args = ap.parse_args(argv)

    outdir = args.outdir
    outdir.mkdir(parents=True, exist_ok=True)

    # ---- 1. mixdown per arm -------------------------------------------------
    mixes: Dict[str, Path] = {}
    for arm in ARMS:
        mix_path, info = mix_arm(arm, outdir)
        mixes[arm] = mix_path
        print(f"[mix] {arm}: {info['duration_s']}s "
              f"beat_peak={info['beat_peak']:.3f} vocal_peak={info['vocal_peak']:.3f} "
              f"pre_guard={info['pre_guard_peak']:.3f} "
              f"guard={'YES' if info['clip_guard_fired'] else 'no'} "
              f"lufs={info['integrated_lufs']}")

    # ---- 2. master per arm --------------------------------------------------
    mastered: Dict[str, Path] = {}
    reports: Dict[str, Dict] = {}
    for arm, mix_path in mixes.items():
        out = outdir / f"mastered_{arm}.wav"
        rep = master.master_file(mix_path, out, target_lufs=args.target_lufs)
        reports[arm] = rep
        mastered[arm] = out
        print(f"[master] {arm}: in={rep['input_lufs']} LUFS -> "
              f"{rep['final_lufs']} LUFS (target {rep['target_lufs']}), "
              f"TP={rep['final_true_peak_dbtp']} dBTP, "
              f"iters={len(rep['iterations'])}, passed={rep['passed']}")
        if args.club:
            club_out = outdir / f"mastered_{arm}_club-9.wav"
            crep = master.master_file(mix_path, club_out,
                                      target_lufs=master.CLUB_LUFS)
            print(f"[master] {arm} club-9: {crep['final_lufs']} LUFS, "
                  f"TP={crep['final_true_peak_dbtp']} dBTP, "
                  f"passed={crep['passed']}")

    # ---- 3. GATE F blind pack ----------------------------------------------
    if not args.skip_pack:
        manifest = build_pack(outdir, mastered, args.target_lufs,
                              master.LUFS_TOLERANCE, master.TP_CEILING_DBTP)
        (outdir / "manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8")
        verified = verify_pack(manifest, outdir)
        (outdir / "verification.json").write_text(
            json.dumps(verified, indent=2), encoding="utf-8")
        write_gate_doc(outdir, manifest, verified, reports)
        for r in verified["per_file"]:
            print(f"[pack] {r['file']}: {r['duration_s']}s "
                  f"{r['lufs']} LUFS, TP={r['true_peak_dbtp']} dBTP")
        print(f"[verify] arm LU spread {verified['arm_lufs_spread']} "
              f"(<= {manifest['lu_tolerance']}) | TP ok={verified['true_peak_ok']} "
              f"| clips={'none' if verified['no_clipping'] else 'PRESENT'} "
              f"| bijection={verified['bijection_ok']} "
              f"| PASSED={verified['passed']}")
        if not verified["passed"]:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
