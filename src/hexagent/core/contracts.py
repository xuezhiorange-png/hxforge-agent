from __future__ import annotations

from typing import Protocol

from hexagent.domain.models import CalculationResult, DesignCase
from hexagent.properties.base import FluidState, PropertyProvider


class ExchangerService(Protocol):
    exchanger_type: str

    def size(self, case: DesignCase) -> CalculationResult:
        ...

    def rate(self, case: DesignCase, geometry: dict[str, float]) -> CalculationResult:
        ...


__all__ = ["ExchangerService", "FluidState", "PropertyProvider"]
