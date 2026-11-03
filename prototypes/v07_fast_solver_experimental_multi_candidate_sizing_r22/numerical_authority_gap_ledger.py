"""Numerical Authority gap ledger for R22A engineering admission."""

# ruff: noqa: E501

from __future__ import annotations

from typing import Any, Literal

GapDisposition = Literal["OPEN", "DEFERRED", "EXPERIMENTAL_ONLY"]


def numerical_authority_gap_ledger() -> tuple[dict[str, Any], ...]:
    return (
        {
            "item": "FAST_SOLVER_VS_R2A_OUTER_BOUNDARY_CERTIFICATE",
            "requirement": "Production sizing/rating must bind R2A outer-boundary enclosure certificates.",
            "current_evidence": "R22 uses frozen R19/R21E live ratings; no new outer boundary solve.",
            "gap": "Experimental fast outer boundary (R3) lacks R2A provider enclosure replay bundle.",
            "disposition": "OPEN",
            "next_action": "Admit only ratings with R2A certificate chain before production sizing.",
        },
        {
            "item": "CELL_ROOT_SOLVER_AUTHORITY",
            "requirement": "Production path requires CELL_ROOT_SOLVER_AUTHORITY_ID with validated enclosure.",
            "current_evidence": "R19/R21E numerical_authority_status=CANDIDATE on R2 fast cell path.",
            "gap": "No production cell-root solver authority on admitted artifacts.",
            "disposition": "OPEN",
            "next_action": "Complete R2A cell closure qualification before VALIDATED promotion.",
        },
        {
            "item": "MESH_REPLAY_AND_DETERMINISM",
            "requirement": "Strict mesh replay and ladder comparisons pinned on full rating artifacts.",
            "current_evidence": "R19/R21E full files pass independent SHA256, blob, and result hash replay.",
            "gap": "R22 does not re-run mesh shooting; relies on pinned full JSON only.",
            "disposition": "EXPERIMENTAL_ONLY",
            "next_action": "Keep fail-closed admission gates; no mesh re-solve in R22A.",
        },
        {
            "item": "PROPERTY_PROVIDER_AND_OPERATING_ENVELOPE",
            "requirement": "Task172 water property profile within declared temperature/pressure envelope.",
            "current_evidence": "Pinned snapshots carry Task172 profile binding on live requests.",
            "gap": "R22 sizing does not re-validate property provider envelope beyond request hash.",
            "disposition": "DEFERRED",
            "next_action": "Bind property envelope audit into production sizing admission.",
        },
        {
            "item": "TASK174_HYDRAULIC_AUTHORITY",
            "requirement": "Task174 result identity must match request binding for DP constraints.",
            "current_evidence": "R19/R21E full artifacts embed task174_result_hash parity.",
            "gap": "R22A adds fail-closed injection for Task174 tamper at admission boundary.",
            "disposition": "EXPERIMENTAL_ONLY",
            "next_action": "Extend injection coverage to production Task173 sizing adapter.",
        },
        {
            "item": "TASK167_FIV_MANDATORY_SCREENING",
            "requirement": "Task173 mandatory screening with Task167 approved rule pack on each candidate.",
            "current_evidence": "R22 records DEFERRED screening; FIV numeric limit authority missing on Task174.",
            "gap": "No Task167 bundle on live rating requests; screening not re-executed live.",
            "disposition": "OPEN",
            "next_action": "Attach Task167 screening authority to rating requests before production recommend.",
        },
        {
            "item": "CANDIDATE_SPACE_SIZING_REQUIREMENT_AUTHORITY",
            "requirement": "Trusted sizing requirement with Q13 candidate space authority/hash binding.",
            "current_evidence": "R22A trusted requirement canonical hash and space pins verified independently.",
            "gap": "Experimental requirement approval is not production Task173 service authority.",
            "disposition": "EXPERIMENTAL_ONLY",
            "next_action": "Replace experimental requirement source with licensed production requirement record.",
        },
        {
            "item": "PRODUCTION_CANDIDATE_RATING_SUCCESS_RESULT",
            "requirement": "VALIDATED numerical authority and production rating authority IDs.",
            "current_evidence": "Admitted ratings use R19/R21 experimental live rating authority IDs.",
            "gap": "Cannot claim production CandidateRatingSuccessResult admission.",
            "disposition": "OPEN",
            "next_action": "Stop at CANDIDATE; do not promote to VALIDATED without review.",
        },
        {
            "item": "PRODUCTION_SIZING_RESULT",
            "requirement": "task173.sizing-result.v1 with mandatory screening complete and production integration.",
            "current_evidence": "R22 emits experimental-multi-candidate-sizing-result.v1/v2 with screening incomplete.",
            "gap": "PRODUCTION_MULTI_CANDIDATE_SIZING_VERIFIED remains false.",
            "disposition": "OPEN",
            "next_action": "Close screening and numerical authority gaps before production sizing result.",
        },
    )
