"""Positive-duty Task172 cell probes and native cell root (R4)."""

# ruff: noqa: E501

from __future__ import annotations

import itertools
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, cast

from hexagent.exchangers.shell_tube.bell_delaware.models import Task166BlockedResult, Task166Result
from hexagent.exchangers.shell_tube.manufacturable_candidates import service as task168
from hexagent.exchangers.shell_tube.manufacturable_candidates.canonical import candidate_space_hash
from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173
from hexagent.exchangers.shell_tube.task173_integrated_sizing.candidate_materialization import (
    materialize_candidate_task171,
)
from hexagent.exchangers.shell_tube.task173_integrated_sizing.service import (
    DIMENSION_ORDER,
    _candidate_rating_request,
    _candidate_request_for_task174,
    validate_task174_candidate,
)
from hexagent.exchangers.shell_tube.task174_hydraulic_orchestration import (
    Task174NativeOutputs,
    Task174SuccessResult,
)
from hexagent.properties.base import FluidIdentifier
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v07_general_rating_sizing_mvp.candidate_selection import (
    CandidateSelectionOutcome,
    enumerate_experimental_rating_candidates,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase
from prototypes.v07_general_rating_sizing_mvp.sizing_request_builder import (
    build_task173_sizing_request,
)
from prototypes.v07_general_rating_sizing_mvp.solver_performance import (
    build_solver_performance_profile,
)


@dataclass(frozen=True)
class NativeCellContext:
    candidate_id: str
    candidate_hash: str
    rating_request_hash: str
    task171_result_hash: str
    task174_result_hash: str
    task025_parallel_area_m2: str
    physical_tube_count: int
    context: Any
    support: Any
    shell_authority: Any


def build_native_cell_context(
    case: EngineeringCase,
    *,
    selection: CandidateSelectionOutcome | None = None,
) -> NativeCellContext:
    outcome = selection or enumerate_experimental_rating_candidates(case)
    if outcome.selected_candidate_id is None:
        raise RuntimeError("no experimental rating candidate selected")
    target_id = outcome.selected_candidate_id
    sizing_req = build_task173_sizing_request(case)
    t168 = sizing_req.task168_candidate_request
    authorities = task168._authority_map(t168)
    dimensions = tuple(
        task168._sort_values(authorities[role].values)
        for role in DIMENSION_ORDER
        if role != "SHELL_GEOMETRY_ID"
    )
    space_hash = candidate_space_hash(t168, t168.discrete_candidate_set_authorities)
    digest = sizing_req.requirement_authority.canonical_hash
    from hexagent.exchangers.shell_tube.task173_integrated_rating.candidate_models import (
        candidate_rating_request_hash,
    )

    for combination in itertools.product(t168.shell_geometry_catalog.records, *dimensions):
        candidate = task168._candidate(t168, authorities, combination[0], tuple(combination[1:]))
        if task168._structural_blockers(candidate):
            continue
        bundle, stage_failure, _ = task168._execute_candidate_chain(
            t168,
            candidate,
            combination[0],
            include_legacy_task162=False,
            include_legacy_task168_rating_dependencies=False,
            preserve_baffle_orientation_sequence=False,
        )
        if stage_failure is not None:
            continue
        if candidate.candidate_id != target_id:
            continue
        topology = materialize_candidate_task171(
            candidate=candidate,
            configuration=bundle.task020_configuration,
            layout=bundle.task021_layout,
            bundle_geometry=bundle.task022_geometry,
            baffle_geometry=bundle.task024_geometry,
            task025_result=bundle.task025_result,
            task024_request=bundle.task024_request,
            task025_request=bundle.task025_request,
        )
        t174_req = _candidate_request_for_task174(candidate, bundle, topology)
        t174 = validate_task174_candidate(
            t174_req,
            Task174NativeOutputs(
                task029=bundle.task029_result,
                task034=None,
                task166=cast(Task166Result | Task166BlockedResult | None, bundle.task166_result),
            ),
        )
        if type(t174) is not Task174SuccessResult:
            continue
        rating_request = _candidate_rating_request(
            candidate, space_hash, bundle, topology, t174, digest
        )
        ctx = t173._candidate_context(rating_request)
        token = t173._CANDIDATE_RATING_CONTEXT.set(ctx)
        try:
            support = t173._build_candidate_local_support(ctx, 0, 1, 0)
            return NativeCellContext(
                candidate_id=candidate.candidate_id,
                candidate_hash=candidate.candidate_hash,
                rating_request_hash=candidate_rating_request_hash(rating_request),
                task171_result_hash=topology.result_hash or "",
                task174_result_hash=t174.result_hash,
                task025_parallel_area_m2=str(bundle.task025_result.total_parallel_flow_area_m2),
                physical_tube_count=bundle.task021_layout.physical_tube_count,
                context=ctx,
                support=support,
                shell_authority=ctx.shell_authority,
            )
        finally:
            t173._CANDIDATE_RATING_CONTEXT.reset(token)
    raise RuntimeError("no native cell context materialized for case")


def _shell_state_from_temperature_k(provider: CoolPropProvider, temperature_k: float) -> Any:
    state = provider.state_tp(FluidIdentifier("Water", "HEOS"), temperature_k, 101325.0)
    return t173._state_from_enthalpy(provider, Decimal(str(state.enthalpy_j_kg)))


def run_positive_duty_trials(
    native: NativeCellContext,
    *,
    shell_left_basis: str,
    shell_temperature_k: float,
    q_values_w: tuple[float, ...],
) -> dict[str, Any]:
    provider = CoolPropProvider()
    tube = t173._state_at_inlet(provider, t173.TUBE_INLET_T_K)
    shell = _shell_state_from_temperature_k(provider, shell_temperature_k)
    token = t173._CANDIDATE_RATING_CONTEXT.set(native.context)
    trials: list[dict[str, Any]] = []
    try:
        for q in q_values_w:
            t0 = time.perf_counter()
            record: dict[str, Any] = {
                "q_trial_w": q,
                "shell_physical_left_basis": shell_left_basis,
                "shell_physical_left_temperature_k": shell_temperature_k,
                "wall_seconds": 0.0,
            }
            try:
                evaluation = t173._cell_evaluation(
                    q,
                    support=native.support,
                    tube_upstream=tube,
                    shell_physical_left=shell,
                    provider=provider,
                    shell_authority=native.shell_authority,
                )
                q_task172 = evaluation.task172_result.signed_q_hot_to_cold_w
                residual = Decimal(str(q)) - q_task172
                record.update(
                    {
                        "outcome": "VALIDATED",
                        "task172_status": evaluation.task172_result.status,
                        "task172_signed_q_hot_to_cold_w": str(q_task172),
                        "residual_f_q_w": str(residual),
                        "task172_request_hash": evaluation.task172_result.request_hash,
                        "task172_result_hash": evaluation.task172_result.result_hash,
                    }
                )
            except t173._LowSideDomainInfeasible:
                record.update(
                    {
                        "outcome": "LOW_SIDE_DOMAIN_INFEASIBLE",
                        "original_failure_code": "LOW_SIDE_DOMAIN_INFEASIBLE",
                    }
                )
            except t173._Stage3Failure as exc:
                record.update(
                    {
                        "outcome": "HARD_BLOCKER",
                        "original_failure_code": exc.code,
                        "diagnostics": list(exc.diagnostics),
                    }
                )
            except t173._Task172NumericalHole:
                record.update(
                    {
                        "outcome": "TASK172_NUMERICAL_HOLE",
                        "original_failure_code": "BLOCKED_RESIDUAL_ACCEPTANCE",
                    }
                )
            record["wall_seconds"] = round(time.perf_counter() - t0, 6)
            trials.append(record)
    finally:
        t173._CANDIDATE_RATING_CONTEXT.reset(token)
    positive_validated = sum(
        1
        for item in trials
        if item.get("outcome") == "VALIDATED" and float(item["q_trial_w"]) > 0.0
    )
    return {
        "schema_version": "hxforge.positive-duty-cell-trials.v1",
        "candidate_id": native.candidate_id,
        "candidate_hash": native.candidate_hash,
        "rating_request_hash": native.rating_request_hash,
        "physical_support_id": native.support.physical_segment_id,
        "trials": trials,
        "positive_duty_trial_count": sum(1 for item in trials if float(item["q_trial_w"]) > 0.0),
        "positive_duty_task172_validated_count": positive_validated,
    }


def solve_positive_duty_cell_root(
    native: NativeCellContext,
    *,
    shell_left_basis: str,
    shell_temperature_k: float,
) -> dict[str, Any]:
    provider = CoolPropProvider()
    tube = t173._state_at_inlet(provider, t173.TUBE_INLET_T_K)
    shell = _shell_state_from_temperature_k(provider, shell_temperature_k)
    token = t173._CANDIDATE_RATING_CONTEXT.set(native.context)
    t0 = time.perf_counter()
    try:
        solution = t173._solve_cell(
            support=native.support,
            tube_upstream=tube,
            shell_physical_left=shell,
            provider=provider,
            shell_authority=native.shell_authority,
            mesh_subdivisions=1,
            capture_diagnostics=True,
        )
    finally:
        t173._CANDIDATE_RATING_CONTEXT.reset(token)
    task172 = solution.task172_result
    residual = Decimal(str(solution.q_w)) - task172.signed_q_hot_to_cold_w
    return {
        "schema_version": "hxforge.cell-root-result.v1",
        "status": "ACCEPTED",
        "candidate_id": native.candidate_id,
        "shell_physical_left_basis": shell_left_basis,
        "shell_physical_left_temperature_k": shell_temperature_k,
        "q_root_w": str(solution.q_w),
        "task172_signed_q_hot_to_cold_w": str(task172.signed_q_hot_to_cold_w),
        "residual_f_q_w": str(residual),
        "task172_status": task172.status,
        "task172_request_hash": task172.request_hash,
        "task172_result_hash": task172.result_hash,
        "cell_root_result_hash": task172.result_hash,
        "wall_seconds": round(time.perf_counter() - t0, 3),
        "positive_duty_cell_root_accepted": float(solution.q_w) > 0.0
        and task172.status == "VALIDATED"
        and abs(residual) <= Decimal("1e-6"),
    }


def run_low_mesh_numeric(
    native: NativeCellContext,
    *,
    subdivisions: int = 1,
) -> dict[str, Any]:
    mesh, profile, _obs = run_mesh_numeric_with_profile(native, subdivisions=subdivisions)
    return {**mesh, "solver_performance_profile": profile}


def run_mesh_numeric_with_profile(
    native: NativeCellContext,
    *,
    subdivisions: int,
) -> tuple[dict[str, Any], dict[str, Any], Any | None]:
    provider = CoolPropProvider()
    lookup_count = {"n": 0}
    _state_tp = provider.state_tp

    def _counting_state_tp(*args: Any, **kwargs: Any) -> Any:
        lookup_count["n"] += 1
        return _state_tp(*args, **kwargs)

    provider.state_tp = _counting_state_tp  # type: ignore[method-assign]
    token = t173._CANDIDATE_RATING_CONTEXT.set(native.context)
    stats = t173._CellSearchStats()
    t0 = time.perf_counter()
    run: t173._MeshRun | None = None
    try:
        run = t173._candidate_transient_outer_boundary(
            subdivisions, provider, native.shell_authority, stats
        )
    except t173._Stage3Failure as exc:
        elapsed = time.perf_counter() - t0
        profile = build_solver_performance_profile(
            stats=stats,
            mesh_run=None,
            property_provider_state_lookup_count=lookup_count["n"],
            total_wall_seconds=elapsed,
            subdivisions=subdivisions,
        )
        mesh = {
            "schema_version": "hxforge.low-mesh-result.v1",
            "status": "BLOCKED",
            "mesh_level": subdivisions,
            "failure_code": exc.code,
            "diagnostics": list(exc.diagnostics),
            "wall_seconds": round(elapsed, 3),
            "low_mesh_numeric_valid": False,
            "full_rating_converged": False,
        }
        return mesh, profile, None
    finally:
        t173._CANDIDATE_RATING_CONTEXT.reset(token)
    elapsed = time.perf_counter() - t0
    assert run is not None
    obs = run.observables
    profile = build_solver_performance_profile(
        stats=stats,
        mesh_run=run,
        property_provider_state_lookup_count=lookup_count["n"],
        total_wall_seconds=elapsed,
        subdivisions=subdivisions,
    )
    mesh = {
        "schema_version": "hxforge.low-mesh-result.v1",
        "status": "NUMERIC_VALID",
        "mesh_level": subdivisions,
        "mesh_result_hash": run.mesh_result_hash,
        "total_duty_w": str(obs.total_duty_w),
        "energy_balance_residual_w": str(obs.energy_balance_residual_w),
        "terminal_boundary_residual_k": str(obs.terminal_boundary_residual_k),
        "terminal_boundary_residual_j_kg": str(obs.terminal_boundary_residual_j_kg),
        "task172_local_evaluation_count": stats.task172_local_evaluation_count,
        "wall_seconds": round(elapsed, 3),
        "low_mesh_numeric_valid": True,
        "full_rating_converged": False,
    }
    return mesh, profile, obs
