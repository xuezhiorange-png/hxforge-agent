"""TASK-029 shared Decimal context, pressure quantum, and negative-zero normalization.

Prerequisite for ledger DECIMAL canonical identity. Does not validate, quantize
non-zero inputs, or perform pressure arithmetic.
"""

from __future__ import annotations

import decimal
from decimal import Context, Decimal
from typing import Final

TASK029_DECIMAL_PRECISION: Final[int] = 28
TASK029_ROUNDING_MODE: Final[str] = decimal.ROUND_HALF_EVEN
TASK029_PRESSURE_QUANTUM_PA: Final[Decimal] = Decimal("0.001")

_TASK029_FROZEN_ZERO: Final[Decimal] = Decimal("0.000")


def _require_decimal(value: object) -> Decimal:
    if type(value) is not Decimal:
        msg = f"normalize_negative_zero requires Decimal, got {type(value).__name__}"
        raise TypeError(msg)
    return value


def task029_decimal_context() -> Context:
    """Return TASK-029 deterministic Decimal context without mutating global state."""
    return Context(prec=TASK029_DECIMAL_PRECISION, rounding=TASK029_ROUNDING_MODE)


def normalize_negative_zero(value: Decimal) -> Decimal:
    """Canonicalize Decimal zero to ``Decimal('0.000')``; preserve non-zero values exactly."""
    decimal_value = _require_decimal(value)
    if decimal_value.is_zero():
        return _TASK029_FROZEN_ZERO
    return decimal_value


__all__ = [
    "TASK029_DECIMAL_PRECISION",
    "TASK029_PRESSURE_QUANTUM_PA",
    "TASK029_ROUNDING_MODE",
    "normalize_negative_zero",
    "task029_decimal_context",
]
