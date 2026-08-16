"""TASK-029 frozen dataclasses for all §3 schemas.

Field order and counts are frozen in ``canonical.py`` field-order tuples.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, Final

from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.canonical import (
    BLOCKER_ENTRY_FIELD_COUNT,
    COMPLETENESS_LEDGER_FIELD_COUNT,
    COMPOSITION_AUTHORITY_FIELD_COUNT,
    EXCLUSION_AUTHORITY_FIELD_COUNT,
    LEDGER_EXCLUSION_EVIDENCE_FIELD_COUNT,
    LEDGER_MEMBER_EVIDENCE_FIELD_COUNT,
    MEMBER_AUTHORITY_FIELD_COUNT,
    PROVENANCE_FIELD_COUNT,
    RAW_PROJECTION_FIELD_COUNT,
    TASK029_BLOCKED_RESULT_FIELD_COUNT,
    TASK029_RAW_BOUNDARY_BLOCKED_FIELD_COUNT,
    TASK029_REQUEST_FIELD_COUNT,
    TASK029_SUCCESS_RESULT_FIELD_COUNT,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.enums import (
    CompletenessStatus,
    ExclusionReason,
    ExclusionStatus,
    IdentityCompatibilityStatus,
    MemberStatus,
    PathContinuityStatus,
    ProducerMemberKind,
    ProducerTask,
    Task029BlockerCode,
    Task029FlowDirectionAssertion,
)

if TYPE_CHECKING:
    from hexagent.exchangers.shell_tube.tube_side.friction_pressure_drop import (
        Task027SuccessResult,
    )
    from hexagent.exchangers.shell_tube.tube_side_local_loss.result import (
        Task028SuccessResult,
    )


@dataclass(frozen=True)
class TubeSidePressurePathMemberAuthority:
    """§3.1 — Immutable 13-field member authority record."""

    schema_version: str
    member_id: str
    global_path_sequence_index: int
    producer_task: ProducerTask
    producer_member_kind: ProducerMemberKind
    producer_component_identity: str
    expected_producer_component_type: str
    expected_producer_authority_hash: str
    expected_upstream_reference_plane: str
    expected_downstream_reference_plane: str
    expected_multiplicity: int
    geometry_evidence_refs: tuple[str, ...]
    member_authority_hash: str


@dataclass(frozen=True)
class TubeSidePressurePathExclusionAuthority:
    """§3.2 — Immutable 6-field exclusion authority record."""

    schema_version: str
    exclusion_id: str
    excluded_item_identity: str
    exclusion_reason: ExclusionReason
    evidence_refs: tuple[str, ...]
    exclusion_authority_hash: str


@dataclass(frozen=True)
class TubeSidePressurePathCompositionAuthority:
    """§3.3 — Immutable 9-field composition authority record."""

    schema_version: str
    modeled_path_id: str
    flow_direction_assertion: Task029FlowDirectionAssertion
    start_reference_plane: str
    end_reference_plane: str
    member_authorities: tuple[TubeSidePressurePathMemberAuthority, ...]
    exclusion_authorities: tuple[TubeSidePressurePathExclusionAuthority, ...]
    geometry_evidence_refs: tuple[str, ...]
    composition_authority_hash: str


@dataclass(frozen=True)
class Task029Request:
    """§3.4 — Immutable 6-field typed request."""

    schema_version: str
    profile_id: str
    task027_success_result: Task027SuccessResult
    task028_success_result: Task028SuccessResult
    composition_authority: TubeSidePressurePathCompositionAuthority
    request_hash: str


@dataclass(frozen=True)
class TubeSidePressurePathLedgerMemberEvidence:
    """§3.5 — Immutable 16-field ledger member evidence record."""

    schema_version: str
    member_id: str
    global_path_sequence_index: int
    producer_task: ProducerTask
    producer_result_hash: str
    producer_member_kind: ProducerMemberKind
    producer_component_identity: str
    producer_component_type: str
    producer_authority_hash: str
    upstream_reference_plane: str
    downstream_reference_plane: str
    expected_multiplicity: int
    observed_multiplicity: int
    pressure_contribution_pa: Decimal
    composition_member_authority_hash: str
    member_status: MemberStatus


@dataclass(frozen=True)
class TubeSidePressurePathLedgerExclusionEvidence:
    """§3.6 — Immutable 7-field ledger exclusion evidence record."""

    schema_version: str
    exclusion_id: str
    excluded_item_identity: str
    exclusion_reason: ExclusionReason
    evidence_refs: tuple[str, ...]
    exclusion_authority_hash: str
    exclusion_status: ExclusionStatus


@dataclass(frozen=True)
class TubeSidePressurePathCompletenessLedger:
    """§3.7 — Immutable 12-field completeness ledger record."""

    schema_version: str
    modeled_path_id: str
    modeled_start_reference_plane: str
    modeled_end_reference_plane: str
    expected_member_count: int
    observed_member_count: int
    ordered_member_evidence: tuple[TubeSidePressurePathLedgerMemberEvidence, ...]
    ordered_exclusion_evidence: tuple[TubeSidePressurePathLedgerExclusionEvidence, ...]
    path_continuity_status: PathContinuityStatus
    identity_compatibility_status: IdentityCompatibilityStatus
    completeness_status: CompletenessStatus
    ledger_hash: str


@dataclass(frozen=True)
class Task029Provenance:
    """§3.13 — Immutable 5-field provenance record."""

    task_id: str
    design_contract_path: str
    implementation_software_version: str
    input_evidence_refs: tuple[str, ...]
    upstream_identity_hashes: tuple[str, ...]


@dataclass(frozen=True)
class FrozenTask029RawProjection:
    """§3.11 — Immutable 2-field raw projection capture."""

    projection_kind: str
    canonical_bytes_hex: str


@dataclass(frozen=True)
class Task029BlockerEntry:
    """§3.12 — Immutable 4-field blocker entry.

    ``field_path`` is a single STRING path per DC-004, not a tuple.
    """

    code: Task029BlockerCode
    field_path: str
    message_key: str
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True)
class Task029SuccessResult:
    """§3.8 — Immutable 18-field success result."""

    schema_version: str
    profile_id: str
    request_hash: str
    result_hash: str
    result_id: str
    task027_result_hash: str
    task028_result_hash: str
    task025_hydraulic_authority_hash: str
    task025_result_hash: str
    task026_result_hash: str
    property_snapshot_hash: str
    composition_authority_hash: str
    completeness_ledger: TubeSidePressurePathCompletenessLedger
    modeled_total_tube_side_pressure_drop_pa: Decimal
    warnings: tuple[str, ...]
    blockers: tuple[Task029BlockerEntry, ...]
    deferred_capabilities: tuple[str, ...]
    provenance: Task029Provenance


@dataclass(frozen=True)
class Task029BlockedResult:
    """§3.9 — Immutable 18-field typed blocked result."""

    schema_version: str
    profile_id: str
    request_hash: str
    result_hash: str
    result_id: str
    task027_result_hash: str
    task028_result_hash: str
    task025_hydraulic_authority_hash: str
    task025_result_hash: str
    task026_result_hash: str
    property_snapshot_hash: str
    composition_authority_hash: str
    raw_request_projection: FrozenTask029RawProjection | None
    raw_upstream_blocked_projection: FrozenTask029RawProjection | None
    warnings: tuple[str, ...]
    blockers: tuple[Task029BlockerEntry, ...]
    deferred_capabilities: tuple[str, ...]
    provenance: Task029Provenance | None


@dataclass(frozen=True)
class Task029RawBoundaryBlockedResult:
    """§3.10 — Immutable 6-field raw-boundary blocked result."""

    schema_version: str
    implementation_software_version: str
    raw_request_projection: FrozenTask029RawProjection
    blockers: tuple[Task029BlockerEntry, ...]
    warnings: tuple[str, ...]
    deferred_capabilities: tuple[str, ...]


_FIELD_COUNT_ASSERTIONS: Final[tuple[tuple[str, int], ...]] = (
    ("MEMBER_AUTHORITY_FIELD_COUNT", MEMBER_AUTHORITY_FIELD_COUNT),
    ("EXCLUSION_AUTHORITY_FIELD_COUNT", EXCLUSION_AUTHORITY_FIELD_COUNT),
    ("COMPOSITION_AUTHORITY_FIELD_COUNT", COMPOSITION_AUTHORITY_FIELD_COUNT),
    ("TASK029_REQUEST_FIELD_COUNT", TASK029_REQUEST_FIELD_COUNT),
    ("LEDGER_MEMBER_EVIDENCE_FIELD_COUNT", LEDGER_MEMBER_EVIDENCE_FIELD_COUNT),
    ("LEDGER_EXCLUSION_EVIDENCE_FIELD_COUNT", LEDGER_EXCLUSION_EVIDENCE_FIELD_COUNT),
    ("COMPLETENESS_LEDGER_FIELD_COUNT", COMPLETENESS_LEDGER_FIELD_COUNT),
    ("TASK029_SUCCESS_RESULT_FIELD_COUNT", TASK029_SUCCESS_RESULT_FIELD_COUNT),
    ("TASK029_BLOCKED_RESULT_FIELD_COUNT", TASK029_BLOCKED_RESULT_FIELD_COUNT),
    ("TASK029_RAW_BOUNDARY_BLOCKED_FIELD_COUNT", TASK029_RAW_BOUNDARY_BLOCKED_FIELD_COUNT),
    ("RAW_PROJECTION_FIELD_COUNT", RAW_PROJECTION_FIELD_COUNT),
    ("BLOCKER_ENTRY_FIELD_COUNT", BLOCKER_ENTRY_FIELD_COUNT),
    ("PROVENANCE_FIELD_COUNT", PROVENANCE_FIELD_COUNT),
)

for _label, _expected in _FIELD_COUNT_ASSERTIONS:
    assert _expected > 0, _label

__all__ = [
    "TubeSidePressurePathMemberAuthority",
    "TubeSidePressurePathExclusionAuthority",
    "TubeSidePressurePathCompositionAuthority",
    "Task029Request",
    "TubeSidePressurePathLedgerMemberEvidence",
    "TubeSidePressurePathLedgerExclusionEvidence",
    "TubeSidePressurePathCompletenessLedger",
    "Task029Provenance",
    "FrozenTask029RawProjection",
    "Task029BlockerEntry",
    "Task029SuccessResult",
    "Task029BlockedResult",
    "Task029RawBoundaryBlockedResult",
]
