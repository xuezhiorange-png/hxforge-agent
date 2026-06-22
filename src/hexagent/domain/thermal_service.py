"""Thermal service — domain layer for heat-balance calculations.

Bridges the ``DesignCase`` input model with the ``heat_balance`` core
kernel.  Responsible for:

- Extracting stream states from ``DesignCase``.
- Invoking the heat-balance solver.
- Converting property-provider errors to structured blockers.
- Returning an immutable ``HeatBalanceResult``.

No engineering logic lives here; all calculation is in
``hexagent.core.heat_balance``.
"""

from __future__ import annotations

from typing import Any

from hexagent.core.heat_balance import (
    HeatBalanceInput,
    HeatBalanceResult,
    SolverParams,
    StreamState,
    solve_heat_balance,
)
from hexagent.domain.models import DesignCase
from hexagent.properties.base import FluidIdentifier, PropertyProvider


def _extract_stream_state(
    stream: Any,  # StreamSpec
) -> StreamState:
    """Extract a ``StreamState`` from a ``StreamSpec``."""
    fluid_id = FluidIdentifier.from_fluid_spec(stream.fluid)
    return StreamState(
        fluid_identifier=fluid_id,
        mass_flow_kg_s=stream.mass_flow.si_value,
        inlet_temperature_k=stream.inlet_temperature_k,
        inlet_pressure_pa=stream.inlet_pressure_pa,
        outlet_temperature_k=(
            stream.outlet_temperature.si_value if stream.outlet_temperature is not None else None
        ),
    )


def run_heat_balance(
    case: DesignCase,
    provider: PropertyProvider,
    *,
    solver_params: SolverParams | None = None,
) -> HeatBalanceResult:
    """Run a heat-balance calculation for a design case.

    Parameters
    ----------
    case : DesignCase
        The design case to evaluate.
    provider : PropertyProvider
        Property provider for thermodynamic state evaluation.
    solver_params : SolverParams, optional
        Override default solver parameters.

    Returns
    -------
    HeatBalanceResult
        Immutable result with solved states, diagnostics, and provenance.
    """
    hot_state = _extract_stream_state(case.hot_stream)
    cold_state = _extract_stream_state(case.cold_stream)

    params = solver_params or SolverParams()

    inp = HeatBalanceInput(
        hot=hot_state,
        cold=cold_state,
        known_duty_w=(case.target_duty.si_value if case.target_duty is not None else None),
        solver_params=params,
    )

    return solve_heat_balance(inp, provider)


__all__ = ["run_heat_balance"]
