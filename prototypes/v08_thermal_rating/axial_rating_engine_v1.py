"""V08-03 isolated full-exchanger thermal path on production Task172/Task173 physics.

Uses the same geometry, CoolProp binding, and Task172 local correlations as production
``validate_candidate_rating``, but can evaluate a single outer shooting enthalpy trial
without claiming production C-ULP or VALIDATED status.

Primary case: HXFORGE_330KW_STRICT_DP. 250 kW fixture is regression-only (see tests).
"""

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
    CandidateRatingRequest,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating.experimental_thermal_boundary import (
    bind_experimental_thermal_boundary_v1,
    build_experimental_thermal_boundary_v1,
    reset_experimental_thermal_boundary,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating.models import (
    REVIEWED_MESH_SEQUENCE,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating.service import (
    _CANDIDATE_RATING_CONTEXT,
    ENERGY_ACCEPTANCE_FLOOR_W,
    _candidate_context,
    _CellSearchStats,
    _MeshRun,
    _outer_trial,
    _OuterTrial,
    effective_shell_cold_inlet_enthalpy_j_kg,
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
from prototypes.v08_general_user_case.loader import load_general_user_design_case_json
from prototypes.v08_general_user_case.physical_feasibility import THERMODYNAMIC_DUTY_TOLERANCE
from prototypes.v08_general_user_case.pipeline import validate_and_build_solver_handoff
from prototypes.v08_general_user_case.solver_handoff import V08SolverHandoffV1
from prototypes.v08_general_user_case.user_design_case import NormalizedUserDesignCase
from prototypes.v08_geometry_candidate_generation.discrete_space import (
    DEFAULT_V08_DISCRETE_SPACE_PATH,
    load_v08_discrete_space,
)
from prototypes.v08_geometry_candidate_generation.generator import enumerate_structural_geometry
from prototypes.v08_geometry_candidate_generation.structural_bundles import (
    V08StructuralGeometryBundle,
)
from prototypes.v08_geometry_candidate_generation.task168_builder import (
    build_v08_task168_request,
    filter_discrete_space_by_envelope,
)
from prototypes.v08_thermal_rating.case_identity_v08 import (
    CASE_250KW_ID,
    CASE_330KW_ID,
    FIXTURE_250,
    FIXTURE_330,
)
from prototypes.v08_thermal_rating.outer_shooting_isolated_v1 import (
    IsolatedOuterBoundaryResult,
    solve_outer_boundary_from_trial_isolated,
)
from prototypes.v08_thermal_rating.pipeline import (
    V08ThermalCandidateRatingRow,
    _rate_one_structural_bundle,
)

DeliveryOutcome = Literal["A", "B"]
PhysicalN1Status = Literal["CLOSED", "BLOCKED", "NOT_RUN"]
ProductionRatingOutcome = Literal[
    "RATING_SUCCESS", "RATING_BLOCKED", "TASK174_BLOCKED", "NOT_ATTEMPTED"
]


@dataclass(frozen=True)
class CandidateRatingBindings:
    """Everything required to run production physics for one structural bundle."""

    bundle: V08StructuralGeometryBundle
    space_hash: str
    normalized: NormalizedUserDesignCase
    handoff: V08SolverHandoffV1
    rating_request: CandidateRatingRequest
    engineering_case_id: str
    target_duty_w: Decimal
    geometry_projection_hash: str


@dataclass(frozen=True)
class IsolatedMeshTrialReport:
    subdivisions: int
    classification: str
    shooting_enthalpy_j_kg: str | None
    total_duty_w: str | None
    energy_balance_residual_w: str | None
    terminal_boundary_residual_k: str | None
    terminal_boundary_residual_j_kg: str | None
    tube_outlet_temperature_k: str | None
    shell_outlet_temperature_k: str | None
    task172_numerical_hole_count: int
    diagnostics: tuple[str, ...]


@dataclass(frozen=True)
class PhysicalClosureReport:
    """Physics-layer N1 assessment (not production VALIDATED)."""

    case_id: str
    candidate_id: str
    n1_status: PhysicalN1Status
    best_shooting_enthalpy_j_kg: str | None
    total_duty_w: str | None
    target_duty_w: str
    duty_vs_target: Literal["AT_OR_ABOVE_TARGET", "BELOW_TARGET", "UNKNOWN"]
    energy_balance_residual_w: str | None
    energy_balance_pass: bool | None
    terminal_boundary_residual_k: str | None
    terminal_within_production_tolerance: bool | None
    task172_numerical_hole_count: int
    geometry_projection_hash: str
    geometry_duty_insufficient: bool
    isolated_n2_n4_fixed_enthalpy: tuple[IsolatedMeshTrialReport, ...]
    outer_solve_by_mesh: tuple[IsolatedOuterBoundaryResult, ...]
    first_blocker: str
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class ProductionCulpReport:
    """Production Task173 rating + C-ULP mesh gate (unchanged tolerances)."""

    case_id: str
    candidate_id: str
    outcome: ProductionRatingOutcome
    failure_code: str | None
    mesh_n1_status: str
    mesh_n2_status: str
    mesh_n4_status: str
    engineering_validated: Literal[False]
    row: V08ThermalCandidateRatingRow | None


@dataclass(frozen=True)
class AxialRatingCandidateCloseout:
    engineering_case_id: str
    candidate_id: str
    physical: PhysicalClosureReport
    production: ProductionCulpReport
    delivery: DeliveryOutcome
    delivery_rationale: tuple[str, ...]


@dataclass(frozen=True)
class AxialRatingCaseCloseout:
    primary_case_id: str
    fixture_path: str
    normalized_input_hash: str
    task168_request_hash: str
    candidates: tuple[AxialRatingCandidateCloseout, ...]
    aggregate_delivery: DeliveryOutcome


def load_case_bindings(
    fixture_path: Path,
    *,
    provider: PropertyProvider | None = None,
) -> tuple[NormalizedUserDesignCase, V08SolverHandoffV1, PropertyProvider]:
    active = provider or CoolPropProvider()
    case = load_general_user_design_case_json(fixture_path.read_text(encoding="utf-8"))
    pipeline = validate_and_build_solver_handoff(case, provider=active)
    if pipeline.handoff.thermal_binding is None:
        raise RuntimeError("thermal_binding required for V08 axial rating engine")
    return pipeline.normalized, pipeline.handoff, active


def enumerate_structural_bundles(
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    *,
    max_valid: int = 32,
) -> tuple[str, str, tuple[V08StructuralGeometryBundle, ...], dict[str, str]]:
    space = load_v08_discrete_space(DEFAULT_V08_DISCRETE_SPACE_PATH)
    filtered, _ = filter_discrete_space_by_envelope(space, normalized.design_envelope)
    t168 = build_v08_task168_request(normalized, handoff, filtered)
    t168_digest = task168_request_hash_digest(t168)
    enum = enumerate_structural_geometry(t168, filtered, (), max_valid_candidates=max_valid)
    geom_by_id = {row.candidate_id: row.geometry_projection_hash for row in enum.candidate_records}
    return enum.space_hash, t168_digest, enum.valid_structural, geom_by_id


def build_candidate_rating_bindings(
    bundle: V08StructuralGeometryBundle,
    *,
    space_hash: str,
    t168_digest: str,
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    provider: PropertyProvider,
    geometry_projection_hash: str = "",
) -> CandidateRatingBindings | None:
    candidate = bundle.candidate
    b = bundle.bundle
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
        return None
    rating_req = v08_thermal_rating_request(candidate, space_hash, b, topology, t174, t168_digest)
    return CandidateRatingBindings(
        bundle=bundle,
        space_hash=space_hash,
        normalized=normalized,
        handoff=handoff,
        rating_request=rating_req,
        engineering_case_id=normalized.engineering_case_id,
        target_duty_w=normalized.target_duty_w,
        geometry_projection_hash=geometry_projection_hash,
    )


def _run_with_rating_context(
    bindings: CandidateRatingBindings,
    provider: PropertyProvider,
    *,
    subdivisions: int,
    body: Any,
) -> Any:
    btoken = _thermal_boundary_token(bindings.normalized, provider)
    context = _candidate_context(bindings.rating_request)
    ctx_token = _CANDIDATE_RATING_CONTEXT.set(context)
    try:
        return body(context, btoken)
    finally:
        _CANDIDATE_RATING_CONTEXT.reset(ctx_token)
        reset_experimental_thermal_boundary(btoken)


def solve_isolated_outer_boundary(
    bindings: CandidateRatingBindings,
    provider: PropertyProvider,
    *,
    subdivisions: int,
) -> IsolatedOuterBoundaryResult:
    """Independent outer shooting solve for one mesh level (production-parallel)."""

    def body(context: Any, _btoken: object) -> IsolatedOuterBoundaryResult:
        stats = _CellSearchStats()

        def trial_at(enthalpy: Decimal, iteration: int) -> _OuterTrial:
            return _outer_trial(
                subdivisions,
                enthalpy,
                provider,
                context.shell_authority,
                iteration,
                stats,
            )

        return solve_outer_boundary_from_trial_isolated(
            trial_at,
            subdivisions=subdivisions,
            provider=provider,
            stats=stats,
        )

    return _run_with_rating_context(bindings, provider, subdivisions=subdivisions, body=body)


def _legacy_wrong_shooting_search(
    bindings: CandidateRatingBindings,
    provider: PropertyProvider,
    *,
    subdivisions: int = 1,
) -> tuple[str | None, str | None]:
    """Pre-correction mistake: VALID_TRAJECTORY updated h_lo (diagnostic baseline only)."""

    def body(context: Any, _btoken: object) -> tuple[str | None, str | None]:
        from hexagent.exchangers.shell_tube.task173_integrated_rating.service import (
            effective_admitted_h_max_j_kg,
        )

        h_lo = float(effective_shell_cold_inlet_enthalpy_j_kg())
        h_hi = float(effective_admitted_h_max_j_kg(provider))
        best_term: str | None = None
        best_duty: str | None = None
        for _ in range(16):
            h_mid = (h_lo + h_hi) / 2.0
            stats = _CellSearchStats()
            trial = _outer_trial(
                subdivisions,
                Decimal(str(h_mid)),
                provider,
                context.shell_authority,
                0,
                stats,
            )
            if trial.classification == "VALID_TRAJECTORY" and trial.mesh_run is not None:
                h_lo = h_mid
                obs = trial.mesh_run.observables
                best_term = str(obs.terminal_boundary_residual_k)
                best_duty = str(obs.total_duty_w)
            elif trial.classification == "LOW_SIDE_DOMAIN_INFEASIBLE":
                h_lo = h_mid
            else:
                h_hi = h_mid
            if abs(h_lo - h_hi) < 1e-6:
                break
        return best_term, best_duty

    return _run_with_rating_context(bindings, provider, subdivisions=subdivisions, body=body)


def _search_valid_shooting_enthalpy(
    bindings: CandidateRatingBindings,
    provider: PropertyProvider,
    *,
    subdivisions: int = 1,
) -> IsolatedOuterBoundaryResult:
    """Corrected outer search (replaces mistaken admitted-max / h_lo-on-VALID bisection)."""
    return solve_isolated_outer_boundary(bindings, provider, subdivisions=subdivisions)


def _mesh_run_summary(run: _MeshRun | None) -> tuple[str | None, ...]:
    if run is None:
        return None, None, None, None, None
    o = run.observables
    return (
        str(o.terminal_boundary_residual_k),
        str(o.terminal_boundary_residual_j_kg),
        str(o.total_duty_w),
        str(o.tube_outlet_temperature_k),
        str(o.shell_outlet_temperature_k),
    )


def _thermal_boundary_token(
    normalized: NormalizedUserDesignCase,
    provider: PropertyProvider,
) -> object:
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
    return bind_experimental_thermal_boundary_v1(exp)


def _trial_report(
    subdivisions: int,
    trial: _OuterTrial,
    stats: _CellSearchStats,
    *,
    shooting_h: Decimal | None,
) -> IsolatedMeshTrialReport:
    obs = trial.mesh_run.observables if trial.mesh_run is not None else None
    return IsolatedMeshTrialReport(
        subdivisions=subdivisions,
        classification=trial.classification,
        shooting_enthalpy_j_kg=str(shooting_h) if shooting_h is not None else None,
        total_duty_w=str(obs.total_duty_w) if obs is not None else None,
        energy_balance_residual_w=str(obs.energy_balance_residual_w) if obs is not None else None,
        terminal_boundary_residual_k=str(obs.terminal_boundary_residual_k)
        if obs is not None
        else None,
        terminal_boundary_residual_j_kg=(
            str(obs.terminal_boundary_residual_j_kg) if obs is not None else None
        ),
        tube_outlet_temperature_k=str(obs.tube_outlet_temperature_k) if obs is not None else None,
        shell_outlet_temperature_k=str(obs.shell_outlet_temperature_k) if obs is not None else None,
        task172_numerical_hole_count=stats.task172_numerical_hole_count,
        diagnostics=tuple(trial.diagnostics),
    )


def _duty_vs_target(
    duty: Decimal | None, target: Decimal
) -> Literal["AT_OR_ABOVE_TARGET", "BELOW_TARGET", "UNKNOWN"]:
    if duty is None:
        return "UNKNOWN"
    if duty * THERMODYNAMIC_DUTY_TOLERANCE >= target:
        return "AT_OR_ABOVE_TARGET"
    return "BELOW_TARGET"


def final_trajectory_task172_holes(
    bindings: CandidateRatingBindings,
    provider: PropertyProvider,
    *,
    subdivisions: int,
    shooting_enthalpy_j_kg: Decimal | str,
) -> int:
    """Task172 hole count on one final accepted shooting enthalpy (not outer-search cumulative)."""

    def body(context: Any, _btoken: object) -> int:
        stats = _CellSearchStats()
        _outer_trial(
            subdivisions,
            Decimal(str(shooting_enthalpy_j_kg)),
            provider,
            context.shell_authority,
            0,
            stats,
        )
        return stats.task172_numerical_hole_count

    return int(_run_with_rating_context(bindings, provider, subdivisions=subdivisions, body=body))


def run_isolated_outer_trials(
    bindings: CandidateRatingBindings,
    provider: PropertyProvider,
    *,
    subdivisions: int,
    shooting_enthalpy_j_kg: Decimal,
) -> IsolatedMeshTrialReport:
    """One production-physics axial march at fixed shell-outlet shooting enthalpy."""
    btoken = _thermal_boundary_token(bindings.normalized, provider)
    context = _candidate_context(bindings.rating_request)
    ctx_token = _CANDIDATE_RATING_CONTEXT.set(context)
    stats = _CellSearchStats()
    try:
        trial = _outer_trial(
            subdivisions,
            shooting_enthalpy_j_kg,
            provider,
            context.shell_authority,
            0,
            stats,
        )
        return _trial_report(subdivisions, trial, stats, shooting_h=shooting_enthalpy_j_kg)
    finally:
        _CANDIDATE_RATING_CONTEXT.reset(ctx_token)
        reset_experimental_thermal_boundary(btoken)


def production_terminal_tolerance_pass(run: _MeshRun | None) -> bool:
    """Authoritative terminal gate — production ``_terminal_tolerance_pass`` only."""
    from hexagent.exchangers.shell_tube.task173_integrated_rating.service import (
        _terminal_tolerance_pass,
    )

    return run is not None and _terminal_tolerance_pass(run)


def isolated_mesh_acceptance_gate(
    bindings: CandidateRatingBindings,
    provider: PropertyProvider,
    result: IsolatedOuterBoundaryResult,
) -> Literal["ACCEPTED", "BLOCKED"]:
    """Experimental mesh gate: outer ACCEPTED + accepted_run only (never best_valid_run)."""
    if result.status != "ACCEPTED" or result.accepted_run is None:
        return "BLOCKED"
    run = result.accepted_run
    if not production_terminal_tolerance_pass(run):
        return "BLOCKED"
    if abs(run.observables.energy_balance_residual_w) > ENERGY_ACCEPTANCE_FLOOR_W:
        return "BLOCKED"
    holes = (
        final_trajectory_task172_holes(
            bindings,
            provider,
            subdivisions=result.subdivisions,
            shooting_enthalpy_j_kg=result.shooting_enthalpy_j_kg,
        )
        if result.shooting_enthalpy_j_kg
        else result.stats.task172_numerical_hole_count
    )
    if holes != 0:
        return "BLOCKED"
    return "ACCEPTED"


def target_330kw_met_label(
    mesh_gate: Literal["ACCEPTED", "BLOCKED"],
    run: _MeshRun | None,
    target_duty_w: Decimal,
) -> Literal["true", "false", "unresolved"]:
    if mesh_gate != "ACCEPTED" or run is None:
        return "unresolved"
    if run.observables.total_duty_w * THERMODYNAMIC_DUTY_TOLERANCE >= target_duty_w:
        return "true"
    return "false"


@dataclass(frozen=True)
class N1VerificationReport:
    N1_OUTER_STATUS: str
    N1_TERMINAL_RESIDUAL_K: str | None
    N1_TERMINAL_RESIDUAL_J_KG: str | None
    N1_TERMINAL_TOLERANCE_PASS: bool
    N1_TOTAL_DUTY_W: str | None
    N1_ENERGY_RESIDUAL_W: str | None
    N1_TASK172_HOLES: int
    N1_ACCEPTED_RUN_HASH: str | None
    N1_TERMINAL_GATE: Literal["PASS", "BLOCKED"]
    outer_search_trace_tail: tuple[str, ...]


def verify_n1_terminal(
    bindings: CandidateRatingBindings,
    provider: PropertyProvider,
    *,
    n1: IsolatedOuterBoundaryResult | None = None,
) -> N1VerificationReport:
    n1 = n1 or solve_isolated_outer_boundary(bindings, provider, subdivisions=1)
    audit_run = n1.accepted_run or n1.best_valid_run
    term_pass = production_terminal_tolerance_pass(audit_run)
    holes = (
        final_trajectory_task172_holes(
            bindings,
            provider,
            subdivisions=1,
            shooting_enthalpy_j_kg=n1.shooting_enthalpy_j_kg,
        )
        if n1.shooting_enthalpy_j_kg
        else n1.stats.task172_numerical_hole_count
    )
    obs = audit_run.observables if audit_run is not None else None
    trace_tail = tuple(
        f"iter={s.iteration}:decision={s.decision_update}:term_pass={s.terminal_tolerance_pass}"
        for s in n1.search_trace[-6:]
    )
    return N1VerificationReport(
        N1_OUTER_STATUS=n1.status,
        N1_TERMINAL_RESIDUAL_K=str(obs.terminal_boundary_residual_k) if obs else None,
        N1_TERMINAL_RESIDUAL_J_KG=str(obs.terminal_boundary_residual_j_kg) if obs else None,
        N1_TERMINAL_TOLERANCE_PASS=term_pass,
        N1_TOTAL_DUTY_W=str(obs.total_duty_w) if obs else None,
        N1_ENERGY_RESIDUAL_W=str(obs.energy_balance_residual_w) if obs else None,
        N1_TASK172_HOLES=holes,
        N1_ACCEPTED_RUN_HASH=(
            n1.accepted_run.mesh_result_hash
            if n1.status == "ACCEPTED" and n1.accepted_run is not None
            else None
        ),
        N1_TERMINAL_GATE="PASS"
        if isolated_mesh_acceptance_gate(bindings, provider, n1) == "ACCEPTED"
        else "BLOCKED",
        outer_search_trace_tail=trace_tail,
    )


@dataclass(frozen=True)
class CandidateMeshCloseout:
    candidate_id: str
    geometry_projection_hash: str
    n1: Literal["ACCEPTED", "BLOCKED"]
    n2: Literal["ACCEPTED", "BLOCKED", "not_run"]
    n4: Literal["ACCEPTED", "BLOCKED", "not_run"]
    n1_verification: N1VerificationReport
    target_330kw_met: Literal["true", "false", "unresolved"]
    tube_dp_pa: str
    shell_dp_pa: str
    tube_dp_pass: bool
    shell_dp_pass: bool
    hydraulic_pass: bool
    nozzle_velocities: str
    thermal_hydraulic_class: str
    production_task173_gate: str | None
    production_mesh_n1: str | None
    production_mesh_n2: str | None
    production_mesh_n4: str | None
    n1_diagnostic: Any | None = None
    n2_diagnostic: Any | None = None
    n4_diagnostic: Any | None = None
    experimental_mesh_gates_accepted: bool = False
    experimental_mesh_convergence_pass: Literal["PASS", "BLOCKED", "not_run"] = "not_run"
    production_rating_validated: bool = False
    engineering_fully_accepted: bool = False


def resolve_candidate_bindings_by_id(
    candidate_id: str,
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    provider: PropertyProvider,
    *,
    max_valid: int = 64,
) -> CandidateRatingBindings | None:
    space_hash, t168_digest, bundles, geom = enumerate_structural_bundles(
        normalized, handoff, max_valid=max_valid
    )
    for bundle in bundles:
        if bundle.candidate.candidate_id != candidate_id:
            continue
        return build_candidate_rating_bindings(
            bundle,
            space_hash=space_hash,
            t168_digest=t168_digest,
            normalized=normalized,
            handoff=handoff,
            provider=provider,
            geometry_projection_hash=geom.get(bundle.candidate.candidate_id, ""),
        )
    return None


def run_candidate_mesh_closeout(
    bindings: CandidateRatingBindings,
    provider: PropertyProvider,
    *,
    run_production_gate: bool = True,
) -> CandidateMeshCloseout:
    from prototypes.v08_thermal_rating.mesh_level_diagnostics_v08 import (
        build_mesh_level_diagnostic,
        experimental_mesh_convergence_pass,
    )

    n1 = solve_isolated_outer_boundary(bindings, provider, subdivisions=1)
    n1_gate = isolated_mesh_acceptance_gate(bindings, provider, n1)
    n1_v = verify_n1_terminal(bindings, provider, n1=n1)
    n1_diag = build_mesh_level_diagnostic(bindings, provider, n1)

    def _solve_mesh(subdivisions: int) -> tuple[Literal["ACCEPTED", "BLOCKED", "not_run"], Any]:
        if n1_gate != "ACCEPTED":
            return "not_run", None
        out = solve_isolated_outer_boundary(bindings, provider, subdivisions=subdivisions)
        gate = isolated_mesh_acceptance_gate(bindings, provider, out)
        return gate, build_mesh_level_diagnostic(bindings, provider, out)

    n2_gate, n2_diag = _solve_mesh(2)
    n4_gate, n4_diag = _solve_mesh(4)

    mesh_conv: Literal["PASS", "BLOCKED", "not_run"] = "not_run"
    if n1_diag and n2_diag and n4_diag:
        ok, _notes = experimental_mesh_convergence_pass(n1_diag, n2_diag, n4_diag)
        mesh_conv = "PASS" if ok else "BLOCKED"
    gates_all = n1_gate == "ACCEPTED" and n2_gate == "ACCEPTED" and n4_gate == "ACCEPTED"

    target_met = target_330kw_met_label(
        n1_gate, n1.accepted_run if n1_gate == "ACCEPTED" else None, bindings.target_duty_w
    )

    t174 = bindings.rating_request.task174_result
    tube_dp = str(t174.modeled_total_tube_side_pressure_drop_pa)
    shell_dp = str(t174.bell_total_shell_pressure_drop_pa)
    max_tube = bindings.normalized.max_tube_side_pressure_drop_pa
    max_shell = bindings.normalized.max_shell_side_pressure_drop_pa
    tube_ok = t174.modeled_total_tube_side_pressure_drop_pa <= max_tube
    shell_ok = t174.bell_total_shell_pressure_drop_pa <= max_shell
    dp_ok = tube_ok and shell_ok
    thermal_hydraulic = (
        "THERMAL_PASS_HYDRAULIC_BLOCKED"
        if n1_gate == "ACCEPTED" and not dp_ok
        else ("PASS" if n1_gate == "ACCEPTED" and dp_ok else "BLOCKED_OR_UNRESOLVED")
    )

    prod_gate: str | None = None
    prod_m1: str | None = None
    prod_m2: str | None = None
    prod_m4: str | None = None
    prod_validated = False
    if run_production_gate:
        prod = assess_production_culp_rating(bindings, provider)
        prod_gate = prod.failure_code or prod.outcome
        prod_m1 = prod.mesh_n1_status
        prod_m2 = prod.mesh_n2_status
        prod_m4 = prod.mesh_n4_status
        prod_validated = prod.outcome == "RATING_SUCCESS"

    return CandidateMeshCloseout(
        candidate_id=bindings.rating_request.candidate_id,
        geometry_projection_hash=bindings.geometry_projection_hash,
        n1=n1_gate,
        n2=n2_gate,
        n4=n4_gate,
        n1_verification=n1_v,
        target_330kw_met=target_met,
        tube_dp_pa=tube_dp,
        shell_dp_pa=shell_dp,
        tube_dp_pass=tube_ok,
        shell_dp_pass=shell_ok,
        hydraulic_pass=dp_ok,
        nozzle_velocities="unresolved: nozzle velocity not bound in Task174 fixed-geometry rating chain",
        thermal_hydraulic_class=thermal_hydraulic,
        production_task173_gate=prod_gate,
        production_mesh_n1=prod_m1,
        production_mesh_n2=prod_m2,
        production_mesh_n4=prod_m4,
        n1_diagnostic=n1_diag,
        n2_diagnostic=n2_diag,
        n4_diagnostic=n4_diag,
        experimental_mesh_gates_accepted=gates_all,
        experimental_mesh_convergence_pass=mesh_conv,
        production_rating_validated=prod_validated,
        engineering_fully_accepted=False,
    )


def experimental_mesh_converged(closeout: CandidateMeshCloseout) -> bool:
    """Isolated prototype N1/N2/N4 all ACCEPTED (does not imply production VALIDATED)."""
    return closeout.n1 == "ACCEPTED" and closeout.n2 == "ACCEPTED" and closeout.n4 == "ACCEPTED"


def production_distinct_fully_converged(closeout: CandidateMeshCloseout) -> bool:
    """Deprecated alias — use :func:`engineering_distinct_fully_converged` with nozzle report."""
    return (
        closeout.production_task173_gate == "RATING_SUCCESS"
        and closeout.production_mesh_n1 == "NUMERIC_VALID"
        and closeout.production_mesh_n2 == "NUMERIC_VALID"
        and closeout.production_mesh_n4 == "NUMERIC_VALID"
        and closeout.hydraulic_pass
        and closeout.target_330kw_met == "true"
        and closeout.n1 == "ACCEPTED"
        and closeout.n2 == "ACCEPTED"
        and closeout.n4 == "ACCEPTED"
    )


def engineering_distinct_fully_converged(
    closeout: CandidateMeshCloseout,
    *,
    nozzle: Any,
    target_met: Literal["true", "false", "unresolved"] | str,
) -> bool:
    """Full engineering acceptance counter (production + duty + hydraulic + nozzle verify)."""
    from prototypes.v08_thermal_rating.nozzle_velocity_v08 import NozzleVelocityReport

    if not production_distinct_fully_converged(closeout):
        return False
    if target_met != "true" and closeout.target_330kw_met != "true":
        return False
    if not isinstance(nozzle, NozzleVelocityReport):
        return False
    if nozzle.status != "VERIFIED":
        return False
    return all(s.in_range_1_3 for s in nozzle.sides if s.velocity_m_s is not None)


def _outer_result_to_trial_report(
    result: IsolatedOuterBoundaryResult,
    *,
    trajectory_hole_count: int | None = None,
) -> IsolatedMeshTrialReport:
    run = result.accepted_run or result.best_valid_run
    classification = result.status
    if result.status == "ACCEPTED":
        classification = "VALID_TRAJECTORY_TERMINAL_PASS"
    elif result.status == "PRECISION_FLOOR":
        classification = "VALID_TRAJECTORY_PRECISION_FLOOR"
    term_k, term_h, duty, t_out, s_out = _mesh_run_summary(run)
    return IsolatedMeshTrialReport(
        subdivisions=result.subdivisions,
        classification=classification,
        shooting_enthalpy_j_kg=result.shooting_enthalpy_j_kg,
        total_duty_w=duty,
        energy_balance_residual_w=(
            str(run.observables.energy_balance_residual_w) if run is not None else None
        ),
        terminal_boundary_residual_k=term_k,
        terminal_boundary_residual_j_kg=term_h,
        tube_outlet_temperature_k=t_out,
        shell_outlet_temperature_k=s_out,
        task172_numerical_hole_count=(
            trajectory_hole_count
            if trajectory_hole_count is not None
            else result.stats.task172_numerical_hole_count
        ),
        diagnostics=result.diagnostics,
    )


def assess_physical_n1_closure(
    bindings: CandidateRatingBindings,
    provider: PropertyProvider,
) -> PhysicalClosureReport:
    """Physics-layer closure via corrected isolated outer shooting (per mesh level)."""
    target = bindings.target_duty_w
    candidate_id = bindings.rating_request.candidate_id
    evidence: list[str] = []
    first_blocker = ""
    mesh_results: list[IsolatedOuterBoundaryResult] = []
    trial_rows: list[IsolatedMeshTrialReport] = []

    wrong_term, wrong_duty = _legacy_wrong_shooting_search(bindings, provider, subdivisions=1)
    if wrong_term is not None:
        evidence.append(f"legacy_wrong_search_terminal_residual_k={wrong_term}")
        evidence.append(f"legacy_wrong_search_total_duty_w={wrong_duty}")

    n1 = solve_isolated_outer_boundary(bindings, provider, subdivisions=1)
    mesh_results.append(n1)

    n1_run = n1.accepted_run or n1.best_valid_run
    if n1_run is None:
        return PhysicalClosureReport(
            case_id=bindings.engineering_case_id,
            candidate_id=candidate_id,
            n1_status="BLOCKED",
            best_shooting_enthalpy_j_kg=n1.shooting_enthalpy_j_kg,
            total_duty_w=None,
            target_duty_w=str(target),
            duty_vs_target="UNKNOWN",
            energy_balance_residual_w=None,
            energy_balance_pass=None,
            terminal_boundary_residual_k=None,
            terminal_within_production_tolerance=None,
            task172_numerical_hole_count=n1.stats.task172_numerical_hole_count,
            geometry_projection_hash=bindings.geometry_projection_hash,
            geometry_duty_insufficient=False,
            isolated_n2_n4_fixed_enthalpy=tuple(trial_rows),
            outer_solve_by_mesh=tuple(mesh_results),
            first_blocker=n1.failure_code or "NO_MESH_RUN",
            evidence=tuple(evidence),
        )

    obs = n1_run.observables
    from hexagent.exchangers.shell_tube.task173_integrated_rating.service import (
        _terminal_tolerance_pass,
    )

    holes = (
        final_trajectory_task172_holes(
            bindings, provider, subdivisions=1, shooting_enthalpy_j_kg=n1.shooting_enthalpy_j_kg
        )
        if n1.shooting_enthalpy_j_kg
        else n1.stats.task172_numerical_hole_count
    )
    trial_rows.append(_outer_result_to_trial_report(n1, trajectory_hole_count=holes))
    ebal = abs(obs.energy_balance_residual_w) <= ENERGY_ACCEPTANCE_FLOOR_W
    term_ok = _terminal_tolerance_pass(n1_run)
    duty_class = _duty_vs_target(obs.total_duty_w, target)
    geometry_duty_insufficient = term_ok and ebal and holes == 0 and duty_class == "BELOW_TARGET"

    if wrong_term is not None:
        evidence.append(f"corrected_search_terminal_residual_k={obs.terminal_boundary_residual_k}")
        evidence.append(f"corrected_search_total_duty_w={obs.total_duty_w}")

    n1_terminal_closed = term_ok and ebal and holes == 0
    if n1_terminal_closed:
        for subdivisions in (2, 4):
            if subdivisions not in REVIEWED_MESH_SEQUENCE:
                continue
            mesh_out = solve_isolated_outer_boundary(bindings, provider, subdivisions=subdivisions)
            mesh_results.append(mesh_out)
            trial_rows.append(_outer_result_to_trial_report(mesh_out))

    n1_closed = n1_terminal_closed and duty_class == "AT_OR_ABOVE_TARGET"

    if n1.status == "PRECISION_FLOOR":
        first_blocker = "OUTER_BOUNDARY_PRECISION_FLOOR"
        evidence.extend(n1.diagnostics)
    elif not term_ok:
        first_blocker = "TERMINAL_BOUNDARY_RESIDUAL_EXCEEDS_PRODUCTION_TOLERANCE"
        evidence.append(f"terminal_boundary_residual_k={obs.terminal_boundary_residual_k}")
        evidence.append(f"terminal_boundary_residual_j_kg={obs.terminal_boundary_residual_j_kg}")
    if geometry_duty_insufficient:
        first_blocker = "GEOMETRY_DUTY_INSUFFICIENT"
        evidence.append(f"total_duty_w={obs.total_duty_w}")
        evidence.append(f"target_duty_w={target}")
    if holes > 0 and not first_blocker:
        first_blocker = "TASK172_NUMERICAL_HOLES"
        evidence.append(f"task172_numerical_hole_count={holes}")

    n1_status: PhysicalN1Status = "CLOSED" if n1_closed else "BLOCKED"

    return PhysicalClosureReport(
        case_id=bindings.engineering_case_id,
        candidate_id=candidate_id,
        n1_status=n1_status,
        best_shooting_enthalpy_j_kg=n1.shooting_enthalpy_j_kg,
        total_duty_w=str(obs.total_duty_w),
        target_duty_w=str(target),
        duty_vs_target=duty_class,
        energy_balance_residual_w=str(obs.energy_balance_residual_w),
        energy_balance_pass=ebal,
        terminal_boundary_residual_k=str(obs.terminal_boundary_residual_k),
        terminal_within_production_tolerance=term_ok,
        task172_numerical_hole_count=holes,
        geometry_projection_hash=bindings.geometry_projection_hash,
        geometry_duty_insufficient=geometry_duty_insufficient,
        isolated_n2_n4_fixed_enthalpy=tuple(trial_rows),
        outer_solve_by_mesh=tuple(mesh_results),
        first_blocker=first_blocker or ("N1_NOT_FULLY_CLOSED" if not n1_closed else ""),
        evidence=tuple(evidence),
    )


def assess_production_culp_rating(
    bindings: CandidateRatingBindings,
    provider: PropertyProvider,
) -> ProductionCulpReport:
    """Unmodified production validate_candidate_rating — no prototype overrides."""
    row = _rate_one_structural_bundle(
        bindings.bundle,
        space_hash=bindings.space_hash,
        target_duty_w=bindings.target_duty_w,
        normalized=bindings.normalized,
        provider=provider,
        handoff=bindings.handoff,
    )
    eng_validated: Literal[False] = False
    return ProductionCulpReport(
        case_id=bindings.engineering_case_id,
        candidate_id=bindings.rating_request.candidate_id,
        outcome=row.rating_outcome,
        failure_code=row.rating_blocked_code,
        mesh_n1_status=row.mesh_n1_status,
        mesh_n2_status=row.mesh_n2_status,
        mesh_n4_status=row.mesh_n4_status,
        engineering_validated=eng_validated,
        row=row,
    )


def _delivery_for_candidate(
    physical: PhysicalClosureReport,
    production: ProductionCulpReport,
) -> tuple[DeliveryOutcome, tuple[str, ...]]:
    if (
        physical.n1_status == "CLOSED"
        and production.outcome == "RATING_SUCCESS"
        and production.mesh_n1_status == "NUMERIC_VALID"
        and production.mesh_n2_status == "NUMERIC_VALID"
        and production.mesh_n4_status == "NUMERIC_VALID"
    ):
        return (
            "A",
            (
                "Isolated N1 physics closed with target duty and terminal tolerance.",
                "Production C-ULP mesh sequence N1/N2/N4 reached NUMERIC_VALID.",
            ),
        )
    rationale: list[str] = []
    if production.failure_code:
        rationale.append(f"production_validate_candidate_rating={production.failure_code}")
    if physical.first_blocker:
        rationale.append(f"isolated_physics={physical.first_blocker}")
    if physical.isolated_n2_n4_fixed_enthalpy:
        blocked = [
            f"n={t.subdivisions}:{t.classification}"
            for t in physical.isolated_n2_n4_fixed_enthalpy
            if t.classification != "VALID_TRAJECTORY"
        ]
        if blocked:
            rationale.append("fixed_enthalpy_n2_n4=" + ",".join(blocked))
    rationale.append(
        "architecture: Task173 counterflow outer enthalpy shooting + per-cell Task172 root "
        "(production service.py _outer_trial / _run_mesh_sequence); not authorized to relax "
        "TERMINAL_TOLERANCE_K or ENERGY_ACCEPTANCE_FLOOR_W."
    )
    return ("B", tuple(rationale))


def closeout_one_candidate(
    bindings: CandidateRatingBindings,
    provider: PropertyProvider,
    *,
    run_production: bool = True,
) -> AxialRatingCandidateCloseout:
    physical = assess_physical_n1_closure(bindings, provider)
    production = (
        assess_production_culp_rating(bindings, provider)
        if run_production
        else ProductionCulpReport(
            case_id=bindings.engineering_case_id,
            candidate_id=bindings.rating_request.candidate_id,
            outcome="NOT_ATTEMPTED",
            failure_code=None,
            mesh_n1_status="NOT_REACHED",
            mesh_n2_status="NOT_REACHED",
            mesh_n4_status="NOT_REACHED",
            engineering_validated=False,
            row=None,
        )
    )
    delivery, rationale = _delivery_for_candidate(physical, production)
    return AxialRatingCandidateCloseout(
        engineering_case_id=bindings.engineering_case_id,
        candidate_id=bindings.rating_request.candidate_id,
        physical=physical,
        production=production,
        delivery=delivery,
        delivery_rationale=rationale,
    )


def run_primary_330kw_closeout(
    provider: PropertyProvider | None = None,
    *,
    max_candidates: int = 2,
    skip_production_rating: bool = False,
) -> AxialRatingCaseCloseout:
    """330 kW primary closeout on first ``max_candidates`` distinct structures."""
    active = provider or CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=active)
    if normalized.engineering_case_id != CASE_330KW_ID:
        raise RuntimeError(f"expected {CASE_330KW_ID}, got {normalized.engineering_case_id}")
    space_hash, t168_digest, bundles, geom_by_id = enumerate_structural_bundles(
        normalized, handoff, max_valid=max(2, max_candidates)
    )
    closeouts: list[AxialRatingCandidateCloseout] = []
    for bundle in bundles[:max_candidates]:
        bindings = build_candidate_rating_bindings(
            bundle,
            space_hash=space_hash,
            t168_digest=t168_digest,
            normalized=normalized,
            handoff=handoff,
            provider=active,
            geometry_projection_hash=geom_by_id.get(bundle.candidate.candidate_id, ""),
        )
        if bindings is None:
            continue
        closeouts.append(
            closeout_one_candidate(
                bindings,
                active,
                run_production=not skip_production_rating,
            )
        )
    aggregate: DeliveryOutcome = (
        "A" if closeouts and all(item.delivery == "A" for item in closeouts) else "B"
    )
    return AxialRatingCaseCloseout(
        primary_case_id=CASE_330KW_ID,
        fixture_path="tests/fixtures/v08_user_case_hxforge_330kw_strict_dp.json",
        normalized_input_hash=handoff.normalized_input_hash,
        task168_request_hash=t168_digest,
        candidates=tuple(closeouts),
        aggregate_delivery=aggregate,
    )


def closeout_to_jsonable(closeout: AxialRatingCaseCloseout) -> dict[str, Any]:
    """Serialize for artifacts and tests."""

    def _physical(p: PhysicalClosureReport) -> dict[str, Any]:
        return {
            "n1_status": p.n1_status,
            "best_shooting_enthalpy_j_kg": p.best_shooting_enthalpy_j_kg,
            "total_duty_w": p.total_duty_w,
            "target_duty_w": p.target_duty_w,
            "duty_vs_target": p.duty_vs_target,
            "energy_balance_residual_w": p.energy_balance_residual_w,
            "energy_balance_pass": p.energy_balance_pass,
            "terminal_boundary_residual_k": p.terminal_boundary_residual_k,
            "terminal_within_production_tolerance": p.terminal_within_production_tolerance,
            "task172_numerical_hole_count": p.task172_numerical_hole_count,
            "first_blocker": p.first_blocker,
            "evidence": list(p.evidence),
            "geometry_projection_hash": p.geometry_projection_hash,
            "geometry_duty_insufficient": p.geometry_duty_insufficient,
            "isolated_n2_n4_fixed_enthalpy": [
                {
                    "subdivisions": t.subdivisions,
                    "classification": t.classification,
                    "total_duty_w": t.total_duty_w,
                    "terminal_boundary_residual_k": t.terminal_boundary_residual_k,
                    "task172_numerical_hole_count": t.task172_numerical_hole_count,
                }
                for t in p.isolated_n2_n4_fixed_enthalpy
            ],
        }

    def _production(pr: ProductionCulpReport) -> dict[str, Any]:
        return {
            "outcome": pr.outcome,
            "failure_code": pr.failure_code,
            "mesh_n1_status": pr.mesh_n1_status,
            "mesh_n2_status": pr.mesh_n2_status,
            "mesh_n4_status": pr.mesh_n4_status,
            "engineering_validated": pr.engineering_validated,
        }

    return {
        "primary_case_id": closeout.primary_case_id,
        "fixture_path": closeout.fixture_path,
        "normalized_input_hash": closeout.normalized_input_hash,
        "task168_request_hash": closeout.task168_request_hash,
        "aggregate_delivery": closeout.aggregate_delivery,
        "regression_case_250kw_id": CASE_250KW_ID,
        "note": "250 kW fixture is regression-only; not mixed into this closeout.",
        "candidates": [
            {
                "candidate_id": item.candidate_id,
                "delivery": item.delivery,
                "delivery_rationale": list(item.delivery_rationale),
                "physical_closure": _physical(item.physical),
                "production_culp": _production(item.production),
            }
            for item in closeout.candidates
        ],
    }


def run_250kw_regression_smoke(
    provider: PropertyProvider | None = None,
) -> dict[str, Any]:
    """250 kW-only regression: production rating row for first geometry (no 330 kW mixing)."""
    active = provider or CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_250, provider=active)
    assert normalized.engineering_case_id != CASE_330KW_ID
    space_hash, t168_digest, bundles, _geom = enumerate_structural_bundles(
        normalized, handoff, max_valid=1
    )
    bundle = bundles[0]
    bindings = build_candidate_rating_bindings(
        bundle,
        space_hash=space_hash,
        t168_digest=t168_digest,
        normalized=normalized,
        handoff=handoff,
        provider=active,
    )
    if bindings is None:
        return {"case_id": normalized.engineering_case_id, "status": "TASK174_BLOCKED"}
    row = _rate_one_structural_bundle(
        bundle,
        space_hash=space_hash,
        target_duty_w=normalized.target_duty_w,
        normalized=normalized,
        provider=active,
        handoff=handoff,
    )
    return {
        "case_id": normalized.engineering_case_id,
        "regression_label": CASE_250KW_ID,
        "normalized_input_hash": handoff.normalized_input_hash,
        "candidate_id": row.candidate_id,
        "rating_outcome": row.rating_outcome,
        "rating_blocked_code": row.rating_blocked_code,
        "isolated_from_330kw": handoff.normalized_input_hash
        != load_case_bindings(FIXTURE_330, provider=active)[1].normalized_input_hash,
    }


__all__ = [
    "AxialRatingCaseCloseout",
    "AxialRatingCandidateCloseout",
    "CandidateMeshCloseout",
    "CASE_330KW_ID",
    "N1VerificationReport",
    "PhysicalClosureReport",
    "ProductionCulpReport",
    "assess_physical_n1_closure",
    "assess_production_culp_rating",
    "closeout_to_jsonable",
    "isolated_mesh_acceptance_gate",
    "production_terminal_tolerance_pass",
    "experimental_mesh_converged",
    "engineering_distinct_fully_converged",
    "production_distinct_fully_converged",
    "run_candidate_mesh_closeout",
    "run_primary_330kw_closeout",
    "run_250kw_regression_smoke",
    "target_330kw_met_label",
    "verify_n1_terminal",
]
