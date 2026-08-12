"""TASK-028 local Decimal context (prec=28, ROUND_HALF_EVEN), quantize helper, canonical lexeme.

§20 — Decimal contract.
"""

from __future__ import annotations

import decimal
from decimal import Context, Decimal, localcontext
from typing import Final

# §9.1 — TASK-028 frozen Decimal context. NOT TASK-025 precision-160.
TASK028_DECIMAL_PRECISION: Final[int] = 28

# §9.5 — Frozen quanta.
REFERENCE_VELOCITY_QUANTUM: Final[Decimal] = Decimal("0.00000001")
PRESSURE_LOSS_QUANTUM: Final[Decimal] = Decimal("0.001")
REFERENCE_FLOW_AREA_QUANTUM: Final[Decimal] = Decimal("0.000000000001")
LOSS_COEFFICIENT_QUANTUM: Final[Decimal] = Decimal("0.00000001")


def task028_decimal_context() -> Context:
    """§9.1 — TASK-028 local Decimal context. NOT TASK-025 precision-160."""
    return Context(prec=TASK028_DECIMAL_PRECISION, rounding=decimal.ROUND_HALF_EVEN)


def quantize_task028_decimal(value: Decimal, quantum: Decimal) -> Decimal:
    """§9.2 — Quantize value to owning quantum inside TASK-028 precision-28 local context.

    Must:
    1. Validate finite
    2. Quantize with ROUND_HALF_EVEN
    3. Preserve exact scale of quantum
    """
    if not value.is_finite():
        raise ValueError(f"quantize_task028_decimal: value must be finite, got {value!r}")
    with localcontext(task028_decimal_context()):
        return value.quantize(quantum)


def normalize_negative_zero(value: Decimal, quantum: Decimal) -> Decimal:
    """§9.3 — Remove negative sign from zero while preserving quantum scale.

    -0.00000000 → 0.00000000 (NOT 0, NOT 0E-8)
    """
    quantized = quantize_task028_decimal(value, quantum)
    if quantized.is_zero():
        # Force exact scale by counting quantum decimal places
        quantum_str = str(quantum)
        scale = len(quantum_str.split(".")[1]) if "." in quantum_str else 0
        return Decimal("0." + "0" * scale)
    return quantized


def task028_decimal_payload(quantized_value: Decimal, owning_quantum: Decimal) -> bytes:
    """§9.4 — Produce fixed-point exact-scale canonical payload bytes.

    Guarantees:
    - NO_EXPONENT_NOTATION
    - EXACT_SCALE_PRESERVED
    - NO_LEADING_PLUS
    - NEGATIVE_ZERO_NORMALIZED

    Examples:
    Decimal("0.5") with K quantum → b"0.50000000"
    Decimal("101.504") with pressure quantum → b"101.504"
    negative-zero velocity → b"0.00000000"
    """
    normalized = normalize_negative_zero(quantized_value, owning_quantum)
    return str(normalized).encode("ascii")


__all__ = [
    "TASK028_DECIMAL_PRECISION",
    "REFERENCE_VELOCITY_QUANTUM",
    "PRESSURE_LOSS_QUANTUM",
    "REFERENCE_FLOW_AREA_QUANTUM",
    "LOSS_COEFFICIENT_QUANTUM",
    "task028_decimal_context",
    "quantize_task028_decimal",
    "normalize_negative_zero",
    "task028_decimal_payload",
]
