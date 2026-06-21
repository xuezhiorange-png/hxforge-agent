from __future__ import annotations

from typing import ClassVar, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError

from hexagent.core.units import (
    QuantityKind,
    QuantitySchemaMixin,
    UnitConversionError,
    UnitErrorCode,
    convert_value,
    normalize_unit,
    si_unit,
    validate_quantity,
)


class Quantity(QuantitySchemaMixin, BaseModel):
    """Base class for unit-bearing engineering quantities.

    Direct construction is intentionally rejected. Public schemas must use one of
    the dimension-specific subclasses below.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    value: float = Field(allow_inf_nan=False)
    unit: str = Field(min_length=1)

    quantity_kind: ClassVar[QuantityKind | None] = None

    @field_validator("unit")
    @classmethod
    def canonicalize_unit(cls, value: str) -> str:
        kind = cls.quantity_kind
        if kind is None:
            raise PydanticCustomError(
                "quantity_kind_required",
                "Use a dimension-specific quantity type instead of Quantity.",
                {},
            )
        try:
            return normalize_unit(kind, value)
        except UnitConversionError as exc:
            raise PydanticCustomError(exc.code.value, str(exc), exc.context) from exc

    @model_validator(mode="after")
    def validate_value_and_dimension(self) -> Self:
        kind = self.quantity_kind
        if kind is None:
            raise PydanticCustomError(
                "quantity_kind_required",
                "Use a dimension-specific quantity type instead of Quantity.",
                {},
            )
        try:
            validate_quantity(self.value, self.unit, kind)
        except UnitConversionError as exc:
            raise PydanticCustomError(exc.code.value, str(exc), exc.context) from exc
        return self

    @property
    def kind(self) -> QuantityKind | None:
        return self.quantity_kind

    def to(self, target_unit: str) -> Self:
        kind = self.quantity_kind
        if kind is None:
            raise UnitConversionError(
                UnitErrorCode.QUANTITY_KIND_REQUIRED,
                "Typed quantity class is required for conversion.",
            )
        canonical_target = normalize_unit(kind, target_unit)
        converted = convert_value(self.value, self.unit, canonical_target, kind)
        return self.__class__.model_validate({"value": converted, "unit": canonical_target})

    def to_si(self) -> Self:
        kind = self.quantity_kind
        if kind is None:
            raise RuntimeError("Typed quantity class is required for SI conversion.")
        return self.to(si_unit(kind))

    @property
    def si_value(self) -> float:
        return self.to_si().value


class MassFlow(Quantity):
    quantity_kind = QuantityKind.MASS_FLOW

    @model_validator(mode="after")
    def _check_positive_mass_flow(self) -> Self:
        kind = self.quantity_kind
        si_val = convert_value(self.value, self.unit, si_unit(kind), kind)
        if si_val <= 0:
            raise PydanticCustomError(
                "quantity_mass_flow_non_positive",
                "Mass flow must be > 0, got {si_value} kg/s.",
                {"value": self.value, "unit": self.unit, "si_value": si_val},
            )
        return self


class VolumeFlow(Quantity):
    quantity_kind = QuantityKind.VOLUME_FLOW


class AbsoluteTemperature(Quantity):
    quantity_kind = QuantityKind.ABSOLUTE_TEMPERATURE

    @model_validator(mode="after")
    def _check_positive_temperature(self) -> Self:
        kind = self.quantity_kind
        si_val = convert_value(self.value, self.unit, si_unit(kind), kind)
        if si_val <= 0:
            raise PydanticCustomError(
                "quantity_absolute_temperature_non_positive",
                "Absolute temperature must be > 0 K, got {si_value} K.",
                {"value": self.value, "unit": self.unit, "si_value": si_val},
            )
        return self


class TemperatureDifference(Quantity):
    quantity_kind = QuantityKind.TEMPERATURE_DIFFERENCE


class AbsolutePressure(Quantity):
    quantity_kind = QuantityKind.ABSOLUTE_PRESSURE

    @model_validator(mode="after")
    def _check_positive_pressure(self) -> Self:
        kind = self.quantity_kind
        si_val = convert_value(self.value, self.unit, si_unit(kind), kind)
        if si_val <= 0:
            raise PydanticCustomError(
                "quantity_absolute_pressure_non_positive",
                "Absolute pressure must be > 0 Pa, got {si_value} Pa.",
                {"value": self.value, "unit": self.unit, "si_value": si_val},
            )
        return self


class PressureDifference(Quantity):
    quantity_kind = QuantityKind.PRESSURE_DIFFERENCE


class Power(Quantity):
    quantity_kind = QuantityKind.POWER


class Area(Quantity):
    quantity_kind = QuantityKind.AREA

    @model_validator(mode="after")
    def _check_non_negative_area(self) -> Self:
        kind = self.quantity_kind
        si_val = convert_value(self.value, self.unit, si_unit(kind), kind)
        if si_val < 0:
            raise PydanticCustomError(
                "quantity_area_negative",
                "Area must be >= 0, got {si_value} m^2.",
                {"value": self.value, "unit": self.unit, "si_value": si_val},
            )
        return self


class Length(Quantity):
    quantity_kind = QuantityKind.LENGTH

    @model_validator(mode="after")
    def _check_non_negative_length(self) -> Self:
        kind = self.quantity_kind
        si_val = convert_value(self.value, self.unit, si_unit(kind), kind)
        if si_val < 0:
            raise PydanticCustomError(
                "quantity_length_negative",
                "Length must be >= 0, got {si_value} m.",
                {"value": self.value, "unit": self.unit, "si_value": si_val},
            )
        return self


class Velocity(Quantity):
    quantity_kind = QuantityKind.VELOCITY


class FoulingResistance(Quantity):
    quantity_kind = QuantityKind.FOULING_RESISTANCE

    @model_validator(mode="after")
    def _check_non_negative_fouling(self) -> Self:
        kind = self.quantity_kind
        si_val = convert_value(self.value, self.unit, si_unit(kind), kind)
        if si_val < 0:
            raise PydanticCustomError(
                "quantity_fouling_resistance_negative",
                "Fouling resistance must be >= 0, got {si_value} m^2*K/W.",
                {"value": self.value, "unit": self.unit, "si_value": si_val},
            )
        return self


class SpecificEnthalpy(Quantity):
    quantity_kind = QuantityKind.SPECIFIC_ENTHALPY


class Dimensionless(Quantity):
    quantity_kind = QuantityKind.DIMENSIONLESS
