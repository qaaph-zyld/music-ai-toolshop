"""Timed lyrics via faster-whisper (H2-M5).

CTranslate2 int8 on CPU - the documented path from
`specs/2026-07-15-oss-integration-map.md`, which lists faster-whisper (MIT) as
INTEGRATE for T2/T4. This delivers **T4-v1**, the word timings that
`flow_analyzer` needs and does not currently have: today it derives "flow" from
syllable counts of *text* in the `lines` table, with no notion of when a word
lands. Syllables-per-bar and on/off-beat placement are not computable from that.
Combined with the M3 beat grid, word timings make them computable.

**The degradation axis is the source, not the backend.** There is no heuristic
fallback for speech recognition - without faster-whisper installed nothing runs
at all, so a `--require-advanced` guard in the melody-carrier sense would be
vacuous here and is deliberately not offered. The real silent degradation is
**transcribing the full mix when a vocal stem was expected**: an instrumental
under the vocal costs accuracy badly, and the output looks identical either way.
So `source` is always recorded, and `--require-stem` turns a fall-back-to-mix
into a hard failure. That is AGENTS.md's fallback discipline applied to the axis
that actually degrades here.

**Language.** Named explicitly, not auto-detected. The corpus is mixed - CrhymeTV
is largely German, the Balkan material Serbian and Bosnian - and on a real
Serbian stem auto-detection chose "hr" at p=0.31, a weak prior. Callers working
German material should pass `language="de"`.

MEASURED 2026-08-31, large-v3 int8 CPU, 249 s real Serbian vocal stem, idle
machine, warm-up discarded, two runs. Three configurations, in the order they
were tried:

                        backend defaults   + sr/no-cond/VAD   + temperature=0
    language            hr, p=0.31         sr, p=1.00         sr, p=1.00
    coverage            57%                62%                **69%**
    words               202 / 233          154 / 194          **188 / 188**
    longest span        36.5 s             39.0 s             **22.3 s**
    runtime drift       31.9% (void)       27.5% (void)       **7.0% (valid)**
    min/track           12.13 / 15.99      4.32 / 5.51        **3.83 / 3.56**
    reproducible        no                 no                 **yes, byte-identical**

**min/track ~3.6-3.8** - the governance number, and the first valid one: the
first two configurations drifted 27-32% between runs and no conclusion could be
drawn from them. Comfortably under AGENTS.md's 15-minute overnight threshold.

**Two lessons worth carrying out of this module.**

*Confidence is not correctness.* The backend-default run reported **0.836 mean
word probability** while dropping 43% of the track and looping inside a 36 s
block. `Word.probability` measures the decoder's certainty, not whether it is
right; nothing downstream may treat it as a truth signal.

*A clip screen overstated the fix.* A 90 s A/B of the middle configuration showed
+23 points of coverage and a 22.3 s -> 5.2 s collapse in span length. On the full
track the same change delivered **+5 points and a span that got worse**. Only
`temperature=0`, validated directly on the full input, actually held.

**Known limit:** 69% coverage, 45 words/min against rap's typical 100-200, and a
22.3 s span whose internal word timings cannot be trusted. The timings that exist
are reproducible and correctly placed; they do not cover the whole vocal.
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from . import paths

logger = logging.getLogger(__name__)

#: Approximate on-disk size of each CTranslate2 int8 model, for the download
#: budget. These are the int8 conversions published on the Hub, not the original
#: fp32 checkpoints.
MODEL_DOWNLOAD_MB = {
    "tiny": 40,
    "base": 75,
    "small": 250,
    "medium": 770,
    "large-v2": 1550,
    "large-v3": 1550,
}

#: Default model. Chosen conservatively: `small` is the cheapest model that is
#: credible on non-English speech, so it is an honest starting point for a
#: measurement rather than a claim. Override with `--model`.
DEFAULT_MODEL = "small"

#: int8 is the CPU path. float32 exists but is far slower for no useful gain.
DEFAULT_COMPUTE_TYPE = "int8"

#: Decode the corpus language explicitly rather than auto-detecting.
#: MEASURED 2026-08-31 on a real Serbian vocal stem: auto-detect chose **"hr" at
#: p=0.31** - a weak prior, on a language the model conflates with sr/bs anyway.
#: Naming the language removes that variable. None restores auto-detection.
DEFAULT_LANGUAGE: Optional[str] = "sr"

#: **Off, deliberately.** With conditioning on, the same run emitted a single
#: **36.5-second "segment"** containing one phrase twice - Whisper's well-known
#: repetition loop, where the decoder feeds its own output back as context and
#: gets stuck. A 36 s span makes every word timing inside it meaningless, which
#: defeats the entire purpose of this module. Off costs a little cross-sentence
#: coherence and buys timings that can be trusted.
DEFAULT_CONDITION_ON_PREVIOUS_TEXT = False

#: Decoding temperature. `None` leaves faster-whisper's own default, which is a
#: **fallback ladder** `(0.0, 0.2, 0.4, 0.6, 0.8, 1.0)`: when a segment trips the
#: log-probability or compression-ratio thresholds the decoder re-runs it hotter.
#:
#: That ladder is why this module is not reproducible. MEASURED 2026-08-31 on an
#: idle machine, same input, same weights, back-to-back: **259 s / 154 words** then
#: **331 s / 194 words** - 27.5% apart in runtime and 26% in word count. A corpus
#: cannot be regenerated from settings that do not produce the same answer twice.
#:
#: A scalar (`0.0`) disables the ladder: one greedy pass, no retries. **That is
#: the default here**, because measuring it settled the question on every axis at
#: once - full track, idle machine, back-to-back runs:
#:
#:                        ladder (default)      temperature=0.0
#:     output              154 / 194 words      **byte-identical** (sha256 equal)
#:     runtime drift       27.5%  (void)        **7.0%  (valid)**
#:     min/track           4.32 / 5.51          **3.83 / 3.56**
#:     RTF                 0.75-0.96x           **1.09-1.17x** (beats realtime)
#:     coverage            62%                  **69%**
#:     longest span        39.0 s               **22.3 s**
#:
#: Reproducible, faster, *and* better. The ladder was re-decoding hard segments
#: hotter and producing worse output more slowly. Set this to `None` to restore
#: the backend ladder if a caller ever wants it.
DEFAULT_TEMPERATURE: Optional[Any] = 0.0

#: Silero VAD settings. MEASURED: the defaults dropped **~80 s of a 249 s track**
#: across four gaps (19.0 / 28.1 / 10.2 / 22.2 s), i.e. 43% of the track produced
#: no output at all. Rap over a separated stem has breathy, artefact-laden pauses
#: that read as non-speech, so the threshold is lowered and the minimum silence
#: lengthened before a gap is cut.
DEFAULT_VAD_PARAMETERS: Dict[str, Any] = {
    "threshold": 0.20,
    "min_silence_duration_ms": 1000,
    "speech_pad_ms": 400,
}

#: Filename markers identifying an isolated vocal stem. audio-separator emits
#: `<name>_(Vocals)_<model>.wav`; demucs emits `vocals.wav` in a per-track dir.
_VOCAL_MARKERS = ("(vocals)", "_vocals", "vocals.wav")

AUDIO_EXTENSIONS = (".wav", ".flac", ".mp3", ".m4a", ".ogg")


class BackendUnavailable(RuntimeError):
    """faster-whisper is not installed."""


class StemRequired(RuntimeError):
    """`require_stem` was set but no isolated vocal stem could be found."""


def faster_whisper_available() -> bool:
    """True if the faster-whisper backend can be imported."""
    import importlib.util

    return importlib.util.find_spec("faster_whisper") is not None


def _require_backend() -> None:
    if not faster_whisper_available():
        raise BackendUnavailable(
            "faster-whisper is not installed.\n"
            "Install with:  pip install -e .[lyrics-asr]\n"
            "A model is downloaded on first use "
            "(~{} MB for '{}').".format(MODEL_DOWNLOAD_MB[DEFAULT_MODEL], DEFAULT_MODEL)
        )


@dataclass
class Word:
    """One word with its timing."""

    text: str
    start: float
    end: float
    #: Whisper's own confidence for this word, 0-1. Low values are the signal to
    #: distrust a timing, so the flow analyser can weight by it.
    probability: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TranscriptSegment:
    """One utterance-level span, as whisper chunks it."""

    start: float
    end: float
    text: str
    words: List[Word] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start": round(self.start, 3),
            "end": round(self.end, 3),
            "text": self.text,
            "words": [w.to_dict() for w in self.words],
        }


@dataclass
class Transcript:
    """A full timed transcription plus the provenance needed to trust it."""

    segments: List[TranscriptSegment]
    language: str
    language_probability: float
    audio_duration: float
    model: str
    compute_type: str
    #: "vocal_stem" or "full_mix" - which input actually ran. Never inferred.
    source: str
    source_path: str
    elapsed_seconds: float
    backend: str = "faster-whisper"
    #: The decode settings that produced this. Recorded because the same model on
    #: the same input is **not** reproducible: two runs returned 202 and 233 words.
    #: Without these, a corpus row cannot be compared with another corpus row.
    decode_settings: Dict[str, Any] = field(default_factory=dict)

    @property
    def words(self) -> List[Word]:
        return [w for seg in self.segments for w in seg.words]

    @property
    def word_count(self) -> int:
        return len(self.words)

    @property
    def text(self) -> str:
        return "\n".join(seg.text.strip() for seg in self.segments if seg.text.strip())

    @property
    def realtime_factor(self) -> float:
        """Audio seconds processed per wall-clock second. >1 beats realtime."""
        if self.elapsed_seconds <= 0:
            return 0.0
        return self.audio_duration / self.elapsed_seconds

    @property
    def minutes_per_track(self) -> float:
        """The AGENTS.md governance number: wall-clock minutes for this track."""
        return self.elapsed_seconds / 60.0

    @property
    def mean_word_probability(self) -> float:
        words = self.words
        if not words:
            return 0.0
        return sum(w.probability for w in words) / len(words)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "backend": self.backend,
            "model": self.model,
            "compute_type": self.compute_type,
            "source": self.source,
            "source_path": self.source_path,
            "language": self.language,
            "language_probability": round(self.language_probability, 4),
            "audio_duration": round(self.audio_duration, 2),
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "realtime_factor": round(self.realtime_factor, 2),
            "minutes_per_track": round(self.minutes_per_track, 2),
            "word_count": self.word_count,
            "mean_word_probability": round(self.mean_word_probability, 4),
            "decode_settings": self.decode_settings,
            "segments": [s.to_dict() for s in self.segments],
        }


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def _is_vocal_stem(path: Path) -> bool:
    name = path.name.lower()
    if "(instrumental)" in name:
        return False
    return any(marker in name for marker in _VOCAL_MARKERS)


def find_vocal_stem(
    audio_path: Path,
    search_dirs: Optional[Sequence[Path]] = None,
) -> Optional[Path]:
    """Locate an isolated vocal stem for `audio_path`, or None.

    Looks in the track's own directory, any sibling `*stem*` directory, and
    `<data>/stems`. A file marked `(Instrumental)` is never a vocal stem even
    though audio-separator's two-pass naming puts both words in some filenames -
    hence the explicit exclusion rather than a bare substring test.
    """
    audio_path = Path(audio_path)
    stem_key = _slug(audio_path.stem)

    roots: List[Path] = []
    if search_dirs:
        roots.extend(Path(d) for d in search_dirs)
    else:
        roots.append(audio_path.parent)
        parent = audio_path.parent
        if parent.exists():
            roots.extend(
                d for d in parent.iterdir() if d.is_dir() and "stem" in d.name.lower()
            )
        roots.append(paths.subdir("stems"))

    candidates: List[Path] = []
    for root in roots:
        root = Path(root)
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in AUDIO_EXTENSIONS:
                continue
            if not _is_vocal_stem(path):
                continue
            # `vocals.wav` carries no track name, so it only counts when the
            # directory holding it does.
            haystack = _slug(path.stem) + _slug(path.parent.name)
            if stem_key and stem_key[:24] not in haystack:
                continue
            candidates.append(path)

    if not candidates:
        return None
    # Prefer the largest: a two-pass hq stem is bigger than a single-pass one.
    return max(candidates, key=lambda p: p.stat().st_size)


def transcribe_file(
    audio_path: Path,
    model: str = DEFAULT_MODEL,
    language: Optional[str] = DEFAULT_LANGUAGE,
    compute_type: str = DEFAULT_COMPUTE_TYPE,
    prefer_stem: bool = True,
    require_stem: bool = False,
    vad_filter: bool = True,
    beam_size: int = 5,
    condition_on_previous_text: bool = DEFAULT_CONDITION_ON_PREVIOUS_TEXT,
    temperature: Optional[Any] = DEFAULT_TEMPERATURE,
    vad_parameters: Optional[Dict[str, Any]] = None,
    stem_search_dirs: Optional[Sequence[Path]] = None,
    model_cache_dir: Optional[Path] = None,
) -> Transcript:
    """Transcribe `audio_path` with word-level timings.

    Prefers an isolated vocal stem when one is found, and records which was used.
    `require_stem=True` raises `StemRequired` rather than quietly using the mix.
    """
    _require_backend()
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError("audio not found: {}".format(audio_path))

    source_path = audio_path
    source = "full_mix"
    if prefer_stem or require_stem:
        stem = find_vocal_stem(audio_path, search_dirs=stem_search_dirs)
        if stem is not None:
            source_path, source = stem, "vocal_stem"
        elif require_stem:
            raise StemRequired(
                "--require-stem was given but no vocal stem was found for "
                "{}.\n"
                "Run:  toolshop stems <path> --preset vocals-hq\n"
                "Or drop --require-stem to transcribe the full mix "
                "(lower accuracy).".format(audio_path.name)
            )

    from faster_whisper import WhisperModel  # imported late: heavy

    cache = str(model_cache_dir) if model_cache_dir else None
    whisper = WhisperModel(
        model, device="cpu", compute_type=compute_type, download_root=cache
    )

    if vad_parameters is None:
        vad_parameters = dict(DEFAULT_VAD_PARAMETERS)
    decode_settings: Dict[str, Any] = {
        "language": language,
        "beam_size": beam_size,
        "vad_filter": vad_filter,
        "vad_parameters": dict(vad_parameters) if vad_filter else None,
        "condition_on_previous_text": condition_on_previous_text,
        "temperature": temperature,
    }
    # Passing temperature=None would override the backend default with a null, so
    # the argument is only included when the caller actually set one.
    extra: Dict[str, Any] = {}
    if temperature is not None:
        extra["temperature"] = temperature

    started = time.perf_counter()
    segment_iter, info = whisper.transcribe(
        str(source_path),
        language=language,
        word_timestamps=True,
        vad_filter=vad_filter,
        vad_parameters=vad_parameters if vad_filter else None,
        beam_size=beam_size,
        condition_on_previous_text=condition_on_previous_text,
        **extra,
    )
    # faster-whisper streams lazily; nothing is computed until the iterator is
    # drained, so the timer must wrap the drain, not the call.
    segments = [_convert_segment(s) for s in segment_iter]
    elapsed = time.perf_counter() - started

    return Transcript(
        segments=segments,
        language=str(getattr(info, "language", None) or language or "unknown"),
        language_probability=float(getattr(info, "language_probability", 0.0) or 0.0),
        audio_duration=float(getattr(info, "duration", 0.0) or 0.0),
        model=model,
        compute_type=compute_type,
        source=source,
        source_path=str(source_path),
        elapsed_seconds=elapsed,
        decode_settings=decode_settings,
    )


def _convert_segment(raw: Any) -> TranscriptSegment:
    """Convert a faster-whisper segment into our own dataclass.

    Word timestamps can be absent even with `word_timestamps=True` - a segment
    VAD-clipped to near-zero length comes back with `words=None`. Treated as an
    empty list rather than crashing a 4-hour batch.
    """
    words: List[Word] = []
    for w in getattr(raw, "words", None) or []:
        words.append(
            Word(
                text=(getattr(w, "word", "") or "").strip(),
                start=float(getattr(w, "start", 0.0) or 0.0),
                end=float(getattr(w, "end", 0.0) or 0.0),
                probability=float(getattr(w, "probability", 0.0) or 0.0),
            )
        )
    return TranscriptSegment(
        start=float(getattr(raw, "start", 0.0) or 0.0),
        end=float(getattr(raw, "end", 0.0) or 0.0),
        text=(getattr(raw, "text", "") or "").strip(),
        words=words,
    )


def _safe_name(text: str) -> str:
    return re.sub(r"[^\w.-]+", "_", text, flags=re.UNICODE).strip("_") or "track"


def transcript_path_for(
    audio_path: Path, model: str, out_dir: Optional[Path] = None
) -> Path:
    """Absolute output path for a transcript. Never relative - see `paths`."""
    base = Path(out_dir) if out_dir else paths.subdir("lyrics", "transcripts")
    return base / "{}.{}.json".format(_safe_name(Path(audio_path).stem), model)


def save_transcript(transcript: Transcript, path: Path) -> Path:
    """Write the transcript as UTF-8 JSON, creating parent directories."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(transcript.to_dict(), fh, ensure_ascii=False, indent=2)
    return path
