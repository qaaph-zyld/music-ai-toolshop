"""Registry scan tests — fake dir trees, dedup, Waves bundle enumeration."""

import json
from pathlib import Path

import pytest

from toolshop.fx import registry


def _fake_tree(tmp_path: Path) -> Path:
    root = tmp_path / "VST3"
    (root / "FabFilter").mkdir(parents=True)
    (root / "FabFilter" / "FabFilter Pro-Q 3.vst3").mkdir()
    (root / "T-De-Esser.vst3").mkdir()
    (root / "WaveShell1-VST3 14.12_x64.vst3").mkdir()
    return root


def _fake_waves(tmp_path: Path) -> Path:
    wdir = tmp_path / "Plug-Ins V14"
    wdir.mkdir(parents=True)
    for name in ("API-2500", "C4", "CLA Vocals"):
        (wdir / f"{name}.bundle").mkdir()
    return wdir


def test_scan_finds_vst3_bundles(tmp_path):
    root = _fake_tree(tmp_path)
    reg = registry.scan(roots=[root], waves_bundle_dir=tmp_path / "nope")
    names = [p["name"] for p in reg["plugins"]]
    assert "FabFilter Pro-Q 3" in names
    assert "T-De-Esser" in names
    for p in reg["plugins"]:
        assert p["format"] in ("vst3", "vst3-shell")


def test_waves_shell_marked_unhostable_members_listed(tmp_path):
    root = _fake_tree(tmp_path)
    wdir = _fake_waves(tmp_path)
    reg = registry.scan(roots=[root], waves_bundle_dir=wdir)

    shell = next(p for p in reg["plugins"] if "WaveShell" in p["name"])
    assert shell["shell"] == "waves"
    assert shell["hostable"] is False

    members = [p for p in reg["plugins"] if p["source"] == "waves-bundles"]
    assert {p["name"] for p in members} == {"API-2500", "C4", "CLA Vocals"}
    for m in members:
        assert m["format"] == "vst3-shell"
        assert m["hostable"] is True
        assert m["plugin_name"] == m["name"]
        assert m["path"].endswith("WaveShell1-VST3 14.12_x64.vst3")


def test_scan_without_shell_skips_waves(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    wdir = _fake_waves(tmp_path)
    reg = registry.scan(roots=[empty], waves_bundle_dir=wdir)
    assert not any(p["source"] == "waves-bundles" for p in reg["plugins"])


def test_vendor_guess_from_first_dir(tmp_path):
    root = _fake_tree(tmp_path)
    reg = registry.scan(roots=[root], waves_bundle_dir=tmp_path / "nope")
    proq = next(p for p in reg["plugins"] if p["name"] == "FabFilter Pro-Q 3")
    assert proq["vendor"] == "FabFilter"


def test_vst2_marked_unhostable(tmp_path):
    root = tmp_path / "VstPlugins"
    root.mkdir()
    (root / "Glitch2.dll").write_bytes(b"x")
    reg = registry.scan(roots=[root], waves_bundle_dir=tmp_path / "nope")
    g = next(p for p in reg["plugins"] if p["name"] == "Glitch2")
    assert g["format"] == "vst2" and g["hostable"] is False


def test_write_load_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("TOOLSHOP_DATA_DIR", str(tmp_path / "data"))
    root = _fake_tree(tmp_path)
    reg = registry.scan(roots=[root], waves_bundle_dir=tmp_path / "nope")
    out = registry.write(reg)
    assert out.exists()
    loaded = registry.load()
    assert loaded["plugins"] == reg["plugins"]
