"""CLI handler for `toolshop fx` — headless plugin rendering.

Subcommands:
    scan    - walk plugin dirs (+Waves bundles) → plugin_registry.json
    probe   - per-plugin subprocess capability probe → plugin_probes.json
    params  - dump a plugin's parameter names (authoring aid)
    chains  - list bundled chain YAMLs
    render  - render one file through a chain
    batch   - resumable directory render
    measure - LUFS/true-peak delta between input and output
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, Sequence

from toolshop import paths
from . import registry as registry_mod
from . import probe as probe_mod
from .chain import FXChain, resolve_chain_path, validate


def add_parser(subparsers: argparse._SubParsersAction) -> None:
    fx = subparsers.add_parser(
        "fx", help="Headless VST3 plugin rendering (registry, chains, batch)"
    )
    sub = fx.add_subparsers(dest="fx_command")
    sub.required = True

    sub.add_parser("scan", help="Scan plugin dirs → plugin_registry.json")

    probe_p = sub.add_parser("probe", help="Probe plugins in subprocesses")
    probe_p.add_argument("--only", type=str, default=None, help="Probe one plugin name")
    probe_p.add_argument("--force", action="store_true", help="Re-probe everything")
    probe_p.add_argument("--limit", type=int, default=0)
    probe_p.add_argument("--timeout", type=float, default=None,
                       help="Per-plugin timeout s (default 60, shells 120)")

    params_p = sub.add_parser("params", help="Dump a plugin's parameter names")
    params_p.add_argument("plugin", type=str, help="Registry plugin name")

    sub.add_parser("chains", help="List bundled chain YAMLs")

    render_p = sub.add_parser("render", help="Render a file through a chain")
    render_p.add_argument("input", type=str)
    render_p.add_argument("--chain", required=True, help="Chain name or YAML path")
    render_p.add_argument("-o", "--output", type=str, default=None)
    render_p.add_argument("--sr", type=int, default=None, help="Override chain SR")

    batch_p = sub.add_parser("batch", help="Resumable directory render")
    batch_p.add_argument("input_dir", type=str)
    batch_p.add_argument("--chain", required=True)
    batch_p.add_argument("--out", type=str, default=None,
                        help="Output dir (default data/toolshop/fx/batch/<chain>)")
    batch_p.add_argument("--limit", type=int, default=0)
    batch_p.add_argument("--offset", type=int, default=0)
    batch_p.add_argument("--ext", type=str, default=None,
                        help="Comma-separated extensions")
    batch_p.add_argument("--no-resume", action="store_true")

    meas_p = sub.add_parser("measure", help="LUFS/TP delta between two files")
    meas_p.add_argument("input", type=str)
    meas_p.add_argument("output", type=str)
    meas_p.add_argument("--json", action="store_true")


def _load_chain(chain_arg: str) -> FXChain:
    return FXChain.from_yaml(resolve_chain_path(chain_arg))


def run(args: argparse.Namespace) -> int:
    cmd = args.fx_command

    if cmd == "scan":
        reg = registry_mod.scan()
        out = registry_mod.write(reg)
        n = len(reg["plugins"])
        hostable = sum(1 for p in reg["plugins"] if p.get("hostable"))
        print(f"scanned {n} entries ({hostable} hostable) -> {out}")
        return 0

    if cmd == "probe":
        reg = registry_mod.load()
        db = probe_mod.probe_all(
            reg, only=args.only, force=args.force, limit=args.limit,
        )
        registry_mod.save(probe_mod.merge_probe_into_registry(reg, db))
        verdicts: dict[str, int] = {}
        for r in db["results"]:
            verdicts[r.get("verdict", "?")] = verdicts.get(r.get("verdict", "?"), 0) + 1
        print("probe verdicts:", verdicts)
        print(f"probe db -> {probe_mod.probes_path()}")
        return 0

    if cmd == "params":
        reg = registry_mod.load()
        entry = registry_mod.find_plugin(reg, args.plugin)
        if entry.get("probe") and entry["probe"].get("parameters"):
            params = entry["probe"]["parameters"]
            print(json.dumps(params, indent=2, default=str))
            return 0
        # Fall back to a live param dump (loads the plugin once).
        from . import engine
        from .chain import FXStage
        plugin = engine.load_plugin_stage(FXStage(plugin=entry["name"]), entry)
        print(json.dumps(dict(plugin.parameters), indent=2, default=str))
        return 0

    if cmd == "chains":
        from .chain import chains_dir
        for f in sorted(chains_dir().glob("*.yaml")):
            print(f.stem)
        return 0

    if cmd == "render":
        chain = _load_chain(args.chain)
        if args.sr:
            chain.sample_rate = args.sr
        reg = registry_mod.load()
        validate(chain, reg)
        out = args.output or str(
            Path(args.input).with_name(
                f"{Path(args.input).stem}_{chain.name}.wav")
        )
        from . import engine
        result = engine.render_file(chain, reg, args.input, out)
        print(json.dumps(result, indent=2))
        return 0

    if cmd == "batch":
        from . import batch_fx
        chain = _load_chain(args.chain)
        reg = registry_mod.load()
        validate(chain, reg)
        out_dir = Path(args.out) if args.out else (
            paths.subdir("fx", "batch", chain.name, create=True)
        )
        exts = args.ext.split(",") if args.ext else None
        status = batch_fx.run_fx_batch(
            chain, reg, Path(args.input_dir), out_dir,
            extensions=exts, limit=args.limit, offset=args.offset,
            resume=not args.no_resume,
        )
        done = sum(1 for t in status["tracks"] if t.get("status") == "completed")
        failed = sum(1 for t in status["tracks"] if t.get("status") == "failed")
        print(f"batch done: {done} completed, {failed} failed, "
              f"status -> {out_dir / 'batch_status.json'}")
        return 0 if failed == 0 else 1

    if cmd == "measure":
        from toolshop import premaster
        a = premaster.analyze_premaster(Path(args.input))
        b = premaster.analyze_premaster(Path(args.output))

        def _metrics(d: dict) -> dict:
            m = {
                "integrated_lufs": d.get("integrated_lufs"),
                "true_peak_dbfs_approx": d.get("true_peak_dbfs_approx"),
                "max_short_term_lufs": d.get("max_short_term_lufs"),
            }
            for g in d.get("gates", []):
                if g.get("name") in ("sample_peak_dbfs", "crest_factor_db",
                                     "psr_db") and g.get("value") is not None:
                    m[g["name"]] = g["value"]
            return m

        report = {"input": _metrics(a), "output": _metrics(b),
                  "verdicts": {"input": a.get("verdict"), "output": b.get("verdict")}}
        for k in set(report["input"]) & set(report["output"]):
            if report["input"][k] is not None and report["output"][k] is not None:
                report.setdefault("delta", {})[k] = round(
                    report["output"][k] - report["input"][k], 2)
        if args.json:
            print(json.dumps(report, indent=2, default=str))
        else:
            for side in ("input", "output"):
                print(f"{side}: {report[side]}")
            if "delta" in report:
                print(f"delta: {report['delta']}")
        return 0

    return 2
