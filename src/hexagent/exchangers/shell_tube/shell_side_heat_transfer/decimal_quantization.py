"""Explicit Decimal context and public HTC quantization."""

from __future__ import annotations

from decimal import (
    ROUND_HALF_EVEN,
    Clamped,
    Context,
    Decimal,
    DivisionByZero,
    FloatOperation,
    Inexact,
    InvalidOperation,
    Overflow,
    Rounded,
    Subnormal,
    Underflow,
)

HTC_OUTPUT_QUANTUM = Decimal("0.0001")


def engineering_context() -> Context:
    context = Context(
        prec=50,
        rounding=ROUND_HALF_EVEN,
        Emin=-999999,
        Emax=999999,
        capitals=1,
        clamp=0,
    )
    for signal in context.traps:
        context.traps[signal] = False
    context.traps[InvalidOperation] = True
    context.traps[DivisionByZero] = True
    context.traps[Overflow] = True
    context.traps[FloatOperation] = True
    context.traps[Inexact] = False
    context.traps[Rounded] = False
    context.traps[Subnormal] = False
    context.traps[Underflow] = False
    context.traps[Clamped] = False
    context.clear_flags()
    return context


def normalize_negative_zero(value: Decimal) -> Decimal:
    if value.is_zero() and value.is_signed():
        return value.copy_abs()
    return value


def quantize_public_htc(value: Decimal) -> Decimal:
    context = engineering_context()
    quantized = context.quantize(value, HTC_OUTPUT_QUANTUM)
    return normalize_negative_zero(quantized)


def quantization_collision(value: Decimal) -> bool:
    if not value.is_finite() or value <= 0:
        return True
    return quantize_public_htc(value).is_zero()


def canonical_decimal(value: Decimal) -> str:
    return str(normalize_negative_zero(value))


__all__ = [
    "HTC_OUTPUT_QUANTUM",
    "canonical_decimal",
    "engineering_context",
    "normalize_negative_zero",
    "quantization_collision",
    "quantize_public_htc",
]
