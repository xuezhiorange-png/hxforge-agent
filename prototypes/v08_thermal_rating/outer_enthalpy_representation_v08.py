"""TASK173 outer enthalpy numerical representation — isolated prototype (non-production).

Does not replace ``task173_integrated_rating.service``; patches are scoped to a context
manager only. Production tolerances and Task172 gates are unchanged.
"""

# ruff: noqa: E501

from __future__ import annotations

import math
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Literal

import hexagent.exchangers.shell_tube.task173_integrated_rating.service as _svc
from hexagent.exchangers.shell_tube.task173_integrated_rating.models import (
    MAX_OUTER_BISECTION_ITERATIONS,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating.service import (
    FluidIdentifier,
    ReferenceStatePolicy,
    _apply_valid_outer_trial_update,
    _assert_outer_classification_order,
    _binary64_enthalpy_step_toward,
    _CellSearchStats,
    _checked_thermo,
    _d,
    _MeshRun,
    _outer_shooting_residual_plateau_evidence,
    _outer_trial,
    _OuterTrial,
    _Stage3Failure,
    effective_outer_shooting_high_enthalpy_j_kg,
    effective_shell_cold_inlet_enthalpy_j_kg,
    effective_shell_property_evaluation_pressure_pa,
)
from hexagent.properties.base import PropertyProvider
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import (
    CandidateRatingBindings,
    _run_with_rating_context,
)
from prototypes.v08_thermal_rating.outer_shooting_isolated_v1 import (
    IsolatedOuterBoundaryResult,
    OuterSearchStepRecord,
    _trace_step,
    solve_outer_boundary_from_trial_isolated,
)

_PROD_STATE_FROM_ENTHALPY = _svc._state_from_enthalpy
_PROD_VALID_TRAJECTORY = _svc._valid_trajectory
_PROD_TERMINAL_TOLERANCE_PASS = _svc._terminal_tolerance_pass
_PROD_SOLVE_OUTER_BOUNDARY = _svc._solve_outer_boundary

EXPERIMENTAL_AUTHORITY_ID = "V08_03_OUTER_ENTHALPY_REPRESENTATION_PROTOTYPE"
TASK_ID = "V08-03"
EXECUTION_STAGE = "TASK173_OUTER_ENTHALPY_NUMERICAL_REPRESENTATION"

_ACTIVE: ContextVar[OuterEnthalpyRepresentation | None] = ContextVar(
    "v08_outer_enthalpy_rep", default=None
)


@dataclass
class EnthalpyAuthorityAuditRow:
    role: str
    conservative_j_kg: str
    property_query_j_kg: str
    provider_return_j_kg: str | None
    face_state_j_kg: str | None
    terminal_boundary_j_kg: str | None
    conversion_error_j_kg: float | None


@dataclass
class OuterEnthalpyRepresentation:
    h_cold_reference_j_kg: Decimal
    shooting_delta_j_kg: Decimal | None = None
    terminal_boundary_j_kg: Decimal | None = None
    audit_rows: list[EnthalpyAuthorityAuditRow] = field(default_factory=list)
    max_property_conversion_error_j_kg: float = 0.0

    def record(
        self,
        *,
        role: str,
        conservative: Decimal,
        property_query: Decimal,
        provider_return: Decimal | None,
        face_h: Decimal | None,
        terminal_h: Decimal | None,
    ) -> None:
        conv: float | None = None
        if provider_return is not None:
            conv = abs(float(conservative - provider_return))
            if conv > self.max_property_conversion_error_j_kg:
                self.max_property_conversion_error_j_kg = conv
        self.audit_rows.append(
            EnthalpyAuthorityAuditRow(
                role=role,
                conservative_j_kg=str(conservative),
                property_query_j_kg=str(property_query),
                provider_return_j_kg=str(provider_return) if provider_return is not None else None,
                face_state_j_kg=str(face_h) if face_h is not None else None,
                terminal_boundary_j_kg=str(terminal_h) if terminal_h is not None else None,
                conversion_error_j_kg=conv,
            )
        )


def _shell_ph_state_experimental(
    provider: PropertyProvider,
    enthalpy_j_kg: Decimal,
    rep: OuterEnthalpyRepresentation,
) -> Any:
    cold = rep.h_cold_reference_j_kg
    delta = enthalpy_j_kg - cold
    h_query_float = float(cold) + float(delta)
    property_query = Decimal(str(h_query_float))
    eval_pressure = effective_shell_property_evaluation_pressure_pa()
    try:
        state = provider.state_ph(
            FluidIdentifier(name="Water"),
            pressure_pa=float(eval_pressure),
            enthalpy_j_kg=h_query_float,
            reference_state=ReferenceStatePolicy.DEF,
        )
    except Exception as exc:
        raise _Stage3Failure(
            "BLOCKED_PROPERTY_EVALUATION_FAILURE", "state_ph", type(exc).__name__
        ) from exc
    provider_h = _d(state.enthalpy_j_kg)
    rep.record(
        role="SHELL_PH_RECONSTRUCTION",
        conservative=enthalpy_j_kg,
        property_query=property_query,
        provider_return=provider_h,
        face_h=None,
        terminal_h=rep.terminal_boundary_j_kg,
    )
    return _checked_thermo(state, query_type="PH")


def experimental_state_from_enthalpy(
    provider: PropertyProvider,
    enthalpy_j_kg: Decimal,
    *,
    shell_search_state: bool = False,
    side: Literal["TUBE", "SHELL"] = "TUBE",
) -> Any:
    rep = _ACTIVE.get()
    if rep is None or side != "SHELL":
        return _PROD_STATE_FROM_ENTHALPY(
            provider, enthalpy_j_kg, shell_search_state=shell_search_state, side=side
        )
    at_terminal = (
        rep.terminal_boundary_j_kg is not None and enthalpy_j_kg == rep.terminal_boundary_j_kg
    )
    if shell_search_state or not at_terminal:
        return _PROD_STATE_FROM_ENTHALPY(
            provider, enthalpy_j_kg, shell_search_state=shell_search_state, side=side
        )
    if enthalpy_j_kg == rep.h_cold_reference_j_kg:
        st = _PROD_STATE_FROM_ENTHALPY(provider, enthalpy_j_kg, shell_search_state=False, side=side)
        rep.record(
            role="SHELL_COLD_INLET",
            conservative=enthalpy_j_kg,
            property_query=enthalpy_j_kg,
            provider_return=_d(st.native.enthalpy_j_kg),
            face_h=_d(st.native.enthalpy_j_kg),
            terminal_h=rep.terminal_boundary_j_kg,
        )
        return st
    return _shell_ph_state_experimental(provider, enthalpy_j_kg, rep)


def experimental_valid_trajectory(
    subdivisions: int,
    shell_outlet_enthalpy: Decimal,
    provider: PropertyProvider,
    shell_authority: Any,
    outer_iterations: int,
    search_stats: _CellSearchStats | None = None,
    capture_diagnostics: bool = False,
) -> _MeshRun:
    rep = _ACTIVE.get()
    if rep is not None:
        rep.terminal_boundary_j_kg = shell_outlet_enthalpy
        rep.shooting_delta_j_kg = shell_outlet_enthalpy - rep.h_cold_reference_j_kg
    run = _PROD_VALID_TRAJECTORY(
        subdivisions,
        shell_outlet_enthalpy,
        provider,
        shell_authority,
        outer_iterations,
        search_stats,
        capture_diagnostics=capture_diagnostics,
    )
    if rep is not None and run.faces_shell:
        face_h = run.faces_shell[0].property_snapshot.enthalpy_j_kg
        rep.record(
            role="SHELL_INLET_FACE_AFTER_TRAJECTORY",
            conservative=shell_outlet_enthalpy,
            property_query=shell_outlet_enthalpy,
            provider_return=None,
            face_h=Decimal(str(face_h)),
            terminal_h=shell_outlet_enthalpy,
        )
    return run


def experimental_terminal_tolerance_pass(run: _MeshRun) -> bool:
    """Production thresholds only — no relaxation."""
    return _PROD_TERMINAL_TOLERANCE_PASS(run)


def _absolute_from_delta(cold: Decimal, delta: Decimal) -> Decimal:
    return cold + delta


def solve_outer_boundary_delta_coordinate(
    trial_at: Callable[[Decimal, int], _OuterTrial],
    *,
    subdivisions: int,
    provider: PropertyProvider,
    stats: _CellSearchStats,
) -> IsolatedOuterBoundaryResult:
    """Outer shooting in shell enthalpy-rise coordinates Δh = h_shell,inlet,outlet − h_cold."""
    trace: list[OuterSearchStepRecord] = []
    cold = effective_shell_cold_inlet_enthalpy_j_kg()
    h_high_abs = effective_outer_shooting_high_enthalpy_j_kg(provider)
    d_low = Decimal(0)
    d_high = h_high_abs - cold

    def trial_delta(delta: Decimal, iteration: int) -> _OuterTrial:
        return trial_at(_absolute_from_delta(cold, delta), iteration)

    low_trial = trial_delta(d_low, 0)
    trace.append(
        _trace_step(
            iteration=0,
            h_low=cold,
            h_high=h_high_abs,
            h_trial=cold,
            trial=low_trial,
            stats=stats,
            decision="DELTA_INITIAL_LOW",
        )
    )
    if low_trial.classification != "LOW_SIDE_DOMAIN_INFEASIBLE":
        code = (
            "BLOCKED_OUTER_LOW_ENDPOINT_HARD_BLOCKER"
            if low_trial.classification == "HARD_BLOCKER"
            else "BLOCKED_OUTER_LOW_ENDPOINT_NOT_INFEASIBLE"
        )
        status: Literal["HARD_BLOCKER", "SETUP_FAILURE"] = (
            "HARD_BLOCKER" if low_trial.classification == "HARD_BLOCKER" else "SETUP_FAILURE"
        )
        return IsolatedOuterBoundaryResult(
            status=status,
            subdivisions=subdivisions,
            accepted_run=None,
            best_valid_run=low_trial.mesh_run,
            shooting_enthalpy_j_kg=str(cold),
            failure_code=code,
            diagnostics=low_trial.diagnostics + (f"delta_low={d_low}", f"delta_high={d_high}"),
            search_trace=tuple(trace),
            stats=stats,
            h_low_final=str(cold),
            h_high_final=str(h_high_abs),
            float_h_low_hex=float(cold).hex(),
            float_h_high_hex=float(h_high_abs).hex(),
        )

    high_trial = trial_delta(d_high, 0)
    trace.append(
        _trace_step(
            iteration=0,
            h_low=cold,
            h_high=h_high_abs,
            h_trial=h_high_abs,
            trial=high_trial,
            stats=stats,
            decision="DELTA_INITIAL_HIGH",
        )
    )
    if high_trial.classification != "VALID_TRAJECTORY" or high_trial.mesh_run is None:
        return IsolatedOuterBoundaryResult(
            status="SETUP_FAILURE",
            subdivisions=subdivisions,
            accepted_run=None,
            best_valid_run=high_trial.mesh_run,
            shooting_enthalpy_j_kg=None,
            failure_code="BLOCKED_OUTER_FEASIBLE_UPPER_ENDPOINT_NOT_FOUND",
            diagnostics=high_trial.diagnostics + (f"delta_high={d_high}",),
            search_trace=tuple(trace),
            stats=stats,
            h_low_final=str(cold),
            h_high_final=str(h_high_abs),
            float_h_low_hex=float(cold).hex(),
            float_h_high_hex=float(h_high_abs).hex(),
        )

    high_run = high_trial.mesh_run
    assert high_run is not None
    if experimental_terminal_tolerance_pass(high_run):
        trace.append(
            _trace_step(
                iteration=0,
                h_low=cold,
                h_high=h_high_abs,
                h_trial=h_high_abs,
                trial=high_trial,
                stats=stats,
                decision="ACCEPTED_DELTA_HIGH",
            )
        )
        return IsolatedOuterBoundaryResult(
            status="ACCEPTED",
            subdivisions=subdivisions,
            accepted_run=high_run,
            best_valid_run=high_run,
            shooting_enthalpy_j_kg=str(h_high_abs),
            failure_code=None,
            diagnostics=("OUTER_DELTA_COORDINATE",),
            search_trace=tuple(trace),
            stats=stats,
            h_low_final=str(cold),
            h_high_final=str(h_high_abs),
            float_h_low_hex=float(cold).hex(),
            float_h_high_hex=float(h_high_abs).hex(),
        )

    seen_low = [d_low]
    seen_valid = [d_high]
    best = high_run
    d_lo, d_hi = d_low, d_high
    iteration = 0
    for iteration in range(1, MAX_OUTER_BISECTION_ITERATIONS + 1):
        abs_lo = _absolute_from_delta(cold, d_lo)
        abs_hi = _absolute_from_delta(cold, d_hi)
        stepped_abs = _binary64_enthalpy_step_toward(abs_hi, abs_lo)
        if stepped_abs is None:
            plateau = _outer_shooting_residual_plateau_evidence(
                abs_lo, abs_hi, trial_delta, iteration, max_probes=32
            )
            return IsolatedOuterBoundaryResult(
                status="PRECISION_FLOOR",
                subdivisions=subdivisions,
                accepted_run=None,
                best_valid_run=best,
                shooting_enthalpy_j_kg=str(best.shooting_enthalpy),
                failure_code="BLOCKED_OUTER_BOUNDARY_PRECISION_FLOOR_REACHED",
                diagnostics=plateau + ("OUTER_DELTA_COORDINATE",),
                search_trace=tuple(trace),
                stats=stats,
                h_low_final=str(abs_lo),
                h_high_final=str(abs_hi),
                float_h_low_hex=float(abs_lo).hex(),
                float_h_high_hex=float(abs_hi).hex(),
            )
        d_mid = stepped_abs - cold
        trial = trial_delta(d_mid, iteration)
        trace.append(
            _trace_step(
                iteration=iteration,
                h_low=abs_lo,
                h_high=abs_hi,
                h_trial=stepped_abs,
                trial=trial,
                stats=stats,
                decision=f"DELTA_STEP_{trial.classification}",
            )
        )
        if trial.classification == "HARD_BLOCKER":
            return IsolatedOuterBoundaryResult(
                status="HARD_BLOCKER",
                subdivisions=subdivisions,
                accepted_run=None,
                best_valid_run=trial.mesh_run,
                shooting_enthalpy_j_kg=str(stepped_abs),
                failure_code=trial.diagnostics[0] if trial.diagnostics else "HARD_BLOCKER",
                diagnostics=trial.diagnostics,
                search_trace=tuple(trace),
                stats=stats,
                h_low_final=str(abs_lo),
                h_high_final=str(abs_hi),
                float_h_low_hex=float(abs_lo).hex(),
                float_h_high_hex=float(abs_hi).hex(),
            )
        if trial.classification == "LOW_SIDE_DOMAIN_INFEASIBLE":
            d_lo = d_mid
            seen_low.append(d_mid)
            continue
        if trial.classification != "VALID_TRAJECTORY" or trial.mesh_run is None:
            d_hi = d_mid
            continue
        _assert_outer_classification_order(
            [_absolute_from_delta(cold, x) for x in seen_low],
            [_absolute_from_delta(cold, x) for x in seen_valid],
            stepped_abs,
            trial.classification,
        )
        run = _apply_valid_outer_trial_update(
            h_mid=stepped_abs, trial=trial, seen_low=[_absolute_from_delta(cold, x) for x in seen_low], seen_valid=[_absolute_from_delta(cold, x) for x in seen_valid]
        )
        best = run
        seen_valid.append(d_mid)
        if experimental_terminal_tolerance_pass(run):
            trace.append(
                _trace_step(
                    iteration=iteration,
                    h_low=_absolute_from_delta(cold, d_lo),
                    h_high=_absolute_from_delta(cold, d_hi),
                    h_trial=stepped_abs,
                    trial=trial,
                    stats=stats,
                    decision="ACCEPTED_DELTA_BISECTION",
                )
            )
            return IsolatedOuterBoundaryResult(
                status="ACCEPTED",
                subdivisions=subdivisions,
                accepted_run=run,
                best_valid_run=run,
                shooting_enthalpy_j_kg=str(stepped_abs),
                failure_code=None,
                diagnostics=("OUTER_DELTA_COORDINATE",),
                search_trace=tuple(trace),
                stats=stats,
                h_low_final=str(_absolute_from_delta(cold, d_lo)),
                h_high_final=str(_absolute_from_delta(cold, d_hi)),
                float_h_low_hex=float(_absolute_from_delta(cold, d_lo)).hex(),
                float_h_high_hex=float(_absolute_from_delta(cold, d_hi)).hex(),
            )
        obs = run.observables
        if obs.terminal_boundary_residual_k > Decimal(0) or obs.terminal_boundary_residual_j_kg > Decimal(0):
            d_hi = d_mid
        else:
            d_lo = d_mid

    return IsolatedOuterBoundaryResult(
        status="PRECISION_FLOOR",
        subdivisions=subdivisions,
        accepted_run=None,
        best_valid_run=best,
        shooting_enthalpy_j_kg=str(best.shooting_enthalpy),
        failure_code="BLOCKED_OUTER_BOUNDARY_PRECISION_FLOOR_REACHED",
        diagnostics=("MAX_OUTER_ITERATIONS", "OUTER_DELTA_COORDINATE"),
        search_trace=tuple(trace),
        stats=stats,
        h_low_final=str(_absolute_from_delta(cold, d_lo)),
        h_high_final=str(_absolute_from_delta(cold, d_hi)),
        float_h_low_hex=float(_absolute_from_delta(cold, d_lo)).hex(),
        float_h_high_hex=float(_absolute_from_delta(cold, d_hi)).hex(),
    )


def experimental_solve_outer_boundary(
    subdivisions: int,
    provider: PropertyProvider,
    shell_authority: Any,
    search_stats: _CellSearchStats | None = None,
) -> _MeshRun:
    stats = search_stats if search_stats is not None else _CellSearchStats()

    def trial_at(enthalpy: Decimal, iteration: int) -> _OuterTrial:
        return _outer_trial(
            subdivisions,
            enthalpy,
            provider,
            shell_authority,
            iteration,
            stats,
        )

    result = solve_outer_boundary_delta_coordinate(
        trial_at, subdivisions=subdivisions, provider=provider, stats=stats
    )
    if result.status != "ACCEPTED" or result.accepted_run is None:
        code = result.failure_code or result.status
        raise _Stage3Failure(code, *result.diagnostics)
    return result.accepted_run


@contextmanager
def outer_enthalpy_representation_scope(
    *,
    h_cold: Decimal | None = None,
) -> Iterator[OuterEnthalpyRepresentation]:
    cold = h_cold if h_cold is not None else effective_shell_cold_inlet_enthalpy_j_kg()
    rep = OuterEnthalpyRepresentation(h_cold_reference_j_kg=cold)
    token = _ACTIVE.set(rep)
    _svc._state_from_enthalpy = experimental_state_from_enthalpy
    _svc._valid_trajectory = experimental_valid_trajectory
    _svc._terminal_tolerance_pass = experimental_terminal_tolerance_pass
    _svc._solve_outer_boundary = experimental_solve_outer_boundary
    try:
        yield rep
    finally:
        _svc._state_from_enthalpy = _PROD_STATE_FROM_ENTHALPY
        _svc._valid_trajectory = _PROD_VALID_TRAJECTORY
        _svc._terminal_tolerance_pass = _PROD_TERMINAL_TOLERANCE_PASS
        _svc._solve_outer_boundary = _PROD_SOLVE_OUTER_BOUNDARY
        _ACTIVE.reset(token)


def solve_isolated_outer_boundary_experimental(
    bindings: CandidateRatingBindings,
    provider: PropertyProvider,
    *,
    subdivisions: int,
) -> tuple[IsolatedOuterBoundaryResult, OuterEnthalpyRepresentation, float]:
    t0 = time.perf_counter()

    def body(
        context: Any, _btoken: object
    ) -> tuple[IsolatedOuterBoundaryResult, OuterEnthalpyRepresentation]:
        stats = _CellSearchStats()
        with outer_enthalpy_representation_scope() as rep:
            def trial_at(enthalpy: Decimal, iteration: int) -> _OuterTrial:
                return _outer_trial(
                    subdivisions,
                    enthalpy,
                    provider,
                    context.shell_authority,
                    iteration,
                    stats,
                )

            result = solve_outer_boundary_from_trial_isolated(
                trial_at,
                subdivisions=subdivisions,
                provider=provider,
                stats=stats,
            )
        return result, rep

    result, rep = _run_with_rating_context(
        bindings, provider, subdivisions=subdivisions, body=body
    )
    return result, rep, time.perf_counter() - t0


def conservative_enthalpy_authority_pass(rep: OuterEnthalpyRepresentation) -> bool:
    if not rep.audit_rows:
        return False
    cold = float(rep.h_cold_reference_j_kg)
    ulp = math.ulp(cold) if cold != 0 else math.ulp(1.0)
    limit = max(ulp * 8, 1e-6)
    return rep.max_property_conversion_error_j_kg <= limit


def property_state_consistency_pass(rep: OuterEnthalpyRepresentation) -> bool:
    """Provider returns are preserved; conversion error is audit only, not overwritten."""
    return conservative_enthalpy_authority_pass(rep) and bool(rep.audit_rows)