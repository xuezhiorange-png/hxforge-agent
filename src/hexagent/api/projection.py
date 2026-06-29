"""TASK-010 Phase 1 — Projection from public API DTOs to domain models.

Each ``project_*`` function maps a frozen, validated public-API DTO
into the corresponding internal domain model.  All Quantity values are
extracted via ``.si_value`` (or ``.value`` for ``ThermalConductivitySpec``).

These functions are pure — no I/O, no property calls, no side effects.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hexagent.api.canonical_request import (
    build_sizing_canonical_request_context,
    compute_api_request_digest,
)
from hexagent.api.models import (
    DoublePipeGeometrySpec,
    FluidStreamSpec,
    ResolvedProviderAuthority,
    SizingApiRequest,
    SolverParamsSpec,
    ValidationApiRequest,
)
from hexagent.api.registry import CatalogRegistry, ProviderRegistry
from hexagent.domain.models import (
    DesignCase,
    DesignConstraints,
    StreamSpec,
)
from hexagent.exchangers.double_pipe.geometry import DoublePipeGeometry
from hexagent.exchangers.double_pipe.solver import SolverParams
from hexagent.optimization.context import (
    SizingRequestIdentity,
    build_sizing_request_identity,
)
from hexagent.optimization.models import (
    CompleteDoublePipeCatalogSnapshot,
    SizingRequest,
)


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
    "ProjectedSizingRequest",
    "project_fluid_stream_to_stream_spec",
    "project_sizing_api_request",
    "project_sizing_to_sizing_request",
    "project_solver_spec_to_solver",
    "project_validation_to_design_case",
    "project_geometry_spec_to_geometry",
]


# ---------------------------------------------------------------------------
# ProjectedSizingRequest — frozen result of full projection
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProjectedSizingRequest:
    """Complete frozen result of SizingApiRequest projection.

    Carries all domain models, identity, and digest produced by
    :func:`project_sizing_api_request`.  This is the authoritative
    projection — all downstream code must use this artifact rather
    than re-projecting the API request.
    """

    design_case: DesignCase
    sizing_request: SizingRequest
    sizing_request_identity: SizingRequestIdentity
    effective_solver_params: SolverParams
    resolved_provider: ResolvedProviderAuthority
    resolved_catalogs: tuple[CompleteDoublePipeCatalogSnapshot, ...]
    canonical_request_snapshot: dict[str, Any]
    request_digest: str


def project_sizing_api_request(
    api_request: SizingApiRequest,
    provider_registry: ProviderRegistry,
    catalog_registry: CatalogRegistry,
) -> ProjectedSizingRequest:
    """Authoritative projection of SizingApiRequest to domain models + identity + digest.

    Steps:
    1. Resolve provider via ProviderRegistry -> ResolvedProviderAuthority
    2. Verify ExpectedProviderIdentity.matches(resolved_provider.identity)
    3. Sort and validate catalog_refs
    4. Resolve each catalog ref via CatalogRegistry
    5. Verify catalog content hash matches
    6. Build effective solver params (None -> SolverParams defaults)
    7. Build design case
    8. Build sizing request
    9. Build sizing request identity
    10. Build canonical request context
    11. Compute request digest
    12. Return frozen ProjectedSizingRequest

    Raises ValueError on:
    - Provider not found
    - Provider identity mismatch
    - Catalog not found
    - Catalog hash mismatch
    - Duplicate catalog refs
    - Same identity key, different content hash
    """
    from hexagent.exchangers.double_pipe.thermal import FlowArrangement

    # Step 1: Resolve provider
    # SizingApiRequest uses expected_provider_identity.name as the provider ref
    # (unlike RatingApiRequest which has an explicit provider_ref field).
    resolved_provider = provider_registry.resolve(
        api_request.expected_provider_identity.name,
    )

    # Step 2: Verify provider identity matches
    if not api_request.expected_provider_identity.matches(resolved_provider.identity):
        raise ValueError(
            f"Provider identity mismatch: expected "
            f"(name={api_request.expected_provider_identity.name!r}, "
            f"version={api_request.expected_provider_identity.version!r}), "
            f"got (name={resolved_provider.identity.name!r}, "
            f"version={resolved_provider.identity.version!r})"
        )

    # Step 3: Sort and validate catalog_refs
    seen_keys: set[tuple[str, str, str, str, str]] = set()
    for ref in api_request.catalog_refs:
        key = (
            ref.catalog_id,
            ref.catalog_version,
            ref.catalog_content_hash,
            ref.source_identity,
            ref.schema_version,
        )
        if key in seen_keys:
            raise ValueError(f"Duplicate catalog ref: {key!r}")
        seen_keys.add(key)

    # Step 4: Resolve each catalog ref via CatalogRegistry
    resolved_catalog_authorities = [
        catalog_registry.resolve(ref) for ref in api_request.catalog_refs
    ]

    # Extract snapshots in the order they were resolved
    resolved_catalogs = tuple(authority.snapshot for authority in resolved_catalog_authorities)

    # Step 5: Verify catalog content hash matches (done by CatalogRegistry.resolve)

    # Step 6: Build effective solver params
    effective_solver_spec = (
        api_request.solver_params if api_request.solver_params is not None else SolverParamsSpec()
    )
    effective_solver_params = project_solver_spec_to_solver(effective_solver_spec)

    # Step 7: Build design case
    design_case = project_validation_to_design_case(api_request.case)

    # Step 8: Build sizing request
    sizing_request = project_sizing_to_sizing_request(api_request, resolved_catalogs)

    # Step 9: Build sizing request identity
    case = api_request.case

    # Extract fluid names
    hot_fluid_name = case.hot_stream.fluid.name
    cold_fluid_name = case.cold_stream.fluid.name
    hot_fluid_eos = case.hot_stream.fluid.backend
    cold_fluid_eos = case.cold_stream.fluid.backend

    # Extract composition (normalized components)
    hot_components: tuple[tuple[str, float], ...] = ()
    if case.hot_stream.fluid.composition is not None:
        hot_components = tuple(sorted(case.hot_stream.fluid.composition.items()))

    cold_components: tuple[tuple[str, float], ...] = ()
    if case.cold_stream.fluid.composition is not None:
        cold_components = tuple(sorted(case.cold_stream.fluid.composition.items()))

    # Extract SI values
    hot_inlet_temp_k = case.hot_stream.inlet.temperature.si_value
    cold_inlet_temp_k = case.cold_stream.inlet.temperature.si_value
    hot_inlet_pressure_pa = case.hot_stream.inlet.pressure.si_value
    cold_inlet_pressure_pa = case.cold_stream.inlet.pressure.si_value
    hot_mass_flow_kg_s = case.hot_stream.mass_flow.si_value
    cold_mass_flow_kg_s = case.cold_stream.mass_flow.si_value

    # Use case.target_duty.si_value for required_duty_w
    required_duty_w = case.target_duty.si_value

    # Use case.minimum_terminal_delta_t.si_value for minimum_terminal_delta_t
    minimum_terminal_delta_t = case.minimum_terminal_delta_t.si_value

    # Parse flow arrangement
    flow_arrangement = FlowArrangement(api_request.flow_arrangement)

    sizing_request_identity = build_sizing_request_identity(
        request=sizing_request,
        hot_fluid_name=hot_fluid_name,
        cold_fluid_name=cold_fluid_name,
        hot_fluid_equation_of_state=hot_fluid_eos,
        cold_fluid_equation_of_state=cold_fluid_eos,
        hot_inlet_temperature_k=hot_inlet_temp_k,
        cold_inlet_temperature_k=cold_inlet_temp_k,
        hot_inlet_pressure_pa=hot_inlet_pressure_pa,
        cold_inlet_pressure_pa=cold_inlet_pressure_pa,
        hot_mass_flow_kg_s=hot_mass_flow_kg_s,
        cold_mass_flow_kg_s=cold_mass_flow_kg_s,
        tube_in_hot=api_request.tube_in_hot,
        flow_arrangement=flow_arrangement,
        tube_boundary_condition=api_request.tube_boundary_condition,
        annulus_boundary_condition=api_request.annulus_boundary_condition,
        minimum_terminal_delta_t=minimum_terminal_delta_t,
        required_duty_w=required_duty_w,
        duty_absolute_tolerance_w=api_request.duty_absolute_tolerance.si_value,
        duty_relative_tolerance=api_request.duty_relative_tolerance.si_value,
        optimization_objective=api_request.optimization_objective,
        top_n=api_request.requested_top_n,
        solver_params=effective_solver_params,
        expected_provider_identity=api_request.expected_provider_identity,
        rating_software_version=api_request.rating_software_version,
        execution_context_policy_version=api_request.execution_context_policy_version,
        hot_fluid_normalized_components=hot_components,
        cold_fluid_normalized_components=cold_components,
        design_case_revision_id=api_request.design_case_revision_id,
        calculation_run_id=api_request.calculation_run_id,
    )

    # Step 10: Build canonical request context
    canonical_request_snapshot = build_sizing_canonical_request_context(
        request=api_request,
        resolved_provider=resolved_provider,
        resolved_catalogs=resolved_catalogs,
    )

    # Step 11: Compute request digest
    request_digest = compute_api_request_digest(canonical_request_snapshot)

    # Step 12: Return frozen ProjectedSizingRequest
    return ProjectedSizingRequest(
        design_case=design_case,
        sizing_request=sizing_request,
        sizing_request_identity=sizing_request_identity,
        effective_solver_params=effective_solver_params,
        resolved_provider=resolved_provider,
        resolved_catalogs=resolved_catalogs,
        canonical_request_snapshot=canonical_request_snapshot,
        request_digest=request_digest,
    )
