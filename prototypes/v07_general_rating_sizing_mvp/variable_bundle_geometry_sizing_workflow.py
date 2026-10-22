"""R13 variable shell diameter / physical tube count live sizing."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from prototypes.v07_general_rating_sizing_mvp.candidate_selection import (
    CandidateSelectionOutcome,
    CandidateSelectionRecord,
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
from prototypes.v07_general_rating_sizing_mvp.r12_25m_task174_blocker_analysis import (
    analyze_r12_25m_05m_task174_blocker,
)
from prototypes.v07_general_rating_sizing_mvp.target_directed_sizing import (
    build_target_directed_sizing_decision,
)


def _load_selection(outcome_path: Path) -> CandidateSelectionOutcome:
    doc = json.loads(outcome_path.read_text(encoding="utf-8"))
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
            shell_inside_diameter_m=row.get("shell_inside_diameter_m"),
            shell_geometry_id=row.get("shell_geometry_id"),
            task025_total_parallel_flow_area_m2=row.get("task025_total_parallel_flow_area_m2"),
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


def run_variable_bundle_geometry_sizing_workflow(
    case: EngineeringCase,
    output_dir: Path,
    *,
    mesh_level: int = 1,
) -> ExperimentalLiveRatingOutcome:
    if case.experimental_candidate_selection_mode != "VARIABLE_SHELL_BUNDLE_MIN_NOMINAL_AREA_R13":
        raise ValueError(
            "R13 workflow requires experimental_candidate_selection_mode="
            "VARIABLE_SHELL_BUNDLE_MIN_NOMINAL_AREA_R13"
        )
    if case.experimental_bundle_geometry_mode != "VARIABLE_SHELL_DIAMETER_R13":
        raise ValueError(
            "R13 workflow requires experimental_bundle_geometry_mode=VARIABLE_SHELL_DIAMETER_R13"
        )

    output_dir.mkdir(parents=True, exist_ok=True)

    r12_case_path = (
        Path(__file__).resolve().parent / "cases" / "mvp_target_directed_r12.json"
    )
    from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import (
        load_general_engineering_case_json,
    )

    r12_case = load_general_engineering_case_json(r12_case_path.read_text(encoding="utf-8"))
    blocker_doc = analyze_r12_25m_05m_task174_blocker(r12_case)
    (output_dir / "R12_25M_TASK174_BLOCKER_ANALYSIS.json").write_text(
        json.dumps(blocker_doc, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    preflight_selection = enumerate_experimental_rating_candidates(case)
    admitted_shells = sorted(
        {
            row.shell_inside_diameter_m
            for row in preflight_selection.records
            if row.rating_request_ready and row.shell_inside_diameter_m
        }
    )
    distinct_tube_counts = sorted(
        {
            row.physical_tube_count
            for row in preflight_selection.records
            if row.rating_request_ready and row.physical_tube_count is not None
        }
    )
    (output_dir / "R13_PREFLIGHT_CANDIDATE_SEARCH.json").write_text(
        json.dumps(
            {
                "schema_version": "hxforge.r13-preflight-candidate-search.v1",
                "selection_reason": preflight_selection.selection_reason,
                "task174_ready_count": preflight_selection.task174_ready_count,
                "selected_for_rating_count": preflight_selection.selected_for_rating_count,
                "selected_candidate_ids": list(preflight_selection.selected_candidate_ids),
                "admitted_shell_inside_diameters_m": admitted_shells,
                "admitted_physical_tube_counts": distinct_tube_counts,
                "bind_task172_c3_reference_geometry": case.bind_task172_c3_reference_geometry,
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
    decision["C3_APPLICABILITY_STATUS"] = (
        "C3_REFERENCE_BOUND" if case.bind_task172_c3_reference_geometry else "NOT_C3_REFERENCE"
    )
    decision["VARIABLE_PHYSICAL_TUBE_COUNT_SUPPORTED"] = True
    decision["NEW_GEOMETRY_DIMENSION_IMPLEMENTED"] = "SHELL_INSIDE_DIAMETER_M"
    (output_dir / "TARGET_DIRECTED_SIZING_DECISION.json").write_text(
        json.dumps(decision, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    r10_rows = load_r10_candidate_rating_rows()
    comparison = {
        "schema_version": "hxforge.r13-r10-r12-comparison.v1",
        "r10_frozen_reference_only": True,
        "r10_candidate_rating_rows": r10_rows,
        "r13_live_rated_rows": rating_rows,
        "target_directed_decision": decision,
        "r12_25m_task174_blocker": blocker_doc,
    }
    (output_dir / "R13_BASELINE_COMPARISON.json").write_text(
        json.dumps(comparison, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    report_md = _render_r13_markdown(case, selection, rating_rows, decision, blocker_doc)
    (output_dir / "R13_ENGINEERING_REPORT.md").write_text(report_md + "\n", encoding="utf-8")
    (output_dir / "R13_ENGINEERING_REPORT.json").write_text(
        json.dumps(
            {
                "schema_version": "hxforge.r13-engineering-report.v1",
                "engineering_case_id": case.engineering_case_id,
                "decision": decision,
                "selection_reason": selection.selection_reason,
                "rated_candidates": rating_rows,
                "r12_25m_task174_blocker": blocker_doc,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    if outcome.raw_result_path and outcome.raw_result_path.is_file():
        raw = json.loads(outcome.raw_result_path.read_text(encoding="utf-8"))
        raw["task_id"] = "V07_GENERAL_VARIABLE_BUNDLE_GEOMETRY_SIZING_R13"
        raw["target_directed_sizing_decision"] = decision
        raw["variable_bundle_geometry"] = {
            "mode": case.experimental_bundle_geometry_mode,
            "c3_applicability_status": decision["C3_APPLICABILITY_STATUS"],
        }
        outcome.raw_result_path.write_text(
            json.dumps(raw, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    manifest_path = output_dir / "EVIDENCE_MANIFEST.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["task_id"] = "V07_GENERAL_VARIABLE_BUNDLE_GEOMETRY_SIZING_R13"
        for name in (
            "R13_ENGINEERING_REPORT.json",
            "R13_ENGINEERING_REPORT.md",
            "TARGET_DIRECTED_SIZING_DECISION.json",
            "R13_BASELINE_COMPARISON.json",
            "R12_25M_TASK174_BLOCKER_ANALYSIS.json",
            "R13_PREFLIGHT_CANDIDATE_SEARCH.json",
        ):
            path = output_dir / name
            if path.is_file():
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                manifest.setdefault("files", {})[name] = digest
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    return outcome


def _render_r13_markdown(
    case: EngineeringCase,
    selection: CandidateSelectionOutcome,
    rating_rows: list[dict[str, Any]],
    decision: dict[str, Any],
    blocker_doc: dict[str, Any],
) -> str:
    lines = [
        f"# R13 Variable bundle geometry sizing — {case.engineering_case_id}",
        "",
        "## Geometry freedom",
        "",
        "- Dimension: **shell inside diameter** → Task021 tube count and Task025 flow area",
        f"- C3 reference binding: **{case.bind_task172_c3_reference_geometry}**",
        f"- Applicability: **{decision.get('C3_APPLICABILITY_STATUS')}**",
        "",
        "## P0 — R12 2.5 m / 0.5 m Task174 blocker (C3 reference case)",
        "",
        f"- Task174 status: **{blocker_doc.get('task174_status')}**",
        f"- Physical tube count at blocker: **{blocker_doc.get('physical_tube_count')}**",
        f"- Interpretation: {blocker_doc.get('engineering_interpretation', 'n/a')}",
        "",
        "## Search policy",
        "",
        "- Selection mode: **VARIABLE_SHELL_BUNDLE_MIN_NOMINAL_AREA_R13**",
        f"- Selection reason: `{selection.selection_reason}`",
        f"- Task174-ready in space: **{selection.task174_ready_count}**",
        f"- Live n=1 ratings this run: **{len(rating_rows)}**",
        "",
        "## Live-rated candidates (this run)",
        "",
    ]
    for row in rating_rows:
        geom = row.get("nominal_geometry") or {}
        preview = row.get("constraint_preview") or {}
        bundle = row.get("bundle_geometry") or {}
        lines.append(
            f"- `{row.get('candidate_id')}`: shell ID {bundle.get('shell_inside_diameter_m')} m, "
            f"N={bundle.get('physical_tube_count')}, "
            f"L={geom.get('nominal_tube_length_m')} m, "
            f"area {geom.get('nominal_tube_outer_area_m2')} m², "
            f"duty {row.get('total_duty_w')} W, mesh {row.get('mesh_status')}, "
            f"Task025 A_flow {bundle.get('task025_total_parallel_flow_area_m2')} m²"
        )
        lines.append(
            f"  - constraints: duty {preview.get('duty_constraint')}, "
            f"tube Δp {preview.get('tube_dp_constraint')}, "
            f"shell Δp {preview.get('shell_dp_constraint')}"
        )
    lines.extend(
        [
            "",
            "## Evaluated-set sizing decision",
            "",
            f"- Target constraint status: **{decision['TARGET_CONSTRAINT_STATUS']}**",
            f"- Best evaluated candidate: `{decision.get('BEST_EVALUATED_CANDIDATE_ID')}`",
            f"- Target duty: {decision.get('TARGET_DUTY_W')} W",
            f"- Duty overshoot ratio: {decision.get('DUTY_OVERSHOOT_RATIO_VS_TARGET')}",
            f"- Hydraulic scope: **{decision['HYDRAULIC_MODEL_SCOPE']}**",
            "",
            "## Engineering conclusion",
            "",
            _engineering_conclusion(case, rating_rows, decision),
            "",
            "## Not production approved",
            "",
            "- full_rating_converged: false",
            "- production_sizing_verified: false",
        ]
    )
    return "\n".join(lines)


def _engineering_conclusion(
    case: EngineeringCase,
    rating_rows: list[dict[str, Any]],
    decision: dict[str, Any],
) -> str:
    target = case.target_duty_w
    rated = [r for r in rating_rows if r.get("mesh_status") == "NUMERIC_VALID"]
    if not rated:
        return (
            "No new live n=1 ratings completed in the applicable envelope; "
            "cannot claim progress toward 9.5 kW without fabricated duty."
        )
    duties = [r.get("total_duty_w") for r in rated]
    min_duty = min(duties, key=lambda v: float(v or "inf"))
    if float(min_duty) > float(target) * 1.05:
        return (
            f"Variable shell diameter changed physical tube count and hydraulic inputs, "
            f"but the lowest live-rated duty ({min_duty} W) remains far above the "
            f"{target} W target under current single-phase Bell–Delaware / Task172 closure "
            f"without C3 reference scaling. Further reduction likely needs additional "
            f"discrete freedoms (e.g. fewer tubes via smaller shell within layout rules, "
            f"different tube OD/pitch authority, or partial duty / multi-pass strategies) "
            f"rather than duty scaling."
        )
    return "At least one rated candidate approached the target duty within the stated envelope."
