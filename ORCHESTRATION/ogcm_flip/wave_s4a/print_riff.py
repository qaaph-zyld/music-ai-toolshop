"""S4 step-2 evidence: extract_riff on region_54_67_raw.mid, printed in both
keys (native F#m, and transposed -4 -> Dm), plus key estimate + stats."""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from toolshop.flip import bed_lanes, sample_voices as sv  # noqa: E402

MIDI = REPO / "Stemmeca_alatkka" / "stems" / "flip_bed_lanes" / "midi" / \
    "region_54_67_raw.mid"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    notes = bed_lanes.pretty_midi_to_notes(bed_lanes.load_midi(MIDI))
    print(f"[load] {MIDI.name}: {len(notes)} raw notes, span "
          f"{min(n.start_s for n in notes):.2f}-{max(n.end_s for n in notes):.2f}s")
    tonic, mode, r = sv.estimate_key(notes)
    print(f"[key] estimate_key(raw) = {sv.PC_NAMES[tonic]} {mode} r={r:+.3f}")

    riff_native, cell_t0 = sv.extract_riff(notes)
    cell_s = 2.0 * sv.BAR_S
    riff_dm = sv.transpose(riff_native, -4)
    print(f"[riff] cell_t0={cell_t0:.2f}s cell_s={cell_s:.2f}s "
          f"n={len(riff_native)}")
    print("  on_s   dur_s  nat(F#m)      -> Dm")
    for nn, nd in zip(riff_native, riff_dm):
        print(f"  {nd.start_s:5.2f}  {nd.duration_s:4.2f}  "
              f"{sv.note_name(nn.note):>4s} ({nn.note:2d}) -> "
              f"{sv.note_name(nd.note):>4s} ({nd.note:2d})")
    print("[stats] Dm riff:", sv.riff_stats(riff_dm, cell_s))
    snapped = sum(1 for n in riff_dm if n.note % 12 not in sv.D_MINOR_PCS)
    print(f"[stats] snapped/out-of-Dm pcs in transposed riff: {snapped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
