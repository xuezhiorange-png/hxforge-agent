"""Unit tests for double-pipe thermal resistance, LMTD, and ε-NTU functions."""

from __future__ import annotations

import math

import pytest

from hexagent.exchangers.double_pipe.thermal import (
    FlowArrangement,
    build_thermal_resistance,
    compute_convective_resistance,
    compute_fouling_resistance,
    compute_wall_resistance,
    duty_from_effectiveness,
    effectiveness_counterflow,
    effectiveness_parallel,
    lmtd_counterflow,
    lmtd_parallel,
)

pytestmark = pytest.mark.pure

# ---------------------------------------------------------------------------
# Wall resistance
# ---------------------------------------------------------------------------


class TestWallResistance:
    """R_wall = ln(D_o / D_i) / (2π·k·L)"""

    def test_known_values(self):
        d_i, d_o, k, L = 0.05, 0.06, 50.0, 3.0
        expected = math.log(d_o / d_i) / (2.0 * math.pi * k * L)
        result = compute_wall_resistance(d_i, d_o, L, k)
        assert math.isclose(result, expected, rel_tol=1e-12)

    def test_unit_diameter_ratio(self):
        """When D_o/D_i ≈ 1, resistance → 0."""
        r = compute_wall_resistance(0.049999, 0.050001, 5.0, 50.0)
        assert r < 1e-7

    def test_negative_inner_diameter_raises(self):
        with pytest.raises(ValueError):
            compute_wall_resistance(-0.1, 0.2, 1.0, 50.0)

    def test_zero_length_raises(self):
        with pytest.raises(ValueError, match="length"):
            compute_wall_resistance(0.05, 0.06, 0.0, 50.0)

    def test_negative_conductivity_raises(self):
        with pytest.raises(ValueError, match="wall conductivity"):
            compute_wall_resistance(0.05, 0.06, 1.0, -10.0)


# ---------------------------------------------------------------------------
# Convective resistance
# ---------------------------------------------------------------------------


class TestConvectiveResistance:
    """R_conv = 1 / (h · A)"""

    def test_known_values(self):
        h, A = 1000.0, 0.5
        expected = 1.0 / (h * A)
        result = compute_convective_resistance(h, A)
        assert math.isclose(result, expected, rel_tol=1e-12)

    def test_zero_h_raises(self):
        with pytest.raises(ValueError, match="h must be > 0"):
            compute_convective_resistance(0.0, 1.0)

    def test_negative_area_raises(self):
        with pytest.raises(ValueError, match="area must be > 0"):
            compute_convective_resistance(500.0, -1.0)


# ---------------------------------------------------------------------------
# Fouling resistance
# ---------------------------------------------------------------------------


class TestFoulingResistance:
    """R_foul = Rf / A"""

    def test_known_values(self):
        Rf, A = 0.0002, 0.5
        expected = Rf / A
        result = compute_fouling_resistance(Rf, A)
        assert math.isclose(result, expected, rel_tol=1e-12)

    def test_zero_fouling_returns_zero(self):
        result = compute_fouling_resistance(0.0, 1.0)
        assert result == 0.0

    def test_negative_fouling_raises(self):
        with pytest.raises(ValueError, match="fouling must be >= 0"):
            compute_fouling_resistance(-0.001, 1.0)

    def test_zero_area_raises(self):
        with pytest.raises(ValueError, match="area must be > 0"):
            compute_fouling_resistance(0.001, 0.0)


# ---------------------------------------------------------------------------
# build_thermal_resistance
# ---------------------------------------------------------------------------


class TestBuildThermalResistance:
    """Build the complete thermal resistance network."""

    def test_total_equals_sum_of_components(self):
        r = build_thermal_resistance(
            h_inner=1000.0,
            h_outer=500.0,
            area_inner_m2=0.5,
            area_outer_m2=0.6,
            wall_resistance_kw=0.001,
            fouling_inner_m2k_w=0.0002,
            fouling_outer_m2k_w=0.0003,
        )
        total = r.r_conv_inner + r.r_foul_inner + r.r_wall + r.r_foul_outer + r.r_conv_outer
        assert math.isclose(r.total_resistance_kw, total, rel_tol=1e-12)

    def test_one_over_ua_equals_total_resistance(self):
        r = build_thermal_resistance(
            h_inner=1000.0,
            h_outer=500.0,
            area_inner_m2=0.5,
            area_outer_m2=0.6,
            wall_resistance_kw=0.001,
        )
        assert math.isclose(1.0 / r.ua_w_k, r.total_resistance_kw, rel_tol=1e-12)

    def test_no_fouling(self):
        r = build_thermal_resistance(
            h_inner=1000.0,
            h_outer=500.0,
            area_inner_m2=0.5,
            area_outer_m2=0.6,
            wall_resistance_kw=0.001,
        )
        assert r.r_foul_inner == 0.0
        assert r.r_foul_outer == 0.0

    def test_individual_resistances(self):
        r = build_thermal_resistance(
            h_inner=2000.0,
            h_outer=1000.0,
            area_inner_m2=1.0,
            area_outer_m2=2.0,
            wall_resistance_kw=0.0005,
        )
        assert math.isclose(r.r_conv_inner, 1.0 / (2000.0 * 1.0), rel_tol=1e-12)
        assert math.isclose(r.r_conv_outer, 1.0 / (1000.0 * 2.0), rel_tol=1e-12)
        assert math.isclose(r.r_wall, 0.0005, rel_tol=1e-12)

    def test_to_dict_keys(self):
        r = build_thermal_resistance(
            h_inner=1000.0,
            h_outer=500.0,
            area_inner_m2=0.5,
            area_outer_m2=0.6,
            wall_resistance_kw=0.001,
        )
        d = r.to_dict()
        expected_keys = {
            "r_conv_inner",
            "r_foul_inner",
            "r_wall",
            "r_foul_outer",
            "r_conv_outer",
            "total_resistance",
            "ua_w_k",
        }
        assert set(d.keys()) == expected_keys

    def test_frozen_dataclass(self):
        r = build_thermal_resistance(
            h_inner=1000.0,
            h_outer=500.0,
            area_inner_m2=0.5,
            area_outer_m2=0.6,
            wall_resistance_kw=0.001,
        )
        with pytest.raises(AttributeError):
            r.r_wall = 0.002  # type: ignore[misc]


# ---------------------------------------------------------------------------
# LMTD — counterflow
# ---------------------------------------------------------------------------


class TestLMTDCounterflow:
    """ΔT₁ = T_h,in − T_c,out ;  ΔT₂ = T_h,out − T_c,in"""

    def test_known_values(self):
        th_in, th_out = 400.0, 350.0
        tc_in, tc_out = 300.0, 320.0
        dt1 = th_in - tc_out  # 80
        dt2 = th_out - tc_in  # 50
        expected = (dt1 - dt2) / math.log(dt1 / dt2)
        result = lmtd_counterflow(th_in, th_out, tc_in, tc_out)
        assert math.isclose(result, expected, rel_tol=1e-12)

    def test_equal_terminal_dts(self):
        """When ΔT₁ ≈ ΔT₂, LMTD = arithmetic mean."""
        lmtd_counterflow(400.0, 300.0, 250.0, 150.0)
        # ΔT₁ = 400−150 = 250, ΔT₂ = 300−250 = 50  → NOT equal
        # Use equal: th_in=350, th_out=300, tc_in=200, tc_out=250
        # ΔT₁=350-250=100, ΔT₂=300-200=100
        lmtd_eq = lmtd_counterflow(350.0, 300.0, 200.0, 250.0)
        assert math.isclose(lmtd_eq, 100.0, rel_tol=1e-6)

    def test_nan_on_temperature_crossing(self):
        """When a terminal ΔT ≤ 0 → NaN."""
        # Counterflow: ΔT₁ = th_in − tc_out; make it negative
        result = lmtd_counterflow(th_in=300.0, th_out=350.0, tc_in=200.0, tc_out=400.0)
        assert math.isnan(result)


# ---------------------------------------------------------------------------
# LMTD — parallel
# ---------------------------------------------------------------------------


class TestLMTDParallel:
    """ΔT₁ = T_h,in − T_c,in ;  ΔT₂ = T_h,out − T_c,out"""

    def test_known_values(self):
        th_in, th_out = 400.0, 350.0
        tc_in, tc_out = 300.0, 320.0
        dt1 = th_in - tc_in  # 100
        dt2 = th_out - tc_out  # 30
        expected = (dt1 - dt2) / math.log(dt1 / dt2)
        result = lmtd_parallel(th_in, th_out, tc_in, tc_out)
        assert math.isclose(result, expected, rel_tol=1e-12)

    def test_equal_terminal_dts(self):
        # ΔT₁=ΔT₂=100: th_in=300, tc_in=200, th_out=250, tc_out=150
        lmtd_eq = lmtd_parallel(300.0, 250.0, 200.0, 150.0)
        assert math.isclose(lmtd_eq, 100.0, rel_tol=1e-6)

    def test_nan_on_temperature_crossing(self):
        # th_out < tc_out → ΔT₂ ≤ 0
        result = lmtd_parallel(400.0, 310.0, 300.0, 320.0)
        assert math.isnan(result)


# ---------------------------------------------------------------------------
# ε-NTU — counterflow
# ---------------------------------------------------------------------------


class TestEffectivenessCounterflow:
    def test_cr_zero(self):
        """C_r = 0 → ε = 1 − exp(−NTU)"""
        ntu = 2.0
        expected = 1.0 - math.exp(-ntu)
        result = effectiveness_counterflow(ntu, 0.0)
        assert math.isclose(result, expected, rel_tol=1e-12)

    def test_cr_one(self):
        """C_r = 1 → ε = NTU / (1 + NTU)"""
        ntu = 3.0
        expected = ntu / (1.0 + ntu)
        result = effectiveness_counterflow(ntu, 1.0)
        assert math.isclose(result, expected, rel_tol=1e-12)

    def test_ntu_zero(self):
        """NTU = 0 → ε = 0."""
        result = effectiveness_counterflow(0.0, 0.5)
        assert math.isclose(result, 0.0, abs_tol=1e-15)

    def test_ntu_large(self):
        """Very large NTU → ε → 1/(1+C_r) for Cr>0? No — check it approaches theoretical."""
        ntu = 100.0
        result = effectiveness_counterflow(ntu, 0.5)
        # For counterflow with Cr=0.5, ε → 1 as NTU → ∞
        assert result > 0.99

    def test_negative_cr_raises(self):
        with pytest.raises(ValueError, match="capacity_ratio"):
            effectiveness_counterflow(1.0, -0.1)

    def test_cr_above_one_raises(self):
        with pytest.raises(ValueError, match="capacity_ratio"):
            effectiveness_counterflow(1.0, 1.5)

    def test_negative_ntu_raises(self):
        with pytest.raises(ValueError, match="NTU must be >= 0"):
            effectiveness_counterflow(-1.0, 0.5)

    def test_general_formula(self):
        """Verify the full formula for a non-degenerate case."""
        ntu, cr = 2.0, 0.3
        exp_val = math.exp(-ntu * (1.0 - cr))
        expected = (1.0 - exp_val) / (1.0 - cr * exp_val)
        result = effectiveness_counterflow(ntu, cr)
        assert math.isclose(result, expected, rel_tol=1e-12)


# ---------------------------------------------------------------------------
# ε-NTU — parallel
# ---------------------------------------------------------------------------


class TestEffectivenessParallel:
    def test_known_value(self):
        """ε = (1 − exp(−NTU·(1+C_r))) / (1+C_r)"""
        ntu, cr = 2.0, 0.5
        exp_val = math.exp(-ntu * (1.0 + cr))
        expected = (1.0 - exp_val) / (1.0 + cr)
        result = effectiveness_parallel(ntu, cr)
        assert math.isclose(result, expected, rel_tol=1e-12)

    def test_cr_zero(self):
        """C_r = 0 → ε = 1 − exp(−NTU)"""
        ntu = 2.0
        expected = 1.0 - math.exp(-ntu)
        result = effectiveness_parallel(ntu, 0.0)
        assert math.isclose(result, expected, rel_tol=1e-12)

    def test_ntu_zero(self):
        result = effectiveness_parallel(0.0, 0.5)
        assert math.isclose(result, 0.0, abs_tol=1e-15)

    def test_negative_cr_raises(self):
        with pytest.raises(ValueError, match="capacity_ratio"):
            effectiveness_parallel(1.0, -0.1)

    def test_cr_above_one_raises(self):
        with pytest.raises(ValueError, match="capacity_ratio"):
            effectiveness_parallel(1.0, 1.5)

    def test_negative_ntu_raises(self):
        with pytest.raises(ValueError, match="NTU must be >= 0"):
            effectiveness_parallel(-1.0, 0.5)


# ---------------------------------------------------------------------------
# Parallel ≤ Counterflow for same inputs
# ---------------------------------------------------------------------------


class TestParallelVsCounterflow:
    """Counter-flow is always at least as effective as parallel-flow."""

    @pytest.mark.parametrize(
        "ntu,cr",
        [
            (0.5, 0.0),
            (1.0, 0.0),
            (1.0, 0.3),
            (2.0, 0.5),
            (3.0, 0.8),
            (10.0, 0.99),
            (0.01, 0.0),
        ],
    )
    def test_counterflow_ge_parallel(self, ntu: float, cr: float):
        eps_cf = effectiveness_counterflow(ntu, cr)
        eps_pf = effectiveness_parallel(ntu, cr)
        assert eps_cf >= eps_pf - 1e-15, (
            f"counterflow ({eps_cf}) < parallel ({eps_pf}) at NTU={ntu}, Cr={cr}"
        )


# ---------------------------------------------------------------------------
# duty_from_effectiveness
# ---------------------------------------------------------------------------


class TestDutyFromEffectiveness:
    """Q = ε · C_min · (T_h,in − T_c,in)"""

    def test_known_values(self):
        eps, c_min = 0.75, 200.0
        th_in, tc_in = 400.0, 300.0
        expected = eps * c_min * (th_in - tc_in)
        result = duty_from_effectiveness(eps, c_min, th_in, tc_in)
        assert math.isclose(result, expected, rel_tol=1e-12)

    def test_zero_effectiveness(self):
        assert duty_from_effectiveness(0.0, 500.0, 400.0, 300.0) == 0.0

    def test_zero_c_min(self):
        assert duty_from_effectiveness(0.8, 0.0, 400.0, 300.0) == 0.0

    def test_equal_inlet_temps(self):
        assert duty_from_effectiveness(0.9, 100.0, 350.0, 350.0) == 0.0


# ---------------------------------------------------------------------------
# FlowArrangement enum
# ---------------------------------------------------------------------------


class TestFlowArrangement:
    def test_members(self):
        assert FlowArrangement.COUNTERFLOW == "counterflow"
        assert FlowArrangement.PARALLEL == "parallel"

    def test_is_str_enum(self):
        assert isinstance(FlowArrangement.COUNTERFLOW, str)
