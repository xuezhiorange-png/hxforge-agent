"""TASK-020 domain models — Section 7 of the TASK-020 design contract.

This module defines the **frozen value-object types** for TASK-020. Every
type is an immutable dataclass with a closed shape; construction
**never** mutates an existing instance and **never** reaches outside the
package. Construction calls the appropriate schema validator
(``schema.py``), which is the only place that may emit ``STC_*``
errors.

Type map (referenced from the TASK-020 design §6–§9):

- ``CaseRevisionAuthority`` (§7.3) — read-only value object derived from
  the TASK-014 ``CaseRevision``. TASK-020 does **not** import TASK-014
  directly; the consumer of TASK-020 is responsible for performing the
  TASK-014 ``CaseRevision`` → TASK-020 ``CaseRevisionAuthority`` mapping.
- ``RequestedRulePackIdentity`` (§6.3.4) — request-side input object
  (only in ``APPROVED_RULE_PACK`` mode).
- ``SelectedRuleAuthority`` (§6.3.5.1) — 8-field value object, the
  **only** per-rule identity carrier in evaluated authority.
- ``EvaluatedRulePackAuthority`` (§6.3.5) — output-side object.
- ``ConfigurationAuthorityBinding`` (§7.5) — value object used in the
  normalized configuration.
- ``ShellAndTubeConfigurationRequest`` (§7.4 / §8) — immutable input.
- ``ShellAndTubeConfiguration`` (§7.6 / §9) — normalized output.
- ``ConfigurationValidationResult`` (§7.7) — the ``VALID`` or
  ``BLOCKED`` result of validating a request.
- ``ComponentTokens`` (§9.1) — normalized front/shell/rear tokens.
- ``ErrorEntry`` (§10.4) — frozen 5-field shape for warnings and
  blockers.

Forbiddens (P1-1, P1-2, P1-3)
------------------------------
- No ``selected_rule_ids`` / ``selected_rule_artifact_hashes`` parallel
  list fields. Per-rule identity lives **only** inside each
  ``SelectedRuleAuthority`` value object.
- No standalone ``rule_pack_id`` / ``rule_pack_version`` /
  ``rule_pack_canonical_hash`` request-side fields. They are merged
  into ``RequestedRulePackIdentity``.
- No ``content_hash`` / ``rule_pack_hash`` fields. The single
  TASK-020-facing name is ``rule_pack_canonical_hash``.
"""

from __future__ import annotations

import enum
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from typing import Any

# ---------------------------------------------------------------------------
# §6.1 — Authority modes
# ---------------------------------------------------------------------------


class AuthorityMode(enum.StrEnum):
    """§6.1 — Closed set of authority modes."""

    INTERNAL_GENERIC = "INTERNAL_GENERIC"
    APPROVED_RULE_PACK = "APPROVED_RULE_PACK"


# ---------------------------------------------------------------------------
# §7.1 — Construction family
# ---------------------------------------------------------------------------


class ConstructionFamily(enum.StrEnum):
    """§7.1 — Closed internal construction-family set."""

    FIXED_TUBESHEET = "FIXED_TUBESHEET"
    U_TUBE = "U_TUBE"
    FLOATING_HEAD = "FLOATING_HEAD"


# ---------------------------------------------------------------------------
# §7.2 — Orientation
# ---------------------------------------------------------------------------


class Orientation(enum.StrEnum):
    """§7.2 — Closed orientation set."""

    HORIZONTAL = "HORIZONTAL"
    VERTICAL = "VERTICAL"
    UNSPECIFIED = "UNSPECIFIED"


# ---------------------------------------------------------------------------
# §9.1 — Equipment family
# ---------------------------------------------------------------------------


class EquipmentFamily(enum.StrEnum):
    """§9.1 — Single allowed value for TASK-020 is ``SHELL_AND_TUBE``."""

    SHELL_AND_TUBE = "SHELL_AND_TUBE"


# ---------------------------------------------------------------------------
# §9.1 — Standard claim status
# ---------------------------------------------------------------------------


class StandardClaimStatus(enum.StrEnum):
    """§9.1 — Standard claim status for the normalized configuration."""

    NO_STANDARD_CLAIM = "NO_STANDARD_CLAIM"
    RULE_PACK_VALIDATED = "RULE_PACK_VALIDATED"


# ---------------------------------------------------------------------------
# §7.7 — Validation status
# ---------------------------------------------------------------------------


class ValidationStatus(enum.StrEnum):
    """§7.7 — The status of a configuration validation result."""

    VALID = "VALID"
    BLOCKED = "BLOCKED"


# ---------------------------------------------------------------------------
# §7.3 — CaseRevisionAuthority (1-to-1 with TASK-014 CaseRevision)
# ---------------------------------------------------------------------------


# TASK-014 lifecycle values that TASK-020 accepts (§7.3 acceptance subset).
# TASK-014 itself has lifecycle values {draft, validated, committed,
# superseded, archived, tombstoned, rejected}; TASK-020 only accepts
# {committed, superseded, archived} for downstream consumption. Any
# other value must produce ``STC_CASE_REVISION_STATUS_BLOCKED``.
TASK_020_ACCEPTED_LIFECYCLE_VALUES: frozenset[str] = frozenset(
    {"committed", "superseded", "archived"}
)


class CaseRevisionStatus(enum.StrEnum):
    """Subset of TASK-014 lifecycle values that TASK-020 accepts."""

    COMMITTED = "committed"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


@dataclass(frozen=True)
class CaseRevisionAuthority:
    """§7.3 — TASK-020-owned read-only value object.

    Mapped 1-to-1 from the TASK-014 frozen ``CaseRevision`` contract.
    The TASK-020 adapter treats this value as immutable; it does not
    perform any persistence query (see §7.3 lines 596–601).
    """

    revision_id: str
    payload_hash: str
    domain_snapshot_hash: str
    revision_status: CaseRevisionStatus

    def __post_init__(self) -> None:
        # Local validation only; STC_* errors are emitted by schema.py.
        if not isinstance(self.revision_id, str):
            raise TypeError(
                f"CaseRevisionAuthority.revision_id must be str, "
                f"got {type(self.revision_id).__name__}"
            )
        if not isinstance(self.payload_hash, str):
            raise TypeError(
                f"CaseRevisionAuthority.payload_hash must be str, "
                f"got {type(self.payload_hash).__name__}"
            )
        if not isinstance(self.domain_snapshot_hash, str):
            raise TypeError(
                f"CaseRevisionAuthority.domain_snapshot_hash must be str, "
                f"got {type(self.domain_snapshot_hash).__name__}"
            )
        if not isinstance(self.revision_status, CaseRevisionStatus):
            raise TypeError(
                f"CaseRevisionAuthority.revision_status must be "
                f"CaseRevisionStatus, got {type(self.revision_status).__name__}"
            )


# ---------------------------------------------------------------------------
# §6.3.4 — RequestedRulePackIdentity (request-side input object)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RequestedRulePackIdentity:
    """§6.3.4 — Request-side rule-pack identity (only in APPROVED_RULE_PACK).

    The only rule-pack object the request carries. The previous
    ``RulePackAuthority`` (which mixed input identity with evaluated
    output fields) is removed from the request (§6.3.4 lines 396–400).
    """

    rule_pack_id: str
    rule_pack_version: str
    rule_pack_canonical_hash: str


# Backward-compatibility alias: the design contract text uses both
# ``RequestRulePackIdentity`` and ``RequestedRulePackIdentity``. They
# are the same frozen 3-field value object; the implementation binds
# the design's exact name.
RequestRulePackIdentity = RequestedRulePackIdentity


# ---------------------------------------------------------------------------
# §6.3.5.1 — SelectedRuleAuthority (8-field versioned object)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SelectedRuleAuthority:
    """§6.3.5.1 — Per-rule authority value object (P1-3, binding, versioned).

    All 8 fields are required. The schema is exact; any field outside
    this shape MUST emit ``STC_UNKNOWN_FIELD`` (per the design contract).
    """

    rule_id: str
    rule_version: str
    rule_artifact_canonical_hash: str
    source_class: str
    license_evidence: Any
    approval_status: str
    provenance_edge_ids: tuple[str, ...] = field(default_factory=tuple)
    evidence_refs: tuple[str, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# §6.3.5 — EvaluatedRulePackAuthority (output-side)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EvaluatedRulePackAuthority:
    """§6.3.5 — Output-side evaluated rule-pack authority.

    Carries the typed ``selected_rule_authorities`` list. The old
    parallel ``selected_rule_ids`` / ``selected_rule_artifact_hashes``
    lists are **deleted** from the contract (§6.3.5 lines 427–431).

    For ``INTERNAL_GENERIC`` mode this object MUST NOT be set; the
    configuration ``authority_binding`` rule-pack slot is ``null``.
    """

    rule_pack_id: str
    rule_pack_version: str
    rule_pack_canonical_hash: str
    validation_status: str
    selected_rule_authorities: tuple[SelectedRuleAuthority, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# §7.5 — ConfigurationAuthorityBinding
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConfigurationAuthorityBinding:
    """§7.5 — Configuration authority binding.

    For ``INTERNAL_GENERIC`` mode, ``evaluated_rule_pack_authority`` is
    ``None`` and ``requested_rule_pack_identity`` is not part of the
    binding. For ``APPROVED_RULE_PACK`` mode, the binding carries the
    complete ``EvaluatedRulePackAuthority`` value object (§6.3.5).
    """

    authority_mode: AuthorityMode
    standard_system_id: str | None
    case_authority: CaseRevisionAuthority
    evaluated_rule_pack_authority: EvaluatedRulePackAuthority | None
    case_authority_evidence_refs: tuple[str, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# §8.1 — Component tokens (normalized structural fields)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ComponentTokens:
    """§9.1 — Normalized component tokens (front_head / shell / rear_head).

    Each value is either a structural token matching the §8.2 pattern
    (``^[A-Z0-9][A-Z0-9._-]{0,15}$``) or ``None``. Tokens are opaque
    to the core schema; semantic authority comes from the rule pack.
    """

    front_head: str | None
    shell: str | None
    rear_head: str | None


# ---------------------------------------------------------------------------
# §8.1 — ShellAndTubeConfigurationRequest
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ShellAndTubeConfigurationRequest:
    """§7.4 / §8.1 — Immutable request value object.

    The schema-version field is frozen at
    ``task020.configuration-request.v1`` (§8.1 line 658).
    """

    schema_version: str
    case_authority: CaseRevisionAuthority
    equipment_family: EquipmentFamily
    authority_mode: AuthorityMode
    construction_family: ConstructionFamily
    orientation: Orientation
    shell_pass_count: int
    tube_pass_count: int
    component_tokens: ComponentTokens
    standard_system_id: str | None
    requested_rule_pack_identity: RequestedRulePackIdentity | None
    evidence_refs: tuple[str, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# §9.1 — ShellAndTubeConfiguration (normalized output)
# ---------------------------------------------------------------------------


# §9.3 — closed initial deferred_capabilities set
DEFERRED_CAPABILITIES: tuple[str, ...] = (
    "TUBE_LAYOUT_NOT_COMPUTABLE",
    "SHELL_DIAMETER_NOT_COMPUTABLE",
    "THERMAL_RATING_NOT_COMPUTABLE",
    "PRESSURE_DROP_NOT_COMPUTABLE",
    "THERMAL_EXPANSION_NOT_COMPUTABLE",
    "MECHANICAL_BOUNDARY_NOT_COMPUTABLE",
    "MATERIAL_SELECTION_NOT_COMPUTABLE",
    "COST_NOT_COMPUTABLE",
    "OPTIMIZATION_NOT_COMPUTABLE",
    "REPORT_NOT_COMPUTABLE",
)


@dataclass(frozen=True)
class ShellAndTubeConfiguration:
    """§7.6 / §9.1 — Normalized shell-and-tube configuration.

    Safe for later M3 consumers to reference by ID. Carries no
    geometry or performance claim (§7.6).

    ``schema_version`` is frozen at ``task020.configuration.v1``
    (§9.1 line 754).
    """

    schema_version: str
    configuration_id: str
    configuration_hash: str
    equipment_family: EquipmentFamily
    authority_mode: AuthorityMode
    standard_claim_status: StandardClaimStatus
    construction_family: ConstructionFamily
    orientation: Orientation
    shell_pass_count: int
    tube_pass_count: int
    component_tokens: ComponentTokens
    authority_binding: ConfigurationAuthorityBinding
    case_authority: CaseRevisionAuthority
    warnings: tuple[ErrorEntry, ...] = field(default_factory=tuple)
    blockers: tuple[ErrorEntry, ...] = field(default_factory=tuple)
    deferred_capabilities: tuple[str, ...] = field(default_factory=lambda: DEFERRED_CAPABILITIES)


# ---------------------------------------------------------------------------
# §10.4 — Error entry (warning or blocker, frozen 5-field shape)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ErrorEntry:
    """§10.4 — Frozen 5-field error object (warnings and blockers).

    Every field is computation authority; localized prose rendered from
    ``message_key`` is presentation metadata and is **excluded** from
    the identity hash (§10.4 lines 925–927).
    """

    code: str
    field_path: str | None
    message_key: str
    evidence_refs: tuple[str, ...] = field(default_factory=tuple)
    details: Mapping[str, Any] | None = None


# ---------------------------------------------------------------------------
# §7.7 — ConfigurationValidationResult
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConfigurationValidationResult:
    """§7.7 — The ``VALID`` or ``BLOCKED`` result of validating a request.

    Per §10.1: a blocked validation returns no ``ShellAndTubeConfiguration``.
    Only ``status == VALID`` carries the normalized configuration.
    """

    status: ValidationStatus
    configuration: ShellAndTubeConfiguration | None = None
    warnings: tuple[ErrorEntry, ...] = field(default_factory=tuple)
    blockers: tuple[ErrorEntry, ...] = field(default_factory=tuple)
    deferred_capabilities: tuple[str, ...] = field(default_factory=lambda: DEFERRED_CAPABILITIES)


# ---------------------------------------------------------------------------
# §10.2 / §10.3 — Closed blocker / warning code enums
# ---------------------------------------------------------------------------


class BlockerCode(enum.StrEnum):
    """§10.2 — Closed set of TASK-020 blocker codes.

    Only codes that the validation pipeline is allowed to emit. Any
    blocker code outside this set is a contract violation.
    """

    # §10.2 schema + case-authority + structural validators
    STC_SCHEMA_VERSION_UNSUPPORTED = "STC_SCHEMA_VERSION_UNSUPPORTED"
    STC_UNKNOWN_FIELD = "STC_UNKNOWN_FIELD"
    STC_CASE_AUTHORITY_MISSING = "STC_CASE_AUTHORITY_MISSING"
    STC_CASE_REVISION_STATUS_BLOCKED = "STC_CASE_REVISION_STATUS_BLOCKED"
    STC_CASE_PAYLOAD_HASH_INVALID = "STC_CASE_PAYLOAD_HASH_INVALID"
    STC_CASE_DOMAIN_SNAPSHOT_HASH_INVALID = "STC_CASE_DOMAIN_SNAPSHOT_HASH_INVALID"
    STC_CASE_REVISION_ID_MISSING = "STC_CASE_REVISION_ID_MISSING"
    STC_EQUIPMENT_FAMILY_INVALID = "STC_EQUIPMENT_FAMILY_INVALID"
    STC_AUTHORITY_MODE_INVALID = "STC_AUTHORITY_MODE_INVALID"
    STC_CONSTRUCTION_FAMILY_INVALID = "STC_CONSTRUCTION_FAMILY_INVALID"
    STC_ORIENTATION_INVALID = "STC_ORIENTATION_INVALID"
    STC_PASS_COUNT_INVALID = "STC_PASS_COUNT_INVALID"
    STC_TOKEN_MALFORMED = "STC_TOKEN_MALFORMED"
    STC_AUTHORITY_FIELDS_INCONSISTENT = "STC_AUTHORITY_FIELDS_INCONSISTENT"
    # Rule-pack blockers (Slice A emits STC_RULE_PACK_REQUIRED only;
    # all other rule-pack codes are Slice B territory and are still
    # defined here for the closed-set guarantee).
    STC_RULE_PACK_REQUIRED = "STC_RULE_PACK_REQUIRED"
    STC_RULE_PACK_NOT_FOUND = "STC_RULE_PACK_NOT_FOUND"
    STC_RULE_PACK_VALIDATION_FAILED = "STC_RULE_PACK_VALIDATION_FAILED"
    STC_RULE_PACK_VALIDATION_REPORT_MISMATCH = "STC_RULE_PACK_VALIDATION_REPORT_MISMATCH"
    STC_REQUESTED_RULE_PACK_IDENTITY_MISSING = "STC_REQUESTED_RULE_PACK_IDENTITY_MISSING"
    STC_REQUESTED_RULE_PACK_IDENTITY_MISMATCH = "STC_REQUESTED_RULE_PACK_IDENTITY_MISMATCH"
    STC_RULE_PACK_CANONICAL_HASH_MISMATCH = "STC_RULE_PACK_CANONICAL_HASH_MISMATCH"
    STC_REQUIRED_RULE_MISSING = "STC_REQUIRED_RULE_MISSING"
    STC_RULE_UNAPPROVED = "STC_RULE_UNAPPROVED"
    STC_RULE_CANONICAL_HASH_MISMATCH = "STC_RULE_CANONICAL_HASH_MISMATCH"
    STC_RULE_LICENSE_BLOCKED = "STC_RULE_LICENSE_BLOCKED"
    STC_RULE_PROVENANCE_BLOCKED = "STC_RULE_PROVENANCE_BLOCKED"
    STC_RULE_TYPE_UNRECOGNIZED = "STC_RULE_TYPE_UNRECOGNIZED"
    STC_RULE_DUPLICATE_IDENTITY = "STC_RULE_DUPLICATE_IDENTITY"
    STC_RULE_APPLICABILITY_UNRESOLVED = "STC_RULE_APPLICABILITY_UNRESOLVED"
    STC_RULE_CONSTRAINT_MISSING = "STC_RULE_CONSTRAINT_MISSING"
    STC_RULE_NORMALIZATION_CONFLICT = "STC_RULE_NORMALIZATION_CONFLICT"
    STC_RULE_RANGE_INTERSECTION_EMPTY = "STC_RULE_RANGE_INTERSECTION_EMPTY"
    STC_RULE_ORIENTATION_INTERSECTION_EMPTY = "STC_RULE_ORIENTATION_INTERSECTION_EMPTY"
    STC_RULE_TOKEN_INTERSECTION_EMPTY = "STC_RULE_TOKEN_INTERSECTION_EMPTY"
    STC_RULE_SLOT_NULLABLE_MISSING = "STC_RULE_SLOT_NULLABLE_MISSING"
    STC_TOKEN_UNSUPPORTED_BY_RULE_PACK = "STC_TOKEN_UNSUPPORTED_BY_RULE_PACK"
    STC_CONFIGURATION_COMBINATION_BLOCKED = "STC_CONFIGURATION_COMBINATION_BLOCKED"
    STC_PROVENANCE_INCOMPLETE = "STC_PROVENANCE_INCOMPLETE"
    STC_CANONICALIZATION_FAILED = "STC_CANONICALIZATION_FAILED"


class WarningCode(enum.StrEnum):
    """§10.3 — Closed set of TASK-020 warning codes."""

    STC_GENERIC_CONFIGURATION_NO_STANDARD_CLAIM = "STC_GENERIC_CONFIGURATION_NO_STANDARD_CLAIM"
    STC_RESTRICTED_STANDARD_METADATA_ONLY = "STC_RESTRICTED_STANDARD_METADATA_ONLY"
    STC_ORIENTATION_UNSPECIFIED = "STC_ORIENTATION_UNSPECIFIED"


__all__ = [
    "AuthorityMode",
    "BlockerCode",
    "CaseRevisionAuthority",
    "CaseRevisionStatus",
    "ComponentTokens",
    "ConfigurationAuthorityBinding",
    "ConfigurationValidationResult",
    "ConstructionFamily",
    "DEFERRED_CAPABILITIES",
    "EquipmentFamily",
    "ErrorEntry",
    "EvaluatedRulePackAuthority",
    "Orientation",
    "RequestRulePackIdentity",
    "RequestedRulePackIdentity",
    "SelectedRuleAuthority",
    "ShellAndTubeConfiguration",
    "ShellAndTubeConfigurationRequest",
    "StandardClaimStatus",
    "TASK_020_ACCEPTED_LIFECYCLE_VALUES",
    "ValidationStatus",
    "WarningCode",
    "replace",
]
