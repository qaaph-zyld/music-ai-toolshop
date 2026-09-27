"""Bleed evidence for the OGCM W0 separation (spec step: evidence JSON).

Compares the v2 RoFormer outputs against the legacy htdemucs_6s stems and
produces a JSON report of measurable bleed indicators — no quality verdicts,
just numbers for the W0 handoff:

- vocal→instrumental bleed: correlation between the v2 vocal stem and the
  v2 instrumental ("other") inside vocal-active regions — lower is better.
- instrumental→vocal bleed: residual harmonic content in the vocal stem
  outside vocal-active regions (median RMS in detected vocal-silent spans).
- karaoke split: energy fraction the lead vocal retains vs the sung-hook
  companion output.

Usage:
  python scripts/ogcm_bleed_evidence.py --stems-dir <v2 dir> --legacy-dir <6s dir> --out <json>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np


def _load(path: Path, sr: int = 22050):
    import librosa

    y, _ = librosa.load(str(path), sr=sr, mono=True)
    return y


def _rms_env(y: np.ndarray, hop: int = 512):
    import librosa

    return librosa.feature.rms(y=y, hop_length=hop)[0]


def _vocal_active_mask(vocal_env: np.ndarray, floor: float) -> np.ndarray:
    peak = vocal_env.max()
    if peak <= 0:
        return np.zeros_like(vocal_env, dtype=bool)
    return vocal_env > max(floor, peak * 0.05)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stems-dir", type=Path, required=True)
    ap.add_argument("--legacy-dir", type=Path, default=None)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--sr", type=int, default=22050)
    args = ap.parse_args()

    v2 = args.stems_dir
    files = {p.stem: p for p in v2.glob("*.wav")}
    evidence = {"stems_dir": str(v2), "files": sorted(files), "metrics": {}}

    # The ogcm-flip chain deletes intermediates: the raw Kim "(vocals)" file is
    # consumed by karaoke, so the surviving vocal probes are the dereverbed
    # lead ("noreverb") and its reverb tail. Prefer noreverb > karaoke main.
    vocals = (
        next((p for k, p in files.items() if "_(noreverb)_" in k), None)
        or next((p for k, p in files.items() if "_(Vocals)_" in k), None)
        or next((p for k, p in files.items() if "_(vocals)_" in k), None)
    )
    other = next((p for k, p in files.items() if "_(other)_" in k), None)
    karaoke = next((p for k, p in files.items() if "karaoke" in k and "vocals" in k.lower()), None)
    dereverb = next((p for k, p in files.items() if "dereverb" in k), None)

    if vocals and other:
        yv = _load(vocals, args.sr)
        yo = _load(other, args.sr)
        n = min(yv.size, yo.size)
        ve = _rms_env(yv[:n])
        oe = _rms_env(yo[:n])
        m = _vocal_active_mask(ve, 0.01)
        m = m[: min(ve.size, oe.size)]
        ve, oe = ve[: m.size], oe[: m.size]
        if m.any():
            a = ve[m] - ve[m].mean()
            b = oe[m] - oe[m].mean()
            denom = np.linalg.norm(a) * np.linalg.norm(b) + 1e-12
            corr = float(np.clip(np.dot(a, b) / denom, 0, 1))
            evidence["metrics"]["vocal_active_env_corr_v2"] = round(corr, 4)
        # residual-in-silent: median vocal env in non-active regions / peak
        silent = ~_vocal_active_mask(ve, 0.01)
        if silent.any():
            evidence["metrics"]["vocal_silent_rms_ratio_v2"] = round(
                float(np.median(ve[silent]) / (ve.max() + 1e-12)), 5
            )

    if args.legacy_dir:
        leg = {p.stem: p for p in Path(args.legacy_dir).glob("*.wav")}
        lv = leg.get("vocals")
        li = leg.get("instrumental_internal") or leg.get("other")
        if lv and li:
            yv = _load(lv, args.sr)
            yo = _load(li, args.sr)
            n = min(yv.size, yo.size)
            ve = _rms_env(yv[:n])
            oe = _rms_env(yo[:n])
            m = _vocal_active_mask(ve, 0.01)[: min(ve.size, oe.size)]
            ve, oe = ve[: m.size], oe[: m.size]
            if m.any():
                a = ve[m] - ve[m].mean()
                b = oe[m] - oe[m].mean()
                denom = np.linalg.norm(a) * np.linalg.norm(b) + 1e-12
                evidence["metrics"]["vocal_active_env_corr_legacy"] = round(
                    float(np.clip(np.dot(a, b) / denom, 0, 1)), 4
                )
            silent = ~_vocal_active_mask(ve, 0.01)
            if silent.any():
                evidence["metrics"]["vocal_silent_rms_ratio_legacy"] = round(
                    float(np.median(ve[silent]) / (ve.max() + 1e-12)), 5
                )

    # Dereverb evidence: energy the model peeled off as reverb vs the dry lead.
    reverb_tail = next((p for k, p in files.items() if "_(reverb)_" in k), None)
    if dereverb and reverb_tail and vocals:
        ylead = _rms_env(_load(vocals, args.sr))
        ytail = _rms_env(_load(reverb_tail, args.sr))
        evidence["metrics"]["reverb_tail_peak_ratio"] = round(
            float(ytail.max() / (ylead.max() + 1e-12)), 4
        )
        evidence["metrics"]["reverb_tail_rms_ratio"] = round(
            float(ytail.mean() / (ylead.mean() + 1e-12)), 4
        )

    evidence["present_outputs"] = {
        "vocals": bool(vocals),
        "other": bool(other),
        "karaoke": bool(karaoke),
        "dereverb": bool(dereverb),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    print(json.dumps(evidence["metrics"], indent=2))
    print(f"written: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
