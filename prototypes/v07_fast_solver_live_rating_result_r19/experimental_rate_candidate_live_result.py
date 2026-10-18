"""Build full experimental Candidate Rating from verified live mesh evidence."""

from __future__ import annotations

from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173
from hexagent.exchangers.shell_tube.task173_integrated_rating.candidate_models import (
    candidate_rating_request_hash,
)
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v07_fast_solver_live_rating_result_r19.live_evidence_admission import (
    LiveMeshEvidenceChain,
)
from prototypes.v07_fast_solver_live_rating_result_r19.live_mesh_replay import (
    LiveMeshReplayError,
    replay_verified_prior_stage_mesh,
)
from prototypes.v07_fast_solver_live_rating_result_r19.live_result_hash import (
    LIVE_RATING_RESULT_R19_AUTHORITY_ID,
    live_rating_result_hash,
    live_rating_result_id,
)
from prototypes.v07_fast_solver_n4_mesh_convergence_r5.mesh_replay import (
    compare_mesh_pair,
    comparison_payload,
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
    verify_wall_extrema_from_cells,
)

ACCEPTED_MESH_N = 32
HEADROOM_MESH_N = 64


def experimental_rate_candidate_live_result(
    evidence: LiveMeshEvidenceChain,
    *,
    provider: CoolPropProvider | None = None,
) -> ExperimentalCandidateRatingResult | ExperimentalRatingBlocked:
    request = evidence.request
    request_hash = candidate_rating_request_hash(request)
    if request_hash != evidence.rating_request_hash:
        return ExperimentalRatingBlocked(
            status="BLOCKED",
            blocked_code="RATING_REQUEST_HASH_MISMATCH",
            blocked_diagnostics=(evidence.rating_request_hash, request_hash),
            execution_mode="LIVE_NUMERICAL_SOLVE",
        )

    context = t173._candidate_context(request)
    token = t173._CANDIDATE_RATING_CONTEXT.set(context)
    active_provider = provider or CoolPropProvider(cache_size=2048)
    try:
        n32_stage = next(s for s in evidence.mesh_stages if int(s.get("mesh_n", 0)) == 32)
        n64_stage = next(s for s in evidence.mesh_stages if int(s.get("mesh_n", 0)) == 64)
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
            return ExperimentalRatingBlocked(
                status="BLOCKED",
                blocked_code=exc.code,
                blocked_diagnostics=exc.diagnostics,
                execution_mode="LIVE_NUMERICAL_SOLVE",
            )

        live_compare = comparison_payload(compare_mesh_pair(accepted, headroom))
        if live_compare.get("overall_status") != "PASS":
            return ExperimentalRatingBlocked(
                status="BLOCKED",
                blocked_code="LIVE_HEADROOM_COMPARE_FAILED",
                blocked_diagnostics=(str(live_compare.get("overall_status")),),
                execution_mode="LIVE_NUMERICAL_SOLVE",
            )

        if not verify_accepted_cell_count(accepted, context, ACCEPTED_MESH_N):
            return ExperimentalRatingBlocked(
                status="BLOCKED",
                blocked_code="ACCEPTED_CELL_COUNT_MISMATCH",
                execution_mode="LIVE_NUMERICAL_SOLVE",
            )
        if not t173._terminal_tolerance_pass(accepted) or not t173._terminal_tolerance_pass(
            headroom
        ):
            return ExperimentalRatingBlocked(
                status="BLOCKED",
                blocked_code="TERMINAL_TOLERANCE_FAILED",
                execution_mode="LIVE_NUMERICAL_SOLVE",
            )
        cell_ok = verify_cell_closure(accepted)
        energy_ok = verify_energy_balance(accepted)
        wall_ok = verify_wall_extrema_from_cells(accepted)
        if not cell_ok or not energy_ok or not wall_ok:
            return ExperimentalRatingBlocked(
                status="BLOCKED",
                blocked_code="CELL_ENERGY_OR_WALL_VERIFICATION_FAILED",
                blocked_diagnostics=(
                    f"task172_cell_closure={cell_ok}",
                    f"energy_balance={energy_ok}",
                    f"wall_extrema={wall_ok}",
                ),
                execution_mode="LIVE_NUMERICAL_SOLVE",
            )
        try:
            trajectory = build_accepted_trajectory_projection(accepted, context)
            trajectory_mode = "PRODUCTION_PROJECTION_COMPATIBLE"
        except t173._Stage3Failure as exc:
            return ExperimentalRatingBlocked(
                status="BLOCKED",
                blocked_code="ACCEPTED_TRAJECTORY_PROJECTION_FAILED",
                blocked_diagnostics=(str(exc),),
                execution_mode="LIVE_NUMERICAL_SOLVE",
            )

        obs = accepted.observables
        tube_in = accepted.faces_tube[0].temperature_k
        shell_in = accepted.faces_shell[-1].temperature_k
        provenance: tuple[tuple[str, str], ...] = tuple(
            sorted(
                (
                    ("execution_mode", "LIVE_NUMERICAL_SOLVE"),
                    ("experimental_rating_authority_id", LIVE_RATING_RESULT_R19_AUTHORITY_ID),
                    ("rating_request_hash", request_hash),
                    ("accepted_mesh_result_hash", accepted.mesh_result_hash),
                    ("headroom_mesh_result_hash", headroom.mesh_result_hash),
                    ("accepted_mesh_source", "VERIFIED_PRIOR_LIVE_STAGE"),
                    ("headroom_mesh_source", "VERIFIED_PRIOR_LIVE_STAGE"),
                    ("mesh_replay_mode", "LIVE_MESH_REPLAY"),
                    ("trajectory_projection_mode", trajectory_mode),
                    ("task174_result_hash", request.task174_result.result_hash),
                    ("snapshot_rel_path", evidence.snapshot_rel_path),
                )
            )
        )
        result = ExperimentalCandidateRatingResult(
            status="CANDIDATE_UNAPPROVED",
            numerical_authority_status="CANDIDATE",
            production_integration=False,
            execution_mode="LIVE_NUMERICAL_SOLVE",
            experimental_rating_authority_id=LIVE_RATING_RESULT_R19_AUTHORITY_ID,
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
            mesh_sequence_gate="PASS",
            strict_replay_pass=True,
            task172_cell_closure_verified=cell_ok,
            wall_temperature_extrema_verified=wall_ok,
            energy_balance_pass=energy_ok,
            mesh_convergence_comparisons=evidence.mesh_comparisons,
            evidence_chain_hashes=evidence.evidence_chain_hashes,
            accepted_trajectory_projection=trajectory,
            task174_result_hash=request.task174_result.result_hash,
            authority_differences=tuple(authority_differences_payload()),
            provenance=provenance,
            result_hash="0" * 64,
            result_id="pending",
        )
        rh = live_rating_result_hash(result)
        rid = live_rating_result_id(rh)
        return result.model_copy(update={"result_hash": rh, "result_id": rid})
    finally:
        t173._CANDIDATE_RATING_CONTEXT.reset(token)
