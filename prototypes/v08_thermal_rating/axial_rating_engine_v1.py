"""V08-03 isolated full-exchanger thermal path on production Task172/Task173 physics.

Uses the same geometry, CoolProp binding, and Task172 local correlations as production
``validate_candidate_rating``, but can evaluate a single outer shooting enthalpy trial
without claiming production C-ULP or VALIDATED status.

Primary case: HXFORGE_330KW_STRICT_DP. 250 kW fixture is regression-only (see tests).
"""

# ruff: noqa: E501

from __future__ import annotations

import math
import os
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
    TERMINAL_TOLERANCE_K,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating.service import (
    _CANDIDATE_RATING_CONTEXT,
    ENERGY_ACCEPTANCE_FLOOR_W,
    _candidate_context,
    _CellSearchStats,
    _outer_trial,
    _OuterTrial,
    effective_admitted_h_max_j_kg,
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
    isolated_n2_n4_fixed_enthalpy: tuple[IsolatedMeshTrialReport, ...]
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


def _bracket_search_limit() -> int:
    raw = os.environ.get("V08_AXIAL_BRACKET_MAX_ITER", "16")
    try:
        return max(4, min(32, int(raw)))
    except ValueError:
        return 16


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
) -> tuple[str, str, tuple[V08StructuralGeometryBundle, ...]]:
    space = load_v08_discrete_space(DEFAULT_V08_DISCRETE_SPACE_PATH)
    filtered, _ = filter_discrete_space_by_envelope(space, normalized.design_envelope)
    t168 = build_v08_task168_request(normalized, handoff, filtered)
    t168_digest = task168_request_hash_digest(t168)
    enum = enumerate_structural_geometry(t168, filtered, (), max_valid_candidates=max_valid)
    return enum.space_hash, t168_digest, enum.valid_structural


def build_candidate_rating_bindings(
    bundle: V08StructuralGeometryBundle,
    *,
    space_hash: str,
    t168_digest: str,
    normalized: NormalizedUserDesignCase,
    handoff: V08SolverHandoffV1,
    provider: PropertyProvider,
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
    rating_req = v08_thermal_rating_request(
        candidate, space_hash, b, topology, t174, t168_digest
    )
    return CandidateRatingBindings(
        bundle=bundle,
        space_hash=space_hash,
        normalized=normalized,
        handoff=handoff,
        rating_request=rating_req,
        engineering_case_id=normalized.engineering_case_id,
        target_duty_w=normalized.target_duty_w,
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
        terminal_boundary_residual_k=str(obs.terminal_boundary_residual_k) if obs is not None else None,
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


def _search_valid_shooting_enthalpy(
    bindings: CandidateRatingBindings,
    provider: PropertyProvider,
    *,
    subdivisions: int = 1,
) -> tuple[Decimal | None, _OuterTrial | None, _CellSearchStats]:
    """Bracket shell-outlet enthalpy between cold inlet and admitted max (production bounds)."""
    btoken = _thermal_boundary_token(bindings.normalized, provider)
    context = _candidate_context(bindings.rating_request)
    ctx_token = _CANDIDATE_RATING_CONTEXT.set(context)
    h_lo = float(effective_shell_cold_inlet_enthalpy_j_kg())
    h_hi = float(effective_admitted_h_max_j_kg(provider))
    best_h: Decimal | None = None
    best_trial: _OuterTrial | None = None
    best_stats = _CellSearchStats()
    try:
        for _ in range(_bracket_search_limit()):
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
            if trial.classification == "VALID_TRAJECTORY":
                h_lo = h_mid
                best_h = Decimal(str(h_mid))
                best_trial = trial
                best_stats = stats
            elif trial.classification == "LOW_SIDE_DOMAIN_INFEASIBLE":
                h_lo = h_mid
            else:
                h_hi = h_mid
            if math.isclose(h_lo, h_hi, rel_tol=0.0, abs_tol=1e-6):
                break
        return best_h, best_trial, best_stats
    finally:
        _CANDIDATE_RATING_CONTEXT.reset(ctx_token)
        reset_experimental_thermal_boundary(btoken)


def assess_physical_n1_closure(
    bindings: CandidateRatingBindings,
    provider: PropertyProvider,
) -> PhysicalClosureReport:
    """Physics-layer N1: full cell march via production _outer_trial, separate from C-ULP."""
    target = bindings.target_duty_w
    best_h, best_trial, stats = _search_valid_shooting_enthalpy(bindings, provider, subdivisions=1)
    candidate_id = bindings.rating_request.candidate_id
    n2_n4: list[IsolatedMeshTrialReport] = []
    first_blocker = ""
    evidence: list[str] = []

    if best_h is None or best_trial is None or best_trial.mesh_run is None:
        return PhysicalClosureReport(
            case_id=bindings.engineering_case_id,
            candidate_id=candidate_id,
            n1_status="BLOCKED",
            best_shooting_enthalpy_j_kg=str(best_h) if best_h is not None else None,
            total_duty_w=None,
            target_duty_w=str(target),
            duty_vs_target="UNKNOWN",
            energy_balance_residual_w=None,
            energy_balance_pass=None,
            terminal_boundary_residual_k=None,
            terminal_within_production_tolerance=None,
            task172_numerical_hole_count=stats.task172_numerical_hole_count,
            isolated_n2_n4_fixed_enthalpy=tuple(n2_n4),
            first_blocker="NO_VALID_TRAJECTORY_IN_SHOOTING_BRACKET",
            evidence=tuple(evidence),
        )

    obs = best_trial.mesh_run.observables
    ebal = abs(obs.energy_balance_residual_w) <= ENERGY_ACCEPTANCE_FLOOR_W
    term_ok = obs.terminal_boundary_residual_k <= TERMINAL_TOLERANCE_K
    duty_class = _duty_vs_target(obs.total_duty_w, target)
    holes = stats.task172_numerical_hole_count

    for subdivisions in (2, 4):
        if subdivisions not in REVIEWED_MESH_SEQUENCE:
            continue
        trial_row = run_isolated_outer_trials(
            bindings, provider, subdivisions=subdivisions, shooting_enthalpy_j_kg=best_h
        )
        n2_n4.append(trial_row)

    n1_closed = (
        ebal
        and holes == 0
        and best_trial.classification == "VALID_TRAJECTORY"
        and term_ok
        and duty_class == "AT_OR_ABOVE_TARGET"
    )

    if not term_ok:
        first_blocker = "TERMINAL_BOUNDARY_RESIDUAL_EXCEEDS_PRODUCTION_TOLERANCE"
        evidence.append(f"terminal_boundary_residual_k={obs.terminal_boundary_residual_k}")
        evidence.append(f"TERMINAL_TOLERANCE_K={TERMINAL_TOLERANCE_K}")
    if duty_class == "BELOW_TARGET":
        if not first_blocker:
            first_blocker = "TOTAL_DUTY_BELOW_TARGET"
        evidence.append(f"total_duty_w={obs.total_duty_w}")
        evidence.append(f"target_duty_w={target}")
    if holes > 0:
        if not first_blocker:
            first_blocker = "TASK172_NUMERICAL_HOLES"
        evidence.append(f"task172_numerical_hole_count={holes}")

    n1_status: PhysicalN1Status = "CLOSED" if n1_closed else "BLOCKED"

    return PhysicalClosureReport(
        case_id=bindings.engineering_case_id,
        candidate_id=candidate_id,
        n1_status=n1_status,
        best_shooting_enthalpy_j_kg=str(best_h),
        total_duty_w=str(obs.total_duty_w),
        target_duty_w=str(target),
        duty_vs_target=duty_class,
        energy_balance_residual_w=str(obs.energy_balance_residual_w),
        energy_balance_pass=ebal,
        terminal_boundary_residual_k=str(obs.terminal_boundary_residual_k),
        terminal_within_production_tolerance=term_ok,
        task172_numerical_hole_count=holes,
        isolated_n2_n4_fixed_enthalpy=tuple(n2_n4),
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
    space_hash, t168_digest, bundles = enumerate_structural_bundles(
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
            "isolated_n2_n4_fixed_enthalpy": [
                {
                    "subdivisions": t.subdivisions,
                    "classification": t.classification,
                    "total_duty_w": t.total_duty_w,
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
    space_hash, t168_digest, bundles = enumerate_structural_bundles(normalized, handoff, max_valid=1)
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
    "CASE_330KW_ID",
    "PhysicalClosureReport",
    "ProductionCulpReport",
    "assess_physical_n1_closure",
    "assess_production_culp_rating",
    "closeout_to_jsonable",
    "run_primary_330kw_closeout",
    "run_250kw_regression_smoke",
]
