"""R27G: shell geometry local Pareto search on authorized Task168 discrete lattice."""

# ruff: noqa: E501

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

from prototypes.v07_general_rating_sizing_mvp.calculation_first_automatic_sizing import (
    _constraint_summary,
    _geometry_report_block,
)
from prototypes.v07_general_rating_sizing_mvp.candidate_selection import (
    CandidateSelectionOutcome,
    CandidateSelectionRecord,
    enumerate_experimental_rating_candidates,
    selection_to_json,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase
from prototypes.v07_general_rating_sizing_mvp.experimental_multi_candidate_engineering_sizing import (
    run_experimental_multi_candidate_engineering_sizing,
)
from prototypes.v07_general_rating_sizing_mvp.nozzle_cooptimization_sizing import (
    LOSS_SCENARIO_KEYS,
    _thermal_block_from_row,
)
from prototypes.v07_general_rating_sizing_mvp.nozzle_pressure_budget_solver import (
    cooptimize_nozzles_for_candidate_scenario,
)
from prototypes.v07_general_rating_sizing_mvp.r27e_targeted_recovery import (
    FOUR_065_SHELL_CANDIDATE_IDS,
)
from prototypes.v07_general_rating_sizing_mvp.thermal_hydraulic_geometry_cooptimization_sizing import (
    _internal_hydraulic_satisfied,
    _mesh_rating_evidence_from_multi_row,
    _pareto_mid_band_feasible,
    _phase_a_screening,
    _r27d_formal_feasible,
)

_TASK_ID = "V07_R27G_SHELL_GEOMETRY_LOCAL_PARETO_OPTIMIZATION"
_SCHEMA = "hxforge.r27g-shell-geometry-local-pareto.v27g"
_DESIGN_DUTY_W = Decimal("330000")
_MAX_LOCAL_RATING_BUDGET = 12

# Authorized Task168 ladder: tube_length_m paired with baffle_spacing_m (not independent).
_R27G_LADDER_PAIRS: tuple[tuple[str, str], ...] = (
    ("3.0", "0.6"),
    ("3.5", "0.7"),
    ("4.0", "0.8"),
    ("4.85", "0.97"),
)
_R27G_SHELL_SEARCH_IDS: tuple[str, ...] = ("0.54", "0.56")
_R27G_SHELL_BLOCKED_PENDING_VALIDATION: tuple[str, ...] = ("0.65",)

R27G_PRIMARY_SEED_PREFIX = "9c4b84db"
R27G_REFERENCE_SEED_PREFIX = "7357afdf"
R27G_NEGATIVE_CONTROL_PREFIX = "09dac82a"

R27GOutcomeClass = Literal[
    "STRUCTURAL_BLOCKED",
    "THERMAL_MODEL_BLOCKED",
    "RATING_INCOMPLETE",
    "THERMAL_DUTY_NOT_MET",
    "FULL_PATH_NOT_FEASIBLE",
    "MID_BAND_FEASIBLE_ASSUMPTION_BASED",
    "MID_BAND_POSITIVE_MARGIN_SENSITIVITY",
]


def _record_matches_ladder(record: CandidateSelectionRecord) -> bool:
    return (record.tube_length_m, record.baffle_spacing_m) in _R27G_LADDER_PAIRS


def _seed_role(record: CandidateSelectionRecord) -> str | None:
    prefix = record.candidate_id[:8]
    if prefix == R27G_PRIMARY_SEED_PREFIX:
        return "PRIMARY"
    if prefix == R27G_REFERENCE_SEED_PREFIX:
        return "REFERENCE"
    if prefix == R27G_NEGATIVE_CONTROL_PREFIX:
        return "NEGATIVE_CONTROL"
    return None


def enumerate_r27g_local_search_records(
    selection: CandidateSelectionOutcome,
) -> tuple[CandidateSelectionRecord, ...]:
    """Up to 12 local combinations: 8 rated shell 0.54/0.56 ladder + 4 phase-A-only 0.65."""
    rows: list[CandidateSelectionRecord] = []
    for shell_id in _R27G_SHELL_SEARCH_IDS:
        for tube_len, baffle in _R27G_LADDER_PAIRS:
            match = next(
                (
                    r
                    for r in selection.records
                    if r.shell_inside_diameter_m == shell_id
                    and r.tube_length_m == tube_len
                    and r.baffle_spacing_m == baffle
                ),
                None,
            )
            if match is not None:
                rows.append(match)
    for shell_id in _R27G_SHELL_BLOCKED_PENDING_VALIDATION:
        for tube_len, baffle in _R27G_LADDER_PAIRS:
            match = next(
                (
                    r
                    for r in selection.records
                    if r.shell_inside_diameter_m == shell_id
                    and r.tube_length_m == tube_len
                    and r.baffle_spacing_m == baffle
                ),
                None,
            )
            if match is not None:
                rows.append(match)
    return tuple(rows[: _MAX_LOCAL_RATING_BUDGET + 4])


def r27g_local_rating_candidate_ids(
    selection: CandidateSelectionOutcome,
) -> tuple[str, ...]:
    """Task174-ready, non-0.65 local lattice points queued for mesh rating (≤12)."""
    ids: list[str] = []
    for record in enumerate_r27g_local_search_records(selection):
        if record.shell_inside_diameter_m in _R27G_SHELL_BLOCKED_PENDING_VALIDATION:
            continue
        if not record.rating_request_ready:
            continue
        if record.candidate_id in FOUR_065_SHELL_CANDIDATE_IDS:
            continue
        ids.append(record.candidate_id)
        if len(ids) >= _MAX_LOCAL_RATING_BUDGET:
            break
    return tuple(ids)


def build_r27g_local_selection(case: EngineeringCase) -> CandidateSelectionOutcome:
    base = enumerate_experimental_rating_candidates(
        case,
        rating_selection_policy="r27d",
        rate_all_distinct_task174_ready=False,
    )
    rate_ids = r27g_local_rating_candidate_ids(base)
    return replace(
        base,
        selected_candidate_ids=rate_ids,
        selected_candidate_id=rate_ids[0] if rate_ids else None,
        selection_reason=(
            "R27G_LOCAL_SHELL_LADDER_SEARCH: shell_inside_diameter_m × "
            "authorized (tube_length_m, baffle_spacing_m) pairs; max 12 ratings."
        ),
    )


def _mid_band_margins_pa(
    scenario_results: dict[str, Any],
) -> tuple[Decimal | None, Decimal | None]:
    mid = scenario_results.get("mid_band") or {}
    fp = mid.get("full_path_hydraulic_verification") or {}
    tube_m = fp.get("TUBE_FULL_PATH_DP_MARGIN_PA")
    shell_m = fp.get("SHELL_FULL_PATH_DP_MARGIN_PA")
    if tube_m is not None and shell_m is not None:
        return Decimal(str(tube_m)), Decimal(str(shell_m))

    def _band_best_margin(side: str) -> Decimal | None:
        solve = mid.get(f"{side}_nozzle_solve") or {}
        allowed = solve.get("allowed_total_dp_pa")
        dp_max_d = solve.get("dp_at_max_diameter_min_velocity_pa")
        if allowed is None or dp_max_d is None:
            return None
        return Decimal(str(allowed)) - Decimal(str(dp_max_d))

    tube_d = _band_best_margin("tube")
    shell_d = _band_best_margin("shell")
    return tube_d, shell_d


def classify_r27g_outcome(
    *,
    record: CandidateSelectionRecord,
    multi_row: dict[str, Any] | None,
    scenario_results: dict[str, Any],
    target_duty_w: Decimal,
    case: EngineeringCase,
) -> dict[str, Any]:
    if record.candidate_id in FOUR_065_SHELL_CANDIDATE_IDS or (
        record.shell_inside_diameter_m in _R27G_SHELL_BLOCKED_PENDING_VALIDATION
        and not record.rating_request_ready
    ):
        return {
            "outcome_class": "STRUCTURAL_BLOCKED",
            "detail": "0.65 m shell family blocked pending model validation; not rated.",
        }
    if not record.structural_admitted or record.task168_chain_status.startswith("BLOCKED"):
        return {
            "outcome_class": "STRUCTURAL_BLOCKED",
            "detail": record.task168_blocked_stage,
            "blocked_codes": list(record.task168_blocked_codes),
        }
    if not record.rating_request_ready:
        return {
            "outcome_class": "STRUCTURAL_BLOCKED",
            "detail": f"Task174 status={record.task174_status}",
        }
    if multi_row is None:
        return {"outcome_class": "RATING_INCOMPLETE", "detail": "NOT_QUEUED_FOR_RATING"}
    postpass = multi_row.get("live_thermal_state_hydraulic_postpass") or {}
    applic = postpass.get("correlation_applicability_status")
    if applic not in (None, "APPLICABLE", "EXPERIMENTAL_TRANSITIONAL_APPLICABLE"):
        return {
            "outcome_class": "THERMAL_MODEL_BLOCKED",
            "detail": applic,
        }
    converged = multi_row.get("FULL_RATING_CONVERGED") is True or (
        multi_row.get("rating_participation_status") == "FULLY_RATED"
    )
    if not converged:
        return {
            "outcome_class": "RATING_INCOMPLETE",
            "detail": multi_row.get("rating_participation_status"),
        }
    duty_raw = None
    if multi_row is not None:
        duty_raw = multi_row.get("duty_w_at_finest_mesh")
        if duty_raw is None:
            duty_raw = (multi_row.get("thermal_rating") or {}).get("duty_w")
    if duty_raw is None or Decimal(str(duty_raw)) < target_duty_w:
        return {
            "outcome_class": "THERMAL_DUTY_NOT_MET",
            "detail": f"duty_w_at_finest_mesh={duty_raw}",
        }
    tube_m, shell_m = _mid_band_margins_pa(scenario_results)
    min_margin = None
    if tube_m is not None and shell_m is not None:
        min_margin = min(tube_m, shell_m)
    max_tube = Decimal(str(case.max_tube_side_pressure_drop_pa))
    max_shell = Decimal(str(case.max_shell_side_pressure_drop_pa))
    sensitivity = {
        "mid_band_min_full_path_margin_pa": str(min_margin) if min_margin is not None else None,
        "positive_margin_sensitivity": (min_margin is not None and min_margin > Decimal("0")),
        "margin_ge_5pct_max_dp_sensitivity": (
            min_margin is not None and min_margin >= Decimal("0.05") * min(max_tube, max_shell)
        ),
        "margin_ge_10pct_max_dp_sensitivity": (
            min_margin is not None and min_margin >= Decimal("0.10") * min(max_tube, max_shell)
        ),
        "disclosure": "5% and 10% tiers are sensitivity filters only—not manufacturing acceptance.",
    }
    formal = _r27d_formal_feasible(
        {
            "rating_participation_status": multi_row.get("rating_participation_status"),
            "thermal_rating": _thermal_block_from_row(multi_row, case=case),
            "constraints": _constraint_summary(multi_row, target_duty_w=target_duty_w),
            "loss_scenario_results": scenario_results,
        },
        "mid_band",
    )
    if formal:
        return {
            "outcome_class": "MID_BAND_FEASIBLE_ASSUMPTION_BASED",
            "sensitivity": sensitivity,
        }
    if min_margin is not None and min_margin > Decimal("0"):
        return {
            "outcome_class": "MID_BAND_POSITIVE_MARGIN_SENSITIVITY",
            "sensitivity": sensitivity,
            "detail": "Positive modeled margin but authorized full-path gate not satisfied.",
        }
    gap = str(min_margin) if min_margin is not None else "UNKNOWN"
    return {
        "outcome_class": "FULL_PATH_NOT_FEASIBLE",
        "sensitivity": sensitivity,
        "pressure_gap_pa": gap,
        "detail": "mid_band full-path infeasible under assumption-based K.",
    }


def _pareto_mid_band_positive_margin(
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Pareto on (area, min mid_band margin) for rows with duty met and numeric margins."""
    points: list[tuple[dict[str, Any], Decimal, Decimal]] = []
    for row in rows:
        sens = (row.get("r27g_classification") or {}).get("sensitivity") or {}
        margin_raw = sens.get("mid_band_min_full_path_margin_pa")
        if margin_raw is None:
            continue
        margin = Decimal(str(margin_raw))
        if row.get("r27g_classification", {}).get("outcome_class") == "THERMAL_DUTY_NOT_MET":
            continue
        area_raw = (row.get("geometry") or {}).get("task171_rated_outside_area_m2")
        if area_raw is None:
            continue
        points.append((row, Decimal(str(area_raw)), margin))

    pareto: list[dict[str, Any]] = []
    for row, area, margin in points:
        dominated = False
        for _other, area_b, margin_b in points:
            if area_b <= area and margin_b >= margin and (area_b < area or margin_b > margin):
                dominated = True
                break
        if not dominated:
            pareto.append(
                {
                    "candidate_id": row["candidate_id"],
                    "candidate_id_prefix": row["candidate_id"][:8],
                    "task171_rated_outside_area_m2": str(area),
                    "mid_band_min_full_path_margin_pa": str(margin),
                    "outcome_class": row["r27g_classification"]["outcome_class"],
                    "geometry": row.get("geometry"),
                }
            )
    return pareto


def run_r27g_shell_geometry_local_pareto(
    case: EngineeringCase,
    *,
    run_full_mesh_hydraulic: bool = True,
    precomputed_selection: CandidateSelectionOutcome | None = None,
) -> dict[str, Any]:
    selection = precomputed_selection or build_r27g_local_selection(case)
    local_records = enumerate_r27g_local_search_records(selection)
    multi = run_experimental_multi_candidate_engineering_sizing(
        case,
        precomputed_selection=selection,
        run_full_mesh_hydraulic=run_full_mesh_hydraulic,
    )
    multi_by_id = {row["candidate_id"]: row for row in multi["candidates"]}
    rate_id_set = set(selection.selected_candidate_ids)
    target_duty = Decimal(str(case.target_duty_w))

    rows: list[dict[str, Any]] = []
    for record in local_records:
        phase_a = _phase_a_screening(record, target_duty_w=target_duty)
        multi_row = multi_by_id.get(record.candidate_id)
        scenario_results: dict[str, Any] = {}
        if (
            record.candidate_id in rate_id_set
            and multi_row
            and multi_row.get("FULL_RATING_CONVERGED") is True
            and multi_row.get("rating_participation_status") == "FULLY_RATED"
        ):
            postpass = multi_row.get("live_thermal_state_hydraulic_postpass") or {}
            for scenario_key in LOSS_SCENARIO_KEYS:
                scenario_results[scenario_key] = cooptimize_nozzles_for_candidate_scenario(
                    case=case,
                    record=record,
                    postpass=postpass,
                    loss_scenario_key=scenario_key,
                )
        constraints = _constraint_summary(multi_row, target_duty_w=target_duty) if multi_row else {}
        classification = classify_r27g_outcome(
            record=record,
            multi_row=multi_row,
            scenario_results=scenario_results,
            target_duty_w=target_duty,
            case=case,
        )
        row_payload: dict[str, Any] = {
            "candidate_id": record.candidate_id,
            "candidate_id_prefix": record.candidate_id[:8],
            "seed_role": _seed_role(record),
            "phase_a": phase_a,
            "geometry_fingerprint": {
                "shell_inside_diameter_m": record.shell_inside_diameter_m,
                "tube_length_m": record.tube_length_m,
                "baffle_spacing_m": record.baffle_spacing_m,
                "physical_tube_count": record.physical_tube_count,
            },
            "rating_participation_status": (
                multi_row.get("rating_participation_status") if multi_row else "NOT_RATED"
            ),
            "mesh_rating_evidence": (
                _mesh_rating_evidence_from_multi_row(multi_row) if multi_row else None
            ),
            "geometry": _geometry_report_block(row=multi_row, case=case) if multi_row else {},
            "thermal_rating": (_thermal_block_from_row(multi_row, case=case) if multi_row else {}),
            "constraints": constraints,
            "internal_hydraulic_satisfied": _internal_hydraulic_satisfied(constraints),
            "loss_scenario_results": scenario_results,
            "r27g_classification": classification,
        }
        rows.append(row_payload)

    formal_pareto = _pareto_mid_band_feasible(
        [
            {
                "candidate_id": r["candidate_id"],
                "geometry": r.get("geometry") or {},
                "rating_participation_status": r["rating_participation_status"],
                "thermal_rating": r.get("thermal_rating") or {},
                "constraints": r.get("constraints") or {},
                "loss_scenario_results": r.get("loss_scenario_results") or {},
            }
            for r in rows
        ]
    )
    margin_pareto = _pareto_mid_band_positive_margin(rows)
    duty_ok = [
        r
        for r in rows
        if r.get("r27g_classification", {}).get("outcome_class")
        not in ("STRUCTURAL_BLOCKED", "THERMAL_DUTY_NOT_MET", "RATING_INCOMPLETE")
    ]
    best_gap = None
    best_row = None
    for r in duty_ok:
        sens = (r.get("r27g_classification") or {}).get("sensitivity") or {}
        raw = sens.get("mid_band_min_full_path_margin_pa")
        if raw is None:
            continue
        margin = Decimal(str(raw))
        if best_gap is None or margin > best_gap:
            best_gap = margin
            best_row = r

    return {
        "schema_version": _SCHEMA,
        "TASK_ID": _TASK_ID,
        "generated_at_utc": datetime.now(tz=UTC).isoformat(),
        "upstream_head": "0849db8cc542ab3e58d3c203cfffd2ba6517068b",
        "discrete_search_disclosure": (
            "Task168 discrete space couples tube_length_m with baffle_spacing_m; "
            "local search is shell_inside_diameter_m × authorized ladder pairs—not "
            "continuous baffle spacing at fixed tube length 4.85 m."
        ),
        "local_search_budget": {
            "max_rating_queue": _MAX_LOCAL_RATING_BUDGET,
            "local_record_count": len(local_records),
            "rated_candidate_ids": list(selection.selected_candidate_ids),
        },
        "candidate_selection": selection_to_json(selection),
        "candidates": rows,
        "mid_band_formal_pareto_feasible": formal_pareto,
        "mid_band_margin_pareto_among_rated": margin_pareto,
        "engineering_verdict": {
            "mid_band_formal_feasible_count": len(formal_pareto),
            "mid_band_positive_margin_sensitivity_count": sum(
                1
                for r in rows
                if r.get("r27g_classification", {}).get("outcome_class")
                in (
                    "MID_BAND_FEASIBLE_ASSUMPTION_BASED",
                    "MID_BAND_POSITIVE_MARGIN_SENSITIVITY",
                )
            ),
            "best_mid_band_min_margin_pa": str(best_gap) if best_gap is not None else None,
            "best_mid_band_candidate_id_prefix": (
                best_row["candidate_id_prefix"] if best_row else None
            ),
            "joint_shell_baffle_ladder_can_deliver_mid_band_positive_margin_at_330kw": (
                best_gap is not None
                and best_gap > Decimal("0")
                and best_row is not None
                and (best_row.get("constraints") or {}).get("duty_constraint") == "SATISFIED"
            ),
            "next_step_if_false": (
                "Expand authorized discrete candidate space (owner-approved Task168 "
                "dimension extension) or adjust shell-side bundle geometry beyond current "
                "0.54/0.56 m × four ladder pairs."
            ),
        },
    }


def write_r27g_reports(report: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "R27G_SHELL_GEOMETRY_LOCAL_PARETO.json"
    md_path = output_dir / "R27G_SHELL_GEOMETRY_LOCAL_PARETO.md"
    json_path.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    v = report["engineering_verdict"]
    lines = [
        f"# R27G local shell Pareto ({report['TASK_ID']})",
        "",
        report["discrete_search_disclosure"],
        "",
        "## Verdict",
        "",
        f"- mid_band formal feasible: {v['mid_band_formal_feasible_count']}",
        f"- best mid_band min margin (Pa): {v['best_mid_band_min_margin_pa']} "
        f"({v['best_mid_band_candidate_id_prefix']})",
        f"- joint adjustment delivers mid_band positive margin @330kW: "
        f"**{v['joint_shell_baffle_ladder_can_deliver_mid_band_positive_margin_at_330kw']}**",
        "",
    ]
    for row in report.get("candidates") or []:
        cls = row.get("r27g_classification") or {}
        gf = row.get("geometry_fingerprint") or {}
        lines.append(
            f"- `{row['candidate_id_prefix']}` {cls.get('outcome_class')} "
            f"shell={gf.get('shell_inside_diameter_m')} L={gf.get('tube_length_m')} "
            f"B={gf.get('baffle_spacing_m')}"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path
