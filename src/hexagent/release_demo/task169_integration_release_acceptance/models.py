"""Typed TASK-169 Golden and release-acceptance models.

The release boundary intentionally carries a TASK-168 request, never a
caller-supplied TASK-168 result.  Results are observed by the release service
after it invokes the TASK-168 public validator.  Golden records are proposals
until an independent authority registers their approval.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass

from hexagent.exchangers.shell_tube.manufacturable_candidates.models import (
    Task168Request,
)
from hexagent.exchangers.shell_tube.selection_release.models import (
    TASK169_FROZEN_TOLERANCE_LEDGER,
    Task169RankingPolicy,
)

TASK169_RELEASE_SCHEMA_VERSION = "task169.release-acceptance-request.v2"
TASK169_RELEASE_RESULT_SCHEMA_VERSION = "task169.release-acceptance-result.v2"
TASK169_RELEASE_VERSION = "task169.release.v2"
TASK169_RELEASE_SOURCE_DEFINITION_ID = "TASK169-RELEASE-SOURCE-DEFINITION-ISSUE-265"
TASK169_RELEASE_SOFTWARE_VERSION = "task169.release-acceptance-impl-v2"
TASK169_GOLDEN_TOLERANCE_CLASS = "TASK165_V06_FROZEN"
TASK169_PROPOSED_IDENTITY_STATUS = "PROPOSED_FOR_REVIEW"
TASK169_APPROVED_IDENTITY_STATUS = "APPROVED"


class GoldenCaseId(enum.StrEnum):
    V06_G01 = "V06-G01"
    V06_G02 = "V06-G02"
    V06_G03 = "V06-G03"
    V06_G04 = "V06-G04"
    V06_G05 = "V06-G05"


class AcceptanceStatus(enum.StrEnum):
    PASS = "PASS"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True, slots=True)
class Task169GoldenCase:
    """One proposed or independently approved TASK-165 Golden case.

    ``task168_request`` is the only execution input.  The expected identity
    fields are evidence bindings, not values that authorize a Golden by
    themselves; ``review_status=PROPOSED`` is deliberately non-authoritative.
    """

    golden_id: GoldenCaseId
    source_id: str
    source_location: str
    source_class: str
    redistribution_status: str
    normalized_input_identity: str
    task168_request: Task168Request
    task168_request_hash: str
    expected_task168_result_hash: str
    expected_task168_result_id: str
    expected_task168_result_status: str
    ranking_policy: Task169RankingPolicy
    expected_task169_result_hash: str | None
    expected_task169_result_id: str | None
    approved_numeric_expectations: tuple[tuple[str, str], ...]
    tolerance_class: str
    provenance_source_hash: str
    reviewer_evidence_refs: tuple[str, ...]
    review_status: str = "PROPOSED"
    approved_by: str = ""
    approval_evidence: tuple[str, ...] = ()
    expected_identity_status: str = TASK169_PROPOSED_IDENTITY_STATUS
    negative_class: str | None = None
    expected_blocker_code: str | None = None
    expected_blocker_owner: str | None = None
    no_recommendation_required: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "approved_numeric_expectations",
            tuple(
                sorted(
                    self.approved_numeric_expectations,
                    key=lambda item: (
                        item[0].encode("utf-8"),
                        item[1].encode("utf-8"),
                    ),
                )
            ),
        )
        object.__setattr__(
            self,
            "reviewer_evidence_refs",
            tuple(sorted(self.reviewer_evidence_refs, key=lambda item: item.encode("utf-8"))),
        )
        object.__setattr__(
            self,
            "approval_evidence",
            tuple(sorted(self.approval_evidence, key=lambda item: item.encode("utf-8"))),
        )
        if type(self.no_recommendation_required) is not bool:
            raise ValueError("no_recommendation_required must be bool")
        has_identity = self.expected_task169_result_hash is not None
        has_numeric = bool(self.approved_numeric_expectations)
        if has_identity == has_numeric:
            raise ValueError("TASK-169 Golden must bind exactly one TASK-169 expectation branch")
        if (self.expected_task169_result_hash is None) != (self.expected_task169_result_id is None):
            raise ValueError("TASK-169 result hash and ID must be supplied together")


@dataclass(frozen=True, slots=True)
class Task169ReleaseRequest:
    """Release input with frozen policy values and no caller parity evidence."""

    schema_version: str
    release_version: str
    source_definition_id: str
    golden_cases: tuple[Task169GoldenCase, ...]
    request_metadata: tuple[tuple[str, str], ...] = ()
    frozen_tolerance_ledger: tuple[tuple[str, str], ...] = TASK169_FROZEN_TOLERANCE_LEDGER


@dataclass(frozen=True, slots=True)
class GoldenAcceptanceRecord:
    golden_id: GoldenCaseId
    status: AcceptanceStatus
    task168_result_hash: str | None
    task168_result_id: str | None
    selection_result_hash: str | None
    selection_result_id: str | None
    recommended_candidate_id: str | None
    recommended_candidate_hash: str | None
    reason_codes: tuple[str, ...]
    alternative_reason_codes: tuple[tuple[str, tuple[str, ...]], ...] = ()
    exclusion_reason_codes: tuple[tuple[str, tuple[str, ...]], ...] = ()


@dataclass(frozen=True, slots=True)
class AcceptanceGateRecord:
    gate_id: str
    status: AcceptanceStatus
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Task169ReleaseResult:
    schema_version: str
    release_version: str
    implementation_software_version: str
    source_definition_id: str
    request_hash: str
    frozen_tolerance_ledger: tuple[tuple[str, str], ...]
    golden_records: tuple[GoldenAcceptanceRecord, ...]
    acceptance_gates: tuple[AcceptanceGateRecord, ...]
    trusted_runtime_observation_hash: str
    trusted_runtime_status: AcceptanceStatus
    overall_status: AcceptanceStatus
    blocker_codes: tuple[str, ...]
    result_hash: str
    result_id: str


@dataclass(frozen=True, slots=True)
class Task169ReleaseBlockedResult:
    schema_version: str
    release_version: str
    implementation_software_version: str
    request_hash: str
    blocker_codes: tuple[str, ...]
    result_hash: str
    result_id: str


@dataclass(frozen=True, slots=True)
class Task169ReleaseValidationResult:
    valid: Task169ReleaseResult | None = None
    blocked: Task169ReleaseBlockedResult | None = None

    def __post_init__(self) -> None:
        if int(self.valid is not None) + int(self.blocked is not None) != 1:
            raise ValueError("TASK-169 release result must populate exactly one branch")


__all__ = [
    "AcceptanceGateRecord",
    "AcceptanceStatus",
    "GoldenAcceptanceRecord",
    "GoldenCaseId",
    "TASK169_GOLDEN_TOLERANCE_CLASS",
    "TASK169_APPROVED_IDENTITY_STATUS",
    "TASK169_PROPOSED_IDENTITY_STATUS",
    "TASK169_RELEASE_RESULT_SCHEMA_VERSION",
    "TASK169_RELEASE_SCHEMA_VERSION",
    "TASK169_RELEASE_SOFTWARE_VERSION",
    "TASK169_RELEASE_SOURCE_DEFINITION_ID",
    "TASK169_RELEASE_VERSION",
    "Task169GoldenCase",
    "Task169ReleaseBlockedResult",
    "Task169ReleaseRequest",
    "Task169ReleaseResult",
    "Task169ReleaseValidationResult",
]
