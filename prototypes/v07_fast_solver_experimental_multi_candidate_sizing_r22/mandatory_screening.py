"""Task173 mandatory screening gap closure for experimental multi-candidate sizing."""

# ruff: noqa: E501

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from hexagent.exchangers.shell_tube.task173_integrated_sizing.models import (
    SizingRequirementAuthority,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.r22_pinned_identity import (
    REQUIRED_SCREENING_POLICY_ID,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.rating_pair_admission import (
    AdmittedLiveRating,
)

_SCREENING_DEFERRED_WARN = "MANDATORY_SCREENING_POLICY_NOT_REEXECUTED_LIVE_EXPERIMENTAL_PATH"
_FIV_WARN = "FIV_NUMERIC_LIMIT_AUTHORITY_MISSING"
_TASK167_GAP = "TASK167_APPROVED_RULE_PACK_AUTHORITY_NOT_ON_RATING_REQUEST"
_PRODUCTION_SCREENING_AUTHORITY_GAP = "PRODUCTION_MANDATORY_SCREENING_AUTHORITY_NOT_AVAILABLE"


class _ScreeningModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class ScreeningRuleRecord(_ScreeningModel):
    rule_id: str
    outcome: Literal["EXECUTED", "DEFERRED", "WARN"]
    detail: str
    provenance: tuple[tuple[str, str], ...] = Field(min_length=1)


class MandatoryScreeningOutcome(_ScreeningModel):
    mandatory_screening_gate: str
    mandatory_screening_complete: bool
    production_recommendation_authorized: bool
    fiv_authority_status: Literal["MISSING", "PRESENT"]
    rule_records: tuple[ScreeningRuleRecord, ...]
    screening_gap_codes: tuple[str, ...] = ()


def execute_experimental_mandatory_screening(
    admitted: tuple[AdmittedLiveRating, ...],
    requirement: SizingRequirementAuthority,
) -> MandatoryScreeningOutcome:
    records: list[ScreeningRuleRecord] = []
    gap_codes: list[str] = []

    policy_ok = requirement.required_screening_policy_id == REQUIRED_SCREENING_POLICY_ID
    records.append(
        ScreeningRuleRecord(
            rule_id="V07-T173-SIZING-MANDATORY-SCREENING-POLICY-ID-BINDING",
            outcome="EXECUTED" if policy_ok else "WARN",
            detail=requirement.required_screening_policy_id,
            provenance=(("requirement_hash", requirement.canonical_hash),),
        )
    )
    if not policy_ok:
        gap_codes.append("MANDATORY_SCREENING_POLICY_ID_MISMATCH")

    fiv_missing_any = False
    for item in admitted:
        task174 = item.request.task174_result
        if task174.fiv_numeric_limit_authority_missing:
            fiv_missing_any = True
        records.append(
            ScreeningRuleRecord(
                rule_id="V07-TASK174-FIV-NUMERIC-LIMIT-AUTHORITY-FLAG",
                outcome="WARN" if task174.fiv_numeric_limit_authority_missing else "EXECUTED",
                detail=(
                    "fiv_numeric_limit_authority_missing="
                    f"{task174.fiv_numeric_limit_authority_missing}"
                ),
                provenance=(
                    ("candidate_id", item.request.candidate_id),
                    ("rating_request_hash", item.full.rating_request_hash),
                ),
            )
        )
        records.append(
            ScreeningRuleRecord(
                rule_id="V07-TASK167-SCREENING-BUNDLE-PRESENCE",
                outcome="DEFERRED",
                detail=_TASK167_GAP,
                provenance=(("candidate_id", item.request.candidate_id),),
            )
        )

    records.append(
        ScreeningRuleRecord(
            rule_id="V07-T173-MANDATORY-SCREENING-LIVE-REEXECUTION",
            outcome="DEFERRED",
            detail=_SCREENING_DEFERRED_WARN,
            provenance=(("path", "experimental_multi_candidate_sizing_r22"),),
        )
    )
    gap_codes.extend(
        (
            _PRODUCTION_SCREENING_AUTHORITY_GAP,
            _SCREENING_DEFERRED_WARN,
            _TASK167_GAP,
        )
    )
    if fiv_missing_any:
        gap_codes.append(_FIV_WARN)

    fiv_status: Literal["MISSING", "PRESENT"] = "MISSING" if fiv_missing_any else "PRESENT"
    return MandatoryScreeningOutcome(
        mandatory_screening_gate="EXPERIMENTAL_DEFERRED_WARN_RECORDED",
        mandatory_screening_complete=False,
        production_recommendation_authorized=False,
        fiv_authority_status=fiv_status,
        rule_records=tuple(records),
        screening_gap_codes=tuple(sorted(set(gap_codes), key=lambda s: s.encode("utf-8"))),
    )
