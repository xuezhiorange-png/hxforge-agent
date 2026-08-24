"""TASK033 public Decimal quantum tests."""

from __future__ import annotations

from decimal import Decimal

from hexagent.exchangers.shell_tube.shell_side_heat_transfer.decimal_quantization import (
    HTC_OUTPUT_QUANTUM,
    engineering_context,
    normalize_negative_zero,
    quantize_public_htc,
)
from tests.exchangers.shell_tube.shell_side_heat_transfer.test_task033_models import valid_result


def test_public_quantization_and_negative_zero() -> None:
    """T033-025_HTC_PUBLIC_QUANTIZATION_AND_NEGATIVE_ZERO."""
    assert Decimal("0.0001") == HTC_OUTPUT_QUANTUM
    assert quantize_public_htc(Decimal("1.23456")) == Decimal("1.2346")
    assert normalize_negative_zero(Decimal("-0.0000")) == Decimal("0.0000")
    result = valid_result()
    assert result.heat_transfer is not None
    assert (
        result.heat_transfer.modeled_shell_side_heat_transfer_coefficient_w_m2_k.as_tuple().exponent
        == -4
    )
    assert engineering_context().prec == 50
