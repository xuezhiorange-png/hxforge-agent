"""Typed TASK-169 selection and v0.6 release-boundary models.

TASK-169 consumes a verified TASK-168 batch.  It does not recompute candidate
physics; it verifies the upstream result identity, filters hard blockers,
applies one explicit deterministic ranking policy, and emits a traceable
recommendation surface.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from decimal import Decimal

from hexagent.exchangers.shell_tube.manufacturable_candidates.models import Task168BatchResult

TASK169_SCHEMA_VERSION = "task169.selection-request.v1"
TASK169_VERSION = "task169.v1"
TASK169_RESULT_SCHEMA_VERSION = "task169.selection-result.v1"
TASK169_BLOCKED_SCHEMA_VERSION = "task169.selection-blocked.v1"
TASK169_SOURCE_DEFINITION_ID = "TASK169-SOURCE-DEFINITION-ISSUE-265"
TASK169_IMPLEMENTATION_SOFTWARE_VERSION = "task169.selection-release-impl-v1"
TASK169_DESIGN_CONTRACT_PATH = (
    "docs/tasks/TASK-169-selection-integration-golden-release-acceptance.md"
)

TASK165_V06_TOLERANCE_CLASS = "TASK165_V06_FROZEN"
TASK169_FROZEN_TOLERANCE_LEDGER = (
    ("ENERGY_BALANCE_RELATIVE_ERROR_MAX", "0.001"),
    ("THERMAL_DUTY_CLOSURE_RELATIVE_ERROR_MAX", "0.001"),
    ("DIRECT_PUBLISHED_EQUATION_REPRODUCTION_RELATIVE_ERROR_MAX", "0.005"),
    ("PUBLISHED_REFERENCE_SHELL_H_RELATIVE_ERROR_MAX", "0.02"),
    ("PUBLISHED_REFERENCE_SHELL_DP_RELATIVE_ERROR_MAX", "0.02"),
    ("MANUFACTURABLE_CATALOG_MEMBERSHIP", "EXACT"),
    ("HARD_CONSTRAINT_STATUS", "EXACT"),
    ("RANKING_ORDER", "EXACT"),
    ("CANONICAL_IDENTITY_REPLAY", "EXACT"),
    ("PY311_PY312_CANONICAL_PARITY", "EXACT"),
)

SUPPORTED_RANKING_METRICS = (
    "modeled_ua_w_k",
    "q_method_w",
    "shell_dp_pa",
    "tube_dp_pa",
    "physical_tube_count",
    "tube_hole_count",
)


class RankingDirection(enum.StrEnum):
    MINIMIZE = "MINIMIZE"
    MAXIMIZE = "MAXIMIZE"


class SelectionStatus(enum.StrEnum):
    SELECTED = "SELECTED"
    NO_RECOMMENDABLE_CANDIDATE = "NO_RECOMMENDABLE_CANDIDATE"
    BLOCKED = "BLOCKED"


class ValidationStatus(enum.StrEnum):
    VALID = "VALID"
    TYPED_BLOCKED = "TYPED_BLOCKED"


@dataclass(frozen=True, slots=True)
class RankingObjective:
    metric: str
    direction: RankingDirection
    weight: Decimal
    scale: Decimal


@dataclass(frozen=True, slots=True)
class Task169RankingPolicy:
    policy_id: str
    policy_version: str
    source_definition_id: str
    source_id: str
    authority_origin: str
    approval_status: str
    top_n: int
    warning_penalty: Decimal
    objectives: tuple[RankingObjective, ...]
    tie_break_rule: str
    evidence_refs: tuple[str, ...] = ()
    provenance_refs: tuple[str, ...] = ()
    canonical_hash: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "evidence_refs",
            tuple(sorted(self.evidence_refs, key=lambda item: item.encode("utf-8"))),
        )
        object.__setattr__(
            self,
            "provenance_refs",
            tuple(sorted(self.provenance_refs, key=lambda item: item.encode("utf-8"))),
        )


@dataclass(frozen=True, slots=True)
class Task169Request:
    schema_version: str
    task169_version: str
    source_definition_id: str
    task168_result: Task168BatchResult
    ranking_policy: Task169RankingPolicy
    request_metadata: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class CandidateExclusionRecord:
    candidate_id: str
    candidate_hash: str
    source_status: str
    reason_code: str
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CandidateRankingRecord:
    rank: int
    candidate_id: str
    candidate_hash: str
    source_status: str
    composite_score: Decimal
    objective_values: tuple[tuple[str, str], ...]
    warning_count: int
    record_hash: str
    warning_penalty_contribution: Decimal = Decimal("0")
    reason_codes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Task169Result:
    schema_version: str
    task169_version: str
    implementation_software_version: str
    source_definition_id: str
    request_hash: str
    source_task168_result_hash: str
    source_task168_result_id: str
    source_task168_provenance_hash: str
    ranking_policy_hash: str
    selection_status: SelectionStatus
    recommendable_candidate_count: int
    excluded_candidate_count: int
    ranked_candidates: tuple[CandidateRankingRecord, ...]
    recommended_candidate: CandidateRankingRecord | None
    alternatives: tuple[CandidateRankingRecord, ...]
    excluded_candidates: tuple[CandidateExclusionRecord, ...]
    provenance_semantic_inputs: tuple[tuple[str, str], ...]
    result_hash: str
    result_id: str
    recommendation_reason_codes: tuple[str, ...] = ()
    alternative_reason_codes: tuple[tuple[str, tuple[str, ...]], ...] = ()


@dataclass(frozen=True, slots=True)
class Task169TypedBlockedResult:
    schema_version: str
    task169_version: str
    implementation_software_version: str
    request_hash: str
    blocker_codes: tuple[str, ...]
    result_hash: str
    result_id: str


@dataclass(frozen=True, slots=True)
class Task169ValidationResult:
    status: ValidationStatus
    valid: Task169Result | None = None
    typed_blocked: Task169TypedBlockedResult | None = None

    def __post_init__(self) -> None:
        populated = int(self.valid is not None) + int(self.typed_blocked is not None)
        if populated != 1:
            raise ValueError("TASK-169 validation result must populate exactly one branch")
        if self.status is ValidationStatus.VALID and self.valid is None:
            raise ValueError("TASK-169 VALID result is missing")
        if self.status is ValidationStatus.TYPED_BLOCKED and self.typed_blocked is None:
            raise ValueError("TASK-169 TYPED_BLOCKED result is missing")


__all__ = [
    "CandidateExclusionRecord",
    "CandidateRankingRecord",
    "RankingDirection",
    "RankingObjective",
    "SelectionStatus",
    "SUPPORTED_RANKING_METRICS",
    "TASK169_BLOCKED_SCHEMA_VERSION",
    "TASK169_DESIGN_CONTRACT_PATH",
    "TASK169_IMPLEMENTATION_SOFTWARE_VERSION",
    "TASK169_RESULT_SCHEMA_VERSION",
    "TASK169_SCHEMA_VERSION",
    "TASK169_SOURCE_DEFINITION_ID",
    "TASK169_VERSION",
    "Task169RankingPolicy",
    "Task169Request",
    "Task169Result",
    "Task169TypedBlockedResult",
    "Task169ValidationResult",
    "ValidationStatus",
]
