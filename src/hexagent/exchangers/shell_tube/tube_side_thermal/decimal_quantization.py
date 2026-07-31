"""TASK-026 S12 quantization.

R8 implementation. Stage S12 is the **only** stage permitted to apply
quantum downshift (R6-R7 §7.2). The 5-field quantization map is
verbatim-frozen:

  bulk_velocity_m_s                     Decimal("0.0000001")
  reynolds_number                       Decimal("0.0001")
  prandtl_number                        Decimal("0.0001")
  nusselt_number                        Decimal("0.0001")
  tube_side_heat_transfer_coefficient_w_m2_k  Decimal("0.000001")

Rounding mode is ROUND_HALF_EVEN. The policy is
FIXED_ABSOLUTE_QUANTUM_1E_MINUS_6 (R6-R7 §7.3).
"""

from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal
from typing import Final

# R6-R7 §7.2 — 5-field quantization map (frozen order).
QUANTIZATION_MAP: Final[tuple[tuple[str, Decimal], ...]] = (
    ("bulk_velocity_m_s", Decimal("0.0000001")),
    ("reynolds_number", Decimal("0.0001")),
    ("prandtl_number", Decimal("0.0001")),
    ("nusselt_number", Decimal("0.0001")),
    ("tube_side_heat_transfer_coefficient_w_m2_k", Decimal("0.000001")),
)

QUANTIZATION_FIELD_COUNT: Final[int] = 5
QUANTIZATION_STAGE: Final[str] = "S12"
ROUNDING_MODE: Final[str] = "ROUND_HALF_EVEN"
HI_QUANTUM_POLICY: Final[str] = "FIXED_ABSOLUTE_QUANTUM_1E_MINUS_6"


def quantize_half_even(value: Decimal, quantum: Decimal) -> Decimal:
    """R6-R7 §7.2 — Apply a quantum downshift with ROUND_HALF_EVEN."""
    if not isinstance(value, Decimal):
        raise ValueError("quantize_half_even input must be Decimal")
    if not isinstance(quantum, Decimal):
        raise ValueError("quantum must be Decimal")
    if quantum <= Decimal(0):
        raise ValueError(f"quantum must be strictly positive; got {quantum!s}")
    return value.quantize(quantum, rounding=ROUND_HALF_EVEN)


def field_for(name: str) -> Decimal:
    """Return the canonical quantum for a single field name."""
    for fname, q in QUANTIZATION_MAP:
        if fname == name:
            return q
    raise ValueError(f"unknown quantization field: {name!r}")


__all__ = [
    "QUANTIZATION_MAP",
    "QUANTIZATION_FIELD_COUNT",
    "QUANTIZATION_STAGE",
    "ROUNDING_MODE",
    "HI_QUANTUM_POLICY",
    "quantize_half_even",
    "field_for",
]
