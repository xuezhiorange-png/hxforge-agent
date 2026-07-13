"""Stage 8 / Stage 12 enumeration primitives for TASK-021 Slice A.

Stage 8 = ``verify_envelope_shape_and_radius``: only the placement-envelope
shape and the effective radius derived from `diameter - outer_diameter -
edge_clearance` are validated. If `rho <= 0`, the result blocks with
``STL_ENVELOPE_INVALID``. ALL Stage-12 work (basis determinant, inverse basis,
bounds, candidate capacity) is intentionally deferred.

Stage 12 = ``verify_inverse_basis_and_candidate_capacity``: takes the verified
``EnumeratedBasisInputs`` from Stage 8 and constructs the inverse basis,
bounds, and candidate count. Blocker codes emitted:

- ``STL_BASIS_NON_INVERTIBLE`` on zero determinant.
- ``STL_ENUMERATION_LIMIT_EXCEEDED`` when the candidate count exceeds the
  rule's frozen capacity.

The two are deliberately separate; round-3 §3 (P0-1) requires stages to fail
in order without leaking work between them.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_HALF_EVEN, Decimal, localcontext

from .canonical import DECIMAL_PRECISION, SQRT_3, parse_decimal
from .models import (
    ApprovedTubeGeometrySnapshot,
    AxisOrientation,
    BlockerCode,
    CircularTubeCenterEnvelope,
    LayoutRuleAuthoritySnapshot,
    MessageEntry,
    OriginMode,
    PatternFamily,
)


class EnumerationFailure(ValueError):
    def __init__(self, blocker: MessageEntry) -> None:
        super().__init__(blocker.message_key)
        self.blocker = blocker


@dataclass(frozen=True)
class Candidate:
    u: int
    v: int
    x: Decimal
    y: Decimal


@dataclass(frozen=True)
class EnumeratedBasisInputs:
    """Frozen Stage 8 output: envelope/radius only, no basis work yet."""

    a_x: Decimal
    a_y: Decimal
    b_x: Decimal
    b_y: Decimal
    offset_x: Decimal
    offset_y: Decimal
    rho: Decimal
    pattern_family: PatternFamily
    origin_mode: OriginMode
    axis_orientation: AxisOrientation


@dataclass(frozen=True)
class EnumerationPlan:
    a_x: Decimal
    a_y: Decimal
    b_x: Decimal
    b_y: Decimal
    offset_x: Decimal
    offset_y: Decimal
    rho: Decimal
    u_bound: int
    v_bound: int
    candidate_count: int


def _block(code: BlockerCode, field_path: str, message_key: str) -> EnumerationFailure:
    return EnumerationFailure(
        MessageEntry(code=code.value, field_path=field_path, message_key=message_key)
    )


def _basis_vectors(
    rule: LayoutRuleAuthoritySnapshot,
    axis_orientation: AxisOrientation,
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    """Return (a_x, a_y, b_x, b_y) for the given pattern_family and orientation.

    Pure stage-8 derivation: the basis vectors themselves do not require
    invertibility or bounds. Invertibility and candidate capacity are deferred
    to stage 12.
    """

    p = parse_decimal(rule.pitch_m, positive=True)
    if rule.pattern_family is PatternFamily.SQUARE:
        a_x, a_y = p, Decimal(0)
        b_x, b_y = Decimal(0), p
    else:
        a_x, a_y = p, Decimal(0)
        b_x, b_y = p / Decimal(2), p * SQRT_3 / Decimal(2)
    if axis_orientation is AxisOrientation.PRIMARY_AXIS_Y:
        a_x, a_y = a_y, a_x
        b_x, b_y = b_y, b_x
    return a_x, a_y, b_x, b_y


def verify_envelope_shape_and_radius(
    rule: LayoutRuleAuthoritySnapshot,
    geometry: ApprovedTubeGeometrySnapshot,
    envelope: CircularTubeCenterEnvelope,
    origin_mode: OriginMode,
    axis_orientation: AxisOrientation,
) -> EnumeratedBasisInputs:
    """Stage 8 — envelope shape + positive effective radius only.

    No basis determinant, no inverse basis, no bounds, no candidate count.
    Those are deferred to Stage 12.
    """

    with localcontext() as ctx:
        ctx.prec = DECIMAL_PRECISION
        ctx.rounding = ROUND_HALF_EVEN
        outer = parse_decimal(geometry.outer_diameter_m, positive=True)
        diameter = parse_decimal(envelope.tube_center_envelope_diameter_m, positive=True)
        edge_clearance = parse_decimal(rule.edge_clearance_m, positive=False)
        a_x, a_y, b_x, b_y = _basis_vectors(rule, axis_orientation)
        if origin_mode is OriginMode.CENTER_ON_LATTICE_POINT:
            offset_x = Decimal(0)
            offset_y = Decimal(0)
        else:
            offset_x = (a_x + b_x) / Decimal(2)
            offset_y = (a_y + b_y) / Decimal(2)
        rho = diameter / Decimal(2) - outer / Decimal(2) - edge_clearance
    if rho <= 0:
        raise _block(
            BlockerCode.STL_ENVELOPE_INVALID,
            "placement_envelope",
            "effective_radius_nonpositive",
        )
    return EnumeratedBasisInputs(
        a_x=a_x,
        a_y=a_y,
        b_x=b_x,
        b_y=b_y,
        offset_x=offset_x,
        offset_y=offset_y,
        rho=rho,
        pattern_family=rule.pattern_family,
        origin_mode=origin_mode,
        axis_orientation=axis_orientation,
    )


def verify_inverse_basis_and_candidate_capacity(
    rule: LayoutRuleAuthoritySnapshot,
    basis: EnumeratedBasisInputs,
) -> EnumerationPlan:
    """Stage 12 — inverse basis, bounds, candidate capacity."""

    with localcontext() as ctx:
        ctx.prec = DECIMAL_PRECISION
        ctx.rounding = ROUND_HALF_EVEN
        a_x, a_y = basis.a_x, basis.a_y
        b_x, b_y = basis.b_x, basis.b_y
        det = a_x * b_y - a_y * b_x
        if det == 0:
            raise _block(
                BlockerCode.STL_BASIS_NON_INVERTIBLE,
                "layout_rule_authority.pattern_family",
                "basis_non_invertible",
            )
        b00 = b_y / det
        b01 = -b_x / det
        b10 = -a_y / det
        b11 = a_x / det
        d_x = basis.rho + abs(basis.offset_x)
        d_y = basis.rho + abs(basis.offset_y)
        u_bound_decimal = abs(b00) * d_x + abs(b01) * d_y
        v_bound_decimal = abs(b10) * d_x + abs(b11) * d_y
        u_bound = int(u_bound_decimal.to_integral_value(rounding=ROUND_CEILING)) + 1
        v_bound = int(v_bound_decimal.to_integral_value(rounding=ROUND_CEILING)) + 1
        candidate_count = (2 * u_bound + 1) * (2 * v_bound + 1)
    if candidate_count > rule.maximum_candidate_positions:
        raise _block(
            BlockerCode.STL_ENUMERATION_LIMIT_EXCEEDED,
            "layout_rule_authority.maximum_candidate_positions",
            "candidate_capacity_exceeded",
        )
    return EnumerationPlan(
        a_x=basis.a_x,
        a_y=basis.a_y,
        b_x=basis.b_x,
        b_y=basis.b_y,
        offset_x=basis.offset_x,
        offset_y=basis.offset_y,
        rho=basis.rho,
        u_bound=u_bound,
        v_bound=v_bound,
        candidate_count=candidate_count,
    )


def build_plan(
    rule: LayoutRuleAuthoritySnapshot,
    geometry: ApprovedTubeGeometrySnapshot,
    envelope: CircularTubeCenterEnvelope,
    origin_mode: OriginMode,
    axis_orientation: AxisOrientation,
) -> EnumerationPlan:
    """Convenience runner used only by legacy callers; pretends stages 8 and 12.

    New code MUST call :func:`verify_envelope_shape_and_radius` and
    :func:`verify_inverse_basis_and_candidate_capacity` separately so that
    the stage ordinals in the blocker remain correct.
    """

    basis = verify_envelope_shape_and_radius(
        rule, geometry, envelope, origin_mode, axis_orientation
    )
    return verify_inverse_basis_and_candidate_capacity(rule, basis)


def enumerate_candidates(plan: EnumerationPlan) -> tuple[Candidate, ...]:
    candidates: list[Candidate] = []
    with localcontext() as ctx:
        ctx.prec = DECIMAL_PRECISION
        ctx.rounding = ROUND_HALF_EVEN
        for u in range(-plan.u_bound, plan.u_bound + 1):
            for v in range(-plan.v_bound, plan.v_bound + 1):
                x = Decimal(u) * plan.a_x + Decimal(v) * plan.b_x + plan.offset_x
                y = Decimal(u) * plan.a_y + Decimal(v) * plan.b_y + plan.offset_y
                candidates.append(Candidate(u=u, v=v, x=x, y=y))
    return tuple(candidates)


__all__ = [
    "Candidate",
    "EnumeratedBasisInputs",
    "EnumerationFailure",
    "EnumerationPlan",
    "build_plan",
    "enumerate_candidates",
    "verify_envelope_shape_and_radius",
    "verify_inverse_basis_and_candidate_capacity",
]
