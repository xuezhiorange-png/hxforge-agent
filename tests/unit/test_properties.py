from __future__ import annotations

import math

import pytest

from hexagent.properties import CoolPropProvider, PropertyErrorCode, PropertyServiceError
from hexagent.properties.base import (
    FluidIdentifier,
    FluidValidationLevel,
    PhaseRegion,
    PropertyQueryType,
)


def _assert_single_phase_state(state: object) -> None:
    from hexagent.properties.base import FluidState

    assert isinstance(state, FluidState)
    assert state.temperature_k > 0.0
    assert state.pressure_pa > 0.0
    assert state.density_kg_m3 > 0.0
    assert state.cp_j_kg_k > 0.0
    assert state.viscosity_pa_s > 0.0
    assert state.conductivity_w_m_k > 0.0
    assert math.isfinite(state.enthalpy_j_kg)
    assert math.isfinite(state.entropy_j_kg_k)
    assert state.quality is None
    assert state.phase not in {
        PhaseRegion.UNKNOWN,
        PhaseRegion.SATURATED_LIQUID,
        PhaseRegion.SATURATED_VAPOR,
    }


@pytest.mark.parametrize(
    ("fluid", "temperature_k", "pressure_pa"),
    [
        ("Water", 300.0, 101_325.0),
        ("Air", 300.0, 101_325.0),
        ("R134a", 300.0, 2_000_000.0),
        ("R717", 300.0, 2_000_000.0),
    ],
)
def test_tier_one_tp_states(
    fluid: str,
    temperature_k: float,
    pressure_pa: float,
) -> None:
    state = CoolPropProvider().state_tp(fluid, temperature_k, pressure_pa)
    _assert_single_phase_state(state)
    assert state.provenance.validation_level is FluidValidationLevel.TIER_1_VALIDATED
    assert state.provenance.query_type is PropertyQueryType.TP
    assert state.provenance.backend_name == "CoolProp"
    assert state.provenance.backend_version
    assert state.provenance.backend_git_revision


@pytest.mark.parametrize(
    ("fluid", "temperature_k", "pressure_pa"),
    [
        ("Water", 330.0, 300_000.0),
        ("R134a", 300.0, 2_000_000.0),
    ],
)
def test_tp_ph_cross_consistency(
    fluid: str,
    temperature_k: float,
    pressure_pa: float,
) -> None:
    provider = CoolPropProvider()
    state_tp = provider.state_tp(fluid, temperature_k, pressure_pa)
    state_ph = provider.state_ph(fluid, pressure_pa, state_tp.enthalpy_j_kg)

    assert state_ph.temperature_k == pytest.approx(state_tp.temperature_k, rel=1e-8)
    assert state_ph.pressure_pa == pytest.approx(state_tp.pressure_pa, rel=1e-12)
    assert state_ph.density_kg_m3 == pytest.approx(state_tp.density_kg_m3, rel=1e-7)
    assert state_ph.provenance.query_type is PropertyQueryType.PH


def test_saturation_at_pressure_returns_liquid_and_vapor() -> None:
    saturation = CoolPropProvider().saturation_at_pressure("R134a", 500_000.0)

    assert saturation.query_type is PropertyQueryType.SATURATION_P
    assert saturation.liquid.quality == 0.0
    assert saturation.vapor.quality == 1.0
    assert saturation.liquid.phase is PhaseRegion.SATURATED_LIQUID
    assert saturation.vapor.phase is PhaseRegion.SATURATED_VAPOR
    assert saturation.liquid.density_kg_m3 > saturation.vapor.density_kg_m3
    assert saturation.vapor.enthalpy_j_kg > saturation.liquid.enthalpy_j_kg


def test_saturation_at_temperature_returns_liquid_and_vapor() -> None:
    saturation = CoolPropProvider().saturation_at_temperature("R134a", 273.15)

    assert saturation.query_type is PropertyQueryType.SATURATION_T
    assert saturation.liquid.temperature_k == pytest.approx(273.15)
    assert saturation.vapor.temperature_k == pytest.approx(273.15)
    assert saturation.liquid.pressure_pa > 0.0
    assert saturation.vapor.pressure_pa > 0.0


def test_exact_tp_saturation_is_rejected() -> None:
    provider = CoolPropProvider()
    saturation = provider.saturation_at_pressure("R134a", 500_000.0)

    with pytest.raises(PropertyServiceError) as exc_info:
        provider.state_tp(
            "R134a",
            saturation.liquid.temperature_k,
            500_000.0,
        )

    assert exc_info.value.code is PropertyErrorCode.NEAR_SATURATION


def test_ph_inside_two_phase_interval_is_rejected() -> None:
    provider = CoolPropProvider()
    saturation = provider.saturation_at_pressure("R134a", 500_000.0)
    midpoint = (
        saturation.liquid.enthalpy_j_kg + saturation.vapor.enthalpy_j_kg
    ) / 2.0

    with pytest.raises(PropertyServiceError) as exc_info:
        provider.state_ph("R134a", 500_000.0, midpoint)

    assert exc_info.value.code is PropertyErrorCode.TWO_PHASE_STATE


def test_invalid_fluid_error_is_structured() -> None:
    provider = CoolPropProvider(allow_unvalidated_fluids=True)

    with pytest.raises(PropertyServiceError) as exc_info:
        provider.state_tp("DefinitelyNotAFluid", 300.0, 101_325.0)

    assert exc_info.value.code is PropertyErrorCode.INVALID_FLUID
    assert exc_info.value.as_dict()["code"] == "property_invalid_fluid"


def test_unvalidated_fluid_requires_explicit_opt_in() -> None:
    with pytest.raises(PropertyServiceError) as exc_info:
        CoolPropProvider().state_tp("R32", 300.0, 2_000_000.0)

    assert exc_info.value.code is PropertyErrorCode.UNVALIDATED_FLUID

    state = CoolPropProvider(allow_unvalidated_fluids=True).state_tp(
        "R32", 300.0, 2_000_000.0
    )
    assert state.provenance.validation_level is FluidValidationLevel.UNVALIDATED


def test_invalid_state_input_is_structured() -> None:
    with pytest.raises(PropertyServiceError) as exc_info:
        CoolPropProvider().state_tp("Water", 300.0, 0.0)

    assert exc_info.value.code is PropertyErrorCode.INVALID_INPUT
    assert exc_info.value.context["field"] == "pressure_pa"


def test_cache_key_is_deterministic_and_observable() -> None:
    provider = CoolPropProvider(cache_size=4)
    first = provider.state_tp("Water", 300.0, 101_325.0)
    second = provider.state_tp("Water", 300.0, 101_325.0)
    info = provider.cache_info()

    assert first is second
    assert info.misses == 1
    assert info.hits == 1
    assert info.size == 1
    assert info.max_size == 4

    provider.clear_cache()
    assert provider.cache_info().size == 0


def test_fluid_identifier_mixture_identity_is_order_independent() -> None:
    first = FluidIdentifier.from_components({"R32": 0.7, "R125": 0.3})
    second = FluidIdentifier.from_components({"R125": 0.3, "R32": 0.7})

    assert first.cache_identity == second.cache_identity
    assert first.cache_identity.startswith("HEOS::")


def test_fluid_identifier_rejects_bad_composition() -> None:
    with pytest.raises(PropertyServiceError) as exc_info:
        FluidIdentifier.from_components({"R32": 0.8, "R125": 0.3})

    assert exc_info.value.code is PropertyErrorCode.INVALID_FLUID


def test_ammonia_alias_resolves_to_r717() -> None:
    state = CoolPropProvider().state_tp("Ammonia", 300.0, 2_000_000.0)

    assert state.provenance.fluid_identifier == "HEOS::R717"
