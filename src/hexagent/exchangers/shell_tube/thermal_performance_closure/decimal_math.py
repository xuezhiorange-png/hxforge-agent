"""Deterministic Decimal arithmetic and the frozen Table 7 operation AST."""

from __future__ import annotations

from collections.abc import Callable
from decimal import (
    ROUND_CEILING,
    ROUND_FLOOR,
    ROUND_HALF_EVEN,
    Context,
    Decimal,
    DecimalException,
    DivisionByZero,
    InvalidOperation,
    Overflow,
    Underflow,
    localcontext,
)

from .models import IntervalDecimal

TASK162_DECIMAL_CONTEXT = Context(
    prec=160,
    rounding=ROUND_HALF_EVEN,
    Emin=-999_999,
    Emax=999_999,
    capitals=1,
    clamp=0,
)
TASK162_LOWER_CONTEXT = Context(
    prec=160,
    rounding=ROUND_FLOOR,
    Emin=-999_999,
    Emax=999_999,
    capitals=1,
    clamp=0,
)
TASK162_UPPER_CONTEXT = Context(
    prec=160,
    rounding=ROUND_CEILING,
    Emin=-999_999,
    Emax=999_999,
    capitals=1,
    clamp=0,
)

TASK162_ENERGY_BALANCE_POLICY_ID = "TASK162_DIRECTED_INTERVAL_CLOSURE_V1"


class DecimalArithmeticError(ArithmeticError):
    """A fatal Decimal operation failure at the TASK162 boundary."""


def _as_decimal(value: Decimal) -> Decimal:
    if type(value) is not Decimal:
        raise DecimalArithmeticError("TASK162 requires Decimal operands")
    return value


def _run(context: Context, operation: Callable[[Context], Decimal]) -> Decimal:
    try:
        with localcontext(context) as active:
            result = operation(active)
            if (
                active.flags[InvalidOperation]
                or active.flags[DivisionByZero]
                or active.flags[Overflow]
            ):
                raise DecimalArithmeticError("fatal Decimal operation")
            if active.flags[Underflow]:
                raise DecimalArithmeticError("fatal Decimal underflow")
            if not result.is_finite():
                raise DecimalArithmeticError("nonfinite Decimal result")
            return result
    except DecimalArithmeticError:
        raise
    except (DecimalException, ArithmeticError) as exc:
        raise DecimalArithmeticError("fatal Decimal operation") from exc


def decimal_add(left: Decimal, right: Decimal) -> Decimal:
    left = _as_decimal(left)
    right = _as_decimal(right)
    return _run(TASK162_DECIMAL_CONTEXT, lambda ctx: ctx.add(left, right))


def decimal_subtract(left: Decimal, right: Decimal) -> Decimal:
    left = _as_decimal(left)
    right = _as_decimal(right)
    return _run(TASK162_DECIMAL_CONTEXT, lambda ctx: ctx.subtract(left, right))


def decimal_multiply(left: Decimal, right: Decimal) -> Decimal:
    left = _as_decimal(left)
    right = _as_decimal(right)
    return _run(TASK162_DECIMAL_CONTEXT, lambda ctx: ctx.multiply(left, right))


def decimal_divide(left: Decimal, right: Decimal) -> Decimal:
    left = _as_decimal(left)
    right = _as_decimal(right)
    if right == 0:
        raise DecimalArithmeticError("Decimal division by zero")
    return _run(TASK162_DECIMAL_CONTEXT, lambda ctx: ctx.divide(left, right))


def decimal_negate(value: Decimal) -> Decimal:
    value = _as_decimal(value)
    return _run(TASK162_DECIMAL_CONTEXT, lambda ctx: ctx.minus(value))


def decimal_exp(value: Decimal) -> Decimal:
    """Evaluate exp with the frozen Decimal context and no binary float."""

    value = _as_decimal(value)
    return _run(TASK162_DECIMAL_CONTEXT, lambda ctx: ctx.exp(value))


def decimal_power_int(value: Decimal, exponent: int) -> Decimal:
    value = _as_decimal(value)
    if type(exponent) is not int or exponent < 0:
        raise DecimalArithmeticError("invalid integer exponent")
    return _run(TASK162_DECIMAL_CONTEXT, lambda ctx: ctx.power(value, exponent))


def _directed(context: Context, operation: Callable[..., Decimal], *operands: Decimal) -> Decimal:
    operands = tuple(_as_decimal(item) for item in operands)
    return _run(context, lambda ctx: operation(ctx, *operands))


def _lower_add(a: Decimal, b: Decimal) -> Decimal:
    return _directed(TASK162_LOWER_CONTEXT, lambda ctx, x, y: ctx.add(x, y), a, b)


def _upper_add(a: Decimal, b: Decimal) -> Decimal:
    return _directed(TASK162_UPPER_CONTEXT, lambda ctx, x, y: ctx.add(x, y), a, b)


def _lower_sub(a: Decimal, b: Decimal) -> Decimal:
    return _directed(TASK162_LOWER_CONTEXT, lambda ctx, x, y: ctx.subtract(x, y), a, b)


def _upper_sub(a: Decimal, b: Decimal) -> Decimal:
    return _directed(TASK162_UPPER_CONTEXT, lambda ctx, x, y: ctx.subtract(x, y), a, b)


def _lower_mul(a: Decimal, b: Decimal) -> Decimal:
    return _directed(TASK162_LOWER_CONTEXT, lambda ctx, x, y: ctx.multiply(x, y), a, b)


def _upper_mul(a: Decimal, b: Decimal) -> Decimal:
    return _directed(TASK162_UPPER_CONTEXT, lambda ctx, x, y: ctx.multiply(x, y), a, b)


def _lower_div(a: Decimal, b: Decimal) -> Decimal:
    if b == 0:
        raise DecimalArithmeticError("interval division by zero")
    return _directed(TASK162_LOWER_CONTEXT, lambda ctx, x, y: ctx.divide(x, y), a, b)


def _upper_div(a: Decimal, b: Decimal) -> Decimal:
    if b == 0:
        raise DecimalArithmeticError("interval division by zero")
    return _directed(TASK162_UPPER_CONTEXT, lambda ctx, x, y: ctx.divide(x, y), a, b)


def _interval(lower: Decimal, upper: Decimal) -> IntervalDecimal:
    lower = _as_decimal(lower)
    upper = _as_decimal(upper)
    if not lower.is_finite() or not upper.is_finite() or lower > upper:
        raise DecimalArithmeticError("invalid Decimal interval")
    return IntervalDecimal(lower=lower, upper=upper)


def interval_add(left: IntervalDecimal, right: IntervalDecimal) -> IntervalDecimal:
    return _interval(_lower_add(left.lower, right.lower), _upper_add(left.upper, right.upper))


def interval_subtract(left: IntervalDecimal, right: IntervalDecimal) -> IntervalDecimal:
    return _interval(_lower_sub(left.lower, right.upper), _upper_sub(left.upper, right.lower))


def interval_multiply(left: IntervalDecimal, right: IntervalDecimal) -> IntervalDecimal:
    products = (
        (left.lower, right.lower),
        (left.lower, right.upper),
        (left.upper, right.lower),
        (left.upper, right.upper),
    )
    lower_values = tuple(_lower_mul(a, b) for a, b in products)
    upper_values = tuple(_upper_mul(a, b) for a, b in products)
    return _interval(min(lower_values), max(upper_values))


def interval_divide(left: IntervalDecimal, right: IntervalDecimal) -> IntervalDecimal:
    if right.lower <= 0 <= right.upper:
        raise DecimalArithmeticError("interval divisor contains zero")
    quotients = (
        (left.lower, right.lower),
        (left.lower, right.upper),
        (left.upper, right.lower),
        (left.upper, right.upper),
    )
    lower_values = tuple(_lower_div(a, b) for a, b in quotients)
    upper_values = tuple(_upper_div(a, b) for a, b in quotients)
    return _interval(min(lower_values), max(upper_values))


def exact_interval(value: Decimal) -> IntervalDecimal:
    value = _as_decimal(value)
    if not value.is_finite():
        raise DecimalArithmeticError("nonfinite exact interval")
    return _interval(value, value)


def interval_contains(interval: IntervalDecimal, value: Decimal) -> bool:
    value = _as_decimal(value)
    return interval.lower <= value <= interval.upper


def _table_k(ntu: Decimal, section_count: int) -> Decimal:
    return decimal_subtract(
        Decimal("1"),
        decimal_exp(decimal_negate(decimal_divide(ntu, Decimal(section_count)))),
    )


def _p1(ntu: Decimal, ratio: Decimal) -> Decimal:
    k = _table_k(ntu, 2)
    a0 = decimal_subtract(k, Decimal("2"))
    a1 = k
    b0 = decimal_negate(decimal_subtract(k, Decimal("2")))
    e2 = decimal_exp(decimal_negate(decimal_multiply(decimal_multiply(Decimal("2"), ratio), k)))
    n = decimal_add(b0, decimal_multiply(a0, e2))
    d = decimal_add(b0, decimal_multiply(a1, e2))
    return decimal_divide(decimal_divide(n, d), ratio)


def _p2(ntu: Decimal, ratio: Decimal) -> Decimal:
    k = _table_k(ntu, 3)
    b1 = decimal_negate(decimal_multiply(k, decimal_subtract(k, Decimal("4"))))
    b2 = decimal_multiply(
        decimal_multiply(Decimal("2"), decimal_power_int(k, 2)),
        decimal_subtract(k, Decimal("2")),
    )
    a0 = decimal_add(b1, decimal_multiply(b2, ratio))
    a1 = Decimal("-4")
    b0 = decimal_power_int(decimal_subtract(k, Decimal("2")), 2)
    e3 = decimal_exp(decimal_negate(decimal_multiply(decimal_multiply(Decimal("3"), ratio), k)))
    e2 = decimal_exp(decimal_negate(decimal_multiply(decimal_multiply(Decimal("2"), ratio), k)))
    n = decimal_add(b0, decimal_add(decimal_multiply(a1, e3), decimal_multiply(a0, e2)))
    d = decimal_add(b0, decimal_multiply(a0, e2))
    return decimal_divide(decimal_divide(n, d), ratio)


def _p3(ntu: Decimal, ratio: Decimal) -> Decimal:
    k = _table_k(ntu, 4)
    b1 = decimal_multiply(decimal_multiply(Decimal("4"), k), decimal_subtract(k, Decimal("2")))
    b2 = decimal_multiply(
        decimal_multiply(Decimal("4"), decimal_power_int(k, 2)),
        decimal_power_int(decimal_subtract(k, Decimal("2")), 2),
    )
    a0 = decimal_add(b1, decimal_multiply(b2, ratio))
    a1 = decimal_negate(
        decimal_multiply(
            decimal_subtract(k, Decimal("2")), decimal_add(decimal_power_int(k, 2), Decimal("4"))
        )
    )
    a2 = decimal_negate(
        decimal_multiply(
            k,
            decimal_add(
                decimal_subtract(decimal_power_int(k, 2), decimal_multiply(Decimal("2"), k)),
                Decimal("4"),
            ),
        )
    )
    b0 = decimal_power_int(decimal_subtract(k, Decimal("2")), 3)
    e2 = decimal_exp(decimal_negate(decimal_multiply(decimal_multiply(Decimal("2"), ratio), k)))
    e4 = decimal_exp(decimal_negate(decimal_multiply(decimal_multiply(Decimal("4"), ratio), k)))
    n = decimal_add(b0, decimal_add(decimal_multiply(a0, e2), decimal_multiply(a1, e4)))
    d = decimal_add(b0, decimal_add(decimal_multiply(a2, e4), decimal_multiply(a0, e2)))
    return decimal_divide(decimal_divide(n, d), ratio)


def _p4(ntu: Decimal, ratio: Decimal) -> Decimal:
    k = _table_k(ntu, 5)
    a0 = decimal_add(
        decimal_multiply(
            k,
            decimal_multiply(
                decimal_add(k, Decimal("4")),
                decimal_power_int(decimal_subtract(k, Decimal("2")), 2),
            ),
        ),
        decimal_multiply(
            decimal_multiply(Decimal("6"), decimal_power_int(k, 2)),
            decimal_power_int(decimal_subtract(k, Decimal("2")), 3),
        ),
    )
    a1 = decimal_add(
        decimal_negate(
            decimal_multiply(
                decimal_multiply(Decimal("2"), k),
                decimal_add(
                    decimal_subtract(
                        decimal_power_int(k, 3),
                        decimal_multiply(Decimal("4"), decimal_power_int(k, 2)),
                    ),
                    decimal_add(decimal_multiply(Decimal("6"), k), Decimal("-8")),
                ),
            )
        ),
        decimal_add(
            decimal_multiply(
                decimal_multiply(Decimal("4"), decimal_power_int(k, 2)),
                decimal_multiply(
                    decimal_subtract(k, Decimal("2")),
                    decimal_add(decimal_subtract(decimal_power_int(k, 2), k), Decimal("2")),
                ),
            ),
            decimal_multiply(
                decimal_multiply(Decimal("2"), decimal_power_int(k, 4)),
                decimal_power_int(decimal_subtract(k, Decimal("2")), 2),
            ),
        ),
    )
    a2 = Decimal("-16")
    b0 = decimal_power_int(decimal_subtract(k, Decimal("2")), 4)
    e2 = decimal_exp(decimal_negate(decimal_multiply(decimal_multiply(Decimal("2"), ratio), k)))
    e4 = decimal_exp(decimal_negate(decimal_multiply(decimal_multiply(Decimal("4"), ratio), k)))
    e5 = decimal_exp(decimal_negate(decimal_multiply(decimal_multiply(Decimal("5"), ratio), k)))
    n = decimal_add(
        b0,
        decimal_add(
            decimal_multiply(a2, e5),
            decimal_add(decimal_multiply(a0, e2), decimal_multiply(a1, e4)),
        ),
    )
    d = decimal_add(b0, decimal_add(decimal_multiply(a0, e2), decimal_multiply(a1, e4)))
    return decimal_divide(decimal_divide(n, d), ratio)


def _p5(ntu: Decimal, ratio: Decimal) -> Decimal:
    k = _table_k(ntu, 6)
    km2 = decimal_subtract(k, Decimal("2"))
    b1 = decimal_multiply(
        decimal_multiply(Decimal("2"), k),
        decimal_multiply(decimal_add(k, Decimal("2")), decimal_power_int(km2, 3)),
    )
    b2 = decimal_multiply(
        decimal_multiply(Decimal("8"), decimal_power_int(k, 2)), decimal_power_int(km2, 4)
    )
    a0 = decimal_add(b1, decimal_multiply(b2, ratio))
    a1 = decimal_add(
        decimal_negate(
            decimal_multiply(
                decimal_multiply(k, km2),
                decimal_add(
                    decimal_subtract(
                        decimal_power_int(k, 3),
                        decimal_multiply(Decimal("8"), decimal_power_int(k, 2)),
                    ),
                    decimal_add(decimal_multiply(Decimal("8"), k), Decimal("-16")),
                ),
            )
        ),
        decimal_add(
            decimal_multiply(
                decimal_multiply(Decimal("4"), decimal_power_int(k, 2)),
                decimal_multiply(
                    decimal_power_int(km2, 2),
                    decimal_add(
                        decimal_add(
                            decimal_multiply(Decimal("3"), decimal_power_int(k, 2)),
                            decimal_multiply(Decimal("-2"), k),
                        ),
                        Decimal("4"),
                    ),
                ),
            ),
            decimal_multiply(
                decimal_multiply(Decimal("8"), decimal_power_int(k, 4)), decimal_power_int(km2, 3)
            ),
        ),
    )
    a2 = decimal_negate(
        decimal_multiply(
            decimal_multiply(Decimal("2"), km2),
            decimal_add(
                decimal_add(
                    decimal_subtract(
                        decimal_power_int(k, 4),
                        decimal_multiply(Decimal("2"), decimal_power_int(k, 3)),
                    ),
                    decimal_multiply(Decimal("4"), decimal_power_int(k, 2)),
                ),
                Decimal("8"),
            ),
        )
    )
    a3 = decimal_negate(
        decimal_multiply(
            decimal_multiply(Decimal("2"), k),
            decimal_add(
                decimal_add(
                    decimal_subtract(
                        decimal_power_int(k, 4),
                        decimal_multiply(Decimal("4"), decimal_power_int(k, 3)),
                    ),
                    decimal_multiply(Decimal("8"), decimal_power_int(k, 2)),
                ),
                decimal_add(decimal_multiply(Decimal("-8"), k), Decimal("8")),
            ),
        )
    )
    b0 = decimal_power_int(km2, 5)
    e2 = decimal_exp(decimal_negate(decimal_multiply(decimal_multiply(Decimal("2"), ratio), k)))
    e4 = decimal_exp(decimal_negate(decimal_multiply(decimal_multiply(Decimal("4"), ratio), k)))
    e6 = decimal_exp(decimal_negate(decimal_multiply(decimal_multiply(Decimal("6"), ratio), k)))
    n = decimal_add(
        b0,
        decimal_add(
            decimal_multiply(a0, e2),
            decimal_add(decimal_multiply(a1, e4), decimal_multiply(a2, e6)),
        ),
    )
    d = decimal_add(
        b0,
        decimal_add(
            decimal_multiply(a0, e2),
            decimal_add(decimal_multiply(a1, e4), decimal_multiply(a3, e6)),
        ),
    )
    return decimal_divide(decimal_divide(n, d), ratio)


def table7_relation(ntu: Decimal, ratio: Decimal, baffle_count: int) -> Decimal:
    """Select exactly one source relation; invalid selectors fail closed."""

    ntu = _as_decimal(ntu)
    ratio = _as_decimal(ratio)
    if type(baffle_count) is not int or not 1 <= baffle_count <= 5:
        raise ValueError("unsupported baffle count")
    if not ntu.is_finite() or ntu < 0 or not ratio.is_finite() or ratio <= 0:
        raise ValueError("invalid Table 7 domain")
    if baffle_count == 1:
        return _p1(ntu, ratio)
    if baffle_count == 2:
        return _p2(ntu, ratio)
    if baffle_count == 3:
        return _p3(ntu, ratio)
    if baffle_count == 4:
        return _p4(ntu, ratio)
    if baffle_count == 5:
        return _p5(ntu, ratio)
    raise ValueError("unreachable baffle selector")
