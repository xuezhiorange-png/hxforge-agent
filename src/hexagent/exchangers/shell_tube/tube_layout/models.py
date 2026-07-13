"""Immutable TASK-021 tube-layout value objects."""

from __future__ import annotations

import enum
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from hexagent.exchangers.shell_tube.models import (
    Orientation,
    ShellAndTubeConfiguration,
)

REQUEST_SCHEMA_VERSION = "task021.tube-layout-request.v1"
ENVELOPE_SCHEMA_VERSION = "task021.circular-envelope.v1"
PAIRING_SCHEMA_VERSION = "task021.u-tube-pairing.v1"
LAYOUT_SCHEMA_VERSION = "task021.tube-layout.v1"
PROFILE_ID = "hxforge.shell_tube.tube_layout.v1"
DESIGN_CONTRACT_PATH = "docs/tasks/TASK-021-shell-and-tube-tube-layout-and-count.md"

DEFERRED_CAPABILITIES: tuple[str, ...] = (
    "SHELL_DIAMETER_NOT_COMPUTABLE",
    "BAFFLE_DESIGN_NOT_COMPUTABLE",
    "PASS_PARTITION_ASSIGNMENT_NOT_COMPUTABLE",
    "THERMAL_RATING_NOT_COMPUTABLE",
    "KERN_SCREENING_NOT_COMPUTABLE",
    "BELL_DELAWARE_NOT_COMPUTABLE",
    "PRESSURE_DROP_NOT_COMPUTABLE",
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


class AuthorityMode(enum.StrEnum):
    INTERNAL_GENERIC = "INTERNAL_GENERIC"
    APPROVED_RULE_PACK = "APPROVED_RULE_PACK"


class PatternFamily(enum.StrEnum):
    SQUARE = "SQUARE"
    TRIANGULAR = "TRIANGULAR"


class OriginMode(enum.StrEnum):
    CENTER_ON_LATTICE_POINT = "CENTER_ON_LATTICE_POINT"
    CENTER_ON_PRIMITIVE_CELL = "CENTER_ON_PRIMITIVE_CELL"


class AxisOrientation(enum.StrEnum):
    PRIMARY_AXIS_X = "PRIMARY_AXIS_X"
    PRIMARY_AXIS_Y = "PRIMARY_AXIS_Y"


class ExclusionZoneType(enum.StrEnum):
    AXIS_ALIGNED_RECTANGLE = "AXIS_ALIGNED_RECTANGLE"
    CIRCLE = "CIRCLE"


class ValidationStatus(enum.StrEnum):
    VALID = "VALID"
    BLOCKED = "BLOCKED"


class BlockerCode(enum.StrEnum):
    STL_SCHEMA_VERSION_UNSUPPORTED = "STL_SCHEMA_VERSION_UNSUPPORTED"
    STL_UNKNOWN_FIELD = "STL_UNKNOWN_FIELD"
    STL_RAW_TYPE_INVALID = "STL_RAW_TYPE_INVALID"
    STL_TASK020_CONFIGURATION_MISSING = "STL_TASK020_CONFIGURATION_MISSING"
    STL_TASK020_CONFIGURATION_INVALID = "STL_TASK020_CONFIGURATION_INVALID"
    STL_TASK020_CONFIGURATION_IDENTITY_MISMATCH = "STL_TASK020_CONFIGURATION_IDENTITY_MISMATCH"
    STL_AUTHORITY_MODE_MISMATCH = "STL_AUTHORITY_MODE_MISMATCH"
    STL_LAYOUT_RULE_AUTHORITY_MISSING = "STL_LAYOUT_RULE_AUTHORITY_MISSING"
    STL_LAYOUT_RULE_PROFILE_UNSUPPORTED = "STL_LAYOUT_RULE_PROFILE_UNSUPPORTED"
    STL_LAYOUT_RULE_UNAPPROVED = "STL_LAYOUT_RULE_UNAPPROVED"
    STL_LAYOUT_RULE_SNAPSHOT_HASH_MISMATCH = "STL_LAYOUT_RULE_SNAPSHOT_HASH_MISMATCH"
    STL_LAYOUT_RULE_LICENSE_BLOCKED = "STL_LAYOUT_RULE_LICENSE_BLOCKED"
    STL_LAYOUT_RULE_PROVENANCE_INCOMPLETE = "STL_LAYOUT_RULE_PROVENANCE_INCOMPLETE"
    STL_RULE_PACK_IDENTITY_MISSING = "STL_RULE_PACK_IDENTITY_MISSING"
    STL_RULE_PACK_IDENTITY_NOT_EXPECTED = "STL_RULE_PACK_IDENTITY_NOT_EXPECTED"
    STL_TUBE_GEOMETRY_MISSING = "STL_TUBE_GEOMETRY_MISSING"
    STL_TUBE_GEOMETRY_TYPE_INVALID = "STL_TUBE_GEOMETRY_TYPE_INVALID"
    STL_TUBE_GEOMETRY_UNAPPROVED = "STL_TUBE_GEOMETRY_UNAPPROVED"
    STL_TUBE_GEOMETRY_SOURCE_INCOMPLETE = "STL_TUBE_GEOMETRY_SOURCE_INCOMPLETE"
    STL_TUBE_GEOMETRY_SNAPSHOT_HASH_MISMATCH = "STL_TUBE_GEOMETRY_SNAPSHOT_HASH_MISMATCH"
    STL_TUBE_DIMENSION_INVALID = "STL_TUBE_DIMENSION_INVALID"
    STL_TUBE_DIMENSION_INCONSISTENT = "STL_TUBE_DIMENSION_INCONSISTENT"
    STL_DECIMAL_LEXICAL_INVALID = "STL_DECIMAL_LEXICAL_INVALID"
    STL_PITCH_INVALID = "STL_PITCH_INVALID"
    STL_PITCH_BELOW_TUBE_OD = "STL_PITCH_BELOW_TUBE_OD"
    STL_EDGE_CLEARANCE_INVALID = "STL_EDGE_CLEARANCE_INVALID"
    STL_ENVELOPE_INVALID = "STL_ENVELOPE_INVALID"
    STL_ORIGIN_MODE_NOT_AUTHORIZED = "STL_ORIGIN_MODE_NOT_AUTHORIZED"
    STL_AXIS_ORIENTATION_NOT_AUTHORIZED = "STL_AXIS_ORIENTATION_NOT_AUTHORIZED"
    STL_EXCLUSION_ZONE_TYPE_NOT_AUTHORIZED = "STL_EXCLUSION_ZONE_TYPE_NOT_AUTHORIZED"
    STL_EXCLUSION_ZONE_INVALID = "STL_EXCLUSION_ZONE_INVALID"
    STL_EXCLUSION_ZONE_DUPLICATE_ID = "STL_EXCLUSION_ZONE_DUPLICATE_ID"
    STL_BASIS_NON_INVERTIBLE = "STL_BASIS_NON_INVERTIBLE"
    STL_ENUMERATION_LIMIT_EXCEEDED = "STL_ENUMERATION_LIMIT_EXCEEDED"
    STL_COORDINATE_QUANTIZATION_COLLISION = "STL_COORDINATE_QUANTIZATION_COLLISION"
    STL_NO_TUBE_POSITIONS = "STL_NO_TUBE_POSITIONS"
    STL_UTUBE_PAIRING_REQUIRED = "STL_UTUBE_PAIRING_REQUIRED"
    STL_UTUBE_PAIRING_NOT_EXPECTED = "STL_UTUBE_PAIRING_NOT_EXPECTED"
    STL_UTUBE_PAIRING_HASH_MISMATCH = "STL_UTUBE_PAIRING_HASH_MISMATCH"
    STL_UTUBE_PAIRING_INVALID = "STL_UTUBE_PAIRING_INVALID"
    STL_CANONICALIZATION_FAILED = "STL_CANONICALIZATION_FAILED"


class WarningCode(enum.StrEnum):
    STL_INTERNAL_GENERIC_NO_STANDARD_CLAIM = "STL_INTERNAL_GENERIC_NO_STANDARD_CLAIM"
    STL_CALLER_SUPPLIED_ENVELOPE_NOT_SHELL_DIAMETER = (
        "STL_CALLER_SUPPLIED_ENVELOPE_NOT_SHELL_DIAMETER"
    )
    STL_PASS_PARTITION_ASSIGNMENT_DEFERRED = "STL_PASS_PARTITION_ASSIGNMENT_DEFERRED"
    STL_UTUBE_BEND_GEOMETRY_DEFERRED = "STL_UTUBE_BEND_GEOMETRY_DEFERRED"


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
class ApprovedTubeGeometrySnapshot:
    geometry_id: str
    geometry_type: str
    revision: str
    approval_state: str
    outer_diameter_m: str
    inner_diameter_m: str
    wall_thickness_m: str
    record_hash: str
    snapshot_hash: str
    source_binding: SourceBindingSnapshot


@dataclass(frozen=True)
class LayoutRuleAuthoritySnapshot:
    profile_id: str
    authority_mode: AuthorityMode
    rule_id: str
    rule_version: str
    rule_artifact_canonical_hash: str
    source_class: str
    license_evidence: Any
    approval_status: str
    provenance_edge_ids: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    rule_pack_identity: RulePackIdentitySnapshot | None
    pattern_family: PatternFamily
    pitch_m: str
    edge_clearance_m: str
    allowed_origin_modes: tuple[OriginMode, ...]
    allowed_axis_orientations: tuple[AxisOrientation, ...]
    allowed_exclusion_zone_types: tuple[ExclusionZoneType, ...]
    maximum_candidate_positions: int
    snapshot_hash: str

    def __post_init__(self) -> None:
        """Round 4 §6.1 + Round 6 §6: deep-freeze ``license_evidence``.

        Post-capture mutation by the caller MUST NOT influence the value
        stored on this object or any hash derived from it. The freeze happens
        exactly once during construction; further attempts to mutate the
        field raise ``dataclasses.FrozenInstanceError`` because the dataclass
        itself is ``frozen=True``.

        Round 6 §6 turns ``force_frozen_canonical`` into a strict public
        Layer-A boundary that rejects internal-only markers
        (``FrozenJsonArray`` / ``FrozenMapping``). Because
        ``parse_layout_rule`` already passes through
        ``_canonical_json_value`` which produces an internal-frozen fragment
        (mapping or array), the second pass here MUST use
        :func:`refreeze_internal_fragment` (Layer B) instead.
        """

        from .canonical import refreeze_internal_fragment

        frozen = refreeze_internal_fragment(self.license_evidence)
        if frozen is not self.license_evidence:
            object.__setattr__(self, "license_evidence", frozen)


@dataclass(frozen=True)
class CircularTubeCenterEnvelope:
    schema_version: str
    tube_center_envelope_diameter_m: str
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True, order=True)
class LatticeIndex:
    u: int
    v: int


@dataclass(frozen=True)
class ExclusionZone:
    zone_id: str
    zone_type: ExclusionZoneType
    center_x_m: str
    center_y_m: str
    clearance_m: str
    reason_code: str
    evidence_refs: tuple[str, ...]
    width_m: str | None
    height_m: str | None
    radius_m: str | None


@dataclass(frozen=True)
class UTubePair:
    pair_id: str
    leg_a: LatticeIndex
    leg_b: LatticeIndex
    evidence_refs: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class UTubePairingPlan:
    schema_version: str
    pairs: tuple[UTubePair, ...]
    evidence_refs: tuple[str, ...]
    pairing_plan_hash: str


@dataclass(frozen=True)
class TubeLayoutRequest:
    schema_version: str
    configuration: ShellAndTubeConfiguration
    tube_geometry: ApprovedTubeGeometrySnapshot
    layout_rule_authority: LayoutRuleAuthoritySnapshot
    placement_envelope: CircularTubeCenterEnvelope
    origin_mode: OriginMode
    axis_orientation: AxisOrientation
    exclusion_zones: tuple[ExclusionZone, ...]
    u_tube_pairing_plan: UTubePairingPlan | None
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True)
class TubePosition:
    position_id: str
    u: int
    v: int
    x_m: str
    y_m: str


@dataclass(frozen=True)
class ExclusionAudit:
    zone_id: str
    rejected_position_count: int
    reason_code: str
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True)
class MessageEntry:
    code: str
    field_path: str | None
    message_key: str
    evidence_refs: tuple[str, ...] = field(default_factory=tuple)
    details: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        """Round 8 §P1-1 — Layer-C deep-freeze ``details`` to a detached snapshot.

        Caller-mutation after construction MUST NOT influence:

        - ``warnings[*].details``
        - ``blockers[*].details``
        - ``request_hash`` / ``layout_hash`` / ``provenance_pre_hash``
        - any consumer of the canonical hash pipeline

        Accepts:

        - ``None``
        - ordinary public canonical dict / list
        - already-frozen ``FrozenJsonObject`` / ``FrozenJsonArray``
        - canonical atoms (``None`` / ``bool`` / ``int`` / ``str``)

        Rejects everything else (``raw tuple`` / ``raw MappingProxyType`
        / ``Decimal`` / ``float`` / ``bytes`` / arbitrary object /
        non-string-keyed mapping) with ``PublicCanonicalDomainError``.
        """

        from .canonical import freeze_known_optional_fragment

        if self.details is None:
            return
        frozen = freeze_known_optional_fragment(self.details)
        if frozen is not self.details:
            object.__setattr__(self, "details", frozen)


@dataclass(frozen=True)
class ProvenancePreHashProjection:
    task_id: str
    design_contract_path: str
    task020_configuration_id: str
    task020_configuration_hash: str
    task020_case_authority: Mapping[str, Any]
    geometry_id: str
    geometry_revision: str
    geometry_record_hash: str
    tube_geometry_snapshot_hash: str
    geometry_source_binding: Mapping[str, Any]
    layout_rule_profile_id: str
    layout_rule_id: str
    layout_rule_version: str
    rule_artifact_canonical_hash: str
    layout_rule_snapshot_hash: str
    source_class: str
    approval_status: str
    provenance_edge_ids: tuple[str, ...]
    layout_rule_evidence_refs: tuple[str, ...]
    rule_pack_identity: Mapping[str, Any] | None
    envelope_evidence_refs: tuple[str, ...]
    exclusion_zone_evidence_refs: tuple[tuple[str, ...], ...]
    u_tube_pairing_evidence_refs: tuple[str, ...] | None
    software_version: str
    git_commit: str
    request_hash: str
    warnings: tuple[MessageEntry, ...]
    deferred_capabilities: tuple[str, ...]

    def __post_init__(self) -> None:
        """Round 4 §6 + Round 7 unified canonical-type-system (Layer C).

        ``task020_case_authority``, ``geometry_source_binding``, and
        ``rule_pack_identity`` MUST be detached frozen snapshots so that
        a caller mutation after construction cannot influence the
        downstream ``provenance_pre_hash`` or ``layout_hash``.

        Round 7: callers in :mod:`validation` may pre-freeze the
        upstream fragments via :func:`.canonical.canonical_mapping`
        (yielding :class:`FrozenJsonObject` already) or hand us raw
        public-domain ``dict`` / ``None``. The explicit
        :func:`freeze_known_fragment` Layer-C converter handles both
        shapes without breaking either contract.
        """

        from .canonical import freeze_known_fragment

        for field_name in ("task020_case_authority", "geometry_source_binding"):
            current = getattr(self, field_name)
            frozen = freeze_known_fragment(current)
            if frozen is not current:
                object.__setattr__(self, field_name, frozen)

        if self.rule_pack_identity is not None:
            frozen = freeze_known_fragment(self.rule_pack_identity)
            if frozen is not self.rule_pack_identity:
                object.__setattr__(self, "rule_pack_identity", frozen)


@dataclass(frozen=True)
class TubeLayout:
    schema_version: str
    layout_id: str
    layout_hash: str
    request_hash: str
    task020_configuration_id: str
    task020_configuration_hash: str
    case_authority: Mapping[str, Any]
    construction_family: str
    equipment_orientation: Orientation
    shell_pass_count: int
    tube_pass_count: int
    tube_geometry: ApprovedTubeGeometrySnapshot
    layout_rule_authority: LayoutRuleAuthoritySnapshot
    placement_envelope: CircularTubeCenterEnvelope
    origin_mode: OriginMode
    axis_orientation: AxisOrientation
    exclusion_zones: tuple[ExclusionZone, ...]
    positions: tuple[TubePosition, ...]
    tube_hole_count: int
    physical_tube_count: int
    boundary_rejection_count: int
    exclusion_rejection_count: int
    exclusion_audit: tuple[ExclusionAudit, ...]
    warnings: tuple[MessageEntry, ...]
    blockers: tuple[MessageEntry, ...]
    deferred_capabilities: tuple[str, ...]
    provenance: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Round 4 §6.3 + §6.4 + Round 7 type-system: deep-freeze case_authority / provenance.

        Both fields are detached frozen snapshots on construction.

        Round 7 Layer C: callers in :mod:`validation` may hand us raw
        public-domain ``dict`` (un-frozen primitive from
        :func:`dataclass_to_mapping`) or pre-frozen Layer-B shapes.
        :func:`freeze_known_fragment` handles both transparently.
        """

        from .canonical import freeze_known_fragment

        frozen_ca = freeze_known_fragment(self.case_authority)
        if frozen_ca is not self.case_authority:
            object.__setattr__(self, "case_authority", frozen_ca)

        frozen_prov = freeze_known_fragment(self.provenance)
        if frozen_prov is not self.provenance:
            object.__setattr__(self, "provenance", frozen_prov)


@dataclass(frozen=True)
class TubeLayoutValidationResult:
    status: ValidationStatus
    layout: TubeLayout | None
    warnings: tuple[MessageEntry, ...]
    blockers: tuple[MessageEntry, ...]
    deferred_capabilities: tuple[str, ...] = DEFERRED_CAPABILITIES
    blocked_result_hash: str | None = None


__all__ = [
    "AuthorityMode",
    "ApprovedTubeGeometrySnapshot",
    "AxisOrientation",
    "BlockerCode",
    "CircularTubeCenterEnvelope",
    "DEFERRED_CAPABILITIES",
    "DESIGN_CONTRACT_PATH",
    "ENVELOPE_SCHEMA_VERSION",
    "ExclusionAudit",
    "ExclusionZone",
    "ExclusionZoneType",
    "LAYOUT_SCHEMA_VERSION",
    "LatticeIndex",
    "LayoutRuleAuthoritySnapshot",
    "MessageEntry",
    "OriginMode",
    "PAIRING_SCHEMA_VERSION",
    "PROFILE_ID",
    "PatternFamily",
    "ProvenancePreHashProjection",
    "REQUEST_SCHEMA_VERSION",
    "RulePackIdentitySnapshot",
    "SourceBindingSnapshot",
    "TubeLayout",
    "TubeLayoutRequest",
    "TubeLayoutValidationResult",
    "TubePosition",
    "UTubePair",
    "UTubePairingPlan",
    "ValidationStatus",
    "WarningCode",
]
