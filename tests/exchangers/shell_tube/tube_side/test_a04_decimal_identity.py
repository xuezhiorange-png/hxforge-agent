"""§A04 — Decimal structural identity tests."""

from __future__ import annotations

from decimal import Decimal

import pytest

import hexagent.exchangers.shell_tube.tube_side as ts


def test_a04_decimal_finite() -> None:
    ctx = ts.local_decimal_context()
    assert ctx.prec == 160


def test_a04_quantize_round_half_even() -> None:
    q = ts.quantize_half_even(Decimal("0.000000005"), Decimal("0.00000001"), "test")
    assert q == Decimal("0.00000000")


def test_a04_quantize_trap_rejects_nan() -> None:
    with pytest.raises(ValueError):
        ts.quantize_half_even(Decimal("NaN"), Decimal("0.00000001"), "test")


def test_a04_pi_canonical_bytes() -> None:
    assert len(ts.PI_DECIMAL_LEXEME) > 50
    assert ts.sha256_hex(ts.PI_DECIMAL_LEXEME) == "aa6eee625a838a2af84f7d591e8c677bdd9c1b07c44380e2fee8fc738f9234f0"


def test_a04_canonical_decimal_lexeme() -> None:
    assert ts.canonical_decimal_lexeme(Decimal("1.5")) == b"1.5"


def test_a04_validate_positive_rejects_zero() -> None:
    with pytest.raises(ValueError):
        ts.validate_positive_finite_decimal(Decimal("0"), "test")

# ruff: noqa: E501
