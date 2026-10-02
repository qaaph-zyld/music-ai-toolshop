"""FXChain — ordered-stage YAML format for the fx lane.

Distinct from ``mastering_tool.tools.chain_dsl.schema.Chain``, which is a
fixed-slot mastering chain (hpf/eq/deesser/comp/clip/limit) consumed by the
open_DAW master bus. An FXChain is an *ordered list* of stages, each either a
real plugin (resolved through the registry) or a builtin pedalboard-backed
stage reusing the chain_dsl field names::

    name: serbian-drill-vocal
    sample_rate: 48000
    assert_wet: true          # verify the chain actually changed the audio
    stages:
      - plugin: "RX 10 Voice De-noise"
        params: {}
      - builtin: comp
        threshold_db: -18
      - plugin: "Waves/CLA Vocals"   # vendor/name or plain registry name
        stateful: true             # fresh plugin instance per file
        bypass: false
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore

BUILTIN_STAGES = ("hpf", "eq", "deesser", "comp", "clip", "limit")

#: Directory searched (after CWD/absolute) when --chain is given a bare name.
def chains_dir() -> Path:
    return Path(__file__).resolve().parent / "chains"


class ChainSpecError(ValueError):
    """A chain file or stage failed validation."""


@dataclass
class FXStage:
    """One stage in an FXChain.

    Exactly one of ``plugin`` (registry name) or ``builtin`` (chain_dsl stage
    name) must be set.
    """

    plugin: Optional[str] = None
    builtin: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)
    plugin_name: Optional[str] = None  # explicit shell member override
    bypass: bool = False
    stateful: bool = False             # reload instance per file

    def active(self) -> bool:
        return not self.bypass


@dataclass
class FXChain:
    name: str = "unnamed"
    sample_rate: float = 48000.0
    stages: List[FXStage] = field(default_factory=list)
    assert_wet: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "sample_rate": self.sample_rate,
            "assert_wet": self.assert_wet,
            "stages": [
                {
                    k: v for k, v in {
                        "plugin": s.plugin,
                        "builtin": s.builtin,
                        "params": s.params,
                        "plugin_name": s.plugin_name,
                        "bypass": s.bypass,
                        "stateful": s.stateful,
                    }.items()
                    if v not in (None, {}, False)
                }
                for s in self.stages
            ],
        }

    def to_yaml(self, path: Path | str) -> None:
        if yaml is None:
            raise RuntimeError("pyyaml is required for YAML output")
        Path(path).write_text(
            yaml.safe_dump(self.to_dict(), sort_keys=False), encoding="utf-8"
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FXChain":
        if not isinstance(data, dict):
            raise ChainSpecError(f"chain must be a mapping, got {type(data).__name__}")
        stages: List[FXStage] = []
        for i, raw in enumerate(data.get("stages", [])):
            if not isinstance(raw, dict):
                raise ChainSpecError(f"stage {i} must be a mapping, got {type(raw).__name__}")
            plugin = raw.get("plugin")
            builtin = raw.get("builtin")
            if bool(plugin) == bool(builtin):
                raise ChainSpecError(
                    f"stage {i}: set exactly one of 'plugin' or 'builtin'"
                )
            if builtin and builtin not in BUILTIN_STAGES:
                raise ChainSpecError(
                    f"stage {i}: unknown builtin {builtin!r}; "
                    f"valid: {', '.join(BUILTIN_STAGES)}"
                )
            # Builtin stage fields live at stage level (freq, threshold_db...);
            # explicit `params:` wins on collision.
            _KNOWN = {"plugin", "builtin", "params", "plugin_name",
                      "bypass", "stateful"}
            extras = {k: v for k, v in raw.items() if k not in _KNOWN}
            params = {**extras, **(raw.get("params") or {})}
            if not isinstance(params, dict):
                raise ChainSpecError(f"stage {i}: params must be a mapping")
            stages.append(FXStage(
                plugin=plugin,
                builtin=builtin,
                params=params,
                plugin_name=raw.get("plugin_name"),
                bypass=bool(raw.get("bypass", False)),
                stateful=bool(raw.get("stateful", False)),
            ))
        return cls(
            name=str(data.get("name", "unnamed")),
            sample_rate=float(data.get("sample_rate", 48000.0)),
            stages=stages,
            assert_wet=bool(data.get("assert_wet", True)),
        )

    @classmethod
    def from_yaml(cls, path: Path | str) -> "FXChain":
        if yaml is None:
            raise RuntimeError("pyyaml is required for YAML input")
        return cls.from_dict(yaml.safe_load(Path(path).read_text(encoding="utf-8")))

    @classmethod
    def from_json(cls, path: Path | str) -> "FXChain":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def resolve_chain_path(name_or_path: str) -> Path:
    """Resolve a chain argument: absolute/relative path, else bundled name."""
    p = Path(name_or_path)
    if p.exists():
        return p
    if p.suffix not in (".yaml", ".yml"):
        for cand in chains_dir().glob(f"{name_or_path}.*"):
            if cand.suffix in (".yaml", ".yml"):
                return cand
        direct = chains_dir() / f"{name_or_path}.yaml"
        if direct.exists():
            return direct
    raise FileNotFoundError(
        f"chain not found: {name_or_path!r} (looked at path and {chains_dir()})"
    )


def validate(chain: FXChain, reg: Dict[str, Any]) -> FXChain:
    """Resolve every plugin stage against the registry; raise on unknown.

    Returns the chain with each plugin stage's ``plugin_name`` filled from the
    registry when the entry is a shell member and none was given explicitly.
    """
    from .registry import find_plugin  # deferred: registry imports nothing here

    for i, stage in enumerate(chain.stages):
        if stage.plugin:
            entry = find_plugin(reg, stage.plugin)
            if not entry.get("hostable"):
                raise ChainSpecError(
                    f"stage {i}: {stage.plugin!r} is {entry.get('format')} — "
                    f"not hostable by pedalboard ({entry.get('host_note')})"
                )
            if stage.plugin_name is None and entry.get("plugin_name"):
                stage.plugin_name = entry["plugin_name"]
    return chain
