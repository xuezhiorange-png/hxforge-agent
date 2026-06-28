"""TASK-009 quantum string canonicalisation — isolated to break circular import."""

from __future__ import annotations

from decimal import Decimal

from hexagent.optimization.errors import InvalidLengthQuantum


def canonicalize_length_quantum(length_quantum_m: str) -> str:
    """Validate and canonicalise a power-of-10 quantum string.

    Equivalent inputs (``"0.001"``, ``"0.0010"``, ``"1E-3"``) all
    produce ``"0.001"``.
    """
    try:
        quantum = Decimal(length_quantum_m)
    except Exception as exc:
        raise InvalidLengthQuantum(length_quantum_m, detail=str(exc)) from exc

    if not quantum.is_finite():
        raise InvalidLengthQuantum(length_quantum_m, detail="quantum must be finite")
    if quantum <= 0:
        raise InvalidLengthQuantum(length_quantum_m, detail="quantum must be positive")

    norm = quantum.normalize()
    digit_tuple = norm.as_tuple().digits
    exponent = norm.as_tuple().exponent

    if isinstance(exponent, int):
        exp: int = exponent
    else:
        raise InvalidLengthQuantum(
            length_quantum_m,
            detail=f"non-integer exponent from finite value: {exponent!r}",
        )
    if len(digit_tuple) != 1 or digit_tuple[0] != 1 or exp > 0:
        raise InvalidLengthQuantum(
            length_quantum_m,
            detail=(f"not a power of 10 (digits={digit_tuple}, exponent={exponent})"),
        )

    return str(norm)
