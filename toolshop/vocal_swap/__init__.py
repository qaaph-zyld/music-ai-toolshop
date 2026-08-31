"""Vocal-swap lane: replace a Suno track's vocal with your own, mixed and mastered.

Two inputs, one deliverable:

    suno track (full mix, AI vocal)  +  your vocal take
        -> instrumental (stem separation)
        -> vocal prep (clean, HPF, DC, gate)
        -> alignment (offset, optional tempo match)
        -> mix (loudness-matched sum, optional ducking)
        -> premaster gates (M4) - refuses to master a broken premaster
        -> master (mastering_tool master_pipeline_v3.sh via WSL)
        -> verification (LUFS/TP against the profile's own targets)

Every stage writes an artifact and a manifest entry, so a run resumes instead of
restarting - the same discipline `toolshop/batch.py` applies to corpora, applied
here to the stages of one track.
"""

from .pipeline import (  # noqa: F401
    SwapConfig,
    SwapResult,
    StageRecord,
    run_swap,
    STAGES,
)
