from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, TypeAlias

from hexagent.properties.errors import PropertyErrorCode, PropertyServiceError


class PropertyQueryType(StrEnum):
    TP = "TP"
    PH = "PH"
    SATURATION_P = "SATURATION_P"
    SATURATION_T = "SATURATION_T"


class PhaseRegion(StrEnum):
    LIQUID = "liquid"
    GAS = "gas"
    SUPERCRITICAL = "supercritical"
    SUPERCRITICAL_GAS = "supercritical_gas"
    SUPERCRITICAL_LIQUID = "supercritical_liquid"
    SATURATED_LIQUID = "saturated_liquid"
    SATURATED_VAPOR = "saturated_vapor"
    UNKNOWN = "unknown"


class FluidValidationLevel(StrEnum):
    TIER_1_VALIDATED = "tier_1_validated"
    UNVALIDATED = "unvalidated"


@dataclass(frozen=True)
class FluidIdentifier:
    """Deterministic CoolProp fluid identifier.

    `components` is a tuple of `(name, mole_fraction)` values. Components are
    sorted when serialized so equivalent mappings produce one cache identity.
    """

    name: str
    backend: str = "HEOS"
    components: tuple[tuple[str, float], ...] = ()

    def __post_init__(self) -> None:
        if not self.name.strip() and not self.components:
            raise PropertyServiceError(
                PropertyErrorCode.INVALID_FLUID,
                "A fluid name or component list is required.",
            )
        if not self.backend.strip():
            raise PropertyServiceError(
                PropertyErrorCode.UNSUPPORTED_BACKEND,
                "A CoolProp backend name is required.",
            )
        if self.components:
            names: set[str] = set()
            total = 0.0
            for component, fraction in self.components:
                if not component.strip() or component in names:
                    raise PropertyServiceError(
                        PropertyErrorCode.INVALID_FLUID,
                        "Mixture component names must be non-empty and unique.",
                        context={"component": component},
                    )
                if not math.isfinite(fraction) or fraction <= 0.0:
                    raise PropertyServiceError(
                        PropertyErrorCode.INVALID_FLUID,
                        "Mixture mole fractions must be finite and positive.",
                        context={"component": component, "fraction": fraction},
                    )
                names.add(component)
                total += fraction
            if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=1e-10):
                raise PropertyServiceError(
                    PropertyErrorCode.INVALID_FLUID,
                    "Mixture mole fractions must sum to 1.0.",
                    context={"fraction_sum": total},
                )

    @classmethod
    def from_value(cls, value: FluidIdentifier | str) -> FluidIdentifier:
        if isinstance(value, cls):
            return value
        return cls(name=value)

    @classmethod
    def from_components(
        cls,
        components: Mapping[str, float],
        *,
        backend: str = "HEOS",
        name: str = "custom_mixture",
    ) -> FluidIdentifier:
        return cls(
            name=name,
            backend=backend,
            components=tuple(sorted(components.items())),
        )

    @property
    def canonical_components(self) -> tuple[tuple[str, float], ...]:
        return tuple(sorted(self.components))

    @property
    def coolprop_fluid(self) -> str:
        if self.components:
            mixture = "&".join(
                f"{component}[{fraction:.16g}]"
                for component, fraction in self.canonical_components
            )
            return f"{self.backend}::{mixture}"
        return f"{self.backend}::{self.name}"

    @property
    def cache_identity(self) -> str:
        return self.coolprop_fluid


@dataclass(frozen=True)
class PropertyProvenance:
    backend_name: str
    backend_version: str
    backend_git_revision: str
    fluid_identifier: str
    validation_level: FluidValidationLevel
    query_type: PropertyQueryType
    inputs: tuple[tuple[str, float], ...]
    cache_policy_version: str


@dataclass(frozen=True)
class FluidState:
    temperature_k: float
    pressure_pa: float
    density_kg_m3: float
    cp_j_kg_k: float
    viscosity_pa_s: float
    conductivity_w_m_k: float
    enthalpy_j_kg: float
    entropy_j_kg_k: float
    phase: PhaseRegion
    quality: float | None
    provenance: PropertyProvenance


@dataclass(frozen=True)
class SaturationState:
    query_type: PropertyQueryType
    input_value: float
    liquid: FluidState
    vapor: FluidState
    provenance: PropertyProvenance


PropertyResult: TypeAlias = FluidState | SaturationState


@dataclass(frozen=True)
class PropertyCacheKey:
    backend_name: str
    backend_version: str
    backend_git_revision: str
    fluid_identifier: str
    query_type: PropertyQueryType
    inputs: tuple[tuple[str, float], ...]
    configuration: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class PropertyCacheInfo:
    hits: int
    misses: int
    size: int
    max_size: int


class PropertyProvider(Protocol):
    name: str
    version: str
    git_revision: str

    def state_tp(
        self,
        fluid: FluidIdentifier | str,
        temperature_k: float,
        pressure_pa: float,
    ) -> FluidState: ...

    def state_ph(
        self,
        fluid: FluidIdentifier | str,
        pressure_pa: float,
        enthalpy_j_kg: float,
    ) -> FluidState: ...

    def saturation_at_pressure(
        self,
        fluid: FluidIdentifier | str,
        pressure_pa: float,
    ) -> SaturationState: ...

    def saturation_at_temperature(
        self,
        fluid: FluidIdentifier | str,
        temperature_k: float,
    ) -> SaturationState: ...

    def cache_info(self) -> PropertyCacheInfo: ...

    def clear_cache(self) -> None: ...
