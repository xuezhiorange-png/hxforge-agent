from __future__ import annotations

from decimal import Decimal

import pytest

from hexagent.exchangers.shell_tube.tube_layout.canonical import (
    CanonicalizationError,
    canonical_json,
    quantized_decimal_string,
)


def test_canonical_json_sorts_keys_and_rejects_float() -> None:
    assert canonical_json({"b": 1, "a": 2}) == '{"a":2,"b":1}'
    with pytest.raises(CanonicalizationError):
        canonical_json({"x": 1.0})


def test_coordinate_quantization_is_half_even() -> None:
    assert quantized_decimal_string(Decimal("0.0000000000015")) == "0.000000000002"
    assert quantized_decimal_string(Decimal("0.0000000000025")) == "0.000000000002"
