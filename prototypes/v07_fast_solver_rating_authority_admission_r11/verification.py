"""Fail-closed engineering verification for experimental Candidate Rating."""

from __future__ import annotations

from decimal import Decimal

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
)
from hexagent.exchangers.shell_tube.task174_hydraulic_orchestration.service import (
    recompute_task174_result_hash,
)


def expected_cell_count(context: t173._CandidateRatingContext, subdivisions: int) -> int:
    return context.interval_count * subdivisions


def verify_accepted_cell_count(
    run: t173._MeshRun,
    context: t173._CandidateRatingContext,
    subdivisions: int,
) -> bool:
    return len(run.cells) == expected_cell_count(context, subdivisions)


def verify_cell_closure(run: t173._MeshRun) -> bool:
    from decimal import localcontext

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


def verify_wall_extrema_from_cells(run: t173._MeshRun) -> bool:
    if not run.cells:
        return False
    inner = tuple(cell.rated_cell.wall_temperature_inner_k for cell in run.cells)
    outer = tuple(cell.rated_cell.wall_temperature_outer_k for cell in run.cells)
    obs = run.observables
    return (
        obs.wall_inner_min_k == min(inner)
        and obs.wall_inner_max_k == max(inner)
        and obs.wall_outer_min_k == min(outer)
        and obs.wall_outer_max_k == max(outer)
    )


def verify_task174_binding(request: CandidateRatingRequest) -> bool:
    t174 = request.task174_result
    if t174.status != "VALIDATED":
        return False
    if t174.result_hash != recompute_task174_result_hash(t174):
        return False
    return t174.task029_result_hash == request.task029_result.result_hash


def verify_energy_balance(run: t173._MeshRun) -> bool:
    obs = run.observables
    return obs.energy_balance_residual_w <= max(
        t173.ENERGY_ACCEPTANCE_FLOOR_W, obs.duty_roundoff_floor_w
    )


def build_accepted_trajectory_projection(
    run: t173._MeshRun,
    context: t173._CandidateRatingContext,
) -> dict:
    """Fail-closed: raises t173._Stage3Failure if projection cannot be built."""
    return t173._candidate_accepted_trajectory_projection(run, context)
