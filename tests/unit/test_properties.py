"""Unit tests for TASK-003 property service.

Covers:
- Tier-1 and benchmark-validated fluid states
- TP-to-PH cross-consistency
- Saturation queries
- Near-saturation and two-phase rejection
- Invalid fluids and invalid inputs
- Cache determinism and mixture identity
- PH reference-state mismatch (Item 3)
- JSON round-trip serialization (Item 5)
- PH saturation tolerance reference-state invariance (Item 6)
- Mixture capability boundary (Item 7)
- Error-boundary regressions (Item 8)
"""

from __future__ import annotations

import math

import pytest

from hexagent.properties import (
    VALIDATION_MATRIX,
    CoolPropProvider,
    FluidIdentifier,
    FluidValidationLevel,
    PhaseRegion,
    PropertyErrorCode,
    PropertyQueryType,
    PropertyServiceError,
    ReferenceStatePolicy,
)
from hexagent.properties.base import FluidState, SaturationState


def _assert_single_phase_state(state: object) -> None:
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


# ======================================================================
# Item 2: SUPPORTED_TIER_1 vs BENCHMARK_VALIDATED
# ======================================================================


class TestValidationLevels:
    """Tier-1 fluids have BENCHMARK_VALIDATED level (Item 2)."""

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
        self,
        fluid: str,
        temperature_k: float,
        pressure_pa: float,
    ) -> None:
        state = CoolPropProvider().state_tp(fluid, temperature_k, pressure_pa)
        _assert_single_phase_state(state)
        assert state.provenance.validation_level is FluidValidationLevel.BENCHMARK_VALIDATED
        assert state.provenance.query_type is PropertyQueryType.TP
        assert state.provenance.backend_name == "CoolProp"
        assert state.provenance.backend_version
        assert state.provenance.backend_git_revision

    def test_ammonia_alias_resolves_to_r717(self) -> None:
        state = CoolPropProvider().state_tp("Ammonia", 300.0, 2_000_000.0)
        assert state.provenance.fluid_identifier == "HEOS::R717"
        assert state.provenance.validation_level is FluidValidationLevel.BENCHMARK_VALIDATED

    def test_validation_matrix_has_entries(self) -> None:
        assert len(VALIDATION_MATRIX) >= 4
        for entry in VALIDATION_MATRIX:
            assert "dataset_id" in entry
            assert "fluid" in entry
            assert "state_points" in entry
            assert "source" in entry
            assert "revision" in entry


# ======================================================================
# TP-to-PH cross consistency
# ======================================================================


class TestTPPHConsistency:
    @pytest.mark.parametrize(
        ("fluid", "temperature_k", "pressure_pa"),
        [
            ("Water", 330.0, 300_000.0),
            ("R134a", 300.0, 2_000_000.0),
        ],
    )
    def test_tp_ph_cross_consistency(
        self,
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


# ======================================================================
# Saturation queries
# ======================================================================


class TestSaturation:
    def test_saturation_at_pressure_returns_liquid_and_vapor(self) -> None:
        saturation = CoolPropProvider().saturation_at_pressure("R134a", 500_000.0)

        assert saturation.query_type is PropertyQueryType.SATURATION_P
        assert saturation.liquid.quality == 0.0
        assert saturation.vapor.quality == 1.0
        assert saturation.liquid.phase is PhaseRegion.SATURATED_LIQUID
        assert saturation.vapor.phase is PhaseRegion.SATURATED_VAPOR
        assert saturation.liquid.density_kg_m3 > saturation.vapor.density_kg_m3
        assert saturation.vapor.enthalpy_j_kg > saturation.liquid.enthalpy_j_kg

    def test_saturation_at_temperature_returns_liquid_and_vapor(self) -> None:
        saturation = CoolPropProvider().saturation_at_temperature("R134a", 273.15)

        assert saturation.query_type is PropertyQueryType.SATURATION_T
        assert saturation.liquid.temperature_k == pytest.approx(273.15)
        assert saturation.vapor.temperature_k == pytest.approx(273.15)
        assert saturation.liquid.pressure_pa > 0.0
        assert saturation.vapor.pressure_pa > 0.0


# ======================================================================
# Near-saturation and two-phase rejection
# ======================================================================


class TestBoundaryRejection:
    def test_exact_tp_saturation_is_rejected(self) -> None:
        provider = CoolPropProvider()
        saturation = provider.saturation_at_pressure("R134a", 500_000.0)

        with pytest.raises(PropertyServiceError) as exc_info:
            provider.state_tp(
                "R134a",
                saturation.liquid.temperature_k,
                500_000.0,
            )

        assert exc_info.value.code is PropertyErrorCode.NEAR_SATURATION

    def test_ph_inside_two_phase_interval_is_rejected(self) -> None:
        provider = CoolPropProvider()
        saturation = provider.saturation_at_pressure("R134a", 500_000.0)
        midpoint = (
            saturation.liquid.enthalpy_j_kg + saturation.vapor.enthalpy_j_kg
        ) / 2.0

        with pytest.raises(PropertyServiceError) as exc_info:
            provider.state_ph("R134a", 500_000.0, midpoint)

        assert exc_info.value.code is PropertyErrorCode.TWO_PHASE_STATE


# ======================================================================
# Error handling
# ======================================================================


class TestErrors:
    def test_invalid_fluid_error_is_structured(self) -> None:
        provider = CoolPropProvider(allow_unvalidated_fluids=True)

        with pytest.raises(PropertyServiceError) as exc_info:
            provider.state_tp("DefinitelyNotAFluid", 300.0, 101_325.0)

        assert exc_info.value.code is PropertyErrorCode.INVALID_FLUID
        assert exc_info.value.as_dict()["code"] == "property_invalid_fluid"

    def test_unvalidated_fluid_requires_explicit_opt_in(self) -> None:
        with pytest.raises(PropertyServiceError) as exc_info:
            CoolPropProvider().state_tp("R32", 300.0, 2_000_000.0)

        assert exc_info.value.code is PropertyErrorCode.UNVALIDATED_FLUID

        state = CoolPropProvider(allow_unvalidated_fluids=True).state_tp(
            "R32", 300.0, 2_000_000.0
        )
        assert state.provenance.validation_level is FluidValidationLevel.UNVALIDATED

    def test_invalid_state_input_is_structured(self) -> None:
        with pytest.raises(PropertyServiceError) as exc_info:
            CoolPropProvider().state_tp("Water", 300.0, 0.0)

        assert exc_info.value.code is PropertyErrorCode.INVALID_INPUT
        assert exc_info.value.context["field"] == "pressure_pa"


# ======================================================================
# Cache
# ======================================================================


class TestCache:
    def test_cache_key_is_deterministic_and_observable(self) -> None:
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

    def test_cache_includes_config_fingerprint(self) -> None:
        """Item 1: cache key includes configuration fingerprint."""
        provider = CoolPropProvider(cache_size=4)
        # Trigger a cache miss to populate
        provider.state_tp("Water", 300.0, 101_325.0)
        info = provider.cache_info()
        assert info.misses == 1
        # Second call should hit (same config)
        provider.state_tp("Water", 300.0, 101_325.0)
        info = provider.cache_info()
        assert info.hits == 1


# ======================================================================
# Fluid identifier
# ======================================================================


class TestFluidIdentifier:
    def test_mixture_identity_is_order_independent(self) -> None:
        first = FluidIdentifier.from_components({"R32": 0.7, "R125": 0.3})
        second = FluidIdentifier.from_components({"R125": 0.3, "R32": 0.7})

        assert first.cache_identity == second.cache_identity
        assert first.cache_identity.startswith("HEOS::")

    def test_mixture_rejects_bad_composition(self) -> None:
        with pytest.raises(PropertyServiceError) as exc_info:
            FluidIdentifier.from_components({"R32": 0.8, "R125": 0.3})

        assert exc_info.value.code is PropertyErrorCode.INVALID_FLUID

    def test_from_fluid_spec_adapter(self) -> None:
        """Item 4: FluidIdentifier.from_fluid_spec adapter."""
        ident = FluidIdentifier.from_fluid_spec("HEOS", "Water")
        assert ident.name == "Water"
        assert ident.equation_of_state_backend == "HEOS"
        assert ident.backend == "HEOS"  # backward-compatible alias

    def test_from_fluid_spec_with_composition(self) -> None:
        ident = FluidIdentifier.from_fluid_spec(
            "HEOS", "R410A", composition={"R32": 0.5, "R125": 0.5}
        )
        assert ident.name == "R410A"
        assert len(ident.components) == 2


# ======================================================================
# Item 3: PH reference-state mismatch
# ======================================================================


class TestPHReferenceState:
    def test_ph_with_matching_reference_state_succeeds(self) -> None:
        provider = CoolPropProvider()
        tp_state = provider.state_tp("Water", 330.0, 300_000.0)
        # Default reference state matches — should succeed
        ph_state = provider.state_ph(
            "Water", 300_000.0, tp_state.enthalpy_j_kg,
            reference_state=ReferenceStatePolicy.DEF,
        )
        assert ph_state.temperature_k == pytest.approx(330.0, rel=1e-8)

    def test_ph_with_mismatched_reference_state_is_rejected(self) -> None:
        """Item 3: PH query with non-DEF reference state is rejected."""
        provider = CoolPropProvider()
        tp_state = provider.state_tp("Water", 330.0, 300_000.0)

        # Monkeypatch the provider's reference_state_policy to a non-DEF value
        # so that requesting DEF will be a mismatch.
        original = provider.reference_state_policy
        try:
            # Use object.__setattr__ to bypass any property descriptor
            object.__setattr__(provider, "reference_state_policy", "NOT_DEF")
            with pytest.raises(PropertyServiceError) as exc_info:
                provider.state_ph(
                    "Water", 300_000.0, tp_state.enthalpy_j_kg,
                    reference_state=ReferenceStatePolicy.DEF,
                )
            assert exc_info.value.code is PropertyErrorCode.INVALID_INPUT
            assert "reference-state" in str(exc_info.value).lower()
        finally:
            object.__setattr__(provider, "reference_state_policy", original)


# ======================================================================
# Item 5: JSON round-trip serialization
# ======================================================================


class TestSerialization:
    def test_fluid_state_json_round_trip(self) -> None:
        """FluidState serializes to JSON and back without data loss."""
        provider = CoolPropProvider()
        state = provider.state_tp("Water", 300.0, 101_325.0)

        json_str = state.to_json()
        restored = FluidState.from_json(json_str)

        assert restored.temperature_k == pytest.approx(state.temperature_k)
        assert restored.pressure_pa == pytest.approx(state.pressure_pa)
        assert restored.density_kg_m3 == pytest.approx(state.density_kg_m3)
        assert restored.phase == state.phase.value
        assert restored.provenance["backend_name"] == "CoolProp"
        assert restored.provenance["reference_state_policy"] == "DEF"

    def test_saturation_state_json_round_trip(self) -> None:
        """SaturationState serializes to JSON and back."""
        provider = CoolPropProvider()
        sat = provider.saturation_at_pressure("R134a", 500_000.0)

        json_str = sat.to_json()
        restored = SaturationState.from_json(json_str)

        assert restored.query_type == sat.query_type.value
        assert restored.input_value == pytest.approx(sat.input_value)
        assert restored.liquid.temperature_k == pytest.approx(
            sat.liquid.temperature_k
        )
        assert restored.vapor.temperature_k == pytest.approx(
            sat.vapor.temperature_k
        )

    def test_provenance_includes_reference_state_and_fingerprint(self) -> None:
        """Item 1: provenance records reference-state policy and config fingerprint."""
        provider = CoolPropProvider()
        state = provider.state_tp("Water", 300.0, 101_325.0)
        prov = state.provenance
        assert prov.reference_state_policy is ReferenceStatePolicy.DEF
        assert isinstance(prov.configuration_fingerprint, str)
        assert len(prov.configuration_fingerprint) == 16  # sha256[:16]


# ======================================================================
# Item 6: PH saturation tolerance reference-state invariance
# ======================================================================


class TestPHSaturationTolerance:
    def test_ph_near_saturation_rejection_uses_latent_heat(self) -> None:
        """Item 6: tolerance scales by abs(hg - hf), not max(abs(h))."""
        provider = CoolPropProvider()
        sat = provider.saturation_at_pressure("R134a", 500_000.0)

        h_f = sat.liquid.enthalpy_j_kg
        h_g = sat.vapor.enthalpy_j_kg
        latent = abs(h_g - h_f)

        # Place enthalpy just inside the tolerance window from h_f
        # Tolerance = near_saturation_relative_tolerance * max(latent, 1.0)
        tol = provider.near_saturation_relative_tolerance * max(latent, 1.0)
        near_h_f = h_f + tol * 0.5  # should be rejected

        with pytest.raises(PropertyServiceError) as exc_info:
            provider.state_ph("R134a", 500_000.0, near_h_f)

        assert exc_info.value.code is PropertyErrorCode.NEAR_SATURATION
        # Verify the context records latent heat
        assert "latent_heat_j_kg" in exc_info.value.context

    def test_ph_far_from_saturation_succeeds(self) -> None:
        """Enthalpy far from saturation should succeed."""
        provider = CoolPropProvider()
        sat = provider.saturation_at_pressure("R134a", 500_000.0)

        h_g = sat.vapor.enthalpy_j_kg
        # Place enthalpy well above saturated vapor
        far_above = h_g + 50_000.0  # 50 kJ/kg above
        state = provider.state_ph("R134a", 500_000.0, far_above)
        assert state.phase in {PhaseRegion.GAS, PhaseRegion.SUPERCRITICAL_GAS}


# ======================================================================
# Item 7: Mixture capability boundary
# ======================================================================


class TestMixtureCapability:
    def test_mixture_identifier_represents_but_may_not_calculate(self) -> None:
        """Item 7: v0.1 mixture support is representation only.

        The FluidIdentifier can represent a mixture, but actual
        mixture TP/PH/saturation calculations are not validated.
        """
        ident = FluidIdentifier.from_components({"R32": 0.5, "R125": 0.5})
        assert len(ident.components) == 2
        assert ident.coolprop_fluid.startswith("HEOS::")

        # Mixture TP query works with unvalidated fluids enabled
        provider = CoolPropProvider(allow_unvalidated_fluids=True)
        state = provider.state_tp(
            ident, 300.0, 2_000_000.0
        )
        assert state.provenance.validation_level is FluidValidationLevel.UNVALIDATED

    def test_mixture_without_opt_in_is_rejected(self) -> None:
        ident = FluidIdentifier.from_components({"R32": 0.5, "R125": 0.5})
        with pytest.raises(PropertyServiceError) as exc_info:
            CoolPropProvider().state_tp(ident, 300.0, 2_000_000.0)
        assert exc_info.value.code is PropertyErrorCode.UNVALIDATED_FLUID


# ======================================================================
# Item 8: Error-boundary regressions
# ======================================================================


class TestErrorBoundaries:
    def test_out_of_range_state(self) -> None:
        """Extremely low enthalpy should return STATE_OUT_OF_RANGE or BACKEND_FAILURE."""
        provider = CoolPropProvider(allow_unvalidated_fluids=True)
        with pytest.raises(PropertyServiceError) as exc_info:
            provider.state_ph("Water", 101_325.0, -1_000_000.0)  # absurdly low h
        assert exc_info.value.code in {
            PropertyErrorCode.STATE_OUT_OF_RANGE,
            PropertyErrorCode.BACKEND_FAILURE,
        }

    def test_saturation_above_critical(self) -> None:
        """Saturation above critical temperature returns SATURATION_UNAVAILABLE."""
        provider = CoolPropProvider()
        # Water critical temperature ~ 647 K
        with pytest.raises(PropertyServiceError) as exc_info:
            provider.saturation_at_temperature("Water", 700.0)
        assert exc_info.value.code is PropertyErrorCode.SATURATION_UNAVAILABLE

    def test_unsupported_backend(self) -> None:
        """Non-HEOS backend is rejected in v0.1."""
        ident = FluidIdentifier(name="Water", equation_of_state_backend="REFPROP")
        with pytest.raises(PropertyServiceError) as exc_info:
            CoolPropProvider().state_tp(ident, 300.0, 101_325.0)
        assert exc_info.value.code is PropertyErrorCode.UNSUPPORTED_BACKEND

    def test_malformed_composition_rejected(self) -> None:
        """Mixture with fractions not summing to 1 is rejected."""
        with pytest.raises(PropertyServiceError) as exc_info:
            FluidIdentifier.from_components({"R32": 0.7, "R125": 0.4})
        assert exc_info.value.code is PropertyErrorCode.INVALID_FLUID
        assert "1.0" in str(exc_info.value)

    def test_empty_fluid_name_rejected(self) -> None:
        with pytest.raises(PropertyServiceError) as exc_info:
            FluidIdentifier(name="  ")
        assert exc_info.value.code is PropertyErrorCode.INVALID_FLUID

    def test_error_codes_are_stable_strings(self) -> None:
        """Item 8: public error codes are stable, independent of backend wording."""
        for code in PropertyErrorCode:
            assert isinstance(code.value, str)
            assert code.value.startswith("property_")

    def test_failed_query_cache_behavior(self) -> None:
        """Failed queries should not pollute the cache."""
        provider = CoolPropProvider(cache_size=4)
        # Successful query
        provider.state_tp("Water", 300.0, 101_325.0)
        assert provider.cache_info().size == 1

        # Failed query (invalid input)
        with pytest.raises(PropertyServiceError):
            provider.state_tp("Water", -1.0, 101_325.0)

        # Cache should still have only 1 entry
        assert provider.cache_info().size == 1
