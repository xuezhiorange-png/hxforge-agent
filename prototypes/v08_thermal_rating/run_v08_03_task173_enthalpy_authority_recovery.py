#!/usr/bin/env python3
"""TASK_ID=V08_03_TASK173_ENTHALPY_AUTHORITY_RECOVERY — trace + authority audit, no BVP."""
# ruff: noqa: E402, E501

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(_REPO), str(_REPO / "src")]

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import (
    assess_production_culp_rating,
    isolated_mesh_acceptance_gate,
    load_case_bindings,
    resolve_candidate_bindings_by_id,
    solve_isolated_outer_boundary,
)
from prototypes.v08_thermal_rating.bvp_gate_evidence_v08 import BVP_PROTOTYPE_ROUTE
from prototypes.v08_thermal_rating.case_identity_v08 import FIXTURE_330
from prototypes.v08_thermal_rating.enthalpy_authority_experiment_v08 import (
    evaluate_n4_authority_experiment,
)
from prototypes.v08_thermal_rating.production_rating_diagnostics_v08 import (
    build_production_rating_diagnostic,
)

FROZEN_CANDIDATE_ID = "9277ebb8-5b05-5130-8b90-92ee4768606b"
GEOMETRY_HASH = "1d5cfed590c20aacb2224df020fd7fc88866c551b9ac6d813812d40b9a0a874f"


def _git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=_REPO, text=True).strip()


def _ci_status() -> str:
    try:
        out = subprocess.check_output(
            [
                "gh",
                "run",
                "list",
                "--repo",
                "xuezhiorange-png/hxforge-agent",
                "--branch",
                "cursor/v08-03-live-thermal-rating-1201",
                "--limit",
                "1",
                "--json",
                "conclusion,status",
            ],
            cwd=_REPO,
            text=True,
        )
        row = json.loads(out)[0]
        if row.get("status") != "completed":
            return "in_progress"
        return str(row.get("conclusion") or "unknown")
    except Exception:
        return "unknown"


def _json_ready(value: Any) -> Any:
    from decimal import Decimal

    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {k: _json_ready(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(v) for v in value]
    return value


def _run_mesh(bindings: Any, provider: CoolPropProvider, subdivisions: int) -> dict[str, Any]:
    iso = solve_isolated_outer_boundary(bindings, provider, subdivisions=subdivisions)
    gate = isolated_mesh_acceptance_gate(bindings, provider, iso)
    run = iso.accepted_run or iso.best_valid_run
    exp = evaluate_n4_authority_experiment(
        run,
        provider=provider,
        outer_status=iso.status,
        holes=None if run else 0,
    )
    return {
        "gate": gate,
        "outer_status": iso.status,
        "experiment": exp,
        "failure_code": iso.failure_code,
    }


def main() -> None:
    out = Path("/opt/cursor/artifacts/v08_03_task173_enthalpy_authority_recovery.json")
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    bindings = resolve_candidate_bindings_by_id(
        FROZEN_CANDIDATE_ID, normalized, handoff, provider, max_valid=64
    )
    assert bindings and bindings.geometry_projection_hash == GEOMETRY_HASH

    n1 = _run_mesh(bindings, provider, 1)
    n2 = _run_mesh(bindings, provider, 2)
    n4 = _run_mesh(bindings, provider, 4)
    n4exp = n4["experiment"]
    trace = n4exp.trace
    prod = build_production_rating_diagnostic(assess_production_culp_rating(bindings, provider))

    payload: dict[str, Any] = {
        "TASK_ID": "V08_03_TASK173_ENTHALPY_AUTHORITY_RECOVERY",
        "PR_NUMBER": 325,
        "HEAD_SHA": _git_head(),
        "CI_STATUS": _ci_status(),
        "ENTHALPY_PROPAGATION_DEFECT_CONFIRMED": n4exp.enthalpy_propagation_defect_confirmed,
        "FIRST_PRECISION_LOSS_CELL": trace.first_precision_loss_cell,
        "CUMULATIVE_ENTHALPY_ERROR_J_KG": trace.cumulative_face_prediction_error_j_kg,
        "PROPERTY_ROUNDTRIP_ERROR_J_KG": trace.max_ph_roundtrip_error_j_kg,
        "DEFECT_ATTRIBUTION": trace.defect_attributed_to,
        "ISOLATED_N1": n1["gate"],
        "ISOLATED_N2": n2["gate"],
        "ISOLATED_N4": n4["gate"],
        "N4_TASK172_GATE": n4exp.task172_gate,
        "N4_TERMINAL_GATE": n4exp.terminal_gate,
        "N4_ENERGY_BALANCE": "PASS" if n4exp.energy_balance_ok else "BLOCKED",
        "N4_TOTAL_Q_W": n4exp.total_q_w,
        "N4_OUTER_STATUS": n4["outer_status"],
        "N4_FAILURE_CODE": n4["failure_code"],
        "NUMERICAL_DECISION": n4exp.numerical_decision,
        "PRODUCTION_TASK173": prod.PRODUCTION_TASK173_STATUS,
        "BVP_ROUTE": BVP_PROTOTYPE_ROUTE,
        "DISTINCT_FULLY_CONVERGED": 0,
        "ENGINEERING_ACCEPTANCE": "BLOCKED",
        "PRODUCTION_SOLVER_REPLACED": False,
        "PRODUCTION_CONTRACT_CHANGE_AUTHORIZED": False,
        "MERGE_AUTHORIZED": False,
        "authority_consistency": _json_ready(asdict(n4exp.consistency)),
        "trace_summary": {
            "shell_inlet_face_minus_authority_j_kg": trace.shell_inlet_face_minus_authority_j_kg,
            "terminal_residual_j_kg": trace.terminal_residual_j_kg,
            "terminal_residual_k": trace.terminal_residual_k,
        },
        "first_cell_trace": _json_ready(asdict(trace.rows[0])) if trace.rows else None,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(_json_ready(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "out": str(out),
                "NUMERICAL_DECISION": n4exp.numerical_decision,
                "ENTHALPY_PROPAGATION_DEFECT_CONFIRMED": n4exp.enthalpy_propagation_defect_confirmed,
            }
        )
    )


if __name__ == "__main__":
    main()
