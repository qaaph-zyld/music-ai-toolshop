"""O1 release gate for the Nachtfahrt beat. Read-only; exit 0 only if all pass.

Usage: python scripts/check_beat_release.py --dir <outdir>
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

LANES = ["kick", "snare", "hats", "fx", "bass808", "synthbass", "pad", "arp",
         "stabs", "lead"]
HOOKS = ["hook_a", "hook_b", "hook_c", "hook_d"]
# section name -> (first_bar, last_bar) for the sub-slice checks
BRIDGE_P1 = (61, 64)


def _line(results, name, ok, value):
    results.append((bool(ok), name, value))
    print(f"{'PASS' if ok else 'FAIL'}  {name}: {value}", flush=True)


def check_master_format(d: Path, results, fname="nachtfahrt_master.wav"):
    from toolshop.flip.master import integrated_lufs, true_peak_dbfs
    p = d / fname
    if not p.is_file():
        _line(results, f"{fname} exists", False, "missing")
        return None
    info = sf.info(str(p))
    _line(results, "main: format 44.1k/stereo/PCM_24",
          info.samplerate == 44100 and info.channels == 2 and info.subtype == "PCM_24",
          f"{info.samplerate} Hz, {info.channels} ch, {info.subtype}")
    dur = info.frames / info.samplerate
    _line(results, "main: duration 182.9-187.0 s", 182.9 <= dur <= 187.0, f"{dur:.3f} s")
    x, sr = sf.read(str(p), always_2d=True, dtype="float32")
    lufs = integrated_lufs(x, sr)
    _line(results, "main: integrated LUFS -9.0 +/- 0.5", abs(lufs + 9.0) <= 0.5,
          f"{lufs:.2f} LUFS")
    tp = true_peak_dbfs(x, sr)
    _line(results, "main: true peak <= -1.0 dBTP", tp <= -1.0, f"{tp:.3f} dBTP")
    n = int((np.abs(x) >= 0.999).sum())
    _line(results, "main: samples |x| >= 0.999 == 0", n == 0, f"{n} samples")
    return x, sr


def check_streaming(d: Path, results):
    from toolshop.flip.master import integrated_lufs, true_peak_dbfs
    p = d / "nachtfahrt_master_streaming.wav"
    if not p.is_file():
        _line(results, "streaming master exists", False, "missing")
        return
    x, sr = sf.read(str(p), always_2d=True, dtype="float32")
    lufs = integrated_lufs(x, sr)
    _line(results, "streaming: integrated LUFS -14.0 +/- 0.5", abs(lufs + 14.0) <= 0.5,
          f"{lufs:.2f} LUFS")
    tp = true_peak_dbfs(x, sr)
    _line(results, "streaming: true peak <= -1.0 dBTP", tp <= -1.0, f"{tp:.3f} dBTP")


def check_premix(d: Path, results):
    from toolshop.premaster import analyze_premaster
    p = d / "nachtfahrt_premix.wav"
    if not p.is_file():
        _line(results, "premix exists", False, "missing")
        return
    rep = analyze_premaster(p)
    _line(results, "premix: analyze_premaster has no FAIL", not rep["failing_gates"],
          f"verdict={rep['verdict']} failing={rep['failing_gates']}")
    g2 = next((g for g in rep["gates"] if g["name"] == "low_band_corr_mean"), None)
    _line(results, "premix: low-band-mono gate PASS",
          g2 is not None and g2["verdict"] == "PASS",
          f"{g2['verdict']} value={g2['value']}" if g2 else "gate missing")


def section_checks(rel: dict, results):
    """``rel``: section name -> LU relative to the mean of the 4 hooks."""
    def chk(label, name, ok, v):
        _line(results, f"section {label}", ok, f"{name}={v:+.2f} LU")
    chk("intro <= -6 LU", "intro", rel["intro"] <= -6.0, rel["intro"])
    for v in ("verse1", "verse2"):
        chk(f"{v} in [-6,-2] LU", v, -6.0 <= rel[v] <= -2.0, rel[v])
    chk("bridge part 1 (bars 61-64) <= -4 LU", "bridge_p1", rel["bridge_p1"] <= -4.0,
        rel["bridge_p1"])
    chk("outro (bars 77-80) <= -6 LU", "outro", rel["outro"] <= -6.0, rel["outro"])
    hooks = [rel[h] for h in HOOKS]
    spread = max(hooks) - min(hooks)
    _line(results, "section hooks max-min <= 1.5 LU", spread <= 1.5,
          f"{spread:.2f} LU ({', '.join(f'{h:+.2f}' for h in hooks)})")


def measure_sections(x: np.ndarray, sr: int) -> dict:
    from toolshop.beat import nachtfahrt as nf
    from toolshop.flip.master import integrated_lufs
    lufs = {}
    for s in nf.section_map():
        lufs[s["name"]] = integrated_lufs(
            x[int(s["start_s"] * sr):int(s["end_s"] * sr)], sr)
    lufs["bridge_p1"] = integrated_lufs(
        x[int(nf._bar_t(BRIDGE_P1[0]) * sr):int(nf._bar_t(BRIDGE_P1[1] + 1) * sr)], sr)
    ref = float(np.mean([lufs[h] for h in HOOKS]))
    return {k: v - ref for k, v in lufs.items()}


def residual_db(stems: list, premix: np.ndarray) -> float:
    n = premix.shape[0]
    tot = np.zeros_like(premix, dtype=np.float64)
    for s in stems:
        m = min(n, s.shape[0])
        tot[:m] += s[:m]
    res = np.sqrt(np.mean((tot - premix) ** 2))
    ref = np.sqrt(np.mean(premix.astype(np.float64) ** 2))
    return float(20 * np.log10(max(res, 1e-30) / ref))


def check_stems(d: Path, results):
    pm = d / "nachtfahrt_premix.wav"
    paths = [d / "stems_mixed" / f"{n}.wav" for n in LANES]
    missing = [p.name for p in paths if not p.is_file()]
    if missing or not pm.is_file():
        _line(results, "stem integrity", False, f"missing {missing or 'premix'}")
        return
    premix, _ = sf.read(str(pm), always_2d=True, dtype="float64")
    stems = [sf.read(str(p), always_2d=True, dtype="float64")[0] for p in paths]
    r = residual_db(stems, premix)
    _line(results, "stem integrity: residual <= -40 dB rel premix", r <= -40.0,
          f"{r:.1f} dB")


def check_manifest(d: Path, results):
    p = d / "release_manifest.json"
    if not p.is_file():
        _line(results, "manifest exists", False, "missing")
        return None
    m = json.loads(p.read_text(encoding="utf-8"))
    _line(results, "manifest: source_audio_in_output == false",
          m.get("source_audio_in_output") is False, m.get("source_audio_in_output"))
    _line(results, "manifest: files_read_during_render == []",
          m.get("files_read_during_render") == [], m.get("files_read_during_render"))
    _line(results, "manifest: composition_hash present", bool(m.get("composition_hash")),
          str(m.get("composition_hash"))[:16])
    _line(results, "manifest: build_started_utc present", bool(m.get("build_started_utc")),
          m.get("build_started_utc"))
    return m


def check_freshness(d: Path, m: dict, results):
    if not m or not m.get("build_started_utc") or not m.get("artifacts"):
        _line(results, "freshness: artifacts mtime >= build_started_utc", False,
              "no manifest/artifacts")
        return
    t0 = datetime.fromisoformat(m["build_started_utc"]).timestamp()
    stale = []
    for a in m["artifacts"]:
        p = d / a["path"]
        if not p.is_file() or p.stat().st_mtime < t0:
            stale.append(a["path"])
    _line(results, "freshness: artifacts mtime >= build_started_utc", not stale,
          f"{len(m['artifacts'])} artifacts, stale={stale}")


def run(d: Path) -> int:
    results: list = []
    main = check_master_format(d, results)
    check_streaming(d, results)
    check_premix(d, results)
    if main is not None:
        section_checks(measure_sections(*main), results)
    else:
        _line(results, "section loudness", False, "no main master")
    check_stems(d, results)
    m = check_manifest(d, results)
    check_freshness(d, m, results)
    bad = [r for r in results if not r[0]]
    print(f"check_beat_release: {'PASS' if not bad else 'FAIL'} "
          f"({len(results) - len(bad)}/{len(results)})", flush=True)
    return 0 if not bad else 1


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", required=True)
    a = ap.parse_args()
    return run(Path(a.dir))


if __name__ == "__main__":
    sys.exit(main())
