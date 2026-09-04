"""Differential round-trip recovery for the mastering_tool Plugin Chain DSL.

Given a dry signal and the same signal rendered through a *known* `Chain`
(`mastering_tool.tools.chain_dsl.schema.Chain`), this package asks: how much
of the chain's parameters can be recovered from the (dry, wet) pair alone?

This is the differential case (both signals known) -- the floor for the
harder blind-extraction problem (wet signal only). See `roundtrip.py` for
the recovery methods and `ORCHESTRATION/wave_vc1/agent_d1_handoff.md` for
the measured recovery table.
"""

from .roundtrip import (
    Recovery,
    extract_differential,
    render_known,
)

__all__ = ["Recovery", "extract_differential", "render_known"]
