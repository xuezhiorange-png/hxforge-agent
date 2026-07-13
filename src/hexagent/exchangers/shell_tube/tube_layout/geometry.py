"""Envelope and exclusion-zone geometry for TASK-021 Slice A."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_EVEN, localcontext

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
            assert zone.radius_m is not None
            radius = parse_decimal(zone.radius_m, positive=True)
            return (candidate.x - center_x) ** 2 + (candidate.y - center_y) ** 2 <= (
                radius + tube_radius + clearance
            ) ** 2
        assert zone.width_m is not None and zone.height_m is not None
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


def evaluate_geometry(
    candidates: tuple[Candidate, ...],
    plan: EnumerationPlan,
    geometry: ApprovedTubeGeometrySnapshot,
    zones: tuple[ExclusionZone, ...],
) -> GeometryResult:
    tube_radius = parse_decimal(geometry.outer_diameter_m, positive=True) / Decimal(2)
    boundary_rejections = 0
    exclusion_rejections = 0
    zone_counts = {zone.zone_id: 0 for zone in zones}
    accepted_raw: list[Candidate] = []
    with localcontext() as ctx:
        ctx.prec = DECIMAL_PRECISION
        ctx.rounding = ROUND_HALF_EVEN
        rho_squared = plan.rho**2
        for candidate in candidates:
            if candidate.x**2 + candidate.y**2 > rho_squared:
                boundary_rejections += 1
                continue
            matched = [
                zone for zone in zones if _matches_zone(candidate, zone, tube_radius)
            ]
            if matched:
                exclusion_rejections += 1
                for zone in matched:
                    zone_counts[zone.zone_id] += 1
                continue
            accepted_raw.append(candidate)
    if not accepted_raw:
        raise _block(
            BlockerCode.STL_NO_TUBE_POSITIONS, "positions", "no_tube_positions"
        )
    quantized: dict[tuple[str, str], tuple[int, int]] = {}
    accepted: list[AcceptedCoordinate] = []
    for candidate in accepted_raw:
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
        accepted.append(
            AcceptedCoordinate(
                u=candidate.u,
                v=candidate.v,
                x=candidate.x,
                y=candidate.y,
                x_m=x_m,
                y_m=y_m,
            )
        )
    accepted.sort(key=lambda item: (item.y, item.x, item.u, item.v))
    audits = tuple(
        ExclusionAudit(
            zone_id=zone.zone_id,
            rejected_position_count=zone_counts[zone.zone_id],
            reason_code=zone.reason_code,
            evidence_refs=zone.evidence_refs,
        )
        for zone in zones
    )
    return GeometryResult(
        accepted=tuple(accepted),
        boundary_rejection_count=boundary_rejections,
        exclusion_rejection_count=exclusion_rejections,
        exclusion_audit=audits,
    )


__all__ = [
    "AcceptedCoordinate",
    "GeometryFailure",
    "GeometryResult",
    "evaluate_geometry",
]
