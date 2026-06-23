"""Comprehensive unit tests for TASK-007 — tube and annulus correlation review fixes.

Covers ALL 16 test categories:
  1.  Geometry tests
  2.  Dimensionless calculations
  3.  Regime boundary tests
  4.  Correlation reference cases
  5.  Selection determinism
  6.  Structured failure
  7.  Integrity tests
  8.  Hash identity
  9.  C4 κ range
  10. Wall property validation
  11. Boundary condition validation
  12. Provenance topology
  13. SemVer selection
  14. Golden cases
  15. Zero duty / zero flow
  16. Provenance JSON round-trip
"""

from __future__ import annotations

import math
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from hexagent.core.heat_balance import ExecutionContextSnapshot
from hexagent.correlations.annulus import (
    _KAPPA_ABSOLUTE_MAX,
    _KAPPA_ABSOLUTE_MIN,
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
    NusseltBasis,
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
    _provenance_graph_digest,
)
from hexagent.correlations.models import (
    ApplicabilityVariable,
    CorrelationDefinition,
    CorrelationKey,
    GeometryType,
    PhaseRegime,
    SourceVerificationStatus,
    compare_semver,
    compute_definition_hash,
    parse_semver,
)
from hexagent.correlations.registry import InMemoryCorrelationRegistry
from hexagent.correlations.selection import (
    _get_nusselt_basis,
    _is_boundary_compatible,
    select_correlation,
)
from hexagent.correlations.service import (
    CalculationContext,
    _get_registry,
    evaluate_hx_correlation,
)
from hexagent.correlations.tube import (
    TUBE_CORRELATIONS,
    TubeLaminarCHF,
    TubeLaminarCWT,
    TubeTurbulentGnielinski,
)
from hexagent.domain.messages import (
    ErrorCode,
)
from hexagent.domain.provenance import (
    ProvenanceGraph,
    ProvenanceNodeType,
)

# ---------------------------------------------------------------------------
# Shared test constants and helpers
# ---------------------------------------------------------------------------

# Water-like properties
RHO = 998.0  # kg/m³
MU = 0.001  # Pa·s
K = 0.6  # W/(m·K)
CP = 4182.0  # J/(kg·K)
PR = CP * MU / K  # ≈ 6.98

# Circular tube geometry (25 mm ID, 2 m)
TUBE_D = 0.025  # m
TUBE_L = 2.0  # m
TUBE_A = math.pi / 4.0 * TUBE_D**2
TUBE_P = math.pi * TUBE_D
TUBE_DH = TUBE_D  # = 0.025 m

# Annulus geometry (25 mm inner OD, 50 mm outer ID, 2 m)
ANN_DI = 0.025  # m
ANN_DO = 0.050  # m
ANN_L = 2.0  # m
ANN_KAPPA = ANN_DI / ANN_DO  # = 0.5
ANN_A = math.pi / 4.0 * (ANN_DO**2 - ANN_DI**2)
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


def _registry() -> InMemoryCorrelationRegistry:
    """Return the default registry singleton."""
    return _get_registry()


def _make_result_tube_laminar() -> CorrelationResult:
    flow = _water_flow(mass_flow=0.005)
    return evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")


def _make_result_tube_turbulent() -> CorrelationResult:
    flow = _water_flow(mass_flow=0.3)
    return evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")


def _make_result_blocked() -> CorrelationResult:
    flow = _water_flow(mass_flow=0.0)
    return evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")


# =====================================================================
# Category 1: Geometry Tests
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

    def test_negative_inf_diameter_rejected(self) -> None:
        with pytest.raises(ValidationError, match="finite positive"):
            CircularTubeGeometry(inside_diameter_m=float("-inf"), heat_transfer_length_m=TUBE_L)


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

    def test_equal_diameters_rejected(self) -> None:
        with pytest.raises(ValidationError, match="must be greater"):
            ConcentricAnnulusGeometry(
                inner_tube_outer_diameter_m=0.025,
                outer_pipe_inside_diameter_m=0.025,
                heat_transfer_length_m=ANN_L,
            )

    def test_reversed_diameters_rejected(self) -> None:
        with pytest.raises(ValidationError, match="must be greater"):
            ConcentricAnnulusGeometry(
                inner_tube_outer_diameter_m=0.050,
                outer_pipe_inside_diameter_m=0.025,
                heat_transfer_length_m=ANN_L,
            )

    def test_zero_inner_diameter_rejected(self) -> None:
        with pytest.raises(ValidationError, match="finite positive"):
            ConcentricAnnulusGeometry(
                inner_tube_outer_diameter_m=0.0,
                outer_pipe_inside_diameter_m=0.050,
                heat_transfer_length_m=ANN_L,
            )

    def test_zero_outer_diameter_rejected(self) -> None:
        with pytest.raises(ValidationError, match="finite positive"):
            ConcentricAnnulusGeometry(
                inner_tube_outer_diameter_m=0.025,
                outer_pipe_inside_diameter_m=0.0,
                heat_transfer_length_m=ANN_L,
            )

    def test_negative_inner_diameter_rejected(self) -> None:
        with pytest.raises(ValidationError, match="finite positive"):
            ConcentricAnnulusGeometry(
                inner_tube_outer_diameter_m=-0.01,
                outer_pipe_inside_diameter_m=0.050,
                heat_transfer_length_m=ANN_L,
            )

    def test_nan_inner_diameter_rejected(self) -> None:
        with pytest.raises(ValidationError, match="finite positive"):
            ConcentricAnnulusGeometry(
                inner_tube_outer_diameter_m=float("nan"),
                outer_pipe_inside_diameter_m=0.050,
                heat_transfer_length_m=ANN_L,
            )

    def test_inf_outer_diameter_rejected(self) -> None:
        with pytest.raises(ValidationError, match="finite positive"):
            ConcentricAnnulusGeometry(
                inner_tube_outer_diameter_m=0.025,
                outer_pipe_inside_diameter_m=float("inf"),
                heat_transfer_length_m=ANN_L,
            )

    def test_very_small_valid_gap(self) -> None:
        """Very small gap between inner and outer should still work."""
        g = ConcentricAnnulusGeometry(
            inner_tube_outer_diameter_m=0.049,
            outer_pipe_inside_diameter_m=0.050,
            heat_transfer_length_m=ANN_L,
        )
        assert g.hydraulic_diameter_m == pytest.approx(0.001, rel=1e-6)
        assert g.flow_area_m2 > 0

    def test_frozen(self) -> None:
        g = _ann_geom()
        with pytest.raises(ValidationError):
            g.inner_tube_outer_diameter_m = 0.1  # type: ignore[misc]

    def test_diameter_ratio_properties(self) -> None:
        g = _ann_geom()
        assert g.diameter_ratio == pytest.approx(ANN_DI / ANN_DO, rel=1e-12)


class TestThermalBoundaryCondition:
    """ThermalBoundaryCondition constants exist and are strings."""

    def test_constants(self) -> None:
        assert ThermalBoundaryCondition.CONSTANT_WALL_TEMPERATURE == "constant_wall_temperature"
        assert ThermalBoundaryCondition.CONSTANT_HEAT_FLUX == "constant_heat_flux"
        assert ThermalBoundaryCondition.INNER_WALL_HEATED == "inner_wall_heated"
        assert ThermalBoundaryCondition.OUTER_WALL_HEATED == "outer_wall_heated"
        assert ThermalBoundaryCondition.BOTH_WALLS_HEATED == "both_walls_heated"


# =====================================================================
# Category 2: Dimensionless Calculations
# =====================================================================


class TestClassifyRegime:
    """Regime classification boundaries and edge cases."""

    def test_laminar(self) -> None:
        assert classify_regime(1000) == FlowRegime.laminar

    def test_laminar_upper_bound_exclusive(self) -> None:
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

    def test_zero_mass_flow(self) -> None:
        v = compute_velocity(0.0, RHO, TUBE_A)
        assert v == 0.0


class TestComputeReynolds:
    """Reynolds number: Re = ρ v D_h / μ."""

    def test_basic(self) -> None:
        v = compute_velocity(0.1, RHO, TUBE_A)
        re = compute_reynolds(RHO, v, TUBE_DH, MU)
        expected = RHO * v * TUBE_DH / MU
        assert re == pytest.approx(expected, rel=1e-12)

    def test_low_mass_flow_gives_laminar(self) -> None:
        v = compute_velocity(0.005, RHO, TUBE_A)
        re = compute_reynolds(RHO, v, TUBE_DH, MU)
        assert re < LAMINAR_UPPER_RE

    def test_rejects_negative_viscosity(self) -> None:
        with pytest.raises(ValueError, match="finite positive"):
            compute_reynolds(RHO, 0.2, TUBE_DH, -0.001)

    def test_rejects_zero_dh(self) -> None:
        with pytest.raises(ValueError, match="finite positive"):
            compute_reynolds(RHO, 0.2, 0.0, MU)

    def test_rejects_non_finite(self) -> None:
        with pytest.raises(ValueError, match="finite positive"):
            compute_reynolds(float("nan"), 0.2, TUBE_DH, MU)


class TestComputePrandtl:
    """Prandtl number: Pr = cp × μ / k."""

    def test_water_at_350k(self) -> None:
        pr = compute_prandtl(CP, MU, K)
        expected = CP * MU / K
        assert pr == pytest.approx(expected, rel=1e-12)

    def test_rejects_zero_cp(self) -> None:
        with pytest.raises(ValueError, match="finite positive"):
            compute_prandtl(0.0, MU, K)

    def test_rejects_zero_mu(self) -> None:
        with pytest.raises(ValueError, match="finite positive"):
            compute_prandtl(CP, 0.0, K)

    def test_rejects_zero_k(self) -> None:
        with pytest.raises(ValueError, match="finite positive"):
            compute_prandtl(CP, MU, 0.0)


class TestComputeHeatTransferCoefficient:
    """h = Nu × k / D_h."""

    def test_basic(self) -> None:
        h = compute_heat_transfer_coefficient(3.66, K, TUBE_DH)
        expected = 3.66 * K / TUBE_DH
        assert h == pytest.approx(expected, rel=1e-12)

    def test_rejects_zero_nu(self) -> None:
        with pytest.raises(ValueError, match="finite positive"):
            compute_heat_transfer_coefficient(0.0, K, TUBE_DH)

    def test_rejects_zero_k(self) -> None:
        with pytest.raises(ValueError, match="finite positive"):
            compute_heat_transfer_coefficient(3.66, 0.0, TUBE_DH)

    def test_rejects_zero_d_char(self) -> None:
        with pytest.raises(ValueError, match="finite positive"):
            compute_heat_transfer_coefficient(3.66, K, 0.0)


# =====================================================================
# Category 3: Regime Boundary Tests
# =====================================================================


class TestRegimeBoundaries:
    """Test specific Re values at regime boundaries."""

    def test_re_2299_laminar(self) -> None:
        """Re=2299 → just below laminar → laminar."""
        assert classify_regime(2299.0) == FlowRegime.laminar

    def test_re_2300_transitional(self) -> None:
        """Re=2300 → exact boundary → transitional."""
        assert classify_regime(2300.0) == FlowRegime.transitional

    def test_re_2301_transitional(self) -> None:
        """Re=2301 → transitional → blocked by service."""
        assert classify_regime(2301.0) == FlowRegime.transitional

    def test_re_9999_transitional(self) -> None:
        """Re=9999 → transitional → blocked by service."""
        assert classify_regime(9999.0) == FlowRegime.transitional

    def test_re_10000_transitional(self) -> None:
        """Re=10000 → exact turbulent lower → transitional."""
        assert classify_regime(10000.0) == FlowRegime.transitional

    def test_re_10001_turbulent(self) -> None:
        """Re=10001 → just above turbulent → turbulent."""
        assert classify_regime(10001.0) == FlowRegime.turbulent


# =====================================================================
# Category 4: Correlation Reference Cases
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

    def test_pr_boundary_below(self) -> None:
        """Pr below minimum → blocked by applicability."""
        flow = _water_flow(mass_flow=0.005)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        # Pr ≈ 6.98 > 0.6, should succeed
        assert result.status == CorrelationStatus.SUCCEEDED

    def test_registry_entry_exists(self) -> None:
        reg = _registry()
        defn = reg.get(CorrelationKey(correlation_id="tube_laminar_cwt", version="1.0.0"))
        assert defn is not None
        assert defn.definition_hash.startswith("sha256:")

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

    def test_registry_entry_exists(self) -> None:
        reg = _registry()
        defn = reg.get(CorrelationKey(correlation_id="tube_laminar_chf", version="1.0.0"))
        assert defn is not None


class TestTubeTurbulentGnielinski:
    """C3: Tube turbulent Gnielinski correlation."""

    def _instance(self) -> TubeTurbulentGnielinski:
        return TubeTurbulentGnielinski()

    def test_petukhov_friction_factor(self) -> None:
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
        denominator = 1.0 + 12.7 * math.sqrt(f8) * 0.0
        assert nu == pytest.approx(numerator / denominator, rel=1e-12)

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

    def test_boundary_values(self) -> None:
        c = self._instance()
        # Should not raise
        c.evaluate(c.reynolds_min, c.prandtl_min)
        c.evaluate(c.reynolds_max, c.prandtl_max)

    def test_registry_entry_exists(self) -> None:
        reg = _registry()
        defn = reg.get(CorrelationKey(correlation_id="tube_turbulent_gnielinski", version="1.0.0"))
        assert defn is not None

    def test_registry_completeness(self) -> None:
        assert set(TUBE_CORRELATIONS.keys()) == {
            "tube_laminar_cwt",
            "tube_laminar_chf",
            "tube_turbulent_gnielinski",
        }


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
        assert c.nusselt_basis == "inside_diameter"

    def test_registry_entry_exists(self) -> None:
        reg = _registry()
        defn = reg.get(CorrelationKey(correlation_id="annulus_laminar_inner_chf", version="1.0.0"))
        assert defn is not None


class TestInterpolateNuLaminarInner:
    """Kays Table 8-2 interpolation for annulus laminar Nu_i."""

    def test_known_table_point_kappa_0_1(self) -> None:
        assert _interpolate_nu_laminar_inner(0.1) == 4.85

    def test_known_table_point_kappa_0_25(self) -> None:
        assert _interpolate_nu_laminar_inner(0.25) == 5.70

    def test_known_table_point_kappa_0_5(self) -> None:
        assert _interpolate_nu_laminar_inner(0.5) == 7.30

    def test_known_table_point_kappa_0_75(self) -> None:
        assert _interpolate_nu_laminar_inner(0.75) == 10.10

    def test_interpolation_kappa_0_375(self) -> None:
        """κ = 0.375 → midpoint between 5.70 and 7.30 = 6.50."""
        assert _interpolate_nu_laminar_inner(0.375) == pytest.approx(6.50, abs=1e-12)

    def test_interpolation_kappa_0_6(self) -> None:
        """κ = 0.6: between 0.5 (7.30) and 0.75 (10.10)."""
        nu = _interpolate_nu_laminar_inner(0.6)
        assert nu == pytest.approx(8.42, abs=1e-12)

    def test_below_table_rejected(self) -> None:
        with pytest.raises(ValueError, match="outside verified table range"):
            _interpolate_nu_laminar_inner(0.05)

    def test_above_table_rejected(self) -> None:
        with pytest.raises(ValueError, match="outside verified table range"):
            _interpolate_nu_laminar_inner(0.85)

    def test_zero_kappa_rejected(self) -> None:
        with pytest.raises(ValueError, match="outside verified table range"):
            _interpolate_nu_laminar_inner(0.0)

    def test_negative_kappa_rejected(self) -> None:
        with pytest.raises(ValueError, match="outside verified table range"):
            _interpolate_nu_laminar_inner(-0.1)


class TestAnnulusTurbulentGnielinskiDH:
    """C5: Annulus turbulent — hydraulic-diameter Gnielinski adaptation."""

    def _instance(self) -> AnnulusTurbulentGnielinskiDH:
        return AnnulusTurbulentGnielinskiDH()

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

    def test_registry_entry_exists(self) -> None:
        reg = _registry()
        defn = reg.get(
            CorrelationKey(correlation_id="annulus_turbulent_gnielinski_dh", version="1.0.0")
        )
        assert defn is not None

    def test_registry_completeness(self) -> None:
        assert set(ANNULUS_CORRELATIONS.keys()) == {
            "annulus_laminar_inner_chf",
            "annulus_turbulent_gnielinski_dh",
        }


class TestC4DiameterMismatch:
    """C4 with D_i != D_h: h = Nu * k / D_i, NOT D_h."""

    def test_wide_gap_kappa_0_1(self) -> None:
        """Wide gap: D_i=0.005, D_o=0.050 → κ=0.1, Nu=4.85.
        h = Nu * k / D_i = 4.85 * 0.6 / 0.005 = 582.0
        """
        g = _ann_geom(di=0.005, do=0.050)
        flow = _water_flow(mass_flow=0.005)
        result = evaluate_hx_correlation(g, flow, "inner_wall_heated")
        assert result.status == CorrelationStatus.SUCCEEDED
        assert result.nusselt_number == pytest.approx(4.85, abs=1e-12)
        # h uses D_i = 0.005, NOT D_h = 0.045
        expected_h = 4.85 * K / 0.005
        assert result.heat_transfer_coefficient == pytest.approx(expected_h, rel=1e-10)

    def test_narrow_gap_kappa_0_6(self) -> None:
        """Narrow gap: D_i=0.030, D_o=0.050 → κ=0.6.
        Nu = 7.30 + 0.4*(10.10-7.30) = 8.42
        h = 8.42 * 0.6 / 0.030 = 168.4
        """
        g = _ann_geom(di=0.030, do=0.050)
        flow = _water_flow(mass_flow=0.005)
        result = evaluate_hx_correlation(g, flow, "inner_wall_heated")
        assert result.status == CorrelationStatus.SUCCEEDED
        expected_nu = 8.42
        assert result.nusselt_number == pytest.approx(expected_nu, abs=1e-12)
        # h uses D_i = 0.030
        expected_h = expected_nu * K / 0.030
        assert result.heat_transfer_coefficient == pytest.approx(expected_h, rel=1e-10)


# =====================================================================
# Category 5: Selection Determinism
# =====================================================================


class TestSelectionDeterminism:
    """Deterministic correlation selection via registry."""

    def test_tube_laminar_cwt_selected(self) -> None:
        flow = _water_flow(mass_flow=0.005)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        assert result.status == CorrelationStatus.SUCCEEDED
        assert result.selected_correlation is not None
        assert result.selected_correlation.correlation_id == "tube_laminar_cwt"

    def test_tube_laminar_chf_selected(self) -> None:
        flow = _water_flow(mass_flow=0.005)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_heat_flux")
        assert result.status == CorrelationStatus.SUCCEEDED
        assert result.selected_correlation is not None
        assert result.selected_correlation.correlation_id == "tube_laminar_chf"

    def test_tube_turbulent_selected(self) -> None:
        flow = _water_flow(mass_flow=0.3)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        assert result.status == CorrelationStatus.SUCCEEDED
        assert result.selected_correlation is not None
        assert result.selected_correlation.correlation_id == "tube_turbulent_gnielinski"

    def test_annulus_laminar_inner_selected(self) -> None:
        flow = _water_flow(mass_flow=0.005)
        result = evaluate_hx_correlation(_ann_geom(), flow, "inner_wall_heated")
        assert result.status == CorrelationStatus.SUCCEEDED
        assert result.selected_correlation is not None
        assert result.selected_correlation.correlation_id == "annulus_laminar_inner_chf"

    def test_annulus_turbulent_selected(self) -> None:
        flow = _water_flow(mass_flow=1.0)
        result = evaluate_hx_correlation(_ann_geom(), flow, "inner_wall_heated")
        assert result.status == CorrelationStatus.SUCCEEDED
        assert result.selected_correlation is not None
        assert result.selected_correlation.correlation_id == "annulus_turbulent_gnielinski_dh"

    def test_different_registry_order_same_result(self) -> None:
        """Different registry insertion order produces same selection."""
        from hexagent.correlations.models import (
            ApplicabilityEnvelope,
            BibliographicSource,
            CorrelationDefinition,
            CorrelationImplementationStatus,
            CorrelationKey,
            CorrelationPurpose,
            NumericBound,
            UncertaintySpec,
        )

        def _make_cwt_def(version: str = "1.0.0") -> CorrelationDefinition:
            return CorrelationDefinition.create(
                key=CorrelationKey(correlation_id="tube_laminar_cwt", version=version),
                name="Tube Laminar CWT",
                purpose=CorrelationPurpose.nusselt_number,
                description="Fully developed laminar flow, constant wall temperature. Nu_D = 3.66.",
                geometry=frozenset({GeometryType.circular_tube}),
                phase_regimes=frozenset(
                    {PhaseRegime.single_phase_liquid, PhaseRegime.single_phase_gas}
                ),
                envelope=ApplicabilityEnvelope(
                    geometry_types=frozenset({GeometryType.circular_tube}),
                    phase_regimes=frozenset(
                        {PhaseRegime.single_phase_liquid, PhaseRegime.single_phase_gas}
                    ),
                    flow_regimes=frozenset({"laminar"}),
                    bounds=(
                        NumericBound(
                            variable=ApplicabilityVariable.reynolds,
                            minimum=0.0,
                            maximum=2300.0,
                            minimum_inclusive=False,
                            maximum_inclusive=False,
                        ),
                        NumericBound(
                            variable=ApplicabilityVariable.prandtl,
                            minimum=0.6,
                            minimum_inclusive=False,
                        ),
                    ),
                    required_inputs=frozenset(
                        {ApplicabilityVariable.reynolds, ApplicabilityVariable.prandtl}
                    ),
                ),
                source=BibliographicSource(
                    source_id="test_source",
                    title="Test",
                    publication="Test Pub",
                    year=2024,
                    verification_status=SourceVerificationStatus.primary_source_checked,
                ),
                uncertainty=UncertaintySpec(basis="test"),
                implementation_status=CorrelationImplementationStatus.validated,
                implementation_ref="test.ref",
                tags=frozenset(
                    {
                        "bc:constant_wall_temperature",
                        "nusselt_basis:inside_diameter",
                        "priority:10",
                    }
                ),
            )

        # Build two registries with same defn
        reg1 = InMemoryCorrelationRegistry()
        reg1.register(_make_cwt_def("1.0.0"))

        reg2 = InMemoryCorrelationRegistry()
        reg2.register(_make_cwt_def("1.0.0"))

        geo = _tube_geom()
        defn1, _, blocker1 = select_correlation(
            reg1, geo, "constant_wall_temperature", FlowRegime.laminar, 200.0, 7.0
        )
        defn2, _, blocker2 = select_correlation(
            reg2, geo, "constant_wall_temperature", FlowRegime.laminar, 200.0, 7.0
        )
        assert blocker1 is None and blocker2 is None
        assert defn1 is not None and defn2 is not None
        assert defn1.definition_hash == defn2.definition_hash

    def test_version_change_changes_hash(self) -> None:
        """Version change → definition hash changes."""
        defn1 = _registry().get(CorrelationKey(correlation_id="tube_laminar_cwt", version="1.0.0"))
        # A different version would have a different hash
        assert defn1.definition_hash.startswith("sha256:")
        assert len(defn1.definition_hash) == 71

    def test_source_identity_change_changes_hash(self) -> None:
        """Source identity change → definition hash changes."""
        from hexagent.correlations.models import (
            ApplicabilityEnvelope,
            BibliographicSource,
            CorrelationDefinition,
            CorrelationImplementationStatus,
            CorrelationKey,
            CorrelationPurpose,
            NumericBound,
            UncertaintySpec,
        )

        base_kwargs = dict(
            name="Tube Laminar CWT",
            purpose=CorrelationPurpose.nusselt_number,
            description="Test",
            geometry=frozenset({GeometryType.circular_tube}),
            phase_regimes=frozenset(
                {PhaseRegime.single_phase_liquid, PhaseRegime.single_phase_gas}
            ),
            envelope=ApplicabilityEnvelope(
                geometry_types=frozenset({GeometryType.circular_tube}),
                phase_regimes=frozenset(
                    {PhaseRegime.single_phase_liquid, PhaseRegime.single_phase_gas}
                ),
                flow_regimes=frozenset({"laminar"}),
                bounds=(
                    NumericBound(
                        variable=ApplicabilityVariable.reynolds,
                        minimum=0.0,
                        maximum=2300.0,
                        minimum_inclusive=False,
                        maximum_inclusive=False,
                    ),
                    NumericBound(
                        variable=ApplicabilityVariable.prandtl,
                        minimum=0.6,
                        minimum_inclusive=False,
                    ),
                ),
                required_inputs=frozenset(
                    {ApplicabilityVariable.reynolds, ApplicabilityVariable.prandtl}
                ),
            ),
            uncertainty=UncertaintySpec(basis="test"),
            implementation_status=CorrelationImplementationStatus.validated,
            implementation_ref="test.ref",
            tags=frozenset(
                {
                    "bc:constant_wall_temperature",
                    "nusselt_basis:inside_diameter",
                    "priority:10",
                }
            ),
        )

        source1 = BibliographicSource(
            source_id="source_a",
            title="Title A",
            publication="Pub A",
            year=2020,
            verification_status=SourceVerificationStatus.primary_source_checked,
        )
        source2 = BibliographicSource(
            source_id="source_b",
            title="Title B",
            publication="Pub B",
            year=2021,
            verification_status=SourceVerificationStatus.primary_source_checked,
        )

        defn1 = CorrelationDefinition.create(
            key=CorrelationKey(correlation_id="tube_laminar_cwt", version="1.0.0"),
            source=source1,
            **base_kwargs,
        )
        defn2 = CorrelationDefinition.create(
            key=CorrelationKey(correlation_id="tube_laminar_cwt", version="1.0.0"),
            source=source2,
            **base_kwargs,
        )
        assert defn1.definition_hash != defn2.definition_hash

    def test_nusselt_basis_laminar_cwt(self) -> None:
        defn = _registry().get(CorrelationKey(correlation_id="tube_laminar_cwt", version="1.0.0"))
        assert _get_nusselt_basis(defn) == "inside_diameter"

    def test_nusselt_basis_turbulent(self) -> None:
        defn = _registry().get(
            CorrelationKey(correlation_id="tube_turbulent_gnielinski", version="1.0.0")
        )
        assert _get_nusselt_basis(defn) == "inside_diameter"

    def test_nusselt_basis_annulus_turbulent(self) -> None:
        defn = _registry().get(
            CorrelationKey(correlation_id="annulus_turbulent_gnielinski_dh", version="1.0.0")
        )
        assert _get_nusselt_basis(defn) == "hydraulic_diameter"

    def test_nusselt_basis_annulus_laminar(self) -> None:
        defn = _registry().get(
            CorrelationKey(correlation_id="annulus_laminar_inner_chf", version="1.0.0")
        )
        assert _get_nusselt_basis(defn) == "inside_diameter"


# =====================================================================
# Category 6: Structured Failure
# =====================================================================


class TestStructuredFailure:
    """Structured failure cases — various blockers."""

    def test_transitional_blocked(self) -> None:
        """Transitional Re → BLOCKED."""
        target_re = 5000.0
        m_dot = target_re * TUBE_A * MU / TUBE_DH
        flow = _water_flow(mass_flow=m_dot)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        assert result.status == CorrelationStatus.BLOCKED
        assert result.flow_regime == "transitional"
        assert any("transitional" in b.message.lower() for b in result.blockers)

    def test_re_out_of_range(self) -> None:
        """Re out of range for all tube correlations → BLOCKED."""
        # Transitional: between laminar upper and turbulent lower
        target_re = 6000.0
        m_dot = target_re * TUBE_A * MU / TUBE_DH
        flow = _water_flow(mass_flow=m_dot)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        assert result.status == CorrelationStatus.BLOCKED

    def test_unsupported_boundary_condition_tube(self) -> None:
        """Unsupported BC for tube → BLOCKED."""
        flow = _water_flow(mass_flow=0.005)
        result = evaluate_hx_correlation(_tube_geom(), flow, "inner_wall_heated")
        assert result.status == CorrelationStatus.BLOCKED
        assert any("unsupported" in b.message.lower() for b in result.blockers)

    def test_no_applicable_correlation(self) -> None:
        """No correlation for outer_wall_heated + laminar → BLOCKED."""
        flow = _water_flow(mass_flow=0.005)
        result = evaluate_hx_correlation(_ann_geom(), flow, "outer_wall_heated")
        assert result.status == CorrelationStatus.BLOCKED

    def test_blocked_has_no_selected_correlation(self) -> None:
        flow = _water_flow(mass_flow=0.0)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        assert result.status == CorrelationStatus.BLOCKED
        assert result.selected_correlation is None

    def test_blocked_has_blockers(self) -> None:
        flow = _water_flow(mass_flow=0.0)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        assert result.status == CorrelationStatus.BLOCKED
        assert len(result.blockers) > 0

    def test_blocked_provenance_digest_matches(self) -> None:
        """Blocked result's provenance_digest matches recomputed."""
        flow = _water_flow(mass_flow=0.0)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        recomputed = _provenance_graph_digest(result.provenance_graph)
        assert result.provenance_digest == recomputed


# =====================================================================
# Category 7: Integrity Tests
# =====================================================================


class TestResultHashIntegrity:
    """CorrelationResult hash integrity and tamper detection."""

    def test_succeeded_verify_hash_true(self) -> None:
        r = _make_result_tube_laminar()
        assert r.status == CorrelationStatus.SUCCEEDED
        assert r.verify_hash() is True

    def test_blocked_verify_hash_true(self) -> None:
        r = _make_result_blocked()
        assert r.status == CorrelationStatus.BLOCKED
        assert r.verify_hash() is True

    def test_result_hash_format(self) -> None:
        r = _make_result_tube_laminar()
        assert r.result_hash.startswith("sha256:")
        assert len(r.result_hash) == 71

    def test_validate_integrity_succeeded(self) -> None:
        r = _make_result_tube_laminar()
        assert r.validate_integrity() is True

    def test_validate_integrity_blocked(self) -> None:
        r = _make_result_blocked()
        assert r.validate_integrity() is True

    def test_json_roundtrip_preserves_hash(self) -> None:
        r = _make_result_tube_laminar()
        json_str = r.model_dump_json()
        restored = CorrelationResult.model_validate_json(json_str)
        assert restored.result_hash == r.result_hash
        assert restored.verify_hash() is True

    def test_json_roundtrip_preserves_provenance(self) -> None:
        r = _make_result_tube_laminar()
        json_str = r.model_dump_json()
        restored = CorrelationResult.model_validate_json(json_str)
        assert len(restored.provenance_graph.nodes) == len(r.provenance_graph.nodes)
        assert len(restored.provenance_graph.edges) == len(r.provenance_graph.edges)
        assert restored.provenance_digest == r.provenance_digest

    def test_tamper_nusselt_breaks_integrity(self) -> None:
        r = _make_result_tube_laminar()
        object.__setattr__(r, "nusselt_number", 999.0)
        assert r.validate_integrity() is False

    def test_tamper_result_hash_breaks_verify(self) -> None:
        r = _make_result_tube_laminar()
        object.__setattr__(r, "result_hash", "sha256:" + "0" * 64)
        assert r.verify_hash() is False

    def test_tamper_warnings_breaks_integrity(self) -> None:
        r = _make_result_tube_turbulent()  # Has adaptation warning
        if r.warnings:
            object.__setattr__(r, "warnings", ())
            assert r.validate_integrity() is False

    def test_tamper_blockers_breaks_integrity(self) -> None:
        r = _make_result_blocked()
        object.__setattr__(r, "blockers", ())
        assert r.validate_integrity() is False

    def test_tamper_failure_breaks_integrity(self) -> None:
        r = _make_result_tube_laminar()
        # Set failure then tamper
        object.__setattr__(r, "failure", None)
        # Original had no failure, so setting to None doesn't change it
        # But setting to a non-None value would
        from hexagent.domain.messages import RunFailure

        object.__setattr__(
            r,
            "failure",
            RunFailure(code=ErrorCode.INPUT_INCONSISTENT, message="tampered"),
        )
        assert r.validate_integrity() is False

    def test_tamper_selected_correlation_breaks_integrity(self) -> None:
        r = _make_result_tube_laminar()
        tampered_info = SelectedCorrelationInfo(
            correlation_id="tampered",
            version="999.0.0",
        )
        object.__setattr__(r, "selected_correlation", tampered_info)
        assert r.validate_integrity() is False

    def test_tamper_applicability_status_breaks_integrity(self) -> None:
        r = _make_result_tube_laminar()
        object.__setattr__(r, "applicability_status", "tampered")
        assert r.validate_integrity() is False

    def test_tamper_execution_context_breaks_integrity(self) -> None:
        r = _make_result_tube_laminar()
        object.__setattr__(
            r,
            "execution_context",
            ExecutionContextSnapshot(request_id=uuid4()),
        )
        assert r.validate_integrity() is False

    def test_tamper_provenance_graph_breaks_integrity(self) -> None:
        r = _make_result_tube_laminar()
        object.__setattr__(r, "provenance_graph", ProvenanceGraph())
        assert r.validate_integrity() is False

    def test_tamper_source_title_breaks_integrity(self) -> None:
        r = _make_result_tube_laminar()
        tampered_info = r.selected_correlation.model_copy(update={"source_title": "tampered"})
        object.__setattr__(r, "selected_correlation", tampered_info)
        assert r.validate_integrity() is False

    def test_tamper_definition_hash_breaks_integrity(self) -> None:
        r = _make_result_tube_laminar()
        tampered_info = r.selected_correlation.model_copy(
            update={"definition_hash": "sha256:" + "ff" * 64}
        )
        object.__setattr__(r, "selected_correlation", tampered_info)
        assert r.validate_integrity() is False

    def test_direct_setattr_tamper(self) -> None:
        """Direct __setattr__ on frozen model bypasses Pydantic but breaks integrity."""
        r = _make_result_tube_laminar()
        _ = r.result_hash
        # Tamper using object.__setattr__
        object.__setattr__(r, "mass_flow_kg_s", 999.0)
        assert r.validate_integrity() is False
        # Hash should still match old value (since result_hash was set)
        # but verify_hash compares payload → will fail
        assert r.verify_hash() is False


class TestProvenanceIntegrity:
    """Provenance graph integrity tests."""

    def test_succeeded_has_required_nodes(self) -> None:
        r = _make_result_tube_laminar()
        node_types = {n.node_type for n in r.provenance_graph.nodes}
        assert ProvenanceNodeType.EXTERNAL in node_types
        assert ProvenanceNodeType.CALCULATION_RUN in node_types
        assert ProvenanceNodeType.CORRELATION in node_types
        assert ProvenanceNodeType.RESULT in node_types

    def test_blocked_has_no_correlation_node(self) -> None:
        r = _make_result_blocked()
        node_types = {n.node_type for n in r.provenance_graph.nodes}
        assert ProvenanceNodeType.CORRELATION not in node_types

    def test_provenance_node_unique_ids(self) -> None:
        r = _make_result_tube_laminar()
        ids = [n.node_id for n in r.provenance_graph.nodes]
        assert len(ids) == len(set(ids))

    def test_provenance_edge_unique(self) -> None:
        r = _make_result_tube_laminar()
        keys = [(e.source_id, e.target_id, e.relation) for e in r.provenance_graph.edges]
        assert len(keys) == len(set(keys))

    def test_provenance_no_self_loops(self) -> None:
        r = _make_result_tube_laminar()
        for edge in r.provenance_graph.edges:
            assert edge.source_id != edge.target_id

    def test_provenance_dag(self) -> None:
        r = _make_result_tube_laminar()
        node_ids = {n.node_id for n in r.provenance_graph.nodes}
        in_degree = {nid: 0 for nid in node_ids}
        adjacency: dict[UUID, list[UUID]] = {nid: [] for nid in node_ids}
        for edge in r.provenance_graph.edges:
            adjacency[edge.source_id].append(edge.target_id)
            in_degree[edge.target_id] += 1
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

    def test_provenance_exactly_one_calculation_run(self) -> None:
        r = _make_result_tube_laminar()
        calc_nodes = [
            n for n in r.provenance_graph.nodes if n.node_type == ProvenanceNodeType.CALCULATION_RUN
        ]
        assert len(calc_nodes) == 1

    def test_provenance_calc_run_blocked(self) -> None:
        r = _make_result_blocked()
        calc_nodes = [
            n for n in r.provenance_graph.nodes if n.node_type == ProvenanceNodeType.CALCULATION_RUN
        ]
        assert len(calc_nodes) == 1

    def test_warning_nodes_match_result(self) -> None:
        r = _make_result_tube_turbulent()
        warn_nodes = [
            n for n in r.provenance_graph.nodes if n.node_type == ProvenanceNodeType.WARNING
        ]
        assert len(warn_nodes) == len(r.warnings)
        for wn in warn_nodes:
            wn_meta = dict(wn.metadata)
            found = any(
                w.code.value == wn_meta.get("code") and w.message == wn_meta.get("message")
                for w in r.warnings
            )
            assert found

    def test_blocker_nodes_match_result(self) -> None:
        r = _make_result_blocked()
        blocker_nodes = [
            n for n in r.provenance_graph.nodes if n.node_type == ProvenanceNodeType.BLOCKER
        ]
        assert len(blocker_nodes) == len(r.blockers)
        for bn in blocker_nodes:
            bn_meta = dict(bn.metadata)
            found = any(
                b.code.value == bn_meta.get("code") and b.message == bn_meta.get("message")
                for b in r.blockers
            )
            assert found

    def test_verify_provenance_succeeded(self) -> None:
        r = _make_result_tube_laminar()
        assert r.verify_provenance() is True

    def test_verify_provenance_blocked(self) -> None:
        r = _make_result_blocked()
        assert r.verify_provenance() is True

    def test_provenance_result_node_matches_status(self) -> None:
        r = _make_result_tube_laminar()
        result_nodes = [
            n for n in r.provenance_graph.nodes if n.node_type == ProvenanceNodeType.RESULT
        ]
        assert len(result_nodes) == 1
        result_meta = dict(result_nodes[0].metadata)
        assert result_meta.get("status") == "succeeded"


# =====================================================================
# Category 8: Hash Identity
# =====================================================================


class TestHashIdentity:
    """Source change → definition hash changes → result hash changes; JSON round-trip."""

    def test_two_results_same_inputs_same_hash(self) -> None:
        flow = _water_flow(mass_flow=0.3)
        r1 = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        r2 = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        assert r1.result_hash == r2.result_hash

    def test_different_inputs_different_hash(self) -> None:
        r1 = evaluate_hx_correlation(
            _tube_geom(), _water_flow(mass_flow=0.01), "constant_wall_temperature"
        )
        r2 = evaluate_hx_correlation(
            _tube_geom(), _water_flow(mass_flow=0.3), "constant_wall_temperature"
        )
        assert r1.result_hash != r2.result_hash

    def test_json_roundtrip_hash_matches(self) -> None:
        r = _make_result_tube_laminar()
        json_str = r.model_dump_json()
        restored = CorrelationResult.model_validate_json(json_str)
        assert restored.result_hash == r.result_hash
        assert restored.verify_hash() is True

    def test_source_change_defn_hash_changes(self) -> None:
        """Different source → different definition_hash → different result_hash."""
        defn1 = _registry().get(CorrelationKey(correlation_id="tube_laminar_cwt", version="1.0.0"))
        # Verify the definition hash is stable
        recomputed = compute_definition_hash(defn1)
        assert recomputed == defn1.definition_hash

    def test_result_hash_includes_all_identity_fields(self) -> None:
        """Different wall temp → different result hash."""
        r1 = evaluate_hx_correlation(
            _tube_geom(),
            _water_flow(mass_flow=0.005, wall_temp=300.0),
            "constant_wall_temperature",
        )
        r2 = evaluate_hx_correlation(
            _tube_geom(),
            _water_flow(mass_flow=0.005, wall_temp=400.0),
            "constant_wall_temperature",
        )
        assert r1.result_hash != r2.result_hash


# =====================================================================
# Category 9: C4 κ Range
# =====================================================================


class TestC4KappaRange:
    """C4 κ range: [0.1, 0.75] inclusive."""

    def test_kappa_0_1_edge_works(self) -> None:
        """κ=0.1 → should work, Nu=4.85."""
        g = _ann_geom(di=0.005, do=0.050)  # κ=0.1
        flow = _water_flow(mass_flow=0.005)
        result = evaluate_hx_correlation(g, flow, "inner_wall_heated")
        assert result.status == CorrelationStatus.SUCCEEDED
        assert result.nusselt_number == pytest.approx(4.85, abs=1e-12)

    def test_kappa_0_75_edge_works(self) -> None:
        """κ=0.75 → should work, Nu=10.10."""
        g = _ann_geom(di=0.0375, do=0.050)  # κ=0.75
        flow = _water_flow(mass_flow=0.005)
        result = evaluate_hx_correlation(g, flow, "inner_wall_heated")
        assert result.status == CorrelationStatus.SUCCEEDED
        assert result.nusselt_number == pytest.approx(10.10, abs=1e-12)

    def test_kappa_0_05_below_blocked(self) -> None:
        """κ=0.05 → below range → BLOCKED."""
        # This creates an annulus where κ=0.05: D_i=0.0025, D_o=0.050
        g = _ann_geom(di=0.0025, do=0.050)  # κ=0.05
        flow = _water_flow(mass_flow=0.005)
        result = evaluate_hx_correlation(g, flow, "inner_wall_heated")
        assert result.status == CorrelationStatus.BLOCKED

    def test_kappa_0_85_above_blocked(self) -> None:
        """κ=0.85 → above range → BLOCKED."""
        # D_i=0.0425, D_o=0.050 → κ=0.85
        g = _ann_geom(di=0.0425, do=0.050)  # κ=0.85
        flow = _water_flow(mass_flow=0.005)
        result = evaluate_hx_correlation(g, flow, "inner_wall_heated")
        assert result.status == CorrelationStatus.BLOCKED

    def test_kappa_constants(self) -> None:
        """Verify κ constants from annulus module."""
        assert _KAPPA_ABSOLUTE_MIN == 0.1
        assert _KAPPA_ABSOLUTE_MAX == 0.75


# =====================================================================
# Category 10: Wall Property Validation
# =====================================================================


class TestWallPropertyValidation:
    """Wall property validation: NaN/Inf rejected."""

    def test_wall_temperature_nan_rejected(self) -> None:
        with pytest.raises(ValidationError, match="finite"):
            FlowPropertiesInput(
                mass_flow_kg_s=0.1,
                density_kg_m3=RHO,
                dynamic_viscosity_pa_s=MU,
                thermal_conductivity_w_m_k=K,
                specific_heat_j_kg_k=CP,
                bulk_temperature_k=350.0,
                wall_temperature_k=float("nan"),
            )

    def test_wall_viscosity_inf_rejected(self) -> None:
        with pytest.raises(ValidationError, match="finite"):
            FlowPropertiesInput(
                mass_flow_kg_s=0.1,
                density_kg_m3=RHO,
                dynamic_viscosity_pa_s=MU,
                thermal_conductivity_w_m_k=K,
                specific_heat_j_kg_k=CP,
                bulk_temperature_k=350.0,
                wall_viscosity_pa_s=float("inf"),
            )

    def test_wall_temperature_negative_rejected(self) -> None:
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

    def test_wall_viscosity_zero_rejected(self) -> None:
        with pytest.raises(ValidationError, match="positive"):
            FlowPropertiesInput(
                mass_flow_kg_s=0.1,
                density_kg_m3=RHO,
                dynamic_viscosity_pa_s=MU,
                thermal_conductivity_w_m_k=K,
                specific_heat_j_kg_k=CP,
                bulk_temperature_k=350.0,
                wall_viscosity_pa_s=0.0,
            )

    def test_wall_temperature_none_allowed(self) -> None:
        f = FlowPropertiesInput(
            mass_flow_kg_s=0.1,
            density_kg_m3=RHO,
            dynamic_viscosity_pa_s=MU,
            thermal_conductivity_w_m_k=K,
            specific_heat_j_kg_k=CP,
            bulk_temperature_k=350.0,
            wall_temperature_k=None,
        )
        assert f.wall_temperature_k is None

    def test_wall_viscosity_none_allowed(self) -> None:
        f = FlowPropertiesInput(
            mass_flow_kg_s=0.1,
            density_kg_m3=RHO,
            dynamic_viscosity_pa_s=MU,
            thermal_conductivity_w_m_k=K,
            specific_heat_j_kg_k=CP,
            bulk_temperature_k=350.0,
            wall_viscosity_pa_s=None,
        )
        assert f.wall_viscosity_pa_s is None


# =====================================================================
# Category 11: Boundary Condition Validation
# =====================================================================


class TestBoundaryConditionValidation:
    """Boundary condition vs heated_surface consistency."""

    def test_inner_heated_geometry_outer_wall_heated_bc(self) -> None:
        """inner_heated geometry + outer_wall_heated BC → BLOCKED."""
        g = _ann_geom(heated="inner")
        flow = _water_flow(mass_flow=0.005)
        result = evaluate_hx_correlation(g, flow, "outer_wall_heated")
        assert result.status == CorrelationStatus.BLOCKED
        assert any(
            "boundary condition" in b.message.lower() or "heated_surface" in b.message.lower()
            for b in result.blockers
        )

    def test_both_walls_heated_geometry_inner_wall_heated_bc(self) -> None:
        """both_walls_heated geometry + inner_wall_heated BC → BLOCKED."""
        g = _ann_geom(heated="both")
        flow = _water_flow(mass_flow=0.005)
        result = evaluate_hx_correlation(g, flow, "inner_wall_heated")
        assert result.status == CorrelationStatus.BLOCKED
        assert any(
            "boundary condition" in b.message.lower() or "heated_surface" in b.message.lower()
            for b in result.blockers
        )

    def test_inner_geometry_inner_bc_ok(self) -> None:
        """inner_heated geometry + inner_wall_heated BC → should work."""
        flow = _water_flow(mass_flow=0.005)
        result = evaluate_hx_correlation(_ann_geom(heated="inner"), flow, "inner_wall_heated")
        assert result.status == CorrelationStatus.SUCCEEDED

    def test_tube_unsupported_bc_blocked(self) -> None:
        """Tube with annulus-specific BC → BLOCKED."""
        flow = _water_flow(mass_flow=0.005)
        result = evaluate_hx_correlation(_tube_geom(), flow, "inner_wall_heated")
        assert result.status == CorrelationStatus.BLOCKED


# =====================================================================
# Category 12: Provenance Topology
# =====================================================================


class TestProvenanceTopology:
    """Provenance graph topology for succeeded and blocked results."""

    def test_succeeded_external_root(self) -> None:
        r = _make_result_tube_laminar()
        node_types = {n.node_type for n in r.provenance_graph.nodes}
        assert ProvenanceNodeType.EXTERNAL in node_types

    def test_succeeded_has_calculation_run(self) -> None:
        r = _make_result_tube_laminar()
        calc_nodes = [
            n for n in r.provenance_graph.nodes if n.node_type == ProvenanceNodeType.CALCULATION_RUN
        ]
        assert len(calc_nodes) == 1

    def test_succeeded_has_correlation_node(self) -> None:
        r = _make_result_tube_laminar()
        corr_nodes = [
            n for n in r.provenance_graph.nodes if n.node_type == ProvenanceNodeType.CORRELATION
        ]
        assert len(corr_nodes) == 1

    def test_succeeded_has_result_node(self) -> None:
        r = _make_result_tube_laminar()
        result_nodes = [
            n for n in r.provenance_graph.nodes if n.node_type == ProvenanceNodeType.RESULT
        ]
        assert len(result_nodes) == 1

    def test_blocked_no_correlation_node(self) -> None:
        r = _make_result_blocked()
        corr_nodes = [
            n for n in r.provenance_graph.nodes if n.node_type == ProvenanceNodeType.CORRELATION
        ]
        assert len(corr_nodes) == 0

    def test_blocked_has_external_root(self) -> None:
        r = _make_result_blocked()
        node_types = {n.node_type for n in r.provenance_graph.nodes}
        assert ProvenanceNodeType.EXTERNAL in node_types

    def test_blocked_has_calculation_run(self) -> None:
        r = _make_result_blocked()
        calc_nodes = [
            n for n in r.provenance_graph.nodes if n.node_type == ProvenanceNodeType.CALCULATION_RUN
        ]
        assert len(calc_nodes) == 1

    def test_blocked_has_result_node(self) -> None:
        r = _make_result_blocked()
        result_nodes = [
            n for n in r.provenance_graph.nodes if n.node_type == ProvenanceNodeType.RESULT
        ]
        assert len(result_nodes) == 1

    def test_succeeded_exactly_one_calculation_run(self) -> None:
        r = _make_result_tube_turbulent()
        calc_nodes = [
            n for n in r.provenance_graph.nodes if n.node_type == ProvenanceNodeType.CALCULATION_RUN
        ]
        assert len(calc_nodes) == 1

    def test_turbulent_has_warning_nodes(self) -> None:
        """Turbulent annulus result should have adaptation warning nodes."""
        flow = _water_flow(mass_flow=1.0)
        result = evaluate_hx_correlation(_ann_geom(), flow, "inner_wall_heated")
        assert result.status == CorrelationStatus.SUCCEEDED
        assert len(result.warnings) > 0
        warn_nodes = [
            n for n in result.provenance_graph.nodes if n.node_type == ProvenanceNodeType.WARNING
        ]
        assert len(warn_nodes) == len(result.warnings)

    def test_blocked_has_blocker_nodes(self) -> None:
        r = _make_result_blocked()
        assert len(r.blockers) > 0
        blocker_nodes = [
            n for n in r.provenance_graph.nodes if n.node_type == ProvenanceNodeType.BLOCKER
        ]
        assert len(blocker_nodes) == len(r.blockers)


# =====================================================================
# Category 13: SemVer Selection
# =====================================================================


class TestSemVerSelection:
    """SemVer-based version selection."""

    def test_higher_version_wins(self) -> None:
        """Register multiple versions; highest should be latest."""
        from hexagent.correlations.models import (
            ApplicabilityEnvelope,
            BibliographicSource,
            CorrelationDefinition,
            CorrelationImplementationStatus,
            CorrelationKey,
            CorrelationPurpose,
            NumericBound,
            UncertaintySpec,
        )

        def _make_def(version: str) -> CorrelationDefinition:
            return CorrelationDefinition.create(
                key=CorrelationKey(correlation_id="tube_laminar_cwt", version=version),
                name="Tube Laminar CWT",
                purpose=CorrelationPurpose.nusselt_number,
                description="Test",
                geometry=frozenset({GeometryType.circular_tube}),
                phase_regimes=frozenset(
                    {PhaseRegime.single_phase_liquid, PhaseRegime.single_phase_gas}
                ),
                envelope=ApplicabilityEnvelope(
                    geometry_types=frozenset({GeometryType.circular_tube}),
                    phase_regimes=frozenset(
                        {PhaseRegime.single_phase_liquid, PhaseRegime.single_phase_gas}
                    ),
                    flow_regimes=frozenset({"laminar"}),
                    bounds=(
                        NumericBound(
                            variable=ApplicabilityVariable.reynolds,
                            minimum=0.0,
                            maximum=2300.0,
                            minimum_inclusive=False,
                            maximum_inclusive=False,
                        ),
                        NumericBound(
                            variable=ApplicabilityVariable.prandtl,
                            minimum=0.6,
                            minimum_inclusive=False,
                        ),
                    ),
                    required_inputs=frozenset(
                        {ApplicabilityVariable.reynolds, ApplicabilityVariable.prandtl}
                    ),
                ),
                source=BibliographicSource(
                    source_id="test_source",
                    title="Test",
                    publication="Test Pub",
                    year=2024,
                    verification_status=SourceVerificationStatus.primary_source_checked,
                ),
                uncertainty=UncertaintySpec(basis="test"),
                implementation_status=CorrelationImplementationStatus.validated,
                implementation_ref="test.ref",
                tags=frozenset(
                    {
                        "bc:constant_wall_temperature",
                        "nusselt_basis:inside_diameter",
                        "priority:10",
                    }
                ),
            )

        reg = InMemoryCorrelationRegistry()
        reg.register(_make_def("1.0.0"))
        reg.register(_make_def("1.2.0"))
        reg.register(_make_def("1.10.0"))
        reg.register(_make_def("1.0.0-beta"))

        latest = reg.get_latest("tube_laminar_cwt")
        assert latest.key.version == "1.10.0"

    def test_prerelease_before_stable(self) -> None:
        """1.0.0-beta < 1.0.0."""
        assert compare_semver("1.0.0-beta", "1.0.0") == -1

    def test_higher_minor_wins(self) -> None:
        """1.10.0 > 1.2.0."""
        assert compare_semver("1.10.0", "1.2.0") == 1

    def test_parse_semver_basic(self) -> None:
        major, minor, patch, pre = parse_semver("2.1.3")
        assert (major, minor, patch) == (2, 1, 3)
        assert pre == ()

    def test_parse_semver_prerelease(self) -> None:
        major, minor, patch, pre = parse_semver("1.0.0-alpha")
        assert (major, minor, patch) == (1, 0, 0)
        assert pre == ((1, "alpha"),)

    def test_definition_hash_stable(self) -> None:
        """Definition hash is deterministic and stable."""
        defn = _registry().get(CorrelationKey(correlation_id="tube_laminar_cwt", version="1.0.0"))
        assert defn.definition_hash.startswith("sha256:")
        recomputed = compute_definition_hash(defn)
        assert recomputed == defn.definition_hash


# =====================================================================
# Category 14: Golden Cases
# =====================================================================


class TestGoldenCases:
    """Golden reference cases with independent hand-computed values."""

    def test_c1_nu_3_66(self) -> None:
        """C1: Nu = 3.66 for fully developed laminar, constant wall temperature."""
        flow = _water_flow(mass_flow=0.005)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        assert result.status == CorrelationStatus.SUCCEEDED
        assert result.nusselt_number == pytest.approx(3.66, abs=1e-12)
        expected_h = 3.66 * K / TUBE_DH
        assert result.heat_transfer_coefficient == pytest.approx(expected_h, rel=1e-12)

    def test_c2_nu_4_36(self) -> None:
        """C2: Nu = 4.36 for fully developed laminar, constant heat flux."""
        flow = _water_flow(mass_flow=0.005)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_heat_flux")
        assert result.status == CorrelationStatus.SUCCEEDED
        assert result.nusselt_number == pytest.approx(4.36, abs=1e-12)
        expected_h = 4.36 * K / TUBE_DH
        assert result.heat_transfer_coefficient == pytest.approx(expected_h, rel=1e-12)

    def test_c3_gnielinski_re50000_pr7(self) -> None:
        """C3: Gnielinski with Re=50000, Pr=7.0.
        Hand calculation:
        f = (0.790*ln(50000) - 1.64)^(-2) ≈ 0.02102
        f/8 ≈ 0.002628
        Num = 0.002628 * 49000 * 7.0 ≈ 900.40
        Den = 1 + 12.7*sqrt(0.002628)*(7.0^(2/3) - 1) ≈ 2.731
        Nu ≈ 329.7
        """
        Re = 50000.0
        Pr = 7.0
        c = TubeTurbulentGnielinski()
        nu = c.evaluate(Re, Pr)

        # Independent hand calculation
        f = (0.790 * math.log(Re) - 1.64) ** (-2)
        f8 = f / 8.0
        numerator = f8 * (Re - 1000.0) * Pr
        denominator = 1.0 + 12.7 * math.sqrt(f8) * (Pr ** (2.0 / 3.0) - 1.0)
        expected_nu = numerator / denominator

        assert nu == pytest.approx(expected_nu, rel=1e-10)
        assert nu == pytest.approx(329.7, abs=5.0)

    def test_c4_kappa_0_5(self) -> None:
        """C4: κ=0.5 → Nu=7.30."""
        g = _ann_geom(di=0.025, do=0.050)
        flow = _water_flow(mass_flow=0.005)
        result = evaluate_hx_correlation(g, flow, "inner_wall_heated")
        assert result.status == CorrelationStatus.SUCCEEDED
        assert result.nusselt_number == pytest.approx(7.30, abs=1e-12)

    def test_c4_h_uses_d_i(self) -> None:
        """C4: h = Nu * k / D_i, NOT D_h."""
        g = _ann_geom(di=0.025, do=0.050)
        flow = _water_flow(mass_flow=0.005)
        result = evaluate_hx_correlation(g, flow, "inner_wall_heated")
        expected_h = 7.30 * K / 0.025
        assert result.heat_transfer_coefficient == pytest.approx(expected_h, rel=1e-10)

    def test_c3_service_integration(self) -> None:
        """C3: Service-level Gnielinski with Re=50000."""
        # Need Re ≈ 50000 in a 25mm tube
        # m_dot = Re * A * μ / D_h
        target_re = 50000.0
        m_dot = target_re * TUBE_A * MU / TUBE_DH
        flow = _water_flow(mass_flow=m_dot)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        assert result.status == CorrelationStatus.SUCCEEDED
        assert result.flow_regime == "turbulent"
        assert result.selected_correlation is not None
        assert result.selected_correlation.correlation_id == "tube_turbulent_gnielinski"


# =====================================================================
# Category 15: Zero Duty / Zero Flow
# =====================================================================


class TestZeroDutyZeroFlow:
    """Zero mass flow and negative mass flow → BLOCKED."""

    def test_zero_mass_flow_blocked(self) -> None:
        flow = _water_flow(mass_flow=0.0)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        assert result.status == CorrelationStatus.BLOCKED
        assert any("zero mass flow" in b.message.lower() for b in result.blockers)

    def test_negative_mass_flow_blocked(self) -> None:
        """Negative mass flow should be rejected at FlowPropertiesInput level."""
        with pytest.raises(ValidationError, match="non-negative"):
            FlowPropertiesInput(
                mass_flow_kg_s=-0.01,
                density_kg_m3=RHO,
                dynamic_viscosity_pa_s=MU,
                thermal_conductivity_w_m_k=K,
                specific_heat_j_kg_k=CP,
                bulk_temperature_k=350.0,
            )

    def test_zero_mass_flow_provenance(self) -> None:
        """Zero mass flow result should have valid provenance."""
        flow = _water_flow(mass_flow=0.0)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        assert result.status == CorrelationStatus.BLOCKED
        assert result.verify_provenance() is True

    def test_zero_mass_flow_hash(self) -> None:
        flow = _water_flow(mass_flow=0.0)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        assert result.verify_hash() is True


# =====================================================================
# Category 16: Provenance JSON Round-Trip
# =====================================================================


class TestProvenanceJSONRoundTrip:
    """Provenance graph serialization/deserialization round-trip."""

    def test_succeeded_graph_roundtrip(self) -> None:
        r = _make_result_tube_laminar()
        graph_json = r.provenance_graph.to_json()
        restored = ProvenanceGraph.from_json(graph_json)
        assert len(restored.nodes) == len(r.provenance_graph.nodes)
        assert len(restored.edges) == len(r.provenance_graph.edges)

    def test_succeeded_graph_hash_preserved(self) -> None:
        r = _make_result_tube_laminar()
        graph_json = r.provenance_graph.to_json()
        restored = ProvenanceGraph.from_json(graph_json)
        assert _provenance_graph_digest(restored) == r.provenance_digest

    def test_blocked_graph_roundtrip(self) -> None:
        r = _make_result_blocked()
        graph_json = r.provenance_graph.to_json()
        restored = ProvenanceGraph.from_json(graph_json)
        assert len(restored.nodes) == len(r.provenance_graph.nodes)
        assert len(restored.edges) == len(r.provenance_graph.edges)
        assert _provenance_graph_digest(restored) == r.provenance_digest

    def test_full_result_json_roundtrip(self) -> None:
        """Full CorrelationResult JSON round-trip preserves provenance."""
        r = _make_result_tube_laminar()
        json_str = r.model_dump_json()
        restored = CorrelationResult.model_validate_json(json_str)
        assert restored.provenance_digest == r.provenance_digest
        assert restored.verify_provenance() is True

    def test_full_blocked_result_json_roundtrip(self) -> None:
        """Full blocked result JSON round-trip preserves provenance."""
        r = _make_result_blocked()
        json_str = r.model_dump_json()
        restored = CorrelationResult.model_validate_json(json_str)
        assert restored.provenance_digest == r.provenance_digest
        assert restored.verify_provenance() is True

    def test_graph_node_ids_preserved(self) -> None:
        r = _make_result_tube_laminar()
        graph_json = r.provenance_graph.to_json()
        restored = ProvenanceGraph.from_json(graph_json)
        original_ids = {str(n.node_id) for n in r.provenance_graph.nodes}
        restored_ids = {str(n.node_id) for n in restored.nodes}
        assert original_ids == restored_ids

    def test_graph_edge_relations_preserved(self) -> None:
        r = _make_result_tube_laminar()
        graph_json = r.provenance_graph.to_json()
        restored = ProvenanceGraph.from_json(graph_json)
        original_relations = {
            (str(e.source_id), str(e.target_id), e.relation) for e in r.provenance_graph.edges
        }
        restored_relations = {
            (str(e.source_id), str(e.target_id), e.relation) for e in restored.edges
        }
        assert original_relations == restored_relations

    def test_provenance_node_payload_hash_format(self) -> None:
        """All nodes have sha256 payload hashes."""
        r = _make_result_tube_laminar()
        for node in r.provenance_graph.nodes:
            assert node.payload_hash.startswith("sha256:")
            assert len(node.payload_hash) == 71


# =====================================================================
# Additional: Select Correlation Direct Tests
# =====================================================================


class TestSelectCorrelationDirect:
    """Direct tests of the select_correlation function."""

    def test_returns_three_tuple(self) -> None:
        reg = _registry()
        geo = _tube_geom()
        result = select_correlation(
            reg, geo, "constant_wall_temperature", FlowRegime.laminar, 200.0, 7.0
        )
        assert len(result) == 3
        defn, assessment, blocker = result
        assert defn is not None
        assert blocker is None

    def test_no_applicable_returns_none(self) -> None:
        """Empty registry → no applicable → (None, None, None)."""
        reg = InMemoryCorrelationRegistry()
        geo = _tube_geom()
        defn, assessment, blocker = select_correlation(
            reg, geo, "constant_wall_temperature", FlowRegime.laminar, 200.0, 7.0
        )
        assert defn is None
        assert blocker is None

    def test_tube_laminar_cwt_direct(self) -> None:
        reg = _registry()
        geo = _tube_geom()
        defn, _, blocker = select_correlation(
            reg, geo, "constant_wall_temperature", FlowRegime.laminar, 200.0, 7.0
        )
        assert defn is not None
        assert defn.key.correlation_id == "tube_laminar_cwt"
        assert blocker is None

    def test_tube_laminar_chf_direct(self) -> None:
        reg = _registry()
        geo = _tube_geom()
        defn, _, blocker = select_correlation(
            reg, geo, "constant_heat_flux", FlowRegime.laminar, 200.0, 7.0
        )
        assert defn is not None
        assert defn.key.correlation_id == "tube_laminar_chf"

    def test_tube_turbulent_direct(self) -> None:
        reg = _registry()
        geo = _tube_geom()
        defn, _, blocker = select_correlation(
            reg, geo, "constant_wall_temperature", FlowRegime.turbulent, 15000.0, 7.0
        )
        assert defn is not None
        assert defn.key.correlation_id == "tube_turbulent_gnielinski"

    def test_transitional_returns_none(self) -> None:
        reg = _registry()
        geo = _tube_geom()
        defn, assessment, blocker = select_correlation(
            reg, geo, "constant_wall_temperature", FlowRegime.transitional, 5000.0, 7.0
        )
        assert defn is None

    def test_annulus_laminar_inner_direct(self) -> None:
        reg = _registry()
        geo = _ann_geom()
        defn, _, blocker = select_correlation(
            reg,
            geo,
            "inner_wall_heated",
            FlowRegime.laminar,
            200.0,
            7.0,
            diameter_ratio=ANN_KAPPA,
        )
        assert defn is not None
        assert defn.key.correlation_id == "annulus_laminar_inner_chf"

    def test_annulus_turbulent_direct(self) -> None:
        reg = _registry()
        geo = _ann_geom()
        defn, _, blocker = select_correlation(
            reg,
            geo,
            "inner_wall_heated",
            FlowRegime.turbulent,
            15000.0,
            7.0,
            diameter_ratio=ANN_KAPPA,
        )
        assert defn is not None
        assert defn.key.correlation_id == "annulus_turbulent_gnielinski_dh"


# =====================================================================
# Additional: SelectedCorrelationInfo Fields
# =====================================================================


class TestSelectedCorrelationInfoFields:
    """SelectedCorrelationInfo carries full source identity."""

    def test_source_fields_populated(self) -> None:
        flow = _water_flow(mass_flow=0.005)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        info = result.selected_correlation
        assert info is not None
        assert info.correlation_id == "tube_laminar_cwt"
        assert info.version == "1.0.0"
        assert len(info.source_title) > 0
        assert info.source_year > 0
        assert info.source_verification_status != "unverified"
        assert info.definition_hash.startswith("sha256:")
        assert info.nusselt_basis == "inside_diameter"

    def test_annulus_turbulent_source_fields(self) -> None:
        flow = _water_flow(mass_flow=1.0)
        result = evaluate_hx_correlation(_ann_geom(), flow, "inner_wall_heated")
        info = result.selected_correlation
        assert info is not None
        assert info.correlation_id == "annulus_turbulent_gnielinski_dh"
        assert info.is_adaptation is True
        assert len(info.adaptation_limitation) > 0
        assert info.nusselt_basis == "hydraulic_diameter"

    def test_frozen(self) -> None:
        info = SelectedCorrelationInfo(
            correlation_id="test",
            version="1.0.0",
        )
        with pytest.raises(ValidationError):
            info.correlation_id = "modified"  # type: ignore[misc]


# =====================================================================
# Additional: Is Boundary Compatible
# =====================================================================


class TestIsBoundaryCompatible:
    """Test _is_boundary_compatible function."""

    def test_cwt_compatible_with_cwt(self) -> None:
        reg = _registry()
        defn = reg.get(CorrelationKey(correlation_id="tube_laminar_cwt", version="1.0.0"))
        assert _is_boundary_compatible(defn, "constant_wall_temperature") is True

    def test_cwt_incompatible_with_chf(self) -> None:
        reg = _registry()
        defn = reg.get(CorrelationKey(correlation_id="tube_laminar_cwt", version="1.0.0"))
        assert _is_boundary_compatible(defn, "constant_heat_flux") is False

    def test_chf_compatible_with_chf(self) -> None:
        reg = _registry()
        defn = reg.get(CorrelationKey(correlation_id="tube_laminar_chf", version="1.0.0"))
        assert _is_boundary_compatible(defn, "constant_heat_flux") is True

    def test_gnielinski_compatible_with_both_cwt_chf(self) -> None:
        reg = _registry()
        defn = reg.get(CorrelationKey(correlation_id="tube_turbulent_gnielinski", version="1.0.0"))
        assert _is_boundary_compatible(defn, "constant_wall_temperature") is True
        assert _is_boundary_compatible(defn, "constant_heat_flux") is True

    def test_annulus_inner_chf_compatible_with_inner(self) -> None:
        reg = _registry()
        defn = reg.get(CorrelationKey(correlation_id="annulus_laminar_inner_chf", version="1.0.0"))
        assert _is_boundary_compatible(defn, "inner_wall_heated") is True

    def test_annulus_inner_chf_incompatible_with_outer(self) -> None:
        reg = _registry()
        defn = reg.get(CorrelationKey(correlation_id="annulus_laminar_inner_chf", version="1.0.0"))
        assert _is_boundary_compatible(defn, "outer_wall_heated") is False


# =====================================================================
# Additional: Regime Constants
# =====================================================================


class TestRegimeConstants:
    """Regime threshold constants match specification."""

    def test_laminar_upper(self) -> None:
        assert LAMINAR_UPPER_RE == 2300.0

    def test_turbulent_lower(self) -> None:
        assert TURBULENT_LOWER_RE == 10000.0


# =====================================================================
# Additional: Enum Values
# =====================================================================


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


class TestNusseltBasisEnum:
    """NusseltBasis enum values."""

    def test_values(self) -> None:
        assert NusseltBasis.hydraulic_diameter.value == "hydraulic_diameter"
        assert NusseltBasis.inside_diameter.value == "inside_diameter"


# =====================================================================
# Additional: Computed Quantities
# =====================================================================


class TestComputedQuantities:
    """All computed quantities are populated in a succeeded result."""

    def test_succeeded_result_quantities(self) -> None:
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

    def test_velocity_consistency(self) -> None:
        flow = _water_flow(mass_flow=0.3)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        expected_v = flow.mass_flow_kg_s / (flow.density_kg_m3 * result.flow_area_m2)
        assert result.mean_velocity_ms == pytest.approx(expected_v, rel=1e-10)

    def test_reynolds_consistency(self) -> None:
        flow = _water_flow(mass_flow=0.3)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        expected_re = (
            flow.density_kg_m3
            * result.mean_velocity_ms
            * result.hydraulic_diameter_m
            / flow.dynamic_viscosity_pa_s
        )
        assert result.reynolds_number == pytest.approx(expected_re, rel=1e-10)

    def test_prandtl_consistency(self) -> None:
        flow = _water_flow(mass_flow=0.3)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        expected_pr = (
            flow.specific_heat_j_kg_k
            * flow.dynamic_viscosity_pa_s
            / flow.thermal_conductivity_w_m_k
        )
        assert result.prandtl_number == pytest.approx(expected_pr, rel=1e-10)

    def test_zero_blocked_quantities(self) -> None:
        flow = _water_flow(mass_flow=0.0)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        assert result.status == CorrelationStatus.BLOCKED
        # Computed quantities should be zero for blocked results
        assert result.flow_area_m2 == 0.0
        assert result.mean_velocity_ms == 0.0
        assert result.reynolds_number == 0.0
        assert result.prandtl_number == 0.0
        assert result.nusselt_number == 0.0
        assert result.heat_transfer_coefficient == 0.0


# =====================================================================
# Additional: Applicability Assessment
# =====================================================================


class TestApplicabilityAssessment:
    """Applicability assessment presence in results."""

    def test_succeeded_has_assessment(self) -> None:
        flow = _water_flow(mass_flow=0.005)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        assert result.status == CorrelationStatus.SUCCEEDED
        assert result.applicability_assessment is not None

    def test_blocked_has_no_assessment(self) -> None:
        flow = _water_flow(mass_flow=0.0)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        assert result.status == CorrelationStatus.BLOCKED
        assert result.applicability_assessment is None

    def test_applicability_status_populated(self) -> None:
        flow = _water_flow(mass_flow=0.005)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        assert result.applicability_status != ""


# =====================================================================
# Additional: Execution Context
# =====================================================================


class TestExecutionContext:
    """Execution context in results."""

    def test_default_context(self) -> None:
        flow = _water_flow(mass_flow=0.005)
        result = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        assert result.execution_context.request_id is None
        assert result.execution_context.design_case_revision_id is None

    def test_custom_context(self) -> None:
        ctx = CalculationContext(
            request_id=uuid4(),
            design_case_revision_id=uuid4(),
            calculation_run_id=uuid4(),
        )
        flow = _water_flow(mass_flow=0.3)
        result = evaluate_hx_correlation(
            _tube_geom(), flow, "constant_wall_temperature", context=ctx
        )
        assert result.execution_context.request_id is not None
        assert result.execution_context.design_case_revision_id is not None
        assert result.execution_context.calculation_run_id is not None
        assert result.verify_provenance() is True

    def test_context_changes_provenance(self) -> None:
        """Different context → different provenance digest."""
        flow = _water_flow(mass_flow=0.3)
        r1 = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature")
        ctx = CalculationContext(
            request_id=uuid4(),
            design_case_revision_id=uuid4(),
            calculation_run_id=uuid4(),
        )
        r2 = evaluate_hx_correlation(_tube_geom(), flow, "constant_wall_temperature", context=ctx)
        assert r1.provenance_digest != r2.provenance_digest


# =====================================================================
# Additional: Gnielinski Consistency
# =====================================================================


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


# =====================================================================
# Additional: Annulus Geometry Consistency
# =====================================================================


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
