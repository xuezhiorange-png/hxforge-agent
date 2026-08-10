"""TASK-026 decimal primitives tests (T1-R2 numbered_inventory items 25-30).

Frozen test reference set (T1-R2):
  25. test_decimal_ln_vectors_1_2_10_match
  26. test_decimal_sqrt_vectors_0_2_match
  27. test_decimal_pow_2_3_vectors_1_8_27_0_125_match
  28. test_decimal_failure_emits_BL_DECIMAL_FAILURE
  29. test_decimal_context_uses_160_nominal_200_working_40_guard
  30. test_quantization_occurs_only_at_s12_round_half_even

T1-R2 module allocation: 6 tests in this module.
"""

from __future__ import annotations

import hashlib
from decimal import Decimal

import pytest

from hexagent.exchangers.shell_tube.tube_side_thermal.decimal_primitives import (
    NOMINAL_DECIMAL_PRECISION,
    WORKING_DECIMAL_PRECISION,
    WORKING_GUARD_DIGITS,
    DecimalFailure,
    decimal_ln,
    decimal_pow_2_3,
    decimal_sqrt,
    task026_decimal_context_160,
    task026_decimal_context_200,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.decimal_quantization import (
    HI_QUANTUM_POLICY,
    QUANTIZATION_FIELD_COUNT,
    QUANTIZATION_STAGE,
    ROUNDING_MODE,
    field_for,
    quantize_half_even,
)


def _sha256_of_decimal_string(value: Decimal) -> str:
    return hashlib.sha256(str(value).encode("ascii")).hexdigest()


def test_decimal_ln_vectors_1_2_10_match() -> None:
    """T1-R2 25 — ln(1), ln(2), ln(10) produce the frozen 64-hex SHA."""
    expected = {
        "1": "5feceb66ffc86f38d952786c6d696c79c2dbc239dd4e91b46729d73a27fb57e9",
        "2": "5762fc59129d77cd110123b4646b46f14f79fc506b141657df47d5d00e2ec995",
        "10": "fb6728f87470342f54fe593bfb40253abb33ac65d2d52042ed93bdb42f632b09",
    }
    for inp, sha in expected.items():
        v = decimal_ln(Decimal(inp))
        actual = _sha256_of_decimal_string(v)
        assert actual == sha, f"ln({inp}) sha mismatch: expected {sha[:16]}, got {actual[:16]}"


def test_decimal_sqrt_vectors_0_2_match() -> None:
    """T1-R2 26 — sqrt(0), sqrt(2) produce the frozen 64-hex SHA."""
    expected = {
        "0": "5feceb66ffc86f38d952786c6d696c79c2dbc239dd4e91b46729d73a27fb57e9",
        "2": "94288de337c2d175cf35ec09bbc7d379fea1716fe4c65e22e1c850e1476141b2",
    }
    for inp, sha in expected.items():
        v = decimal_sqrt(Decimal(inp))
        actual = _sha256_of_decimal_string(v)
        assert actual == sha, f"sqrt({inp}) sha mismatch"


def test_decimal_pow_2_3_vectors_1_8_27_0_125_match() -> None:
    """T1-R2 27 — pow_2_3(1, 8, 27, 0.125) produce the frozen 64-hex SHA."""
    expected = {
        "1": "6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4b",
        "8": "47878ec644cf5035e0bd2292f5c88bf3ad5034b8d8e22f19b3de78df4a76dc4b",
        "27": "bc0001f504e48553c9cd782c76f9e80e0b71e057ca770944f7552031830bf39e",
        "0.125": "bf3ebe906c3744d88b8701927fe012e526a8dd0eab1778619669f2bca1fca33a",
    }
    for inp, sha in expected.items():
        v = decimal_pow_2_3(Decimal(inp))
        actual = _sha256_of_decimal_string(v)
        assert actual == sha, f"pow_2_3({inp}) sha mismatch"


def test_decimal_failure_emits_BL_DECIMAL_FAILURE() -> None:
    """T1-R2 28 — Decimal failure maps to DecimalFailure (BL_DECIMAL_FAILURE)."""
    with pytest.raises(DecimalFailure):
        decimal_ln(Decimal("-1"))
    with pytest.raises(DecimalFailure):
        decimal_sqrt(Decimal("-1"))
    with pytest.raises(DecimalFailure):
        decimal_pow_2_3(Decimal("-1"))
    with pytest.raises(DecimalFailure):
        decimal_ln(Decimal("0"))


def test_decimal_context_uses_160_nominal_200_working_40_guard() -> None:
    """T1-R2 29 — Decimal contexts are 160 / 200 / 40 guard digits."""
    assert NOMINAL_DECIMAL_PRECISION == 160
    assert WORKING_DECIMAL_PRECISION == 200
    assert WORKING_GUARD_DIGITS == 40
    ctx_160 = task026_decimal_context_160()
    ctx_200 = task026_decimal_context_200()
    assert ctx_160.prec == 160
    assert ctx_200.prec == 200


def test_quantization_occurs_only_at_s12_round_half_even() -> None:
    """T1-R2 30 — Quantization is at S12 only, ROUND_HALF_EVEN, fixed quantum."""
    assert QUANTIZATION_STAGE == "S12"
    assert ROUNDING_MODE == "ROUND_HALF_EVEN"
    assert HI_QUANTUM_POLICY == "FIXED_ABSOLUTE_QUANTUM_1E_MINUS_6"
    assert QUANTIZATION_FIELD_COUNT == 5
    assert field_for("reynolds_number") == Decimal("0.0001")
    assert field_for("nusselt_number") == Decimal("0.0001")
    assert field_for("tube_side_heat_transfer_coefficient_w_m2_k") == Decimal("0.000001")
    # Verify quantize_half_even applies ROUND_HALF_EVEN
    val = Decimal("0.00015")
    q = quantize_half_even(val, Decimal("0.0001"))
    # ROUND_HALF_EVEN: 0.00015 -> 0.0002 (round to even)
    assert q == Decimal("0.0002")
