"""Decimal-only arithmetic policy for TASK-038."""

from __future__ import annotations

from decimal import Decimal, localcontext

from .schema import (
    NOMINAL_DECIMAL_PRECISION,
    OUTER_AREA_QUANTUM,
    OVERALL_U_QUANTUM,
    ROUNDING_MODE,
    UA_QUANTUM,
    WORKING_DECIMAL_PRECISION,
    WORKING_GUARD_DIGITS,
)


def validate_finite_decimal(value: object, field_path: str) -> Decimal:
    if type(value) is not Decimal or not value.is_finite():
        raise ValueError(f"{field_path} must be a finite Decimal")
    return value


def validate_positive_decimal(value: object, field_path: str) -> Decimal:
    result = validate_finite_decimal(value, field_path)
    if result <= 0:
        raise ValueError(f"{field_path} must be positive")
    return result


def validate_nonnegative_decimal(value: object, field_path: str) -> Decimal:
    result = validate_finite_decimal(value, field_path)
    if result < 0:
        raise ValueError(f"{field_path} must be non-negative")
    return result


def working_precision() -> int:
    return max(NOMINAL_DECIMAL_PRECISION, WORKING_DECIMAL_PRECISION) + WORKING_GUARD_DIGITS


def quantize_public(value: Decimal, quantum: Decimal) -> Decimal:
    validate_finite_decimal(value, "value")
    with localcontext() as context:
        context.prec = working_precision()
        context.rounding = ROUNDING_MODE
        return value.quantize(quantum)


def compose_resistances(
    gamma: Decimal,
    h_i: Decimal,
    h_o: Decimal,
    r_fi_i: Decimal,
    r_w_o: Decimal,
    r_fo_o: Decimal,
) -> tuple[Decimal, Decimal, Decimal, Decimal, Decimal, Decimal, Decimal]:
    """Compute the five outer-reference resistance terms and U.

    No resistance is quantized before the total is formed.
    """

    values = (
        validate_positive_decimal(gamma, "outer_to_inner_area_ratio"),
        validate_positive_decimal(h_i, "tube_side_heat_transfer_coefficient_w_m2_k"),
        validate_positive_decimal(h_o, "shell_side_heat_transfer_coefficient_w_m2_k"),
        validate_nonnegative_decimal(r_fi_i, "inside_fouling_resistance"),
        validate_nonnegative_decimal(r_w_o, "wall_resistance"),
        validate_nonnegative_decimal(r_fo_o, "outside_fouling_resistance"),
    )
    ratio, tube_h, shell_h, inside, wall, outside = values
    with localcontext() as context:
        context.prec = working_precision()
        r01 = ratio / tube_h
        r02 = ratio * inside
        r03 = wall
        r04 = outside
        r05 = Decimal(1) / shell_h
        total = r01 + r02 + r03 + r04 + r05
        return r01, r02, r03, r04, r05, total, Decimal(1) / total


def public_u(value: Decimal) -> Decimal:
    return quantize_public(value, OVERALL_U_QUANTUM)


def public_outer_area(value: Decimal) -> Decimal:
    return quantize_public(value, OUTER_AREA_QUANTUM)


def public_ua(value: Decimal) -> Decimal:
    return quantize_public(value, UA_QUANTUM)


__all__ = [
    "compose_resistances",
    "public_outer_area",
    "public_u",
    "public_ua",
    "quantize_public",
    "validate_finite_decimal",
    "validate_nonnegative_decimal",
    "validate_positive_decimal",
    "working_precision",
]
