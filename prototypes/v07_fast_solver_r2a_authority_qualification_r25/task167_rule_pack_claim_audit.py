"""R25 correction audit for Task167 configuration rule pack approval claims."""

# ruff: noqa: E501

from __future__ import annotations

from typing import Any

from hexagent.exchangers.shell_tube.engineering_screening.authority import (
    FIV_NUMERIC_LIMIT_AUTHORITY_AVAILABLE,
    SOURCE_TASK020_RULE_PACK,
)
from hexagent.exchangers.shell_tube.models import EvaluatedRulePackAuthority
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.rating_pair_admission import (
    AdmittedLiveRating,
)


def _request_has_evaluated_rule_pack(
    admitted: AdmittedLiveRating,
) -> EvaluatedRulePackAuthority | None:
    request = admitted.request
    for attr in ("approved_rule_pack_authority", "task167_request"):
        value = getattr(request, attr, None)
        if isinstance(value, EvaluatedRulePackAuthority):
            return value
        if value is not None and hasattr(value, "approved_rule_pack_authority"):
            inner = getattr(value, "approved_rule_pack_authority", None)
            if isinstance(inner, EvaluatedRulePackAuthority):
                return inner
    return None


def _verify_evaluated_rule_pack(pack: EvaluatedRulePackAuthority) -> tuple[bool, list[str]]:
    failures: list[str] = []
    if pack.validation_status != "ok":
        failures.append("validation_status_not_ok")
    if not pack.selected_rule_authorities:
        failures.append("selected_rule_authorities_empty")
    for index, rule in enumerate(pack.selected_rule_authorities):
        if rule.approval_status != "approved":
            failures.append(f"rule_not_approved:{index}")
        if rule.license_evidence is None:
            failures.append(f"license_evidence_missing:{index}")
        if not rule.rule_artifact_canonical_hash:
            failures.append(f"rule_artifact_hash_missing:{index}")
    return not failures, failures


def audit_task167_rule_pack_claim(admitted: AdmittedLiveRating) -> dict[str, Any]:
    pack = _request_has_evaluated_rule_pack(admitted)
    if pack is None:
        return {
            "candidate_id": admitted.request.candidate_id,
            "label": admitted.label,
            "configuration_rule_pack_approval": "CONFIGURATION_RULE_PACK_APPROVAL_NOT_VERIFIED",
            "evaluated_rule_pack_present": False,
            "source_task020_rule_pack_id": SOURCE_TASK020_RULE_PACK,
            "fiv_numeric_limit_authority": "MISSING",
            "fiv_numeric_limit_authority_available": FIV_NUMERIC_LIMIT_AUTHORITY_AVAILABLE,
            "r24_claim_correction": (
                "R24 task167_rule_pack_approved_for_configuration_rules=true was based on "
                "static SOURCE_TASK020_RULE_PACK identity only; no EvaluatedRulePackAuthority "
                "is bound on this CandidateRatingRequest."
            ),
        }

    approved, failures = _verify_evaluated_rule_pack(pack)
    return {
        "candidate_id": admitted.request.candidate_id,
        "label": admitted.label,
        "configuration_rule_pack_approval": (
            "APPROVED_VERIFIED" if approved else "CONFIGURATION_RULE_PACK_APPROVAL_NOT_VERIFIED"
        ),
        "evaluated_rule_pack_present": True,
        "validation_status": pack.validation_status,
        "canonical_hash": getattr(pack, "canonical_hash", None),
        "selected_rule_count": len(pack.selected_rule_authorities),
        "verification_failures": failures,
        "fiv_numeric_limit_authority": "MISSING",
        "fiv_numeric_limit_authority_available": FIV_NUMERIC_LIMIT_AUTHORITY_AVAILABLE,
        "distinction": "Configuration rule pack approval does not imply FIV numeric limit approval.",
    }


def audit_both_candidates(
    candidate_b: AdmittedLiveRating,
    second: AdmittedLiveRating,
) -> dict[str, Any]:
    rows = [
        audit_task167_rule_pack_claim(candidate_b),
        audit_task167_rule_pack_claim(second),
    ]
    any_verified = any(
        row["configuration_rule_pack_approval"] == "APPROVED_VERIFIED" for row in rows
    )
    return {
        "schema_version": "task167.rule-pack-claim-audit.v1",
        "task167_configuration_rule_pack_approval": (
            "APPROVED_VERIFIED" if any_verified else "CONFIGURATION_RULE_PACK_APPROVAL_NOT_VERIFIED"
        ),
        "candidates": rows,
        "fiv_numeric_limit_authority": "MISSING",
        "r24_static_claim_corrected": True,
    }
