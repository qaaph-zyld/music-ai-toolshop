"""Drive `mastering_tool/master_pipeline_v3.sh` from Python, through WSL.

**The engine is the bash pipeline, not the tray EXE.** The EXE is a GUI wrapper
around this script; calling it from a pipeline would mean driving a tray app.
The script is the real interface:

    bash master_pipeline_v3.sh <source.wav> <name> <project_dir> <profile>

and it writes `<project_dir>/master/<name>_MASTER_32f.wav`, `_MASTER_16.wav` and
`_MASTER.mp3`, with QC under `<project_dir>/verification/`.

**Path translation is the whole risk here.** The script runs inside WSL and
receives paths as strings; hand it `D:\\Projects\\...` and ffmpeg fails deep
inside stage A with an error that looks like an audio problem. `to_wsl_path`
converts once, at the boundary, and `check_environment` proves the translated
path is visible from inside WSL *before* a long run starts rather than after.

The submodule is in daily use and is not modified from here - this module only
calls it.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

#: Profiles `family_policy.sh` accepts, with the targets it sets. Mirrored here
#: only to fail fast on a typo - the script remains the authority, and
#: `verify_master` reads the targets back from this table purely to *report*
#: agreement, never to overrule what the chain actually did.
PROFILE_TARGETS: Dict[str, Dict[str, float]] = {
    "archival": {"lufs": -10.0, "tp_dbtp": -1.0},
    "club": {"lufs": -8.5, "tp_dbtp": -1.0},
    "streaming": {"lufs": -14.0, "tp_dbtp": -1.5},
    "hiphop": {"lufs": -8.0, "tp_dbtp": -1.0},
    "german_rap": {"lufs": -9.0, "tp_dbtp": -1.0},
    "german_drill": {"lufs": -8.0, "tp_dbtp": -0.8},
    "serbian_drill": {"lufs": -8.5, "tp_dbtp": -1.0},
    "house": {"lufs": -8.5, "tp_dbtp": -1.0},
}

DEFAULT_PROFILE = "serbian_drill"

#: The mastering chain runs ffmpeg and several LV2 stages over the whole track.
#: Generous, because a timeout that fires mid-chain leaves half-written
#: intermediates that look like corrupt audio to the next run.
DEFAULT_TIMEOUT_S = 1800

MASTERING_TOOL_DIR = Path(__file__).resolve().parents[2] / "mastering_tool"
PIPELINE_SCRIPT = "master_pipeline_v3.sh"


class MasteringUnavailable(RuntimeError):
    """WSL, bash, or the mastering script is not usable on this machine."""


class MasteringFailed(RuntimeError):
    """The mastering chain ran and returned non-zero."""


@dataclass
class MasterResult:
    """What the chain produced, and whether it hit the profile it was given."""

    profile: str
    project_dir: str
    name: str
    master_32f: Optional[str]
    master_16: Optional[str]
    master_mp3: Optional[str]
    target_lufs: Optional[float]
    target_tp_dbtp: Optional[float]
    measured_lufs: Optional[float] = None
    measured_true_peak_dbtp: Optional[float] = None
    lufs_delta: Optional[float] = None
    verdict: str = "not_verified"
    elapsed_seconds: float = 0.0
    log_tail: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        for key in ("measured_lufs", "measured_true_peak_dbtp", "lufs_delta", "elapsed_seconds"):
            if isinstance(data.get(key), float):
                data[key] = round(data[key], 2)
        return data


def to_wsl_path(path: Path) -> str:
    """Convert a Windows path to its /mnt/<drive> WSL equivalent.

    Paths that are already POSIX pass through unchanged, so this is safe to call
    unconditionally and safe to call twice.
    """
    text = str(path).replace("\\", "/")
    match = re.match(r"^([A-Za-z]):/(.*)$", text)
    if match:
        drive, rest = match.groups()
        return f"/mnt/{drive.lower()}/{rest}"
    return text


def wsl_available() -> bool:
    return shutil.which("wsl.exe") is not None or shutil.which("wsl") is not None


def _wsl_exe() -> str:
    return shutil.which("wsl.exe") or shutil.which("wsl") or "wsl.exe"


def run_in_wsl(command: str, timeout: int = 120) -> subprocess.CompletedProcess:
    """Run a bash command inside WSL, capturing UTF-8 output."""
    return subprocess.run(
        [_wsl_exe(), "-e", "bash", "-lc", command],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def check_environment(mastering_dir: Path = MASTERING_TOOL_DIR) -> Dict[str, Any]:
    """Prove the mastering chain is runnable before anything long starts.

    Checked here rather than trusted: WSL present, bash reachable, ffmpeg on the
    WSL PATH (the chain's stages A-C are pure ffmpeg), and the script visible at
    its translated path.
    """
    report: Dict[str, Any] = {
        "wsl_available": wsl_available(),
        "script_exists_windows": (mastering_dir / PIPELINE_SCRIPT).exists(),
        "ffmpeg_in_wsl": False,
        "script_visible_in_wsl": False,
        "errors": [],
    }
    if not report["wsl_available"]:
        report["errors"].append("wsl.exe not found on PATH")
        report["ok"] = False
        return report
    if not report["script_exists_windows"]:
        report["errors"].append(f"{PIPELINE_SCRIPT} not found in {mastering_dir}")

    script_wsl = to_wsl_path(mastering_dir / PIPELINE_SCRIPT)
    try:
        probe = run_in_wsl(f"command -v ffmpeg >/dev/null && test -f '{script_wsl}' && echo READY")
    except subprocess.TimeoutExpired:
        report["errors"].append("WSL did not respond within 120 s")
        return report

    if "READY" in (probe.stdout or ""):
        report["ffmpeg_in_wsl"] = True
        report["script_visible_in_wsl"] = True
    else:
        report["ok"] = False
        detail = (probe.stderr or probe.stdout or "").strip().splitlines()[-3:]
        # Distinguish the two failure modes; they need different fixes.
        ff = run_in_wsl("command -v ffmpeg || true")
        report["ffmpeg_in_wsl"] = bool((ff.stdout or "").strip())
        vis = run_in_wsl(f"test -f '{script_wsl}' && echo YES || true")
        report["script_visible_in_wsl"] = "YES" in (vis.stdout or "")
        if not report["ffmpeg_in_wsl"]:
            report["errors"].append("ffmpeg is not installed inside WSL (apt install ffmpeg)")
        if not report["script_visible_in_wsl"]:
            report["errors"].append(f"{script_wsl} not visible from inside WSL")
        if not report["errors"] and detail:
            report["errors"].append("; ".join(detail))

    report["ok"] = not report["errors"]
    return report


def resolve_profile(profile: str) -> Dict[str, float]:
    if profile not in PROFILE_TARGETS:
        raise ValueError(
            f"unknown mastering profile '{profile}'. "
            f"Valid: {', '.join(sorted(PROFILE_TARGETS))}"
        )
    return PROFILE_TARGETS[profile]


def master(
    source_wav: Path,
    name: str,
    project_dir: Path,
    profile: str = DEFAULT_PROFILE,
    mastering_dir: Path = MASTERING_TOOL_DIR,
    timeout: int = DEFAULT_TIMEOUT_S,
    env_overrides: Optional[Dict[str, str]] = None,
) -> MasterResult:
    """Run the mastering chain over `source_wav`."""
    import time

    source_wav = Path(source_wav)
    project_dir = Path(project_dir)
    if not source_wav.exists():
        raise FileNotFoundError(f"premaster not found: {source_wav}")

    targets = resolve_profile(profile)
    env_report = check_environment(mastering_dir)
    if not env_report.get("ok"):
        raise MasteringUnavailable("; ".join(env_report["errors"]) or "WSL environment unusable")

    project_dir.mkdir(parents=True, exist_ok=True)

    script_dir_wsl = to_wsl_path(mastering_dir)
    source_wsl = to_wsl_path(source_wav)
    project_wsl = to_wsl_path(project_dir)

    prefix = ""
    if env_overrides:
        # Quoted per-variable: an EQ_CHAIN value contains '=' and ':' and would
        # otherwise be re-split by the shell.
        prefix = " ".join(f"{k}='{v}'" for k, v in env_overrides.items()) + " "

    command = (
        f"cd '{script_dir_wsl}' && {prefix}bash {PIPELINE_SCRIPT} "
        f"'{source_wsl}' '{name}' '{project_wsl}' '{profile}'"
    )
    logger.info("mastering: %s", command)

    started = time.perf_counter()
    try:
        proc = run_in_wsl(command, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise MasteringFailed(
            f"mastering chain exceeded {timeout} s; intermediates in {project_dir/'intermediate'} "
            "are incomplete and should be deleted before retrying"
        ) from exc
    elapsed = time.perf_counter() - started

    combined = ((proc.stdout or "") + (proc.stderr or "")).splitlines()
    tail = [line for line in combined if line.strip()][-25:]
    if proc.returncode != 0:
        raise MasteringFailed(
            f"master_pipeline_v3.sh exited {proc.returncode}\n" + "\n".join(tail)
        )

    out_dir = project_dir / "master"

    def _found(suffix: str) -> Optional[str]:
        candidate = out_dir / f"{name}{suffix}"
        return str(candidate) if candidate.exists() else None

    result = MasterResult(
        profile=profile,
        project_dir=str(project_dir),
        name=name,
        master_32f=_found("_MASTER_32f.wav"),
        master_16=_found("_MASTER_16.wav"),
        master_mp3=_found("_MASTER.mp3"),
        target_lufs=targets["lufs"],
        target_tp_dbtp=targets["tp_dbtp"],
        elapsed_seconds=elapsed,
        log_tail=tail,
    )

    # A zero exit code with no deliverable is the failure mode that matters: the
    # chain "succeeded" and produced nothing. Never report that as success.
    if not result.master_16 and not result.master_32f:
        raise MasteringFailed(
            f"mastering exited 0 but no deliverable appeared in {out_dir}\n" + "\n".join(tail)
        )
    return result


def verify_master(result: MasterResult) -> MasterResult:
    """Measure the delivered master and compare it to the profile's targets.

    Reads the 16-bit deliverable because that is what the chain's own QC checks
    and what ships. Verdict is `pass` within 1.0 LU of target and under the
    true-peak ceiling, `flag` within 2.0 LU, `fail` beyond.
    """
    import numpy as np
    import soundfile as sf
    import pyloudnorm as pyln

    target_file = result.master_16 or result.master_32f
    if not target_file or not Path(target_file).exists():
        result.verdict = "not_verified"
        return result

    data, sr = sf.read(target_file, always_2d=True)
    meter = pyln.Meter(sr)
    measured = float(meter.integrated_loudness(data))

    mono = data.mean(axis=1)
    from ..premaster import true_peak_dbfs

    tp = float(true_peak_dbfs(mono))

    result.measured_lufs = measured
    result.measured_true_peak_dbtp = tp
    if result.target_lufs is not None and np.isfinite(measured):
        delta = measured - result.target_lufs
        result.lufs_delta = delta
        over_ceiling = (
            result.target_tp_dbtp is not None
            and np.isfinite(tp)
            and tp > result.target_tp_dbtp + 0.1
        )
        if over_ceiling:
            result.verdict = "fail"
        elif abs(delta) <= 1.0:
            result.verdict = "pass"
        elif abs(delta) <= 2.0:
            result.verdict = "flag"
        else:
            result.verdict = "fail"
    return result
