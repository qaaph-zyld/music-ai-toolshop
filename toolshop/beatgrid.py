"""Beat grid and downbeat estimation, with MIDI click export (H2-M3, #049).

**The gap this fills.** `reverse_engineering_adapter` already called
``librosa.beat.beat_track`` and then threw the result away, keeping only
``beat_count`` — an integer. The grid itself, which is what any downstream tool
actually needs (Sample Forge slicing, T9's E5 universal pack, a DAW click track),
was computed and discarded on every analysis. Downbeats did not exist anywhere in
the repo.

**On downbeats — a heuristic, labelled as one.** librosa has no downbeat model.
This assumes **4/4** and picks the phase whose beats carry the most onset energy:
in most popular music the bar's first beat is the most strongly accented. That is
derivable from audio and cheap, but it is inference, not detection, so:

* ``time_signature_assumed`` is always in the output — nothing here *detects* metre;
* ``downbeat_confidence`` reports how much better the chosen phase scored than the
  runner-up. A low value means the phases were nearly indistinguishable and the
  downbeats may be offset by a beat or more.

Reporting a bar line the caller cannot question would repeat the mistake in
#048, where sections carried invented "chorus" labels a consumer had no way to
distrust.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

DEFAULT_BEATS_PER_BAR = 4
#: General MIDI percussion notes for the click track.
CLICK_DOWNBEAT_NOTE = 76  # High Woodblock
CLICK_BEAT_NOTE = 77      # Low Woodblock


@dataclass
class BeatGrid:
    """A track's beat grid and inferred bar lines."""

    tempo: float
    beat_times: List[float]
    downbeat_times: List[float]
    beats_per_bar: int
    #: How much better the chosen downbeat phase scored than the runner-up, 0-1.
    #: Low means the phases were nearly indistinguishable.
    downbeat_confidence: float
    #: Median seconds between beats — a steadiness cross-check on `tempo`.
    median_beat_interval: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tempo": round(float(self.tempo), 2),
            "beat_count": len(self.beat_times),
            "beat_times": [round(float(t), 4) for t in self.beat_times],
            "downbeat_times": [round(float(t), 4) for t in self.downbeat_times],
            "bar_count": len(self.downbeat_times),
            "beats_per_bar": self.beats_per_bar,
            "time_signature_assumed": f"{self.beats_per_bar}/4",
            "downbeat_confidence": round(float(self.downbeat_confidence), 4),
            "median_beat_interval": round(float(self.median_beat_interval), 4),
            "method": "librosa beat_track + onset-strength phase selection",
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "BeatGrid":
        """Rebuild a grid from its serialised form (e.g. a dossier's `beat_grid`)."""
        return cls(
            tempo=float(d.get("tempo", 0.0)),
            beat_times=[float(t) for t in d.get("beat_times", [])],
            downbeat_times=[float(t) for t in d.get("downbeat_times", [])],
            beats_per_bar=int(d.get("beats_per_bar", DEFAULT_BEATS_PER_BAR)),
            downbeat_confidence=float(d.get("downbeat_confidence", 0.0)),
            median_beat_interval=float(d.get("median_beat_interval", 0.0)),
        )


def estimate_downbeat_phase(
    beat_times: np.ndarray,
    onset_env: np.ndarray,
    sr: int,
    hop_length: int = 512,
    beats_per_bar: int = DEFAULT_BEATS_PER_BAR,
) -> tuple[int, float]:
    """Pick which beat of each bar is the downbeat.

    Scores every candidate phase by the mean onset strength of the beats it would
    make downbeats, and returns ``(phase, confidence)``. Confidence is the
    normalised gap to the runner-up: near 0 means the phases were effectively tied
    and the bar lines should not be trusted.
    """
    if beat_times.size == 0 or onset_env.size == 0:
        return 0, 0.0

    frames = np.clip(
        (beat_times * sr / hop_length).astype(int), 0, len(onset_env) - 1
    )
    strengths = onset_env[frames]

    scores = []
    for phase in range(beats_per_bar):
        sel = strengths[phase::beats_per_bar]
        scores.append(float(sel.mean()) if sel.size else 0.0)

    scores_arr = np.asarray(scores)
    best = int(np.argmax(scores_arr))
    if scores_arr.size < 2 or scores_arr.max() <= 0:
        return best, 0.0

    ordered = np.sort(scores_arr)[::-1]
    confidence = float((ordered[0] - ordered[1]) / (ordered[0] + 1e-12))
    return best, confidence


def analyze_beats(
    y: np.ndarray,
    sr: int,
    beats_per_bar: int = DEFAULT_BEATS_PER_BAR,
) -> BeatGrid:
    """Extract the beat grid and infer bar lines."""
    import librosa

    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, onset_envelope=onset_env)
    tempo = float(np.atleast_1d(tempo)[0])
    beat_frames = np.asarray(beat_frames).reshape(-1)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)

    phase, confidence = estimate_downbeat_phase(
        beat_times, onset_env, sr, beats_per_bar=beats_per_bar
    )
    downbeats = beat_times[phase::beats_per_bar] if beat_times.size else np.array([])

    intervals = np.diff(beat_times) if beat_times.size > 1 else np.array([0.0])

    return BeatGrid(
        tempo=tempo,
        beat_times=[float(t) for t in beat_times],
        downbeat_times=[float(t) for t in downbeats],
        beats_per_bar=beats_per_bar,
        downbeat_confidence=confidence,
        median_beat_interval=float(np.median(intervals)) if intervals.size else 0.0,
    )


def write_click_midi(grid: BeatGrid, out_path: Path) -> Path:
    """Write the grid as a MIDI click track.

    Downbeats get a distinct, louder note so the bar lines are audible when the
    click is dropped onto a DAW timeline next to the audio — which is also the
    quickest way for a human to hear whether the phase estimate is wrong.
    """
    import pretty_midi

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    pm = pretty_midi.PrettyMIDI(initial_tempo=max(1.0, float(grid.tempo)))
    drum = pretty_midi.Instrument(program=0, is_drum=True, name="click")
    downbeats = set(round(t, 4) for t in grid.downbeat_times)

    for t in grid.beat_times:
        is_down = round(t, 4) in downbeats
        drum.notes.append(
            pretty_midi.Note(
                velocity=110 if is_down else 70,
                pitch=CLICK_DOWNBEAT_NOTE if is_down else CLICK_BEAT_NOTE,
                start=float(t),
                end=float(t) + 0.05,
            )
        )

    pm.instruments.append(drum)
    pm.write(str(out_path))
    return out_path
