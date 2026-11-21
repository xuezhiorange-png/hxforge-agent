"""Isolation callback-budget experiment for candidate e1baa795 (does not change production caps)."""

from __future__ import annotations

import json
import os
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

from hexagent.exchangers.shell_tube.task172_local_runtime import service as task172_service
from hexagent.exchangers.shell_tube.task172_local_runtime.models import (
    Task172LocalResult,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating.experimental_thermal_boundary import (
    bind_experimental_thermal_boundary_v1,
    build_experimental_thermal_boundary_v1,
    reset_experimental_thermal_boundary,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating.models import Task173BlockedResult
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
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_general_user_case.loader import load_general_user_design_case_json
from prototypes.v08_general_user_case.pipeline import validate_and_build_solver_handoff
from prototypes.v08_thermal_rating.export_v08_03_blocked_cell_evidence import (
    DEFAULT_FIXTURE,
    _enumerate_for_fixture,
    _find_bundle,
)

CANDIDATE_ID = "e1baa795-9cf5-5718-8fa8-0688d2102c5c"
BUDGETS = (48, 96, 192)
_ISOLATION_WIDE_CALLBACK_CAP = 48
_SOLVE_ATTEMPT_UNPATCHED: Any = None


def _wide_budget(callback_cap: int) -> task172_service._SolverBudget:
    base = task172_service._WIDE_EXPERIMENTAL_SOLVER_BUDGET
    return replace(base, callback_cap=callback_cap, max_nfev=callback_cap // 2)


def _install_wide_callback_cap_patcher() -> None:
    """Monkeypatch wide attempts once; vary cap via _ISOLATION_WIDE_CALLBACK_CAP."""

    global _SOLVE_ATTEMPT_UNPATCHED
    if _SOLVE_ATTEMPT_UNPATCHED is not None:
        return
    _SOLVE_ATTEMPT_UNPATCHED = task172_service._solve_attempt

    def patched_attempt(
        request: Any,
        provider: Any,
        *,
        method: Any,
        budget: task172_service._SolverBudget = task172_service._FROZEN_SOLVER_BUDGET,
        initial_guess: tuple[float, float, float] | None = None,
    ) -> Any:
        active_budget = budget
        if budget.wide_experimental:
            active_budget = _wide_budget(_ISOLATION_WIDE_CALLBACK_CAP)
        return _SOLVE_ATTEMPT_UNPATCHED(
            request,
            provider,
            method=method,
            budget=active_budget,
            initial_guess=initial_guess,
        )

    task172_service._solve_attempt = patched_attempt  # type: ignore[method-assign]


def _build_rating_request() -> Any:
    normalized, handoff, enum, task168_digest = _enumerate_for_fixture()
    bundle_row = _find_bundle(enum, CANDIDATE_ID)
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
            task166=b.task166_result,
        ),
    )
    if type(t174) is not Task174SuccessResult:
        raise RuntimeError(f"task174 blocked: {type(t174).__name__}")
    return v08_thermal_rating_request(
        candidate,
        enum.space_hash,
        b,
        topology,
        t174,
        task168_digest,
    )


def _run_one_budget(
    cap: int,
    provider: CoolPropProvider,
    rating_req: Any,
) -> dict[str, Any]:
    global _ISOLATION_WIDE_CALLBACK_CAP
    _ISOLATION_WIDE_CALLBACK_CAP = cap
    os.environ["HXFORGE_TASK172_COUPLED_ACCOUNTING"] = "1"
    accounting_path = Path(f"/opt/cursor/artifacts/e1baa795_coupled_accounting_{cap}.json")
    os.environ["HXFORGE_TASK172_ACCOUNTING_OUT"] = str(accounting_path)

    case = load_general_user_design_case_json(DEFAULT_FIXTURE.read_text(encoding="utf-8"))
    pipeline = validate_and_build_solver_handoff(case, provider=provider)
    normalized = pipeline.normalized
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

    started = time.perf_counter()
    token = bind_experimental_thermal_boundary_v1(exp)
    try:
        outcome = validate_candidate_rating(rating_req, provider)
    finally:
        reset_experimental_thermal_boundary(token)
    wall_s = time.perf_counter() - started

    record: dict[str, Any] = {
        "callback_cap_isolation": cap,
        "wall_seconds": wall_s,
        "task173_status": getattr(outcome, "status", type(outcome).__name__),
    }
    if type(outcome) is Task173BlockedResult:
        record["task173_failure_code"] = outcome.failure_code
        record["task173_diagnostics"] = list(outcome.diagnostics)[:12]
    elif type(outcome) is not Task172LocalResult:
        record["note"] = type(outcome).__name__

    if accounting_path.is_file():
        record["last_coupled_accounting"] = json.loads(accounting_path.read_text())
    else:
        record["last_coupled_accounting"] = None

    stats_path = Path(
        "/opt/cursor/artifacts/v08_03_blocked_cell_evidence_e1baa795-9cf5-5718-8fa8-0688d2102c5c.json"
    )
    if stats_path.is_file():
        stats = json.loads(stats_path.read_text()).get("task173_cell_search_stats") or {}
        record["reference_hole_count"] = stats.get("task172_numerical_hole_count")

    return record


def main() -> int:
    Path("/opt/cursor/artifacts").mkdir(parents=True, exist_ok=True)
    _install_wide_callback_cap_patcher()
    provider = CoolPropProvider()
    rating_req = _build_rating_request()
    results = []
    for cap in BUDGETS:
        print(f"running isolation cap={cap}", flush=True)
        results.append(_run_one_budget(cap, provider, rating_req))

    out = {
        "task_id": "V08_03_ISOLATED_CALLBACK_BUDGET_EXPERIMENT",
        "candidate_id": CANDIDATE_ID,
        "geometry_projection_hash": (
            "a98e73756a24cc181f89ccc4f97df42d2afac717056b2e5d570e83d6da472973"
        ),
        "production_wide_cap_unchanged": task172_service._WIDE_EXPERIMENTAL_CALLBACK_CAP,
        "budgets_tested": list(BUDGETS),
        "runs": results,
    }
    out_path = Path("/opt/cursor/artifacts/v08_03_isolated_budget_experiment_e1baa795.json")
    out_path.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
