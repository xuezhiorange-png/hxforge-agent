"""Immutable value objects for TASK-022 Slice A."""

from __future__ import annotations

import enum
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from hexagent.exchangers.shell_tube.models import Orientation, ShellAndTubeConfiguration
from hexagent.exchangers.shell_tube.tube_layout.canonical import (
    freeze_known_fragment,
    freeze_known_optional_fragment,
)
from hexagent.exchangers.shell_tube.tube_layout.models import TubeLayout

REQUEST_SCHEMA_VERSION = "task022.shell-bundle-geometry-request.v1"
CALLER_SHELL_SCHEMA_VERSION = "task022.caller-shell-diameter.v1"
SHELL_SNAPSHOT_SCHEMA_VERSION = "task022.approved-shell-geometry.v1"
RULE_SNAPSHOT_SCHEMA_VERSION = "task022.shell-bundle-rule-authority.v1"
RESULT_SCHEMA_VERSION = "task022.shell-bundle-geometry.v1"
PROFILE_ID = "hxforge.shell_tube.shell_bundle_geometry.v1"
DESIGN_CONTRACT_PATH = "docs/tasks/TASK-022-shell-and-bundle-geometry.md"

DEFERRED_CAPABILITIES: tuple[str, ...] = (
    "BAFFLE_DESIGN_NOT_COMPUTABLE",
    "PASS_PARTITION_ASSIGNMENT_NOT_COMPUTABLE",
    "NOZZLE_AND_FLOW_PATH_DESIGN_NOT_COMPUTABLE",
    "UTUBE_BEND_GEOMETRY_NOT_COMPUTABLE",
    "SHELL_SIDE_THERMAL_RATING_NOT_COMPUTABLE",
    "KERN_SCREENING_NOT_COMPUTABLE",
    "BELL_DELAWARE_NOT_COMPUTABLE",
    "SHELL_SIDE_PRESSURE_DROP_NOT_COMPUTABLE",
    "TUBE_SIDE_PRESSURE_DROP_NOT_COMPUTABLE",
    "VIBRATION_NOT_COMPUTABLE",
    "THERMAL_EXPANSION_NOT_COMPUTABLE",
    "MECHANICAL_BOUNDARY_NOT_COMPUTABLE",
    "MATERIAL_SELECTION_NOT_COMPUTABLE",
    "MASS_NOT_COMPUTABLE",
    "COST_NOT_COMPUTABLE",
    "OPTIMIZATION_NOT_COMPUTABLE",
    "API_NOT_COMPUTABLE",
    "REPORT_NOT_COMPUTABLE",
    "GOLDEN_VALIDATION_NOT_COMPUTABLE",
)


class ShellInsideDiameterAuthorityMode(enum.StrEnum):
    CALLER_SUPPLIED_EXPLICIT = "CALLER_SUPPLIED_EXPLICIT"
    APPROVED_CATALOG_SNAPSHOT = "APPROVED_CATALOG_SNAPSHOT"


class RuleAuthorityMode(enum.StrEnum):
    INTERNAL_GENERIC = "INTERNAL_GENERIC"
    APPROVED_RULE_PACK = "APPROVED_RULE_PACK"


class ValidationStatus(enum.StrEnum):
    VALID = "VALID"
    BLOCKED = "BLOCKED"


class BlockerCode(enum.StrEnum):
    SBG_SCHEMA_VERSION_UNSUPPORTED = "SBG_SCHEMA_VERSION_UNSUPPORTED"
    SBG_UNKNOWN_FIELD = "SBG_UNKNOWN_FIELD"
    SBG_RAW_TYPE_INVALID = "SBG_RAW_TYPE_INVALID"
    SBG_DECIMAL_LEXICAL_INVALID = "SBG_DECIMAL_LEXICAL_INVALID"
    SBG_TASK020_CONFIGURATION_MISSING = "SBG_TASK020_CONFIGURATION_MISSING"
    SBG_TASK020_CONFIGURATION_INVALID = "SBG_TASK020_CONFIGURATION_INVALID"
    SBG_TASK020_CONFIGURATION_IDENTITY_MISMATCH = "SBG_TASK020_CONFIGURATION_IDENTITY_MISMATCH"
    SBG_TASK021_LAYOUT_MISSING = "SBG_TASK021_LAYOUT_MISSING"
    SBG_TASK021_LAYOUT_INVALID = "SBG_TASK021_LAYOUT_INVALID"
    SBG_TASK021_LAYOUT_HAS_BLOCKERS = "SBG_TASK021_LAYOUT_HAS_BLOCKERS"
    SBG_TASK021_LAYOUT_IDENTITY_MISMATCH = "SBG_TASK021_LAYOUT_IDENTITY_MISMATCH"
    SBG_LAYOUT_CONFIGURATION_BINDING_MISMATCH = "SBG_LAYOUT_CONFIGURATION_BINDING_MISMATCH"
    SBG_LAYOUT_HAS_NO_POSITIONS = "SBG_LAYOUT_HAS_NO_POSITIONS"
    SBG_LAYOUT_POSITION_COUNT_EXCEEDED = "SBG_LAYOUT_POSITION_COUNT_EXCEEDED"
    SBG_TUBE_GEOMETRY_SNAPSHOT_INVALID = "SBG_TUBE_GEOMETRY_SNAPSHOT_INVALID"
    SBG_RULE_AUTHORITY_MISSING = "SBG_RULE_AUTHORITY_MISSING"
    SBG_RULE_PROFILE_UNSUPPORTED = "SBG_RULE_PROFILE_UNSUPPORTED"
    SBG_RULE_AUTHORITY_MODE_INVALID = "SBG_RULE_AUTHORITY_MODE_INVALID"
    SBG_RULE_UNAPPROVED = "SBG_RULE_UNAPPROVED"
    SBG_RULE_SNAPSHOT_HASH_MISMATCH = "SBG_RULE_SNAPSHOT_HASH_MISMATCH"
    SBG_RULE_LICENSE_BLOCKED = "SBG_RULE_LICENSE_BLOCKED"
    SBG_RULE_PROVENANCE_INCOMPLETE = "SBG_RULE_PROVENANCE_INCOMPLETE"
    SBG_SHELL_AUTHORITY_MODE_INVALID = "SBG_SHELL_AUTHORITY_MODE_INVALID"
    SBG_SHELL_AUTHORITY_MODE_NOT_ALLOWED = "SBG_SHELL_AUTHORITY_MODE_NOT_ALLOWED"
    SBG_CALLER_SHELL_DIAMETER_MISSING = "SBG_CALLER_SHELL_DIAMETER_MISSING"
    SBG_CALLER_SHELL_DIAMETER_NOT_EXPECTED = "SBG_CALLER_SHELL_DIAMETER_NOT_EXPECTED"
    SBG_CALLER_SHELL_AUTHORITY_HASH_MISMATCH = "SBG_CALLER_SHELL_AUTHORITY_HASH_MISMATCH"
    SBG_APPROVED_SHELL_GEOMETRY_MISSING = "SBG_APPROVED_SHELL_GEOMETRY_MISSING"
    SBG_APPROVED_SHELL_GEOMETRY_NOT_EXPECTED = "SBG_APPROVED_SHELL_GEOMETRY_NOT_EXPECTED"
    SBG_APPROVED_SHELL_GEOMETRY_TYPE_INVALID = "SBG_APPROVED_SHELL_GEOMETRY_TYPE_INVALID"
    SBG_APPROVED_SHELL_GEOMETRY_UNAPPROVED = "SBG_APPROVED_SHELL_GEOMETRY_UNAPPROVED"
    SBG_APPROVED_SHELL_SOURCE_INCOMPLETE = "SBG_APPROVED_SHELL_SOURCE_INCOMPLETE"
    SBG_APPROVED_SHELL_SNAPSHOT_HASH_MISMATCH = "SBG_APPROVED_SHELL_SNAPSHOT_HASH_MISMATCH"
    SBG_SHELL_INSIDE_DIAMETER_INVALID = "SBG_SHELL_INSIDE_DIAMETER_INVALID"
    SBG_BUNDLE_PERIPHERAL_ALLOWANCE_INVALID = "SBG_BUNDLE_PERIPHERAL_ALLOWANCE_INVALID"
    SBG_BUNDLE_PERIPHERAL_ALLOWANCE_BELOW_RULE_MINIMUM = (
        "SBG_BUNDLE_PERIPHERAL_ALLOWANCE_BELOW_RULE_MINIMUM"
    )
    SBG_REQUIRED_MINIMUM_CLEARANCE_INVALID = "SBG_REQUIRED_MINIMUM_CLEARANCE_INVALID"
    SBG_REQUIRED_MINIMUM_CLEARANCE_BELOW_RULE_MINIMUM = (
        "SBG_REQUIRED_MINIMUM_CLEARANCE_BELOW_RULE_MINIMUM"
    )
    SBG_BUNDLE_ENVELOPE_CALCULATION_FAILED = "SBG_BUNDLE_ENVELOPE_CALCULATION_FAILED"
    SBG_SHELL_NOT_LARGER_THAN_BUNDLE = "SBG_SHELL_NOT_LARGER_THAN_BUNDLE"
    SBG_RADIAL_CLEARANCE_BELOW_REQUIRED_MINIMUM = "SBG_RADIAL_CLEARANCE_BELOW_REQUIRED_MINIMUM"
    SBG_CANONICALIZATION_FAILED = "SBG_CANONICALIZATION_FAILED"


class WarningCode(enum.StrEnum):
    SBG_INTERNAL_GENERIC_NO_STANDARD_CLAIM = "SBG_INTERNAL_GENERIC_NO_STANDARD_CLAIM"
    SBG_CALLER_SUPPLIED_SHELL_DIAMETER_NO_CATALOG_SELECTION = (
        "SBG_CALLER_SUPPLIED_SHELL_DIAMETER_NO_CATALOG_SELECTION"
    )
    SBG_ZERO_BUNDLE_PERIPHERAL_ALLOWANCE = "SBG_ZERO_BUNDLE_PERIPHERAL_ALLOWANCE"
    SBG_ZERO_REQUIRED_MINIMUM_RADIAL_CLEARANCE = "SBG_ZERO_REQUIRED_MINIMUM_RADIAL_CLEARANCE"
    SBG_GEOMETRIC_CLEARANCE_NOT_MECHANICAL_ADEQUACY = (
        "SBG_GEOMETRIC_CLEARANCE_NOT_MECHANICAL_ADEQUACY"
    )
    SBG_FIXED_TUBESHEET_THERMAL_EXPANSION_DEFERRED = (
        "SBG_FIXED_TUBESHEET_THERMAL_EXPANSION_DEFERRED"
    )
    SBG_UTUBE_BEND_AND_PULL_CLEARANCE_DEFERRED = "SBG_UTUBE_BEND_AND_PULL_CLEARANCE_DEFERRED"
    SBG_FLOATING_HEAD_HARDWARE_AND_PULL_CLEARANCE_DEFERRED = (
        "SBG_FLOATING_HEAD_HARDWARE_AND_PULL_CLEARANCE_DEFERRED"
    )
    SBG_BAFFLE_GEOMETRY_DEFERRED = "SBG_BAFFLE_GEOMETRY_DEFERRED"
    SBG_PASS_PARTITION_ASSIGNMENT_DEFERRED = "SBG_PASS_PARTITION_ASSIGNMENT_DEFERRED"


@dataclass(frozen=True)
class SourceBindingSnapshot:
    source_id: str
    source_type: str
    source_revision: str
    source_location: str
    evidence_ref: str
    approved_by: str
    approved_at: str


@dataclass(frozen=True)
class RulePackIdentitySnapshot:
    rule_pack_id: str
    rule_pack_version: str
    rule_pack_canonical_hash: str


@dataclass(frozen=True)
class ShellBundleGeometryRuleAuthoritySnapshot:
    schema_version: str
    profile_id: str
    authority_mode: RuleAuthorityMode
    rule_id: str
    rule_version: str
    rule_artifact_canonical_hash: str
    source_class: str
    license_evidence: Any
    approval_status: str
    provenance_edge_ids: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    rule_pack_identity: RulePackIdentitySnapshot | None
    allowed_shell_authority_modes: tuple[ShellInsideDiameterAuthorityMode, ...]
    minimum_bundle_peripheral_allowance_m: str
    minimum_radial_clearance_m: str
    maximum_position_count: int
    snapshot_hash: str

    def __post_init__(self) -> None:
        frozen = freeze_known_fragment(self.license_evidence)
        if frozen is not self.license_evidence:
            object.__setattr__(self, "license_evidence", frozen)


@dataclass(frozen=True)
class CallerSuppliedShellInsideDiameter:
    schema_version: str
    shell_inside_diameter_m: str
    evidence_refs: tuple[str, ...]
    authority_hash: str


@dataclass(frozen=True)
class ApprovedShellGeometrySnapshot:
    schema_version: str
    geometry_id: str
    geometry_type: str
    revision: str
    approval_state: str
    shell_inside_diameter_m: str
    record_hash: str
    source_binding: SourceBindingSnapshot
    snapshot_hash: str


@dataclass(frozen=True)
class ShellBundleGeometryRequest:
    schema_version: str
    configuration: ShellAndTubeConfiguration
    tube_layout: TubeLayout
    geometry_rule_authority: ShellBundleGeometryRuleAuthoritySnapshot
    shell_authority_mode: ShellInsideDiameterAuthorityMode
    caller_supplied_shell: CallerSuppliedShellInsideDiameter | None
    approved_shell_geometry: ApprovedShellGeometrySnapshot | None
    bundle_peripheral_allowance_m: str
    bundle_peripheral_allowance_evidence_refs: tuple[str, ...]
    required_minimum_radial_clearance_m: str
    minimum_clearance_evidence_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True)
class MessageEntry:
    code: str
    field_path: str | None
    message_key: str
    evidence_refs: tuple[str, ...] = field(default_factory=tuple)
    details: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        frozen = freeze_known_optional_fragment(self.details)
        if frozen is not self.details:
            object.__setattr__(self, "details", frozen)


@dataclass(frozen=True)
class ShellBundleGeometry:
    schema_version: str
    geometry_id: str
    geometry_hash: str
    request_hash: str
    task020_configuration_id: str
    task020_configuration_hash: str
    task021_layout_id: str
    task021_layout_hash: str
    construction_family: str
    equipment_orientation: Orientation
    shell_pass_count: int
    tube_pass_count: int
    tube_geometry_snapshot_hash: str
    geometry_rule_authority: ShellBundleGeometryRuleAuthoritySnapshot
    shell_authority_mode: ShellInsideDiameterAuthorityMode
    caller_supplied_shell: CallerSuppliedShellInsideDiameter | None
    approved_shell_geometry: ApprovedShellGeometrySnapshot | None
    shell_inside_diameter_m: str
    shell_radius_m: str
    bare_tube_bundle_radius_m: str
    bare_tube_bundle_diameter_m: str
    bundle_peripheral_allowance_m: str
    bundle_outer_envelope_radius_m: str
    bundle_outer_envelope_diameter_m: str
    shell_to_bundle_radial_clearance_m: str
    shell_to_bundle_diametral_clearance_m: str
    required_minimum_radial_clearance_m: str
    radial_clearance_margin_m: str
    limiting_position_ids: tuple[str, ...]
    position_count: int
    warnings: tuple[MessageEntry, ...]
    blockers: tuple[MessageEntry, ...]
    deferred_capabilities: tuple[str, ...]
    provenance: Mapping[str, Any]

    def __post_init__(self) -> None:
        frozen = freeze_known_fragment(self.provenance)
        if frozen is not self.provenance:
            object.__setattr__(self, "provenance", frozen)


@dataclass(frozen=True)
class ShellBundleGeometryValidationResult:
    status: ValidationStatus
    geometry: ShellBundleGeometry | None
    warnings: tuple[MessageEntry, ...]
    blockers: tuple[MessageEntry, ...]
    deferred_capabilities: tuple[str, ...] = DEFERRED_CAPABILITIES
    blocked_result_hash: str | None = None


__all__ = [
    "ApprovedShellGeometrySnapshot",
    "BlockerCode",
    "CALLER_SHELL_SCHEMA_VERSION",
    "CallerSuppliedShellInsideDiameter",
    "DEFERRED_CAPABILITIES",
    "DESIGN_CONTRACT_PATH",
    "MessageEntry",
    "PROFILE_ID",
    "REQUEST_SCHEMA_VERSION",
    "RESULT_SCHEMA_VERSION",
    "RULE_SNAPSHOT_SCHEMA_VERSION",
    "RuleAuthorityMode",
    "RulePackIdentitySnapshot",
    "SHELL_SNAPSHOT_SCHEMA_VERSION",
    "ShellBundleGeometry",
    "ShellBundleGeometryRequest",
    "ShellBundleGeometryRuleAuthoritySnapshot",
    "ShellBundleGeometryValidationResult",
    "ShellInsideDiameterAuthorityMode",
    "SourceBindingSnapshot",
    "ValidationStatus",
    "WarningCode",
]
