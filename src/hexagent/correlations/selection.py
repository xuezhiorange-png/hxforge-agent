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
from hexagent.correlations.flow import FlowRegime, NusseltBasis
from hexagent.correlations.geometry import CircularTubeGeometry, ConcentricAnnulusGeometry
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
        selection_status: One of "selected", "no_match", "ambiguous", "blocked".
        blockers: Tuple of EngineeringMessage explaining why selection failed.
    """

    selected_definition: CorrelationDefinition | None
    selected_assessment: ApplicabilityAssessment | None
    rejected_candidates: tuple[tuple[CorrelationDefinition, ApplicabilityAssessment], ...]
    selection_status: str  # "selected" | "no_match" | "ambiguous" | "blocked"
    blockers: tuple[EngineeringMessage, ...]


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


def _is_boundary_compatible(definition: CorrelationDefinition, boundary_condition: str) -> bool:
    """Check if a correlation definition supports the given boundary condition.

    Boundary condition compatibility is driven by definition metadata:
    tags with ``bc:`` prefix (e.g. ``bc:constant_wall_temperature``).
    This replaces the previous correlation_id string-matching approach.
    """
    return f"bc:{boundary_condition}" in definition.tags


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
    boundary_condition: str,
    flow_regime: FlowRegime,
    reynolds: float,
    prandtl: float,
    diameter_ratio: float = 0.0,
    has_wall_viscosity: bool = False,
) -> SelectionResult:
    """Select the best correlation candidate deterministically using the registry.

    Returns a :class:`SelectionResult` with the selected definition (or None),
    its applicability assessment, any rejected candidates with full context,
    a status string, and any blocker messages.
    """
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

    # Assess all candidates, partitioning into passed/failed
    passed: list[tuple[CorrelationDefinition, ApplicabilityAssessment]] = []
    rejected: list[tuple[CorrelationDefinition, ApplicabilityAssessment]] = []

    for defn in candidates:
        # Check flow regime compatibility
        if model_flow not in defn.envelope.flow_regimes:
            continue

        # Check boundary condition compatibility (tag-driven)
        if not _is_boundary_compatible(defn, boundary_condition):
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

    # No applicable correlation found
    if not passed:
        # Return best rejected candidate's assessment with full context
        best_rejected_defn = None
        best_rejected_assessment = None
        if rejected:
            # Sort rejected candidates the same way to find the "best" one
            rejected.sort(key=cmp_to_key(_compare_candidates))
            best_rejected_defn, best_rejected_assessment = rejected[0]

        return SelectionResult(
            selected_definition=best_rejected_defn,
            selected_assessment=best_rejected_assessment,
            rejected_candidates=tuple(rejected),
            selection_status="no_match",
            blockers=(),
        )

    # Deterministic sort: priority desc, correlation_id asc, version desc
    passed.sort(key=cmp_to_key(_compare_candidates))

    # Check for ambiguity: first two candidates tie on ALL sort keys
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


__all__ = [
    "SelectionResult",
    "select_correlation",
    "_get_nusselt_basis",
    "_is_boundary_compatible",
]
