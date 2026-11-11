"""Isolated replica of Task173 outer enthalpy shooting (EXPERIMENTAL_NOT_APPROVED).

Mirrors ``service._solve_outer_boundary_from_trial`` classification updates without
mutating production code or relaxing terminal tolerances.
"""

# ruff: noqa: E501

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal, localcontext
from typing import Literal

from hexagent.exchangers.shell_tube.task173_integrated_rating.experimental_thermal_boundary import (
    active_experimental_thermal_boundary,
    bulk_property_pressure_feedback_active,
    variable_water_temperature_active,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating.models import (
    MAX_OUTER_BISECTION_ITERATIONS,
    TERMINAL_TOLERANCE_K,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating.service import (
    _apply_valid_outer_trial_update,
    _assert_outer_classification_order,
    _binary64_enthalpy_step_toward,
    _CellSearchStats,
    _MeshRun,
    _outer_shooting_residual_plateau_evidence,
    _OuterTrial,
    _Stage3Failure,
    _terminal_tolerance_pass,
    effective_outer_shooting_high_enthalpy_j_kg,
    effective_shell_cold_inlet_enthalpy_j_kg,
    effective_shell_inlet_temperature_k,
)
from hexagent.properties.base import PropertyProvider

OuterSolveStatus = Literal[
    "ACCEPTED",
    "PRECISION_FLOOR",
    "HARD_BLOCKER",
    "SETUP_FAILURE",
    "RESOURCE_EXHAUSTION",
]


@dataclass(frozen=True)
class OuterSearchStepRecord:
    iteration: int
    h_low: str
    h_high: str
    h_trial: str
    classification: str
    terminal_residual_k: str | None
    terminal_residual_j_kg: str | None
    total_duty_w: str | None
    task172_hole_count: int
    decision_update: str
    terminal_tolerance_pass: bool


@dataclass(frozen=True)
class IsolatedOuterBoundaryResult:
    status: OuterSolveStatus
    subdivisions: int
    accepted_run: _MeshRun | None
    best_valid_run: _MeshRun | None
    shooting_enthalpy_j_kg: str | None
    failure_code: str | None
    diagnostics: tuple[str, ...]
    search_trace: tuple[OuterSearchStepRecord, ...]
    stats: _CellSearchStats
    h_low_final: str | None
    h_high_final: str | None
    float_h_low_hex: str | None
    float_h_high_hex: str | None


def _trace_step(
    *,
    iteration: int,
    h_low: Decimal,
    h_high: Decimal,
    h_trial: Decimal,
    trial: _OuterTrial,
    stats: _CellSearchStats,
    decision: str,
) -> OuterSearchStepRecord:
    obs = trial.mesh_run.observables if trial.mesh_run is not None else None
    term_pass = _terminal_tolerance_pass(trial.mesh_run) if trial.mesh_run is not None else False
    return OuterSearchStepRecord(
        iteration=iteration,
        h_low=str(h_low),
        h_high=str(h_high),
        h_trial=str(h_trial),
        classification=trial.classification,
        terminal_residual_k=str(obs.terminal_boundary_residual_k) if obs else None,
        terminal_residual_j_kg=str(obs.terminal_boundary_residual_j_kg) if obs else None,
        total_duty_w=str(obs.total_duty_w) if obs else None,
        task172_hole_count=stats.task172_numerical_hole_count,
        decision_update=decision,
        terminal_tolerance_pass=term_pass,
    )


def solve_outer_boundary_from_trial_isolated(
    trial_at: Callable[[Decimal, int], _OuterTrial],
    *,
    subdivisions: int,
    provider: PropertyProvider,
    stats: _CellSearchStats,
) -> IsolatedOuterBoundaryResult:
    """Production-parallel outer solve with full search trace (prototype only)."""
    trace: list[OuterSearchStepRecord] = []

    h_low = effective_shell_cold_inlet_enthalpy_j_kg()
    h_high = effective_outer_shooting_high_enthalpy_j_kg(provider)

    low_trial = trial_at(h_low, 0)
    trace.append(
        _trace_step(
            iteration=0,
            h_low=h_low,
            h_high=h_high,
            h_trial=h_low,
            trial=low_trial,
            stats=stats,
            decision="INITIAL_LOW_ENDPOINT",
        )
    )
    if low_trial.classification != "LOW_SIDE_DOMAIN_INFEASIBLE":
        if low_trial.classification == "HARD_BLOCKER":
            return IsolatedOuterBoundaryResult(
                status="HARD_BLOCKER",
                subdivisions=subdivisions,
                accepted_run=None,
                best_valid_run=low_trial.mesh_run,
                shooting_enthalpy_j_kg=str(h_low),
                failure_code="BLOCKED_OUTER_LOW_ENDPOINT_HARD_BLOCKER",
                diagnostics=low_trial.diagnostics,
                search_trace=tuple(trace),
                stats=stats,
                h_low_final=str(h_low),
                h_high_final=str(h_high),
                float_h_low_hex=float(h_low).hex(),
                float_h_high_hex=float(h_high).hex(),
            )
        return IsolatedOuterBoundaryResult(
            status="SETUP_FAILURE",
            subdivisions=subdivisions,
            accepted_run=None,
            best_valid_run=None,
            shooting_enthalpy_j_kg=None,
            failure_code="BLOCKED_OUTER_LOW_ENDPOINT_NOT_INFEASIBLE",
            diagnostics=low_trial.diagnostics,
            search_trace=tuple(trace),
            stats=stats,
            h_low_final=str(h_low),
            h_high_final=str(h_high),
            float_h_low_hex=float(h_low).hex(),
            float_h_high_hex=float(h_high).hex(),
        )

    high_trial = trial_at(h_high, 0)
    trace.append(
        _trace_step(
            iteration=0,
            h_low=h_low,
            h_high=h_high,
            h_trial=h_high,
            trial=high_trial,
            stats=stats,
            decision="INITIAL_HIGH_ENDPOINT",
        )
    )
    if high_trial.classification != "VALID_TRAJECTORY" or high_trial.mesh_run is None:
        bound = active_experimental_thermal_boundary()
        if bound is not None and (
            bulk_property_pressure_feedback_active(bound)
            or variable_water_temperature_active(bound)
        ):
            bracket_lo = h_low
            bracket_hi = h_high
            recovered: _OuterTrial | None = None
            for _ in range(24):
                probe_h = (bracket_lo + bracket_hi) / Decimal(2)
                if probe_h in (bracket_lo, bracket_hi):
                    break
                probe = trial_at(probe_h, 0)
                trace.append(
                    _trace_step(
                        iteration=0,
                        h_low=bracket_lo,
                        h_high=bracket_hi,
                        h_trial=probe_h,
                        trial=probe,
                        stats=stats,
                        decision="RECOVERY_BRACKET_PROBE",
                    )
                )
                if probe.classification == "VALID_TRAJECTORY" and probe.mesh_run is not None:
                    recovered = probe
                    bracket_lo = probe_h
                    trace.append(
                        _trace_step(
                            iteration=0,
                            h_low=bracket_lo,
                            h_high=bracket_hi,
                            h_trial=probe_h,
                            trial=probe,
                            stats=stats,
                            decision="RECOVERY_BRACKET_UPDATE_H_LOW_VALID",
                        )
                    )
                elif probe.classification == "LOW_SIDE_DOMAIN_INFEASIBLE":
                    bracket_lo = probe_h
                elif probe.classification == "HARD_BLOCKER":
                    return IsolatedOuterBoundaryResult(
                        status="HARD_BLOCKER",
                        subdivisions=subdivisions,
                        accepted_run=None,
                        best_valid_run=probe.mesh_run,
                        shooting_enthalpy_j_kg=str(probe_h),
                        failure_code="BLOCKED_OUTER_RECOVERY_HARD_BLOCKER",
                        diagnostics=probe.diagnostics,
                        search_trace=tuple(trace),
                        stats=stats,
                        h_low_final=str(bracket_lo),
                        h_high_final=str(bracket_hi),
                        float_h_low_hex=float(bracket_lo).hex(),
                        float_h_high_hex=float(bracket_hi).hex(),
                    )
                else:
                    bracket_hi = probe_h
            if recovered is not None:
                high_trial = recovered
                h_high = recovered.enthalpy_j_kg
        if high_trial.classification != "VALID_TRAJECTORY" or high_trial.mesh_run is None:
            if high_trial.classification == "HARD_BLOCKER":
                return IsolatedOuterBoundaryResult(
                    status="HARD_BLOCKER",
                    subdivisions=subdivisions,
                    accepted_run=None,
                    best_valid_run=high_trial.mesh_run,
                    shooting_enthalpy_j_kg=str(h_high),
                    failure_code="BLOCKED_OUTER_HIGH_ENDPOINT_HARD_BLOCKER",
                    diagnostics=high_trial.diagnostics,
                    search_trace=tuple(trace),
                    stats=stats,
                    h_low_final=str(h_low),
                    h_high_final=str(h_high),
                    float_h_low_hex=float(h_low).hex(),
                    float_h_high_hex=float(h_high).hex(),
                )
            return IsolatedOuterBoundaryResult(
                status="SETUP_FAILURE",
                subdivisions=subdivisions,
                accepted_run=None,
                best_valid_run=None,
                shooting_enthalpy_j_kg=None,
                failure_code="BLOCKED_OUTER_FEASIBLE_UPPER_ENDPOINT_NOT_FOUND",
                diagnostics=high_trial.diagnostics,
                search_trace=tuple(trace),
                stats=stats,
                h_low_final=str(h_low),
                h_high_final=str(h_high),
                float_h_low_hex=float(h_low).hex(),
                float_h_high_hex=float(h_high).hex(),
            )

    high_run = high_trial.mesh_run
    assert high_run is not None
    if (
        high_run.observables.terminal_boundary_residual_j_kg < 0
        or high_run.observables.terminal_boundary_residual_k < 0
    ):
        return IsolatedOuterBoundaryResult(
            status="SETUP_FAILURE",
            subdivisions=subdivisions,
            accepted_run=None,
            best_valid_run=high_run,
            shooting_enthalpy_j_kg=str(h_high),
            failure_code="BLOCKED_OUTER_HIGH_ENDPOINT_RESIDUAL_NEGATIVE",
            diagnostics=(),
            search_trace=tuple(trace),
            stats=stats,
            h_low_final=str(h_low),
            h_high_final=str(h_high),
            float_h_low_hex=float(h_low).hex(),
            float_h_high_hex=float(h_high).hex(),
        )

    seen_low = [h_low]
    seen_valid = [h_high]
    if _terminal_tolerance_pass(high_run):
        trace.append(
            _trace_step(
                iteration=0,
                h_low=h_low,
                h_high=h_high,
                h_trial=h_high,
                trial=high_trial,
                stats=stats,
                decision="ACCEPTED_INITIAL_HIGH_ENDPOINT",
            )
        )
        return IsolatedOuterBoundaryResult(
            status="ACCEPTED",
            subdivisions=subdivisions,
            accepted_run=high_run,
            best_valid_run=high_run,
            shooting_enthalpy_j_kg=str(h_high),
            failure_code=None,
            diagnostics=(),
            search_trace=tuple(trace),
            stats=stats,
            h_low_final=str(h_low),
            h_high_final=str(h_high),
            float_h_low_hex=float(h_low).hex(),
            float_h_high_hex=float(h_high).hex(),
        )

    iterations = 0
    while iterations < MAX_OUTER_BISECTION_ITERATIONS:
        with localcontext() as context:
            context.prec = 80
            h_mid = (h_low + h_high) / Decimal(2)
        decimal_collapsed = h_mid in (h_low, h_high)
        float_collapsed = float(h_mid) in (float(h_low), float(h_high))
        if decimal_collapsed or float_collapsed:
            shell_inlet_t = effective_shell_inlet_temperature_k()
            temp_floor = Decimal(
                str(
                    math.ulp(
                        float(high_run.observables.terminal_boundary_residual_k + shell_inlet_t)
                    )
                )
            )
            if _terminal_tolerance_pass(high_run):
                return IsolatedOuterBoundaryResult(
                    status="ACCEPTED",
                    subdivisions=subdivisions,
                    accepted_run=high_run,
                    best_valid_run=high_run,
                    shooting_enthalpy_j_kg=str(h_high),
                    failure_code=None,
                    diagnostics=(),
                    search_trace=tuple(trace),
                    stats=stats,
                    h_low_final=str(h_low),
                    h_high_final=str(h_high),
                    float_h_low_hex=float(h_low).hex(),
                    float_h_high_hex=float(h_high).hex(),
                )
            if float_collapsed and not decimal_collapsed:
                stepped = _binary64_enthalpy_step_toward(h_high, h_low)
                if stepped is not None:
                    iterations += 1
                    step_trial = trial_at(stepped, iterations)
                    if step_trial.classification == "HARD_BLOCKER":
                        trace.append(
                            _trace_step(
                                iteration=iterations,
                                h_low=h_low,
                                h_high=h_high,
                                h_trial=stepped,
                                trial=step_trial,
                                stats=stats,
                                decision="HARD_BLOCKER_BINARY64_STEP",
                            )
                        )
                        return IsolatedOuterBoundaryResult(
                            status="HARD_BLOCKER",
                            subdivisions=subdivisions,
                            accepted_run=None,
                            best_valid_run=high_run,
                            shooting_enthalpy_j_kg=str(h_high),
                            failure_code="BLOCKED_OUTER_BINARY64_HARD_BLOCKER",
                            diagnostics=step_trial.diagnostics,
                            search_trace=tuple(trace),
                            stats=stats,
                            h_low_final=str(h_low),
                            h_high_final=str(h_high),
                            float_h_low_hex=float(h_low).hex(),
                            float_h_high_hex=float(h_high).hex(),
                        )
                    if step_trial.classification == "LOW_SIDE_DOMAIN_INFEASIBLE":
                        try:
                            _assert_outer_classification_order(
                                seen_low, seen_valid, stepped, step_trial.classification
                            )
                        except _Stage3Failure as exc:
                            return IsolatedOuterBoundaryResult(
                                status="SETUP_FAILURE",
                                subdivisions=subdivisions,
                                accepted_run=None,
                                best_valid_run=high_run,
                                shooting_enthalpy_j_kg=str(h_high),
                                failure_code=exc.code,
                                diagnostics=exc.diagnostics,
                                search_trace=tuple(trace),
                                stats=stats,
                                h_low_final=str(h_low),
                                h_high_final=str(h_high),
                                float_h_low_hex=float(h_low).hex(),
                                float_h_high_hex=float(h_high).hex(),
                            )
                        h_low = stepped
                        seen_low.append(stepped)
                        trace.append(
                            _trace_step(
                                iteration=iterations,
                                h_low=h_low,
                                h_high=h_high,
                                h_trial=stepped,
                                trial=step_trial,
                                stats=stats,
                                decision="UPDATE_H_LOW_BINARY64_STEP",
                            )
                        )
                        continue
                    if (
                        step_trial.classification == "VALID_TRAJECTORY"
                        and step_trial.mesh_run is not None
                    ):
                        high_run = _apply_valid_outer_trial_update(
                            h_mid=stepped,
                            trial=step_trial,
                            seen_low=seen_low,
                            seen_valid=seen_valid,
                        )
                        h_high = stepped
                        seen_valid.append(stepped)
                        trace.append(
                            _trace_step(
                                iteration=iterations,
                                h_low=h_low,
                                h_high=h_high,
                                h_trial=stepped,
                                trial=step_trial,
                                stats=stats,
                                decision="UPDATE_H_HIGH_BINARY64_STEP",
                            )
                        )
                        if _terminal_tolerance_pass(high_run):
                            return IsolatedOuterBoundaryResult(
                                status="ACCEPTED",
                                subdivisions=subdivisions,
                                accepted_run=high_run,
                                best_valid_run=high_run,
                                shooting_enthalpy_j_kg=str(h_high),
                                failure_code=None,
                                diagnostics=(),
                                search_trace=tuple(trace),
                                stats=stats,
                                h_low_final=str(h_low),
                                h_high_final=str(h_high),
                                float_h_low_hex=float(h_low).hex(),
                                float_h_high_hex=float(h_high).hex(),
                            )
                        continue
            enthalpy_ulp = Decimal(str(math.ulp(float(h_high))))
            plateau = _outer_shooting_residual_plateau_evidence(h_low, h_high, trial_at, iterations)
            if (
                high_run.observables.terminal_boundary_residual_k - temp_floor
                > TERMINAL_TOLERANCE_K
            ):
                return IsolatedOuterBoundaryResult(
                    status="PRECISION_FLOOR",
                    subdivisions=subdivisions,
                    accepted_run=None,
                    best_valid_run=high_run,
                    shooting_enthalpy_j_kg=str(h_high),
                    failure_code="BLOCKED_OUTER_BOUNDARY_PRECISION_FLOOR_REACHED",
                    diagnostics=(
                        f"terminal_residual_k={high_run.observables.terminal_boundary_residual_k}",
                        f"terminal_residual_j_kg={high_run.observables.terminal_boundary_residual_j_kg}",
                        f"temperature_ulp_floor_k={temp_floor}",
                        f"enthalpy_ulp_floor_j_kg={enthalpy_ulp}",
                        f"h_low={h_low}",
                        f"h_high={h_high}",
                        f"decimal_collapsed={decimal_collapsed}",
                        f"float_collapsed={float_collapsed}",
                        *plateau,
                    ),
                    search_trace=tuple(trace),
                    stats=stats,
                    h_low_final=str(h_low),
                    h_high_final=str(h_high),
                    float_h_low_hex=float(h_low).hex(),
                    float_h_high_hex=float(h_high).hex(),
                )
            return IsolatedOuterBoundaryResult(
                status="PRECISION_FLOOR",
                subdivisions=subdivisions,
                accepted_run=None,
                best_valid_run=high_run,
                shooting_enthalpy_j_kg=str(h_high),
                failure_code="PRECISION_FLOOR_UNRESOLVED",
                diagnostics=(
                    f"terminal_residual_k={high_run.observables.terminal_boundary_residual_k}",
                    *plateau,
                ),
                search_trace=tuple(trace),
                stats=stats,
                h_low_final=str(h_low),
                h_high_final=str(h_high),
                float_h_low_hex=float(h_low).hex(),
                float_h_high_hex=float(h_high).hex(),
            )

        iterations += 1
        trial = trial_at(h_mid, iterations)
        if trial.classification == "HARD_BLOCKER":
            trace.append(
                _trace_step(
                    iteration=iterations,
                    h_low=h_low,
                    h_high=h_high,
                    h_trial=h_mid,
                    trial=trial,
                    stats=stats,
                    decision="HARD_BLOCKER_MIDPOINT",
                )
            )
            return IsolatedOuterBoundaryResult(
                status="HARD_BLOCKER",
                subdivisions=subdivisions,
                accepted_run=None,
                best_valid_run=high_run,
                shooting_enthalpy_j_kg=str(h_high),
                failure_code="BLOCKED_OUTER_MIDPOINT_HARD_BLOCKER",
                diagnostics=trial.diagnostics,
                search_trace=tuple(trace),
                stats=stats,
                h_low_final=str(h_low),
                h_high_final=str(h_high),
                float_h_low_hex=float(h_low).hex(),
                float_h_high_hex=float(h_high).hex(),
            )
        if trial.classification == "LOW_SIDE_DOMAIN_INFEASIBLE":
            try:
                _assert_outer_classification_order(
                    seen_low, seen_valid, h_mid, trial.classification
                )
            except _Stage3Failure as exc:
                trace.append(
                    _trace_step(
                        iteration=iterations,
                        h_low=h_low,
                        h_high=h_high,
                        h_trial=h_mid,
                        trial=trial,
                        stats=stats,
                        decision="NONMONOTONIC_LOW_SIDE",
                    )
                )
                return IsolatedOuterBoundaryResult(
                    status="SETUP_FAILURE",
                    subdivisions=subdivisions,
                    accepted_run=None,
                    best_valid_run=high_run,
                    shooting_enthalpy_j_kg=str(h_high),
                    failure_code=exc.code,
                    diagnostics=exc.diagnostics,
                    search_trace=tuple(trace),
                    stats=stats,
                    h_low_final=str(h_low),
                    h_high_final=str(h_high),
                    float_h_low_hex=float(h_low).hex(),
                    float_h_high_hex=float(h_high).hex(),
                )
            h_low = h_mid
            seen_low.append(h_mid)
            trace.append(
                _trace_step(
                    iteration=iterations,
                    h_low=h_low,
                    h_high=h_high,
                    h_trial=h_mid,
                    trial=trial,
                    stats=stats,
                    decision="UPDATE_H_LOW",
                )
            )
            continue
        if trial.classification != "VALID_TRAJECTORY" or trial.mesh_run is None:
            trace.append(
                _trace_step(
                    iteration=iterations,
                    h_low=h_low,
                    h_high=h_high,
                    h_trial=h_mid,
                    trial=trial,
                    stats=stats,
                    decision="INVALID_CLASSIFICATION",
                )
            )
            return IsolatedOuterBoundaryResult(
                status="SETUP_FAILURE",
                subdivisions=subdivisions,
                accepted_run=None,
                best_valid_run=high_run,
                shooting_enthalpy_j_kg=str(h_high),
                failure_code="BLOCKED_OUTER_TRIAL_CLASSIFICATION_INVALID",
                diagnostics=trial.diagnostics + (trial.classification,),
                search_trace=tuple(trace),
                stats=stats,
                h_low_final=str(h_low),
                h_high_final=str(h_high),
                float_h_low_hex=float(h_low).hex(),
                float_h_high_hex=float(h_high).hex(),
            )
        high_run = _apply_valid_outer_trial_update(
            h_mid=h_mid,
            trial=trial,
            seen_low=seen_low,
            seen_valid=seen_valid,
        )
        h_high = h_mid
        seen_valid.append(h_mid)
        term_pass = _terminal_tolerance_pass(high_run)
        trace.append(
            _trace_step(
                iteration=iterations,
                h_low=h_low,
                h_high=h_high,
                h_trial=h_mid,
                trial=trial,
                stats=stats,
                decision="ACCEPTED_TERMINAL" if term_pass else "UPDATE_H_HIGH",
            )
        )
        if term_pass:
            return IsolatedOuterBoundaryResult(
                status="ACCEPTED",
                subdivisions=subdivisions,
                accepted_run=high_run,
                best_valid_run=high_run,
                shooting_enthalpy_j_kg=str(h_high),
                failure_code=None,
                diagnostics=(),
                search_trace=tuple(trace),
                stats=stats,
                h_low_final=str(h_low),
                h_high_final=str(h_high),
                float_h_low_hex=float(h_low).hex(),
                float_h_high_hex=float(h_high).hex(),
            )

    if _terminal_tolerance_pass(high_run):
        trace.append(
            _trace_step(
                iteration=iterations,
                h_low=h_low,
                h_high=h_high,
                h_trial=h_high,
                trial=_OuterTrial("VALID_TRAJECTORY", h_high, mesh_run=high_run),
                stats=stats,
                decision="ACCEPTED_AFTER_ITERATION_BUDGET",
            )
        )
        return IsolatedOuterBoundaryResult(
            status="ACCEPTED",
            subdivisions=subdivisions,
            accepted_run=high_run,
            best_valid_run=high_run,
            shooting_enthalpy_j_kg=str(h_high),
            failure_code=None,
            diagnostics=(),
            search_trace=tuple(trace),
            stats=stats,
            h_low_final=str(h_low),
            h_high_final=str(h_high),
            float_h_low_hex=float(h_low).hex(),
            float_h_high_hex=float(h_high).hex(),
        )
    return IsolatedOuterBoundaryResult(
        status="RESOURCE_EXHAUSTION",
        subdivisions=subdivisions,
        accepted_run=None,
        best_valid_run=high_run,
        shooting_enthalpy_j_kg=str(h_high),
        failure_code="BLOCKED_OUTER_BOUNDARY_RESOURCE_EXHAUSTION",
        diagnostics=(f"maximum_iterations={MAX_OUTER_BISECTION_ITERATIONS}",),
        search_trace=tuple(trace),
        stats=stats,
        h_low_final=str(h_low),
        h_high_final=str(h_high),
        float_h_low_hex=float(h_low).hex(),
        float_h_high_hex=float(h_high).hex(),
    )


__all__ = [
    "IsolatedOuterBoundaryResult",
    "OuterSearchStepRecord",
    "solve_outer_boundary_from_trial_isolated",
]
