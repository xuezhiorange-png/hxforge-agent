"""Frozen Decimal F01-F04 formula tests."""

from decimal import Decimal

from hexagent.exchangers.shell_tube.shell_side_flow_state import formulas


def test_t032_frm_001_mass_velocity_raw_and_public() -> None:
    raw = formulas.evaluate_mass_velocity(Decimal("2.0000"), Decimal("0.1000"))
    assert raw == Decimal("20")
    assert formulas.quantize_mass_velocity(raw) == Decimal("20.0000000")


def test_t032_frm_002_bulk_velocity_raw_and_public() -> None:
    raw = formulas.evaluate_bulk_velocity(Decimal("20"), Decimal("998.2000"))
    assert raw == Decimal("0.020036064916850330595071128030454818673612502504508")
    assert formulas.quantize_bulk_velocity(raw) == Decimal("0.0200361")


def test_t032_frm_003_reynolds_raw_and_public() -> None:
    raw = formulas.evaluate_reynolds(Decimal("20"), Decimal("0.0200000"), Decimal("0.0010000"))
    assert raw == Decimal("400")
    assert formulas.quantize_reynolds(raw) == Decimal("400.0000")


def test_t032_frm_004_prandtl_raw_and_public() -> None:
    raw = formulas.evaluate_prandtl(
        Decimal("0.0010000"), Decimal("4000.0000"), Decimal("0.6000000")
    )
    assert raw == Decimal("6.6666666666666666666666666666666666666666666666667")
    assert formulas.quantize_prandtl(raw) == Decimal("6.6667")


def test_t032_frm_005_task031_canonical_decimal_string_to_decimal_binding() -> None:
    value = Decimal("0.1000000")
    assert type(value) is Decimal
    assert formulas.evaluate_mass_velocity(Decimal("2.0000000"), value) == Decimal("20")
    assert formulas.DECIMAL_PRECISION == 50
    assert formulas.ROUNDING_MODE == "ROUND_HALF_EVEN"
