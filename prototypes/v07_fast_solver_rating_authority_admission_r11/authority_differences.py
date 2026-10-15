"""Field-level authority gap list vs production validate_candidate_rating()."""

from __future__ import annotations

PRODUCTION_CLAIMS_NOT_TRANSFERRED: tuple[dict[str, str], ...] = (
    {
        "field": "status",
        "production": "VALIDATED",
        "experimental": "CANDIDATE_UNAPPROVED",
        "reason": "Fast Solver mesh path is experimental; not production Task173 rating authority",
    },
    {
        "field": "result_schema",
        "production": "task173.candidate-rating-result.v1",
        "experimental": "task173.experimental-candidate-rating-result.v1",
        "reason": "Independent experimental result hash domain",
    },
    {
        "field": "outer_boundary_solver",
        "production": "_candidate_transient_outer_boundary + R2A certificates",
        "experimental": "V07 Fast Solver narrow-bracket / continuation (CANDIDATE)",
        "reason": "No production outer R2A provider enclosure replay on experimental path",
    },
    {
        "field": "mesh_sequence_execution",
        "production": "_run_mesh_sequence live n=1..headroom",
        "experimental": "FROZEN_EVIDENCE_REPLAY at accepted n=32 and headroom n=64 only",
        "reason": "R11 does not re-run full outer boundary ladder",
    },
    {
        "field": "determinism_replay",
        "production": "BLOCKED_TASK173_DETERMINISM_REPLAY_MISMATCH gate on transient replay",
        "experimental": "Strict mesh hash replay at frozen shooting enthalpy; no R2A hash parity",
        "reason": "Experimental trajectory lacks production transient certificate bundle",
    },
    {
        "field": "cell_root_authority",
        "production": "CELL_ROOT_SOLVER_AUTHORITY_ID production cell root + R2A",
        "experimental": "Fast coupled cell R2 (experimental authority)",
        "reason": "Cell closure audited with production F(q) tolerance but different solver path",
    },
    {
        "field": "candidate_rating_result_hash",
        "production": "candidate_rating_result_hash(CandidateRatingSuccessResult)",
        "experimental": "experimental_rating_result_hash(ExperimentalCandidateRatingResult)",
        "reason": "Must not alias production result hash",
    },
)


def authority_differences_payload() -> list[dict[str, str]]:
    return [dict(item) for item in PRODUCTION_CLAIMS_NOT_TRANSFERRED]
