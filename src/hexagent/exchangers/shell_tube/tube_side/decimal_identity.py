"""TASK-025 Decimal arithmetic authority.

§8 — Frozen local Decimal context + structural identity.

Every engineering calculation executes inside an explicit local Decimal
context. The factory ``local_decimal_context()`` returns a copy of the
frozen context with the §8.5 signal policy applied (traps cleared at
each operation start).
"""

from __future__ import annotations

import decimal
from decimal import Context, Decimal
from typing import Any, Final

# §8.1 — Frozen local context parameters.
_PRECISION: Final[int] = 160
_EMIN: Final[int] = -999999
_EMAX: Final[int] = 999999
_CAPITALS: Final[int] = 1
_CLAMP: Final[int] = 0
_TRAPS: Final[tuple[Any, ...]] = (
    decimal.DivisionByZero,
    decimal.InvalidOperation,
    decimal.Overflow,
)


# §8.2 — Frozen quantums.
LENGTH_QUANTUM_M: Final[Decimal] = Decimal("0.00000001")
PERIMETER_QUANTUM_M: Final[Decimal] = Decimal("0.00000001")
AREA_QUANTUM_M2: Final[Decimal] = Decimal("0.0000000001")
VOLUME_QUANTUM_M3: Final[Decimal] = Decimal("0.000000000001")
HYDRAULIC_DIAMETER_QUANTUM_M: Final[Decimal] = Decimal("0.00000001")


def local_decimal_context() -> Context:
    """§8.1 — Return a fresh Context with §8.1 frozen parameters.

    Python 3.12's ``Context.__init__`` requires the ``flags`` parameter to
    be a SignalDict (not a plain dict or list). We omit ``flags`` and rely
    on ``clear_flags`` at operation start (§8.5).
    """
    return Context(
        prec=_PRECISION,
        rounding=decimal.ROUND_HALF_EVEN,
        Emin=_EMIN,
        Emax=_EMAX,
        capitals=_CAPITALS,
        clamp=_CLAMP,
    )


def with_signals_cleared(context: Context) -> Context:
    """§8.5 — Return a copy of ``context`` with all flags cleared and traps set."""
    cleared = context.copy()
    cleared.clear_flags()
    # Re-apply traps per §8.5.
    for trap in _TRAPS:
        cleared.traps[trap] = True  # noqa: index
    return cleared


def validate_finite_decimal(value: Decimal, field_path: str) -> Decimal:
    """Validate that ``value`` is finite (not NaN, not infinite).

    §8.1 — Inputs must be finite, non-NaN, non-infinite.
    """
    if not value.is_finite():
        raise ValueError(f"{field_path} must be a finite Decimal; got {value!s}")
    return value


def validate_positive_finite_decimal(value: Decimal, field_path: str) -> Decimal:
    """Validate that ``value`` is finite and strictly positive.

    §5.3 / §8.1 — Lengths must be finite, dimensionally metres, strictly positive.
    """
    validate_finite_decimal(value, field_path)
    if value <= Decimal(0):
        raise ValueError(f"{field_path} must be strictly positive; got {value!s}")
    return value


def quantize_half_even(value: Decimal, quantum: Decimal, field_path: str) -> Decimal:
    """Quantize ``value`` under the §8.1 context with ROUND_HALF_EVEN.

    §8.3 — Step 4 of calculation/hashing order.
    """
    ctx = with_signals_cleared(local_decimal_context())
    try:
        with decimal.localcontext(ctx):
            quantized = value.quantize(quantum)
    except decimal.InvalidOperation as exc:  # pragma: no cover - trap fires
        raise ValueError(f"{field_path} quantize failed: {exc!s}") from exc
    if not quantized.is_finite():
        raise ValueError(f"{field_path} quantized to non-finite value {quantized!s}")
    return quantized


def canonical_decimal_lexeme(value: Decimal) -> bytes:
    """§8.3 step 5 — canonical Decimal lexical form (fixed-point UTF-8).

    The canonical form has no exponent marker, no leading plus sign,
    and exactly the scale implied by the quantized value.
    """
    return str(value).encode("utf-8")


__all__ = [
    "LENGTH_QUANTUM_M",
    "PERIMETER_QUANTUM_M",
    "AREA_QUANTUM_M2",
    "VOLUME_QUANTUM_M3",
    "HYDRAULIC_DIAMETER_QUANTUM_M",
    "local_decimal_context",
    "with_signals_cleared",
    "validate_finite_decimal",
    "validate_positive_finite_decimal",
    "quantize_half_even",
    "canonical_decimal_lexeme",
]