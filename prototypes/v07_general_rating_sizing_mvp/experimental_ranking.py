"""Experimental multi-candidate ranking and objective-aware preference (non-production)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from prototypes.v07_general_rating_sizing_mvp.candidate_selection import (
    CandidateSelectionOutcome,
    enumerate_experimental_rating_candidates,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_candidate_eligibility import (
    build_candidate_eligibility,
    constraint_satisfied_ids,
    reevaluate_constraint_for_target,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_hydraulic_constraint_decision import (
    effective_shell_dp_pa,
    live_hydraulic_postpass_enabled,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_objective import (
    DEFAULT_OBJECTIVE,
    ExperimentalSizingObjective,
    resolve_experimental_sizing_objective,
)
from prototypes.v07_general_rating_sizing_mvp.nominal_geometry import nominal_area_for_native
from prototypes.v07_general_rating_sizing_mvp.positive_duty_cell import build_native_cell_context


def _enrich_nominal_geometry(
    case: Any,
    rating_rows: list[dict[str, Any]],
    selection: CandidateSelectionOutcome | None,
) -> CandidateSelectionOutcome:
    if selection is None:
        selection = enumerate_experimental_rating_candidates(case)
    records_by_id = {rec.candidate_id: rec for rec in selection.records}
    for row in rating_rows:
        if row.get("nominal_geometry"):
            continue
        rec = records_by_id.get(row["candidate_id"])
        if rec is None:
            continue
        native = build_native_cell_context(
            case,
            selection=selection,
            candidate_id=row["candidate_id"],
        )
        row["nominal_geometry"] = nominal_area_for_native(
            case,
            native,
            tube_length_m=rec.tube_length_m,
        )
    return selection


def _mesh_ok(row: dict[str, Any]) -> bool:
    return row.get("mesh_status") == "NUMERIC_VALID" or row.get("status") == "NUMERIC_VALID"


def _duty_w(row: dict[str, Any]) -> Decimal:
    return Decimal(str(row["total_duty_w"]))


def _nominal_area_m2(row: dict[str, Any]) -> Decimal | None:
    geom = row.get("nominal_geometry") or {}
    raw = geom.get("nominal_tube_outer_area_m2")
    if raw is None:
        return None
    return Decimal(str(raw))


def _shell_dp_pa(case: Any, row: dict[str, Any]) -> Decimal | None:
    return effective_shell_dp_pa(case, row)


def _pareto_frontier(case: Any, rows: list[dict[str, Any]]) -> list[str]:
    """Non-dominated on (max duty, min nominal area, min shell Δp preview)."""
    ids: list[str] = []
    for i, a in enumerate(rows):
        duty_a = _duty_w(a)
        area_a = _nominal_area_m2(a)
        shell_a = _shell_dp_pa(case, a)
        dominated = False
        for j, b in enumerate(rows):
            if i == j:
                continue
            duty_b = _duty_w(b)
            area_b = _nominal_area_m2(b)
            shell_b = _shell_dp_pa(case, b)
            better_or_equal_duty = duty_b >= duty_a
            area_axis = area_a is not None and area_b is not None
            shell_axis = shell_a is not None and shell_b is not None
            better_or_equal_area = (not area_axis) or (area_b <= area_a)
            better_or_equal_shell = (not shell_axis) or (shell_b <= shell_a)
            strictly_better = (
                duty_b > duty_a
                or (area_axis and area_b < area_a)
                or (shell_axis and shell_b < shell_a)
            )
            if (
                better_or_equal_duty
                and better_or_equal_area
                and better_or_equal_shell
                and strictly_better
            ):
                dominated = True
                break
        if not dominated:
            ids.append(a["candidate_id"])
    return ids


def build_experimental_pareto_result(
    case: Any,
    rating_rows: list[dict[str, Any]],
    *,
    feasible_ids: list[str],
) -> dict[str, Any]:
    feasible_rows = [row for row in rating_rows if row["candidate_id"] in feasible_ids]
    frontier = (
        _pareto_frontier(case, feasible_rows)
        if len(feasible_rows) >= 2
        else [row["candidate_id"] for row in feasible_rows]
    )
    shell_axis = (
        "minimize_live_recalculated_shell_dp_pa"
        if live_hydraulic_postpass_enabled(case)
        else "minimize_modeled_shell_dp_pa_preview"
    )
    return {
        "schema_version": "hxforge.experimental-pareto-result.v1",
        "PARETO_FRONTIER_AVAILABLE": len(frontier) >= 1,
        "pareto_frontier_candidate_ids": frontier,
        "dominance_axes": [
            "maximize_total_duty_w",
            "minimize_nominal_tube_outer_area_m2",
            shell_axis,
        ],
        "production_sizing_verified": False,
    }


def build_experimental_ranking(
    case: Any,
    rating_rows: list[dict[str, Any]],
    *,
    selection: CandidateSelectionOutcome | None = None,
    objective: ExperimentalSizingObjective | str | None = None,
    cli_objective: str | None = None,
) -> dict[str, Any]:
    resolved = (
        objective
        if objective is not None and objective != ""
        else resolve_experimental_sizing_objective(case, cli_override=cli_objective)
    )
    if isinstance(resolved, str):
        resolved_objective: ExperimentalSizingObjective = resolved  # type: ignore[assignment]
    else:
        resolved_objective = resolved

    selection = _enrich_nominal_geometry(case, rating_rows, selection)

    numeric_valid = [row for row in rating_rows if _mesh_ok(row)]
    eligibility = build_candidate_eligibility(case, selection, rating_rows)
    feasible_ids = (
        constraint_satisfied_ids(eligibility)
        if eligibility
        else [
            row["candidate_id"]
            for row in numeric_valid
            if (row.get("constraint_preview") or {}).get("duty_constraint") == "SATISFIED"
            and (row.get("constraint_preview") or {}).get("tube_dp_constraint") == "SATISFIED"
            and (row.get("constraint_preview") or {}).get("shell_dp_constraint") == "SATISFIED"
        ]
    )
    feasible_rows = [row for row in numeric_valid if row["candidate_id"] in feasible_ids]

    comparison_status = (
        "EXPERIMENTAL_COMPARISON_AVAILABLE"
        if len(numeric_valid) >= 2
        else ("EXPERIMENTAL_COMPARISON_AVAILABLE" if len(numeric_valid) == 1 else "NOT_AVAILABLE")
    )

    base = {
        "schema_version": "hxforge.experimental-ranking-result.v1",
        "experimental_sizing_objective": resolved_objective,
        "EXPERIMENTAL_COMPARISON_STATUS": comparison_status,
        "EXPERIMENTAL_COMPARISON_AVAILABLE": comparison_status
        == "EXPERIMENTAL_COMPARISON_AVAILABLE",
        "feasible_candidate_ids": feasible_ids,
        "ranked_candidate_ids": [],
        "preferred_candidate_id": None,
        "EXPERIMENTAL_PREFERRED_CANDIDATE": None,
        "trace": [],
        "production_sizing_verified": False,
        "production_design_approved": False,
        "non_production_disclaimer": "Experimental objective selection — not production sizing.",
    }

    if len(numeric_valid) < 2:
        base.update(
            {
                "EXPERIMENTAL_RANKING_STATUS": "NOT_AVAILABLE",
                "CONDITIONAL_PREFERENCE_STATUS": "NOT_AVAILABLE",
                "ranking_policy_id": f"EXPERIMENTAL_{resolved_objective}",
            }
        )
        return base

    pareto_doc = build_experimental_pareto_result(case, rating_rows, feasible_ids=feasible_ids)
    base["pareto_frontier_candidate_ids"] = pareto_doc["pareto_frontier_candidate_ids"]

    if not feasible_rows:
        base.update(
            {
                "EXPERIMENTAL_RANKING_STATUS": "NOT_AVAILABLE",
                "CONDITIONAL_PREFERENCE_STATUS": "NO_FEASIBLE_CANDIDATE",
                "ranking_policy_id": f"EXPERIMENTAL_{resolved_objective}",
            }
        )
        return base

    def order_key_max_duty(row: dict[str, Any]) -> Decimal:
        return _duty_w(row)

    ordered_feasible: list[dict[str, Any]]
    preferred: str | None = None
    conditional_status = "NOT_AVAILABLE"

    if resolved_objective == "PARETO_ONLY":
        frontier_ids = pareto_doc["pareto_frontier_candidate_ids"]
        ordered_feasible = sorted(
            feasible_rows,
            key=lambda row: (-_duty_w(row), _nominal_area_m2(row) or Decimal("0")),
        )
        base["EXPERIMENTAL_RANKING_STATUS"] = "COMPARISON_ONLY"
        base["CONDITIONAL_PREFERENCE_STATUS"] = "PARETO_FRONTIER_ONLY"
        base["ranking_policy_id"] = "EXPERIMENTAL_PARETO_ONLY"
        base["ranked_candidate_ids"] = frontier_ids
        trace = []
        for rank, cid in enumerate(frontier_ids, start=1):
            row = next(r for r in feasible_rows if r["candidate_id"] == cid)
            trace.append(
                {
                    "rank": rank,
                    "candidate_id": cid,
                    "pareto_member": True,
                    "total_duty_w": str(_duty_w(row)),
                    "nominal_tube_outer_area_m2": (row.get("nominal_geometry") or {}).get(
                        "nominal_tube_outer_area_m2"
                    ),
                }
            )
        base["trace"] = trace
        return base

    if resolved_objective == "MAX_DUTY":
        ordered_feasible = sorted(feasible_rows, key=order_key_max_duty, reverse=True)
        preferred = ordered_feasible[0]["candidate_id"]
        conditional_status = "PREFERENCE_AVAILABLE"
        policy = "EXPERIMENTAL_MAX_DUTY"
    elif resolved_objective == "MIN_NOMINAL_TUBE_AREA":
        ordered_feasible = sorted(
            feasible_rows,
            key=lambda row: (_nominal_area_m2(row) or Decimal("Infinity"), -_duty_w(row)),
        )
        preferred = ordered_feasible[0]["candidate_id"]
        conditional_status = "PREFERENCE_AVAILABLE"
        policy = "EXPERIMENTAL_MIN_NOMINAL_TUBE_AREA"
    elif resolved_objective == "MIN_SHELL_DP_PREVIEW":
        ordered_feasible = sorted(
            feasible_rows,
            key=lambda row: (
                _shell_dp_pa(case, row) or Decimal("Infinity"),
                -_duty_w(row),
            ),
        )
        preferred = ordered_feasible[0]["candidate_id"]
        conditional_status = "PREFERENCE_AVAILABLE"
        policy = "EXPERIMENTAL_MIN_SHELL_DP_PREVIEW"
    else:
        ordered_feasible = feasible_rows
        policy = f"EXPERIMENTAL_{resolved_objective}"

    trace = []
    for rank, row in enumerate(ordered_feasible, start=1):
        trace.append(
            {
                "rank": rank,
                "candidate_id": row["candidate_id"],
                "total_duty_w": str(_duty_w(row)),
                "meets_target_duty": _duty_w(row) >= case.target_duty_w,
                "mesh_result_hash": row.get("mesh_result_hash"),
                "nominal_tube_outer_area_m2": (row.get("nominal_geometry") or {}).get(
                    "nominal_tube_outer_area_m2"
                ),
            }
        )
    base.update(
        {
            "EXPERIMENTAL_RANKING_STATUS": "EXPERIMENTAL_RANKING_AVAILABLE",
            "CONDITIONAL_PREFERENCE_STATUS": conditional_status,
            "ranking_policy_id": policy,
            "ranked_candidate_ids": [row["candidate_id"] for row in ordered_feasible],
            "preferred_candidate_id": preferred,
            "EXPERIMENTAL_PREFERRED_CANDIDATE": preferred,
            "trace": trace,
        }
    )
    return base


def build_offline_duty_scenarios(
    case: Any,
    rating_rows: list[dict[str, Any]],
    *,
    scenario_targets_w: tuple[Decimal, ...],
    objective: ExperimentalSizingObjective = DEFAULT_OBJECTIVE,
) -> dict[str, Any]:
    scenarios: list[dict[str, Any]] = []
    for target in scenario_targets_w:
        per_candidate = []
        feasible: list[str] = []
        for row in rating_rows:
            c_status = reevaluate_constraint_for_target(case, row, target)
            per_candidate.append(
                {
                    "candidate_id": row["candidate_id"],
                    "target_duty_w": str(target),
                    "CONSTRAINT_STATUS": c_status,
                    "total_duty_w": row.get("total_duty_w"),
                    "mesh_status": row.get("mesh_status") or row.get("status"),
                }
            )
            if c_status == "PRELIMINARY_CONSTRAINT_SATISFIED":
                feasible.append(row["candidate_id"])
        feasible_rows = [r for r in rating_rows if r["candidate_id"] in feasible]
        preferred = None
        if objective == "MAX_DUTY" and feasible_rows:
            preferred = max(feasible_rows, key=_duty_w)["candidate_id"]
        elif objective == "MIN_NOMINAL_TUBE_AREA" and feasible_rows:
            preferred = min(
                feasible_rows,
                key=lambda r: (_nominal_area_m2(r) or Decimal("Infinity"), -_duty_w(r)),
            )["candidate_id"]
        scenarios.append(
            {
                "target_duty_w": str(target),
                "OFFLINE_SCREENING_USING_R10_FROZEN_MESH": True,
                "candidates": per_candidate,
                "feasible_candidate_ids": feasible,
                "experimental_sizing_objective": objective,
                "conditional_preferred_candidate_id": preferred,
            }
        )
    return {
        "schema_version": "hxforge.sizing-objective-scenarios.v1",
        "OFFLINE_SCREENING_USING_R10_FROZEN_MESH": True,
        "scenarios": scenarios,
        "production_sizing_verified": False,
    }
