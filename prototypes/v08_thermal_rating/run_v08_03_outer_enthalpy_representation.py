#!/usr/bin/env python3
"""V08-03 TASK173_OUTER_ENTHALPY_NUMERICAL_REPRESENTATION — before/after isolated run."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(_REPO), str(_REPO / "src")]

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.task173_integrated_rating.models import TERMINAL_TOLERANCE_K
from hexagent.exchangers.shell_tube.task173_integrated_rating.service import (
    _terminal_tolerance_pass,
)
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import (
    final_trajectory_task172_holes,
    isolated_mesh_acceptance_gate,
    load_case_bindings,
    resolve_candidate_bindings_by_id,
    solve_isolated_outer_boundary,
)
from prototypes.v08_thermal_rating.case_identity_v08 import FIXTURE_250
from prototypes.v08_thermal_rating.outer_enthalpy_representation_v08 import (
    EXECUTION_STAGE,
    TASK_ID,
    conservative_enthalpy_authority_pass,
    property_state_consistency_pass,
    solve_isolated_outer_boundary_experimental,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating.candidate_models import (
    candidate_rating_request_hash,
)

CANDIDATE_ID = "e1baa795-9cf5-5718-8fa8-0688d2102c5c"
OUT = Path("/opt/cursor/artifacts/v08_03_outer_enthalpy_representation.json")


def _mesh_summary(
    label: str,
    bindings: Any,
    provider: CoolPropProvider,
    subdivisions: int,
    *,
    experimental: bool,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    if experimental:
        iso, rep, elapsed = solve_isolated_outer_boundary_experimental(
            bindings, provider, subdivisions=subdivisions
        )
        auth_pass = conservative_enthalpy_authority_pass(rep)
        prop_pass = property_state_consistency_pass(rep)
        prop_err = rep.max_property_conversion_error_j_kg
        audit_count = len(rep.audit_rows)
    else:
        iso = solve_isolated_outer_boundary(bindings, provider, subdivisions=subdivisions)
        elapsed = time.perf_counter() - t0
        auth_pass = False
        prop_pass = False
        prop_err = None
        audit_count = 0
    run = iso.accepted_run or iso.best_valid_run
    gate = isolated_mesh_acceptance_gate(bindings, provider, iso)
    obs = run.observables if run is not None else None
    holes = (
        final_trajectory_task172_holes(
            bindings,
            provider,
            subdivisions=subdivisions,
            shooting_enthalpy_j_kg=iso.shooting_enthalpy_j_kg,
        )
        if iso.shooting_enthalpy_j_kg
        else iso.stats.task172_numerical_hole_count
    )
    term_t = str(obs.terminal_boundary_residual_k) if obs else None
    term_h = str(obs.terminal_boundary_residual_j_kg) if obs else None
    term_pass = _terminal_tolerance_pass(run) if run is not None else False
    energy = str(obs.energy_balance_residual_w) if obs else None
    duty = str(obs.total_duty_w) if obs else None
    cp = float(run.faces_shell[-1].property_snapshot.cp_j_kg_k) if run else 0.0
    cold_h = str(run.shooting_enthalpy) if run else None
    allowed_h = None
    if run is not None and obs is not None:
        import math
        from decimal import Decimal

        from hexagent.exchangers.shell_tube.task173_integrated_rating.service import (
            effective_shell_cold_inlet_enthalpy_j_kg,
        )

        ch = effective_shell_cold_inlet_enthalpy_j_kg()
        h_floor = Decimal(str(math.ulp(float(ch))))
        allowed_h = str(cp * float(TERMINAL_TOLERANCE_K) + float(h_floor))
    return {
        "label": label,
        "experimental": experimental,
        "subdivisions": subdivisions,
        "gate": gate,
        "outer_status": iso.status,
        "failure_code": iso.failure_code,
        "terminal_residual_k": term_t,
        "terminal_residual_j_kg": term_h,
        "terminal_tolerance_pass": term_pass,
        "allowed_terminal_h_residual_j_kg": allowed_h,
        "task172_holes": holes,
        "task172_gate_pass": holes == 0,
        "energy_balance_residual_w": energy,
        "total_duty_w": duty,
        "wall_time_s": round(elapsed, 3),
        "conservative_enthalpy_authority_pass": auth_pass,
        "property_state_consistency_pass": prop_pass,
        "max_property_conversion_error_j_kg": prop_err,
        "enthalpy_audit_rows": audit_count,
        "search_iterations": len(iso.search_trace),
    }


def _v07_golden_smoke() -> str:
    try:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/exchangers/shell_tube/test_task173_integrated_rating.py::test_corrected_native_shell_flow_chain_replays_exactly",
                "tests/exchangers/shell_tube/test_task173_integrated_rating.py::test_task172_support_identity_and_roundoff_floor_replay",
                "tests/exchangers/shell_tube/test_task173_integrated_rating.py::test_zero_q_and_local_reconstruction_authorities_are_deterministic",
                "-q",
                "--timeout=300",
            ],
            cwd=_REPO,
            check=True,
            capture_output=True,
            text=True,
        )
        return "PASS"
    except subprocess.CalledProcessError as exc:
        return f"FAIL:{exc.returncode}"


def main() -> int:
    after_only = "--after-only" in sys.argv
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_250, provider=provider)
    bindings = resolve_candidate_bindings_by_id(
        CANDIDATE_ID, normalized, handoff, provider, max_valid=32
    )
    if bindings is None:
        raise SystemExit("candidate not in 250kW envelope")
    req_hash = candidate_rating_request_hash(bindings.rating_request)
    identity = {
        "normalized_input_hash": handoff.normalized_input_hash,
        "candidate_id": bindings.rating_request.candidate_id,
        "candidate_hash": bindings.rating_request.candidate_hash,
        "rating_request_hash": req_hash,
        "task168_request_hash": bindings.bundle.task168_request_hash_digest,
        "geometry_projection_hash": bindings.geometry_projection_hash,
        "fixture": str(FIXTURE_250.relative_to(_REPO)),
    }
    identity_ok = canonical_sha256(identity)

    before: dict[str, Any] = {}
    after: dict[str, Any] = {}
    if after_only and OUT.is_file():
        prior = json.loads(OUT.read_text(encoding="utf-8"))
        before = dict(prior.get("mesh_comparison", {}).get("before", {}))
    for sub in (1, 2, 4):
        if not after_only or not before:
            before[f"N{sub}"] = _mesh_summary(
                f"production_N{sub}", bindings, provider, sub, experimental=False
            )
        after[f"N{sub}"] = _mesh_summary(
            f"experimental_N{sub}", bindings, provider, sub, experimental=True
        )

    n1_b, n1_a = before["N1"], after["N1"]
    n2_a, n4_a = after["N2"], after["N4"]
    outer_resolved = n1_a["outer_status"] == "ACCEPTED" and n1_a["terminal_tolerance_pass"]
    live_success = (
        outer_resolved
        and n2_a["gate"] == "ACCEPTED"
        and n4_a["gate"] == "ACCEPTED"
        and n1_a["task172_gate_pass"]
        and n2_a["task172_gate_pass"]
        and n4_a["task172_gate_pass"]
    )

    remaining = None
    if not outer_resolved:
        remaining = n1_a["failure_code"] or "OUTER_PRECISION"
    elif not n4_a["task172_gate_pass"]:
        remaining = "TASK172_LOCAL_CONSTITUTIVE_CLOSURE"
    elif not live_success:
        remaining = "MESH_OR_ENERGY_BLOCKER"

    architecture_acceptance = "PASS" if live_success else "BLOCKED"

    payload: dict[str, Any] = {
        "TASK_ID": TASK_ID,
        "EXECUTION_STAGE": EXECUTION_STAGE,
        "IDENTITY": identity,
        "IDENTITY_SHA256": identity_ok,
        "OUTER_ENTHALPY_REPRESENTATION_IMPLEMENTED": True,
        "CONSERVATIVE_ENTHALPY_AUTHORITY_PASS": n1_a["conservative_enthalpy_authority_pass"],
        "PROPERTY_STATE_CONSISTENCY_PASS": n1_a["property_state_consistency_pass"],
        "OUTER_PRECISION_BLOCKER_RESOLVED": outer_resolved,
        "TASK172_ORIGINAL_RESIDUAL_GATE_PASS": all(
            before.get(f"N{n}", {}).get("task172_gate_pass") for n in (1, 2, 4)
        )
        if before
        else False,
        "TASK172_INDEPENDENT_STATUS": {
            "production_N1_holes": before.get("N1", {}).get("task172_holes"),
            "production_N2_holes": before.get("N2", {}).get("task172_holes"),
            "production_N4_holes": before.get("N4", {}).get("task172_holes"),
            "experimental_outer_blocker": n1_a["failure_code"],
        },
        "N1_STATUS": n1_a["gate"],
        "N2_STATUS": n2_a["gate"],
        "N4_STATUS": n4_a["gate"],
        "ENERGY_BALANCE_STATUS": "PASS"
        if n1_a.get("energy_balance_residual_w")
        and float(n1_a["energy_balance_residual_w"]) <= 1e-6
        else "NOT_EVALUATED_OR_BLOCKED",
        "LIVE_RATING_SUCCESS_COUNT": 1 if live_success else 0,
        "LIVE_DUTY_W": n4_a["total_duty_w"] if live_success else None,
        "V07_GOLDEN_REGRESSION_STATUS": _v07_golden_smoke(),
        "REMAINING_BLOCKER": remaining,
        "ARCHITECTURE_ACCEPTANCE": architecture_acceptance,
        "BEFORE_N1_TERMINAL_RESIDUAL_K": n1_b["terminal_residual_k"],
        "AFTER_N1_TERMINAL_RESIDUAL_K": n1_a["terminal_residual_k"],
        "BEFORE_N1_TERMINAL_RESIDUAL_J_KG": n1_b["terminal_residual_j_kg"],
        "AFTER_N1_TERMINAL_RESIDUAL_J_KG": n1_a["terminal_residual_j_kg"],
        "BEFORE_N1_OUTER_STATUS": n1_b["outer_status"],
        "AFTER_N1_OUTER_STATUS": n1_a["outer_status"],
        "BEFORE_N1_WALL_S": n1_b["wall_time_s"],
        "AFTER_N1_WALL_S": n1_a["wall_time_s"],
        "PRODUCTION_SOLVER_REPLACED": False,
        "mesh_comparison": {"before": before, "after": after},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0 if architecture_acceptance == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())