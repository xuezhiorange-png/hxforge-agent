from __future__ import annotations

import math
from collections import OrderedDict
from dataclasses import replace
from threading import RLock
from typing import NoReturn

import CoolProp.CoolProp as CP

from hexagent.properties.base import (
    FluidIdentifier,
    FluidState,
    FluidValidationLevel,
    PhaseRegion,
    PropertyCacheInfo,
    PropertyCacheKey,
    PropertyProvenance,
    PropertyQueryType,
    PropertyResult,
    SaturationState,
)
from hexagent.properties.errors import PropertyErrorCode, PropertyServiceError


class CoolPropProvider:
    """Deterministic CoolProp HEOS property provider."""

    name = "CoolProp"
    cache_policy_version = "1.0"

    _TIER_1_ALIASES = {
        "water": "Water",
        "air": "Air",
        "r134a": "R134a",
        "r717": "R717",
        "ammonia": "R717",
    }

    def __init__(
        self,
        *,
        allow_unvalidated_fluids: bool = False,
        near_saturation_relative_tolerance: float = 1e-6,
        cache_size: int = 256,
    ) -> None:
        if not math.isfinite(near_saturation_relative_tolerance):
            raise ValueError("near_saturation_relative_tolerance must be finite")
        if not 0.0 < near_saturation_relative_tolerance < 1.0:
            raise ValueError("near_saturation_relative_tolerance must be in (0, 1)")
        if cache_size < 0:
            raise ValueError("cache_size must be non-negative")

        self.version = str(CP.get_global_param_string("version"))
        self.git_revision = str(CP.get_global_param_string("gitrevision"))
        self.allow_unvalidated_fluids = allow_unvalidated_fluids
        self.near_saturation_relative_tolerance = (
            near_saturation_relative_tolerance
        )
        self.cache_size = cache_size
        self._cache: OrderedDict[PropertyCacheKey, PropertyResult] = OrderedDict()
        self._cache_hits = 0
        self._cache_misses = 0
        self._cache_lock = RLock()

    def state_tp(
        self,
        fluid: FluidIdentifier | str,
        temperature_k: float,
        pressure_pa: float,
    ) -> FluidState:
        identifier, validation = self._resolve_fluid(fluid)
        self._require_positive("temperature_k", temperature_k)
        self._require_positive("pressure_pa", pressure_pa)
        inputs = (
            ("temperature_k", temperature_k),
            ("pressure_pa", pressure_pa),
        )
        key = self._cache_key(identifier, PropertyQueryType.TP, inputs)
        cached = self._cache_get(key)
        if cached is not None:
            if not isinstance(cached, FluidState):
                raise RuntimeError("Property cache type mismatch for TP query")
            return cached

        state = self._state_tp_uncached(
            identifier,
            validation,
            temperature_k,
            pressure_pa,
        )
        self._cache_store(key, state)
        return state

    def state_ph(
        self,
        fluid: FluidIdentifier | str,
        pressure_pa: float,
        enthalpy_j_kg: float,
    ) -> FluidState:
        identifier, validation = self._resolve_fluid(fluid)
        self._require_positive("pressure_pa", pressure_pa)
        self._require_finite("enthalpy_j_kg", enthalpy_j_kg)
        inputs = (
            ("pressure_pa", pressure_pa),
            ("enthalpy_j_kg", enthalpy_j_kg),
        )
        key = self._cache_key(identifier, PropertyQueryType.PH, inputs)
        cached = self._cache_get(key)
        if cached is not None:
            if not isinstance(cached, FluidState):
                raise RuntimeError("Property cache type mismatch for PH query")
            return cached

        state = self._state_ph_uncached(
            identifier,
            validation,
            pressure_pa,
            enthalpy_j_kg,
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
        inputs = (("pressure_pa", pressure_pa),)
        query_type = PropertyQueryType.SATURATION_P
        key = self._cache_key(identifier, query_type, inputs)
        cached = self._cache_get(key)
        if cached is not None:
            if not isinstance(cached, SaturationState):
                raise RuntimeError("Property cache type mismatch for saturation query")
            return cached

        state = self._saturation_pressure_uncached(
            identifier,
            validation,
            pressure_pa,
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
        inputs = (("temperature_k", temperature_k),)
        query_type = PropertyQueryType.SATURATION_T
        key = self._cache_key(identifier, query_type, inputs)
        cached = self._cache_get(key)
        if cached is not None:
            if not isinstance(cached, SaturationState):
                raise RuntimeError("Property cache type mismatch for saturation query")
            return cached

        state = self._saturation_temperature_uncached(
            identifier,
            validation,
            temperature_k,
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

    def _state_tp_uncached(
        self,
        fluid: FluidIdentifier,
        validation: FluidValidationLevel,
        temperature_k: float,
        pressure_pa: float,
    ) -> FluidState:
        self._check_tp_near_saturation(fluid, temperature_k, pressure_pa)
        phase = self._phase(
            fluid,
            "T",
            temperature_k,
            "P",
            pressure_pa,
            PropertyQueryType.TP,
        )
        self._reject_unknown_phase(phase, fluid, PropertyQueryType.TP)
        return self._build_state(
            fluid,
            validation,
            PropertyQueryType.TP,
            "T",
            temperature_k,
            "P",
            pressure_pa,
            phase=phase,
            quality=None,
        )

    def _state_ph_uncached(
        self,
        fluid: FluidIdentifier,
        validation: FluidValidationLevel,
        pressure_pa: float,
        enthalpy_j_kg: float,
    ) -> FluidState:
        self._check_ph_saturation(fluid, pressure_pa, enthalpy_j_kg)
        phase = self._phase(
            fluid,
            "P",
            pressure_pa,
            "Hmass",
            enthalpy_j_kg,
            PropertyQueryType.PH,
        )
        self._reject_unknown_phase(phase, fluid, PropertyQueryType.PH)
        return self._build_state(
            fluid,
            validation,
            PropertyQueryType.PH,
            "P",
            pressure_pa,
            "Hmass",
            enthalpy_j_kg,
            phase=phase,
            quality=None,
        )

    def _saturation_pressure_uncached(
        self,
        fluid: FluidIdentifier,
        validation: FluidValidationLevel,
        pressure_pa: float,
    ) -> SaturationState:
        query_type = PropertyQueryType.SATURATION_P
        try:
            liquid = self._build_state(
                fluid,
                validation,
                query_type,
                "P",
                pressure_pa,
                "Q",
                0.0,
                phase=PhaseRegion.SATURATED_LIQUID,
                quality=0.0,
            )
            vapor = self._build_state(
                fluid,
                validation,
                query_type,
                "P",
                pressure_pa,
                "Q",
                1.0,
                phase=PhaseRegion.SATURATED_VAPOR,
                quality=1.0,
            )
        except PropertyServiceError as exc:
            self._raise_saturation_unavailable(
                exc,
                fluid,
                "pressure_pa",
                pressure_pa,
            )
        provenance = self._provenance(
            fluid,
            validation,
            query_type,
            (("pressure_pa", pressure_pa),),
        )
        return SaturationState(
            query_type=query_type,
            input_value=pressure_pa,
            liquid=liquid,
            vapor=vapor,
            provenance=provenance,
        )

    def _saturation_temperature_uncached(
        self,
        fluid: FluidIdentifier,
        validation: FluidValidationLevel,
        temperature_k: float,
    ) -> SaturationState:
        query_type = PropertyQueryType.SATURATION_T
        try:
            liquid = self._build_state(
                fluid,
                validation,
                query_type,
                "T",
                temperature_k,
                "Q",
                0.0,
                phase=PhaseRegion.SATURATED_LIQUID,
                quality=0.0,
            )
            vapor = self._build_state(
                fluid,
                validation,
                query_type,
                "T",
                temperature_k,
                "Q",
                1.0,
                phase=PhaseRegion.SATURATED_VAPOR,
                quality=1.0,
            )
        except PropertyServiceError as exc:
            self._raise_saturation_unavailable(
                exc,
                fluid,
                "temperature_k",
                temperature_k,
            )
        provenance = self._provenance(
            fluid,
            validation,
            query_type,
            (("temperature_k", temperature_k),),
        )
        return SaturationState(
            query_type=query_type,
            input_value=temperature_k,
            liquid=liquid,
            vapor=vapor,
            provenance=provenance,
        )

    def _raise_saturation_unavailable(
        self,
        exc: PropertyServiceError,
        fluid: FluidIdentifier,
        input_name: str,
        input_value: float,
    ) -> NoReturn:
        if exc.code not in {
            PropertyErrorCode.STATE_OUT_OF_RANGE,
            PropertyErrorCode.BACKEND_FAILURE,
        }:
            raise exc
        raise PropertyServiceError(
            PropertyErrorCode.SATURATION_UNAVAILABLE,
            "Saturation properties are unavailable at the requested state.",
            context={
                "fluid": fluid.cache_identity,
                input_name: input_value,
                "backend_error": exc.as_dict(),
            },
        ) from exc

    def _build_state(
        self,
        fluid: FluidIdentifier,
        validation: FluidValidationLevel,
        query_type: PropertyQueryType,
        input1_name: str,
        input1_value: float,
        input2_name: str,
        input2_value: float,
        *,
        phase: PhaseRegion,
        quality: float | None,
    ) -> FluidState:
        inputs = (
            (self._input_context_name(input1_name), input1_value),
            (self._input_context_name(input2_name), input2_value),
        )
        query = (
            input1_name,
            input1_value,
            input2_name,
            input2_value,
        )
        values = {
            "temperature_k": self._props("T", fluid, query_type, query),
            "pressure_pa": self._props("P", fluid, query_type, query),
            "density_kg_m3": self._props("Dmass", fluid, query_type, query),
            "cp_j_kg_k": self._props("Cpmass", fluid, query_type, query),
            "viscosity_pa_s": self._props(
                "VISCOSITY",
                fluid,
                query_type,
                query,
            ),
            "conductivity_w_m_k": self._props(
                "CONDUCTIVITY",
                fluid,
                query_type,
                query,
            ),
            "enthalpy_j_kg": self._props("Hmass", fluid, query_type, query),
            "entropy_j_kg_k": self._props("Smass", fluid, query_type, query),
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
                fluid,
                validation,
                query_type,
                inputs,
            ),
        )

    def _validate_outputs(
        self,
        values: dict[str, float],
        fluid: FluidIdentifier,
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
            "temperature_k",
            "pressure_pa",
            "density_kg_m3",
            "cp_j_kg_k",
            "viscosity_pa_s",
            "conductivity_w_m_k",
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

    def _resolve_fluid(
        self,
        fluid: FluidIdentifier | str,
    ) -> tuple[FluidIdentifier, FluidValidationLevel]:
        identifier = FluidIdentifier.from_value(fluid)
        if identifier.backend.upper() != "HEOS":
            raise PropertyServiceError(
                PropertyErrorCode.UNSUPPORTED_BACKEND,
                "Only the CoolProp HEOS backend is approved in v0.1.",
                context={"backend": identifier.backend},
            )
        validation = FluidValidationLevel.UNVALIDATED
        if not identifier.components:
            canonical = self._TIER_1_ALIASES.get(identifier.name.casefold())
            if canonical is not None:
                identifier = replace(
                    identifier,
                    name=canonical,
                    backend="HEOS",
                )
                validation = FluidValidationLevel.TIER_1_VALIDATED

        self._assert_fluid_exists(identifier)
        if (
            validation is FluidValidationLevel.UNVALIDATED
            and not self.allow_unvalidated_fluids
        ):
            raise PropertyServiceError(
                PropertyErrorCode.UNVALIDATED_FLUID,
                "The requested fluid is not in the approved Tier-1 validation set.",
                context={"fluid": identifier.cache_identity},
            )
        return identifier, validation

    def _assert_fluid_exists(self, fluid: FluidIdentifier) -> None:
        try:
            molar_mass = float(CP.PropsSI("M", fluid.coolprop_fluid))
        except Exception as exc:
            raise PropertyServiceError(
                PropertyErrorCode.INVALID_FLUID,
                "CoolProp could not resolve the requested fluid identifier.",
                context={
                    "fluid": fluid.cache_identity,
                    "backend_message": str(exc),
                },
            ) from exc
        if not math.isfinite(molar_mass) or molar_mass <= 0.0:
            raise PropertyServiceError(
                PropertyErrorCode.INVALID_FLUID,
                "CoolProp returned an invalid molar mass for the fluid.",
                context={
                    "fluid": fluid.cache_identity,
                    "molar_mass": molar_mass,
                },
            )

    def _check_tp_near_saturation(
        self,
        fluid: FluidIdentifier,
        temperature_k: float,
        pressure_pa: float,
    ) -> None:
        saturation_pressures = self._try_saturation_values(
            fluid,
            "P",
            "T",
            temperature_k,
        )
        for saturation_pressure in saturation_pressures:
            denominator = max(abs(saturation_pressure), 1.0)
            relative_distance = abs(pressure_pa - saturation_pressure) / denominator
            if relative_distance <= self.near_saturation_relative_tolerance:
                raise PropertyServiceError(
                    PropertyErrorCode.NEAR_SATURATION,
                    "TP state is too close to the saturation boundary.",
                    context={
                        "fluid": fluid.cache_identity,
                        "temperature_k": temperature_k,
                        "pressure_pa": pressure_pa,
                        "saturation_pressure_pa": saturation_pressure,
                        "relative_distance": relative_distance,
                    },
                )

    def _check_ph_saturation(
        self,
        fluid: FluidIdentifier,
        pressure_pa: float,
        enthalpy_j_kg: float,
    ) -> None:
        saturation_enthalpies = self._try_saturation_values(
            fluid,
            "Hmass",
            "P",
            pressure_pa,
        )
        if len(saturation_enthalpies) != 2:
            return
        lower, upper = sorted(saturation_enthalpies)
        scale = max(abs(lower), abs(upper), 1.0)
        boundary_distance = min(
            abs(enthalpy_j_kg - lower),
            abs(enthalpy_j_kg - upper),
        )
        if boundary_distance <= self.near_saturation_relative_tolerance * scale:
            raise PropertyServiceError(
                PropertyErrorCode.NEAR_SATURATION,
                "PH state is too close to a saturation boundary.",
                context={
                    "fluid": fluid.cache_identity,
                    "pressure_pa": pressure_pa,
                    "enthalpy_j_kg": enthalpy_j_kg,
                    "saturated_liquid_enthalpy_j_kg": lower,
                    "saturated_vapor_enthalpy_j_kg": upper,
                },
            )
        if lower < enthalpy_j_kg < upper:
            raise PropertyServiceError(
                PropertyErrorCode.TWO_PHASE_STATE,
                "PH state lies inside the two-phase enthalpy interval.",
                context={
                    "fluid": fluid.cache_identity,
                    "pressure_pa": pressure_pa,
                    "enthalpy_j_kg": enthalpy_j_kg,
                    "saturated_liquid_enthalpy_j_kg": lower,
                    "saturated_vapor_enthalpy_j_kg": upper,
                },
            )

    def _try_saturation_values(
        self,
        fluid: FluidIdentifier,
        output: str,
        fixed_input: str,
        fixed_value: float,
    ) -> list[float]:
        values: list[float] = []
        for quality in (0.0, 1.0):
            try:
                value = float(
                    CP.PropsSI(
                        output,
                        fixed_input,
                        fixed_value,
                        "Q",
                        quality,
                        fluid.coolprop_fluid,
                    )
                )
            except Exception:
                return []
            if math.isfinite(value):
                values.append(value)
        return values

    def _phase(
        self,
        fluid: FluidIdentifier,
        input1_name: str,
        input1_value: float,
        input2_name: str,
        input2_value: float,
        query_type: PropertyQueryType,
    ) -> PhaseRegion:
        try:
            phase_text = str(
                CP.PhaseSI(
                    input1_name,
                    input1_value,
                    input2_name,
                    input2_value,
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
        self,
        phase: PhaseRegion,
        fluid: FluidIdentifier,
        query_type: PropertyQueryType,
    ) -> None:
        if phase is PhaseRegion.UNKNOWN:
            raise PropertyServiceError(
                PropertyErrorCode.BACKEND_FAILURE,
                "CoolProp returned an unknown phase classification.",
                context={
                    "fluid": fluid.cache_identity,
                    "query_type": query_type.value,
                },
            )

    def _props(
        self,
        output: str,
        fluid: FluidIdentifier,
        query_type: PropertyQueryType,
        query: tuple[str, float, str, float],
    ) -> float:
        input1_name, input1_value, input2_name, input2_value = query
        try:
            return float(
                CP.PropsSI(
                    output,
                    input1_name,
                    input1_value,
                    input2_name,
                    input2_value,
                    fluid.coolprop_fluid,
                )
            )
        except Exception as exc:
            self._raise_backend_error(exc, fluid, query_type)

    def _raise_backend_error(
        self,
        exc: Exception,
        fluid: FluidIdentifier,
        query_type: PropertyQueryType,
    ) -> NoReturn:
        backend_message = str(exc)
        lowered = backend_message.casefold()
        range_tokens = (
            "out of range",
            "triple",
            "critical",
            "unable to solve",
        )
        code = PropertyErrorCode.BACKEND_FAILURE
        if any(token in lowered for token in range_tokens):
            code = PropertyErrorCode.STATE_OUT_OF_RANGE
        raise PropertyServiceError(
            code,
            "CoolProp failed to evaluate the requested state.",
            context={
                "fluid": fluid.cache_identity,
                "query_type": query_type.value,
                "backend_message": backend_message,
            },
        ) from exc

    def _provenance(
        self,
        fluid: FluidIdentifier,
        validation: FluidValidationLevel,
        query_type: PropertyQueryType,
        inputs: tuple[tuple[str, float], ...],
    ) -> PropertyProvenance:
        return PropertyProvenance(
            backend_name=self.name,
            backend_version=self.version,
            backend_git_revision=self.git_revision,
            fluid_identifier=fluid.cache_identity,
            validation_level=validation,
            query_type=query_type,
            inputs=inputs,
            cache_policy_version=self.cache_policy_version,
        )

    def _cache_key(
        self,
        fluid: FluidIdentifier,
        query_type: PropertyQueryType,
        inputs: tuple[tuple[str, float], ...],
    ) -> PropertyCacheKey:
        configuration = (
            (
                "allow_unvalidated_fluids",
                str(self.allow_unvalidated_fluids),
            ),
            (
                "near_saturation_relative_tolerance",
                self.near_saturation_relative_tolerance.hex(),
            ),
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
        )

    def _cache_get(self, key: PropertyCacheKey) -> PropertyResult | None:
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
        self,
        key: PropertyCacheKey,
        value: PropertyResult,
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
        return {
            "T": "temperature_k",
            "P": "pressure_pa",
            "Hmass": "enthalpy_j_kg",
            "Q": "quality",
        }[coolprop_name]

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
