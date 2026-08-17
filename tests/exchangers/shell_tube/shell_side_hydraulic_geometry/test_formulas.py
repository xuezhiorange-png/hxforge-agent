from __future__ import annotations

from decimal import Decimal

from hexagent.exchangers.shell_tube.shell_side_hydraulic_geometry import formulas
from hexagent.exchangers.shell_tube.tube_layout.models import PatternFamily


def test_formula_a_v1_oracle() -> None:
    raw = formulas.evaluate_formula_a(
        shell_inside_diameter_m=Decimal("0.250000000000"),
        central_inter_baffle_spacing_m=Decimal("0.125000000000"),
        pitch_m=Decimal("0.025000000000"),
        tube_outside_diameter_m=Decimal("0.019000000000"),
    )
    assert formulas.quantize_area(raw) == "0.007500000000000000000000"


def test_formula_b_square_v1_oracle() -> None:
    raw = formulas.evaluate_formula_b(
        pattern_family=PatternFamily.SQUARE,
        pitch_m=Decimal("0.025000000000"),
        tube_outside_diameter_m=Decimal("0.019000000000"),
    )
    assert formulas.quantize_diameter(raw) == "0.022882879761"


def test_formula_b_triangular_v2_oracle() -> None:
    raw = formulas.evaluate_formula_b(
        pattern_family=PatternFamily.TRIANGULAR,
        pitch_m=Decimal("0.025000000000"),
        tube_outside_diameter_m=Decimal("0.019000000000"),
    )
    assert formulas.quantize_diameter(raw) == "0.017271637857"


def test_frozen_constants_are_decimal_strings() -> None:
    assert type(formulas.PI) is Decimal
    assert type(formulas.SQRT3) is Decimal
    assert formulas.DECIMAL_PRECISION == 50
