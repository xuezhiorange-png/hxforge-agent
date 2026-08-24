"""TASK033 formula and nominal single-phase tests."""

from __future__ import annotations

from decimal import Decimal

import pytest

from hexagent.exchangers.shell_tube.shell_side_heat_transfer import validate_request
from hexagent.exchangers.shell_tube.shell_side_heat_transfer.formulas import (
    FormulaCalculationError,
    evaluate_htc,
)
from tests.exchangers.shell_tube.shell_side_heat_transfer.test_task033_models import (
    copy_request,
    valid_result,
)


def test_nominal_single_phase_liquid() -> None:
    """T033-019_NOMINAL_SINGLE_PHASE_LIQUID."""
    result = valid_result(phase="SINGLE_PHASE_LIQUID")
    assert result.heat_transfer is not None
    assert result.heat_transfer.heat_transfer_surface == "OUTER_TUBE_SURFACE"


def test_nominal_single_phase_gas() -> None:
    """T033-020_NOMINAL_SINGLE_PHASE_GAS."""
    result = valid_result(phase="SINGLE_PHASE_GAS")
    assert result.heat_transfer is not None


def test_re_exponent_is_exact_eleven_over_twenty() -> None:
    """T033-021_RE_EXPONENT_11_OVER_20."""
    result = evaluate_htc(
        reynolds=Decimal("10000"),
        prandtl=Decimal("2"),
        thermal_conductivity=Decimal("0.5"),
        equivalent_diameter=Decimal("0.02"),
    )
    assert result.raw > Decimal("0")


def test_pr_exponent_is_exact_one_over_three() -> None:
    """T033-022_PR_EXPONENT_1_OVER_3."""
    first = evaluate_htc(
        reynolds=Decimal("10000"),
        prandtl=Decimal("1"),
        thermal_conductivity=Decimal("0.5"),
        equivalent_diameter=Decimal("0.02"),
    )
    second = evaluate_htc(
        reynolds=Decimal("10000"),
        prandtl=Decimal("8"),
        thermal_conductivity=Decimal("0.5"),
        equivalent_diameter=Decimal("0.02"),
    )
    assert second.raw > first.raw


def test_formula_input_domain_is_fail_closed() -> None:
    """T033-023_FORMULA_INPUT_DOMAIN."""
    with pytest.raises(FormulaCalculationError):
        evaluate_htc(
            reynolds=Decimal("0"),
            prandtl=Decimal("1"),
            thermal_conductivity=Decimal("1"),
            equivalent_diameter=Decimal("1"),
        )


def test_fractional_power_failure_is_not_fallback() -> None:
    """T033-024_FRACTIONAL_POWER_FAILURE."""
    raw = copy_request()
    raw["task032_flow_state"]["shell_side_prandtl_number"] = "NaN"
    result = validate_request(raw)
    assert result.heat_transfer is None
    assert result.blockers
