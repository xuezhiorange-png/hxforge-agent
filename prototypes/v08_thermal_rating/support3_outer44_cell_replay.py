"""Replay support 3 @ outer 44 for e1baa795 — endpoint holes and F(q) map (V08-03)."""
# ruff: noqa: E402

from __future__ import annotations

import json
import os
import sys
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
from hexagent.exchangers.shell_tube.task173_integrated_rating.service import (
    _CANDIDATE_RATING_CONTEXT,
    _candidate_context,
    _candidate_transient_outer_boundary,
    _CellSearchStats,
    _Stage3Failure,
)
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_general_user_case.loader import load_general_user_design_case_json
from prototypes.v08_general_user_case.pipeline import validate_and_build_solver_handoff
from prototypes.v08_thermal_rating.direct_coupled_cell_solver import (
    physical_q_upper_w,
    probe_q_direct_coupled,
    scan_q_direct_coupled,
)
from prototypes.v08_thermal_rating.export_v08_03_blocked_cell_evidence import (
    DEFAULT_FIXTURE,
    _enumerate_for_fixture,
)
from prototypes.v08_thermal_rating.mesh2_support2_direct_coupled_verify import (
    CANDIDATE_ID,
    _build_rating_request,
)
from prototypes.v08_thermal_rating.true_three_equation_cell_coupling import (
    compare_same_request_production_vs_frozen_trf,
)

TARGET_SUPPORT_SUFFIX = "support:3"
TARGET_OUTER = 44
OUT = Path(f"/opt/cursor/artifacts/v08_03_support3_outer44_replay_{CANDIDATE_ID}.json")


def main() -> int:
    os.environ.setdefault("HXFORGE_TASK173_CAPTURE_CELL_ROOT_DIAGNOSTICS", "1")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    replay_state: dict[str, Any] = {"outer_iteration": -1}
    capture: dict[str, Any] = {
        "task_id": "V08_03_SUPPORT3_OUTER44_REPLAY",
        "candidate_id": CANDIDATE_ID,
        "target_support_suffix": TARGET_SUPPORT_SUFFIX,
        "target_outer_iteration": TARGET_OUTER,
    }
    provider = CoolPropProvider()
    _enumerate_for_fixture()
    normalized = validate_and_build_solver_handoff(
        load_general_user_design_case_json(DEFAULT_FIXTURE.read_text(encoding="utf-8")),
        provider=provider,
    ).normalized
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
    native = t173._solve_cell
    rating_req = _build_rating_request()
    ctx = _candidate_context(rating_req)
    ct = _CANDIDATE_RATING_CONTEXT.set(ctx)

    def intercept(**kwargs: Any) -> Any:
        s = kwargs["support"]
        outer = kwargs.get("outer_iteration")
        if (
            TARGET_SUPPORT_SUFFIX in s.physical_segment_id
            and outer is not None
            and int(outer) >= TARGET_OUTER
        ):
            replay_state.update(kwargs)
            replay_state["outer_iteration"] = int(outer)
        return native(**kwargs)

    t173._solve_cell = intercept  # type: ignore[method-assign]
    try:
        try:
            _candidate_transient_outer_boundary(
                1, provider, ctx.shell_authority, _CellSearchStats()
            )
        except _Stage3Failure as exc:
            capture["mesh_outer_outcome"] = exc.code
            capture["mesh_outer_diagnostics"] = list(exc.diagnostics)[:12]
    finally:
        if replay_state.get("support") is not None:
            upper = physical_q_upper_w(
                tube_upstream=replay_state["tube_upstream"],
                shell_physical_left=replay_state["shell_physical_left"],
            )
            q_grid = [0.0] + [upper * i / 32 for i in range(1, 33)]
            grid = scan_q_direct_coupled(
                q_grid,
                support=replay_state["support"],
                tube_upstream=replay_state["tube_upstream"],
                shell_physical_left=replay_state["shell_physical_left"],
                provider=replay_state["provider"],
                shell_authority=replay_state["shell_authority"],
            )
            endpoint: dict[str, Any] = {}
            for q in (0.0, upper):
                probe = probe_q_direct_coupled(
                    q,
                    support=replay_state["support"],
                    tube_upstream=replay_state["tube_upstream"],
                    shell_physical_left=replay_state["shell_physical_left"],
                    provider=replay_state["provider"],
                    shell_authority=replay_state["shell_authority"],
                )
                endpoint[str(q)] = probe
            capture.update(
                {
                    "replayed_outer_iteration": replay_state["outer_iteration"],
                    "physical_support_id": replay_state["support"].physical_segment_id,
                    "shooting_enthalpy_j_kg": str(replay_state.get("shooting_enthalpy")),
                    "physical_q_upper_w": upper,
                    "f_q_scan": grid,
                    "endpoint_probes": endpoint,
                }
            )
            for label, q in [("lower", 0.0), ("upper", upper)]:
                evaluation = t173._cell_evaluation(
                    q,
                    support=replay_state["support"],
                    tube_upstream=replay_state["tube_upstream"],
                    shell_physical_left=replay_state["shell_physical_left"],
                    provider=replay_state["provider"],
                    shell_authority=replay_state["shell_authority"],
                )
                comp = compare_same_request_production_vs_frozen_trf(
                    evaluation.task172_request, provider
                )
                capture[f"same_request_{label}"] = comp
        _CANDIDATE_RATING_CONTEXT.reset(ct)
        t173._solve_cell = native  # type: ignore[method-assign]
        reset_experimental_thermal_boundary(tok)

    OUT.write_text(json.dumps(capture, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
