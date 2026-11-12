#!/usr/bin/env python3
"""TASK_ID=V08_03_N4_CLOSURE_AND_PRODUCTION_RATING — frozen candidate closeout."""
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
    CASE_330KW_ID,
    assess_production_culp_rating,
    engineering_distinct_fully_converged,
    load_case_bindings,
    resolve_candidate_bindings_by_id,
    run_candidate_mesh_closeout,
)
from prototypes.v08_thermal_rating.boundary_precision_audit_v1 import run_boundary_precision_audit
from prototypes.v08_thermal_rating.case_identity_v08 import FIXTURE_330
from prototypes.v08_thermal_rating.mesh_level_diagnostics_v08 import IsolatedMeshLevelDiagnostic
from prototypes.v08_thermal_rating.nozzle_velocity_v08 import assess_nozzle_velocities
from prototypes.v08_thermal_rating.production_rating_diagnostics_v08 import (
    build_production_rating_diagnostic,
)

FROZEN_CANDIDATE_ID = "9277ebb8-5b05-5130-8b90-92ee4768606b"
FROZEN_GEOMETRY_HASH = "1d5cfed590c20aacb2224df020fd7fc88866c551b9ac6d813812d40b9a0a874f"


def _git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=_REPO, text=True).strip()


def _json_ready(value: Any) -> Any:
    from decimal import Decimal

    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {k: _json_ready(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(v) for v in value]
    return value


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
            return "in_progress"
        return str(row.get("conclusion") or "unknown")
    except Exception:
        return "unknown"


def _n4_fields(d: IsolatedMeshLevelDiagnostic | None) -> dict[str, Any]:
    if d is None:
        return {
            k: None
            for k in (
                "N4_OUTER_STATUS",
                "N4_FAILURE_CODE",
                "N4_FAILURE_DIAGNOSTICS",
                "N4_FIRST_FAILED_CELL",
                "N4_FIRST_FAILED_EQUATION",
                "N4_TERMINAL_RESIDUAL_K",
                "N4_TERMINAL_RESIDUAL_J_KG",
                "N4_TASK172_HOLES",
                "N4_SEARCH_TRACE",
                "N4_SHOOTING_BRACKET",
                "N4_ITERATIONS",
                "N4_RUN_HASH",
            )
        }
    return {
        "N4_OUTER_STATUS": d.N_OUTER_STATUS,
        "N4_FAILURE_CODE": d.N_FAILURE_CODE,
        "N4_FAILURE_DIAGNOSTICS": list(d.N_FAILURE_DIAGNOSTICS),
        "N4_FIRST_FAILED_CELL": d.N_FIRST_FAILED_CELL,
        "N4_FIRST_FAILED_EQUATION": d.N_FIRST_FAILED_EQUATION,
        "N4_TERMINAL_RESIDUAL_K": d.N_TERMINAL_RESIDUAL_K,
        "N4_TERMINAL_RESIDUAL_J_KG": d.N_TERMINAL_RESIDUAL_J_KG,
        "N4_TASK172_HOLES": d.N_TASK172_HOLES,
        "N4_SEARCH_TRACE": list(d.N_SEARCH_TRACE),
        "N4_SHOOTING_BRACKET": d.N_SHOOTING_BRACKET,
        "N4_ITERATIONS": d.N_ITERATIONS,
        "N4_RUN_HASH": d.N_RUN_HASH,
    }


def main() -> None:
    out = Path("/opt/cursor/artifacts/v08_03_n4_closure_and_production_rating.json")
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    assert normalized.engineering_case_id == CASE_330KW_ID
    bindings = resolve_candidate_bindings_by_id(
        FROZEN_CANDIDATE_ID, normalized, handoff, provider, max_valid=64
    )
    if bindings is None:
        raise SystemExit(f"candidate {FROZEN_CANDIDATE_ID} not found in manufacturable set")
    assert bindings.geometry_projection_hash == FROZEN_GEOMETRY_HASH

    closeout = run_candidate_mesh_closeout(bindings, provider, run_production_gate=True)
    prod = assess_production_culp_rating(bindings, provider)
    prod_diag = build_production_rating_diagnostic(prod)
    nozzle = assess_nozzle_velocities(bindings, provider)
    n1_solved = (
        closeout.n1_diagnostic.outer_result
        if closeout.n1_diagnostic is not None
        else None
    )
    precision = run_boundary_precision_audit(
        bindings, provider, subdivisions=1, solved=n1_solved
    )

    n1v = closeout.n1_verification
    run_n1 = closeout.n1_diagnostic.outer_result.accepted_run if closeout.n1_diagnostic else None
    obs = run_n1.observables if run_n1 is not None else None

    tube_v = next((s for s in nozzle.sides if s.side == "TUBE"), None)
    shell_v = next((s for s in nozzle.sides if s.side == "SHELL"), None)

    eng_ok = engineering_distinct_fully_converged(
        closeout, nozzle=nozzle, target_met=closeout.target_330kw_met
    )

    n4_fields = _n4_fields(closeout.n4_diagnostic)
    n4_first = (
        (n4_fields.get("N4_FAILURE_CODE") or "")
        + (
            f";cell={n4_fields.get('N4_FIRST_FAILED_CELL')}"
            if n4_fields.get("N4_FIRST_FAILED_CELL")
            else ""
        )
    ).strip(";") or str(n4_fields.get("N4_OUTER_STATUS"))

    tp_delta = "unverified"
    if precision.tp_ph_roundtrip:
        rt = precision.tp_ph_roundtrip
        tp_delta = (
            f"delta_t_k={rt.delta_t_k};delta_h_j_kg={rt.delta_h_j_kg};"
            f"inlet_face_minus_authority={rt.inlet_face_minus_authority_j_kg}"
        )

    blockers = []
    if closeout.n4 != "ACCEPTED":
        blockers.append(f"N4={n4_first}")
    if closeout.experimental_mesh_convergence_pass != "PASS":
        blockers.append(f"MESH_CONV={closeout.experimental_mesh_convergence_pass}")
    if prod_diag.PRODUCTION_TASK173_STATUS != "VALIDATED":
        blockers.append(prod_diag.PRODUCTION_FIRST_BLOCKER or "PRODUCTION_BLOCKED")
    if nozzle.status != "VERIFIED":
        blockers.append("NOZZLE_UNRESOLVED")

    payload: dict[str, Any] = {
        "TASK_ID": "V08_03_N4_CLOSURE_AND_PRODUCTION_RATING",
        "PR_NUMBER": 325,
        "HEAD_SHA": _git_head(),
        "CI_STATUS": _ci_status(),
        "CASE_ID": CASE_330KW_ID,
        "CANDIDATE_ID": FROZEN_CANDIDATE_ID,
        "GEOMETRY_HASH": FROZEN_GEOMETRY_HASH,
        "N1": closeout.n1,
        "N2": closeout.n2,
        "N4": closeout.n4,
        "N4_FIRST_FAILURE": n4_first,
        "N4_REMAINING_BLOCKER": n4_first if closeout.n4 != "ACCEPTED" else None,
        **n4_fields,
        "EXPERIMENTAL_MESH_GATES_ACCEPTED": closeout.experimental_mesh_gates_accepted,
        "EXPERIMENTAL_MESH_CONVERGENCE": closeout.experimental_mesh_convergence_pass,
        "PRODUCTION_RATING_VALIDATED": closeout.production_rating_validated,
        "ENGINEERING_FULLY_ACCEPTED": eng_ok,
        "Q_TOTAL_W": n1v.N1_TOTAL_DUTY_W or (str(obs.total_duty_w) if obs else "unverified"),
        "TUBE_OUTLET_K": str(obs.tube_outlet_temperature_k) if obs else None,
        "SHELL_OUTLET_K": str(obs.shell_outlet_temperature_k) if obs else None,
        "PRODUCTION_TASK172": prod_diag.PRODUCTION_TASK172_GATE,
        "PRODUCTION_TASK173": prod_diag.PRODUCTION_TASK173_STATUS,
        "PRODUCTION_FIRST_BLOCKER": prod_diag.PRODUCTION_FIRST_BLOCKER,
        "PRODUCTION_FAILED_MESH": prod_diag.PRODUCTION_FAILED_MESH,
        "PRODUCTION_RESULT_HASH": prod_diag.PRODUCTION_RESULT_HASH,
        "TUBE_DP_PA": closeout.tube_dp_pa,
        "SHELL_DP_PA": closeout.shell_dp_pa,
        "TUBE_NOZZLE_VELOCITY": tube_v.velocity_m_s
        if tube_v and tube_v.velocity_m_s
        else "UNRESOLVED",
        "SHELL_NOZZLE_VELOCITY": shell_v.velocity_m_s
        if shell_v and shell_v.velocity_m_s
        else "UNRESOLVED",
        "TP_PH_RECONSTRUCTION_DELTA": tp_delta,
        "DISTINCT_FULLY_CONVERGED": 1 if eng_ok else 0,
        "ENGINEERING_ACCEPTANCE": "BLOCKED",
        "REMAINING_BLOCKER": "; ".join(blockers) if blockers else "BLOCKED",
        "PRODUCTION_CONTRACT_CHANGE_AUTHORIZED": False,
        "PRODUCTION_SOLVER_REPLACED": False,
        "MERGE_AUTHORIZED": False,
        "precision_audit": _json_ready(asdict(precision)),
        "production_row": _json_ready(asdict(prod.row)) if prod.row else None,
        "nozzle_report": _json_ready(asdict(nozzle)),
    }

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(_json_ready(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {"out": str(out), "N4": closeout.n4, "PRODUCTION": prod_diag.PRODUCTION_TASK173_STATUS}
        )
    )


if __name__ == "__main__":
    main()
