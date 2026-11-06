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
from hexagent.exchangers.shell_tube.task173_integrated_rating.candidate_models import (
    CandidateRatingSuccessResult,
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

V08ThermalRatingTaskId = Literal["V08_03_LIVE_THERMAL_RATING"]

V08ThermalRatingBlockedReason = Literal[
    "MODEL_BLOCKED_THERMAL_BINDING",
    "NO_STRUCTURAL_GEOMETRY",
    "TASK174_BLOCKED",
    "TASK173_BLOCKED",
]

MeshNStatus = Literal["NOT_REACHED", "NUMERIC_VALID", "OTHER"]


@dataclass(frozen=True)
class V08ThermalCandidateRatingRow:
    """One structurally admitted V08 geometry row with optional mesh rating outcome."""

    candidate_id: str
    geometry_projection_hash: str
    task174_status: str
    rating_request_hash: str | None
    mesh_n1_status: MeshNStatus
    mesh_n2_status: MeshNStatus
    mesh_n4_status: MeshNStatus
    total_duty_w: str | None
    target_duty_w: str
    duty_vs_target: Literal["AT_OR_ABOVE_TARGET", "BELOW_TARGET"] | None
    energy_balance_residual_w: str | None
    rating_blocked_code: str | None
    task173_result_hash: str | None


@dataclass(frozen=True)
class V08ThermalRatingResult:
    task_id: V08ThermalRatingTaskId
    status: Literal["OK", "BLOCKED", "PARTIAL"]
    blocked_reason: V08ThermalRatingBlockedReason | None
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


def _duty_vs_target(
    total_duty_w: Decimal, target_duty_w: Decimal
) -> Literal["AT_OR_ABOVE_TARGET", "BELOW_TARGET"]:
    """Classify rated duty vs user target using the same envelope factor as V08 feasibility."""
    if total_duty_w * THERMODYNAMIC_DUTY_TOLERANCE >= target_duty_w:
        return "AT_OR_ABOVE_TARGET"
    return "BELOW_TARGET"


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
            geometry_projection_hash="",
            task174_status="BLOCKED",
            rating_request_hash=None,
            mesh_n1_status="NOT_REACHED",
            mesh_n2_status="NOT_REACHED",
            mesh_n4_status="NOT_REACHED",
            total_duty_w=None,
            target_duty_w=str(target_duty_w),
            duty_vs_target=None,
            energy_balance_residual_w=None,
            rating_blocked_code=None,
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
    from hexagent.exchangers.shell_tube.task173_integrated_rating.candidate_models import (
        candidate_rating_request_hash,
    )

    rhash = candidate_rating_request_hash(rating_req)
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
            geometry_projection_hash="",
            task174_status="VALIDATED",
            rating_request_hash=rhash,
            mesh_n1_status="NOT_REACHED",
            mesh_n2_status="NOT_REACHED",
            mesh_n4_status="NOT_REACHED",
            total_duty_w=None,
            target_duty_w=str(target_duty_w),
            duty_vs_target=None,
            energy_balance_residual_w=None,
            rating_blocked_code=outcome.failure_code,
            task173_result_hash=outcome.result_hash,
        )
    assert type(outcome) is CandidateRatingSuccessResult
    mesh_levels = outcome.mesh_levels
    duty_class = _duty_vs_target(outcome.total_duty_w, target_duty_w)
    seq = REVIEWED_MESH_SEQUENCE
    return V08ThermalCandidateRatingRow(
        candidate_id=candidate.candidate_id,
        geometry_projection_hash="",
        task174_status="VALIDATED",
        rating_request_hash=rhash,
        mesh_n1_status=_mesh_level_status(mesh_levels, 1) if 1 in seq else "NOT_REACHED",
        mesh_n2_status=_mesh_level_status(mesh_levels, 2) if 2 in seq else "NOT_REACHED",
        mesh_n4_status=_mesh_level_status(mesh_levels, 4) if 4 in seq else "NOT_REACHED",
        total_duty_w=str(outcome.total_duty_w),
        target_duty_w=str(target_duty_w),
        duty_vs_target=duty_class,
        energy_balance_residual_w=str(outcome.energy_balance_residual_w),
        rating_blocked_code=None,
        task173_result_hash=outcome.result_hash,
    )


def run_v08_thermal_rating(
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    *,
    discrete_space_path: Path | None = None,
    max_valid_geometry: int = 4,
    provider: PropertyProvider | None = None,
) -> V08ThermalRatingResult:
    """Run Task173 production mesh sequence on V08 structural candidates when thermal binding is ready."""
    active = provider or CoolPropProvider()
    target = normalized.target_duty_w

    if (
        handoff.downstream_readiness != "THERMAL_HYDRAULIC_PARAMETERS_READY"
        or handoff.thermal_binding is None
    ):
        return V08ThermalRatingResult(
            task_id="V08_03_LIVE_THERMAL_RATING",
            status="BLOCKED",
            blocked_reason="MODEL_BLOCKED_THERMAL_BINDING",
            candidate_space_hash=None,
            task168_request_hash=None,
            normalized_input_hash=handoff.normalized_input_hash,
            downstream_readiness=handoff.downstream_readiness,
            target_duty_w=str(target),
            candidates_rated=(),
            warnings=handoff.warnings,
        )

    try:
        space = load_v08_discrete_space(discrete_space_path)
    except (FileNotFoundError, ValueError, KeyError):
        return V08ThermalRatingResult(
            task_id="V08_03_LIVE_THERMAL_RATING",
            status="BLOCKED",
            blocked_reason="NO_STRUCTURAL_GEOMETRY",
            candidate_space_hash=None,
            task168_request_hash=None,
            normalized_input_hash=handoff.normalized_input_hash,
            downstream_readiness=handoff.downstream_readiness,
            target_duty_w=str(target),
            candidates_rated=(),
            warnings=handoff.warnings,
        )
    filtered, envelope_msgs = filter_discrete_space_by_envelope(space, normalized.design_envelope)
    if not filtered.shell_inside_diameters_m or not filtered.tube_baffle_ladder:
        return V08ThermalRatingResult(
            task_id="V08_03_LIVE_THERMAL_RATING",
            status="BLOCKED",
            blocked_reason="NO_STRUCTURAL_GEOMETRY",
            candidate_space_hash=None,
            task168_request_hash=None,
            normalized_input_hash=handoff.normalized_input_hash,
            downstream_readiness=handoff.downstream_readiness,
            target_duty_w=str(target),
            candidates_rated=(),
            warnings=handoff.warnings,
        )

    try:
        t168 = build_v08_task168_request(normalized, handoff, filtered)
    except V08GeometryGenerationBlocked:
        return V08ThermalRatingResult(
            task_id="V08_03_LIVE_THERMAL_RATING",
            status="BLOCKED",
            blocked_reason="NO_STRUCTURAL_GEOMETRY",
            candidate_space_hash=None,
            task168_request_hash=None,
            normalized_input_hash=handoff.normalized_input_hash,
            downstream_readiness=handoff.downstream_readiness,
            target_duty_w=str(target),
            candidates_rated=(),
            warnings=handoff.warnings,
        )
    except ValueError:
        return V08ThermalRatingResult(
            task_id="V08_03_LIVE_THERMAL_RATING",
            status="BLOCKED",
            blocked_reason="NO_STRUCTURAL_GEOMETRY",
            candidate_space_hash=None,
            task168_request_hash=None,
            normalized_input_hash=handoff.normalized_input_hash,
            downstream_readiness=handoff.downstream_readiness,
            target_duty_w=str(target),
            candidates_rated=(),
            warnings=handoff.warnings,
        )
    task168_digest = task168_request_hash_digest(t168)
    enum = enumerate_structural_geometry(
        t168,
        filtered,
        envelope_msgs,
        max_valid_candidates=max_valid_geometry,
    )
    if not enum.valid_structural:
        return V08ThermalRatingResult(
            task_id="V08_03_LIVE_THERMAL_RATING",
            status="BLOCKED",
            blocked_reason="NO_STRUCTURAL_GEOMETRY",
            candidate_space_hash=enum.space_hash,
            task168_request_hash=task168_digest,
            normalized_input_hash=handoff.normalized_input_hash,
            downstream_readiness=handoff.downstream_readiness,
            target_duty_w=str(target),
            candidates_rated=(),
            warnings=handoff.warnings,
        )

    geom_by_candidate: dict[str, str] = {
        row.candidate_id: row.geometry_projection_hash for row in enum.candidate_records
    }

    rows: list[V08ThermalCandidateRatingRow] = []
    for item in enum.valid_structural:
        row = _rate_one_structural_bundle(
            item,
            space_hash=enum.space_hash,
            target_duty_w=target,
            normalized=normalized,
            provider=active,
            handoff=handoff,
        )
        ghash = geom_by_candidate.get(row.candidate_id, "")
        rows.append(
            V08ThermalCandidateRatingRow(
                candidate_id=row.candidate_id,
                geometry_projection_hash=ghash,
                task174_status=row.task174_status,
                rating_request_hash=row.rating_request_hash,
                mesh_n1_status=row.mesh_n1_status,
                mesh_n2_status=row.mesh_n2_status,
                mesh_n4_status=row.mesh_n4_status,
                total_duty_w=row.total_duty_w,
                target_duty_w=row.target_duty_w,
                duty_vs_target=row.duty_vs_target,
                energy_balance_residual_w=row.energy_balance_residual_w,
                rating_blocked_code=row.rating_blocked_code,
                task173_result_hash=row.task173_result_hash,
            )
        )

    if any(r.task174_status == "BLOCKED" for r in rows):
        overall: Literal["OK", "BLOCKED", "PARTIAL"] = "BLOCKED"
        reason: V08ThermalRatingBlockedReason | None = "TASK174_BLOCKED"
    elif any(r.rating_blocked_code is not None for r in rows):
        overall = "BLOCKED"
        reason = "TASK173_BLOCKED"
    elif all(r.total_duty_w is not None and r.duty_vs_target == "AT_OR_ABOVE_TARGET" for r in rows):
        overall = "OK"
        reason = None
    else:
        overall = "PARTIAL"
        reason = None

    return V08ThermalRatingResult(
        task_id="V08_03_LIVE_THERMAL_RATING",
        status=overall,
        blocked_reason=reason,
        candidate_space_hash=enum.space_hash,
        task168_request_hash=task168_digest,
        normalized_input_hash=handoff.normalized_input_hash,
        downstream_readiness=handoff.downstream_readiness,
        target_duty_w=str(target),
        candidates_rated=tuple(rows),
        warnings=handoff.warnings,
    )
