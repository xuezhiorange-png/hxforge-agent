"""Declared applicability envelopes for V08 user design cases."""

from __future__ import annotations

from decimal import Decimal

# Input acceptance envelope (liquid water single-phase intent at inlets).
V08_INLET_TEMPERATURE_MIN_K = Decimal("280")
V08_INLET_TEMPERATURE_MAX_K = Decimal("360")
V08_INLET_PRESSURE_MIN_PA = Decimal("50000")
V08_INLET_PRESSURE_MAX_PA = Decimal("2000000")

# Envelope where Task173 experimental thermal boundary can be materialized today.
V08_THERMAL_BINDING_TEMPERATURE_MIN_K = Decimal("290")
V08_THERMAL_BINDING_TEMPERATURE_MAX_K = Decimal("320")
V08_THERMAL_BINDING_PRESSURE_MIN_PA = Decimal("100000")
V08_THERMAL_BINDING_PRESSURE_MAX_PA = Decimal("101325")

V08_SUPPORTED_EXCHANGER = "SHELL_AND_TUBE_FIXED_TUBESHEET_SINGLE_PHASE"
V08_SUPPORTED_FLUID = "PURE_ORDINARY_WATER"
