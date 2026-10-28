"""R26D: experimental multi-candidate engineering rating + live hydraulic sizing comparison."""

# ruff: noqa: E501

from __future__ import annotations

from decimal import Decimal
from typing import Any

from prototypes.v07_general_rating_sizing_mvp.candidate_selection import (
    CandidateSelectionOutcome,
    CandidateSelectionRecord,
    enumerate_experimental_rating_candidates,
    selection_to_json,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase
from prototypes.v07_general_rating_sizing_mvp.engineering_sizing_eligibility import (
    assess_engineering_sizing_eligibility,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_engineering_rating_core import (
    ENGINEERING_NUMERIC_VALID,
    run_experimental_engineering_rating,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_engineering_rating_live_bridge import (
    build_experimental_engineering_rating_live_package,
)
from prototypes.v07_general_rating_sizing_mvp.positive_duty_cell import (
    build_native_cell_context,
)

_SCHEMA = "hxforge.experimental-multi-candidate-engineering-sizing.v26d"
_SIZING_TARGET_AUTHORITY = "EXPERIMENTAL_DEMONSTRATION_NOT_OWNER_APPROVED"
_BASELINE_CANDIDATE_B_FINGERPRINT = ("3.0", "0.6", "0.56")


def _finest_duty_w(
    receipt: dict[str, Any] | None,
    mesh: dict[str, Any],
    n1_result: Any | None,
) -> float | None:
    if receipt and receipt.get("N4_DUTY_W") is not None:
        return float(receipt["N4_DUTY_W"])
    results = mesh.get("results") or {}
    for level in (4, 2, 1):
        if level in results and hasattr(results[level], "duty_w"):
            return float(results[level].duty_w)
    if n1_result is not None:
        return float(n1_result.duty_w)
    return None


def _record_by_id(selection: CandidateSelectionOutcome) -> dict[str, CandidateSelectionRecord]:
    return {row.candidate_id: row for row in selection.records}


def _is_baseline_candidate_b(row: CandidateSelectionRecord) -> bool:
    return (
        row.tube_length_m == _BASELINE_CANDIDATE_B_FINGERPRINT[0]
        and row.baffle_spacing_m == _BASELINE_CANDIDATE_B_FINGERPRINT[1]
        and (row.shell_inside_diameter_m or "0.56") == _BASELINE_CANDIDATE_B_FINGERPRINT[2]
    )


def _nominal_experimental_comparison_status(
    package: dict[str, Any] | None,
    *,
    case: EngineeringCase,
) -> tuple[bool, str, list[str]]:
    """Experimental sizing comparison eligibility (independent of production ENGINEERING_SIZING_ELIGIBILITY)."""
    if package is None:
        return False, "NOT_RATED", ["NO_ENGINEERING_PACKAGE"]
    mesh = package.get("mesh_convergence") or {}
    reasons: list[str] = []
    if not mesh.get("FULL_RATING_CONVERGED"):
        reasons.append("FULL_RATING_MESH_NOT_CONVERGED")
    results = mesh.get("results") or {}
    finest = results.get(4) or results.get(2) or results.get(1)
    if finest is None or finest.status != ENGINEERING_NUMERIC_VALID:
        reasons.append("THERMAL_NUMERIC_NOT_VALID")
    elif float(finest.duty_w) < float(case.target_duty_w):
        reasons.append("DUTY_BELOW_DEMONSTRATION_TARGET")
    margin = package.get("hydraulic_margin") or {}
    if margin.get("NOMINAL_CONSTRAINT_STATUS") != "SATISFIED":
        reasons.append("HYDRAULIC_NOMINAL_NOT_SATISFIED")
    postpass = package.get("live_thermal_state_hydraulic_postpass") or {}
    if postpass.get("correlation_applicability_status") == "BLOCKED":
        reasons.append("CORRELATION_APPLICABILITY_BLOCKED")
    if postpass.get("shell_hydraulic_recompute_status") == "BLOCKED":
        reasons.append("SHELL_HYDRAULIC_BLOCKED")
    if postpass.get("tube_hydraulic_recompute_status") == "BLOCKED":
        reasons.append("TUBE_HYDRAULIC_BLOCKED")
    ok = not reasons
    status = "NOMINAL_EXPERIMENTAL_SIZING_FEASIBLE" if ok else "NOT_NOMINAL_FEASIBLE"
    return ok, status, reasons


def _candidate_report_row(
    *,
    case: EngineeringCase,
    record: CandidateSelectionRecord,
    n1_result: Any | None,
    package: dict[str, Any] | None,
    screening_status: str,
) -> dict[str, Any]:
    receipt = package.get("engineering_delivery_receipt") if package else None
    mesh = (package or {}).get("mesh_convergence") or {}
    margin = (package or {}).get("hydraulic_margin") or {}
    eligibility = (
        assess_engineering_sizing_eligibility(
            case,
            {
                "status": "NUMERIC_VALID"
                if n1_result and n1_result.status == ENGINEERING_NUMERIC_VALID
                else "BLOCKED",
                "mesh_status": (
                    "NUMERIC_VALID"
                    if n1_result and n1_result.status == ENGINEERING_NUMERIC_VALID
                    else "BLOCKED"
                ),
            },
        )
        if n1_result
        else {}
    )
    nominal_ok, nominal_status, nominal_reasons = _nominal_experimental_comparison_status(
        package, case=case
    )
    tube_area = record.nominal_tube_outer_area_proxy_m2
    row: dict[str, Any] = {
        "candidate_id": record.candidate_id,
        "candidate_hash": record.candidate_hash,
        "geometry_projection_hash": record.geometry_projection_hash,
        "shell_inside_diameter_m": record.shell_inside_diameter_m,
        "tube_length_m": record.tube_length_m,
        "baffle_spacing_m": record.baffle_spacing_m,
        "physical_tube_count": record.physical_tube_count,
        "nominal_tube_outer_area_m2": tube_area,
        "task168_chain_status": record.task168_chain_status,
        "task174_status": record.task174_status,
        "manufacturing_constraint_status": (
            "STRUCTURAL_ADMITTED" if record.structural_admitted else "STRUCTURAL_BLOCKED"
        ),
        "is_candidate_b_baseline_geometry": _is_baseline_candidate_b(record),
        "screening_n1_status": screening_status,
        "n1_duty_w": n1_result.duty_w if n1_result else None,
        "n1_thermal_numeric_status": n1_result.status if n1_result else None,
        "FULL_RATING_CONVERGED": mesh.get("FULL_RATING_CONVERGED"),
        "duty_w_at_finest_mesh": _finest_duty_w(receipt, mesh, n1_result),
        "tube_outlet_temperature_k_n4": receipt.get("N4_TUBE_OUTLET_K") if receipt else None,
        "shell_outlet_temperature_k_n4": receipt.get("N4_SHELL_OUTLET_K") if receipt else None,
        "LIVE_TUBE_DP_PA": receipt.get("LIVE_TUBE_DP_PA") if receipt else None,
        "LIVE_SHELL_DP_PA": receipt.get("LIVE_SHELL_DP_PA") if receipt else None,
        "TUBE_DP_MARGIN_PA": receipt.get("TUBE_DP_MARGIN_PA") if receipt else None,
        "SHELL_DP_MARGIN_PA": receipt.get("SHELL_DP_MARGIN_PA") if receipt else None,
        "SHELL_DP_MARGIN_PERCENT": receipt.get("SHELL_DP_MARGIN_PERCENT") if receipt else None,
        "HYDRAULIC_NOMINAL_STATUS": margin.get("HYDRAULIC_NOMINAL_STATUS"),
        "HYDRAULIC_ROBUSTNESS_STATUS": margin.get("HYDRAULIC_ROBUSTNESS_STATUS"),
        "EXPERIMENTAL_NOMINAL_SIZING_COMPARISON_STATUS": nominal_status,
        "EXPERIMENTAL_NOMINAL_SIZING_COMPARISON_REASONS": nominal_reasons,
        "NOMINAL_EXPERIMENTAL_SIZING_FEASIBLE": nominal_ok,
        "ENGINEERING_SIZING_ELIGIBILITY": eligibility.get("ENGINEERING_SIZING_ELIGIBILITY"),
        "GEOMETRY_COMPLETENESS_STATUS": eligibility.get("GEOMETRY_COMPLETENESS_STATUS"),
        "elimination_reason": None
        if nominal_ok
        else nominal_reasons[0]
        if nominal_reasons
        else screening_status,
    }
    if package:
        row["engineering_delivery_receipt"] = receipt
    return row


def _rank_feasible(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    feasible = [row for row in rows if row.get("NOMINAL_EXPERIMENTAL_SIZING_FEASIBLE")]
    feasible.sort(
        key=lambda item: (
            Decimal(str(item["nominal_tube_outer_area_m2"]))
            if item.get("nominal_tube_outer_area_m2")
            else Decimal("999999")
        )
    )
    for rank, row in enumerate(feasible, start=1):
        row["experimental_rank"] = rank
    return feasible


def run_experimental_multi_candidate_engineering_sizing(
    case: EngineeringCase,
    *,
    max_candidates: int | None = None,
    run_full_mesh_hydraulic: bool = True,
) -> dict[str, Any]:
    """Engineering case → Task168 space → n=1 screen → n=1/2/4 + live hydraulic per admitted candidate."""
    selection = enumerate_experimental_rating_candidates(case)
    records = _record_by_id(selection)
    rate_ids = list(selection.selected_candidate_ids)
    if max_candidates is not None:
        rate_ids = rate_ids[:max_candidates]

    ready_distinct = len(
        {r.geometry_projection_hash for r in selection.records if r.rating_request_ready}
    )
    space_blocker: str | None = None
    if ready_distinct < 2:
        space_blocker = (
            f"INSUFFICIENT_TASK174_READY_DISTINCT_GEOMETRY count={ready_distinct} "
            f"task174_ready={selection.task174_ready_count}"
        )

    candidate_rows: list[dict[str, Any]] = []
    rated_count = 0
    fully_converged = 0

    for candidate_id in rate_ids:
        record = records[candidate_id]
        native = build_native_cell_context(case, selection=selection, candidate_id=candidate_id)
        n1_cache: dict[int, Any] = {}
        n1 = run_experimental_engineering_rating(
            case,
            subdivisions=1,
            native=native,
            mesh_result_cache=n1_cache,
        )
        package: dict[str, Any] | None = None
        screening = n1.status
        if n1.status == ENGINEERING_NUMERIC_VALID:
            rated_count += 1
            if run_full_mesh_hydraulic:
                package = build_experimental_engineering_rating_live_package(
                    case,
                    native=native,
                    run_mesh_ladder=True,
                    run_hydraulic_sensitivity=True,
                )
                if (package.get("mesh_convergence") or {}).get("FULL_RATING_CONVERGED"):
                    fully_converged += 1
            else:
                screening = "N1_NUMERIC_VALID_FULL_LADDER_SKIPPED"
        else:
            screening = f"BLOCKED_N1_{n1.failure_code or n1.status}"

        candidate_rows.append(
            _candidate_report_row(
                case=case,
                record=record,
                n1_result=n1,
                package=package,
                screening_status=screening,
            )
        )

    for record in selection.records:
        if record.candidate_id in rate_ids:
            continue
        candidate_rows.append(
            _candidate_report_row(
                case=case,
                record=record,
                n1_result=None,
                package=None,
                screening_status="NOT_SELECTED_FOR_RATING",
            )
        )

    ranked = _rank_feasible(candidate_rows)
    if ranked:
        ranking_status = "EXPERIMENTAL_RANKING_AVAILABLE"
        best_id = ranked[0]["candidate_id"]
    else:
        ranking_status = "NO_NOMINAL_FEASIBLE_CANDIDATE"
        best_id = None

    gap_summary = [
        {
            "candidate_id": row["candidate_id"],
            "duty_gap_w": (
                float(case.target_duty_w) - float(row["duty_w_at_finest_mesh"])
                if row.get("duty_w_at_finest_mesh") is not None
                else None
            ),
            "reasons": row.get("EXPERIMENTAL_NOMINAL_SIZING_COMPARISON_REASONS"),
        }
        for row in candidate_rows
        if row["candidate_id"] in rate_ids
    ]

    return {
        "schema_version": _SCHEMA,
        "TASK_ID": "V07_R26D_MULTI_CANDIDATE_ENGINEERING_SIZING_MVP",
        "SIZING_TARGET_AUTHORITY": _SIZING_TARGET_AUTHORITY,
        "demonstration_target_duty_w": str(case.target_duty_w),
        "candidate_selection": selection_to_json(selection),
        "CANDIDATE_SPACE_COUNT": selection.candidate_space_count,
        "TASK174_READY_COUNT": selection.task174_ready_count,
        "DISTINCT_READY_GEOMETRY_COUNT": ready_distinct,
        "CANDIDATE_SPACE_BLOCKER": space_blocker,
        "RATED_CANDIDATE_COUNT": rated_count,
        "FULLY_CONVERGED_CANDIDATE_COUNT": fully_converged,
        "NOMINAL_FEASIBLE_COUNT": len(ranked),
        "RANKING_STATUS": ranking_status,
        "BEST_EXPERIMENTAL_CANDIDATE_ID": best_id,
        "ranked_candidates": ranked,
        "candidates": candidate_rows,
        "nominal_infeasible_gap_summary": gap_summary,
        "engineering_comparison_report": _build_comparison_report(
            case, candidate_rows, ranked, best_id
        ),
    }


def _build_comparison_report(
    case: EngineeringCase,
    rows: list[dict[str, Any]],
    ranked: list[dict[str, Any]],
    best_id: str | None,
) -> dict[str, Any]:
    baseline = next((r for r in rows if r.get("is_candidate_b_baseline_geometry")), None)
    best = next((r for r in rows if r["candidate_id"] == best_id), None) if best_id else None
    answer: dict[str, Any] = {
        "question": (
            "Under the same demonstration case, which geometry meets duty and hydraulic limits, "
            "and what area / margin trade-off applies?"
        ),
        "SIZING_TARGET_AUTHORITY": _SIZING_TARGET_AUTHORITY,
        "baseline_candidate_b": baseline,
        "best_experimental_candidate": best,
    }
    if best and baseline and best["candidate_id"] != baseline.get("candidate_id"):
        try:
            area_delta = Decimal(str(best["nominal_tube_outer_area_m2"])) - Decimal(
                str(baseline["nominal_tube_outer_area_m2"])
            )
            answer["area_delta_vs_baseline_m2"] = str(area_delta)
        except Exception:
            pass
        if best.get("SHELL_DP_MARGIN_PA") and baseline.get("SHELL_DP_MARGIN_PA"):
            answer["shell_margin_delta_vs_baseline_pa"] = str(
                Decimal(str(best["SHELL_DP_MARGIN_PA"]))
                - Decimal(str(baseline["SHELL_DP_MARGIN_PA"]))
            )
    if not ranked:
        answer["conclusion"] = "NO_NOMINAL_FEASIBLE_CANDIDATE under demonstration criteria."
    else:
        answer["conclusion"] = (
            f"Candidate {best_id} is the smallest nominal-area feasible geometry in this comparison "
            "(experimental only; not owner-approved design)."
        )
    answer["ranking_table"] = [
        {
            "rank": item.get("experimental_rank"),
            "candidate_id": item["candidate_id"],
            "shell_inside_diameter_m": item["shell_inside_diameter_m"],
            "tube_length_m": item["tube_length_m"],
            "baffle_spacing_m": item["baffle_spacing_m"],
            "physical_tube_count": item["physical_tube_count"],
            "nominal_tube_outer_area_m2": item["nominal_tube_outer_area_m2"],
            "duty_w": item.get("duty_w_at_finest_mesh"),
            "tube_outlet_k": item.get("tube_outlet_temperature_k_n4"),
            "shell_outlet_k": item.get("shell_outlet_temperature_k_n4"),
            "tube_dp_pa": item.get("LIVE_TUBE_DP_PA"),
            "shell_dp_pa": item.get("LIVE_SHELL_DP_PA"),
            "tube_margin_pa": item.get("TUBE_DP_MARGIN_PA"),
            "shell_margin_pa": item.get("SHELL_DP_MARGIN_PA"),
            "mesh_converged": item.get("FULL_RATING_CONVERGED"),
            "hydraulic_robustness": item.get("HYDRAULIC_ROBUSTNESS_STATUS"),
            "engineering_eligibility": item.get("ENGINEERING_SIZING_ELIGIBILITY"),
            "elimination_reason": item.get("elimination_reason"),
        }
        for item in ranked
    ]
    return answer
