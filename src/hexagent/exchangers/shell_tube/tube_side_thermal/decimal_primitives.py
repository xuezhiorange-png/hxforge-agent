"""TASK-026 Decimal primitives.

R8 implementation. All intermediate Decimal computation runs in a 200
working-precision context with 40 guard digits per R6-R7 §7.1. The
three helpers (decimal_ln, decimal_sqrt, decimal_pow_2_3) are
Decimal-only; math.log / math.sqrt / float fractional powers are
forbidden (R6-R7 §5.2.1).

The 9 golden vectors from R4 §10.6.1 (R6-R7 §7.4) are pinned: each
helper's output for the canonical input lexeme must encode to the
exact 64-hex SHA-256 frozen in the contract.

Any Decimal exception (Overflow, DivisionByZero, InvalidOperation,
or working-context Clamped/Inexact/Rounded signal raised as exception)
is converted to a typed BL_DECIMAL_FAILURE outcome; the helper does
not raise a bare Decimal exception to the caller.
"""

from __future__ import annotations

import decimal as _decimal
from decimal import Context, Decimal, DivisionByZero, InvalidOperation, Overflow
from typing import Final

# Working precision is 200 with 40 guard digits (R6-R7 §7.1).
# Nominal precision is 160 (handoff fingerprint - P1 contract).
NOMINAL_DECIMAL_PRECISION: Final[int] = 160
WORKING_DECIMAL_PRECISION: Final[int] = 200
WORKING_GUARD_DIGITS: Final[int] = 40

# 9 golden vectors (R6-R7 §7.4). Name = (operation, input_lexeme).
GOLDEN_VECTORS: Final[tuple[tuple[str, str], ...]] = (
    ("ln", "1"),
    ("ln", "2"),
    ("ln", "10"),
    ("sqrt", "0"),
    ("sqrt", "2"),
    ("pow_2_3", "1"),
    ("pow_2_3", "8"),
    ("pow_2_3", "27"),
    ("pow_2_3", "0.125"),
)


def task026_decimal_context_200() -> Context:
    """R6-R7 §7.1 — Working-precision context (prec=200, ROUND_HALF_EVEN).

    The 40 guard digits are absorbed by prec=200 itself; the nominal
    160 precision is the project's bound for hand-formatting (see
    P1 contract). The task026 request validation uses prec=160.
    """
    return Context(
        prec=WORKING_DECIMAL_PRECISION,
        rounding=_decimal.ROUND_HALF_EVEN,
        Emin=-999999,
        Emax=999999,
        capitals=1,
        clamp=0,
    )


def task026_decimal_context_160() -> Context:
    """R6-R7 §7.1 — Nominal-precision context (prec=160, ROUND_HALF_EVEN)."""
    return Context(
        prec=NOMINAL_DECIMAL_PRECISION,
        rounding=_decimal.ROUND_HALF_EVEN,
        Emin=-999999,
        Emax=999999,
        capitals=1,
        clamp=0,
    )


class DecimalFailure(Exception):
    """R6-R7 §6.3 — Out-of-band wrapper for BL_DECIMAL_FAILURE outcomes.

    The stage_pipeline catches this and emits a typed blocker entry;
    nothing higher in the call stack may see a bare Decimal exception.
    """

    def __init__(self, operation: str, lexeme: str, reason: str) -> None:
        super().__init__(f"BL_DECIMAL_FAILURE op={operation} lexeme={lexeme} reason={reason}")
        self.operation = operation
        self.lexeme = lexeme
        self.reason = reason


def _raise_decimal_failure(operation: str, lexeme: str, reason: str) -> None:
    raise DecimalFailure(operation, lexeme, reason)


def decimal_ln(value: Decimal) -> Decimal:
    """R6-R7 §5.2 — Decimal-only natural log, working-precision context.

    Uses the .ln() method (not math.log) inside a 200-precision context.
    Raises DecimalFailure on any Decimal infrastructure error.
    """
    if not isinstance(value, Decimal):
        _raise_decimal_failure("ln", str(value), "input_not_decimal")
    if value <= Decimal(0):
        _raise_decimal_failure("ln", str(value), "input_non_positive")
    with _decimal.localcontext(task026_decimal_context_200()):
        try:
            return value.ln()
        except (InvalidOperation, DivisionByZero, Overflow) as exc:
            _raise_decimal_failure("ln", str(value), type(exc).__name__)
    raise DecimalFailure("ln", str(value), "unreachable")


def decimal_sqrt(value: Decimal) -> Decimal:
    """R6-R7 §5.2 — Decimal-only square root, working-precision context.

    Uses the .sqrt() method (not math.sqrt) inside a 200-precision context.
    Raises DecimalFailure on any Decimal infrastructure error.
    """
    if not isinstance(value, Decimal):
        _raise_decimal_failure("sqrt", str(value), "input_not_decimal")
    if value < Decimal(0):
        _raise_decimal_failure("sqrt", str(value), "input_negative")
    with _decimal.localcontext(task026_decimal_context_200()):
        try:
            return value.sqrt()
        except (InvalidOperation, DivisionByZero, Overflow) as exc:
            _raise_decimal_failure("sqrt", str(value), type(exc).__name__)
    raise DecimalFailure("sqrt", str(value), "unreachable")


def decimal_pow_2_3(value: Decimal) -> Decimal:
    """R6-R7 §5.2 — Decimal-only 2/3 fractional power.

    Computed as exp((2/3) * ln(value)) using the working-precision
    helpers. math.pow / float exponentiation is forbidden. Raises
    DecimalFailure on negative input or any Decimal infrastructure error.
    """
    if not isinstance(value, Decimal):
        _raise_decimal_failure("pow_2_3", str(value), "input_not_decimal")
    if value < Decimal(0):
        _raise_decimal_failure("pow_2_3", str(value), "input_negative")
    with _decimal.localcontext(task026_decimal_context_200()):
        try:
            log_val = value.ln()
            two_thirds = Decimal(2) / Decimal(3)
            return (two_thirds * log_val).exp()
        except (InvalidOperation, DivisionByZero, Overflow) as exc:
            _raise_decimal_failure("pow_2_3", str(value), type(exc).__name__)
    raise DecimalFailure("pow_2_3", str(value), "unreachable")


__all__ = [
    "NOMINAL_DECIMAL_PRECISION",
    "WORKING_DECIMAL_PRECISION",
    "WORKING_GUARD_DIGITS",
    "GOLDEN_VECTORS",
    "task026_decimal_context_200",
    "task026_decimal_context_160",
    "DecimalFailure",
    "decimal_ln",
    "decimal_sqrt",
    "decimal_pow_2_3",
]
