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
    # Rule-pack blockers (Slice A emits STC_RULE_PACK_REQUIRED only;
    # S2 Phase B emits the full slice):
    STC_RULE_PACK_REQUIRED = "STC_RULE_PACK_REQUIRED"
    STC_RULE_PACK_NOT_FOUND = "STC_RULE_PACK_NOT_FOUND"
    STC_RULE_PACK_VALIDATION_FAILED = "STC_RULE_PACK_VALIDATION_FAILED"
    STC_RULE_PACK_VALIDATION_REPORT_MISMATCH = "STC_RULE_PACK_VALIDATION_REPORT_MISMATCH"
    # §19.F — input-presence blockers for the
    # ``validate_request(payload, *, loaded_rule_pack, validation_report)``
    # top-level entry point. Phase A deferred these to Phase B.
    STC_RULE_PACK_NOT_EXPECTED_IN_MODE = "STC_RULE_PACK_NOT_EXPECTED_IN_MODE"
    STC_RULE_PACK_ADAPTER_INPUTS_MISSING = "STC_RULE_PACK_ADAPTER_INPUTS_MISSING"
    STC_RULE_PACK_ADAPTER_INPUTS_INCOMPLETE = "STC_RULE_PACK_ADAPTER_INPUTS_INCOMPLETE"
    STC_RULE_PACK_CANONICAL_HASH_MISMATCH = "STC_RULE_PACK_CANONICAL_HASH_MISMATCH"
    STC_REQUESTED_RULE_PACK_IDENTITY_MISSING = "STC_REQUESTED_RULE_PACK_IDENTITY_MISSING"
    STC_REQUESTED_RULE_PACK_IDENTITY_MISMATCH = "STC_REQUESTED_RULE_PACK_IDENTITY_MISMATCH"
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
    "CASE_REVISION_AUTHORITY_VALUES",
    "CaseRevisionAuthority",
    "CaseRevisionStatus",
    "CLOSED_RULE_TYPES",
    "ComponentTokens",
    "ConfigurationAuthorityBinding",
    "ConfigurationRuleEvaluation",
    "ConfigurationValidationResult",
    "ConstructionFamily",
    "DEFERRED_CAPABILITIES",
    "EquipmentFamily",
    "ErrorEntry",
    "EvaluatedRulePackAuthority",
    "LoadedRulePackView",
    "Orientation",
    "PROFILE_ID_TASK_020_CONFIGURATION_RULE_V1",
    "RequestRulePackIdentity",
    "RequestedRulePackIdentity",
    "RulePackValidationReport",
    "SelectedRuleAuthority",
    "ShellAndTubeConfiguration",
    "ShellAndTubeConfigurationRequest",
    "StandardClaimStatus",
    "TASK_020_ACCEPTED_LIFECYCLE_VALUES",
    "TASK_020_VALIDATION_REPORT_OK",
    "ValidationStatus",
    "WarningCode",
    "replace",
]  # noqa: E501


# ---------------------------------------------------------------------------
# §6.3.1 — TASK-020-owned typed view: LoadedRulePackView (S2, frozen)
# ---------------------------------------------------------------------------


PROFILE_ID_TASK_020_CONFIGURATION_RULE_V1 = "task020.configuration-rule.v1"

# §12.3 — closed rule_type set
CLOSED_RULE_TYPES: tuple[str, ...] = (
    "COMPONENT_TOKEN_ALLOWLIST",
    "CONSTRUCTION_FAMILY_NORMALIZATION",
    "PASS_COUNT_ALLOWED_RANGE",
    "ORIENTATION_ALLOWLIST",
    "CONFIGURATION_COMBINATION_BLOCKLIST",
)

TASK_020_VALIDATION_REPORT_OK = "ok"

CASE_REVISION_AUTHORITY_VALUES: tuple[str, ...] = (
    "committed",
    "superseded",
    "archived",
    "draft_blocked",
)


@dataclass(frozen=True)
class LoadedRulePackView:
    """§6.3.1 — TASK-020-owned typed view over TASK-012 ``load_rule_pack``.

    The view is a frozen wrapper around the plain ``dict`` returned by
    ``hexagent.rule_packs.loader.load_rule_pack(root)``. It exposes the
    three identity fields the TASK-020 adapter reads from the manifest
    and the per-rule artifact dictionary keyed by ``rule_id``. The view
    does **not** re-validate, re-verify, or re-canonicalize anything —
    it just freezes the dict-by-key shape so that the adapter can rely
    on deterministic iteration over the dict (ascending Unicode code-point
    order on the ``rule_id`` key, per §6.3.1's frozen iteration
    discipline).
    """

    manifest: Mapping[str, object]
    rules: Mapping[str, Mapping[str, object]]
    provenance_edges: tuple[Mapping[str, object], ...]
    permission_evidence: Mapping[str, Mapping[str, object]]
    rule_pack_id: str
    rule_pack_version: str
    rule_pack_canonical_hash: str
    rule_count: int

    def __post_init__(self) -> None:
        # Local defensive checks only — these mirror what the adapter
        # would otherwise re-check at runtime; the typed view construction
        # is the boundary where the loader result becomes a TASK-020
        # value object. STC_* errors are emitted by the adapter, not
        # here.
        for name in ("rule_pack_id", "rule_pack_version", "rule_pack_canonical_hash"):
            v = getattr(self, name)
            if not isinstance(v, str) or not v:
                raise TypeError(
                    f"LoadedRulePackView.{name} must be a non-empty str, got {type(v).__name__}"
                )
        if not isinstance(self.rule_count, int) or self.rule_count < 0:
            raise TypeError(
                "LoadedRulePackView.rule_count must be a non-negative int, "
                f"got {type(self.rule_count).__name__}"
            )
        if len(self.rules) != self.rule_count:
            raise ValueError(
                "LoadedRulePackView.rule_count disagrees with len(rules) "
                f"({self.rule_count} vs {len(self.rules)})"
            )


# ---------------------------------------------------------------------------
# §6.3.2 — TASK-020-owned typed view: RulePackValidationReport (S2, frozen)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RulePackValidationReport:
    """§6.3.2 — TASK-020-owned typed view over TASK-012 ``validate_rule_pack``.

    Adapter reads only ``status`` (must equal ``"ok"``), the identity
    triple from ``manifest`` (``rule_pack_id`` / ``rule_pack_version`` /
    ``canonical_hash``), and ``rule_count``. The ``errors`` list is
    carried so the adapter can confirm the report shape but it is
    **never parsed** to extract per-rule blockers (per §6.3.2 + §6.3.3).
    """

    status: str
    manifest: Mapping[str, object]
    rule_count: int
    errors: tuple[Mapping[str, object], ...] = field(default_factory=tuple)
    rule_pack_id: str = ""
    rule_pack_version: str = ""
    rule_pack_canonical_hash: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.status, str) or not self.status:
            raise TypeError("RulePackValidationReport.status must be a non-empty str")
        if not isinstance(self.rule_count, int) or self.rule_count < 0:
            raise TypeError("RulePackValidationReport.rule_count must be a non-negative int")


# ---------------------------------------------------------------------------
# §20.D — ConfigurationRuleEvaluation (S2 success-only value object)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConfigurationRuleEvaluation:
    """§20.D — Frozen success-only value object returned by the adapter.

    Two fields exactly; no parallel lists, no optional fields, no
    blocked-state representation. The ``validate(...)`` method raises
    ``BlockerError`` on any non-success path (per §6.3); a partial
    result is **not** permitted.
    """

    normalized_construction_family: ConstructionFamily
    evaluated_rule_pack_authority: EvaluatedRulePackAuthority

    def __post_init__(self) -> None:
        if not isinstance(self.normalized_construction_family, ConstructionFamily):
            raise TypeError(
                "ConfigurationRuleEvaluation.normalized_construction_family "
                "must be ConstructionFamily, got "
                f"{type(self.normalized_construction_family).__name__}"
            )
        if not isinstance(self.evaluated_rule_pack_authority, EvaluatedRulePackAuthority):
            raise TypeError(
                "ConfigurationRuleEvaluation.evaluated_rule_pack_authority "
                "must be EvaluatedRulePackAuthority, got "
                f"{type(self.evaluated_rule_pack_authority).__name__}"
            )
        # Cross-check: evaluated authority's identity triple must agree
        # on its own fields. If it doesn't, construction fails (this
        # enforces the §6.3.5 invariant that the adapter only builds an
        # authority whose three identity fields are mutually consistent).
        era = self.evaluated_rule_pack_authority
        if not (era.rule_pack_id and era.rule_pack_version and era.rule_pack_canonical_hash):
            raise ValueError(
                "ConfigurationRuleEvaluation.evaluated_rule_pack_authority "
                "must have non-empty identity triple"
            )
