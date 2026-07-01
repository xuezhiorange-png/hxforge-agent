"""Unit tests for DoublePipeGeometry model.

Covers construction, derived properties, validation, serialization,
and immutability of the double-pipe heat-exchanger geometry.
"""

from __future__ import annotations

import math

import pytest

from hexagent.exchangers.double_pipe.geometry import DoublePipeGeometry

pytestmark = pytest.mark.pure

# ---------------------------------------------------------------------------
# Canonical example geometry
# ---------------------------------------------------------------------------

_D_I = 0.020  # inner tube inner diameter [m]
_D_O = 0.025  # inner tube outer diameter [m]
_D_OUTER = 0.040  # outer pipe inner diameter [m]
_L = 3.0  # effective length [m]
_K = 50.0  # wall thermal conductivity [W/(m·K)]


def _make_geometry(**overrides) -> DoublePipeGeometry:
    """Return a valid geometry with the canonical example values."""
    defaults = dict(
        inner_tube_inner_diameter_m=_D_I,
        inner_tube_outer_diameter_m=_D_O,
        outer_pipe_inner_diameter_m=_D_OUTER,
        effective_length_m=_L,
        wall_thermal_conductivity_w_m_k=_K,
    )
    defaults.update(overrides)
    return DoublePipeGeometry(**defaults)


# ---------------------------------------------------------------------------
# 1. Valid geometry construction with all defaults
# ---------------------------------------------------------------------------


class TestConstruction:
    """Test that a valid geometry can be constructed with defaults."""

    def test_construction_with_required_fields_only(self):
        geo = _make_geometry()
        assert geo.inner_tube_inner_diameter_m == _D_I
        assert geo.inner_tube_outer_diameter_m == _D_O
        assert geo.outer_pipe_inner_diameter_m == _D_OUTER
        assert geo.effective_length_m == _L
        assert geo.wall_thermal_conductivity_w_m_k == _K

    def test_default_optional_fields_are_zero(self):
        geo = _make_geometry()
        assert geo.inner_surface_roughness_m == 0.0
        assert geo.annulus_surface_roughness_m == 0.0
        assert geo.inner_fouling_resistance_m2k_w == 0.0
        assert geo.outer_fouling_resistance_m2k_w == 0.0

    def test_construction_with_explicit_optional_fields(self):
        geo = _make_geometry(
            inner_surface_roughness_m=4.5e-6,
            annulus_surface_roughness_m=3.2e-6,
            inner_fouling_resistance_m2k_w=2e-4,
            outer_fouling_resistance_m2k_w=3e-4,
        )
        assert geo.inner_surface_roughness_m == 4.5e-6
        assert geo.annulus_surface_roughness_m == 3.2e-6
        assert geo.inner_fouling_resistance_m2k_w == 2e-4
        assert geo.outer_fouling_resistance_m2k_w == 3e-4


# ---------------------------------------------------------------------------
# 2-7. Derived property calculations (hand-verified)
# ---------------------------------------------------------------------------


class TestDerivedProperties:
    """Verify all computed properties against hand calculations."""

    @pytest.fixture()
    def geo(self) -> DoublePipeGeometry:
        return _make_geometry()

    def test_area_inner_m2(self, geo: DoublePipeGeometry):
        """area_inner_m2 = π × D_i × L = π × 0.020 × 3.0 = 0.06π"""
        expected = math.pi * _D_I * _L
        assert geo.area_inner_m2 == pytest.approx(expected, rel=1e-12)

    def test_area_outer_m2(self, geo: DoublePipeGeometry):
        """area_outer_m2 = π × D_o × L = π × 0.025 × 3.0 = 0.075π"""
        expected = math.pi * _D_O * _L
        assert geo.area_outer_m2 == pytest.approx(expected, rel=1e-12)

    def test_hydraulic_diameter_annulus_m(self, geo: DoublePipeGeometry):
        """hydraulic_diameter_annulus_m = D_outer - D_o = 0.040 - 0.025 = 0.015"""
        expected = _D_OUTER - _D_O
        assert geo.hydraulic_diameter_annulus_m == pytest.approx(expected, rel=1e-12)

    def test_flow_area_tube_m2(self, geo: DoublePipeGeometry):
        """flow_area_tube_m2 = π × (D_i / 2)² = π × 0.010²"""
        expected = math.pi * (_D_I / 2.0) ** 2
        assert geo.flow_area_tube_m2 == pytest.approx(expected, rel=1e-12)

    def test_flow_area_annulus_m2(self, geo: DoublePipeGeometry):
        """flow_area_annulus_m2 = π × ((D_outer/2)² - (D_o/2)²)
        = π × (0.020² - 0.0125²) = π × 0.00024375
        """
        r_outer = _D_OUTER / 2.0
        r_o = _D_O / 2.0
        expected = math.pi * (r_outer**2 - r_o**2)
        assert geo.flow_area_annulus_m2 == pytest.approx(expected, rel=1e-12)

    def test_diameter_ratio(self, geo: DoublePipeGeometry):
        """diameter_ratio = D_o / D_outer = 0.025 / 0.040 = 0.625"""
        expected = _D_O / _D_OUTER
        assert geo.diameter_ratio == pytest.approx(expected, rel=1e-12)


# ---------------------------------------------------------------------------
# 8-14. Validation error cases
# ---------------------------------------------------------------------------


class TestValidation:
    """Ensure invalid geometries raise ValueError."""

    def test_di_ge_do_raises(self):
        """D_i >= D_o must be rejected."""
        with pytest.raises(ValueError, match="inner_tube_inner_diameter.*must be <"):
            _make_geometry(inner_tube_inner_diameter_m=0.025)  # D_i == D_o

    def test_di_gt_do_raises(self):
        """D_i > D_o must be rejected."""
        with pytest.raises(ValueError, match="inner_tube_inner_diameter.*must be <"):
            _make_geometry(inner_tube_inner_diameter_m=0.030)  # D_i > D_o

    def test_do_ge_douter_raises(self):
        """D_o >= D_outer must be rejected."""
        with pytest.raises(ValueError, match="inner_tube_outer_diameter.*must be <"):
            _make_geometry(inner_tube_outer_diameter_m=0.040)  # D_o == D_outer

    def test_do_gt_douter_raises(self):
        """D_o > D_outer must be rejected."""
        with pytest.raises(ValueError, match="inner_tube_outer_diameter.*must be <"):
            _make_geometry(inner_tube_outer_diameter_m=0.050)  # D_o > D_outer

    def test_negative_di_raises(self):
        with pytest.raises(ValueError):
            _make_geometry(inner_tube_inner_diameter_m=-0.01)

    def test_zero_di_raises(self):
        with pytest.raises(ValueError):
            _make_geometry(inner_tube_inner_diameter_m=0.0)

    def test_negative_do_raises(self):
        with pytest.raises(ValueError):
            _make_geometry(inner_tube_outer_diameter_m=-0.01)

    def test_negative_douter_raises(self):
        with pytest.raises(ValueError):
            _make_geometry(outer_pipe_inner_diameter_m=-0.01)

    def test_negative_length_raises(self):
        with pytest.raises(ValueError):
            _make_geometry(effective_length_m=-1.0)

    def test_zero_length_raises(self):
        with pytest.raises(ValueError):
            _make_geometry(effective_length_m=0.0)

    def test_negative_k_raises(self):
        with pytest.raises(ValueError):
            _make_geometry(wall_thermal_conductivity_w_m_k=-10.0)

    def test_zero_k_raises(self):
        with pytest.raises(ValueError):
            _make_geometry(wall_thermal_conductivity_w_m_k=0.0)

    def test_negative_inner_roughness_raises(self):
        with pytest.raises(ValueError):
            _make_geometry(inner_surface_roughness_m=-1e-6)

    def test_negative_annulus_roughness_raises(self):
        with pytest.raises(ValueError):
            _make_geometry(annulus_surface_roughness_m=-1e-6)

    def test_negative_inner_fouling_raises(self):
        with pytest.raises(ValueError):
            _make_geometry(inner_fouling_resistance_m2k_w=-0.001)

    def test_negative_outer_fouling_raises(self):
        with pytest.raises(ValueError):
            _make_geometry(outer_fouling_resistance_m2k_w=-0.001)

    def test_nan_di_raises(self):
        with pytest.raises(ValueError):
            _make_geometry(inner_tube_inner_diameter_m=float("nan"))

    def test_inf_do_raises(self):
        with pytest.raises(ValueError):
            _make_geometry(inner_tube_outer_diameter_m=float("inf"))

    def test_nan_length_raises(self):
        with pytest.raises(ValueError):
            _make_geometry(effective_length_m=float("nan"))

    def test_inf_k_raises(self):
        with pytest.raises(ValueError):
            _make_geometry(wall_thermal_conductivity_w_m_k=float("inf"))

    def test_nan_roughness_raises(self):
        with pytest.raises(ValueError):
            _make_geometry(inner_surface_roughness_m=float("nan"))

    def test_inf_fouling_raises(self):
        with pytest.raises(ValueError):
            _make_geometry(outer_fouling_resistance_m2k_w=float("inf"))

    def test_multiple_errors_collected(self):
        """Multiple validation errors are collected into one ValueError."""
        with pytest.raises(ValueError, match=";"):
            DoublePipeGeometry(
                inner_tube_inner_diameter_m=-1.0,
                inner_tube_outer_diameter_m=-1.0,
                outer_pipe_inner_diameter_m=-1.0,
                effective_length_m=-1.0,
                wall_thermal_conductivity_w_m_k=-1.0,
            )


# ---------------------------------------------------------------------------
# 15. Serialization round-trip
# ---------------------------------------------------------------------------


class TestSerialization:
    """to_dict() and from_dict() round-trip."""

    def test_round_trip_with_defaults(self):
        geo = _make_geometry()
        d = geo.to_dict()
        geo2 = DoublePipeGeometry.from_dict(d)
        assert geo == geo2

    def test_round_trip_with_optional_fields(self):
        geo = _make_geometry(
            inner_surface_roughness_m=4.5e-6,
            annulus_surface_roughness_m=3.2e-6,
            inner_fouling_resistance_m2k_w=2e-4,
            outer_fouling_resistance_m2k_w=3e-4,
        )
        d = geo.to_dict()
        geo2 = DoublePipeGeometry.from_dict(d)
        assert geo == geo2

    def test_to_dict_keys(self):
        geo = _make_geometry()
        d = geo.to_dict()
        expected_keys = {
            "inner_tube_inner_diameter_m",
            "inner_tube_outer_diameter_m",
            "outer_pipe_inner_diameter_m",
            "effective_length_m",
            "wall_thermal_conductivity_w_m_k",
            "inner_surface_roughness_m",
            "annulus_surface_roughness_m",
            "inner_fouling_resistance_m2k_w",
            "outer_fouling_resistance_m2k_w",
        }
        assert set(d.keys()) == expected_keys

    def test_from_dict_ignores_extra_keys(self):
        """from_dict silently drops keys not in the dataclass fields."""
        geo = _make_geometry()
        d = geo.to_dict()
        d["extra_key"] = "should be ignored"
        geo2 = DoublePipeGeometry.from_dict(d)
        assert geo == geo2


# ---------------------------------------------------------------------------
# 16. Immutability
# ---------------------------------------------------------------------------


class TestFrozen:
    """Assignment to any field on an existing instance must raise."""

    def test_cannot_reassign_inner_diameter(self):
        geo = _make_geometry()
        with pytest.raises(AttributeError):
            geo.inner_tube_inner_diameter_m = 0.1  # type: ignore[misc]

    def test_cannot_reassign_outer_diameter(self):
        geo = _make_geometry()
        with pytest.raises(AttributeError):
            geo.inner_tube_outer_diameter_m = 0.1  # type: ignore[misc]

    def test_cannot_reassign_length(self):
        geo = _make_geometry()
        with pytest.raises(AttributeError):
            geo.effective_length_m = 5.0  # type: ignore[misc]

    def test_cannot_reassign_roughness(self):
        geo = _make_geometry()
        with pytest.raises(AttributeError):
            geo.inner_surface_roughness_m = 1e-5  # type: ignore[misc]

    def test_cannot_reassign_fouling(self):
        geo = _make_geometry()
        with pytest.raises(AttributeError):
            geo.inner_fouling_resistance_m2k_w = 1e-3  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Boundary / edge-case tests
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Additional edge cases for robustness."""

    def test_zero_roughness_and_fouling_is_valid(self):
        geo = _make_geometry(
            inner_surface_roughness_m=0.0,
            annulus_surface_roughness_m=0.0,
            inner_fouling_resistance_m2k_w=0.0,
            outer_fouling_resistance_m2k_w=0.0,
        )
        assert geo.inner_surface_roughness_m == 0.0

    def test_tight_diameter_gap(self):
        """D_i < D_o < D_outer with very small margins."""
        geo = _make_geometry(
            inner_tube_inner_diameter_m=0.020,
            inner_tube_outer_diameter_m=0.020001,
            outer_pipe_inner_diameter_m=0.020002,
        )
        assert geo.hydraulic_diameter_annulus_m == pytest.approx(0.020002 - 0.020001, rel=1e-12)

    def test_very_long_heat_exchanger(self):
        geo = _make_geometry(effective_length_m=100.0)
        expected_area = math.pi * _D_I * 100.0
        assert geo.area_inner_m2 == pytest.approx(expected_area, rel=1e-12)

    def test_very_small_heat_exchanger(self):
        geo = _make_geometry(effective_length_m=0.01)
        expected_area = math.pi * _D_I * 0.01
        assert geo.area_inner_m2 == pytest.approx(expected_area, rel=1e-12)

    def test_high_conductivity_wall(self):
        geo = _make_geometry(wall_thermal_conductivity_w_m_k=400.0)
        assert geo.wall_thermal_conductivity_w_m_k == 400.0

    def test_equality_semantics(self):
        """Two geometries with identical values are equal."""
        geo1 = _make_geometry()
        geo2 = _make_geometry()
        assert geo1 == geo2
        assert hash(geo1) == hash(geo2)

    def test_inequality_semantics(self):
        """Two geometries with different values are not equal."""
        geo1 = _make_geometry()
        geo2 = _make_geometry(effective_length_m=5.0)
        assert geo1 != geo2
