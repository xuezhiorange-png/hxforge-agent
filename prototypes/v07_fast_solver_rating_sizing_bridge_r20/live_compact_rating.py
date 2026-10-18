"""Live compact rating (authority-aligned with LIVE_NUMERICAL_SOLVE full results)."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from hexagent.canonical_json import canonical_sha256
from prototypes.v07_fast_solver_live_rating_result_r19.live_result_hash import (
    LIVE_RATING_RESULT_R19_AUTHORITY_ID,
)
from prototypes.v07_fast_solver_rating_authority_admission_r11.experimental_models import (
    ExecutionMode,
    ExperimentalCandidateRatingResult,
)
from prototypes.v07_fast_solver_rating_authority_admission_r11.geometry_summary import (
    GeometrySummary,
)

LIVE_COMPACT_RATING_SCHEMA = "task173.live-numerical-solve-candidate-rating-compact.v1"
LIVE_COMPACT_HASH_DOMAIN = "task173.live-numerical-solve-candidate-rating-compact-hash.v1"


class StrictModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class FullTrajectoryArtifactRef(StrictModel):
    path: str
    file_sha256: str = Field(min_length=64, max_length=64)
    full_result_hash: str = Field(min_length=64, max_length=64)


class LiveCompactCandidateRating(StrictModel):
    schema_version: Literal["task173.live-numerical-solve-candidate-rating-compact.v1"] = (
        LIVE_COMPACT_RATING_SCHEMA
    )
    status: Literal["CANDIDATE_UNAPPROVED"]
    numerical_authority_status: Literal["CANDIDATE"]
    production_integration: Literal[False] = False
    execution_mode: ExecutionMode
    experimental_rating_authority_id: str
    candidate_id: str
    candidate_hash: str
    rating_request_hash: str
    geometry_summary: GeometrySummary
    accepted_mesh_n: int
    headroom_mesh_n: int
    accepted_mesh_result_hash: str
    headroom_mesh_result_hash: str
    task174_result_hash: str
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


class LiveCompactAuthorityError(RuntimeError):
    def __init__(self, code: str, *diagnostics: str) -> None:
        self.code = code
        self.diagnostics = diagnostics
        super().__init__(code)


def live_compact_rating_hash(compact: LiveCompactCandidateRating) -> str:
    body = compact.model_dump(mode="json", exclude={"compact_result_hash"})
    body["_live_compact_hash_domain"] = LIVE_COMPACT_HASH_DOMAIN
    return canonical_sha256(body)


def build_live_compact_from_full(
    full: ExperimentalCandidateRatingResult,
    *,
    trajectory_artifact_path: str,
    trajectory_file_sha256: str,
    geometry_summary: GeometrySummary,
) -> LiveCompactCandidateRating:
    if full.execution_mode != "LIVE_NUMERICAL_SOLVE":
        raise LiveCompactAuthorityError("EXECUTION_MODE_NOT_LIVE")
    if full.experimental_rating_authority_id != LIVE_RATING_RESULT_R19_AUTHORITY_ID:
        raise LiveCompactAuthorityError(
            "FULL_AUTHORITY_ID_MISMATCH",
            full.experimental_rating_authority_id,
        )
    artifact = FullTrajectoryArtifactRef(
        path=trajectory_artifact_path,
        file_sha256=trajectory_file_sha256,
        full_result_hash=full.result_hash,
    )
    base = LiveCompactCandidateRating(
        status=full.status,
        numerical_authority_status=full.numerical_authority_status,
        production_integration=False,
        execution_mode=full.execution_mode,
        experimental_rating_authority_id=full.experimental_rating_authority_id,
        candidate_id=full.candidate_id,
        candidate_hash=full.candidate_hash,
        rating_request_hash=full.rating_request_hash,
        geometry_summary=geometry_summary,
        accepted_mesh_n=full.accepted_mesh_n,
        headroom_mesh_n=full.headroom_mesh_n,
        accepted_mesh_result_hash=full.accepted_mesh_result_hash,
        headroom_mesh_result_hash=full.headroom_mesh_result_hash,
        task174_result_hash=full.task174_result_hash,
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
    digest = live_compact_rating_hash(base)
    return base.model_copy(update={"compact_result_hash": digest})


def verify_live_compact_against_full(
    compact: LiveCompactCandidateRating,
    full: ExperimentalCandidateRatingResult,
    *,
    full_file_sha256: str,
) -> None:
    if compact.compact_result_hash != live_compact_rating_hash(compact):
        raise LiveCompactAuthorityError("COMPACT_HASH_REPLAY_MISMATCH")
    if compact.full_result_hash != full.result_hash:
        raise LiveCompactAuthorityError("COMPACT_FULL_RESULT_HASH_MISMATCH")
    if compact.experimental_rating_authority_id != full.experimental_rating_authority_id:
        raise LiveCompactAuthorityError("COMPACT_FULL_AUTHORITY_MISMATCH")
    if compact.experimental_rating_authority_id != LIVE_RATING_RESULT_R19_AUTHORITY_ID:
        raise LiveCompactAuthorityError("COMPACT_NOT_LIVE_R19_AUTHORITY")
    if compact.full_trajectory_artifact.file_sha256 != full_file_sha256:
        raise LiveCompactAuthorityError("COMPACT_TRAJECTORY_FILE_SHA_MISMATCH")
    if compact.full_trajectory_artifact.full_result_hash != full.result_hash:
        raise LiveCompactAuthorityError("COMPACT_ARTIFACT_FULL_HASH_MISMATCH")
    if compact.task174_result_hash != full.task174_result_hash:
        raise LiveCompactAuthorityError("COMPACT_TASK174_HASH_MISMATCH")
    if compact.candidate_id != full.candidate_id or compact.candidate_hash != full.candidate_hash:
        raise LiveCompactAuthorityError("COMPACT_CANDIDATE_IDENTITY_MISMATCH")
    if compact.rating_request_hash != full.rating_request_hash:
        raise LiveCompactAuthorityError("COMPACT_REQUEST_HASH_MISMATCH")
