"""Regression tests for chain_dsl parameters the executors silently dropped.

`mastering_tool/tools/chain_dsl/schema.py` declares three parameters that
`executors/pedalboard_exec.py::build_pedalboard` never read:
    - HPF.slope (default 12)
    - Compressor.knee_db (default 4.0)
    - Limiter.lookahead_ms (default 20.0)

Checked against the installed pedalboard 0.9.24 API directly (its
HighpassFilter/Compressor/Limiter classes expose no slope, knee_db, or
lookahead_ms control at all -- confirmed via dir()/docstrings, since
inspect.signature() cannot introspect pedalboard's pybind11 builtins), none
of the three can be honoured by pedalboard. So each must be refused loudly
(raise) when set away from its schema default, rather than silently ignored.

This file lives in the parent repo's tests/ (not
mastering_tool/tools/chain_dsl/test_chain_dsl.py) because pytest.ini's
`testpaths = tests` does not collect inside the mastering_tool submodule --
the submodule's own test_chain_dsl.py never runs under the parent suite.
"""

from __future__ import annotations

import numpy as np
import pytest

from mastering_tool.tools.chain_dsl.schema import Chain, Compressor, HPF, Limiter
from mastering_tool.tools.chain_dsl.executors import masterbus_exec, pedalboard_exec


SR = 48000


def _white_noise(seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.standard_normal((SR, 2)).astype(np.float32)


# ---------------------------------------------------------------------------
# pedalboard_exec: all three parameters are unsupported by installed
# pedalboard -> must refuse loudly when non-default, must stay silent at
# default.
# ---------------------------------------------------------------------------


class TestPedalboardExecHpfSlope:
    def test_nondefault_slope_raises_and_names_parameter(self) -> None:
        chain = Chain(hpf=HPF(freq=100.0, slope=24, bypass=False))
        with pytest.raises(Exception, match=r"(?i)HPF\.slope"):
            pedalboard_exec.build_pedalboard(chain)

    def test_default_slope_does_not_raise(self) -> None:
        chain = Chain(hpf=HPF(freq=100.0, slope=12, bypass=False))
        pedalboard_exec.build_pedalboard(chain)  # must not raise

    def test_nondefault_slope_while_bypassed_does_not_raise(self) -> None:
        # The stage is not applied, so the unused value cannot corrupt the
        # render; only an *active* stage's unsupported param must refuse.
        chain = Chain(hpf=HPF(freq=100.0, slope=24, bypass=True))
        pedalboard_exec.build_pedalboard(chain)  # must not raise


class TestPedalboardExecCompressorKnee:
    def test_nondefault_knee_db_raises_and_names_parameter(self) -> None:
        chain = Chain(comp=Compressor(threshold_db=-18.0, knee_db=8.0, bypass=False))
        with pytest.raises(Exception, match=r"(?i)Compressor\.knee_db|knee_db"):
            pedalboard_exec.build_pedalboard(chain)

    def test_default_knee_db_does_not_raise(self) -> None:
        chain = Chain(comp=Compressor(threshold_db=-18.0, knee_db=4.0, bypass=False))
        pedalboard_exec.build_pedalboard(chain)  # must not raise


class TestPedalboardExecLimiterLookahead:
    def test_nondefault_lookahead_ms_raises_and_names_parameter(self) -> None:
        chain = Chain(limit=Limiter(ceiling_db=-1.0, lookahead_ms=5.0, bypass=False))
        with pytest.raises(Exception, match=r"(?i)Limiter\.lookahead_ms|lookahead_ms"):
            pedalboard_exec.build_pedalboard(chain)

    def test_default_lookahead_ms_does_not_raise(self) -> None:
        chain = Chain(limit=Limiter(ceiling_db=-1.0, lookahead_ms=20.0, bypass=False))
        pedalboard_exec.build_pedalboard(chain)  # must not raise

    def test_render_still_works_at_default(self) -> None:
        chain = Chain(limit=Limiter(ceiling_db=-1.0, lookahead_ms=20.0, bypass=False))
        x = _white_noise()
        y = pedalboard_exec.render(chain, x)
        assert y.shape == x.shape


# ---------------------------------------------------------------------------
# masterbus_exec: same shape gap for HPF.slope / Compressor.knee_db (not
# present in the Rust MasterBusConfig struct either). Limiter.lookahead_ms IS
# genuinely wired through to open_DAW/daw-engine/src/master_bus.rs, so it is
# NOT expected to raise here.
# ---------------------------------------------------------------------------


class TestMasterbusExecHpfSlope:
    def test_nondefault_slope_raises(self) -> None:
        chain = Chain(hpf=HPF(freq=100.0, slope=24, bypass=False))
        with pytest.raises(Exception, match=r"(?i)HPF\.slope"):
            masterbus_exec.to_masterbus_config(chain)

    def test_default_slope_does_not_raise(self) -> None:
        chain = Chain(hpf=HPF(freq=100.0, slope=12, bypass=False))
        masterbus_exec.to_masterbus_config(chain)  # must not raise


class TestMasterbusExecCompressorKnee:
    def test_nondefault_knee_db_raises(self) -> None:
        chain = Chain(comp=Compressor(threshold_db=-18.0, knee_db=8.0, bypass=False))
        with pytest.raises(Exception, match=r"(?i)knee_db"):
            masterbus_exec.to_masterbus_config(chain)

    def test_default_knee_db_does_not_raise(self) -> None:
        chain = Chain(comp=Compressor(threshold_db=-18.0, knee_db=4.0, bypass=False))
        masterbus_exec.to_masterbus_config(chain)  # must not raise


class TestMasterbusExecLimiterLookaheadIsWired:
    def test_nondefault_lookahead_ms_does_not_raise(self) -> None:
        # Unlike pedalboard, the Rust master bus genuinely consumes
        # limit_lookahead_ms (Limiter::new/reconfigure) -- this path is
        # already correctly wired, so a non-default value must be accepted.
        chain = Chain(limit=Limiter(ceiling_db=-1.0, lookahead_ms=5.0, bypass=False))
        masterbus_exec.to_masterbus_config(chain)  # must not raise

    def test_lookahead_ms_value_reaches_the_output_dict(self) -> None:
        chain = Chain(limit=Limiter(ceiling_db=-1.0, lookahead_ms=5.0, bypass=False))
        config = masterbus_exec.to_masterbus_config(chain)
        assert config["limit_lookahead_ms"] == 5.0

        default_chain = Chain(limit=Limiter(ceiling_db=-1.0, lookahead_ms=20.0, bypass=False))
        default_config = masterbus_exec.to_masterbus_config(default_chain)
        assert default_config["limit_lookahead_ms"] == 20.0
        assert config["limit_lookahead_ms"] != default_config["limit_lookahead_ms"]
