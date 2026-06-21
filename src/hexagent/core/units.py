from __future__ import annotations

import math
import unicodedata
from dataclasses import dataclass
from enum import StrEnum
from functools import lru_cache
from typing import Any, Protocol

from pint import DimensionalityError, UndefinedUnitError, UnitRegistry


class QuantityKind(StrEnum):
    MASS_FLOW = "mass_flow"
    VOLUME_FLOW = "volume_flow"
    ABSOLUTE_TEMPERATURE = "absolute_temperature"
    TEMPERATURE_DIFFERENCE = "temperature_difference"
    ABSOLUTE_PRESSURE = "absolute_pressure"
    PRESSURE_DIFFERENCE = "pressure_difference"
    POWER = "power"
    AREA = "area"
    LENGTH = "length"
    VELOCITY = "velocity"
    FOULING_RESISTANCE = "fouling_resistance"
    SPECIFIC_ENTHALPY = "specific_enthalpy"
    DIMENSIONLESS = "dimensionless"


class UnitErrorCode(StrEnum):
    QUANTITY_KIND_REQUIRED = "quantity_kind_required"
    NON_FINITE_VALUE = "quantity_non_finite_value"
    EMPTY_UNIT = "quantity_empty_unit"
    UNIT_NOT_ALLOWED = "quantity_unit_not_allowed"
    UNDEFINED_UNIT = "quantity_undefined_unit"
    DIMENSION_MISMATCH = "quantity_dimension_mismatch"
    CONVERSION_FAILED = "quantity_conversion_failed"


class UnitConversionError(ValueError):
    def __init__(
        self,
        code: UnitErrorCode,
        message: str,
        *,
        context: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.context = context or {}

    def as_dict(self) -> dict[str, object]:
        return {
            "code": self.code.value,
            "message": str(self),
            "context": self.context,
        }


@dataclass(frozen=True)
class UnitRule:
    si_unit: str
    aliases: dict[str, str]


class QuantityLike(Protocol):
    value: float
    unit: str

    @property
    def kind(self) -> QuantityKind | None: ...


def _unit_key(unit: str) -> str:
    normalized = unicodedata.normalize("NFKC", unit).strip()
    normalized = normalized.replace("²", "^2").replace("³", "^3").replace("·", "*")
    return "".join(normalized.split())


def _aliases(*groups: tuple[str, str]) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for alias, canonical in groups:
        aliases[_unit_key(alias)] = canonical
        aliases[_unit_key(canonical)] = canonical
    return aliases


UNIT_RULES: dict[QuantityKind, UnitRule] = {
    QuantityKind.MASS_FLOW: UnitRule(
        si_unit="kg/s",
        aliases=_aliases(
            ("kg/s", "kg/s"),
            ("kg/h", "kg/h"),
            ("kg/hr", "kg/h"),
            ("g/s", "g/s"),
            ("g/min", "g/min"),
            ("lb/s", "lb/s"),
            ("lb/h", "lb/h"),
            ("lb/hr", "lb/h"),
            ("lbm/s", "lb/s"),
            ("lbm/h", "lb/h"),
        ),
    ),
    QuantityKind.VOLUME_FLOW: UnitRule(
        si_unit="m^3/s",
        aliases=_aliases(
            ("m^3/s", "m^3/s"),
            ("m3/s", "m^3/s"),
            ("m^3/h", "m^3/h"),
            ("m3/h", "m^3/h"),
            ("L/s", "L/s"),
            ("l/s", "L/s"),
            ("L/min", "L/min"),
            ("l/min", "L/min"),
            ("L/h", "L/h"),
            ("l/h", "L/h"),
            ("ft^3/min", "ft^3/min"),
            ("cfm", "ft^3/min"),
            ("gal/min", "gallon/minute"),
            ("gpm", "gallon/minute"),
        ),
    ),
    QuantityKind.ABSOLUTE_TEMPERATURE: UnitRule(
        si_unit="K",
        aliases=_aliases(
            ("K", "K"),
            ("kelvin", "K"),
            ("degC", "degC"),
            ("°C", "degC"),
            ("celsius", "degC"),
            ("degF", "degF"),
            ("°F", "degF"),
            ("fahrenheit", "degF"),
            ("degR", "degR"),
            ("°R", "degR"),
            ("rankine", "degR"),
        ),
    ),
    QuantityKind.TEMPERATURE_DIFFERENCE: UnitRule(
        si_unit="K",
        aliases=_aliases(
            ("K", "K"),
            ("kelvin", "K"),
            ("delta_K", "K"),
            ("ΔK", "K"),
            ("delta_degC", "delta_degC"),
            ("degC_delta", "delta_degC"),
            ("Δ°C", "delta_degC"),
            ("delta_degF", "delta_degF"),
            ("degF_delta", "delta_degF"),
            ("Δ°F", "delta_degF"),
            ("delta_degR", "delta_degR"),
            ("degR_delta", "delta_degR"),
            ("Δ°R", "delta_degR"),
        ),
    ),
    QuantityKind.ABSOLUTE_PRESSURE: UnitRule(
        si_unit="Pa",
        aliases=_aliases(
            ("Pa", "Pa"),
            ("pascal", "Pa"),
            ("kPa", "kPa"),
            ("MPa", "MPa"),
            ("bar", "bar"),
            ("bar(a)", "bar"),
            ("bara", "bar"),
            ("kPa(a)", "kPa"),
            ("kPaa", "kPa"),
            ("psi", "psi"),
            ("psi(a)", "psi"),
            ("psia", "psi"),
            ("atm", "atm"),
        ),
    ),
    QuantityKind.PRESSURE_DIFFERENCE: UnitRule(
        si_unit="Pa",
        aliases=_aliases(
            ("Pa", "Pa"),
            ("delta_Pa", "Pa"),
            ("ΔPa", "Pa"),
            ("kPa", "kPa"),
            ("delta_kPa", "kPa"),
            ("kPa(d)", "kPa"),
            ("MPa", "MPa"),
            ("bar", "bar"),
            ("delta_bar", "bar"),
            ("bar(d)", "bar"),
            ("psi", "psi"),
            ("delta_psi", "psi"),
            ("psi(d)", "psi"),
        ),
    ),
    QuantityKind.POWER: UnitRule(
        si_unit="W",
        aliases=_aliases(
            ("W", "W"),
            ("watt", "W"),
            ("kW", "kW"),
            ("MW", "MW"),
            ("Btu/h", "Btu/hour"),
            ("Btu/hr", "Btu/hour"),
            ("Btu/hour", "Btu/hour"),
            ("ton_refrigeration", "ton_refrigeration"),
            ("TR", "ton_refrigeration"),
        ),
    ),
    QuantityKind.AREA: UnitRule(
        si_unit="m^2",
        aliases=_aliases(
            ("m^2", "m^2"),
            ("m2", "m^2"),
            ("cm^2", "cm^2"),
            ("cm2", "cm^2"),
            ("mm^2", "mm^2"),
            ("mm2", "mm^2"),
            ("ft^2", "ft^2"),
            ("ft2", "ft^2"),
            ("in^2", "in^2"),
            ("in2", "in^2"),
        ),
    ),
    QuantityKind.LENGTH: UnitRule(
        si_unit="m",
        aliases=_aliases(
            ("m", "m"),
            ("meter", "m"),
            ("cm", "cm"),
            ("mm", "mm"),
            ("um", "um"),
            ("µm", "um"),
            ("ft", "ft"),
            ("foot", "ft"),
            ("in", "in"),
            ("inch", "in"),
        ),
    ),
    QuantityKind.VELOCITY: UnitRule(
        si_unit="m/s",
        aliases=_aliases(
            ("m/s", "m/s"),
            ("m/min", "m/min"),
            ("m/h", "m/h"),
            ("ft/s", "ft/s"),
            ("ft/min", "ft/min"),
        ),
    ),
    QuantityKind.FOULING_RESISTANCE: UnitRule(
        si_unit="m^2*K/W",
        aliases=_aliases(
            ("m^2*K/W", "m^2*K/W"),
            ("m2*K/W", "m^2*K/W"),
            ("m^2*delta_degC/W", "m^2*delta_degC/W"),
            ("m2*delta_degC/W", "m^2*delta_degC/W"),
            ("h*ft^2*delta_degF/Btu", "hour*ft^2*delta_degF/Btu"),
            ("hr*ft^2*delta_degF/Btu", "hour*ft^2*delta_degF/Btu"),
            ("hour*ft^2*delta_degF/Btu", "hour*ft^2*delta_degF/Btu"),
        ),
    ),
    QuantityKind.SPECIFIC_ENTHALPY: UnitRule(
        si_unit="J/kg",
        aliases=_aliases(
            ("J/kg", "J/kg"),
            ("kJ/kg", "kJ/kg"),
            ("MJ/kg", "MJ/kg"),
            ("Btu/lb", "Btu/lb"),
            ("Btu/lbm", "Btu/lb"),
        ),
    ),
    QuantityKind.DIMENSIONLESS: UnitRule(
        si_unit="dimensionless",
        aliases=_aliases(
            ("1", "dimensionless"),
            ("dimensionless", "dimensionless"),
            ("fraction", "dimensionless"),
            ("%", "percent"),
            ("percent", "percent"),
        ),
    ),
}


@lru_cache(maxsize=1)
def unit_registry() -> UnitRegistry[Any]:
    registry: UnitRegistry[Any] = UnitRegistry(autoconvert_offset_to_baseunit=True)
    registry.define("delta_degR = 5 / 9 * kelvin = delta_degree_Rankine")
    registry.define("ton_refrigeration = 12000 * Btu / hour = TR")
    return registry


def allowed_units(kind: QuantityKind) -> tuple[str, ...]:
    return tuple(sorted(set(UNIT_RULES[kind].aliases.values())))


def normalize_unit(kind: QuantityKind, unit: str) -> str:
    if not unit or not unit.strip():
        raise UnitConversionError(
            UnitErrorCode.EMPTY_UNIT,
            "A unit is required for every public engineering quantity.",
            context={"quantity_kind": kind.value},
        )

    key = _unit_key(unit)
    rule = UNIT_RULES[kind]
    try:
        return rule.aliases[key]
    except KeyError as exc:
        raise UnitConversionError(
            UnitErrorCode.UNIT_NOT_ALLOWED,
            f"Unit {unit!r} is not allowed for {kind.value}.",
            context={
                "quantity_kind": kind.value,
                "unit": unit,
                "allowed_units": allowed_units(kind),
            },
        ) from exc


def validate_quantity(value: float, unit: str, kind: QuantityKind) -> str:
    if not math.isfinite(value):
        raise UnitConversionError(
            UnitErrorCode.NON_FINITE_VALUE,
            "Quantity values must be finite.",
            context={"quantity_kind": kind.value, "value": value},
        )

    canonical_unit = normalize_unit(kind, unit)
    registry = unit_registry()
    try:
        parsed = registry.Quantity(value, canonical_unit)
        expected = registry.Quantity(1.0, UNIT_RULES[kind].si_unit).dimensionality
    except UndefinedUnitError as exc:
        raise UnitConversionError(
            UnitErrorCode.UNDEFINED_UNIT,
            f"Unit {canonical_unit!r} is not defined by the unit registry.",
            context={"quantity_kind": kind.value, "unit": canonical_unit},
        ) from exc

    if parsed.dimensionality != expected:
        raise UnitConversionError(
            UnitErrorCode.DIMENSION_MISMATCH,
            f"Unit {canonical_unit!r} has the wrong dimensionality for {kind.value}.",
            context={
                "quantity_kind": kind.value,
                "unit": canonical_unit,
                "actual_dimensionality": str(parsed.dimensionality),
                "expected_dimensionality": str(expected),
            },
        )
    return canonical_unit


def convert_value(value: float, from_unit: str, target_unit: str, kind: QuantityKind) -> float:
    canonical_from = validate_quantity(value, from_unit, kind)
    canonical_target = normalize_unit(kind, target_unit)
    registry = unit_registry()
    try:
        converted = registry.Quantity(value, canonical_from).to(canonical_target)
    except (DimensionalityError, UndefinedUnitError, ValueError) as exc:
        raise UnitConversionError(
            UnitErrorCode.CONVERSION_FAILED,
            f"Could not convert {value} {canonical_from} to {canonical_target}.",
            context={
                "quantity_kind": kind.value,
                "from_unit": canonical_from,
                "target_unit": canonical_target,
            },
        ) from exc
    return float(converted.magnitude)


def si_unit(kind: QuantityKind) -> str:
    return UNIT_RULES[kind].si_unit


def to_si(quantity: QuantityLike, target_unit: str | None = None) -> float:
    kind = quantity.kind
    if kind is None:
        raise UnitConversionError(
            UnitErrorCode.QUANTITY_KIND_REQUIRED,
            "Typed quantity class is required for SI conversion.",
            context={"unit": quantity.unit},
        )
    requested_unit = target_unit or si_unit(kind)
    return convert_value(quantity.value, quantity.unit, requested_unit, kind)
