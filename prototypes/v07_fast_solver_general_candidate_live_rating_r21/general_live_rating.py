"""General live rating entry (any frozen Task168 candidate, not Candidate-B pins)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173
from hexagent.exchangers.shell_tube.task173_integrated_rating.candidate_models import (
    CandidateRatingRequest,
    candidate_rating_request_hash,
)
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v07_fast_solver_general_candidate_live_rating_r21.general_live_result_hash import (
    GENERAL_LIVE_RATING_R21_AUTHORITY_ID,
    general_live_rating_result_hash,
    general_live_rating_result_id,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.continuation_engine import (
    LiveContinuationOutcome,
    run_live_ladder_continuation,
)
from prototypes.v07_fast_solver_live_rating_result_r19.live_mesh_replay import (
    LiveMeshReplayError,
    replay_verified_prior_stage_mesh,
)
from prototypes.v07_fast_solver_rating_authority_admission_r11.authority_differences import (
    authority_differences_payload,
)
from prototypes.v07_fast_solver_rating_authority_admission_r11.experimental_models import (
    ExperimentalCandidateRatingResult,
    ExperimentalRatingBlocked,
)
from prototypes.v07_fast_solver_rating_authority_admission_r11.verification import (
    build_accepted_trajectory_projection,
    verify_accepted_cell_count,
    verify_cell_closure,
    verify_energy_balance,
    verify_task174_binding,
    verify_wall_extrema_from_cells,
)

ACCEPTED_MESH_N = 32
HEADROOM_MESH_N = 64
REQUIRED_CONSECUTIVE_PASSING_PAIRS = 2


def _general_blocked(code: str, *diag: str) -> ExperimentalRatingBlocked:
    return ExperimentalRatingBlocked(
        status="BLOCKED",
        blocked_code=code,
        blocked_diagnostics=diag,
        execution_mode="LIVE_NUMERICAL_SOLVE",
        experimental_rating_authority_id=GENERAL_LIVE_RATING_R21_AUTHORITY_ID,
    )


@dataclass(frozen=True)
class GeneralLiveRatingBudget:
    total_budget_s: float = 5400.0
    mesh_budgets_s: dict[int, float] | None = None


def _mesh_sequence_gate(comparisons: tuple[dict[str, Any], ...]) -> tuple[str, str | None]:
    if len(comparisons) < 6:
        return "FAIL", "INCOMPLETE_MESH_COMPARISON_CHAIN"
    statuses = [str(c.get("overall_status")) for c in comparisons]
    pass_runs = 0
    for status in statuses:
        if status == "PASS":
            pass_runs += 1
        else:
            pass_runs = 0
        if pass_runs >= REQUIRED_CONSECUTIVE_PASSING_PAIRS:
            break
    else:
        return "FAIL", "MESH_CANDIDATE_CONSECUTIVE_PASS_NOT_FOUND"
    last = comparisons[-1]
    if int(last.get("coarse_subdivisions", 0)) != 32 or int(last.get("fine_subdivisions", 0)) != 64:
        return "FAIL", "HEADROOM_COMPARISON_PAIR_MISMATCH"
    if last.get("overall_status") != "PASS":
        return "FAIL", "HEADROOM_COMPARISON_NOT_PASS"
    return "PASS", None


def _stage_by_mesh(stages: tuple[dict[str, Any], ...], mesh_n: int) -> dict[str, Any] | None:
    for stage in stages:
        if int(stage.get("mesh_n", 0)) == mesh_n:
            return stage
    return None


def experimental_rate_general_candidate_live(
    request: CandidateRatingRequest,
    *,
    root: Path,
    source_commit: str,
    evidence_snapshot_dir: Path,
    budget: GeneralLiveRatingBudget,
    stage_dir: Path | None = None,
    provider: CoolPropProvider | None = None,
) -> ExperimentalCandidateRatingResult | ExperimentalRatingBlocked:
    if not verify_task174_binding(request):
        return _general_blocked("TASK174_BINDING_GATE_FAILED")

    mesh_budgets = budget.mesh_budgets_s or {
        1: 180.0,
        2: 240.0,
        4: 300.0,
        8: 360.0,
        16: 480.0,
        32: 720.0,
        64: 900.0,
    }
    continuation = run_live_ladder_continuation(
        request,
        root=root,
        source_commit=source_commit,
        snapshot_dir=evidence_snapshot_dir,
        stage_dir=stage_dir,
        prior_pins=(),
        live_mesh_levels=(1, 2, 4, 8, 16, 32, 64),
        mesh_budgets_s=mesh_budgets,
        total_budget_s=budget.total_budget_s,
        rehydrate_budget_s=120.0,
        compare_budget_s=120.0,
    )
    if isinstance(continuation, ExperimentalRatingBlocked):
        return continuation
    snapshot_rel_path = continuation.request_snapshot_rel_path or ""
    return _finalize_from_continuation(
        request,
        continuation,
        snapshot_rel_path=snapshot_rel_path,
        provider=provider,
    )


def _finalize_from_continuation(
    request: CandidateRatingRequest,
    outcome: LiveContinuationOutcome,
    *,
    snapshot_rel_path: str,
    provider: CoolPropProvider | None,
) -> ExperimentalCandidateRatingResult | ExperimentalRatingBlocked:
    if outcome.status in ("TIMEOUT", "BLOCKED"):
        return _general_blocked(
            outcome.blocked_code or outcome.status,
            *outcome.blocked_diagnostics,
        )
    if outcome.ladder_continuation_status != "HEADROOM_PASS":
        return _general_blocked(
            "GENERAL_LIVE_RATING_INCOMPLETE",
            f"ladder_status={outcome.ladder_continuation_status}",
            f"orchestrator_status={outcome.status}",
        )

    mesh_gate, gate_err = _mesh_sequence_gate(tuple(outcome.mesh_comparisons))
    if mesh_gate != "PASS":
        return _general_blocked(gate_err or "MESH_SEQUENCE_GATE_FAILED")

    n32_stage = _stage_by_mesh(tuple(outcome.mesh_stages), ACCEPTED_MESH_N)
    n64_stage = _stage_by_mesh(tuple(outcome.mesh_stages), HEADROOM_MESH_N)
    if n32_stage is None or n64_stage is None:
        return _general_blocked("MISSING_ACCEPTED_OR_HEADROOM_STAGE")

    request_hash = candidate_rating_request_hash(request)
    context = t173._candidate_context(request)
    token = t173._CANDIDATE_RATING_CONTEXT.set(context)
    active_provider = provider or CoolPropProvider(cache_size=2048)
    try:
        try:
            accepted = replay_verified_prior_stage_mesh(
                ACCEPTED_MESH_N,
                shooting_enthalpy_j_kg=str(n32_stage["shooting_enthalpy_for_rehydrate"]),
                outer_iterations=int(n32_stage.get("outer_iterations_for_rehydrate", 0)),
                expected_mesh_hash=str(n32_stage["mesh_result_hash"]),
                provider=active_provider,
                shell_authority=context.shell_authority,
            )
            headroom = replay_verified_prior_stage_mesh(
                HEADROOM_MESH_N,
                shooting_enthalpy_j_kg=str(n64_stage["shooting_enthalpy_for_rehydrate"]),
                outer_iterations=int(n64_stage.get("outer_iterations_for_rehydrate", 0)),
                expected_mesh_hash=str(n64_stage["mesh_result_hash"]),
                provider=active_provider,
                shell_authority=context.shell_authority,
            )
        except LiveMeshReplayError as exc:
            return _general_blocked(exc.code, *exc.diagnostics)

        if not verify_accepted_cell_count(accepted, context, ACCEPTED_MESH_N):
            return _general_blocked("ACCEPTED_CELL_COUNT_MISMATCH")
        cell_ok = verify_cell_closure(accepted)
        energy_ok = verify_energy_balance(accepted)
        wall_ok = verify_wall_extrema_from_cells(accepted)
        if not cell_ok or not energy_ok or not wall_ok:
            return _general_blocked(
                "CELL_ENERGY_OR_WALL_VERIFICATION_FAILED",
                f"task172_cell_closure={cell_ok}",
                f"energy_balance={energy_ok}",
                f"wall_extrema={wall_ok}",
            )
        terminal_ok = t173._terminal_tolerance_pass(accepted) and t173._terminal_tolerance_pass(
            headroom
        )
        if not terminal_ok:
            return _general_blocked("TERMINAL_TOLERANCE_FAILED")
        try:
            trajectory = build_accepted_trajectory_projection(accepted, context)
            trajectory_mode = "PRODUCTION_PROJECTION_COMPATIBLE"
        except t173._Stage3Failure as exc:
            return _general_blocked("ACCEPTED_TRAJECTORY_PROJECTION_FAILED", str(exc))

        obs = accepted.observables
        tube_in = accepted.faces_tube[0].temperature_k
        shell_in = accepted.faces_shell[-1].temperature_k
        chain_hashes = tuple(
            sorted(
                (f"stage_mesh_n{int(stage.get('mesh_n', 0))}", str(stage.get("mesh_result_hash")))
                for stage in outcome.mesh_stages
                if stage.get("mesh_result_hash")
            )
        )
        provenance: tuple[tuple[str, str], ...] = tuple(
            sorted(
                (
                    ("execution_mode", "LIVE_NUMERICAL_SOLVE"),
                    ("experimental_rating_authority_id", GENERAL_LIVE_RATING_R21_AUTHORITY_ID),
                    ("rating_request_hash", request_hash),
                    ("accepted_mesh_result_hash", accepted.mesh_result_hash),
                    ("headroom_mesh_result_hash", headroom.mesh_result_hash),
                    ("accepted_mesh_source", "GENERAL_LIVE_OUTER_SOLVE"),
                    ("headroom_mesh_source", "GENERAL_LIVE_OUTER_SOLVE"),
                    ("mesh_replay_mode", "LIVE_MESH_REPLAY"),
                    ("trajectory_projection_mode", trajectory_mode),
                    ("task174_result_hash", request.task174_result.result_hash),
                    ("snapshot_rel_path", snapshot_rel_path),
                    ("orchestrator_wall_seconds", str(Decimal(str(outcome.total_wall_seconds)))),
                )
            )
        )
        result = ExperimentalCandidateRatingResult(
            status="CANDIDATE_UNAPPROVED",
            numerical_authority_status="CANDIDATE",
            production_integration=False,
            execution_mode="LIVE_NUMERICAL_SOLVE",
            experimental_rating_authority_id=GENERAL_LIVE_RATING_R21_AUTHORITY_ID,
            candidate_id=request.candidate_id,
            candidate_hash=request.candidate_hash,
            rating_request_hash=request_hash,
            accepted_mesh_n=ACCEPTED_MESH_N,
            headroom_mesh_n=HEADROOM_MESH_N,
            accepted_mesh_result_hash=accepted.mesh_result_hash,
            headroom_mesh_result_hash=headroom.mesh_result_hash,
            total_duty_w=obs.total_duty_w,
            tube_outlet_temperature_k=obs.tube_outlet_temperature_k,
            shell_outlet_temperature_k=obs.shell_outlet_temperature_k,
            tube_inlet_temperature_k=tube_in,
            shell_inlet_temperature_k=shell_in,
            tube_outlet_pressure_pa=request.task174_result.tube_outlet_pressure_pa,
            shell_outlet_pressure_pa=request.task174_result.shell_outlet_pressure_pa,
            wall_inner_min_k=obs.wall_inner_min_k,
            wall_inner_max_k=obs.wall_inner_max_k,
            wall_outer_min_k=obs.wall_outer_min_k,
            wall_outer_max_k=obs.wall_outer_max_k,
            minimum_approach_temperature_k=obs.minimum_approach_temperature_k,
            energy_balance_residual_w=obs.energy_balance_residual_w,
            terminal_boundary_residual_k=obs.terminal_boundary_residual_k,
            terminal_boundary_residual_j_kg=obs.terminal_boundary_residual_j_kg,
            mesh_sequence_gate=mesh_gate,
            strict_replay_pass=True,
            task172_cell_closure_verified=cell_ok,
            wall_temperature_extrema_verified=wall_ok,
            energy_balance_pass=energy_ok,
            mesh_convergence_comparisons=outcome.mesh_comparisons,
            evidence_chain_hashes=chain_hashes,
            accepted_trajectory_projection=trajectory,
            task174_result_hash=request.task174_result.result_hash,
            authority_differences=tuple(authority_differences_payload()),
            provenance=provenance,
            result_hash="0" * 64,
            result_id="pending",
        )
        rh = general_live_rating_result_hash(result)
        rid = general_live_rating_result_id(rh)
        return result.model_copy(update={"result_hash": rh, "result_id": rid})
    finally:
        t173._CANDIDATE_RATING_CONTEXT.reset(token)


def finalize_general_live_rating_from_continuation(
    request: CandidateRatingRequest,
    outcome: LiveContinuationOutcome,
    *,
    provider: CoolPropProvider | None = None,
) -> ExperimentalCandidateRatingResult | ExperimentalRatingBlocked:
    snapshot_rel = outcome.request_snapshot_rel_path or ""
    return _finalize_from_continuation(
        request,
        outcome,
        snapshot_rel_path=snapshot_rel,
        provider=provider,
    )
