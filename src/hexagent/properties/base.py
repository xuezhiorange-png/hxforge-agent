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
from typing import Any, Literal, Protocol, TypeAlias

from pydantic import BaseModel, ConfigDict

from hexagent.properties.errors import (
    PropertyErrorCode,
    PropertyServiceError,
)

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
      independently sourced reference data (not available in v0.1;
      all current fixtures are same-backend regressions).
    * ``SUPPORTED_TIER_1`` — fluid is in the approved name allowlist
      and passes basic positivity/consistency tests against the same
      backend.  This is the highest level available in v0.1.
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

    # Backward-compatible alias
    @property
    def backend(self) -> str:
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

    # Factory helpers

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

    # Item 4: FluidSpec adapter — accepts FluidSpec object or provider_id

    @classmethod
    def from_fluid_spec(
        cls,
        spec_or_provider: Any,
        name: str = "",
        *,
        equation_of_state_backend: str = "HEOS",
        composition: dict[str, float] | None = None,
        composition_basis: str = "mole_fraction",
    ) -> FluidIdentifier:
        """Create a :class:`FluidIdentifier` from a public FluidSpec.

        Accepts either:
        - an actual ``FluidSpec`` object (preferred), or
        - ``provider_id`` as a string (e.g. ``"CoolProp"``).

        ``equation_of_state_backend`` defaults to ``HEOS``.
        ``composition_basis`` is validated (v0.1: ``mole_fraction`` only).
        """
        # Accept actual FluidSpec object
        if hasattr(spec_or_provider, "backend") and hasattr(
            spec_or_provider, "name"
        ):
            provider_id = spec_or_provider.backend
            fluid_name = spec_or_provider.name
            comp = getattr(spec_or_provider, "composition", None)
            return cls._from_provider_and_name(
                provider_id,
                fluid_name,
                equation_of_state_backend=equation_of_state_backend,
                composition=comp,
                composition_basis=composition_basis,
            )
        # String provider_id path
        return cls._from_provider_and_name(
            str(spec_or_provider),
            name,
            equation_of_state_backend=equation_of_state_backend,
            composition=composition,
            composition_basis=composition_basis,
        )

    @classmethod
    def _from_provider_and_name(
        cls,
        provider_id: str,
        name: str,
        *,
        equation_of_state_backend: str,
        composition: dict[str, float] | None,
        composition_basis: str,
    ) -> FluidIdentifier:
        if provider_id != "CoolProp":
            raise PropertyServiceError(
                PropertyErrorCode.UNSUPPORTED_BACKEND,
                f"Provider {provider_id!r} is not supported in v0.1.",
                context={"provider_id": provider_id},
            )
        if composition_basis != "mole_fraction":
            raise PropertyServiceError(
                PropertyErrorCode.INVALID_FLUID,
                f"Composition basis {composition_basis!r} "
                "is not supported in v0.1.",
                context={"composition_basis": composition_basis},
            )
        if composition:
            return cls.from_components(
                composition,
                equation_of_state_backend=equation_of_state_backend,
                name=name,
            )
        return cls(
            name=name,
            equation_of_state_backend=equation_of_state_backend,
        )

    # Properties

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

    @property
    def is_mixture(self) -> bool:
        return len(self.components) > 0


# ---------------------------------------------------------------------------
# Validation matrix (Item 2)
# ---------------------------------------------------------------------------

ValidationMatrixEntry = dict[str, Any]


def _default_validation_matrix() -> list[ValidationMatrixEntry]:
    """Fixed v0.1 backend-regression fixtures.

    These are **same-backend** regression data points (CoolProp HEOS
    evaluating its own outputs).  They are NOT independent/reference
    benchmarks.  All Tier-1 fluids receive ``SUPPORTED_TIER_1`` level.

    Each entry records:
    - dataset_id: unique identifier
    - fluid: canonical CoolProp fluid name
    - query_type: TP, SATURATION_P, etc.
    - state_points: inputs + expected outputs + tolerance
    - source: identifies this as backend regression
    - revision: dataset version
    """
    return [
        {
            "dataset_id": "HXFORGE-V01-WATER-TP-REGRESSION-001",
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
            "source": "CoolProp v7.6.1 HEOS backend regression",
            "revision": "2026-06-21",
            "validation_basis": "backend_regression",
        },
        {
            "dataset_id": "HXFORGE-V01-AIR-TP-REGRESSION-001",
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
            "source": "CoolProp v7.6.1 HEOS backend regression",
            "revision": "2026-06-21",
            "validation_basis": "backend_regression",
        },
        {
            "dataset_id": "HXFORGE-V01-R134A-TP-REGRESSION-001",
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
            "source": "CoolProp v7.6.1 HEOS backend regression",
            "revision": "2026-06-21",
            "validation_basis": "backend_regression",
        },
        {
            "dataset_id": "HXFORGE-V01-R134A-SAT-REGRESSION-001",
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
            "source": "CoolProp v7.6.1 HEOS backend regression",
            "revision": "2026-06-21",
            "validation_basis": "backend_regression",
        },
        {
            "dataset_id": "HXFORGE-V01-R717-TP-REGRESSION-001",
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
            "source": "CoolProp v7.6.1 HEOS backend regression",
            "revision": "2026-06-21",
            "validation_basis": "backend_regression",
        },
        {
            "dataset_id": "HXFORGE-V01-R717-SAT-REGRESSION-001",
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
            "source": "CoolProp v7.6.1 HEOS backend regression",
            "revision": "2026-06-21",
            "validation_basis": "backend_regression",
        },
    ]


VALIDATION_MATRIX: list[ValidationMatrixEntry] = _default_validation_matrix()


# ---------------------------------------------------------------------------
# Provenance (Item 5: strict Pydantic models)
# ---------------------------------------------------------------------------


class PropertyProvenanceModel(BaseModel):
    """Strict versioned Pydantic model for property provenance."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    backend_name: str
    backend_version: str
    backend_git_revision: str
    fluid_identifier: str
    validation_level: FluidValidationLevel
    validation_dataset_id: str | None = None
    validation_dataset_revision: str | None = None
    validation_basis: str | None = None
    query_type: PropertyQueryType
    inputs: dict[str, float]
    cache_policy_version: str
    reference_state_policy: ReferenceStatePolicy
    configuration_fingerprint: str
    result_schema_version: Literal["1.0"] = "1.0"


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
    validation_dataset_id: str | None = None
    validation_dataset_revision: str | None = None
    validation_basis: str | None = None
    reference_state_policy: ReferenceStatePolicy = ReferenceStatePolicy.DEF
    configuration_fingerprint: str = ""
    result_schema_version: Literal["1.0"] = "1.0"

    def to_model(self) -> PropertyProvenanceModel:
        return PropertyProvenanceModel(
            backend_name=self.backend_name,
            backend_version=self.backend_version,
            backend_git_revision=self.backend_git_revision,
            fluid_identifier=self.fluid_identifier,
            validation_level=self.validation_level,
            validation_dataset_id=self.validation_dataset_id,
            validation_dataset_revision=self.validation_dataset_revision,
            validation_basis=self.validation_basis,
            query_type=self.query_type,
            inputs=dict(self.inputs),
            cache_policy_version=self.cache_policy_version,
            reference_state_policy=self.reference_state_policy,
            configuration_fingerprint=self.configuration_fingerprint,
            result_schema_version=self.result_schema_version,
        )

    def to_dict(self) -> dict[str, Any]:
        return self.to_model().model_dump()


# ---------------------------------------------------------------------------
# Result serialization models (Item 5: strict, Literal version, extra=forbid)
# ---------------------------------------------------------------------------


class FluidStateModel(BaseModel):
    """Versioned Pydantic serialization model for :class:`FluidState`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    result_schema_version: Literal["1.0"] = "1.0"
    temperature_k: float
    pressure_pa: float
    density_kg_m3: float
    cp_j_kg_k: float
    viscosity_pa_s: float
    conductivity_w_m_k: float
    enthalpy_j_kg: float
    entropy_j_kg_k: float
    phase: PhaseRegion
    quality: float | None = None
    provenance: PropertyProvenanceModel


class SaturationStateModel(BaseModel):
    """Versioned Pydantic serialization model for :class:`SaturationState`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    result_schema_version: Literal["1.0"] = "1.0"
    query_type: PropertyQueryType
    input_value: float
    liquid: FluidStateModel
    vapor: FluidStateModel
    provenance: PropertyProvenanceModel


# ---------------------------------------------------------------------------
# Dataclass results (with true round-trip to_json / from_json)
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
            phase=self.phase,
            quality=self.quality,
            provenance=self.provenance.to_model(),
        )

    def to_json(self) -> str:
        return self.to_model().model_dump_json()

    @classmethod
    def from_json(cls, raw: str) -> FluidState:
        """Deserialize from JSON back to a domain FluidState."""
        model = FluidStateModel.model_validate_json(raw)
        prov_dict = model.provenance.model_dump()
        prov = PropertyProvenance(
            backend_name=prov_dict["backend_name"],
            backend_version=prov_dict["backend_version"],
            backend_git_revision=prov_dict["backend_git_revision"],
            fluid_identifier=prov_dict["fluid_identifier"],
            validation_level=FluidValidationLevel(prov_dict["validation_level"]),
            validation_dataset_id=prov_dict.get("validation_dataset_id"),
            validation_dataset_revision=prov_dict.get("validation_dataset_revision"),
            validation_basis=prov_dict.get("validation_basis"),
            query_type=PropertyQueryType(prov_dict["query_type"]),
            inputs=tuple(prov_dict["inputs"].items()),
            cache_policy_version=prov_dict["cache_policy_version"],
            reference_state_policy=ReferenceStatePolicy(
                prov_dict["reference_state_policy"]
            ),
            configuration_fingerprint=prov_dict["configuration_fingerprint"],
        )
        return cls(
            temperature_k=model.temperature_k,
            pressure_pa=model.pressure_pa,
            density_kg_m3=model.density_kg_m3,
            cp_j_kg_k=model.cp_j_kg_k,
            viscosity_pa_s=model.viscosity_pa_s,
            conductivity_w_m_k=model.conductivity_w_m_k,
            enthalpy_j_kg=model.enthalpy_j_kg,
            entropy_j_kg_k=model.entropy_j_kg_k,
            phase=PhaseRegion(model.phase),
            quality=model.quality,
            provenance=prov,
        )


@dataclass(frozen=True)
class SaturationState:
    query_type: PropertyQueryType
    input_value: float
    liquid: FluidState
    vapor: FluidState
    provenance: PropertyProvenance

    def to_model(self) -> SaturationStateModel:
        return SaturationStateModel(
            query_type=self.query_type,
            input_value=self.input_value,
            liquid=self.liquid.to_model(),
            vapor=self.vapor.to_model(),
            provenance=self.provenance.to_model(),
        )

    def to_json(self) -> str:
        return self.to_model().model_dump_json()

    @classmethod
    def from_json(cls, raw: str) -> SaturationState:
        """Deserialize from JSON back to a domain SaturationState."""
        model = SaturationStateModel.model_validate_json(raw)
        prov_dict = model.provenance.model_dump()
        prov = PropertyProvenance(
            backend_name=prov_dict["backend_name"],
            backend_version=prov_dict["backend_version"],
            backend_git_revision=prov_dict["backend_git_revision"],
            fluid_identifier=prov_dict["fluid_identifier"],
            validation_level=FluidValidationLevel(prov_dict["validation_level"]),
            validation_dataset_id=prov_dict.get("validation_dataset_id"),
            validation_dataset_revision=prov_dict.get("validation_dataset_revision"),
            validation_basis=prov_dict.get("validation_basis"),
            query_type=PropertyQueryType(prov_dict["query_type"]),
            inputs=tuple(prov_dict["inputs"].items()),
            cache_policy_version=prov_dict["cache_policy_version"],
            reference_state_policy=ReferenceStatePolicy(
                prov_dict["reference_state_policy"]
            ),
            configuration_fingerprint=prov_dict["configuration_fingerprint"],
        )
        liquid = FluidState.from_json(model.liquid.model_dump_json())
        vapor = FluidState.from_json(model.vapor.model_dump_json())
        return cls(
            query_type=PropertyQueryType(model.query_type),
            input_value=model.input_value,
            liquid=liquid,
            vapor=vapor,
            provenance=prov,
        )


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
# Provider protocol (Item 3: reference_state mandatory in PH)
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
        *,
        reference_state: ReferenceStatePolicy,
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
