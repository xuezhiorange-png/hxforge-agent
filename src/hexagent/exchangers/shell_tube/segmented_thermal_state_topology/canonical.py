"""Semantic projections into the shared canonical JSON implementation."""

import re
from decimal import Decimal
from fractions import Fraction
from typing import Any

from hexagent.canonical_json import canonical_sha256

from .errors import Code, Failure
from .models import Model


def number(value: str) -> Fraction:
    if type(value) is not str or len(value) > 128 or not re.fullmatch(r"-?\d+(?:\.\d+)?", value):
        raise Failure(Code.RAW_BOUNDARY_INVALID, "decimal")
    return Fraction(Decimal(value))


def decimal_text(value: Fraction) -> str:
    """Exact terminating decimal, without ambient context or quantization."""
    denominator = value.denominator
    twos = fives = 0
    while denominator % 2 == 0:
        twos += 1
        denominator //= 2
    while denominator % 5 == 0:
        fives += 1
        denominator //= 5
    if denominator != 1:
        raise Failure(Code.RAW_BOUNDARY_INVALID, "nonterminating_decimal")
    places = max(twos, fives)
    integer = abs(value.numerator) * 2 ** (places - twos) * 5 ** (places - fives)
    digits = str(integer).zfill(places + 1)
    if places:
        digits = (digits[:-places] + "." + digits[-places:]).rstrip("0").rstrip(".")
    return ("-" if value < 0 else "") + digits


def projection(value: Model) -> dict[str, Any]:
    def normalize(item: Any, key: str = "") -> Any:
        if type(item) is dict:
            return {k: normalize(v, k) for k, v in item.items()}
        if type(item) is list:
            result = [normalize(v, key) for v in item]
            # All repeated records are sets; topology comes from explicit edges.
            return sorted(result, key=lambda v: canonical_sha256({"item": v}))
        if type(item) is str and key.endswith(("_m", "_m2", "_w", "_kg_s", "_j_kg")):
            return decimal_text(number(item))
        return item

    return normalize(value.model_dump(mode="json"))  # type: ignore[no-any-return]


def identity(value: Model) -> str:
    return canonical_sha256(projection(value))
