"""Frozen TASK-031 engineering formula evaluation."""

from __future__ import annotations

import decimal
from decimal import Decimal, localcontext

from hexagent.exchangers.shell_tube.tube_layout.models import PatternFamily

from .models import FORMULA_A_ID, FORMULA_B_ID

DECIMAL_PRECISION = 50
ROUNDING_MODE = decimal.ROUND_HALF_EVEN

PI = Decimal(
    "3.141592653589793238462643383279502884197169399375105820974944592307816406286208628620898062808825348"
)
SQRT3 = Decimal(
    "1.7320508075688772935274463415058723669428052538103806280558069794519330169088000370811461867572485756"
)

AREA_OUTPUT_QUANTUM = Decimal("0.000000000000000000000001")
DIAMETER_OUTPUT_QUANTUM = Decimal("0.000000000001")


def _decimal_context() -> decimal.Context:
    return decimal.Context(prec=DECIMAL_PRECISION, rounding=ROUNDING_MODE)


def evaluate_formula_a(
    *,
    shell_inside_diameter_m: Decimal,
    central_inter_baffle_spacing_m: Decimal,
    pitch_m: Decimal,
    tube_outside_diameter_m: Decimal,
) -> Decimal:
    with localcontext(_decimal_context()):
        ct = pitch_m - tube_outside_diameter_m
        ratio = shell_inside_diameter_m / pitch_m
        as_step = ratio * central_inter_baffle_spacing_m
        return as_step * ct


def evaluate_formula_b_square(
    *,
    pitch_m: Decimal,
    tube_outside_diameter_m: Decimal,
) -> Decimal:
    with localcontext(_decimal_context()):
        do2 = tube_outside_diameter_m * tube_outside_diameter_m
        pt2 = pitch_m * pitch_m
        tube_term = PI * do2 / Decimal("4")
        free_area = pt2 - tube_term
        numerator = Decimal("4") * free_area
        denominator = PI * tube_outside_diameter_m
        return numerator / denominator


def evaluate_formula_b_triangular(
    *,
    pitch_m: Decimal,
    tube_outside_diameter_m: Decimal,
) -> Decimal:
    with localcontext(_decimal_context()):
        do2 = tube_outside_diameter_m * tube_outside_diameter_m
        pt2 = pitch_m * pitch_m
        cell_term = SQRT3 * pt2 / Decimal("4")
        tube_term = PI * do2 / Decimal("8")
        free_area = cell_term - tube_term
        numerator = Decimal("4") * free_area
        denominator = PI * tube_outside_diameter_m / Decimal("2")
        return numerator / denominator


def evaluate_formula_b(
    *,
    pattern_family: PatternFamily,
    pitch_m: Decimal,
    tube_outside_diameter_m: Decimal,
) -> Decimal:
    if pattern_family is PatternFamily.SQUARE:
        return evaluate_formula_b_square(
            pitch_m=pitch_m,
            tube_outside_diameter_m=tube_outside_diameter_m,
        )
    if pattern_family is PatternFamily.TRIANGULAR:
        return evaluate_formula_b_triangular(
            pitch_m=pitch_m,
            tube_outside_diameter_m=tube_outside_diameter_m,
        )
    raise ValueError("unsupported pattern family for formula B")


def quantize_area(raw_value: Decimal) -> str:
    with localcontext(_decimal_context()):
        public_q = raw_value.quantize(AREA_OUTPUT_QUANTUM, rounding=ROUNDING_MODE)
        if public_q.is_zero():
            public_q = public_q.copy_abs()
        return format(public_q, "f")


def quantize_diameter(raw_value: Decimal) -> str:
    with localcontext(_decimal_context()):
        public_q = raw_value.quantize(DIAMETER_OUTPUT_QUANTUM, rounding=ROUNDING_MODE)
        if public_q.is_zero():
            public_q = public_q.copy_abs()
        return format(public_q, "f")


def area_quantization_collision(raw_value: Decimal) -> bool:
    with localcontext(_decimal_context()):
        public_q = raw_value.quantize(AREA_OUTPUT_QUANTUM, rounding=ROUNDING_MODE)
        return raw_value > 0 and public_q.is_zero()


def diameter_quantization_collision(raw_value: Decimal) -> bool:
    with localcontext(_decimal_context()):
        public_q = raw_value.quantize(DIAMETER_OUTPUT_QUANTUM, rounding=ROUNDING_MODE)
        return raw_value > 0 and public_q.is_zero()


__all__ = [
    "AREA_OUTPUT_QUANTUM",
    "DECIMAL_PRECISION",
    "DIAMETER_OUTPUT_QUANTUM",
    "FORMULA_A_ID",
    "FORMULA_B_ID",
    "PI",
    "ROUNDING_MODE",
    "SQRT3",
    "area_quantization_collision",
    "diameter_quantization_collision",
    "evaluate_formula_a",
    "evaluate_formula_b",
    "evaluate_formula_b_square",
    "evaluate_formula_b_triangular",
    "quantize_area",
    "quantize_diameter",
]
