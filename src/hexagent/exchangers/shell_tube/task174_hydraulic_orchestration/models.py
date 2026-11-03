"""Strict TASK174 case-bound hydraulic orchestration value models."""

from __future__ import annotations

from decimal import Decimal
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from hexagent.canonical_json import canonical_sha256

TASK174_REQUEST_SCHEMA: Final = "task174.case-hydraulic-orchestration-request.v2"
TASK174_RESULT_SCHEMA: Final = "task174.case-hydraulic-orchestration-result.v2"
TASK174_BLOCKED_SCHEMA: Final = "task174.case-hydraulic-orchestration-blocked.v2"
TASK174_IMPLEMENTATION_VERSION: Final = "task174.hydraulic-orchestration-v2"
TASK174_CANDIDATE_REQUEST_SCHEMA: Final = "task174.candidate-hydraulic-orchestration-request.v1"

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


class CandidatePhysicalAbsenceProof(StrictModel):
    """Candidate-native evidence for a component absent from this topology."""

    candidate_id: str = Field(min_length=1)
    candidate_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    task020_configuration_id: str = Field(min_length=1)
    task020_configuration_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    task021_layout_id: str = Field(min_length=1)
    task021_layout_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    task022_geometry_id: str = Field(min_length=1)
    task022_geometry_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    task024_geometry_id: str = Field(min_length=1)
    task024_geometry_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    component_type: Literal[
        "ENTRANCE", "EXIT", "CHANNEL_HEAD", "NOZZLE", "CONTRACTION", "EXPANSION"
    ]
    upstream_reference_plane: str = Field(min_length=1)
    downstream_reference_plane: str = Field(min_length=1)
    structural_reason: str = Field(min_length=1)
    exclusion_authority_id: Literal["V07-T173-SIZING-TASK174-CANDIDATE-PROJECT-TRANSFER-R1"]
    exclusion_authority_hash: Literal[
        "893a6c1644a940b27fbad85ef4d4fc402a7999971dc5e2ed3603fada0398b857"
    ]
    evidence_ref: str = Field(min_length=1)
    canonical_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def valid_boundary(self) -> CandidatePhysicalAbsenceProof:
        if self.upstream_reference_plane == self.downstream_reference_plane:
            raise ValueError("candidate absence proof must identify its equipment boundary")
        projection = self.model_dump(mode="json", exclude={"canonical_hash"})
        if self.canonical_hash != canonical_sha256(projection):
            raise ValueError("candidate physical absence proof canonical hash does not replay")
        return self


class CandidateTask174Request(StrictModel):
    """Candidate-bound TASK174 sibling; reference-case literals remain untouched."""

    schema_version: Literal["task174.candidate-hydraulic-orchestration-request.v1"] = (
        TASK174_CANDIDATE_REQUEST_SCHEMA
    )
    candidate_id: str = Field(min_length=1)
    candidate_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    authority_package_id: Literal["V07-T173-SIZING-AUTHORITY-PACKAGE-R2"]
    authority_package_hash: Literal[
        "750c1f76953f46b63de90f2c21302160746e890cf4c61227538397e69b8501a9"
    ]
    task174_candidate_authority_hash: Literal[
        "4d0f83b8ab1777ba6516dfc607c7accc814ef8a521d26c25c8cf0adc1b264023"
    ]
    task174_project_transfer_authority_hash: Literal[
        "893a6c1644a940b27fbad85ef4d4fc402a7999971dc5e2ed3603fada0398b857"
    ]
    bell_event_transfer_authority_hash: Literal[
        "28c89b6c58fef6050f9a0f5d33b80ce686f875a4ba9350e254d43ff699dccc58"
    ]
    pressure_coupling_authority_hash: Literal[
        "7506d4217d27123cdec1a5d46813445a1a8b500ef24af39e10b7598ba163ce19"
    ]
    task020_configuration_id: str = Field(min_length=1)
    task020_configuration_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    task021_layout_id: str = Field(min_length=1)
    task021_layout_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    task022_geometry_id: str = Field(min_length=1)
    task022_geometry_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    task024_geometry_id: str = Field(min_length=1)
    task024_geometry_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    task025_result_id: str = Field(min_length=1)
    task025_result_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    task025_hydraulic_authority_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    task171_topology_id: str = Field(min_length=1)
    task171_result_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    mesh_identity: str = Field(pattern=r"^[0-9a-f]{64}$")
    physical_ownership_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    task166_result_id: str = Field(min_length=1)
    task166_result_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    tube_component_bindings: tuple[HydraulicComponentBinding, ...]
    physical_absence_proofs: tuple[CandidatePhysicalAbsenceProof, ...]
    physical_events: tuple[PhysicalEventBinding, ...] = Field(min_length=1)
    bell_event_region_allocations: tuple[BellEventRegionAllocation, ...] = Field(min_length=1)
    pressure_property_bindings: tuple[PressurePropertyBinding, ...] = Field(min_length=2)
    fiv_requirement_mode: Literal["DIAGNOSTIC_SCREENING_ONLY"] = FIV_REQUIREMENT_MODE
    fiv_array_specific_critical_velocity_limit_m_s: Decimal | None = None

    @model_validator(mode="after")
    def candidate_identity_and_coverage(self) -> CandidateTask174Request:
        modeled = [item.component_type for item in self.tube_component_bindings]
        absent = [item.component_type for item in self.physical_absence_proofs]
        if len(modeled + absent) != len(TUBE_COMPONENT_TYPES):
            raise ValueError("candidate tube boundary must cover all six component classes")
        if set(modeled + absent) != TUBE_COMPONENT_TYPES:
            raise ValueError("candidate tube boundary must cover all six component classes")
        if len(set(modeled + absent)) != len(modeled + absent):
            raise ValueError("a candidate component class must be modeled or absent exactly once")
        if any(
            proof.candidate_id != self.candidate_id
            or proof.candidate_hash != self.candidate_hash
            or proof.task020_configuration_id != self.task020_configuration_id
            or proof.task020_configuration_hash != self.task020_configuration_hash
            or proof.task021_layout_id != self.task021_layout_id
            or proof.task021_layout_hash != self.task021_layout_hash
            or proof.task022_geometry_id != self.task022_geometry_id
            or proof.task022_geometry_hash != self.task022_geometry_hash
            or proof.task024_geometry_id != self.task024_geometry_id
            or proof.task024_geometry_hash != self.task024_geometry_hash
            for proof in self.physical_absence_proofs
        ):
            raise ValueError("candidate physical absence proof is stale or cross-candidate")
        event_ids = [event.physical_event_id for event in self.physical_events]
        allocation_ids = [item.physical_event_id for item in self.bell_event_region_allocations]
        if len(event_ids) != len(set(event_ids)) or set(event_ids) != set(allocation_ids):
            raise ValueError("candidate TASK171 physical events need exact-once Bell allocation")
        if len(allocation_ids) != len(set(allocation_ids)):
            raise ValueError("candidate TASK171 event may not be allocated more than once")
        if any(
            event.native_geometry_id != self.task024_geometry_id
            or event.native_geometry_hash != self.task024_geometry_hash
            for event in self.physical_events
        ):
            raise ValueError("candidate physical events must bind its native TASK024 geometry")
        by_id = {event.physical_event_id: event for event in self.physical_events}
        expected_roles = {
            "CENTRAL_CROSSFLOW": ("ADDITIVE_PRESSURE_REGION", "BELL_CENTRAL_CROSSFLOW_REGION"),
            "WINDOW": ("ADDITIVE_PRESSURE_REGION", "BELL_WINDOW_REGION"),
            "INLET_END_ZONE": ("ADDITIVE_PRESSURE_REGION", "BELL_INLET_END_ZONE"),
            "OUTLET_END_ZONE": ("ADDITIVE_PRESSURE_REGION", "BELL_OUTLET_END_ZONE"),
            "BAFFLE": ("CORRECTION_OR_GEOMETRY_SUPPORT", "BAFFLE_GEOMETRY_SUPPORT"),
            "LEAKAGE_GEOMETRY": (
                "CORRECTION_OR_GEOMETRY_SUPPORT",
                "RL_LEAKAGE_CORRECTION_SUPPORT",
            ),
            "BYPASS_GEOMETRY": ("CORRECTION_OR_GEOMETRY_SUPPORT", "RB_BYPASS_CORRECTION_SUPPORT"),
            "TUBE_ROW_OR_CROSSED_ROW": (
                "CORRECTION_OR_GEOMETRY_SUPPORT",
                "CROSS_FLOW_ROW_COUNT_SUPPORT",
            ),
        }
        for allocation in self.bell_event_region_allocations:
            event = by_id[allocation.physical_event_id]
            if allocation.task166_result_hash != self.task166_result_hash or expected_roles.get(
                event.event_role
            ) != (allocation.allocation_role, allocation.bell_region_or_support_role):
                raise ValueError("candidate Bell event allocation does not match native event role")
        pressure_sides = [item.side for item in self.pressure_property_bindings]
        if set(pressure_sides) != {"TUBE", "SHELL"} or len(pressure_sides) != 2:
            raise ValueError("candidate must bind one frozen reference pressure per side")
        if any(item.pressure_pa != Decimal("101325") for item in self.pressure_property_bindings):
            raise ValueError("candidate pressure coupling is frozen at 101325 Pa")
        if self.fiv_array_specific_critical_velocity_limit_m_s is not None and (
            not self.fiv_array_specific_critical_velocity_limit_m_s.is_finite()
            or self.fiv_array_specific_critical_velocity_limit_m_s <= 0
        ):
            raise ValueError("explicit FIV diagnostic limit must be positive and finite")
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
    "CandidatePhysicalAbsenceProof",
    "CandidateTask174Request",
    "HydraulicComponentBinding",
    "PhysicalAbsenceExclusion",
    "PhysicalEventBinding",
    "PressurePropertyBinding",
    "Task174Blocker",
    "Task174BlockedResult",
    "Task174CaseRequest",
    "Task174SuccessResult",
]
