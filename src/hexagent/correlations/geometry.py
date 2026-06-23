"""Geometry models for single-phase convective heat-transfer correlations.

Provides immutable, unit-safe geometry definitions for circular tubes and
concentric annuli with comprehensive validation.
"""

from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator


class CircularTubeGeometry(BaseModel):
    """Immutable circular tube geometry.

    All dimensions in SI (meters).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    geometry_type: Literal["circular_tube"] = "circular_tube"
    inside_diameter_m: float
    heat_transfer_length_m: float

    @model_validator(mode="after")
    def _validate_dimensions(self) -> CircularTubeGeometry:
        for name in ("inside_diameter_m", "heat_transfer_length_m"):
            val = getattr(self, name)
            if not math.isfinite(val) or val <= 0:
                raise ValueError(f"{name} must be a finite positive number, got {val!r}")
        return self

    @property
    def flow_area_m2(self) -> float:
        """Cross-sectional flow area: A = π/4 × D²."""
        return math.pi / 4.0 * self.inside_diameter_m**2

    @property
    def wetted_perimeter_m(self) -> float:
        """Wetted perimeter: P = π × D."""
        return math.pi * self.inside_diameter_m

    @property
    def hydraulic_diameter_m(self) -> float:
        """Hydraulic diameter: D_h = 4A / P = D for circular tube."""
        return self.inside_diameter_m

    @property
    def heated_perimeter_m(self) -> float:
        """Heated perimeter (same as wetted for tube): P_h = π × D."""
        return math.pi * self.inside_diameter_m


class ThermalBoundaryCondition:
    """Thermal boundary condition identifiers for annulus."""

    CONSTANT_WALL_TEMPERATURE = "constant_wall_temperature"
    CONSTANT_HEAT_FLUX = "constant_heat_flux"
    INNER_WALL_HEATED = "inner_wall_heated"
    OUTER_WALL_HEATED = "outer_wall_heated"
    BOTH_WALLS_HEATED = "both_walls_heated"


class ConcentricAnnulusGeometry(BaseModel):
    """Immutable concentric annulus geometry.

    All dimensions in SI (meters).
    Inner tube is the smaller-diameter tube; outer pipe is the larger.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    geometry_type: Literal["concentric_annulus"] = "concentric_annulus"
    inner_tube_outer_diameter_m: float
    outer_pipe_inside_diameter_m: float
    heat_transfer_length_m: float
    heated_surface: Literal["inner", "outer", "both"] = "inner"

    @model_validator(mode="after")
    def _validate_dimensions(self) -> ConcentricAnnulusGeometry:
        for name in (
            "inner_tube_outer_diameter_m",
            "outer_pipe_inside_diameter_m",
            "heat_transfer_length_m",
        ):
            val = getattr(self, name)
            if not math.isfinite(val) or val <= 0:
                raise ValueError(f"{name} must be a finite positive number, got {val!r}")
        if self.outer_pipe_inside_diameter_m <= self.inner_tube_outer_diameter_m:
            raise ValueError(
                f"outer_pipe_inside_diameter_m ({self.outer_pipe_inside_diameter_m}) "
                f"must be greater than inner_tube_outer_diameter_m "
                f"({self.inner_tube_outer_diameter_m})"
            )
        return self

    @property
    def flow_area_m2(self) -> float:
        """Cross-sectional flow area: A = π/4 × (D_o² - D_i²)."""
        return (
            math.pi
            / 4.0
            * (self.outer_pipe_inside_diameter_m**2 - self.inner_tube_outer_diameter_m**2)
        )

    @property
    def inner_wetted_perimeter_m(self) -> float:
        """Inner tube wetted perimeter: P_i = π × D_i."""
        return math.pi * self.inner_tube_outer_diameter_m

    @property
    def outer_wetted_perimeter_m(self) -> float:
        """Outer pipe wetted perimeter: P_o = π × D_o."""
        return math.pi * self.outer_pipe_inside_diameter_m

    @property
    def total_wetted_perimeter_m(self) -> float:
        """Total wetted perimeter: P = P_i + P_o."""
        return self.inner_wetted_perimeter_m + self.outer_wetted_perimeter_m

    @property
    def hydraulic_diameter_m(self) -> float:
        """Hydraulic diameter: D_h = 4A / P_total."""
        return 4.0 * self.flow_area_m2 / self.total_wetted_perimeter_m

    @property
    def diameter_ratio(self) -> float:
        """Diameter ratio: κ = D_i / D_o."""
        return self.inner_tube_outer_diameter_m / self.outer_pipe_inside_diameter_m

    @property
    def inner_heated_perimeter_m(self) -> float:
        """Heated perimeter on inner surface."""
        if self.heated_surface in ("inner", "both"):
            return self.inner_wetted_perimeter_m
        return 0.0

    @property
    def outer_heated_perimeter_m(self) -> float:
        """Heated perimeter on outer surface."""
        if self.heated_surface in ("outer", "both"):
            return self.outer_wetted_perimeter_m
        return 0.0
