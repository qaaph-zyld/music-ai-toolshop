"""CLI for the vocal-swap lane: `toolshop vocal-swap ...`."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

from . import align as align_mod
from . import mastering_bridge
from . import mix as mix_mod
from .pipeline import PipelineError, StageRecord, SwapConfig, run_swap, load_manifest


def add_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "vocal-swap",
        help="Replace a Suno track's vocal with your own, mixed and mastered",
        description=(
            "Two tracks in, a mastered track out: the Suno track is separated to "
            "an instrumental, your take is aligned and mixed over it, the M4 "
            "premaster gates run, and the mastering chain finishes it."
        ),
    )
    sub = parser.add_subparsers(dest="swap_command")
    sub.required = True

    run_p = sub.add_parser("run", help="Run the full swap pipeline")
    run_p.add_argument("suno_track", type=Path, help="Suno track (full mix with the AI vocal)")
    run_p.add_argument("vocal_take", type=Path, help="Your vocal recording")
    run_p.add_argument("--name", type=str, default="", help="Output name (default: Suno track stem)")
    run_p.add_argument("--work-dir", type=Path, default=None,
                       help="Working directory (default: <data>/vocal_swap/<name>)")

    sep = run_p.add_argument_group("separation")
    sep.add_argument("--instrumental", type=Path, default=None,
                     help="Use this instrumental instead of separating the Suno track")
    sep.add_argument("--stem-preset", default="karaoke",
                     choices=["karaoke", "vocals-hq", "full-vocals", "full-vocals-hq"],
                     help="Separation preset (default: karaoke, the fast one)")

    voc = run_p.add_argument_group("vocal")
    voc.add_argument("--clean-vocal", action="store_true",
                     help="Run the cleaning pipeline over the take before mixing")
    voc.add_argument("--vocal-hpf", type=float, default=mix_mod.DEFAULT_VOCAL_HPF_HZ,
                     help=f"High-pass on the vocal in Hz (default: {mix_mod.DEFAULT_VOCAL_HPF_HZ:g}; 0 disables)")

    ali = run_p.add_argument_group("alignment")
    ali.add_argument("--align-reference", default="auto",
                     choices=["auto", "vocal", "instrumental"],
                     help="What to align the take against. 'vocal' uses the Suno "
                          "vocal stem (measured far more reliable than the "
                          "instrumental on rap); 'auto' prefers it when available")
    ali.add_argument("--offset-seconds", type=float, default=None,
                     help="Declare the offset instead of estimating it")
    ali.add_argument("--require-alignment", action="store_true",
                     help="Fail if alignment confidence is low or tempos disagree")
    ali.add_argument("--allow-time-stretch", action="store_true",
                     help="Time-stretch the vocal when tempos disagree (phase vocoder)")
    ali.add_argument("--max-offset", type=float, default=align_mod.DEFAULT_MAX_OFFSET_S,
                     help=f"Widest offset searched, seconds (default: {align_mod.DEFAULT_MAX_OFFSET_S:g})")

    mixg = run_p.add_argument_group("mix")
    mixg.add_argument("--vocal-balance", type=float, default=mix_mod.DEFAULT_VOCAL_BALANCE_DB,
                      help=f"Vocal loudness relative to the instrumental, LU (default: {mix_mod.DEFAULT_VOCAL_BALANCE_DB:g})")
    mixg.add_argument("--duck", type=float, default=mix_mod.DEFAULT_DUCK_DB,
                      help="Duck the instrumental under the vocal by this many dB (default: 0, off)")
    mixg.add_argument("--bus-peak", type=float, default=mix_mod.DEFAULT_BUS_PEAK_DBFS,
                      help=f"Premaster peak target, dBFS (default: {mix_mod.DEFAULT_BUS_PEAK_DBFS:g})")

    mas = run_p.add_argument_group("master")
    mas.add_argument("--profile", default=mastering_bridge.DEFAULT_PROFILE,
                     choices=sorted(mastering_bridge.PROFILE_TARGETS),
                     help=f"Mastering profile (default: {mastering_bridge.DEFAULT_PROFILE})")
    mas.add_argument("--skip-master", action="store_true",
                     help="Stop after the premaster and its gates")
    mas.add_argument("--master-on-gate-fail", action="store_true",
                     help="Master even if the premaster gates FAIL (not recommended)")
    mas.add_argument("--master-timeout", type=int, default=mastering_bridge.DEFAULT_TIMEOUT_S,
                     help=f"Mastering timeout in seconds (default: {mastering_bridge.DEFAULT_TIMEOUT_S})")

    run_p.add_argument("--no-resume", action="store_true",
                       help="Ignore any existing manifest and redo every stage")
    run_p.add_argument("--json", action="store_true", help="Print the result as JSON")

    doc_p = sub.add_parser("doctor", help="Check that the swap pipeline can run here")
    doc_p.add_argument("--json", action="store_true", help="Print the report as JSON")

    st_p = sub.add_parser("status", help="Show the manifest of a previous run")
    st_p.add_argument("work_dir", type=Path, help="Working directory of the run")
    st_p.add_argument("--json", action="store_true", help="Print the manifest as JSON")


def run(args: argparse.Namespace) -> int:
    command = getattr(args, "swap_command", None)
    if command == "run":
        return _cmd_run(args)
    if command == "doctor":
        return _cmd_doctor(args)
    if command == "status":
        return _cmd_status(args)
    print(f"Error: Unknown vocal-swap subcommand: {command}", file=sys.stderr)
    return 1


def _cmd_run(args: argparse.Namespace) -> int:
    cfg = SwapConfig(
        suno_track=args.suno_track,
        vocal_take=args.vocal_take,
        name=args.name,
        work_dir=args.work_dir,
        instrumental=args.instrumental,
        stem_preset=args.stem_preset,
        clean_vocal=args.clean_vocal,
        vocal_hpf_hz=args.vocal_hpf,
        offset_seconds=args.offset_seconds,
        require_alignment=args.require_alignment,
        allow_time_stretch=args.allow_time_stretch,
        max_offset_s=args.max_offset,
        vocal_balance_db=args.vocal_balance,
        duck_db=args.duck,
        bus_peak_dbfs=args.bus_peak,
        profile=args.profile,
        skip_master=args.skip_master,
        master_on_gate_fail=args.master_on_gate_fail,
        master_timeout_s=args.master_timeout,
        resume=not args.no_resume,
    )

    def announce(stage: StageRecord) -> None:
        if args.json:
            return
        mark = {"ok": "[ok]", "skipped": "[--]", "failed": "[!!]"}.get(stage.status, "[??]")
        line = f"{mark} {stage.name:<12} {stage.elapsed_seconds:6.1f}s"
        if stage.message:
            line += f"  {stage.message}"
        print(line, flush=True)

    try:
        result = run_swap(cfg, on_stage=announce)
    except PipelineError as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        return 1
    except FileNotFoundError as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return 0

    _print_summary(result.to_dict())
    return 0


def _print_summary(data: Dict[str, Any]) -> None:
    print()
    print(f"Status:            {data['status']}")
    print(f"Premaster gates:   {data['premaster_verdict']}")
    print(f"Master verdict:    {data['master_verdict']}")

    align_detail = ((data.get("stages") or {}).get("align") or {}).get("detail") or {}
    if align_detail:
        print(
            f"Alignment:         {align_detail.get('offset_seconds', 0):+.3f} s "
            f"(confidence {align_detail.get('confidence', 0):.3f}, "
            f"{'trustworthy' if align_detail.get('trustworthy') else 'LOW - check by ear'})"
        )

    mix_detail = ((data.get("stages") or {}).get("mix") or {}).get("detail") or {}
    if mix_detail:
        print(
            f"Mix:               vocal {mix_detail.get('vocal_gain_db', 0):+.1f} dB "
            f"to sit {mix_detail.get('vocal_balance_db', 0):+.1f} LU over the "
            f"instrumental; premaster {mix_detail.get('output_lufs')} LUFS "
            f"peak {mix_detail.get('output_peak_dbfs')} dBFS"
        )

    print("\nDeliverables:")
    for key, value in (data.get("deliverables") or {}).items():
        print(f"  {key:<12} {value}")
    print(f"\nWork dir:          {data['work_dir']}")


def _cmd_doctor(args: argparse.Namespace) -> int:
    import importlib.util

    report: Dict[str, Any] = {"packages": {}, "mastering": {}}
    for module, extra in (
        ("librosa", "audio"), ("soundfile", "audio"), ("numpy", "audio"),
        ("scipy", "audio"), ("pyloudnorm", "track"), ("audio_separator", "stems"),
    ):
        try:
            present = importlib.util.find_spec(module) is not None
        except (ImportError, ValueError):
            present = False
        report["packages"][module] = {"present": present, "extra": extra}

    report["mastering"] = mastering_bridge.check_environment()

    missing = [m for m, info in report["packages"].items() if not info["present"]]
    report["ok"] = not missing and bool(report["mastering"].get("ok"))

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["ok"] else 1

    print("vocal-swap doctor\n")
    for module, info in report["packages"].items():
        mark = "ok " if info["present"] else "MISSING"
        print(f"  [{mark:>7}] {module}  (extra: {info['extra']})")
    print()
    mast = report["mastering"]
    for key in ("wsl_available", "script_exists_windows", "ffmpeg_in_wsl", "script_visible_in_wsl"):
        print(f"  [{'ok     ' if mast.get(key) else 'MISSING'}] {key}")
    for err in mast.get("errors", []):
        print(f"      ! {err}")
    print(f"\nOverall: {'PASS' if report['ok'] else 'FAIL'}")
    if missing:
        print(f"Install missing packages:  pip install -e .[swap]")
    return 0 if report["ok"] else 1


def _cmd_status(args: argparse.Namespace) -> int:
    manifest = load_manifest(Path(args.work_dir))
    if not manifest:
        print(f"No manifest found in {args.work_dir}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return 0
    for name, stage in (manifest.get("stages") or {}).items():
        print(f"  {stage.get('status', '?'):<8} {name:<12} "
              f"{stage.get('elapsed_seconds', 0):6.1f}s  {stage.get('message', '')}")
    _print_summary(manifest)
    return 0
