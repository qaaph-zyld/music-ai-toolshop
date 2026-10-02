"""Engine tests — builtin-stage rendering, resample, assert_wet guard.

No commercial plugins needed: builtin stages render through pedalboard's
stock effects. Plugin-stage tests are marked slow and skip when absent.
"""

import numpy as np
import pytest
import soundfile as sf

pedalboard = pytest.importorskip("pedalboard")

from toolshop.fx.chain import FXChain, FXStage
from toolshop.fx import engine

SR = 48000


def _tone(sr=SR, seconds=1.0, freq=440.0, level_db=-12.0):
    t = np.arange(int(sr * seconds)) / sr
    x = np.sin(2 * np.pi * freq * t) * (10 ** (level_db / 20))
    return np.stack([x, x], axis=1).astype(np.float32)


def _reg():
    return {"plugins": []}


def test_builtin_chain_renders_and_changes_audio():
    chain = FXChain(name="t", sample_rate=SR, stages=[
        FXStage(builtin="hpf", params={"freq": 300.0}),
        FXStage(builtin="comp",
                params={"threshold_db": -30.0, "ratio": 6.0}),
    ])
    dry = _tone()
    wet = engine.render(chain, _reg(), dry)
    assert wet.shape[0] > dry.shape[0]  # tail appended
    n = len(dry)
    delta = np.max(np.abs(wet[:n] - dry))
    assert 20 * np.log10(delta) > -80  # chain audibly processed


def test_bypass_only_chain_skips_assert_wet():
    chain = FXChain(name="t", sample_rate=SR, stages=[
        FXStage(builtin="hpf", params={"freq": 300.0}, bypass=True),
    ])
    wet = engine.render(chain, _reg(), _tone())
    assert wet.shape[0] > 0  # no DryRenderError


def test_assert_wet_fires_on_noop_chain():
    # ratio 1.0 / threshold 0.0 => compressor mathematically inert
    chain = FXChain(name="t", sample_rate=SR, assert_wet=True, stages=[
        FXStage(builtin="comp", params={"threshold_db": 0.0, "ratio": 1.0}),
    ])
    with pytest.raises(engine.DryRenderError):
        engine.render(chain, _reg(), _tone())


def test_unknown_builtin_param_is_hard_error():
    chain = FXChain(sample_rate=SR, stages=[
        FXStage(builtin="comp", params={"not_a_field": 1.0}),
    ])
    with pytest.raises(Exception, match="bad params"):
        engine.build_board(chain, _reg())


def test_render_file_resamples_44k1(tmp_path):
    inp = tmp_path / "in.wav"
    sf.write(str(inp), _tone(sr=44100), 44100)
    out = tmp_path / "out.wav"
    chain = FXChain(name="t", sample_rate=SR, stages=[
        FXStage(builtin="hpf", params={"freq": 200.0}),
    ])
    result = engine.render_file(chain, _reg(), inp, out)
    assert result["in_sr"] == 44100
    audio, sr = sf.read(str(out))
    assert sr == SR
    assert result["status"] == "completed"


def test_plugin_stage_loads_when_absent_fails_loud():
    chain = FXChain(sample_rate=SR, stages=[
        FXStage(plugin="No Such Plugin 9000"),
    ])
    from toolshop.fx.registry import PluginNotFoundError
    with pytest.raises(PluginNotFoundError):
        engine.build_board(chain, _reg())


@pytest.mark.slow
def test_real_vst3_stage(tmp_path):
    """Render through a real installed VST3 — skip if absent.

    T-De-Esser (Techivation, free) is on this machine; any other plugin from
    the registry works too — pick the first hostable non-shell entry.
    """
    from toolshop.fx import registry as registry_mod
    reg = registry_mod.load()
    candidates = [p for p in reg["plugins"]
                  if p.get("hostable") and not p.get("shell")]
    if not candidates:
        pytest.skip("no hostable plugins in registry (run `toolshop fx scan`)")
    # assert_wet=False: this is a load+render smoke test. A dynamics/de-esser
    # at default settings legitimately renders a sine dry; wetness is guarded
    # per-chain at author time, not here.
    entry = next(
        (p for p in candidates if "T-De-Esser" in p["name"]), candidates[0])
    chain = FXChain(name="t", sample_rate=SR, assert_wet=False, stages=[
        FXStage(plugin=entry["name"], plugin_name=entry.get("plugin_name")),
    ])
    inp = tmp_path / "in.wav"
    sf.write(str(inp), _tone(), SR)
    out = tmp_path / "out.wav"
    result = engine.render_file(chain, reg, inp, out)
    assert out.exists()
    assert result["status"] == "completed"
