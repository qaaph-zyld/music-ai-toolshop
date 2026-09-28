#!/usr/bin/env python
"""OGCM flip W2+W3 render driver — dual-grid beat renders (megaplan m3).

GATE C2 pick (user audition 2026-09-28, hidden-manifest resolution):
  arm felt_89     (178.2 written / 89.1 felt): Lane B interpolated bed —
                  region_63_66_cleaned_Dm.mid, epiano voice, D minor.
  arm triplet_133 (133.65 written):            Lane C programmed motifs as
                  section alternates — motif_dm_1 (pad, Dm) verses +
                  motif_csm_1 (epiano, C#m) hooks.
  Lane A (chops) is NOT used. Hook sections reserve space for the
  backing-vocal-driven hook (vocal placement is wave m4's job).

Per arm: arrange.build_plan -> plan_drum_events (true 2-bar cycle) ->
plan_bass (m3/P4 slides, 90-200 ms glide, landing on kicks) ->
build_bed_lane -> assemble.render_beat -> verify_render evidence JSON.

Outputs (gitignored data): stems/flip_renders/beat_<arm>.wav +
beat_<arm>_events.json + renders_manifest.json. Also materialises the
picked motif MIDIs into stems/flip_bed_lanes/midi/ and re-runs the A29
kit audit -> stems/flip_kit/kit_audit.json.

Usage:
  python scripts/ogcm_render_arms.py [--sr 44100] [--arm felt_89|triplet_133]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from toolshop.flip import arrange, bed_lanes, drums  # noqa: E402

STEMS = REPO / "Stemmeca_alatkka" / "stems"
KIT = STEMS / "flip_kit"
MIDI_DIR = STEMS / "flip_bed_lanes" / "midi"
OUT = STEMS / "flip_renders"
LANE_B_MIDI = MIDI_DIR / "region_63_66_cleaned_Dm.mid"
SR = 44100


def _stereo(y: np.ndarray) -> np.ndarray:
    return np.stack([y, y], axis=1) if y.ndim == 1 else y


def materialise_motif_midis() -> list:
    """Write the picked Lane-C motifs into the midi/ dir (Lane C sources
    were spike-script note lists; the manifest names them as MIDI)."""
    written = []
    MIDI_DIR.mkdir(parents=True, exist_ok=True)
    for name in ("motif_dm_1", "motif_csm_1"):
        p = MIDI_DIR / f"{name}.mid"
        arrange.write_motif_midi(p, name)
        written.append(str(p))
    return written


def build_bed_segments(arm: str, sr: int) -> dict:
    """Render the GATE-C2-picked bed sources to audio segments (native
    felt timing @89.1 — arrange tiles them across written-bar spans)."""
    if arm == "felt_89":
        notes = bed_lanes.pretty_midi_to_notes(bed_lanes.load_midi(LANE_B_MIDI))
        seg = bed_lanes.render_loop(notes, "epiano", bars=4,
                                  bpm=arrange.FELT_BPM, sr=sr)
        return {"region_63_66": seg}
    if arm == "triplet_133":
        segs = {}
        for name in ("motif_dm_1", "motif_csm_1"):
            meta = arrange.motif_meta(name)
            notes = bed_lanes.quantize_to_grid(
                arrange.motif_notes(name), bpm=arrange.FELT_BPM, subdivision=4)
            segs[name] = bed_lanes.render_loop(
                notes, meta["voice"], bars=meta["felt_bars"],
                bpm=arrange.FELT_BPM, sr=sr)
        return segs
    raise ValueError(f"unknown arm {arm!r}")


def render_arm(arm: str, sr: int = SR) -> dict:
    plan = arrange.build_plan(arm)
    manifest = json.loads((KIT / "kit_manifest.json").read_text(encoding="utf-8"))
    kit = drums.load_kit_buffers(KIT, manifest)
    segments = build_bed_segments(arm, sr)
    res = arrange.render_arm(plan, segments, kit, sr=sr)

    wav = OUT / f"beat_{arm}.wav"
    ev_json = OUT / f"beat_{arm}_events.json"
    sf.write(str(wav), _stereo(res["audio"]), sr)
    body = dict(res["events"])
    body["verification"] = res["verification"]
    ev_json.write_text(json.dumps(body, indent=2), encoding="utf-8")
    return {
        "arm": arm, "wav": wav.name, "events_json": ev_json.name,
        "duration_s": round(res["audio"].size / sr, 3),
        "verification": res["verification"],
        "warnings": res["warnings"],
    }


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--sr", type=int, default=SR)
    ap.add_argument("--arm", choices=list(arrange.ARM_BPM), default=None,
                    help="render one arm only (default: both)")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)

    # Task 1 evidence: kit audit (A29) recorded next to the kit.
    kit_manifest = json.loads((KIT / "kit_manifest.json").read_text(encoding="utf-8"))
    audit = drums.audit_kit_manifest(kit_manifest, kit_dir=KIT)
    (KIT / "kit_audit.json").write_text(json.dumps(audit, indent=2),
                                        encoding="utf-8")
    print("kit audit:", {p: d["verdict"] for p, d in audit["pieces"].items()},
          "| weak:", audit["weak_pieces"], "| ok:", audit["ok"])

    written = materialise_motif_midis()
    print("motif MIDIs:", written)

    arms = [args.arm] if args.arm else list(arrange.ARM_BPM)
    results = [render_arm(a, sr=args.sr) for a in arms]
    manifest = {
        "pack": "ogcm_flip_m3_dual_grid",
        "gate_c2_pick": {
            "felt_89": "Lane B interpolated bed (region_63_66_cleaned_Dm.mid, epiano, D minor)",
            "triplet_133": "Lane C programmed motifs (motif_dm_1 pad Dm verses / motif_csm_1 epiano C#m hooks)",
            "lane_a": "not used",
            "hook": "backing_vocals-driven hook space reserved (m4 places vocals)",
        },
        "kit_audit": "flip_kit/kit_audit.json",
        "renders": results,
    }
    (OUT / "renders_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")
    for r in results:
        v = r["verification"]
        print(f"{r['arm']}: {r['duration_s']}s peak={v['peak']} "
              f"clips={v['clip_count']} grid={v['grid_adherence']['pass']} "
              f"mono120={v['mono_below_120hz']['pass']} PASS={v['pass']}")
        for w in r["warnings"]:
            print("  warning:", w)
    return 0 if all(r["verification"]["pass"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
