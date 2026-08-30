"""Owned Decimal arithmetic for TASK-037.

All engineering inputs are Decimal values.  Binary floating point is rejected
at this boundary so that Python-version differences cannot enter the identity
chain through an implicit conversion.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from decimal import ROUND_HALF_EVEN, Context, Decimal, InvalidOperation, localcontext
from typing import Final

from .schema import (
    NOMINAL_DECIMAL_PRECISION,
    RATIO_QUANTUM,
    ROUNDING_MODE,
    WALL_OUTPUT_QUANTUM,
    WORKING_DECIMAL_PRECISION,
)

DECIMAL_ROUNDING: Final[str] = ROUNDING_MODE
RATIO_QUANTUM_DECIMAL: Final[Decimal] = Decimal(RATIO_QUANTUM)
WALL_OUTPUT_QUANTUM_DECIMAL: Final[Decimal] = Decimal(WALL_OUTPUT_QUANTUM)


def require_decimal(value: object, field_path: str) -> Decimal:
    """Return an exact Decimal or reject non-Decimal engineering input."""

    if type(value) is not Decimal:
        raise TypeError(f"{field_path} must be Decimal")
    if not value.is_finite():
        raise ValueError(f"{field_path} must be finite")
    return value


def validate_finite_decimal(value: object, field_path: str) -> Decimal:
    return require_decimal(value, field_path)


def validate_positive_finite_decimal(value: object, field_path: str) -> Decimal:
    result = require_decimal(value, field_path)
    if result <= 0:
        raise ValueError(f"{field_path} must be positive")
    return result


def validate_nonnegative_finite_decimal(value: object, field_path: str) -> Decimal:
    result = require_decimal(value, field_path)
    if result < 0:
        raise ValueError(f"{field_path} must be non-negative")
    return result


@contextmanager
def working_decimal_context() -> Iterator[Context]:
    """Use the frozen 200-digit working context with HALF_EVEN rounding."""

    with localcontext() as context:
        context.prec = WORKING_DECIMAL_PRECISION
        context.rounding = ROUND_HALF_EVEN
        yield context


@contextmanager
def nominal_decimal_context() -> Iterator[Context]:
    """Expose the frozen nominal precision for callers doing validation."""

    with localcontext() as context:
        context.prec = NOMINAL_DECIMAL_PRECISION
        context.rounding = ROUND_HALF_EVEN
        yield context


local_decimal_context = working_decimal_context


def quantize_half_even(value: object, quantum: Decimal) -> Decimal:
    """Quantize a finite Decimal under the owned HALF_EVEN policy."""

    decimal_value = require_decimal(value, "value")
    quantum_value = require_decimal(quantum, "quantum")
    if quantum_value <= 0:
        raise ValueError("quantum must be positive")
    with working_decimal_context():
        try:
            return decimal_value.quantize(quantum_value, rounding=ROUND_HALF_EVEN)
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("Decimal quantization failed") from exc


def canonical_decimal_lexeme(value: object) -> str:
    """Return the caller-supplied Decimal's stable ASCII lexical spelling."""

    decimal_value = require_decimal(value, "value")
    return str(decimal_value)


def decimal_ln(value: object) -> Decimal:
    """Compute natural logarithm through Decimal.ln only."""

    decimal_value = validate_positive_finite_decimal(value, "value")
    with working_decimal_context():
        return decimal_value.ln()


__all__ = [
    "DECIMAL_ROUNDING",
    "RATIO_QUANTUM_DECIMAL",
    "WALL_OUTPUT_QUANTUM_DECIMAL",
    "canonical_decimal_lexeme",
    "decimal_ln",
    "local_decimal_context",
    "nominal_decimal_context",
    "quantize_half_even",
    "require_decimal",
    "validate_finite_decimal",
    "validate_nonnegative_finite_decimal",
    "validate_positive_finite_decimal",
    "working_decimal_context",
]
