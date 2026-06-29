"""TASK-010 canonical scalar/quantity serialization for API request payloads.

Provides deterministic string representations of Decimal scalars and
recursive canonicalization of arbitrary API request objects.  All
numerical values are serialized as strings so that JSON round-trips
are lossless and content hashes are stable.
"""

from __future__ import annotations

import math
from decimal import ROUND_HALF_EVEN, Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from hexagent.core.canonical import sha256_digest
from hexagent.domain.quantities import Quantity

# ---------------------------------------------------------------------------
# canonical_decimal_string
# ---------------------------------------------------------------------------


def canonical_decimal_string(value: Decimal) -> str:
    """Produce a canonical string representation of a ``Decimal``.

    Rules:
    * Exactly **15 significant digits** after rounding with
      ``ROUND_HALF_EVEN`` (banker's rounding).
    * Trailing zeros are stripped via ``Decimal.normalize()``.
    * Non-finite values (``NaN``, ``Infinity``) are rejected.
    * Negative zero (``-0``) is rejected.

    Test vectors (all must pass):
    >>> canonical_decimal_string(Decimal('0'))
    '0'
    >>> canonical_decimal_string(Decimal('1'))
    '1'
    >>> canonical_decimal_string(Decimal('1.0'))
    '1'
    >>> canonical_decimal_string(Decimal('1.5000'))
    '1.5'
    >>> canonical_decimal_string(Decimal('1.234567890123445'))
    '1.23456789012344'
    >>> canonical_decimal_string(Decimal('1.234567890123455'))
    '1.23456789012346'
    >>> canonical_decimal_string(Decimal('999999999999999.5'))
    '1E+15'
    >>> canonical_decimal_string(Decimal('1E-30'))
    '1E-30'
    >>> canonical_decimal_string(Decimal('1E+30'))
    '1E+30'
    >>> canonical_decimal_string(Decimal('0.00000000001'))
    '1E-11'
    >>> canonical_decimal_string(Decimal('0.000000000001'))
    '1E-12'
    >>> canonical_decimal_string(Decimal('99999999999'))
    '99999999999'
    >>> canonical_decimal_string(Decimal('100000000000'))
    '1E+11'
    """
    if not isinstance(value, Decimal):
        raise TypeError(f"Expected Decimal, got {type(value).__name__}")

    # Reject non-finite
    if not value.is_finite():
        raise ValueError(f"Non-finite Decimal {value!r} cannot be canonicalized")

    # Reject negative zero
    if value.is_zero() and value.is_signed():
        raise ValueError("Negative zero is not allowed in canonical form")

    # Zero is always '0'
    if value.is_zero():
        return "0"

    # Determine how many significant digits the input carries.
    # Decimal.as_tuple() returns DecimalTuple(sign, digits, exponent).
    _sign, digits, exponent = value.as_tuple()
    if not isinstance(exponent, int):
        raise ValueError(f"non-finite decimal: {value}")
    num_sig = len(digits)

    if num_sig > 15:
        # Round to 15 significant digits.
        # The target quantize exponent places the last significant digit
        # at the 15th position:  target_exp = exponent + num_sig - 15
        target_exp = exponent + num_sig - 15
        quantize_ref = Decimal(1).scaleb(target_exp)
        value = value.quantize(quantize_ref, rounding=ROUND_HALF_EVEN)

    # normalize() strips trailing zeros and applies the canonical
    # E-notation threshold used by Python's Decimal (>= 1E+11 or <= 1E-11).
    return str(value.normalize())


# ---------------------------------------------------------------------------
# canonical_quantity_payload
# ---------------------------------------------------------------------------


def canonical_quantity_payload(q: Quantity) -> dict[str, str]:
    """Convert a ``Quantity`` to its canonical API dict representation.

    The value is first converted to SI units so that equivalent physical
    quantities (e.g. 100 °C and 373.15 K) produce identical payloads.
    The SI value is then rendered via :func:`canonical_decimal_string`.

    Returns a dict with ``"si_value"`` and ``"kind"`` keys, both strings.
    """
    si_q = q.to_si()
    kind = si_q.kind
    return {
        "si_value": canonical_decimal_string(Decimal(str(si_q.value))),
        "kind": kind.value if kind is not None else "",
    }


# ---------------------------------------------------------------------------
# canonicalize_api_payload — recursive canonicalization
# ---------------------------------------------------------------------------


def canonicalize_api_payload(obj: Any) -> Any:
    """Recursively canonicalize *obj* for deterministic API serialization.

    Contract rules:

    * ``Decimal`` / ``float`` → string via :func:`canonical_decimal_string`
    * ``int`` → JSON number (pass-through)
    * ``bool`` → JSON boolean (pass-through; checked **before** ``int``
      because ``bool`` is a subclass of ``int``)
    * ``None`` → JSON null (pass-through)
    * ``Enum`` → canonicalized ``.value``
    * ``UUID`` → string
    * ``Quantity`` (or duck-typed equivalent) → canonical dict via
      :func:`canonical_quantity_payload`
    * ``dict`` → sorted keys, recursively canonicalized values
    * ``tuple`` / ``list`` → JSON array, recursively canonicalized elements
    * ``str`` → pass-through
    """
    # Decimal → canonical string
    if isinstance(obj, Decimal):
        return canonical_decimal_string(obj)

    # float → canonical string (via Decimal for exact rounding)
    if isinstance(obj, float):
        if not math.isfinite(obj):
            raise ValueError(f"Non-finite float {obj!r} cannot be canonicalized")
        # Use repr() to preserve the exact binary value through the
        # Decimal constructor, then apply canonical formatting.
        return canonical_decimal_string(Decimal(repr(obj)))

    # bool — MUST be checked before int (bool is a subclass of int)
    if isinstance(obj, bool):
        return obj

    # int → pass-through (JSON number)
    if isinstance(obj, int):
        return obj

    # None → null
    if obj is None:
        return None

    # Enum → canonicalize the .value
    if isinstance(obj, Enum):
        return canonicalize_api_payload(obj.value)

    # UUID → string
    if isinstance(obj, UUID):
        return str(obj)

    # Quantity → canonical dict (duck-typed check)
    if _is_quantity(obj):
        return canonical_quantity_payload(obj)

    # dict → sorted keys, recursively canonicalized values
    if isinstance(obj, dict):
        return {
            k: canonicalize_api_payload(v) for k, v in sorted(obj.items(), key=lambda kv: kv[0])
        }

    # tuple / list → array, recursively canonicalized elements
    if isinstance(obj, (tuple, list)):
        return [canonicalize_api_payload(item) for item in obj]

    # str → pass-through
    if isinstance(obj, str):
        return obj

    raise TypeError(f"Cannot canonicalize object of type {type(obj).__name__}")


def _is_quantity(obj: Any) -> bool:
    """Return ``True`` if *obj* is a Quantity-like object."""
    return isinstance(obj, Quantity) or (
        hasattr(obj, "value")
        and hasattr(obj, "unit")
        and hasattr(obj, "kind")
        and hasattr(obj, "to_si")
    )


# ---------------------------------------------------------------------------
# compute_api_request_digest
# ---------------------------------------------------------------------------


def compute_api_request_digest(obj: Any) -> str:
    """Return a SHA-256 content hash of *obj* after canonicalization.

    ``obj`` is first canonicalized via :func:`canonicalize_api_payload`,
    then serialized to canonical JSON and hashed with
    :func:`~hexagent.core.canonical.sha256_digest`.

    The return value is always ``"sha256:<64-char lowercase hex>"``.
    """
    canonical = canonicalize_api_payload(obj)
    return sha256_digest(canonical)


__all__ = [
    "canonical_decimal_string",
    "canonical_quantity_payload",
    "canonicalize_api_payload",
    "compute_api_request_digest",
]
