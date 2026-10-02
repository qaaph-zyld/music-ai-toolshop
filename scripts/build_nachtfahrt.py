"""Nachtfahrt build driver. Stage 'render' (b2): dry lanes + manifests."""
import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from toolshop.beat import mixdown as mx  # noqa: E402
from toolshop.beat import nachtfahrt as nf  # noqa: E402

AUDIO_EXT = (".wav", ".flac", ".mp3", ".mid", ".midi")
DEFAULT_OUT = "D:/Projects/Music-AI-Toolshop/Stemmeca_alatkka/stems/beats/nachtfahrt"
_state = {"active": False, "opened": []}


def _hook(event, args):
    if event == "open" and _state["active"]:
        p = args[0]
        if isinstance(p, bytes):
            p = p.decode("utf-8", "replace")
        if isinstance(p, (str, Path)) and str(p).lower().endswith(AUDIO_EXT):
            _state["opened"].append(str(p))


sys.addaudithook(_hook)


def audited_call(fn, *a, **kw):
    """Run fn with the open-audit active; returns (result, audio/MIDI opens)."""
    _state["opened"] = []
    _state["active"] = True
    try:
        res = fn(*a, **kw)
    finally:
        _state["active"] = False
    return res, list(_state["opened"])


def _db(x):
    r = float(np.sqrt(np.mean(np.square(x, dtype=np.float64)))) if x.size else 0.0
    return round(20 * math.log10(r), 2) if r > 0 else None


def render_stage(outdir: Path, sr: int, started: str = None) -> dict:
    started = started or datetime.now(timezone.utc).isoformat()
    lanes, opened = audited_call(nf.render_lanes, sr)
    stems = outdir / "stems"
    stems.mkdir(parents=True, exist_ok=True)
    smap = nf.section_map()
    (outdir / "section_map.json").write_text(
        json.dumps(smap, indent=2), encoding="utf-8")
    info = []
    for name in nf.LANES:
        x = lanes[name]
        p = stems / f"{name}.wav"
        sf.write(str(p), x, sr, subtype="PCM_24")
        per = {s["name"]: _db(x[int(s["start_s"] * sr):int(s["end_s"] * sr)])
               for s in smap}
        info.append({"name": name, "path": str(p),
                     "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                     "peak": round(float(np.abs(x).max()), 5),
                     "rms_db_per_section": per})
    man = {"bpm": nf.BPM, "bars": nf.N_BARS, "sr": sr, "lanes": info,
           "composition_hash": nf.composition_hash(),
           "build_started_utc": started,
           "files_read_during_render": opened,
           "source_audio_in_output": False}
    (outdir / "render_manifest.json").write_text(
        json.dumps(man, indent=2), encoding="utf-8")
    return man


def _jload(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def mix_stage(outdir: Path, sr: int) -> dict:
    """Read the dry lanes (own outdir), process, write stems_mixed + premix."""
    lanes = {}
    for name in nf.LANES:
        x, fsr = sf.read(str(outdir / "stems" / f"{name}.wav"), always_2d=True,
                         dtype="float32")
        assert fsr == sr, (name, fsr)
        lanes[name] = x
    stems, premix, scalar = mx.mix_lanes(lanes, sr)
    sm = outdir / "stems_mixed"
    sm.mkdir(parents=True, exist_ok=True)
    for name in nf.LANES:
        sf.write(str(sm / f"{name}.wav"), stems[name], sr, subtype="PCM_24")
    sf.write(str(outdir / "nachtfahrt_premix.wav"), premix, sr, subtype="PCM_24")
    smap = nf.section_map()
    rep = {
        "gains_db": mx.GAINS_DB, "highpass_hz": mx.HP_HZ,
        "sidechain_depth_db": mx.SC_DEPTH_DB,
        "sidechain_attack_ms": mx.SC_ATTACK_MS,
        "sidechain_release_ms": mx.SC_RELEASE_MS,
        "sends_db": mx.SENDS_DB, "lead_delay": mx.DELAY,
        "rooms": {"plate": mx.PLATE_ROOM, "hall": mx.HALL_ROOM,
                  "short": mx.SHORT_ROOM},
        "mono_low_hz": mx.MONO_LOW_HZ,
        "automation_kind_db": mx.AUTO_KIND,
        "automation_bars_db": {k: [list(t) for t in v]
                               for k, v in mx.AUTO_BARS.items()},
        "premix_scalar": scalar,
        "premix_scalar_db": round(20 * math.log10(scalar), 3),
        "premix_peak_db": round(20 * math.log10(float(np.abs(premix).max())), 3),
        "stem_rms_db_per_section": {
            k: {s["name"]: _db(stems[k][int(s["start_s"] * sr):int(s["end_s"] * sr)])
                for s in smap} for k in nf.LANES},
    }
    (outdir / "mix_report.json").write_text(json.dumps(rep, indent=2),
                                            encoding="utf-8")
    return rep


def _master_pair(outdir: Path):
    from pedalboard import Compressor, Pedalboard
    from toolshop.flip.master import master_audio, true_peak_dbfs
    premix, sr = sf.read(str(outdir / "nachtfahrt_premix.wav"), always_2d=True,
                         dtype="float32")
    board = Pedalboard([Compressor(threshold_db=-16.0, ratio=2.0,
                                   attack_ms=30.0, release_ms=150.0)])
    glued = board(np.ascontiguousarray(premix.T), sr).T.astype(np.float32)
    reports = {}
    for key, fname, lufs in (("main", "nachtfahrt_master.wav", -9.0),
                             ("streaming", "nachtfahrt_master_streaming.wav", -14.0)):
        if key == "main":   # master_audio's limiter loop flattens sections
            y, rep = mx.loud_master(glued, sr, target_lufs=lufs, tp_ceiling_dbtp=-1.0)
        else:
            y, rep = master_audio(glued, sr, target_lufs=lufs)
        sf.write(str(outdir / fname), y, sr, subtype="PCM_24")
        back, _ = sf.read(str(outdir / fname), always_2d=True, dtype="float32")
        tp = true_peak_dbfs(back, sr)
        if tp > -1.0:   # PCM_24 rounding pushed the peak over the ceiling
            y = (back * np.float32(10 ** ((-1.0 - tp - 0.01) / 20))).astype(np.float32)
            sf.write(str(outdir / fname), y, sr, subtype="PCM_24")
            rep["post_write_trim_db"] = round(-1.0 - tp - 0.01, 3)
        reports[key] = rep
    return reports, sr


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _artifacts(outdir: Path) -> list:
    files = ["nachtfahrt_master.wav", "nachtfahrt_master_streaming.wav",
             "nachtfahrt_premix.wav"]
    files += [f"stems_mixed/{n}.wav" for n in nf.LANES] + ["index.html"]
    out = []
    for f in files:
        p = outdir / f
        out.append({"path": f, "sha256": _sha(p), "mtime_utc": datetime.fromtimestamp(
            p.stat().st_mtime, timezone.utc).isoformat(), "bytes": p.stat().st_size})
    return out


def _index_html(outdir: Path, meas: dict, smap: list) -> str:
    def player(label, rel):
        return (f'<tr><td>{label}</td><td><audio controls preload="none" '
                f'src="{rel}"></audio></td><td><a href="{rel}">{rel}</a></td></tr>')
    rows = [player("Master (-9 LUFS)", "nachtfahrt_master.wav"),
            player("Streaming master (-14 LUFS)", "nachtfahrt_master_streaming.wav"),
            player("Premix (no bus processing)", "nachtfahrt_premix.wav")]
    rows += [player(f"Stem: {n}", f"stems_mixed/{n}.wav") for n in nf.LANES]
    nums = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in meas["numbers"].items())
    secs = "".join(
        f"<tr><td>{s['name']}</td><td>{s['first_bar']}-{s['first_bar'] + s['n_bars'] - 1}"
        f"</td><td>{s['start_s']:.2f}-{s['end_s']:.2f} s</td>"
        f"<td>{meas['section']['lufs'][s['name']]}</td>"
        f"<td>{meas['section']['rel_lu'][s['name']]}</td></tr>" for s in smap)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Nachtfahrt \u2014 original instrumental (105 BPM, D minor)</title>
<style>body{{font-family:sans-serif;max-width:900px;margin:2em auto;background:#111;color:#ddd}}
td,th{{padding:4px 10px;border-bottom:1px solid #333;text-align:left}}a{{color:#8cf}}</style>
</head><body>
<h1>Nachtfahrt \u2014 original instrumental (105 BPM, D minor)</h1>
<p>Composed, synthesized, arranged, mixed and mastered from scratch by Claude (orchestrated waves). No samples.</p>
<h2>Audio</h2><table>{''.join(rows)}</table>
<h2>Measured numbers</h2><table>{nums}</table>
<h2>Section map (main master loudness, LU relative to mean of the 4 hooks)</h2>
<table><tr><th>section</th><th>bars</th><th>time</th><th>LUFS</th><th>rel LU</th></tr>{secs}</table>
</body></html>
"""


def master_stage(outdir: Path) -> dict:
    from toolshop.flip.master import integrated_lufs, true_peak_dbfs
    from toolshop.premaster import analyze_premaster
    rman = _jload(outdir / "render_manifest.json")
    reports, sr = _master_pair(outdir)
    (outdir / "master_report_main.json").write_text(
        json.dumps(reports["main"], indent=2), encoding="utf-8")
    (outdir / "master_report_streaming.json").write_text(
        json.dumps(reports["streaming"], indent=2), encoding="utf-8")
    main_a, _ = sf.read(str(outdir / "nachtfahrt_master.wav"), always_2d=True,
                        dtype="float32")
    sec = mx.section_loudness(main_a, sr)
    pre = analyze_premaster(outdir / "nachtfahrt_premix.wav")
    smap = nf.section_map()
    mixrep = _jload(outdir / "mix_report.json")
    numbers = {
        "main master LUFS": round(integrated_lufs(main_a, sr), 2),
        "main master true peak dBTP": round(true_peak_dbfs(main_a, sr), 2),
        "main master duration s": round(main_a.shape[0] / sr, 2),
        "streaming LUFS": reports["streaming"]["final_lufs"],
        "streaming true peak dBTP": reports["streaming"]["final_true_peak_dbtp"],
        "premix verdict": pre["verdict"],
        "premix peak dBFS": mixrep["premix_peak_db"],
        "hook spread LU": sec["hook_spread_lu"],
    }
    meas = {"numbers": numbers, "section": sec}
    (outdir / "index.html").write_text(_index_html(outdir, meas, smap),
                                       encoding="utf-8")
    man = {
        "composition_hash": rman["composition_hash"],
        "build_started_utc": rman["build_started_utc"],
        "files_read_during_render": rman["files_read_during_render"],
        "source_audio_in_output": False,
        "bpm": nf.BPM, "key": nf.KEY, "bars": nf.N_BARS, "section_map": smap,
        "mix": {k: mixrep[k] for k in (
            "gains_db", "highpass_hz", "sidechain_depth_db", "sends_db",
            "automation_kind_db", "automation_bars_db", "premix_scalar_db")}
        ,"master_chain": {"glue": {"threshold_db": -16.0, "ratio": 2.0, "attack_ms": 30.0, "release_ms": 150.0}, "main_softclip_knee": mx.SOFTCLIP_KNEE},
        "master_reports": reports, "measured": numbers,
        "section_loudness": sec,
        "premaster": {k: pre[k] for k in ("verdict", "failing_gates", "gates")},
        "artifacts": _artifacts(outdir),
    }
    (outdir / "release_manifest.json").write_text(json.dumps(man, indent=2),
                                                  encoding="utf-8")
    return man


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stage", choices=["render", "mix", "master", "all"],
                    required=True)
    ap.add_argument("--outdir", default=DEFAULT_OUT)
    ap.add_argument("--sr", type=int, default=44100)
    a = ap.parse_args(argv)
    out = Path(a.outdir)
    rc = 0
    if a.stage in ("render", "all"):
        started = datetime.now(timezone.utc).isoformat()
        man = render_stage(out, a.sr, started)
        print(f"rendered {len(man['lanes'])} lanes; files_read="
              f"{len(man['files_read_during_render'])}", flush=True)
        rc = 1 if man["files_read_during_render"] else 0
    if a.stage in ("mix", "all"):
        rep = mix_stage(out, a.sr)
        print(f"mixed; premix scalar {rep['premix_scalar_db']} dB, peak "
              f"{rep['premix_peak_db']} dBFS", flush=True)
    if a.stage in ("master", "all"):
        man = master_stage(out)
        print("master:", json.dumps(man["measured"]), flush=True)
        for k, v in man["section_loudness"]["rel_lu"].items():
            print(f"  {k}: {v} LU", flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
