"""R12 target-directed live sizing (area search + limited new n=1 ratings)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from prototypes.v07_general_rating_sizing_mvp.candidate_selection import (
    CandidateSelectionOutcome,
    enumerate_experimental_rating_candidates,
    selection_to_json,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase
from prototypes.v07_general_rating_sizing_mvp.experimental_live_workflow import (
    ExperimentalLiveRatingOutcome,
    run_experimental_live_rating_workflow,
)
from prototypes.v07_general_rating_sizing_mvp.r10_frozen_baseline import (
    load_r10_candidate_rating_rows,
)
from prototypes.v07_general_rating_sizing_mvp.target_directed_sizing import (
    build_target_directed_sizing_decision,
)


def _load_selection(outcome_path: Path) -> CandidateSelectionOutcome:
    doc = json.loads(outcome_path.read_text(encoding="utf-8"))
    from prototypes.v07_general_rating_sizing_mvp.candidate_selection import (
        CandidateSelectionRecord,
    )

    records = tuple(
        CandidateSelectionRecord(
            candidate_id=row["candidate_id"],
            candidate_hash=row["candidate_hash"],
            tube_length_m=row["tube_length_m"],
            baffle_spacing_m=row["baffle_spacing_m"],
            geometry_projection_hash=row["geometry_projection_hash"],
            structural_admitted=row["structural_admitted"],
            task168_chain_status=row["task168_chain_status"],
            task168_blocked_stage=row.get("task168_blocked_stage"),
            task168_blocked_codes=tuple(row.get("task168_blocked_codes") or ()),
            task174_status=row["task174_status"],
            rating_request_ready=row["rating_request_ready"],
            rating_request_hash=row.get("rating_request_hash"),
            task171_result_hash=row.get("task171_result_hash"),
            task174_result_hash=row.get("task174_result_hash"),
            selected_for_rating=row["selected_for_rating"],
            task173_rating_status=row["task173_rating_status"],
            physical_tube_count=row.get("physical_tube_count"),
            nominal_tube_outer_area_proxy_m2=row.get("nominal_tube_outer_area_proxy_m2"),
        )
        for row in doc["records"]
    )
    return CandidateSelectionOutcome(
        status=doc["status"],
        candidate_space_hash=doc["candidate_space_hash"],
        selected_candidate_id=doc.get("selected_candidate_id"),
        selected_candidate_ids=tuple(doc.get("selected_candidate_ids") or ()),
        selected_rating_request_hash=doc.get("selected_rating_request_hash"),
        records=records,
        selection_reason=doc.get("selection_reason"),
    )


def run_target_directed_live_sizing_workflow(
    case: EngineeringCase,
    output_dir: Path,
    *,
    mesh_level: int = 1,
) -> ExperimentalLiveRatingOutcome:
    if case.experimental_candidate_selection_mode != "MIN_NOMINAL_TUBE_AREA_SEARCH":
        raise ValueError(
            "R12 workflow requires experimental_candidate_selection_mode="
            "MIN_NOMINAL_TUBE_AREA_SEARCH"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    preflight_selection = enumerate_experimental_rating_candidates(case)
    (output_dir / "R12_PREFLIGHT_CANDIDATE_SEARCH.json").write_text(
        json.dumps(
            {
                "schema_version": "hxforge.r12-preflight-candidate-search.v1",
                "selection_reason": preflight_selection.selection_reason,
                "task174_ready_count": preflight_selection.task174_ready_count,
                "selected_for_rating_count": preflight_selection.selected_for_rating_count,
                "selected_candidate_ids": list(preflight_selection.selected_candidate_ids),
                "selection": selection_to_json(preflight_selection),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    outcome = run_experimental_live_rating_workflow(
        case,
        output_dir,
        mesh_level=mesh_level,
        cli_objective="MIN_NOMINAL_TUBE_AREA",
    )

    selection = _load_selection(output_dir / "CANDIDATE_SELECTION_RESULT.json")
    rating_path = output_dir / "CANDIDATE_RATING_RESULTS.json"
    rating_doc = json.loads(rating_path.read_text(encoding="utf-8"))
    rating_rows: list[dict[str, Any]] = rating_doc["candidates"]
    decision = build_target_directed_sizing_decision(
        case,
        selection,
        rating_rows,
        selection_reason=str(selection.selection_reason or ""),
    )
    (output_dir / "TARGET_DIRECTED_SIZING_DECISION.json").write_text(
        json.dumps(decision, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    r10_rows = load_r10_candidate_rating_rows()
    comparison = {
        "schema_version": "hxforge.r12-r10-comparison.v1",
        "r10_frozen_reference_only": True,
        "r10_candidate_rating_rows": r10_rows,
        "r12_live_rated_rows": rating_rows,
        "target_directed_decision": decision,
    }
    (output_dir / "R12_R10_COMPARISON.json").write_text(
        json.dumps(comparison, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    report_md = _render_r12_markdown(case, selection, rating_rows, decision)
    (output_dir / "R12_ENGINEERING_REPORT.md").write_text(report_md + "\n", encoding="utf-8")
    (output_dir / "R12_ENGINEERING_REPORT.json").write_text(
        json.dumps(
            {
                "schema_version": "hxforge.r12-engineering-report.v1",
                "engineering_case_id": case.engineering_case_id,
                "decision": decision,
                "selection_reason": selection.selection_reason,
                "rated_candidates": rating_rows,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    if outcome.raw_result_path and outcome.raw_result_path.is_file():
        raw = json.loads(outcome.raw_result_path.read_text(encoding="utf-8"))
        raw["task_id"] = "V07_GENERAL_TARGET_DIRECTED_LIVE_SIZING_R12"
        raw["target_directed_sizing_decision"] = decision
        outcome.raw_result_path.write_text(
            json.dumps(raw, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    return outcome


def _render_r12_markdown(
    case: EngineeringCase,
    selection: CandidateSelectionOutcome,
    rating_rows: list[dict[str, Any]],
    decision: dict[str, Any],
) -> str:
    lines = [
        f"# R12 Target-directed sizing — {case.engineering_case_id}",
        "",
        "## Search policy",
        "",
        "- Selection mode: **MIN_NOMINAL_TUBE_AREA_SEARCH**",
        f"- Selection reason: `{selection.selection_reason}`",
        f"- Task174-ready in space: **{selection.task174_ready_count}**",
        f"- Live n=1 ratings this run: **{len(rating_rows)}**",
        "",
        "## R10 frozen baseline (reference only)",
        "",
        (
            "- Candidate A nominal area: "
            f"{decision['R10_BASELINE_CANDIDATE_A']['nominal_tube_outer_area_m2']} m²"
        ),
        f"- Candidate A duty: {decision['R10_BASELINE_CANDIDATE_A']['total_duty_w']} W",
        "",
        "## Live-rated candidates (this run)",
        "",
    ]
    for row in rating_rows:
        geom = row.get("nominal_geometry") or {}
        preview = row.get("constraint_preview") or {}
        lines.append(
            f"- `{row.get('candidate_id')}`: L={geom.get('nominal_tube_length_m')} m, "
            f"area proxy {geom.get('nominal_tube_outer_area_m2')} m², "
            f"duty {row.get('total_duty_w')} W, mesh {row.get('mesh_status')}, "
            f"duty constraint {preview.get('duty_constraint')}, "
            f"wall {row.get('wall_seconds')} s, "
            f"Task172 evals {row.get('task172_local_evaluation_count')}"
        )
    lines.extend(
        [
            "",
            "## Evaluated-set sizing decision",
            "",
            f"- Target constraint status: **{decision['TARGET_CONSTRAINT_STATUS']}**",
            f"- Best evaluated candidate: `{decision.get('BEST_EVALUATED_CANDIDATE_ID')}`",
            f"- Area reduction vs R10 A: {decision.get('AREA_REDUCTION_VS_R10_A_PERCENT')} %",
            f"- Hydraulic scope: **{decision['HYDRAULIC_MODEL_SCOPE']}**",
            f"- {decision['scope_disclaimer']}",
            "",
            "## Not production approved",
            "",
            "- full_rating_converged: false",
            "- production_sizing_verified: false",
        ]
    )
    return "\n".join(lines)
