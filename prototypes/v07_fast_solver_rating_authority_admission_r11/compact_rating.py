"""Compact experimental rating surface (no embedded full trajectory)."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from hexagent.canonical_json import canonical_sha256
from prototypes.v07_fast_solver_rating_authority_admission_r11.experimental_models import (
    EXPERIMENTAL_RATING_AUTHORITY_ID,
    ExecutionMode,
    ExperimentalCandidateRatingResult,
)

COMPACT_RATING_SCHEMA = "task173.experimental-candidate-rating-compact.v1"


class StrictModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class FullTrajectoryArtifactRef(StrictModel):
    path: str
    file_sha256: str = Field(min_length=64, max_length=64)
    full_result_hash: str = Field(min_length=64, max_length=64)


class ExperimentalCompactCandidateRating(StrictModel):
    schema_version: Literal["task173.experimental-candidate-rating-compact.v1"] = (
        COMPACT_RATING_SCHEMA
    )
    status: Literal["CANDIDATE_UNAPPROVED"]
    numerical_authority_status: Literal["CANDIDATE"]
    production_integration: Literal[False] = False
    execution_mode: ExecutionMode
    experimental_rating_authority_id: str
    candidate_id: str
    candidate_hash: str
    rating_request_hash: str
    geometry_summary: str
    accepted_mesh_n: int
    headroom_mesh_n: int
    accepted_mesh_result_hash: str
    headroom_mesh_result_hash: str
    total_duty_w: Decimal
    tube_inlet_temperature_k: Decimal
    tube_outlet_temperature_k: Decimal
    shell_inlet_temperature_k: Decimal
    shell_outlet_temperature_k: Decimal
    tube_outlet_pressure_pa: Decimal
    shell_outlet_pressure_pa: Decimal
    wall_inner_min_k: Decimal
    wall_inner_max_k: Decimal
    wall_outer_min_k: Decimal
    wall_outer_max_k: Decimal
    minimum_approach_temperature_k: Decimal
    terminal_boundary_residual_k: Decimal
    terminal_boundary_residual_j_kg: Decimal
    energy_balance_residual_w: Decimal
    mesh_sequence_gate: Literal["PASS", "FAIL", "NOT_COMPUTED"]
    strict_replay_pass: bool
    task172_cell_closure_verified: bool
    wall_temperature_extrema_verified: bool
    energy_balance_pass: bool
    full_trajectory_artifact: FullTrajectoryArtifactRef
    compact_result_hash: str = Field(min_length=64, max_length=64)
    full_result_hash: str = Field(min_length=64, max_length=64)


def compact_rating_hash(compact: ExperimentalCompactCandidateRating) -> str:
    return canonical_sha256(compact.model_dump(mode="json", exclude={"compact_result_hash"}))


def build_compact_from_full(
    full: ExperimentalCandidateRatingResult,
    *,
    trajectory_artifact_path: str,
    trajectory_file_sha256: str,
    geometry_summary: str = "Task171 topology + CandidateRatingRequest binding",
) -> ExperimentalCompactCandidateRating:
    artifact = FullTrajectoryArtifactRef(
        path=trajectory_artifact_path,
        file_sha256=trajectory_file_sha256,
        full_result_hash=full.result_hash,
    )
    base = ExperimentalCompactCandidateRating(
        status=full.status,
        numerical_authority_status=full.numerical_authority_status,
        production_integration=False,
        execution_mode=full.execution_mode,
        experimental_rating_authority_id=EXPERIMENTAL_RATING_AUTHORITY_ID,
        candidate_id=full.candidate_id,
        candidate_hash=full.candidate_hash,
        rating_request_hash=full.rating_request_hash,
        geometry_summary=geometry_summary,
        accepted_mesh_n=full.accepted_mesh_n,
        headroom_mesh_n=full.headroom_mesh_n,
        accepted_mesh_result_hash=full.accepted_mesh_result_hash,
        headroom_mesh_result_hash=full.headroom_mesh_result_hash,
        total_duty_w=full.total_duty_w,
        tube_inlet_temperature_k=full.tube_inlet_temperature_k,
        tube_outlet_temperature_k=full.tube_outlet_temperature_k,
        shell_inlet_temperature_k=full.shell_inlet_temperature_k,
        shell_outlet_temperature_k=full.shell_outlet_temperature_k,
        tube_outlet_pressure_pa=full.tube_outlet_pressure_pa,
        shell_outlet_pressure_pa=full.shell_outlet_pressure_pa,
        wall_inner_min_k=full.wall_inner_min_k,
        wall_inner_max_k=full.wall_inner_max_k,
        wall_outer_min_k=full.wall_outer_min_k,
        wall_outer_max_k=full.wall_outer_max_k,
        minimum_approach_temperature_k=full.minimum_approach_temperature_k,
        terminal_boundary_residual_k=full.terminal_boundary_residual_k,
        terminal_boundary_residual_j_kg=full.terminal_boundary_residual_j_kg,
        energy_balance_residual_w=full.energy_balance_residual_w,
        mesh_sequence_gate=full.mesh_sequence_gate,
        strict_replay_pass=full.strict_replay_pass,
        task172_cell_closure_verified=full.task172_cell_closure_verified,
        wall_temperature_extrema_verified=full.wall_temperature_extrema_verified,
        energy_balance_pass=full.energy_balance_pass,
        full_trajectory_artifact=artifact,
        compact_result_hash="0" * 64,
        full_result_hash=full.result_hash,
    )
    ch = compact_rating_hash(base)
    return base.model_copy(update={"compact_result_hash": ch})
