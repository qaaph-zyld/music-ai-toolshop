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
