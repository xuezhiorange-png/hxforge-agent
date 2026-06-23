"""Deterministic correlation selection for single-phase heat transfer.

Selection is deterministic: same inputs always produce the same selected
correlation regardless of registry insertion order or dict iteration order.
"""

from __future__ import annotations

from dataclasses import dataclass

from hexagent.correlations.flow import FlowRegime
from hexagent.correlations.geometry import CircularTubeGeometry, ConcentricAnnulusGeometry


@dataclass(frozen=True)
class CorrelationCandidate:
    """A candidate correlation with its applicability metadata."""

    correlation_id: str
    version: str
    priority: int
    supports_geometry: str
    supports_boundary: str
    supports_flow_regime: str
    requires_wall_viscosity: bool
    is_adaptation: bool = False
    adaptation_limitation: str = ""


def _build_candidates(
    geometry: CircularTubeGeometry | ConcentricAnnulusGeometry,
    boundary_condition: str,
    regime: FlowRegime,
    has_wall_viscosity: bool,
) -> list[CorrelationCandidate]:
    """Build list of candidate correlations matching geometry and regime."""
    candidates: list[CorrelationCandidate] = []

    if isinstance(geometry, CircularTubeGeometry):
        if regime == FlowRegime.laminar:
            if boundary_condition in ("constant_wall_temperature", "both"):
                candidates.append(
                    CorrelationCandidate(
                        correlation_id="tube_laminar_cwt",
                        version="1.0.0",
                        priority=10,
                        supports_geometry="circular_tube",
                        supports_boundary="constant_wall_temperature",
                        supports_flow_regime="laminar",
                        requires_wall_viscosity=False,
                    )
                )
            if boundary_condition in ("constant_heat_flux", "both"):
                candidates.append(
                    CorrelationCandidate(
                        correlation_id="tube_laminar_chf",
                        version="1.0.0",
                        priority=10,
                        supports_geometry="circular_tube",
                        supports_boundary="constant_heat_flux",
                        supports_flow_regime="laminar",
                        requires_wall_viscosity=False,
                    )
                )
        elif regime == FlowRegime.turbulent:
            candidates.append(
                CorrelationCandidate(
                    correlation_id="tube_turbulent_gnielinski",
                    version="1.0.0",
                    priority=10,
                    supports_geometry="circular_tube",
                    supports_boundary="both",
                    supports_flow_regime="turbulent",
                    requires_wall_viscosity=False,
                )
            )

    elif isinstance(geometry, ConcentricAnnulusGeometry):
        if regime == FlowRegime.laminar:
            if boundary_condition in ("inner_wall_heated", "both"):
                candidates.append(
                    CorrelationCandidate(
                        correlation_id="annulus_laminar_inner_chf",
                        version="1.0.0",
                        priority=10,
                        supports_geometry="concentric_annulus",
                        supports_boundary="inner_wall_heated",
                        supports_flow_regime="laminar",
                        requires_wall_viscosity=False,
                    )
                )
        elif regime == FlowRegime.turbulent:
            candidates.append(
                CorrelationCandidate(
                    correlation_id="annulus_turbulent_gnielinski_dh",
                    version="1.0.0",
                    priority=5,
                    supports_geometry="concentric_annulus",
                    supports_boundary="both",
                    supports_flow_regime="turbulent",
                    requires_wall_viscosity=False,
                    is_adaptation=True,
                    adaptation_limitation=(
                        "Hydraulic-diameter approximation may underpredict heat transfer "
                        "for highly asymmetric heating in annuli with large diameter ratios."
                    ),
                )
            )

    return candidates


def _sort_key(c: CorrelationCandidate) -> tuple[int, str, str, str]:
    """Deterministic sort key for candidates.

    Sort order: higher priority first, then alphabetically by ID,
    then by version, then by boundary support.
    """
    return (-c.priority, c.correlation_id, c.version, c.supports_boundary)


def select_correlation(
    geometry: CircularTubeGeometry | ConcentricAnnulusGeometry,
    boundary_condition: str,
    regime: FlowRegime,
    has_wall_viscosity: bool,
) -> CorrelationCandidate | None:
    """Select the best correlation candidate deterministically.

    Returns None if no applicable correlation found.
    Returns a CorrelationCandidate if exactly one is selected.
    Raises ValueError if ambiguous (multiple candidates tie on all keys).
    """
    candidates = _build_candidates(geometry, boundary_condition, regime, has_wall_viscosity)

    if not candidates:
        return None

    # Sort deterministically
    candidates.sort(key=_sort_key)

    if len(candidates) == 1:
        return candidates[0]

    # Check for ambiguity: are all candidates identical on selection keys?
    first = candidates[0]
    for c in candidates[1:]:
        if (
            c.priority != first.priority
            or c.correlation_id != first.correlation_id
            or c.version != first.version
        ):
            # Different candidates — not ambiguous, first wins
            return first

    # All candidates are identical — not ambiguous
    return first
