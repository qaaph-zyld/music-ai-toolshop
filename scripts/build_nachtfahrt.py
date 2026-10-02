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


def render_stage(outdir: Path, sr: int) -> dict:
    started = datetime.now(timezone.utc).isoformat()
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


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stage", choices=["render"], required=True)
    ap.add_argument("--outdir", default=DEFAULT_OUT)
    ap.add_argument("--sr", type=int, default=44100)
    a = ap.parse_args(argv)
    man = render_stage(Path(a.outdir), a.sr)
    print(f"rendered {len(man['lanes'])} lanes; files_read="
          f"{len(man['files_read_during_render'])}")
    return 1 if man["files_read_during_render"] else 0


if __name__ == "__main__":
    sys.exit(main())
