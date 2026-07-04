from __future__ import annotations

import math

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from hexagent.core.units import (
    UNIT_RULES,
    UnitConversionError,
    allowed_units,
    to_si,
)
from hexagent.domain.models import DesignCase
from hexagent.domain.quantities import (
    AbsolutePressure,
    AbsoluteTemperature,
    Area,
    Dimensionless,
    FoulingResistance,
    MassFlow,
    Power,
    PressureDifference,
    Quantity,
    SpecificEnthalpy,
    TemperatureDifference,
    VolumeFlow,
)

pytestmark = pytest.mark.coolprop


@pytest.mark.parametrize(
    ("kind", "unit"),
    [(kind, unit) for kind in UNIT_RULES for unit in allowed_units(kind)],
)
def test_every_allowed_unit_converts_to_si(kind: object, unit: str) -> None:
    from hexagent.core.units import QuantityKind, convert_value

    assert isinstance(kind, QuantityKind)
    assert math.isfinite(convert_value(1.0, unit, UNIT_RULES[kind].si_unit, kind))


def test_absolute_celsius_to_kelvin() -> None:
    temperature = AbsoluteTemperature(value=0.0, unit="°C")
    assert temperature.unit == "degC"
    assert temperature.si_value == pytest.approx(273.15)


def test_absolute_fahrenheit_to_kelvin() -> None:
    temperature = AbsoluteTemperature(value=32.0, unit="degF")
    assert temperature.si_value == pytest.approx(273.15)


def test_temperature_difference_has_no_offset() -> None:
    assert TemperatureDifference(value=10.0, unit="delta_degC").si_value == pytest.approx(10.0)
    assert TemperatureDifference(value=18.0, unit="Δ°F").si_value == pytest.approx(10.0)


def test_plain_celsius_is_rejected_for_temperature_difference() -> None:
    with pytest.raises(ValidationError) as exc_info:
        TemperatureDifference(value=10.0, unit="degC")
    assert exc_info.value.errors()[0]["type"] == "quantity_unit_not_allowed"


def test_wrong_dimension_has_structured_error() -> None:
    with pytest.raises(ValidationError) as exc_info:
        MassFlow(value=2.0, unit="kW")
    error = exc_info.value.errors()[0]
    assert error["type"] == "quantity_unit_not_allowed"
    assert error["ctx"]["quantity_kind"] == "mass_flow"
    assert "kg/s" in error["ctx"]["allowed_units"]


def test_generic_quantity_is_rejected() -> None:
    with pytest.raises(ValidationError) as exc_info:
        Quantity(value=1.0, unit="kg/s")
    assert exc_info.value.errors()[0]["type"] == "quantity_kind_required"


def test_non_finite_value_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Power(value=math.inf, unit="kW")


def test_absolute_and_differential_pressure_are_distinct_types() -> None:
    absolute = AbsolutePressure(value=4.0, unit="bar(a)")
    differential = PressureDifference(value=50.0, unit="kPa(d)")
    assert absolute.unit == "bar"
    assert absolute.si_value == pytest.approx(400_000.0)
    assert differential.unit == "kPa"
    assert differential.si_value == pytest.approx(50_000.0)


@pytest.mark.parametrize(
    ("quantity", "expected_si"),
    [
        (MassFlow(value=3600.0, unit="kg/h"), 1.0),
        (VolumeFlow(value=3.6, unit="m^3/h"), 0.001),
        (Power(value=250.0, unit="kW"), 250_000.0),
        (Area(value=10.0, unit="ft^2"), 0.9290304),
        (SpecificEnthalpy(value=250.0, unit="kJ/kg"), 250_000.0),
        (Dimensionless(value=25.0, unit="%"), 0.25),
    ],
)
def test_supported_quantity_si_conversions(quantity: Quantity, expected_si: float) -> None:
    assert quantity.si_value == pytest.approx(expected_si)


def test_fouling_resistance_imperial_conversion() -> None:
    quantity = FoulingResistance(value=1.0, unit="hr*ft^2*delta_degF/Btu")
    assert quantity.si_value == pytest.approx(0.17611015908160327)


def test_model_serialization_round_trip() -> None:
    original = PressureDifference(value=50.0, unit="kPa(d)")
    restored = PressureDifference.model_validate_json(original.model_dump_json())
    assert restored == original
    assert restored.unit == "kPa"


def test_legacy_to_si_adapter_uses_typed_semantics() -> None:
    value = to_si(AbsoluteTemperature(value=0.0, unit="degC"), "kelvin")
    assert value == pytest.approx(273.15)
    with pytest.raises(UnitConversionError):
        to_si(TemperatureDifference(value=10.0, unit="delta_degC"), "degC")


@given(st.floats(min_value=1e-10, max_value=1.0e6, allow_nan=False, allow_infinity=False))
def test_mass_flow_round_trip(value: float) -> None:
    original = MassFlow(value=value, unit="kg/s")
    restored = original.to("lb/h").to("kg/s")
    assert restored.value == pytest.approx(value, rel=1e-12, abs=1e-9)


@given(st.floats(min_value=-200.0, max_value=1000.0, allow_nan=False, allow_infinity=False))
def test_absolute_temperature_round_trip(value: float) -> None:
    original = AbsoluteTemperature(value=value, unit="degC")
    restored = original.to("degF").to("degC")
    assert restored.value == pytest.approx(value, rel=1e-12, abs=1e-9)


def test_public_domain_models_reject_wrong_quantity_dimension() -> None:
    payload = {
        "name": "invalid-unit-case",
        "hot_stream": {
            "fluid": {"backend": "CoolProp", "name": "Water"},
            "mass_flow": {"value": 1.0, "unit": "kW"},
            "inlet_temperature": {"value": 80.0, "unit": "degC"},
            "outlet_temperature": {"value": 60.0, "unit": "degC"},
            "inlet_pressure": {"value": 3.0, "unit": "bar(a)"},
            "fouling_resistance": {
                "value": {"value": 0.0002, "unit": "m^2*K/W"},
                "source": {
                    "source_type": "STANDARD",
                    "reference_id": "TEMA-RGP-T-2.4",
                    "edition": "TBD",
                    "table_or_clause": "TBD",
                    "verification_status": "UNVERIFIED_REFERENCE",
                    "note": "test",
                },
            },
        },
        "cold_stream": {
            "fluid": {"backend": "CoolProp", "name": "Water"},
            "mass_flow": {"value": 1.0, "unit": "kg/s"},
            "inlet_temperature": {"value": 20.0, "unit": "degC"},
            "outlet_temperature": {"value": 40.0, "unit": "degC"},
            "inlet_pressure": {"value": 3.0, "unit": "bar(a)"},
            "fouling_resistance": {
                "value": {"value": 0.0002, "unit": "m^2*K/W"},
                "source": {
                    "source_type": "STANDARD",
                    "reference_id": "TEMA-RGP-T-2.4",
                    "edition": "TBD",
                    "table_or_clause": "TBD",
                    "verification_status": "UNVERIFIED_REFERENCE",
                    "note": "test",
                },
            },
        },
        "constraints": {
            "design_pressure_hot": {"value": 10.0, "unit": "bar(a)"},
            "design_pressure_cold": {"value": 10.0, "unit": "bar(a)"},
            "design_temperature_hot": {"value": 120.0, "unit": "degC"},
            "design_temperature_cold": {"value": 80.0, "unit": "degC"},
            "required_area_margin_fraction": 0.1,
        },
        "target_duty": {"value": 100.0, "unit": "kW"},
    }
    with pytest.raises(ValidationError) as exc_info:
        DesignCase.model_validate(payload)
    assert any(error["type"] == "quantity_unit_not_allowed" for error in exc_info.value.errors())
