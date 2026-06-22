"""Unit tests for TASK-006 — heat-balance and specification-closure kernel.

Uses a mock PropertyProvider to isolate the kernel from CoolProp.
Integration tests with real CoolProp are in
``tests/integration/test_heat_balance_property_provider.py``.

Covers all required test scenarios from the task card.
"""

from __future__ import annotations

import math
from unittest.mock import MagicMock

import pytest

from hexagent.core.heat_balance import (
    HeatBalanceInput,
    SolverParams,
    SpecificationMode,
    StreamState,
    classify_specification,
    solve_heat_balance,
)
from hexagent.domain.provenance import ProvenanceEdge, ProvenanceGraph, ProvenanceNode
from hexagent.properties.base import (
    FluidIdentifier,
    FluidState,
    PhaseRegion,
    PropertyCacheInfo,
    ReferenceStatePolicy,
    SaturationState,
)
from hexagent.properties.errors import PropertyErrorCode, PropertyServiceError

# ---------------------------------------------------------------------------
# Mock property provider — simple linear Cp model
# ---------------------------------------------------------------------------

# Water-like: Cp ~ 4180 J/(kg·K), h(T) = Cp * (T - 273.15) [reference at 0°C]
_WATER_CP = 4180.0
_WATER_T_REF = 273.15
_WATER_H_REF = 0.0  # h(273.15 K) = 0


def _water_enthalpy(t_k: float) -> float:
    return _WATER_CP * (t_k - _WATER_T_REF) + _WATER_H_REF


# Air-like: Cp ~ 1005 J/(kg·K)
_AIR_CP = 1005.0
_AIR_T_REF = 273.15


def _air_enthalpy(t_k: float) -> float:
    return _AIR_CP * (t_k - _AIR_T_REF)


class MockPropertyProvider:
    """Deterministic mock property provider for unit tests.

    Supports Water and Air with constant Cp (for unit-test isolation;
    integration tests use real CoolProp with temperature-dependent Cp).
    """

    def __init__(
        self,
        *,
        fail_fluid: str | None = None,
        out_of_range_temps: tuple[float, float] = (0.0, 1000.0),
    ) -> None:
        self._fail_fluid = fail_fluid
        self._oor_temps = out_of_range_temps
        self._call_count = 0

    @property
    def name(self) -> str:
        return "MockProvider"

    @property
    def version(self) -> str:
        return "0.1.0-test"

    @property
    def git_revision(self) -> str:
        return "mock"

    @property
    def reference_state_policy(self) -> ReferenceStatePolicy:
        return ReferenceStatePolicy.DEF

    def state_tp(
        self,
        fluid: FluidIdentifier | str,
        temperature_k: float,
        pressure_pa: float,
    ) -> FluidState:
        self._call_count += 1
        fluid_name = str(fluid) if not hasattr(fluid, "name") else fluid.name

        if self._fail_fluid and fluid_name == self._fail_fluid:
            raise PropertyServiceError(
                PropertyErrorCode.BACKEND_FAILURE,
                f"Mock failure for {fluid_name}",
            )

        if not (self._oor_temps[0] < temperature_k < self._oor_temps[1]):
            raise PropertyServiceError(
                PropertyErrorCode.STATE_OUT_OF_RANGE,
                f"Temperature {temperature_k} K out of range",
            )

        if fluid_name in ("Water", "water"):
            h = _water_enthalpy(temperature_k)
            cp = _WATER_CP
            phase = PhaseRegion.LIQUID
        elif fluid_name in ("Air", "air"):
            h = _air_enthalpy(temperature_k)
            cp = _AIR_CP
            phase = PhaseRegion.GAS
        else:
            raise PropertyServiceError(
                PropertyErrorCode.INVALID_FLUID,
                f"Unknown fluid: {fluid_name}",
            )

        return FluidState(
            temperature_k=temperature_k,
            pressure_pa=pressure_pa,
            density_kg_m3=1000.0 if "Water" in fluid_name else 1.2,
            cp_j_kg_k=cp,
            viscosity_pa_s=0.001 if "Water" in fluid_name else 1.8e-5,
            conductivity_w_m_k=0.6 if "Water" in fluid_name else 0.026,
            enthalpy_j_kg=h,
            entropy_j_kg_k=0.0,
            phase=phase,
            quality=None,
            provenance=MagicMock(),
        )

    def state_ph(
        self,
        fluid: FluidIdentifier | str,
        pressure_pa: float,
        enthalpy_j_kg: float,
        *,
        reference_state: ReferenceStatePolicy,
    ) -> FluidState:
        raise NotImplementedError("Not needed for unit tests")

    def saturation_at_pressure(
        self,
        fluid: FluidIdentifier | str,
        pressure_pa: float,
    ) -> SaturationState:
        raise NotImplementedError("Not needed for unit tests")

    def saturation_at_temperature(
        self,
        fluid: FluidIdentifier | str,
        temperature_k: float,
    ) -> SaturationState:
        raise NotImplementedError("Not needed for unit tests")

    def cache_info(self) -> PropertyCacheInfo:
        return PropertyCacheInfo(hits=0, misses=self._call_count, size=0, max_size=0)

    def clear_cache(self) -> None:
        self._call_count = 0


# ---------------------------------------------------------------------------
# Helper builders
# ---------------------------------------------------------------------------


def _water_stream(
    *,
    inlet_t: float = 350.0,
    outlet_t: float | None = 310.0,
    mass_flow: float = 1.0,
    pressure: float = 200000.0,
) -> StreamState:
    return StreamState(
        fluid_identifier=FluidIdentifier(name="Water"),
        mass_flow_kg_s=mass_flow,
        inlet_temperature_k=inlet_t,
        inlet_pressure_pa=pressure,
        outlet_temperature_k=outlet_t,
    )


def _air_stream(
    *,
    inlet_t: float = 400.0,
    outlet_t: float | None = 320.0,
    mass_flow: float = 0.5,
    pressure: float = 101325.0,
) -> StreamState:
    return StreamState(
        fluid_identifier=FluidIdentifier(name="Air"),
        mass_flow_kg_s=mass_flow,
        inlet_temperature_k=inlet_t,
        inlet_pressure_pa=pressure,
        outlet_temperature_k=outlet_t,
    )


def _default_params() -> SolverParams:
    return SolverParams(temperature_tolerance=1e-4, energy_tolerance=1e-3, max_iterations=100)


# ======================================================================
# Specification classification tests
# ======================================================================


class TestSpecificationClassification:
    """Test the specification classifier for all supported modes."""

    def test_known_duty(self) -> None:
        hot = _water_stream(outlet_t=None)
        cold = _water_stream(outlet_t=None)
        inp = HeatBalanceInput(hot=hot, cold=cold, known_duty_w=100000.0)
        assert classify_specification(inp) == SpecificationMode.KNOWN_DUTY

    def test_known_hot_outlet(self) -> None:
        hot = _water_stream(outlet_t=310.0)
        cold = _water_stream(outlet_t=None)
        inp = HeatBalanceInput(hot=hot, cold=cold)
        assert classify_specification(inp) == SpecificationMode.KNOWN_HOT_OUTLET

    def test_known_cold_outlet(self) -> None:
        hot = _water_stream(outlet_t=None)
        cold = _water_stream(outlet_t=330.0)
        inp = HeatBalanceInput(hot=hot, cold=cold)
        assert classify_specification(inp) == SpecificationMode.KNOWN_COLD_OUTLET

    def test_both_outlets_known(self) -> None:
        hot = _water_stream(outlet_t=310.0)
        cold = _water_stream(outlet_t=330.0)
        inp = HeatBalanceInput(hot=hot, cold=cold)
        assert classify_specification(inp) == SpecificationMode.BOTH_OUTLETS_KNOWN

    def test_one_side_known_hot_outlet_with_duty(self) -> None:
        hot = _water_stream(outlet_t=310.0)
        cold = _water_stream(outlet_t=None)
        inp = HeatBalanceInput(hot=hot, cold=cold, known_duty_w=167200.0)
        assert classify_specification(inp) == SpecificationMode.KNOWN_HOT_OUTLET

    def test_one_side_known_cold_outlet_with_duty(self) -> None:
        hot = _water_stream(outlet_t=None)
        cold = _water_stream(outlet_t=330.0)
        inp = HeatBalanceInput(hot=hot, cold=cold, known_duty_w=133760.0)
        assert classify_specification(inp) == SpecificationMode.KNOWN_COLD_OUTLET

    def test_under_specified(self) -> None:
        hot = _water_stream(outlet_t=None)
        cold = _water_stream(outlet_t=None)
        inp = HeatBalanceInput(hot=hot, cold=cold)
        assert classify_specification(inp) == SpecificationMode.UNDER_SPECIFIED

    def test_over_specified(self) -> None:
        hot = _water_stream(outlet_t=310.0)
        cold = _water_stream(outlet_t=330.0)
        inp = HeatBalanceInput(hot=hot, cold=cold, known_duty_w=167200.0)
        assert classify_specification(inp) == SpecificationMode.OVER_SPECIFIED


# ======================================================================
# Energy convention tests
# ======================================================================


class TestEnergyConvention:
    """Verify Q_hot, Q_cold and residual definitions."""

    def test_known_duty_energy_balance(self) -> None:
        """With known duty, Q_hot = Q_cold = Q by construction."""
        provider = MockPropertyProvider()
        hot = _water_stream(outlet_t=None, mass_flow=1.0)
        cold = _water_stream(outlet_t=None, mass_flow=0.8, inlet_t=290.0)
        # Q = 167200 W
        # Hot: h_out = h_in - Q/m = 4180*(350-273.15) - 167200/1.0 = 321233 - 167200 = 154033
        # T_out_hot = 154033/4180 + 273.15 = 36.85 + 273.15 = 310.0 K
        # Cold: h_out = h_in + Q/m = 4180*(290-273.15) + 167200/0.8 = 70398 + 209000 = 279398
        # T_out_cold = 279398/4180 + 273.15 = 66.84 + 273.15 = 340.0 K
        inp = HeatBalanceInput(
            hot=hot, cold=cold, known_duty_w=167200.0, solver_params=_default_params()
        )
        result = solve_heat_balance(inp, provider)

        assert result.specification_mode == SpecificationMode.KNOWN_DUTY
        assert result.duty_w == pytest.approx(167200.0, abs=1.0)
        assert abs(result.residual_w) < 1.0
        assert result.relative_imbalance < 0.001
        assert result.solver_converged

    def test_residual_definition(self) -> None:
        """Residual = Q_hot - Q_cold."""
        provider = MockPropertyProvider()
        hot = _water_stream(outlet_t=310.0, mass_flow=1.0)
        cold = _water_stream(outlet_t=None, mass_flow=0.8, inlet_t=290.0)
        inp = HeatBalanceInput(hot=hot, cold=cold, solver_params=_default_params())
        result = solve_heat_balance(inp, provider)

        # Q_hot = 1.0 * 4180 * (350 - 310) = 167200
        # Q_cold = 0.8 * 4180 * (T_cold_out - 290)
        # For perfect mock: Q_cold = Q_hot, residual ~ 0
        q_hot = 1.0 * _WATER_CP * (350.0 - 310.0)
        q_cold = 0.8 * _WATER_CP * (result.cold_outlet_state["temperature_k"] - 290.0)
        expected_residual = q_hot - q_cold
        assert result.residual_w == pytest.approx(expected_residual, abs=1.0)


# ======================================================================
# Solver tests — liquid-liquid
# ======================================================================


class TestLiquidLiquidNominal:
    """Liquid-liquid nominal balance tests."""

    def test_known_duty_water_water(self) -> None:
        provider = MockPropertyProvider()
        hot = _water_stream(outlet_t=None, inlet_t=350.0, mass_flow=1.0)
        cold = _water_stream(outlet_t=None, inlet_t=290.0, mass_flow=0.8)
        Q = 1.0 * _WATER_CP * (350.0 - 310.0)  # 167200 W
        inp = HeatBalanceInput(hot=hot, cold=cold, known_duty_w=Q, solver_params=_default_params())
        result = solve_heat_balance(inp, provider)

        assert result.specification_mode == SpecificationMode.KNOWN_DUTY
        assert result.hot_outlet_state["temperature_k"] == pytest.approx(310.0, abs=0.5)
        assert result.cold_outlet_state["temperature_k"] == pytest.approx(340.0, abs=0.5)
        assert result.relative_imbalance < 0.001

    def test_known_hot_outlet(self) -> None:
        provider = MockPropertyProvider()
        hot = _water_stream(outlet_t=310.0, inlet_t=350.0, mass_flow=1.0)
        cold = _water_stream(outlet_t=None, inlet_t=290.0, mass_flow=0.8)
        inp = HeatBalanceInput(hot=hot, cold=cold, solver_params=_default_params())
        result = solve_heat_balance(inp, provider)

        assert result.specification_mode == SpecificationMode.KNOWN_HOT_OUTLET
        expected_duty = 1.0 * _WATER_CP * (350.0 - 310.0)
        assert result.duty_w == pytest.approx(expected_duty, abs=1.0)
        assert result.cold_outlet_state["temperature_k"] == pytest.approx(340.0, abs=0.5)

    def test_known_cold_outlet(self) -> None:
        provider = MockPropertyProvider()
        hot = _water_stream(outlet_t=None, inlet_t=350.0, mass_flow=1.0)
        cold = _water_stream(outlet_t=340.0, inlet_t=290.0, mass_flow=0.8)
        inp = HeatBalanceInput(hot=hot, cold=cold, solver_params=_default_params())
        result = solve_heat_balance(inp, provider)

        assert result.specification_mode == SpecificationMode.KNOWN_COLD_OUTLET
        expected_duty = 0.8 * _WATER_CP * (340.0 - 290.0)
        assert result.duty_w == pytest.approx(expected_duty, abs=1.0)
        assert result.hot_outlet_state["temperature_k"] == pytest.approx(310.0, abs=0.5)


# ======================================================================
# Gas-liquid tests
# ======================================================================


class TestGasLiquidNominal:
    """Gas-liquid nominal balance (Air-water)."""

    def test_air_water_known_duty(self) -> None:
        provider = MockPropertyProvider()
        hot = StreamState(
            fluid_identifier=FluidIdentifier(name="Air"),
            mass_flow_kg_s=0.5,
            inlet_temperature_k=400.0,
            inlet_pressure_pa=101325.0,
            outlet_temperature_k=None,
        )
        cold = _water_stream(outlet_t=None, inlet_t=290.0, mass_flow=0.3)

        # Q = 0.5 * 1005 * (400 - 320) = 40200 W
        Q = 0.5 * _AIR_CP * (400.0 - 320.0)
        inp = HeatBalanceInput(hot=hot, cold=cold, known_duty_w=Q, solver_params=_default_params())
        result = solve_heat_balance(inp, provider)

        assert result.specification_mode == SpecificationMode.KNOWN_DUTY
        assert result.hot_outlet_state["temperature_k"] == pytest.approx(320.0, abs=0.5)
        assert result.relative_imbalance < 0.001

    def test_air_water_known_hot_outlet(self) -> None:
        provider = MockPropertyProvider()
        hot = StreamState(
            fluid_identifier=FluidIdentifier(name="Air"),
            mass_flow_kg_s=0.5,
            inlet_temperature_k=400.0,
            inlet_pressure_pa=101325.0,
            outlet_temperature_k=320.0,
        )
        cold = _water_stream(outlet_t=None, inlet_t=290.0, mass_flow=0.3)
        inp = HeatBalanceInput(hot=hot, cold=cold, solver_params=_default_params())
        result = solve_heat_balance(inp, provider)

        assert result.specification_mode == SpecificationMode.KNOWN_HOT_OUTLET
        expected_duty = 0.5 * _AIR_CP * (400.0 - 320.0)
        assert result.duty_w == pytest.approx(expected_duty, abs=1.0)


# ======================================================================
# Both-outlet verification mode
# ======================================================================


class TestBothOutletsKnown:
    """Both outlets known — energy balance verification."""

    def test_consistent_outlets(self) -> None:
        provider = MockPropertyProvider()
        hot = _water_stream(outlet_t=310.0, inlet_t=350.0, mass_flow=1.0)
        cold = _water_stream(outlet_t=340.0, inlet_t=290.0, mass_flow=0.8)
        inp = HeatBalanceInput(hot=hot, cold=cold, solver_params=_default_params())
        result = solve_heat_balance(inp, provider)

        assert result.specification_mode == SpecificationMode.BOTH_OUTLETS_KNOWN
        # With constant Cp mock: Q_hot = 1*4180*40 = 167200
        # Q_cold = 0.8*4180*50 = 167200 → residual ~ 0
        assert abs(result.residual_w) < 1.0
        assert result.relative_imbalance < 0.001

    def test_inconsistent_outlets(self) -> None:
        provider = MockPropertyProvider()
        hot = _water_stream(outlet_t=310.0, inlet_t=350.0, mass_flow=1.0)
        cold = _water_stream(outlet_t=320.0, inlet_t=290.0, mass_flow=0.8)
        inp = HeatBalanceInput(hot=hot, cold=cold, solver_params=_default_params())
        result = solve_heat_balance(inp, provider)

        assert result.specification_mode == SpecificationMode.BOTH_OUTLETS_KNOWN
        # Q_hot = 1*4180*40 = 167200, Q_cold = 0.8*4180*30 = 100320
        assert abs(result.residual_w) > 1000
        assert result.relative_imbalance > 0.001
        assert not result.solver_converged


# ======================================================================
# Inconsistent duty / outlet tests
# ======================================================================


class TestInconsistentDutyOutlet:
    """Duty and outlet state are inconsistent."""

    def test_hot_outlet_inconsistent_with_duty(self) -> None:
        provider = MockPropertyProvider()
        hot = _water_stream(outlet_t=310.0, inlet_t=350.0, mass_flow=1.0)
        cold = _water_stream(outlet_t=None, inlet_t=290.0, mass_flow=0.8)
        # Wrong duty: should be 167200 but we give 100000
        inp = HeatBalanceInput(
            hot=hot,
            cold=cold,
            known_duty_w=100000.0,
            solver_params=_default_params(),
        )
        with pytest.raises(ValueError, match="Over-specified|inconsistent"):
            solve_heat_balance(inp, provider)

    def test_cold_outlet_inconsistent_with_duty(self) -> None:
        provider = MockPropertyProvider()
        hot = _water_stream(outlet_t=None, inlet_t=350.0, mass_flow=1.0)
        cold = _water_stream(outlet_t=330.0, inlet_t=290.0, mass_flow=0.8)
        # Wrong duty: should be 0.8*4180*40=133760 but we give 200000
        inp = HeatBalanceInput(
            hot=hot,
            cold=cold,
            known_duty_w=200000.0,
            solver_params=_default_params(),
        )
        with pytest.raises(ValueError, match="Over-specified|inconsistent"):
            solve_heat_balance(inp, provider)


# ======================================================================
# Under/over-specified tests
# ======================================================================


class TestUnderOverSpecified:
    """Under-specified and over-specified must return structured errors."""

    def test_under_specified_raises(self) -> None:
        provider = MockPropertyProvider()
        hot = _water_stream(outlet_t=None)
        cold = _water_stream(outlet_t=None)
        inp = HeatBalanceInput(hot=hot, cold=cold)
        with pytest.raises(ValueError, match="Under-specified"):
            solve_heat_balance(inp, provider)

    def test_over_specified_raises(self) -> None:
        provider = MockPropertyProvider()
        hot = _water_stream(outlet_t=310.0)
        cold = _water_stream(outlet_t=330.0)
        inp = HeatBalanceInput(hot=hot, cold=cold, known_duty_w=167200.0)
        with pytest.raises(ValueError, match="Over-specified"):
            solve_heat_balance(inp, provider)


# ======================================================================
# Zero duty tests
# ======================================================================


class TestZeroDuty:
    """Zero duty must be handled without division by zero."""

    def test_zero_duty_outlets_equal_inlets(self) -> None:
        provider = MockPropertyProvider()
        hot = _water_stream(outlet_t=None, inlet_t=350.0)
        cold = _water_stream(outlet_t=None, inlet_t=290.0)
        inp = HeatBalanceInput(hot=hot, cold=cold, known_duty_w=0.0)
        result = solve_heat_balance(inp, provider)

        assert result.duty_w == 0.0
        assert result.hot_outlet_state["temperature_k"] == pytest.approx(350.0)
        assert result.cold_outlet_state["temperature_k"] == pytest.approx(290.0)
        assert result.residual_w == 0.0
        assert result.relative_imbalance == 0.0

    def test_zero_duty_no_division_by_zero(self) -> None:
        """Ensure no ZeroDivisionError for zero duty."""
        provider = MockPropertyProvider()
        hot = _water_stream(outlet_t=None)
        cold = _water_stream(outlet_t=None)
        inp = HeatBalanceInput(hot=hot, cold=cold, known_duty_w=0.0)
        result = solve_heat_balance(inp, provider)
        assert math.isfinite(result.relative_imbalance)


# ======================================================================
# Zero and negative flow tests
# ======================================================================


class TestFlowValidation:
    """Zero and negative flow must be rejected at StreamState construction."""

    def test_zero_hot_flow(self) -> None:
        with pytest.raises(ValueError, match="Mass flow must be > 0"):
            StreamState(
                fluid_identifier=FluidIdentifier(name="Water"),
                mass_flow_kg_s=0.0,
                inlet_temperature_k=350.0,
                inlet_pressure_pa=200000.0,
            )

    def test_negative_hot_flow(self) -> None:
        with pytest.raises(ValueError, match="Mass flow must be > 0"):
            StreamState(
                fluid_identifier=FluidIdentifier(name="Water"),
                mass_flow_kg_s=-1.0,
                inlet_temperature_k=350.0,
                inlet_pressure_pa=200000.0,
            )

    def test_zero_cold_flow(self) -> None:
        with pytest.raises(ValueError, match="Mass flow must be > 0"):
            StreamState(
                fluid_identifier=FluidIdentifier(name="Water"),
                mass_flow_kg_s=0.0,
                inlet_temperature_k=290.0,
                inlet_pressure_pa=150000.0,
            )

    def test_negative_cold_flow(self) -> None:
        with pytest.raises(ValueError, match="Mass flow must be > 0"):
            StreamState(
                fluid_identifier=FluidIdentifier(name="Water"),
                mass_flow_kg_s=-0.8,
                inlet_temperature_k=290.0,
                inlet_pressure_pa=150000.0,
            )


# ======================================================================
# Temperature direction tests
# ======================================================================


class TestTemperatureDirection:
    """Hot outlet above hot inlet or cold outlet below cold inlet."""

    def test_hot_outlet_above_inlet_rejected(self) -> None:
        """Hot outlet above hot inlet for positive duty → ValueError."""
        provider = MockPropertyProvider()
        hot = _water_stream(outlet_t=360.0, inlet_t=350.0)  # hot outlet > hot inlet
        cold = _water_stream(outlet_t=None, inlet_t=290.0)
        inp = HeatBalanceInput(hot=hot, cold=cold, solver_params=_default_params())
        with pytest.raises(ValueError, match="negative|below|exceeds"):
            solve_heat_balance(inp, provider)

    def test_cold_outlet_below_inlet_rejected(self) -> None:
        """Cold outlet below cold inlet for positive duty → ValueError."""
        provider = MockPropertyProvider()
        hot = _water_stream(outlet_t=None, inlet_t=350.0)
        cold = _water_stream(outlet_t=280.0, inlet_t=290.0)  # cold outlet < cold inlet
        inp = HeatBalanceInput(hot=hot, cold=cold, solver_params=_default_params())
        with pytest.raises(ValueError, match="negative|below|exceeds"):
            solve_heat_balance(inp, provider)


# ======================================================================
# Temperature cross tests
# ======================================================================


class TestTemperatureCross:
    """Temperature cross detection."""

    def test_temperature_cross_detected(self) -> None:
        provider = MockPropertyProvider()
        # Hot outlet (310 K) < Cold outlet (330 K) — cross
        hot = _water_stream(outlet_t=310.0, inlet_t=350.0)
        cold = _water_stream(outlet_t=330.0, inlet_t=290.0)
        inp = HeatBalanceInput(hot=hot, cold=cold, solver_params=_default_params())
        result = solve_heat_balance(inp, provider)
        cross_msgs = [m for m in result.warnings if "cross" in m.get("message", "")]
        assert len(cross_msgs) > 0


# ======================================================================
# Terminal approach tests
# ======================================================================


class TestTerminalApproach:
    """Non-positive minimum approach temperature detection."""

    def test_zero_approach(self) -> None:
        provider = MockPropertyProvider()
        # Hot outlet = Cold inlet → approach = 0
        hot = _water_stream(outlet_t=290.0, inlet_t=350.0)
        cold = _water_stream(outlet_t=350.0, inlet_t=290.0)
        inp = HeatBalanceInput(hot=hot, cold=cold, solver_params=_default_params())
        result = solve_heat_balance(inp, provider)
        approach_msgs = [m for m in result.warnings if "approach" in m.get("message", "").lower()]
        assert len(approach_msgs) > 0

    def test_negative_approach(self) -> None:
        provider = MockPropertyProvider()
        # Hot outlet (280 K) < Cold inlet (290 K) → negative approach
        hot = _water_stream(outlet_t=280.0, inlet_t=350.0)
        cold = _water_stream(outlet_t=360.0, inlet_t=290.0)
        inp = HeatBalanceInput(hot=hot, cold=cold, solver_params=_default_params())
        result = solve_heat_balance(inp, provider)
        approach_msgs = [m for m in result.warnings if "approach" in m.get("message", "").lower()]
        assert len(approach_msgs) > 0


# ======================================================================
# Property provider failure tests
# ======================================================================


class TestPropertyFailure:
    """Property-provider failures must produce structured blockers."""

    def test_hot_inlet_property_failure(self) -> None:
        provider = MockPropertyProvider(fail_fluid="Water")
        hot = _water_stream(outlet_t=None, inlet_t=350.0)
        cold = _water_stream(outlet_t=None, inlet_t=290.0)
        inp = HeatBalanceInput(hot=hot, cold=cold, known_duty_w=100000.0)
        with pytest.raises(ValueError, match="property|Mock failure"):
            solve_heat_balance(inp, provider)

    def test_cold_inlet_property_failure(self) -> None:
        provider = MockPropertyProvider(fail_fluid="Air")
        hot = StreamState(
            fluid_identifier=FluidIdentifier(name="Air"),
            mass_flow_kg_s=0.5,
            inlet_temperature_k=400.0,
            inlet_pressure_pa=101325.0,
        )
        cold = StreamState(
            fluid_identifier=FluidIdentifier(name="Air"),
            mass_flow_kg_s=0.3,
            inlet_temperature_k=290.0,
            inlet_pressure_pa=101325.0,
        )
        inp = HeatBalanceInput(hot=hot, cold=cold, known_duty_w=10000.0)
        with pytest.raises(ValueError, match="property|Mock failure"):
            solve_heat_balance(inp, provider)

    def test_hot_outlet_property_failure(self) -> None:
        provider = MockPropertyProvider(fail_fluid="Water")
        hot = _water_stream(outlet_t=310.0, inlet_t=350.0)
        cold = _water_stream(outlet_t=None, inlet_t=290.0)
        inp = HeatBalanceInput(hot=hot, cold=cold, solver_params=_default_params())
        with pytest.raises(ValueError):
            solve_heat_balance(inp, provider)


# ======================================================================
# Property out-of-range tests
# ======================================================================


class TestPropertyOutOfRange:
    """Property out-of-range states must produce structured errors."""

    def test_out_of_range_hot_inlet(self) -> None:
        provider = MockPropertyProvider(out_of_range_temps=(300.0, 400.0))
        hot = _water_stream(inlet_t=500.0, outlet_t=None)  # 500 K > 400 K max
        cold = _water_stream(outlet_t=None, inlet_t=290.0)
        inp = HeatBalanceInput(hot=hot, cold=cold, known_duty_w=100000.0)
        with pytest.raises(ValueError):
            solve_heat_balance(inp, provider)


# ======================================================================
# Phase-change rejection tests
# ======================================================================


class TestPhaseChangeRejection:
    """Phase-change states must be explicitly rejected."""

    def test_saturated_liquid_inlet_rejected(self) -> None:
        """A mock that returns saturated liquid phase → blocker."""
        provider = MockPropertyProvider()

        # Patch the provider to return a saturated liquid state
        original_state_tp = provider.state_tp

        def patched_state_tp(fluid, t, p):
            state = original_state_tp(fluid, t, p)
            # Override phase to saturated liquid
            return FluidState(
                temperature_k=state.temperature_k,
                pressure_pa=state.pressure_pa,
                density_kg_m3=state.density_kg_m3,
                cp_j_kg_k=state.cp_j_kg_k,
                viscosity_pa_s=state.viscosity_pa_s,
                conductivity_w_m_k=state.conductivity_w_m_k,
                enthalpy_j_kg=state.enthalpy_j_kg,
                entropy_j_kg_k=state.entropy_j_kg_k,
                phase=PhaseRegion.SATURATED_LIQUID,
                quality=0.0,
                provenance=state.provenance,
            )

        provider.state_tp = patched_state_tp  # type: ignore[assignment]

        hot = _water_stream(outlet_t=None, inlet_t=350.0)
        cold = _water_stream(outlet_t=None, inlet_t=290.0)
        inp = HeatBalanceInput(hot=hot, cold=cold, known_duty_w=100000.0)
        with pytest.raises(ValueError, match="phase|Phase|UNSUPPORTED"):
            solve_heat_balance(inp, provider)

    def test_unknown_phase_rejected(self) -> None:
        """Unknown phase region → blocker."""
        provider = MockPropertyProvider()
        original_state_tp = provider.state_tp

        def patched_state_tp(fluid, t, p):
            state = original_state_tp(fluid, t, p)
            return FluidState(
                temperature_k=state.temperature_k,
                pressure_pa=state.pressure_pa,
                density_kg_m3=state.density_kg_m3,
                cp_j_kg_k=state.cp_j_kg_k,
                viscosity_pa_s=state.viscosity_pa_s,
                conductivity_w_m_k=state.conductivity_w_m_k,
                enthalpy_j_kg=state.enthalpy_j_kg,
                entropy_j_kg_k=state.entropy_j_kg_k,
                phase=PhaseRegion.UNKNOWN,
                quality=None,
                provenance=state.provenance,
            )

        provider.state_tp = patched_state_tp  # type: ignore[assignment]

        hot = _water_stream(outlet_t=None, inlet_t=350.0)
        cold = _water_stream(outlet_t=None, inlet_t=290.0)
        inp = HeatBalanceInput(hot=hot, cold=cold, known_duty_w=100000.0)
        with pytest.raises(ValueError, match="phase|Phase|UNSUPPORTED"):
            solve_heat_balance(inp, provider)


# ======================================================================
# Solver convergence tests
# ======================================================================


class TestSolverConvergence:
    """Solver convergence diagnostics."""

    def test_converged_result(self) -> None:
        provider = MockPropertyProvider()
        hot = _water_stream(outlet_t=None, inlet_t=350.0, mass_flow=1.0)
        cold = _water_stream(outlet_t=None, inlet_t=290.0, mass_flow=0.8)
        Q = 1.0 * _WATER_CP * (350.0 - 310.0)
        inp = HeatBalanceInput(hot=hot, cold=cold, known_duty_w=Q, solver_params=_default_params())
        result = solve_heat_balance(inp, provider)

        assert result.solver_converged
        assert result.solver_iterations > 0
        assert result.relative_imbalance < 0.001

    def test_iterations_recorded(self) -> None:
        provider = MockPropertyProvider()
        hot = _water_stream(outlet_t=None, inlet_t=350.0, mass_flow=1.0)
        cold = _water_stream(outlet_t=None, inlet_t=290.0, mass_flow=0.8)
        inp = HeatBalanceInput(
            hot=hot, cold=cold, known_duty_w=80000.0, solver_params=_default_params()
        )
        result = solve_heat_balance(inp, provider)
        assert result.solver_iterations > 0


# ======================================================================
# Result immutability tests
# ======================================================================


class TestResultImmutability:
    """Result models must be immutable."""

    def test_frozen_model(self) -> None:
        provider = MockPropertyProvider()
        hot = _water_stream(outlet_t=310.0)
        cold = _water_stream(outlet_t=None, inlet_t=290.0)
        inp = HeatBalanceInput(hot=hot, cold=cold, solver_params=_default_params())
        result = solve_heat_balance(inp, provider)

        with pytest.raises((ValueError, AttributeError)):
            result.duty_w = 0.0  # type: ignore[misc]


# ======================================================================
# Hash tests
# ======================================================================


class TestResultHash:
    """Deterministic result hashing."""

    def test_hash_repeatability(self) -> None:
        """Same inputs → same hash."""
        provider = MockPropertyProvider()
        hot = _water_stream(outlet_t=310.0, inlet_t=350.0, mass_flow=1.0)
        cold = _water_stream(outlet_t=None, inlet_t=290.0, mass_flow=0.8)
        inp = HeatBalanceInput(hot=hot, cold=cold, solver_params=_default_params())

        result1 = solve_heat_balance(inp, provider)
        result2 = solve_heat_balance(inp, provider)

        assert result1.result_hash == result2.result_hash

    def test_hash_changes_with_input(self) -> None:
        """Different inputs → different hash."""
        provider = MockPropertyProvider()

        hot1 = _water_stream(outlet_t=310.0, inlet_t=350.0, mass_flow=1.0)
        cold1 = _water_stream(outlet_t=None, inlet_t=290.0, mass_flow=0.8)
        inp1 = HeatBalanceInput(hot=hot1, cold=cold1, solver_params=_default_params())
        result1 = solve_heat_balance(inp1, provider)

        hot2 = _water_stream(outlet_t=300.0, inlet_t=350.0, mass_flow=1.0)  # different outlet
        cold2 = _water_stream(outlet_t=None, inlet_t=290.0, mass_flow=0.8)
        inp2 = HeatBalanceInput(hot=hot2, cold=cold2, solver_params=_default_params())
        result2 = solve_heat_balance(inp2, provider)

        assert result1.result_hash != result2.result_hash

    def test_hash_format(self) -> None:
        provider = MockPropertyProvider()
        hot = _water_stream(outlet_t=310.0)
        cold = _water_stream(outlet_t=None, inlet_t=290.0)
        inp = HeatBalanceInput(hot=hot, cold=cold, solver_params=_default_params())
        result = solve_heat_balance(inp, provider)

        assert result.result_hash.startswith("sha256:")
        assert len(result.result_hash) == 71  # "sha256:" + 64 hex chars


# ======================================================================
# No NaN / Infinity tests
# ======================================================================


class TestNoNaNInf:
    """Public result models must not contain NaN or Infinity."""

    def test_no_nan_in_result(self) -> None:
        provider = MockPropertyProvider()
        hot = _water_stream(outlet_t=None, inlet_t=350.0, mass_flow=1.0)
        cold = _water_stream(outlet_t=None, inlet_t=290.0, mass_flow=0.8)
        inp = HeatBalanceInput(
            hot=hot,
            cold=cold,
            known_duty_w=167200.0,
            solver_params=_default_params(),
        )
        result = solve_heat_balance(inp, provider)

        assert math.isfinite(result.duty_w)
        assert math.isfinite(result.residual_w)
        assert math.isfinite(result.relative_imbalance)
        assert math.isfinite(result.hot_inlet_state["temperature_k"])
        assert math.isfinite(result.hot_outlet_state["temperature_k"])
        assert math.isfinite(result.cold_inlet_state["temperature_k"])
        assert math.isfinite(result.cold_outlet_state["temperature_k"])


# ======================================================================
# Provenance tests
# ======================================================================


class TestProvenance:
    """Provenance graph must be a valid DAG."""

    def test_provenance_graph_valid_dag(self) -> None:
        provider = MockPropertyProvider()
        hot = _water_stream(outlet_t=310.0)
        cold = _water_stream(outlet_t=None, inlet_t=290.0)
        inp = HeatBalanceInput(hot=hot, cold=cold, solver_params=_default_params())
        result = solve_heat_balance(inp, provider)

        # ProvenanceGraph validator ensures DAG on construction
        assert isinstance(result.provenance_graph, ProvenanceGraph)
        assert len(result.provenance_graph.nodes) > 0
        assert len(result.provenance_graph.edges) > 0

    def test_provenance_has_required_node_types(self) -> None:
        provider = MockPropertyProvider()
        hot = _water_stream(outlet_t=310.0)
        cold = _water_stream(outlet_t=None, inlet_t=290.0)
        inp = HeatBalanceInput(hot=hot, cold=cold, solver_params=_default_params())
        result = solve_heat_balance(inp, provider)

        node_types = {n.node_type.value for n in result.provenance_graph.nodes}
        assert "CASE_REVISION" in node_types
        assert "CALCULATION_RUN" in node_types
        assert "RESULT" in node_types
        assert "PROPERTY_CALL" in node_types

    def test_provenance_json_roundtrip(self) -> None:
        provider = MockPropertyProvider()
        hot = _water_stream(outlet_t=310.0)
        cold = _water_stream(outlet_t=None, inlet_t=290.0)
        inp = HeatBalanceInput(hot=hot, cold=cold, solver_params=_default_params())
        result = solve_heat_balance(inp, provider)

        json_str = result.provenance_graph.to_json()
        restored = ProvenanceGraph.from_json(json_str)
        assert len(restored.nodes) == len(result.provenance_graph.nodes)
        assert len(restored.edges) == len(result.provenance_graph.edges)

    def test_provenance_dag_validation(self) -> None:
        """ProvenanceGraph rejects cycles at construction."""
        from uuid import uuid4

        n1 = uuid4()
        n2 = uuid4()
        with pytest.raises(ValueError, match="cycle"):
            ProvenanceGraph(
                nodes=(
                    ProvenanceNode(
                        node_id=n1,
                        node_type="CASE_REVISION",
                        label="a",
                        payload_hash="sha256:" + "a" * 64,
                    ),
                    ProvenanceNode(
                        node_id=n2,
                        node_type="CALCULATION_RUN",
                        label="b",
                        payload_hash="sha256:" + "b" * 64,
                    ),
                ),
                edges=(
                    # n1 → n2 and n2 → n1 creates a cycle
                    ProvenanceEdge(source_id=n1, target_id=n2, relation="a"),
                    ProvenanceEdge(source_id=n2, target_id=n1, relation="b"),
                ),
            )


# ======================================================================
# Property call recording tests
# ======================================================================


class TestPropertyCallRecording:
    """Property calls must be recorded for provenance."""

    def test_calls_recorded(self) -> None:
        provider = MockPropertyProvider()
        hot = _water_stream(outlet_t=None, inlet_t=350.0, mass_flow=1.0)
        cold = _water_stream(outlet_t=None, inlet_t=290.0, mass_flow=0.8)
        Q = 1.0 * _WATER_CP * (350.0 - 310.0)
        inp = HeatBalanceInput(hot=hot, cold=cold, known_duty_w=Q, solver_params=_default_params())
        result = solve_heat_balance(inp, provider)

        assert len(result.property_calls) > 0
        # At least 2 inlet calls + solver calls
        assert len(result.property_calls) >= 2
        for call in result.property_calls:
            assert "fluid" in call
            assert "query_type" in call
            assert "backend_name" in call


# ======================================================================
# Warning and blocker tests
# ======================================================================


class TestWarningsAndBlockers:
    """Warnings and blockers must use existing EngineeringMessage model."""

    def test_warnings_are_dicts(self) -> None:
        provider = MockPropertyProvider()
        hot = _water_stream(outlet_t=310.0, inlet_t=350.0)
        cold = _water_stream(outlet_t=330.0, inlet_t=290.0)
        inp = HeatBalanceInput(hot=hot, cold=cold, solver_params=_default_params())
        result = solve_heat_balance(inp, provider)

        for w in result.warnings:
            assert "code" in w
            assert "severity" in w
            assert "message" in w


# ======================================================================
# Golden case documentation
# ======================================================================


class TestGoldenCaseDocumentation:
    """Golden case tolerance documentation."""

    def test_tolerance_documented(self) -> None:
        """Verify that tolerance is documented in the result."""
        provider = MockPropertyProvider()
        hot = _water_stream(outlet_t=None, inlet_t=350.0, mass_flow=1.0)
        cold = _water_stream(outlet_t=None, inlet_t=290.0, mass_flow=0.8)
        Q = 1.0 * _WATER_CP * (350.0 - 310.0)
        inp = HeatBalanceInput(
            hot=hot,
            cold=cold,
            known_duty_w=Q,
            solver_params=SolverParams(
                temperature_tolerance=1e-4,
                energy_tolerance=1e-3,
                max_iterations=100,
            ),
        )
        result = solve_heat_balance(inp, provider)

        # With constant Cp mock, the result should be exact
        assert result.hot_outlet_state["temperature_k"] == pytest.approx(310.0, abs=0.5)
        assert result.cold_outlet_state["temperature_k"] == pytest.approx(340.0, abs=0.5)
        assert result.relative_imbalance < 0.001
        assert result.solver_converged


# ======================================================================
# Negative duty rejection
# ======================================================================


class TestNegativeDuty:
    """Negative duty must be rejected at input validation."""

    def test_negative_duty_rejected(self) -> None:
        hot = _water_stream(outlet_t=None)
        cold = _water_stream(outlet_t=None)
        with pytest.raises(ValueError, match="Duty must be >= 0"):
            HeatBalanceInput(hot=hot, cold=cold, known_duty_w=-1000.0)
