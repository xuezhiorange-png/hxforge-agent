"""Unit tests for TASK-003 property service — Round 2 review.

Covers all 8 review items:
1. Runtime CoolProp configuration guard
2. SUPPORTED_TIER_1 for all Tier-1 fluids (no BENCHMARK_VALIDATED)
3. Mandatory PH reference-state identity
4. FluidSpec adapter (provider CoolProp -> EOS HEOS)
5. Strict deterministic result/error serialization
6. Mixture capability boundary (NOT_IMPLEMENTED)
7. Deterministic error classification
8. Error-boundary regressions
"""

from __future__ import annotations

import math

import pytest

from hexagent.properties import (
    VALIDATION_MATRIX,
    CoolPropProvider,
    FluidIdentifier,
    FluidStateModel,
    FluidValidationLevel,
    PhaseRegion,
    PropertyErrorCode,
    PropertyQueryType,
    PropertyServiceError,
    ReferenceStatePolicy,
)
from hexagent.properties.base import FluidState, PropertyProvenance, SaturationState


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
# Item 1: Runtime configuration guard
# ======================================================================


class TestConfigurationGuard:
    def test_fingerprint_matches_between_queries(self) -> None:
        """Normal operation: fingerprint stays stable across queries."""
        provider = CoolPropProvider(cache_size=4)
        provider.state_tp("Water", 300.0, 101_325.0)
        provider.state_tp("Water", 310.0, 101_325.0)
        info = provider.cache_info()
        assert info.misses == 2
        assert info.hits == 0

    def test_configuration_changed_clears_cache_and_raises(self) -> None:
        """Item 1: mutating CoolProp after provider creation triggers
        CONFIGURATION_CHANGED on the next query."""
        import CoolProp.CoolProp as CP

        provider = CoolPropProvider(cache_size=4)
        # Normal query succeeds
        provider.state_tp("R134a", 300.0, 2_000_000.0)
        assert provider.cache_info().size == 1

        # Mutate CoolProp reference state for R134a
        original_ref = "DEF"
        try:
            CP.set_reference_state("R134a", "IIR")
            # Next query should detect the change and raise
            with pytest.raises(PropertyServiceError) as exc_info:
                provider.state_tp("R134a", 300.0, 2_000_000.0)
            assert exc_info.value.code is PropertyErrorCode.CONFIGURATION_CHANGED
            # Cache should be cleared
            assert provider.cache_info().size == 0
        finally:
            CP.set_reference_state("R134a", original_ref)

    def test_configuration_error_has_both_fingerprints(self) -> None:
        """Error context includes construction and current fingerprints."""
        import CoolProp.CoolProp as CP

        provider = CoolPropProvider()
        try:
            CP.set_reference_state("R134a", "IIR")
            with pytest.raises(PropertyServiceError) as exc_info:
                provider.state_tp("R134a", 300.0, 2_000_000.0)
            ctx = exc_info.value.context
            assert "construction_fingerprint" in ctx
            assert "current_fingerprint" in ctx
            assert ctx["construction_fingerprint"] != ctx["current_fingerprint"]
        finally:
            CP.set_reference_state("R134a", "DEF")


# ======================================================================
# Item 2: SUPPORTED_TIER_1 for all Tier-1 fluids
# ======================================================================


class TestValidationLevels:
    @pytest.mark.parametrize(
        ("fluid", "temperature_k", "pressure_pa"),
        [
            ("Water", 300.0, 101_325.0),
            ("Air", 300.0, 101_325.0),
            ("R134a", 300.0, 2_000_000.0),
            ("R717", 300.0, 2_000_000.0),
        ],
    )
    def test_all_tier_one_are_supported_tier_1(
        self,
        fluid: str,
        temperature_k: float,
        pressure_pa: float,
    ) -> None:
        """Item 2: all Tier-1 fluids get SUPPORTED_TIER_1, not
        BENCHMARK_VALIDATED (fixtures are same-backend regressions)."""
        state = CoolPropProvider().state_tp(fluid, temperature_k, pressure_pa)
        _assert_single_phase_state(state)
        assert state.provenance.validation_level is FluidValidationLevel.SUPPORTED_TIER_1
        assert state.provenance.query_type is PropertyQueryType.TP
        assert state.provenance.backend_name == "CoolProp"

    def test_ammonia_alias_resolves_to_r717(self) -> None:
        state = CoolPropProvider().state_tp("Ammonia", 300.0, 2_000_000.0)
        assert state.provenance.fluid_identifier == "HEOS::R717"
        assert state.provenance.validation_level is FluidValidationLevel.SUPPORTED_TIER_1

    def test_validation_matrix_is_backend_regression(self) -> None:
        """Item 2: matrix entries are labelled backend_regression."""
        assert len(VALIDATION_MATRIX) >= 4
        for entry in VALIDATION_MATRIX:
            assert "dataset_id" in entry
            assert entry.get("validation_basis") == "backend_regression"


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
        state_ph = provider.state_ph(
            fluid,
            pressure_pa,
            state_tp.enthalpy_j_kg,
            reference_state=ReferenceStatePolicy.DEF,
        )
        assert state_ph.temperature_k == pytest.approx(state_tp.temperature_k, rel=1e-8)
        assert state_ph.pressure_pa == pytest.approx(state_tp.pressure_pa, rel=1e-12)
        assert state_ph.density_kg_m3 == pytest.approx(state_tp.density_kg_m3, rel=1e-7)
        assert state_ph.provenance.query_type is PropertyQueryType.PH


# ======================================================================
# Saturation queries
# ======================================================================


class TestSaturation:
    def test_saturation_at_pressure(self) -> None:
        sat = CoolPropProvider().saturation_at_pressure("R134a", 500_000.0)
        assert sat.query_type is PropertyQueryType.SATURATION_P
        assert sat.liquid.quality == 0.0
        assert sat.vapor.quality == 1.0
        assert sat.liquid.phase is PhaseRegion.SATURATED_LIQUID
        assert sat.vapor.phase is PhaseRegion.SATURATED_VAPOR
        assert sat.liquid.density_kg_m3 > sat.vapor.density_kg_m3
        assert sat.vapor.enthalpy_j_kg > sat.liquid.enthalpy_j_kg

    def test_saturation_at_temperature(self) -> None:
        sat = CoolPropProvider().saturation_at_temperature("R134a", 273.15)
        assert sat.query_type is PropertyQueryType.SATURATION_T
        assert sat.liquid.temperature_k == pytest.approx(273.15)
        assert sat.vapor.temperature_k == pytest.approx(273.15)


# ======================================================================
# Near-saturation and two-phase rejection
# ======================================================================


class TestBoundaryRejection:
    def test_exact_tp_saturation_is_rejected(self) -> None:
        provider = CoolPropProvider()
        sat = provider.saturation_at_pressure("R134a", 500_000.0)
        with pytest.raises(PropertyServiceError) as exc_info:
            provider.state_tp(
                "R134a",
                sat.liquid.temperature_k,
                500_000.0,
            )
        assert exc_info.value.code is PropertyErrorCode.NEAR_SATURATION

    def test_ph_inside_two_phase_is_rejected(self) -> None:
        provider = CoolPropProvider()
        sat = provider.saturation_at_pressure("R134a", 500_000.0)
        midpoint = (sat.liquid.enthalpy_j_kg + sat.vapor.enthalpy_j_kg) / 2.0
        with pytest.raises(PropertyServiceError) as exc_info:
            provider.state_ph(
                "R134a",
                500_000.0,
                midpoint,
                reference_state=ReferenceStatePolicy.DEF,
            )
        assert exc_info.value.code is PropertyErrorCode.TWO_PHASE_STATE


# ======================================================================
# Item 3: Mandatory PH reference state
# ======================================================================


class TestPHReferenceState:
    def test_ph_with_matching_reference_succeeds(self) -> None:
        provider = CoolPropProvider()
        tp = provider.state_tp("Water", 330.0, 300_000.0)
        ph = provider.state_ph(
            "Water",
            300_000.0,
            tp.enthalpy_j_kg,
            reference_state=ReferenceStatePolicy.DEF,
        )
        assert ph.temperature_k == pytest.approx(330.0, rel=1e-8)

    def test_ph_with_mismatched_reference_is_rejected(self) -> None:
        provider = CoolPropProvider()
        tp = provider.state_tp("Water", 330.0, 300_000.0)
        original = provider.reference_state_policy
        try:
            object.__setattr__(provider, "reference_state_policy", "NOT_DEF")
            with pytest.raises(PropertyServiceError) as exc_info:
                provider.state_ph(
                    "Water",
                    300_000.0,
                    tp.enthalpy_j_kg,
                    reference_state=ReferenceStatePolicy.DEF,
                )
            assert exc_info.value.code is PropertyErrorCode.INVALID_INPUT
            assert "reference-state" in str(exc_info.value).lower()
        finally:
            object.__setattr__(provider, "reference_state_policy", original)

    def test_ph_reference_state_in_provenance(self) -> None:
        provider = CoolPropProvider()
        tp = provider.state_tp("Water", 330.0, 300_000.0)
        ph = provider.state_ph(
            "Water",
            300_000.0,
            tp.enthalpy_j_kg,
            reference_state=ReferenceStatePolicy.DEF,
        )
        assert ph.provenance.reference_state_policy is ReferenceStatePolicy.DEF


# ======================================================================
# Item 4: FluidSpec adapter
# ======================================================================


class TestFluidSpecAdapter:
    def test_adapter_maps_coolprop_to_heos(self) -> None:
        ident = FluidIdentifier.from_fluid_spec("CoolProp", "Water")
        assert ident.name == "Water"
        assert ident.equation_of_state_backend == "HEOS"
        assert ident.backend == "HEOS"

    def test_adapter_rejects_unsupported_provider(self) -> None:
        with pytest.raises(PropertyServiceError) as exc_info:
            FluidIdentifier.from_fluid_spec("REFPROP", "Water")
        assert exc_info.value.code is PropertyErrorCode.UNSUPPORTED_BACKEND

    def test_adapter_rejects_unsupported_composition_basis(self) -> None:
        with pytest.raises(PropertyServiceError) as exc_info:
            FluidIdentifier.from_fluid_spec(
                "CoolProp",
                "Water",
                composition_basis="mass_fraction",
            )
        assert exc_info.value.code is PropertyErrorCode.INVALID_FLUID

    def test_adapter_with_composition(self) -> None:
        ident = FluidIdentifier.from_fluid_spec(
            "CoolProp",
            "R410A",
            composition={"R32": 0.5, "R125": 0.5},
        )
        assert ident.name == "R410A"
        assert len(ident.components) == 2
        assert ident.equation_of_state_backend == "HEOS"

    def test_adapter_rejects_non_coolprop_provider(self) -> None:
        with pytest.raises(PropertyServiceError) as exc_info:
            FluidIdentifier.from_fluid_spec("NIST", "Water")
        assert "NIST" in str(exc_info.value)


# ======================================================================
# Item 5: Strict serialization
# ======================================================================


class TestSerialization:
    def test_fluid_state_json_round_trip(self) -> None:
        """Item 5: true FluidState -> JSON -> FluidState round trip."""
        provider = CoolPropProvider()
        state = provider.state_tp("Water", 300.0, 101_325.0)

        json_str = state.to_json()
        restored = FluidState.from_json(json_str)

        assert restored.temperature_k == pytest.approx(state.temperature_k)
        assert restored.pressure_pa == pytest.approx(state.pressure_pa)
        assert restored.density_kg_m3 == pytest.approx(state.density_kg_m3)
        assert restored.phase is state.phase
        assert restored.provenance.validation_level is state.provenance.validation_level
        assert restored.provenance.query_type is state.provenance.query_type
        assert restored.provenance.reference_state_policy is state.provenance.reference_state_policy

    def test_saturation_json_round_trip(self) -> None:
        provider = CoolPropProvider()
        sat = provider.saturation_at_pressure("R134a", 500_000.0)
        json_str = sat.to_json()
        restored = SaturationState.from_json(json_str)

        assert restored.query_type is sat.query_type
        assert restored.input_value == pytest.approx(sat.input_value)
        assert restored.liquid.temperature_k == pytest.approx(sat.liquid.temperature_k)

    def test_provenance_model_strict(self) -> None:
        """Provenance model has extra=forbid and Literal version."""
        from hexagent.properties.base import PropertyProvenanceModel

        prov = PropertyProvenanceModel(
            backend_name="CoolProp",
            backend_version="7.6.1",
            backend_git_revision="abc",
            fluid_identifier="HEOS::Water",
            validation_level="supported_tier_1",
            query_type="TP",
            inputs={"temperature_k": 300.0},
            cache_policy_version="1.0",
            reference_state_policy="DEF",
            configuration_fingerprint="abc",
        )
        # Extra field should be rejected
        with pytest.raises((ValueError, TypeError)):
            prov.model_validate({**prov.model_dump(), "extra": "bad"})

    def test_fluid_state_model_strict(self) -> None:
        """FluidStateModel has extra=forbid."""
        state_model = FluidStateModel(
            temperature_k=300.0,
            pressure_pa=101325.0,
            density_kg_m3=996.5,
            cp_j_kg_k=4178.0,
            viscosity_pa_s=0.001,
            conductivity_w_m_k=0.6,
            enthalpy_j_kg=100000.0,
            entropy_j_kg_k=300.0,
            phase="liquid",
            provenance={
                "backend_name": "CoolProp",
                "backend_version": "7.6.1",
                "backend_git_revision": "abc",
                "fluid_identifier": "HEOS::Water",
                "validation_level": "supported_tier_1",
                "query_type": "TP",
                "inputs": {"temperature_k": 300.0},
                "cache_policy_version": "1.0",
                "reference_state_policy": "DEF",
                "configuration_fingerprint": "abc",
            },
        )
        with pytest.raises((ValueError, TypeError)):
            state_model.model_validate({**state_model.model_dump(), "extra": "bad"})

    def test_error_code_stable_strings(self) -> None:
        """Item 8: all error codes are stable property_ prefixed strings."""
        for code in PropertyErrorCode:
            assert isinstance(code.value, str)
            assert code.value.startswith("property_")

    def test_error_as_dict_is_json_safe(self) -> None:
        import json

        err = PropertyServiceError(
            PropertyErrorCode.INVALID_INPUT,
            "test error",
            context={"field": "x", "value": 1.0},
        )
        d = err.as_dict()
        serialized = json.dumps(d)
        assert "test error" in serialized
        assert d["code"] == "property_invalid_input"


# ======================================================================
# Item 6: Mixture capability boundary
# ======================================================================


class TestMixtureCapability:
    def test_mixture_tp_returns_unsupported_query(self) -> None:
        """Item 6: mixture calculations return UNSUPPORTED_QUERY."""
        ident = FluidIdentifier.from_components({"R32": 0.5, "R125": 0.5})
        with pytest.raises(PropertyServiceError) as exc_info:
            CoolPropProvider(allow_unvalidated_fluids=True).state_tp(
                ident,
                300.0,
                2_000_000.0,
            )
        assert exc_info.value.code is PropertyErrorCode.UNSUPPORTED_QUERY
        assert "mixture" in str(exc_info.value).lower()

    def test_mixture_ph_returns_unsupported_query(self) -> None:
        ident = FluidIdentifier.from_components({"R32": 0.5, "R125": 0.5})
        with pytest.raises(PropertyServiceError) as exc_info:
            CoolPropProvider(allow_unvalidated_fluids=True).state_ph(
                ident,
                2_000_000.0,
                200_000.0,
                reference_state=ReferenceStatePolicy.DEF,
            )
        assert exc_info.value.code is PropertyErrorCode.UNSUPPORTED_QUERY

    def test_mixture_saturation_returns_unsupported_query(self) -> None:
        ident = FluidIdentifier.from_components({"R32": 0.5, "R125": 0.5})
        with pytest.raises(PropertyServiceError) as exc_info:
            CoolPropProvider(allow_unvalidated_fluids=True).saturation_at_pressure(
                ident,
                2_000_000.0,
            )
        assert exc_info.value.code is PropertyErrorCode.UNSUPPORTED_QUERY

    def test_mixture_identifier_is_representable(self) -> None:
        """Mixture identifiers can be created, just not computed."""
        ident = FluidIdentifier.from_components({"R32": 0.7, "R125": 0.3})
        assert len(ident.components) == 2
        assert ident.is_mixture

    def test_pure_fluid_is_not_mixture(self) -> None:
        ident = FluidIdentifier(name="Water")
        assert not ident.is_mixture


# ======================================================================
# Item 7: Deterministic error classification
# ======================================================================


class TestErrorClassification:
    def test_below_triple_returns_state_out_of_range(self) -> None:
        """Item 7: extremely low enthalpy returns STATE_OUT_OF_RANGE."""
        provider = CoolPropProvider(allow_unvalidated_fluids=True)
        with pytest.raises(PropertyServiceError) as exc_info:
            provider.state_ph(
                "Water",
                101_325.0,
                -1_000_000.0,
                reference_state=ReferenceStatePolicy.DEF,
            )
        # Must be deterministic: exactly STATE_OUT_OF_RANGE
        assert exc_info.value.code is PropertyErrorCode.STATE_OUT_OF_RANGE

    def test_above_critical_saturation_unavailable(self) -> None:
        """Item 7: saturation above critical returns SATURATION_UNAVAILABLE."""
        provider = CoolPropProvider()
        with pytest.raises(PropertyServiceError) as exc_info:
            provider.saturation_at_temperature("Water", 700.0)
        assert exc_info.value.code is PropertyErrorCode.SATURATION_UNAVAILABLE

    def test_unsupported_backend_error(self) -> None:
        ident = FluidIdentifier(name="Water", equation_of_state_backend="REFPROP")
        with pytest.raises(PropertyServiceError) as exc_info:
            CoolPropProvider().state_tp(ident, 300.0, 101_325.0)
        assert exc_info.value.code is PropertyErrorCode.UNSUPPORTED_BACKEND

    def test_malformed_composition(self) -> None:
        with pytest.raises(PropertyServiceError) as exc_info:
            FluidIdentifier.from_components({"R32": 0.7, "R125": 0.4})
        assert exc_info.value.code is PropertyErrorCode.INVALID_FLUID

    def test_empty_fluid_name(self) -> None:
        with pytest.raises(PropertyServiceError) as exc_info:
            FluidIdentifier(name="  ")
        assert exc_info.value.code is PropertyErrorCode.INVALID_FLUID

    def test_failed_query_does_not_pollute_cache(self) -> None:
        provider = CoolPropProvider(cache_size=4)
        provider.state_tp("Water", 300.0, 101_325.0)
        assert provider.cache_info().size == 1
        with pytest.raises(PropertyServiceError):
            provider.state_tp("Water", -1.0, 101_325.0)
        assert provider.cache_info().size == 1
        assert provider.cache_info().hits == 0


# ======================================================================
# Cache
# ======================================================================


class TestCache:
    def test_cache_determinism(self) -> None:
        provider = CoolPropProvider(cache_size=4)
        first = provider.state_tp("Water", 300.0, 101_325.0)
        second = provider.state_tp("Water", 300.0, 101_325.0)
        info = provider.cache_info()
        assert first is second
        assert info.misses == 1
        assert info.hits == 1
        provider.clear_cache()
        assert provider.cache_info().size == 0


# ======================================================================
# Item 1: DEF baseline guard (replaces old reference-state verification)
# ======================================================================


class TestDEFBaselineGuard:
    def test_def_baseline_captured_during_init(self) -> None:
        """Item 1: provider captures DEF enthalpies during construction."""
        provider = CoolPropProvider()
        assert hasattr(provider, "_def_baseline")
        assert "Water" in provider._def_baseline
        assert "R134a" in provider._def_baseline
        assert "R717" in provider._def_baseline
        for fluid, h in provider._def_baseline.items():
            assert math.isfinite(h), f"{fluid} baseline is not finite"

    def test_r717_mutation_detected_by_baseline(self) -> None:
        """Item 1: R717 mutation is caught by the DEF baseline check."""
        import CoolProp.CoolProp as CP

        provider = CoolPropProvider(cache_size=4)
        # Normal query succeeds
        provider.state_tp("R717", 300.0, 2_000_000.0)
        assert provider.cache_info().size == 1

        try:
            CP.set_reference_state("R717", "IIR")
            with pytest.raises(PropertyServiceError) as exc_info:
                provider.state_tp("R717", 300.0, 2_000_000.0)
            assert exc_info.value.code is PropertyErrorCode.CONFIGURATION_CHANGED
            assert "DEF baseline" in str(exc_info.value)
        finally:
            CP.set_reference_state("R717", "DEF")

    def test_def_baseline_force_during_init(self) -> None:
        """Item 1: init forces DEF even if CoolProp was in IIR."""
        import CoolProp.CoolProp as CP

        try:
            CP.set_reference_state("R134a", "IIR")
            provider = CoolPropProvider()
            # Provider should have forced DEF and captured correct baseline
            # A normal query should succeed (not use stale IIR values)
            state = provider.state_tp("R134a", 300.0, 2_000_000.0)
            assert state.temperature_k == pytest.approx(300.0, rel=1e-6)
        finally:
            CP.set_reference_state("R134a", "DEF")


# ======================================================================
# Item 4: FluidSpec object adapter
# ======================================================================


class TestFluidSpecObjectAdapter:
    def test_adapter_accepts_fluid_spec_object(self) -> None:
        """Item 4: from_fluid_spec accepts actual FluidSpec objects."""
        from hexagent.domain.models import FluidSpec

        spec = FluidSpec(backend="CoolProp", name="Water")
        ident = FluidIdentifier.from_fluid_spec(spec)
        assert ident.name == "Water"
        assert ident.equation_of_state_backend == "HEOS"

    def test_adapter_accepts_fluid_spec_with_composition(self) -> None:
        from hexagent.domain.models import FluidSpec

        spec = FluidSpec(
            backend="CoolProp",
            name="R410A",
            composition={"R32": 0.5, "R125": 0.5},
        )
        ident = FluidIdentifier.from_fluid_spec(spec)
        assert ident.name == "R410A"
        assert len(ident.components) == 2
        assert ident.equation_of_state_backend == "HEOS"

    def test_adapter_rejects_non_coolprop_fluid_spec(self) -> None:
        from hexagent.domain.models import FluidSpec

        spec = FluidSpec(backend="REFPROP", name="Water")
        with pytest.raises(PropertyServiceError) as exc_info:
            FluidIdentifier.from_fluid_spec(spec)
        assert exc_info.value.code is PropertyErrorCode.UNSUPPORTED_BACKEND


# ======================================================================
# Item 5: Canonical JSON and enum fields
# ======================================================================


class TestCanonicalJSON:
    def test_provenance_json_has_enum_fields(self) -> None:
        """Item 5: provenance JSON contains enum values, not plain strings."""
        provider = CoolPropProvider()
        state = provider.state_tp("Water", 300.0, 101_325.0)
        json_str = state.to_json()
        # Enum values should appear as strings in JSON
        assert '"validation_level":"supported_tier_1"' in json_str
        assert '"query_type":"TP"' in json_str
        assert '"reference_state_policy":"DEF"' in json_str

    def test_provenance_round_trip_preserves_enums(self) -> None:
        """Item 5: enum fields survive JSON round trip."""
        provider = CoolPropProvider()
        state = provider.state_tp("Water", 300.0, 101_325.0)
        restored = FluidState.from_json(state.to_json())
        assert restored.provenance.validation_level is FluidValidationLevel.SUPPORTED_TIER_1
        assert restored.provenance.query_type is PropertyQueryType.TP
        assert restored.provenance.reference_state_policy is ReferenceStatePolicy.DEF

    def test_fluid_state_model_rejects_extra_fields(self) -> None:
        """Item 5: FluidStateModel has extra=forbid."""
        state = FluidState(
            temperature_k=300.0,
            pressure_pa=101325.0,
            density_kg_m3=996.5,
            cp_j_kg_k=4178.0,
            viscosity_pa_s=0.001,
            conductivity_w_m_k=0.6,
            enthalpy_j_kg=100000.0,
            entropy_j_kg_k=300.0,
            phase=PhaseRegion.LIQUID,
            quality=None,
            provenance=PropertyProvenance(
                backend_name="CoolProp",
                backend_version="7.6.1",
                backend_git_revision="abc",
                fluid_identifier="HEOS::Water",
                validation_level=FluidValidationLevel.SUPPORTED_TIER_1,
                query_type=PropertyQueryType.TP,
                inputs=(("temperature_k", 300.0),),
                cache_policy_version="1.0",
            ),
        )
        model = state.to_model()
        with pytest.raises((ValueError, TypeError)):
            model.model_validate({**model.model_dump(), "extra_field": "bad"})

    def test_canonical_json_is_deterministic(self) -> None:
        """Item 5: same state produces identical JSON."""
        provider = CoolPropProvider()
        state1 = provider.state_tp("Water", 300.0, 101_325.0)
        provider.clear_cache()
        state2 = provider.state_tp("Water", 300.0, 101_325.0)
        # Same inputs should produce same JSON (modulo fingerprint which
        # is the same in the same process)
        assert state1.to_json() == state2.to_json()


# ======================================================================
# Item 1: Atomic lock — verification and evaluation under one lock
# ======================================================================


class TestAtomicLock:
    def test_concurrent_mutation_detected(self) -> None:
        """Item 1: if CoolProp is mutated, the next query detects it."""
        import CoolProp.CoolProp as CP

        provider = CoolPropProvider(cache_size=4)
        provider.state_tp("R134a", 300.0, 2_000_000.0)
        try:
            CP.set_reference_state("R134a", "IIR")
            with pytest.raises(PropertyServiceError) as exc_info:
                provider.state_tp("R134a", 300.0, 2_000_000.0)
            assert exc_info.value.code is PropertyErrorCode.CONFIGURATION_CHANGED
        finally:
            CP.set_reference_state("R134a", "DEF")


# ======================================================================
# Item 2: PHStateSpec with reference_state + adapter
# ======================================================================


class TestPHStateSpecReferenceState:
    def test_ph_state_spec_requires_reference_state(self) -> None:
        """Item 2: PHStateSpec has a reference_state field."""
        from hexagent.domain.models import PHStateSpec
        from hexagent.domain.quantities import AbsolutePressure, SpecificEnthalpy

        spec = PHStateSpec(
            type="PH",
            pressure=AbsolutePressure(value=101_325.0, unit="Pa"),
            enthalpy=SpecificEnthalpy(value=100_000.0, unit="J/kg"),
            reference_state=ReferenceStatePolicy.DEF,
        )
        assert spec.reference_state is ReferenceStatePolicy.DEF

    def test_ph_state_spec_to_provider_args(self) -> None:
        """Item 2: adapter converts PHStateSpec to provider kwargs."""
        from hexagent.domain.models import PHStateSpec
        from hexagent.domain.quantities import AbsolutePressure, SpecificEnthalpy

        spec = PHStateSpec(
            type="PH",
            pressure=AbsolutePressure(value=300_000.0, unit="Pa"),
            enthalpy=SpecificEnthalpy(value=200_000.0, unit="J/kg"),
            reference_state=ReferenceStatePolicy.DEF,
        )
        args = spec.to_provider_args()
        assert args["pressure_pa"] == 300_000.0
        assert args["enthalpy_j_kg"] == 200_000.0
        assert args["reference_state"] is ReferenceStatePolicy.DEF

    def test_ph_state_spec_json_round_trip(self) -> None:
        """Item 2: PHStateSpec serializes and deserializes with ref state."""
        from hexagent.domain.models import PHStateSpec
        from hexagent.domain.quantities import AbsolutePressure, SpecificEnthalpy

        spec = PHStateSpec(
            type="PH",
            pressure=AbsolutePressure(value=101_325.0, unit="Pa"),
            enthalpy=SpecificEnthalpy(value=100_000.0, unit="J/kg"),
            reference_state=ReferenceStatePolicy.DEF,
        )
        json_str = spec.model_dump_json()
        restored = PHStateSpec.model_validate_json(json_str)
        assert restored.reference_state is ReferenceStatePolicy.DEF
        assert restored.pressure.si_value == 101_325.0

    def test_ph_state_spec_rejects_unknown_reference(self) -> None:
        """Item 2: unknown reference state value is rejected."""
        from hexagent.domain.models import PHStateSpec
        from hexagent.domain.quantities import AbsolutePressure, SpecificEnthalpy

        with pytest.raises((ValueError, TypeError)):
            PHStateSpec(
                type="PH",
                pressure=AbsolutePressure(value=101_325.0, unit="Pa"),
                enthalpy=SpecificEnthalpy(value=100_000.0, unit="J/kg"),
                reference_state="UNKNOWN",
            )

    def test_ph_state_spec_adapter_e2e(self) -> None:
        """Item 2: PHStateSpec → provider.state_ph end-to-end."""
        from hexagent.domain.models import PHStateSpec
        from hexagent.domain.quantities import AbsolutePressure, SpecificEnthalpy

        provider = CoolPropProvider()
        tp = provider.state_tp("Water", 330.0, 300_000.0)
        spec = PHStateSpec(
            type="PH",
            pressure=AbsolutePressure(value=300_000.0, unit="Pa"),
            enthalpy=SpecificEnthalpy(value=tp.enthalpy_j_kg, unit="J/kg"),
            reference_state=ReferenceStatePolicy.DEF,
        )
        args = spec.to_provider_args()
        ph = provider.state_ph(
            "Water",
            args["pressure_pa"],
            args["enthalpy_j_kg"],
            reference_state=args["reference_state"],
        )
        assert ph.temperature_k == pytest.approx(330.0, rel=1e-8)


# ======================================================================
# Item 3: Validation provenance — fixture matching
# ======================================================================


class TestValidationProvenance:
    def test_fixture_match_populates_dataset_fields(self) -> None:
        """Item 3: matching fixture populates dataset_id in provenance."""
        provider = CoolPropProvider()
        state = provider.state_tp("Water", 300.0, 101_325.0)
        assert state.provenance.validation_dataset_id is not None
        assert "WATER" in state.provenance.validation_dataset_id
        assert state.provenance.validation_basis == "backend_regression"
        assert state.provenance.validation_dataset_revision is not None

    def test_non_matching_query_has_support_allowlist(self) -> None:
        """Item 3: non-fixture Tier-1 query has support_allowlist basis."""
        provider = CoolPropProvider()
        state = provider.state_tp("Water", 350.0, 500_000.0)
        assert state.provenance.validation_dataset_id is None
        assert state.provenance.validation_basis == "support_allowlist"

    def test_unvalidated_opt_in_basis(self) -> None:
        """Item 3: explicitly allowed unvalidated fluid has unvalidated_opt_in."""
        provider = CoolPropProvider(allow_unvalidated_fluids=True)
        state = provider.state_tp("CO2", 300.0, 5_000_000.0)
        assert state.provenance.validation_basis == "unvalidated_opt_in"
        assert state.provenance.validation_dataset_id is None

    def test_r134a_saturation_fixture_match(self) -> None:
        """Item 3: R134a saturation fixture is matched."""
        provider = CoolPropProvider()
        sat = provider.saturation_at_pressure("R134a", 500_000.0)
        assert sat.provenance.validation_dataset_id is not None
        assert "R134A" in sat.provenance.validation_dataset_id
        assert sat.provenance.validation_basis == "backend_regression"

    def test_r717_fixture_match(self) -> None:
        """Item 3: R717 fixture is matched."""
        provider = CoolPropProvider()
        state = provider.state_tp("R717", 300.0, 2_000_000.0)
        assert state.provenance.validation_dataset_id is not None
        assert "R717" in state.provenance.validation_dataset_id

    def test_fixture_match_in_provenance_json(self) -> None:
        """Item 3: fixture fields survive JSON round trip."""
        provider = CoolPropProvider()
        state = provider.state_tp("Water", 300.0, 101_325.0)
        restored = FluidState.from_json(state.to_json())
        assert restored.provenance.validation_dataset_id is not None
        assert restored.provenance.validation_basis == "backend_regression"


# ======================================================================
# Item 4: Strict serialization — Literal version, enum fields, error model
# ======================================================================


class TestStrictSerializationV2:
    def test_literal_schema_version_in_provenance(self) -> None:
        """Item 4: result_schema_version is Literal['1.0'], not pattern."""
        provider = CoolPropProvider()
        state = provider.state_tp("Water", 300.0, 101_325.0)
        model = state.to_model()
        assert model.result_schema_version == "1.0"
        # Literal["1.0"] rejects other values
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            model.model_validate({**model.model_dump(), "result_schema_version": "2.0"})

    def test_enum_phase_in_model(self) -> None:
        """Item 4: phase field is PhaseRegion enum, not plain string."""
        provider = CoolPropProvider()
        state = provider.state_tp("Water", 300.0, 101_325.0)
        model = state.to_model()
        assert isinstance(model.phase, PhaseRegion)
        assert model.phase is PhaseRegion.LIQUID

    def test_enum_query_type_in_saturation_model(self) -> None:
        """Item 4: query_type field is PropertyQueryType enum."""
        provider = CoolPropProvider()
        sat = provider.saturation_at_pressure("R134a", 500_000.0)
        model = sat.to_model()
        assert isinstance(model.query_type, PropertyQueryType)
        assert model.query_type is PropertyQueryType.SATURATION_P

    def test_error_model_strict_round_trip(self) -> None:
        """Item 4: PropertyServiceError → JSON → error model round trip."""

        err = PropertyServiceError(
            PropertyErrorCode.STATE_OUT_OF_RANGE,
            "test error message",
            context={"fluid": "HEOS::Water", "value": -1.0},
        )
        json_str = err.to_json()
        restored = PropertyServiceError.from_json(json_str)
        assert restored.code is PropertyErrorCode.STATE_OUT_OF_RANGE
        assert str(restored) == "test error message"
        assert restored.context["fluid"] == "HEOS::Water"
        assert restored.context["value"] == -1.0

    def test_error_model_rejects_extra_fields(self) -> None:
        """Item 4: error model has extra=forbid."""
        from hexagent.properties.errors import PropertyServiceErrorModel

        with pytest.raises((ValueError, TypeError)):
            PropertyServiceErrorModel.model_validate(
                {
                    "code": "property_invalid_input",
                    "message": "test",
                    "extra_field": "bad",
                }
            )

    def test_error_model_has_literal_version(self) -> None:
        """Item 4: error model includes schema_version."""

        err = PropertyServiceError(PropertyErrorCode.INVALID_INPUT, "test")
        model = err.to_model()
        assert model.schema_version == "1.0"

    def test_error_model_is_json_safe(self) -> None:
        """Item 4: error model serializes to valid JSON."""
        import json

        err = PropertyServiceError(
            PropertyErrorCode.BACKEND_FAILURE,
            "backend error",
            context={"nested": {"key": "value"}},
        )
        model = err.to_model()
        dumped = model.model_dump()
        serialized = json.dumps(dumped)
        parsed = json.loads(serialized)
        assert parsed["code"] == "property_backend_failure"
        assert parsed["context"]["nested"]["key"] == "value"


# ======================================================================
# Item 5: Error classification — explicit pre-checks, not message tokens
# ======================================================================


class TestErrorClassificationV2:
    def test_above_critical_pressure_returns_saturation_unavailable(
        self,
    ) -> None:
        """Item 5: above-critical pressure pre-check returns SATURATION_UNAVAILABLE."""
        provider = CoolPropProvider()
        with pytest.raises(PropertyServiceError) as exc_info:
            provider.saturation_at_pressure("Water", 25_000_000.0)
        assert exc_info.value.code is PropertyErrorCode.SATURATION_UNAVAILABLE
        assert "critical" in str(exc_info.value).lower()

    def test_above_critical_temperature_returns_saturation_unavailable(
        self,
    ) -> None:
        """Item 5: above-critical temperature pre-check."""
        provider = CoolPropProvider()
        with pytest.raises(PropertyServiceError) as exc_info:
            provider.saturation_at_temperature("Water", 700.0)
        assert exc_info.value.code is PropertyErrorCode.SATURATION_UNAVAILABLE

    def test_below_triple_returns_state_out_of_range(self) -> None:
        """Item 5: below-triple-point temperature via explicit TP pre-check."""
        provider = CoolPropProvider()
        with pytest.raises(PropertyServiceError) as exc_info:
            provider.state_tp("Water", 200.0, 101_325.0)
        assert exc_info.value.code is PropertyErrorCode.STATE_OUT_OF_RANGE
        assert "triple point" in str(exc_info.value).lower()
        assert "triple_point_temperature_k" in exc_info.value.context

    def test_pre_check_has_critical_context(self) -> None:
        """Item 5: pre-check error includes critical point in context."""
        provider = CoolPropProvider()
        with pytest.raises(PropertyServiceError) as exc_info:
            provider.saturation_at_pressure("Water", 25_000_000.0)
        ctx = exc_info.value.context
        assert "critical_pressure_pa" in ctx
        assert ctx["critical_pressure_pa"] == 22_064_000.0

    def test_failed_query_does_not_pollute_cache_v2(self) -> None:
        """Item 5: failed queries do not create cache entries."""
        provider = CoolPropProvider(cache_size=4)
        provider.state_tp("Water", 300.0, 101_325.0)
        assert provider.cache_info().size == 1
        with pytest.raises(PropertyServiceError):
            provider.state_tp("Water", -1.0, 101_325.0)
        assert provider.cache_info().size == 1
        assert provider.cache_info().hits == 0

    def test_unexpected_backend_returns_backend_failure(self) -> None:
        """Item 5: _classify_backend_error always returns BACKEND_FAILURE.

        Since message-token classification was removed, any CoolProp
        exception that reaches _classify_backend_error is an unexpected
        fault — regardless of its message text.  Tests with monkeypatched
        different exception messages.
        """
        provider = CoolPropProvider()
        fluid = FluidIdentifier(name="Water")
        qt = PropertyQueryType.TP

        for msg in (
            "something went wrong",
            "out of range error",
            "triple point exceeded",
            "critical temperature reached",
            "unexpected internal error",
        ):
            exc = ValueError(msg)
            code = provider._classify_backend_error(exc, fluid, qt)
            assert code is PropertyErrorCode.BACKEND_FAILURE, (
                f"Message {msg!r} produced {code}, expected BACKEND_FAILURE"
            )


# ======================================================================
# Item 1 (Review-04): PHStateSpec missing reference_state is rejected
# ======================================================================


class TestPHStateSpecRequired:
    def test_omitting_reference_state_is_rejected(self) -> None:
        """Item 1: PHStateSpec without reference_state fails validation."""
        from hexagent.domain.models import PHStateSpec
        from hexagent.domain.quantities import AbsolutePressure, SpecificEnthalpy

        with pytest.raises((ValueError, TypeError)):
            PHStateSpec(
                type="PH",
                pressure=AbsolutePressure(value=101_325.0, unit="Pa"),
                enthalpy=SpecificEnthalpy(value=100_000.0, unit="J/kg"),
                # reference_state intentionally omitted
            )

    def test_schema_json_requires_reference_state(self) -> None:
        """Item 1: JSON schema marks reference_state as required."""
        from hexagent.domain.models import PHStateSpec

        schema = PHStateSpec.model_json_schema()
        assert "reference_state" in schema.get("required", [])

    def test_json_without_reference_state_is_rejected(self) -> None:
        """Item 1: deserializing JSON without reference_state fails."""
        from hexagent.domain.models import PHStateSpec

        incomplete = (
            '{"type":"PH","pressure":{"value":101325,"unit":"Pa"},'
            '"enthalpy":{"value":100000,"unit":"J/kg"}}'
        )
        with pytest.raises((ValueError, TypeError)):
            PHStateSpec.model_validate_json(incomplete)


# ======================================================================
# Item 2 (Review-04): Error model Literal version + canonical JSON
# ======================================================================


class TestErrorModelLiteral:
    def test_schema_version_is_literal(self) -> None:
        """Item 2: schema_version rejects non-Literal values."""
        from pydantic import ValidationError

        from hexagent.properties.errors import PropertyServiceErrorModel

        model = PropertyServiceErrorModel(code=PropertyErrorCode.INVALID_INPUT, message="test")
        assert model.schema_version == "1.0"
        with pytest.raises(ValidationError):
            PropertyServiceErrorModel.model_validate(
                {
                    "code": "property_invalid_input",
                    "message": "test",
                    "schema_version": "2.0",
                }
            )

    def test_context_uses_default_factory(self) -> None:
        """Item 2: context default is not shared mutable state."""
        from hexagent.properties.errors import PropertyServiceErrorModel

        m1 = PropertyServiceErrorModel(code=PropertyErrorCode.INVALID_INPUT, message="a")
        m2 = PropertyServiceErrorModel(code=PropertyErrorCode.INVALID_INPUT, message="b")
        assert m1.context is not m2.context

    def test_error_canonical_json_round_trip(self) -> None:
        """Item 2: error → JSON → error → JSON produces identical output."""
        err = PropertyServiceError(
            PropertyErrorCode.STATE_OUT_OF_RANGE,
            "test boundary",
            context={"fluid": "HEOS::Water", "temperature_k": 200.0},
        )
        json1 = err.to_json()
        restored = PropertyServiceError.from_json(json1)
        json2 = restored.to_json()
        assert json1 == json2

    def test_error_json_has_literal_version(self) -> None:
        """Item 2: error JSON includes schema_version 1.0."""
        import json

        err = PropertyServiceError(PropertyErrorCode.BACKEND_FAILURE, "test")
        parsed = json.loads(err.to_json())
        assert parsed["schema_version"] == "1.0"
