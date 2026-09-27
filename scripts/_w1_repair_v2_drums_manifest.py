"""W-1 one-shot: repair Stemmeca_alatkka/stems/v2_drums/manifest.json IN PLACE.

The DrumSep run emitted 6 FLACs — (kick)(snare)(toms)(hh)(crash)(ride) — but
the manifest only declared kick/snare/toms (registry pattern bug, F1). This
script adds the three orphaned stems to the manifest's `stems` map using the
canonical piece names now declared in toolshop/stem_models.py
(hihat/cymbals/ride). Metadata-only: no audio is touched, no separation
re-run.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "Stemmeca_alatkka" / "stems" / "v2_drums" / "manifest.json"

# canonical_name -> raw emission slot
EMISSIONS = {
    "hihat": "(hh)",
    "cymbals": "(crash)",
    "ride": "(ride)",
}

def main() -> int:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    stems = data.setdefault("stems", {})
    added = []
    for canonical, slot in EMISSIONS.items():
        if canonical in stems:
            continue
        fname = f"drums_{slot}_MDX23C-DrumSep-aufr33-jarredou.flac"
        fpath = MANIFEST.parent / fname
        if not fpath.exists():
            print(f"WARN: missing on disk: {fname}")
            continue
        stems[canonical] = str(fpath)
        added.append(canonical)
    # Record the repair provenance without rewriting history.
    notes = data.setdefault("repair_notes", [])
    notes.append(
        "W-1 F1 repair: added orphaned (hh)/(crash)/(ride) emissions as "
        "canonical hihat/cymbals/ride; metadata-only, no re-separation. "
        f"Added: {added}"
    )
    MANIFEST.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"repaired {MANIFEST}; added={added}; total stems={len(stems)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
