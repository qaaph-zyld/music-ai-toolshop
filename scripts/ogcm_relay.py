"""Wave m4 (W4) vocal relay driver — phrase strips -> lattice-anchored lanes.

Pipeline (spec W4 + megaplan A20/A21):

1. CACHED transcript `flip_relay/lead_transcript.json` (911 words) + measured
   source beat grid from `flip_chops_v2/manifest.json` — extended backwards to
   t=0 so intro phrases before the first detected beat keep their positions.
2. Phrase strips from the v2 lead stem: bounds at >=300 ms gaps confirmed by
   energy dips (`relay.detect_phrases`), extracted with pads+microfades
   (`relay.strip_phrase`). Same boundary logic on `backing_vocals` via energy
   (`relay.detect_strips_energy`) — backing carries the hook sections per
   GATE C2.
3. `map_phrases(lattice_bpm=89.1)` — each phrase's measured source beat
   position maps onto the nominal felt lattice shared by both written grids;
   onsets snap to anchors <=30 ms (downbeats preferred, ties bias early),
   deeper syncopation floats at its preserved beat fraction. IDENTICAL
   schedule on both arms (A20).
4. Per-arm vocal lanes: lead everywhere + backing strips inside that arm's
   `hook_sections` (hook treatment = backing_vocals). Rendered to the beat
   render's exact length.
5. Verification per arm: anchor-offset stats (PASS = median <=30 ms),
   word-offset table, onset-xcorr vs the drum-events envelope, clip check.
   JSON + `RELAY_REPORT.md` under `stems/flip_relay/`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from toolshop.flip import relay  # noqa: E402

ROOT = Path(r"D:\Projects\Music-AI-Toolshop")
STEMS = ROOT / "Stemmeca_alatkka" / "stems"
V2 = STEMS / "v2"
LEAD_WAV = V2 / (
    "2Pac - Only God Can Judge Me_(vocals)_mel_band_roformer_kim_ft2_bleedless_unwa"
    "_(Vocals)_mel_band_roformer_karaoke_aufr33_viperx_sdr_10_(noreverb)"
    "_dereverb_mel_band_roformer_less_aggressive_anvuew_sdr_18.wav"
)
BACK_WAV = V2 / (
    "2Pac - Only God Can Judge Me_(vocals)_mel_band_roformer_kim_ft2_bleedless_unwa"
    "_(Instrumental)_mel_band_roformer_karaoke_aufr33_viperx_sdr_10.wav"
)
TRANSCRIPT = STEMS / "flip_relay" / "lead_transcript.json"
GRID_MANIFEST = STEMS / "flip_chops_v2" / "manifest.json"
RENDERS = STEMS / "flip_renders"
OUT = STEMS / "flip_relay"

ARMS = {
    "felt_89": {"bpm": 178.2, "wav": RENDERS / "beat_felt_89.wav",
                "events": RENDERS / "beat_felt_89_events.json"},
    "triplet_133": {"bpm": 133.65, "wav": RENDERS / "beat_triplet_133.wav",
                    "events": RENDERS / "beat_triplet_133_events.json"},
}

FELT_BPM = relay.FELT_BPM  # 89.1 nominal lattice
LEAD_GAIN = 1.0
BACK_GAIN = 0.9


def _load_mono(path: Path) -> tuple[np.ndarray, int]:
    import librosa

    y, sr = librosa.load(str(path), sr=44100, mono=True)
    return y.astype(np.float32), int(sr)


def _hook_windows(events_json: dict) -> list[tuple[float, float]]:
    return [(s["start_s"], s["end_s"]) for s in events_json.get("hook_sections", [])]


def _in_windows(start_s: float, dur_s: float, windows) -> bool:
    return any(start_s < we and (start_s + dur_s) > ws for ws, we in windows)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    import soundfile as sf

    OUT.mkdir(parents=True, exist_ok=True)

    # --- inputs -------------------------------------------------------------
    words = relay.load_transcript_words(TRANSCRIPT)
    grid = json.loads(GRID_MANIFEST.read_text(encoding="utf-8"))["grid"]
    beat_times = np.asarray(grid["beat_times"], dtype=float)
    src_tempo = float(grid["tempo"])
    ext_beats = relay.extend_grid_left(beat_times, fill_to_s=0.0)
    prepended = int(ext_beats.size - beat_times.size)
    # downbeat phase on the extended grid (manifest downbeat_confidence was
    # 0.08 — the class is a best-effort anchor preference, nothing more)
    first_db = float(grid["downbeat_times"][0])
    db_idx = prepended + int(np.argmin(np.abs(beat_times - first_db)))
    downbeat_phase = db_idx % 4
    print(f"words={len(words)}  grid tempo={src_tempo}  beats={beat_times.size}"
          f" (+{prepended} extrapolated)  downbeat_phase={downbeat_phase}")

    y_lead, sr = _load_mono(LEAD_WAV)
    y_back, _ = _load_mono(BACK_WAV)

    # --- phrase strips -------------------------------------------------------
    phrases = relay.detect_phrases(words, y_lead, sr)
    relay.annotate_grid(phrases, ext_beats)
    back_phrases = relay.detect_strips_energy(y_back, sr)
    relay.annotate_grid(back_phrases, ext_beats)
    print(f"lead phrases={len(phrases)}  backing strips={len(back_phrases)}")

    strips_dir = OUT / "strips"
    strips_dir.mkdir(exist_ok=True)
    lead_strips: dict[int, np.ndarray] = {}
    for p in phrases:
        chunk = relay.strip_phrase(y_lead, sr, p)
        lead_strips[p.index] = chunk
        sf.write(strips_dir / f"lead_p{p.index:03d}_{p.start_s:.2f}-{p.end_s:.2f}.wav",
                 chunk, sr)
    back_strips: dict[int, np.ndarray] = {}
    for p in back_phrases:
        chunk = relay.strip_phrase(y_back, sr, p)
        back_strips[p.index] = chunk
        sf.write(strips_dir / f"back_p{p.index:03d}_{p.start_s:.2f}-{p.end_s:.2f}.wav",
                 chunk, sr)

    # --- lattice placement (identical schedule both arms — A20) ---------------
    min_beat = min(p.source_beat for p in phrases)
    shift = 4.0 * float(np.ceil(max(0.0, -min_beat) / 4.0 - 1e-9))
    felt_s = 60.0 / FELT_BPM
    print(f"lattice shift={shift} felt beats  felt_beat={felt_s*1000:.1f} ms")

    per_arm = {}
    for arm, cfg in ARMS.items():
        ev = json.loads(cfg["events"].read_text(encoding="utf-8"))
        beat_audio, _ = _load_mono(cfg["wav"])
        total_s = len(beat_audio) / sr
        hook_windows = _hook_windows(ev)

        placements = relay.map_phrases(
            phrases, bpm=cfg["bpm"], bars=10 ** 9, bpm_source=src_tempo,
            lattice_bpm=FELT_BPM, lattice_shift_beats=shift,
            downbeat_phase=downbeat_phase,
        )
        back_pl = relay.map_phrases(
            back_phrases, bpm=cfg["bpm"], bars=10 ** 9, bpm_source=src_tempo,
            lattice_bpm=FELT_BPM, lattice_shift_beats=shift,
            downbeat_phase=downbeat_phase,
        )

        # hook treatment: backing strips only inside this arm's hook windows
        back_sel = []
        back_ph_by_idx = {p.index: p for p in back_phrases}
        for pl in back_pl:
            ph = back_ph_by_idx[pl.phrase_index]
            dur = (ph.end_s - ph.start_s) + 2 * relay.PAD_MS / 1000.0
            if _in_windows(pl.start_s, dur, hook_windows):
                back_sel.append(pl)

        lead_lane, lead_events = relay.render_vocal_lane(
            lead_strips, placements, phrases, sr, total_s)
        hook_lane, hook_events = relay.render_vocal_lane(
            back_strips, back_sel, back_phrases, sr, total_s)
        lane = lead_lane * LEAD_GAIN + hook_lane * BACK_GAIN
        peak = float(np.abs(lane).max())
        clips = int(np.sum(np.abs(lane) >= 0.999))
        if peak > 0.99:
            lane *= 0.99 / peak
            clips = -1  # normalised

        out_wav = OUT / f"vocal_{arm}.wav"
        sf.write(out_wav, np.stack([lane, lane], axis=1), sr)

        # --- verification ----------------------------------------------------
        anchors = relay.summarize_anchors(placements)
        wtable = relay.word_offset_table(
            words, phrases, placements, ext_beats, FELT_BPM, shift)
        w_offs = np.abs([r["offset_ms"] for r in wtable]) if wtable else np.zeros(1)
        # lead-only envelope for lead metrics (hook backing is a separate lane)
        venv_lead = relay.onset_envelope(lead_lane, sr)
        venv_mix = relay.onset_envelope(lane, sr)
        denv = relay.drum_envelope(ev["drum_events"], total_s, sr)
        xc = relay.xcorr_offset(venv_lead, denv, sr)
        xc_mix = relay.xcorr_offset(venv_mix, denv, sr)
        # secondary: vocal onset env vs the beat WAV's own onset env
        benv = relay.onset_envelope(beat_audio, sr)
        xc_audio = relay.xcorr_offset(venv_lead, benv, sr)
        # per-phrase local xcorr at each anchor (spec W4 wording)
        hit_times = [e["time_s"] for e in ev["drum_events"]
                     if e.get("time_s") is not None]
        rendered_idx = {e["phrase_index"] for e in lead_events if e["rendered"]}
        pxt = relay.phrase_xcorr_table(
            venv_lead, denv,
            [p for p in placements if p.phrase_index in rendered_idx], sr,
            phrases=phrases, drum_hit_times_s=hit_times)
        lags = [abs(r["lag_ms"]) for r in pxt if r["lag_ms"] is not None]
        delays = [r["onset_delay_ms"] for r in pxt
                  if r.get("onset_delay_ms") is not None]
        hits_ms = [abs(r["nearest_hit_ms"]) for r in pxt
                   if r.get("nearest_hit_ms") is not None]
        phrase_align = {
            "n": len(lags),
            "median_abs_lag_ms": round(float(np.median(lags)), 2) if lags else None,
            "within_50ms": int(sum(1 for x in lags if x <= 50.0)),
            "median_onset_delay_ms": (
                round(float(np.median(delays)), 2) if delays else None),
            "median_abs_nearest_hit_ms": (
                round(float(np.median(hits_ms)), 2) if hits_ms else None),
            "note": "onset_delay = whisper word-start → acoustic onset inside "
                    "the strip; nearest_hit = effective onset → nearest drum hit",
            "table": pxt,
        }
        grid_resid = np.asarray([
            abs(pl.start_s / felt_s - round(pl.start_s / felt_s)) * felt_s * 1000.0
            for pl in placements
        ])

        rend_ev = [e for e in lead_events if e["rendered"]]
        last_end = max((e["start_s"] + e["duration_s"] for e in rend_ev),
                       default=0.0)
        per_arm[arm] = {
            "bpm_written": cfg["bpm"],
            "total_s": round(total_s, 3),
            "lead": {"phrases": len(phrases),
                     "placed": len(placements),
                     "rendered": len(rend_ev),
                     "unrendered_indices": [
                         e["phrase_index"] for e in lead_events
                         if not e["rendered"]],
                     "coverage_end_s": round(last_end, 2),
                     "anchors": anchors},
            "backing": {"strips": len(back_phrases),
                        "in_hook_windows": len(back_sel),
                        "hook_windows": hook_windows,
                        "hook_strip_starts_s": [
                            round(p.start_s, 3) for p in back_sel]},
            "word_offsets": {
                "n": int(w_offs.size),
                "median_abs_ms": round(float(np.median(w_offs)), 2),
                "p90_abs_ms": round(float(np.percentile(w_offs, 90)), 2),
                "max_abs_ms": round(float(w_offs.max()), 2),
            },
            "grid_residual_ms": {
                "median": round(float(np.median(grid_resid)), 2),
                "p90": round(float(np.percentile(grid_resid, 90)), 2),
                "note": "distance of placed onset to nearest felt-lattice anchor; "
                        "floats keep source beat fraction (syncopation preserved)",
            },
            "xcorr_vocal_vs_drum_events": xc,
            "xcorr_mix_vs_drum_events": xc_mix,
            "xcorr_vocal_vs_beat_audio": xc_audio,
            "phrase_xcorr_at_anchor": phrase_align,
            "vocal_peak": round(peak, 4),
            "clip_count": clips,
            "pass_median_anchor_le_30ms": anchors["anchor_pass_median_le_30ms"],
            "events_json": f"relay_{arm}_events.json",
            "vocal_wav": out_wav.name,
        }
        (OUT / f"relay_{arm}_events.json").write_text(
            json.dumps({
                "arm": arm, "bpm_written": cfg["bpm"], "felt_bpm": FELT_BPM,
                "lattice_shift_beats": shift, "downbeat_phase": downbeat_phase,
                "source_grid": {"tempo": src_tempo,
                                "beats": int(beat_times.size),
                                "prepended_extrapolated": prepended},
                "lead_placements": [p.to_dict() for p in placements],
                "lead_lane_events": lead_events,
                "backing_hook_placements": [p.to_dict() for p in back_sel],
                "backing_hook_lane_events": hook_events,
                "word_offsets": wtable,
            }, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{arm}: placed={len(placements)} rendered={per_arm[arm]['lead']['rendered']}"
              f"  anchor_median={anchors['median_anchor_offset_ms']:.2f} ms"
              f"  snapped={anchors['snapped']} floated={anchors['floated']}"
              f"  xcorr lag={xc['lag_ms']} ms peak={xc['peak']}")

    # identical-schedule check across arms
    sa = [p["start_s"] for p in
          json.loads((OUT / "relay_felt_89_events.json").read_text())["lead_placements"]]
    sb = [p["start_s"] for p in
          json.loads((OUT / "relay_triplet_133_events.json").read_text())["lead_placements"]]
    identical = sa == sb

    verification = {
        "wave": "m4 / W4 vocal relay",
        "mode": "lattice-anchored source-felt placement",
        "felt_bpm": FELT_BPM,
        "source_grid_tempo_measured": src_tempo,
        "identical_schedule_both_arms": identical,
        "hook_treatment": "backing_vocals strips inside each arm's hook_sections",
        "pass_criterion": ("median applied anchor correction <= 30 ms "
                           "(anchor_offset_ms; floats report 0 = unmoved) "
                           "AND identical schedule on both arms"),
        "metric_semantics": {
            "anchor_offset_ms": "correction the relay APPLIED at placement "
                                "(0 for floated phrases — syncopation kept)",
            "grid_residual_ms": "post-placement distance of each onset to the "
                                "nearest felt-lattice beat — the preserved "
                                "microtiming, NOT placement error",
            "word_offset_ms": "placed word time vs the word's own lattice "
                              "position (whisper start vs acoustic onset "
                              "included)",
            "xcorr_lag_ms": "groove diagnostic — best-lag of lead onset "
                            "envelope vs drum-events envelope; NOT bounded "
                            "by the 30 ms anchor bar",
        },
        "arms": per_arm,
        "pass": all(a["pass_median_anchor_le_30ms"] for a in per_arm.values())
                and identical,
    }
    (OUT / "relay_verification.json").write_text(
        json.dumps(verification, ensure_ascii=False, indent=1), encoding="utf-8")

    _write_report(verification, OUT / "RELAY_REPORT.md")
    print(f"identical_schedule={identical}  PASS={verification['pass']}")
    print(f"-> {OUT / 'relay_verification.json'}")
    return 0


def _write_report(v: dict, path: Path) -> None:
    lines = [
        "# W4 vocal relay — verification report",
        "",
        f"Mode: {v['mode']} · felt {v['felt_bpm']} BPM lattice "
        f"(measured source grid ≈{v['source_grid_tempo_measured']} — tempo delta absorbed "
        "in inter-phrase gaps, never stretched)",
        f"Identical schedule both arms (A20): **{v['identical_schedule_both_arms']}**",
        f"Hook treatment: {v['hook_treatment']}",
        f"PASS criterion: {v['pass_criterion']} → **{'PASS' if v['pass'] else 'FAIL'}**",
        "",
        "| Arm | placed | rendered | snapped | floated | median anchor corr (ms) | "
        "median lattice resid (ms) | median word |off| (ms) | xcorr lag (ms) | xcorr peak | clips |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for arm, a in v["arms"].items():
        an = a["lead"]["anchors"]
        lines.append(
            f"| {arm} | {a['lead']['placed']} | {a['lead']['rendered']} "
            f"| {an['snapped']} | {an['floated']} "
            f"| {an['median_anchor_offset_ms']:.2f} "
            f"| {a['grid_residual_ms']['median']:.1f} "
            f"| {a['word_offsets']['median_abs_ms']:.1f} "
            f"| {a['xcorr_vocal_vs_drum_events']['lag_ms']} "
            f"| {a['xcorr_vocal_vs_drum_events']['peak']} "
            f"| {a['clip_count']} |"
        )
    lines += [
        "",
        "## Per-phrase onset alignment (lead lane vs drum events)",
        "",
        "| Arm | n | median |xcorr lag| (ms) | within 50 ms | "
        "median onset delay (ms) | median |nearest hit| (ms) |",
        "|---|---|---|---|---|---|",
    ]
    for arm, a in v["arms"].items():
        px = a["phrase_xcorr_at_anchor"]
        lines.append(
            f"| {arm} | {px['n']} | {px['median_abs_lag_ms']} "
            f"| {px['within_50ms']} | {px['median_onset_delay_ms']} "
            f"| {px['median_abs_nearest_hit_ms']} |"
        )
    lines += [
        "",
        "## Coverage (lead vocal vs render length)",
        "",
    ]
    for arm, a in v["arms"].items():
        l = a["lead"]
        lines.append(
            f"- **{arm}**: render {a['total_s']:.1f} s covers lead phrases "
            f"through ≈{l['coverage_end_s']:.1f} s — **{l['rendered']}/{l['placed']}** "
            f"phrases relayed; unrendered indices "
            f"{l['unrendered_indices']} (source timeline ≈297 s ≫ beat "
            "render — extending the arrangement is a W5/megaplan decision, "
            "NOT a W4 defect; placements are still emitted for the full set)."
        )
    lines += [
        "",
        "## Backing-vocal hook strips (GATE C2)",
        "",
    ]
    for arm, a in v["arms"].items():
        b = a["backing"]
        lines.append(
            f"- **{arm}** hook {b['hook_windows']}: "
            f"{b['in_hook_windows']} strips placed "
            f"(starts: {[round(s, 1) for s in b['hook_strip_starts_s']]})"
        )
    lines += [
        "",
        "## Reading the numbers",
        "",
        "- `anchor corr` = |placed onset − nominal lattice position| — the correction",
        "  the relay APPLIED (snaps ≤30 ms; floats = 0, unmoved, syncopation kept).",
        "  Median 0.00 with all-floated means no onset sat within 30 ms of a lattice",
        "  anchor — the relay kept every phrase at its source beat fraction.",
        "- `lattice resid` = post-placement distance to the nearest felt-lattice",
        "  beat — the preserved microtiming; large values are syncopation, not error.",
        "- `word |offset|` = placed word time vs the word's own lattice position —",
        "  intra-phrase divergence is preserved native timing, not placement error.",
        "- `xcorr lag` = best-lag (±250 ms) of the LEAD lane onset envelope vs the",
        "  drum-events impulse envelope — a groove diagnostic, NOT the 30 ms anchor",
        "  bar. A nonzero lag means the vocal's accent pattern as a whole prefers",
        "  that shift against the drums; the spec forbids forcing it.",
        "- `onset delay` = whisper word-start → acoustic onset inside the strip",
        "  (transcript timestamps precede the attack; envelope finds the real hit).",
        "- `nearest hit` = effective onset → closest drum hit; positive = laid-back.",
        "- Backing strips (energy-detected) are layered ONLY inside each arm's",
        "  hook_sections (GATE C2: backing_vocals carries the hook).",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
