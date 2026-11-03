"""Task167 / FIV authority read-only verification for R23 pre-admission."""

# ruff: noqa: E501

from __future__ import annotations

from typing import Any, Literal

from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.rating_pair_admission import (
    AdmittedLiveRating,
)

FivAuthorityStatus = Literal["MISSING", "DIAGNOSTIC_ONLY"]


def verify_fiv_and_mandatory_screening_authority(
    admitted: tuple[AdmittedLiveRating, ...],
) -> dict[str, Any]:
    """Deterministic checks against frozen request Task174 flags; no new numerical solves."""
    fiv_missing_any = False
    per_candidate: list[dict[str, Any]] = []
    for item in admitted:
        task174 = item.request.task174_result
        fiv_missing = bool(task174.fiv_numeric_limit_authority_missing)
        fiv_missing_any = fiv_missing_any or fiv_missing
        per_candidate.append(
            {
                "candidate_id": item.request.candidate_id,
                "label": item.label,
                "fiv_numeric_limit_authority_missing": fiv_missing,
                "fiv_numeric_limit_not_guessed": bool(task174.fiv_numeric_limit_not_guessed),
                "fiv_requirement_mode": getattr(task174, "fiv_requirement_mode", None),
                "task167_screening_bundle_on_request": False,
            }
        )

    approved_rule_pack_present = False
    fiv_status: FivAuthorityStatus = "MISSING" if fiv_missing_any else "DIAGNOSTIC_ONLY"
    return {
        "fiv_authority_status": fiv_status,
        "approved_fiv_rule_pack_present": approved_rule_pack_present,
        "mandatory_screening_complete": False,
        "production_recommendation_authorized": False,
        "task167_approved_rule_pack_authority": "MISSING_AUTHORITY",
        "per_candidate": per_candidate,
        "deterministic_checks_executed": True,
        "notes": (
            "Frozen live requests expose Task174 fiv_numeric_limit_authority_missing=true; "
            "no Task167 approved rule pack is bound on rating requests in R19/R21E evidence."
        ),
    }
