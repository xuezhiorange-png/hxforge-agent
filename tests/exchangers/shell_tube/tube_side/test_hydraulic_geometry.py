"""§9 — Hydraulic geometry tests."""

from __future__ import annotations

import decimal
from decimal import Decimal

import pytest

import hexagent.exchangers.shell_tube.tube_side as ts
from tests.fixtures.shell_and_tube.tube_side.conftest import DEFAULT_POSITION_IDS


def test_hydraulic_geometry_outputs_exist() -> None:
    """All seven §9 outputs are produced."""
    out = ts.compute_hydraulic_geometry(
        tube_inner_diameter_m=Decimal("0.016"),
        active_tube_count=8,
        internal_flow_length_m=Decimal("4.85000000"),
        heat_transfer_length_m=Decimal("4.85000000"),
    )
    assert out.single_tube_flow_area_m2 > Decimal(0)
    assert out.total_parallel_flow_area_m2 > Decimal(0)
    assert out.flow_cross_section_wetted_perimeter_m > Decimal(0)
    assert out.total_flow_cross_section_wetted_perimeter_m > Decimal(0)
    assert out.hydraulic_diameter_m > Decimal(0)
    assert out.internal_volume_m3 > Decimal(0)
    assert out.internal_heat_transfer_surface_area_m2 > Decimal(0)


def test_hydraulic_geometry_quantums() -> None:
    """§9.3 — quantized lexical forms match the quantum scale."""
    out = ts.compute_hydraulic_geometry(
        tube_inner_diameter_m=Decimal("0.016"),
        active_tube_count=8,
        internal_flow_length_m=Decimal("4.85000000"),
        heat_transfer_length_m=Decimal("4.85000000"),
    )
    # Perimeter quantum 1e-8 — quantized to 8 fractional digits.
    assert _scale(out.flow_cross_section_wetted_perimeter_m) == 8
    # Area quantum 1e-10
    assert _scale(out.single_tube_flow_area_m2) == 10
    # Volume quantum 1e-12
    assert _scale(out.internal_volume_m3) == 12


def _scale(d: Decimal) -> int:
    """Return the scale (negative exponent) of a Decimal value."""
    sign, digits, exp = d.as_tuple()
    return -int(exp)


def test_hydraulic_diameter_equals_inner_diameter() -> None:
    """§9.2 — hydraulic_diameter_m quantizes from tube_inner_diameter_m."""
    d = Decimal("0.016")
    out = ts.compute_hydraulic_geometry(
        tube_inner_diameter_m=d,
        active_tube_count=8,
        internal_flow_length_m=Decimal("4.85000000"),
        heat_transfer_length_m=Decimal("4.85000000"),
    )
    assert out.hydraulic_diameter_m == d.quantize(Decimal("0.00000001"))


def test_hydraulic_geometry_zero_active_count_rejected() -> None:
    # §12 — stage 8 blocks non-positive active_tube_count before geometry.
    # The implementation does not accept 0 active tubes.
    with pytest.raises((ValueError, decimal.InvalidOperation)):
        ts.compute_hydraulic_geometry(
            tube_inner_diameter_m=Decimal("0.016"),
            active_tube_count=0,
            internal_flow_length_m=Decimal("4.85000000"),
            heat_transfer_length_m=Decimal("4.85000000"),
        )


def test_hydraulic_geometry_negative_inner_diameter_rejected() -> None:
    with pytest.raises(ValueError):
        ts.compute_hydraulic_geometry(
            tube_inner_diameter_m=Decimal("-0.016"),
            active_tube_count=8,
            internal_flow_length_m=Decimal("4.85000000"),
            heat_transfer_length_m=Decimal("4.85000000"),
        )


def test_hydraulic_geometry_default_position_ids() -> None:
    """Sanity: 8 default positions are valid inputs."""
    assert len(DEFAULT_POSITION_IDS) == 8
