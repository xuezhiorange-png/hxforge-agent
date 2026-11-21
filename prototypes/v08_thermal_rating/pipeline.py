"""V08-03: live thermal rating on V08-02 structural geometry (Task168 chain → Task173 rating)."""

# ruff: noqa: E501

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal, cast

from hexagent.exchangers.shell_tube.bell_delaware.models import Task166BlockedResult, Task166Result
from hexagent.exchangers.shell_tube.manufacturable_candidates.canonical import (
    request_hash as task168_request_hash_digest,
)
from hexagent.exchangers.shell_tube.segmented_thermal_state_topology.models import (
    Result as Task171Result,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating.candidate_models import (
    CandidateRatingSuccessResult,
    candidate_rating_request_hash,
    candidate_rating_result_hash,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating.experimental_thermal_boundary import (
    bind_experimental_thermal_boundary_v1,
    build_experimental_thermal_boundary_v1,
    reset_experimental_thermal_boundary,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating.models import (
    REVIEWED_MESH_SEQUENCE,
    Task173BlockedResult,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating.service import (
    ENERGY_ACCEPTANCE_FLOOR_W,
    validate_candidate_rating,
)
from hexagent.exchangers.shell_tube.task173_integrated_sizing.candidate_materialization import (
    materialize_candidate_task171,
)
from hexagent.exchangers.shell_tube.task173_integrated_sizing.service import (
    _candidate_request_for_task174,
    v08_thermal_rating_request,
)
from hexagent.exchangers.shell_tube.task174_hydraulic_orchestration import (
    Task174NativeOutputs,
    Task174SuccessResult,
)
from hexagent.exchangers.shell_tube.task174_hydraulic_orchestration import (
    validate_candidate_request as validate_task174_candidate,
)
from hexagent.properties.base import PropertyProvider
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_general_user_case.physical_feasibility import THERMODYNAMIC_DUTY_TOLERANCE
from prototypes.v08_general_user_case.solver_handoff import V08SolverHandoffV1
from prototypes.v08_general_user_case.user_design_case import NormalizedUserDesignCase
from prototypes.v08_geometry_candidate_generation.discrete_space import load_v08_discrete_space
from prototypes.v08_geometry_candidate_generation.errors import V08GeometryGenerationBlocked
from prototypes.v08_geometry_candidate_generation.generator import enumerate_structural_geometry
from prototypes.v08_geometry_candidate_generation.structural_bundles import (
    V08StructuralGeometryBundle,
)
from prototypes.v08_geometry_candidate_generation.task168_builder import (
    build_v08_task168_request,
    filter_discrete_space_by_envelope,
)

V08ThermalRatingTaskId = Literal[
    "V08_03_LIVE_THERMAL_RATING", "V08_03_LIVE_RATING_ACCEPTANCE_CLOSEOUT"
]

V08ThermalRatingBlockedReason = Literal[
    "MODEL_BLOCKED_THERMAL_BINDING",
    "NO_STRUCTURAL_GEOMETRY",
    "TASK174_BLOCKED",
    "ENGINEERING_ACCEPTANCE_RATING",
]

MeshNStatus = Literal["NOT_REACHED", "NUMERIC_VALID", "OTHER"]

RatingOutcome = Literal["RATING_SUCCESS", "RATING_BLOCKED", "TASK174_BLOCKED", "NOT_ATTEMPTED"]

EnergyBalanceStatus = Literal["PASS", "FAIL", "NOT_APPLICABLE"]

MeshConvergenceStatus = Literal["PASS", "FAIL", "NOT_APPLICABLE"]

EngineeringAcceptance = Literal["PASS", "BLOCKED"]


@dataclass(frozen=True)
class V08ThermalCandidateRatingRow:
    """One structural geometry row with Task171/174/173 traceability and rating outcome."""

    candidate_id: str
    candidate_hash: str
    geometry_projection_hash: str
    task174_status: str
    task171_result_hash: str | None
    task174_result_hash: str | None
    rating_request_hash: str | None
    rating_request_replay_ok: bool | None
    rating_outcome: RatingOutcome
    mesh_n1_status: MeshNStatus
    mesh_n2_status: MeshNStatus
    mesh_n4_status: MeshNStatus
    mesh_convergence_n1_n2_n4: MeshConvergenceStatus
    accepted_subdivisions_per_interval: str | None
    total_duty_w: str | None
    target_duty_w: str
    duty_vs_target: Literal["AT_OR_ABOVE_TARGET", "BELOW_TARGET"] | None
    tube_outlet_temperature_k: str | None
    shell_outlet_temperature_k: str | None
    energy_balance_residual_w: str | None
    energy_balance_status: EnergyBalanceStatus
    rating_blocked_code: str | None
    task173_diagnostics: tuple[str, ...]
    task173_result_hash: str | None


@dataclass(frozen=True)
class V08ThermalRatingResult:
    task_id: V08ThermalRatingTaskId
    status: Literal["OK", "BLOCKED", "PARTIAL"]
    blocked_reason: V08ThermalRatingBlockedReason | None
    engineering_acceptance: EngineeringAcceptance
    engineering_acceptance_blockers: tuple[str, ...]
    distinct_structural_geometries_attempted: int
    distinct_fully_converged_rating_count: int
    model_blockers: tuple[str, ...]
    candidate_space_hash: str | None
    task168_request_hash: str | None
    normalized_input_hash: str
    downstream_readiness: str
    target_duty_w: str
    candidates_rated: tuple[V08ThermalCandidateRatingRow, ...]
    warnings: tuple[str, ...]


def _mesh_level_status(
    mesh_levels: tuple[dict[str, object], ...], subdivisions: int
) -> MeshNStatus:
    for row in mesh_levels:
        if int(cast(Any, row.get("mesh_subdivisions", 0))) != subdivisions:
            continue
        status = str(row.get("mesh_status", "OTHER"))
        if status == "NUMERIC_VALID":
            return "NUMERIC_VALID"
        return "OTHER"
    return "NOT_REACHED"


def _pair_convergence_pass(
    comparisons: tuple[dict[str, object], ...], coarse: int, fine: int
) -> bool:
    for item in comparisons:
        if int(cast(Any, item["coarse_subdivisions"])) != coarse:
            continue
        if int(cast(Any, item["fine_subdivisions"])) != fine:
            continue
        return str(item.get("overall_status", "FAIL")) == "PASS"
    return False


def _mesh_convergence_n1_n2_n4(success: CandidateRatingSuccessResult) -> MeshConvergenceStatus:
    seq = REVIEWED_MESH_SEQUENCE
    mesh_levels = success.mesh_levels
    n1_ok = (_mesh_level_status(mesh_levels, 1) == "NUMERIC_VALID") if 1 in seq else False
    n2_ok = (_mesh_level_status(mesh_levels, 2) == "NUMERIC_VALID") if 2 in seq else False
    n4_ok = (_mesh_level_status(mesh_levels, 4) == "NUMERIC_VALID") if 4 in seq else False
    if not (n1_ok and n2_ok and n4_ok):
        return "FAIL"
    comparisons = success.convergence_comparisons
    if not (
        _pair_convergence_pass(comparisons, 1, 2)
        and _pair_convergence_pass(comparisons, 2, 4)
        and _pair_convergence_pass(comparisons, 4, 8)
    ):
        return "FAIL"
    return "PASS"


def _energy_balance_status(success: CandidateRatingSuccessResult) -> EnergyBalanceStatus:
    """Residual must be within the Task173 acceptance floor (success path already satisfied kernel gate)."""
    lim = ENERGY_ACCEPTANCE_FLOOR_W
    if abs(success.energy_balance_residual_w) <= lim:
        return "PASS"
    return "FAIL"


def _duty_vs_target(
    total_duty_w: Decimal, target_duty_w: Decimal
) -> Literal["AT_OR_ABOVE_TARGET", "BELOW_TARGET"]:
    if total_duty_w * THERMODYNAMIC_DUTY_TOLERANCE >= target_duty_w:
        return "AT_OR_ABOVE_TARGET"
    return "BELOW_TARGET"


def _verify_rating_hashes(
    *,
    topology: Task171Result,
    t174: Task174SuccessResult,
    request_hash: str,
    outcome: CandidateRatingSuccessResult,
) -> bool:
    if outcome.request_hash != request_hash:
        return False
    if outcome.task171_result_hash != topology.result_hash:
        return False
    if outcome.task174_result_hash != t174.result_hash:
        return False
    replay = candidate_rating_result_hash(outcome)
    return replay == outcome.result_hash


def _rate_one_structural_bundle(
    bundle_row: V08StructuralGeometryBundle,
    *,
    space_hash: str,
    target_duty_w: Decimal,
    normalized: NormalizedUserDesignCase,
    provider: PropertyProvider,
    handoff: V08SolverHandoffV1,
) -> V08ThermalCandidateRatingRow:
    candidate = bundle_row.candidate
    b = bundle_row.bundle
    topology = materialize_candidate_task171(
        candidate=candidate,
        configuration=b.task020_configuration,
        layout=b.task021_layout,
        bundle_geometry=b.task022_geometry,
        baffle_geometry=b.task024_geometry,
        task025_result=b.task025_result,
        task024_request=b.task024_request,
        task025_request=b.task025_request,
    )
    t174_req = _candidate_request_for_task174(candidate, b, topology)
    t174 = validate_task174_candidate(
        t174_req,
        Task174NativeOutputs(
            task029=b.task029_result,
            task034=None,
            task166=cast(Task166Result | Task166BlockedResult | None, b.task166_result),
        ),
    )
    if type(t174) is not Task174SuccessResult:
        return V08ThermalCandidateRatingRow(
            candidate_id=candidate.candidate_id,
            candidate_hash=candidate.candidate_hash,
            geometry_projection_hash="",
            task174_status="BLOCKED",
            task171_result_hash=getattr(topology, "result_hash", None),
            task174_result_hash=getattr(t174, "result_hash", None),
            rating_request_hash=None,
            rating_request_replay_ok=None,
            rating_outcome="TASK174_BLOCKED",
            mesh_n1_status="NOT_REACHED",
            mesh_n2_status="NOT_REACHED",
            mesh_n4_status="NOT_REACHED",
            mesh_convergence_n1_n2_n4="NOT_APPLICABLE",
            accepted_subdivisions_per_interval=None,
            total_duty_w=None,
            target_duty_w=str(target_duty_w),
            duty_vs_target=None,
            tube_outlet_temperature_k=None,
            shell_outlet_temperature_k=None,
            energy_balance_residual_w=None,
            energy_balance_status="NOT_APPLICABLE",
            rating_blocked_code=None,
            task173_diagnostics=(),
            task173_result_hash=getattr(t174, "result_hash", None),
        )

    rating_req = v08_thermal_rating_request(
        candidate,
        space_hash,
        b,
        topology,
        t174,
        bundle_row.task168_request_hash_digest,
    )
    rhash = candidate_rating_request_hash(rating_req)
    meta_ok = any(
        k == "v08_acceptance_task_id" and v == "V08_03_LIVE_RATING_ACCEPTANCE_CLOSEOUT"
        for k, v in rating_req.request_metadata
    )
    if not meta_ok:
        raise RuntimeError(
            "V08 rating request metadata must declare V08_03_LIVE_RATING_ACCEPTANCE_CLOSEOUT"
        )
    if handoff.thermal_binding is None:
        raise RuntimeError("thermal binding required for V08 rating (caller must gate)")
    exp = build_experimental_thermal_boundary_v1(
        provider=provider,
        tube_inlet_temperature_k=normalized.tube_side.inlet_temperature_k,
        shell_inlet_temperature_k=normalized.shell_side.inlet_temperature_k,
        tube_mass_flow_kg_s=normalized.tube_side.mass_flow_kg_s,
        shell_mass_flow_kg_s=normalized.shell_side.mass_flow_kg_s,
        tube_property_evaluation_pressure_pa=normalized.tube_side.inlet_pressure_pa,
        shell_property_evaluation_pressure_pa=normalized.shell_side.inlet_pressure_pa,
        allow_live_variable_tube_mass_flow=True,
        allow_live_variable_shell_mass_flow=True,
        allow_variable_water_temperature=True,
    )
    token = bind_experimental_thermal_boundary_v1(exp)
    try:
        outcome = validate_candidate_rating(rating_req, provider)
    finally:
        reset_experimental_thermal_boundary(token)
    if type(outcome) is Task173BlockedResult:
        return V08ThermalCandidateRatingRow(
            candidate_id=candidate.candidate_id,
            candidate_hash=candidate.candidate_hash,
            geometry_projection_hash="",
            task174_status="VALIDATED",
            task171_result_hash=topology.result_hash,
            task174_result_hash=t174.result_hash,
            rating_request_hash=rhash,
            rating_request_replay_ok=None,
            rating_outcome="RATING_BLOCKED",
            mesh_n1_status="NOT_REACHED",
            mesh_n2_status="NOT_REACHED",
            mesh_n4_status="NOT_REACHED",
            mesh_convergence_n1_n2_n4="NOT_APPLICABLE",
            accepted_subdivisions_per_interval=None,
            total_duty_w=None,
            target_duty_w=str(target_duty_w),
            duty_vs_target=None,
            tube_outlet_temperature_k=None,
            shell_outlet_temperature_k=None,
            energy_balance_residual_w=None,
            energy_balance_status="NOT_APPLICABLE",
            rating_blocked_code=outcome.failure_code,
            task173_diagnostics=outcome.diagnostics,
            task173_result_hash=outcome.result_hash,
        )
    assert type(outcome) is CandidateRatingSuccessResult
    replay_ok = _verify_rating_hashes(
        topology=topology, t174=t174, request_hash=rhash, outcome=outcome
    )
    mesh_levels = outcome.mesh_levels
    duty_class = _duty_vs_target(outcome.total_duty_w, target_duty_w)
    seq = REVIEWED_MESH_SEQUENCE
    mesh_conv = _mesh_convergence_n1_n2_n4(outcome)
    ebal = _energy_balance_status(outcome)
    return V08ThermalCandidateRatingRow(
        candidate_id=candidate.candidate_id,
        candidate_hash=candidate.candidate_hash,
        geometry_projection_hash="",
        task174_status="VALIDATED",
        task171_result_hash=topology.result_hash,
        task174_result_hash=t174.result_hash,
        rating_request_hash=rhash,
        rating_request_replay_ok=replay_ok,
        rating_outcome="RATING_SUCCESS",
        mesh_n1_status=_mesh_level_status(mesh_levels, 1) if 1 in seq else "NOT_REACHED",
        mesh_n2_status=_mesh_level_status(mesh_levels, 2) if 2 in seq else "NOT_REACHED",
        mesh_n4_status=_mesh_level_status(mesh_levels, 4) if 4 in seq else "NOT_REACHED",
        mesh_convergence_n1_n2_n4=mesh_conv,
        accepted_subdivisions_per_interval=str(outcome.accepted_subdivisions_per_interval),
        total_duty_w=str(outcome.total_duty_w),
        target_duty_w=str(target_duty_w),
        duty_vs_target=duty_class,
        tube_outlet_temperature_k=str(outcome.tube_outlet_temperature_k),
        shell_outlet_temperature_k=str(outcome.shell_outlet_temperature_k),
        energy_balance_residual_w=str(outcome.energy_balance_residual_w),
        energy_balance_status=ebal,
        rating_blocked_code=None,
        task173_diagnostics=(),
        task173_result_hash=outcome.result_hash,
    )


def run_v08_thermal_rating(
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    *,
    discrete_space_path: Path | None = None,
    max_valid_geometry: int = 32,
    min_accepted_distinct_geometries: int = 2,
    acceptance_task_id: V08ThermalRatingTaskId = "V08_03_LIVE_RATING_ACCEPTANCE_CLOSEOUT",
    provider: PropertyProvider | None = None,
) -> V08ThermalRatingResult:
    """Search structural geometry and require ``min_accepted_distinct_geometries`` successful Task173 ratings."""
    active = provider or CoolPropProvider()
    target = normalized.target_duty_w

    def _blocked_early(
        reason: V08ThermalRatingBlockedReason,
        *,
        csh: str | None = None,
        t168h: str | None = None,
    ) -> V08ThermalRatingResult:
        return V08ThermalRatingResult(
            task_id=acceptance_task_id,
            status="BLOCKED",
            blocked_reason=reason,
            engineering_acceptance="BLOCKED",
            engineering_acceptance_blockers=(f"EARLY_BLOCK:{reason}",),
            distinct_structural_geometries_attempted=0,
            distinct_fully_converged_rating_count=0,
            model_blockers=(),
            candidate_space_hash=csh,
            task168_request_hash=t168h,
            normalized_input_hash=handoff.normalized_input_hash,
            downstream_readiness=handoff.downstream_readiness,
            target_duty_w=str(target),
            candidates_rated=(),
            warnings=handoff.warnings,
        )

    if (
        handoff.downstream_readiness != "THERMAL_HYDRAULIC_PARAMETERS_READY"
        or handoff.thermal_binding is None
    ):
        return _blocked_early("MODEL_BLOCKED_THERMAL_BINDING")

    try:
        space = load_v08_discrete_space(discrete_space_path)
    except (FileNotFoundError, ValueError, KeyError):
        return _blocked_early("NO_STRUCTURAL_GEOMETRY")

    filtered, envelope_msgs = filter_discrete_space_by_envelope(space, normalized.design_envelope)
    if not filtered.shell_inside_diameters_m or not filtered.tube_baffle_ladder:
        return _blocked_early("NO_STRUCTURAL_GEOMETRY")

    try:
        t168 = build_v08_task168_request(normalized, handoff, filtered)
    except V08GeometryGenerationBlocked:
        return _blocked_early("NO_STRUCTURAL_GEOMETRY")
    except ValueError:
        return _blocked_early("NO_STRUCTURAL_GEOMETRY")

    task168_digest = task168_request_hash_digest(t168)
    enum = enumerate_structural_geometry(
        t168,
        filtered,
        envelope_msgs,
        max_valid_candidates=max_valid_geometry,
    )
    if not enum.valid_structural:
        return _blocked_early(
            "NO_STRUCTURAL_GEOMETRY",
            csh=enum.space_hash,
            t168h=task168_digest,
        )

    geom_by_candidate: dict[str, str] = {
        row.candidate_id: row.geometry_projection_hash for row in enum.candidate_records
    }

    attempt_rows: list[V08ThermalCandidateRatingRow] = []
    success_hashes: set[str] = set()
    model_blockers: list[str] = []

    for item in enum.valid_structural:
        base_row = _rate_one_structural_bundle(
            item,
            space_hash=enum.space_hash,
            target_duty_w=target,
            normalized=normalized,
            provider=active,
            handoff=handoff,
        )
        ghash = geom_by_candidate.get(base_row.candidate_id, "")
        row = V08ThermalCandidateRatingRow(
            candidate_id=base_row.candidate_id,
            candidate_hash=base_row.candidate_hash,
            geometry_projection_hash=ghash,
            task174_status=base_row.task174_status,
            task171_result_hash=base_row.task171_result_hash,
            task174_result_hash=base_row.task174_result_hash,
            rating_request_hash=base_row.rating_request_hash,
            rating_request_replay_ok=base_row.rating_request_replay_ok,
            rating_outcome=base_row.rating_outcome,
            mesh_n1_status=base_row.mesh_n1_status,
            mesh_n2_status=base_row.mesh_n2_status,
            mesh_n4_status=base_row.mesh_n4_status,
            mesh_convergence_n1_n2_n4=base_row.mesh_convergence_n1_n2_n4,
            accepted_subdivisions_per_interval=base_row.accepted_subdivisions_per_interval,
            total_duty_w=base_row.total_duty_w,
            target_duty_w=base_row.target_duty_w,
            duty_vs_target=base_row.duty_vs_target,
            tube_outlet_temperature_k=base_row.tube_outlet_temperature_k,
            shell_outlet_temperature_k=base_row.shell_outlet_temperature_k,
            energy_balance_residual_w=base_row.energy_balance_residual_w,
            energy_balance_status=base_row.energy_balance_status,
            rating_blocked_code=base_row.rating_blocked_code,
            task173_diagnostics=base_row.task173_diagnostics,
            task173_result_hash=base_row.task173_result_hash,
        )
        attempt_rows.append(row)

        if row.rating_outcome == "RATING_SUCCESS":
            if row.rating_request_replay_ok is not True:
                model_blockers.append("BLOCKED_RATING_REQUEST_HASH_MISMATCH")
            if row.mesh_convergence_n1_n2_n4 != "PASS":
                model_blockers.append("BLOCKED_MESH_N1_N2_N4_CONVERGENCE")
            if row.energy_balance_status != "PASS":
                model_blockers.append("BLOCKED_ENERGY_BALANCE_ACCEPTANCE")
            if (
                row.rating_request_replay_ok is True
                and row.mesh_convergence_n1_n2_n4 == "PASS"
                and row.energy_balance_status == "PASS"
                and ghash
                and ghash not in success_hashes
            ):
                success_hashes.add(ghash)
        elif row.rating_outcome == "RATING_BLOCKED" and row.rating_blocked_code:
            model_blockers.append(row.rating_blocked_code)
        elif row.rating_outcome == "TASK174_BLOCKED":
            model_blockers.append("TASK174_BLOCKED")

        if len(success_hashes) >= min_accepted_distinct_geometries:
            break

    distinct_attempted = len(
        {r.geometry_projection_hash for r in attempt_rows if r.geometry_projection_hash}
    )
    distinct_converged = len(success_hashes)

    eng_blockers: list[str] = []
    if any(r.task174_status == "BLOCKED" for r in attempt_rows):
        overall: Literal["OK", "BLOCKED", "PARTIAL"] = "BLOCKED"
        reason: V08ThermalRatingBlockedReason | None = "TASK174_BLOCKED"
        eng_accept: EngineeringAcceptance = "BLOCKED"
        eng_blockers.append("TASK174_BLOCKED")
    elif distinct_converged < min_accepted_distinct_geometries:
        overall = "BLOCKED"
        reason = "ENGINEERING_ACCEPTANCE_RATING"
        eng_accept = "BLOCKED"
        eng_blockers.append(
            f"INSUFFICIENT_DISTINCT_SUCCESSFUL_RATINGS:{distinct_converged}/{min_accepted_distinct_geometries}"
        )
        eng_blockers.extend(sorted(frozenset(model_blockers)))
    elif all(
        r.duty_vs_target == "AT_OR_ABOVE_TARGET"
        for r in attempt_rows
        if r.rating_outcome == "RATING_SUCCESS" and r.geometry_projection_hash in success_hashes
    ):
        overall = "OK"
        reason = None
        eng_accept = "PASS"
    else:
        overall = "PARTIAL"
        reason = None
        eng_accept = "PASS"

    return V08ThermalRatingResult(
        task_id=acceptance_task_id,
        status=overall,
        blocked_reason=reason,
        engineering_acceptance=eng_accept,
        engineering_acceptance_blockers=tuple(eng_blockers),
        distinct_structural_geometries_attempted=distinct_attempted,
        distinct_fully_converged_rating_count=distinct_converged,
        model_blockers=tuple(sorted(frozenset(model_blockers))),
        candidate_space_hash=enum.space_hash,
        task168_request_hash=task168_digest,
        normalized_input_hash=handoff.normalized_input_hash,
        downstream_readiness=handoff.downstream_readiness,
        target_duty_w=str(target),
        candidates_rated=tuple(attempt_rows),
        warnings=handoff.warnings,
    )
