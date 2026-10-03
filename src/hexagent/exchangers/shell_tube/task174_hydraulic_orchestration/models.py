"""Strict TASK174 case-bound hydraulic orchestration value models."""

from __future__ import annotations

from decimal import Decimal
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

TASK174_REQUEST_SCHEMA: Final = "task174.case-hydraulic-orchestration-request.v2"
TASK174_RESULT_SCHEMA: Final = "task174.case-hydraulic-orchestration-result.v2"
TASK174_BLOCKED_SCHEMA: Final = "task174.case-hydraulic-orchestration-blocked.v2"
TASK174_IMPLEMENTATION_VERSION: Final = "task174.hydraulic-orchestration-v2"

TOPOLOGY_ID: Final = (
    "urn:hxforge:task171:98b4bb0ce1d209b6e19ae313330b1a8d5692b2398967586d4edc1e368e9345a7"
)
TASK171_RESULT_HASH: Final = "98b4bb0ce1d209b6e19ae313330b1a8d5692b2398967586d4edc1e368e9345a7"
MESH_IDENTITY: Final = "ec4a01bbfe81cd6b12ede63c6f4e4aa05372414868cee54a54fb7c98aaffd607"
PHYSICAL_OWNERSHIP_HASH: Final = "63ea9cb1d10037dde273fc40746d6cf98604a40e41d91705f640031e5b6ec7fe"
CASE_ID: Final = "V07-T172-PROJECT-ENGINEERING-REFERENCE-CASE-R1"
CASE_REVISION_ID: Final = "V07-T172-PROJECT-ENGINEERING-REFERENCE-CASE-R2"
TASK020_CONFIGURATION_ID: Final = "96637b2b-3583-5fdd-8645-bb2b5526996a"
TASK020_CONFIGURATION_HASH: Final = (
    "04fbacd4037e4740328dd76b01caa0e85f22569924308d74b35bb13f0beb9125"
)
TASK025_RESULT_ID: Final = "6ff54552-d44e-50d2-bdf2-fe5b766c6ff9"
TASK025_RESULT_HASH: Final = "b74a037507e525e1ec647ac6a594e3723f0de07965e916b7a2eb1bb9de4dfc2a"
TASK025_HYDRAULIC_AUTHORITY_HASH: Final = (
    "2fb039ad6bc5a398ec75911c5b05b36e889d7d37a307ea424c4c7a15884365e5"
)

TUBE_PATH_MAPPING_ID: Final = "V07-T172-R119A-FLOW-PATH-MAPPING-R1"
COMPARTMENT_MAPPING_ID: Final = "V07-T172-R119A-PHYSICAL-COMPARTMENT-MAPPING-R1"
AREA_OWNERSHIP_ID: Final = "V07-T172-R119A-AREA-OWNERSHIP-R1"
LENGTH_OWNERSHIP_ID: Final = "V07-T172-R119A-LENGTH-OWNERSHIP-R1"
TASK171_MESH_AUTHORITY_ID: Final = "V07-T172-R119A-TASK171-MESH-R1"
FIV_REQUIREMENT_MODE: Final = "DIAGNOSTIC_SCREENING_ONLY"
TUBE_MODELED_BOUNDARY_AUTHORITY_ID: Final = "V07-T174-TUBE-INTERNAL-MODELED-BOUNDARY-R1"
PRESSURE_COUPLING_AUTHORITY_ID: Final = "V07-T174-REFERENCE-PRESSURE-COUPLING-R1"
EVENT_TO_BELL_REGION_AUTHORITY_ID: Final = "V07-T174-BELL-EVENT-REGION-ALLOCATION-R1"

TUBE_COMPONENT_TYPES = frozenset(
    {"ENTRANCE", "EXIT", "CHANNEL_HEAD", "NOZZLE", "CONTRACTION", "EXPANSION"}
)


class StrictModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class HydraulicComponentBinding(StrictModel):
    component_type: Literal[
        "ENTRANCE", "EXIT", "CHANNEL_HEAD", "NOZZLE", "CONTRACTION", "EXPANSION"
    ]
    component_id: str = Field(min_length=1)
    task028_result_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    component_authority_id: str = Field(min_length=1)
    component_authority_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    upstream_reference_plane: str = Field(min_length=1)
    downstream_reference_plane: str = Field(min_length=1)
    multiplicity: int = Field(gt=0)

    @model_validator(mode="after")
    def distinct_reference_planes(self) -> HydraulicComponentBinding:
        if self.upstream_reference_plane == self.downstream_reference_plane:
            raise ValueError("a modeled component must span distinct reviewed reference planes")
        return self


class PhysicalAbsenceExclusion(StrictModel):
    component_type: Literal[
        "ENTRANCE", "EXIT", "CHANNEL_HEAD", "NOZZLE", "CONTRACTION", "EXPANSION"
    ]
    exclusion_authority_id: str = Field(min_length=1)
    exclusion_authority_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_ref: str = Field(min_length=1)


class PhysicalEventBinding(StrictModel):
    physical_event_id: str = Field(min_length=1)
    physical_compartment_id: str = Field(min_length=1)
    event_role: str = Field(min_length=1)
    native_geometry_id: str = Field(min_length=1)
    native_geometry_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    physical_segment_ids: tuple[str, ...]
    multiplicity: int = Field(gt=0)


class BellEventRegionAllocation(StrictModel):
    physical_event_id: str = Field(min_length=1)
    allocation_role: Literal["ADDITIVE_PRESSURE_REGION", "CORRECTION_OR_GEOMETRY_SUPPORT"]
    bell_region_or_support_role: str = Field(min_length=1)
    task166_result_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_refs: tuple[str, ...] = Field(min_length=1)


class PressurePropertyBinding(StrictModel):
    location_id: str = Field(min_length=1)
    side: Literal["TUBE", "SHELL"]
    pressure_pa: Decimal
    property_snapshot_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("pressure_pa")
    @classmethod
    def within_reviewed_pressure_domain(cls, value: Decimal) -> Decimal:
        if type(value) is not Decimal or not value.is_finite():
            raise ValueError("pressure must be finite Decimal")
        if not Decimal("100000") <= value <= Decimal("101325"):
            raise ValueError("pressure leaves the reviewed case property domain")
        return value


class Task174CaseRequest(StrictModel):
    schema_version: Literal["task174.case-hydraulic-orchestration-request.v2"] = (
        TASK174_REQUEST_SCHEMA
    )
    case_id: Literal["V07-T172-PROJECT-ENGINEERING-REFERENCE-CASE-R1"] = CASE_ID
    case_revision_id: Literal["V07-T172-PROJECT-ENGINEERING-REFERENCE-CASE-R2"] = CASE_REVISION_ID
    topology_id: Literal[
        "urn:hxforge:task171:98b4bb0ce1d209b6e19ae313330b1a8d5692b2398967586d4edc1e368e9345a7"
    ] = TOPOLOGY_ID
    task171_result_hash: Literal[
        "98b4bb0ce1d209b6e19ae313330b1a8d5692b2398967586d4edc1e368e9345a7"
    ] = TASK171_RESULT_HASH
    mesh_identity: Literal["ec4a01bbfe81cd6b12ede63c6f4e4aa05372414868cee54a54fb7c98aaffd607"] = (
        MESH_IDENTITY
    )
    physical_ownership_hash: Literal[
        "63ea9cb1d10037dde273fc40746d6cf98604a40e41d91705f640031e5b6ec7fe"
    ] = PHYSICAL_OWNERSHIP_HASH
    flow_path_mapping_authority_id: Literal["V07-T172-R119A-FLOW-PATH-MAPPING-R1"] = (
        TUBE_PATH_MAPPING_ID
    )
    physical_compartment_mapping_authority_id: Literal[
        "V07-T172-R119A-PHYSICAL-COMPARTMENT-MAPPING-R1"
    ] = COMPARTMENT_MAPPING_ID
    area_ownership_authority_id: Literal["V07-T172-R119A-AREA-OWNERSHIP-R1"] = AREA_OWNERSHIP_ID
    length_ownership_authority_id: Literal["V07-T172-R119A-LENGTH-OWNERSHIP-R1"] = (
        LENGTH_OWNERSHIP_ID
    )
    structural_mesh_authority_id: Literal["V07-T172-R119A-TASK171-MESH-R1"] = (
        TASK171_MESH_AUTHORITY_ID
    )
    tube_component_bindings: tuple[HydraulicComponentBinding, ...] = ()
    physical_absence_exclusions: tuple[PhysicalAbsenceExclusion, ...] = ()
    physical_events: tuple[PhysicalEventBinding, ...] = ()
    bell_event_region_allocations: tuple[BellEventRegionAllocation, ...] = ()
    pressure_property_bindings: tuple[PressurePropertyBinding, ...] = ()
    tube_modeled_boundary_authority_id: Literal["V07-T174-TUBE-INTERNAL-MODELED-BOUNDARY-R1"] = (
        TUBE_MODELED_BOUNDARY_AUTHORITY_ID
    )
    pressure_coupling_authority_id: Literal["V07-T174-REFERENCE-PRESSURE-COUPLING-R1"] = (
        PRESSURE_COUPLING_AUTHORITY_ID
    )
    event_to_bell_region_authority_id: Literal["V07-T174-BELL-EVENT-REGION-ALLOCATION-R1"] = (
        EVENT_TO_BELL_REGION_AUTHORITY_ID
    )
    fiv_requirement_mode: Literal["DIAGNOSTIC_SCREENING_ONLY"] = FIV_REQUIREMENT_MODE
    fiv_array_specific_critical_velocity_limit_m_s: Decimal | None = None

    @field_validator("fiv_array_specific_critical_velocity_limit_m_s")
    @classmethod
    def optional_fiv_limit_is_explicit(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and (
            type(value) is not Decimal or not value.is_finite() or value <= 0
        ):
            raise ValueError("an FIV limit, when supplied, must be positive finite Decimal")
        return value

    @model_validator(mode="after")
    def unique_structural_events(self) -> Task174CaseRequest:
        event_ids = tuple(event.physical_event_id for event in self.physical_events)
        if len(event_ids) != len(set(event_ids)):
            raise ValueError("TASK171 physical events may be bound only once")
        if any(
            event.native_geometry_id != "279ed479-378d-5ea5-b2f0-8926133bf4dd"
            or event.native_geometry_hash
            != "68efd0e8dc69f203d49b73b2a87106863725d9a1b4a9bf1282cc1f650942d994"
            for event in self.physical_events
        ):
            raise ValueError(
                "physical events must retain the reviewed TASK024 native geometry binding"
            )
        bell_ids = tuple(
            binding.physical_event_id for binding in self.bell_event_region_allocations
        )
        if len(bell_ids) != len(set(bell_ids)):
            raise ValueError("Bell event allocations must not multiply a TASK171 physical event")
        return self


class Task174Blocker(StrictModel):
    code: str
    scope: str
    missing_bindings: tuple[str, ...]
    consumer: str


class Task174BlockedResult(StrictModel):
    schema_version: Literal["task174.case-hydraulic-orchestration-blocked.v2"] = (
        TASK174_BLOCKED_SCHEMA
    )
    status: Literal["BLOCKED"]
    request_hash: str
    tube_pressure_drop_status: Literal["VALIDATED", "BLOCKED_INCOMPLETE_MODELED_BOUNDARY"]
    shell_pressure_drop_status: Literal[
        "VALIDATED", "BLOCKED_INCOMPLETE_PHYSICAL_EVENT_AGGREGATION"
    ]
    bell_aggregation_status: Literal["VALIDATED", "BLOCKED_EVENT_TO_REGION_MAPPING"]
    pressure_coupling_status: Literal["VALIDATED", "BLOCKED_PROPERTY_PRESSURE_COUPLING_AUTHORITY"]
    fiv_status: Literal["DIAGNOSTIC_ONLY", "WARN_MISSING_NUMERIC_LIMIT"]
    fiv_numeric_limit_authority_missing: bool
    fiv_numeric_limit_not_guessed: Literal[True]
    blockers: tuple[Task174Blocker, ...]
    warnings: tuple[str, ...]
    result_hash: str
    result_id: str


class Task174SuccessResult(StrictModel):
    schema_version: Literal["task174.case-hydraulic-orchestration-result.v2"] = (
        TASK174_RESULT_SCHEMA
    )
    status: Literal["VALIDATED"]
    request_hash: str
    task029_result_id: str
    task029_result_hash: str
    task166_result_id: str
    task166_result_hash: str
    modeled_total_tube_side_pressure_drop_pa: Decimal
    bell_total_shell_pressure_drop_pa: Decimal
    bell_central_crossflow_contribution_pa: Decimal
    bell_window_contribution_pa: Decimal
    bell_inlet_end_zone_contribution_pa: Decimal
    bell_outlet_end_zone_contribution_pa: Decimal
    task034_screening_result_id: str | None = None
    task034_screening_result_hash: str | None = None
    kern_screening_pressure_drop_pa: Decimal | None = None
    tube_outlet_pressure_pa: Decimal
    shell_outlet_pressure_pa: Decimal
    bell_physical_event_count: int
    event_multiplicity_sum: int
    bell_additive_event_count: int
    bell_support_event_count: int
    pressure_coupling_authority_id: str
    fiv_status: Literal["DIAGNOSTIC_ONLY", "WARN_MISSING_NUMERIC_LIMIT"]
    fiv_numeric_limit_authority_missing: bool
    fiv_numeric_limit_not_guessed: Literal[True]
    result_hash: str
    result_id: str


__all__ = [
    "BellEventRegionAllocation",
    "HydraulicComponentBinding",
    "PhysicalAbsenceExclusion",
    "PhysicalEventBinding",
    "PressurePropertyBinding",
    "Task174Blocker",
    "Task174BlockedResult",
    "Task174CaseRequest",
    "Task174SuccessResult",
]
