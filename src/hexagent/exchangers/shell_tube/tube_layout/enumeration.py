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

from .canonical import DECIMAL_PRECISION, SQRT_3, decimal_string, parse_decimal
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
class VerifiedEnvelopeRadius:
    """Frozen Stage 8 output: envelope/radius only, NO basis work.

    Round 4 §4 (P0-2) requires Stage 8 to expose ONLY ``rho`` (the verified
    effective radius) and the supporting envelope / geometry decimals needed
    for hashing. There are intentionally NO basis vectors, NO axis swap, NO
    origin offset, NO determinant, NO bounds, and NO candidate count.
    """

    envelope_diameter_m: str
    outer_diameter_m: str
    edge_clearance_m: str
    rho: str


@dataclass(frozen=True)
class EnumeratedBasisInputs:
    """Frozen Stage-12-pre-stage snapshot: basis vectors, axis swap, origin offset.

    Round 4 §4 (P0-2) makes this the SECOND stage's responsibility. It is
    produced by :func:`_compute_basis_for_stage12` and consumed by
    :func:`verify_inverse_basis_and_candidate_capacity`. Stage 8 NEVER sees
    or produces this; doing so would leak Stage-12 basis construction into
    Stage 8.
    """

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


def _block(code: BlockerCode, field_path: str, message_key: str) -> EnumerationFailure:
    return EnumerationFailure(
        MessageEntry(code=code.value, field_path=field_path, message_key=message_key)
    )


def _basis_vectors(
    rule: LayoutRuleAuthoritySnapshot,
    axis_orientation: AxisOrientation,
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    """Return (a_x, a_y, b_x, b_y) for the given pattern_family and orientation.

    This is pure Stage-12 derivation: it does not call any Stage-8 helper and
    does not validate the envelope. Round 4 §4 (P0-2) keeps this private to
    :mod:`enumeration` so that only :func:`verify_inverse_basis_and_candidate_capacity`
    can introduce basis work.
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
) -> VerifiedEnvelopeRadius:
    """Stage 8 — envelope shape AND positive effective radius ONLY.

    Round 4 §4 (P0-2): this function MUST NOT construct the pattern basis
    vectors. It MUST NOT perform axis swap. It MUST NOT compute origin
    offset. It MUST NOT check invertibility or candidate capacity.

    The returned :class:`VerifiedEnvelopeRadius` carries the verified
    ``rho`` decimal string plus the raw decimal strings needed to derive
    it, so downstream Stage-12 work can compute the basis without
    touching Stage-8 inputs.
    """

    with localcontext() as ctx:
        ctx.prec = DECIMAL_PRECISION
        ctx.rounding = ROUND_HALF_EVEN
        outer = parse_decimal(geometry.outer_diameter_m, positive=True)
        diameter = parse_decimal(envelope.tube_center_envelope_diameter_m, positive=True)
        edge_clearance = parse_decimal(rule.edge_clearance_m, positive=False)
        rho = diameter / Decimal(2) - outer / Decimal(2) - edge_clearance
    if rho <= 0:
        raise _block(
            BlockerCode.STL_ENVELOPE_INVALID,
            "placement_envelope",
            "effective_radius_nonpositive",
        )
    return VerifiedEnvelopeRadius(
        envelope_diameter_m=envelope.tube_center_envelope_diameter_m,
        outer_diameter_m=geometry.outer_diameter_m,
        edge_clearance_m=rule.edge_clearance_m,
        rho=decimal_string(rho),
    )


def _compute_basis_for_stage12(
    rule: LayoutRuleAuthoritySnapshot,
    geometry: ApprovedTubeGeometrySnapshot,
    envelope: CircularTubeCenterEnvelope,
    origin_mode: OriginMode,
    axis_orientation: AxisOrientation,
    rho_decimal: Decimal,
) -> EnumeratedBasisInputs:
    """Stage 12 internal: produce the full :class:`EnumeratedBasisInputs`.

    Round 4 §4 (P0-2): this is the ONLY place where basis vectors, axis
    swap, and origin offset get derived. It does not run if Stage 8 has
    not already produced :func:`verify_envelope_shape_and_radius`.
    """

    a_x, a_y, b_x, b_y = _basis_vectors(rule, axis_orientation)
    if origin_mode is OriginMode.CENTER_ON_LATTICE_POINT:
        offset_x = Decimal(0)
        offset_y = Decimal(0)
    else:
        offset_x = (a_x + b_x) / Decimal(2)
        offset_y = (a_y + b_y) / Decimal(2)
    return EnumeratedBasisInputs(
        a_x=a_x,
        a_y=a_y,
        b_x=b_x,
        b_y=b_y,
        offset_x=offset_x,
        offset_y=offset_y,
        rho=rho_decimal,
        pattern_family=rule.pattern_family,
        origin_mode=origin_mode,
        axis_orientation=axis_orientation,
    )


def verify_inverse_basis_and_candidate_capacity(
    rule: LayoutRuleAuthoritySnapshot,
    geometry: ApprovedTubeGeometrySnapshot,
    envelope: CircularTubeCenterEnvelope,
    origin_mode: OriginMode,
    axis_orientation: AxisOrientation,
    stage8: VerifiedEnvelopeRadius,
) -> EnumerationPlan:
    """Stage 12 — inverse basis, bounds, candidate capacity.

    Round 4 §4 (P0-2): the basis construction that was previously leaked
    into Stage 8 now happens here. Caller passes the verified radius from
    Stage 8; we rebuild the basis internally and compute determinant,
    inverse basis, U/V bounds, and candidate count. Blocker codes emitted:

    - ``STL_BASIS_NON_INVERTIBLE`` on zero determinant.
    - ``STL_ENUMERATION_LIMIT_EXCEEDED`` when the candidate count exceeds
      the rule's frozen capacity.
    """

    with localcontext() as ctx:
        ctx.prec = DECIMAL_PRECISION
        ctx.rounding = ROUND_HALF_EVEN
        rho_decimal = parse_decimal(stage8.rho, positive=True)
        basis = _compute_basis_for_stage12(
            rule, geometry, envelope, origin_mode, axis_orientation, rho_decimal
        )
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
        d_x = rho_decimal + abs(basis.offset_x)
        d_y = rho_decimal + abs(basis.offset_y)
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
        a_x=a_x,
        a_y=a_y,
        b_x=b_x,
        b_y=b_y,
        offset_x=basis.offset_x,
        offset_y=basis.offset_y,
        rho=rho_decimal,
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
    the stage ordinals in the blocker remain correct and Stage 8 stays free
    of basis work.
    """

    stage8 = verify_envelope_shape_and_radius(
        rule, geometry, envelope, origin_mode, axis_orientation
    )
    return verify_inverse_basis_and_candidate_capacity(
        rule, geometry, envelope, origin_mode, axis_orientation, stage8
    )


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
    "VerifiedEnvelopeRadius",
    "build_plan",
    "enumerate_candidates",
    "verify_envelope_shape_and_radius",
    "verify_inverse_basis_and_candidate_capacity",
]
