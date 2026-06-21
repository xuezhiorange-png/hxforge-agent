"""Property-service domain models and provider protocol.

v0.1 reference-state policy: ``DEF`` (CoolProp default) unless separately
approved.  The policy identifier is recorded in provenance and cache keys
so that a future change in reference convention invalidates cached results.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol, TypeAlias

from pydantic import BaseModel, ConfigDict, Field

from hexagent.properties.errors import PropertyErrorCode, PropertyServiceError

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


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


class ReferenceStatePolicy(StrEnum):
    """Enthalpy/entropy reference-state convention.

    ``DEF`` is the CoolProp default (IIR for refrigerants, NIST-JANAF
    for others).  The active policy MUST be recorded in provenance and
    cache keys so that a process-wide reference-state change cannot
    silently reuse stale cached results.
    """

    DEF = "DEF"


class FluidValidationLevel(StrEnum):
    """Three-tier fluid validation per DEC-016.

    * ``BENCHMARK_VALIDATED`` — fluid has been validated against
      independently sourced reference data (dataset ID, tolerances,
      state-point list recorded in ``VALIDATION_MATRIX``).
    * ``SUPPORTED_TIER_1`` — fluid is in the approved name allowlist
      and passes basic positivity/consistency tests, but has not been
      validated against independent reference data.
    * ``UNVALIDATED`` — fluid is not in the approved set.
    """

    BENCHMARK_VALIDATED = "benchmark_validated"
    SUPPORTED_TIER_1 = "supported_tier_1"
    UNVALIDATED = "unvalidated"


# ---------------------------------------------------------------------------
# Fluid identifier
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FluidIdentifier:
    """Deterministic CoolProp fluid identifier.

    ``equation_of_state_backend`` is the internal CoolProp EOS backend
    (e.g. ``HEOS``), distinct from the property-provider identity
    (``CoolProp``).

    ``components`` is a tuple of ``(name, mole_fraction)`` values.
    Components are sorted when serialized so equivalent mappings produce
    one cache identity.
    """

    name: str
    equation_of_state_backend: str = "HEOS"
    components: tuple[tuple[str, float], ...] = ()

    # Backward-compatible alias --------------------------------------------------
    @property
    def backend(self) -> str:  # noqa: D401
        """Alias for :pyattr:`equation_of_state_backend`."""
        return self.equation_of_state_backend

    def __post_init__(self) -> None:
        if not self.name.strip() and not self.components:
            raise PropertyServiceError(
                PropertyErrorCode.INVALID_FLUID,
                "A fluid name or component list is required.",
            )
        if not self.equation_of_state_backend.strip():
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

    # Factory helpers -----------------------------------------------------------

    @classmethod
    def from_value(cls, value: FluidIdentifier | str) -> FluidIdentifier:
        if isinstance(value, FluidIdentifier):
            return value
        return cls(name=value)

    @classmethod
    def from_components(
        cls,
        components: Mapping[str, float],
        *,
        equation_of_state_backend: str = "HEOS",
        name: str = "custom_mixture",
    ) -> FluidIdentifier:
        return cls(
            name=name,
            equation_of_state_backend=equation_of_state_backend,
            components=tuple(sorted(components.items())),
        )

    # Adapter from public FluidSpec (TASK-002 domain model) --------------------

    @classmethod
    def from_fluid_spec(
        cls,
        backend: str,
        name: str,
        composition: dict[str, float] | None = None,
    ) -> FluidIdentifier:
        """Create a :class:`FluidIdentifier` from a public FluidSpec.

        ``backend`` maps to ``equation_of_state_backend`` (e.g. ``HEOS``).
        ``composition`` is a mole-fraction mapping for mixtures.
        """
        if composition:
            return cls.from_components(
                composition,
                equation_of_state_backend=backend,
                name=name,
            )
        return cls(name=name, equation_of_state_backend=backend)

    # Properties ---------------------------------------------------------------

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
            return f"{self.equation_of_state_backend}::{mixture}"
        return f"{self.equation_of_state_backend}::{self.name}"

    @property
    def cache_identity(self) -> str:
        return self.coolprop_fluid


# ---------------------------------------------------------------------------
# Validation matrix (Item 2)
# ---------------------------------------------------------------------------

ValidationMatrixEntry = dict[str, Any]


def _default_validation_matrix() -> list[ValidationMatrixEntry]:
    """Fixed v0.1 Tier-1 validation matrix.

    Each entry records:
    - dataset_id: unique identifier for the reference dataset
    - fluid: canonical CoolProp fluid name
    - state_points: list of (input_name, input_value, output_name, expected, tolerance_rel)
    - source: bibliographic or institutional reference
    - revision: dataset version or access date
    """
    return [
        {
            "dataset_id": "HXFORGE-V01-WATER-TP-001",
            "fluid": "Water",
            "query_type": "TP",
            "state_points": [
                {
                    "input": {"temperature_k": 300.0, "pressure_pa": 101_325.0},
                    "expected": {
                        "density_kg_m3": 996.5,
                        "cp_j_kg_k": 4178.0,
                    },
                    "tolerance_rel": 0.01,
                },
            ],
            "source": "CoolProp v7.6.1 default Water HEOS",
            "revision": "2026-06-21",
            "phase_region": "liquid",
        },
        {
            "dataset_id": "HXFORGE-V01-AIR-TP-001",
            "fluid": "Air",
            "query_type": "TP",
            "state_points": [
                {
                    "input": {"temperature_k": 300.0, "pressure_pa": 101_325.0},
                    "expected": {
                        "density_kg_m3": 1.177,
                        "cp_j_kg_k": 1007.0,
                    },
                    "tolerance_rel": 0.02,
                },
            ],
            "source": "CoolProp v7.6.1 default Air HEOS",
            "revision": "2026-06-21",
            "phase_region": "gas",
        },
        {
            "dataset_id": "HXFORGE-V01-R134A-TP-001",
            "fluid": "R134a",
            "query_type": "TP",
            "state_points": [
                {
                    "input": {"temperature_k": 300.0, "pressure_pa": 2_000_000.0},
                    "expected": {
                        "density_kg_m3": 1206.0,
                        "cp_j_kg_k": 1430.0,
                    },
                    "tolerance_rel": 0.02,
                },
            ],
            "source": "CoolProp v7.6.1 default R134a HEOS",
            "revision": "2026-06-21",
            "phase_region": "liquid",
        },
        {
            "dataset_id": "HXFORGE-V01-R134A-SAT-001",
            "fluid": "R134a",
            "query_type": "SATURATION_P",
            "state_points": [
                {
                    "input": {"pressure_pa": 500_000.0},
                    "expected": {
                        "liquid_temperature_k": 283.5,
                        "vapor_density_kg_m3": 23.0,
                    },
                    "tolerance_rel": 0.02,
                },
            ],
            "source": "CoolProp v7.6.1 default R134a HEOS",
            "revision": "2026-06-21",
        },
        {
            "dataset_id": "HXFORGE-V01-R717-TP-001",
            "fluid": "R717",
            "query_type": "TP",
            "state_points": [
                {
                    "input": {"temperature_k": 300.0, "pressure_pa": 2_000_000.0},
                    "expected": {
                        "density_kg_m3": 602.0,
                        "cp_j_kg_k": 4700.0,
                    },
                    "tolerance_rel": 0.03,
                },
            ],
            "source": "CoolProp v7.6.1 default R717 HEOS",
            "revision": "2026-06-21",
            "phase_region": "liquid",
        },
        {
            "dataset_id": "HXFORGE-V01-R717-SAT-001",
            "fluid": "R717",
            "query_type": "SATURATION_P",
            "state_points": [
                {
                    "input": {"pressure_pa": 1_000_000.0},
                    "expected": {
                        "liquid_temperature_k": 282.4,
                    },
                    "tolerance_rel": 0.02,
                },
            ],
            "source": "CoolProp v7.6.1 default R717 HEOS",
            "revision": "2026-06-21",
        },
    ]


VALIDATION_MATRIX: list[ValidationMatrixEntry] = _default_validation_matrix()


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


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
    reference_state_policy: ReferenceStatePolicy = ReferenceStatePolicy.DEF
    configuration_fingerprint: str = ""
    result_schema_version: str = "1.0"


# ---------------------------------------------------------------------------
# Property result models (Item 5: versioned Pydantic)
# ---------------------------------------------------------------------------


class FluidStateModel(BaseModel):
    """Versioned Pydantic serialization model for :class:`FluidState`."""

    model_config = ConfigDict(frozen=True)

    result_schema_version: str = Field(default="1.0", pattern=r"^1\.0$")
    temperature_k: float
    pressure_pa: float
    density_kg_m3: float
    cp_j_kg_k: float
    viscosity_pa_s: float
    conductivity_w_m_k: float
    enthalpy_j_kg: float
    entropy_j_kg_k: float
    phase: str
    quality: float | None = None
    provenance: dict[str, Any]


class SaturationStateModel(BaseModel):
    """Versioned Pydantic serialization model for :class:`SaturationState`."""

    model_config = ConfigDict(frozen=True)

    result_schema_version: str = Field(default="1.0", pattern=r"^1\.0$")
    query_type: str
    input_value: float
    liquid: FluidStateModel
    vapor: FluidStateModel
    provenance: dict[str, Any]


# ---------------------------------------------------------------------------
# Dataclass results (unchanged interface, plus to_model / from_json)
# ---------------------------------------------------------------------------


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

    def to_model(self) -> FluidStateModel:
        return FluidStateModel(
            temperature_k=self.temperature_k,
            pressure_pa=self.pressure_pa,
            density_kg_m3=self.density_kg_m3,
            cp_j_kg_k=self.cp_j_kg_k,
            viscosity_pa_s=self.viscosity_pa_s,
            conductivity_w_m_k=self.conductivity_w_m_k,
            enthalpy_j_kg=self.enthalpy_j_kg,
            entropy_j_kg_k=self.entropy_j_kg_k,
            phase=self.phase.value,
            quality=self.quality,
            provenance={
                "backend_name": self.provenance.backend_name,
                "backend_version": self.provenance.backend_version,
                "backend_git_revision": self.provenance.backend_git_revision,
                "fluid_identifier": self.provenance.fluid_identifier,
                "validation_level": self.provenance.validation_level.value,
                "query_type": self.provenance.query_type.value,
                "inputs": dict(self.provenance.inputs),
                "cache_policy_version": self.provenance.cache_policy_version,
                "reference_state_policy": self.provenance.reference_state_policy.value,
                "configuration_fingerprint": self.provenance.configuration_fingerprint,
            },
        )

    def to_json(self) -> str:
        return self.to_model().model_dump_json()

    @classmethod
    def from_json(cls, raw: str) -> FluidStateModel:
        return FluidStateModel.model_validate_json(raw)


@dataclass(frozen=True)
class SaturationState:
    query_type: PropertyQueryType
    input_value: float
    liquid: FluidState
    vapor: FluidState
    provenance: PropertyProvenance

    def to_model(self) -> SaturationStateModel:
        return SaturationStateModel(
            query_type=self.query_type.value,
            input_value=self.input_value,
            liquid=self.liquid.to_model(),
            vapor=self.vapor.to_model(),
            provenance={
                "backend_name": self.provenance.backend_name,
                "backend_version": self.provenance.backend_version,
                "backend_git_revision": self.provenance.backend_git_revision,
                "fluid_identifier": self.provenance.fluid_identifier,
                "validation_level": self.provenance.validation_level.value,
                "query_type": self.provenance.query_type.value,
                "inputs": dict(self.provenance.inputs),
                "cache_policy_version": self.provenance.cache_policy_version,
                "reference_state_policy": self.provenance.reference_state_policy.value,
                "configuration_fingerprint": self.provenance.configuration_fingerprint,
            },
        )

    def to_json(self) -> str:
        return self.to_model().model_dump_json()

    @classmethod
    def from_json(cls, raw: str) -> SaturationStateModel:
        return SaturationStateModel.model_validate_json(raw)


PropertyResult: TypeAlias = FluidState | SaturationState


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PropertyCacheKey:
    backend_name: str
    backend_version: str
    backend_git_revision: str
    fluid_identifier: str
    query_type: PropertyQueryType
    inputs: tuple[tuple[str, float], ...]
    configuration: tuple[tuple[str, str], ...]
    reference_state_policy: ReferenceStatePolicy = ReferenceStatePolicy.DEF
    configuration_fingerprint: str = ""


@dataclass(frozen=True)
class PropertyCacheInfo:
    hits: int
    misses: int
    size: int
    max_size: int


# ---------------------------------------------------------------------------
# Provider protocol
# ---------------------------------------------------------------------------


class PropertyProvider(Protocol):
    name: str
    version: str
    git_revision: str
    reference_state_policy: ReferenceStatePolicy

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
