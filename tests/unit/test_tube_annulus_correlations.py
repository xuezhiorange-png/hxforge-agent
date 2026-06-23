"""Comprehensive unit tests for TASK-007 — tube and annulus correlation implementation.

Covers ALL categories from the task card:
  1. Geometry models (CircularTubeGeometry, ConcentricAnnulusGeometry)
  2. Flow regime classification and dimensionless number computation
  3. Tube correlations (laminar CWT, laminar CHF, turbulent Gnielinski)
  4. Annulus correlations (laminar inner CHF, turbulent Gnielinski-DH)
  5. Correlation selection logic
  6. End-to-end service evaluation (evaluate_hx_correlation)
  7. Hash integrity, provenance, JSON round-trip, tamper detection

Hand-calculated reference values use water-like properties:
  ρ = 1000 kg/m³, μ = 0.001 Pa·s, k = 0.6 W/(m·K), cp = 4180 J/(kg·K)
  Pr = cp·μ/k = 4180×0.001/0.6 = 6.9667

Circular tube (D = 0.025 m, L = 2.0 m):
  A = π/4 × D² = 4.9087×10⁻⁴ m²
  P_w = π × D = 0.07854 m
  D_h = D = 0.025 m

Concentric annulus (Di = 0.025 m, Do = 0.050 m, L = 2.0 m):
  κ = Di/Do = 0.5
  A = π/4 × (Do² - Di²) = 1.4726×10⁻³ m²
  D_h = Do - Di = 0.025 m
"""

from __future__ import annotations

import math
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from hexagent.core.heat_balance import ExecutionContextSnapshot
from hexagent.correlations.annulus import (
    ANNULUS_CORRELATIONS,
    AnnulusLaminarInnerCHF,
    AnnulusTurbulentGnielinskiDH,
    _interpolate_nu_laminar_inner,
)
from hexagent.correlations.flow import (
    LAMINAR_UPPER_RE,
    TURBULENT_LOWER_RE,
    FlowPropertiesInput,
    FlowRegime,
    classify_regime,
    compute_heat_transfer_coefficient,
    compute_prandtl,
    compute_reynolds,
    compute_velocity,
)
from hexagent.correlations.geometry import (
    CircularTubeGeometry,
    ConcentricAnnulusGeometry,
    ThermalBoundaryCondition,
)
from hexagent.correlations.hx_result import (
    CorrelationResult,
    CorrelationStatus,
    SelectedCorrelationInfo,
    _build_provenance_graph,
    _deterministic_uuid5,
    _provenance_graph_digest,
)
from hexagent.correlations.selection import (
    CorrelationCandidate,
    _build_candidates,
    _sort_key,
    select_correlation,
)
from hexagent.correlations.service import (
    CalculationContext,
    evaluate_hx_correlation,
)
from hexagent.correlations.tube import (
    TUBE_CORRELATIONS,
    TubeLaminarCHF,
    TubeLaminarCWT,
    TubeTurbulentGnielinski,
)
from hexagent.domain.provenance import (
    ProvenanceNodeType,
)

# ---------------------------------------------------------------------------
# Shared test constants and helpers
# ---------------------------------------------------------------------------

# Water-like properties
RHO = 1000.0  # kg/m³
MU = 0.001  # Pa·s
K = 0.6  # W/(m·K)
CP = 4180.0  # J/(kg·K)
PR = CP * MU / K  # ≈ 6.9667

# Circular tube geometry (25 mm ID, 2 m)
TUBE_D = 0.025  # m
TUBE_L = 2.0  # m
TUBE_A = math.pi / 4.0 * TUBE_D**2  # ≈ 4.9087e-4 m²
TUBE_P = math.pi * TUBE_D  # ≈ 0.07854 m
TUBE_DH = TUBE_D  # = 0.025 m

# Annulus geometry (25 mm inner OD, 50 mm outer ID, 2 m)
ANN_DI = 0.025  # m
ANN_DO = 0.050  # m
ANN_L = 2.0  # m
ANN_KAPPA = ANN_DI / ANN_DO  # = 0.5
ANN_A = math.pi / 4.0 * (ANN_DO**2 - ANN_DI**2)  # ≈ 1.4726e-3 m²
ANN_PI = math.pi * ANN_DI  # inner perimeter
ANN_PO = math.pi * ANN_DO  # outer perimeter
ANN_DH = ANN_DO - ANN_DI  # = 0.025 m


def _tube_geom() -> CircularTubeGeometry:
    return CircularTubeGeometry(
        inside_diameter_m=TUBE_D,
        heat_transfer_length_m=TUBE_L,
    )


def _ann_geom(
    *, di: float = ANN_DI, do: float = ANN_DO, heated: str = "inner"
) -> ConcentricAnnulusGeometry:
    return ConcentricAnnulusGeometry(
        inner_tube_outer_diameter_m=di,
        outer_pipe_inside_diameter_m=do,
        heat_transfer_length_m=ANN_L,
        heated_surface=heated,
    )


def _water_flow(
    *,
    mass_flow: float = 0.1,
    heating: bool = True,
    wall_temp: float | None = None,
    wall_visc: float | None = None,
) -> FlowPropertiesInput:
    return FlowPropertiesInput(
        mass_flow_kg_s=mass_flow,
        density_kg_m3=RHO,
        dynamic_viscosity_pa_s=MU,
        thermal_conductivity_w_m_k=K,
        specific_heat_j_kg_k=CP,
        bulk_temperature_k=350.0,
        wall_temperature_k=wall_temp,
        wall_viscosity_pa_s=wall_visc,
        heating=heating,
    )


# =====================================================================
# Category 1: Geometry Models
# =====================================================================


class TestCircularTubeGeometry:
    """CircularTubeGeometry construction, validation, and properties."""

    def test_construction_succeeds(self) -> None:
        g = _tube_geom()
        assert g.inside_diameter_m == TUBE_D
        assert g.heat_transfer_length_m == TUBE_L
        assert g.geometry_type == "circular_tube"

    def test_flow_area(self) -> None:
        g = _tube_geom()
        assert g.flow_area_m2 == pytest.approx(math.pi / 4.0 * TUBE_D**2, rel=1e-12)

    def test_wetted_perimeter(self) -> None:
        g = _tube_geom()
        assert g.wetted_perimeter_m == pytest.approx(math.pi * TUBE_D, rel=1e-12)

    def test_hydraulic_diameter_equals_diameter(self) -> None:
        g = _tube_geom()
        assert g.hydraulic_diameter_m == pytest.approx(TUBE_D, rel=1e-12)

    def test_heated_perimeter_equals_wetted(self) -> None:
        g = _tube_geom()
        assert g.heated_perimeter_m == pytest.approx(g.wetted_perimeter_m, rel=1e-12)

    def test_frozen(self) -> None:
        g = _tube_geom()
        with pytest.raises(ValidationError):
            g.inside_diameter_m = 0.05  # type: ignore[misc]

    def test_forbids_extra(self) -> None:
        with pytest.raises(ValidationError):
            CircularTubeGeometry(
                inside_diameter_m=TUBE_D,
                heat_transfer_length_m=TUBE_L,
                unknown_field=42,  # type: ignore[call-arg]
            )

    def test_zero_diameter_rejected(self) -> None:
        with pytest.raises(ValidationError, match="finite positive"):
            CircularTubeGeometry(inside_diameter_m=0.0, heat_transfer_length_m=TUBE_L)

    def test_negative_diameter_rejected(self) -> None:
        with pytest.raises(ValidationError, match="finite positive"):
            CircularTubeGeometry(inside_diameter_m=-0.01, heat_transfer_length_m=TUBE_L)

    def test_nan_diameter_rejected(self) -> None:
        with pytest.raises(ValidationError, match="finite positive"):
            CircularTubeGeometry(inside_diameter_m=float("nan"), heat_transfer_length_m=TUBE_L)

    def test_inf_diameter_rejected(self) -> None:
        with pytest.raises(ValidationError, match="finite positive"):
            CircularTubeGeometry(inside_diameter_m=float("inf"), heat_transfer_length_m=TUBE_L)


class TestConcentricAnnulusGeometry:
    """ConcentricAnnulusGeometry construction, validation, and properties."""

    def test_construction_succeeds(self) -> None:
        g = _ann_geom()
        assert g.inner_tube_outer_diameter_m == ANN_DI
        assert g.outer_pipe_inside_diameter_m == ANN_DO
        assert g.heated_surface == "inner"
        assert g.geometry_type == "concentric_annulus"

    def test_flow_area(self) -> None:
        g = _ann_geom()
        expected = math.pi / 4.0 * (ANN_DO**2 - ANN_DI**2)
        assert g.flow_area_m2 == pytest.approx(expected, rel=1e-12)

    def test_hydraulic_diameter(self) -> None:
        """For concentric annulus: D_h = 4A / (P_i + P_o) = D_o - D_i."""
        g = _ann_geom()
        assert g.hydraulic_diameter_m == pytest.approx(ANN_DO - ANN_DI, rel=1e-12)

    def test_diameter_ratio(self) -> None:
        g = _ann_geom()
        assert g.diameter_ratio == pytest.approx(ANN_KAPPA, rel=1e-12)

    def test_inner_wetted_perimeter(self) -> None:
        g = _ann_geom()
        assert g.inner_wetted_perimeter_m == pytest.approx(math.pi * ANN_DI, rel=1e-12)

    def test_outer_wetted_perimeter(self) -> None:
        g = _ann_geom()
        assert g.outer_wetted_perimeter_m == pytest.approx(math.pi * ANN_DO, rel=1e-12)

    def test_total_wetted_perimeter(self) -> None:
        g = _ann_geom()
        assert g.total_wetted_perimeter_m == pytest.approx(math.pi * (ANN_DI + ANN_DO), rel=1e-12)

    def test_inner_heated_perimeter_inner_heated(self) -> None:
        g = _ann_geom(heated="inner")
        assert g.inner_heated_perimeter_m == pytest.approx(math.pi * ANN_DI, rel=1e-12)
        assert g.outer_heated_perimeter_m == 0.0

    def test_outer_heated_perimeter_outer_heated(self) -> None:
        g = _ann_geom(heated="outer")
        assert g.inner_heated_perimeter_m == 0.0
        assert g.outer_heated_perimeter_m == pytest.approx(math.pi * ANN_DO, rel=1e-12)

    def test_both_heated_perimeters(self) -> None:
        g = _ann_geom(heated="both")
        assert g.inner_heated_perimeter_m == pytest.approx(math.pi * ANN_DI, rel=1e-12)
        assert g.outer_heated_perimeter_m == pytest.approx(math.pi * ANN_DO, rel=1e-12)

    def test_outer_leq_inner_rejected(self) -> None:
        with pytest.raises(ValidationError, match="must be greater"):
            ConcentricAnnulusGeometry(
                inner_tube_outer_diameter_m=0.050,
                outer_pipe_inside_diameter_m=0.025,
                heat_transfer_length_m=ANN_L,
            )

    def test_equal_diameters_rejected(self) -> None:
        with pytest.raises(ValidationError, match="must be greater"):
            ConcentricAnnulusGeometry(
                inner_tube_outer_diameter_m=0.025,
                outer_pipe_inside_diameter_m=0.025,
                heat_transfer_length_m=ANN_L,
            )

    def test_frozen(self) -> None:
        g = _ann_geom()
        with pytest.raises(ValidationError):
            g.inner_tube_outer_diameter_m = 0.1  # type: ignore[misc]


class TestThermalBoundaryCondition:
    """ThermalBoundaryCondition constants exist and are strings."""

    def test_constants(self) -> None:
        assert ThermalBoundaryCondition.CONSTANT_WALL_TEMPERATURE == "constant_wall_temperature"
        assert ThermalBoundaryCondition.CONSTANT_HEAT_FLUX == "constant_heat_flux"
        assert ThermalBoundaryCondition.INNER_WALL_HEATED == "inner_wall_heated"
        assert ThermalBoundaryCondition.OUTER_WALL_HEATED == "outer_wall_heated"
        assert ThermalBoundaryCondition.BOTH_WALLS_HEATED == "both_walls_heated"


# =====================================================================
# Category 2: Flow Regime Classification & Dimensionless Numbers
# =====================================================================


class TestClassifyRegime:
    """Regime classification boundaries and edge cases."""

    def test_laminar(self) -> None:
        assert classify_regime(1000) == FlowRegime.laminar

    def test_laminar_upper_bound_exclusive(self) -> None:
        """Re < 2300 is laminar; Re = 2300 is transitional."""
        assert classify_regime(LAMINAR_UPPER_RE - 1) == FlowRegime.laminar

    def test_exactly_laminar_upper_is_transitional(self) -> None:
        assert classify_regime(LAMINAR_UPPER_RE) == FlowRegime.transitional

    def test_transitional(self) -> None:
        assert classify_regime(5000) == FlowRegime.transitional

    def test_turbulent(self) -> None:
        assert classify_regime(TURBULENT_LOWER_RE + 1) == FlowRegime.turbulent

    def test_exactly_turbulent_lower_is_transitional(self) -> None:
        assert classify_regime(TURBULENT_LOWER_RE) == FlowRegime.transitional

    def test_zero_is_laminar(self) -> None:
        assert classify_regime(0.0) == FlowRegime.laminar

    def test_negative_is_invalid(self) -> None:
        assert classify_regime(-1.0) == FlowRegime.invalid

    def test_nan_is_invalid(self) -> None:
        assert classify_regime(float("nan")) == FlowRegime.invalid

    def test_inf_is_invalid(self) -> None:
        assert classify_regime(float("inf")) == FlowRegime.invalid

    def test_negative_inf_is_invalid(self) -> None:
        assert classify_regime(float("-inf")) == FlowRegime.invalid


class TestComputeVelocity:
    """Mean velocity computation: v = m_dot / (ρ × A)."""

    def test_basic(self) -> None:
        # v = 0.1 / (1000 * 4.9087e-4) ≈ 0.2037 m/s
        v = compute_velocity(0.1, RHO, TUBE_A)
        expected = 0.1 / (RHO * TUBE_A)
        assert v == pytest.approx(expected, rel=1e-12)

    def test_zero_area_rejected(self) -> None:
        with pytest.raises(ValueError, match="finite positive"):
            compute_velocity(0.1, RHO, 0.0)

    def test_negative_area_rejected(self) -> None:
        with pytest.raises(ValueError, match="finite positive"):
            compute_velocity(0.1, RHO, -0.001)

    def test_zero_density_rejected(self) -> None:
        with pytest.raises(ValueError, match="finite positive"):
            compute_velocity(0.1, 0.0, TUBE_A)


class TestComputeReynolds:
    """Reynolds number: Re = ρ v D_h / μ."""

    def test_basic(self) -> None:
        v = compute_velocity(0.1, RHO, TUBE_A)
        re = compute_reynolds(RHO, v, TUBE_DH, MU)
        expected = RHO * v * TUBE_DH / MU
        assert re == pytest.approx(expected, rel=1e-12)

    def test_low_mass_flow_gives_laminar(self) -> None:
        """With 0.005 kg/s in a 25 mm tube, Re ≈ 255 (laminar)."""
        v = compute_velocity(0.005, RHO, TUBE_A)
        re = compute_reynolds(RHO, v, TUBE_DH, MU)
        assert re < LAMINAR_UPPER_RE

    def test_rejects_negative_re_in_input(self) -> None:
        with pytest.raises(ValueError, match="finite positive"):
            compute_reynolds(RHO, 0.2, TUBE_DH, -0.001)


class TestComputePrandtl:
    """Prandtl number: Pr = cp × μ / k."""

    def test_water_at_350k(self) -> None:
        pr = compute_prandtl(CP, MU, K)
        expected = CP * MU / K
        assert pr == pytest.approx(expected, rel=1e-12)

    def test_air_like(self) -> None:
        pr = compute_prandtl(1005.0, 1.8e-5, 0.026)
        expected = 1005.0 * 1.8e-5 / 0.026
        assert pr == pytest.approx(expected, rel=1e-12)

    def test_rejects_zero_cp(self) -> None:
        with pytest.raises(ValueError, match="finite positive"):
            compute_prandtl(0.0, MU, K)


class TestComputeHeatTransferCoefficient:
    """h = Nu × k / D_h."""

    def test_basic(self) -> None:
        h = compute_heat_transfer_coefficient(3.66, K, TUBE_DH)
        expected = 3.66 * K / TUBE_DH
        assert h == pytest.approx(expected, rel=1e-12)

    def test_rejects_zero_nu(self) -> None:
        with pytest.raises(ValueError, match="finite positive"):
            compute_heat_transfer_coefficient(0.0, K, TUBE_DH)


# =====================================================================
# Category 3: Tube Correlations
# =====================================================================


class TestTubeLaminarCWT:
    """C1: Tube laminar, constant wall temperature — Nu = 3.66."""

    def test_nu_value(self) -> None:
        c = TubeLaminarCWT()
        assert c.evaluate() == 3.66

    def test_metadata(self) -> None:
        c = TubeLaminarCWT()
        assert c.correlation_id == "tube_laminar_cwt"
        assert c.version == "1.0.0"
        assert c.supported_geometry == "circular_tube"
        assert c.flow_regime == "laminar"
        assert c.boundary_condition == "constant_wall_temperature"
        assert c.reynolds_max == 2300.0
        assert c.prandtl_min == 0.6
        assert c.requires_wall_viscosity is False

    def test_frozen(self) -> None:
        c = TubeLaminarCWT()
        with pytest.raises(AttributeError):
            c.correlation_id = "modified"  # type: ignore[misc]


class TestTubeLaminarCHF:
    """C2: Tube laminar, constant heat flux — Nu = 4.36."""

    def test_nu_value(self) -> None:
        c = TubeLaminarCHF()
        assert c.evaluate() == 4.36

    def test_metadata(self) -> None:
        c = TubeLaminarCHF()
        assert c.correlation_id == "tube_laminar_chf"
        assert c.boundary_condition == "constant_heat_flux"
        assert c.reynolds_max == 2300.0

    def test_frozen(self) -> None:
        c = TubeLaminarCHF()
        with pytest.raises(AttributeError):
            c.version = "2.0.0"  # type: ignore[misc]


class TestTubeTurbulentGnielinski:
    """C3: Tube turbulent Gnielinski correlation."""

    def _instance(self) -> TubeTurbulentGnielinski:
        return TubeTurbulentGnielinski()

    def test_petukhov_friction_factor(self) -> None:
        """f = (0.790·ln(Re) - 1.64)^{-2}."""
        c = self._instance()
        f = c.petukhov_friction_factor(10000.0)
        expected = (0.790 * math.log(10000.0) - 1.64) ** (-2)
        assert f == pytest.approx(expected, rel=1e-12)

    def test_nu_at_pr1(self) -> None:
        """For Pr = 1.0: denominator simplifies since Pr^(2/3) = 1."""
        c = self._instance()
        nu = c.evaluate(10000.0, 1.0)
        f = c.petukhov_friction_factor(10000.0)
        f8 = f / 8.0
        numerator = f8 * (10000.0 - 1000.0) * 1.0
        # Pr^(2/3) - 1 = 0 for Pr = 1
        denominator = 1.0 + 12.7 * math.sqrt(f8) * 0.0
        assert nu == pytest.approx(numerator / denominator, rel=1e-12)

    def test_nu_manual_calculation(self) -> None:
        """Hand-computed Gnielinski for Re=10000, Pr=0.71."""
        c = self._instance()
        Re, Pr = 10000.0, 0.71
        f = (0.790 * math.log(Re) - 1.64) ** (-2)
        f8 = f / 8.0
        num = f8 * (Re - 1000.0) * Pr
        den = 1.0 + 12.7 * math.sqrt(f8) * (Pr ** (2.0 / 3.0) - 1.0)
        expected_nu = num / den
        assert c.evaluate(Re, Pr) == pytest.approx(expected_nu, rel=1e-12)

    def test_boundary_values(self) -> None:
        c = self._instance()
        # Just inside valid range
        c.evaluate(c.reynolds_min, c.prandtl_min)
        c.evaluate(c.reynolds_max, c.prandtl_max)

    def test_re_below_min_raises(self) -> None:
        c = self._instance()
        with pytest.raises(ValueError, match="outside valid range"):
            c.evaluate(2999.0, 1.0)

    def test_re_above_max_raises(self) -> None:
        c = self._instance()
        with pytest.raises(ValueError, match="outside valid range"):
            c.evaluate(5e6 + 1, 1.0)

    def test_pr_below_min_raises(self) -> None:
        c = self._instance()
        with pytest.raises(ValueError, match="outside valid range"):
            c.evaluate(10000.0, 0.49)

    def test_pr_above_max_raises(self) -> None:
        c = self._instance()
        with pytest.raises(ValueError, match="outside valid range"):
            c.evaluate(10000.0, 2001.0)

    def test_negative_re_raises(self) -> None:
        c = self._instance()
        with pytest.raises(ValueError):
            c.evaluate(-100.0, 1.0)

    def test_metadata(self) -> None:
        c = self._instance()
        assert c.correlation_id == "tube_turbulent_gnielinski"
        assert c.supported_geometry == "circular_tube"
        assert c.flow_regime == "turbulent"
        assert c.requires_wall_viscosity is False

    def test_registry_completeness(self) -> None:
        assert set(TUBE_CORRELATIONS.keys()) == {
            "tube_laminar_cwt",
            "tube_laminar_chf",
            "tube_turbulent_gnielinski",
        }


# =====================================================================
# Category 4: Annulus Correlations
# =====================================================================


class TestInterpolateNuLaminarInner:
    """Kays Table 8-2 interpolation for annulus laminar Nu_i."""

    def test_known_table_point_kappa_0_25(self) -> None:
        nu = _interpolate_nu_laminar_inner(0.25)
        assert nu == 5.70

    def test_known_table_point_kappa_0_5(self) -> None:
        nu = _interpolate_nu_laminar_inner(0.5)
        assert nu == 7.30

    def test_known_table_point_kappa_0_75(self) -> None:
        nu = _interpolate_nu_laminar_inner(0.75)
        assert nu == 10.10

    def test_known_table_point_kappa_0_1(self) -> None:
        nu = _interpolate_nu_laminar_inner(0.1)
        assert nu == 4.85

    def test_interpolation_between_0_25_and_0_5(self) -> None:
        """κ = 0.375 → midpoint between 5.70 and 7.30 = 6.50."""
        nu = _interpolate_nu_laminar_inner(0.375)
        assert nu == pytest.approx(6.50, abs=1e-12)

    def test_interpolation_kappa_0_6(self) -> None:
        """κ = 0.6: between 0.5 (7.30) and 0.75 (10.10).
        t = (0.6-0.5)/(0.75-0.5) = 0.4
        nu = 7.30 + 0.4*(10.10-7.30) = 7.30 + 1.12 = 8.42
        """
        nu = _interpolate_nu_laminar_inner(0.6)
        assert nu == pytest.approx(8.42, abs=1e-12)

    def test_extrapolation_below_table(self) -> None:
        """κ = 0.05: extrapolate from 0.1→0.25 trend.
        slope = (5.70-4.85)/(0.25-0.1) = 0.85/0.15 = 5.6667
        nu = 4.85 + 5.6667*(0.05-0.1) = 4.85 - 0.2833 = 4.5667
        """
        nu = _interpolate_nu_laminar_inner(0.05)
        expected = 4.85 + (5.70 - 4.85) / (0.25 - 0.1) * (0.05 - 0.1)
        assert nu == pytest.approx(expected, rel=1e-12)

    def test_extrapolation_above_table(self) -> None:
        """κ = 0.85: extrapolate from 0.5→0.75 trend.
        slope = (10.10-7.30)/(0.75-0.5) = 2.80/0.25 = 11.2
        nu = 10.10 + 11.2*(0.85-0.75) = 10.10 + 1.12 = 11.22
        """
        nu = _interpolate_nu_laminar_inner(0.85)
        expected = 10.10 + (10.10 - 7.30) / (0.75 - 0.5) * (0.85 - 0.75)
        assert nu == pytest.approx(expected, rel=1e-12)

    def test_kappa_zero_rejected(self) -> None:
        with pytest.raises(ValueError, match="kappa must be in"):
            _interpolate_nu_laminar_inner(0.0)

    def test_kappa_one_rejected(self) -> None:
        with pytest.raises(ValueError, match="kappa must be in"):
            _interpolate_nu_laminar_inner(1.0)

    def test_negative_kappa_rejected(self) -> None:
        with pytest.raises(ValueError, match="kappa must be in"):
            _interpolate_nu_laminar_inner(-0.1)

    def test_monotonicity(self) -> None:
        """Nu_i should be monotonically increasing with κ in (0, 1)."""
        prev = 0.0
        for k in [0.01, 0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 0.99]:
            nu = _interpolate_nu_laminar_inner(k)
            assert nu > prev, f"Non-monotone at kappa={k}"
            prev = nu


class TestAnnulusLaminarInnerCHF:
    """C4: Annulus laminar, inner wall heated, outer insulated."""

    def test_nu_at_known_kappa(self) -> None:
        c = AnnulusLaminarInnerCHF()
        assert c.evaluate(0.5) == pytest.approx(7.30, abs=1e-12)

    def test_metadata(self) -> None:
        c = AnnulusLaminarInnerCHF()
        assert c.correlation_id == "annulus_laminar_inner_chf"
        assert c.supported_geometry == "concentric_annulus"
        assert c.flow_regime == "laminar"
        assert c.boundary_condition == "inner_wall_heated"
        assert c.requires_wall_viscosity is False


class TestAnnulusTurbulentGnielinskiDH:
    """C5: Annulus turbulent — hydraulic-diameter Gnielinski adaptation."""

    def _instance(self) -> AnnulusTurbulentGnielinskiDH:
        return AnnulusTurbulentGnielinskiDH()

    def test_petukhov_friction_factor(self) -> None:
        c = self._instance()
        f = c.petukhov_friction_factor(10000.0)
        expected = (0.790 * math.log(10000.0) - 1.64) ** (-2)
        assert f == pytest.approx(expected, rel=1e-12)

    def test_nu_same_as_tube_for_same_inputs(self) -> None:
        """The D_h adaptation gives the same formula as the tube version."""
        c_ann = self._instance()
        c_tube = TubeTurbulentGnielinski()
        Re, Pr = 20000.0, 5.0
        assert c_ann.evaluate(Re, Pr) == pytest.approx(c_tube.evaluate(Re, Pr), rel=1e-12)

    def test_is_adaptation_flag(self) -> None:
        c = self._instance()
        assert c.is_adaptation is True
        assert len(c.adaptation_limitation) > 0

    def test_boundary_values(self) -> None:
        c = self._instance()
        c.evaluate(c.reynolds_min, c.prandtl_min)
        c.evaluate(c.reynolds_max, c.prandtl_max)

    def test_re_below_min_raises(self) -> None:
        c = self._instance()
        with pytest.raises(ValueError, match="outside valid range"):
            c.evaluate(2999.0, 1.0)

    def test_metadata(self) -> None:
        c = self._instance()
        assert c.correlation_id == "annulus_turbulent_gnielinski_dh"
        assert c.supported_geometry == "concentric_annulus"
        assert c.flow_regime == "turbulent"

    def test_registry_completeness(self) -> None:
        assert set(ANNULUS_CORRELATIONS.keys()) == {
            "annulus_laminar_inner_chf",
            "annulus_turbulent_gnielinski_dh",
        }


# =====================================================================
# Category 5: Correlation Selection
# =====================================================================


class TestSelectCorrelation:
    """Deterministic correlation selection for each geometry/regime combo."""

    def test_tube_laminar_cwt(self) -> None:
        c = select_correlation(_tube_geom(), "constant_wall_temperature", FlowRegime.laminar, False)
        assert c is not None
        assert c.correlation_id == "tube_laminar_cwt"

    def test_tube_laminar_chf(self) -> None:
        c = select_correlation(_tube_geom(), "constant_heat_flux", FlowRegime.laminar, False)
        assert c is not None
        assert c.correlation_id == "tube_laminar_chf"

    def test_tube_laminar_both_returns_cwt_first(self) -> None:
        """BC 'both' selects CHF (alphabetically first, equal priority)."""
        c = select_correlation(_tube_geom(), "both", FlowRegime.laminar, False)
        assert c is not None
        assert c.correlation_id == "tube_laminar_chf"

    def test_tube_turbulent_gnielinski(self) -> None:
        c = select_correlation(
            _tube_geom(), "constant_wall_temperature", FlowRegime.turbulent, False
        )
        assert c is not None
        assert c.correlation_id == "tube_turbulent_gnielinski"

    def test_tube_transitional_returns_none(self) -> None:
        c = select_correlation(
            _tube_geom(), "constant_wall_temperature", FlowRegime.transitional, False
        )
        assert c is None

    def test_annulus_laminar_inner(self) -> None:
        c = select_correlation(_ann_geom(), "inner_wall_heated", FlowRegime.laminar, False)
        assert c is not None
        assert c.correlation_id == "annulus_laminar_inner_chf"

    def test_annulus_laminar_both_selects_inner_chf(self) -> None:
        """Boundary condition 'both' for laminar annulus should select inner CHF."""
        c = select_correlation(_ann_geom(), "both", FlowRegime.laminar, False)
        assert c is not None
        assert c.correlation_id == "annulus_laminar_inner_chf"

    def test_annulus_turbulent(self) -> None:
        c = select_correlation(_ann_geom(), "inner_wall_heated", FlowRegime.turbulent, False)
        assert c is not None
        assert c.correlation_id == "annulus_turbulent_gnielinski_dh"

    def test_annulus_turbulent_adaptation_flag(self) -> None:
        c = select_correlation(_ann_geom(), "inner_wall_heated", FlowRegime.turbulent, False)
        assert c is not None
        assert c.is_adaptation is True

    def test_annulus_laminar_outer_wall_heated_returns_none(self) -> None:
        """No correlation for outer wall heated laminar annulus."""
        c = select_correlation(_ann_geom(), "outer_wall_heated", FlowRegime.laminar, False)
        assert c is None

    def test_tube_laminar_outer_wall_heated_returns_none(self) -> None:
        """No tube correlation for outer_wall_heated."""
        c = select_correlation(_tube_geom(), "outer_wall_heated", FlowRegime.laminar, False)
        assert c is None

    def test_deterministic_selection(self) -> None:
        """Multiple calls with same inputs produce the same candidate."""
        args = (_tube_geom(), "constant_wall_temperature", FlowRegime.laminar, False)
        c1 = select_correlation(*args)
        c2 = select_correlation(*args)
        assert c1 is not None and c2 is not None
        assert c1.correlation_id == c2.correlation_id
        assert c1.version == c2.version


class TestBuildCandidates:
    """Candidate list construction."""

    def test_tube_laminar_candidates(self) -> None:
        cs = _build_candidates(_tube_geom(), "constant_wall_temperature", FlowRegime.laminar, False)
        ids = [c.correlation_id for c in cs]
        assert "tube_laminar_cwt" in ids

    def test_tube_turbulent_candidates(self) -> None:
        cs = _build_candidates(
            _tube_geom(), "constant_wall_temperature", FlowRegime.turbulent, False
        )
        assert len(cs) == 1
        assert cs[0].correlation_id == "tube_turbulent_gnielinski"

    def test_empty_transitional(self) -> None:
        cs = _build_candidates(
            _tube_geom(), "constant_wall_temperature", FlowRegime.transitional, False
        )
        assert len(cs) == 0

    def test_empty_invalid(self) -> None:
        cs = _build_candidates(_tube_geom(), "constant_wall_temperature", FlowRegime.invalid, False)
        assert len(cs) == 0


class TestSortKey:
    """Deterministic sort key ordering."""

    def test_priority_ordering(self) -> None:
        c1 = CorrelationCandidate(
            correlation_id="aaa",
            version="1.0.0",
            priority=10,
            supports_geometry="circular_tube",
            supports_boundary="a",
            supports_flow_regime="laminar",
            requires_wall_viscosity=False,
        )
        c2 = CorrelationCandidate(
            correlation_id="bbb",
            version="1.0.0",
            priority=5,
            supports_geometry="circular_tube",
            supports_boundary="a",
            supports_flow_regime="laminar",
            requires_wall_viscosity=False,
        )
        # Higher priority comes first → smaller (-priority) is first
        assert _sort_key(c1) < _sort_key(c2)


# =====================================================================
# Category 6: End-to-End Service Evaluation
# =====================================================================


class TestEvaluateHXCorrelation:
    """Full-service integration tests for evaluate_hx_correlation."""

    def test_tube_laminar_cwt_success(self) -> None:
        """Low mass flow → laminar → CWT → Nu = 3.66."""
        flow = _water_flow(mass_flow=0.005)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")

        assert result.status == CorrelationStatus.SUCCEEDED
        assert result.nusselt_number == pytest.approx(3.66, abs=1e-12)
        assert result.selected_correlation is not None
        assert result.selected_correlation.correlation_id == "tube_laminar_cwt"
        assert result.flow_regime == "laminar"

        # Verify h = Nu * k / D_h
        expected_h = 3.66 * K / TUBE_DH
        assert result.heat_transfer_coefficient == pytest.approx(expected_h, rel=1e-12)

    def test_tube_laminar_chf_success(self) -> None:
        """Low mass flow → laminar → CHF → Nu = 4.36."""
        flow = _water_flow(mass_flow=0.005)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_heat_flux")

        assert result.status == CorrelationStatus.SUCCEEDED
        assert result.nusselt_number == pytest.approx(4.36, abs=1e-12)
        assert result.selected_correlation is not None
        assert result.selected_correlation.correlation_id == "tube_laminar_chf"

    def test_tube_turbulent_gnielinski_success(self) -> None:
        """High mass flow → turbulent → Gnielinski."""
        # Need Re > 10000: m_dot = Re * A * μ / D_h
        # For Re ≈ 15000: m_dot ≈ 0.3 kg/s
        flow = _water_flow(mass_flow=0.3)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")

        assert result.status == CorrelationStatus.SUCCEEDED
        assert result.flow_regime == "turbulent"
        assert result.selected_correlation is not None
        assert result.selected_correlation.correlation_id == "tube_turbulent_gnielinski"
        assert result.nusselt_number > 1.0  # reasonable Nu
        assert result.heat_transfer_coefficient > 0.0

    def test_annulus_turbulent_gnielinski_dh_success(self) -> None:
        """Turbulent flow in annulus → adapted Gnielinski-DH."""
        # Annulus: Re = m_dot * D_h / (A * μ), need Re > 10000
        # For Re ≈ 17000: m_dot ≈ 1.0 kg/s
        flow = _water_flow(mass_flow=1.0)
        result = evaluate_hx_correlation(_ann_geom(), flow, "inner_wall_heated")

        assert result.status == CorrelationStatus.SUCCEEDED
        assert result.flow_regime == "turbulent"
        assert result.selected_correlation is not None
        assert result.selected_correlation.correlation_id == "annulus_turbulent_gnielinski_dh"
        # Adaptation warning should be present
        adapt_warns = [w for w in result.warnings if "adaptation" in w.message.lower()]
        assert len(adapt_warns) > 0

    def test_annulus_laminar_inner_chf_success(self) -> None:
        """Low mass flow in annulus → laminar → inner CHF."""
        flow = _water_flow(mass_flow=0.005)
        result = evaluate_hx_correlation(_ann_geom(), flow, "inner_wall_heated")

        assert result.status == CorrelationStatus.SUCCEEDED
        assert result.flow_regime == "laminar"
        assert result.selected_correlation is not None
        assert result.selected_correlation.correlation_id == "annulus_laminar_inner_chf"
        # For κ = 0.5, Nu_i = 7.30
        assert result.nusselt_number == pytest.approx(7.30, abs=1e-12)

    def test_zero_mass_flow_blocked(self) -> None:
        """Zero mass flow → BLOCKED."""
        flow = _water_flow(mass_flow=0.0)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")

        assert result.status == CorrelationStatus.BLOCKED
        assert len(result.blockers) > 0
        assert any("zero mass flow" in b.message.lower() for b in result.blockers)

    def test_transitional_blocked(self) -> None:
        """Transitional Re → BLOCKED (no correlations available)."""
        # Need Re between 2300 and 10000 → set mass flow accordingly
        # Re = m_dot * D_h / (A * μ) → m_dot = Re * A * μ / D_h
        # For Re ≈ 5000: m_dot ≈ 0.098 kg/s
        target_re = 5000.0
        m_dot = target_re * TUBE_A * MU / TUBE_DH
        flow = _water_flow(mass_flow=m_dot)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")

        assert result.status == CorrelationStatus.BLOCKED
        assert result.flow_regime == "transitional"
        assert any("transitional" in b.message.lower() for b in result.blockers)

    def test_computed_quantities_populated(self) -> None:
        """All computed quantities should be populated in a succeeded result."""
        flow = _water_flow(mass_flow=0.3)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")

        assert result.status == CorrelationStatus.SUCCEEDED
        assert result.flow_area_m2 > 0
        assert result.mean_velocity_ms > 0
        assert result.hydraulic_diameter_m > 0
        assert result.reynolds_number > 0
        assert result.prandtl_number > 0
        assert result.nusselt_number > 0
        assert result.heat_transfer_coefficient > 0

    def test_provenance_graph_built(self) -> None:
        """A succeeded result should have a valid provenance graph."""
        flow = _water_flow(mass_flow=0.3)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")

        assert len(result.provenance_graph.nodes) > 0
        assert len(result.provenance_graph.edges) > 0

    def test_geometry_type_tube(self) -> None:
        flow = _water_flow(mass_flow=0.005)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        geo = result.geometry
        assert geo.geometry_type == "circular_tube"

    def test_geometry_type_annulus(self) -> None:
        flow = _water_flow(mass_flow=0.005)
        result = evaluate_hx_correlation(_ann_geom(), flow, "inner_wall_heated")
        geo = result.geometry
        assert geo.geometry_type == "concentric_annulus"


# =====================================================================
# Category 7: Hash Integrity, Provenance, JSON Round-Trip, Tamper Detection
# =====================================================================


class TestResultHashIntegrity:
    """CorrelationResult hash integrity and tamper detection."""

    def _make_result(self) -> CorrelationResult:
        flow = _water_flow(mass_flow=0.3)
        return evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")

    def test_result_hash_format(self) -> None:
        r = self._make_result()
        assert r.result_hash.startswith("sha256:")
        assert len(r.result_hash) == 71  # "sha256:" + 64 hex chars

    def test_result_hash_is_hex(self) -> None:
        r = self._make_result()
        hex_part = r.result_hash[7:]
        int(hex_part, 16)  # Should not raise

    def test_validate_integrity(self) -> None:
        r = self._make_result()
        assert r.validate_integrity() is True

    def test_tamper_detection_nusselt(self) -> None:
        """Changing nusselt_number should break integrity."""
        r = self._make_result()
        # Pydantic frozen model: use object.__setattr__ to tamper
        object.__setattr__(r, "nusselt_number", 999.0)
        assert r.validate_integrity() is False

    def test_tamper_detection_result_hash(self) -> None:
        """Tampering with result_hash should break verify_hash."""
        r = self._make_result()
        object.__setattr__(r, "result_hash", "sha256:" + "0" * 64)
        assert r.verify_hash() is False

    def test_two_results_same_inputs_same_hash(self) -> None:
        """Deterministic: same inputs → same hash."""
        flow = _water_flow(mass_flow=0.3)
        r1 = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        r2 = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        assert r1.result_hash == r2.result_hash

    def test_different_inputs_different_hash(self) -> None:
        """Different mass flows → different hashes."""
        r1 = evaluate_hx_correlation(
            _tube_geom(), _water_flow(mass_flow=0.01), "constant_wall_temperature"
        )
        r2 = evaluate_hx_correlation(
            _tube_geom(), _water_flow(mass_flow=0.3), "constant_wall_temperature"
        )
        assert r1.result_hash != r2.result_hash


class TestJSONRoundTrip:
    """JSON serialization/deserialization round-trip for CorrelationResult."""

    def test_succeeded_roundtrip(self) -> None:
        flow = _water_flow(mass_flow=0.3)
        r = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")

        json_str = r.model_dump_json()
        restored = CorrelationResult.model_validate_json(json_str)

        assert restored.status == CorrelationStatus.SUCCEEDED
        assert restored.result_hash == r.result_hash
        assert restored.nusselt_number == pytest.approx(r.nusselt_number, rel=1e-12)
        assert restored.heat_transfer_coefficient == pytest.approx(
            r.heat_transfer_coefficient, rel=1e-12
        )

    def test_blocked_roundtrip(self) -> None:
        flow = _water_flow(mass_flow=0.0)
        r = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")

        json_str = r.model_dump_json()
        restored = CorrelationResult.model_validate_json(json_str)

        assert restored.status == CorrelationStatus.BLOCKED
        assert len(restored.blockers) > 0

    def test_roundtrip_preserves_provenance(self) -> None:
        flow = _water_flow(mass_flow=0.3)
        r = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")

        json_str = r.model_dump_json()
        restored = CorrelationResult.model_validate_json(json_str)

        assert len(restored.provenance_graph.nodes) == len(r.provenance_graph.nodes)
        assert len(restored.provenance_graph.edges) == len(r.provenance_graph.edges)

    def test_roundtrip_preserves_selected_correlation(self) -> None:
        flow = _water_flow(mass_flow=0.3)
        r = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")

        json_str = r.model_dump_json()
        restored = CorrelationResult.model_validate_json(json_str)

        assert restored.selected_correlation is not None
        assert restored.selected_correlation.correlation_id == r.selected_correlation.correlation_id


class TestCorrelationResultModel:
    """CorrelationResult model validation and status contracts."""

    def test_succeeded_no_blockers(self) -> None:
        flow = _water_flow(mass_flow=0.3)
        r = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        assert r.status == CorrelationStatus.SUCCEEDED
        assert len(r.blockers) == 0
        assert r.failure is None

    def test_blocked_has_blockers(self) -> None:
        flow = _water_flow(mass_flow=0.0)
        r = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        assert r.status == CorrelationStatus.BLOCKED
        assert len(r.blockers) > 0

    def test_blocked_status_contract(self) -> None:
        """BLOCKED status must have at least one blocker (enforced by validator)."""
        flow = _water_flow(mass_flow=0.0)
        r = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        assert r.status == CorrelationStatus.BLOCKED
        assert len(r.blockers) >= 1

    def test_selected_correlation_info_fields(self) -> None:
        flow = _water_flow(mass_flow=0.005)
        r = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        info = r.selected_correlation
        assert info is not None
        assert info.correlation_id == "tube_laminar_cwt"
        assert info.version == "1.0.0"
        assert info.priority > 0

    def test_execution_context(self) -> None:
        ctx = CalculationContext(
            request_id=uuid4(),
            design_case_revision_id=uuid4(),
            calculation_run_id=uuid4(),
        )
        flow = _water_flow(mass_flow=0.3)
        r = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature", context=ctx)
        assert r.execution_context.request_id is not None
        assert r.execution_context.calculation_run_id is not None


class TestProvenanceGraph:
    """Provenance graph construction and verification."""

    def _make_result(self) -> CorrelationResult:
        flow = _water_flow(mass_flow=0.3)
        return evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")

    def test_graph_has_required_nodes(self) -> None:
        r = self._make_result()
        node_types = {n.node_type for n in r.provenance_graph.nodes}
        assert ProvenanceNodeType.EXTERNAL in node_types
        assert ProvenanceNodeType.CALCULATION_RUN in node_types
        assert ProvenanceNodeType.CORRELATION in node_types
        assert ProvenanceNodeType.RESULT in node_types

    def test_graph_dag(self) -> None:
        """Provenance graph should be a DAG (no cycles)."""
        r = self._make_result()
        node_ids = {n.node_id for n in r.provenance_graph.nodes}
        in_degree = {nid: 0 for nid in node_ids}
        adjacency: dict[UUID, list[UUID]] = {nid: [] for nid in node_ids}
        for edge in r.provenance_graph.edges:
            assert edge.source_id in node_ids
            assert edge.target_id in node_ids
            adjacency[edge.source_id].append(edge.target_id)
            in_degree[edge.target_id] += 1

        # Topological sort to verify no cycles
        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        visited = 0
        while queue:
            nid = queue.pop(0)
            visited += 1
            for neighbor in adjacency[nid]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        assert visited == len(node_ids)

    def test_graph_no_self_loops(self) -> None:
        r = self._make_result()
        for edge in r.provenance_graph.edges:
            assert edge.source_id != edge.target_id

    def test_graph_edge_references_valid_nodes(self) -> None:
        r = self._make_result()
        node_ids = {n.node_id for n in r.provenance_graph.nodes}
        for edge in r.provenance_graph.edges:
            assert edge.source_id in node_ids
            assert edge.target_id in node_ids

    def test_provenance_digest_deterministic(self) -> None:
        flow = _water_flow(mass_flow=0.3)
        r1 = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        r2 = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        assert r1.provenance_digest == r2.provenance_digest

    def test_provenance_digest_changes_with_inputs(self) -> None:
        r1 = evaluate_hx_correlation(
            _tube_geom(), _water_flow(mass_flow=0.01), "constant_wall_temperature"
        )
        r2 = evaluate_hx_correlation(
            _tube_geom(), _water_flow(mass_flow=0.3), "constant_wall_temperature"
        )
        assert r1.provenance_digest != r2.provenance_digest

    def test_deterministic_uuid5(self) -> None:
        """Same payload → same UUID5."""
        payload = {"key": "value", "num": 42}
        u1 = _deterministic_uuid5(payload)
        u2 = _deterministic_uuid5(payload)
        assert u1 == u2

    def test_deterministic_uuid5_different_payloads(self) -> None:
        u1 = _deterministic_uuid5({"key": "a"})
        u2 = _deterministic_uuid5({"key": "b"})
        assert u1 != u2

    def test_build_provenance_graph_directly(self) -> None:
        """Direct construction of provenance graph."""
        ctx = ExecutionContextSnapshot(request_id=uuid4())
        graph = _build_provenance_graph(
            geometry=_tube_geom(),
            correlation_id="tube_laminar_cwt",
            correlation_version="1.0.0",
            reynolds=200.0,
            prandtl=7.0,
            nu=3.66,
            h=87.84,
            warnings=(),
            blockers=(),
            execution_context=ctx,
            status=CorrelationStatus.SUCCEEDED,
        )
        assert len(graph.nodes) > 0
        assert len(graph.edges) > 0

        # Verify all nodes have deterministic UUID5 IDs
        for node in graph.nodes:
            assert isinstance(node.node_id, UUID)

    def test_graph_digest_deterministic(self) -> None:
        """Same graph structure → same digest."""
        ctx = ExecutionContextSnapshot(request_id=uuid4())
        g1 = _build_provenance_graph(
            geometry=_tube_geom(),
            correlation_id="tube_laminar_cwt",
            correlation_version="1.0.0",
            reynolds=200.0,
            prandtl=7.0,
            nu=3.66,
            h=87.84,
            warnings=(),
            blockers=(),
            execution_context=ctx,
            status=CorrelationStatus.SUCCEEDED,
        )
        g2 = _build_provenance_graph(
            geometry=_tube_geom(),
            correlation_id="tube_laminar_cwt",
            correlation_version="1.0.0",
            reynolds=200.0,
            prandtl=7.0,
            nu=3.66,
            h=87.84,
            warnings=(),
            blockers=(),
            execution_context=ctx,
            status=CorrelationStatus.SUCCEEDED,
        )
        assert _provenance_graph_digest(g1) == _provenance_graph_digest(g2)


class TestSelectedCorrelationInfo:
    """SelectedCorrelationInfo immutability."""

    def test_frozen(self) -> None:
        info = SelectedCorrelationInfo(
            correlation_id="tube_laminar_cwt",
            version="1.0.0",
        )
        with pytest.raises(ValidationError):
            info.correlation_id = "modified"  # type: ignore[misc]

    def test_adaptation_fields(self) -> None:
        info = SelectedCorrelationInfo(
            correlation_id="annulus_turbulent_gnielinski_dh",
            version="1.0.0",
            is_adaptation=True,
            adaptation_limitation="Test limitation",
        )
        assert info.is_adaptation is True
        assert info.adaptation_limitation == "Test limitation"


# =====================================================================
# Category 8: Edge Cases and Integration
# =====================================================================


class TestEdgeCases:
    """Boundary conditions and unusual inputs."""

    def test_very_high_re_turbulent(self) -> None:
        """Very high Reynolds number should still produce a result."""
        # With mass flow = 10 kg/s in a 25 mm tube:
        # Re = 10 / (1000 * 4.9087e-4) * 0.025 / 0.001 * 1000 ≈ 509,000
        flow = _water_flow(mass_flow=10.0)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        assert result.status == CorrelationStatus.SUCCEEDED
        assert result.flow_regime == "turbulent"
        assert result.nusselt_number > 0

    def test_very_low_re_laminar(self) -> None:
        """Very low Reynolds number (creeping flow) should still work for laminar."""
        flow = _water_flow(mass_flow=0.0005)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        assert result.status == CorrelationStatus.SUCCEEDED
        assert result.flow_regime == "laminar"
        assert result.nusselt_number == pytest.approx(3.66, abs=1e-12)

    def test_annulus_wide_gap(self) -> None:
        """Annulus with small inner tube (low κ)."""
        g = _ann_geom(di=0.005, do=0.050)  # κ = 0.1
        flow = _water_flow(mass_flow=0.005)
        result = evaluate_hx_correlation(g, flow, "inner_wall_heated")
        assert result.status == CorrelationStatus.SUCCEEDED
        assert result.nusselt_number == pytest.approx(4.85, abs=1e-12)

    def test_annulus_narrow_gap(self) -> None:
        """Annulus with large inner tube (high κ)."""
        g = _ann_geom(di=0.045, do=0.050)  # κ = 0.9
        flow = _water_flow(mass_flow=0.005)
        result = evaluate_hx_correlation(g, flow, "inner_wall_heated")
        assert result.status == CorrelationStatus.SUCCEEDED
        assert result.nusselt_number > 10.0  # Extrapolated, high Nu_i

    def test_heating_vs_cooling(self) -> None:
        """Heating and cooling should both produce valid results."""
        flow_heat = _water_flow(mass_flow=0.005, heating=True)
        flow_cool = _water_flow(mass_flow=0.005, heating=False)
        r1 = evaluate_hx_correlation(_tube_geom(), flow_heat, "constant_wall_temperature")
        r2 = evaluate_hx_correlation(_tube_geom(), flow_cool, "constant_wall_temperature")
        # Both should succeed and have same Nu (laminar CWT is independent of heating direction)
        assert r1.status == CorrelationStatus.SUCCEEDED
        assert r2.status == CorrelationStatus.SUCCEEDED
        assert r1.nusselt_number == pytest.approx(r2.nusselt_number, abs=1e-12)

    def test_wall_temperature_optional(self) -> None:
        """Wall temperature is optional — should not affect laminar CWT result."""
        flow_no_wall = _water_flow(mass_flow=0.005, wall_temp=None)
        flow_with_wall = _water_flow(mass_flow=0.005, wall_temp=400.0)
        r1 = evaluate_hx_correlation(_tube_geom(), flow_no_wall, "constant_wall_temperature")
        r2 = evaluate_hx_correlation(_tube_geom(), flow_with_wall, "constant_wall_temperature")
        assert r1.status == CorrelationStatus.SUCCEEDED
        assert r2.status == CorrelationStatus.SUCCEEDED
        assert r1.nusselt_number == pytest.approx(r2.nusselt_number, abs=1e-12)


class TestFlowPropertiesInput:
    """FlowPropertiesInput validation."""

    def test_construction(self) -> None:
        f = _water_flow()
        assert f.mass_flow_kg_s == 0.1
        assert f.density_kg_m3 == RHO

    def test_frozen(self) -> None:
        f = _water_flow()
        with pytest.raises(ValidationError):
            f.mass_flow_kg_s = 0.5  # type: ignore[misc]

    def test_negative_mass_flow_rejected(self) -> None:
        with pytest.raises(ValidationError, match="non-negative"):
            FlowPropertiesInput(
                mass_flow_kg_s=-0.1,
                density_kg_m3=RHO,
                dynamic_viscosity_pa_s=MU,
                thermal_conductivity_w_m_k=K,
                specific_heat_j_kg_k=CP,
                bulk_temperature_k=350.0,
            )

    def test_zero_mass_flow_allowed(self) -> None:
        f = FlowPropertiesInput(
            mass_flow_kg_s=0.0,
            density_kg_m3=RHO,
            dynamic_viscosity_pa_s=MU,
            thermal_conductivity_w_m_k=K,
            specific_heat_j_kg_k=CP,
            bulk_temperature_k=350.0,
        )
        assert f.mass_flow_kg_s == 0.0

    def test_negative_density_rejected(self) -> None:
        with pytest.raises(ValidationError, match="positive"):
            FlowPropertiesInput(
                mass_flow_kg_s=0.1,
                density_kg_m3=-1000.0,
                dynamic_viscosity_pa_s=MU,
                thermal_conductivity_w_m_k=K,
                specific_heat_j_kg_k=CP,
                bulk_temperature_k=350.0,
            )

    def test_negative_bulk_temp_rejected(self) -> None:
        with pytest.raises(ValidationError, match="positive"):
            FlowPropertiesInput(
                mass_flow_kg_s=0.1,
                density_kg_m3=RHO,
                dynamic_viscosity_pa_s=MU,
                thermal_conductivity_w_m_k=K,
                specific_heat_j_kg_k=CP,
                bulk_temperature_k=-100.0,
            )

    def test_optional_fields(self) -> None:
        f = _water_flow()
        assert f.wall_temperature_k is None
        assert f.wall_viscosity_pa_s is None
        assert f.heating is True

    def test_wall_temp_positive_validation(self) -> None:
        with pytest.raises(ValidationError, match="positive"):
            FlowPropertiesInput(
                mass_flow_kg_s=0.1,
                density_kg_m3=RHO,
                dynamic_viscosity_pa_s=MU,
                thermal_conductivity_w_m_k=K,
                specific_heat_j_kg_k=CP,
                bulk_temperature_k=350.0,
                wall_temperature_k=-100.0,
            )


class TestFlowRegimeEnum:
    """FlowRegime enum values."""

    def test_values(self) -> None:
        assert FlowRegime.laminar.value == "laminar"
        assert FlowRegime.transitional.value == "transitional"
        assert FlowRegime.turbulent.value == "turbulent"
        assert FlowRegime.invalid.value == "invalid"


class TestCorrelationStatusEnum:
    """CorrelationStatus enum values."""

    def test_values(self) -> None:
        assert CorrelationStatus.SUCCEEDED.value == "succeeded"
        assert CorrelationStatus.BLOCKED.value == "blocked"
        assert CorrelationStatus.FAILED.value == "failed"


class TestRegimeConstants:
    """Regime threshold constants match specification."""

    def test_laminar_upper(self) -> None:
        assert LAMINAR_UPPER_RE == 2300.0

    def test_turbulent_lower(self) -> None:
        assert TURBULENT_LOWER_RE == 10000.0


class TestGnielinskiConsistency:
    """Verify tube and annulus Gnielinski use the same formula."""

    def test_same_petukhov(self) -> None:
        tube = TubeTurbulentGnielinski()
        ann = AnnulusTurbulentGnielinskiDH()
        for re in [3000, 5000, 10000, 50000, 100000]:
            assert tube.petukhov_friction_factor(re) == pytest.approx(
                ann.petukhov_friction_factor(re), rel=1e-12
            )

    def test_same_nu_for_pr1(self) -> None:
        """At Pr = 1, denominator is 1, so Nu = (f/8)(Re-1000)."""
        tube = TubeTurbulentGnielinski()
        ann = AnnulusTurbulentGnielinskiDH()
        for re in [3000, 10000, 100000]:
            assert tube.evaluate(re, 1.0) == pytest.approx(ann.evaluate(re, 1.0), rel=1e-12)


class TestAnnulusGeometryConsistency:
    """D_h for concentric annulus equals D_o - D_i."""

    def test_various_diameters(self) -> None:
        for di, do in [(0.010, 0.030), (0.015, 0.050), (0.020, 0.040), (0.030, 0.060)]:
            g = ConcentricAnnulusGeometry(
                inner_tube_outer_diameter_m=di,
                outer_pipe_inside_diameter_m=do,
                heat_transfer_length_m=2.0,
            )
            assert g.hydraulic_diameter_m == pytest.approx(do - di, rel=1e-12)

    def test_area_plus_perimeters(self) -> None:
        """4A / P_total should equal D_h = D_o - D_i."""
        g = _ann_geom()
        dh = 4.0 * g.flow_area_m2 / g.total_wetted_perimeter_m
        assert dh == pytest.approx(g.hydraulic_diameter_m, rel=1e-12)
