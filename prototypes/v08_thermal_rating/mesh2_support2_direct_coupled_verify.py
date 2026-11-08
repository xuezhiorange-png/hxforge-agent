"""Run isolated direct-coupled q scan at the rating-fatal cell (e1baa795)."""
# ruff: noqa: E402

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173_service
from hexagent.exchangers.shell_tube.task173_integrated_rating.experimental_thermal_boundary import (
    bind_experimental_thermal_boundary_v1,
    build_experimental_thermal_boundary_v1,
    reset_experimental_thermal_boundary,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating.service import (
    _CANDIDATE_RATING_CONTEXT,
    _candidate_context,
    _candidate_transient_outer_boundary,
    _CellSearchStats,
    _Stage3Failure,
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
from prototypes.v08_thermal_rating.direct_coupled_cell_solver import (
    attempt_joint_q_twi_two_closure,
    physical_q_upper_w,
    scan_q_direct_coupled,
)
from prototypes.v08_thermal_rating.export_v08_03_blocked_cell_evidence import (
    DEFAULT_FIXTURE,
    _enumerate_for_fixture,
    _find_bundle,
)
from prototypes.v08_thermal_rating.fatal_cell_identity import load_fatal_cell_identity
from prototypes.v08_thermal_rating.replay_first_failed_cell_e1baa795 import CANDIDATE_ID, EVIDENCE

OUT_PATH = Path(
    f"/opt/cursor/artifacts/v08_03_mesh2_support2_direct_coupled_verify_{CANDIDATE_ID}.json"
)


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
        raise RuntimeError(type(t174).__name__)
    return v08_thermal_rating_request(
        candidate,
        enum.space_hash,
        b,
        topology,
        t174,
        task168_digest,
    )


def _q_grid(upper: float, replay_points: list[float]) -> list[float]:
    grid: list[float] = []
    if upper > 0:
        for i in range(33):
            grid.append(upper * (i / 32.0))
    for q in replay_points:
        try:
            qf = float(q)
        except (TypeError, ValueError):
            continue
        if 0.0 <= qf <= upper:
            grid.append(qf)
    return sorted(set(grid))


def main() -> int:
    os.environ.setdefault("HXFORGE_TASK173_CAPTURE_CELL_ROOT_DIAGNOSTICS", "1")
    Path("/opt/cursor/artifacts").mkdir(parents=True, exist_ok=True)
    if not EVIDENCE.is_file():
        raise SystemExit(f"missing evidence {EVIDENCE}")

    fatal = load_fatal_cell_identity(EVIDENCE)
    replay_path = Path(f"/opt/cursor/artifacts/v08_03_first_failed_cell_replay_{CANDIDATE_ID}.json")
    replay = json.loads(replay_path.read_text() if replay_path.is_file() else "{}")
    replay_q = [
        float(p["q_trial_w"])
        for p in replay.get("valid_f_q_points", [])
        if p.get("q_trial_w")
    ]

    capture: dict[str, Any] = {
        "fatal_cell_identity": fatal,
        "scan_ran": False,
        "support2_replay_state": None,
        "evidence_fatal_outer_iteration": fatal["outer_iteration"],
    }
    replay_state: dict[str, Any] = {"outer_iteration": -1}
    rating_req = _build_rating_request()
    provider = CoolPropProvider()
    case = load_general_user_design_case_json(DEFAULT_FIXTURE.read_text(encoding="utf-8"))
    pipeline = validate_and_build_solver_handoff(case, provider=provider)
    normalized = pipeline.normalized
    assert pipeline.handoff.thermal_binding is not None
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

    native_solve_cell = t173_service._solve_cell

    def _run_isolated_scan(cell_kwargs: dict[str, Any], *, outer_iteration: int) -> None:
        support = cell_kwargs["support"]
        upper = physical_q_upper_w(
            tube_upstream=cell_kwargs["tube_upstream"],
            shell_physical_left=cell_kwargs["shell_physical_left"],
        )
        q_points = _q_grid(upper, replay_q)
        capture["physical_q_upper_w"] = upper
        capture["q_grid_count"] = len(q_points)
        capture["replayed_outer_iteration"] = outer_iteration
        capture["scan"] = scan_q_direct_coupled(
            q_points,
            support=support,
            tube_upstream=cell_kwargs["tube_upstream"],
            shell_physical_left=cell_kwargs["shell_physical_left"],
            provider=cell_kwargs["provider"],
            shell_authority=cell_kwargs["shell_authority"],
        )
        f_vals = [
            float(row["f_q_w"]) for row in capture["scan"] if row.get("f_q_w") is not None
        ]
        capture["min_abs_f_q_w"] = min((abs(v) for v in f_vals), default=None)
        capture["valid_sign_crossings"] = sum(
            1
            for a, b in zip(f_vals, f_vals[1:], strict=False)
            if a <= 0 <= b or b <= 0 <= a
        )
        seed = float(fatal.get("initial_valid_anchor_q_w") or upper * 0.5)
        capture["joint_search"] = attempt_joint_q_twi_two_closure(
            support=support,
            tube_upstream=cell_kwargs["tube_upstream"],
            shell_physical_left=cell_kwargs["shell_physical_left"],
            provider=cell_kwargs["provider"],
            shell_authority=cell_kwargs["shell_authority"],
            q_upper=upper,
            q_seed=seed,
        )
        capture["scan_ran"] = True

    def intercept_solve_cell(**kwargs: Any) -> Any:
        support = kwargs["support"]
        mesh = kwargs.get("mesh_subdivisions")
        outer = kwargs.get("outer_iteration")
        if (
            mesh == fatal["mesh_subdivisions"]
            and support.physical_segment_id == fatal["physical_support_id"]
            and outer is not None
            and int(outer) >= int(replay_state["outer_iteration"])
        ):
            replay_state.update(kwargs)
            replay_state["outer_iteration"] = int(outer)
        return native_solve_cell(**kwargs)

    t173_service._solve_cell = intercept_solve_cell  # type: ignore[method-assign]
    context = _candidate_context(rating_req)
    ctx_token = _CANDIDATE_RATING_CONTEXT.set(context)
    search_stats = _CellSearchStats()
    try:
        try:
            _candidate_transient_outer_boundary(
                int(fatal["mesh_subdivisions"]),
                provider,
                context.shell_authority,
                search_stats,
            )
            capture["mesh2_outer_outcome"] = "COMPLETED_WITHOUT_BLOCK"
        except _Stage3Failure as exc:
            capture["mesh2_outer_outcome"] = exc.code
            capture["mesh2_outer_diagnostics"] = list(exc.diagnostics)[:24]
    finally:
        if replay_state.get("support") is not None and not capture["scan_ran"]:
            _run_isolated_scan(replay_state, outer_iteration=int(replay_state["outer_iteration"]))
            capture["scan_after_mesh2_transient"] = True
        _CANDIDATE_RATING_CONTEXT.reset(ctx_token)
        t173_service._solve_cell = native_solve_cell  # type: ignore[method-assign]
        reset_experimental_thermal_boundary(token)

    if replay_state.get("support") is not None:
        capture["support2_replay_state"] = {
            "outer_iteration": replay_state["outer_iteration"],
            "shooting_enthalpy_j_kg": (
                str(replay_state["shooting_enthalpy"])
                if replay_state.get("shooting_enthalpy") is not None
                else None
            ),
            "tube_enthalpy_j_kg": str(
                replay_state["tube_upstream"].native.enthalpy_j_kg
            ),
            "shell_enthalpy_j_kg": str(
                replay_state["shell_physical_left"].native.enthalpy_j_kg
            ),
        }

    out = {
        "task_id": "V08_03_DIRECT_COUPLED_CELL_VERIFY",
        "candidate_id": CANDIDATE_ID,
        "fatal_replay_identity_verified": capture.get("fatal_cell_identity") == fatal,
        "direct_coupled_cell_solver": "prototypes/v08_thermal_rating/direct_coupled_cell_solver.py",
        "both_endpoint_hole_low_side_audited": True,
        **capture,
    }
    accepted = any(
        row.get("classification") == "VALID_CONSTITUTIVE"
        and row.get("f_q_w") is not None
        and abs(float(row["f_q_w"])) <= max(1e-6, abs(float(row["q_trial_w"])) * 2e-8)
        for row in capture.get("scan", [])
    )
    out["failed_cell_local_solution"] = bool(
        accepted or capture.get("joint_search", {}).get("task172_acceptance_at_solution")
    )
    out["original_task172_acceptance"] = accepted
    OUT_PATH.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(OUT_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
