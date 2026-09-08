"""Immutable TASK-167 request, screen, result, and provenance models."""

from __future__ import annotations

import enum
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from hexagent.exchangers.shell_tube.bell_delaware.models import Task166Result
from hexagent.exchangers.shell_tube.models import (
    AuthorityMode,
    ShellAndTubeConfiguration,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.result import TubeSideThermalResult

from .authority import (
    BLOCKED_RESULT_SCHEMA_VERSION,
    DEFERRED_CAPABILITIES,
    IMPLEMENTATION_SOFTWARE_VERSION,
    RAW_BLOCKED_RESULT_SCHEMA_VERSION,
    RESULT_SCHEMA_VERSION,
    TASK167_VERSION,
)
from .errors import Blocker, FailureStage


class ValidationStatus(enum.StrEnum):
    RAW_BOUNDARY_BLOCKED = "RAW_BOUNDARY_BLOCKED"
    TYPED_BLOCKED = "TYPED_BLOCKED"
    VALID = "VALID"


class ScreenStatus(enum.StrEnum):
    PASS = "PASS"
    WARN = "WARN"
    BLOCKED = "BLOCKED"


class FIVStatus(enum.StrEnum):
    WARN = "WARN"
    BLOCKED = "BLOCKED"


class FoulingTendency(enum.StrEnum):
    NONE = "NONE"
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    UNSPECIFIED = "UNSPECIFIED"


@dataclass(frozen=True)
class ScreeningRequirements:
    """Explicit project requirements; never anonymous numerical limits."""

    shell_side_fouling_tendency: FoulingTendency = FoulingTendency.UNSPECIFIED
    tube_side_fouling_tendency: FoulingTendency = FoulingTendency.UNSPECIFIED
    shell_side_mechanical_cleaning_required: bool | None = None
    tube_side_mechanical_cleaning_required: bool | None = None
    thermal_expansion_accommodation_required: bool | None = None
    removable_bundle_required: bool | None = None
    nozzle_velocity_screen_required: bool = False
    authority_mode: AuthorityMode = AuthorityMode.INTERNAL_GENERIC
    requirement_id: str = ""
    source_id: str = ""
    source_version: str = ""
    evidence_ref: str = ""
    snapshot_hash: str = ""


@dataclass(frozen=True)
class ScreeningPropertySnapshot:
    """Source-bound optional screening properties.

    Missing values mean that the corresponding diagnostic is not computed;
    no default material, damping, temperature, or density is invented.
    """

    snapshot_id: str = ""
    source_id: str = ""
    source_version: str = ""
    evidence_ref: str = ""
    snapshot_hash: str = ""
    fluid_density_kg_m3: Decimal | None = None
    shell_bulk_velocity_m_s: Decimal | None = None
    shell_crossflow_velocity_m_s: Decimal | None = None
    nozzle_mass_flow_rate_kg_s: Decimal | None = None
    nozzle_density_kg_m3: Decimal | None = None
    tube_free_span_m: Decimal | None = None
    tube_material_density_kg_m3: Decimal | None = None
    tube_mass_per_length_kg_m: Decimal | None = None
    young_modulus_pa: Decimal | None = None
    damping_ratio: Decimal | None = None
    coefficient_thermal_expansion_per_k: Decimal | None = None
    reference_temperature_k: Decimal | None = None
    effective_shell_temperature_k: Decimal | None = None
    effective_tube_temperature_k: Decimal | None = None
    effective_length_m: Decimal | None = None
    added_mass_kg_m: Decimal | None = None
    natural_frequency_hz: Decimal | None = None


@dataclass(frozen=True)
class NozzleGeometryAuthority:
    authority_id: str
    source_id: str
    source_version: str
    evidence_ref: str
    snapshot_hash: str
    flow_area_m2: Decimal


@dataclass(frozen=True)
class ScreenRecord:
    screen_id: str
    status: ScreenStatus
    authority_mode: AuthorityMode
    source_id: str
    rule_id: str | None
    diagnostic_values: tuple[tuple[str, str], ...]
    limit_values: tuple[tuple[str, str], ...]
    reason_code: str
    standard_claim: bool
    applicability: tuple[str, ...]
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True)
class FIVScreen:
    crossflow_velocity_m_s: Decimal | None = None
    tube_span_m: Decimal | None = None
    tube_outer_diameter_m: Decimal | None = None
    pitch_m: Decimal | None = None
    fluid_density_kg_m3: Decimal | None = None
    tube_mass_per_length_kg_m: Decimal | None = None
    added_mass_kg_m: Decimal | None = None
    effective_mass_kg_m: Decimal | None = None
    natural_frequency_hz: Decimal | None = None
    reduced_velocity: Decimal | None = None
    mass_damping_parameter: Decimal | None = None
    critical_velocity_m_s: Decimal | None = None
    critical_velocity_ratio: Decimal | None = None
    status: FIVStatus = FIVStatus.WARN
    numeric_limit_authority_missing: bool = True
    numeric_limit_not_guessed: bool = True
    source_id: str = ""
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class ApplicabilityCheck:
    check_id: str
    status: str
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class ApplicabilityLedger:
    checks: tuple[ApplicabilityCheck, ...]
    status: str


@dataclass(frozen=True)
class CompletenessLedger:
    required_fields: tuple[str, ...]
    present_fields: tuple[str, ...]
    status: str


@dataclass(frozen=True)
class ProvenanceNode:
    node_id: str
    payload_hash: str


@dataclass(frozen=True)
class ProvenanceEdge:
    source_node_id: str
    relation: str
    target_node_id: str


@dataclass(frozen=True)
class ProvenanceGraph:
    nodes: tuple[ProvenanceNode, ...]
    edges: tuple[ProvenanceEdge, ...]
    graph_hash: str
    self_edge_count: int = 0
    cycle_count: int = 0


@dataclass(frozen=True)
class Task167Request:
    schema_version: str
    task167_version: str
    source_definition_id: str
    task020_configuration: ShellAndTubeConfiguration
    task166_result: Task166Result
    tube_side_result: TubeSideThermalResult
    screening_requirements: ScreeningRequirements
    screening_property_snapshot: ScreeningPropertySnapshot
    nozzle_geometry: NozzleGeometryAuthority | None = None
    approved_rule_pack_authority: Any | None = None
    request_metadata: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class Task167Result:
    schema_version: str = RESULT_SCHEMA_VERSION
    task167_version: str = TASK167_VERSION
    implementation_software_version: str = IMPLEMENTATION_SOFTWARE_VERSION
    source_definition_id: str = ""
    request_hash: str = ""
    configuration_evidence: tuple[tuple[str, str], ...] = ()
    task166_evidence: tuple[tuple[str, str], ...] = ()
    tube_side_evidence: tuple[tuple[str, str], ...] = ()
    screening_requirements_evidence: tuple[tuple[str, str], ...] = ()
    screening_property_evidence: tuple[tuple[str, str], ...] = ()
    nozzle_geometry_evidence: tuple[tuple[str, str], ...] = ()
    velocity_screens: tuple[ScreenRecord, ...] = ()
    erosion_screen: ScreenRecord | None = None
    fouling_cleanability_screen: ScreenRecord | None = None
    thermal_expansion_screen: ScreenRecord | None = None
    construction_family_suitability_screen: ScreenRecord | None = None
    fiv_screen: FIVScreen | None = None
    aggregate_screening_status: ScreenStatus = ScreenStatus.BLOCKED
    warnings: tuple[str, ...] = ()
    blockers: tuple[Blocker, ...] = ()
    deferred_capabilities: tuple[str, ...] = DEFERRED_CAPABILITIES
    applicability: ApplicabilityLedger | None = None
    completeness: CompletenessLedger | None = None
    provenance_semantic_inputs: tuple[tuple[str, str], ...] = ()
    provenance: ProvenanceGraph | None = None
    result_hash: str = ""
    result_id: str = ""


@dataclass(frozen=True)
class Task167BlockedResult:
    schema_version: str = BLOCKED_RESULT_SCHEMA_VERSION
    task167_version: str = TASK167_VERSION
    implementation_software_version: str = IMPLEMENTATION_SOFTWARE_VERSION
    failure_stage: FailureStage = FailureStage.TYPED_VALIDATION
    request_hash: str = ""
    blockers: tuple[Blocker, ...] = ()
    warnings: tuple[str, ...] = ()
    deferred_capabilities: tuple[str, ...] = DEFERRED_CAPABILITIES
    result_hash: str = ""
    result_id: str = ""
    provenance: None = None


@dataclass(frozen=True)
class Task167RawBoundaryBlockedResult:
    schema_version: str = RAW_BLOCKED_RESULT_SCHEMA_VERSION
    task167_version: str = TASK167_VERSION
    implementation_software_version: str = IMPLEMENTATION_SOFTWARE_VERSION
    raw_request_projection_hash: str = ""
    blockers: tuple[Blocker, ...] = ()
    warnings: tuple[str, ...] = ()
    deferred_capabilities: tuple[str, ...] = DEFERRED_CAPABILITIES
    result_hash: str = ""
    result_id: str = ""
    provenance: None = None


@dataclass(frozen=True)
class Task167ValidationResult:
    status: ValidationStatus
    raw_boundary_blocked: Task167RawBoundaryBlockedResult | None = None
    typed_blocked: Task167BlockedResult | None = None
    valid: Task167Result | None = None

    def __post_init__(self) -> None:
        populated = sum(
            item is not None for item in (self.raw_boundary_blocked, self.typed_blocked, self.valid)
        )
        if populated != 1:
            raise ValueError("TASK-167 validation result must populate exactly one branch")
        if (
            self.status is ValidationStatus.RAW_BOUNDARY_BLOCKED
            and self.raw_boundary_blocked is None
        ):
            raise ValueError("raw boundary status requires raw_boundary_blocked")
        if self.status is ValidationStatus.TYPED_BLOCKED and self.typed_blocked is None:
            raise ValueError("typed blocked status requires typed_blocked")
        if self.status is ValidationStatus.VALID and self.valid is None:
            raise ValueError("valid status requires valid")


REQUEST_FIELDS: tuple[str, ...] = (
    "schema_version",
    "task167_version",
    "source_definition_id",
    "task020_configuration",
    "task166_result",
    "tube_side_result",
    "screening_requirements",
    "screening_property_snapshot",
    "nozzle_geometry",
    "approved_rule_pack_authority",
    "request_metadata",
)

__all__ = [
    "ApplicabilityCheck",
    "ApplicabilityLedger",
    "CompletenessLedger",
    "FIVScreen",
    "FIVStatus",
    "FoulingTendency",
    "NozzleGeometryAuthority",
    "ProvenanceEdge",
    "ProvenanceGraph",
    "ProvenanceNode",
    "REQUEST_FIELDS",
    "ScreenRecord",
    "ScreenStatus",
    "ScreeningPropertySnapshot",
    "ScreeningRequirements",
    "Task167BlockedResult",
    "Task167RawBoundaryBlockedResult",
    "Task167Request",
    "Task167Result",
    "Task167ValidationResult",
    "ValidationStatus",
]
