"""V08-03 diagnostic: q=0 Task172 chain and outer shooting enthalpy bracket."""
# ruff: noqa: E402, E501, F401, F841, I001

from __future__ import annotations

import json
import math
import os
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(_REPO), str(_REPO / "src")]

from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173
from hexagent.exchangers.shell_tube.task173_integrated_rating.experimental_thermal_boundary import (
    bind_experimental_thermal_boundary_v1,
    build_experimental_thermal_boundary_v1,
    reset_experimental_thermal_boundary,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating.models import TERMINAL_TOLERANCE_K
from hexagent.exchangers.shell_tube.task173_integrated_rating.service import (
    _CANDIDATE_RATING_CONTEXT,
    _CellSearchStats,
    _Stage3Failure,
    _Task172NumericalHole,
    _candidate_context,
    _candidate_transient_outer_boundary,
    _cell_evaluation,
    _solve_outer_boundary_from_trial,
    _terminal_tolerance_pass,
    effective_hot_ceiling_enthalpy_j_kg,
    effective_shell_cold_inlet_enthalpy_j_kg,
    effective_shell_inlet_temperature_k,
)
from hexagent.exchangers.shell_tube.task172_local_runtime.service import audit_task172_solver_chain
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.export_v08_03_blocked_cell_evidence import (
    _enumerate_for_fixture,
    _find_bundle,
)
from prototypes.v08_thermal_rating.mesh2_support2_direct_coupled_verify import (
    CANDIDATE_ID,
    _build_rating_request,
)
from prototypes.v08_thermal_rating.support3_outer44_cell_replay import (
    TARGET_MESH,
    TARGET_OUTER,
    TARGET_SUPPORT_SUFFIX,
    _endpoint_audits,
    _task172_request_at_q,
)

OUT = Path("/opt/cursor/artifacts/v08_03_outer_shooting_diagnostic_e1baa795.json")


def capture_support3_cell(provider: CoolPropProvider, ctx: Any) -> dict[str, Any]:
    hit: dict[str, Any] = {}
    native = t173._solve_cell

    def intercept(**kwargs: Any) -> Any:
        support = kwargs["support"]
        if (
            kwargs.get("mesh_subdivisions") == TARGET_MESH
            and kwargs.get("outer_iteration") == TARGET_OUTER
            and TARGET_SUPPORT_SUFFIX in support.physical_segment_id
        ):
            hit.clear()
            hit.update(kwargs)
        return native(**kwargs)

    t173._solve_cell = intercept  # type: ignore[method-assign]
    outer_error: _Stage3Failure | None = None
    try:
        try:
            _candidate_transient_outer_boundary(
                TARGET_MESH, provider, ctx.shell_authority, _CellSearchStats()
            )
        except _Stage3Failure as exc:
            outer_error = exc
    finally:
        t173._solve_cell = native  # type: ignore[method-assign]
    return {"hit": hit, "outer_error": outer_error}


def outer_bracket_audit(
    hit: dict[str, Any], provider: CoolPropProvider, ctx: Any, outer_iter: int
) -> dict[str, Any]:
    h_low = effective_shell_cold_inlet_enthalpy_j_kg()
    h_high = effective_hot_ceiling_enthalpy_j_kg()
    shell_inlet_t = effective_shell_inlet_temperature_k()
    t_floor = Decimal(str(math.ulp(float(shell_inlet_t))))
    trials: list[dict[str, Any]] = []

    def trial_at(enthalpy: Decimal, iteration: int) -> Any:
        control = t173._CandidateTransientControl(
            mode="LEFT_BRANCH",
            mesh_subdivisions=TARGET_MESH,
            outer_iteration=iteration,
            shooting_enthalpy=enthalpy,
        )
        token = t173._CANDIDATE_TRANSIENT_CONTROL.set(control)
        ctx_token = _CANDIDATE_RATING_CONTEXT.get()
        try:
            trial = t173._outer_trial(
                TARGET_MESH,
                enthalpy,
                provider,
                ctx.shell_authority,
                iteration,
                _CellSearchStats(),
                capture_diagnostics=False,
            )
        finally:
            t173._CANDIDATE_TRANSIENT_CONTROL.reset(token)
        entry = {
            "iteration": iteration,
            "h_decimal": str(enthalpy),
            "h_float": float(enthalpy),
            "classification": trial.classification,
        }
        if trial.mesh_run is not None:
            obs = trial.mesh_run.observables
            entry.update(
                {
                    "terminal_residual_k": float(obs.terminal_boundary_residual_k),
                    "terminal_residual_j_kg": float(obs.terminal_boundary_residual_j_kg),
                    "terminal_pass": _terminal_tolerance_pass(trial.mesh_run),
                    "temperature_ulp_floor_k": float(
                        Decimal(str(math.ulp(float(shell_inlet_t + obs.terminal_boundary_residual_k))))
                    ),
                }
            )
        trials.append(entry)
        return trial

    low = trial_at(h_low, 0)
    high = trial_at(h_high, 0)
    record = {
        "h_low": str(h_low),
        "h_high": str(h_high),
        "float_h_low": float(h_low),
        "float_h_high": float(h_high),
        "low_classification": low.classification,
        "high_classification": high.classification,
        "terminal_temperature_tolerance_k": str(TERMINAL_TOLERANCE_K),
        "shell_inlet_temperature_ulp_k": float(t_floor),
        "trials_at_captured_outer": trials,
    }
    if high.mesh_run is not None:
        obs = high.mesh_run.observables
        record["high_terminal_residual_k"] = float(obs.terminal_boundary_residual_k)
        record["high_terminal_residual_j_kg"] = float(obs.terminal_boundary_residual_j_kg)
        record["high_terminal_pass"] = _terminal_tolerance_pass(high.mesh_run)
        t_ulp = Decimal(
            str(math.ulp(float(shell_inlet_t + obs.terminal_boundary_residual_k)))
        )
        record["temperature_ulp_floor_k"] = float(t_ulp)
        record["residual_minus_ulp"] = float(obs.terminal_boundary_residual_k - t_ulp)
        record["blocked_precision_floor"] = (
            not _terminal_tolerance_pass(high.mesh_run)
            and obs.terminal_boundary_residual_k - t_ulp > TERMINAL_TOLERANCE_K
        )
    record["h_mid_at_collapse"] = str((h_low + h_high) / Decimal(2))
    record["float_h_mid"] = float((h_low + h_high) / Decimal(2))
    return record


def main() -> int:
    os.environ.setdefault("HXFORGE_TASK173_CAPTURE_CELL_ROOT_DIAGNOSTICS", "0")
    provider = CoolPropProvider()
    normalized, _, enum, _ = _enumerate_for_fixture()
    _find_bundle(enum, CANDIDATE_ID)
    ctx_rating = _build_rating_request()
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
    tok = bind_experimental_thermal_boundary_v1(exp)
    ctx = _candidate_context(ctx_rating)
    ct = _CANDIDATE_RATING_CONTEXT.set(ctx)
    payload: dict[str, Any] = {"candidate_id": CANDIDATE_ID}
    try:
        cap = capture_support3_cell(provider, ctx)
        hit = cap["hit"]
        err = cap["outer_error"]
        if err is not None:
            payload["mesh_outer_outcome"] = err.code
            payload["mesh_outer_diagnostics"] = list(err.diagnostics)[:24]
        if hit:
            payload["outer_shooting_bracket"] = outer_bracket_audit(hit, provider, ctx, TARGET_OUTER)
            payload["endpoint_audits"] = _endpoint_audits(hit, provider)
            q0_chain: dict[str, Any] = {}
            try:
                ev = _cell_evaluation(
                    0.0,
                    support=hit["support"],
                    tube_upstream=hit["tube_upstream"],
                    shell_physical_left=hit["shell_physical_left"],
                    provider=provider,
                    shell_authority=hit["shell_authority"],
                )
                q172 = ev.task172_result.signed_q_hot_to_cold_w
                q0_chain["production_cell_evaluation"] = "VALID"
                q0_chain["trial_q_w"] = 0.0
                q0_chain["task172_q_w"] = float(q172)
                q0_chain["f_q_w"] = float(Decimal("0") - q172)
                q0_chain["task172_result_hash"] = ev.task172_result.result_hash
            except _Task172NumericalHole as hole:
                q0_chain["production_cell_evaluation"] = "TASK172_NUMERICAL_HOLE"
                q0_chain["blocked_result_hash"] = hole.blocked_result_hash
                q0_chain["solver_trace_steps"] = [
                    e.get("step") for e in hole.last_task172_solver_trace
                ]
            req0 = _task172_request_at_q(
                0.0,
                support=hit["support"],
                tube_upstream=hit["tube_upstream"],
                shell_physical_left=hit["shell_physical_left"],
                provider=provider,
                shell_authority=hit["shell_authority"],
            )
            q0_chain["audit"] = audit_task172_solver_chain(req0, provider, trial_q_w=0.0)
            payload["q0_production_chain"] = q0_chain
    finally:
        _CANDIDATE_RATING_CONTEXT.reset(ct)
        reset_experimental_thermal_boundary(tok)
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
