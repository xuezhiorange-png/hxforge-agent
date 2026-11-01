"""R27E: numeric regression guard for the seven R27D-converged reference candidates."""

from __future__ import annotations

import json
import math
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
_R27D_BASELINE_HEAD = "e320aaf5840812eafe86a0e7d6fef97bf8062544"
_MESH_LEVELS = ("1", "2", "4")


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
                    "mesh_ladder": {
                        str(level): metrics
                        for level, metrics in (mesh.get("per_mesh") or {}).items()
                    },
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
    energy_abs_tol: float = 1e-9,
    closure_abs_tol_w: float = 0.5,
) -> list[dict[str, Any]]:
    """Fail closed on R27D provenance, missing fields, and N1/N2/N4 numeric drift."""
    deltas: list[dict[str, Any]] = []
    if baseline.get("schema_version") != _SCHEMA or current.get("schema_version") != _SCHEMA:
        deltas.append({"error": "reference_schema_mismatch"})
    source = baseline.get("baseline_provenance") or {}
    if (
        source.get("source_commit_sha") != _R27D_BASELINE_HEAD
        or source.get("source_pr_number") != 310
    ):
        deltas.append(
            {
                "error": "unverified_r27d_baseline_origin",
                "expected_head": _R27D_BASELINE_HEAD,
                "actual": source,
            }
        )

    base_rows = baseline.get("candidates") or []
    current_rows = current.get("candidates") or []
    base_by_id = {row["candidate_id"]: row for row in base_rows}
    current_by_id = {row["candidate_id"]: row for row in current_rows}
    if len(base_rows) != 7 or len(base_by_id) != 7:
        deltas.append({"error": "baseline_must_have_seven_unique_candidates"})
    if len(current_rows) != 7 or len(current_by_id) != 7:
        deltas.append({"error": "current_must_have_seven_unique_candidates"})
    for missing in sorted(base_by_id.keys() - current_by_id.keys()):
        deltas.append({"candidate_id": missing, "error": "missing_current"})
    for missing in sorted(current_by_id.keys() - base_by_id.keys()):
        deltas.append({"candidate_id": missing, "error": "missing_baseline"})

    def compare_numeric(
        cid: str,
        label: str,
        bval: Any,
        cval: Any,
        tolerance: float,
        *,
        relative: bool = False,
    ) -> None:
        if bval is None or cval is None:
            deltas.append({"candidate_id": cid, "field": label, "error": "missing_numeric_metric"})
            return
        try:
            b, c = float(bval), float(cval)
        except (TypeError, ValueError):
            deltas.append({"candidate_id": cid, "field": label, "error": "invalid_numeric_metric"})
            return
        if not math.isfinite(b) or not math.isfinite(c):
            deltas.append(
                {"candidate_id": cid, "field": label, "error": "nonfinite_numeric_metric"}
            )
            return
        difference = abs(b - c) / max(abs(b), 1.0) if relative else abs(b - c)
        if difference > tolerance:
            deltas.append(
                {
                    "candidate_id": cid,
                    "field": label,
                    "baseline": b,
                    "current": c,
                    "delta": difference,
                    "tolerance": tolerance,
                }
            )

    for cid in sorted(base_by_id.keys() & current_by_id.keys()):
        base, row = base_by_id[cid], current_by_id[cid]
        for field in ("candidate_hash", "geometry_projection_hash", "n1_status"):
            if not base.get(field) or base.get(field) != row.get(field):
                deltas.append(
                    {"candidate_id": cid, "field": field, "error": "identity_or_status_drift"}
                )
        for field, tolerance, relative in (
            ("n1_duty_w", duty_abs_tol_w, False),
            ("energy_balance_relative_error_n1", energy_abs_tol, False),
            ("max_cell_thermal_residual_w_n1", closure_abs_tol_w, False),
            ("max_closure_residual_w_n1", closure_abs_tol_w, False),
            ("N4_DUTY_W", duty_abs_tol_w, False),
            ("N4_TUBE_OUTLET_K", temperature_abs_tol_k, False),
            ("N4_SHELL_OUTLET_K", temperature_abs_tol_k, False),
            ("LIVE_TUBE_DP_PA", dp_rel_tol, True),
            ("LIVE_SHELL_DP_PA", dp_rel_tol, True),
        ):
            compare_numeric(
                cid, field, base.get(field), row.get(field), tolerance, relative=relative
            )
        if (
            base.get("FULL_RATING_CONVERGED") is not True
            or row.get("FULL_RATING_CONVERGED") is not True
        ):
            deltas.append(
                {"candidate_id": cid, "field": "FULL_RATING_CONVERGED", "error": "not_converged"}
            )
        bmesh = base.get("mesh_ladder") or {}
        cmesh = row.get("mesh_ladder") or {}
        for level in _MESH_LEVELS:
            bm, cm = bmesh.get(level) or {}, cmesh.get(level) or {}
            if not bm or not cm:
                deltas.append(
                    {"candidate_id": cid, "field": f"N{level}", "error": "missing_mesh_metrics"}
                )
                continue
            if bm.get("status") != cm.get("status") or not bm.get("status"):
                deltas.append(
                    {"candidate_id": cid, "field": f"N{level}.status", "error": "status_drift"}
                )
            for metric, tolerance in (
                ("duty_w", duty_abs_tol_w),
                ("tube_outlet_temperature_k", temperature_abs_tol_k),
                ("shell_outlet_temperature_k", temperature_abs_tol_k),
                ("energy_balance_relative_error", energy_abs_tol),
                ("max_cell_thermal_residual_w", closure_abs_tol_w),
                ("max_inner_wall_outer_closure_residual_w", closure_abs_tol_w),
            ):
                compare_numeric(
                    cid, f"N{level}.{metric}", bm.get(metric), cm.get(metric), tolerance
                )
    return deltas


def load_reference_fixture(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
