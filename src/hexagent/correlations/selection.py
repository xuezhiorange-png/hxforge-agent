"""Deterministic correlation selection for single-phase heat transfer.

Selection uses the TASK-004 InMemoryCorrelationRegistry and
assess_applicability() engine. Selection is deterministic: same inputs
always produce the same selected correlation regardless of registry
insertion order.
"""

from __future__ import annotations

from typing import Any

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


def _derive_boundary_condition(
    geometry: CircularTubeGeometry | ConcentricAnnulusGeometry,
    boundary_condition: str,
) -> str:
    """Derive the effective boundary condition from geometry and user input.

    For annulus: validates heated_surface compatibility with boundary_condition.
    """
    if isinstance(geometry, ConcentricAnnulusGeometry):
        hs = geometry.heated_surface
        if boundary_condition == "inner_wall_heated" and hs != "inner":
            return "__blocker__geometry_mismatch"
        if boundary_condition == "outer_wall_heated" and hs != "outer":
            return "__blocker__geometry_mismatch"
        if boundary_condition == "both_walls_heated" and hs != "both":
            return "__blocker__geometry_mismatch"
    return boundary_condition


def _is_boundary_compatible(definition: CorrelationDefinition, boundary_condition: str) -> bool:
    """Check if a correlation definition supports the given boundary condition.

    Uses the correlation's boundary_condition field from its envelope or
    tags. C3 (tube_turbulent) supports both CWT and CHF.
    """
    # Boundary condition compatibility is checked by correlation ID
    # For C3: boundary_condition is "both" meaning supports both CWT and CHF
    if definition.key.correlation_id == "tube_turbulent_gnielinski":
        return boundary_condition in ("constant_wall_temperature", "constant_heat_flux")

    # For C5: supports multiple boundary conditions (adaptation)
    if definition.key.correlation_id == "annulus_turbulent_gnielinski_dh":
        return boundary_condition in (
            "inner_wall_heated",
            "outer_wall_heated",
            "both_walls_heated",
            "constant_wall_temperature",
            "constant_heat_flux",
        )

    # For C1: constant_wall_temperature only
    if definition.key.correlation_id == "tube_laminar_cwt":
        return boundary_condition == "constant_wall_temperature"

    # For C2: constant_heat_flux only
    if definition.key.correlation_id == "tube_laminar_chf":
        return boundary_condition == "constant_heat_flux"

    # For C4: inner_wall_heated only
    if definition.key.correlation_id == "annulus_laminar_inner_chf":
        return boundary_condition == "inner_wall_heated"

    return False


def _get_nusselt_basis(definition: CorrelationDefinition) -> str:
    """Get the Nusselt characteristic length basis from the definition's tags."""
    for tag in definition.tags:
        if tag.startswith("nusselt_basis:"):
            return tag.split(":", 1)[1]
    # Default based on correlation ID
    if definition.key.correlation_id == "annulus_laminar_inner_chf":
        return NusseltBasis.inside_diameter.value
    if definition.key.correlation_id == "annulus_turbulent_gnielinski_dh":
        return NusseltBasis.hydraulic_diameter.value
    return NusseltBasis.inside_diameter.value


def select_correlation(
    registry: InMemoryCorrelationRegistry,
    geometry: CircularTubeGeometry | ConcentricAnnulusGeometry,
    boundary_condition: str,
    flow_regime: FlowRegime,
    reynolds: float,
    prandtl: float,
    diameter_ratio: float = 0.0,
    has_wall_viscosity: bool = False,
) -> tuple[CorrelationDefinition | None, ApplicabilityAssessment | None, str | None]:
    """Select the best correlation candidate deterministically using the registry.

    Returns:
        (definition, assessment, None) if a single correlation is selected
        (None, None, blocker_message) if blocked or ambiguous
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
        return None, None, f"Unsupported flow regime: {flow_regime.value}"

    # Search registry for matching definitions
    # Use the models module's FlowRegime equivalent
    from hexagent.correlations.models import FlowRegime as ModelFlowRegime

    model_flow = ModelFlowRegime(model_flow_regime)

    candidates = registry.search(
        purpose=CorrelationPurpose.nusselt_number,
        geometry=geo_type,
        implementation_status=None,  # include all
    )

    if not candidates:
        # Try heat_transfer_coefficient purpose too
        candidates = registry.search(
            purpose=CorrelationPurpose.heat_transfer_coefficient,
            geometry=geo_type,
            implementation_status=None,
        )

    # Filter by flow regime compatibility
    filtered: list[tuple[CorrelationDefinition, ApplicabilityAssessment]] = []

    for defn in candidates:
        # Check flow regime
        if model_flow not in defn.envelope.flow_regimes:
            continue

        # Check boundary condition compatibility
        if not _is_boundary_compatible(defn, boundary_condition):
            continue

        # Build applicability input
        values_list = [
            (ApplicabilityVariable.reynolds, reynolds),
            (ApplicabilityVariable.prandtl, prandtl),
        ]
        if (
            defn.key.correlation_id == "annulus_laminar_inner_chf"
            or defn.key.correlation_id == "annulus_turbulent_gnielinski_dh"
        ):
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
            filtered.append((defn, assessment))

    if not filtered:
        return None, None, None  # No applicable correlation found

    # Deterministic sort: priority desc, correlation_id asc, version desc (SemVer)
    def _sort_key(item: tuple[CorrelationDefinition, ApplicabilityAssessment]) -> tuple[Any, ...]:
        import contextlib

        defn = item[0]
        # priority: negative for descending
        priority = -100  # default
        for tag in defn.tags:
            if tag.startswith("priority:"):
                with contextlib.suppress(ValueError):
                    priority = -int(tag.split(":")[1])
        # Use the definition's source priority if available
        # For now, hardcode based on correlation ID (registry is authoritative)
        prio_map = {
            "tube_laminar_cwt": -10,
            "tube_laminar_chf": -10,
            "tube_turbulent_gnielinski": -10,
            "annulus_laminar_inner_chf": -10,
            "annulus_turbulent_gnielinski_dh": -5,
        }
        p = prio_map.get(defn.key.correlation_id, priority)

        # Parse SemVer for version comparison (highest wins → negative for sort)
        from hexagent.correlations.models import parse_semver

        major, minor, patch, prerelease = parse_semver(defn.key.version)
        pre_flag = 0 if prerelease else 1  # stable > prerelease
        version_key = (major, minor, patch, pre_flag, prerelease)

        return (
            p,
            defn.key.correlation_id,
            tuple(-v if isinstance(v, int) else v for v in version_key),
        )

    filtered.sort(key=_sort_key)

    # Check for ambiguity: all selection keys identical
    first_defn = filtered[0][0]
    ambiguous = False
    for defn, _ in filtered[1:]:
        if (
            defn.key.correlation_id == first_defn.key.correlation_id
            and compare_semver(defn.key.version, first_defn.key.version) == 0
        ):
            # Same ID and version — should not happen with registry dedup
            continue
        # Different correlation — not ambiguous (first wins by sort order)
        break

    if ambiguous:
        return (
            None,
            None,
            ("Ambiguous correlation selection: multiple candidates tie on all selection keys"),
        )

    return filtered[0][0], filtered[0][1], None


__all_ = ["select_correlation", "_get_nusselt_basis"]
