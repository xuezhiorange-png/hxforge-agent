"""Stage 13 / 14 / 15 geometry primitives for TASK-021 Slice A.

The three stages are separated by §9:

- Stage 13 — ``enumeration_envelope_filter``: pure envelope filtering of the
  candidate lattice. No exclusion-zone work.

- Stage 14 — ``multi_zone_exclusion_evaluation``: complete multi-zone
  exclusion evaluation with full per-zone audit accumulation. Returns the
  accepted candidate list after exclusion filtering, or raises
  ``GeometryFailure(STL_NO_TUBE_POSITIONS)`` when no candidate survives.

- Stage 15 — ``coordinate_quantization_collision_guard``: quantize accepted
  candidates and detect two distinct (u,v) lattice indices that quantize to
  the same canonical (x_m, y_m) string. Returns the canonical accepted
  coordinates with §8.10 ordering.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal, localcontext

from .canonical import DECIMAL_PRECISION, parse_decimal, quantized_decimal_string
from .enumeration import Candidate, EnumerationPlan
from .models import (
    ApprovedTubeGeometrySnapshot,
    BlockerCode,
    ExclusionAudit,
    ExclusionZone,
    ExclusionZoneType,
    MessageEntry,
)


class GeometryFailure(ValueError):
    def __init__(self, blocker: MessageEntry) -> None:
        super().__init__(blocker.message_key)
        self.blocker = blocker


@dataclass(frozen=True)
class AcceptedCoordinate:
    u: int
    v: int
    x: Decimal
    y: Decimal
    x_m: str
    y_m: str


@dataclass(frozen=True)
class GeometryResult:
    accepted: tuple[AcceptedCoordinate, ...]
    boundary_rejection_count: int
    exclusion_rejection_count: int
    exclusion_audit: tuple[ExclusionAudit, ...]


def _block(code: BlockerCode, field_path: str, message_key: str) -> GeometryFailure:
    return GeometryFailure(
        MessageEntry(code=code.value, field_path=field_path, message_key=message_key)
    )


def _matches_zone(
    candidate: Candidate,
    zone: ExclusionZone,
    tube_radius: Decimal,
) -> bool:
    center_x = parse_decimal(zone.center_x_m)
    center_y = parse_decimal(zone.center_y_m)
    clearance = parse_decimal(zone.clearance_m, positive=False)
    with localcontext() as ctx:
        ctx.prec = DECIMAL_PRECISION
        ctx.rounding = ROUND_HALF_EVEN
        if zone.zone_type is ExclusionZoneType.CIRCLE:
            if zone.radius_m is None:
                return False
            radius = parse_decimal(zone.radius_m, positive=True)
            return (candidate.x - center_x) ** 2 + (candidate.y - center_y) ** 2 <= (
                radius + tube_radius + clearance
            ) ** 2
        if zone.width_m is None or zone.height_m is None:
            return False
        half_width = parse_decimal(zone.width_m, positive=True) / Decimal(2)
        half_height = parse_decimal(zone.height_m, positive=True) / Decimal(2)
        min_x = center_x - half_width
        max_x = center_x + half_width
        min_y = center_y - half_height
        max_y = center_y + half_height
        closest_x = min(max(candidate.x, min_x), max_x)
        closest_y = min(max(candidate.y, min_y), max_y)
        return (candidate.x - closest_x) ** 2 + (candidate.y - closest_y) ** 2 <= (
            tube_radius + clearance
        ) ** 2


def enumeration_envelope_filter(
    candidates: tuple[Candidate, ...],
    plan: EnumerationPlan,
) -> tuple[tuple[Candidate, ...], int]:
    """Stage 13 — apply ``rho`` boundary; return (inside, boundary_rejection_count)."""

    inside: list[Candidate] = []
    boundary_rejection_count = 0
    with localcontext() as ctx:
        ctx.prec = DECIMAL_PRECISION
        ctx.rounding = ROUND_HALF_EVEN
        rho_squared = plan.rho**2
        for candidate in candidates:
            if candidate.x**2 + candidate.y**2 > rho_squared:
                boundary_rejection_count += 1
                continue
            inside.append(candidate)
    return tuple(inside), boundary_rejection_count


def multi_zone_exclusion_evaluation(
    inside: tuple[Candidate, ...],
    geometry: ApprovedTubeGeometrySnapshot,
    zones: tuple[ExclusionZone, ...],
) -> tuple[tuple[Candidate, ...], int, tuple[ExclusionAudit, ...]]:
    """Stage 14 — exclusion filtering + audit. ``STL_NO_TUBE_POSITIONS`` if empty."""

    tube_radius = parse_decimal(geometry.outer_diameter_m, positive=True) / Decimal(2)
    accepted: list[Candidate] = []
    exclusion_rejection_count = 0
    zone_counts = {zone.zone_id: 0 for zone in zones}
    for candidate in inside:
        matched = [zone for zone in zones if _matches_zone(candidate, zone, tube_radius)]
        if matched:
            exclusion_rejection_count += 1
            for zone in matched:
                zone_counts[zone.zone_id] += 1
            continue
        accepted.append(candidate)
    sorted_zones = tuple(sorted(zones, key=lambda zone: zone.zone_id))
    audit = tuple(
        ExclusionAudit(
            zone_id=zone.zone_id,
            rejected_position_count=zone_counts[zone.zone_id],
            reason_code=zone.reason_code,
            evidence_refs=zone.evidence_refs,
        )
        for zone in sorted_zones
    )
    if not accepted:
        raise _block(BlockerCode.STL_NO_TUBE_POSITIONS, "positions", "no_tube_positions")
    return tuple(accepted), exclusion_rejection_count, audit


def coordinate_quantization_collision_guard(
    accepted: tuple[Candidate, ...],
) -> tuple[AcceptedCoordinate, ...]:
    """Stage 15 — quantize and detect two distinct lattice indices colliding."""

    quantized: dict[tuple[str, str], tuple[int, int]] = {}
    accepted_records: list[AcceptedCoordinate] = []
    for candidate in accepted:
        x_m = quantized_decimal_string(candidate.x)
        y_m = quantized_decimal_string(candidate.y)
        key = (x_m, y_m)
        previous = quantized.get(key)
        if previous is not None and previous != (candidate.u, candidate.v):
            raise _block(
                BlockerCode.STL_COORDINATE_QUANTIZATION_COLLISION,
                "positions",
                "coordinate_quantization_collision",
            )
        quantized[key] = (candidate.u, candidate.v)
        accepted_records.append(
            AcceptedCoordinate(
                u=candidate.u,
                v=candidate.v,
                x=candidate.x,
                y=candidate.y,
                x_m=x_m,
                y_m=y_m,
            )
        )
    accepted_records.sort(key=lambda item: (item.y, item.x, item.u, item.v))
    return tuple(accepted_records)


def evaluate_geometry(
    candidates: tuple[Candidate, ...],
    plan: EnumerationPlan,
    geometry: ApprovedTubeGeometrySnapshot,
    zones: tuple[ExclusionZone, ...],
) -> GeometryResult:
    """Legacy runner that packs stages 13/14/15. New callers MUST run them separately."""

    inside, boundary_rejection_count = enumeration_envelope_filter(candidates, plan)
    accepted, exclusion_rejection_count, audit = multi_zone_exclusion_evaluation(
        inside, geometry, zones
    )
    accepted_records = coordinate_quantization_collision_guard(accepted)
    return GeometryResult(
        accepted=accepted_records,
        boundary_rejection_count=boundary_rejection_count,
        exclusion_rejection_count=exclusion_rejection_count,
        exclusion_audit=audit,
    )


__all__ = [
    "AcceptedCoordinate",
    "GeometryFailure",
    "GeometryResult",
    "coordinate_quantization_collision_guard",
    "enumeration_envelope_filter",
    "evaluate_geometry",
    "multi_zone_exclusion_evaluation",
]
