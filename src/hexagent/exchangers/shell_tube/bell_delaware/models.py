"""Immutable TASK-166 request, geometry, result, and evidence models."""

from __future__ import annotations

import enum
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from .authority import (
    BLOCKED_RESULT_SCHEMA_VERSION,
    IMPLEMENTATION_SOFTWARE_VERSION,
    RAW_BOUNDARY_BLOCKED_RESULT_SCHEMA_VERSION,
    RESULT_SCHEMA_VERSION,
)
from .errors import Blocker, FailureStage


class ValidationStatus(enum.StrEnum):
    RAW_BOUNDARY_BLOCKED = "RAW_BOUNDARY_BLOCKED"
    TYPED_BLOCKED = "TYPED_BLOCKED"
    VALID = "VALID"


class ApplicabilityStatus(enum.StrEnum):
    APPLICABLE = "APPLICABLE"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class ApplicabilityCheck:
    check_id: str
    status: str
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class ApplicabilityLedger:
    checks: tuple[ApplicabilityCheck, ...]
    status: ApplicabilityStatus


@dataclass(frozen=True)
class CompletenessLedger:
    required_fields: tuple[str, ...]
    present_fields: tuple[str, ...]
    status: str


@dataclass(frozen=True)
class FactorEvidence:
    factor_id: str
    factor_version: str
    source_id: str
    source_location: str
    applicability: tuple[str, ...]
    input_projection: tuple[tuple[str, str], ...]
    value: Decimal


@dataclass(frozen=True)
class BellGeometry:
    shell_inside_diameter_m: Decimal
    bundle_outer_diameter_m: Decimal
    tube_outer_diameter_m: Decimal
    tube_pitch_m: Decimal
    baffle_cut_fraction: Decimal
    baffle_count: int
    central_baffle_spacing_m: Decimal
    inlet_baffle_spacing_m: Decimal
    outlet_baffle_spacing_m: Decimal
    shell_to_bundle_diametral_clearance_m: Decimal
    shell_to_baffle_diametral_clearance_m: Decimal
    tube_to_baffle_hole_diametral_clearance_m: Decimal
    tube_count: Decimal
    layout_id: str
    layout_angle: str
    theta_ctl_rad: Decimal
    theta_ds_rad: Decimal
    window_tube_fraction: Decimal
    pure_crossflow_tube_fraction: Decimal
    central_crossflow_tube_rows: Decimal
    window_tube_rows: Decimal
    total_crossflow_tube_rows: Decimal
    window_tube_count: Decimal
    gross_window_flow_area_m2: Decimal
    window_tube_area_m2: Decimal
    central_crossflow_flow_area_m2: Decimal
    window_flow_area_m2: Decimal
    shell_to_baffle_leakage_area_m2: Decimal
    tube_to_baffle_leakage_area_m2: Decimal
    total_leakage_area_m2: Decimal
    bundle_bypass_area_m2: Decimal
    shell_leakage_fraction: Decimal
    leakage_area_ratio: Decimal
    bypass_area_ratio: Decimal
    effective_tube_pitch_m: Decimal
    window_hydraulic_diameter_m: Decimal
    source_formula_ids: tuple[str, ...]


@dataclass(frozen=True)
class HeatTransferCalculation:
    ideal_crossflow_heat_transfer_coefficient: Decimal
    j_c: Decimal
    j_l: Decimal
    j_b: Decimal
    j_s: Decimal
    j_r: Decimal
    corrected_shell_side_heat_transfer_coefficient: Decimal
    parameter_row_identity: str
    a1: Decimal
    a2: Decimal
    a3: Decimal
    a4: Decimal
    factor_evidence: tuple[FactorEvidence, ...]


@dataclass(frozen=True)
class PressureDropCalculation:
    ideal_crossflow_pressure_drop: Decimal
    crossflow_pressure_drop: Decimal
    window_pressure_drop: Decimal
    end_zone_pressure_drop: Decimal
    r_l: Decimal
    r_b: Decimal
    r_s: Decimal
    total_shell_pressure_drop: Decimal
    central_crossflow_contribution: Decimal
    window_contribution: Decimal
    entrance_zone_contribution: Decimal
    exit_zone_contribution: Decimal
    parameter_row_identity: str
    b1: Decimal
    b2: Decimal
    b3: Decimal
    b4: Decimal
    factor_evidence: tuple[FactorEvidence, ...]


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
class Task166Request:
    schema_version: str
    task166_version: str
    source_definition_id: str
    task020_configuration: Mapping[str, Any]
    tube_layout: Mapping[str, Any]
    shell_bundle_geometry: Mapping[str, Any]
    baffle_geometry: Mapping[str, Any]
    shell_side_hydraulic_geometry: Mapping[str, Any]
    shell_side_flow_state: Mapping[str, Any]
    shell_side_flow_state_request: Mapping[str, Any]
    request_metadata: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class Task166Result:
    schema_version: str = RESULT_SCHEMA_VERSION
    task166_version: str = "1.0"
    implementation_software_version: str = IMPLEMENTATION_SOFTWARE_VERSION
    source_definition_id: str = ""
    request_hash: str = ""
    task020_evidence: tuple[tuple[str, str], ...] = ()
    tube_layout_evidence: tuple[tuple[str, str], ...] = ()
    shell_bundle_evidence: tuple[tuple[str, str], ...] = ()
    baffle_evidence: tuple[tuple[str, str], ...] = ()
    shell_side_hydraulic_evidence: tuple[tuple[str, str], ...] = ()
    shell_side_flow_evidence: tuple[tuple[str, str], ...] = ()
    bell_geometry: BellGeometry | None = None
    ideal_crossflow_heat_transfer_coefficient: Decimal = Decimal("0")
    j_c: Decimal = Decimal("0")
    j_l: Decimal = Decimal("0")
    j_b: Decimal = Decimal("0")
    j_s: Decimal = Decimal("0")
    j_r: Decimal = Decimal("0")
    corrected_shell_side_heat_transfer_coefficient: Decimal = Decimal("0")
    ideal_crossflow_pressure_drop: Decimal = Decimal("0")
    crossflow_pressure_drop: Decimal = Decimal("0")
    window_pressure_drop: Decimal = Decimal("0")
    end_zone_pressure_drop: Decimal = Decimal("0")
    central_crossflow_contribution: Decimal = Decimal("0")
    window_contribution: Decimal = Decimal("0")
    entrance_zone_contribution: Decimal = Decimal("0")
    exit_zone_contribution: Decimal = Decimal("0")
    r_l: Decimal = Decimal("0")
    r_b: Decimal = Decimal("0")
    r_s: Decimal = Decimal("0")
    total_shell_pressure_drop: Decimal = Decimal("0")
    heat_transfer_parameter_row_identity: str = ""
    heat_transfer_parameter_source_id: str = ""
    heat_transfer_a1: Decimal = Decimal("0")
    heat_transfer_a2: Decimal = Decimal("0")
    heat_transfer_a3: Decimal = Decimal("0")
    heat_transfer_a4: Decimal = Decimal("0")
    pressure_drop_parameter_row_identity: str = ""
    pressure_drop_parameter_source_id: str = ""
    pressure_drop_b1: Decimal = Decimal("0")
    pressure_drop_b2: Decimal = Decimal("0")
    pressure_drop_b3: Decimal = Decimal("0")
    pressure_drop_b4: Decimal = Decimal("0")
    factor_evidence: tuple[FactorEvidence, ...] = ()
    applicability: ApplicabilityLedger | None = None
    completeness: CompletenessLedger | None = None
    warnings: tuple[str, ...] = ()
    blockers: tuple[Blocker, ...] = ()
    provenance_semantic_inputs: tuple[tuple[str, str], ...] = ()
    provenance: ProvenanceGraph | None = None
    result_hash: str = ""
    result_id: str = ""


@dataclass(frozen=True)
class Task166BlockedResult:
    schema_version: str = BLOCKED_RESULT_SCHEMA_VERSION
    task166_version: str = "1.0"
    implementation_software_version: str = IMPLEMENTATION_SOFTWARE_VERSION
    failure_stage: FailureStage = FailureStage.TYPED_VALIDATION
    request_hash: str = ""
    blockers: tuple[Blocker, ...] = ()
    warnings: tuple[str, ...] = ()
    result_hash: str = ""
    result_id: str = ""
    provenance: None = None


@dataclass(frozen=True)
class Task166RawBoundaryBlockedResult:
    schema_version: str = RAW_BOUNDARY_BLOCKED_RESULT_SCHEMA_VERSION
    task166_version: str = "1.0"
    implementation_software_version: str = IMPLEMENTATION_SOFTWARE_VERSION
    raw_request_projection_hash: str = ""
    blockers: tuple[Blocker, ...] = ()
    warnings: tuple[str, ...] = ()
    result_hash: str = ""
    result_id: str = ""
    provenance: None = None


@dataclass(frozen=True)
class Task166ValidationResult:
    status: ValidationStatus
    raw_boundary_blocked: Task166RawBoundaryBlockedResult | None = None
    typed_blocked: Task166BlockedResult | None = None
    valid: Task166Result | None = None

    def __post_init__(self) -> None:
        populated = sum(
            value is not None
            for value in (self.raw_boundary_blocked, self.typed_blocked, self.valid)
        )
        if populated != 1:
            raise ValueError("TASK-166 validation result must populate exactly one branch")


REQUEST_FIELDS: tuple[str, ...] = (
    "schema_version",
    "task166_version",
    "source_definition_id",
    "task020_configuration",
    "tube_layout",
    "shell_bundle_geometry",
    "baffle_geometry",
    "shell_side_hydraulic_geometry",
    "shell_side_flow_state",
    "shell_side_flow_state_request",
    "request_metadata",
)

__all__ = [
    "ApplicabilityCheck",
    "ApplicabilityLedger",
    "ApplicabilityStatus",
    "BellGeometry",
    "CompletenessLedger",
    "FactorEvidence",
    "HeatTransferCalculation",
    "PressureDropCalculation",
    "ProvenanceEdge",
    "ProvenanceGraph",
    "ProvenanceNode",
    "REQUEST_FIELDS",
    "Task166BlockedResult",
    "Task166RawBoundaryBlockedResult",
    "Task166Request",
    "Task166Result",
    "Task166ValidationResult",
    "ValidationStatus",
]
