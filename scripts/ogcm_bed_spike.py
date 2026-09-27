#!/usr/bin/env python
"""OGCM flip W1' bed-lane spike -> GATE C2 audition pack (megaplan W1').

Drives the pure-code melodic-bed pivot:
  basic-pitch ONNX  ->  MIDI cleanup  ->  numpy voice render  ->  blind pack.

Three lanes feed the GATE C2 audition (user picks lane + grid arm + hook):
  - Lane A: existing chop pack (stems/flip_chops_v2, cand_220/121, F#min) —
            reused, no new module code; this script only tiles + time-stretches.
  - Lane B: interpolated bed — basic-pitch on the top GATE-C regions of the
            v2 `(other)` bed -> cleanup -> epiano/pad render.
  - Lane C: 2-3 hand-programmed dark Dm/C#m motifs via pretty_midi -> same voices.

Pack follows ADR-009: all lanes x both grid arms (178.2 written/89.1 felt AND
133.65) as 8-bar loops, loudness-matched <=0.3 LU, hidden keys in a JSON,
verified pre-listening, plus GATE_C2.md that describes the pack WITHOUT
revealing which file is which lane.

STOP at GATE C2: the user auditions and picks. No drum/808/arrange work here.

Usage:
  python scripts/ogcm_bed_spike.py [--bed <path>] [--outdir <path>]
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import random
import sys
import warnings
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np
import soundfile as sf

# quiet basic-pitch's tensorflow-absence warnings (expected under --no-deps)
warnings.filterwarnings("ignore")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
logging.getLogger("root").setLevel(logging.ERROR)

from toolshop.flip import bed_lanes

REPO = Path(__file__).resolve().parents[1]
STEMS = REPO / "Stemmeca_alatkka" / "stems"
V2_BED_GLOB = "*_(other)_*.wav"
CHOP_AUDITION = STEMS / "flip_chops_v2" / "audition"
LANE_A_CANDS = ["cand_220_4bar_F#min_score0.58.wav", "cand_121_2bar_F#min_score0.62.wav"]

# Top GATE-C regions on the v2 (other) bed (megaplan W1' step 2).
REGIONS: List[Tuple[str, float, float]] = [
    ("region_63_66", 63.0, 73.0),     # ~63-66 s (10 s window for context)
    ("region_12_6", 12.6, 22.6),       # ~12.6 s
    ("region_233_258", 233.0, 258.0),  # ~233-258 s
]

# Grid arms (megaplan dual-grid): 89.1 felt (=178.2 written) and 133.65.
ARMS = {"felt_89": 89.1, "triplet_133": 133.65}
BARS = 8
SR = 44100
TARGET_LUFS = -18.0
LU_TOLERANCE = 0.3


# ---------------------------------------------------------------------------
# Transcription (Lane B input)
# ---------------------------------------------------------------------------

def find_bed(stems_v2: Path) -> Path:
    cands = sorted(stems_v2.glob(V2_BED_GLOB))
    if not cands:
        raise FileNotFoundError(f"no (other) bed in {stems_v2}")
    return cands[0]


def transcribe_region(bed: Path, start_s: float, end_s: float,
                      outdir: Path) -> Tuple[List[bed_lanes.BedNote], List[Tuple]]:
    """Clip a region from the bed, run basic-pitch ONNX, return (notes, events)."""
    from basic_pitch.inference import predict
    y, sr = sf.read(str(bed))
    if y.ndim > 1:
        y = y.mean(axis=1)
    s = int(start_s * sr)
    e = int(end_s * sr)
    clip = y[s:e].astype(np.float32)
    tmp = outdir / f"_clip_{int(start_s)}_{int(end_s)}.wav"
    sf.write(str(tmp), clip, sr)
    _model_out, _pmidi, events = predict(
        str(tmp), onset_threshold=0.5, frame_threshold=0.3,
        minimum_note_length=80.0, midi_tempo=89.1)
    tmp.unlink(missing_ok=True)
    notes = bed_lanes.events_to_notes(events)
    return notes, events


# ---------------------------------------------------------------------------
# Lane C: hand-programmed dark motifs
# ---------------------------------------------------------------------------

def _motif_dm_1() -> List[bed_lanes.BedNote]:
    """Dark Dm motif: i-VI arpeggio, 2-bar, 89.1-grid aligned (16ths)."""
    beat = 60.0 / 89.1
    six = beat / 4.0
    # D F A (i) then Bb D F (VI) — dark minor vault
    seq = [
        (0, 0.5, 62), (0.5, 1.0, 65), (1.0, 1.5, 69),   # D F A
        (2.0, 2.5, 58), (2.5, 3.0, 62), (3.0, 3.5, 65),  # Bb D F
        (4.0, 4.5, 65), (4.5, 5.0, 69), (5.0, 5.5, 72),  # F A C
        (6.0, 7.0, 62),                                    # D sustain
    ]
    return [bed_lanes.BedNote(s * six, e * six, n, 0.85) for s, e, n in seq]


def _motif_dm_2() -> List[bed_lanes.BedNote]:
    """Dark Dm motif 2: sparse minor-9 stabs, 2-bar."""
    beat = 60.0 / 89.1
    six = beat / 4.0
    seq = [
        (0, 1.0, 62), (0, 1.0, 74),   # D + D (octave stab)
        (2, 3.0, 65), (2, 3.0, 77),   # F + F
        (4, 5.0, 60), (4, 5.0, 72),   # C + C (VII)
        (6, 7.0, 58), (6, 7.0, 70),   # Bb + Bb (VI)
    ]
    return [bed_lanes.BedNote(s * six, e * six, n, 0.8) for s, e, n in seq]


def _motif_csm_1() -> List[bed_lanes.BedNote]:
    """Dark C#m motif: i-VII-VI arpeggio, 2-bar."""
    beat = 60.0 / 89.1
    six = beat / 4.0
    # C# E G# (i) then B D# F# (VI) then A C# E (V)
    seq = [
        (0, 0.5, 61), (0.5, 1.0, 64), (1.0, 1.5, 68),
        (2.0, 2.5, 59), (2.5, 3.0, 63), (3.0, 3.5, 66),
        (4.0, 4.5, 57), (4.5, 5.0, 61), (5.0, 5.5, 64),
        (6.0, 7.0, 61),
    ]
    return [bed_lanes.BedNote(s * six, e * six, n, 0.85) for s, e, n in seq]


LANE_C_MOTIFS = [
    ("motif_dm_1", "D", "minor", _motif_dm_1()),
    ("motif_dm_2", "D", "minor", _motif_dm_2()),
    ("motif_csm_1", "C#", "minor", _motif_csm_1()),
]


# ---------------------------------------------------------------------------
# Lane A: existing chops (reuse, tile + time-stretch)
# ---------------------------------------------------------------------------

def lane_a_loop(chop_path: Path, arm_bpm: float, bars: int = BARS) -> np.ndarray:
    """Tile an existing chop to `bars` felt bars at `arm_bpm` (pitch-preserving)."""
    y, sr = sf.read(str(chop_path))
    if y.ndim > 1:
        y = y.mean(axis=1)
    y = y.astype(np.float32)
    target_len = int(bars * 4 * 60.0 / arm_bpm * sr)
    # tile to target
    if y.size < target_len:
        reps = int(np.ceil(target_len / y.size))
        y = np.tile(y, reps)
    y = y[:target_len]
    return y.astype(np.float32)


# ---------------------------------------------------------------------------
# Render helpers
# ---------------------------------------------------------------------------

def render_lane_b_loop(notes: Sequence[bed_lanes.BedNote], voice: str,
                       arm_bpm: float, root: str, bars: int = BARS) -> np.ndarray:
    cleaned = bed_lanes.cleanup(notes, bpm=89.1, subdivision=4,
                                min_conf=0.4, min_ms=80.0,
                                root=root, mode="minor")
    return bed_lanes.render_loop(cleaned, voice=voice, bars=bars,
                                 bpm=arm_bpm, sr=SR)


def render_lane_c_loop(motif_notes: Sequence[bed_lanes.BedNote], voice: str,
                       arm_bpm: float, bars: int = BARS) -> np.ndarray:
    # motifs are already grid-aligned + in-scale; just quantize defensively
    q = bed_lanes.quantize_to_grid(motif_notes, bpm=89.1, subdivision=4)
    return bed_lanes.render_loop(q, voice=voice, bars=bars, bpm=arm_bpm, sr=SR)


# ---------------------------------------------------------------------------
# Pack builder (ADR-009 blind pack)
# ---------------------------------------------------------------------------

def _stereo(y: np.ndarray) -> np.ndarray:
    return np.stack([y, y], axis=1) if y.ndim == 1 else y


def build_pack(outdir: Path, items: List[Dict]) -> Tuple[Dict, List[Dict]]:
    """Loudness-match all items, write opaque WAVs + hidden-key manifest."""
    outdir.mkdir(parents=True, exist_ok=True)
    aud = outdir / "audition"
    aud.mkdir(exist_ok=True)
    # gather raw audio
    raws = [it["audio"] for it in items]
    matched = bed_lanes.loudness_match_many(raws, sr=SR, target_lufs=TARGET_LUFS)
    # clip guard
    for i, m in enumerate(matched):
        peak = float(np.abs(m).max())
        if peak > 0.99:
            matched[i] = (m * (0.99 / peak)).astype(np.float32)
    # write opaque files + manifest
    manifest = {"pack": "GATE_C2_bed_lanes", "target_lufs": TARGET_LUFS,
                "lu_tolerance": LU_TOLERANCE, "bars": BARS, "sr": SR,
                "arms": ARMS, "files": []}
    rng = random.Random(20260927)
    order = list(range(len(items)))
    rng.shuffle(order)
    for n, i in enumerate(order, 1):
        it = items[i]
        fname = f"bed_{n:03d}.wav"
        sf.write(str(aud / fname), _stereo(matched[i]), SR)
        manifest["files"].append({
            "file": fname,
            "lane": it["lane"],
            "arm": it["arm"],
            "arm_bpm": it["arm_bpm"],
            "voice": it.get("voice"),
            "source": it.get("source"),
            "key": it["key"],
        })
    return manifest, items


def verify_pack(manifest: Dict, outdir: Path) -> Dict:
    """ADR-009 pre-listening verification: LU spread <=0.3, no clipping."""
    aud = outdir / "audition"
    lufs = []
    peaks = []
    for f in manifest["files"]:
        y, sr = sf.read(str(aud / f["file"]))
        lufs.append(bed_lanes.measure_lufs(y, sr))
        peaks.append(float(np.abs(y).max()))
    spread = max(lufs) - min(lufs) if lufs else 0.0
    verified = {
        "lufs_per_file": [round(x, 2) for x in lufs],
        "lufs_spread": round(spread, 3),
        "lufs_spread_ok": spread <= LU_TOLERANCE,
        "max_peak": round(max(peaks), 4) if peaks else 0.0,
        "no_clipping": all(p <= 1.0 for p in peaks),
        "bijection_ok": len({f["file"] for f in manifest["files"]}) == len(manifest["files"]),
        "passed": False,
    }
    verified["passed"] = (verified["lufs_spread_ok"] and verified["no_clipping"]
                          and verified["bijection_ok"])
    return verified


def write_gate_doc(outdir: Path, manifest: Dict, verified: Dict) -> None:
    """GATE_C2.md — describes the pack WITHOUT revealing which file is which lane."""
    n = len(manifest["files"])
    doc = outdir / "GATE_C2.md"
    text = f"""# GATE C2 — Melodic-Bed Lane Audition Pack

Blind audition for the melodic-bed decision (megaplan W1'). The pack contains
**{n} files**, each an **{BARS}-bar loop** loudness-matched to
{TARGET_LUFS} LUFS (ADR-009: spread <= {LU_TOLERANCE} LU, hidden keys).

## What you are choosing

1. **Lane** — which melodic-bed approach carries the flip (the file identities
   are hidden; the manifest maps file -> lane/arm/voice/key, kept separate so
   the ear decides).
2. **Grid arm** — {ARMS['felt_89']} felt (= 178.2 written) vs {ARMS['triplet_133']}
   (the triplet-fight arm). Each lane is rendered at both.
3. **Hook treatment** — does the sung hook ride with `lead_vocal`, or does
   `backing_vocals` carry a separate hook worth placing? Audition both karaoke
   stems alongside this pack:
   `stems/v2/..._(noreverb)_dereverb_....wav` (lead) and
   `..._(Instrumental)_karaoke_....wav` (backing).

## How to listen

- Loop each file (they are seam-tiled 8-bar loops).
- Compare within a lane across the two grid arms for feel; compare across
  lanes for which bed sits best under the vocal.
- Timbre is intentionally synthetic (pure-code render) — judge the
  composition/contour and how it sits, not the sample quality. If a lane wins
  on a thin timbre, an SF2/FL upgrade is one step (megaplan A24).

## Verification (ran before you listen)

- LUFS spread across all files: **{verified['lufs_spread']} LU**
  (tolerance {LU_TOLERANCE}) -> **{'PASS' if verified['lufs_spread_ok'] else 'FAIL'}**
- Clipping: max peak {verified['max_peak']} -> **{'PASS' if verified['no_clipping'] else 'FAIL'}**
- File/identity bijection: **{'PASS' if verified['bijection_ok'] else 'FAIL'}**
- Overall: **{'PASS' if verified['passed'] else 'FAIL'}**

## Picks needed

- **Lane** (one file, or a progression).
- **Grid arm** (89.1 felt or 133.65).
- **Hook treatment** (lead_vocal vs backing_vocals).

The hidden-key mapping lives in `manifest.json` (do not read before picking).
"""
    doc.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bed", default=str(STEMS / "v2"))
    ap.add_argument("--outdir", default=str(STEMS / "flip_bed_lanes"))
    ap.add_argument("--lane-a", action="store_true", default=True,
                    help="include Lane A (existing chops)")
    args = ap.parse_args(argv)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    midi_dir = outdir / "midi"
    midi_dir.mkdir(exist_ok=True)

    items: List[Dict] = []

    # ---- Lane B: transcribe + cleanup + render ----
    bed = find_bed(Path(args.bed))
    print(f"[bed] {bed.name}")
    region_notes = {}
    for name, s, e in REGIONS:
        notes, events = transcribe_region(bed, s, e, outdir)
        region_notes[name] = notes
        # save raw + cleaned MIDI
        raw_pm = bed_lanes.notes_to_pretty_midi(notes, bpm=89.1)
        bed_lanes.save_midi(midi_dir / f"{name}_raw.mid", raw_pm)
        cleaned = bed_lanes.cleanup(notes, bpm=89.1, subdivision=4,
                                    min_conf=0.4, min_ms=80.0,
                                    root="D", mode="minor")
        cl_pm = bed_lanes.notes_to_pretty_midi(cleaned, bpm=89.1)
        bed_lanes.save_midi(midi_dir / f"{name}_cleaned_Dm.mid", cl_pm)
        print(f"  [B] {name}: {len(notes)} raw -> {len(cleaned)} cleaned notes")

    # Lane B: use the richest region (233-258) for the main loop, plus 63-66
    for region_name, voice in [("region_233_258", "epiano"),
                                ("region_233_258", "pad"),
                                ("region_63_66", "epiano")]:
        if region_name not in region_notes:
            continue
        for arm_name, arm_bpm in ARMS.items():
            audio = render_lane_b_loop(region_notes[region_name], voice,
                                        arm_bpm, root="D")
            items.append({"lane": "B", "arm": arm_name, "arm_bpm": arm_bpm,
                          "voice": voice, "source": region_name, "key": "D minor",
                          "audio": audio})

    # ---- Lane C: hand-programmed motifs ----
    for motif_name, root, mode, motif_notes in LANE_C_MOTIFS:
        for voice in ("epiano", "pad"):
            for arm_name, arm_bpm in ARMS.items():
                audio = render_lane_c_loop(motif_notes, voice, arm_bpm)
                items.append({"lane": "C", "arm": arm_name, "arm_bpm": arm_bpm,
                              "voice": voice, "source": motif_name,
                              "key": f"{root} {mode}", "audio": audio})

    # ---- Lane A: existing chops (reuse) ----
    if args.lane_a:
        for cand in LANE_A_CANDS:
            p = CHOP_AUDITION / cand
            if not p.exists():
                print(f"  [A] missing {p}, skipping")
                continue
            for arm_name, arm_bpm in ARMS.items():
                audio = lane_a_loop(p, arm_bpm)
                items.append({"lane": "A", "arm": arm_name, "arm_bpm": arm_bpm,
                              "voice": "chop", "source": cand,
                              "key": "F# minor", "audio": audio})

    # ---- Build pack ----
    print(f"[pack] {len(items)} items; loudness-matching + writing...")
    manifest, _ = build_pack(outdir, items)
    (outdir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    verified = verify_pack(manifest, outdir)
    (outdir / "verification.json").write_text(
        json.dumps(verified, indent=2, ensure_ascii=False), encoding="utf-8")
    write_gate_doc(outdir, manifest, verified)
    print(f"[pack] wrote {len(items)} files to {outdir/'audition'}")
    print(f"[verify] LU spread {verified['lufs_spread']} LU "
          f"({'PASS' if verified['lufs_spread_ok'] else 'FAIL'}), "
          f"clipping {'PASS' if verified['no_clipping'] else 'FAIL'}, "
          f"overall {'PASS' if verified['passed'] else 'FAIL'}")
    return 0 if verified["passed"] else 2


if __name__ == "__main__":
    sys.exit(main())
