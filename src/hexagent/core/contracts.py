from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from hexagent.domain.models import CalculationResult, DesignCase


@dataclass(frozen=True)
class FluidState:
    temperature_k: float
    pressure_pa: float
    density_kg_m3: float
    cp_j_kg_k: float
    viscosity_pa_s: float
    conductivity_w_m_k: float
    enthalpy_j_kg: float
    phase: str


class PropertyProvider(Protocol):
    name: str
    version: str

    def state_tp(self, fluid_name: str, temperature_k: float, pressure_pa: float) -> FluidState:
        ...


class ExchangerService(Protocol):
    exchanger_type: str

    def size(self, case: DesignCase) -> CalculationResult:
        ...

    def rate(self, case: DesignCase, geometry: dict[str, float]) -> CalculationResult:
        ...
