"""Experimental Candidate Rating result schema (not production VALIDATED)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

EXPERIMENTAL_RATING_RESULT_SCHEMA = "task173.experimental-candidate-rating-result.v1"
EXPERIMENTAL_RATING_AUTHORITY_ID = "V07-FAST-SOLVER-RATING-AUTHORITY-ADMISSION-R11"
ExecutionMode = Literal["FROZEN_EVIDENCE_REPLAY", "LIVE_NUMERICAL_SOLVE"]


class StrictModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class ExperimentalCandidateRatingResult(StrictModel):
    schema_version: Literal["task173.experimental-candidate-rating-result.v1"] = (
        EXPERIMENTAL_RATING_RESULT_SCHEMA
    )
    status: Literal["CANDIDATE_UNAPPROVED"]
    numerical_authority_status: Literal["CANDIDATE"]
    production_integration: Literal[False] = False
    execution_mode: ExecutionMode
    experimental_rating_authority_id: str
    candidate_id: str
    candidate_hash: str
    rating_request_hash: str
    accepted_mesh_n: int
    headroom_mesh_n: int
    accepted_mesh_result_hash: str
    headroom_mesh_result_hash: str
    total_duty_w: Decimal
    tube_outlet_temperature_k: Decimal
    shell_outlet_temperature_k: Decimal
    tube_inlet_temperature_k: Decimal
    shell_inlet_temperature_k: Decimal
    tube_outlet_pressure_pa: Decimal
    shell_outlet_pressure_pa: Decimal
    wall_inner_min_k: Decimal
    wall_inner_max_k: Decimal
    wall_outer_min_k: Decimal
    wall_outer_max_k: Decimal
    minimum_approach_temperature_k: Decimal
    energy_balance_residual_w: Decimal
    terminal_boundary_residual_k: Decimal
    terminal_boundary_residual_j_kg: Decimal
    mesh_sequence_gate: Literal["PASS", "FAIL", "NOT_COMPUTED"]
    strict_replay_pass: bool
    task172_cell_closure_verified: bool
    wall_temperature_extrema_verified: bool
    energy_balance_pass: bool
    mesh_convergence_comparisons: tuple[dict[str, Any], ...]
    evidence_chain_hashes: tuple[tuple[str, str], ...]
    accepted_trajectory_projection: dict[str, Any]
    task174_result_hash: str
    authority_differences: tuple[dict[str, str], ...]
    provenance: tuple[tuple[str, str], ...]
    result_hash: str = Field(min_length=64, max_length=64)
    result_id: str = Field(min_length=1)


class ExperimentalRatingBlocked(StrictModel):
    schema_version: Literal["task173.experimental-candidate-rating-blocked.v1"] = (
        "task173.experimental-candidate-rating-blocked.v1"
    )
    status: Literal["BLOCKED"]
    blocked_code: str
    blocked_diagnostics: tuple[str, ...] = ()
    execution_mode: ExecutionMode | None = None
    experimental_rating_authority_id: str = EXPERIMENTAL_RATING_AUTHORITY_ID
