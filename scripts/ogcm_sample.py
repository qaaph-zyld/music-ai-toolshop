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
from typing import Callable, Dict, List, Optional, Tuple

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
# S4: RAW native-key region (F# minor) — transposed, never scale-snapped.
# Root cause of the S3 ear-test reject: region_54_67_cleaned_Dm.mid had been
# scale_locked D-minor on F#m material, rewriting every riff interval.
S4_REGION = "region_54_67_raw.mid"
S4_CHOP = "ref_slice_54_67.wav"                  # the real 54-67 s slice
S4_TRANSPOSE_ST = -4                             # F#m -> Dm exactly
S4_MIN_MIDI = 55                                 # riff register floor

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
               n_bars: int = S3_BARS,
               chords: Optional[List[dict]] = None) -> np.ndarray:
    """Shared S3/S4 builder: motif lead @1.0 + quiet chords + sub, folded
    into a seamless n_bars loop. ``chords=None`` keeps the S3 fallback
    i-VI-III-VII cycle; S4 passes chords derived from the segment's bass."""
    if chords is None:
        chords = sv.derive_chords([], [], n_bars)  # fallback i-VI-III-VII cycle
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


# ---------------------------------------------------------------------------
# GATE S4 — raw native-key riff, transposed (never snapped) to D minor
# ---------------------------------------------------------------------------

_PC_OF_NAME = {"C": 0, "C#": 1, "DB": 1, "D": 2, "D#": 3, "EB": 3, "E": 4,
               "F": 5, "F#": 6, "GB": 6, "G": 7, "G#": 8, "AB": 8, "A": 9,
               "A#": 10, "BB": 10, "B": 11}


def _transpose_chord_name(name: str, st: int) -> str:
    """'Bbmaj7' shifted -4 -> 'Gmaj7'. Root token transposed, suffix kept."""
    i = 1
    if len(name) > 1 and name[1] in "#b":
        i = 2
    root, suffix = name[:i].upper(), name[i:]
    pc = (_PC_OF_NAME[root] + st) % 12
    return sv.PC_NAMES[pc] + suffix


def _transpose_chords(chords: List[dict], st: int) -> List[dict]:
    """Whole chord dicts shifted by `st` (voicings + bass root)."""
    return [{"bar": c["bar"], "root_pc": (c["root_pc"] + st) % 12,
             "name": _transpose_chord_name(c["name"], st),
             "notes": [m + st for m in c["notes"]]} for c in chords]


def _s4_variants(region: str, chop: str, shift: float, transpose_st: int
                 ) -> Tuple[Dict[str, Callable[[], np.ndarray]], Dict]:
    """GATE S4: riff from the RAW native-key region, transposed to Dm.

    riff is extracted in F# minor (no scale lock), shifted `transpose_st`
    (-4) so it lands exactly on D natural minor. Chords are derived from the
    segment's own bass inside the winning cell (transposed the same way).
    `s4_04` shifts every lane +4 back to the native F# minor for a
    direct A/B against instrumental.wav.
    """
    raw = _region_notes(region)
    tonic_pc, mode, key_r = sv.estimate_key(raw)
    riff_native, cell_t0 = sv.extract_riff(raw, min_midi=S4_MIN_MIDI)
    if not riff_native:
        raise SystemExit(f"[s4] extract_riff returned no notes on {region}")
    cell_s = 2.0 * sv.BAR_S
    riff_dm = sv.transpose(riff_native, transpose_st)
    n_bars = S3_BARS
    reps = n_bars // 2

    # print the riff BEFORE rendering — the human sanity check of record
    print(f"[s4] source key estimate: {sv.PC_NAMES[tonic_pc]} {mode} "
          f"(r={key_r:+.3f})")
    print(f"[s4] winning cell t0={cell_t0:.2f}s cell_s={cell_s:.2f}s "
          f"-> riff {len(riff_dm)} notes on 16th grid")
    print("[s4] riff (native F#m -> Dm):")
    for nn, nd in zip(riff_native, riff_dm):
        print(f"   on={nd.start_s:5.2f}s dur={nd.duration_s:4.2f}s "
              f"{sv.note_name(nn.note):>4s} ({nn.note:2d}) -> "
              f"{sv.note_name(nd.note):>4s} ({nd.note:2d})")

    # chords: raw bass below the floor inside the winning cell, transposed,
    # tiled to the loop length, derived per bar (empty bars -> fallback)
    bass_cell = [bed_lanes.BedNote(n.start_s - cell_t0, n.end_s - cell_t0,
                                   n.note, n.velocity)
                 for n in raw
                 if n.note < S4_MIN_MIDI
                 and cell_t0 <= n.start_s < cell_t0 + cell_s]
    bass_dm = sv.tile_motif(sv.transpose(bass_cell, transpose_st),
                            cell_s, reps)
    chords = sv.derive_chords(bass_dm, [], n_bars)
    chords_native = _transpose_chords(chords, -transpose_st)
    print("[s4] chords per bar (Dm): "
          + " ".join(c["name"] for c in chords))
    print("[s4] chords per bar (native F#m, +4): "
          + " ".join(c["name"] for c in chords_native))

    tiled = sv.tile_motif(riff_dm, cell_s, reps)
    octaved = sv.octave_double(tiled, up_st=12, vel_scale=0.35)
    tiled_native = sv.tile_motif(riff_native, cell_s, reps)
    stats = sv.riff_stats(riff_dm, cell_s)
    snapped = sum(1 for n in riff_dm if n.note % 12 not in sv.D_MINOR_PCS)
    print(f"[s4] riff_stats={stats} snapped_notes={snapped}")

    meta = {
        "region": region, "chop_ref": chop, "chop_shift_st": shift,
        "transpose_st": transpose_st,
        "source_key": {"tonic_pc": tonic_pc,
                       "tonic": sv.PC_NAMES[tonic_pc],
                       "mode": mode, "r": round(key_r, 4)},
        "cell_t0_s": round(cell_t0, 4), "cell_s": round(cell_s, 4),
        "riff": [{"i": i,
                  "start_s": round(nd.start_s, 4),
                  "dur_s": round(nd.duration_s, 4),
                  "midi_dm": nd.note, "name_dm": sv.note_name(nd.note),
                  "midi_native": nn.note,
                  "name_native": sv.note_name(nn.note)}
                 for i, (nn, nd) in enumerate(zip(riff_native, riff_dm))],
        "riff_stats": stats,
        "chords_per_bar": [c["name"] for c in chords],
        "chords_per_bar_native": [c["name"] for c in chords_native],
        "snapped_notes": snapped,
    }
    variants = {
        "s4_01_riff_sine": lambda: _render_s3(tiled, sv.render_simple_lead,
                                              chords=chords),
        "s4_02_riff_ep": lambda: _render_s3(tiled, sv.render_rhodes,
                                            chords=chords),
        "s4_03_riff_oct": lambda: _render_s3(octaved, sv.render_simple_lead,
                                             chords=chords),
        "s4_04_riff_native_Fsm": lambda: _render_s3(
            tiled_native, sv.render_simple_lead, chords=chords_native),
        "s4_05_chop_REF": lambda: _real_chop(chop, shift),
    }
    return variants, meta


def main(argv: Optional[List[str]] = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(prog="ogcm_sample",
                                description="OGCM Suno-sample builder (S3/S4).")
    p.add_argument("--pack", choices=("s2", "s3", "s4"), default="s3")
    p.add_argument("--region", default=None,
                   help="midi file under stems/flip_bed_lanes/midi "
                        "(default: per-pack region)")
    p.add_argument("--chop", default=None,
                   help="real-audio reference chop under flip_chops_v2/audition")
    p.add_argument("--shift", type=float, default=CHOP_SHIFT_ST,
                   help="semitones to shift the chop into D minor")
    p.add_argument("--transpose", type=int, default=S4_TRANSPOSE_ST,
                   help="s4: semitones to shift the riff (default -4, F#m->Dm)")
    args = p.parse_args(argv)

    region = args.region or (S4_REGION if args.pack == "s4" else S3_REGION)
    chop = args.chop or (S4_CHOP if args.pack == "s4" else S3_CHOP)

    aud = OUTDIR / f"audition_{args.pack}"
    aud.mkdir(parents=True, exist_ok=True)
    s4_meta: Optional[Dict] = None
    if args.pack == "s2":
        variants = dict(S2_VARIANTS)
    elif args.pack == "s4":
        variants, s4_meta = _s4_variants(region, chop, args.shift,
                                         args.transpose)
    else:
        variants = _s3_variants(region, chop, args.shift)
    manifest: Dict = {"pack": f"GATE_{args.pack.upper()}_suno_sample",
                      "sr": SR, "target_lufs": TARGET_LUFS, "lu_tol": LU_TOL,
                      "tp_ceiling": TP_CEILING, "files": []}
    if args.pack == "s3":
        manifest["region"] = region
        manifest["chop_ref"] = chop
        manifest["chop_shift_st"] = args.shift
    if s4_meta is not None:
        manifest["s4"] = s4_meta
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
