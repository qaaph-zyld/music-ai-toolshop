"""OGCM Suno-sample builder — post-GATE-F pivot deliverable.

Builds polished west-coast melodic SAMPLE loops from melodies transcribed off
the real OGCM instrumental (Basic Pitch regions cleaned to D minor), voiced
through ``toolshop.flip.sample_voices`` (Rhodes EP / warm pad / G-funk
portamento lead / sine sub) with per-lane pedalboard FX. Output is a GATE-S
audition pack under ``stems/flip_sample/`` — seamless loops, loudness-matched,
with an index.html player page. One labeled variant renders a REAL chopped
slice of the record pitched to Dm, so the synth-vs-literal-sample question is
settled by ear.

Usage:
    python scripts/ogcm_sample.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Dict, List

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from toolshop.flip import arrange, bed_lanes, master, sample_voices as sv  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
STEMS = REPO / "Stemmeca_alatkka" / "stems"
MIDI_DIR = STEMS / "flip_bed_lanes" / "midi"
CHOP_AUD = STEMS / "flip_chops_v2" / "audition"
OUTDIR = STEMS / "flip_sample"
AUD = OUTDIR / "audition"

SR = 44100
TARGET_LUFS = -16.0
LU_TOL = 0.3
TP_CEILING = -1.0
SUBTYPE = "PCM_24"
# real-audio variant: F#min 4-bar chop -> -4 st lands D minor
CHOP_SRC = CHOP_AUD / "cand_220_4bar_F#min_score0.58.wav"
CHOP_SHIFT_ST = -4.0


def _region_notes(name: str) -> List[bed_lanes.BedNote]:
    pm = bed_lanes.load_midi(MIDI_DIR / name)
    return bed_lanes.pretty_midi_to_notes(pm)


def _loop_bars(notes: List[bed_lanes.BedNote]) -> int:
    """Even bar count covering the note span (>=4)."""
    span = max((n.start_s + n.duration_s for n in notes), default=0.0)
    bars = int(math.ceil(span / sv.BAR_S - 1e-9))
    return max(4, bars + (bars % 2))


def _render_region_variant(midi_name: str, lead_voice: str,
                           chord_voice: str = "rhodes",
                           add_pad: bool = False,
                           seed: int = sv.SEED) -> np.ndarray:
    """Shared builder for the transcription variants."""
    notes = _region_notes(midi_name)
    n_bars = _loop_bars(notes)
    bass, melody = sv.split_registers(notes)
    chords = sv.derive_chords(bass, melody, n_bars)
    melody = sv.humanize(melody, seed=seed)

    chord_notes = sv.chord_bednotes(chords)
    sub_notes = sv.bass_root_notes(chords)
    # real transcription bass joins the sub lane, octave-folded into 24..42
    for b in bass:
        bn = b.note
        while bn > 42:
            bn -= 12
        while bn < 24:
            bn += 12
        sub_notes.append(bed_lanes.BedNote(b.start_s, b.end_s, bn, 0.7))

    lanes: Dict[str, np.ndarray] = {
        "sub": sv.render_sub(sub_notes, sr=SR),
    }
    # chord voice selectable: "pad" puts the harmony on the warm pad lane
    chord_lane = "pad" if chord_voice == "pad" else "rhodes"
    lanes[chord_lane] = (
        sv.render_warm_pad(chord_notes, sr=SR) if chord_lane == "pad"
        else sv.render_rhodes(chord_notes, sr=SR))
    if lead_voice == "gfunk":
        lanes["lead"] = sv.render_gfunk_lead(melody, sr=SR)
    else:
        lanes["rhodes"] = lanes.get("rhodes", np.zeros((0, 2), np.float32))
        mel_r = sv.render_rhodes(melody, sr=SR)
        n = max(lanes["rhodes"].shape[0], mel_r.shape[0])
        acc = np.zeros((n, 2), dtype=np.float32)
        acc[: lanes["rhodes"].shape[0]] += lanes["rhodes"]
        acc[: mel_r.shape[0]] += mel_r
        lanes["rhodes"] = acc
    if add_pad and "pad" not in lanes:
        lanes["pad"] = sv.render_warm_pad(chord_notes, sr=SR)
    bus = sv.west_coast_chain(lanes, sr=SR)
    return sv.fit_loop(bus, SR, n_bars * sv.BAR_S)


def _render_motif_variant(seed: int = sv.SEED) -> np.ndarray:
    """Variant D: programmed motif hook over the canonical i-VI-III-VII cycle.

    NOTE: arrange's motifs span ~2 beats (8 sixteenths) despite their
    'felt_bars: 2' metadata — treat them as short figures; we restate the Dm
    figure on each bar's beat 1 and harmonize with the fallback cycle.
    """
    motif = arrange.motif_notes("motif_dm_1")
    n_bars = 8
    melody: List[bed_lanes.BedNote] = []
    # restate the ~2-beat figure on every bar downbeat, +8va every other bar
    for bar in range(n_bars):
        off = bar * sv.BAR_S
        up = 12 if bar % 2 else 0
        for n in motif:
            melody.append(bed_lanes.BedNote(n.start_s + off, n.end_s + off,
                                            n.note + up, n.velocity))
    chords = sv.derive_chords([], [], n_bars)  # -> fallback cycle i-VI-III-VII
    lanes = {
        "rhodes": sv.render_rhodes(sv.chord_bednotes(chords), sr=SR),
        "pad": sv.render_warm_pad(sv.chord_bednotes(chords, velocity=0.4),
                                  sr=SR),
        "lead": sv.render_gfunk_lead(sv.humanize(melody, seed=seed), sr=SR),
        "sub": sv.render_sub(sv.bass_root_notes(chords), sr=SR),
    }
    bus = sv.west_coast_chain(lanes, sr=SR)
    return sv.fit_loop(bus, SR, n_bars * sv.BAR_S)


def _xadd_tile(x: np.ndarray, reps: int, overlap_s: float, sr: int
               ) -> np.ndarray:
    """Tile a buffer `reps` times with equal-power overlap-add joins."""
    ov = int(overlap_s * sr)
    out = x.astype(np.float64).copy()
    for _ in range(reps - 1):
        head = out[-ov:]
        fade_out = np.sqrt(np.linspace(1.0, 0.0, ov))[:, None]
        fade_in = np.sqrt(np.linspace(0.0, 1.0, ov))[:, None]
        join = head * fade_out + x[:ov].astype(np.float64) * fade_in
        out = np.vstack([out[:-ov], join, x[ov:].astype(np.float64)])
    return out


def _render_real_chop_variant() -> np.ndarray:
    """Variant E (labeled): a real OGCM bed chop pitched to D minor."""
    from pedalboard import (Compressor, Gain, LadderFilter, Pedalboard,
                            PitchShift, Reverb)

    y, sr = sf.read(str(CHOP_SRC), always_2d=True)
    if sr != SR:
        import librosa
        y = librosa.resample(y.T, orig_sr=sr, target_sr=SR).T
    if y.shape[1] == 1:
        y = np.repeat(y, 2, axis=1)
    board = Pedalboard([PitchShift(semitones=CHOP_SHIFT_ST)])
    y = board(np.ascontiguousarray(y.T), SR).T.astype(np.float32)
    tiled = _xadd_tile(y, reps=2, overlap_s=0.02, sr=SR)
    chain = Pedalboard([
        LadderFilter(mode=LadderFilter.Mode.LPF24, cutoff_hz=4500.0,
                     resonance=0.1, drive=1.3),
        Reverb(room_size=0.4, damping=0.65, wet_level=0.2, dry_level=1.0,
               width=1.0),
        Compressor(threshold_db=-14.0, ratio=2.0, attack_ms=8.0,
                   release_ms=100.0),
        Gain(gain_db=0.0)])
    wet = chain(np.ascontiguousarray(tiled.T), SR).T
    return sv.fit_loop(wet.astype(np.float32), SR, 8 * sv.BAR_S)


def _to_target(audio: np.ndarray, target_lufs: float) -> np.ndarray:
    cur = master.integrated_lufs(audio, SR)
    gain = target_lufs - cur if np.isfinite(cur) else 0.0
    out = audio * np.float32(10.0 ** (gain / 20.0))
    tp = master.true_peak_dbfs(out, SR)
    if tp > TP_CEILING:
        out = out * np.float32(10.0 ** ((TP_CEILING - tp) / 20.0))
    return out.astype(np.float32)


VARIANTS = {
    "sample_A_region63_ep": lambda: _render_region_variant(
        "region_63_66_cleaned_Dm.mid", lead_voice="rhodes"),
    "sample_B_region233_gfunk": lambda: _render_region_variant(
        "region_233_258_cleaned_Dm.mid", lead_voice="gfunk", add_pad=True),
    "sample_C_region12_darkpad": lambda: _render_region_variant(
        "region_12_6_cleaned_Dm.mid", lead_voice="rhodes",
        chord_voice="pad", add_pad=True),
    "sample_D_motif_prog": _render_motif_variant,
    "sample_E_real_chop_REF": _render_real_chop_variant,
}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    AUD.mkdir(parents=True, exist_ok=True)
    manifest: Dict = {"pack": "GATE_S_suno_sample", "sr": SR,
                    "target_lufs": TARGET_LUFS, "lu_tol": LU_TOL,
                    "tp_ceiling": TP_CEILING, "files": []}
    for name, build in VARIANTS.items():
        print(f"[render] {name} ...", flush=True)
        audio = build()
        audio = _to_target(audio, TARGET_LUFS)
        peak = float(np.abs(audio).max())
        out = AUD / f"{name}.wav"
        sf.write(str(out), audio, SR, subtype=SUBTYPE)
        rec = {"file": out.name, "duration_s": round(audio.shape[0] / SR, 3),
               "sample_peak": round(peak, 4)}
        manifest["files"].append(rec)
        print(f"         {audio.shape[0]/SR:.1f}s peak={peak:.3f}")

    # verify written files
    lufs_vals, ok_tp, ok_clip, ok_seam = [], True, True, {}
    for rec in manifest["files"]:
        y, _ = sf.read(str(AUD / rec["file"]), always_2d=True)
        rec["lufs"] = round(master.integrated_lufs(y, SR), 2)
        rec["true_peak_dbtp"] = round(master.true_peak_dbfs(y, SR), 2)
        lufs_vals.append(rec["lufs"])
        ok_tp &= rec["true_peak_dbtp"] <= TP_CEILING + 0.05
        ok_clip &= rec["sample_peak"] <= 0.999
        f = int(0.05 * SR)
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
