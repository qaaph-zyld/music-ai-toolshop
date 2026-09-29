"""OGCM Suno-sample builder — GATE S3 (simple recognizable motif).

S3 distills the picked segment's transcription into a short canonical motif
(most-repeated 2-bar cell, simplified to <=8 grid-quantized Dm notes), tiles
it across an 8-bar loop, and voices it on plain tones over quiet Dm chords +
sub. Variants: sine lead, EP lead, sine+octave, A/A' call-response, and a
labeled real-audio chop of the picked segment for comparison.

Output: ``stems/flip_sample/audition_s3/`` — seamless loops, -16 LUFS matched.
(--pack s2 rebuilds the previous melody-legibility pack into audition_s2.)

Usage:
    python scripts/ogcm_sample.py [--pack s3] [--region region_63_66_cleaned_Dm.mid]
        [--chop cand_317_8bar_F#min_score0.47.wav] [--shift -4]
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from toolshop.flip import arrange, bed_lanes, master, sample_voices as sv  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
STEMS = REPO / "Stemmeca_alatkka" / "stems"
MIDI_DIR = STEMS / "flip_bed_lanes" / "midi"
CHOP_AUD = STEMS / "flip_chops_v2" / "audition"
OUTDIR = STEMS / "flip_sample"

SR = 44100
TARGET_LUFS = -16.0
LU_TOL = 0.3
TP_CEILING = -1.0
SUBTYPE = "PCM_24"
# real-audio variants: audition wavs are chops already doubled (internal
# seam baked); F#min -> -4 st lands D minor
S2_CHOP = "cand_297_8bar_F#min_score0.47.wav"    # intro window ref (S2)
S3_CHOP = "cand_317_8bar_F#min_score0.47.wav"    # riff 63-73s ref (S3 default)
CHOP_SHIFT_ST = -4.0

S2_REGION = "region_233_258_cleaned_Dm.mid"
S3_REGION = "region_63_66_cleaned_Dm.mid"        # riff: best score, 7x repeated
S3_BARS = 8

# lead-forward mix (the S1 complaint: melody buried under chords/pad)
LANE_GAINS = {"lead": 1.0, "rhodes": 0.32, "pad": 0.22, "sub": 0.65}
S3_GAINS = {"lead": 1.0, "rhodes": 0.30, "sub": 0.60}


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
    return _render_variant(_region_notes(S2_REGION))


def _v_fast() -> np.ndarray:
    return _render_variant(sv.tempo_scale(_region_notes(S2_REGION), 0.95))


def _v_swing() -> np.ndarray:
    six = sv.BAR_S / 16.0
    return _render_variant(sv.swing(_region_notes(S2_REGION), six, amt=0.15))


def _v_motif_intro() -> np.ndarray:
    lick = [bed_lanes.BedNote(n.start_s, n.end_s, n.note + 12, n.velocity)
            for n in arrange.motif_notes("motif_dm_1")]
    region = _region_notes(S2_REGION)
    off = 2 * sv.BAR_S  # lick plays the first 2 bars; melody shifted after
    shifted = [bed_lanes.BedNote(n.start_s + off, n.end_s + off, n.note,
                                 n.velocity) for n in region]
    return _render_variant(shifted, intro_lick=lick)


def _v_sparse() -> np.ndarray:
    return _render_variant(_region_notes(S2_REGION), sparse=True)


def _real_chop(chop_name: str, shift_st: float) -> np.ndarray:
    """Labeled real-audio reference: the picked segment's audition chop
    (already a doubled loop internally), pitch-shifted into D minor."""
    from pedalboard import (Compressor, Gain, LadderFilter, Pedalboard,
                            PitchShift, Reverb)

    y, sr = sf.read(str(CHOP_AUD / chop_name), always_2d=True)
    if sr != SR:
        import librosa
        y = librosa.resample(y.T, orig_sr=sr, target_sr=SR).T
    if y.shape[1] == 1:
        y = np.repeat(y, 2, axis=1)
    y = Pedalboard([PitchShift(semitones=shift_st)])(
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


def _v_s2_chop() -> np.ndarray:
    return _real_chop(S2_CHOP, CHOP_SHIFT_ST)


S2_VARIANTS = {
    "s2_01_B_native": _v_native,
    "s2_02_B_fast": _v_fast,
    "s2_03_B_swing": _v_swing,
    "s2_04_B_motif_intro": _v_motif_intro,
    "s2_05_B_sparse": _v_sparse,
    "s2_06_E_real8_REF": _v_s2_chop,
}


# ---------------------------------------------------------------------------
# GATE S3 — distilled motif on plain tones
# ---------------------------------------------------------------------------

def _render_s3(melody: List[bed_lanes.BedNote],
               voice_fn: Callable[..., np.ndarray],
               n_bars: int = S3_BARS) -> np.ndarray:
    """Shared S3 builder: motif lead @1.0 + quiet Dm chords + sub, folded
    into a seamless n_bars loop."""
    chords = sv.derive_chords([], [], n_bars)      # fallback i-VI-III-VII cycle
    lanes: Dict[str, np.ndarray] = {
        "lead": voice_fn(melody, sr=SR),
        "rhodes": sv.render_rhodes(sv.chord_bednotes(chords, velocity=0.45),
                                   sr=SR),
        "sub": sv.render_sub(sv.bass_root_notes(chords, velocity=0.7), sr=SR),
    }
    lanes = {k: a * S3_GAINS.get(k, 1.0) for k, a in lanes.items()}
    return sv.fit_loop(sv.west_coast_chain(lanes, sr=SR), SR, n_bars * sv.BAR_S)


def _aa_form(motif: List[bed_lanes.BedNote], motif_s: float
             ) -> List[bed_lanes.BedNote]:
    """A A' A A': the motif alternating with its answer response."""
    ans = sv.answer_motif(motif)
    out: List[bed_lanes.BedNote] = []
    for k, m in enumerate((motif, ans, motif, ans)):
        off = k * motif_s
        out.extend(bed_lanes.BedNote(n.start_s + off, n.end_s + off, n.note,
                                     n.velocity) for n in m)
    out.sort(key=lambda n: n.start_s)
    return out


def _s3_variants(region: str, chop: str, shift: float
                 ) -> Dict[str, Callable[[], np.ndarray]]:
    notes = _region_notes(region)
    motif = sv.extract_motif(notes, motif_bars=2, max_notes=8)
    motif_s = 2.0 * sv.BAR_S
    tiled = sv.tile_motif(motif, motif_s, 4)
    octaved = sv.octave_double(tiled, up_st=12, vel_scale=0.35)
    return {
        "s3_01_motif_sine": lambda: _render_s3(tiled, sv.render_simple_lead),
        "s3_02_motif_ep": lambda: _render_s3(tiled, sv.render_rhodes),
        "s3_03_motif_oct": lambda: _render_s3(octaved, sv.render_simple_lead),
        "s3_04_motif_answer": lambda: _render_s3(_aa_form(motif, motif_s),
                                                 sv.render_simple_lead),
        "s3_05_chop_REF": lambda: _real_chop(chop, shift),
    }


def main(argv: Optional[List[str]] = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(prog="ogcm_sample",
                                description="OGCM Suno-sample builder (GATE S3).")
    p.add_argument("--pack", choices=("s2", "s3"), default="s3")
    p.add_argument("--region", default=S3_REGION,
                   help="midi file under stems/flip_bed_lanes/midi")
    p.add_argument("--chop", default=S3_CHOP,
                   help="real-audio reference chop under flip_chops_v2/audition")
    p.add_argument("--shift", type=float, default=CHOP_SHIFT_ST,
                   help="semitones to shift the chop into D minor")
    args = p.parse_args(argv)

    aud = OUTDIR / f"audition_{args.pack}"
    aud.mkdir(parents=True, exist_ok=True)
    variants = (S2_VARIANTS if args.pack == "s2"
                else _s3_variants(args.region, args.chop, args.shift))
    manifest: Dict = {"pack": f"GATE_{args.pack.upper()}_suno_sample",
                      "sr": SR, "target_lufs": TARGET_LUFS, "lu_tol": LU_TOL,
                      "tp_ceiling": TP_CEILING, "files": []}
    if args.pack == "s3":
        manifest["region"] = args.region
        manifest["chop_ref"] = args.chop
        manifest["chop_shift_st"] = args.shift
    for name, build in variants.items():
        print(f"[render] {name} ...", flush=True)
        audio = _to_target(build(), TARGET_LUFS)
        peak = float(np.abs(audio).max())
        out = aud / f"{name}.wav"
        sf.write(str(out), audio, SR, subtype=SUBTYPE)
        rec = {"file": out.name, "duration_s": round(audio.shape[0] / SR, 3),
               "sample_peak": round(peak, 4)}
        manifest["files"].append(rec)
        print(f"         {audio.shape[0]/SR:.1f}s peak={peak:.3f}")

    lufs_vals, ok_tp, ok_clip, ok_seam = [], True, True, {}
    for rec in manifest["files"]:
        y, _ = sf.read(str(aud / rec["file"]), always_2d=True)
        rec["lufs"] = round(master.integrated_lufs(y, SR), 2)
        rec["true_peak_dbtp"] = round(master.true_peak_dbfs(y, SR), 2)
        lufs_vals.append(rec["lufs"])
        ok_tp &= rec["true_peak_dbtp"] <= TP_CEILING + 0.05
        ok_clip &= rec["sample_peak"] <= 0.999
        ok_seam[rec["file"]] = float(np.abs(y[-1] - y[0]).max())
    spread = max(lufs_vals) - min(lufs_vals)
    passed = bool(spread <= LU_TOL and ok_tp and ok_clip)
    verification = {"pass": passed, "passed": passed,
                    "per_file_lufs": {r["file"]: r["lufs"] for r in manifest["files"]},
                    "spread_lu": round(spread, 3),
                    "lufs_ok": bool(spread <= LU_TOL),
                    "tp_ok": bool(ok_tp), "clips_ok": bool(ok_clip),
                    "seam_boundary_max_absdiff": ok_seam}
    (aud / "manifest.json").write_text(json.dumps(manifest, indent=2),
                                       encoding="utf-8")
    (aud / "verification.json").write_text(json.dumps(verification, indent=2),
                                           encoding="utf-8")
    print(json.dumps({k: v for k, v in verification.items()
                      if k != "seam_boundary_max_absdiff"}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
