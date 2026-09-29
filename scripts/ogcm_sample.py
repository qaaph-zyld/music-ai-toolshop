"""OGCM Suno-sample builder — GATE S2 (melody-legibility iteration).

GATE S verdict: region_233_258 + G-funk lead is the direction, but the melody
was inaudible — the transcription is bass-dominated (50/95 notes <= MIDI 50)
and the surviving melody notes were ~0.17 s blips. S2 extracts the TOP LINE
(adaptive, register-free), extends notes legato so the line sustains, doubles
it +12 st, and pushes the lead forward in the mix. Variants cover the user's
explicit asks: tempo/timing A/B, D's motif figure as an intro lick, a sparse
maximum-audibility take, and a re-chopped single-take real-audio variant.

Output: ``stems/flip_sample/audition_s2/`` — seamless loops, -16 LUFS matched.

Usage:
    python scripts/ogcm_sample.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from toolshop.flip import arrange, bed_lanes, master, sample_voices as sv  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
STEMS = REPO / "Stemmeca_alatkka" / "stems"
MIDI_DIR = STEMS / "flip_bed_lanes" / "midi"
CHOP_AUD = STEMS / "flip_chops_v2" / "audition"
OUTDIR = STEMS / "flip_sample"
AUD = OUTDIR / "audition_s2"

SR = 44100
TARGET_LUFS = -16.0
LU_TOL = 0.3
TP_CEILING = -1.0
SUBTYPE = "PCM_24"
# real-audio variant: 8-bar F#min chop (audition wav is the chop doubled,
# internal seam baked) -> -4 st lands D minor
CHOP_SRC = CHOP_AUD / "cand_297_8bar_F#min_score0.47.wav"
CHOP_SHIFT_ST = -4.0

REGION = "region_233_258_cleaned_Dm.mid"

# lead-forward mix (the S1 complaint: melody buried under chords/pad)
LANE_GAINS = {"lead": 1.0, "rhodes": 0.32, "pad": 0.22, "sub": 0.65}


def _region_notes(name: str) -> List[bed_lanes.BedNote]:
    return bed_lanes.pretty_midi_to_notes(bed_lanes.load_midi(MIDI_DIR / name))


def _loop_bars(notes: List[bed_lanes.BedNote]) -> int:
    """Even bar count covering the (possibly tempo-scaled) note span."""
    span = max((n.start_s + n.duration_s for n in notes), default=0.0)
    bars = int(math.ceil(span / sv.BAR_S - 1e-9))
    return max(4, bars + (bars % 2))


def _s2_melody(notes: List[bed_lanes.BedNote]) -> List[bed_lanes.BedNote]:
    """The S2 melody path: adaptive top line -> legato -> velocity variance
    (timing stays on the quantized grid) -> +12 double."""
    mel = sv.top_line(notes)
    mel = sv.legato(mel, gap_ms=20.0)
    mel = sv.humanize(mel, timing_ms=0.0, seed=sv.SEED)
    return sv.octave_double(mel, up_st=12, vel_scale=0.4)


def _render_variant(notes: List[bed_lanes.BedNote],
                    intro_lick: Optional[List[bed_lanes.BedNote]] = None,
                    sparse: bool = False) -> np.ndarray:
    """Shared S2 builder: lead voice carries the melody; chords/sub quiet."""
    all_notes = list(notes)
    n_bars = _loop_bars(all_notes)
    if intro_lick:
        all_notes = intro_lick + all_notes
    melody = _s2_melody(all_notes)
    chords = sv.derive_chords([], [], n_bars)  # fallback i-VI-III-VII cycle
    if sparse:
        chords = [c for c in chords if c["bar"] % 2 == 0]
    lanes: Dict[str, np.ndarray] = {
        "lead": sv.render_gfunk_lead(melody, sr=SR),
        "sub": sv.render_sub(sv.bass_root_notes(chords, velocity=0.7), sr=SR),
    }
    if not sparse:
        lanes["rhodes"] = sv.render_rhodes(sv.chord_bednotes(chords), sr=SR)
        lanes["pad"] = sv.render_warm_pad(
            sv.chord_bednotes(chords, velocity=0.4), sr=SR)
    else:
        lanes["rhodes"] = sv.render_rhodes(sv.chord_bednotes(chords), sr=SR)
    lanes = {k: a * LANE_GAINS.get(k, 1.0) for k, a in lanes.items()}
    bus = sv.west_coast_chain(lanes, sr=SR)
    return sv.fit_loop(bus, SR, n_bars * sv.BAR_S)


def _v_native() -> np.ndarray:
    return _render_variant(_region_notes(REGION))


def _v_fast() -> np.ndarray:
    return _render_variant(sv.tempo_scale(_region_notes(REGION), 0.95))


def _v_swing() -> np.ndarray:
    six = sv.BAR_S / 16.0
    return _render_variant(sv.swing(_region_notes(REGION), six, amt=0.15))


def _v_motif_intro() -> np.ndarray:
    lick = [bed_lanes.BedNote(n.start_s, n.end_s, n.note + 12, n.velocity)
            for n in arrange.motif_notes("motif_dm_1")]
    region = _region_notes(REGION)
    off = 2 * sv.BAR_S  # lick plays the first 2 bars; melody shifted after
    shifted = [bed_lanes.BedNote(n.start_s + off, n.end_s + off, n.note,
                                 n.velocity) for n in region]
    return _render_variant(shifted, intro_lick=lick)


def _v_sparse() -> np.ndarray:
    return _render_variant(_region_notes(REGION), sparse=True)


def _v_real_chop() -> np.ndarray:
    """Variant E (labeled): cand_297 — 8-bar F#min chop, audition wav is the
    chop already doubled (~38.6 s, internal seam baked) -> -4 st -> Dm."""
    from pedalboard import (Compressor, Gain, LadderFilter, Pedalboard,
                            PitchShift, Reverb)

    y, sr = sf.read(str(CHOP_SRC), always_2d=True)
    if sr != SR:
        import librosa
        y = librosa.resample(y.T, orig_sr=sr, target_sr=SR).T
    if y.shape[1] == 1:
        y = np.repeat(y, 2, axis=1)
    y = Pedalboard([PitchShift(semitones=CHOP_SHIFT_ST)])(
        np.ascontiguousarray(y.T), SR).T.astype(np.float32)
    chain = Pedalboard([
        LadderFilter(mode=LadderFilter.Mode.LPF24, cutoff_hz=4500.0,
                     resonance=0.1, drive=1.3),
        Reverb(room_size=0.4, damping=0.65, wet_level=0.2, dry_level=1.0,
               width=1.0),
        Compressor(threshold_db=-14.0, ratio=2.0, attack_ms=8.0,
                   release_ms=100.0),
        Gain(gain_db=0.0)])
    wet = chain(np.ascontiguousarray(y.T), SR).T
    # loop at the file's own length — it is already a doubled loop internally
    return sv.fit_loop(wet.astype(np.float32), SR, wet.shape[0] / SR)


def _to_target(audio: np.ndarray, target_lufs: float) -> np.ndarray:
    cur = master.integrated_lufs(audio, SR)
    gain = target_lufs - cur if np.isfinite(cur) else 0.0
    out = audio * np.float32(10.0 ** (gain / 20.0))
    tp = master.true_peak_dbfs(out, SR)
    if tp > TP_CEILING:
        out = out * np.float32(10.0 ** ((TP_CEILING - tp) / 20.0))
    return out.astype(np.float32)


VARIANTS = {
    "s2_01_B_native": _v_native,
    "s2_02_B_fast": _v_fast,
    "s2_03_B_swing": _v_swing,
    "s2_04_B_motif_intro": _v_motif_intro,
    "s2_05_B_sparse": _v_sparse,
    "s2_06_E_real8_REF": _v_real_chop,
}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    AUD.mkdir(parents=True, exist_ok=True)
    manifest: Dict = {"pack": "GATE_S2_suno_sample", "sr": SR,
                      "target_lufs": TARGET_LUFS, "lu_tol": LU_TOL,
                      "tp_ceiling": TP_CEILING, "files": []}
    for name, build in VARIANTS.items():
        print(f"[render] {name} ...", flush=True)
        audio = _to_target(build(), TARGET_LUFS)
        peak = float(np.abs(audio).max())
        out = AUD / f"{name}.wav"
        sf.write(str(out), audio, SR, subtype=SUBTYPE)
        rec = {"file": out.name, "duration_s": round(audio.shape[0] / SR, 3),
               "sample_peak": round(peak, 4)}
        manifest["files"].append(rec)
        print(f"         {audio.shape[0]/SR:.1f}s peak={peak:.3f}")

    lufs_vals, ok_tp, ok_clip, ok_seam = [], True, True, {}
    for rec in manifest["files"]:
        y, _ = sf.read(str(AUD / rec["file"]), always_2d=True)
        rec["lufs"] = round(master.integrated_lufs(y, SR), 2)
        rec["true_peak_dbtp"] = round(master.true_peak_dbfs(y, SR), 2)
        lufs_vals.append(rec["lufs"])
        ok_tp &= rec["true_peak_dbtp"] <= TP_CEILING + 0.05
        ok_clip &= rec["sample_peak"] <= 0.999
        ok_seam[rec["file"]] = float(np.abs(y[-1] - y[0]).max())
    spread = max(lufs_vals) - min(lufs_vals)
    verification = {"per_file_lufs": {r["file"]: r["lufs"] for r in manifest["files"]},
                    "spread_lu": round(spread, 3),
                    "lufs_ok": bool(spread <= LU_TOL),
                    "tp_ok": bool(ok_tp), "clips_ok": bool(ok_clip),
                    "seam_boundary_max_absdiff": ok_seam}
    verification["passed"] = bool(
        verification["lufs_ok"] and ok_tp and ok_clip)
    (AUD / "manifest.json").write_text(json.dumps(manifest, indent=2),
                                       encoding="utf-8")
    (AUD / "verification.json").write_text(json.dumps(verification, indent=2),
                                           encoding="utf-8")
    print(json.dumps({k: v for k, v in verification.items()
                      if k != "seam_boundary_max_absdiff"}, indent=2))
    return 0 if verification["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
