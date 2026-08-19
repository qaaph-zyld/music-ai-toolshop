"""Tests for the melody carrier renderer (Stage 2)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pretty_midi
import pytest

from toolshop.melody_carrier import renderer


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def stage1_dir(tmp_path):
    """Create a minimal stage1/ directory matching extractor output layout."""
    s1 = tmp_path / "stage1"
    s1.mkdir()
    midi_dir = s1 / "midi"
    midi_dir.mkdir()

    pm = pretty_midi.PrettyMIDI(initial_tempo=140)
    inst = pretty_midi.Instrument(program=0)
    inst.notes.append(pretty_midi.Note(velocity=100, pitch=69, start=0, end=1))
    pm.instruments.append(inst)
    pm.write(str(midi_dir / "melody.mid"))
    pm.write(str(midi_dir / "chords.mid"))
    pm.write(str(midi_dir / "bass.mid"))
    pm.write(str(midi_dir / "drums.mid"))
    pm.write(str(midi_dir / "full_sketch.mid"))

    analysis = {
        "bpm": 140.0,
        "key": "C#",
        "mode": "minor",
        "genre": "drill",
        "duration_seconds": 30.0,
        "spectral_centroid": 2500.0,
        "spectral_bandwidth": 1800.0,
        "harmonic_ratio": 0.65,
        "onset_strength": 0.8,
        "tuning_offset": 5.0,
        "chord_progression": [
            {"chord": "C#:min", "start": 0, "end": 2},
        ],
        "detected_instruments": ["piano", "synth pad"],
        "melody_source": "vocals",
        "extraction_tools": {
            "melody": "basic_pitch",
            "chords": "autochord",
            "bass": "pyin",
            "drums": "adtof",
        },
        "drum_pattern": {
            "kick_density": 2.0,
            "snare_density": 1.0,
            "hat_density": 4.0,
            "pattern_type": "trap",
        },
    }
    (s1 / "analysis.json").write_text(
        json.dumps(analysis, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    stems = s1 / "stems"
    stems.mkdir()
    (stems / "other.wav").write_bytes(b"\x00" * 100)

    return s1


# ---------------------------------------------------------------------------
# render() tests
# ---------------------------------------------------------------------------

class TestRender:
    @patch.object(renderer, "_write_readme")
    @patch.object(renderer, "_render_carriers")
    @patch.object(renderer.prompt_gen, "generate_prompts")
    @patch.object(renderer.midi_utils, "render_sine")
    def test_render_full_pipeline(
        self, mock_sine, mock_prompts, mock_carriers, mock_readme, stage1_dir
    ):
        work_dir = stage1_dir.parent
        mock_carriers.return_value = {"carrier_sine": work_dir / "stage2" / "carrier_sine.wav"}
        mock_prompts.return_value = {
            "minimal": work_dir / "stage2" / "suno_prompt_minimal.txt",
            "descriptive": work_dir / "stage2" / "suno_prompt_descriptive.txt",
            "detailed": work_dir / "stage2" / "suno_prompt_detailed.txt",
        }
        mock_readme.return_value = work_dir / "stage2" / "README.txt"

        result = renderer.render(work_dir)

        assert "stage2_dir" in result
        assert "carriers" in result
        assert "prompts" in result
        assert "readme" in result
        assert "fidelity_pct" in result

    def test_render_missing_analysis_json(self, tmp_path):
        work_dir = tmp_path / "project"
        work_dir.mkdir()
        s1 = work_dir / "stage1"
        s1.mkdir()
        # No analysis.json

        with pytest.raises(FileNotFoundError, match="analysis.json"):
            renderer.render(work_dir)

    def test_render_missing_melody_mid(self, tmp_path):
        work_dir = tmp_path / "project"
        work_dir.mkdir()
        s1 = work_dir / "stage1"
        s1.mkdir()
        midi_dir = s1 / "midi"
        midi_dir.mkdir()
        # analysis.json exists but no melody.mid
        analysis = {"bpm": 120.0, "key": "C", "mode": "major", "genre": "pop"}
        (s1 / "analysis.json").write_text(
            json.dumps(analysis), encoding="utf-8"
        )

        with pytest.raises(FileNotFoundError, match="melody.mid"):
            renderer.render(work_dir)

    @patch.object(renderer, "_write_readme")
    @patch.object(renderer, "_render_carriers")
    @patch.object(renderer.prompt_gen, "generate_prompts")
    @patch.object(renderer.midi_utils, "render_sine")
    def test_render_fidelity_pct(
        self, mock_sine, mock_prompts, mock_carriers, mock_readme, stage1_dir
    ):
        work_dir = stage1_dir.parent
        mock_carriers.return_value = {"carrier_sine": Path("x")}
        mock_prompts.return_value = {"minimal": Path("x")}
        mock_readme.return_value = Path("x")

        result = renderer.render(work_dir, fidelity="medium")
        assert result["fidelity_pct"] == 55

    @patch.object(renderer, "_write_readme")
    @patch.object(renderer, "_render_carriers")
    @patch.object(renderer.prompt_gen, "generate_prompts")
    @patch.object(renderer.midi_utils, "render_sine")
    def test_render_prints_detected_instruments(
        self, mock_sine, mock_prompts, mock_carriers, mock_readme, stage1_dir, capsys
    ):
        work_dir = stage1_dir.parent
        mock_carriers.return_value = {"carrier_sine": Path("x")}
        mock_prompts.return_value = {"minimal": Path("x")}
        mock_readme.return_value = Path("x")

        renderer.render(work_dir)
        captured = capsys.readouterr()
        assert "Detected instruments:" in captured.out

    @patch.object(renderer, "_write_readme")
    @patch.object(renderer, "_render_carriers")
    @patch.object(renderer.prompt_gen, "generate_prompts")
    @patch.object(renderer.midi_utils, "render_sine")
    def test_render_prints_summary(
        self, mock_sine, mock_prompts, mock_carriers, mock_readme, stage1_dir, capsys
    ):
        work_dir = stage1_dir.parent
        mock_carriers.return_value = {"carrier_sine": Path("x")}
        mock_prompts.return_value = {"minimal": Path("x")}
        mock_readme.return_value = Path("x")

        renderer.render(work_dir)
        captured = capsys.readouterr()
        assert "Stage 2 complete" in captured.out

    @patch.object(renderer, "_write_readme")
    @patch.object(renderer, "_render_carriers")
    @patch.object(renderer.prompt_gen, "generate_prompts")
    @patch.object(renderer.midi_utils, "render_sine")
    def test_render_no_substitutions(
        self, mock_sine, mock_prompts, mock_carriers, mock_readme, stage1_dir
    ):
        work_dir = stage1_dir.parent
        mock_carriers.return_value = {"carrier_sine": Path("x")}
        mock_prompts.return_value = {"minimal": Path("x")}
        mock_readme.return_value = Path("x")

        result = renderer.render(work_dir, instruments="")
        # generate_prompts should have been called with empty substitutions
        call_args = mock_prompts.call_args
        subs_arg = call_args[0][1] if call_args.args else call_args.kwargs.get("substitutions", {})
        assert subs_arg == {}

    @patch.object(renderer, "_render_carriers")
    @patch.object(renderer.midi_utils, "render_sine")
    def test_render_creates_prompts(self, mock_sine, mock_carriers, stage1_dir):
        work_dir = stage1_dir.parent
        mock_carriers.return_value = {"carrier_sine": work_dir / "stage2" / "carrier_sine.wav"}

        result = renderer.render(work_dir)

        stage2 = work_dir / "stage2"
        assert (stage2 / "suno_prompt_minimal.txt").exists()
        assert (stage2 / "suno_prompt_descriptive.txt").exists()
        assert (stage2 / "suno_prompt_detailed.txt").exists()
        assert "prompts" in result
        assert len(result["prompts"]) == 3


# ---------------------------------------------------------------------------
# _parse_substitutions() tests
# ---------------------------------------------------------------------------

class TestParseSubstitutions:
    def test_parse_empty_string(self):
        assert renderer._parse_substitutions("") == {}

    def test_parse_single_pair(self):
        result = renderer._parse_substitutions("piano:cathedral organ")
        assert result == {"piano": "cathedral organ"}

    def test_parse_multiple_pairs(self):
        result = renderer._parse_substitutions("piano:cathedral organ,guitar:synth lead")
        assert result == {"piano": "cathedral organ", "guitar": "synth lead"}

    def test_parse_with_spaces(self):
        result = renderer._parse_substitutions("piano : cathedral organ , guitar : synth lead")
        assert result == {"piano": "cathedral organ", "guitar": "synth lead"}

    def test_parse_missing_colon(self, capsys):
        result = renderer._parse_substitutions("piano cathedral organ,guitar:synth lead")
        captured = capsys.readouterr()
        assert "guitar" in result
        assert "piano" not in result
        assert "Warning" in captured.err or "warning" in captured.err.lower()


# ---------------------------------------------------------------------------
# _render_carriers() tests
# ---------------------------------------------------------------------------

class TestRenderCarriers:
    @patch.object(renderer.midi_utils, "render_sine")
    def test_render_carriers_sine_always(self, mock_sine, stage1_dir, tmp_path):
        stage2_dir = tmp_path / "stage2"
        stage2_dir.mkdir()
        result = renderer._render_carriers(stage1_dir, stage2_dir, {})
        assert "carrier_sine" in result

    @patch.object(renderer.midi_utils, "render_sine")
    def test_render_carriers_midirenderer_available(self, mock_sine, stage1_dir, tmp_path):
        stage2_dir = tmp_path / "stage2"
        stage2_dir.mkdir()
        mock_mr = MagicMock()
        with patch.dict("sys.modules", {"midirenderer": mock_mr}):
            result = renderer._render_carriers(stage1_dir, stage2_dir, {})
        assert "carrier_sine" in result
        assert "carrier_melody_only" in result
        assert "carrier_melody_chords" in result
        assert "carrier_melody_chords_bass" in result
        assert "carrier_full_sketch" in result
        assert "carrier_reference" in result

    @patch.object(renderer.midi_utils, "render_sine")
    def test_render_carriers_midirenderer_missing(self, mock_sine, stage1_dir, tmp_path, capsys):
        stage2_dir = tmp_path / "stage2"
        stage2_dir.mkdir()
        with patch.dict("sys.modules", {"midirenderer": None}):
            result = renderer._render_carriers(stage1_dir, stage2_dir, {})
        assert "carrier_sine" in result
        assert "carrier_melody_only" not in result
        assert "carrier_reference" in result

    @patch.object(renderer.midi_utils, "render_sine")
    def test_render_carriers_reference_copy(self, mock_sine, stage1_dir, tmp_path):
        stage2_dir = tmp_path / "stage2"
        stage2_dir.mkdir()
        result = renderer._render_carriers(stage1_dir, stage2_dir, {})
        assert "carrier_reference" in result
        ref_path = result["carrier_reference"]
        assert ref_path.exists()
        assert ref_path.read_bytes() == (stage1_dir / "stems" / "other.wav").read_bytes()


# ---------------------------------------------------------------------------
# _write_readme() tests
# ---------------------------------------------------------------------------

class TestWriteReadme:
    def test_write_readme_exists(self, tmp_path):
        carriers = {"carrier_sine": tmp_path / "carrier_sine.wav"}
        readme_path = renderer._write_readme(tmp_path, "medium", carriers)
        assert readme_path.exists()

    def test_write_readme_contains_upload_steps(self, tmp_path):
        carriers = {"carrier_sine": tmp_path / "carrier_sine.wav"}
        readme_path = renderer._write_readme(tmp_path, "medium", carriers)
        content = readme_path.read_text(encoding="utf-8")
        assert "Suno" in content
        assert "Cover mode" in content
        assert "Audio Influence" in content

    def test_write_readme_contains_tips(self, tmp_path):
        carriers = {"carrier_sine": tmp_path / "carrier_sine.wav"}
        readme_path = renderer._write_readme(tmp_path, "medium", carriers)
        content = readme_path.read_text(encoding="utf-8")
        assert "shorter clips" in content or "dry" in content

    def test_write_readme_fidelity_pct(self, tmp_path):
        carriers = {"carrier_sine": tmp_path / "carrier_sine.wav"}
        readme_path = renderer._write_readme(tmp_path, "high", carriers)
        content = readme_path.read_text(encoding="utf-8")
        assert "70%" in content

    def test_fidelity_low_audio_influence(self, tmp_path):
        carriers = {"carrier_sine": tmp_path / "carrier_sine.wav"}
        readme_path = renderer._write_readme(tmp_path, "low", carriers)
        content = readme_path.read_text(encoding="utf-8")
        assert "35%" in content


# ---------------------------------------------------------------------------
# _merge_midi_files() tests
# ---------------------------------------------------------------------------

class TestMergeMidiFiles:
    def test_merge_midi_files_basic(self, tmp_path):
        pm1 = pretty_midi.PrettyMIDI(initial_tempo=120)
        inst1 = pretty_midi.Instrument(program=0, name="melody")
        inst1.notes.append(pretty_midi.Note(velocity=100, pitch=60, start=0, end=1))
        pm1.instruments.append(inst1)
        mid1 = tmp_path / "mid1.mid"
        pm1.write(str(mid1))

        pm2 = pretty_midi.PrettyMIDI(initial_tempo=120)
        inst2 = pretty_midi.Instrument(program=0, name="chords")
        inst2.notes.append(pretty_midi.Note(velocity=80, pitch=64, start=0, end=2))
        pm2.instruments.append(inst2)
        mid2 = tmp_path / "mid2.mid"
        pm2.write(str(mid2))

        output = tmp_path / "merged.mid"
        result = renderer._merge_midi_files([mid1, mid2], 120.0, output)

        assert result == output
        assert output.exists()
        merged = pretty_midi.PrettyMIDI(str(output))
        assert len(merged.instruments) == 2

    def test_merge_midi_files_tempo(self, tmp_path):
        pm = pretty_midi.PrettyMIDI(initial_tempo=100)
        inst = pretty_midi.Instrument(program=0)
        inst.notes.append(pretty_midi.Note(velocity=100, pitch=60, start=0, end=1))
        pm.instruments.append(inst)
        mid1 = tmp_path / "mid1.mid"
        pm.write(str(mid1))

        output = tmp_path / "merged.mid"
        renderer._merge_midi_files([mid1], 140.0, output)

        merged = pretty_midi.PrettyMIDI(str(output))
        tempo = merged.get_tempo_changes()[1]
        if len(tempo) > 0:
            assert float(tempo[0]) == pytest.approx(140.0, abs=0.5)
        else:
            assert merged.estimate_tempo() == pytest.approx(140.0, abs=1.0)
