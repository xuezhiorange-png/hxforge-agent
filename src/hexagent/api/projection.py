"""TASK-010 Phase 1 — Projection from public API DTOs to domain models.

Each ``project_*`` function maps a frozen, validated public-API DTO
into the corresponding internal domain model.  All Quantity values are
extracted via ``.si_value`` (or ``.value`` for ``ThermalConductivitySpec``).

These functions are pure — no I/O, no property calls, no side effects.
"""

from __future__ import annotations

from hexagent.api.models import (
    DoublePipeGeometrySpec,
    FluidStreamSpec,
    SizingApiRequest,
    SolverParamsSpec,
    ValidationApiRequest,
)
from hexagent.domain.models import (
    DesignCase,
    DesignConstraints,
    StreamSpec,
)
from hexagent.exchangers.double_pipe.geometry import DoublePipeGeometry
from hexagent.exchangers.double_pipe.solver import SolverParams
from hexagent.optimization.models import CompleteDoublePipeCatalogSnapshot, SizingRequest


def project_fluid_stream_to_stream_spec(spec: FluidStreamSpec) -> StreamSpec:
    """Map a ``FluidStreamSpec`` DTO to a domain ``StreamSpec``.

    Field mapping:
      - ``spec.fluid`` → ``fluid``
      - ``spec.inlet`` (``TPStateSpec``) → ``state_spec``
      - ``spec.mass_flow`` → ``mass_flow``
      - ``spec.fouling`` (``FoulingResistanceSpec``) → ``fouling_resistance``
    """
    return StreamSpec(
        fluid=spec.fluid,
        state_spec=spec.inlet,
        mass_flow=spec.mass_flow,
        fouling_resistance=spec.fouling,
    )


def project_validation_to_design_case(req: ValidationApiRequest) -> DesignCase:
    """Map a ``ValidationApiRequest`` DTO to a domain ``DesignCase``.

    Field mapping:
      - ``req.case_name`` → ``name``
      - ``req.hot_stream`` → ``hot_stream`` (via ``project_fluid_stream_to_stream_spec``)
      - ``req.cold_stream`` → ``cold_stream`` (via ``project_fluid_stream_to_stream_spec``)
      - ``req.target_duty`` → ``target_duty``
      - constraint fields → ``constraints: DesignConstraints``
    """
    return DesignCase(
        name=req.case_name,
        hot_stream=project_fluid_stream_to_stream_spec(req.hot_stream),
        cold_stream=project_fluid_stream_to_stream_spec(req.cold_stream),
        target_duty=req.target_duty,
        constraints=DesignConstraints(
            design_pressure_hot=req.design_pressure_hot,
            design_pressure_cold=req.design_pressure_cold,
            design_temperature_hot=req.design_temperature_hot,
            design_temperature_cold=req.design_temperature_cold,
            required_area_margin_fraction=req.required_area_margin_fraction,
        ),
    )


def project_geometry_spec_to_geometry(
    spec: DoublePipeGeometrySpec,
) -> DoublePipeGeometry:
    """Map a ``DoublePipeGeometrySpec`` DTO to a domain ``DoublePipeGeometry``.

    All ``Length`` fields are projected via ``.si_value``.
    ``ThermalConductivitySpec.value`` is used directly (unit is fixed to ``W/(m*K)``).
    """
    return DoublePipeGeometry(
        inner_tube_inner_diameter_m=spec.inner_tube_inner_diameter.si_value,
        inner_tube_outer_diameter_m=spec.inner_tube_outer_diameter.si_value,
        outer_pipe_inner_diameter_m=spec.outer_pipe_inner_diameter.si_value,
        effective_length_m=spec.effective_length.si_value,
        wall_thermal_conductivity_w_m_k=spec.wall_thermal_conductivity.value,
        inner_surface_roughness_m=spec.inner_surface_roughness.si_value,
        annulus_surface_roughness_m=spec.annulus_surface_roughness.si_value,
    )


def project_solver_spec_to_solver(spec: SolverParamsSpec) -> SolverParams:
    """Map a ``SolverParamsSpec`` DTO to a domain ``SolverParams``.

    ``Power`` fields → ``.si_value`` (watts).
    ``TemperatureDifference`` fields → ``.si_value`` (kelvins).
    ``float`` and ``int`` fields pass through directly.
    """
    return SolverParams(
        absolute_residual_w=spec.absolute_residual_w.si_value,
        relative_residual_fraction=spec.relative_residual_fraction,
        bracket_temperature_tolerance_k=spec.bracket_temperature_tolerance_k.si_value,
        max_iterations=spec.max_iterations,
    )


def project_sizing_to_sizing_request(
    api_request: SizingApiRequest,
    resolved_catalogs: tuple[CompleteDoublePipeCatalogSnapshot, ...],
) -> SizingRequest:
    """Build a domain ``SizingRequest`` from a ``SizingApiRequest`` + resolved catalogs.

    The application service resolves ``catalog_refs`` into fully validated
    ``CompleteDoublePipeCatalogSnapshot`` objects **before** calling this
    function.  Length bounds are projected via ``.si_value``.
    """
    return SizingRequest(
        catalogs=resolved_catalogs,
        minimum_effective_length_m=(
            api_request.minimum_effective_length.si_value
            if api_request.minimum_effective_length is not None
            else None
        ),
        maximum_effective_length_m=(
            api_request.maximum_effective_length.si_value
            if api_request.maximum_effective_length is not None
            else None
        ),
        request_raw_combination_cap=api_request.request_raw_combination_cap,
    )


__all__ = [
    "project_fluid_stream_to_stream_spec",
    "project_validation_to_design_case",
    "project_geometry_spec_to_geometry",
    "project_solver_spec_to_solver",
    "project_sizing_to_sizing_request",
]
