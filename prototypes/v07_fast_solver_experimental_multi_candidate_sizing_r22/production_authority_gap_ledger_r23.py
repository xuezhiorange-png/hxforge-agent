"""R23 production authority gap ledger (formal REQUIREMENT / SOURCE_CODE / ...)."""

# ruff: noqa: E501

from __future__ import annotations

from typing import Any, Literal

GapStatus = Literal["VERIFIED", "EXPERIMENTAL_ONLY", "MISSING_AUTHORITY", "BLOCKED"]


def production_authority_gap_ledger_r23() -> tuple[dict[str, Any], ...]:
    return (
        {
            "item": "R2A_OUTER_BOUNDARY_CERTIFICATE",
            "requirement": "Production rating/sizing binds R2A outer-boundary enclosure certificates.",
            "source_code": "prototypes/v07_fast_solver_rating_contract_live_bridge_r12/AUTHORITY_ADMISSION_R12.md",
            "existing_evidence": "R22 admits frozen R19/R21E full JSON only; no R2A certificate bundle on path.",
            "gap": "Fast R3 outer boundary used for live solves; R2A replay bundle absent.",
            "status": "MISSING_AUTHORITY",
            "next_action": "Attach R2A provider enclosure certificates before VALIDATED promotion.",
        },
        {
            "item": "CELL_ROOT_SOLVER_AUTHORITY",
            "requirement": "Validated cell-root solver authority with enclosure replay.",
            "source_code": "src/hexagent/exchangers/shell_tube/task173_integrated_rating/service.py",
            "existing_evidence": "R19/R21E full artifacts: numerical_authority_status=CANDIDATE.",
            "gap": "No production cell-root VALIDATED authority on admitted ratings.",
            "status": "EXPERIMENTAL_ONLY",
            "next_action": "Complete R2A cell closure qualification.",
        },
        {
            "item": "TASK172_PROPERTY_ENVELOPE",
            "requirement": "Task172 water property profile within declared operating envelope.",
            "source_code": "src/hexagent/exchangers/shell_tube/task173_integrated_sizing/models.py SizingServiceAuthority",
            "existing_evidence": "Pinned snapshots bind property_profile_id on live requests.",
            "gap": "R23 consumer does not re-run property envelope audit beyond request hash binding.",
            "status": "EXPERIMENTAL_ONLY",
            "next_action": "Add property envelope replay gate to production sizing admission.",
        },
        {
            "item": "TASK174_HYDRAULIC_AUTHORITY",
            "requirement": "Task174 result hash replay and DP binding on request and full.",
            "source_code": "hexagent.exchangers.shell_tube.task174_hydraulic_orchestration.recompute_task174_result_hash",
            "existing_evidence": "R23 independent consumer replays Task174 hash on admitted bundles.",
            "gap": "Production Task173 sizing service authority package not invoked.",
            "status": "VERIFIED",
            "next_action": "Wire same binding into production task173.sizing-result.v1 path.",
        },
        {
            "item": "TASK167_FIV_NUMERIC_LIMIT_AUTHORITY",
            "requirement": "Approved FIV rule pack and numeric limits for mandatory screening.",
            "source_code": "src/hexagent/exchangers/shell_tube/engineering_screening/",
            "existing_evidence": "Task174 flags fiv_numeric_limit_authority_missing on frozen requests.",
            "gap": "No Task167 approved_rule_pack_authority on live rating requests.",
            "status": "MISSING_AUTHORITY",
            "next_action": "Bind Task167 screening authority to rating requests before production recommend.",
        },
        {
            "item": "MANDATORY_SCREENING_POLICY",
            "requirement": "V07-T173-SIZING-MANDATORY-SCREENING-R1 live re-execution.",
            "source_code": "prototypes/.../mandatory_screening.py",
            "existing_evidence": "EXPERIMENTAL_DEFERRED_WARN_RECORDED on R22/R22A results.",
            "gap": "Screening not re-executed with production Task167 bundle.",
            "status": "BLOCKED",
            "next_action": "Execute mandatory screening with licensed rule pack; do not downgrade WARN.",
        },
        {
            "item": "TASK168_CANDIDATE_SPACE_AUTHORITY",
            "requirement": "Q13 candidate space authority ID and hash on requirement and requests.",
            "source_code": "prototypes/.../independent_consumer_admission.py",
            "existing_evidence": "Frozen Q13 hash aeb350ec… verified on both candidates.",
            "gap": "Experimental requirement source, not production Task173 service requirement.",
            "status": "VERIFIED",
            "next_action": "Replace with production sizing requirement authority record.",
        },
        {
            "item": "PRODUCTION_SIZING_REQUIREMENT",
            "requirement": "Licensed production SizingRequirementAuthority with engineering approval.",
            "source_code": "src/hexagent/exchangers/shell_tube/task173_integrated_sizing/models.py",
            "existing_evidence": "R22 experimental requirement pin 03bc0fa7… with APPROVED experimental source.",
            "gap": "Not production Task173 authority package integration.",
            "status": "EXPERIMENTAL_ONLY",
            "next_action": "Obtain engineering owner approval for production requirement binding.",
        },
        {
            "item": "CANDIDATE_RATING_SUCCESS_RESULT",
            "requirement": "Production CandidateRatingSuccessResult with VALIDATED numerical authority.",
            "source_code": "task173_integrated_rating result models",
            "existing_evidence": "Experimental R19/R21 live rating authority IDs on full JSON.",
            "gap": "Cannot claim production rating success admission.",
            "status": "BLOCKED",
            "next_action": "Keep CANDIDATE; independent review before VALIDATED.",
        },
        {
            "item": "PRODUCTION_SIZING_RESULT",
            "requirement": "task173.sizing-result.v1 with production_integration=true and screening complete.",
            "source_code": "task173_integrated_sizing/service.py",
            "existing_evidence": "experimental-multi-candidate-sizing-result.v1/v2 only.",
            "gap": "PRODUCTION_MULTI_CANDIDATE_SIZING_VERIFIED remains false.",
            "status": "BLOCKED",
            "next_action": "Close authority gaps before production sizing result emission.",
        },
    )
