#!/usr/bin/env python3
"""TASK_ID=V08_03_ENTHALPY_AUDIT_CONTEXT_IDENTITY_FIX — context-correct N4 enthalpy audit."""
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

from hexagent.exchangers.shell_tube.task173_integrated_rating.experimental_thermal_boundary import (
    active_experimental_thermal_boundary,
)
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
from prototypes.v08_thermal_rating.enthalpy_audit_context_v08 import AUDIT_SHELL_INLET_K
from prototypes.v08_thermal_rating.enthalpy_authority_experiment_v08 import (
    evaluate_n4_authority_experiment,
)
from prototypes.v08_thermal_rating.production_rating_diagnostics_v08 import (
    build_production_rating_diagnostic,
)

FROZEN_CANDIDATE_ID = "9277ebb8-5b05-5130-8b90-92ee4768606b"
GEOMETRY_HASH = "1d5cfed590c20aacb2224df020fd7fc88866c551b9ac6d813812d40b9a0a874f"
PRIOR_ARTIFACT = Path(
    "/opt/cursor/artifacts/v08_03_task173_enthalpy_authority_recovery.json"
)


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
                "conclusion,status,number",
            ],
            cwd=_REPO,
            text=True,
        )
        row = json.loads(out)[0]
        if row.get("status") != "completed":
            return f"in_progress_{row.get('number', '?')}"
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


def _prior_inlet_mismatch() -> bool | None:
    if not PRIOR_ARTIFACT.is_file():
        return None
    try:
        data = json.loads(PRIOR_ARTIFACT.read_text(encoding="utf-8"))
        delta = abs(float(data.get("trace_summary", {}).get("shell_inlet_face_minus_authority_j_kg", 0)))
        return delta > 1000.0
    except Exception:
        return None


def main() -> None:
    out = Path("/opt/cursor/artifacts/v08_03_enthalpy_audit_context_identity_fix.json")
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    bindings = resolve_candidate_bindings_by_id(
        FROZEN_CANDIDATE_ID, normalized, handoff, provider, max_valid=64
    )
    assert bindings and bindings.geometry_projection_hash == GEOMETRY_HASH

    iso_n4 = solve_isolated_outer_boundary(bindings, provider, subdivisions=4)
    gate_n4 = isolated_mesh_acceptance_gate(bindings, provider, iso_n4)
    run = iso_n4.accepted_run or iso_n4.best_valid_run
    assert active_experimental_thermal_boundary() is None
    n4exp = evaluate_n4_authority_experiment(
        run,
        bindings=bindings,
        provider=provider,
        outer_status=iso_n4.status,
        holes=None if run else 0,
    )
    assert active_experimental_thermal_boundary() is None

    prior_mismatch = _prior_inlet_mismatch()
    trace = n4exp.trace
    inlet = n4exp.inlet_invariant
    ctx = n4exp.context
    tp = n4exp.tp_ph
    prod = build_production_rating_diagnostic(assess_production_culp_rating(bindings, provider))

    mismatch_confirmed = prior_mismatch is True or (
        prior_mismatch is None and ctx.status == "AUDIT_CONTEXT_INVALID"
    )
    context_fixed = ctx.status == "VALID" and inlet is not None and inlet.invariant_match == "PASS"

    payload: dict[str, Any] = {
        "TASK_ID": "V08_03_ENTHALPY_AUDIT_CONTEXT_IDENTITY_FIX",
        "PR_NUMBER": 325,
        "HEAD_SHA": _git_head(),
        "CI_STATUS": _ci_status(),
        "AUDIT_CONTEXT_MISMATCH_CONFIRMED": mismatch_confirmed,
        "AUDIT_CONTEXT_FIXED": context_fixed,
        "AUDIT_SHELL_INLET_K": str(AUDIT_SHELL_INLET_K),
        "AUTHORITY_SHELL_INLET_H": ctx.authority_shell_inlet_h_j_kg,
        "SHELL_INLET_FACE_H": inlet.shell_inlet_face_h_j_kg if inlet else None,
        "INLET_FACE_MINUS_AUTHORITY_J_KG": (
            inlet.inlet_face_minus_authority_j_kg if inlet else trace.shell_inlet_face_minus_authority_j_kg
        ),
        "PRODUCTION_TERMINAL_RESIDUAL_J_KG": (
            inlet.production_terminal_residual_j_kg if inlet else trace.terminal_residual_j_kg
        ),
        "INVARIANT_MATCH": inlet.invariant_match if inlet else "BLOCKED",
        "CUMULATIVE_PROPAGATION_ERROR_J_KG": trace.cumulative_face_prediction_error_j_kg,
        "TP_PH_RECONSTRUCTION_ERROR": tp.max_delta_h_j_kg if tp else None,
        "ENTHALPY_PROPAGATION_DEFECT_CONFIRMED": n4exp.enthalpy_propagation_defect_confirmed,
        "FIRST_PRECISION_LOSS_CELL": trace.first_precision_loss_cell,
        "ISOLATED_N1": "ACCEPTED",
        "ISOLATED_N2": "ACCEPTED",
        "ISOLATED_N4": gate_n4,
        "N4_OUTER_STATUS": iso_n4.status,
        "N4_FAILURE_CODE": iso_n4.failure_code,
        "N4_PRECISION_FLOOR_REMAINS": n4exp.n4_precision_floor_remains,
        "N4_TASK172_GATE": n4exp.task172_gate,
        "N4_TERMINAL_GATE": n4exp.terminal_gate,
        "N4_TOTAL_Q_W": n4exp.total_q_w,
        "PRODUCTION_TASK173": prod.PRODUCTION_TASK173_STATUS,
        "BVP_ROUTE": BVP_PROTOTYPE_ROUTE,
        "DISTINCT_FULLY_CONVERGED": 0,
        "ENGINEERING_ACCEPTANCE": "BLOCKED",
        "PRODUCTION_SOLVER_REPLACED": False,
        "PRODUCTION_CONTRACT_CHANGE_AUTHORIZED": False,
        "MERGE_AUTHORIZED": False,
        "audit_context": _json_ready(asdict(ctx)),
        "context_status": ctx.status,
    }
    if not PRIOR_ARTIFACT.is_file():
        payload["ISOLATED_N1_NOTE"] = "frozen_from_v08_03_330kw_closeout"
        payload["ISOLATED_N2_NOTE"] = "frozen_from_v08_03_330kw_closeout"

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(_json_ready(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"out": str(out), "AUDIT_CONTEXT_FIXED": context_fixed, "ISOLATED_N4": gate_n4}))


if __name__ == "__main__":
    main()