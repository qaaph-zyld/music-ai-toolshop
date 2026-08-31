"""Orchestrate the vocal swap: two tracks in, a mastered track out.

**Why this is a staged pipeline and not a function.** The expensive stage (stem
separation) costs tens of minutes and the last stage (mastering) is a separate
process in another OS. A single function that redid separation every time a mix
balance was tweaked would make the tool unusable in practice, so every stage
writes an artifact and a manifest entry, and a rerun skips what is already done.
That is `toolshop/batch.py`'s resume discipline applied to the stages of one
track rather than to a list of tracks.

**Where it refuses to continue.** A pipeline that always produces a file is not
robust, it is just quiet. This one stops at three points:

- **preflight** - inputs unreadable, decoders missing, or WSL unusable, checked
  *before* the 30-minute stage rather than after it.
- **alignment** - a low correlation or a tempo disagreement means the mix would
  be wrong in a way no mastering can repair. `require_alignment` makes that fatal.
- **premaster gates** - the M4 gates run on the mix, and a FAIL does not go to
  the mastering chain. Feeding a clipped or phase-broken premaster to a limiter
  produces a loud broken master, which is worse than no master at all.

Each of those can be overridden explicitly. None can be overridden silently.
"""

from __future__ import annotations

import json
import logging
import re
import shutil
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .. import paths
from . import align as align_mod
from . import mastering_bridge
from . import mix as mix_mod

logger = logging.getLogger(__name__)

#: Stage order. The manifest keys off these names, so renaming one invalidates
#: existing resumable runs - which is correct, since the artifact would be stale.
STAGES = (
    "preflight",
    "instrumental",
    "vocal_prep",
    "align",
    "mix",
    "premaster",
    "master",
    "verify",
)

MANIFEST_NAME = "manifest.json"

#: Presets that yield an `instrumental` output. Only two-stem separations are
#: useful here; a 4/6-stem run would have to be re-summed and would lose nothing
#: but time.
INSTRUMENTAL_PRESETS = ("karaoke", "vocals-hq", "full-vocals", "full-vocals-hq")


class PipelineError(RuntimeError):
    """A stage refused to continue. The message says which and why."""


@dataclass
class SwapConfig:
    """Everything the run needs. Defaults are the sane path, not the only path."""

    suno_track: Path
    vocal_take: Path
    name: str = ""
    work_dir: Optional[Path] = None

    #: Skip separation entirely by supplying an instrumental you already have.
    instrumental: Optional[Path] = None
    stem_preset: str = "karaoke"

    #: Vocal conditioning before the mix.
    clean_vocal: bool = False
    vocal_hpf_hz: float = mix_mod.DEFAULT_VOCAL_HPF_HZ

    #: What the take is aligned *against*. MEASURED 2026-08-31 on real Serbian
    #: material whose true offset was exactly 0 (instrumental and vocal separated
    #: from one file): aligning against the **instrumental** returned +1.416 s,
    #: confidence 0.107, ambiguous - wrong, and correctly refused. A rap vocal's
    #: onsets simply do not track an instrumental's.
    #:
    #: The Suno track's own vocal stem is the better reference and separation
    #: already produces it: both vocals perform the same words at the same points
    #: in the arrangement. "auto" uses it when available and falls back to the
    #: instrumental. NOT yet verified on two genuinely different performances -
    #: the reference actually used is always recorded.
    align_reference: str = "auto"  # auto | vocal | instrumental

    #: Alignment. `offset_seconds` skips estimation and declares the answer.
    offset_seconds: Optional[float] = None
    require_alignment: bool = False
    allow_time_stretch: bool = False
    max_offset_s: float = align_mod.DEFAULT_MAX_OFFSET_S

    #: Mix.
    vocal_balance_db: float = mix_mod.DEFAULT_VOCAL_BALANCE_DB
    duck_db: float = mix_mod.DEFAULT_DUCK_DB
    bus_lufs_target: float = mix_mod.DEFAULT_BUS_LUFS
    bus_peak_dbfs: float = mix_mod.DEFAULT_BUS_PEAK_DBFS

    #: Master.
    profile: str = mastering_bridge.DEFAULT_PROFILE
    skip_master: bool = False
    master_on_gate_fail: bool = False
    master_timeout_s: int = mastering_bridge.DEFAULT_TIMEOUT_S

    resume: bool = True

    def resolved_name(self) -> str:
        if self.name:
            return _safe_name(self.name)
        return _safe_name(Path(self.suno_track).stem)

    def resolved_work_dir(self) -> Path:
        if self.work_dir:
            return Path(self.work_dir).resolve()
        return paths.subdir("vocal_swap", self.resolved_name())

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        for key, value in data.items():
            if isinstance(value, Path):
                data[key] = str(value)
        return data


@dataclass
class StageRecord:
    """One stage's outcome, as written to the manifest."""

    name: str
    status: str  # ok | skipped | failed
    started_at: str = ""
    elapsed_seconds: float = 0.0
    outputs: Dict[str, str] = field(default_factory=dict)
    detail: Dict[str, Any] = field(default_factory=dict)
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["elapsed_seconds"] = round(self.elapsed_seconds, 2)
        return data


@dataclass
class SwapResult:
    """The run as a whole."""

    config: Dict[str, Any]
    work_dir: str
    stages: Dict[str, StageRecord] = field(default_factory=dict)
    status: str = "incomplete"
    premaster_verdict: str = "not_run"
    master_verdict: str = "not_run"
    deliverables: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config": self.config,
            "work_dir": self.work_dir,
            "status": self.status,
            "premaster_verdict": self.premaster_verdict,
            "master_verdict": self.master_verdict,
            "deliverables": self.deliverables,
            "stages": {k: v.to_dict() for k, v in self.stages.items()},
        }


def _safe_name(text: str) -> str:
    cleaned = re.sub(r"[^\w.-]+", "_", str(text), flags=re.UNICODE).strip("_")
    return cleaned or "swap"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def load_manifest(work_dir: Path) -> Dict[str, Any]:
    path = Path(work_dir) / MANIFEST_NAME
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError):
        # A half-written manifest must not strand the run. Losing resume state is
        # recoverable; refusing to start is not.
        logger.warning("manifest at %s is unreadable; starting fresh", path)
        return {}


def save_manifest(work_dir: Path, result: SwapResult) -> Path:
    """Flush the manifest after every stage, not at the end.

    The point of a manifest written per stage is that a crash, a timeout or a
    Ctrl-C still leaves a resumable run.
    """
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    path = work_dir / MANIFEST_NAME
    tmp = path.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(result.to_dict(), fh, ensure_ascii=False, indent=2)
    tmp.replace(path)  # atomic: a killed process never leaves a truncated manifest
    return path


def _completed(previous: Dict[str, Any], stage: str) -> Optional[Dict[str, Any]]:
    """Return the prior record for `stage` if it succeeded and its outputs exist."""
    record = (previous.get("stages") or {}).get(stage)
    if not record or record.get("status") not in ("ok", "skipped"):
        return None
    for path_str in (record.get("outputs") or {}).values():
        if path_str and not Path(path_str).exists():
            return None
    return record


# --------------------------------------------------------------------------- #
# Stages
# --------------------------------------------------------------------------- #

def _stage_preflight(cfg: SwapConfig, work_dir: Path) -> StageRecord:
    """Fail here, cheaply, rather than 30 minutes into separation."""
    detail: Dict[str, Any] = {}
    problems: List[str] = []

    for label, path in (("suno_track", cfg.suno_track), ("vocal_take", cfg.vocal_take)):
        p = Path(path)
        if not p.exists():
            problems.append(f"{label} not found: {p}")
            continue
        if p.stat().st_size == 0:
            problems.append(f"{label} is empty: {p}")
            continue
        try:
            info = _probe(p)
            detail[label] = info
            if info["duration"] <= 0:
                problems.append(f"{label} decodes to zero length: {p}")
        except Exception as exc:
            problems.append(f"{label} could not be decoded ({p}): {exc}")

    if cfg.instrumental is not None and not Path(cfg.instrumental).exists():
        problems.append(f"instrumental not found: {cfg.instrumental}")

    if cfg.stem_preset not in INSTRUMENTAL_PRESETS:
        problems.append(
            f"stem preset '{cfg.stem_preset}' does not produce an instrumental; "
            f"use one of {', '.join(INSTRUMENTAL_PRESETS)}"
        )

    try:
        mastering_bridge.resolve_profile(cfg.profile)
    except ValueError as exc:
        problems.append(str(exc))

    for module in ("librosa", "soundfile", "numpy", "scipy", "pyloudnorm"):
        if not _importable(module):
            problems.append(f"required package missing: {module} (pip install -e .[swap])")

    if not cfg.skip_master:
        env = mastering_bridge.check_environment()
        detail["mastering_env"] = env
        if not env.get("ok"):
            problems.append(
                "mastering environment unusable: " + "; ".join(env.get("errors", []))
                + " (rerun with --skip-master to stop at the premaster)"
            )

    if problems:
        raise PipelineError("preflight failed:\n  - " + "\n  - ".join(problems))

    return StageRecord(name="preflight", status="ok", started_at=_now(), detail=detail)


def _importable(module: str) -> bool:
    import importlib.util

    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):  # pragma: no cover
        return False


def _probe(path: Path) -> Dict[str, Any]:
    """Read duration/sr/channels without loading the whole file where possible."""
    import soundfile as sf

    try:
        info = sf.info(str(path))
        return {
            "path": str(path),
            "duration": float(info.duration),
            "sample_rate": int(info.samplerate),
            "channels": int(info.channels),
            "format": info.format,
        }
    except Exception:
        # soundfile cannot read mp3 on every build; librosa's audioread path can.
        import librosa

        duration = float(librosa.get_duration(path=str(path)))
        return {"path": str(path), "duration": duration, "sample_rate": None,
                "channels": None, "format": Path(path).suffix.lstrip(".")}


def _stage_instrumental(cfg: SwapConfig, work_dir: Path) -> StageRecord:
    """Separate the Suno track, or adopt the instrumental the user supplied."""
    started = time.perf_counter()

    if cfg.instrumental is not None:
        # Keep the source suffix. Copying an .mp3 to "instrumental.wav" gives a
        # file whose name lies about its contents, and `soundfile` probes by
        # header on some builds and by extension on others.
        source = Path(cfg.instrumental)
        target = work_dir / f"instrumental{source.suffix or '.wav'}"
        shutil.copyfile(source, target)
        return StageRecord(
            name="instrumental", status="skipped", started_at=_now(),
            elapsed_seconds=time.perf_counter() - started,
            outputs={"instrumental": str(target)},
            message=f"supplied by caller: {cfg.instrumental}",
        )

    from .. import stem_extractor_adapter

    out_dir = work_dir / "stems"
    result = stem_extractor_adapter.extract_stems_preset(
        input_file=Path(cfg.suno_track),
        preset_id=cfg.stem_preset,
        output_dir=out_dir,
    )
    stems = result.get("stems") or result.get("final_stems") or {}
    instrumental = stems.get("instrumental")
    if not instrumental or not Path(instrumental).exists():
        raise PipelineError(
            f"stem separation with preset '{cfg.stem_preset}' produced no instrumental. "
            f"Got keys: {sorted(stems)}"
        )

    outputs = {"instrumental": str(instrumental)}
    # Keep the AI vocal too: it is the better alignment reference and separation
    # has already paid for it. Discarding it would mean aligning against the
    # instrumental, which measured wrong on real material.
    ai_vocal = stems.get("main_vocals") or stems.get("vocals")
    if ai_vocal and Path(ai_vocal).exists():
        outputs["ai_vocal"] = str(ai_vocal)

    return StageRecord(
        name="instrumental", status="ok", started_at=_now(),
        elapsed_seconds=time.perf_counter() - started,
        outputs=outputs,
        detail={"preset": cfg.stem_preset, "stems": {k: str(v) for k, v in stems.items()}},
    )


def _stage_vocal_prep(cfg: SwapConfig, work_dir: Path) -> StageRecord:
    """Condition the vocal take. Off by default - cleaning is not free of risk."""
    started = time.perf_counter()
    source = Path(cfg.vocal_take)

    if not cfg.clean_vocal:
        # Suffix preserved for the same reason as the instrumental stage.
        target = work_dir / f"vocal_prepped{source.suffix or '.wav'}"
        shutil.copyfile(source, target)
        return StageRecord(
            name="vocal_prep", status="skipped", started_at=_now(),
            elapsed_seconds=time.perf_counter() - started,
            outputs={"vocal": str(target)},
            message="cleaning not requested; take passed through unmodified",
        )

    from .. import cleaning_pipeline_adapter

    target = work_dir / "vocal_prepped.wav"
    config = cleaning_pipeline_adapter.get_default_config()
    report = cleaning_pipeline_adapter.AudioCleaningPipeline(config).process(
        str(source), str(target)
    )
    if not target.exists():
        raise PipelineError(f"vocal cleaning produced no output at {target}")

    return StageRecord(
        name="vocal_prep", status="ok", started_at=_now(),
        elapsed_seconds=time.perf_counter() - started,
        outputs={"vocal": str(target)},
        detail={"cleaning_report": _jsonable(report)},
    )


def _stage_align(cfg: SwapConfig, work_dir: Path, reference: Path, vocal: Path,
                 reference_kind: str) -> StageRecord:
    started = time.perf_counter()

    if cfg.offset_seconds is not None:
        result = align_mod.declared_offset(cfg.offset_seconds)
    else:
        result = align_mod.estimate_offset(
            reference, vocal, max_offset_s=cfg.max_offset_s
        )
        # Cross-correlation is unreliable on sparse vocal material: on a real pair
        # it returned the mirror placement, +12.70 s where the truth was -12.31 s,
        # with a peak margin of 0.0005. When the reference is the Suno vocal and
        # correlation admits it is ambiguous, aligning on the first sung sound is a
        # direct measurement rather than a search. Only for vocal-vs-vocal: it
        # assumes both sides open on the same word, which an instrumental does not.
        if reference_kind == "ai_vocal" and not result.trustworthy:
            onset = align_mod.estimate_offset_by_onset(reference, vocal)
            if onset is not None:
                onset.notes = (
                    "cross-correlation was ambiguous (offset {:+.2f}s, margin "
                    "{:.4f}); {}"
                ).format(result.offset_seconds, result.peak_margin, onset.notes)
                result = onset

    if cfg.require_alignment and not result.trustworthy:
        raise PipelineError(
            "alignment is not trustworthy and --require-alignment was given:\n"
            f"  offset      {result.offset_seconds:+.3f} s\n"
            f"  confidence  {result.confidence:.3f} "
            f"(threshold {align_mod.DEFAULT_MIN_CONFIDENCE})\n"
            f"  tempo       instrumental {result.instrumental_tempo} / "
            f"vocal {result.vocal_tempo}\n"
            f"  {result.notes}\n"
            "Pass --offset-seconds to declare the offset, or drop --require-alignment."
        )

    detail = result.to_dict()
    detail["reference"] = reference_kind
    detail["reference_path"] = str(reference)

    message = result.notes or ""
    if reference_kind == "instrumental" and result.method == "cross_correlation":
        message = (message + " ").strip() + (
            " [aligned against the instrumental - measured unreliable on rap; "
            "supply --offset-seconds if this looks wrong]"
        )
    return StageRecord(
        name="align", status="ok", started_at=_now(),
        elapsed_seconds=time.perf_counter() - started,
        detail=detail, message=message.strip(),
    )


def _stage_mix(
    cfg: SwapConfig, work_dir: Path, instrumental: Path, vocal: Path,
    alignment: Dict[str, Any],
) -> StageRecord:
    started = time.perf_counter()
    target = work_dir / f"{cfg.resolved_name()}_premaster.wav"

    instr_audio = mix_mod.load_audio(instrumental)
    vocal_audio = mix_mod.load_audio(vocal)

    stretched = False
    ratio = alignment.get("tempo_ratio")
    if cfg.allow_time_stretch and ratio and alignment.get("tempo_mismatch"):
        vocal_audio = align_mod.time_stretch_to(vocal_audio, mix_mod.MIX_SR, ratio)
        stretched = True

    vocal_audio = align_mod.apply_offset(
        vocal_audio, mix_mod.MIX_SR, float(alignment.get("offset_seconds") or 0.0)
    )

    audio, mix_result = mix_mod.mix(
        instr_audio, vocal_audio,
        sr=mix_mod.MIX_SR,
        vocal_balance_db=cfg.vocal_balance_db,
        duck_db=cfg.duck_db,
        bus_lufs_target=cfg.bus_lufs_target,
        bus_peak_dbfs=cfg.bus_peak_dbfs,
        vocal_hpf_hz=cfg.vocal_hpf_hz,
        output_path=target,
    )
    mix_mod.write_wav(audio, target, sr=mix_mod.MIX_SR)

    detail = mix_result.to_dict()
    detail["time_stretched"] = stretched
    return StageRecord(
        name="mix", status="ok", started_at=_now(),
        elapsed_seconds=time.perf_counter() - started,
        outputs={"premaster": str(target)}, detail=detail,
    )


def _stage_premaster(cfg: SwapConfig, work_dir: Path, premaster: Path) -> StageRecord:
    started = time.perf_counter()
    from .. import premaster as premaster_mod

    report = premaster_mod.analyze_premaster(Path(premaster))
    # `analyze_premaster` names this key "verdict"; reading "overall" here
    # silently produced UNKNOWN for every run until a test caught it.
    verdict = str(report.get("verdict", "UNKNOWN"))

    report_path = work_dir / "premaster_gates.json"
    with open(report_path, "w", encoding="utf-8") as fh:
        json.dump(_jsonable(report), fh, ensure_ascii=False, indent=2)

    return StageRecord(
        name="premaster", status="ok", started_at=_now(),
        elapsed_seconds=time.perf_counter() - started,
        outputs={"report": str(report_path)},
        detail={"verdict": verdict, "report": _jsonable(report)},
        message=f"premaster gates: {verdict}",
    )


def _stage_master(cfg: SwapConfig, work_dir: Path, premaster: Path) -> StageRecord:
    started = time.perf_counter()
    result = mastering_bridge.master(
        source_wav=Path(premaster),
        name=cfg.resolved_name(),
        project_dir=work_dir / "master_project",
        profile=cfg.profile,
        timeout=cfg.master_timeout_s,
    )
    outputs = {
        key: value
        for key, value in (
            ("master_32f", result.master_32f),
            ("master_16", result.master_16),
            ("master_mp3", result.master_mp3),
        )
        if value
    }
    return StageRecord(
        name="master", status="ok", started_at=_now(),
        elapsed_seconds=time.perf_counter() - started,
        outputs=outputs, detail=result.to_dict(),
    )


def _stage_verify(cfg: SwapConfig, work_dir: Path, master_detail: Dict[str, Any]) -> StageRecord:
    started = time.perf_counter()
    result = mastering_bridge.MasterResult(
        profile=master_detail.get("profile", cfg.profile),
        project_dir=master_detail.get("project_dir", ""),
        name=master_detail.get("name", cfg.resolved_name()),
        master_32f=master_detail.get("master_32f"),
        master_16=master_detail.get("master_16"),
        master_mp3=master_detail.get("master_mp3"),
        target_lufs=master_detail.get("target_lufs"),
        target_tp_dbtp=master_detail.get("target_tp_dbtp"),
    )
    result = mastering_bridge.verify_master(result)
    return StageRecord(
        name="verify", status="ok", started_at=_now(),
        elapsed_seconds=time.perf_counter() - started,
        detail=result.to_dict(),
        message=(
            f"{result.verdict}: {result.measured_lufs} LUFS "
            f"(target {result.target_lufs}), TP {result.measured_true_peak_dbtp} dBTP"
        ),
    )


def _jsonable(value: Any) -> Any:
    """Coerce numpy scalars and Paths so `json.dump` cannot fail at the last step."""
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "item") and callable(getattr(value, "item")):
        try:
            return value.item()
        except Exception:
            return str(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _pick_align_reference(cfg: SwapConfig, result: "SwapResult",
                          instrumental: Path) -> tuple:
    """Choose what the take is aligned against, and name the choice.

    The Suno vocal is preferred when separation produced one: two vocals of the
    same song share syllable placement, while a vocal and an instrumental share
    almost nothing an onset envelope can see. See `SwapConfig.align_reference`
    for the measurement behind that.
    """
    ai_vocal = (result.stages.get("instrumental").outputs.get("ai_vocal")
                if "instrumental" in result.stages else None)

    if cfg.align_reference == "instrumental":
        return instrumental, "instrumental"
    if cfg.align_reference == "vocal":
        if not ai_vocal:
            raise PipelineError(
                "--align-reference vocal was given but no Suno vocal stem is "
                "available. It comes from the separation stage, so this needs a "
                "run without --instrumental, or use --align-reference auto."
            )
        return Path(ai_vocal), "ai_vocal"
    if ai_vocal:
        return Path(ai_vocal), "ai_vocal"
    return instrumental, "instrumental"


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #

def run_swap(cfg: SwapConfig, on_stage: Optional[Callable[[StageRecord], None]] = None) -> SwapResult:
    """Run the full swap. Resumes from the manifest unless `cfg.resume` is False."""
    work_dir = cfg.resolved_work_dir()
    work_dir.mkdir(parents=True, exist_ok=True)

    previous = load_manifest(work_dir) if cfg.resume else {}
    result = SwapResult(config=cfg.to_dict(), work_dir=str(work_dir))

    def record(stage: StageRecord) -> None:
        result.stages[stage.name] = stage
        save_manifest(work_dir, result)
        if on_stage:
            on_stage(stage)

    def reuse(stage: str) -> Optional[StageRecord]:
        prior = _completed(previous, stage)
        if prior is None:
            return None
        restored = StageRecord(
            name=stage,
            status=prior.get("status", "ok"),
            started_at=prior.get("started_at", ""),
            elapsed_seconds=float(prior.get("elapsed_seconds") or 0.0),
            outputs=dict(prior.get("outputs") or {}),
            detail=dict(prior.get("detail") or {}),
            message=(prior.get("message") or "") + " [resumed]",
        )
        record(restored)
        return restored

    # 1. preflight - never resumed: the environment can change between runs, and
    #    that is exactly what preflight exists to catch.
    record(_stage_preflight(cfg, work_dir))

    # 2. instrumental
    stage = reuse("instrumental") or _stage_instrumental(cfg, work_dir)
    if stage.name not in result.stages:
        record(stage)
    instrumental = Path(stage.outputs["instrumental"])

    # 3. vocal prep
    stage = reuse("vocal_prep") or _stage_vocal_prep(cfg, work_dir)
    if stage.name not in result.stages:
        record(stage)
    vocal = Path(stage.outputs["vocal"])

    # 4. align - cheap, and its inputs may have just been rebuilt, so always rerun.
    reference, reference_kind = _pick_align_reference(cfg, result, instrumental)
    align_record = _stage_align(cfg, work_dir, reference, vocal, reference_kind)
    record(align_record)

    # 5. mix
    mix_record = _stage_mix(cfg, work_dir, instrumental, vocal, align_record.detail)
    record(mix_record)
    premaster_path = Path(mix_record.outputs["premaster"])
    result.deliverables["premaster"] = str(premaster_path)

    # 6. premaster gates
    gate_record = _stage_premaster(cfg, work_dir, premaster_path)
    record(gate_record)
    result.premaster_verdict = str(gate_record.detail.get("verdict", "UNKNOWN"))

    if cfg.skip_master:
        result.status = "premaster_only"
        save_manifest(work_dir, result)
        return result

    if result.premaster_verdict == "FAIL" and not cfg.master_on_gate_fail:
        result.status = "stopped_at_gate"
        save_manifest(work_dir, result)
        raise PipelineError(
            "premaster gates returned FAIL; refusing to master.\n"
            f"  report: {gate_record.outputs.get('report')}\n"
            "Fix the mix (usually vocal level or phase), or rerun with "
            "--master-on-gate-fail to proceed anyway."
        )

    # 7. master
    master_record = _stage_master(cfg, work_dir, premaster_path)
    record(master_record)
    result.deliverables.update(master_record.outputs)

    # 8. verify
    verify_record = _stage_verify(cfg, work_dir, master_record.detail)
    record(verify_record)
    result.master_verdict = str(verify_record.detail.get("verdict", "not_verified"))

    result.status = "complete"
    save_manifest(work_dir, result)
    return result
