"""Public quantization and negative-zero contract."""

from decimal import Decimal

from hexagent.exchangers.shell_tube.shell_side_pressure_drop import validate_request
from hexagent.exchangers.shell_tube.shell_side_pressure_drop import validation as validation_module
from hexagent.exchangers.shell_tube.shell_side_pressure_drop.decimal_quantization import (
    quantize_public,
)
from hexagent.exchangers.shell_tube.shell_side_pressure_drop.formulas import FormulaCalculationError
from tests.exchangers.shell_tube.shell_side_pressure_drop.test_task034_success_contract import (
    make_valid_raw_request,
)


def test_b043_sspd_public_quantization_failure_token_is_frozen(monkeypatch):
    assert quantize_public(Decimal("-0.0004")) == Decimal("0.000")

    def fail(_value):
        raise FormulaCalculationError("F15_PUBLIC_QUANTIZATION")

    monkeypatch.setattr(validation_module, "quantize_public_pressure_drop", fail)
    result = validate_request(make_valid_raw_request())
    assert "SSPD_PUBLIC_QUANTIZATION_FAILURE" in {item.code for item in result.blockers}
    assert result.blocked_result is not None
    assert result.blocked_result.failure_stage == "S15"
