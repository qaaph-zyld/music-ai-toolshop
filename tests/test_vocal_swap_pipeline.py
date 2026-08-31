"""Pipeline tests: the refusals, the resume, and one real end-to-end premaster.

The mastering chain is mocked (it is another OS), but everything up to and
including the premaster gates runs for real on synthetic audio.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from toolshop.vocal_swap import mastering_bridge
from toolshop.vocal_swap import pipeline as pipe


SR = 44100


def _tone(path: Path, seconds: float = 6.0, freq: float = 220.0,
          amp: float = 0.25, seed: int | None = None) -> Path:
    t = np.arange(int(seconds * SR)) / SR
    wave = amp * np.sin(2 * np.pi * freq * t)
    if seed is not None:
        wave = wave + np.random.default_rng(seed).normal(0, 0.01, wave.shape)
    audio = np.stack([wave, wave], axis=1).astype(np.float32)
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), audio, SR)
    return path


@pytest.fixture
def inputs(tmp_path):
    return {
        "suno": _tone(tmp_path / "suno.wav", freq=110.0, amp=0.30),
        "instrumental": _tone(tmp_path / "instr.wav", freq=110.0, amp=0.30),
        "vocal": _tone(tmp_path / "vocal.wav", freq=440.0, amp=0.05, seed=1),
    }


def _config(inputs, tmp_path, **overrides) -> pipe.SwapConfig:
    base = dict(
        suno_track=inputs["suno"],
        vocal_take=inputs["vocal"],
        instrumental=inputs["instrumental"],
        work_dir=tmp_path / "work",
        name="testsong",
        skip_master=True,
        offset_seconds=0.0,
    )
    base.update(overrides)
    return pipe.SwapConfig(**base)


class TestPreflight:
    def test_missing_suno_track_is_caught(self, inputs, tmp_path):
        cfg = _config(inputs, tmp_path, suno_track=tmp_path / "absent.wav")
        with pytest.raises(pipe.PipelineError) as exc:
            pipe.run_swap(cfg)
        assert "suno_track not found" in str(exc.value)

    def test_missing_vocal_take_is_caught(self, inputs, tmp_path):
        cfg = _config(inputs, tmp_path, vocal_take=tmp_path / "absent.wav")
        with pytest.raises(pipe.PipelineError) as exc:
            pipe.run_swap(cfg)
        assert "vocal_take not found" in str(exc.value)

    def test_empty_file_is_caught(self, inputs, tmp_path):
        empty = tmp_path / "empty.wav"
        empty.write_bytes(b"")
        cfg = _config(inputs, tmp_path, vocal_take=empty)
        with pytest.raises(pipe.PipelineError) as exc:
            pipe.run_swap(cfg)
        assert "empty" in str(exc.value)

    def test_preset_without_an_instrumental_is_rejected(self, inputs, tmp_path):
        cfg = _config(inputs, tmp_path, stem_preset="4stem")
        with pytest.raises(pipe.PipelineError) as exc:
            pipe.run_swap(cfg)
        assert "does not produce an instrumental" in str(exc.value)

    def test_unknown_profile_is_rejected(self, inputs, tmp_path):
        cfg = _config(inputs, tmp_path, profile="nonesuch")
        with pytest.raises(pipe.PipelineError) as exc:
            pipe.run_swap(cfg)
        assert "unknown mastering profile" in str(exc.value)

    def test_all_problems_are_reported_together(self, inputs, tmp_path):
        """One run should not require five round trips to fix five mistakes."""
        cfg = _config(
            inputs, tmp_path,
            suno_track=tmp_path / "absent.wav",
            profile="nonesuch",
            stem_preset="4stem",
        )
        with pytest.raises(pipe.PipelineError) as exc:
            pipe.run_swap(cfg)
        message = str(exc.value)
        assert "suno_track not found" in message
        assert "unknown mastering profile" in message
        assert "does not produce an instrumental" in message


class TestEndToEndPremaster:
    def test_premaster_is_produced_and_graded(self, inputs, tmp_path):
        result = pipe.run_swap(_config(inputs, tmp_path))

        assert result.status == "premaster_only"
        premaster = Path(result.deliverables["premaster"])
        assert premaster.exists()
        assert result.premaster_verdict in ("PASS", "FLAG", "FAIL")

        info = sf.info(str(premaster))
        assert info.samplerate == SR
        assert info.channels == 2

    def test_manifest_records_every_stage_that_ran(self, inputs, tmp_path):
        result = pipe.run_swap(_config(inputs, tmp_path))
        manifest = pipe.load_manifest(Path(result.work_dir))

        for stage in ("preflight", "instrumental", "vocal_prep", "align", "mix", "premaster"):
            assert stage in manifest["stages"], f"{stage} missing from manifest"
        # skip_master=True, so these two must be absent rather than recorded empty.
        assert "master" not in manifest["stages"]
        assert "verify" not in manifest["stages"]

    def test_vocal_gain_is_recorded_for_audit(self, inputs, tmp_path):
        result = pipe.run_swap(_config(inputs, tmp_path, vocal_balance_db=3.0))
        detail = result.stages["mix"].detail
        assert detail["vocal_balance_db"] == 3.0
        # The quiet vocal fixture must have been turned up to reach that balance.
        assert detail["vocal_gain_db"] > 0

    def test_supplied_instrumental_skips_separation(self, inputs, tmp_path):
        result = pipe.run_swap(_config(inputs, tmp_path))
        assert result.stages["instrumental"].status == "skipped"
        assert "supplied by caller" in result.stages["instrumental"].message


class TestGate:
    def _force_verdict(self, monkeypatch, verdict):
        def fake(path):
            return {"file": str(path), "verdict": verdict, "gates": []}
        monkeypatch.setattr("toolshop.premaster.analyze_premaster", fake)

    def test_gate_failure_stops_before_mastering(self, inputs, tmp_path, monkeypatch):
        self._force_verdict(monkeypatch, "FAIL")
        monkeypatch.setattr(
            mastering_bridge, "check_environment", lambda *a, **k: {"ok": True, "errors": []}
        )
        called = []
        monkeypatch.setattr(pipe, "_stage_master", lambda *a, **k: called.append(1))

        cfg = _config(inputs, tmp_path, skip_master=False)
        with pytest.raises(pipe.PipelineError) as exc:
            pipe.run_swap(cfg)

        assert "refusing to master" in str(exc.value)
        assert not called, "the mastering chain must not have been reached"

    def test_gate_failure_is_recorded_in_the_manifest(self, inputs, tmp_path, monkeypatch):
        self._force_verdict(monkeypatch, "FAIL")
        monkeypatch.setattr(
            mastering_bridge, "check_environment", lambda *a, **k: {"ok": True, "errors": []}
        )
        cfg = _config(inputs, tmp_path, skip_master=False)
        with pytest.raises(pipe.PipelineError):
            pipe.run_swap(cfg)

        manifest = pipe.load_manifest(tmp_path / "work")
        assert manifest["status"] == "stopped_at_gate"
        assert manifest["premaster_verdict"] == "FAIL"

    def test_override_lets_a_failing_premaster_through(self, inputs, tmp_path, monkeypatch):
        """The override must exist, and must be explicit."""
        self._force_verdict(monkeypatch, "FAIL")
        monkeypatch.setattr(
            mastering_bridge, "check_environment", lambda *a, **k: {"ok": True, "errors": []}
        )

        def fake_master(cfg_, work_dir, premaster):
            return pipe.StageRecord(
                name="master", status="ok",
                outputs={"master_16": str(premaster)},
                detail={"profile": cfg_.profile, "target_lufs": -8.5,
                        "target_tp_dbtp": -1.0, "master_16": str(premaster)},
            )

        monkeypatch.setattr(pipe, "_stage_master", fake_master)
        cfg = _config(inputs, tmp_path, skip_master=False, master_on_gate_fail=True)
        result = pipe.run_swap(cfg)
        assert result.status == "complete"
        assert result.premaster_verdict == "FAIL"


class TestAlignReference:
    """What the take is aligned *against* — measured to matter more than the method.

    On real Serbian material with a true offset of exactly 0, aligning against the
    instrumental returned +1.416 s at confidence 0.107. A rap vocal's onsets do not
    track an instrumental's, so the Suno vocal stem is preferred where it exists.
    """

    def _result_with_stem(self, ai_vocal):
        result = pipe.SwapResult(config={}, work_dir="")
        outputs = {"instrumental": "instr.wav"}
        if ai_vocal:
            outputs["ai_vocal"] = str(ai_vocal)
        result.stages["instrumental"] = pipe.StageRecord(
            name="instrumental", status="ok", outputs=outputs
        )
        return result

    def test_ai_vocal_is_preferred_when_available(self, tmp_path):
        cfg = pipe.SwapConfig(suno_track=tmp_path / "s.wav", vocal_take=tmp_path / "v.wav")
        ref, kind = pipe._pick_align_reference(
            cfg, self._result_with_stem(tmp_path / "ai.wav"), tmp_path / "instr.wav"
        )
        assert kind == "ai_vocal"
        assert ref == tmp_path / "ai.wav"

    def test_falls_back_to_instrumental_when_no_stem_exists(self, tmp_path):
        cfg = pipe.SwapConfig(suno_track=tmp_path / "s.wav", vocal_take=tmp_path / "v.wav")
        ref, kind = pipe._pick_align_reference(
            cfg, self._result_with_stem(None), tmp_path / "instr.wav"
        )
        assert kind == "instrumental"

    def test_explicit_instrumental_overrides_an_available_stem(self, tmp_path):
        cfg = pipe.SwapConfig(suno_track=tmp_path / "s.wav", vocal_take=tmp_path / "v.wav",
                              align_reference="instrumental")
        _, kind = pipe._pick_align_reference(
            cfg, self._result_with_stem(tmp_path / "ai.wav"), tmp_path / "instr.wav"
        )
        assert kind == "instrumental"

    def test_demanding_the_vocal_without_one_is_an_error(self, tmp_path):
        cfg = pipe.SwapConfig(suno_track=tmp_path / "s.wav", vocal_take=tmp_path / "v.wav",
                              align_reference="vocal")
        with pytest.raises(pipe.PipelineError) as exc:
            pipe._pick_align_reference(cfg, self._result_with_stem(None), tmp_path / "i.wav")
        assert "--instrumental" in str(exc.value)

    def test_run_records_which_reference_was_used(self, inputs, tmp_path):
        result = pipe.run_swap(_config(inputs, tmp_path))
        detail = result.stages["align"].detail
        assert detail["reference"] == "instrumental"  # no separation ran
        assert detail["reference_path"]

    def test_instrumental_reference_carries_a_warning(self, inputs, tmp_path):
        """The weaker reference must announce itself, not pass silently."""
        cfg = _config(inputs, tmp_path, offset_seconds=None)
        result = pipe.run_swap(cfg)
        assert "measured unreliable" in result.stages["align"].message


class TestManifest:
    def test_written_atomically_with_no_stray_temp_file(self, inputs, tmp_path):
        result = pipe.run_swap(_config(inputs, tmp_path))
        work = Path(result.work_dir)
        assert (work / pipe.MANIFEST_NAME).exists()
        assert not list(work.glob("*.tmp")), "temp file left behind"

    def test_unreadable_manifest_does_not_strand_the_run(self, inputs, tmp_path):
        work = tmp_path / "work"
        work.mkdir(parents=True)
        (work / pipe.MANIFEST_NAME).write_text("{ this is not json", encoding="utf-8")

        result = pipe.run_swap(_config(inputs, tmp_path))
        assert result.status == "premaster_only"

    def test_missing_manifest_reads_as_empty(self, tmp_path):
        assert pipe.load_manifest(tmp_path / "nowhere") == {}


class TestResume:
    def test_stage_is_reused_when_its_output_still_exists(self, inputs, tmp_path):
        first = pipe.run_swap(_config(inputs, tmp_path))
        assert "resumed" not in first.stages["instrumental"].message

        second = pipe.run_swap(_config(inputs, tmp_path))
        assert "[resumed]" in second.stages["instrumental"].message

    def test_stage_is_redone_when_its_output_vanished(self, inputs, tmp_path):
        first = pipe.run_swap(_config(inputs, tmp_path))
        Path(first.stages["instrumental"].outputs["instrumental"]).unlink()

        second = pipe.run_swap(_config(inputs, tmp_path))
        assert "[resumed]" not in second.stages["instrumental"].message

    def test_no_resume_redoes_everything(self, inputs, tmp_path):
        pipe.run_swap(_config(inputs, tmp_path))
        second = pipe.run_swap(_config(inputs, tmp_path, resume=False))
        assert "[resumed]" not in second.stages["instrumental"].message

    def test_completed_helper_rejects_a_record_with_a_missing_output(self, tmp_path):
        previous = {"stages": {"mix": {"status": "ok",
                                       "outputs": {"premaster": str(tmp_path / "gone.wav")}}}}
        assert pipe._completed(previous, "mix") is None

    def test_completed_helper_rejects_a_failed_record(self):
        previous = {"stages": {"mix": {"status": "failed", "outputs": {}}}}
        assert pipe._completed(previous, "mix") is None


class TestConfig:
    def test_name_defaults_to_the_suno_stem(self, tmp_path):
        cfg = pipe.SwapConfig(suno_track=tmp_path / "My Track.wav",
                              vocal_take=tmp_path / "v.wav")
        assert cfg.resolved_name() == "My_Track"

    def test_work_dir_defaults_under_the_data_dir(self, tmp_path):
        cfg = pipe.SwapConfig(suno_track=tmp_path / "t.wav", vocal_take=tmp_path / "v.wav")
        assert cfg.resolved_work_dir().is_absolute()
        assert "vocal_swap" in str(cfg.resolved_work_dir())

    def test_unicode_names_survive(self, tmp_path):
        cfg = pipe.SwapConfig(suno_track=tmp_path / "Täterprofil ćevap.wav",
                              vocal_take=tmp_path / "v.wav")
        assert cfg.resolved_name()
        assert "/" not in cfg.resolved_name()


def test_jsonable_coerces_numpy_and_paths(tmp_path):
    payload = {"a": np.float32(1.5), "b": [np.int64(2)], "c": tmp_path}
    coerced = pipe._jsonable(payload)
    json.dumps(coerced)  # must not raise
    assert coerced["a"] == pytest.approx(1.5)
    assert coerced["b"] == [2]
