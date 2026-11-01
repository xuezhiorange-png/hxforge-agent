"""R27E: targeted recovery rating for previously blocked R27D candidates."""

# ruff: noqa: E501

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from prototypes.v07_general_rating_sizing_mvp.candidate_selection import (
    enumerate_experimental_rating_candidates,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase
from prototypes.v07_general_rating_sizing_mvp.experimental_engineering_rating_core import (
    ENGINEERING_NUMERIC_VALID,
    run_experimental_engineering_rating,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_engineering_rating_live_bridge import (
    build_experimental_engineering_rating_live_package,
)
from prototypes.v07_general_rating_sizing_mvp.nozzle_pressure_budget_solver import (
    cooptimize_nozzles_for_candidate_scenario,
)
from prototypes.v07_general_rating_sizing_mvp.positive_duty_cell import build_native_cell_context
from prototypes.v07_general_rating_sizing_mvp.thermal_hydraulic_geometry_cooptimization_sizing import (
    _mesh_rating_evidence_from_multi_row,
)

_TASK_ID = "V07_R27E_THERMAL_REGIME_AND_N1_CONVERGENCE_RECOVERY"
_SCHEMA = "hxforge.r27e-targeted-recovery.v27e"

R27D_RECOVERY_CANDIDATE_IDS: tuple[str, ...] = (
    "6ec6323f-402b-5d5f-90ef-2aab514d37de",
    "5b75a185-0813-5097-b37e-9e0d94332778",
    "8988992a-24cd-55e6-bff2-32b83aa32941",
    "c20fb684-9827-5cdb-9550-a4c5c03200c0",
    "09dac82a-0a84-5bc2-9b3f-93aaecd30a9e",
)


def _classify_outcome(*, full_converged: bool, n1_status: str, diagnostics: list[str]) -> str:
    if full_converged:
        return "FULL_RATING_CONVERGED"
    diag_text = " ".join(diagnostics)
    if "THERMAL_CORRELATION_UNAVAILABLE" in diag_text:
        return "MODEL_NOT_APPLICABLE"
    if "enthalpy_domain_exit" in diag_text:
        return "MODEL_NOT_APPLICABLE"
    if n1_status != ENGINEERING_NUMERIC_VALID:
        return "NUMERICAL_NONCONVERGENCE"
    return "NUMERICAL_NONCONVERGENCE"


def run_r27e_targeted_recovery(
    case: EngineeringCase,
    *,
    candidate_ids: tuple[str, ...] = R27D_RECOVERY_CANDIDATE_IDS,
) -> dict[str, Any]:
    selection = enumerate_experimental_rating_candidates(
        case,
        rating_selection_policy="r27d",
        rate_all_distinct_task174_ready=True,
    )
    records = {row.candidate_id: row for row in selection.records}
    rows: list[dict[str, Any]] = []
    for cid in candidate_ids:
        record = records[cid]
        native = build_native_cell_context(case, selection=selection, candidate_id=cid)
        n1_cache: dict[int, Any] = {}
        n1 = run_experimental_engineering_rating(
            case, subdivisions=1, native=native, mesh_result_cache=n1_cache
        )
        package: dict[str, Any] | None = None
        screening = f"BLOCKED_N1_{n1.failure_code or n1.status}"
        if n1.status == ENGINEERING_NUMERIC_VALID:
            screening = "N1_NUMERIC_VALID"
            package = build_experimental_engineering_rating_live_package(
                case,
                native=native,
                run_mesh_ladder=True,
                run_hydraulic_sensitivity=True,
                mesh_result_cache=n1_cache,
            )
        multi_row: dict[str, Any] = {
            "candidate_id": cid,
            "rating_participation_status": "NOT_EVALUATED",
            "screening_n1_status": screening,
            "n1_thermal_numeric_status": n1.status,
            "n1_duty_w": n1.duty_w,
            "FULL_RATING_CONVERGED": None,
            "task174_status": record.task174_status,
        }
        if package:
            mesh = package.get("mesh_convergence") or {}
            multi_row["FULL_RATING_CONVERGED"] = mesh.get("FULL_RATING_CONVERGED")
            if mesh.get("FULL_RATING_CONVERGED"):
                multi_row["rating_participation_status"] = "FULLY_RATED"
            else:
                multi_row["rating_participation_status"] = "SCREENED_N1_ONLY"
            multi_row["live_thermal_state_hydraulic_postpass"] = package.get(
                "live_thermal_state_hydraulic_postpass"
            )
            receipt = package.get("engineering_delivery_receipt") or {}
            multi_row["LIVE_TUBE_DP_PA"] = receipt.get("LIVE_TUBE_DP_PA")
            multi_row["LIVE_SHELL_DP_PA"] = receipt.get("LIVE_SHELL_DP_PA")
            multi_row["duty_w_at_finest_mesh"] = receipt.get("N4_DUTY_W")
            multi_row["tube_outlet_temperature_k_n4"] = receipt.get("N4_TUBE_OUTLET_K")
            multi_row["shell_outlet_temperature_k_n4"] = receipt.get("N4_SHELL_OUTLET_K")
        evidence = _mesh_rating_evidence_from_multi_row(multi_row)
        scenario_results: dict[str, Any] = {}
        if multi_row.get("FULL_RATING_CONVERGED") is True:
            postpass = multi_row.get("live_thermal_state_hydraulic_postpass") or {}
            for key in ("mid_band", "low_loss_sensitivity", "high_loss_sensitivity"):
                scenario_results[key] = cooptimize_nozzles_for_candidate_scenario(
                    case=case,
                    record=record,
                    postpass=postpass,
                    loss_scenario_key=key,
                )
        rows.append(
            {
                "candidate_id": cid,
                "candidate_hash": record.candidate_hash,
                "geometry": {
                    "shell_inside_diameter_m": record.shell_inside_diameter_m,
                    "tube_length_m": record.tube_length_m,
                    "baffle_spacing_m": record.baffle_spacing_m,
                    "physical_tube_count": record.physical_tube_count,
                    "task025_total_parallel_flow_area_m2": record.task025_total_parallel_flow_area_m2,
                },
                "original_r27d_blocker": evidence.get("n1_failure_code")
                or evidence.get("screening_n1_status"),
                "recovery_outcome_class": _classify_outcome(
                    full_converged=multi_row.get("FULL_RATING_CONVERGED") is True,
                    n1_status=str(n1.status),
                    diagnostics=list(n1.diagnostics or []),
                ),
                "mesh_rating_evidence": evidence,
                "n1_diagnostics_tail": list(n1.diagnostics[-5:]) if n1.diagnostics else [],
                "thermal_rating": {
                    "duty_w": multi_row.get("duty_w_at_finest_mesh"),
                    "tube_outlet_temperature_k": multi_row.get("tube_outlet_temperature_k_n4"),
                    "shell_outlet_temperature_k": multi_row.get("shell_outlet_temperature_k_n4"),
                    "full_rating_converged": multi_row.get("FULL_RATING_CONVERGED"),
                },
                "internal_hydraulics_pa": {
                    "live_tube_dp_pa": multi_row.get("LIVE_TUBE_DP_PA"),
                    "live_shell_dp_pa": multi_row.get("LIVE_SHELL_DP_PA"),
                },
                "loss_scenario_results": scenario_results,
            }
        )
    return {
        "schema_version": _SCHEMA,
        "TASK_ID": _TASK_ID,
        "generated_at_utc": datetime.now(tz=UTC).isoformat(),
        "recovery_candidates": rows,
        "disclosure": (
            "R27E admits Task026 laminar tube HTC on experimental MVP boundary only; "
            "transition remains THERMAL_CORRELATION_UNAVAILABLE. Production C3 turbulent "
            "path unchanged."
        ),
    }


def write_r27e_recovery_report(report: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "R27E_TARGETED_RECOVERY.json"
    md_path = output_dir / "R27E_TARGETED_RECOVERY.md"
    json_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    lines = [f"# {_TASK_ID}", ""]
    for row in report["recovery_candidates"]:
        lines.append(f"## `{row['candidate_id'][:8]}` → {row['recovery_outcome_class']}")
        lines.append(f"- Original blocker: {row['original_r27d_blocker']}")
        lines.append(f"- Geometry: {row['geometry']}")
        lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path
