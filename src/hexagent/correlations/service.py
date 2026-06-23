"""Top-level service for single-phase convective heat-transfer correlation evaluation.

Provides `evaluate_hx_correlation()` — the main entry point that orchestrates:
1. Geometry validation
2. Flow property validation
3. Regime classification
4. Registry-backed correlation selection with applicability assessment
5. Nusselt evaluation
6. Heat-transfer coefficient computation (using correlation-specific D_char)
7. Provenance and hash construction

Uses the TASK-004 InMemoryCorrelationRegistry and assess_applicability()
engine for all correlation lookups and applicability checks.
"""

from __future__ import annotations

import copy
from typing import Any
from uuid import UUID

from hexagent.core.heat_balance import ExecutionContextSnapshot
from hexagent.correlations.annulus import ANNULUS_CORRELATIONS
from hexagent.correlations.flow import (
    FlowPropertiesInput,
    FlowRegime,
    NusseltBasis,
    ThermalBoundaryCondition,
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
from hexagent.correlations.registry import InMemoryCorrelationRegistry
from hexagent.correlations.selection import _get_nusselt_basis, select_correlation
from hexagent.correlations.tube import TUBE_CORRELATIONS
from hexagent.domain.messages import EngineeringMessage, EngineeringMessageSeverity, ErrorCode

# ---------------------------------------------------------------------------
# Boundary condition validation
# ---------------------------------------------------------------------------

_VALID_ANNULUS_BC = frozenset(
    {
        "inner_wall_heated",
        "outer_wall_heated",
        "both_walls_heated",
        "constant_wall_temperature",
        "constant_heat_flux",
    }
)

_VALID_TUBE_BC = frozenset(
    {
        "constant_wall_temperature",
        "constant_heat_flux",
    }
)


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


# ---------------------------------------------------------------------------
# Registry singleton (created once, frozen — deep copy on access)
# ---------------------------------------------------------------------------


def _build_default_registry() -> InMemoryCorrelationRegistry:
    """Build and populate the default correlation registry.

    This is the single source of truth for correlation definitions.
    Each definition includes:
    - CorrelationKey (ID + SemVer)
    - Authoritative source identity
    - Definition hash
    - Applicability envelope with numeric bounds
    - Tags for boundary condition and Nusselt basis
    """
    from hexagent.correlations.annulus import (
        _KAPPA_ABSOLUTE_MAX,
        _KAPPA_ABSOLUTE_MIN,
    )
    from hexagent.correlations.models import (
        ApplicabilityEnvelope,
        ApplicabilityVariable,
        BibliographicSource,
        CorrelationDefinition,
        CorrelationImplementationStatus,
        CorrelationKey,
        CorrelationPurpose,
        GeometryType,
        NumericBound,
        OutOfRangeAction,
        OutOfRangePolicy,
        PhaseRegime,
        SourceVerificationStatus,
        UncertaintySpec,
    )
    from hexagent.correlations.models import (
        FlowRegime as ModelsFlowRegime,
    )

    registry = InMemoryCorrelationRegistry()

    def _register(defn: CorrelationDefinition) -> None:
        registry.register(defn)

    # C1: Tube laminar CWT
    _register(
        CorrelationDefinition.create(
            key=CorrelationKey(correlation_id="tube_laminar_cwt", version="1.0.0"),
            name="Tube Laminar CWT",
            purpose=CorrelationPurpose.nusselt_number,
            description="Fully developed laminar flow, constant wall temperature. Nu_D = 3.66.",
            geometry=frozenset({GeometryType.circular_tube}),
            phase_regimes=frozenset(
                {PhaseRegime.single_phase_liquid, PhaseRegime.single_phase_gas}
            ),
            envelope=ApplicabilityEnvelope(
                geometry_types=frozenset({GeometryType.circular_tube}),
                phase_regimes=frozenset(
                    {PhaseRegime.single_phase_liquid, PhaseRegime.single_phase_gas}
                ),
                flow_regimes=frozenset({ModelsFlowRegime.laminar}),
                bounds=(
                    NumericBound(
                        variable=ApplicabilityVariable.reynolds,
                        minimum=0.0,
                        maximum=2300.0,
                        minimum_inclusive=False,
                        maximum_inclusive=False,
                    ),
                    NumericBound(
                        variable=ApplicabilityVariable.prandtl,
                        minimum=0.6,
                        minimum_inclusive=False,
                    ),
                ),
                required_inputs=frozenset(
                    {ApplicabilityVariable.reynolds, ApplicabilityVariable.prandtl}
                ),
            ),
            source=BibliographicSource(
                source_id="incropera_2011_table_8_1",
                authors=("Incropera, F.P.", "DeWitt, D.P.", "Bergman, T.L.", "Lavine, A.S."),
                title="Fundamentals of Heat and Mass Transfer",
                publication="Wiley",
                year=2011,
                edition="7th",
                equation_or_clause="Table 8.1",
                verification_status=SourceVerificationStatus.primary_source_checked,
            ),
            uncertainty=UncertaintySpec(
                basis="exact analytical solution for fully developed laminar flow",
            ),
            implementation_status=CorrelationImplementationStatus.validated,
            implementation_ref="hexagent.correlations.tube.TubeLaminarCWT",
            tags=frozenset(
                {
                    "bc:constant_wall_temperature",
                    "nusselt_basis:inside_diameter",
                    "priority:10",
                }
            ),
        )
    )

    # C2: Tube laminar CHF
    _register(
        CorrelationDefinition.create(
            key=CorrelationKey(correlation_id="tube_laminar_chf", version="1.0.0"),
            name="Tube Laminar CHF",
            purpose=CorrelationPurpose.nusselt_number,
            description="Fully developed laminar flow, constant heat flux. Nu_D = 4.36.",
            geometry=frozenset({GeometryType.circular_tube}),
            phase_regimes=frozenset(
                {PhaseRegime.single_phase_liquid, PhaseRegime.single_phase_gas}
            ),
            envelope=ApplicabilityEnvelope(
                geometry_types=frozenset({GeometryType.circular_tube}),
                phase_regimes=frozenset(
                    {PhaseRegime.single_phase_liquid, PhaseRegime.single_phase_gas}
                ),
                flow_regimes=frozenset({ModelsFlowRegime.laminar}),
                bounds=(
                    NumericBound(
                        variable=ApplicabilityVariable.reynolds,
                        minimum=0.0,
                        maximum=2300.0,
                        minimum_inclusive=False,
                        maximum_inclusive=False,
                    ),
                    NumericBound(
                        variable=ApplicabilityVariable.prandtl,
                        minimum=0.6,
                        minimum_inclusive=False,
                    ),
                ),
                required_inputs=frozenset(
                    {ApplicabilityVariable.reynolds, ApplicabilityVariable.prandtl}
                ),
            ),
            source=BibliographicSource(
                source_id="incropera_2011_table_8_1",
                authors=("Incropera, F.P.", "DeWitt, D.P.", "Bergman, T.L.", "Lavine, A.S."),
                title="Fundamentals of Heat and Mass Transfer",
                publication="Wiley",
                year=2011,
                edition="7th",
                equation_or_clause="Table 8.1",
                verification_status=SourceVerificationStatus.primary_source_checked,
            ),
            uncertainty=UncertaintySpec(
                basis="exact analytical solution for fully developed laminar flow",
            ),
            implementation_status=CorrelationImplementationStatus.validated,
            implementation_ref="hexagent.correlations.tube.TubeLaminarCHF",
            tags=frozenset(
                {
                    "bc:constant_heat_flux",
                    "nusselt_basis:inside_diameter",
                    "priority:10",
                }
            ),
        )
    )

    # C3: Tube turbulent Gnielinski
    _register(
        CorrelationDefinition.create(
            key=CorrelationKey(correlation_id="tube_turbulent_gnielinski", version="1.0.0"),
            name="Tube Turbulent Gnielinski",
            purpose=CorrelationPurpose.nusselt_number,
            description=(
                "Gnielinski correlation for turbulent pipe flow. "
                "Nu_D = (f/8)(Re-1000)Pr / [1+12.7(f/8)^0.5(Pr^(2/3)-1)]"
            ),
            geometry=frozenset({GeometryType.circular_tube}),
            phase_regimes=frozenset(
                {PhaseRegime.single_phase_liquid, PhaseRegime.single_phase_gas}
            ),
            envelope=ApplicabilityEnvelope(
                geometry_types=frozenset({GeometryType.circular_tube}),
                phase_regimes=frozenset(
                    {PhaseRegime.single_phase_liquid, PhaseRegime.single_phase_gas}
                ),
                flow_regimes=frozenset({ModelsFlowRegime.turbulent}),
                bounds=(
                    NumericBound(
                        variable=ApplicabilityVariable.reynolds,
                        minimum=3000.0,
                        maximum=5e6,
                    ),
                    NumericBound(
                        variable=ApplicabilityVariable.prandtl,
                        minimum=0.5,
                        maximum=2000.0,
                    ),
                ),
                required_inputs=frozenset(
                    {ApplicabilityVariable.reynolds, ApplicabilityVariable.prandtl}
                ),
            ),
            source=BibliographicSource(
                source_id="gnielinski_1976",
                authors=("Gnielinski, V.",),
                title="New Equations for Heat and Mass Transfer in Turbulent Pipe and Channel Flow",
                publication="International Chemical Engineering",
                year=1976,
                volume="Vol. 16, No. 2",
                pages="pp. 359-368",
                equation_or_clause="Eq. 1",
                verification_status=SourceVerificationStatus.primary_source_checked,
            ),
            uncertainty=UncertaintySpec(
                basis="experimental correlation, ±10% for Re > 3000, 0.5 < Pr < 2000",
            ),
            implementation_status=CorrelationImplementationStatus.validated,
            implementation_ref="hexagent.correlations.tube.TubeTurbulentGnielinski",
            tags=frozenset(
                {
                    "bc:constant_wall_temperature",
                    "bc:constant_heat_flux",
                    "nusselt_basis:inside_diameter",
                    "priority:10",
                }
            ),
        )
    )

    # C4: Annulus laminar inner CHF
    # STATUS: metadata_only — source data pending verification
    _register(
        CorrelationDefinition.create(
            key=CorrelationKey(correlation_id="annulus_laminar_inner_chf", version="1.0.0"),
            name="Annulus Laminar Inner CHF",
            purpose=CorrelationPurpose.nusselt_number,
            description=(
                "Laminar Nu_i for inner wall heated, outer insulated. "
                "Interpolated from Kays & Crawford Table 9-1. "
                "DATA PENDING SOURCE VERIFICATION."
            ),
            geometry=frozenset({GeometryType.annulus}),
            phase_regimes=frozenset(
                {PhaseRegime.single_phase_liquid, PhaseRegime.single_phase_gas}
            ),
            envelope=ApplicabilityEnvelope(
                geometry_types=frozenset({GeometryType.annulus}),
                phase_regimes=frozenset(
                    {PhaseRegime.single_phase_liquid, PhaseRegime.single_phase_gas}
                ),
                flow_regimes=frozenset({ModelsFlowRegime.laminar}),
                bounds=(
                    NumericBound(
                        variable=ApplicabilityVariable.reynolds,
                        minimum=0.0,
                        maximum=2300.0,
                        minimum_inclusive=False,
                        maximum_inclusive=False,
                    ),
                    NumericBound(
                        variable=ApplicabilityVariable.prandtl,
                        minimum=0.6,
                        minimum_inclusive=False,
                    ),
                    NumericBound(
                        variable=ApplicabilityVariable.diameter_ratio,
                        minimum=_KAPPA_ABSOLUTE_MIN,
                        maximum=_KAPPA_ABSOLUTE_MAX,
                        minimum_inclusive=True,
                        maximum_inclusive=True,
                        tolerance_fraction=1e-6,
                    ),
                ),
                required_inputs=frozenset(
                    {
                        ApplicabilityVariable.reynolds,
                        ApplicabilityVariable.prandtl,
                        ApplicabilityVariable.diameter_ratio,
                    }
                ),
            ),
            source=BibliographicSource(
                source_id="kays_crawford_1993_table_9_1",
                authors=("Kays, W.M.", "Crawford, M.E."),
                title="Convective Heat and Mass Transfer",
                publication="McGraw-Hill",
                year=1993,
                edition="3rd",
                equation_or_clause="Chapter 9, Table 9-1 (pending verification)",
                verification_status=SourceVerificationStatus.unverified,
            ),
            uncertainty=UncertaintySpec(
                basis="interpolated from tabulated exact solutions (pending verification)",
            ),
            implementation_status=CorrelationImplementationStatus.metadata_only,
            tags=frozenset(
                {
                    "bc:inner_wall_heated",
                    "nusselt_basis:hydraulic_diameter",
                    "priority:10",
                }
            ),
        )
    )

    # C5: Annulus turbulent Gnielinski DH adaptation
    # STATUS: implemented (not validated) — source verification pending
    _register(
        CorrelationDefinition.create(
            key=CorrelationKey(correlation_id="annulus_turbulent_gnielinski_dh", version="1.0.0"),
            name="Annulus Turbulent Gnielinski DH",
            purpose=CorrelationPurpose.nusselt_number,
            description=(
                "Hydraulic-diameter adaptation of Gnielinski for annulus turbulent flow. "
                "ADAPTATION — not an original annulus correlation."
            ),
            geometry=frozenset({GeometryType.annulus}),
            phase_regimes=frozenset(
                {PhaseRegime.single_phase_liquid, PhaseRegime.single_phase_gas}
            ),
            envelope=ApplicabilityEnvelope(
                geometry_types=frozenset({GeometryType.annulus}),
                phase_regimes=frozenset(
                    {PhaseRegime.single_phase_liquid, PhaseRegime.single_phase_gas}
                ),
                flow_regimes=frozenset({ModelsFlowRegime.turbulent}),
                bounds=(
                    NumericBound(
                        variable=ApplicabilityVariable.reynolds,
                        minimum=3000.0,
                        maximum=5e6,
                    ),
                    NumericBound(
                        variable=ApplicabilityVariable.prandtl,
                        minimum=0.5,
                        maximum=2000.0,
                    ),
                    NumericBound(
                        variable=ApplicabilityVariable.diameter_ratio,
                        minimum=0.0,
                        maximum=1.0,
                        minimum_inclusive=False,
                        maximum_inclusive=False,
                    ),
                ),
                required_inputs=frozenset(
                    {
                        ApplicabilityVariable.reynolds,
                        ApplicabilityVariable.prandtl,
                        ApplicabilityVariable.diameter_ratio,
                    }
                ),
            ),
            source=BibliographicSource(
                source_id="kays_crawford_1993_ch10",
                authors=("Kays, W.M.", "Crawford, M.E."),
                title="Convective Heat and Mass Transfer",
                publication="McGraw-Hill",
                year=1993,
                edition="3rd",
                equation_or_clause="Ch. 10 (hydraulic diameter approximation)",
                verification_status=SourceVerificationStatus.unverified,
            ),
            uncertainty=UncertaintySpec(
                basis="hydraulic-diameter approximation, may underpredict for asymmetric heating",
            ),
            out_of_range_policy=OutOfRangePolicy(
                absolute_violation=OutOfRangeAction.block,
                recommended_violation=OutOfRangeAction.warn,
            ),
            implementation_status=CorrelationImplementationStatus.implemented,
            implementation_ref="hexagent.correlations.annulus.AnnulusTurbulentGnielinskiDH",
            tags=frozenset(
                {
                    "bc:inner_wall_heated",
                    "bc:outer_wall_heated",
                    "bc:both_walls_heated",
                    "bc:constant_wall_temperature",
                    "bc:constant_heat_flux",
                    "nusselt_basis:hydraulic_diameter",
                    "priority:5",
                }
            ),
        )
    )

    return registry


# Default registry singleton (frozen — deep copy on access)
_DEFAULT_REGISTRY: InMemoryCorrelationRegistry | None = None


def _get_registry() -> InMemoryCorrelationRegistry:
    """Get a deep copy of the default registry singleton.

    The canonical registry is built once and frozen.  Each call returns a
    fresh deep copy so that external mutations (register, etc.) have no
    effect on subsequent evaluations.
    """
    global _DEFAULT_REGISTRY
    if _DEFAULT_REGISTRY is None:
        _DEFAULT_REGISTRY = _build_default_registry()
    return copy.deepcopy(_DEFAULT_REGISTRY)


# ---------------------------------------------------------------------------
# Calculation context
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Main evaluation entry point
# ---------------------------------------------------------------------------


def evaluate_hx_correlation(
    geometry: CircularTubeGeometry | ConcentricAnnulusGeometry,
    flow: FlowPropertiesInput,
    boundary_condition: str = "constant_wall_temperature",
    context: CalculationContext | None = None,
) -> CorrelationResult:
    """Evaluate single-phase convective heat-transfer correlation.

    This is the main entry point for TASK-007.
    Uses the TASK-004 registry and applicability engine.
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

    if flow.mass_flow_kg_s < 0:
        blockers.append(
            _make_blocker(
                ErrorCode.INPUT_INCONSISTENT,
                f"Negative mass flow: {flow.mass_flow_kg_s}.",
                (("mass_flow_kg_s", flow.mass_flow_kg_s),),
            )
        )
        return _blocked_result(geometry=geometry, flow=flow, blockers=blockers, ctx=ctx)

    # --- Step 2: Convert and validate boundary condition ---
    try:
        bc_enum = ThermalBoundaryCondition(boundary_condition)
    except ValueError:
        blockers.append(
            _make_blocker(
                ErrorCode.CORRELATION_GEOMETRY_INCOMPATIBLE,
                f"Invalid boundary condition: {boundary_condition!r}",
                (("boundary_condition", boundary_condition),),
            )
        )
        return _blocked_result(geometry=geometry, flow=flow, blockers=blockers, ctx=ctx)

    # Validate boundary condition vs geometry
    if isinstance(geometry, ConcentricAnnulusGeometry):
        if bc_enum.value not in _VALID_ANNULUS_BC:
            blockers.append(
                _make_blocker(
                    ErrorCode.CORRELATION_GEOMETRY_INCOMPATIBLE,
                    f"Unsupported boundary condition for annulus: {boundary_condition!r}",
                    (("boundary_condition", boundary_condition),),
                )
            )
            return _blocked_result(geometry=geometry, flow=flow, blockers=blockers, ctx=ctx)

        # Validate heated_surface / boundary_condition consistency
        hs = geometry.heated_surface
        if bc_enum == ThermalBoundaryCondition.inner_wall_heated and hs != "inner":
            blockers.append(
                _make_blocker(
                    ErrorCode.CORRELATION_GEOMETRY_INCOMPATIBLE,
                    f"Boundary condition 'inner_wall_heated' requires heated_surface='inner', "
                    f"got '{hs}'",
                    (("heated_surface", hs), ("boundary_condition", boundary_condition)),
                )
            )
            return _blocked_result(geometry=geometry, flow=flow, blockers=blockers, ctx=ctx)
        if bc_enum == ThermalBoundaryCondition.outer_wall_heated and hs != "outer":
            blockers.append(
                _make_blocker(
                    ErrorCode.CORRELATION_GEOMETRY_INCOMPATIBLE,
                    f"Boundary condition 'outer_wall_heated' requires heated_surface='outer', "
                    f"got '{hs}'",
                    (("heated_surface", hs), ("boundary_condition", boundary_condition)),
                )
            )
            return _blocked_result(geometry=geometry, flow=flow, blockers=blockers, ctx=ctx)
        if bc_enum == ThermalBoundaryCondition.both_walls_heated and hs != "both":
            blockers.append(
                _make_blocker(
                    ErrorCode.CORRELATION_GEOMETRY_INCOMPATIBLE,
                    f"Boundary condition 'both_walls_heated' requires heated_surface='both', "
                    f"got '{hs}'",
                    (("heated_surface", hs), ("boundary_condition", boundary_condition)),
                )
            )
            return _blocked_result(geometry=geometry, flow=flow, blockers=blockers, ctx=ctx)
    else:
        if bc_enum.value not in _VALID_TUBE_BC:
            blockers.append(
                _make_blocker(
                    ErrorCode.CORRELATION_GEOMETRY_INCOMPATIBLE,
                    f"Unsupported boundary condition for tube: {boundary_condition!r}",
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

    # --- Step 5: Select correlation via registry ---
    registry = _get_registry()
    diameter_ratio = (
        geometry.diameter_ratio if isinstance(geometry, ConcentricAnnulusGeometry) else 0.0
    )

    selection_result = select_correlation(
        registry=registry,
        geometry=geometry,
        boundary_condition=bc_enum.value,
        flow_regime=regime,
        reynolds=reynolds,
        prandtl=prandtl,
        diameter_ratio=diameter_ratio,
    )

    # Handle selection blockers (ambiguous, unsupported regime, etc.)
    if selection_result.selection_status in ("ambiguous", "blocked"):
        blockers.extend(selection_result.blockers)
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
            assessment=selection_result.selected_assessment,
        )

    # Handle no_match: all candidates rejected by applicability
    if selection_result.selection_status == "no_match":
        # Use best rejected candidate's assessment and blockers
        if selection_result.selected_assessment is not None:
            blockers.extend(selection_result.selected_assessment.blockers)
        if not blockers:
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
            assessment=selection_result.selected_assessment,
        )

    definition = selection_result.selected_definition
    assessment = selection_result.selected_assessment

    # definition is guaranteed non-None here because selection_status == "selected"
    assert definition is not None, "Selection returned 'selected' status but definition is None"

    # --- Step 6: Add adaptation warning if needed ---
    corr_id = definition.key.correlation_id
    adaptation_limitation = ""
    if corr_id == "annulus_turbulent_gnielinski_dh":
        adaptation_limitation = (
            "Hydraulic-diameter approximation may underpredict heat transfer "
            "for highly asymmetric heating in annuli with large diameter ratios. "
            "Consult Kays & Crawford for corrections."
        )
        warnings.append(
            _make_warning(
                ErrorCode.CORRELATION_RECOMMENDED_RANGE_EXCEEDED,
                f"Adaptation limitation: {adaptation_limitation}",
                (("correlation_id", corr_id),),
            )
        )

    # --- Step 7: Evaluate correlation ---
    nu: float = 0.0
    corr_cls = TUBE_CORRELATIONS.get(corr_id) or ANNULUS_CORRELATIONS.get(corr_id)
    if corr_cls is None:
        blockers.append(
            _make_blocker(
                ErrorCode.NOT_IMPLEMENTED,
                f"Correlation {corr_id!r} has no evaluator.",
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
            assessment=assessment,
        )

    try:
        corr_instance = corr_cls()
        if corr_id in ("tube_laminar_cwt", "tube_laminar_chf"):
            nu = corr_instance.evaluate()
        elif corr_id == "tube_turbulent_gnielinski":
            nu = corr_instance.evaluate(reynolds, prandtl)
        elif corr_id == "annulus_laminar_inner_chf":
            nu = corr_instance.evaluate(diameter_ratio)
        elif corr_id == "annulus_turbulent_gnielinski_dh":
            nu = corr_instance.evaluate(reynolds, prandtl)
        else:
            blockers.append(
                _make_blocker(
                    ErrorCode.NOT_IMPLEMENTED,
                    f"Correlation {corr_id!r} has no evaluator.",
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
                assessment=assessment,
            )
    except NotImplementedError as exc:
        # C4 blocked at evaluation time — data pending source verification
        blockers.append(
            _make_blocker(
                ErrorCode.NOT_IMPLEMENTED,
                str(exc),
                (("correlation_id", corr_id),),
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
            assessment=assessment,
        )
    except ValueError as exc:
        blockers.append(
            _make_blocker(
                ErrorCode.CORRELATION_ABSOLUTE_RANGE_EXCEEDED,
                str(exc),
                (("correlation_id", corr_id),),
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

    # --- Step 8: Compute h using correlation-specific D_char ---
    nusselt_basis = _get_nusselt_basis(definition)
    if nusselt_basis == NusseltBasis.inside_diameter.value:
        if isinstance(geometry, ConcentricAnnulusGeometry):
            d_char = geometry.inner_tube_outer_diameter_m
        else:
            d_char = geometry.inside_diameter_m
    else:
        d_char = dh

    h = compute_heat_transfer_coefficient(nu, flow.thermal_conductivity_w_m_k, d_char)

    # --- Step 9: Build SelectedCorrelationInfo from definition ---
    source = definition.source
    selected_info = SelectedCorrelationInfo(
        correlation_id=corr_id,
        version=definition.key.version,
        priority=_extract_priority(definition),
        source_title=source.title,
        source_authors=", ".join(source.authors) if source.authors else "",
        source_year=source.year,
        source_reference=(f"{source.edition or ''} {source.equation_or_clause or ''}".strip()),
        source_verification_status=source.verification_status.value,
        definition_hash=definition.definition_hash,
        is_adaptation=corr_id == "annulus_turbulent_gnielinski_dh",
        adaptation_limitation=adaptation_limitation,
        nusselt_basis=nusselt_basis,
    )

    # --- Step 10: Build provenance ---
    assessment_hash = assessment.assessment_hash if assessment else ""
    provenance_graph = _build_provenance_graph(
        geometry=geometry,
        correlation_id=corr_id,
        correlation_version=definition.key.version,
        definition_hash=definition.definition_hash,
        source_title=source.title,
        source_authors=", ".join(source.authors) if source.authors else "",
        source_year=source.year,
        nusselt_basis=nusselt_basis,
        assessment_hash=assessment_hash,
        reynolds=reynolds,
        prandtl=prandtl,
        nu=nu,
        h=h,
        warnings=tuple(warnings),
        blockers=(),
        execution_context=ctx,
        status=CorrelationStatus.SUCCEEDED,
    )
    provenance_digest = _provenance_graph_digest(provenance_graph)

    # --- Step 11: Build result with hash (no self-reference) ---
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
        applicability_assessment=assessment,
        applicability_status=assessment.status.value if assessment else "applicable",
        warnings=tuple(warnings),
        blockers=(),
        failure=None,
        provenance_graph=provenance_graph,
        provenance_digest=provenance_digest,
        execution_context=ctx,
    )

    # Compute result hash (no self-reference — payload excludes result_hash)
    result_hash = result._compute_result_hash()
    object.__setattr__(result, "result_hash", result_hash)
    # Recompute field hash with the real result_hash
    object.__setattr__(result, "_field_hash", result._compute_field_hash())

    return result


def _extract_priority(definition: Any) -> int:
    """Extract priority from definition tags."""
    for tag in definition.tags:
        if tag.startswith("priority:"):
            try:
                return int(tag.split(":", 1)[1])
            except (ValueError, IndexError):
                pass
    return 0


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
    assessment: Any = None,
) -> CorrelationResult:
    """Build a BLOCKED result with no correlation selected."""
    assessment_hash = ""
    if assessment is not None and hasattr(assessment, "assessment_hash"):
        assessment_hash = assessment.assessment_hash

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
        assessment_hash=assessment_hash,
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
        applicability_assessment=assessment,
        applicability_status="blocked",
        warnings=(),
        blockers=tuple(blockers),
        failure=None,
        provenance_graph=provenance_graph,
        provenance_digest=provenance_digest,
        execution_context=ctx,
    )

    result_hash = result._compute_result_hash()
    object.__setattr__(result, "result_hash", result_hash)
    object.__setattr__(result, "_field_hash", result._compute_field_hash())

    return result
