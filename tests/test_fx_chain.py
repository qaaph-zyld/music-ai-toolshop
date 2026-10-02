"""FXChain schema tests — YAML parse, validation, registry resolution."""

import pytest
import yaml

from toolshop.fx.chain import (
    BUILTIN_STAGES, ChainSpecError, FXChain, FXStage, chains_dir,
    resolve_chain_path, validate,
)
from toolshop.fx.registry import PluginNotFoundError


FAKE_REG = {
    "plugins": [
        {"name": "FabFilter Pro-Q 3", "path": "C:/pf/proq3.vst3",
         "format": "vst3", "vendor": "FabFilter", "hostable": True,
         "plugin_name": None, "shell": None},
        {"name": "API-2500", "path": "C:/pf/waveshell.vst3",
         "format": "vst3-shell", "vendor": "Waves", "hostable": True,
         "plugin_name": "API-2500", "shell": "waves"},
        {"name": "Glitch2", "path": "C:/pf/glitch2.dll",
         "format": "vst2", "vendor": None, "hostable": False,
         "host_note": "vst2 needs a VST2 host"},
    ]
}


def test_parse_minimal(tmp_path):
    f = tmp_path / "c.yaml"
    f.write_text(yaml.safe_dump({
        "name": "t", "stages": [{"builtin": "hpf", "freq": 80}],
    }), encoding="utf-8")
    chain = FXChain.from_yaml(f)
    assert chain.name == "t"
    assert chain.sample_rate == 48000.0
    assert len(chain.stages) == 1
    assert chain.stages[0].builtin == "hpf"
    # stage-level fields merge into params for builtin stages
    assert chain.stages[0].params == {"freq": 80}


def test_parse_plugin_stage(tmp_path):
    f = tmp_path / "c.yaml"
    f.write_text(yaml.safe_dump({
        "name": "v",
        "stages": [
            {"plugin": "FabFilter Pro-Q 3", "params": {"x": 1}},
            {"plugin": "Waves/API-2500", "stateful": True},
        ],
    }), encoding="utf-8")
    chain = FXChain.from_yaml(f)
    assert chain.stages[0].plugin == "FabFilter Pro-Q 3"
    assert chain.stages[0].params == {"x": 1}
    assert chain.stages[1].stateful is True


def test_stage_needs_exactly_one_kind(tmp_path):
    for raw in ({"params": {}}, {"plugin": "A", "builtin": "hpf"}):
        f = tmp_path / "bad.yaml"
        f.write_text(yaml.safe_dump({"name": "b", "stages": [raw]}),
                     encoding="utf-8")
        with pytest.raises(ChainSpecError, match="exactly one"):
            FXChain.from_yaml(f)


def test_unknown_builtin_rejected(tmp_path):
    f = tmp_path / "bad.yaml"
    f.write_text(yaml.safe_dump({
        "name": "b", "stages": [{"builtin": "nope"}],
    }), encoding="utf-8")
    with pytest.raises(ChainSpecError, match="unknown builtin"):
        FXChain.from_yaml(f)


def test_resolve_and_fill_shell_plugin_name():
    chain = FXChain(stages=[FXStage(plugin="API-2500")])
    validate(chain, FAKE_REG)
    assert chain.stages[0].plugin_name == "API-2500"


def test_validate_rejects_unhostable():
    chain = FXChain(stages=[FXStage(plugin="Glitch2")])
    with pytest.raises(ChainSpecError, match="not hostable"):
        validate(chain, FAKE_REG)


def test_validate_unknown_plugin_lists_matches():
    chain = FXChain(stages=[FXStage(plugin="Pro-Q")])
    with pytest.raises(PluginNotFoundError):
        validate(chain, FAKE_REG)


def test_vendor_qualified_lookup():
    from toolshop.fx.registry import find_plugin
    entry = find_plugin(FAKE_REG, "Waves/API-2500")
    assert entry["plugin_name"] == "API-2500"
    entry = find_plugin(FAKE_REG, "api-2500")
    assert entry["vendor"] == "Waves"


def test_bundled_chains_load_and_validate():
    for yaml_file in chains_dir().glob("*.yaml"):
        chain = FXChain.from_yaml(yaml_file)
        assert chain.stages, f"{yaml_file.name} has no stages"
        for s in chain.stages:
            assert bool(s.plugin) != bool(s.builtin)


def test_all_builtins_are_valid():
    for name in BUILTIN_STAGES:
        chain = FXChain(stages=[FXStage(builtin=name)])
        assert chain.stages[0].builtin == name
