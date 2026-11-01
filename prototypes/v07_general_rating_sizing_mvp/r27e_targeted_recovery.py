"""R27E: targeted recovery rating for previously blocked R27D candidates."""

# ruff: noqa: E501

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173
from hexagent.properties.coolprop_provider import CoolPropProvider
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
from prototypes.v07_general_rating_sizing_mvp.native_thermal_boundary_binding import (
    native_thermal_boundary_session,
)
from prototypes.v07_general_rating_sizing_mvp.nozzle_pressure_budget_solver import (
    cooptimize_nozzles_for_candidate_scenario,
)
from prototypes.v07_general_rating_sizing_mvp.positive_duty_cell import build_native_cell_context
from prototypes.v07_general_rating_sizing_mvp.r27e_tube_regime_diagnostics import (
    probe_enthalpy_domain_exit,
    scan_tube_regime_along_temperature,
)
from prototypes.v07_general_rating_sizing_mvp.thermal_hydraulic_geometry_cooptimization_sizing import (
    _mesh_rating_evidence_from_multi_row,
)

_TASK_ID = "V07_R27E_THERMAL_REGIME_AND_N1_CONVERGENCE_RECOVERY"
_SCHEMA = "hxforge.r27e-targeted-recovery.v27e2"

RecoveryOutcome = Literal[
    "FULL_RATING_CONVERGED",
    "FULL_PATH_CONSTRAINT_NOT_SATISFIED",
    "NUMERICAL_NONCONVERGENCE",
    "MODEL_NOT_APPLICABLE",
]

RecoveryRootCause = Literal[
    "NONE",
    "THERMAL_CORRELATION_TRANSITION_GAP",
    "PROPERTY_ENTHALPY_DOMAIN_EXIT",
    "R27D_N1_NUMERIC_NONCONVERGENCE",
    "OTHER_NUMERICAL",
]

R27D_RECOVERY_CANDIDATE_IDS: tuple[str, ...] = (
    "6ec6323f-402b-5d5f-90ef-2aab514d37de",
    "5b75a185-0813-5097-b37e-9e0d94332778",
    "8988992a-24cd-55e6-bff2-32b83aa32941",
    "c20fb684-9827-5cdb-9550-a4c5c03200c0",
    "09dac82a-0a84-5bc2-9b3f-93aaecd30a9e",
)

# Frozen R27D mesh-rating blockers (pre-R27E recovery), not post-recovery N1 codes.
R27D_ORIGINAL_BLOCKERS: dict[str, str] = {
    "6ec6323f-402b-5d5f-90ef-2aab514d37de": "BLOCKED_TUBE_C3_REGIME_NOT_APPLICABLE",
    "5b75a185-0813-5097-b37e-9e0d94332778": "BLOCKED_TUBE_C3_REGIME_NOT_APPLICABLE",
    "8988992a-24cd-55e6-bff2-32b83aa32941": "BLOCKED_TUBE_C3_REGIME_NOT_APPLICABLE",
    "c20fb684-9827-5cdb-9550-a4c5c03200c0": "MESH_TOPOLOGY_INVALID;enthalpy_domain_exit",
    "09dac82a-0a84-5bc2-9b3f-93aaecd30a9e": "N1_NUMERIC_NONCONVERGENCE;global_q_residual_floor",
}

R27E_RECOVERED_FULL_RATING_IDS: tuple[str, ...] = ("09dac82a-0a84-5bc2-9b3f-93aaecd30a9e",)

FOUR_065_SHELL_CANDIDATE_IDS: tuple[str, ...] = (
    "6ec6323f-402b-5d5f-90ef-2aab514d37de",
    "5b75a185-0813-5097-b37e-9e0d94332778",
    "8988992a-24cd-55e6-bff2-32b83aa32941",
    "c20fb684-9827-5cdb-9550-a4c5c03200c0",
)


def _parse_enthalpy_from_diagnostics(diagnostics: list[str]) -> float | None:
    for item in diagnostics:
        match = re.search(r"enthalpy_domain_exit;h=([0-9.eE+-]+)", item)
        if match:
            return float(match.group(1))
    return None


def _recovery_root_cause(
    *,
    full_converged: bool,
    diagnostics: list[str],
    original_r27d_blocker: str,
) -> RecoveryRootCause:
    if full_converged:
        return "NONE"
    diag_text = " ".join(diagnostics)
    if "enthalpy_domain_exit" in diag_text or "enthalpy_domain_exit" in original_r27d_blocker:
        return "PROPERTY_ENTHALPY_DOMAIN_EXIT"
    if "THERMAL_CORRELATION_UNAVAILABLE" in diag_text:
        return "THERMAL_CORRELATION_TRANSITION_GAP"
    if "global_q_residual_floor" in original_r27d_blocker:
        return "R27D_N1_NUMERIC_NONCONVERGENCE"
    return "OTHER_NUMERICAL"


def _classify_outcome(
    *,
    full_converged: bool,
    full_path_feasible_any_k: bool | None,
    root_cause: RecoveryRootCause,
) -> RecoveryOutcome:
    if full_converged:
        if full_path_feasible_any_k is True:
            return "FULL_RATING_CONVERGED"
        return "FULL_PATH_CONSTRAINT_NOT_SATISFIED"
    if root_cause in ("THERMAL_CORRELATION_TRANSITION_GAP", "PROPERTY_ENTHALPY_DOMAIN_EXIT"):
        return "MODEL_NOT_APPLICABLE"
    return "NUMERICAL_NONCONVERGENCE"


def run_r27e_targeted_recovery(
    case: EngineeringCase,
    *,
    candidate_ids: tuple[str, ...] = R27D_RECOVERY_CANDIDATE_IDS,
    include_regime_diagnostics: bool = True,
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
            multi_row["experimental_mesh_result_hash"] = receipt.get(
                "EXPERIMENTAL_MESH_RESULT_HASH"
            )
        evidence = _mesh_rating_evidence_from_multi_row(multi_row)
        scenario_results: dict[str, Any] = {}
        full_path_feasible_any: bool | None = None
        if multi_row.get("FULL_RATING_CONVERGED") is True:
            postpass = multi_row.get("live_thermal_state_hydraulic_postpass") or {}
            for key in ("mid_band", "low_loss_sensitivity", "high_loss_sensitivity"):
                scenario_results[key] = cooptimize_nozzles_for_candidate_scenario(
                    case=case,
                    record=record,
                    postpass=postpass,
                    loss_scenario_key=key,
                )
            full_path_feasible_any = any(
                row.get("full_path_feasible") is True for row in scenario_results.values()
            )
        original_blocker = R27D_ORIGINAL_BLOCKERS.get(cid, "UNKNOWN_R27D_BLOCKER")
        root_cause = _recovery_root_cause(
            full_converged=multi_row.get("FULL_RATING_CONVERGED") is True,
            diagnostics=list(n1.diagnostics or []),
            original_r27d_blocker=original_blocker,
        )
        regime_diag: dict[str, Any] | None = None
        if include_regime_diagnostics and cid in FOUR_065_SHELL_CANDIDATE_IDS:
            regime_diag = scan_tube_regime_along_temperature(
                case, selection=selection, candidate_id=cid
            )
            if cid == "c20fb684-9827-5cdb-9550-a4c5c03200c0":
                h_probe = _parse_enthalpy_from_diagnostics(list(n1.diagnostics or []))
                if h_probe is None:
                    regime_diag["enthalpy_domain_probe"] = {
                        "status": "NOT_EXECUTED_NO_RUNTIME_ENTHALPY_DIAGNOSTIC",
                        "disclosure": (
                            "Do not substitute a historical assumed enthalpy for an "
                            "actual R27E solver diagnostic."
                        ),
                    }
                else:
                    with native_thermal_boundary_session(
                        case, CoolPropProvider(), enable_live_binding=True
                    ):
                        provider = CoolPropProvider()
                        p_pa = float(t173.effective_tube_property_evaluation_pressure_pa())
                        h_min = float(t173._effective_h_min_j_kg())
                        h_max = float(t173.effective_admitted_h_max_j_kg(provider))
                    regime_diag["enthalpy_domain_probe"] = probe_enthalpy_domain_exit(
                        enthalpy_j_kg=h_probe,
                        pressure_pa=p_pa,
                        rating_admitted_h_min_j_kg=h_min,
                        rating_admitted_h_max_j_kg=h_max,
                    )
        rows.append(
            {
                "candidate_id": cid,
                "candidate_hash": record.candidate_hash,
                "geometry_projection_hash": record.geometry_projection_hash,
                "rating_request_hash": record.rating_request_hash,
                "task171_result_hash": record.task171_result_hash,
                "task174_result_hash": record.task174_result_hash,
                "geometry": {
                    "shell_inside_diameter_m": record.shell_inside_diameter_m,
                    "tube_length_m": record.tube_length_m,
                    "baffle_spacing_m": record.baffle_spacing_m,
                    "physical_tube_count": record.physical_tube_count,
                    "task025_total_parallel_flow_area_m2": record.task025_total_parallel_flow_area_m2,
                },
                "original_r27d_blocker": original_blocker,
                "r27e_n1_failure_code": n1.failure_code,
                "r27e_n1_status": n1.status,
                "recovery_root_cause": root_cause,
                "recovery_outcome_class": _classify_outcome(
                    full_converged=multi_row.get("FULL_RATING_CONVERGED") is True,
                    full_path_feasible_any_k=full_path_feasible_any,
                    root_cause=root_cause,
                ),
                "mesh_rating_evidence": evidence,
                "n1_diagnostics_tail": list(n1.diagnostics[-5:]) if n1.diagnostics else [],
                "tube_side_regime_diagnostics": regime_diag,
                "thermal_rating": {
                    "duty_w": multi_row.get("duty_w_at_finest_mesh"),
                    "tube_outlet_temperature_k": multi_row.get("tube_outlet_temperature_k_n4"),
                    "shell_outlet_temperature_k": multi_row.get("shell_outlet_temperature_k_n4"),
                    "full_rating_converged": multi_row.get("FULL_RATING_CONVERGED"),
                    "experimental_mesh_result_hash": multi_row.get("experimental_mesh_result_hash"),
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
        "provenance": {
            "r27d_original_blocker_source": "R27D mesh-rating evidence (frozen)",
            "r27e_new_full_rating_candidate_ids": list(R27E_RECOVERED_FULL_RATING_IDS),
            "tube_side_model": (
                "Task026 laminar CWT without C3 wall-Pr correction; turbulent C3 retained; "
                "transition THERMAL_CORRELATION_UNAVAILABLE"
            ),
        },
        "recovery_candidates": rows,
        "disclosure": (
            "R27E admits Task026 laminar tube HTC on experimental MVP boundary only; "
            "C3 wall-Pr correction applies to turbulent tube branch only. Transition remains "
            "THERMAL_CORRELATION_UNAVAILABLE. Production non-experimental path unchanged."
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
        lines.append(f"- R27D blocker: {row['original_r27d_blocker']}")
        lines.append(f"- Root cause: {row['recovery_root_cause']}")
        lines.append(f"- R27E N1: {row['r27e_n1_status']} / {row.get('r27e_n1_failure_code')}")
        diag = row.get("tube_side_regime_diagnostics") or {}
        first_tr = diag.get("first_transition_sweep_point")
        if first_tr:
            lines.append(
                f"- First transition (T sweep): T={first_tr.get('tube_bulk_temperature_k'):.3f} K, "
                f"Re={first_tr.get('reynolds'):.1f}, Pr={first_tr.get('prandtl'):.3f}"
            )
        lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path
