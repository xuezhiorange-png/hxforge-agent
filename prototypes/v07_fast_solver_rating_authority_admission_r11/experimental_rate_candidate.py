"""Experimental Candidate Rating API (frozen evidence replay for Candidate B)."""

from __future__ import annotations

import importlib.util
import json
from decimal import Decimal, localcontext
from pathlib import Path

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.task172_local_runtime.models import (
    CandidateTask172LocalRequest,
    Task172LocalResult,
)
from hexagent.exchangers.shell_tube.task172_local_runtime.service import (
    recompute_task172_request_hash,
    recompute_task172_result_hash,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173
from hexagent.exchangers.shell_tube.task173_integrated_rating.candidate_models import (
    CandidateRatingRequest,
    candidate_rating_request_hash,
)
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v07_fast_solver_evidence_gate.trusted_constants import (
    CANDIDATE_B_ID,
    R9_RESULT_JSON_REL,
    R10_RESULT_JSON_REL,
)
from prototypes.v07_fast_solver_n4_mesh_convergence_r5.mesh_replay import (
    compare_mesh_pair,
    comparison_payload,
)
from prototypes.v07_fast_solver_rating_authority_admission_r11.authority_differences import (
    authority_differences_payload,
)
from prototypes.v07_fast_solver_rating_authority_admission_r11.evidence_chain import (
    verify_candidate_b_evidence_chain,
)
from prototypes.v07_fast_solver_rating_authority_admission_r11.experimental_models import (
    EXPERIMENTAL_RATING_AUTHORITY_ID,
    ExecutionMode,
    ExperimentalCandidateRatingResult,
    ExperimentalRatingBlocked,
)
from prototypes.v07_fast_solver_replay_n8_r6.strict_replay import strict_replay_level

ROOT = Path(__file__).resolve().parents[2]
FROZEN_RUNNER = (
    ROOT / "docs/tasks/evidence/TASK-173-v0.7-full-sizing-q13-correction-candidate-rating-run-r1.py"
)


def experimental_rating_result_hash(result: ExperimentalCandidateRatingResult) -> str:
    return canonical_sha256(result.model_dump(mode="json", exclude={"result_hash", "result_id"}))


def experimental_rating_result_id(result_hash: str) -> str:
    return f"experimental-candidate-rating:{result_hash[:16]}"


def _load_frozen_candidate_request(candidate_id: str) -> CandidateRatingRequest:
    if candidate_id != CANDIDATE_B_ID:
        raise ValueError("only frozen Candidate B is admitted in R11")
    spec = importlib.util.spec_from_file_location("q13", FROZEN_RUNNER)
    if spec is None or spec.loader is None:
        raise RuntimeError("frozen candidate runner missing")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _candidate, rating_request = mod._build_candidate_requests()[candidate_id]
    if type(rating_request) is not CandidateRatingRequest:
        encoded = json.dumps(rating_request, separators=(",", ":"), ensure_ascii=False)
        rating_request = CandidateRatingRequest.model_validate_json(encoded, strict=True)
    return rating_request


def _verify_cell_closure(run: t173._MeshRun, context: t173._CandidateRatingContext) -> bool:
    for record in run.cells:
        request = record.solution.task172_request
        result = record.solution.task172_result
        if (
            type(request) is not CandidateTask172LocalRequest
            or type(result) is not Task172LocalResult
            or result.status != "VALIDATED"
        ):
            return False
        request_hash = recompute_task172_request_hash(request)
        result_hash = recompute_task172_result_hash(result)
        with localcontext() as decimal_context:
            decimal_context.prec = 80
            residual = record.solution.q_w - result.signed_q_hot_to_cold_w
        if (
            result.request_hash != request_hash
            or result.result_hash != result_hash
            or abs(residual) > Decimal("1e-6")
        ):
            return False
    return True


def _energy_balance_pass(run: t173._MeshRun) -> bool:
    obs = run.observables
    return obs.energy_balance_residual_w <= max(
        t173.ENERGY_ACCEPTANCE_FLOOR_W, obs.duty_roundoff_floor_w
    )


def experimental_rate_candidate(
    candidate_id: str,
    *,
    execution_mode: ExecutionMode = "FROZEN_EVIDENCE_REPLAY",
    provider: CoolPropProvider | None = None,
) -> ExperimentalCandidateRatingResult | ExperimentalRatingBlocked:
    if execution_mode != "FROZEN_EVIDENCE_REPLAY":
        return ExperimentalRatingBlocked(
            status="BLOCKED",
            blocked_code="LIVE_NUMERICAL_SOLVE_NOT_IMPLEMENTED",
            blocked_diagnostics=("only FROZEN_EVIDENCE_REPLAY is in scope for R11",),
            execution_mode=execution_mode,
        )
    try:
        chain = verify_candidate_b_evidence_chain()
        request = _load_frozen_candidate_request(candidate_id)
        request_hash = candidate_rating_request_hash(request)
        if request_hash != chain["rating_request_hash"]:
            raise ValueError("rating request hash mismatch vs frozen evidence chain")
        if request.candidate_id != candidate_id:
            raise ValueError("candidate_id mismatch")
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        return ExperimentalRatingBlocked(
            status="BLOCKED",
            blocked_code="EVIDENCE_CHAIN_OR_REQUEST_FAILED",
            blocked_diagnostics=(str(exc),),
            execution_mode=execution_mode,
        )

    context = t173._candidate_context(request)
    token = t173._CANDIDATE_RATING_CONTEXT.set(context)
    active_provider = provider or CoolPropProvider(cache_size=2048)
    try:
        n32_body = chain["r9_n32_body"]
        n64_body = chain["r10_n64_body"]
        r9_path = ROOT / R9_RESULT_JSON_REL
        r10_path = ROOT / R10_RESULT_JSON_REL
        n32_replay = strict_replay_level(
            32,
            n32_body,
            r9_path,
            active_provider,
            context.shell_authority,
            rating_request_hash=request_hash,
        )
        n64_replay = strict_replay_level(
            64,
            n64_body,
            r10_path,
            active_provider,
            context.shell_authority,
            rating_request_hash=request_hash,
        )
        n32_run = n32_replay.pop("_mesh_run")
        n64_run = n64_replay.pop("_mesh_run")
        strict_pass = (
            n32_replay.get("hash_parity") == "PASS" and n64_replay.get("hash_parity") == "PASS"
        )
        if not strict_pass:
            return ExperimentalRatingBlocked(
                status="BLOCKED",
                blocked_code="STRICT_MESH_REPLAY_FAILED",
                blocked_diagnostics=(
                    f"n32={n32_replay.get('hash_parity')}",
                    f"n64={n64_replay.get('hash_parity')}",
                ),
                execution_mode=execution_mode,
            )
        live_compare = comparison_payload(compare_mesh_pair(n32_run, n64_run))
        if live_compare.get("overall_status") != "PASS":
            return ExperimentalRatingBlocked(
                status="BLOCKED",
                blocked_code="LIVE_MESH_COMPARE_FAILED",
                blocked_diagnostics=(live_compare.get("overall_status", "UNKNOWN"),),
                execution_mode=execution_mode,
            )
        accepted = n32_run
        headroom = n64_run
        if not t173._terminal_tolerance_pass(accepted) or not t173._terminal_tolerance_pass(
            headroom
        ):
            return ExperimentalRatingBlocked(
                status="BLOCKED",
                blocked_code="TERMINAL_TOLERANCE_FAILED",
                execution_mode=execution_mode,
            )
        cell_ok = _verify_cell_closure(accepted, context)
        energy_ok = _energy_balance_pass(accepted)
        if not cell_ok or not energy_ok:
            return ExperimentalRatingBlocked(
                status="BLOCKED",
                blocked_code="CELL_OR_ENERGY_VERIFICATION_FAILED",
                blocked_diagnostics=(
                    f"task172_cell_closure={cell_ok}",
                    f"energy_balance={energy_ok}",
                ),
                execution_mode=execution_mode,
            )
        try:
            trajectory = t173._candidate_accepted_trajectory_projection(accepted, context)
            trajectory_mode: str = "PRODUCTION_PROJECTION_COMPATIBLE"
        except t173._Stage3Failure as exc:
            trajectory = {
                "schema_version": "task173.experimental-fast-accepted-trajectory.v1",
                "projection_error": str(exc),
                "mesh_result_hash": accepted.mesh_result_hash,
                "cell_count": len(accepted.cells),
            }
            trajectory_mode = "EXPERIMENTAL_FALLBACK_SUMMARY"

        obs = accepted.observables
        tube_in = accepted.faces_tube[0].temperature_k
        shell_in = accepted.faces_shell[-1].temperature_k
        provenance: tuple[tuple[str, str], ...] = tuple(
            sorted(
                (
                    ("execution_mode", execution_mode),
                    ("experimental_rating_authority_id", EXPERIMENTAL_RATING_AUTHORITY_ID),
                    ("rating_request_hash", request_hash),
                    ("accepted_mesh_result_hash", accepted.mesh_result_hash),
                    ("headroom_mesh_result_hash", headroom.mesh_result_hash),
                    ("trajectory_projection_mode", trajectory_mode),
                    ("task174_result_hash", request.task174_result.result_hash),
                    ("n32_replay_hash_parity", n32_replay.get("hash_parity", "")),
                    ("n64_replay_hash_parity", n64_replay.get("hash_parity", "")),
                )
            )
        )
        result = ExperimentalCandidateRatingResult(
            status="CANDIDATE_UNAPPROVED",
            numerical_authority_status="CANDIDATE",
            production_integration=False,
            execution_mode=execution_mode,
            experimental_rating_authority_id=EXPERIMENTAL_RATING_AUTHORITY_ID,
            candidate_id=request.candidate_id,
            candidate_hash=request.candidate_hash,
            rating_request_hash=request_hash,
            accepted_mesh_n=32,
            headroom_mesh_n=64,
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
            wall_temperature_extrema_verified=True,
            energy_balance_pass=energy_ok,
            mesh_convergence_comparisons=(
                chain["n16_n32_comparison"],
                chain["n32_n64_comparison"],
                live_compare,
            ),
            evidence_chain_hashes=chain["evidence_chain_hashes"],
            accepted_trajectory_projection=trajectory,
            task174_result_hash=request.task174_result.result_hash,
            authority_differences=tuple(authority_differences_payload()),
            provenance=provenance,
            result_hash="0" * 64,
            result_id="pending",
        )
        rh = experimental_rating_result_hash(result)
        rid = experimental_rating_result_id(rh)
        return result.model_copy(update={"result_hash": rh, "result_id": rid})
    finally:
        t173._CANDIDATE_RATING_CONTEXT.reset(token)
