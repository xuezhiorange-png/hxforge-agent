#!/usr/bin/env python3
"""TASK_ID=V08_03_AUTONOMOUS_NOZZLE_AND_FULL_PATH_HYDRAULICS delivery runner."""
# ruff: noqa: E402

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
from prototypes.v08_thermal_rating.autonomous_nozzle_full_path_hydraulics_v08 import (
    run_autonomous_nozzle_full_path,
    scan_manufacturable_full_path_inventory,
)
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import (
    load_case_bindings,
    resolve_candidate_bindings_by_id,
)
from prototypes.v08_thermal_rating.bvp_gate_evidence_v08 import BVP_PROTOTYPE_ROUTE
from prototypes.v08_thermal_rating.case_identity_v08 import CASE_330KW_ID, FIXTURE_330

FROZEN_CANDIDATE_ID = "9277ebb8-5b05-5130-8b90-92ee4768606b"
PR_NUMBER = 325


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


def _port_mm(ports: tuple[Any, ...], port_id: str) -> str:
    for p in ports:
        if p.port_id == port_id:
            return f"{float(p.inside_diameter_m) * 1000:.3f}"
    return "UNRESOLVED"


def _port_v(ports: tuple[Any, ...], port_id: str) -> str:
    for p in ports:
        if p.port_id == port_id:
            return f"{float(p.velocity_m_s):.6g}"
    return "UNRESOLVED"


def main() -> None:
    out = Path("/opt/cursor/artifacts/v08_03_autonomous_nozzle_and_full_path_hydraulics.json")
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    assert normalized.engineering_case_id == CASE_330KW_ID
    bindings = resolve_candidate_bindings_by_id(
        FROZEN_CANDIDATE_ID, normalized, handoff, provider, max_valid=64
    )
    if bindings is None:
        raise RuntimeError("frozen candidate not resolved")

    report = run_autonomous_nozzle_full_path(bindings)
    inventory = scan_manufacturable_full_path_inventory(
        normalized, handoff, provider=provider, max_candidates=64
    )

    scenario_payload = {
        s.scenario_key: {
            "FULL_PATH_HYDRAULIC_CHECK": s.hydraulic_check,
            "FULL_PATH_TUBE_DP_PA": s.tube_full_path_dp_pa or s.tube_modeled_side_dp_pa,
            "FULL_PATH_SHELL_DP_PA": s.shell_full_path_dp_pa or s.shell_modeled_side_dp_pa,
            "TUBE_MARGIN_PA": s.tube_margin_pa,
            "SHELL_MARGIN_PA": s.shell_margin_pa,
            "overall_status": s.overall_status,
        }
        for s in report.scenarios
    }

    blockers = list(report.remaining_blockers) + [
        "SHOOTING_N4=BLOCKED",
        "PRODUCTION_TASK172=BLOCKED",
        "PRODUCTION_TASK173=BLOCKED",
        "ENGINEERING_PHYSICAL_EVIDENCE=PARTIAL",
        "ENGINEERING_ACCEPTANCE=BLOCKED",
    ]
    if inventory.full_path_hydraulic_feasible_count < 2:
        blockers.append("CANDIDATE_SPACE_FULL_PATH_FEASIBLE_LT_2")

    payload: dict[str, Any] = {
        "TASK_ID": "V08_03_AUTONOMOUS_NOZZLE_AND_FULL_PATH_HYDRAULICS",
        "PR_NUMBER": PR_NUMBER,
        "HEAD_SHA": _git_head(),
        "CI_STATUS": _ci_status(),
        "CASE_ID": CASE_330KW_ID,
        "CANDIDATE_ID": FROZEN_CANDIDATE_ID,
        "STRUCTURAL_GEOMETRY_HASH": report.structural_geometry_hash,
        "NOZZLE_DESIGN_HASH": report.nozzle_design_hash,
        "NOZZLE_SIZE_AUTHORITY": report.nozzle_size_authority,
        "TUBE_INLET_NOZZLE_D_MM": _port_mm(report.ports, "TUBE_INLET"),
        "TUBE_OUTLET_NOZZLE_D_MM": _port_mm(report.ports, "TUBE_OUTLET"),
        "SHELL_INLET_NOZZLE_D_MM": _port_mm(report.ports, "SHELL_INLET"),
        "SHELL_OUTLET_NOZZLE_D_MM": _port_mm(report.ports, "SHELL_OUTLET"),
        "TUBE_INLET_V_M_S": _port_v(report.ports, "TUBE_INLET"),
        "TUBE_OUTLET_V_M_S": _port_v(report.ports, "TUBE_OUTLET"),
        "SHELL_INLET_V_M_S": _port_v(report.ports, "SHELL_INLET"),
        "SHELL_OUTLET_V_M_S": _port_v(report.ports, "SHELL_OUTLET"),
        "NOZZLE_VELOCITY_CHECK": report.nozzle_velocity_check,
        "NOZZLE_INSTALLATION_CHECK": report.nozzle_installation_check,
        "FULL_PATH_DP_AUTHORITY": report.full_path_dp_authority,
        "FULL_PATH_SCENARIOS": scenario_payload,
        "TASK174_BASELINE_TUBE_DP_PA": report.task174_baseline_tube_dp_pa,
        "TASK174_BASELINE_SHELL_DP_PA": report.task174_baseline_shell_dp_pa,
        "MANUFACTURABLE_VALID_COUNT": inventory.manufacturable_valid_count,
        "FULL_PATH_HYDRAULIC_FEASIBLE_COUNT": inventory.full_path_hydraulic_feasible_count,
        "TASK174_HYDRAULIC_FEASIBLE_COUNT": inventory.task174_hydraulic_feasible_count,
        "PRODUCTION_TASK172": "BLOCKED",
        "PRODUCTION_TASK173": "BLOCKED",
        "ENGINEERING_ACCEPTANCE": "BLOCKED",
        "REMAINING_ENGINEERING_BLOCKERS": blockers,
        "CANDIDATE_SPACE_GAP_NOTES": list(inventory.gap_notes),
        "BVP_ROUTE": BVP_PROTOTYPE_ROUTE,
        "PRODUCTION_CONTRACT_CHANGE_AUTHORIZED": False,
        "PRODUCTION_SOLVER_REPLACED": False,
        "MERGE_AUTHORIZED": False,
        "disclosure": list(report.disclosure),
        "ports": [_json_ready(asdict(p)) for p in report.ports],
        "inventory_head": _json_ready(list(inventory.per_candidate)),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(_json_ready(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"out": str(out), "NOZZLE_VELOCITY_CHECK": report.nozzle_velocity_check}))


if __name__ == "__main__":
    main()
