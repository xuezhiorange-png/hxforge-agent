"""TASK-169 v0.6 Golden and release-acceptance models."""

# fmt: off

from __future__ import annotations

import enum
from dataclasses import dataclass

from hexagent.exchangers.shell_tube.selection_release.models import Task169Request

TASK169_RELEASE_SCHEMA_VERSION = "task169.release-acceptance-request.v1"
TASK169_RELEASE_RESULT_SCHEMA_VERSION = "task169.release-acceptance-result.v1"
TASK169_RELEASE_VERSION = "task169.release.v1"
TASK169_RELEASE_SOURCE_DEFINITION_ID = "TASK169-RELEASE-SOURCE-DEFINITION-ISSUE-265"
TASK169_RELEASE_SOFTWARE_VERSION = "task169.release-acceptance-impl-v1"


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
    golden_id: GoldenCaseId
    source_id: str
    source_location: str
    redistribution_status: str
    normalized_input_identity: str
    expected_result_identity: str | None
    approved_numeric_expectations: tuple[tuple[str, str], ...]
    tolerance_class: str
    reviewer_evidence_refs: tuple[str, ...]
    provenance_source_hash: str
    selection_request: Task169Request

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
            tuple(
                sorted(
                    self.reviewer_evidence_refs,
                    key=lambda item: item.encode("utf-8"),
                )
            ),
        )
        has_identity = self.expected_result_identity is not None
        has_numeric = bool(self.approved_numeric_expectations)
        if has_identity == has_numeric:
            raise ValueError(
                "TASK-169 Golden must bind exactly one expectation authority branch"
            )


@dataclass(frozen=True, slots=True)
class Task169RuntimeParityEvidence:
    runtime_id: str
    golden_result_hashes: tuple[tuple[str, str], ...]
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "golden_result_hashes",
            tuple(
                sorted(
                    self.golden_result_hashes,
                    key=lambda item: item[0].encode("utf-8"),
                )
            ),
        )
        object.__setattr__(
            self,
            "evidence_refs",
            tuple(
                sorted(
                    self.evidence_refs,
                    key=lambda item: item.encode("utf-8"),
                )
            ),
        )


@dataclass(frozen=True, slots=True)
class Task169ReleaseRequest:
    schema_version: str
    release_version: str
    source_definition_id: str
    golden_cases: tuple[Task169GoldenCase, ...]
    runtime_parity_evidence: tuple[Task169RuntimeParityEvidence, ...]
    request_metadata: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class GoldenAcceptanceRecord:
    golden_id: GoldenCaseId
    status: AcceptanceStatus
    selection_result_hash: str | None
    selection_result_id: str | None
    recommended_candidate_id: str | None
    reason_codes: tuple[str, ...]


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
    overall_status: AcceptanceStatus
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
    "Task169RuntimeParityEvidence",
]

# fmt: on
