"""Shared fixtures for HXForge TASK-004 tests."""

from __future__ import annotations

import sys

# Python 3.11 + pydantic v2: assertion introspection can hit default
# recursion limit when repr-ing deeply nested models.
if sys.getrecursionlimit() < 10000:
    sys.setrecursionlimit(10000)

from datetime import UTC, datetime
from uuid import UUID

import pytest

from hexagent.domain.models import (
    DesignCase,
    DesignConstraints,
    FluidSpec,
    FoulingResistanceSpec,
    FoulingSource,
    FoulingSourceType,
    StreamSpec,
    VerificationStatus,
)
from hexagent.domain.quantities import (
    AbsolutePressure,
    AbsoluteTemperature,
    FoulingResistance,
    Length,
    MassFlow,
)

# ---------------------------------------------------------------------------
# Fixed helpers
# ---------------------------------------------------------------------------

FIXED_NOW = datetime(2026, 1, 1, tzinfo=UTC)
FIXED_IDS = [UUID(int=i) for i in range(1, 20)]


def _make_fluid(name: str = "Water") -> FluidSpec:
    return FluidSpec(backend="CoolProp", name=name)


def _make_fouling_source() -> FoulingSource:
    return FoulingSource(
        source_type=FoulingSourceType.STANDARD,
        reference_id="TEMA",
        edition="2019",
        table_or_clause="Table RGP-K-2",
        verification_status=VerificationStatus.VERIFIED,
        note="Clean water fouling",
    )


def _make_fouling_spec() -> FoulingResistanceSpec:
    return FoulingResistanceSpec(
        value=FoulingResistance(value=0.0002, unit="m^2*K/W"),
        source=_make_fouling_source(),
    )


def _make_hot_stream(
    *,
    outlet_temp: float | None = 310.0,
    inlet_temp: float = 350.0,
) -> StreamSpec:
    return StreamSpec(
        fluid=_make_fluid("Water"),
        mass_flow=MassFlow(value=1.0, unit="kg/s"),
        inlet_temperature=AbsoluteTemperature(value=inlet_temp, unit="K"),
        inlet_pressure=AbsolutePressure(value=200000.0, unit="Pa"),
        fouling_resistance=_make_fouling_spec(),
        outlet_temperature=(
            AbsoluteTemperature(value=outlet_temp, unit="K") if outlet_temp is not None else None
        ),
    )


def _make_cold_stream(
    *,
    outlet_temp: float | None = 330.0,
    inlet_temp: float = 290.0,
) -> StreamSpec:
    return StreamSpec(
        fluid=_make_fluid("Water"),
        mass_flow=MassFlow(value=0.8, unit="kg/s"),
        inlet_temperature=AbsoluteTemperature(value=inlet_temp, unit="K"),
        inlet_pressure=AbsolutePressure(value=150000.0, unit="Pa"),
        fouling_resistance=_make_fouling_spec(),
        outlet_temperature=(
            AbsoluteTemperature(value=outlet_temp, unit="K") if outlet_temp is not None else None
        ),
    )


def _make_constraints() -> DesignConstraints:
    return DesignConstraints(
        design_pressure_hot=AbsolutePressure(value=250000.0, unit="Pa"),
        design_pressure_cold=AbsolutePressure(value=200000.0, unit="Pa"),
        design_temperature_hot=AbsoluteTemperature(value=370.0, unit="K"),
        design_temperature_cold=AbsoluteTemperature(value=350.0, unit="K"),
        corrosion_allowance=Length(value=0.003, unit="m"),
        required_area_margin_fraction=0.1,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_design_case() -> DesignCase:
    """Return a fully valid DesignCase with deterministic IDs."""
    return DesignCase(
        id=FIXED_IDS[0],
        name="Test Heat Exchanger",
        hot_stream=_make_hot_stream(),
        cold_stream=_make_cold_stream(),
        constraints=_make_constraints(),
    )


@pytest.fixture()
def sample_design_case_v2() -> DesignCase:
    """Return a second DesignCase with a different id."""
    return DesignCase(
        id=FIXED_IDS[1],
        name="Test Heat Exchanger V2",
        hot_stream=_make_hot_stream(outlet_temp=305.0),
        cold_stream=_make_cold_stream(),
        constraints=_make_constraints(),
    )
