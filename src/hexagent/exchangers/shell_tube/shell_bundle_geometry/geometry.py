"""Pure Decimal geometry mathematics for TASK-022 Slice A."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, localcontext
from typing import Any

from .canonical import (
    DECIMAL_PRECISION,
    CanonicalizationError,
    decimal_sqrt,
    decimal_string,
    parse_decimal,
)
from .models import BlockerCode, MessageEntry, ShellBundleGeometryRequest


@dataclass(frozen=True)
class GeometryValues:
    shell_inside_diameter: Decimal
    shell_radius: Decimal
    bare_tube_bundle_radius: Decimal
    bare_tube_bundle_diameter: Decimal
    bundle_peripheral_allowance: Decimal
    bundle_outer_envelope_radius: Decimal
    bundle_outer_envelope_diameter: Decimal
    shell_to_bundle_radial_clearance: Decimal
    shell_to_bundle_diametral_clearance: Decimal
    required_minimum_radial_clearance: Decimal
    radial_clearance_margin: Decimal
    limiting_position_ids: tuple[str, ...]


class GeometryFailure(ValueError):
    def __init__(self, stage: int, *blockers: MessageEntry) -> None:
        super().__init__(blockers[0].message_key if blockers else "geometry_failure")
        self.stage = stage
        self.blockers = blockers


def _message(
    code: BlockerCode,
    field_path: str | None,
    message_key: str,
    *,
    evidence_refs: tuple[str, ...] = (),
    details: dict[str, Any] | None = None,
) -> MessageEntry:
    return MessageEntry(
        code=code.value,
        field_path=field_path,
        message_key=message_key,
        evidence_refs=evidence_refs,
        details=details,
    )


def parse_explicit_constraints(
    request: ShellBundleGeometryRequest,
) -> tuple[Decimal, Decimal]:
    blockers: list[MessageEntry] = []
    try:
        allowance = parse_decimal(request.bundle_peripheral_allowance_m, positive=False)
    except CanonicalizationError:
        allowance = Decimal(0)
        blockers.append(
            _message(
                BlockerCode.SBG_BUNDLE_PERIPHERAL_ALLOWANCE_INVALID,
                "bundle_peripheral_allowance_m",
                "bundle_peripheral_allowance_invalid",
                evidence_refs=request.bundle_peripheral_allowance_evidence_refs,
            )
        )
    try:
        minimum = parse_decimal(request.required_minimum_radial_clearance_m, positive=False)
    except CanonicalizationError:
        minimum = Decimal(0)
        blockers.append(
            _message(
                BlockerCode.SBG_REQUIRED_MINIMUM_CLEARANCE_INVALID,
                "required_minimum_radial_clearance_m",
                "required_minimum_radial_clearance_invalid",
                evidence_refs=request.minimum_clearance_evidence_refs,
            )
        )
    try:
        rule_allowance = parse_decimal(
            request.geometry_rule_authority.minimum_bundle_peripheral_allowance_m,
            positive=False,
        )
        rule_minimum = parse_decimal(
            request.geometry_rule_authority.minimum_radial_clearance_m,
            positive=False,
        )
    except CanonicalizationError as exc:  # authority stage should already prevent this
        raise GeometryFailure(
            9,
            _message(
                BlockerCode.SBG_DECIMAL_LEXICAL_INVALID,
                "geometry_rule_authority",
                "verified_rule_minimum_decimal_invalid",
            ),
        ) from exc
    if allowance < rule_allowance:
        blockers.append(
            _message(
                BlockerCode.SBG_BUNDLE_PERIPHERAL_ALLOWANCE_BELOW_RULE_MINIMUM,
                "bundle_peripheral_allowance_m",
                "bundle_peripheral_allowance_below_rule_minimum",
                evidence_refs=request.bundle_peripheral_allowance_evidence_refs,
                details={
                    "actual": decimal_string(allowance),
                    "minimum": decimal_string(rule_allowance),
                },
            )
        )
    if minimum < rule_minimum:
        blockers.append(
            _message(
                BlockerCode.SBG_REQUIRED_MINIMUM_CLEARANCE_BELOW_RULE_MINIMUM,
                "required_minimum_radial_clearance_m",
                "required_minimum_radial_clearance_below_rule_minimum",
                evidence_refs=request.minimum_clearance_evidence_refs,
                details={
                    "actual": decimal_string(minimum),
                    "minimum": decimal_string(rule_minimum),
                },
            )
        )
    if blockers:
        raise GeometryFailure(9, *blockers)
    return allowance, minimum


def compute_bundle_envelope(
    request: ShellBundleGeometryRequest,
    allowance: Decimal,
) -> tuple[Decimal, Decimal, Decimal, Decimal, tuple[str, ...]]:
    try:
        tube_outer_diameter = parse_decimal(
            request.tube_layout.tube_geometry.outer_diameter_m, positive=True
        )
        with localcontext() as ctx:
            ctx.prec = DECIMAL_PRECISION
            tube_radius = tube_outer_diameter / Decimal(2)
            extents: list[tuple[str, Decimal]] = []
            for position in request.tube_layout.positions:
                x_value = parse_decimal(position.x_m)
                y_value = parse_decimal(position.y_m)
                center_radius = decimal_sqrt(x_value * x_value + y_value * y_value)
                extents.append((position.position_id, center_radius + tube_radius))
            if not extents:
                raise CanonicalizationError("layout positions are empty")
            bare_radius = max(item[1] for item in extents)
            limiting = tuple(sorted(item[0] for item in extents if item[1] == bare_radius))
            bare_diameter = bare_radius * Decimal(2)
            outer_radius = bare_radius + allowance
            outer_diameter = outer_radius * Decimal(2)
    except (CanonicalizationError, ArithmeticError) as exc:
        raise GeometryFailure(
            11,
            _message(
                BlockerCode.SBG_BUNDLE_ENVELOPE_CALCULATION_FAILED,
                "tube_layout.positions",
                "bundle_envelope_calculation_failed",
            ),
        ) from exc
    return bare_radius, bare_diameter, outer_radius, outer_diameter, limiting


def compute_clearance(
    *,
    shell_inside_diameter_m: str,
    bundle_outer_envelope_radius: Decimal,
    bundle_outer_envelope_diameter: Decimal,
    required_minimum: Decimal,
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    try:
        shell_inside_diameter = parse_decimal(shell_inside_diameter_m, positive=True)
        with localcontext() as ctx:
            ctx.prec = DECIMAL_PRECISION
            shell_radius = shell_inside_diameter / Decimal(2)
            radial = shell_radius - bundle_outer_envelope_radius
            diametral = shell_inside_diameter - bundle_outer_envelope_diameter
            margin = radial - required_minimum
    except (CanonicalizationError, ArithmeticError) as exc:
        raise GeometryFailure(
            12,
            _message(
                BlockerCode.SBG_SHELL_INSIDE_DIAMETER_INVALID,
                "shell_inside_diameter_m",
                "shell_inside_diameter_invalid",
            ),
        ) from exc
    if shell_inside_diameter <= bundle_outer_envelope_diameter:
        raise GeometryFailure(
            12,
            _message(
                BlockerCode.SBG_SHELL_NOT_LARGER_THAN_BUNDLE,
                "shell_inside_diameter_m",
                "shell_not_larger_than_bundle",
                details={
                    "shell_inside_diameter_m": decimal_string(shell_inside_diameter),
                    "bundle_outer_envelope_diameter_m": decimal_string(
                        bundle_outer_envelope_diameter
                    ),
                },
            ),
        )
    if radial < required_minimum:
        raise GeometryFailure(
            13,
            _message(
                BlockerCode.SBG_RADIAL_CLEARANCE_BELOW_REQUIRED_MINIMUM,
                "required_minimum_radial_clearance_m",
                "radial_clearance_below_required_minimum",
                details={
                    "actual_radial_clearance_m": decimal_string(radial),
                    "required_minimum_radial_clearance_m": decimal_string(required_minimum),
                    "margin_m": decimal_string(margin),
                },
            ),
        )
    return shell_inside_diameter, shell_radius, radial, diametral


__all__ = [
    "GeometryFailure",
    "GeometryValues",
    "compute_bundle_envelope",
    "compute_clearance",
    "parse_explicit_constraints",
]
