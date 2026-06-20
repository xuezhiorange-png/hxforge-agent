from __future__ import annotations

from functools import lru_cache
from typing import Any

from pint import UnitRegistry

from hexagent.domain.models import Quantity


@lru_cache(maxsize=1)
def unit_registry() -> UnitRegistry[Any]:
    registry: UnitRegistry[Any] = UnitRegistry(autoconvert_offset_to_baseunit=True)
    return registry


def to_si(quantity: Quantity, target_unit: str) -> float:
    q = quantity.value * unit_registry()(quantity.unit)
    return float(q.to(target_unit).magnitude)
