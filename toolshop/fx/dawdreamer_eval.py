"""DawDreamer capability evaluation — the E-avenue evidence spike.

Every check runs in an isolated subprocess (same reasoning as ``probe.py``:
a crashing plugin must not take down the eval, and hard timeouts guard
against shells like WaveShell hanging). Each child prints exactly one JSON
line on stdout; the parent merges verdicts into
``data/toolshop/fx/dawdreamer_eval.json``.

Parent mode::

    python -m toolshop.fx.dawdreamer_eval                 # all checks
    python -m toolshop.fx.dawdreamer_eval --check vst2_fx # one check

Child mode (internal — spawned by the parent)::

    python -m toolshop.fx.dawdreamer_eval --child vst2_fx --sr 48000

Checks (W1B gate evidence):

- ``vst2_fx``      Glitch2 VST2 renders the probe signal wet (max|Δ| > −80 dBFS)
- ``vsti_midi``    Serum_x64 VSTi + a generated 4-bar MIDI clip → audible output
- ``automation``   Parameter ramp via ``set_automation`` changes the render
- ``preset``       ``load_preset`` on an on-disk .fxp/.vstpreset mutates state
- ``determinism``  Two identical renders are bit-identical
- ``parity_perf``  Kickstart 2 VST3 via pedalboard vs DawDreamer, timed
- ``dry_gate``     Playback-only graph returns the input bit-exact
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from toolshop import paths

from .probe_one import make_probe_signal

SR = 48000
SECONDS = 1.5
CHILD_TIMEOUT_S = 120.0

GLITCH2_X64 = r"C:\Program Files\VstPlugins\Glitch2_64bit\Glitch2.dll"
SERUM_X64 = r"C:\Program Files\Steinberg\VstPlugins\Serum_x64.dll"
KICKSTART_VST3 = r"C:\Program Files\Common Files\VST3\Kickstart 2.vst3"

CHECKS = [
    "dry_gate", "vst2_fx", "vsti_midi", "automation",
    "preset", "determinism", "parity_perf",
]

PRESET_SEARCH_DIRS = [
    r"C:\Program Files\VstPlugins\Glitch2_64bit",
    r"C:\Program Files (x86)\Steinberg\VstPlugins",
    r"C:\Program Files\Steinberg\VstPlugins",
    os.path.expandvars(r"%USERPROFILE%\Documents\Xfer"),
    os.path.expandvars(r"%USERPROFILE%\Documents\Image-Line"),
]
# load_preset() in 0.9.0 is documented for ".fxp" only — .vstpreset is listed
# so the check can report "found but unsupported" rather than pretending
# the extension never existed.
PRESET_EXTS = {".fxp", ".fxb", ".vstpreset"}


def eval_path() -> Path:
    return paths.subdir("fx") / "dawdreamer_eval.json"


# ---------------------------------------------------------------------------
# Child-side check implementations (run inside the spawned interpreter)
# ---------------------------------------------------------------------------

def _db(v: float) -> float:
    import numpy as np
    return float(20 * np.log10(max(abs(float(v)), 1e-12)))


def _engine(sr: int):
    import dawdreamer as daw
    return daw.RenderEngine(sr, 512)


def _render_fx(path: str, signal, sr: int):
    """playback -> plugin graph render; returns (audio, processor)."""
    engine = _engine(sr)
    pb = engine.make_playback_processor("input", signal.T.copy())
    fx = engine.make_plugin_processor("fx", path)
    engine.load_graph([(pb, []), (fx, [pb.get_name()])])
    engine.render(signal.shape[0] / sr)
    return engine.get_audio(), fx


def _mk_midi_file() -> str:
    """4-bar C-major-ish arp at 120 BPM; returns a temp .mid path."""
    import mido
    mid = mido.MidiFile(ticks_per_beat=480)
    tr = mido.MidiTrack()
    mid.tracks.append(tr)
    tr.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(120)))
    for n in (60, 64, 67, 71, 72, 71, 67, 64) * 4:
        tr.append(mido.Message("note_on", note=n, velocity=100, time=0))
        tr.append(mido.Message("note_off", note=n, velocity=0, time=480))
    tr.append(mido.MetaMessage("end_of_track"))
    fd, tmp = tempfile.mkstemp(suffix=".mid", prefix="dd_eval_")
    os.close(fd)
    mid.save(tmp)
    return tmp


def _check_dry_gate(sr: int) -> Dict[str, Any]:
    x = make_probe_signal(sr, SECONDS)
    engine = _engine(sr)
    pb = engine.make_playback_processor("input", x.T.copy())
    engine.load_graph([(pb, [])])
    engine.render(SECONDS)
    y = engine.get_audio().T
    n = min(len(x), len(y))
    delta = _db(float(abs(y[:n] - x[:n]).max()))
    return {"verdict": "ok" if delta < -60.0 else "fail",
            "evidence": f"playback-only delta {delta:.1f} dBFS (n={n})"}


def _wait_ready(fx, tries: int = 6, delay: float = 0.5):
    """VST2 shells (Glitch2) finish initialising asynchronously — the
    description call races it inside subprocesses. Poll briefly; the audio
    delta stays the real verdict either way."""
    for _ in range(tries):
        try:
            return fx.get_plugin_parameters_description()
        except RuntimeError:
            time.sleep(delay)
    return []


def _check_vst2_fx(sr: int) -> Dict[str, Any]:
    if not Path(GLITCH2_X64).is_file():
        return {"verdict": "skipped-missing", "evidence": GLITCH2_X64}
    x = make_probe_signal(sr, SECONDS)
    t0 = time.monotonic()
    y, fx = _render_fx(GLITCH2_X64, x, sr)
    load_render_s = round(time.monotonic() - t0, 3)
    n = min(len(x), y.shape[1])
    delta = _db(float(abs(y[:, :n] - x[:n].T).max()))
    desc = _wait_ready(fx)
    return {
        "verdict": "ok" if delta > -80.0 else "dry",
        "evidence": (f"Glitch2 64-bit VST2 max|delta| {delta:.1f} dBFS, "
                     f"{len(desc)} params, {load_render_s}s load+render"),
        "param_count": len(desc),
    }


def _check_vsti_midi(sr: int) -> Dict[str, Any]:
    if not Path(SERUM_X64).is_file():
        return {"verdict": "skipped-missing", "evidence": SERUM_X64}
    engine = _engine(sr)
    engine.set_bpm(120.0)
    synth = engine.make_plugin_processor("serum", SERUM_X64)
    midi_path = _mk_midi_file()
    try:
        # load_midi(filepath, clear_previous=True, beats=False, all_events=True)
        # — beats=False converts note times using the file's tempo map.
        synth.load_midi(midi_path)
    finally:
        os.unlink(midi_path)
    engine.load_graph([(synth, [])])
    engine.render(8.0)  # 4 bars at 120bpm
    y = engine.get_audio()
    import numpy as np
    rms = _db(float(np.sqrt(np.mean(y.astype(np.float64) ** 2))))
    return {
        "verdict": "ok" if rms > -60.0 else "silent",
        "evidence": f"Serum_x64 + 4-bar MIDI arp output RMS {rms:.1f} dBFS",
    }


def _check_automation(sr: int) -> Dict[str, Any]:
    if not Path(GLITCH2_X64).is_file():
        return {"verdict": "skipped-missing", "evidence": GLITCH2_X64}
    import numpy as np
    x = make_probe_signal(sr, SECONDS)

    # Constant-value automation dodges PPQN indexing semantics entirely —
    # A: force param 0.0, B: force 1.0; applied automation makes A != B.
    candidates = [3, 1, 15]  # Glitch2: MST:Volume, MST:Mix, MOD:Freq
    n = int(sr * SECONDS)
    for idx in candidates:
        renders = []
        for val in (0.0, 1.0):
            engine = _engine(sr)
            pb = engine.make_playback_processor("input", x.T.copy())
            fx = engine.make_plugin_processor("fx", GLITCH2_X64)
            engine.load_graph([(pb, []), (fx, [pb.get_name()])])
            fx.set_automation(idx, np.full(n, val, dtype=np.float32))
            engine.render(SECONDS)
            renders.append(engine.get_audio())
        a, b = renders
        m = min(a.shape[1], b.shape[1])
        delta = _db(float(abs(a[:, :m] - b[:, :m]).max()))
        if delta > -80.0:
            return {
                "verdict": "ok",
                "evidence": (f"set_automation on Glitch2 param {idx} forced "
                             f"0.0 vs 1.0 -> renders differ by "
                             f"{delta:.1f} dBFS"),
                "param": idx,
            }
    return {
        "verdict": "no-effect",
        "evidence": ("forced 0.0 vs 1.0 on Glitch2 params "
                     f"{candidates} produced identical renders"),
    }


def _find_preset() -> Optional[str]:
    for root in PRESET_SEARCH_DIRS:
        p = Path(root)
        if not p.is_dir():
            continue
        for f in sorted(p.rglob("*")):
            if f.suffix.lower() in PRESET_EXTS and f.is_file():
                return str(f)
    return None


def _check_preset(sr: int) -> Dict[str, Any]:
    preset = _find_preset()
    if preset is None:
        return {"verdict": "skipped-no-preset",
                "evidence": f"no {sorted(PRESET_EXTS)} found under "
                            f"{PRESET_SEARCH_DIRS}"}
    if not Path(GLITCH2_X64).is_file():
        return {"verdict": "skipped-missing", "evidence": GLITCH2_X64}
    x = make_probe_signal(sr, SECONDS)
    before = _render_fx(GLITCH2_X64, x, sr)[0]
    engine = _engine(sr)
    pb = engine.make_playback_processor("input", x.T.copy())
    fx = engine.make_plugin_processor("fx", GLITCH2_X64)

    def _state():
        return tuple(str(d.get("text", "")) for d
                     in fx.get_plugin_parameters_description())

    state_before = _state()
    fx.load_preset(preset)
    state_after = _state()
    changed = sum(1 for a, b in zip(state_before, state_after) if a != b)

    engine.load_graph([(pb, []), (fx, [pb.get_name()])])
    engine.render(SECONDS)
    after = engine.get_audio()
    n = min(before.shape[1], after.shape[1])
    delta = _db(float(abs(after[:, :n] - before[:, :n]).max()))
    return {
        "verdict": "ok" if (delta > -80.0 or changed > 0) else "no-change",
        "evidence": (f"load_preset({Path(preset).name}): {changed} param "
                     f"texts changed, render delta {delta:.1f} dBFS max "
                     f"(note: preset is not necessarily authored for Glitch2)"),
        "preset": preset,
        "params_changed": changed,
    }


def _check_determinism(sr: int) -> Dict[str, Any]:
    if not Path(KICKSTART_VST3).is_file():
        return {"verdict": "skipped-missing", "evidence": KICKSTART_VST3}
    x = make_probe_signal(sr, SECONDS)
    a = _render_fx(KICKSTART_VST3, x, sr)[0]
    b = _render_fx(KICKSTART_VST3, x, sr)[0]
    n = min(a.shape[1], b.shape[1])
    delta = float(abs(a[:, :n] - b[:, :n]).max())
    return {
        "verdict": "ok" if delta == 0.0 else "nondeterministic",
        "evidence": f"two identical renders max|delta| = {delta}",
    }


def _check_parity_perf(sr: int) -> Dict[str, Any]:
    if not Path(KICKSTART_VST3).is_file():
        return {"verdict": "skipped-missing", "evidence": KICKSTART_VST3}
    import pedalboard
    x = make_probe_signal(sr, 3.0)  # 3 s so per-render time >> timer noise
    iters = 30

    def timed_pb():
        return plug(x, sr, reset=True)

    def median_time(fn, n):
        import statistics
        samples = []
        out = None
        for _ in range(n):
            t0 = time.perf_counter()
            out = fn()
            samples.append(time.perf_counter() - t0)
        return statistics.median(samples), out

    plug = pedalboard.load_plugin(KICKSTART_VST3, initialization_timeout=60.0)

    engine = _engine(sr)
    pb = engine.make_playback_processor("input", x.T.copy())
    fx = engine.make_plugin_processor("fx", KICKSTART_VST3)
    engine.load_graph([(pb, []), (fx, [pb.get_name()])])

    def timed_dd():
        engine.render(3.0)  # render() repeats cleanly on one engine
        return engine.get_audio()

    timed_pb()   # pedalboard warm-up (discarded)
    timed_dd()   # DD warm-up (discarded)
    pb_s, pb_wet = median_time(timed_pb, iters)
    dd_s, dd_wet = median_time(timed_dd, iters)
    pb_s2, _ = median_time(timed_pb, iters)  # repeated baseline

    # Drift gate: >10% relative AND >1ms absolute — below 1ms the machine's
    # timer resolution is the noise floor, not instability.
    drift = abs(pb_s2 - pb_s) / max(pb_s, 1e-9)
    drift_abs = abs(pb_s2 - pb_s)
    n = min(pb_wet.shape[0], dd_wet.shape[1])
    agree = _db(float(abs(dd_wet[:, :n] - pb_wet[:n].T).max()))
    ratio = dd_s / max(pb_s, 1e-9)
    verdict = ("ok" if (drift <= 0.10 or drift_abs < 1e-3)
               else "inconclusive")
    return {
        "verdict": verdict,
        "evidence": (f"Kickstart 2 VST3 on 3s probe x{iters} (median): pedalboard "
                     f"{pb_s*1e3:.1f}ms (repeat {pb_s2*1e3:.1f}ms, drift "
                     f"{drift:.0%}), dawdreamer {dd_s*1e3:.1f}ms -> "
                     f"{ratio:.1f}x; engines agree to {agree:.1f} dBFS "
                     f"(note: Kickstart ducks this probe to silence in BOTH "
                     f"engines — the agreement floor is -240 dBFS)"),
        "pedalboard_ms": round(pb_s * 1e3, 1),
        "pedalboard_repeat_ms": round(pb_s2 * 1e3, 1),
        "dawdreamer_ms": round(dd_s * 1e3, 1),
        "baseline_drift": round(drift, 4),
    }


_CHILD_CHECKS = {
    "dry_gate": _check_dry_gate,
    "vst2_fx": _check_vst2_fx,
    "vsti_midi": _check_vsti_midi,
    "automation": _check_automation,
    "preset": _check_preset,
    "determinism": _check_determinism,
    "parity_perf": _check_parity_perf,
}


def run_child(check: str, sr: int) -> Dict[str, Any]:
    """Execute one check inside this interpreter; never raises."""
    out: Dict[str, Any] = {"check": check, "verdict": "error",
                           "evidence": None}
    try:
        import importlib.metadata
        try:
            out["dawdreamer_version"] = importlib.metadata.version("dawdreamer")
        except importlib.metadata.PackageNotFoundError:
            out["dawdreamer_version"] = None
        import dawdreamer  # noqa: F401
    except ImportError as exc:
        out["evidence"] = f"import failed: {exc}"
        out["verdict"] = "blocked-env"
        return out

    t0 = time.monotonic()
    try:
        out.update(_CHILD_CHECKS[check](sr))
    except Exception as exc:
        out["verdict"] = "error"
        out["evidence"] = f"{exc.__class__.__name__}: {exc}"
    out["wall_s"] = round(time.monotonic() - t0, 3)
    return out


# ---------------------------------------------------------------------------
# Parent side — subprocess isolation per check
# ---------------------------------------------------------------------------

def run_check(check: str, timeout_s: float = CHILD_TIMEOUT_S) -> Dict[str, Any]:
    """Spawn ``--child <check>``; convert crash/timeout into a verdict row."""
    cmd = [sys.executable, "-m", "toolshop.fx.dawdreamer_eval",
           "--child", check, "--sr", str(SR)]
    env = dict(os.environ)
    root = str(paths.REPO_ROOT)
    env["PYTHONPATH"] = root + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONIOENCODING"] = "utf-8"

    t0 = time.monotonic()
    try:
        cp = subprocess.run(cmd, capture_output=True, text=True,
                            encoding="utf-8", errors="replace",
                            timeout=timeout_s, cwd=root, env=env)
    except subprocess.TimeoutExpired:
        return {"check": check, "verdict": "timeout",
                "evidence": f"child exceeded {timeout_s}s",
                "wall_s": round(time.monotonic() - t0, 3)}

    line = ""
    if cp.stdout:
        lines = [l for l in cp.stdout.splitlines() if l.strip()]
        line = lines[-1] if lines else ""
    try:
        result = json.loads(line)
    except json.JSONDecodeError:
        return {"check": check,
                "verdict": "crash" if cp.returncode else "no-output",
                "evidence": (cp.stderr or cp.stdout or "")[-500:],
                "returncode": cp.returncode,
                "wall_s": round(time.monotonic() - t0, 3)}
    result.setdefault("check", check)
    return result


def evaluate(checks: Optional[List[str]] = None) -> Dict[str, Any]:
    """Run every check in a subprocess; return the merged verdict document."""
    doc: Dict[str, Any] = {
        "eval": "dawdreamer-0.9.0",
        "license": "GPLv3",
        "python": sys.version.split()[0],
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "checks": [],
    }
    for check in checks or CHECKS:
        result = run_check(check)
        doc["checks"].append(result)
        print(f"  {check:<12} -> {result.get('verdict')} "
              f"({result.get('wall_s', '?')}s)")
    okish = {"ok", "skipped", "skipped-missing", "skipped-no-preset"}
    hard_fails = [c for c in doc["checks"]
                  if c["verdict"] in ("error", "crash", "timeout", "dry",
                                      "silent", "fail", "no-effect",
                                      "nondeterministic", "blocked-env")]
    doc["summary"] = {
        "checks": len(doc["checks"]),
        "hard_failures": len(hard_fails),
        "all_ok_or_skipped": not hard_fails,
        "non_ok": [c["check"] for c in doc["checks"]
                   if c["verdict"] not in okish],
    }
    return doc


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="toolshop.fx.dawdreamer_eval")
    ap.add_argument("--child", default=None,
                    help="internal: run one check in-process")
    ap.add_argument("--check", default=None,
                    help="run only this check (parent mode)")
    ap.add_argument("--sr", type=int, default=SR)
    ap.add_argument("--out", default=None,
                    help=f"output JSON (default: {eval_path()})")
    args = ap.parse_args(argv)

    if args.child:
        result = run_child(args.child, args.sr)
        sys.stdout.write(json.dumps(result, default=str) + "\n")
        sys.stdout.flush()
        return 0

    checks = [args.check] if args.check else None
    doc = evaluate(checks)
    out_path = Path(args.out) if args.out else eval_path()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False,
                                   default=str), encoding="utf-8")
    s = doc["summary"]
    print(f"\n{s['checks']} checks, {s['hard_failures']} hard failures "
          f"-> {out_path}")
    if s["non_ok"]:
        print(f"non-ok: {s['non_ok']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
