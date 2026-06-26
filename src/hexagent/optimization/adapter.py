"""
TASK-009 Phase 2 — TASK-008 adapter.

Maps materialized candidates to ``rate_double_pipe()`` calls, forwards
uniform request parameters, and returns raw ``RatingResult`` objects
for verification.
"""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from typing import Any

from hexagent.correlations.flow import ThermalBoundaryCondition
from hexagent.exchangers.double_pipe.geometry import DoublePipeGeometry
from hexagent.exchangers.double_pipe.rating import rate_double_pipe
from hexagent.exchangers.double_pipe.result import RatingResult
from hexagent.exchangers.double_pipe.solver import SolverParams
from hexagent.exchangers.double_pipe.thermal import FlowArrangement
from hexagent.optimization.identities import ManufacturableCandidate
from hexagent.properties.base import FluidIdentifier, PropertyProvider

# ---------------------------------------------------------------------------
# Rating callable type
# ---------------------------------------------------------------------------

RatingCallable = Callable[..., RatingResult]

# ---------------------------------------------------------------------------
# TASK-008 adapter — per-candidate rating call
# ---------------------------------------------------------------------------


def build_candidate_geometry(
    candidate: ManufacturableCandidate,
) -> DoublePipeGeometry:
    """Build a ``DoublePipeGeometry`` from a materialized candidate.

    The effective length is parsed from the canonical string and
    passed as a float.
    """
    length_m = float(Decimal(candidate.effective_length_m_canonical))
    return DoublePipeGeometry(
        inner_tube_inner_diameter_m=candidate.physical_identity.inner_tube_inner_diameter_m,
        inner_tube_outer_diameter_m=candidate.physical_identity.inner_tube_outer_diameter_m,
        outer_pipe_inner_diameter_m=candidate.physical_identity.outer_pipe_inner_diameter_m,
        effective_length_m=length_m,
        wall_thermal_conductivity_w_m_k=candidate.physical_identity.wall_thermal_conductivity_w_m_k,
        inner_surface_roughness_m=candidate.physical_identity.inner_surface_roughness_m,
        annulus_surface_roughness_m=candidate.physical_identity.annulus_surface_roughness_m,
        inner_fouling_resistance_m2k_w=candidate.physical_identity.inner_fouling_resistance_m2k_w,
        outer_fouling_resistance_m2k_w=candidate.physical_identity.outer_fouling_resistance_m2k_w,
    )


def rate_candidate(
    candidate: ManufacturableCandidate,
    *,
    hot_fluid: FluidIdentifier,
    cold_fluid: FluidIdentifier,
    hot_mass_flow_kg_s: float,
    cold_mass_flow_kg_s: float,
    hot_inlet_temperature_k: float,
    cold_inlet_temperature_k: float,
    hot_inlet_pressure_pa: float,
    cold_inlet_pressure_pa: float,
    tube_in_hot: bool,
    flow_arrangement: FlowArrangement,
    provider: PropertyProvider,
    solver_params: SolverParams,
    minimum_terminal_delta_t: float,
    tube_boundary_condition: ThermalBoundaryCondition | str = "adiabatic",
    annulus_boundary_condition: ThermalBoundaryCondition | str = "adiabatic",
    context: Any = None,
    rating_fn: RatingCallable = rate_double_pipe,
) -> RatingResult:
    """Evaluate a single candidate via ``rate_double_pipe()``.

    All flow/fluid/solver parameters are shared across all candidates
    in a sizing run.  Only the geometry (length) varies per candidate.

    Returns an exact ``RatingResult`` (never raises for domain errors).
    """
    geometry = build_candidate_geometry(candidate)

    # Resolve boundary condition strings to enum if needed
    tbc = (
        ThermalBoundaryCondition(tube_boundary_condition)
        if isinstance(tube_boundary_condition, str)
        else tube_boundary_condition
    )
    abc = (
        ThermalBoundaryCondition(annulus_boundary_condition)
        if isinstance(annulus_boundary_condition, str)
        else annulus_boundary_condition
    )

    return rating_fn(
        geometry=geometry,
        hot_fluid=hot_fluid,
        cold_fluid=cold_fluid,
        hot_mass_flow_kg_s=hot_mass_flow_kg_s,
        cold_mass_flow_kg_s=cold_mass_flow_kg_s,
        hot_inlet_temperature_k=hot_inlet_temperature_k,
        cold_inlet_temperature_k=cold_inlet_temperature_k,
        hot_inlet_pressure_pa=hot_inlet_pressure_pa,
        cold_inlet_pressure_pa=cold_inlet_pressure_pa,
        tube_in_hot=tube_in_hot,
        flow_arrangement=flow_arrangement,
        provider=provider,
        solver_params=solver_params,
        context=context,
        minimum_terminal_delta_t=minimum_terminal_delta_t,
        tube_boundary_condition=tbc,
        annulus_boundary_condition=abc,
    )


# ---------------------------------------------------------------------------
# Batch evaluation — process all candidates
# ---------------------------------------------------------------------------


def evaluate_all_candidates(
    candidates: tuple[ManufacturableCandidate, ...],
    *,
    hot_fluid: FluidIdentifier,
    cold_fluid: FluidIdentifier,
    hot_mass_flow_kg_s: float,
    cold_mass_flow_kg_s: float,
    hot_inlet_temperature_k: float,
    cold_inlet_temperature_k: float,
    hot_inlet_pressure_pa: float,
    cold_inlet_pressure_pa: float,
    tube_in_hot: bool,
    flow_arrangement: FlowArrangement,
    provider: PropertyProvider,
    solver_params: SolverParams,
    minimum_terminal_delta_t: float,
    tube_boundary_condition: ThermalBoundaryCondition | str = "adiabatic",
    annulus_boundary_condition: ThermalBoundaryCondition | str = "adiabatic",
    context_builder: Callable[[ManufacturableCandidate], Any] | None = None,
    rating_fn: RatingCallable = rate_double_pipe,
) -> tuple[tuple[ManufacturableCandidate, RatingResult], ...]:
    """Evaluate all candidates with uniform request parameters.

    Returns a tuple of ``(candidate, rating_result)`` pairs preserving
    candidate evaluation order.
    """
    results: list[tuple[ManufacturableCandidate, RatingResult]] = []
    for candidate in candidates:
        ctx = context_builder(candidate) if context_builder else None
        result = rate_candidate(
            candidate,
            hot_fluid=hot_fluid,
            cold_fluid=cold_fluid,
            hot_mass_flow_kg_s=hot_mass_flow_kg_s,
            cold_mass_flow_kg_s=cold_mass_flow_kg_s,
            hot_inlet_temperature_k=hot_inlet_temperature_k,
            cold_inlet_temperature_k=cold_inlet_temperature_k,
            hot_inlet_pressure_pa=hot_inlet_pressure_pa,
            cold_inlet_pressure_pa=cold_inlet_pressure_pa,
            tube_in_hot=tube_in_hot,
            flow_arrangement=flow_arrangement,
            provider=provider,
            solver_params=solver_params,
            minimum_terminal_delta_t=minimum_terminal_delta_t,
            tube_boundary_condition=tube_boundary_condition,
            annulus_boundary_condition=annulus_boundary_condition,
            context=ctx,
            rating_fn=rating_fn,
        )
        results.append((candidate, result))
    return tuple(results)


__all__ = [
    "RatingCallable",
    "build_candidate_geometry",
    "evaluate_all_candidates",
    "rate_candidate",
]
