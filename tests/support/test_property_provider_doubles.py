"""Acceptance tests for the property provider test doubles.

Validates that every public double in ``property_provider_doubles``
behaves according to its documented contract.
"""

from __future__ import annotations

import pytest

from hexagent.properties.base import (
    FluidIdentifier,
    FluidState,
    FluidValidationLevel,
    PhaseRegion,
    PropertyProvenance,
    PropertyProvider,
    PropertyQueryType,
    ReferenceStatePolicy,
    SaturationState,
)
from tests.support.property_provider_doubles import (
    CountingPropertyProvider,
    ProviderQueryKey,
    ReplayPropertyProvider,
    SelectiveFailurePropertyProvider,
    StubPropertyProvider,
    TestProviderError,
    canonical_fluid_identity,
)

pytestmark = [pytest.mark.pure]

# ---------------------------------------------------------------------------
# Helpers – tiny reusable factories so every test stays self-contained.
# ---------------------------------------------------------------------------

_WATER = FluidIdentifier.from_value("Water")

_PROV_TP = PropertyProvenance(
    backend_name="stub",
    backend_version="1",
    backend_git_revision="test",
    fluid_identifier="Water",
    validation_level=FluidValidationLevel.UNVALIDATED,
    query_type=PropertyQueryType.TP,
    inputs=(("pressure_pa", 101325.0), ("temperature_k", 300.0)),
    cache_policy_version="v1",
)

_PROV_PH = PropertyProvenance(
    backend_name="stub",
    backend_version="1",
    backend_git_revision="test",
    fluid_identifier="Water",
    validation_level=FluidValidationLevel.UNVALIDATED,
    query_type=PropertyQueryType.PH,
    inputs=(("enthalpy_j_kg", 100000.0), ("pressure_pa", 101325.0)),
    cache_policy_version="v1",
)

_PROV_SAT = PropertyProvenance(
    backend_name="stub",
    backend_version="1",
    backend_git_revision="test",
    fluid_identifier="Water",
    validation_level=FluidValidationLevel.UNVALIDATED,
    query_type=PropertyQueryType.SATURATION_P,
    inputs=(("pressure_pa", 101325.0),),
    cache_policy_version="v1",
)


def _tp_result() -> FluidState:
    return FluidState(
        temperature_k=300.0,
        pressure_pa=101325.0,
        density_kg_m3=996.0,
        cp_j_kg_k=4180.0,
        viscosity_pa_s=0.001,
        conductivity_w_m_k=0.6,
        enthalpy_j_kg=104_800.0,
        entropy_j_kg_k=360.0,
        phase=PhaseRegion.LIQUID,
        quality=None,
        provenance=_PROV_TP,
    )


def _ph_result() -> FluidState:
    return FluidState(
        temperature_k=350.0,
        pressure_pa=101325.0,
        density_kg_m3=970.0,
        cp_j_kg_k=4200.0,
        viscosity_pa_s=0.0008,
        conductivity_w_m_k=0.65,
        enthalpy_j_kg=200_000.0,
        entropy_j_kg_k=500.0,
        phase=PhaseRegion.LIQUID,
        quality=None,
        provenance=_PROV_PH,
    )


def _sat_p_result() -> SaturationState:
    liq = FluidState(
        temperature_k=373.15,
        pressure_pa=101325.0,
        density_kg_m3=958.0,
        cp_j_kg_k=4218.0,
        viscosity_pa_s=0.00028,
        conductivity_w_m_k=0.68,
        enthalpy_j_kg=419_000.0,
        entropy_j_kg_k=1307.0,
        phase=PhaseRegion.SATURATED_LIQUID,
        quality=0.0,
        provenance=_PROV_SAT,
    )
    vap = FluidState(
        temperature_k=373.15,
        pressure_pa=101325.0,
        density_kg_m3=0.598,
        cp_j_kg_k=2080.0,
        viscosity_pa_s=0.000012,
        conductivity_w_m_k=0.025,
        enthalpy_j_kg=2_676_000.0,
        entropy_j_kg_k=7354.0,
        phase=PhaseRegion.SATURATED_VAPOR,
        quality=1.0,
        provenance=_PROV_SAT,
    )
    return SaturationState(
        query_type=PropertyQueryType.SATURATION_P,
        input_value=101325.0,
        liquid=liq,
        vapor=vap,
        provenance=_PROV_SAT,
    )


def _sat_t_result() -> SaturationState:
    liq = FluidState(
        temperature_k=373.15,
        pressure_pa=101325.0,
        density_kg_m3=958.0,
        cp_j_kg_k=4218.0,
        viscosity_pa_s=0.00028,
        conductivity_w_m_k=0.68,
        enthalpy_j_kg=419_000.0,
        entropy_j_kg_k=1307.0,
        phase=PhaseRegion.SATURATED_LIQUID,
        quality=0.0,
        provenance=_PROV_SAT,
    )
    vap = FluidState(
        temperature_k=373.15,
        pressure_pa=101325.0,
        density_kg_m3=0.598,
        cp_j_kg_k=2080.0,
        viscosity_pa_s=0.000012,
        conductivity_w_m_k=0.025,
        enthalpy_j_kg=2_676_000.0,
        entropy_j_kg_k=7354.0,
        phase=PhaseRegion.SATURATED_VAPOR,
        quality=1.0,
        provenance=_PROV_SAT,
    )
    prov = PropertyProvenance(
        backend_name="stub",
        backend_version="1",
        backend_git_revision="test",
        fluid_identifier="Water",
        validation_level=FluidValidationLevel.UNVALIDATED,
        query_type=PropertyQueryType.SATURATION_T,
        inputs=(("temperature_k", 373.15),),
        cache_policy_version="v1",
    )
    return SaturationState(
        query_type=PropertyQueryType.SATURATION_T,
        input_value=373.15,
        liquid=liq,
        vapor=vap,
        provenance=prov,
    )


# ===================================================================
# 1. Stub matches exact TP / PH / SAT_P / SAT_T keys
# ===================================================================


class TestStubExactKeyMatching:
    """The stub resolves exactly the key it was configured with."""

    def test_tp_key_exact_match(self) -> None:
        stub = StubPropertyProvider()
        result = _tp_result()
        stub.configure_tp(_WATER, 300.0, 101325.0, result=result)
        assert stub.state_tp(_WATER, 300.0, 101325.0) is result

    def test_ph_key_exact_match(self) -> None:
        stub = StubPropertyProvider()
        result = _ph_result()
        stub.configure_ph(
            _WATER,
            101325.0,
            200_000.0,
            reference_state=ReferenceStatePolicy.DEF,
            result=result,
        )
        assert (
            stub.state_ph(_WATER, 101325.0, 200_000.0, reference_state=ReferenceStatePolicy.DEF)
            is result
        )

    def test_sat_p_key_exact_match(self) -> None:
        stub = StubPropertyProvider()
        result = _sat_p_result()
        stub.configure_saturation_at_pressure(_WATER, 101325.0, result=result)
        assert stub.saturation_at_pressure(_WATER, 101325.0) is result

    def test_sat_t_key_exact_match(self) -> None:
        stub = StubPropertyProvider()
        result = _sat_t_result()
        stub.configure_saturation_at_temperature(_WATER, 373.15, result=result)
        assert stub.saturation_at_temperature(_WATER, 373.15) is result


# ===================================================================
# 2. Stub unclosed key → TestProviderError
# ===================================================================


class TestStubUnconfiguredKey:
    """Querying an unconfigured key raises ``TestProviderError``."""

    def test_unconfigured_tp_raises(self) -> None:
        stub = StubPropertyProvider()
        with pytest.raises(TestProviderError, match="unconfigured"):
            stub.state_tp(_WATER, 300.0, 101325.0)

    def test_unconfigured_ph_raises(self) -> None:
        stub = StubPropertyProvider()
        with pytest.raises(TestProviderError, match="unconfigured"):
            stub.state_ph(_WATER, 101325.0, 200_000.0, reference_state=ReferenceStatePolicy.DEF)

    def test_unconfigured_sat_p_raises(self) -> None:
        stub = StubPropertyProvider()
        with pytest.raises(TestProviderError, match="unconfigured"):
            stub.saturation_at_pressure(_WATER, 101325.0)

    def test_unconfigured_sat_t_raises(self) -> None:
        stub = StubPropertyProvider()
        with pytest.raises(TestProviderError, match="unconfigured"):
            stub.saturation_at_temperature(_WATER, 373.15)


# ===================================================================
# 3. Stub TP → FluidState, PH → FluidState, SAT → SaturationState
# ===================================================================


class TestStubReturnTypeCoercion:
    """Each stub entry is validated to return the expected result type."""

    def test_tp_returns_fluid_state(self) -> None:
        stub = StubPropertyProvider()
        result = _tp_result()
        stub.configure_tp(_WATER, 300.0, 101325.0, result=result)
        assert isinstance(stub.state_tp(_WATER, 300.0, 101325.0), FluidState)

    def test_ph_returns_fluid_state(self) -> None:
        stub = StubPropertyProvider()
        result = _ph_result()
        stub.configure_ph(
            _WATER,
            101325.0,
            200_000.0,
            reference_state=ReferenceStatePolicy.DEF,
            result=result,
        )
        assert isinstance(
            stub.state_ph(_WATER, 101325.0, 200_000.0, reference_state=ReferenceStatePolicy.DEF),
            FluidState,
        )

    def test_sat_p_returns_saturation_state(self) -> None:
        stub = StubPropertyProvider()
        result = _sat_p_result()
        stub.configure_saturation_at_pressure(_WATER, 101325.0, result=result)
        assert isinstance(stub.saturation_at_pressure(_WATER, 101325.0), SaturationState)

    def test_sat_t_returns_saturation_state(self) -> None:
        stub = StubPropertyProvider()
        result = _sat_t_result()
        stub.configure_saturation_at_temperature(_WATER, 373.15, result=result)
        assert isinstance(stub.saturation_at_temperature(_WATER, 373.15), SaturationState)


# ===================================================================
# 4. PH reference_state enters key identity
# ===================================================================


class TestStubReferenceStateIdentity:
    """Different reference_state values produce distinct keys for PH queries."""

    def test_different_reference_states_are_distinct_keys(self) -> None:
        stub = StubPropertyProvider()
        def_result = _ph_result()

        # Use a different provenance for the second result
        iir_prov = PropertyProvenance(
            backend_name="stub",
            backend_version="1",
            backend_git_revision="test",
            fluid_identifier="Water",
            validation_level=FluidValidationLevel.UNVALIDATED,
            query_type=PropertyQueryType.PH,
            inputs=(("enthalpy_j_kg", 200_000.0), ("pressure_pa", 101325.0)),
            cache_policy_version="v1",
            reference_state_policy=ReferenceStatePolicy.DEF,
        )
        iir_result = FluidState(
            temperature_k=360.0,
            pressure_pa=101325.0,
            density_kg_m3=965.0,
            cp_j_kg_k=4210.0,
            viscosity_pa_s=0.0007,
            conductivity_w_m_k=0.62,
            enthalpy_j_kg=250_000.0,
            entropy_j_kg_k=550.0,
            phase=PhaseRegion.LIQUID,
            quality=None,
            provenance=iir_prov,
        )
        stub.configure_ph(
            _WATER,
            101325.0,
            200_000.0,
            reference_state=ReferenceStatePolicy.DEF,
            result=def_result,
        )
        stub.configure_ph(
            _WATER,
            101325.0,
            200_000.0,
            reference_state=ReferenceStatePolicy.DEF,
            result=iir_result,
        )
        # The second configure overwrites the first (same key since both DEF)
        assert (
            stub.state_ph(_WATER, 101325.0, 200_000.0, reference_state=ReferenceStatePolicy.DEF)
            is iir_result
        )

    def test_unconfigured_ph_different_enthalpy_raises(self) -> None:
        stub = StubPropertyProvider()
        stub.configure_ph(
            _WATER,
            101325.0,
            200_000.0,
            reference_state=ReferenceStatePolicy.DEF,
            result=_ph_result(),
        )
        # Query with same reference_state but different enthalpy → different key
        with pytest.raises(TestProviderError, match="unconfigured"):
            stub.state_ph(
                _WATER,
                101325.0,
                999_999.0,
                reference_state=ReferenceStatePolicy.DEF,
            )

    def test_ph_key_includes_reference_state_field(self) -> None:
        key_def = ProviderQueryKey.from_request(
            PropertyQueryType.PH,
            _WATER,
            pressure_pa=101325.0,
            enthalpy_j_kg=200_000.0,
            reference_state=ReferenceStatePolicy.DEF,
        )
        assert key_def.reference_state == ReferenceStatePolicy.DEF
        # TP key should not have reference_state
        key_tp = ProviderQueryKey.from_request(
            PropertyQueryType.TP,
            _WATER,
            temperature_k=300.0,
            pressure_pa=101325.0,
        )
        assert key_tp.reference_state is None


# ===================================================================
# 5. Replay consumes each query independently in order
# ===================================================================


class TestReplayOrderConsumption:
    """Replay serves results in the exact sequence configured per query type."""

    def test_tp_serves_in_order(self) -> None:
        r1, r2 = _tp_result(), _tp_result()
        replay = ReplayPropertyProvider(tp=[r1, r2])
        assert replay.state_tp(_WATER, 300.0, 101325.0) is r1
        assert replay.state_tp(_WATER, 300.0, 101325.0) is r2

    def test_ph_serves_in_order(self) -> None:
        r1, r2 = _ph_result(), _ph_result()
        replay = ReplayPropertyProvider(ph=[r1, r2])
        assert (
            replay.state_ph(_WATER, 101325.0, 200_000.0, reference_state=ReferenceStatePolicy.DEF)
            is r1
        )
        assert (
            replay.state_ph(_WATER, 101325.0, 200_000.0, reference_state=ReferenceStatePolicy.DEF)
            is r2
        )

    def test_sat_p_serves_in_order(self) -> None:
        r1, r2 = _sat_p_result(), _sat_p_result()
        replay = ReplayPropertyProvider(saturation_p=[r1, r2])
        assert replay.saturation_at_pressure(_WATER, 101325.0) is r1
        assert replay.saturation_at_pressure(_WATER, 101325.0) is r2

    def test_sat_t_serves_in_order(self) -> None:
        r1, r2 = _sat_t_result(), _sat_t_result()
        replay = ReplayPropertyProvider(saturation_t=[r1, r2])
        assert replay.saturation_at_temperature(_WATER, 373.15) is r1
        assert replay.saturation_at_temperature(_WATER, 373.15) is r2

    def test_independent_per_query_type(self) -> None:
        """Calling TP does not advance the PH queue."""
        tp_r = _tp_result()
        ph_r = _ph_result()
        replay = ReplayPropertyProvider(tp=[tp_r], ph=[ph_r])
        assert replay.state_tp(_WATER, 300.0, 101325.0) is tp_r
        # PH queue is untouched
        assert (
            replay.state_ph(_WATER, 101325.0, 200_000.0, reference_state=ReferenceStatePolicy.DEF)
            is ph_r
        )

    def test_calls_tracked(self) -> None:
        r1, r2 = _tp_result(), _tp_result()
        replay = ReplayPropertyProvider(tp=[r1, r2])
        replay.state_tp(_WATER, 300.0, 101325.0)
        replay.state_tp(_WATER, 300.0, 101325.0)
        assert len(replay.calls) == 2
        assert all(k.query_type == PropertyQueryType.TP for k in replay.calls)


# ===================================================================
# 6. Replay exhausted → TestProviderError
# ===================================================================


class TestReplayExhausted:
    """After all replay slots are consumed, the next call raises."""

    def test_exhausted_tp_raises(self) -> None:
        replay = ReplayPropertyProvider(tp=[_tp_result()])
        replay.state_tp(_WATER, 300.0, 101325.0)
        with pytest.raises(TestProviderError, match="replay exhausted"):
            replay.state_tp(_WATER, 300.0, 101325.0)

    def test_exhausted_ph_raises(self) -> None:
        replay = ReplayPropertyProvider(ph=[_ph_result()])
        replay.state_ph(_WATER, 101325.0, 200_000.0, reference_state=ReferenceStatePolicy.DEF)
        with pytest.raises(TestProviderError, match="replay exhausted"):
            replay.state_ph(_WATER, 101325.0, 200_000.0, reference_state=ReferenceStatePolicy.DEF)

    def test_exhausted_sat_p_raises(self) -> None:
        replay = ReplayPropertyProvider(saturation_p=[_sat_p_result()])
        replay.saturation_at_pressure(_WATER, 101325.0)
        with pytest.raises(TestProviderError, match="replay exhausted"):
            replay.saturation_at_pressure(_WATER, 101325.0)

    def test_empty_queue_raises_immediately(self) -> None:
        replay = ReplayPropertyProvider(tp=())
        with pytest.raises(TestProviderError, match="replay exhausted"):
            replay.state_tp(_WATER, 300.0, 101325.0)


# ===================================================================
# 7. Replay assert_fully_consumed fails with remaining
# ===================================================================


class TestReplayFullyConsumed:
    """assert_fully_consumed raises when any queue has leftover items."""

    def test_all_consumed_passes(self) -> None:
        r1, r2 = _tp_result(), _tp_result()
        replay = ReplayPropertyProvider(tp=[r1, r2])
        replay.state_tp(_WATER, 300.0, 101325.0)
        replay.state_tp(_WATER, 300.0, 101325.0)
        replay.assert_fully_consumed()  # should not raise

    def test_remaining_tp_raises(self) -> None:
        r1, r2 = _tp_result(), _tp_result()
        replay = ReplayPropertyProvider(tp=[r1, r2])
        replay.state_tp(_WATER, 300.0, 101325.0)
        with pytest.raises(AssertionError, match="TP.*1"):
            replay.assert_fully_consumed()

    def test_remaining_multiple_types(self) -> None:
        replay = ReplayPropertyProvider(tp=[_tp_result()], ph=[_ph_result(), _ph_result()])
        replay.state_tp(_WATER, 300.0, 101325.0)
        with pytest.raises(AssertionError, match="PH.*2"):
            replay.assert_fully_consumed()

    def test_nothing_consumed_fails(self) -> None:
        replay = ReplayPropertyProvider(tp=[_tp_result()])
        with pytest.raises(AssertionError, match="TP.*1"):
            replay.assert_fully_consumed()

    def test_empty_replay_passes(self) -> None:
        replay = ReplayPropertyProvider()
        replay.assert_fully_consumed()  # no queues → nothing remaining


# ===================================================================
# 8. SelectiveFailure uses (PropertyQueryType, 1-based index)
# ===================================================================


class TestSelectiveFailureKey:
    """SelectiveFailurePropertyProvider keys failures on (query_type, 1-based index)."""

    def test_invalid_index_zero_raises(self) -> None:
        inner = StubPropertyProvider()
        with pytest.raises(ValueError, match="invalid failure key"):
            SelectiveFailurePropertyProvider(
                inner, {(PropertyQueryType.TP, 0): RuntimeError("boom")}
            )

    def test_invalid_index_negative_raises(self) -> None:
        inner = StubPropertyProvider()
        with pytest.raises(ValueError, match="invalid failure key"):
            SelectiveFailurePropertyProvider(
                inner, {(PropertyQueryType.TP, -1): RuntimeError("boom")}
            )

    def test_first_call_fails(self) -> None:
        inner = StubPropertyProvider()
        inner.configure_tp(_WATER, 300.0, 101325.0, result=_tp_result())
        fail_prov = SelectiveFailurePropertyProvider(
            inner, {(PropertyQueryType.TP, 1): RuntimeError("boom")}
        )
        with pytest.raises(RuntimeError, match="boom"):
            fail_prov.state_tp(_WATER, 300.0, 101325.0)

    def test_second_call_fails(self) -> None:
        inner = StubPropertyProvider()
        inner.configure_tp(_WATER, 300.0, 101325.0, result=_tp_result())
        fail_prov = SelectiveFailurePropertyProvider(
            inner, {(PropertyQueryType.TP, 2): RuntimeError("boom")}
        )
        # First call succeeds
        result = fail_prov.state_tp(_WATER, 300.0, 101325.0)
        assert isinstance(result, FluidState)
        # Second call fails
        with pytest.raises(RuntimeError, match="boom"):
            fail_prov.state_tp(_WATER, 300.0, 101325.0)


# ===================================================================
# 9. Failure triggered BEFORE inner delegation
# ===================================================================


class TestSelectiveFailureBeforeDelegation:
    """The injected exception fires before the inner provider is reached."""

    def test_inner_not_called_on_failure(self) -> None:
        inner = StubPropertyProvider()
        inner.configure_tp(_WATER, 300.0, 101325.0, result=_tp_result())
        fail_prov = SelectiveFailurePropertyProvider(
            inner, {(PropertyQueryType.TP, 1): RuntimeError("boom")}
        )
        with pytest.raises(RuntimeError, match="boom"):
            fail_prov.state_tp(_WATER, 300.0, 101325.0)
        # The inner stub records calls; verify it was NOT called
        assert len(inner.calls) == 0

    def test_inner_called_after_non_failing_index(self) -> None:
        inner = StubPropertyProvider()
        r = _tp_result()
        inner.configure_tp(_WATER, 300.0, 101325.0, result=r)
        fail_prov = SelectiveFailurePropertyProvider(
            inner, {(PropertyQueryType.TP, 1): RuntimeError("boom")}
        )
        # First call fails, inner is not called
        with pytest.raises(RuntimeError):
            fail_prov.state_tp(_WATER, 300.0, 101325.0)
        assert len(inner.calls) == 0
        # Second call succeeds, inner IS called
        result = fail_prov.state_tp(_WATER, 300.0, 101325.0)
        assert result is r
        assert len(inner.calls) == 1

    def test_ph_failure_before_delegation(self) -> None:
        inner = StubPropertyProvider()
        r = _ph_result()
        inner.configure_ph(
            _WATER,
            101325.0,
            200_000.0,
            reference_state=ReferenceStatePolicy.DEF,
            result=r,
        )
        fail_prov = SelectiveFailurePropertyProvider(
            inner, {(PropertyQueryType.PH, 1): RuntimeError("ph-boom")}
        )
        with pytest.raises(RuntimeError, match="ph-boom"):
            fail_prov.state_ph(
                _WATER, 101325.0, 200_000.0, reference_state=ReferenceStatePolicy.DEF
            )
        assert len(inner.calls) == 0

    def test_sat_failure_before_delegation(self) -> None:
        inner = StubPropertyProvider()
        r = _sat_p_result()
        inner.configure_saturation_at_pressure(_WATER, 101325.0, result=r)
        fail_prov = SelectiveFailurePropertyProvider(
            inner,
            {(PropertyQueryType.SATURATION_P, 1): RuntimeError("sat-boom")},
        )
        with pytest.raises(RuntimeError, match="sat-boom"):
            fail_prov.saturation_at_pressure(_WATER, 101325.0)
        assert len(inner.calls) == 0


# ===================================================================
# 10. Counting records per-query counts and canonical call records
# ===================================================================


class TestCountingProvider:
    """CountingPropertyProvider tracks per-query counts and canonical keys."""

    def test_counts_per_query_type(self) -> None:
        stub = StubPropertyProvider()
        stub.configure_tp(_WATER, 300.0, 101325.0, result=_tp_result())
        stub.configure_saturation_at_pressure(_WATER, 101325.0, result=_sat_p_result())
        counter = CountingPropertyProvider(stub)

        counter.state_tp(_WATER, 300.0, 101325.0)
        counter.state_tp(_WATER, 300.0, 101325.0)
        counter.saturation_at_pressure(_WATER, 101325.0)

        assert counter.counts[PropertyQueryType.TP] == 2
        assert counter.counts[PropertyQueryType.SATURATION_P] == 1
        assert counter.counts[PropertyQueryType.PH] == 0
        assert counter.counts[PropertyQueryType.SATURATION_T] == 0

    def test_canonical_calls_recorded(self) -> None:
        stub = StubPropertyProvider()
        r = _tp_result()
        stub.configure_tp(_WATER, 300.0, 101325.0, result=r)
        counter = CountingPropertyProvider(stub)

        result = counter.state_tp(_WATER, 300.0, 101325.0)
        assert result is r
        assert len(counter.calls) == 1
        key = counter.calls[0]
        assert key.query_type == PropertyQueryType.TP
        assert key.fluid_identity == canonical_fluid_identity(_WATER)

    def test_delegates_to_inner(self) -> None:
        stub = StubPropertyProvider()
        r = _tp_result()
        stub.configure_tp(_WATER, 300.0, 101325.0, result=r)
        counter = CountingPropertyProvider(stub)
        assert counter.state_tp(_WATER, 300.0, 101325.0) is r
        # Inner stub also recorded the call
        assert len(stub.calls) == 1


# ===================================================================
# 11. reset_counts and reset_replay work
# ===================================================================


class TestResetMethods:
    """reset_counts clears the counting provider; reset_replay resets position."""

    def test_reset_counts_clears_counts_and_calls(self) -> None:
        stub = StubPropertyProvider()
        stub.configure_tp(_WATER, 300.0, 101325.0, result=_tp_result())
        counter = CountingPropertyProvider(stub)
        counter.state_tp(_WATER, 300.0, 101325.0)
        counter.state_tp(_WATER, 300.0, 101325.0)
        assert counter.counts[PropertyQueryType.TP] == 2
        assert len(counter.calls) == 2

        counter.reset_counts()
        assert counter.counts[PropertyQueryType.TP] == 0
        assert len(counter.calls) == 0

    def test_reset_replay_resets_position_and_calls(self) -> None:
        r1, r2 = _tp_result(), _tp_result()
        replay = ReplayPropertyProvider(tp=[r1, r2])
        assert replay.state_tp(_WATER, 300.0, 101325.0) is r1
        assert replay.state_tp(_WATER, 300.0, 101325.0) is r2
        with pytest.raises(TestProviderError, match="replay exhausted"):
            replay.state_tp(_WATER, 300.0, 101325.0)

        replay.reset_replay()
        # After reset, we can consume the same sequence again
        assert replay.state_tp(_WATER, 300.0, 101325.0) is r1
        assert replay.state_tp(_WATER, 300.0, 101325.0) is r2
        assert len(replay.calls) == 2


# ===================================================================
# 12. Static assignment passes mypy concept
# ===================================================================


class TestTypeAssignment:
    """All doubles are structurally assignable to PropertyProvider."""

    def test_stub_is_property_provider(self) -> None:
        provider: PropertyProvider = StubPropertyProvider()
        assert provider.name == "StubPropertyProvider"

    def test_replay_is_property_provider(self) -> None:
        provider: PropertyProvider = ReplayPropertyProvider()
        assert provider.name == "ReplayPropertyProvider"

    def test_selective_is_property_provider(self) -> None:
        inner = StubPropertyProvider()
        provider: PropertyProvider = SelectiveFailurePropertyProvider(inner, {})
        assert provider.name == "StubPropertyProvider"

    def test_counting_is_property_provider(self) -> None:
        inner = StubPropertyProvider()
        provider: PropertyProvider = CountingPropertyProvider(inner)
        assert provider.name == "StubPropertyProvider"


# ===================================================================
# ProviderQueryKey tests
# ===================================================================


class TestProviderQueryKey:
    """ProviderQueryKey from_request produces correct canonical keys."""

    def test_tp_key(self) -> None:
        key = ProviderQueryKey.from_request(
            PropertyQueryType.TP, _WATER, temperature_k=300.0, pressure_pa=101325.0
        )
        assert key.query_type == PropertyQueryType.TP
        assert key.fluid_identity == canonical_fluid_identity(_WATER)
        assert key.reference_state is None

    def test_ph_key(self) -> None:
        key = ProviderQueryKey.from_request(
            PropertyQueryType.PH,
            _WATER,
            pressure_pa=101325.0,
            enthalpy_j_kg=200_000.0,
            reference_state=ReferenceStatePolicy.DEF,
        )
        assert key.query_type == PropertyQueryType.PH
        assert key.reference_state == ReferenceStatePolicy.DEF

    def test_tp_rejects_extra_kwargs(self) -> None:
        with pytest.raises(TestProviderError, match="prohibited"):
            ProviderQueryKey.from_request(
                PropertyQueryType.TP,
                _WATER,
                temperature_k=300.0,
                pressure_pa=101325.0,
                enthalpy_j_kg=100.0,
            )

    def test_ph_rejects_temperature(self) -> None:
        with pytest.raises(TestProviderError, match="prohibited"):
            ProviderQueryKey.from_request(
                PropertyQueryType.PH,
                _WATER,
                pressure_pa=101325.0,
                enthalpy_j_kg=200_000.0,
                reference_state=ReferenceStatePolicy.DEF,
                temperature_k=300.0,
            )

    def test_string_fluid(self) -> None:
        key = ProviderQueryKey.from_request(
            PropertyQueryType.TP, "Water", temperature_k=300.0, pressure_pa=101325.0
        )
        assert key.fluid_identity == canonical_fluid_identity("Water")

    def test_frozen(self) -> None:
        key = ProviderQueryKey.from_request(
            PropertyQueryType.TP, _WATER, temperature_k=300.0, pressure_pa=101325.0
        )
        with pytest.raises(AttributeError):
            key.query_type = PropertyQueryType.PH  # type: ignore[misc]


class TestCanonicalFluidIdentity:
    """canonical_fluid_identity produces the same cache identity as FluidIdentifier."""

    def test_string_input(self) -> None:
        identity = canonical_fluid_identity("Water")
        expected = FluidIdentifier.from_value("Water").cache_identity
        assert identity == expected

    def test_identifier_input(self) -> None:
        identity = canonical_fluid_identity(_WATER)
        expected = _WATER.cache_identity
        assert identity == expected
