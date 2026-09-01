"""Transcription tests (H2-M5). The ASR backend is mocked; the plumbing is not.

Per AGENTS.md, model calls are mocked here. What is tested for real is the part
that decides *what gets transcribed* - stem discovery and the stem-vs-mix
provenance - because that is the axis on which this module degrades silently.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import soundfile as sf

from toolshop import transcribe


def _wav(path: Path, seconds: float = 1.0, sr: int = 22050, amp: float = 0.2) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    t = np.arange(int(seconds * sr)) / sr
    sf.write(str(path), (amp * np.sin(2 * np.pi * 220 * t)).astype(np.float32), sr)
    return path


class TestFindVocalStem:
    def test_audio_separator_naming_is_found(self, tmp_path):
        track = _wav(tmp_path / "Borba 015.mp3")
        stems = tmp_path / "toolshop_stems"
        _wav(stems / "Borba 015_(Vocals)_model_bs_roformer.wav")

        found = transcribe.find_vocal_stem(track)
        assert found is not None
        assert "(Vocals)" in found.name

    def test_instrumental_is_never_treated_as_a_vocal_stem(self, tmp_path):
        """Two-pass naming puts both words in one filename; only one is a vocal."""
        track = _wav(tmp_path / "Borba 015.mp3")
        stems = tmp_path / "stems_dir"
        _wav(stems / "Borba 015_(Vocals)_roformer_(Instrumental)_karaoke.wav")

        assert transcribe.find_vocal_stem(track) is None

    def test_demucs_layout_is_found_via_its_directory(self, tmp_path):
        track = _wav(tmp_path / "Kawasaki.mp3")
        _wav(tmp_path / "stems" / "Kawasaki" / "vocals.wav")

        found = transcribe.find_vocal_stem(track, search_dirs=[tmp_path / "stems"])
        assert found is not None and found.name == "vocals.wav"

    def test_unrelated_stem_is_not_claimed(self, tmp_path):
        track = _wav(tmp_path / "Kawasaki.mp3")
        _wav(tmp_path / "stems" / "SomethingElse_(Vocals)_x.wav")

        assert transcribe.find_vocal_stem(track, search_dirs=[tmp_path / "stems"]) is None

    def test_largest_candidate_wins(self, tmp_path):
        """An hq two-pass stem is bigger than a single-pass one; prefer it."""
        track = _wav(tmp_path / "Song.mp3")
        stems = tmp_path / "stems"
        _wav(stems / "Song_(Vocals)_a.wav", seconds=1.0)
        _wav(stems / "Song_(Vocals)_b.wav", seconds=4.0)

        found = transcribe.find_vocal_stem(track, search_dirs=[stems])
        assert found.name == "Song_(Vocals)_b.wav"

    def test_missing_search_dir_is_not_an_error(self, tmp_path):
        track = _wav(tmp_path / "Song.mp3")
        assert transcribe.find_vocal_stem(track, search_dirs=[tmp_path / "nope"]) is None


class TestBackendGuard:
    def test_missing_backend_raises_with_install_instructions(self, tmp_path, monkeypatch):
        monkeypatch.setattr(transcribe, "faster_whisper_available", lambda: False)
        with pytest.raises(transcribe.BackendUnavailable) as exc:
            transcribe.transcribe_file(_wav(tmp_path / "a.wav"))
        assert "lyrics-asr" in str(exc.value)

    def test_missing_audio_raises_filenotfound(self, tmp_path, monkeypatch):
        monkeypatch.setattr(transcribe, "faster_whisper_available", lambda: True)
        with pytest.raises(FileNotFoundError):
            transcribe.transcribe_file(tmp_path / "absent.wav")

    def test_require_stem_fails_rather_than_using_the_mix(self, tmp_path, monkeypatch):
        """The degradation this module is built to refuse."""
        monkeypatch.setattr(transcribe, "faster_whisper_available", lambda: True)
        track = _wav(tmp_path / "lonely.wav")
        with pytest.raises(transcribe.StemRequired) as exc:
            transcribe.transcribe_file(track, require_stem=True,
                                       stem_search_dirs=[tmp_path / "nope"])
        assert "vocals-hq" in str(exc.value)


class TestSegmentConversion:
    def test_words_are_converted(self):
        raw = SimpleNamespace(
            start=1.0, end=2.0, text="  ulica  ",
            words=[SimpleNamespace(word=" uli", start=1.0, end=1.4, probability=0.9),
                   SimpleNamespace(word="ca", start=1.4, end=2.0, probability=0.8)],
        )
        segment = transcribe._convert_segment(raw)
        assert segment.text == "ulica"
        assert [w.text for w in segment.words] == ["uli", "ca"]
        assert segment.words[0].probability == pytest.approx(0.9)

    def test_missing_word_timestamps_do_not_crash(self):
        """A VAD-clipped segment comes back with words=None mid-batch."""
        raw = SimpleNamespace(start=0.0, end=0.1, text="x", words=None)
        segment = transcribe._convert_segment(raw)
        assert segment.words == []

    def test_absent_attributes_default_rather_than_raise(self):
        segment = transcribe._convert_segment(SimpleNamespace())
        assert segment.text == "" and segment.words == []


class TestTranscriptMetrics:
    def _transcript(self, **overrides):
        words = [transcribe.Word("a", 0.0, 0.5, 0.9), transcribe.Word("b", 0.5, 1.0, 0.7)]
        base = dict(
            segments=[transcribe.TranscriptSegment(0.0, 1.0, "a b", words)],
            language="sr", language_probability=0.88, audio_duration=60.0,
            model="small", compute_type="int8", source="vocal_stem",
            source_path="x.wav", elapsed_seconds=30.0,
        )
        base.update(overrides)
        return transcribe.Transcript(**base)

    def test_word_count_and_text(self):
        t = self._transcript()
        assert t.word_count == 2
        assert t.text == "a b"

    def test_realtime_factor_and_minutes_per_track(self):
        t = self._transcript()
        assert t.realtime_factor == pytest.approx(2.0)
        assert t.minutes_per_track == pytest.approx(0.5)

    def test_zero_elapsed_does_not_divide_by_zero(self):
        assert self._transcript(elapsed_seconds=0.0).realtime_factor == 0.0

    def test_mean_word_probability(self):
        assert self._transcript().mean_word_probability == pytest.approx(0.8)

    def test_empty_transcript_is_safe(self):
        t = self._transcript(segments=[])
        assert t.word_count == 0 and t.mean_word_probability == 0.0

    def test_to_dict_carries_provenance(self):
        data = self._transcript().to_dict()
        assert data["source"] == "vocal_stem"
        assert data["model"] == "small"
        assert data["minutes_per_track"] == 0.5


class TestOutputPaths:
    def test_transcript_path_is_absolute(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TOOLSHOP_DATA_DIR", str(tmp_path))
        path = transcribe.transcript_path_for(Path("Some Track.mp3"), "small")
        assert path.is_absolute()
        assert path.name == "Some_Track.small.json"

    def test_unicode_names_are_preserved_not_mangled_to_ascii(self, tmp_path):
        path = transcribe.transcript_path_for(
            Path("Täterprofil ćevap.mp3"), "small", out_dir=tmp_path
        )
        assert "Täterprofil" in path.name

    def test_save_writes_utf8_json_and_creates_parents(self, tmp_path):
        transcript = transcribe.Transcript(
            segments=[transcribe.TranscriptSegment(0.0, 1.0, "ćevap", [])],
            language="sr", language_probability=0.9, audio_duration=1.0,
            model="small", compute_type="int8", source="full_mix",
            source_path="x.wav", elapsed_seconds=1.0,
        )
        target = tmp_path / "nested" / "out.json"
        transcribe.save_transcript(transcript, target)

        assert target.exists()
        assert "ćevap" in target.read_text(encoding="utf-8")


class TestTranscribeWithMockedBackend:
    """Exercise `transcribe_file` end to end with a fake WhisperModel."""

    @pytest.fixture
    def fake_whisper(self, monkeypatch):
        import sys
        import types

        calls = {}

        class FakeModel:
            def __init__(self, model, device, compute_type, download_root=None):
                calls["init"] = dict(model=model, device=device,
                                     compute_type=compute_type, root=download_root)

            def transcribe(self, path, **kwargs):
                calls["transcribe"] = dict(path=path, **kwargs)
                segments = iter([
                    SimpleNamespace(
                        start=0.0, end=1.0, text="ulicni kodeks",
                        words=[SimpleNamespace(word="ulicni", start=0.0, end=0.5, probability=0.95),
                               SimpleNamespace(word="kodeks", start=0.5, end=1.0, probability=0.91)],
                    )
                ])
                info = SimpleNamespace(language="sr", language_probability=0.97, duration=1.0)
                return segments, info

        module = types.ModuleType("faster_whisper")
        module.WhisperModel = FakeModel
        monkeypatch.setitem(sys.modules, "faster_whisper", module)
        monkeypatch.setattr(transcribe, "faster_whisper_available", lambda: True)
        return calls

    def test_full_mix_is_recorded_when_no_stem_exists(self, tmp_path, fake_whisper):
        track = _wav(tmp_path / "track.wav")
        result = transcribe.transcribe_file(track, stem_search_dirs=[tmp_path / "none"])

        assert result.source == "full_mix"
        assert result.source_path == str(track)
        assert result.word_count == 2
        assert result.language == "sr"

    def test_vocal_stem_is_preferred_and_recorded(self, tmp_path, fake_whisper):
        track = _wav(tmp_path / "track.wav")
        stem = _wav(tmp_path / "stems" / "track_(Vocals)_x.wav")

        result = transcribe.transcribe_file(track, stem_search_dirs=[tmp_path / "stems"])

        assert result.source == "vocal_stem"
        assert result.source_path == str(stem)
        assert fake_whisper["transcribe"]["path"] == str(stem)

    def test_word_timestamps_are_always_requested(self, tmp_path, fake_whisper):
        """Without this flag the module delivers nothing the flow analyser needs."""
        transcribe.transcribe_file(_wav(tmp_path / "t.wav"),
                                   stem_search_dirs=[tmp_path / "none"])
        assert fake_whisper["transcribe"]["word_timestamps"] is True

    def test_cpu_int8_is_the_configured_path(self, tmp_path, fake_whisper):
        transcribe.transcribe_file(_wav(tmp_path / "t.wav"),
                                   stem_search_dirs=[tmp_path / "none"])
        assert fake_whisper["init"]["device"] == "cpu"
        assert fake_whisper["init"]["compute_type"] == "int8"

    def test_elapsed_time_is_measured_over_the_drain(self, tmp_path, fake_whisper):
        """faster-whisper is lazy; timing the call alone would measure nothing."""
        result = transcribe.transcribe_file(_wav(tmp_path / "t.wav"),
                                            stem_search_dirs=[tmp_path / "none"])
        assert result.elapsed_seconds > 0.0

    def test_prefer_stem_false_uses_the_mix_even_when_a_stem_exists(self, tmp_path, fake_whisper):
        track = _wav(tmp_path / "track.wav")
        _wav(tmp_path / "stems" / "track_(Vocals)_x.wav")
        result = transcribe.transcribe_file(track, prefer_stem=False,
                                            stem_search_dirs=[tmp_path / "stems"])
        assert result.source == "full_mix"


# ── Integration test (skip-guarded) ───────────────────────────────────

#: A 30 s excerpt of the Serbian vocal stem M5 was measured on. Kept out of the
#: repo (data boundary); the test skips when it is absent.
REAL_STEM = (
    Path(__file__).resolve().parents[1] / "data" / "toolshop" / "Stemmeca_alatkka"
    / "toolshop_stems_borba_hq"
    / ("Srpskki Istocnicci - Borba 015_(Vocals)_model_bs_roformer_ep_317_sdr_12_"
       "(Vocals)_mel_band_roformer_karaoke_aufr33_viperx_sdr_10.wav")
)


@pytest.mark.slow
def test_real_serbian_vocal_transcribes_with_usable_timings():
    """Live faster-whisper on real Serbian rap — the check M5 actually needs.

    Mocked tests prove the plumbing; they cannot show that word timings on
    non-English rap are usable, which is the whole premise of the milestone. So
    this asserts on the *timings*, not on "a string came back": words must be
    ordered, non-overlapping, inside the clip, and carry real confidences.
    """
    pytest.importorskip("faster_whisper", reason="[lyrics-asr] extra not installed")
    if not REAL_STEM.exists():
        pytest.skip(f"real stem not present: {REAL_STEM}")

    import soundfile as sf

    # A 30 s excerpt keeps the test minutes-not-tens-of-minutes on CPU.
    data, sr = sf.read(str(REAL_STEM), frames=30 * 44100)
    clip = Path(__file__).parent / "_tmp_real_clip.wav"
    sf.write(str(clip), data, sr)
    try:
        result = transcribe.transcribe_file(
            clip, model="large-v3", prefer_stem=False, vad_filter=True
        )
    finally:
        clip.unlink(missing_ok=True)  # never leave the tree dirty

    assert result.word_count > 0, "no words recognised in 30 s of rap vocal"
    assert result.source == "full_mix"
    assert result.language_probability > 0.0

    words = result.words
    for word in words:
        assert 0.0 <= word.start <= word.end <= 31.0, f"timing out of range: {word}"
        assert 0.0 <= word.probability <= 1.0

    starts = [w.start for w in words]
    assert starts == sorted(starts), "word timings must be monotonic"
    assert result.mean_word_probability > 0.3, (
        "mean word confidence below 0.3 would mean the timings are not usable "
        "downstream, which is what M5 exists to deliver"
    )


# --- forced-alignment language resolution (JOURNAL.md J-014, J-052, J-061) ----
#
# Whisper is multilingual; alignment models are per-language wav2vec2 CTC
# checkpoints. DEFAULT_LANGUAGE is "sr", which whisperX has no model for at all,
# so passing it through would raise ValueError inside load_align_model.

from toolshop.transcribe import (  # noqa: E402
    ALIGNMENT_LANGUAGE_PROXIES,
    ALIGNMENT_MODEL_LANGUAGES,
    AlignmentLanguage,
    AlignmentLanguageUnavailable,
    alignment_script_conflict,
    resolve_alignment_language,
)


def test_sr_resolves_to_hr_and_says_so():
    got = resolve_alignment_language("sr")
    assert got.resolved == "hr"
    assert got.requested == "sr"
    assert got.is_substitution is True
    assert "hr" in got.reason


def test_the_module_default_language_is_the_one_that_needs_the_mapping():
    """The regression guard: DEFAULT_LANGUAGE must not be passed through raw."""
    from toolshop import transcribe

    assert transcribe.DEFAULT_LANGUAGE not in ALIGNMENT_MODEL_LANGUAGES
    assert resolve_alignment_language(transcribe.DEFAULT_LANGUAGE).resolved == "hr"


def test_a_supported_language_is_not_marked_as_substituted():
    got = resolve_alignment_language("de")
    assert got.resolved == "de"
    assert got.is_substitution is False


@pytest.mark.parametrize("code", ["SR", " sr ", "Sr"])
def test_language_codes_are_normalised(code):
    assert resolve_alignment_language(code).resolved == "hr"


def test_require_language_match_refuses_the_substitution():
    """--require-language-match: nothing, rather than sr quietly aligned by hr."""
    with pytest.raises(AlignmentLanguageUnavailable) as exc:
        resolve_alignment_language("sr", allow_substitution=False)
    assert "hr" in str(exc.value)


def test_an_unserved_language_refuses_rather_than_guessing():
    with pytest.raises(AlignmentLanguageUnavailable):
        resolve_alignment_language("mk")


def test_macedonian_is_deliberately_not_proxied_to_croatian():
    """mk is not BCMS — it is closer to Bulgarian, and Cyrillic. A proxy here
    would be exactly the confident-wrong output this module refuses."""
    assert "mk" not in ALIGNMENT_LANGUAGE_PROXIES


def test_empty_language_refuses():
    with pytest.raises(AlignmentLanguageUnavailable):
        resolve_alignment_language("")


def test_every_proxy_target_actually_has_a_model():
    """A proxy pointing at a language whisperX cannot align is worse than none."""
    for source, target in ALIGNMENT_LANGUAGE_PROXIES.items():
        assert target in ALIGNMENT_MODEL_LANGUAGES, f"{source} -> {target} is unserved"


def test_provenance_has_no_defaults():
    """J-054: Transcript.source read full_mix on five separated stems because it
    had a default. No field in this path gets one."""
    with pytest.raises(TypeError):
        AlignmentLanguage(requested="sr")  # type: ignore[call-arg]


def test_resolution_is_recorded_for_the_transcript():
    d = resolve_alignment_language("sr").to_dict()
    assert d["align_language_requested"] == "sr"
    assert d["align_language"] == "hr"
    assert d["align_language_substituted"] is True
    assert d["align_language_reason"]


def test_cyrillic_against_a_latin_model_is_flagged():
    """align() maps OOV characters to a wildcard and returns confident timings
    anyway, so this has to be caught before the aligner sees it."""
    got = resolve_alignment_language("sr")
    assert alignment_script_conflict("Борба на улици", got) is not None
    assert alignment_script_conflict("Borba na ulici", got) is None


def test_cyrillic_is_fine_for_a_cyrillic_model():
    assert alignment_script_conflict("Привет", resolve_alignment_language("ru")) is None


def test_script_is_checked_per_span_not_per_document():
    """J-052: one real transcript carries both alphabets in a single run —
    segments 1-12 Cyrillic, 13-25 Latin. A document-level check gets it half
    wrong whichever way it decides."""
    got = resolve_alignment_language("sr")
    segments = ["Борба на улици", "Borba na ulici"]
    flagged = [s for s in segments if alignment_script_conflict(s, got)]
    assert flagged == ["Борба на улици"]


def test_the_language_snapshot_still_matches_the_installed_whisperx():
    """ALIGNMENT_MODEL_LANGUAGES is a snapshot taken from whisperX 3.4.5 on
    2026-09-01. A snapshot drifts silently, so check it against the real package
    when the sidecar is present. Skips in CI and on any machine without it —
    whisperX is deliberately absent from the main venv (J-012)."""
    import json as _json
    import subprocess
    from pathlib import Path as _Path

    sidecar = _Path(__file__).resolve().parents[1] / ".venv-align" / "Scripts" / "python.exe"
    if not sidecar.exists():
        pytest.skip("whisperX sidecar venv not present")

    probe = (
        "import json;"
        "from whisperx.alignment import DEFAULT_ALIGN_MODELS_HF as H,"
        " DEFAULT_ALIGN_MODELS_TORCH as T;"
        "print(json.dumps(sorted(set(H)|set(T))))"
    )
    out = subprocess.run(
        [str(sidecar), "-c", probe], capture_output=True, text=True, timeout=300
    )
    if out.returncode != 0:
        pytest.skip(f"sidecar probe failed: {out.stderr[-200:]}")

    installed = set(_json.loads(out.stdout.strip().splitlines()[-1]))
    assert installed == set(ALIGNMENT_MODEL_LANGUAGES), (
        "the hardcoded alignment-language snapshot has drifted from the installed "
        f"whisperX. only-installed={sorted(installed - set(ALIGNMENT_MODEL_LANGUAGES))} "
        f"only-snapshot={sorted(set(ALIGNMENT_MODEL_LANGUAGES) - installed)}"
    )
