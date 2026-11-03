"""Build versioned PRODUCTION_AUTHORITY_ADMISSION_REPORT for R23."""

# ruff: noqa: E501

from __future__ import annotations

from typing import Any

from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.fiv_authority_verification import (
    verify_fiv_and_mandatory_screening_authority,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.production_authority_gap_ledger_r23 import (
    production_authority_gap_ledger_r23,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.rating_pair_admission import (
    AdmittedLiveRating,
)

REPORT_SCHEMA = "task173.production-authority-admission-report.v1"


def build_production_authority_admission_report(
    admitted: tuple[AdmittedLiveRating, ...],
    *,
    sizing_result_hash: str,
    independent_consumer_verified: bool,
) -> dict[str, Any]:
    fiv = verify_fiv_and_mandatory_screening_authority(admitted)
    ledger = list(production_authority_gap_ledger_r23())
    blocking = [row for row in ledger if row["status"] in ("MISSING_AUTHORITY", "BLOCKED")]
    return {
        "schema_version": REPORT_SCHEMA,
        "numerical_authority_status": "CANDIDATE",
        "production_integration": False,
        "production_recommendation_authorized": False,
        "production_multi_candidate_sizing_verified": False,
        "experimental_multi_candidate_sizing_verified": independent_consumer_verified,
        "independent_consumer_fail_closed": independent_consumer_verified,
        "fiv_authority_status": fiv["fiv_authority_status"],
        "mandatory_screening_complete": fiv["mandatory_screening_complete"],
        "experimental_ratings_proven_capabilities": [
            "Frozen R19 Candidate B and R21E second-candidate live full ratings admit to sizing consumer.",
            "Task174 hydraulic DP constraints evaluated from pinned request binding.",
            "Experimental ranking minimizes shell_dp with WARN penalty policy.",
        ],
        "verified_with_frozen_evidence": [
            row["item"] for row in ledger if row["status"] == "VERIFIED"
        ],
        "experimental_only_items": [
            row["item"] for row in ledger if row["status"] == "EXPERIMENTAL_ONLY"
        ],
        "blocking_authority_items": [row["item"] for row in blocking],
        "engineering_owner_approval_required": [
            "Production SizingRequirementAuthority licensing",
            "Task167 FIV approved rule pack binding on live rating requests",
            "VALIDATED numerical authority promotion (not CANDIDATE)",
            "Mandatory screening live re-execution sign-off",
        ],
        "pre_task173_production_work": [
            "Close R2A outer boundary certificate gap",
            "Attach Task167 screening bundle to rating admission chain",
            "Promote numerical authority only after independent engineering review",
        ],
        "recommended_next_engineering_task": (
            "Bind Task167 approved_rule_pack_authority to live rating requests and re-run "
            "mandatory screening without new outer-boundary solves."
        ),
        "fiv_verification": fiv,
        "authority_gap_ledger": ledger,
        "sizing_result_hash_reference": sizing_result_hash,
    }
