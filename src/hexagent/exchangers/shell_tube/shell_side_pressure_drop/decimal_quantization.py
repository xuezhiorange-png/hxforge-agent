"""Explicit Decimal context and public quantization for TASK-034."""

from __future__ import annotations

from decimal import (  # noqa: F401
    ROUND_HALF_EVEN,
    Clamped,
    Context,
    Decimal,
    DecimalException,
    DivisionByZero,
    FloatOperation,
    Inexact,
    InvalidOperation,
    Overflow,
    Rounded,
    Subnormal,
    Underflow,
    localcontext,
)


def engineering_context() -> Context:
    context = Context(
        prec=50, rounding=ROUND_HALF_EVEN, Emin=-999999, Emax=999999, capitals=1, clamp=0
    )
    context.traps[InvalidOperation] = True
    context.traps[DivisionByZero] = True
    context.traps[Overflow] = True
    context.traps[Inexact] = False
    context.traps[Rounded] = False
    context.traps[Subnormal] = False
    context.traps[Underflow] = False
    context.traps[Clamped] = False
    context.traps[FloatOperation] = True
    context.clear_flags()
    return context


def finite_decimal(value: object) -> bool:
    return isinstance(value, Decimal) and value.is_finite()


def positive_decimal(value: object) -> bool:
    return isinstance(value, Decimal) and value.is_finite() and value > Decimal("0")


def normalize_negative_zero(value: Decimal) -> Decimal:
    return Decimal("0") if value.is_zero() else value


def quantize_public(value: Decimal) -> Decimal:
    with localcontext(engineering_context()) as context:
        result = context.quantize(value, Decimal("0.001"))
        return normalize_negative_zero(result)


class PublicQuantizationError(ValueError):
    """Raised when the S15 public pressure-drop quantization fails."""


def quantize_public_pressure_drop(value: Decimal) -> Decimal:
    """Own the frozen S15 public quantization stage."""
    try:
        return quantize_public(value)
    except (DecimalException, ArithmeticError, TypeError, ValueError) as exc:
        raise PublicQuantizationError("F15_PUBLIC_QUANTIZATION") from exc


def quantization_collision(value: Decimal) -> bool:
    return finite_decimal(value) and quantize_public(value) == Decimal("0.000") and value != 0


__all__ = [
    "engineering_context",
    "finite_decimal",
    "positive_decimal",
    "normalize_negative_zero",
    "quantize_public",
    "PublicQuantizationError",
    "quantize_public_pressure_drop",
    "quantization_collision",
]
