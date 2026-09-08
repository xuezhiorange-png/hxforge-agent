"""TASK-166 Decimal-only engineering arithmetic."""

from __future__ import annotations

import decimal
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
    localcontext,
)

PI = Decimal("3.1415926535897932384626433832795028841971693993751")
TWO = Decimal("2")
ONE = Decimal("1")
ZERO = Decimal("0")


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


def finite(value: Decimal) -> bool:
    return type(value) is Decimal and value.is_finite()


def evaluate_exp(value: Decimal) -> Decimal:
    if not finite(value):
        raise InvalidOperation("exp requires finite Decimal")
    with localcontext(engineering_context()) as context:
        result = context.exp(value)
        if not result.is_finite():
            raise Overflow("non-finite exp result")
        return result


def power(base: Decimal, exponent: Decimal) -> Decimal:
    if not finite(base) or not finite(exponent):
        raise InvalidOperation("power requires finite Decimal values")
    with localcontext(engineering_context()) as context:
        result = context.power(base, exponent)
        if not result.is_finite():
            raise Overflow("non-finite power result")
        return result


def sqrt(value: Decimal) -> Decimal:
    with localcontext(engineering_context()) as context:
        result = context.sqrt(value)
        if not result.is_finite():
            raise Overflow("non-finite sqrt result")
        return result


def _atan_reduced(value: Decimal) -> Decimal:
    """Deterministic Decimal atan series after range reduction."""
    if value.is_zero():
        return ZERO
    if value > ONE:
        return PI / TWO - _atan_reduced(ONE / value)
    if value > Decimal("0.5"):
        reduced = (value - ONE) / (value + ONE)
        return PI / Decimal("4") + _atan_reduced(reduced)
    term = value
    result = value
    n = 1
    while n < 400:
        term = -term * value * value
        addend = term / Decimal(2 * n + 1)
        result += addend
        if addend.copy_abs() < Decimal("1e-48"):
            return result
        n += 1
    raise InvalidOperation("atan did not converge")


def acos(value: Decimal) -> Decimal:
    with localcontext(engineering_context()):
        if not finite(value) or value < -ONE or value > ONE:
            raise InvalidOperation("acos domain")
        if value == ONE:
            return ZERO
        if value == -ONE:
            return PI
        root = sqrt(ONE - value * value)
        if value >= ZERO:
            return PI / TWO - _atan_reduced(value / root)
        return PI / TWO + _atan_reduced((-value) / root)


def sin(value: Decimal) -> Decimal:
    """Deterministic Decimal sine used only for source geometry equations."""
    if not finite(value):
        raise InvalidOperation("sin requires finite Decimal")
    with localcontext(engineering_context()):
        # Reduce to [-pi, pi], then use an alternating Taylor series.  The
        # source geometry only reaches a bounded central-angle domain.
        turns = (value / (TWO * PI)).to_integral_value(rounding=decimal.ROUND_HALF_EVEN)
        reduced = value - turns * TWO * PI
        term = reduced
        result = reduced
        square = reduced * reduced
        for index in range(1, 300):
            term = -term * square / Decimal((2 * index) * (2 * index + 1))
            result += term
            if term.copy_abs() < Decimal("1e-48"):
                return result
        raise InvalidOperation("sin did not converge")


def divide(numerator: Decimal, denominator: Decimal) -> Decimal:
    with localcontext(engineering_context()):
        result = numerator / denominator
        if not result.is_finite():
            raise Overflow("non-finite division result")
        return result


__all__ = [
    "ONE",
    "PI",
    "TWO",
    "ZERO",
    "acos",
    "divide",
    "engineering_context",
    "evaluate_exp",
    "finite",
    "power",
    "sin",
    "sqrt",
]
