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
from prototypes.v07_general_rating_sizing_mvp.engineering_hydraulic_path_geometry import (
    R26D_HISTORICAL_LONG_BASELINE_REFERENCE,
    candidate_geometry_from_selection_record,
    historical_long_baseline_area,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_engineering_rating_core import (
    ENGINEERING_NUMERIC_VALID,
    run_experimental_engineering_rating,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_engineering_rating_live_bridge import (
    build_experimental_engineering_rating_live_package,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_transitional_tube_hydraulic import (
    APPLICABILITY_STATUS as R20_TRANSITIONAL_APPLICABILITY,
)
from prototypes.v07_general_rating_sizing_mvp.positive_duty_cell import (
    build_native_cell_context,
)

_SCHEMA = "hxforge.experimental-multi-candidate-engineering-sizing.v26e"
_TASK_ID = "V07_R26E_ENGINEERING_TRADEOFF_AND_CANDIDATE_EXPANSION"
_SIZING_TARGET_AUTHORITY = "EXPERIMENTAL_DEMONSTRATION_NOT_OWNER_APPROVED"
_BASELINE_CANDIDATE_B_FINGERPRINT = ("3.0", "0.6", "0.56")
_ALLOWED_CORRELATION_APPLICABILITY = frozenset({"APPLICABLE", R20_TRANSITIONAL_APPLICABILITY})


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
            duty = results[level].duty_w
            if duty is not None:
                return float(duty)
    if n1_result is not None and n1_result.duty_w is not None:
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


def _hydraulic_blocker_reasons(
    postpass: dict[str, Any], receipt: dict[str, Any] | None
) -> list[str]:
    reasons: list[str] = []
    if postpass.get("hydraulic_constraint_status") != "SATISFIED":
        reasons.append(
            f"HYDRAULIC_CONSTRAINT_{postpass.get('hydraulic_constraint_status', 'NOT_EVALUATED')}"
        )
    if postpass.get("tube_dp_constraint") != "SATISFIED":
        reasons.append(f"TUBE_DP_{postpass.get('tube_dp_constraint', 'NOT_EVALUATED')}")
    if postpass.get("shell_dp_constraint") != "SATISFIED":
        reasons.append(f"SHELL_DP_{postpass.get('shell_dp_constraint', 'NOT_EVALUATED')}")
    if postpass.get("tube_hydraulic_recompute_status") == "BLOCKED":
        reasons.append("TUBE_HYDRAULIC_RECOMPUTE_BLOCKED")
    if postpass.get("shell_hydraulic_recompute_status") == "BLOCKED":
        reasons.append("SHELL_HYDRAULIC_RECOMPUTE_BLOCKED")
    applicability = postpass.get("correlation_applicability_status")
    if applicability not in _ALLOWED_CORRELATION_APPLICABILITY:
        reasons.append(f"CORRELATION_APPLICABILITY_{applicability or 'NOT_EVALUATED'}")
    blockers = postpass.get("blockers") or []
    if blockers:
        reasons.append("HYDRAULIC_POSTPASS_BLOCKERS_PRESENT")
    if receipt:
        hr_status = receipt.get("HYDRAULIC_CONSTRAINT_STATUS")
        if hr_status not in (None, "SATISFIED", "NOT_EVALUATED"):
            reasons.append(f"HYDRAULIC_RECEIPT_{hr_status}")
        if receipt.get("LIVE_HYDRAULIC_IMPLEMENTED") is False:
            reasons.append("LIVE_HYDRAULIC_NOT_IMPLEMENTED")
    return reasons


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
    postpass = package.get("live_thermal_state_hydraulic_postpass") or {}
    hydraulic_receipt = package.get("hydraulic_receipt") or {}
    reasons.extend(_hydraulic_blocker_reasons(postpass, hydraulic_receipt))
    margin = package.get("hydraulic_margin") or {}
    if margin.get("NOMINAL_CONSTRAINT_STATUS") != "SATISFIED":
        reasons.append("HYDRAULIC_NOMINAL_MARGIN_NOT_SATISFIED")
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
    if package is not None:
        engineering_eligibility = package.get("ENGINEERING_SIZING_ELIGIBILITY")
        geometry_completeness = package.get("GEOMETRY_COMPLETENESS_STATUS")
    else:
        engineering_eligibility = "NOT_EVALUATED"
        geometry_completeness = "NOT_EVALUATED"
    nominal_ok, nominal_status, nominal_reasons = _nominal_experimental_comparison_status(
        package, case=case
    )
    tube_area = record.nominal_tube_outer_area_proxy_m2
    if screening_status == "NOT_SELECTED_FOR_RATING":
        participation = "NOT_SELECTED_FOR_RATING"
    elif package is not None and mesh.get("FULL_RATING_CONVERGED"):
        participation = "FULLY_RATED"
    elif n1_result is not None:
        participation = "SCREENED_N1_ONLY"
    else:
        participation = "NOT_EVALUATED"
    row: dict[str, Any] = {
        "candidate_geometry_authority": candidate_geometry_from_selection_record(record),
        "rating_participation_status": participation,
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
        "ENGINEERING_SIZING_ELIGIBILITY": engineering_eligibility,
        "GEOMETRY_COMPLETENESS_STATUS": geometry_completeness,
        "elimination_reason": None
        if participation in {"NOT_SELECTED_FOR_RATING", "NOT_EVALUATED", "SCREENED_N1_ONLY"}
        else None
        if nominal_ok
        else nominal_reasons[0]
        if nominal_reasons
        else screening_status,
    }
    if package:
        row["engineering_delivery_receipt"] = receipt
        postpass = package.get("live_thermal_state_hydraulic_postpass") or {}
        from prototypes.v07_general_rating_sizing_mvp.engineering_hydraulic_dp_breakdown import (
            build_hydraulic_dp_breakdown,
        )

        row["hydraulic_dp_breakdown"] = build_hydraulic_dp_breakdown(postpass, case=case)
    return row


def _decimal_or_zero(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def _observed_hydraulic_risk_score(robustness: str | None) -> int:
    if robustness == "SENSITIVITY_INDICATES_RISK":
        return 2
    if robustness == "NOT_OWNER_DESIGN_TOLERANCE_VERIFIED":
        return 1
    return 0


def _pareto_vector(row: dict[str, Any], *, target_duty_w: Decimal) -> tuple[Decimal, ...]:
    duty = _decimal_or_zero(row.get("duty_w_at_finest_mesh"))
    overshoot = max(Decimal("0"), duty - target_duty_w)
    return (
        _decimal_or_zero(row.get("nominal_tube_outer_area_m2")),
        -_decimal_or_zero(row.get("TUBE_DP_MARGIN_PA")),
        -_decimal_or_zero(row.get("SHELL_DP_MARGIN_PA")),
        overshoot,
        Decimal(str(_observed_hydraulic_risk_score(row.get("HYDRAULIC_ROBUSTNESS_STATUS")))),
    )


def _dominates(a: tuple[Decimal, ...], b: tuple[Decimal, ...]) -> bool:
    if len(a) != len(b):
        return False
    le_all = all(x <= y for x, y in zip(a, b, strict=True))
    lt_any = any(x < y for x, y in zip(a, b, strict=True))
    return le_all and lt_any


def _pareto_frontier_candidates(
    feasible: list[dict[str, Any]], *, target_duty_w: Decimal
) -> list[str]:
    if not feasible:
        return []
    vectors = {
        row["candidate_id"]: _pareto_vector(row, target_duty_w=target_duty_w) for row in feasible
    }
    frontier: list[str] = []
    for row in feasible:
        cid = row["candidate_id"]
        dominated = any(
            other_id != cid and _dominates(vectors[other_id], vectors[cid]) for other_id in vectors
        )
        if not dominated:
            frontier.append(cid)
    frontier.sort(
        key=lambda cid: (
            vectors[cid][0],
            vectors[cid][4],
            -vectors[cid][3],
        )
    )
    return frontier


def _build_experimental_tradeoff_views(
    case: EngineeringCase,
    rows: list[dict[str, Any]],
    ranked: list[dict[str, Any]],
) -> dict[str, Any]:
    fully_rated_feasible = [
        row
        for row in rows
        if row.get("NOMINAL_EXPERIMENTAL_SIZING_FEASIBLE")
        and row.get("FULL_RATING_CONVERGED") is True
        and row.get("rating_participation_status") == "FULLY_RATED"
    ]
    feasible = fully_rated_feasible
    target = Decimal(str(case.target_duty_w))
    min_area_row = ranked[0] if ranked else None
    lower_risk_sorted = sorted(
        feasible,
        key=lambda row: (
            _observed_hydraulic_risk_score(row.get("HYDRAULIC_ROBUSTNESS_STATUS")),
            -_decimal_or_zero(row.get("SHELL_DP_MARGIN_PA")),
            _decimal_or_zero(row.get("nominal_tube_outer_area_m2")),
        ),
    )
    pareto_ids = _pareto_frontier_candidates(feasible, target_duty_w=target)
    baseline_b = next((r for r in rows if r.get("is_candidate_b_baseline_geometry")), None)
    historical_long_area = historical_long_baseline_area()
    middle_candidates = [
        r
        for r in feasible
        if baseline_b
        and baseline_b.get("candidate_id") != r.get("candidate_id")
        and _decimal_or_zero(baseline_b.get("nominal_tube_outer_area_m2"))
        < _decimal_or_zero(r.get("nominal_tube_outer_area_m2"))
        < historical_long_area
    ]
    middle_answer: dict[str, Any] = {
        "question": (
            "Is there a more reasonable intermediate geometry between the ~60.5 m2 short "
            "baseline and the ~97.8 m2 historical R26D long reference under the same case?"
        ),
        "current_rating_scope": (
            "Intermediate assessment uses candidates with FULL_RATING_CONVERGED in this run only."
        ),
        "historical_long_baseline_reference": R26D_HISTORICAL_LONG_BASELINE_REFERENCE,
        "baseline_short_area_m2": baseline_b.get("nominal_tube_outer_area_m2")
        if baseline_b
        else None,
        "historical_long_reference_area_m2": str(historical_long_area),
        "intermediate_feasible_candidates": [
            {
                "candidate_id": r["candidate_id"],
                "candidate_geometry_authority": r.get("candidate_geometry_authority"),
                "tube_length_m": r["candidate_geometry_authority"]["tube_length_m"],
                "baffle_spacing_m": r["candidate_geometry_authority"]["baffle_spacing_m"],
                "shell_inside_diameter_m": r["candidate_geometry_authority"][
                    "shell_inside_diameter_m"
                ],
                "physical_tube_count": r["candidate_geometry_authority"]["physical_tube_count"],
                "nominal_tube_outer_area_m2": r["candidate_geometry_authority"][
                    "nominal_tube_outer_area_m2"
                ],
                "area_delta_vs_short_baseline_m2": str(
                    _decimal_or_zero(
                        r["candidate_geometry_authority"].get("nominal_tube_outer_area_m2")
                    )
                    - _decimal_or_zero(baseline_b.get("nominal_tube_outer_area_m2"))
                )
                if baseline_b
                else None,
                "shell_dp_margin_pa": r.get("SHELL_DP_MARGIN_PA"),
                "tube_dp_margin_pa": r.get("TUBE_DP_MARGIN_PA"),
                "hydraulic_robustness": r.get("HYDRAULIC_ROBUSTNESS_STATUS"),
            }
            for r in middle_candidates
        ],
    }
    if middle_candidates:
        middle_answer["conclusion"] = (
            "At least one fully rated, nominally feasible geometry lies between the short baseline "
            "and the historical long reference area (experimental comparison only)."
        )
    elif len(feasible) >= 1 and baseline_b:
        middle_answer["conclusion"] = (
            "No fully rated nominally feasible geometry in this run lies strictly between the "
            "short baseline and historical long reference areas; unrated combinations are not "
            "treated as eliminated."
        )
    else:
        middle_answer["conclusion"] = (
            "Insufficient fully rated feasible candidates to assess intermediates."
        )

    return {
        "ENGINEERING_DESIGN_PREFERENCE": "OWNER_POLICY_REQUIRED",
        "MIN_AREA_NOMINAL_CANDIDATE_ID": min_area_row["candidate_id"] if min_area_row else None,
        "MIN_AREA_SCOPE": "FULLY_RATED_NOMINAL_FEASIBLE_CANDIDATES_THIS_RUN",
        "LOWER_OBSERVED_HYDRAULIC_RISK_CANDIDATE_IDS": [
            row["candidate_id"] for row in lower_risk_sorted
        ],
        "AREA_HYDRAULIC_MARGIN_PARETO_FRONTIER_CANDIDATE_IDS": pareto_ids,
        "pareto_frontier_rows": [
            next(r for r in feasible if r["candidate_id"] == cid) for cid in pareto_ids
        ],
        "lower_risk_ranking_table": [
            {
                "candidate_id": row["candidate_id"],
                "observed_hydraulic_risk_score": _observed_hydraulic_risk_score(
                    row.get("HYDRAULIC_ROBUSTNESS_STATUS")
                ),
                "hydraulic_robustness": row.get("HYDRAULIC_ROBUSTNESS_STATUS"),
                "shell_dp_margin_pa": row.get("SHELL_DP_MARGIN_PA"),
                "tube_dp_margin_pa": row.get("TUBE_DP_MARGIN_PA"),
                "nominal_tube_outer_area_m2": row.get("nominal_tube_outer_area_m2"),
            }
            for row in lower_risk_sorted
        ],
        "intermediate_geometry_answer": middle_answer,
        "disclosure": (
            "Trade-off views are experimental comparisons only. Lower observed hydraulic risk "
            "does not constitute owner-approved robustness. No weighted score is an approved design standard."
        ),
    }


def _rank_feasible(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    feasible = [
        row
        for row in rows
        if row.get("NOMINAL_EXPERIMENTAL_SIZING_FEASIBLE")
        and row.get("FULL_RATING_CONVERGED") is True
        and row.get("rating_participation_status") == "FULLY_RATED"
    ]
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
    screened_count = len(rate_ids)
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
                    mesh_result_cache=n1_cache,
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

    tradeoff = _build_experimental_tradeoff_views(case, candidate_rows, ranked)

    return {
        "schema_version": _SCHEMA,
        "TASK_ID": _TASK_ID,
        "SIZING_TARGET_AUTHORITY": _SIZING_TARGET_AUTHORITY,
        "demonstration_target_duty_w": str(case.target_duty_w),
        "candidate_selection": selection_to_json(selection),
        "CANDIDATE_SPACE_COUNT": selection.candidate_space_count,
        "TASK174_READY_COUNT": selection.task174_ready_count,
        "DISTINCT_READY_GEOMETRY_COUNT": ready_distinct,
        "CANDIDATE_SPACE_BLOCKER": space_blocker,
        "SCREENED_CANDIDATE_COUNT": screened_count,
        "RATED_CANDIDATE_COUNT": rated_count,
        "FULLY_RATED_CANDIDATE_COUNT": fully_converged,
        "FULLY_CONVERGED_CANDIDATE_COUNT": fully_converged,
        "NOMINAL_FEASIBLE_COUNT": len(ranked),
        "RANKING_STATUS": ranking_status,
        "BEST_EXPERIMENTAL_CANDIDATE_ID": best_id,
        "MIN_AREA_NOMINAL_CANDIDATE_ID": tradeoff.get("MIN_AREA_NOMINAL_CANDIDATE_ID"),
        "PARETO_CANDIDATE_IDS": tradeoff.get("AREA_HYDRAULIC_MARGIN_PARETO_FRONTIER_CANDIDATE_IDS"),
        "ranked_candidates": ranked,
        "candidates": candidate_rows,
        "nominal_infeasible_gap_summary": gap_summary,
        "experimental_tradeoff_comparison": tradeoff,
        "engineering_comparison_report": _build_comparison_report(
            case, candidate_rows, ranked, best_id, tradeoff
        ),
    }


def _build_comparison_report(
    case: EngineeringCase,
    rows: list[dict[str, Any]],
    ranked: list[dict[str, Any]],
    best_id: str | None,
    tradeoff: dict[str, Any] | None = None,
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
    if tradeoff:
        answer["experimental_tradeoff_comparison"] = tradeoff
        answer["intermediate_geometry_answer"] = tradeoff.get("intermediate_geometry_answer")
    return answer
