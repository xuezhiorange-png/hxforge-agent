"""Deterministic correlation selection for single-phase heat transfer.

Selection uses the TASK-004 InMemoryCorrelationRegistry and
assess_applicability() engine. Selection is deterministic: same inputs
always produce the same selected correlation regardless of registry
insertion order.

Returns a SelectionResult dataclass instead of a raw tuple.
Boundary condition compatibility is driven by definition metadata
(tags with "bc:" prefix), NOT by correlation_id string matching.
Priority is extracted from definition tags (priority:N), NOT from
a hardcoded map.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cmp_to_key

from hexagent.correlations.applicability import assess_applicability
from hexagent.correlations.flow import FlowRegime, NusseltBasis, ThermalBoundaryCondition
from hexagent.correlations.geometry import CircularTubeGeometry, ConcentricAnnulusGeometry
from hexagent.correlations.hx_result import SelectedCorrelationInfo
from hexagent.correlations.models import (
    ApplicabilityAssessment,
    ApplicabilityVariable,
    CorrelationApplicabilityInput,
    CorrelationDefinition,
    CorrelationPurpose,
    GeometryType,
    PhaseRegime,
    compare_semver,
)
from hexagent.correlations.registry import InMemoryCorrelationRegistry
from hexagent.domain.messages import EngineeringMessage, EngineeringMessageSeverity, ErrorCode

# ---------------------------------------------------------------------------
# Selection result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SelectionResult:
    """Immutable result of correlation selection.

    Attributes:
        selected_definition: The best matching correlation definition, or None.
        selected_assessment: The applicability assessment for the selected
            (or best rejected) candidate, or None if no candidates.
        rejected_candidates: Tuple of (CorrelationDefinition, ApplicabilityAssessment)
            pairs for candidates that failed applicability.  Preserves full
            context including blockers/warnings.
        unavailable_candidates: Tuple of (CorrelationDefinition, ApplicabilityAssessment)
            pairs for candidates that were applicable but metadata_only.  The
            selected candidate's blockers are in ``blockers``; this tuple
            preserves the full set of unavailable candidates.
        selection_status: One of "selected", "no_match", "ambiguous", "blocked",
            "implementation_unavailable".
        blockers: Tuple of EngineeringMessage explaining why selection failed.
        identified_correlation: SelectedCorrelationInfo if a specific correlation
            was identified but could not be executed (e.g. metadata_only), or None.
    """

    selected_definition: CorrelationDefinition | None
    selected_assessment: ApplicabilityAssessment | None
    rejected_candidates: tuple[tuple[CorrelationDefinition, ApplicabilityAssessment], ...]
    # "selected" | "no_match" | "ambiguous" | "blocked" | "implementation_unavailable"
    selection_status: str
    blockers: tuple[EngineeringMessage, ...]
    unavailable_candidates: tuple[tuple[CorrelationDefinition, ApplicabilityAssessment], ...] = ()
    identified_correlation: SelectedCorrelationInfo | None = None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _extract_priority(definition: CorrelationDefinition) -> int:
    """Extract priority from definition tags (priority:N).  Default is 0."""
    for tag in definition.tags:
        if tag.startswith("priority:"):
            try:
                return int(tag.split(":", 1)[1])
            except (ValueError, IndexError):
                pass
    return 0


def _is_boundary_compatible(
    definition: CorrelationDefinition,
    boundary_condition: ThermalBoundaryCondition | str,
) -> bool:
    """Check if a correlation definition supports the given boundary condition.

    Boundary condition compatibility is driven by definition metadata:
    tags with ``bc:`` prefix (e.g. ``bc:constant_wall_temperature``).
    This replaces the previous correlation_id string-matching approach.
    Accepts both enum and string; converts at boundary.
    """
    if isinstance(boundary_condition, str):
        bc_value = boundary_condition
    else:
        bc_value = boundary_condition.value
    return f"bc:{bc_value}" in definition.tags


def _get_nusselt_basis(definition: CorrelationDefinition) -> str:
    """Get the Nusselt characteristic length basis from the definition's tags."""
    for tag in definition.tags:
        if tag.startswith("nusselt_basis:"):
            return tag.split(":", 1)[1]
    return NusseltBasis.inside_diameter.value


# ---------------------------------------------------------------------------
# Candidate comparison (for deterministic sorting)
# ---------------------------------------------------------------------------


def _compare_candidates(
    a: tuple[CorrelationDefinition, ApplicabilityAssessment],
    b: tuple[CorrelationDefinition, ApplicabilityAssessment],
) -> int:
    """Compare two candidates for selection.

    Sort order (ascending — first element wins):
    1. Priority: higher = preferred  (negated for ascending sort)
    2. Correlation ID: ascending alphabetical
    3. Version: descending SemVer (highest version first, stable > prerelease)

    Returns negative if *a* is preferred over *b*, positive if *b* is preferred,
    0 if they tie on all keys (ambiguous).
    """
    defn_a, _ = a
    defn_b, _ = b

    # 1. Priority: higher = preferred
    prio_a = _extract_priority(defn_a)
    prio_b = _extract_priority(defn_b)
    if prio_a != prio_b:
        return -(prio_a - prio_b)  # higher priority sorts first

    # 2. Correlation ID: ascending alphabetical
    if defn_a.key.correlation_id != defn_b.key.correlation_id:
        return -1 if defn_a.key.correlation_id < defn_b.key.correlation_id else 1

    # 3. Version: descending SemVer (highest first, stable > prerelease)
    semver_cmp = compare_semver(defn_a.key.version, defn_b.key.version)
    if semver_cmp != 0:
        return -semver_cmp  # negate for descending

    # All keys identical — tie (ambiguous)
    return 0


# ---------------------------------------------------------------------------
# Main selection function
# ---------------------------------------------------------------------------


def select_correlation(
    registry: InMemoryCorrelationRegistry,
    geometry: CircularTubeGeometry | ConcentricAnnulusGeometry,
    boundary_condition: ThermalBoundaryCondition | str,
    flow_regime: FlowRegime,
    reynolds: float,
    prandtl: float,
    diameter_ratio: float = 0.0,
    has_wall_viscosity: bool = False,
) -> SelectionResult:
    """Select the best correlation candidate deterministically using the registry.

    Args:
        registry: The correlation registry to search.
        geometry: Flow geometry.
        boundary_condition: Typed boundary condition enum or string (converted at boundary).
        flow_regime: Classified flow regime.
        reynolds: Reynolds number.
        prandtl: Prandtl number.
        diameter_ratio: Diameter ratio kappa (annulus only).
        has_wall_viscosity: Whether wall viscosity is available.

    Returns a :class:`SelectionResult` with the selected definition (or None),
    its applicability assessment, any rejected candidates with full context,
    a status string, and any blocker messages.
    """
    # Convert str → enum at the domain boundary
    if isinstance(boundary_condition, str):
        try:
            bc_enum = ThermalBoundaryCondition(boundary_condition)
        except ValueError:
            return SelectionResult(
                selected_definition=None,
                selected_assessment=None,
                rejected_candidates=(),
                selection_status="blocked",
                blockers=(
                    EngineeringMessage(
                        code=ErrorCode.CORRELATION_GEOMETRY_INCOMPATIBLE,
                        severity=EngineeringMessageSeverity.BLOCKER,
                        message=f"Invalid boundary condition: {boundary_condition!r}",
                        source_module="correlations.selection",
                    ),
                ),
            )
    else:
        bc_enum = boundary_condition

    # Map geometry to GeometryType for the registry
    if isinstance(geometry, CircularTubeGeometry):
        geo_type = GeometryType.circular_tube
    else:
        geo_type = GeometryType.annulus

    # Map flow regime to the models FlowRegime
    if flow_regime == FlowRegime.laminar:
        model_flow_regime = "laminar"
    elif flow_regime == FlowRegime.turbulent:
        model_flow_regime = "turbulent"
    else:
        return SelectionResult(
            selected_definition=None,
            selected_assessment=None,
            rejected_candidates=(),
            selection_status="blocked",
            blockers=(
                EngineeringMessage(
                    code=ErrorCode.CORRELATION_FLOW_REGIME_INCOMPATIBLE,
                    severity=EngineeringMessageSeverity.BLOCKER,
                    message=f"Unsupported flow regime: {flow_regime.value}",
                    source_module="correlations.selection",
                ),
            ),
        )

    from hexagent.correlations.models import FlowRegime as ModelFlowRegime

    model_flow = ModelFlowRegime(model_flow_regime)

    candidates = registry.search(
        purpose=CorrelationPurpose.nusselt_number,
        geometry=geo_type,
        implementation_status=None,  # include all
    )

    if not candidates:
        candidates = registry.search(
            purpose=CorrelationPurpose.heat_transfer_coefficient,
            geometry=geo_type,
            implementation_status=None,
        )

    # Assess all candidates, partitioning into three lists
    passed: list[tuple[CorrelationDefinition, ApplicabilityAssessment]] = []
    rejected: list[tuple[CorrelationDefinition, ApplicabilityAssessment]] = []
    unavailable: list[tuple[CorrelationDefinition, ApplicabilityAssessment]] = []

    for defn in candidates:
        # Check flow regime compatibility
        if model_flow not in defn.envelope.flow_regimes:
            continue

        # Check boundary condition compatibility (tag-driven, enum-based)
        if not _is_boundary_compatible(defn, bc_enum):
            continue

        # Check implementation status: metadata_only → collect into unavailable
        if defn.implementation_status.value == "metadata_only":
            from hexagent.correlations.models import (
                ApplicabilityIdentitySnapshot,
                ApplicabilityStatus,
                OutOfRangePolicy,
                compute_assessment_hash,
            )

            # Build the blocker message
            blocker_msg = EngineeringMessage(
                code=ErrorCode.NOT_IMPLEMENTED,
                severity=EngineeringMessageSeverity.BLOCKER,
                message=(
                    f"Correlation {defn.key.correlation_id} v{defn.key.version} "
                    f"is metadata_only — source data pending verification. "
                    f"implementation_status=metadata_only, "
                    f"source_verification_status={defn.source.verification_status.value}"
                ),
                source_module="correlations.selection",
                context=(
                    ("correlation_id", defn.key.correlation_id),
                    ("version", defn.key.version),
                    ("implementation_status", "metadata_only"),
                    ("source_verification_status", defn.source.verification_status.value),
                    ("definition_hash", defn.definition_hash),
                ),
            )

            # Collect ALL input values including diameter_ratio (P0-3)
            all_input_values = [
                (ApplicabilityVariable.reynolds, reynolds),
                (ApplicabilityVariable.prandtl, prandtl),
            ]
            if ApplicabilityVariable.diameter_ratio in defn.envelope.required_inputs:
                all_input_values.append((ApplicabilityVariable.diameter_ratio, diameter_ratio))

            # Build identity snapshot with ALL inputs
            identity_snapshot = ApplicabilityIdentitySnapshot(
                definition_hash=defn.definition_hash,
                geometry=geo_type,
                phase_regime=PhaseRegime.single_phase_liquid,
                flow_regime=model_flow,
                input_values=tuple(all_input_values),
                policy=OutOfRangePolicy(),
                allow_extrapolation=False,
            )

            # Compute assessment hash before constructing
            assessment_hash = compute_assessment_hash(
                definition_hash=defn.definition_hash,
                correlation_key=defn.key,
                geometry=geo_type,
                phase_regime=PhaseRegime.single_phase_liquid,
                flow_regime=model_flow,
                input_values=tuple(all_input_values),
                status=ApplicabilityStatus.implementation_unavailable,
                variable_results=(),
                warnings=(),
                blockers=(blocker_msg,),
                policy=OutOfRangePolicy(),
                allow_extrapolation=False,
            )

            # Construct the blocked assessment with correct status
            blocked_assessment = ApplicabilityAssessment(
                correlation_key=defn.key,
                status=ApplicabilityStatus.implementation_unavailable,
                variable_results=(),
                warnings=(),
                blockers=(blocker_msg,),
                assessment_hash=assessment_hash,
                identity_snapshot=identity_snapshot,
            )

            # Collect into unavailable list — do NOT return early
            unavailable.append((defn, blocked_assessment))
            continue

        # Build applicability input
        values_list = [
            (ApplicabilityVariable.reynolds, reynolds),
            (ApplicabilityVariable.prandtl, prandtl),
        ]
        # Check if this definition requires diameter_ratio
        if ApplicabilityVariable.diameter_ratio in defn.envelope.required_inputs:
            values_list.append((ApplicabilityVariable.diameter_ratio, diameter_ratio))

        inputs = CorrelationApplicabilityInput(
            geometry=geo_type,
            phase_regime=PhaseRegime.single_phase_liquid,
            flow_regime=model_flow,
            values=tuple(values_list),
        )

        # Assess applicability
        assessment = assess_applicability(defn, inputs)

        if assessment.allows_evaluation:
            passed.append((defn, assessment))
        else:
            rejected.append((defn, assessment))

    # ------------------------------------------------------------------
    # Final decision logic
    # ------------------------------------------------------------------

    # 1. If passed is non-empty: sort with _compare_candidates, select top.
    if passed:
        passed.sort(key=cmp_to_key(_compare_candidates))

        # Ambiguity check
        if len(passed) >= 2 and _compare_candidates(passed[0], passed[1]) == 0:
            return SelectionResult(
                selected_definition=None,
                selected_assessment=None,
                rejected_candidates=tuple(rejected),
                selection_status="ambiguous",
                blockers=(
                    EngineeringMessage(
                        code=ErrorCode.CORRELATION_NOT_FOUND,
                        severity=EngineeringMessageSeverity.BLOCKER,
                        message=(
                            "Ambiguous correlation selection: multiple candidates "
                            "tie on all selection keys (priority, id, version)"
                        ),
                        source_module="correlations.selection",
                    ),
                ),
            )

        selected_defn, selected_assessment = passed[0]
        return SelectionResult(
            selected_definition=selected_defn,
            selected_assessment=selected_assessment,
            rejected_candidates=tuple(rejected),
            selection_status="selected",
            blockers=(),
        )

    # 2. If passed is empty and unavailable is non-empty:
    #    Sort unavailable, select top, return with implementation_unavailable.
    if unavailable:
        unavailable.sort(key=cmp_to_key(_compare_candidates))
        unavail_defn, unavail_assessment = unavailable[0]

        # Ambiguity check among unavailable candidates
        if len(unavailable) >= 2 and _compare_candidates(unavailable[0], unavailable[1]) == 0:
            return SelectionResult(
                selected_definition=None,
                selected_assessment=None,
                rejected_candidates=tuple(rejected),
                selection_status="ambiguous",
                blockers=(
                    EngineeringMessage(
                        code=ErrorCode.CORRELATION_NOT_FOUND,
                        severity=EngineeringMessageSeverity.BLOCKER,
                        message=(
                            "Ambiguous correlation selection: multiple candidates "
                            "tie on all selection keys (priority, id, version)"
                        ),
                        source_module="correlations.selection",
                    ),
                ),
            )

        # Build identified correlation info from the top unavailable candidate
        source = unavail_defn.source
        identified_info = SelectedCorrelationInfo(
            correlation_id=unavail_defn.key.correlation_id,
            version=unavail_defn.key.version,
            priority=_extract_priority(unavail_defn),
            source_title=source.title,
            source_authors=", ".join(source.authors) if source.authors else "",
            source_year=source.year,
            source_reference=(f"{source.edition or ''} {source.equation_or_clause or ''}".strip()),
            source_verification_status=source.verification_status.value,
            definition_hash=unavail_defn.definition_hash,
            is_adaptation=False,
            adaptation_limitation="",
            nusselt_basis=_get_nusselt_basis(unavail_defn),
        )

        return SelectionResult(
            selected_definition=unavail_defn,
            selected_assessment=unavail_assessment,
            rejected_candidates=tuple(rejected),
            selection_status="implementation_unavailable",
            blockers=tuple(unavail_assessment.blockers),
            identified_correlation=identified_info,
            unavailable_candidates=tuple(unavailable),
        )

    # 3. Both passed and unavailable empty: from rejected, return best
    #    failed assessment or CORRELATION_NOT_FOUND.
    best_rejected_defn = None
    best_rejected_assessment = None
    if rejected:
        rejected.sort(key=cmp_to_key(_compare_candidates))
        best_rejected_defn, best_rejected_assessment = rejected[0]

    return SelectionResult(
        selected_definition=best_rejected_defn,
        selected_assessment=best_rejected_assessment,
        rejected_candidates=tuple(rejected),
        selection_status="no_match",
        blockers=(),
    )


__all__ = [
    "SelectionResult",
    "select_correlation",
    "_get_nusselt_basis",
    "_is_boundary_compatible",
]
