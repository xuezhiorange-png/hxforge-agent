"""Public API request DTOs for TASK-010.

All models are frozen, reject extra fields, and use the project's existing
StrictBaseModel from hexagent.domain.models.
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import Field

from hexagent.core.heat_balance import ProviderIdentitySnapshot
from hexagent.domain.models import (
    FluidSpec,
    FoulingResistanceSpec,
    StrictBaseModel,
    TPStateSpec,
)
from hexagent.domain.quantities import (
    AbsolutePressure,
    AbsoluteTemperature,
    Dimensionless,
    Length,
    MassFlow,
    Power,
    TemperatureDifference,
)
from hexagent.optimization.context import (
    ExpectedProviderIdentity,
    OptimizationObjective,
)

# ---------------------------------------------------------------------------
# Thermal conductivity spec (standalone — no QuantityKind for this dimension)
# ---------------------------------------------------------------------------


class ThermalConductivitySpec(StrictBaseModel):
    """Wall thermal conductivity with a fixed unit literal."""

    model_config = {"frozen": True, "extra": "forbid"}

    value: float = Field(allow_inf_nan=False, gt=0)
    unit: Literal["W/(m*K)"]


# ---------------------------------------------------------------------------
# Fluid stream spec
# ---------------------------------------------------------------------------


class FluidStreamSpec(StrictBaseModel):
    """Complete fluid stream specification for the public API."""

    model_config = {"frozen": True, "extra": "forbid"}

    fluid: FluidSpec
    inlet: TPStateSpec
    mass_flow: MassFlow
    fouling: FoulingResistanceSpec


# ---------------------------------------------------------------------------
# Validation request
# ---------------------------------------------------------------------------


class ValidationApiRequest(StrictBaseModel):
    """Request to validate a thermal design case."""

    model_config = {"frozen": True, "extra": "forbid"}

    api_schema_version: Literal["1"]
    case_name: str
    hot_stream: FluidStreamSpec
    cold_stream: FluidStreamSpec
    target_duty: Power
    minimum_terminal_delta_t: TemperatureDifference
    design_pressure_hot: AbsolutePressure
    design_pressure_cold: AbsolutePressure
    design_temperature_hot: AbsoluteTemperature
    design_temperature_cold: AbsoluteTemperature
    required_area_margin_fraction: float = Field(ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# Double-pipe geometry spec
# ---------------------------------------------------------------------------


class DoublePipeGeometrySpec(StrictBaseModel):
    """Geometry specification for a double-pipe heat exchanger.

    No fouling fields — fouling is carried by the stream specs.
    """

    model_config = {"frozen": True, "extra": "forbid"}

    inner_tube_inner_diameter: Length
    inner_tube_outer_diameter: Length
    outer_pipe_inner_diameter: Length
    effective_length: Length
    wall_thermal_conductivity: ThermalConductivitySpec
    inner_surface_roughness: Length
    annulus_surface_roughness: Length


# ---------------------------------------------------------------------------
# Solver parameters spec
# ---------------------------------------------------------------------------


class SolverParamsSpec(StrictBaseModel):
    """Solver control parameters for the rating kernel."""

    model_config = {"frozen": True, "extra": "forbid"}

    absolute_residual_w: Power = Field(
        default=Power(value=1e-3, unit="W"),
    )
    relative_residual_fraction: float = Field(
        default=1e-8,
        ge=0,
    )
    bracket_temperature_tolerance_k: TemperatureDifference = Field(
        default=TemperatureDifference(value=1e-4, unit="K"),
    )
    max_iterations: int = Field(
        default=100,
        ge=1,
    )


# ---------------------------------------------------------------------------
# Rating request
# ---------------------------------------------------------------------------


class RatingApiRequest(StrictBaseModel):
    """Request to rate a specific double-pipe geometry."""

    model_config = {"frozen": True, "extra": "forbid"}

    api_schema_version: Literal["1"]
    case: ValidationApiRequest
    geometry: DoublePipeGeometrySpec
    tube_in_hot: bool = True
    flow_arrangement: Literal["counterflow", "parallel"]
    tube_boundary_condition: Literal["constant_wall_temperature", "inner_wall_heated"]
    annulus_boundary_condition: Literal["inner_wall_heated", "constant_wall_temperature"]
    solver_params: SolverParamsSpec | None = None
    provider_ref: str


# ---------------------------------------------------------------------------
# Catalog snapshot reference
# ---------------------------------------------------------------------------


class CatalogSnapshotReference(StrictBaseModel):
    """Reference to a frozen catalog snapshot."""

    model_config = {"frozen": True, "extra": "forbid"}

    catalog_id: str
    catalog_version: str
    catalog_content_hash: str
    source_identity: str
    schema_version: str


# ---------------------------------------------------------------------------
# Sizing request
# ---------------------------------------------------------------------------


class SizingApiRequest(StrictBaseModel):
    """Request to size a double-pipe exchanger against a catalog."""

    model_config = {"frozen": True, "extra": "forbid"}

    api_schema_version: Literal["1"]
    case: ValidationApiRequest
    catalog_refs: tuple[CatalogSnapshotReference, ...]
    minimum_effective_length: Length | None = None
    maximum_effective_length: Length | None = None
    request_raw_combination_cap: int | None = None
    tube_boundary_condition: Literal["constant_wall_temperature", "inner_wall_heated"]
    annulus_boundary_condition: Literal["inner_wall_heated", "constant_wall_temperature"]
    flow_arrangement: Literal["counterflow", "parallel"]
    tube_in_hot: bool = True
    duty_absolute_tolerance: Power = Field(
        default=Power(value=0, unit="W"),
    )
    duty_relative_tolerance: Dimensionless = Field(
        default=Dimensionless(value=0, unit="dimensionless"),
    )
    optimization_objective: OptimizationObjective
    requested_top_n: int = Field(ge=1)
    expected_provider_identity: ExpectedProviderIdentity
    solver_params: SolverParamsSpec | None = None
    design_case_revision_id: UUID | None = None
    calculation_run_id: UUID | None = None
    rating_software_version: str = "0.1.0"
    execution_context_policy_version: str = ""


# ---------------------------------------------------------------------------
# Resolved provider authority
# ---------------------------------------------------------------------------


class ResolvedProviderAuthority(StrictBaseModel):
    """Resolved reference to a property provider with full identity."""

    model_config = {"frozen": True, "extra": "forbid"}

    provider_ref: str
    identity: ProviderIdentitySnapshot
    identity_digest: str


__all__ = [
    "CatalogSnapshotReference",
    "DoublePipeGeometrySpec",
    "FluidStreamSpec",
    "RatingApiRequest",
    "ResolvedProviderAuthority",
    "SizingApiRequest",
    "SolverParamsSpec",
    "ThermalConductivitySpec",
    "ValidationApiRequest",
]
