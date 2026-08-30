"""Structural segmentation of a track (H2-M2, CHANGELOG #048).

Boundaries and repetition classes from beat-synchronous chroma, via
self-similarity — the CPU-cheap route the roadmap specifies (librosa/MSAF style,
deliberately *not* the Demucs-dependent allin1).

**What this replaces.** `video_features._detect_sections` called
``librosa.segment.agglomerative(chroma, k=None)``, which raises
``ValueError: Exactly one of n_clusters and distance_threshold has to be set``
on **every** input — `k=None` is not a valid argument. A bare
``except Exception: return []`` swallowed it, so the function returned an empty
list for every track ever analysed, and the intro/verse/chorus labelling beneath
it was unreachable. That is also why T7 Sample Forge's automatic sectioning was
deferred in #018 as "dossier emits none yet": the feature had never run.

**On labels — deliberately not "chorus".** The replaced code assigned
``"intro" if i == 0 else "verse" if i % 2 == 1 else "chorus"``: index parity
dressed as musical analysis. A downstream consumer cannot tell a fabricated label
from a real one, which makes it worse than no label at all.

What *is* derivable from audio is **repetition**: which segments resemble each
other. So segments carry a ``segment_class`` (A, B, C…) and a
``repetitions`` count. The most-repeated class is reported as
``most_repeated_class`` — a hint a caller may choose to read as a chorus, with
that inference sitting in the caller rather than being baked in here as fact.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

import numpy as np

#: Target seconds per segment when estimating how many to look for.
DEFAULT_SEGMENT_SECONDS = 15.0
MIN_SEGMENTS = 2
MAX_SEGMENTS = 16
#: How many repetition classes to sort segments into.
DEFAULT_CLASSES = 4
#: Spans shorter than this are boundary artefacts, not structure, and get merged
#: into their neighbour. Observed on a 31 s track: a 0.5 s opening "segment".
MIN_SEGMENT_SECONDS = 4.0


@dataclass
class Segment:
    """One structural span."""

    start: float
    end: float
    #: Repetition class: segments sharing a letter are musically similar.
    segment_class: str
    #: How many segments in the track share this class (including this one).
    repetitions: int

    @property
    def duration(self) -> float:
        return self.end - self.start

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["start"] = round(float(self.start), 3)
        d["end"] = round(float(self.end), 3)
        d["duration"] = round(float(self.duration), 3)
        return d


def estimate_segment_count(duration_s: float, target_s: float = DEFAULT_SEGMENT_SECONDS) -> int:
    """How many segments to look for in a track of this length.

    librosa's agglomerative segmentation needs an explicit count; passing `None`
    is what made the previous implementation raise on every call.
    """
    if duration_s <= 0:
        return MIN_SEGMENTS
    return int(np.clip(round(duration_s / target_s), MIN_SEGMENTS, MAX_SEGMENTS))


def _assign_classes(features: np.ndarray, n_classes: int) -> List[int]:
    """Group segment feature vectors into repetition classes.

    Agglomerative clustering on segment-mean chroma: segments that sound alike
    land in the same class. This is the part that is genuinely derived from the
    audio, as opposed to the index parity it replaces.
    """
    from sklearn.cluster import AgglomerativeClustering

    n_segments = features.shape[0]
    if n_segments <= 1:
        return [0] * n_segments

    # Cap classes at roughly half the segment count. `min(n_classes, n_segments)`
    # looks reasonable and is useless: with 4 segments and 4 clusters every segment
    # necessarily gets its own class, so repetition can never be detected at all.
    # A verse/chorus track needs ~2 classes for 4 sections, not 4.
    k = int(max(2, min(n_classes, n_segments // 2)))
    k = min(k, n_segments)
    labels = AgglomerativeClustering(n_clusters=k).fit_predict(features)
    return [int(v) for v in labels]


def _merge_short(segments: List[Segment], min_seconds: float) -> List[Segment]:
    """Absorb sub-`min_seconds` spans into a neighbour.

    Boundary detection produces occasional slivers - a 31 s track yielded a 0.5 s
    opening "segment". A span that short is an artefact of where the boundary
    landed, not a section of the song, and emitting it invites downstream tools
    (Sample Forge especially) to slice on it.

    Merges into whichever neighbour shares its class, else the longer one.
    """
    if not segments:
        return []
    out = list(segments)
    changed = True
    while changed and len(out) > 1:
        changed = False
        for i, seg in enumerate(out):
            if seg.duration >= min_seconds:
                continue
            prev_seg = out[i - 1] if i > 0 else None
            next_seg = out[i + 1] if i + 1 < len(out) else None
            if prev_seg is not None and prev_seg.segment_class == seg.segment_class:
                target = prev_seg
            elif next_seg is not None and next_seg.segment_class == seg.segment_class:
                target = next_seg
            elif prev_seg is None:
                target = next_seg
            elif next_seg is None:
                target = prev_seg
            else:
                target = prev_seg if prev_seg.duration >= next_seg.duration else next_seg
            if target is None:
                continue
            target.start = min(target.start, seg.start)
            target.end = max(target.end, seg.end)
            out.pop(i)
            changed = True
            break
    return out


def segment_track(
    y: np.ndarray,
    sr: int,
    n_segments: Optional[int] = None,
    n_classes: int = DEFAULT_CLASSES,
    min_segment_s: float = MIN_SEGMENT_SECONDS,
) -> Dict[str, Any]:
    """Segment a track into structural spans with repetition classes.

    Args:
        y: Mono audio.
        sr: Sample rate.
        n_segments: Boundary count. ``None`` estimates from duration.
        n_classes: How many repetition classes to sort segments into.

    Returns:
        ``{"segments": [...], "n_segments": int, "most_repeated_class": str|None,
        "duration": float, "method": str}``

    Raises rather than returning an empty list on failure. The previous
    implementation's silent ``except Exception: return []`` is precisely how a
    total failure went unnoticed for the life of the feature.
    """
    import librosa

    duration = float(len(y)) / sr
    if n_segments is None:
        n_segments = estimate_segment_count(duration)

    # Beat-synchronous chroma: musically meaningful frames, and far cheaper than
    # working at raw frame rate.
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    _, beat_frames = librosa.beat.beat_track(y=y, sr=sr, trim=False)
    beat_frames = np.asarray(beat_frames).reshape(-1)

    if beat_frames.size >= 2:
        sync = librosa.util.sync(chroma, beat_frames, aggregate=np.median)
        frame_index = beat_frames
    else:
        # No usable beat grid — fall back to raw frames rather than failing.
        sync = chroma
        frame_index = np.arange(chroma.shape[1])

    n_cols = sync.shape[1]
    k = int(min(n_segments, n_cols))
    if k < MIN_SEGMENTS:
        # Too short to segment meaningfully; report the whole track as one span.
        return {
            "segments": [Segment(0.0, duration, "A", 1).to_dict()],
            "n_segments": 1,
            "most_repeated_class": "A",
            "duration": round(duration, 3),
            "method": "single-span (input too short to segment)",
        }

    bound_cols = librosa.segment.agglomerative(sync, k)
    bound_cols = np.unique(np.asarray(bound_cols).reshape(-1))

    # Map column indices back to times through whichever frame index applies.
    bound_frames = np.asarray([frame_index[min(int(c), len(frame_index) - 1)] for c in bound_cols])
    bound_times = librosa.frames_to_time(bound_frames, sr=sr)
    bound_times = np.concatenate([bound_times, [duration]])

    # Per-segment mean chroma, the feature repetition classes are built from.
    seg_features = []
    for i in range(len(bound_cols)):
        lo = int(bound_cols[i])
        hi = int(bound_cols[i + 1]) if i + 1 < len(bound_cols) else n_cols
        block = sync[:, lo:hi] if hi > lo else sync[:, lo : lo + 1]
        seg_features.append(block.mean(axis=1))
    features = np.vstack(seg_features)

    class_ids = _assign_classes(features, n_classes)
    counts: Dict[int, int] = {}
    for c in class_ids:
        counts[c] = counts.get(c, 0) + 1

    # Letter the classes by first appearance, so A is always the opening material.
    order: List[int] = []
    for c in class_ids:
        if c not in order:
            order.append(c)
    letters = {c: chr(ord("A") + i) for i, c in enumerate(order)}

    raw = [
        Segment(
            start=float(bound_times[i]),
            end=float(bound_times[i + 1]),
            segment_class=letters[class_ids[i]],
            repetitions=0,  # recounted after merging
        )
        for i in range(len(class_ids))
    ]

    segments = _merge_short(raw, min_segment_s)

    # Re-letter by first appearance AFTER merging. Letters were assigned on the
    # pre-merge sequence, so a track that collapses to one span could come back
    # labelled "B" - which reads as if an "A" existed somewhere.
    relabel: Dict[str, str] = {}
    for seg in segments:
        if seg.segment_class not in relabel:
            relabel[seg.segment_class] = chr(ord("A") + len(relabel))
    for seg in segments:
        seg.segment_class = relabel[seg.segment_class]

    # Recount repetitions AFTER merging - a count taken before would describe
    # segments that no longer exist.
    counts_by_letter: Dict[str, int] = {}
    for seg in segments:
        counts_by_letter[seg.segment_class] = counts_by_letter.get(seg.segment_class, 0) + 1
    for seg in segments:
        seg.repetitions = counts_by_letter[seg.segment_class]

    most_repeated = max(counts_by_letter, key=lambda c: counts_by_letter[c]) if counts_by_letter else None

    return {
        "segments": [s.to_dict() for s in segments],
        "n_segments": len(segments),
        "most_repeated_class": most_repeated,
        "duration": round(duration, 3),
        "method": "beat-sync chroma + agglomerative boundaries + repetition clustering",
    }
