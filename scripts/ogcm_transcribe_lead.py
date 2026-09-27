"""Transcribe the v2 lead vocal ONCE and cache word timings (wave W4 prep).

faster-whisper word timings vary run-to-run (transcribe.py documents the
variance), so the spec's rule is: run once, cache the JSON, treat as the
immutable input for every downstream relay decision. Model "small"/int8
on CPU, language pinned to "en" (module default is "sr").

Input is ALREADY the dereverbed lead stem — prefer_stem/require_stem off:
we pass the stem directly rather than asking find_vocal_stem to re-search.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from toolshop import transcribe as T

LEAD = Path(
    r"D:\Projects\Music-AI-Toolshop\Stemmeca_alatkka\stems\v2"
    r"\2Pac - Only God Can Judge Me_(vocals)_mel_band_roformer_kim_ft2_bleedless_unwa"
    r"_(Vocals)_mel_band_roformer_karaoke_aufr33_viperx_sdr_10_(noreverb)"
    r"_dereverb_mel_band_roformer_less_aggressive_anvuew_sdr_18.wav"
)
OUT = Path(r"D:\Projects\Music-AI-Toolshop\Stemmeca_alatkka\stems\flip_relay")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    OUT.mkdir(parents=True, exist_ok=True)
    tr = T.transcribe_file(
        LEAD,
        model="small",
        language="en",
        compute_type="int8",
        prefer_stem=False,
        require_stem=False,
    )
    out = OUT / "lead_transcript.json"
    payload = tr.to_dict()
    payload["cached_for"] = "ogcm-flip W4 relay — immutable input, do not re-run"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"words={tr.word_count} lang={tr.language}({tr.language_probability:.2f}) "
        f"rt_factor={tr.realtime_factor:.2f} elapsed={tr.elapsed_seconds:.1f}s "
        f"mean_p={tr.mean_word_probability:.3f}"
    )
    print(f"-> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
