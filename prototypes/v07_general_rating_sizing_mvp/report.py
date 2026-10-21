"""Engineering report generation (JSON + Markdown)."""

# ruff: noqa: E501

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from hexagent.exchangers.shell_tube.task173_integrated_sizing import Task173SizingSuccessResult
from prototypes.v07_general_rating_sizing_mvp.case_streams import design_conditions_for_report
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase


def _candidate_rows(outcome: Task173SizingSuccessResult) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in outcome.candidate_records:
        rows.append(
            {
                "candidate_id": entry.candidate_id,
                "candidate_hash": entry.candidate_hash,
                "status": entry.status,
                "disposition": entry.disposition,
                "selected_dimensions": list(entry.selected_dimensions),
                "rated_duty_w": str(entry.rated_duty_w) if entry.rated_duty_w is not None else None,
                "tube_dp_pa": str(entry.tube_dp_pa) if entry.tube_dp_pa is not None else None,
                "shell_dp_pa": str(entry.shell_dp_pa) if entry.shell_dp_pa is not None else None,
                "duty_constraint": entry.duty_constraint,
                "tube_dp_constraint": entry.tube_dp_constraint,
                "shell_dp_constraint": entry.shell_dp_constraint,
                "accepted_mesh_subdivisions": entry.accepted_subdivisions_per_interval,
                "headroom_mesh_subdivisions": entry.headroom_subdivisions_per_interval,
                "ranking_score": str(entry.ranking_score)
                if entry.ranking_score is not None
                else None,
                "rank": entry.rank,
                "warnings": list(entry.warnings),
                "blockers": list(entry.blockers),
            }
        )
    return rows


def build_report_payload(
    case: EngineeringCase,
    *,
    preflight: dict[str, Any],
    sizing_outcome: Task173SizingSuccessResult | None,
    workflow_status: str,
    experimental_mesh: dict[str, Any] | None = None,
) -> dict[str, Any]:
    generated_at = datetime.now(UTC).isoformat()
    payload: dict[str, Any] = {
        "schema_version": "hxforge.engineering-report.v1",
        "generated_at_utc": generated_at,
        "engineering_case_id": case.engineering_case_id,
        "workflow_status": workflow_status,
        "experimental_ranking_status": (
            "EXPERIMENTAL_RANKING_AVAILABLE"
            if sizing_outcome and sizing_outcome.selection_status == "RECOMMENDATION_AVAILABLE"
            else "NOT_AVAILABLE"
        ),
        "production_design_approved": False,
        "numerical_authority_status": "CANDIDATE",
        "production_integration": False,
        "fiv_numeric_limit_authority": "MISSING",
        "r2a_production_authority_verified": False,
        "design_conditions": design_conditions_for_report(case),
        "candidate_generation": {
            "preflight_status": preflight.get("status"),
            "candidate_count": preflight.get("candidate_count"),
            "distinct_geometry_count": preflight.get("distinct_geometry_count"),
            "candidate_space_hash": preflight.get("candidate_space_hash"),
            "geometry_constraints": case.candidate_constraints.model_dump(mode="json"),
        },
        "candidates": preflight.get("candidates", []),
        "rating_and_sizing": None,
        "experimental_low_mesh_rating": experimental_mesh,
        "ranking": None,
        "engineering_warnings": [
            "EXPERIMENTAL_MVP — not production design approval.",
            "FIV numeric limits not verified (FIV_NUMERIC_LIMIT_AUTHORITY=MISSING).",
            "R2A production certificate authority not verified for this workflow.",
            "Task167 configuration rule pack approval not claimed.",
        ],
        "model_applicability": {
            "fluid": "PURE_ORDINARY_WATER single-phase",
            "construction": "FIXED_TUBESHEET E-shell one shell pass",
            "service_envelope": "Tube 12 kg/s, shell 20 kg/s, 298.15–300 K, 100–101325 Pa",
        },
        "solver": {
            "task173_integrated_sizing": sizing_outcome is not None,
            "mesh_profile": "V07-T172-REAL-CASE-PRODUCTION-MESH-PROFILE-R1 (full ladder when rated)",
        },
        "notes": case.notes,
    }
    if experimental_mesh is not None:
        payload["rating_and_sizing"] = {
            "mode": "EXPERIMENTAL_LOW_MESH_ONLY",
            "full_rating_converged": experimental_mesh.get("full_rating_converged", False),
            "low_mesh_numeric_valid": experimental_mesh.get("low_mesh_numeric_valid", False),
            "mesh_comparison_available": experimental_mesh.get("mesh_comparison_available", False),
            "sizing_evaluated": False,
            "experimental_ranking_status": "NOT_YET_AVAILABLE",
            "frozen_r4_n1": experimental_mesh.get("frozen_r4_n1"),
            "mesh_levels": experimental_mesh.get("mesh_levels", []),
            "mesh_comparison": experimental_mesh.get("mesh_comparison"),
        }
    if sizing_outcome is not None:
        payload["rating_and_sizing"] = {
            "selection_status": sizing_outcome.selection_status,
            "request_hash": sizing_outcome.request_hash,
            "result_hash": sizing_outcome.result_hash,
            "candidate_count": sizing_outcome.candidate_count,
            "pass_count": sizing_outcome.pass_count,
            "warn_count": sizing_outcome.warn_count,
            "blocked_count": sizing_outcome.blocked_count,
            "recommendable_count": sizing_outcome.recommendable_count,
        }
        payload["candidate_results"] = _candidate_rows(sizing_outcome)
        payload["ranking"] = {
            "recommended_candidate_id": sizing_outcome.recommended_candidate_id,
            "alternative_candidate_ids": list(sizing_outcome.alternative_candidate_ids),
            "ranked_candidate_ids": list(sizing_outcome.ranked_candidate_ids),
            "trace": [item.model_dump(mode="json") for item in sizing_outcome.ranking_trace],
        }
        if sizing_outcome.recommended_candidate_id:
            rec = next(
                (
                    row
                    for row in sizing_outcome.candidate_records
                    if row.candidate_id == sizing_outcome.recommended_candidate_id
                ),
                None,
            )
            if rec is not None:
                payload["recommendation_rationale"] = {
                    "ranking_score": str(rec.ranking_score) if rec.ranking_score else None,
                    "rated_duty_w": str(rec.rated_duty_w) if rec.rated_duty_w else None,
                    "tube_dp_pa": str(rec.tube_dp_pa) if rec.tube_dp_pa else None,
                    "shell_dp_pa": str(rec.shell_dp_pa) if rec.shell_dp_pa else None,
                    "policy": sizing_outcome.ranking_policy_id,
                }
    return payload


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# Engineering Report — {report['engineering_case_id']}",
        "",
        f"Generated: {report['generated_at_utc']}",
        "",
        "## Executive summary",
        "",
        f"- Workflow status: **{report['workflow_status']}**",
        f"- Experimental ranking: **{report['experimental_ranking_status']}**",
        "- Production design approved: **false** (experimental MVP)",
        "",
        "## Design conditions",
        "",
    ]
    dc = report["design_conditions"]
    stream_lines: list[str] = []
    if "tube_side" in dc:
        conv = dc.get("heat_transfer_convention") or {}
        stream_lines = [
            f"- Tube side ({conv.get('tube_thermal_role', 'HOT')}): "
            f"{dc['tube_side']['inlet_temperature_k']} K @ "
            f"{dc['tube_side']['mass_flow_kg_s']} kg/s",
            f"- Shell side ({conv.get('shell_thermal_role', 'COLD')}): "
            f"{dc['shell_side']['inlet_temperature_k']} K @ "
            f"{dc['shell_side']['mass_flow_kg_s']} kg/s",
        ]
    else:
        stream_lines = [
            f"- Cold side: {dc['cold_side']['inlet_temperature_k']} K @ "
            f"{dc['cold_side']['mass_flow_kg_s']} kg/s",
            f"- Hot side: {dc['hot_side']['inlet_temperature_k']} K @ "
            f"{dc['hot_side']['mass_flow_kg_s']} kg/s",
        ]
    lines.extend(
        [
            f"- Target duty: {dc['target_duty_w']} W",
            f"- Max tube Δp: {dc['max_tube_dp_pa']} Pa",
            f"- Max shell Δp: {dc['max_shell_dp_pa']} Pa",
            *stream_lines,
            "",
            "## Candidate generation (Task168)",
            "",
            f"- Preflight status: {report['candidate_generation']['preflight_status']}",
            f"- Candidates enumerated: {report['candidate_generation']['candidate_count']}",
            f"- Distinct geometries: {report['candidate_generation']['distinct_geometry_count']}",
            "",
        ]
    )
    low_mesh = report.get("experimental_low_mesh_rating") or report.get("rating_and_sizing")
    if low_mesh and low_mesh.get("mesh_levels"):
        lines.extend(["## Experimental mesh rating (native Task173)", ""])
        for row in low_mesh["mesh_levels"]:
            lines.append(
                f"- n={row.get('mesh_level')}: duty {row.get('total_duty_w')} W, "
                f"energy residual {row.get('energy_balance_residual_w')} W, "
                f"terminal residual {row.get('terminal_boundary_residual_k')} K, "
                f"Task172 evals {row.get('task172_local_evaluation_count')}, "
                f"wall {row.get('wall_seconds')} s"
            )
        if low_mesh.get("mesh_comparison"):
            cmp_row = low_mesh["mesh_comparison"]
            lines.append(
                f"- n1/n2 duty delta: {cmp_row.get('duty_delta_w')} W "
                f"({cmp_row.get('duty_delta_percent')} %), status {cmp_row.get('mesh_comparison_status')}"
            )
        lines.append("")
    if report.get("candidate_results"):
        lines.append("## Rating, hydraulic, and sizing results")
        lines.append("")
        for row in report["candidate_results"]:
            lines.append(f"### Candidate `{row['candidate_id'][:8]}…`")
            lines.append("")
            lines.append(f"- Status: {row['status']} ({row['disposition']})")
            lines.append(f"- Rated duty: {row['rated_duty_w']} W")
            lines.append(f"- Tube Δp: {row['tube_dp_pa']} Pa | Shell Δp: {row['shell_dp_pa']} Pa")
            mesh = row.get("accepted_mesh_subdivisions")
            lines.append(f"- Accepted mesh subdivisions: {mesh}")
            if row["blockers"]:
                lines.append(f"- Blockers: {', '.join(row['blockers'])}")
            lines.append("")
        ranking = report.get("ranking") or {}
        lines.extend(
            [
                "## Ranking",
                "",
                f"- Recommended: `{ranking.get('recommended_candidate_id')}`",
                f"- Alternatives: {ranking.get('alternative_candidate_ids')}",
                "",
            ]
        )
    lines.extend(
        [
            "## Engineering warnings",
            "",
        ]
    )
    for warn in report["engineering_warnings"]:
        lines.append(f"- {warn}")
    lines.extend(
        [
            "",
            "## Model applicability",
            "",
            f"- {report['model_applicability']['fluid']}",
            f"- {report['model_applicability']['construction']}",
            f"- Service envelope: {report['model_applicability']['service_envelope']}",
            "",
        ]
    )
    if report.get("notes"):
        lines.extend(["## Notes", "", report["notes"], ""])
    return "\n".join(lines)


def write_engineering_reports(
    case: EngineeringCase,
    *,
    preflight: dict[str, Any],
    sizing_outcome: Task173SizingSuccessResult | None,
    output_dir: Path,
    workflow_status: str,
    experimental_mesh: dict[str, Any] | None = None,
) -> tuple[Path, Path]:
    payload = build_report_payload(
        case,
        preflight=preflight,
        sizing_outcome=sizing_outcome,
        workflow_status=workflow_status,
        experimental_mesh=experimental_mesh,
    )
    json_path = output_dir / "ENGINEERING_REPORT.json"
    md_path = output_dir / "ENGINEERING_REPORT.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(payload) + "\n", encoding="utf-8")
    return json_path, md_path
