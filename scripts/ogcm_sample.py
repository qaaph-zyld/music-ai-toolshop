"""OGCM Suno-sample builder — GATE S3 (simple recognizable motif).

S3 distills the picked segment's transcription into a short canonical motif
(most-repeated 2-bar cell, simplified to <=8 grid-quantized Dm notes), tiles
it across an 8-bar loop, and voices it on plain tones over quiet Dm chords +
sub. Variants: sine lead, EP lead, sine+octave, A/A' call-response, and a
labeled real-audio chop of the picked segment for comparison.

Output: ``stems/flip_sample/audition_s3/`` — seamless loops, -16 LUFS matched.
(--pack s2 rebuilds the previous melody-legibility pack into audition_s2;
--pack s4 the raw-key riff pack; --pack s5 renders the SYNTHESIS-ONLY
resynthesized-wail pack into audition_s5: the whine probe s5_00, the wail
layered on / replacing the S4 lead (A, B, B_saw) and the half-speed texture
(C). The wail is a pitch contour (pyin) of the htdemucs_6s guitar stem
re-performed on our own oscillators; stem audio is read only for that
contour. The whole s5 pack runs at --tempo-bpm (default 105).
--pack s6 renders the DRUMLESS, SYNTHESIS-ONLY organ x synthwave "night drive"
pack into audition_s6: the S5-A lead layering (riff + saw wail), the S4
chords as string-machine / combo / drawbar organ stabs (plus an EP control),
a driving 8th-note octave synth bass and a quarter-note pump, at 105 BPM.)

Usage:
    python scripts/ogcm_sample.py [--pack s3] [--region region_63_66_cleaned_Dm.mid]
        [--chop cand_317_8bar_F#min_score0.47.wav] [--shift -4]
        [--tempo-bpm 105] [--wail-bars auto|2|4]   # --pack s5 / s6 only
        [--outdir <root>]   # pack goes to <root>/audition_<pack>
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
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
               chords: Optional[List[dict]] = None,
               lead_delay_s: Optional[float] = None) -> np.ndarray:
    """Shared S3/S4/S5 builder: motif lead @1.0 + quiet chords + sub, folded
    into a seamless n_bars loop. ``chords=None`` keeps the S3 fallback
    i-VI-III-VII cycle; S4 passes chords derived from the segment's bass.
    ``lead_delay_s=None`` keeps west_coast_chain's default 0.375 s echo
    (S3/S4 unchanged); S5 passes the tempo-synced dotted 8th."""
    if chords is None:
        chords = sv.derive_chords([], [], n_bars)  # fallback i-VI-III-VII cycle
    lanes: Dict[str, np.ndarray] = {
        "lead": voice_fn(melody, sr=SR),
        "rhodes": sv.render_rhodes(sv.chord_bednotes(chords, velocity=0.45),
                                   sr=SR),
        "sub": sv.render_sub(sv.bass_root_notes(chords, velocity=0.7), sr=SR),
    }
    lanes = {k: a * S3_GAINS.get(k, 1.0) for k, a in lanes.items()}
    if lead_delay_s is None:
        bus = sv.west_coast_chain(lanes, sr=SR)
    else:
        bus = sv.west_coast_chain(lanes, sr=SR, lead_delay_s=lead_delay_s)
    return sv.fit_loop(bus, SR, n_bars * sv.BAR_S)


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


def _riff_rows(riff_native: List[bed_lanes.BedNote],
               riff_dm: List[bed_lanes.BedNote]) -> List[dict]:
    """Manifest rows for a riff, named in both keys (shared by S4 and S5)."""
    return [{"i": i,
             "start_s": round(nd.start_s, 4),
             "dur_s": round(nd.duration_s, 4),
             "midi_dm": nd.note, "name_dm": sv.note_name(nd.note),
             "midi_native": nn.note,
             "name_native": sv.note_name(nn.note)}
            for i, (nn, nd) in enumerate(zip(riff_native, riff_dm))]


def _s4_source(region: str, transpose_st: int) -> Dict:
    """Shared S4/S5 source path: RAW native-key region -> riff + chords.

    riff is extracted in F# minor (no scale lock), shifted `transpose_st`
    (-4) so it lands exactly on D natural minor. Chords are derived from the
    segment's own bass inside the winning cell (transposed the same way).
    Reads only the transcription MIDI — no audio. Used verbatim by both
    ``_s4_variants`` and ``_s5_variants`` (S4 output is byte-identical to the
    pre-factoring code: the body below is the moved, unchanged S4 logic).
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
    return {"tonic_pc": tonic_pc, "mode": mode, "key_r": key_r,
            "riff_native": riff_native, "riff_dm": riff_dm,
            "cell_t0": cell_t0, "cell_s": cell_s, "n_bars": n_bars,
            "chords": chords, "chords_native": chords_native,
            "tiled": tiled, "octaved": octaved, "tiled_native": tiled_native,
            "stats": stats, "snapped": snapped,
            "bass_dm": bass_dm}     # S5b re-derives chords at another tempo


def _s4_variants(region: str, chop: str, shift: float, transpose_st: int
                 ) -> Tuple[Dict[str, Callable[[], np.ndarray]], Dict]:
    """GATE S4: riff from the RAW native-key region, transposed to Dm.

    `s4_04` shifts every lane +4 back to the native F# minor for a
    direct A/B against instrumental.wav. Source path: ``_s4_source``.
    """
    src = _s4_source(region, transpose_st)
    tonic_pc, mode, key_r = src["tonic_pc"], src["mode"], src["key_r"]
    riff_native, riff_dm = src["riff_native"], src["riff_dm"]
    cell_t0, cell_s = src["cell_t0"], src["cell_s"]
    chords, chords_native = src["chords"], src["chords_native"]
    tiled, octaved = src["tiled"], src["octaved"]
    tiled_native = src["tiled_native"]
    stats, snapped = src["stats"], src["snapped"]

    meta = {
        "region": region, "chop_ref": chop, "chop_shift_st": shift,
        "transpose_st": transpose_st,
        "source_key": {"tonic_pc": tonic_pc,
                       "tonic": sv.PC_NAMES[tonic_pc],
                       "mode": mode, "r": round(key_r, 4)},
        "cell_t0_s": round(cell_t0, 4), "cell_s": round(cell_s, 4),
        "riff": _riff_rows(riff_native, riff_dm),
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


# ---------------------------------------------------------------------------
# GATE S5 — resynthesized wail. SYNTHESIS ONLY: no _real_chop and no stem
# audio anywhere in this pack. The guitar stem is read ONLY by
# ``_s5_wail`` and ONLY to extract a pitch contour + RMS envelope; every
# rendered lane is our own oscillators.
#   s5a: s5_00_riff_whine (the S4 riff on the whine voice, dotted-8th echo)
#   s5b: + s5_A/B/B_saw/C from the f0 contour, whole pack at --tempo-bpm
# ---------------------------------------------------------------------------

S5_STEM = STEMS / "htdemucs_6s" / "2Pac - Only God Can Judge Me" / "guitar.wav"
S5_TEMPO_BPM = 105.0            # 1.1785x the record's 89.1 felt BPM
S5_PRE_S = 0.3                  # pyin context before the window (cropped off)
S5_EXTRACT_BARS = 4             # always extracted; cropped to 2 or 4 bars
S5_CONTINUE_GAP_S = 0.3         # phrase "continues" past the 2-bar boundary
S5_VIB_MAX_PP_CENTS = 40.0      # synthetic vibrato only below this (s5r)
S5_AGREE_TOL_ST = 1.0           # riff-agreement pitch tolerance
S5_TIMBRE_DEFAULT = {"sine": 1.0, "saw": 0.35, "lpf_hz": None}
S5_TIMBRE_SAW = {"sine": 0.3, "saw": 1.0, "lpf_hz": 5000.0,
                 "lpf_resonance": 0.2}
S5_TIMBRE_TEXTURE = {"sine": 1.0, "saw": 0.35, "lpf_hz": 2200.0,
                     "lpf_resonance": 0.1}
S5_A_WAIL_DB = -3.0             # wail under the S4 lead in the layer variant
S5_B_WAIL_DB = 0.0              # wail AS the lead: same level as the S4 lead
S5_C_TEXTURE_DB = -12.0         # post-FX texture level vs the S4 lead
S5_TEXTURE_SLOW = 2.0           # half speed: contour time axis x2
S5_TEXTURE_FB = 0.40


def _region_start_s(region: str) -> float:
    """Record time of a region MIDI's t=0, from its ``region_<a>_<b>...`` name."""
    m = re.match(r"region_(\d+(?:\.\d+)?)_(\d+(?:\.\d+)?)", region)
    if not m:
        raise SystemExit(f"[s5] cannot read the record start time from region "
                         f"name {region!r}")
    return float(m.group(1))


def _rms(a: np.ndarray, n: int) -> float:
    x = np.asarray(a[:n], dtype=np.float64)
    return float(np.sqrt(np.mean(x * x))) if x.size else 0.0


def _sum_pad(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    n = max(a.shape[0], b.shape[0])
    out = np.zeros((n, 2), dtype=np.float64)
    out[: a.shape[0]] += a
    out[: b.shape[0]] += b
    return out.astype(np.float32)


def _phrase_continues(c4: Dict, boundary_s: float) -> Tuple[bool, str]:
    """Does the wail phrase clearly continue past the 2-bar boundary? Yes if
    the contour is voiced at the boundary, or voiced again within
    ``S5_CONTINUE_GAP_S`` after it (no rest straddles the boundary)."""
    t, v = c4["times"], c4["voiced"]
    i = int(np.searchsorted(t, boundary_s))
    if i < len(t) and v[i]:
        return True, (f"voiced at the {boundary_s:.3f} s boundary: a note "
                      f"sustains across it")
    later = np.flatnonzero(v & (t >= boundary_s))
    if later.size and t[later[0]] - boundary_s <= S5_CONTINUE_GAP_S:
        return True, (f"next voiced frame {t[later[0]] - boundary_s:.3f} s "
                      f"after the boundary (<= {S5_CONTINUE_GAP_S} s)")
    return False, "rest straddles the 2-bar boundary"


def _riff_agreement(riff_native: List[bed_lanes.BedNote], segs: List[Dict],
                    cell_s: float, n_cells: int) -> Dict:
    """Do the contour's note segments coincide with the S4 riff notes, in the
    NATIVE key? A riff note is matched when a segment starts within one
    sixteenth of it and its median pitch is within one semitone."""
    six = sv.GRID_16TH_S

    def match(off: float, r_note: bed_lanes.BedNote):
        best = None
        for s in segs:
            dt = s["start_s"] - (r_note.start_s + off)
            dp = s["median_midi"] - r_note.note
            if abs(dt) <= six + 1e-9 and abs(dp) <= S5_AGREE_TOL_ST + 1e-9:
                if best is None or abs(dt) < abs(best[0]):
                    best = (dt, dp, s)
        return best

    def recall(off: float, cell: int) -> float:
        shifted = [bed_lanes.BedNote(n.start_s + cell * cell_s, n.end_s,
                                     n.note, n.velocity) for n in riff_native]
        return sum(match(off, n) is not None for n in shifted) / len(shifted)

    rows = []
    hit = 0
    for i, n in enumerate(riff_native):
        b = match(0.0, n)
        hit += b is not None
        rows.append({"riff_i": i, "riff_start_s": round(n.start_s, 4),
                     "riff_name_native": sv.note_name(n.note),
                     "riff_midi_native": n.note,
                     "matched": b is not None,
                     "seg_start_s": None if b is None
                     else round(b[2]["start_s"], 4),
                     "seg_median_midi": None if b is None
                     else round(b[2]["median_midi"], 3),
                     "dt_s": None if b is None else round(b[0], 4),
                     "dpitch_st": None if b is None else round(b[1], 3)})
    cell_segs = [s for s in segs if s["start_s"] < cell_s]
    seg_hit = sum(any(abs(s["start_s"] - r.start_s) <= six + 1e-9
                      and abs(s["median_midi"] - r.note) <= S5_AGREE_TOL_ST
                      for r in riff_native) for s in cell_segs)
    sweep_step = six / 4.0
    sweep = [(round(k * sweep_step, 4), recall(k * sweep_step, 0))
             for k in range(-12, 13)]
    best_off, best_rec = max(sweep, key=lambda x: (x[1], -abs(x[0])))
    out = {"tolerance": {"onset_s": round(six, 4),
                         "onset_label": "1 sixteenth at the felt 89.1 BPM",
                         "pitch_st": S5_AGREE_TOL_ST},
           "key": "native F# minor (contour before the -4 transpose)",
           "riff_notes": len(riff_native),
           "riff_notes_matched": int(hit),
           "riff_recall": round(hit / len(riff_native), 4),
           "contour_segments_in_cell": len(cell_segs),
           "contour_segments_matching_riff": int(seg_hit),
           "contour_precision": (round(seg_hit / len(cell_segs), 4)
                                 if cell_segs else 0.0),
           "per_note": rows,
           "offset_sweep_best_s": best_off,
           "offset_sweep_best_recall": round(best_rec, 4),
           "offset_sweep_note": "riff onsets shifted by k*(sixteenth/4), "
                                "k=-12..12; best at 0 supports the "
                                "54.0 + cell_t0 time mapping"}
    if n_cells >= 2:
        out["riff_recall_cell2"] = round(recall(0.0, 1), 4)
    return out


def _s5_wail(src: Dict, region: str, bars_arg: str, transpose_st: int) -> Dict:
    """Read the guitar stem ONLY to extract a pitch contour + RMS envelope.

    The window is the S4 riff cell: absolute ``region_start + cell_t0`` (record
    time). A 4-bar contour is always extracted (pyin has ``S5_PRE_S`` of
    context); the wail is then cropped to 2 or 4 bars (rule in
    ``_phrase_continues``). The audio array never leaves this function.
    """
    t_abs0 = _region_start_s(region) + src["cell_t0"]
    win_full = S5_EXTRACT_BARS * sv.BAR_S
    start = t_abs0 - S5_PRE_S
    if start < 0.0:
        raise SystemExit(f"[s5] window start {start:.3f} s is before the stem")
    with sf.SoundFile(str(S5_STEM)) as f:
        sr_in = f.samplerate
        f.seek(int(round(start * sr_in)))
        y = f.read(int(round((win_full + 2 * S5_PRE_S) * sr_in)),
                   dtype="float32", always_2d=True)
    t_wall = time.time()
    raw = sv.extract_f0_contour(y, sr_in)
    del y                                   # pitch + RMS are all that survive
    print(f"[s5] pyin on the guitar stem: {len(raw['times'])} frames, "
          f"{time.time() - t_wall:.1f} s wall", flush=True)
    if not raw["voiced"].any():
        raise SystemExit("[s5] no voiced frames in the guitar window")
    clean = sv.clean_contour(raw)
    c4 = sv.crop_contour(clean, S5_PRE_S, S5_PRE_S + win_full)
    if bars_arg == "auto":
        cont, reason = _phrase_continues(c4, 2.0 * sv.BAR_S)
        bars = 4 if cont else 2
        reason = f"auto: {reason} -> {bars} bars"
    else:
        bars = int(bars_arg)
        reason = f"forced by --wail-bars {bars}"
    native = c4 if bars == 4 else sv.crop_contour(
        clean, S5_PRE_S, S5_PRE_S + bars * sv.BAR_S)
    dm = sv.transpose_contour(native, transpose_st)
    stats = sv.contour_stats(dm)
    segs4 = sv.note_segments(c4)
    agreement = _riff_agreement(src["riff_native"], segs4, src["cell_s"],
                                n_cells=2)
    return {"t_abs0": t_abs0, "bars": bars, "reason": reason,
            "native": native, "dm": dm, "stats": stats,
            "agreement": agreement, "stem_sr": sr_in,
            "win_full_s": win_full}


def _texture_fx(wail: np.ndarray, delay_s: float) -> np.ndarray:
    """Fully wet echo + fully wet reverb for the half-speed texture lane."""
    from pedalboard import Delay, Pedalboard, Reverb
    board = Pedalboard([
        Delay(delay_seconds=delay_s, feedback=S5_TEXTURE_FB, mix=1.0),
        Reverb(room_size=0.8, damping=0.5, wet_level=1.0, dry_level=0.0,
               width=1.0)])
    return board(np.ascontiguousarray(wail.T), SR).T.astype(np.float32)


def _render_s5_bus(lead_audio: np.ndarray, chords: List[dict], bar_s: float,
                   n_bars: int, lead_delay_s: float,
                   texture: Optional[np.ndarray] = None) -> np.ndarray:
    """``_render_s3``'s bus with a pre-rendered lead lane, a tempo (``bar_s``)
    and an optional dry texture lane. Lane order / gains / chain match
    ``_render_s3`` so s5_00 at 89.1 BPM is byte-identical to the s5a probe."""
    lanes: Dict[str, np.ndarray] = {
        "lead": lead_audio,
        "rhodes": sv.render_rhodes(
            sv.chord_bednotes(chords, bar_s=bar_s, velocity=0.45), sr=SR),
        "sub": sv.render_sub(
            sv.bass_root_notes(chords, bar_s=bar_s, velocity=0.7), sr=SR),
    }
    lanes = {k: a * S3_GAINS.get(k, 1.0) for k, a in lanes.items()}
    if texture is not None:
        lanes["texture"] = texture         # not in the chain table: stays dry
    bus = sv.west_coast_chain(lanes, sr=SR, lead_delay_s=lead_delay_s)
    return sv.fit_loop(bus, SR, n_bars * bar_s)


def _s5_core(region: str, transpose_st: int, tempo_bpm: float,
             wail_bars_arg: str) -> Dict:
    """Shared S5/S6 construction at ``tempo_bpm``: riff, chords, wail contour
    and the loop all time-scale by ``FELT_BPM / tempo_bpm`` (S4's grid is
    89.1). The body is the moved, unchanged head of ``_s5_variants`` (S5
    output stays byte-identical); the stem is read only inside ``_s5_wail``."""
    src = _s4_source(region, transpose_st)
    tonic_pc = src["tonic_pc"]
    f = bed_lanes.FELT_BPM / tempo_bpm
    bar_s = 4.0 * 60.0 / tempo_bpm
    n_bars = src["n_bars"]
    reps = n_bars // 2
    loop_s = n_bars * bar_s
    loop_n = int(loop_s * SR)
    lead_delay = 0.75 * 60.0 / tempo_bpm       # dotted 8th at this tempo
    print(f"[s5] tempo {tempo_bpm:g} BPM = {tempo_bpm / bed_lanes.FELT_BPM:.4f}x "
          f"the felt {bed_lanes.FELT_BPM} BPM; time factor {f:.6f}; bar "
          f"{bar_s:.4f} s; loop {loop_s:.3f} s; lead echo {lead_delay:.4f} s")

    riff_native_t = sv.tempo_scale(src["riff_native"], f)
    riff_dm_t = sv.tempo_scale(src["riff_dm"], f)
    tiled_t = sv.tile_motif(riff_dm_t, 2.0 * bar_s, reps)
    chords = sv.derive_chords(sv.tempo_scale(src["bass_dm"], f), [], n_bars,
                              bar_s=bar_s)
    chords_match_s4 = ([c["name"] for c in chords]
                       == [c["name"] for c in src["chords"]])

    w = _s5_wail(src, region, wail_bars_arg, transpose_st)
    bars = w["bars"]
    if n_bars % bars or (n_bars % (bars * 2)):
        raise SystemExit(f"[s5] {bars}-bar wail does not tile an {n_bars}-bar "
                         f"loop (and its half-speed copy)")
    c_t = sv.time_scale_contour(w["dm"], f)
    tiled_w = sv.tile_contour(c_t, bars * bar_s, n_bars // bars)
    c_slow = sv.time_scale_contour(c_t, S5_TEXTURE_SLOW)
    tiled_slow = sv.tile_contour(c_slow, bars * bar_s * S5_TEXTURE_SLOW,
                                 n_bars // (bars * 2))
    vib_pp = w["stats"]["vibrato_pp_cents"]
    n_sus = w["stats"]["n_sustained"]
    add_vib = bool(n_sus == 0 or vib_pp < S5_VIB_MAX_PP_CENTS)
    print(f"[s5] window {w['t_abs0']:.4f}-{w['t_abs0'] + bars * sv.BAR_S:.4f} s "
          f"({bars} bars): {w['reason']}")
    print(f"[s5] contour_stats {json.dumps(w['stats'])}")
    print(f"[s5] measured contour vibrato {vib_pp} cents pk-pk over {n_sus} "
          f"sustained notes -> add_vibrato={add_vib} (threshold "
          f"{S5_VIB_MAX_PP_CENTS})")
    print(f"[s5] riff agreement (native key, 1 sixteenth / 1 st): "
          f"{w['agreement']['riff_notes_matched']}/"
          f"{w['agreement']['riff_notes']} riff notes matched")
    return {"src": src, "tonic_pc": tonic_pc, "f": f, "bar_s": bar_s,
            "n_bars": n_bars, "loop_s": loop_s, "loop_n": loop_n,
            "lead_delay": lead_delay, "riff_native_t": riff_native_t,
            "riff_dm_t": riff_dm_t, "tiled_t": tiled_t, "chords": chords,
            "chords_match_s4": chords_match_s4, "w": w, "bars": bars,
            "tiled_w": tiled_w, "tiled_slow": tiled_slow, "vib_pp": vib_pp,
            "n_sus": n_sus, "add_vib": add_vib}


def _gain_for(audio: np.ndarray, db: float, ref_rms: float,
              loop_n: int) -> float:
    """Gain that puts ``audio``'s loop RMS ``db`` dB from ``ref_rms``."""
    r = _rms(audio, loop_n)
    return float(ref_rms * 10.0 ** (db / 20.0) / r) if r > 0 else 0.0


def _wail_source_meta(w: Dict, region: str, bars: int) -> Dict:
    """Manifest ``wail_source`` block (shared by the S5 and S6 manifests)."""
    return {
        "stem": S5_STEM.relative_to(REPO).as_posix(),
        "stem_role": "htdemucs_6s guitar stem (G1 pick)",
        "stem_used_for": "pitch contour + RMS envelope ONLY; no stem "
                         "sample in any output lane",
        "region": region,
        "window_abs_start_s": round(w["t_abs0"], 4),
        "window_abs_end_s": round(w["t_abs0"] + bars * sv.BAR_S, 4),
        "window_bars": bars,
        "window_bar_s_at_89p1": round(sv.BAR_S, 4),
        "window_bars_reason": w["reason"],
        "context_pre_s": S5_PRE_S,
        "stem_sr": w["stem_sr"],
    }


def _s5_variants(region: str, transpose_st: int, tempo_bpm: float,
                 wail_bars_arg: str
                 ) -> Tuple[Dict[str, Callable[[], np.ndarray]], Dict, Dict]:
    """The S5 pack at ``tempo_bpm``: riff, chords, sub, wail contour and the
    loop all time-scale by ``FELT_BPM / tempo_bpm`` (S4's grid is 89.1).
    Construction: ``_s5_core``.

    Returns (variants, meta, extra) — extra carries the manifest additions,
    ``lead_delay_s`` and the ``contour.npz`` arrays."""
    core = _s5_core(region, transpose_st, tempo_bpm, wail_bars_arg)
    src, tonic_pc, f = core["src"], core["tonic_pc"], core["f"]
    bar_s, n_bars = core["bar_s"], core["n_bars"]
    loop_s, loop_n, lead_delay = core["loop_s"], core["loop_n"], core["lead_delay"]
    riff_native_t, riff_dm_t = core["riff_native_t"], core["riff_dm_t"]
    tiled_t, chords = core["tiled_t"], core["chords"]
    chords_match_s4, w, bars = core["chords_match_s4"], core["w"], core["bars"]
    tiled_w, tiled_slow = core["tiled_w"], core["tiled_slow"]
    vib_pp, n_sus, add_vib = core["vib_pp"], core["n_sus"], core["add_vib"]

    riff_lead = sv.render_simple_lead(tiled_t, sr=SR)   # the S4 sine lead
    lead_rms = _rms(riff_lead, loop_n)
    wail_def = sv.render_f0_lead(tiled_w, sr=SR, add_vibrato=add_vib,
                                 **S5_TIMBRE_DEFAULT)
    wail_saw = sv.render_f0_lead(tiled_w, sr=SR, add_vibrato=add_vib,
                                 **S5_TIMBRE_SAW)
    wail_tex = sv.render_f0_lead(tiled_slow, sr=SR, add_vibrato=False,
                                 **S5_TIMBRE_TEXTURE)
    tex_fx = _texture_fx(wail_tex, lead_delay)

    def gain_for(audio: np.ndarray, db: float) -> float:
        return _gain_for(audio, db, lead_rms, loop_n)

    g_a = gain_for(wail_def, S5_A_WAIL_DB)
    g_b = gain_for(wail_def, S5_B_WAIL_DB)
    g_bs = gain_for(wail_saw, S5_B_WAIL_DB)
    g_c = gain_for(tex_fx, S5_C_TEXTURE_DB)     # calibrated AFTER the fx

    def bus(lead: np.ndarray, texture: Optional[np.ndarray] = None
            ) -> np.ndarray:
        return _render_s5_bus(lead, chords, bar_s, n_bars, lead_delay, texture)

    variants: Dict[str, Callable[[], np.ndarray]] = {
        "s5_00_riff_whine": lambda: bus(sv.render_gfunk_lead(tiled_t, sr=SR)),
        "s5_A_layer": lambda: bus(_sum_pad(riff_lead, wail_def * g_a)),
        "s5_B_replace": lambda: bus(wail_def * g_b),
        "s5_B_replace_saw": lambda: bus(wail_saw * g_bs),
        "s5_C_texture": lambda: bus(riff_lead, tex_fx * g_c),
    }

    tonic = sv.PC_NAMES[tonic_pc]
    meta = {
        "region": region,
        "riff_source": "S4 _s4_source (raw native-key transcription, "
                       "transposed, never scale-snapped)",
        "transpose_st": transpose_st,
        "source_key": {"tonic_pc": tonic_pc, "tonic": tonic,
                       "mode": src["mode"], "r": round(src["key_r"], 4)},
        "cell_t0_s": round(src["cell_t0"], 4),
        "cell_s": round(2.0 * bar_s, 4),
        "riff": _riff_rows(riff_native_t, riff_dm_t),
        "riff_stats": src["stats"],
        "chords_per_bar": [c["name"] for c in chords],
        "chords_match_s4": chords_match_s4,
        "snapped_notes": src["snapped"],
        "lead_voice": "render_gfunk_lead (glide 100 ms, vib 5.5 Hz, "
                      "180 ms delay, 0.45 st)",
        "lead_delay_label": f"dotted 8th at {tempo_bpm:g} BPM",
        "variants": {
            "s5_00_riff_whine": "riff on render_gfunk_lead (probe)",
            "s5_A_layer": "S4 body (riff on the S4 sine lead + chords + sub) "
                          "+ resynthesized wail on top",
            "s5_B_replace": "wail as the lead over the S4 chords + sub; "
                            "riff muted",
            "s5_B_replace_saw": "B with a saw-heavy timbre (saw 1.0, sine "
                                "0.3, 24 dB/oct LPF 5 kHz, mild resonance)",
            "s5_C_texture": "S4 riff as lead; wail at half speed, low-passed, "
                            "fully wet echo + reverb, -12 dB under",
        },
    }

    def rec_timbre(d: Dict) -> Dict:
        return dict(d, attack_ms=10.0, release_ms=70.0, smooth_ms=20.0,
                    dyn_exp=0.5, drive=1.4)

    npz = {"times": w["dm"]["times"], "f0_hz": w["dm"]["f0_hz"],
           "voiced": w["dm"]["voiced"], "rms": w["dm"]["rms"],
           "f0_hz_native": w["native"]["f0_hz"],
           "transpose_st": np.float64(transpose_st),
           "hop_s": np.float64(w["dm"]["hop_s"]),
           "window_start_abs_s": np.float64(w["t_abs0"]),
           "window_bars": np.int64(bars)}
    extra = {
        "lead_delay_s": lead_delay,
        "npz": npz,
        "manifest": {
            "bpm": tempo_bpm,
            "felt_bpm_source": bed_lanes.FELT_BPM,
            "tempo_factor": round(f, 6),
            "tempo_ratio_vs_source": round(tempo_bpm / bed_lanes.FELT_BPM, 4),
            "loop_s": round(loop_s, 4),
            "wail_source": _wail_source_meta(w, region, bars),
            "contour_stats": w["stats"],
            "riff_agreement": w["agreement"],
            "recipe": {
                "pyin": {"sr": sv.CONTOUR_SR, "fmin_hz": sv.CONTOUR_FMIN_HZ,
                         "fmax_hz": sv.CONTOUR_FMAX_HZ,
                         "frame_length": sv.CONTOUR_FRAME,
                         "hop_length": sv.CONTOUR_HOP,
                         "voiced_mask": "voiced_flag AND prob>=0.5 AND "
                                        "RMS gate (>-60 dBFS, within 35 dB "
                                        "of p95)",
                         "other": "librosa defaults, fill_na=nan"},
                "clean": {"order": ["octave fix per segment", "median "
                                    "filter", "drop islands", "bridge gaps"],
                          "median_frames": 5, "min_island_frames": 9,
                          "max_gap_frames": 17, "max_bridge_st": 3.0,
                          "frames_quoted_at_hop": sv.CONTOUR_HOP},
                "transpose_st": transpose_st,
                "time_scale": round(f, 6),
                "tile": f"{bars}-bar contour x{n_bars // bars} over "
                        f"{n_bars} bars",
                "vibrato": {"measured_pp_cents": vib_pp,
                            "n_sustained": n_sus,
                            "threshold_pp_cents": S5_VIB_MAX_PP_CENTS,
                            "synthetic_vibrato_added": add_vib},
                "render": {"default": rec_timbre(S5_TIMBRE_DEFAULT),
                           "saw_heavy": rec_timbre(S5_TIMBRE_SAW),
                           "texture": dict(rec_timbre(S5_TIMBRE_TEXTURE),
                                           time_scale_x=S5_TEXTURE_SLOW,
                                           echo_mix=1.0,
                                           echo_feedback=S5_TEXTURE_FB,
                                           reverb_wet=1.0, reverb_dry=0.0),
                           "pitch_smoothing_ms": 20.0},
                "levels": {
                    "reference": "S4 sine lead lane RMS over the loop",
                    "A_wail_db": S5_A_WAIL_DB, "B_wail_db": S5_B_WAIL_DB,
                    "C_texture_db_post_fx": S5_C_TEXTURE_DB,
                    "gains": {"A": round(g_a, 4), "B": round(g_b, 4),
                              "B_saw": round(g_bs, 4),
                              "C_texture": round(g_c, 4)}},
                "lead_delay_s": round(lead_delay, 6),
            },
        },
    }
    return variants, meta, extra


# ---------------------------------------------------------------------------
# GATE S6 — organ x synthwave "night drive", street-rap energy. SYNTHESIS ONLY
# and DRUMLESS (Suno builds the beat): no source audio, no noise, no
# percussion voice. Lead = the S5-A layering (S4 riff + the resynthesized wail
# in the SAW timbre, -3 dB under the riff); chords = the S4-derived chords
# (existing voicings) as organ stabs; bass = driving 8th-note octave synth
# bass; pump = quarter-note duck. The guitar stem is read ONLY by ``_s5_wail``
# (pitch + RMS), exactly as in S5.
# ---------------------------------------------------------------------------

S6_TEMPO_BPM = 105.0
S6_STAB_DB = -6.0               # organ stabs under the lead lane (RMS, pre-FX)
S6_BASS_DB = -6.0               # driving bass under the lead lane (RMS, pre-FX)
S6_PUMP_DB = {"bass": -6.0, "ep": -9.0, "organ": -2.0}   # the lead is NOT pumped
S6_PUMP_ATTACK_MS = 5.0
S6_PUMP_RELEASE_BEATS = 0.6     # 343 ms at 105 BPM
S6_TAIL_S = 3.0                 # lane length past the loop: tails fold in
S6_RETURN = {"pre_delay_s": 0.025, "reverb_room_size": 0.8,
             "reverb_damping": 0.5, "hp_hz": 200.0, "wet_db": -16.0}
S6_LANE_NAMES = ("lead", "rhodes", "organ", "bass", "fx_return")
S6_FILES = (("s6_00_drive_control", None), ("s6_01_organ_string", "string"),
            ("s6_02_organ_combo", "combo"), ("s6_03_organ_drawbar", "drawbar"))
# s6r report (research_s6_report.md), copied verbatim
S6_SUNO_STYLE_PROMPT = {
    "primary": "German street rap x synthwave night drive, energetic, hard "
               "trap drums, organ stabs, driving octave synth bass, gritty "
               "male rap vocals, dark neon mood, 105 BPM, D minor",
    "alt1": "Gritty German gangsta rap meets 80s synthwave, neon midnight "
            "drive, retro organ chord stabs, pulsing octave saw bass, punchy "
            "808 drums, raspy male rap, energetic, 105 BPM",
    "alt2": "Aggressive German rap over retro synthwave, combo organ stabs, "
            "pumping sidechain bass, tight trap hi-hats, hard kick, dark "
            "cinematic night drive, male rap vocal, 105 BPM",
}
_DRUM_LANE_TAGS = ("drum", "perc", "kick", "snare", "hat", "clap", "noise")


def _fit_len(a: np.ndarray, n: int) -> np.ndarray:
    """Zero-pad / trim a lane to exactly ``n`` samples (float32)."""
    out = np.zeros((n,) + a.shape[1:], dtype=np.float32)
    m = min(n, a.shape[0])
    out[:m] = a[:m]
    return out


def _db(x: float) -> float:
    return round(20.0 * math.log10(x), 2) if x > 0 else float("-inf")


def _s6_return(send: np.ndarray, loop_n: int) -> Tuple[np.ndarray, float]:
    """Hall return for the organ + bass send: 25 ms pre-delay (a sample
    shift), wet-only Freeverb (room 0.8), 200 Hz high-pass on the return, then
    scaled so the return's RMS over the loop is ``wet_db`` (-16 dB) under the
    send's. Returns (return audio, scale)."""
    from pedalboard import HighpassFilter, Pedalboard, Reverb
    n = send.shape[0]
    pre = int(round(S6_RETURN["pre_delay_s"] * SR))
    x = np.zeros_like(send)
    x[pre:] = send[: n - pre]
    board = Pedalboard([
        Reverb(room_size=S6_RETURN["reverb_room_size"],
               damping=S6_RETURN["reverb_damping"], wet_level=1.0,
               dry_level=0.0, width=1.0),
        HighpassFilter(cutoff_frequency_hz=S6_RETURN["hp_hz"])])
    wet = board(np.ascontiguousarray(x.T), SR).T.astype(np.float32)
    r_wet = _rms(wet, loop_n)
    g = (_rms(send, loop_n) * 10.0 ** (S6_RETURN["wet_db"] / 20.0) / r_wet
         if r_wet > 0 else 0.0)
    return (wet * g).astype(np.float32), float(g)


def _render_s6_bus(lead: np.ndarray, chord_lane: np.ndarray, chord_name: str,
                   bass: np.ndarray, fx_return: np.ndarray,
                   lead_delay_s: float, loop_s: float) -> np.ndarray:
    """S6 bus: ``west_coast_chain`` unchanged (lead: dotted-8th echo + reverb;
    ``rhodes``: chorus + reverb for the control; ``organ`` / ``bass`` /
    ``fx_return`` stay dry in the chain table, so the hall return is the only
    FX on them), summed and glued by the chain's bus compressor, folded into
    a seamless loop."""
    lanes = {"lead": lead, chord_name: chord_lane, "bass": bass,
             "fx_return": fx_return}
    bus = sv.west_coast_chain(lanes, sr=SR, lead_delay_s=lead_delay_s)
    return sv.fit_loop(bus, SR, loop_s)


def _s6_variants(region: str, transpose_st: int, tempo_bpm: float,
                 wail_bars_arg: str
                 ) -> Tuple[Dict[str, Callable[[], np.ndarray]], Dict, Dict]:
    """The S6 pack at ``tempo_bpm``. Returns (variants, meta, extra) like
    ``_s5_variants``; every lane is rendered (and level-calibrated) here, the
    variant callables only run the bus."""
    core = _s5_core(region, transpose_st, tempo_bpm, wail_bars_arg)
    src, tonic_pc, f = core["src"], core["tonic_pc"], core["f"]
    bar_s, n_bars = core["bar_s"], core["n_bars"]
    loop_s, loop_n, lead_delay = core["loop_s"], core["loop_n"], core["lead_delay"]
    riff_native_t, riff_dm_t = core["riff_native_t"], core["riff_dm_t"]
    tiled_t, chords = core["tiled_t"], core["chords"]
    w, bars = core["w"], core["bars"]
    add_vib = core["add_vib"]
    beat_s = 60.0 / tempo_bpm
    n_total = loop_n + int(S6_TAIL_S * SR)

    # lead: S5-A layering with the SAW wail (riff at 1.0, wail -3 dB under it)
    riff_lead = sv.render_simple_lead(tiled_t, sr=SR)
    riff_rms = _rms(riff_lead, loop_n)
    wail_saw = sv.render_f0_lead(core["tiled_w"], sr=SR, add_vibrato=add_vib,
                                 **S5_TIMBRE_SAW)
    g_wail = _gain_for(wail_saw, S5_A_WAIL_DB, riff_rms, loop_n)
    lead = _fit_len(_sum_pad(riff_lead, wail_saw * g_wail), n_total)
    lead_ref = _rms(lead, loop_n)        # level reference: the lead lane

    def pumped(a: np.ndarray, depth_db: float) -> np.ndarray:
        return sv.pump(_fit_len(a, n_total), SR, beat_s, depth_db,
                       attack_ms=S6_PUMP_ATTACK_MS,
                       release_s=S6_PUMP_RELEASE_BEATS * beat_s)

    # bass: driving 8th-note octave synth bass, pumped, -6 dB vs the lead
    bass_notes = sv.driving_bass(chords, bar_s)
    bass_p = pumped(sv.render_synth_bass(bass_notes, sr=SR), S6_PUMP_DB["bass"])
    g_bass = _gain_for(bass_p, S6_BASS_DB, lead_ref, loop_n)
    bass = (bass_p * g_bass).astype(np.float32)

    # control chords: the S5 EP lane (whole notes, S5 gain), pumped -9 dB
    ep_raw = sv.render_rhodes(
        sv.chord_bednotes(chords, bar_s=bar_s, velocity=0.45), sr=SR
    ) * S3_GAINS["rhodes"]
    ep = pumped(ep_raw, S6_PUMP_DB["ep"])

    # organ stab lanes: same chords, same stab notes, -2 dB pump, -6 dB level
    stabs = sv.stab_pattern(chords, bar_s)
    organs: Dict[str, np.ndarray] = {}
    g_organ: Dict[str, float] = {}
    for kind in sv.ORGAN_KINDS:
        p_org = pumped(sv.render_organ(stabs, kind, sr=SR), S6_PUMP_DB["organ"])
        g_organ[kind] = _gain_for(p_org, S6_STAB_DB, lead_ref, loop_n)
        organs[kind] = (p_org * g_organ[kind]).astype(np.float32)

    # hall returns (organ + bass send; bass only for the control)
    rets: Dict[Optional[str], np.ndarray] = {}
    g_ret: Dict[str, float] = {}
    rets[None], g_ret["control"] = _s6_return(bass, loop_n)
    for kind in sv.ORGAN_KINDS:
        rets[kind], g_ret[kind] = _s6_return(organs[kind] + bass, loop_n)

    def lane_report(chord_lane: np.ndarray, ret: np.ndarray) -> Dict:
        rows = {"lead": lead, "chords": chord_lane, "bass": bass,
                "fx_return": ret}
        out = {}
        for k, a in rows.items():
            r = _rms(a, loop_n)
            out[k] = {"rms_dbfs": _db(r), "db_vs_lead": _db(r / lead_ref)}
        return out

    variants: Dict[str, Callable[[], np.ndarray]] = {}
    per_file: Dict[str, Dict] = {}
    for name, kind in S6_FILES:
        chord_lane = ep if kind is None else organs[kind]
        chord_name = "rhodes" if kind is None else "organ"
        per_file[name] = dict(
            chord_voice="render_rhodes whole notes (as S5)" if kind is None
            else f"organ stabs: {kind}",
            lanes=lane_report(chord_lane, rets[kind]))
        variants[name] = (lambda cl=chord_lane, cn=chord_name, r=rets[kind]:
                          _render_s6_bus(lead, cl, cn, bass, r, lead_delay,
                                         loop_s))

    lane_names = S6_LANE_NAMES
    drums = any(tag in lane for lane in lane_names for tag in _DRUM_LANE_TAGS)
    st_odd = [i for i, c in enumerate(sv.STAB_GRIDS[0]) if c == "x"]
    st_even = [i for i, c in enumerate(sv.STAB_GRIDS[1]) if c == "x"]
    tonic = sv.PC_NAMES[tonic_pc]
    meta = {
        "region": region,
        "riff_source": "S4 _s4_source (raw native-key transcription, "
                       "transposed, never scale-snapped)",
        "transpose_st": transpose_st,
        "source_key": {"tonic_pc": tonic_pc, "tonic": tonic,
                       "mode": src["mode"], "r": round(src["key_r"], 4)},
        "cell_t0_s": round(src["cell_t0"], 4),
        "cell_s": round(2.0 * bar_s, 4),
        "riff": _riff_rows(riff_native_t, riff_dm_t),
        "riff_stats": src["stats"],
        "chords_per_bar": [c["name"] for c in chords],
        "chords_match_s4": core["chords_match_s4"],
        "chord_voicings_midi": [list(c["notes"]) for c in chords],
        "snapped_notes": src["snapped"],
        "lead_delay_label": f"dotted 8th at {tempo_bpm:g} BPM",
        "variants": {
            "s6_00_drive_control": "control: riff + saw wail lead, EP whole "
                                   "notes as in S5, driving bass, pump "
                                   "(EP -9 dB, bass -6 dB); no organ",
            "s6_01_organ_string": "same lead and bass; string-machine stabs "
                                  "replace the EP",
            "s6_02_organ_combo": "same lead and bass; combo-organ stabs "
                                 "replace the EP",
            "s6_03_organ_drawbar": "same lead and bass; drawbar + rotary "
                                   "(Leslie) stabs replace the EP",
        },
    }
    extra = {
        "lead_delay_s": lead_delay,
        "manifest": {
            "bpm": tempo_bpm,
            "felt_bpm_source": bed_lanes.FELT_BPM,
            "tempo_factor": round(f, 6),
            "tempo_ratio_vs_source": round(tempo_bpm / bed_lanes.FELT_BPM, 4),
            "loop_s": round(loop_s, 4),
            "n_bars": n_bars,
            "key": "D minor",
            "drums": drums,
            "lanes": list(lane_names),
            "wail_source": _wail_source_meta(w, region, bars),
            "contour_stats": w["stats"],
            "riff_agreement": w["agreement"],
            "lead": {
                "layering": "S5-A: S4 riff on render_simple_lead + the "
                            "resynthesized wail in the SAW timbre "
                            "(S5_TIMBRE_SAW), one shared lead chain; the lead "
                            "is not pumped",
                "wail_db_vs_riff": S5_A_WAIL_DB,
                "wail_gain": round(g_wail, 4),
                "wail_render": dict(S5_TIMBRE_SAW, attack_ms=10.0,
                                    release_ms=70.0, smooth_ms=20.0,
                                    dyn_exp=0.5, drive=1.4,
                                    add_vibrato=add_vib),
                "lead_delay_s": round(lead_delay, 6),
                "lead_delay_label": f"dotted 8th at {tempo_bpm:g} BPM",
            },
            "organ_kinds": list(sv.ORGAN_KINDS),
            "organ": {k: sv.organ_recipe(k) for k in sv.ORGAN_KINDS},
            "stab_grids": {
                "grids": list(sv.STAB_GRIDS),
                "velocities": list(sv.STAB_VELOCITIES),
                "gates_ms": [[t, ms] for t, ms in sv.STAB_GATES_MS],
                "bars": "grid 0 on bars 1,3,5,7; grid 1 on bars 2,4,6,8 "
                        "(1-indexed)",
                "step_s": round(bar_s / 16.0, 6),
                "hit_steps_grid0": st_odd, "hit_steps_grid1": st_even,
                "voicing": "derive_chords' own 'notes' per bar (unchanged); "
                           "velocity = digit / 9",
                "n_stab_notes": len(stabs),
            },
            "bass": {
                "pattern": "8ths, alternating low / high octave on the bar's "
                           "chord root",
                "velocities": sv.BASS_VELOCITIES,
                "gate_frac_of_8th": sv.BASS_GATE_FRAC,
                "notes_per_bar": 8,
                "low_octave_window_midi": [sv.BASS_LOW_FLOOR_MIDI,
                                           sv.BASS_LOW_FLOOR_MIDI + 11],
                "low_notes_midi": [sv.bass_low_midi(c["root_pc"])
                                   for c in chords],
                "recipe": dict(sv.BASS_RECIPE),
            },
            "pump": {
                "kind": "quarter-note duck, no sidechain source, no drums",
                "beat_s": round(beat_s, 6),
                "depth_db": dict(S6_PUMP_DB),
                "attack_ms": S6_PUMP_ATTACK_MS,
                "release_s": round(S6_PUMP_RELEASE_BEATS * beat_s, 6),
                "release_curve": "exponential, time constant = release / 3",
                "lead_pumped": False,
            },
            "fx": {
                "lead": "west_coast_chain lead chain (Delay 0.22 mix fb 0.28 "
                        "at the dotted 8th + Reverb 0.45), unchanged",
                "organ_bass_return": dict(S6_RETURN, send="organ + bass "
                                          "(bass only in the control)"),
                "return_scale": {k: round(v, 4) for k, v in g_ret.items()},
                "bus": "west_coast_chain bus glue compressor, unchanged",
            },
            "levels": {
                "reference": "the lead lane (riff + saw wail) RMS over the "
                             "loop, before any FX",
                "lead_rms_dbfs": _db(lead_ref),
                "targets_db_vs_lead": {"organ_stabs": S6_STAB_DB,
                                       "bass": S6_BASS_DB},
                "note": "control EP keeps the S5 gain (0.30), it is not "
                        "re-calibrated; fx_return is -16 dB vs its send",
                "gains": {"bass": round(g_bass, 4),
                          **{f"organ_{k}": round(v, 4)
                             for k, v in g_organ.items()}},
                "per_file": per_file,
            },
            "suno_style_prompt": dict(S6_SUNO_STYLE_PROMPT),
        },
    }
    return variants, meta, extra


def main(argv: Optional[List[str]] = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(prog="ogcm_sample",
                                description="OGCM Suno-sample builder "
                                            "(S3/S4/S5/S6).")
    p.add_argument("--pack", choices=("s2", "s3", "s4", "s5", "s6"),
                   default="s3")
    p.add_argument("--outdir", default=None,
                   help="output root (default: stems/flip_sample); the pack "
                        "is written to <outdir>/audition_<pack>")
    p.add_argument("--region", default=None,
                   help="midi file under stems/flip_bed_lanes/midi "
                        "(default: per-pack region)")
    p.add_argument("--chop", default=None,
                   help="real-audio reference chop under flip_chops_v2/audition")
    p.add_argument("--shift", type=float, default=CHOP_SHIFT_ST,
                   help="semitones to shift the chop into D minor")
    p.add_argument("--transpose", type=int, default=S4_TRANSPOSE_ST,
                   help="s4: semitones to shift the riff (default -4, F#m->Dm)")
    p.add_argument("--tempo-bpm", type=float, default=None,
                   help=f"s5/s6 only: tempo of the whole pack (default "
                        f"{S5_TEMPO_BPM:g}; the record's felt tempo is "
                        f"{bed_lanes.FELT_BPM})")
    p.add_argument("--wail-bars", choices=("auto", "2", "4"), default="auto",
                   help="s5/s6 only: wail window length in bars (auto = 4 "
                        "when the phrase continues past bar 2)")
    args = p.parse_args(argv)
    if args.tempo_bpm is not None and args.pack not in ("s5", "s6"):
        raise SystemExit("--tempo-bpm applies to --pack s5 / s6 only (S2-S4 "
                         "stay at the felt tempo)")
    if args.tempo_bpm is not None and args.tempo_bpm <= 0:
        raise SystemExit("--tempo-bpm must be positive")

    region = args.region or (S4_REGION if args.pack in ("s4", "s5", "s6")
                             else S3_REGION)
    chop = args.chop or (S4_CHOP if args.pack == "s4" else S3_CHOP)

    aud = (Path(args.outdir) if args.outdir else OUTDIR) / f"audition_{args.pack}"
    aud.mkdir(parents=True, exist_ok=True)
    s4_meta: Optional[Dict] = None
    s5_meta: Optional[Dict] = None
    s5_extra: Optional[Dict] = None
    s6_meta: Optional[Dict] = None
    s6_extra: Optional[Dict] = None
    if args.pack == "s2":
        variants = dict(S2_VARIANTS)
    elif args.pack == "s4":
        variants, s4_meta = _s4_variants(region, chop, args.shift,
                                         args.transpose)
    elif args.pack == "s5":
        variants, s5_meta, s5_extra = _s5_variants(
            region, args.transpose, args.tempo_bpm or S5_TEMPO_BPM,
            args.wail_bars)
    elif args.pack == "s6":
        variants, s6_meta, s6_extra = _s6_variants(
            region, args.transpose, args.tempo_bpm or S6_TEMPO_BPM,
            args.wail_bars)
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
    if s5_meta is not None:
        # Suno-bound pack: structurally forbid any chop/REF variant
        has_source_audio = any(n.endswith("_REF") or "chop" in n.lower()
                               for n in variants)
        if has_source_audio:
            raise SystemExit("[s5] refusing to render a chop/REF variant "
                             "into the Suno-bound pack")
        manifest["s5"] = s5_meta
        manifest["source_audio_in_output"] = has_source_audio
        manifest["lead_delay_s"] = round(s5_extra["lead_delay_s"], 6)
        manifest.update(s5_extra["manifest"])
        np.savez(str(aud / "contour.npz"), **s5_extra["npz"])
    if s6_meta is not None:
        # Suno-bound pack: structurally forbid any chop/REF variant
        has_source_audio = any(n.endswith("_REF") or "chop" in n.lower()
                               for n in variants)
        if has_source_audio:
            raise SystemExit("[s6] refusing to render a chop/REF variant "
                             "into the Suno-bound pack")
        manifest["s6"] = s6_meta
        manifest["source_audio_in_output"] = has_source_audio
        manifest["lead_delay_s"] = round(s6_extra["lead_delay_s"], 6)
        manifest.update(s6_extra["manifest"])
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
    if s5_meta is not None:
        verification["source_audio_in_output"] = manifest[
            "source_audio_in_output"]
        verification["lead_delay_s"] = manifest["lead_delay_s"]
        verification["bpm"] = manifest["bpm"]
        verification["tempo_factor"] = manifest["tempo_factor"]
        verification["loop_s"] = manifest["loop_s"]
    if s6_meta is not None:
        verification["source_audio_in_output"] = manifest[
            "source_audio_in_output"]
        verification["drums"] = manifest["drums"]
        verification["organ_kinds"] = manifest["organ_kinds"]
        verification["lead_delay_s"] = manifest["lead_delay_s"]
        verification["bpm"] = manifest["bpm"]
        verification["tempo_factor"] = manifest["tempo_factor"]
        verification["loop_s"] = manifest["loop_s"]
        verification["lane_rms_db_vs_lead"] = {
            k: {lane: row["db_vs_lead"] for lane, row in v["lanes"].items()}
            for k, v in manifest["levels"]["per_file"].items()}
    (aud / "manifest.json").write_text(json.dumps(manifest, indent=2),
                                       encoding="utf-8")
    (aud / "verification.json").write_text(json.dumps(verification, indent=2),
                                           encoding="utf-8")
    print(json.dumps({k: v for k, v in verification.items()
                      if k != "seam_boundary_max_absdiff"}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
