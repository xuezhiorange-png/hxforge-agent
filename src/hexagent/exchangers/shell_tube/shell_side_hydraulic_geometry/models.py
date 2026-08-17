# ruff: noqa: E501
"""TASK-031 domain models."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any

from hexagent.exchangers.shell_tube.baffle_geometry.models import (
    BaffleGeometry,
    BaffleGeometryValidationResult,
)
from hexagent.exchangers.shell_tube.tube_layout.canonical import (
    freeze_known_fragment,
    freeze_known_optional_fragment,
)
from hexagent.exchangers.shell_tube.tube_layout.models import TubeLayout

REQUEST_SCHEMA_VERSION = "task031.shell-side-hydraulic-geometry-request.v1"
RESULT_SCHEMA_VERSION = "task031.shell-side-hydraulic-geometry.v1"
ENGINEERING_AUTHORITY_SCHEMA_VERSION = "task031.engineering-authority.v1"
ENGINEERING_AUTHORITY_REQUEST_SCHEMA_VERSION = "task031.engineering-authority-request.v1"
PROFILE_ID = "hxforge.shell_tube.shell_side_hydraulic_geometry.v1"
DESIGN_CONTRACT_PATH = (
    "docs/tasks/TASK-031-shell-and-tube-shell-side-flow-path-hydraulic-geometry.md"
)
FLOW_REGION_IDENTITY = "CENTRAL_CROSSFLOW_SCREENING"
FORMULA_A_ID = "TASK031_CF_AREA_KERN_SCREENING_INTCHOPN_EQ55_56_V1"
FORMULA_B_ID = "TASK031_DE_KERN_SCREENING_INTCHOPN_EQ51_BRANCH_V1"
AGGREGATE_AUTHORITY_PROFILE_ID = "TASK031_CENTRAL_CROSSFLOW_SCREENING_GEOMETRY_V1_FORMULA_AUTHORITY"

DEFERRED_CAPABILITIES: tuple[str, ...] = (
    "WINDOW_FLOW_AREA_NOT_COMPUTABLE",
    "PER_COMPARTMENT_CROSSFLOW_AREA_SET_NOT_COMPUTABLE",
    "MINIMUM_ADMITTED_FLOW_AREA_NOT_COMPUTABLE",
    "INLET_REGION_FLOW_AREA_NOT_COMPUTABLE",
    "OUTLET_REGION_FLOW_AREA_NOT_COMPUTABLE",
    "LEAKAGE_FLOW_AREA_NOT_COMPUTABLE",
    "BYPASS_FLOW_AREA_NOT_COMPUTABLE",
    "SHELL_SIDE_FLOW_STATE_NOT_COMPUTABLE",
    "SHELL_SIDE_HEAT_TRANSFER_SCREENING_NOT_COMPUTABLE",
    "SHELL_SIDE_PRESSURE_DROP_SCREENING_NOT_COMPUTABLE",
    "BELL_DELAWARE_NOT_COMPUTABLE",
    "OVERALL_U_NOT_COMPUTABLE",
    "UA_NOT_COMPUTABLE",
    "LMTD_NOT_COMPUTABLE",
    "HEAT_DUTY_NOT_COMPUTABLE",
    "OUTLET_TEMPERATURES_NOT_COMPUTABLE",
    "FULL_EXCHANGER_RATING_NOT_COMPUTABLE",
)


class ValidationStatus(enum.StrEnum):
    VALID = "VALID"
    BLOCKED = "BLOCKED"


class BlockerCode(enum.StrEnum):
    SSHG_SCHEMA_VERSION_UNSUPPORTED = "SSHG_SCHEMA_VERSION_UNSUPPORTED"
    SSHG_RAW_TYPE_INVALID = "SSHG_RAW_TYPE_INVALID"
    SSHG_UNKNOWN_FIELD = "SSHG_UNKNOWN_FIELD"
    SSHG_DECIMAL_LEXICAL_INVALID = "SSHG_DECIMAL_LEXICAL_INVALID"
    SSHG_EVIDENCE_REFS_INVALID = "SSHG_EVIDENCE_REFS_INVALID"
    SSHG_TASK021_LAYOUT_MISSING = "SSHG_TASK021_LAYOUT_MISSING"
    SSHG_TASK021_LAYOUT_INVALID = "SSHG_TASK021_LAYOUT_INVALID"
    SSHG_TASK021_LAYOUT_HAS_BLOCKERS = "SSHG_TASK021_LAYOUT_HAS_BLOCKERS"
    SSHG_TASK021_LAYOUT_IDENTITY_MISMATCH = "SSHG_TASK021_LAYOUT_IDENTITY_MISMATCH"
    SSHG_TASK024_RESULT_MISSING = "SSHG_TASK024_RESULT_MISSING"
    SSHG_TASK024_RESULT_INVALID = "SSHG_TASK024_RESULT_INVALID"
    SSHG_TASK024_RESULT_HAS_BLOCKERS = "SSHG_TASK024_RESULT_HAS_BLOCKERS"
    SSHG_TASK024_GEOMETRY_MISSING = "SSHG_TASK024_GEOMETRY_MISSING"
    SSHG_TASK024_IDENTITY_MISMATCH = "SSHG_TASK024_IDENTITY_MISMATCH"
    SSHG_TASK021_TASK024_TUBE_OD_MISMATCH = "SSHG_TASK021_TASK024_TUBE_OD_MISMATCH"
    SSHG_UPSTREAM_CONFIGURATION_BINDING_MISMATCH = "SSHG_UPSTREAM_CONFIGURATION_BINDING_MISMATCH"
    SSHG_UPSTREAM_LAYOUT_BINDING_MISMATCH = "SSHG_UPSTREAM_LAYOUT_BINDING_MISMATCH"
    SSHG_CONSTRUCTION_FAMILY_UNSUPPORTED = "SSHG_CONSTRUCTION_FAMILY_UNSUPPORTED"
    SSHG_SHELL_PASS_COUNT_UNSUPPORTED = "SSHG_SHELL_PASS_COUNT_UNSUPPORTED"
    SSHG_BAFFLE_TYPE_UNSUPPORTED = "SSHG_BAFFLE_TYPE_UNSUPPORTED"
    SSHG_BAFFLE_COUNT_INSUFFICIENT = "SSHG_BAFFLE_COUNT_INSUFFICIENT"
    SSHG_SPACING_SEQUENCE_INVALID = "SSHG_SPACING_SEQUENCE_INVALID"
    SSHG_CENTRAL_INTER_BAFFLE_SPACING_ABSENT = "SSHG_CENTRAL_INTER_BAFFLE_SPACING_ABSENT"
    SSHG_CENTRAL_INTER_BAFFLE_SPACING_NONUNIFORM = "SSHG_CENTRAL_INTER_BAFFLE_SPACING_NONUNIFORM"
    SSHG_PATTERN_FAMILY_UNSUPPORTED = "SSHG_PATTERN_FAMILY_UNSUPPORTED"
    SSHG_ENGINEERING_AUTHORITY_IDENTITY_MISMATCH = "SSHG_ENGINEERING_AUTHORITY_IDENTITY_MISMATCH"
    SSHG_PITCH_INVALID = "SSHG_PITCH_INVALID"
    SSHG_TUBE_OD_INVALID = "SSHG_TUBE_OD_INVALID"
    SSHG_PITCH_NOT_GREATER_THAN_TUBE_OD = "SSHG_PITCH_NOT_GREATER_THAN_TUBE_OD"
    SSHG_SHELL_INSIDE_DIAMETER_INVALID = "SSHG_SHELL_INSIDE_DIAMETER_INVALID"
    SSHG_CENTRAL_INTER_BAFFLE_SPACING_INVALID = "SSHG_CENTRAL_INTER_BAFFLE_SPACING_INVALID"
    SSHG_FORMULA_DOMAIN_VIOLATION = "SSHG_FORMULA_DOMAIN_VIOLATION"
    SSHG_FORMULA_CALCULATION_FAILED = "SSHG_FORMULA_CALCULATION_FAILED"
    SSHG_PUBLIC_AREA_QUANTIZATION_COLLISION = "SSHG_PUBLIC_AREA_QUANTIZATION_COLLISION"
    SSHG_PUBLIC_DIAMETER_QUANTIZATION_COLLISION = "SSHG_PUBLIC_DIAMETER_QUANTIZATION_COLLISION"
    SSHG_CANONICALIZATION_FAILED = "SSHG_CANONICALIZATION_FAILED"


class WarningCode(enum.StrEnum):
    SSHG_CENTRAL_CROSSFLOW_SCREENING_GEOMETRY_ONLY = (
        "SSHG_CENTRAL_CROSSFLOW_SCREENING_GEOMETRY_ONLY"
    )
    SSHG_LEAKAGE_BYPASS_CORRECTIONS_EXCLUDED = "SSHG_LEAKAGE_BYPASS_CORRECTIONS_EXCLUDED"
    SSHG_MINIMUM_AREA_SELECTION_DEFERRED = "SSHG_MINIMUM_AREA_SELECTION_DEFERRED"
    SSHG_WINDOW_INLET_OUTLET_FLOW_AREAS_DEFERRED = "SSHG_WINDOW_INLET_OUTLET_FLOW_AREAS_DEFERRED"
    SSHG_FLOW_STATE_THERMAL_PRESSURE_DROP_DEFERRED = (
        "SSHG_FLOW_STATE_THERMAL_PRESSURE_DROP_DEFERRED"
    )
    SSHG_NO_FULL_EXCHANGER_RATING_CLAIM = "SSHG_NO_FULL_EXCHANGER_RATING_CLAIM"
    SSHG_FORMULA_AUTHORITY_SCREENING_MODEL_ONLY = "SSHG_FORMULA_AUTHORITY_SCREENING_MODEL_ONLY"


BLOCKER_CODES: frozenset[str] = frozenset(item.value for item in BlockerCode)
WARNING_CODES: frozenset[str] = frozenset(item.value for item in WarningCode)


@dataclass(frozen=True)
class MessageEntry:
    code: str
    field_path: str | None
    message_key: str
    evidence_refs: tuple[str, ...] = field(default_factory=tuple)
    details: tuple[tuple[str, str], ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class EngineeringAuthorityRequestBinding:
    schema_version: str
    authority_profile_id: str
    authority_hash: str
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True)
class ShellSideHydraulicGeometryRequest:
    schema_version: str
    tube_layout: TubeLayout
    baffle_geometry_result: BaffleGeometryValidationResult
    engineering_authority: EngineeringAuthorityRequestBinding
    evidence_refs: tuple[str, ...]
    raw_baffle_geometry_result: dict[str, Any] | None = None


@dataclass(frozen=True)
class ShellSideHydraulicGeometry:
    schema_version: str
    geometry_id: str
    geometry_hash: str
    request_hash: str
    task020_configuration_id: str
    task020_configuration_hash: str
    task021_layout_id: str
    task021_layout_hash: str
    task022_geometry_id: str
    task022_geometry_hash: str
    task024_geometry_id: str
    task024_geometry_hash: str
    engineering_authority_id: str
    engineering_authority_hash: str
    formula_a_id: str
    formula_b_id: str
    pattern_family: str
    flow_region_identity: str
    central_inter_baffle_spacing_m: str
    central_crossflow_flow_area_m2: str
    shell_side_equivalent_hydraulic_diameter_m: str
    warnings: tuple[MessageEntry, ...]
    blockers: tuple[MessageEntry, ...]
    deferred_capabilities: tuple[str, ...]
    provenance: tuple[tuple[str, Any], ...]


@dataclass(frozen=True)
class ShellSideHydraulicGeometryValidationResult:
    status: ValidationStatus
    geometry: ShellSideHydraulicGeometry | None
    warnings: tuple[MessageEntry, ...]
    blockers: tuple[MessageEntry, ...]
    deferred_capabilities: tuple[str, ...] = DEFERRED_CAPABILITIES
    blocked_result_hash: str | None = None


__all__ = [
    "AGGREGATE_AUTHORITY_PROFILE_ID",
    "BaffleGeometry",
    "BaffleGeometryValidationResult",
    "BLOCKER_CODES",
    "BlockerCode",
    "DEFERRED_CAPABILITIES",
    "DESIGN_CONTRACT_PATH",
    "ENGINEERING_AUTHORITY_REQUEST_SCHEMA_VERSION",
    "ENGINEERING_AUTHORITY_SCHEMA_VERSION",
    "EngineeringAuthorityRequestBinding",
    "FLOW_REGION_IDENTITY",
    "FORMULA_A_ID",
    "FORMULA_B_ID",
    "MessageEntry",
    "PROFILE_ID",
    "REQUEST_SCHEMA_VERSION",
    "RESULT_SCHEMA_VERSION",
    "ShellSideHydraulicGeometry",
    "ShellSideHydraulicGeometryRequest",
    "ShellSideHydraulicGeometryValidationResult",
    "TubeLayout",
    "ValidationStatus",
    "WARNING_CODES",
    "WarningCode",
    "freeze_known_fragment",
    "freeze_known_optional_fragment",
]
