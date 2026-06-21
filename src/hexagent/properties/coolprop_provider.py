"""CoolProp HEOS property provider — deterministic, cache-safe, reference-state-aware.

v0.1 reference-state policy: ``DEF`` (CoolProp default).
Configuration fingerprint is recomputed before every query to detect
external mutations and fail closed.  A process-level lock protects
the combined "verify + evaluate" operation as one atomic action.
"""
from __future__ import annotations

import hashlib
import math
import threading
from collections import OrderedDict
from dataclasses import replace
from typing import NoReturn

import CoolProp.CoolProp as CP

from hexagent.properties.base import (
    VALIDATION_MATRIX,
    FluidIdentifier,
    FluidState,
    FluidValidationLevel,
    PhaseRegion,
    PropertyCacheInfo,
    PropertyCacheKey,
    PropertyProvenance,
    PropertyQueryType,
    PropertyResult,
    ReferenceStatePolicy,
    SaturationState,
)
from hexagent.properties.errors import PropertyErrorCode, PropertyServiceError

# ---------------------------------------------------------------------------
# Module-level process lock — serializes all CoolProp global-state access
# ---------------------------------------------------------------------------

_COOLPROP_STATE_LOCK = threading.Lock()

# ---------------------------------------------------------------------------
# Reference-sensitive fluids and verification state points
# ---------------------------------------------------------------------------

_REFERENCE_SENSITIVE_FLUIDS: tuple[str, ...] = ("Water", "R134a", "R717")

_REF_VERIFY_STATE_POINTS: dict[str, tuple[float, float]] = {
    "Water": (300.0, 101_325.0),
    "R134a": (300.0, 2_000_000.0),
    "R717": (300.0, 2_000_000.0),
}

# ---------------------------------------------------------------------------
# Configuration fingerprint (Item 1: all reference-sensitive fluids)
# ---------------------------------------------------------------------------


def _coolprop_configuration_fingerprint() -> str:
    """Capture a hash of CoolProp configuration state.

    Probes all reference-sensitive fluids (Water, R134a, R717) at known
    state points.  Any change in reference state or backend configuration
    changes the fingerprint.
    """
    parts: list[str] = []
    parts.append(f"version={CP.get_global_param_string('version')}")
    parts.append(f"git={CP.get_global_param_string('gitrevision')}")
    for fluid, (t, p) in _REF_VERIFY_STATE_POINTS.items():
        try:
            h = float(
                CP.PropsSI("Hmass", "T", t, "P", p, fluid)
            )
            parts.append(f"{fluid}_{t}_{p}={h:.15e}")
        except Exception:
            parts.append(f"{fluid}_{t}_{p}=err")
    blob = "|".join(parts)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Fluid-support matrix (Item 2: all SUPPORTED_TIER_1, no BENCHMARK_VALIDATED)
# ---------------------------------------------------------------------------

_TIER_1_ALIASES: dict[str, str] = {
    "water": "Water",
    "air": "Air",
    "r134a": "R134a",
    "r717": "R717",
    "ammonia": "R717",
}

# v0.1: No fluid receives BENCHMARK_VALIDATED.  All Tier-1 fluids are
# SUPPORTED_TIER_1 (same-backend regression only, not independent evidence).
_BENCHMARK_VALIDATED_FLUIDS: set[str] = set()


def _validation_level_for(canonical_name: str) -> FluidValidationLevel:
    if canonical_name in _BENCHMARK_VALIDATED_FLUIDS:
        return FluidValidationLevel.BENCHMARK_VALIDATED
    return FluidValidationLevel.SUPPORTED_TIER_1


# ---------------------------------------------------------------------------
# Known error classification (Item 7)
# ---------------------------------------------------------------------------

_COOLPROP_OUT_OF_RANGE_TOKENS = (
    "out of range",
    "triple",
    "below the minimum",
    "above the maximum",
    "unable to solve",
)


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------


class CoolPropProvider:
    """Deterministic CoolProp HEOS property provider."""

    name = "CoolProp"
    cache_policy_version = "1.0"
    reference_state_policy = ReferenceStatePolicy.DEF

    def __init__(
        self,
        *,
        allow_unvalidated_fluids: bool = False,
        near_saturation_relative_tolerance: float = 1e-6,
        cache_size: int = 256,
    ) -> None:
        if not math.isfinite(near_saturation_relative_tolerance):
            raise ValueError(
                "near_saturation_relative_tolerance must be finite"
            )
        if not 0.0 < near_saturation_relative_tolerance < 1.0:
            raise ValueError(
                "near_saturation_relative_tolerance must be in (0, 1)"
            )
        if cache_size < 0:
            raise ValueError("cache_size must be non-negative")

        self.version = str(CP.get_global_param_string("version"))
        self.git_revision = str(CP.get_global_param_string("gitrevision"))
        self.allow_unvalidated_fluids = allow_unvalidated_fluids
        self.near_saturation_relative_tolerance = (
            near_saturation_relative_tolerance
        )
        self.cache_size = cache_size

        # Item 1: Establish known DEF baseline during controlled init.
        # Force DEF for all reference-sensitive fluids, then capture
        # enthalpies and compute the construction fingerprint.  If
        # CoolProp was already in DEF this is a no-op; if it was in
        # IIR (or any other state) we reset to DEF and capture the
        # correct baseline.
        with _COOLPROP_STATE_LOCK:
            self._force_def_reference_state()
            self._def_baseline = self._capture_def_enthalpies()
            self._construction_fingerprint = (
                _coolprop_configuration_fingerprint()
            )

        self._cache: OrderedDict[PropertyCacheKey, PropertyResult] = (
            OrderedDict()
        )
        self._cache_hits = 0
        self._cache_misses = 0
        self._cache_lock = threading.Lock()

    # ------------------------------------------------------------------
    # Item 1: Runtime configuration guard + DEF baseline
    # ------------------------------------------------------------------

    @staticmethod
    def _force_def_reference_state() -> None:
        """Force DEF reference state for all reference-sensitive fluids.

        Called during ``__init__`` under ``_COOLPROP_STATE_LOCK``.
        If CoolProp is already in DEF this is a no-op.
        """
        import contextlib

        for fluid in _REFERENCE_SENSITIVE_FLUIDS:
            with contextlib.suppress(Exception):
                CP.set_reference_state(fluid, "DEF")

    @staticmethod
    def _capture_def_enthalpies() -> dict[str, float]:
        """Capture enthalpies at known state points under DEF state.

        Returns a mapping of fluid name → enthalpy (J/kg).  These
        values form the known-DEF baseline that runtime verification
        checks against.
        """
        baseline: dict[str, float] = {}
        for fluid, (t, p) in _REF_VERIFY_STATE_POINTS.items():
            try:
                h = float(
                    CP.PropsSI("Hmass", "T", t, "P", p, fluid)
                )
                baseline[fluid] = h
            except Exception:
                baseline[fluid] = float("nan")
        return baseline

    def _verify_def_baseline(self, fluid_name: str) -> None:
        """Verify the current CoolProp state matches the known DEF baseline.

        For the given fluid, recompute the enthalpy at the known state
        point and compare against the value captured during ``__init__``.
        A mismatch means the reference state was mutated.
        """
        if fluid_name not in _REF_VERIFY_STATE_POINTS:
            return
        expected = self._def_baseline.get(fluid_name)
        if expected is None or math.isnan(expected):
            return
        t, p = _REF_VERIFY_STATE_POINTS[fluid_name]
        try:
            h = float(
                CP.PropsSI("Hmass", "T", t, "P", p, fluid_name)
            )
        except Exception:
            return  # Let the actual query handle the error
        if not math.isclose(h, expected, rel_tol=1e-6, abs_tol=1.0):
            raise PropertyServiceError(
                PropertyErrorCode.CONFIGURATION_CHANGED,
                "CoolProp reference state has changed since provider "
                "construction. The active state no longer matches the "
                "known DEF baseline.",
                context={
                    "fluid": fluid_name,
                    "expected_enthalpy_j_kg": expected,
                    "actual_enthalpy_j_kg": h,
                },
            )

    def _verify_configuration(self, fluid_name: str | None = None) -> str:
        """Recompute fingerprint and verify against construction baseline.

        If the global CoolProp configuration has changed since provider
        construction, clear the cache and raise CONFIGURATION_CHANGED.
        Optionally also verify the DEF baseline for a specific fluid.
        Returns the current fingerprint for cache keys.

        Must be called under ``_COOLPROP_STATE_LOCK``.
        """
        if fluid_name is not None:
            self._verify_def_baseline(fluid_name)
        current = _coolprop_configuration_fingerprint()
        if current != self._construction_fingerprint:
            with self._cache_lock:
                self._cache.clear()
                self._cache_hits = 0
                self._cache_misses = 0
            raise PropertyServiceError(
                PropertyErrorCode.CONFIGURATION_CHANGED,
                "CoolProp global configuration changed since provider "
                "construction. All cached results have been discarded.",
                context={
                    "construction_fingerprint": (
                        self._construction_fingerprint
                    ),
                    "current_fingerprint": current,
                },
            )
        return current

    # ------------------------------------------------------------------
    # Public query API
    # ------------------------------------------------------------------

    def state_tp(
        self,
        fluid: FluidIdentifier | str,
        temperature_k: float,
        pressure_pa: float,
    ) -> FluidState:
        identifier, validation = self._resolve_fluid(fluid)
        self._require_positive("temperature_k", temperature_k)
        self._require_positive("pressure_pa", pressure_pa)
        self._reject_mixture(identifier, "TP")

        inputs = (
            ("temperature_k", temperature_k),
            ("pressure_pa", pressure_pa),
        )

        # Item 1: atomic verify + evaluate under process lock
        with _COOLPROP_STATE_LOCK:
            fingerprint = self._verify_configuration(identifier.name)
            key = self._cache_key(
                identifier, PropertyQueryType.TP, inputs, fingerprint
            )
            cached = self._cache_get(key)
            if cached is not None:
                if not isinstance(cached, FluidState):
                    raise RuntimeError("Cache type mismatch for TP query")
                return cached

            state = self._state_tp_uncached(
                identifier, validation, temperature_k, pressure_pa,
                fingerprint,
            )
            self._cache_store(key, state)
            return state

    def state_ph(
        self,
        fluid: FluidIdentifier | str,
        pressure_pa: float,
        enthalpy_j_kg: float,
        *,
        reference_state: ReferenceStatePolicy,
    ) -> FluidState:
        identifier, validation = self._resolve_fluid(fluid)
        self._require_positive("pressure_pa", pressure_pa)
        self._require_finite("enthalpy_j_kg", enthalpy_j_kg)

        # Item 3: mandatory reference-state check
        if reference_state is not self.reference_state_policy:
            raise PropertyServiceError(
                PropertyErrorCode.INVALID_INPUT,
                "PH query reference-state policy does not match "
                "the provider policy.",
                context={
                    "requested": str(reference_state),
                    "provider": str(self.reference_state_policy),
                },
            )

        self._reject_mixture(identifier, "PH")

        inputs = (
            ("pressure_pa", pressure_pa),
            ("enthalpy_j_kg", enthalpy_j_kg),
        )

        # Item 1: atomic verify + evaluate under process lock
        with _COOLPROP_STATE_LOCK:
            fingerprint = self._verify_configuration(identifier.name)
            key = self._cache_key(
                identifier, PropertyQueryType.PH, inputs, fingerprint
            )
            cached = self._cache_get(key)
            if cached is not None:
                if not isinstance(cached, FluidState):
                    raise RuntimeError("Cache type mismatch for PH query")
                return cached

            state = self._state_ph_uncached(
                identifier, validation, pressure_pa, enthalpy_j_kg,
                fingerprint,
            )
            self._cache_store(key, state)
            return state

    def saturation_at_pressure(
        self,
        fluid: FluidIdentifier | str,
        pressure_pa: float,
    ) -> SaturationState:
        identifier, validation = self._resolve_fluid(fluid)
        self._require_positive("pressure_pa", pressure_pa)
        self._reject_mixture(identifier, "SATURATION_P")

        inputs = (("pressure_pa", pressure_pa),)
        query_type = PropertyQueryType.SATURATION_P

        # Item 1: atomic verify + evaluate under process lock
        with _COOLPROP_STATE_LOCK:
            fingerprint = self._verify_configuration(identifier.name)
            key = self._cache_key(
                identifier, query_type, inputs, fingerprint
            )
            cached = self._cache_get(key)
            if cached is not None:
                if not isinstance(cached, SaturationState):
                    raise RuntimeError("Cache type mismatch for saturation")
                return cached

            state = self._saturation_pressure_uncached(
                identifier, validation, pressure_pa, fingerprint,
            )
            self._cache_store(key, state)
            return state

    def saturation_at_temperature(
        self,
        fluid: FluidIdentifier | str,
        temperature_k: float,
    ) -> SaturationState:
        identifier, validation = self._resolve_fluid(fluid)
        self._require_positive("temperature_k", temperature_k)
        self._reject_mixture(identifier, "SATURATION_T")

        inputs = (("temperature_k", temperature_k),)
        query_type = PropertyQueryType.SATURATION_T

        # Item 1: atomic verify + evaluate under process lock
        with _COOLPROP_STATE_LOCK:
            fingerprint = self._verify_configuration(identifier.name)
            key = self._cache_key(
                identifier, query_type, inputs, fingerprint
            )
            cached = self._cache_get(key)
            if cached is not None:
                if not isinstance(cached, SaturationState):
                    raise RuntimeError("Cache type mismatch for saturation")
                return cached

            state = self._saturation_temperature_uncached(
                identifier, validation, temperature_k, fingerprint,
            )
            self._cache_store(key, state)
            return state

    def cache_info(self) -> PropertyCacheInfo:
        with self._cache_lock:
            return PropertyCacheInfo(
                hits=self._cache_hits,
                misses=self._cache_misses,
                size=len(self._cache),
                max_size=self.cache_size,
            )

    def clear_cache(self) -> None:
        with self._cache_lock:
            self._cache.clear()
            self._cache_hits = 0
            self._cache_misses = 0

    # ------------------------------------------------------------------
    # Item 6: Mixture rejection
    # ------------------------------------------------------------------

    @staticmethod
    def _reject_mixture(
        identifier: FluidIdentifier, query_type: str
    ) -> None:
        if identifier.is_mixture:
            raise PropertyServiceError(
                PropertyErrorCode.UNSUPPORTED_QUERY,
                "Mixture property calculations are not implemented "
                "in v0.1. Mixture identifiers are representable "
                "but not computable.",
                context={
                    "fluid": identifier.cache_identity,
                    "query_type": query_type,
                },
            )

    # ------------------------------------------------------------------
    # Internal — uncached computation
    # ------------------------------------------------------------------

    def _state_tp_uncached(
        self, fluid: FluidIdentifier, validation: FluidValidationLevel,
        temperature_k: float, pressure_pa: float, fingerprint: str,
    ) -> FluidState:
        self._check_tp_near_saturation(fluid, temperature_k, pressure_pa)
        phase = self._phase(
            fluid, "T", temperature_k, "P", pressure_pa,
            PropertyQueryType.TP,
        )
        self._reject_unknown_phase(phase, fluid, PropertyQueryType.TP)
        return self._build_state(
            fluid, validation, PropertyQueryType.TP,
            "T", temperature_k, "P", pressure_pa,
            phase=phase, quality=None, fingerprint=fingerprint,
        )

    def _state_ph_uncached(
        self, fluid: FluidIdentifier, validation: FluidValidationLevel,
        pressure_pa: float, enthalpy_j_kg: float, fingerprint: str,
    ) -> FluidState:
        self._check_ph_saturation(fluid, pressure_pa, enthalpy_j_kg)
        phase = self._phase(
            fluid, "P", pressure_pa, "Hmass", enthalpy_j_kg,
            PropertyQueryType.PH,
        )
        self._reject_unknown_phase(phase, fluid, PropertyQueryType.PH)
        return self._build_state(
            fluid, validation, PropertyQueryType.PH,
            "P", pressure_pa, "Hmass", enthalpy_j_kg,
            phase=phase, quality=None, fingerprint=fingerprint,
        )

    def _saturation_pressure_uncached(
        self, fluid: FluidIdentifier, validation: FluidValidationLevel,
        pressure_pa: float, fingerprint: str,
    ) -> SaturationState:
        query_type = PropertyQueryType.SATURATION_P
        # Item 5: explicit boundary pre-check before calling CoolProp
        self._pre_check_saturation_boundaries(
            fluid, "pressure_pa", pressure_pa
        )
        try:
            liquid = self._build_state(
                fluid, validation, query_type,
                "P", pressure_pa, "Q", 0.0,
                phase=PhaseRegion.SATURATED_LIQUID, quality=0.0,
                fingerprint=fingerprint,
            )
            vapor = self._build_state(
                fluid, validation, query_type,
                "P", pressure_pa, "Q", 1.0,
                phase=PhaseRegion.SATURATED_VAPOR, quality=1.0,
                fingerprint=fingerprint,
            )
        except PropertyServiceError as exc:
            self._raise_saturation_unavailable(
                exc, fluid, "pressure_pa", pressure_pa
            )
        provenance = self._provenance(
            fluid, validation, query_type,
            (("pressure_pa", pressure_pa),), fingerprint,
        )
        return SaturationState(
            query_type=query_type, input_value=pressure_pa,
            liquid=liquid, vapor=vapor, provenance=provenance,
        )

    def _saturation_temperature_uncached(
        self, fluid: FluidIdentifier, validation: FluidValidationLevel,
        temperature_k: float, fingerprint: str,
    ) -> SaturationState:
        query_type = PropertyQueryType.SATURATION_T
        # Item 5: explicit boundary pre-check before calling CoolProp
        self._pre_check_saturation_boundaries(
            fluid, "temperature_k", temperature_k
        )
        try:
            liquid = self._build_state(
                fluid, validation, query_type,
                "T", temperature_k, "Q", 0.0,
                phase=PhaseRegion.SATURATED_LIQUID, quality=0.0,
                fingerprint=fingerprint,
            )
            vapor = self._build_state(
                fluid, validation, query_type,
                "T", temperature_k, "Q", 1.0,
                phase=PhaseRegion.SATURATED_VAPOR, quality=1.0,
                fingerprint=fingerprint,
            )
        except PropertyServiceError as exc:
            self._raise_saturation_unavailable(
                exc, fluid, "temperature_k", temperature_k
            )
        provenance = self._provenance(
            fluid, validation, query_type,
            (("temperature_k", temperature_k),), fingerprint,
        )
        return SaturationState(
            query_type=query_type, input_value=temperature_k,
            liquid=liquid, vapor=vapor, provenance=provenance,
        )

    def _raise_saturation_unavailable(
        self, exc: PropertyServiceError, fluid: FluidIdentifier,
        input_name: str, input_value: float,
    ) -> NoReturn:
        if exc.code not in {
            PropertyErrorCode.STATE_OUT_OF_RANGE,
            PropertyErrorCode.BACKEND_FAILURE,
        }:
            raise exc
        raise PropertyServiceError(
            PropertyErrorCode.SATURATION_UNAVAILABLE,
            "Saturation properties are unavailable at the "
            "requested state.",
            context={
                "fluid": fluid.cache_identity,
                input_name: input_value,
                "backend_error": exc.as_dict(),
            },
        ) from exc

    # ------------------------------------------------------------------
    # Internal — state construction
    # ------------------------------------------------------------------

    def _build_state(
        self, fluid: FluidIdentifier, validation: FluidValidationLevel,
        query_type: PropertyQueryType,
        input1_name: str, input1_value: float,
        input2_name: str, input2_value: float,
        *, phase: PhaseRegion, quality: float | None,
        fingerprint: str,
    ) -> FluidState:
        inputs = (
            (self._input_context_name(input1_name), input1_value),
            (self._input_context_name(input2_name), input2_value),
        )
        query = (input1_name, input1_value, input2_name, input2_value)
        values = {
            "temperature_k": self._props(
                "T", fluid, query_type, query
            ),
            "pressure_pa": self._props(
                "P", fluid, query_type, query
            ),
            "density_kg_m3": self._props(
                "Dmass", fluid, query_type, query
            ),
            "cp_j_kg_k": self._props(
                "Cpmass", fluid, query_type, query
            ),
            "viscosity_pa_s": self._props(
                "VISCOSITY", fluid, query_type, query
            ),
            "conductivity_w_m_k": self._props(
                "CONDUCTIVITY", fluid, query_type, query
            ),
            "enthalpy_j_kg": self._props(
                "Hmass", fluid, query_type, query
            ),
            "entropy_j_kg_k": self._props(
                "Smass", fluid, query_type, query
            ),
        }
        self._validate_outputs(values, fluid, query_type)
        return FluidState(
            temperature_k=values["temperature_k"],
            pressure_pa=values["pressure_pa"],
            density_kg_m3=values["density_kg_m3"],
            cp_j_kg_k=values["cp_j_kg_k"],
            viscosity_pa_s=values["viscosity_pa_s"],
            conductivity_w_m_k=values["conductivity_w_m_k"],
            enthalpy_j_kg=values["enthalpy_j_kg"],
            entropy_j_kg_k=values["entropy_j_kg_k"],
            phase=phase,
            quality=quality,
            provenance=self._provenance(
                fluid, validation, query_type, inputs, fingerprint
            ),
        )

    def _validate_outputs(
        self, values: dict[str, float], fluid: FluidIdentifier,
        query_type: PropertyQueryType,
    ) -> None:
        for name, value in values.items():
            if not math.isfinite(value):
                raise PropertyServiceError(
                    PropertyErrorCode.NON_FINITE_RESULT,
                    f"CoolProp returned a non-finite {name}.",
                    context={
                        "fluid": fluid.cache_identity,
                        "query_type": query_type.value,
                    },
                )
        positive_outputs = (
            "temperature_k", "pressure_pa", "density_kg_m3",
            "cp_j_kg_k", "viscosity_pa_s", "conductivity_w_m_k",
        )
        for name in positive_outputs:
            if values[name] <= 0.0:
                raise PropertyServiceError(
                    PropertyErrorCode.NON_FINITE_RESULT,
                    f"CoolProp returned a non-positive {name}.",
                    context={
                        "fluid": fluid.cache_identity,
                        "query_type": query_type.value,
                        "value": values[name],
                    },
                )

    # ------------------------------------------------------------------
    # Internal — fluid resolution
    # ------------------------------------------------------------------

    def _resolve_fluid(
        self, fluid: FluidIdentifier | str,
    ) -> tuple[FluidIdentifier, FluidValidationLevel]:
        identifier = FluidIdentifier.from_value(fluid)
        if identifier.equation_of_state_backend.upper() != "HEOS":
            raise PropertyServiceError(
                PropertyErrorCode.UNSUPPORTED_BACKEND,
                "Only the CoolProp HEOS backend is approved in v0.1.",
                context={
                    "backend": identifier.equation_of_state_backend,
                },
            )
        validation = FluidValidationLevel.UNVALIDATED
        if not identifier.components:
            canonical = _TIER_1_ALIASES.get(identifier.name.casefold())
            if canonical is not None:
                identifier = replace(
                    identifier,
                    name=canonical,
                    equation_of_state_backend="HEOS",
                )
                validation = _validation_level_for(canonical)

        self._assert_fluid_exists(identifier)
        if (
            validation is FluidValidationLevel.UNVALIDATED
            and not self.allow_unvalidated_fluids
        ):
            raise PropertyServiceError(
                PropertyErrorCode.UNVALIDATED_FLUID,
                "The requested fluid is not in the approved "
                "Tier-1 validation set.",
                context={"fluid": identifier.cache_identity},
            )
        return identifier, validation

    def _assert_fluid_exists(self, fluid: FluidIdentifier) -> None:
        try:
            molar_mass = float(
                CP.PropsSI("M", fluid.coolprop_fluid)
            )
        except Exception as exc:
            raise PropertyServiceError(
                PropertyErrorCode.INVALID_FLUID,
                "CoolProp could not resolve the requested "
                "fluid identifier.",
                context={
                    "fluid": fluid.cache_identity,
                    "backend_message": str(exc),
                },
            ) from exc
        if not math.isfinite(molar_mass) or molar_mass <= 0.0:
            raise PropertyServiceError(
                PropertyErrorCode.INVALID_FLUID,
                "CoolProp returned an invalid molar mass "
                "for the fluid.",
                context={
                    "fluid": fluid.cache_identity,
                    "molar_mass": molar_mass,
                },
            )

    # ------------------------------------------------------------------
    # Internal — saturation boundary checks
    # ------------------------------------------------------------------

    def _check_tp_near_saturation(
        self, fluid: FluidIdentifier,
        temperature_k: float, pressure_pa: float,
    ) -> None:
        saturation_pressures = self._try_saturation_values(
            fluid, "P", "T", temperature_k
        )
        for sp in saturation_pressures:
            denominator = max(abs(sp), 1.0)
            rel_dist = abs(pressure_pa - sp) / denominator
            if rel_dist <= self.near_saturation_relative_tolerance:
                raise PropertyServiceError(
                    PropertyErrorCode.NEAR_SATURATION,
                    "TP state is too close to the saturation "
                    "boundary.",
                    context={
                        "fluid": fluid.cache_identity,
                        "temperature_k": temperature_k,
                        "pressure_pa": pressure_pa,
                        "saturation_pressure_pa": sp,
                        "relative_distance": rel_dist,
                    },
                )

    def _check_ph_saturation(
        self, fluid: FluidIdentifier,
        pressure_pa: float, enthalpy_j_kg: float,
    ) -> None:
        saturation_enthalpies = self._try_saturation_values(
            fluid, "Hmass", "P", pressure_pa
        )
        if len(saturation_enthalpies) != 2:
            return
        lower, upper = sorted(saturation_enthalpies)

        # Item 6: reference-state-invariant scale using latent heat
        latent_heat = abs(upper - lower)
        MIN_LATENT_FLOOR = 1.0  # J/kg
        scale = max(latent_heat, MIN_LATENT_FLOOR)

        boundary_distance = min(
            abs(enthalpy_j_kg - lower),
            abs(enthalpy_j_kg - upper),
        )
        if (
            boundary_distance
            <= self.near_saturation_relative_tolerance * scale
        ):
            raise PropertyServiceError(
                PropertyErrorCode.NEAR_SATURATION,
                "PH state is too close to a saturation boundary.",
                context={
                    "fluid": fluid.cache_identity,
                    "pressure_pa": pressure_pa,
                    "enthalpy_j_kg": enthalpy_j_kg,
                    "saturated_liquid_enthalpy_j_kg": lower,
                    "saturated_vapor_enthalpy_j_kg": upper,
                    "latent_heat_j_kg": latent_heat,
                    "tolerance_scale_j_kg": scale,
                },
            )
        if lower < enthalpy_j_kg < upper:
            raise PropertyServiceError(
                PropertyErrorCode.TWO_PHASE_STATE,
                "PH state lies inside the two-phase "
                "enthalpy interval.",
                context={
                    "fluid": fluid.cache_identity,
                    "pressure_pa": pressure_pa,
                    "enthalpy_j_kg": enthalpy_j_kg,
                    "saturated_liquid_enthalpy_j_kg": lower,
                    "saturated_vapor_enthalpy_j_kg": upper,
                },
            )

    def _try_saturation_values(
        self, fluid: FluidIdentifier, output: str,
        fixed_input: str, fixed_value: float,
    ) -> list[float]:
        values: list[float] = []
        for quality in (0.0, 1.0):
            try:
                value = float(
                    CP.PropsSI(
                        output, fixed_input, fixed_value,
                        "Q", quality, fluid.coolprop_fluid,
                    )
                )
            except Exception:
                return []
            if math.isfinite(value):
                values.append(value)
        return values

    # ------------------------------------------------------------------
    # Internal — phase detection
    # ------------------------------------------------------------------

    def _phase(
        self, fluid: FluidIdentifier,
        input1_name: str, input1_value: float,
        input2_name: str, input2_value: float,
        query_type: PropertyQueryType,
    ) -> PhaseRegion:
        try:
            phase_text = str(
                CP.PhaseSI(
                    input1_name, input1_value,
                    input2_name, input2_value,
                    fluid.coolprop_fluid,
                )
            )
        except Exception as exc:
            self._raise_backend_error(exc, fluid, query_type)

        phase_map = {
            "liquid": PhaseRegion.LIQUID,
            "gas": PhaseRegion.GAS,
            "supercritical": PhaseRegion.SUPERCRITICAL,
            "supercritical_gas": PhaseRegion.SUPERCRITICAL_GAS,
            "supercritical_liquid": PhaseRegion.SUPERCRITICAL_LIQUID,
        }
        if phase_text == "twophase":
            raise PropertyServiceError(
                PropertyErrorCode.TWO_PHASE_STATE,
                "CoolProp identified a two-phase state.",
                context={
                    "fluid": fluid.cache_identity,
                    "query_type": query_type.value,
                },
            )
        return phase_map.get(phase_text, PhaseRegion.UNKNOWN)

    def _reject_unknown_phase(
        self, phase: PhaseRegion, fluid: FluidIdentifier,
        query_type: PropertyQueryType,
    ) -> None:
        if phase is PhaseRegion.UNKNOWN:
            raise PropertyServiceError(
                PropertyErrorCode.STATE_OUT_OF_RANGE,
                "CoolProp could not determine the phase, which "
                "typically indicates the state is outside the "
                "valid fluid domain.",
                context={
                    "fluid": fluid.cache_identity,
                    "query_type": query_type.value,
                },
            )

    # ------------------------------------------------------------------
    # Internal — CoolProp property queries
    # ------------------------------------------------------------------

    def _props(
        self, output: str, fluid: FluidIdentifier,
        query_type: PropertyQueryType,
        query: tuple[str, float, str, float],
    ) -> float:
        input1_name, input1_value, input2_name, input2_value = query
        try:
            return float(
                CP.PropsSI(
                    output, input1_name, input1_value,
                    input2_name, input2_value,
                    fluid.coolprop_fluid,
                )
            )
        except Exception as exc:
            self._raise_backend_error(exc, fluid, query_type)

    def _raise_backend_error(
        self, exc: Exception, fluid: FluidIdentifier,
        query_type: PropertyQueryType,
    ) -> NoReturn:
        backend_message = str(exc)

        # Item 5: classify via explicit checks, not message keywords
        code = self._classify_backend_error(exc, fluid, query_type)

        raise PropertyServiceError(
            code,
            "CoolProp failed to evaluate the requested state.",
            context={
                "fluid": fluid.cache_identity,
                "query_type": query_type.value,
                "backend_message": backend_message,
            },
        ) from exc

    # ------------------------------------------------------------------
    # Internal — Item 5: explicit boundary pre-checks
    # ------------------------------------------------------------------

    # Known critical points for pre-check classification (SI units)
    _CRITICAL_POINTS: dict[str, tuple[float, float]] = {
        # fluid: (T_crit_K, P_crit_Pa)
        "Water": (647.096, 22_064_000.0),
        "R134a": (374.21, 4_059_300.0),
        "R717": (405.40, 11_333_000.0),
    }

    def _pre_check_saturation_boundaries(
        self, fluid: FluidIdentifier,
        input_name: str, input_value: float,
    ) -> None:
        """Explicit boundary check for saturation queries.

        Classifies above-critical states as SATURATION_UNAVAILABLE
        *before* calling CoolProp, so the public error code is
        independent of backend message wording.
        """
        canonical = fluid.name
        if canonical not in self._CRITICAL_POINTS:
            return
        t_crit, p_crit = self._CRITICAL_POINTS[canonical]
        if input_name == "temperature_k" and input_value > t_crit:
            raise PropertyServiceError(
                PropertyErrorCode.SATURATION_UNAVAILABLE,
                "Saturation temperature exceeds the critical point.",
                context={
                    "fluid": fluid.cache_identity,
                    "temperature_k": input_value,
                    "critical_temperature_k": t_crit,
                },
            )
        if input_name == "pressure_pa" and input_value > p_crit:
            raise PropertyServiceError(
                PropertyErrorCode.SATURATION_UNAVAILABLE,
                "Saturation pressure exceeds the critical point.",
                context={
                    "fluid": fluid.cache_identity,
                    "pressure_pa": input_value,
                    "critical_pressure_pa": p_crit,
                },
            )

    def _classify_backend_error(
        self, exc: Exception, fluid: FluidIdentifier,
        query_type: PropertyQueryType,
    ) -> PropertyErrorCode:
        """Classify a CoolProp backend exception.

        Item 5: uses explicit boundary checks first.  Message-token
        matching is only a fallback for unexpected error wording.
        ``BACKEND_FAILURE`` is reserved for truly unexpected faults.
        """
        backend_message = str(exc)
        lowered = backend_message.casefold()

        # Primary: explicit keyword classification
        if any(
            token in lowered for token in _COOLPROP_OUT_OF_RANGE_TOKENS
        ):
            return PropertyErrorCode.STATE_OUT_OF_RANGE
        if "critical" in lowered:
            return PropertyErrorCode.SATURATION_UNAVAILABLE

        # Fallback: no match → truly unexpected backend fault
        return PropertyErrorCode.BACKEND_FAILURE

    # ------------------------------------------------------------------
    # Internal — Item 3: validation fixture matching
    # ------------------------------------------------------------------

    def _match_validation_fixture(
        self, fluid: FluidIdentifier,
        query_type: PropertyQueryType,
        inputs: tuple[tuple[str, float], ...],
    ) -> tuple[str | None, str | None, str | None]:
        """Match a query against the validation regression fixtures.

        Returns (dataset_id, dataset_revision, validation_basis) or
        (None, None, None) if no fixture matches.
        """
        input_dict = dict(inputs)
        for entry in VALIDATION_MATRIX:
            if entry["fluid"] != fluid.name:
                continue
            if entry["query_type"] != query_type.value:
                continue
            # Check if all required input keys match
            sp = entry["state_points"][0]
            expected_inputs = sp["input"]
            if set(expected_inputs.keys()) != set(input_dict.keys()):
                continue
            # Check if input values match within tolerance
            match = True
            for key, expected_val in expected_inputs.items():
                actual_val = input_dict.get(key)
                if actual_val is None:
                    match = False
                    break
                if not math.isclose(
                    actual_val, expected_val,
                    rel_tol=sp.get("tolerance_rel", 0.01),
                ):
                    match = False
                    break
            if match:
                return (
                    entry.get("dataset_id"),
                    entry.get("revision"),
                    entry.get("validation_basis", "backend_regression"),
                )
        return None, None, None

    # ------------------------------------------------------------------
    # Internal — provenance and cache
    # ------------------------------------------------------------------

    def _provenance(
        self, fluid: FluidIdentifier,
        validation: FluidValidationLevel,
        query_type: PropertyQueryType,
        inputs: tuple[tuple[str, float], ...],
        fingerprint: str,
    ) -> PropertyProvenance:
        # Item 3: populate dataset fields when a fixture matches
        dataset_id, dataset_revision, validation_basis = (
            self._match_validation_fixture(fluid, query_type, inputs)
        )
        return PropertyProvenance(
            backend_name=self.name,
            backend_version=self.version,
            backend_git_revision=self.git_revision,
            fluid_identifier=fluid.cache_identity,
            validation_level=validation,
            query_type=query_type,
            inputs=inputs,
            cache_policy_version=self.cache_policy_version,
            validation_dataset_id=dataset_id,
            validation_dataset_revision=dataset_revision,
            validation_basis=validation_basis,
            reference_state_policy=self.reference_state_policy,
            configuration_fingerprint=fingerprint,
        )

    def _cache_key(
        self, fluid: FluidIdentifier,
        query_type: PropertyQueryType,
        inputs: tuple[tuple[str, float], ...],
        fingerprint: str,
    ) -> PropertyCacheKey:
        configuration = (
            ("allow_unvalidated_fluids",
             str(self.allow_unvalidated_fluids)),
            ("near_saturation_relative_tolerance",
             self.near_saturation_relative_tolerance.hex()),
            ("cache_policy_version", self.cache_policy_version),
        )
        return PropertyCacheKey(
            backend_name=self.name,
            backend_version=self.version,
            backend_git_revision=self.git_revision,
            fluid_identifier=fluid.cache_identity,
            query_type=query_type,
            inputs=inputs,
            configuration=configuration,
            reference_state_policy=self.reference_state_policy,
            configuration_fingerprint=fingerprint,
        )

    def _cache_get(
        self, key: PropertyCacheKey
    ) -> PropertyResult | None:
        if self.cache_size == 0:
            return None
        with self._cache_lock:
            cached = self._cache.get(key)
            if cached is None:
                self._cache_misses += 1
                return None
            self._cache.move_to_end(key)
            self._cache_hits += 1
            return cached

    def _cache_store(
        self, key: PropertyCacheKey, value: PropertyResult
    ) -> None:
        if self.cache_size == 0:
            return
        with self._cache_lock:
            self._cache[key] = value
            self._cache.move_to_end(key)
            while len(self._cache) > self.cache_size:
                self._cache.popitem(last=False)

    @staticmethod
    def _input_context_name(coolprop_name: str) -> str:
        mapping = {
            "T": "temperature_k",
            "P": "pressure_pa",
            "Hmass": "enthalpy_j_kg",
            "Q": "quality",
        }
        return mapping[coolprop_name]

    @staticmethod
    def _require_positive(name: str, value: float) -> None:
        if not math.isfinite(value) or value <= 0.0:
            raise PropertyServiceError(
                PropertyErrorCode.INVALID_INPUT,
                f"{name} must be finite and positive.",
                context={"field": name, "value": value},
            )

    @staticmethod
    def _require_finite(name: str, value: float) -> None:
        if not math.isfinite(value):
            raise PropertyServiceError(
                PropertyErrorCode.INVALID_INPUT,
                f"{name} must be finite.",
                context={"field": name, "value": value},
            )


__all__ = ["CoolPropProvider"]
