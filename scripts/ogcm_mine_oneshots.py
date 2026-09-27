"""Mine drum one-shots from v2_drums DrumSep stems -> stems/flip_kit/ (wave W2).

Per-stem `piece_hint` mining (separated stems bypass the mixed-stem spectral
classifier — declared path, no silent fallback). Exports top-K representative
hits per kit piece (peak-normalized to 0.9) plus `kit_manifest.json` with
mining stats so the render layer and the ledger can audit what was used.

Piece map DrumSep->drill grammar:
  kick->kick, snare->snare, hh->hat, toms->tom, ride->openhat, crash->cymbal
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from toolshop.flip import drums as flip_drums

STEMS = Path(r"D:\Projects\Music-AI-Toolshop\Stemmeca_alatkka\stems\v2_drums")
OUT = Path(r"D:\Projects\Music-AI-Toolshop\Stemmeca_alatkka\stems\flip_kit")
PIECE_MAP = {
    "kick": "kick",
    "snare": "snare",
    "hh": "hat",
    "toms": "tom",
    "ride": "openhat",
    "crash": "cymbal",
}
TOP_K = 3
MAX_MINED = 24
MIN_PEAK = 0.01  # drop near-noise-floor hits (crash/ride stems are ~silent)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    OUT.mkdir(parents=True, exist_ok=True)
    manifest: dict = {"source_dir": str(STEMS), "top_k": TOP_K, "pieces": {}}
    for f in sorted(STEMS.glob("*.flac")):
        m = re.search(r"\((\w+)\)_", f.name)
        src_piece = m.group(1) if m else f.stem
        piece = PIECE_MAP.get(src_piece, src_piece)
        y, sr = sf.read(str(f), dtype="float32")
        if y.ndim > 1:
            y = y.mean(axis=1)
        shots = flip_drums.mine_one_shots(y, sr, piece_hint=piece, max_shots=MAX_MINED)
        reps = [s for s in sorted(shots, key=lambda s: s.peak, reverse=True) if s.peak >= MIN_PEAK][:TOP_K]
        entries = []
        for i, shot in enumerate(reps, 1):
            buf = flip_drums.slice_one_shot(y, shot, sr)
            peak = float(np.abs(buf).max()) or 1.0
            buf = (buf / peak * 0.9).astype(np.float32)
            name = f"{piece}_{i:02d}.wav"
            sf.write(str(OUT / name), buf, sr)
            entries.append({**shot.to_dict(), "file": name, "src_peak": round(peak, 4)})
        manifest["pieces"][piece] = {
            "src_stem": f.name,
            "src_rms": round(float(np.sqrt((y**2).mean())), 6),
            "n_mined": len(shots),
            "n_kept": len(entries),
            "reps": entries,
        }
        print(
            f"{piece:8s} stem={f.name[:50]:50s} rms={manifest['pieces'][piece]['src_rms']:.5f} "
            f"mined={len(shots):3d} kept={len(entries)} onsets={[e['onset_s'] for e in entries]}"
        )
    (OUT / "kit_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"manifest -> {OUT / 'kit_manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
