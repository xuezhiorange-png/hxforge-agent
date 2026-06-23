"""Top-level service for single-phase convective heat-transfer correlation evaluation.

Provides `evaluate_hx_correlation()` — the main entry point that orchestrates:
1. Geometry validation
2. Flow property validation
3. Regime classification
4. Correlation selection
5. Applicability check
6. Nusselt evaluation
7. Heat-transfer coefficient computation
8. Provenance and hash construction
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from hexagent.core.canonical import sha256_digest
from hexagent.core.heat_balance import ExecutionContextSnapshot
from hexagent.correlations.annulus import ANNULUS_CORRELATIONS
from hexagent.correlations.flow import (
    FlowPropertiesInput,
    FlowRegime,
    classify_regime,
    compute_heat_transfer_coefficient,
    compute_prandtl,
    compute_reynolds,
    compute_velocity,
)
from hexagent.correlations.geometry import (
    CircularTubeGeometry,
    ConcentricAnnulusGeometry,
)
from hexagent.correlations.hx_result import (
    CorrelationResult,
    CorrelationStatus,
    SelectedCorrelationInfo,
    _build_provenance_graph,
    _provenance_graph_digest,
)
from hexagent.correlations.selection import select_correlation
from hexagent.correlations.tube import TUBE_CORRELATIONS
from hexagent.domain.messages import EngineeringMessage, EngineeringMessageSeverity, ErrorCode


def _make_warning(
    code: ErrorCode,
    message: str,
    context: tuple[tuple[str, Any], ...] = (),
) -> EngineeringMessage:
    """Create an EngineeringMessage with WARNING severity."""
    return EngineeringMessage(
        code=code,
        severity=EngineeringMessageSeverity.WARNING,
        message=message,
        source_module="correlations.service",
        context=context,
    )


def _make_blocker(
    code: ErrorCode,
    message: str,
    context: tuple[tuple[str, Any], ...] = (),
) -> EngineeringMessage:
    """Create an EngineeringMessage with BLOCKER severity."""
    return EngineeringMessage(
        code=code,
        severity=EngineeringMessageSeverity.BLOCKER,
        message=message,
        source_module="correlations.service",
        context=context,
    )


class CalculationContext:
    """Mutable context for constructing a correlation evaluation."""

    def __init__(
        self,
        *,
        request_id: UUID | None = None,
        design_case_revision_id: UUID | None = None,
        calculation_run_id: UUID | None = None,
    ) -> None:
        self.request_id = request_id
        self.design_case_revision_id = design_case_revision_id
        self.calculation_run_id = calculation_run_id

    def to_snapshot(self) -> ExecutionContextSnapshot:
        return ExecutionContextSnapshot(
            request_id=self.request_id,
            design_case_revision_id=self.design_case_revision_id,
            calculation_run_id=self.calculation_run_id,
        )


def evaluate_hx_correlation(
    geometry: CircularTubeGeometry | ConcentricAnnulusGeometry,
    flow: FlowPropertiesInput,
    boundary_condition: str = "constant_wall_temperature",
    context: CalculationContext | None = None,
) -> CorrelationResult:
    """Evaluate single-phase convective heat-transfer correlation.

    This is the main entry point for TASK-007.
    """
    warnings: list[EngineeringMessage] = []
    blockers: list[EngineeringMessage] = []
    ctx = (context or CalculationContext()).to_snapshot()

    # --- Step 1: Validate zero mass flow ---
    if flow.mass_flow_kg_s == 0:
        blockers.append(
            _make_blocker(
                ErrorCode.INPUT_INCONSISTENT,
                "Zero mass flow: cannot evaluate convective heat transfer.",
                (("mass_flow_kg_s", 0.0),),
            )
        )
        return _blocked_result(geometry=geometry, flow=flow, blockers=blockers, ctx=ctx)

    # --- Step 2: Validate geometry consistency ---
    if isinstance(geometry, ConcentricAnnulusGeometry) and boundary_condition not in (
        "inner_wall_heated",
        "outer_wall_heated",
        "both_walls_heated",
        "constant_wall_temperature",
        "constant_heat_flux",
    ):
        blockers.append(
            _make_blocker(
                ErrorCode.CORRELATION_GEOMETRY_INCOMPATIBLE,
                f"Unsupported boundary condition for annulus: {boundary_condition!r}",
                (("boundary_condition", boundary_condition),),
            )
        )
        return _blocked_result(geometry=geometry, flow=flow, blockers=blockers, ctx=ctx)

    # --- Step 3: Compute flow quantities ---
    area = geometry.flow_area_m2
    dh = geometry.hydraulic_diameter_m

    velocity = compute_velocity(flow.mass_flow_kg_s, flow.density_kg_m3, area)
    reynolds = compute_reynolds(flow.density_kg_m3, velocity, dh, flow.dynamic_viscosity_pa_s)
    prandtl = compute_prandtl(
        flow.specific_heat_j_kg_k, flow.dynamic_viscosity_pa_s, flow.thermal_conductivity_w_m_k
    )

    # --- Step 4: Classify regime ---
    regime = classify_regime(reynolds)

    if regime == FlowRegime.invalid:
        blockers.append(
            _make_blocker(
                ErrorCode.INPUT_INCONSISTENT,
                f"Invalid Reynolds number: {reynolds!r}",
                (("reynolds_number", reynolds),),
            )
        )
        return _blocked_result(
            geometry=geometry,
            flow=flow,
            blockers=blockers,
            ctx=ctx,
            reynolds=reynolds,
            prandtl=prandtl,
            velocity=velocity,
            area=area,
            dh=dh,
            regime=regime.value,
        )

    if regime == FlowRegime.transitional:
        blockers.append(
            _make_blocker(
                ErrorCode.CORRELATION_FLOW_REGIME_INCOMPATIBLE,
                (
                    f"Transitional flow (2300 ≤ Re = {reynolds:.1f} ≤ 10000) "
                    "is not supported. Specify laminar (Re < 2300) or "
                    "turbulent (Re > 10000)."
                ),
                (
                    ("reynolds_number", reynolds),
                    ("laminar_upper", 2300.0),
                    ("turbulent_lower", 10000.0),
                ),
            )
        )
        return _blocked_result(
            geometry=geometry,
            flow=flow,
            blockers=blockers,
            ctx=ctx,
            reynolds=reynolds,
            prandtl=prandtl,
            velocity=velocity,
            area=area,
            dh=dh,
            regime=regime.value,
        )

    # --- Step 5: Select correlation ---
    has_wall_viscosity = flow.wall_viscosity_pa_s is not None
    candidate = select_correlation(geometry, boundary_condition, regime, has_wall_viscosity)

    if candidate is None:
        blockers.append(
            _make_blocker(
                ErrorCode.CORRELATION_NOT_FOUND,
                f"No applicable correlation for geometry={type(geometry).__name__}, "
                f"bc={boundary_condition!r}, regime={regime.value!r}",
                (
                    ("geometry_type", type(geometry).__name__),
                    ("boundary_condition", boundary_condition),
                    ("flow_regime", regime.value),
                ),
            )
        )
        return _blocked_result(
            geometry=geometry,
            flow=flow,
            blockers=blockers,
            ctx=ctx,
            reynolds=reynolds,
            prandtl=prandtl,
            velocity=velocity,
            area=area,
            dh=dh,
            regime=regime.value,
        )

    # --- Step 6: Add adaptation warning if needed ---
    if candidate.is_adaptation and candidate.adaptation_limitation:
        warnings.append(
            _make_warning(
                ErrorCode.CORRELATION_RECOMMENDED_RANGE_EXCEEDED,
                f"Adaptation limitation: {candidate.adaptation_limitation}",
                (("correlation_id", candidate.correlation_id),),
            )
        )

    # --- Step 7: Evaluate correlation ---
    nu: float = 0.0
    try:
        corr_cls = TUBE_CORRELATIONS.get(candidate.correlation_id) or ANNULUS_CORRELATIONS.get(
            candidate.correlation_id
        )
        if corr_cls is None:
            raise ValueError(f"Correlation {candidate.correlation_id!r} not found in registry")

        corr_instance = corr_cls()

        if (
            candidate.correlation_id == "tube_laminar_cwt"
            or candidate.correlation_id == "tube_laminar_chf"
        ):
            nu = corr_instance.evaluate()
        elif candidate.correlation_id == "tube_turbulent_gnielinski":
            nu = corr_instance.evaluate(reynolds, prandtl)
        elif candidate.correlation_id == "annulus_laminar_inner_chf":
            kappa = (
                geometry.diameter_ratio if isinstance(geometry, ConcentricAnnulusGeometry) else 0.0
            )
            nu = corr_instance.evaluate(kappa)
        elif candidate.correlation_id == "annulus_turbulent_gnielinski_dh":
            nu = corr_instance.evaluate(reynolds, prandtl)
        else:
            blockers.append(
                _make_blocker(
                    ErrorCode.NOT_IMPLEMENTED,
                    f"Correlation {candidate.correlation_id!r} has no evaluator.",
                )
            )
            return _blocked_result(
                geometry=geometry,
                flow=flow,
                blockers=blockers,
                ctx=ctx,
                reynolds=reynolds,
                prandtl=prandtl,
                velocity=velocity,
                area=area,
                dh=dh,
                regime=regime.value,
            )
    except ValueError as exc:
        blockers.append(
            _make_blocker(
                ErrorCode.CORRELATION_ABSOLUTE_RANGE_EXCEEDED,
                str(exc),
                (("correlation_id", candidate.correlation_id),),
            )
        )
        return _blocked_result(
            geometry=geometry,
            flow=flow,
            blockers=blockers,
            ctx=ctx,
            reynolds=reynolds,
            prandtl=prandtl,
            velocity=velocity,
            area=area,
            dh=dh,
            regime=regime.value,
        )

    # --- Step 8: Compute h ---
    h = compute_heat_transfer_coefficient(nu, flow.thermal_conductivity_w_m_k, dh)

    # --- Step 9: Build result ---
    selected_info = SelectedCorrelationInfo(
        correlation_id=candidate.correlation_id,
        version=candidate.version,
        priority=candidate.priority,
        is_adaptation=candidate.is_adaptation,
        adaptation_limitation=candidate.adaptation_limitation,
    )

    # Build provenance
    provenance_graph = _build_provenance_graph(
        geometry=geometry,
        correlation_id=candidate.correlation_id,
        correlation_version=candidate.version,
        reynolds=reynolds,
        prandtl=prandtl,
        nu=nu,
        h=h,
        warnings=tuple(warnings),
        blockers=tuple(blockers),
        execution_context=ctx,
        status=CorrelationStatus.SUCCEEDED,
    )
    provenance_digest = _provenance_graph_digest(provenance_graph)

    # Build result hash
    result = CorrelationResult(
        status=CorrelationStatus.SUCCEEDED,
        geometry=geometry,
        mass_flow_kg_s=flow.mass_flow_kg_s,
        density_kg_m3=flow.density_kg_m3,
        dynamic_viscosity_pa_s=flow.dynamic_viscosity_pa_s,
        thermal_conductivity_w_m_k=flow.thermal_conductivity_w_m_k,
        specific_heat_j_kg_k=flow.specific_heat_j_kg_k,
        bulk_temperature_k=flow.bulk_temperature_k,
        wall_temperature_k=flow.wall_temperature_k,
        wall_viscosity_pa_s=flow.wall_viscosity_pa_s,
        heating=flow.heating,
        flow_area_m2=area,
        mean_velocity_ms=velocity,
        hydraulic_diameter_m=dh,
        reynolds_number=reynolds,
        prandtl_number=prandtl,
        nusselt_number=nu,
        heat_transfer_coefficient=h,
        flow_regime=regime.value,
        selected_correlation=selected_info,
        applicability_status="applicable",
        warnings=tuple(warnings),
        blockers=(),
        failure=None,
        provenance_graph=provenance_graph,
        provenance_digest=provenance_digest,
        execution_context=ctx,
    )

    # Compute result hash (circular: result_hash is part of payload but
    # we compute it with result_hash="" first)
    result_hash = sha256_digest(result._build_result_payload())
    object.__setattr__(result, "result_hash", result_hash)
    # Recompute field hash with the real result_hash
    object.__setattr__(result, "_field_hash", result._compute_field_hash())

    return result


def _blocked_result(
    *,
    geometry: CircularTubeGeometry | ConcentricAnnulusGeometry,
    flow: FlowPropertiesInput,
    blockers: list[EngineeringMessage],
    ctx: ExecutionContextSnapshot,
    reynolds: float = 0.0,
    prandtl: float = 0.0,
    velocity: float = 0.0,
    area: float = 0.0,
    dh: float = 0.0,
    regime: str = "",
) -> CorrelationResult:
    """Build a BLOCKED result with no correlation selected."""
    provenance_graph = _build_provenance_graph(
        geometry=geometry,
        correlation_id="",
        correlation_version="",
        reynolds=reynolds,
        prandtl=prandtl,
        nu=0.0,
        h=0.0,
        warnings=(),
        blockers=tuple(blockers),
        execution_context=ctx,
        status=CorrelationStatus.BLOCKED,
    )
    provenance_digest = _provenance_graph_digest(provenance_graph)

    result = CorrelationResult(
        status=CorrelationStatus.BLOCKED,
        geometry=geometry,
        mass_flow_kg_s=flow.mass_flow_kg_s,
        density_kg_m3=flow.density_kg_m3,
        dynamic_viscosity_pa_s=flow.dynamic_viscosity_pa_s,
        thermal_conductivity_w_m_k=flow.thermal_conductivity_w_m_k,
        specific_heat_j_kg_k=flow.specific_heat_j_kg_k,
        bulk_temperature_k=flow.bulk_temperature_k,
        wall_temperature_k=flow.wall_temperature_k,
        wall_viscosity_pa_s=flow.wall_viscosity_pa_s,
        heating=flow.heating,
        flow_area_m2=area,
        mean_velocity_ms=velocity,
        hydraulic_diameter_m=dh,
        reynolds_number=reynolds,
        prandtl_number=prandtl,
        nusselt_number=0.0,
        heat_transfer_coefficient=0.0,
        flow_regime=regime,
        selected_correlation=None,
        applicability_status="blocked",
        warnings=(),
        blockers=tuple(blockers),
        failure=None,
        provenance_graph=provenance_graph,
        provenance_digest=provenance_digest,
        execution_context=ctx,
    )

    result_hash = sha256_digest(result._build_result_payload())
    object.__setattr__(result, "result_hash", result_hash)
    object.__setattr__(result, "_field_hash", result._compute_field_hash())

    return result
