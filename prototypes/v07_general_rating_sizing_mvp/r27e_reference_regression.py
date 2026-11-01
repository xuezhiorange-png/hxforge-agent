"""R27E: numeric regression guard for the seven R27D-converged reference candidates."""

from __future__ import annotations

import json
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
from prototypes.v07_general_rating_sizing_mvp.positive_duty_cell import build_native_cell_context
from prototypes.v07_general_rating_sizing_mvp.r27e_targeted_recovery import (
    R27D_RECOVERY_CANDIDATE_IDS,
)

_SCHEMA = "hxforge.r27e-r27d-seven-reference-regression.v27e"


def r27d_seven_reference_candidate_ids(
    case: EngineeringCase,
) -> tuple[str, ...]:
    selection = enumerate_experimental_rating_candidates(
        case,
        rating_selection_policy="r27d",
        rate_all_distinct_task174_ready=True,
    )
    recovery = set(R27D_RECOVERY_CANDIDATE_IDS)
    return tuple(cid for cid in selection.selected_candidate_ids if cid not in recovery)


def capture_reference_metrics(case: EngineeringCase) -> dict[str, Any]:
    selection = enumerate_experimental_rating_candidates(
        case,
        rating_selection_policy="r27d",
        rate_all_distinct_task174_ready=True,
    )
    rows: list[dict[str, Any]] = []
    for cid in r27d_seven_reference_candidate_ids(case):
        record = next(r for r in selection.records if r.candidate_id == cid)
        native = build_native_cell_context(case, selection=selection, candidate_id=cid)
        cache: dict[int, Any] = {}
        n1 = run_experimental_engineering_rating(
            case, subdivisions=1, native=native, mesh_result_cache=cache
        )
        row: dict[str, Any] = {
            "candidate_id": cid,
            "candidate_hash": record.candidate_hash,
            "geometry_projection_hash": record.geometry_projection_hash,
            "n1_status": n1.status,
            "n1_duty_w": n1.duty_w,
            "energy_balance_relative_error_n1": n1.energy_balance_relative_error,
            "max_cell_thermal_residual_w_n1": n1.max_cell_thermal_residual_w,
            "max_closure_residual_w_n1": n1.max_inner_wall_outer_closure_residual_w,
        }
        if n1.status == ENGINEERING_NUMERIC_VALID:
            package = build_experimental_engineering_rating_live_package(
                case,
                native=native,
                run_mesh_ladder=True,
                run_hydraulic_sensitivity=False,
                mesh_result_cache=cache,
            )
            mesh = package.get("mesh_convergence") or {}
            receipt = package.get("engineering_delivery_receipt") or {}
            row.update(
                {
                    "FULL_RATING_CONVERGED": mesh.get("FULL_RATING_CONVERGED"),
                    "mesh_ladder": mesh.get("mesh_ladder"),
                    "N4_DUTY_W": receipt.get("N4_DUTY_W"),
                    "N4_TUBE_OUTLET_K": receipt.get("N4_TUBE_OUTLET_K"),
                    "N4_SHELL_OUTLET_K": receipt.get("N4_SHELL_OUTLET_K"),
                    "LIVE_TUBE_DP_PA": receipt.get("LIVE_TUBE_DP_PA"),
                    "LIVE_SHELL_DP_PA": receipt.get("LIVE_SHELL_DP_PA"),
                    "experimental_mesh_result_hash": receipt.get("EXPERIMENTAL_MESH_RESULT_HASH"),
                }
            )
        rows.append(row)
    return {
        "schema_version": _SCHEMA,
        "reference_candidate_count": len(rows),
        "candidates": rows,
        "model_identity": {
            "task172_implementation": "task172_local_runtime.service",
            "tube_regime_isolation": "R27E_PHYSICAL_MODEL_ISOLATION",
        },
    }


def compare_reference_metrics(
    baseline: dict[str, Any],
    current: dict[str, Any],
    *,
    duty_abs_tol_w: float = 0.5,
    temperature_abs_tol_k: float = 1e-4,
    dp_rel_tol: float = 1e-6,
) -> list[dict[str, Any]]:
    deltas: list[dict[str, Any]] = []
    base_by_id = {row["candidate_id"]: row for row in baseline["candidates"]}
    for row in current["candidates"]:
        cid = row["candidate_id"]
        base = base_by_id.get(cid)
        if base is None:
            deltas.append({"candidate_id": cid, "error": "missing_baseline"})
            continue
        if base.get("candidate_hash") != row.get("candidate_hash"):
            deltas.append(
                {
                    "candidate_id": cid,
                    "error": "candidate_hash_changed",
                    "baseline": base.get("candidate_hash"),
                    "current": row.get("candidate_hash"),
                }
            )
            continue
        for key, tol, mode in (
            ("N4_DUTY_W", duty_abs_tol_w, "abs"),
            ("N4_TUBE_OUTLET_K", temperature_abs_tol_k, "abs"),
            ("N4_SHELL_OUTLET_K", temperature_abs_tol_k, "abs"),
            ("LIVE_TUBE_DP_PA", dp_rel_tol, "rel"),
            ("LIVE_SHELL_DP_PA", dp_rel_tol, "rel"),
        ):
            b_val = base.get(key)
            c_val = row.get(key)
            if b_val is None or c_val is None:
                continue
            bf = float(b_val)
            cf = float(c_val)
            if mode == "abs":
                diff = abs(cf - bf)
                if diff > tol:
                    deltas.append(
                        {
                            "candidate_id": cid,
                            "field": key,
                            "baseline": bf,
                            "current": cf,
                            "abs_delta": diff,
                            "tolerance": tol,
                        }
                    )
            else:
                denom = max(abs(bf), 1.0)
                rel = abs(cf - bf) / denom
                if rel > tol:
                    deltas.append(
                        {
                            "candidate_id": cid,
                            "field": key,
                            "baseline": bf,
                            "current": cf,
                            "rel_delta": rel,
                            "tolerance": tol,
                        }
                    )
        if base.get("FULL_RATING_CONVERGED") != row.get("FULL_RATING_CONVERGED"):
            deltas.append(
                {
                    "candidate_id": cid,
                    "field": "FULL_RATING_CONVERGED",
                    "baseline": base.get("FULL_RATING_CONVERGED"),
                    "current": row.get("FULL_RATING_CONVERGED"),
                }
            )
    return deltas


def load_reference_fixture(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
