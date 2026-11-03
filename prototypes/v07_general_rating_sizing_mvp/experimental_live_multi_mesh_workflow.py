"""Experimental live multi-mesh rating workflow (R16)."""

# ruff: noqa: E501

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v07_general_rating_sizing_mvp.candidate_selection import (
    enumerate_experimental_rating_candidates,
    selection_to_json,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase
from prototypes.v07_general_rating_sizing_mvp.experimental_live_scope import (
    check_experimental_live_rating_scope,
)
from prototypes.v07_general_rating_sizing_mvp.live_multi_mesh_rating import (
    PINNED_R16_CANDIDATE_ID,
    attach_live_hydraulic_postpass_for_mesh,
    build_live_multi_mesh_analysis,
    highest_numeric_valid_mesh_row,
    render_multi_mesh_markdown_table,
    run_mesh_levels_for_candidate,
)
from prototypes.v07_general_rating_sizing_mvp.native_thermal_boundary_binding import (
    build_native_thermal_boundary_from_case,
    disclosure_document,
)
from prototypes.v07_general_rating_sizing_mvp.positive_duty_cell import build_native_cell_context
from prototypes.v07_general_rating_sizing_mvp.preflight import enumerate_task168_candidates
from prototypes.v07_general_rating_sizing_mvp.sizing_request_builder import (
    build_task173_sizing_request,
    sizing_request_identity,
)


@dataclass(frozen=True)
class LiveMultiMeshOutcome:
    status: str
    engineering_case_id: str
    output_dir: Path
    raw_result_path: Path | None
    analysis: dict[str, Any] | None
    total_numerical_seconds: float
    cli_success: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "hxforge.experimental-live-multi-mesh-outcome.v1",
            "status": self.status,
            "engineering_case_id": self.engineering_case_id,
            "raw_result_path": str(self.raw_result_path) if self.raw_result_path else None,
            "total_numerical_seconds": self.total_numerical_seconds,
            "cli_success": self.cli_success,
            "analysis": self.analysis,
        }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_candidate_id(
    selection: Any,
    *,
    preferred_id: str | None = None,
) -> str | None:
    if preferred_id and preferred_id in selection.selected_candidate_ids:
        return preferred_id
    if preferred_id:
        for record in selection.records:
            if record.candidate_id == preferred_id and record.task174_status == "VALIDATED":
                return preferred_id
    if selection.selected_candidate_ids:
        return selection.selected_candidate_ids[0]
    for record in selection.records:
        if record.task174_status == "VALIDATED" and record.rating_request_ready:
            return record.candidate_id
    return None


def run_experimental_live_multi_mesh_workflow(
    case: EngineeringCase,
    output_dir: Path,
    *,
    mesh_levels: Sequence[int] = (1, 2),
    pinned_candidate_id: str | None = PINNED_R16_CANDIDATE_ID,
    enable_ephemeral_tp_cache: bool = False,
) -> LiveMultiMeshOutcome:
    output_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    scope_code, scope_detail = check_experimental_live_rating_scope(case)
    (output_dir / "GENERAL_ENGINEERING_CASE.json").write_text(
        case.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    if scope_code != "IN_SCOPE":
        raw_path = output_dir / "RAW_RESULT.json"
        raw_path.write_text(
            json.dumps(
                {
                    "schema_version": "hxforge.experimental-live-multi-mesh-raw.v1",
                    "status": "INPUT_OUT_OF_SUPPORTED_SCOPE",
                    "detail": scope_detail,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return LiveMultiMeshOutcome(
            status="INPUT_OUT_OF_SUPPORTED_SCOPE",
            engineering_case_id=case.engineering_case_id,
            output_dir=output_dir,
            raw_result_path=raw_path,
            analysis=None,
            total_numerical_seconds=time.perf_counter() - t0,
            cli_success=False,
        )

    provider = CoolPropProvider()
    binding_doc = disclosure_document(build_native_thermal_boundary_from_case(case, provider))
    (output_dir / "NATIVE_THERMAL_BOUNDARY.json").write_text(
        json.dumps(binding_doc, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    sizing_request = build_task173_sizing_request(case)
    preflight = enumerate_task168_candidates(sizing_request)
    (output_dir / "TASK168_PREFLIGHT.json").write_text(
        json.dumps(preflight, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "TASK173_SIZING_REQUEST_HASH.txt").write_text(
        sizing_request_identity(sizing_request) + "\n", encoding="utf-8"
    )
    if preflight.get("status") != "VALID":
        raw_path = output_dir / "RAW_RESULT.json"
        raw_path.write_text(
            json.dumps(
                {"status": "BLOCKED_PREFLIGHT", "preflight": preflight},
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return LiveMultiMeshOutcome(
            status="BLOCKED_PREFLIGHT",
            engineering_case_id=case.engineering_case_id,
            output_dir=output_dir,
            raw_result_path=raw_path,
            analysis=None,
            total_numerical_seconds=time.perf_counter() - t0,
            cli_success=False,
        )

    selection = enumerate_experimental_rating_candidates(case)
    (output_dir / "CANDIDATE_SELECTION_RESULT.json").write_text(
        json.dumps(selection_to_json(selection), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    candidate_id = _resolve_candidate_id(selection, preferred_id=pinned_candidate_id)
    if candidate_id is None:
        raw_path = output_dir / "RAW_RESULT.json"
        raw_path.write_text(
            json.dumps({"status": "BLOCKED_NO_RATING_READY_CANDIDATE"}, indent=2) + "\n",
            encoding="utf-8",
        )
        return LiveMultiMeshOutcome(
            status="BLOCKED_CANDIDATE_SELECTION",
            engineering_case_id=case.engineering_case_id,
            output_dir=output_dir,
            raw_result_path=raw_path,
            analysis=None,
            total_numerical_seconds=time.perf_counter() - t0,
            cli_success=False,
        )

    native = build_native_cell_context(case, selection=selection, candidate_id=candidate_id)
    budget_s = float(case.solver_budget.total_budget_s)
    mesh_rows, observations = run_mesh_levels_for_candidate(
        case,
        native,
        mesh_levels=mesh_levels,
        budget_s=budget_s,
        t0=t0,
        enable_ephemeral_tp_cache=enable_ephemeral_tp_cache,
    )

    analysis = build_live_multi_mesh_analysis(
        candidate_id=candidate_id,
        rating_request_hash=native.rating_request_hash,
        mesh_level_rows=mesh_rows,
        coarse_obs=observations.get(1),
        fine_obs=observations.get(2),
    )

    highest = highest_numeric_valid_mesh_row(mesh_rows)
    live_postpass: dict[str, Any] | None = None
    if highest is not None and getattr(case, "experimental_live_thermal_hydraulic_postpass", False):
        live_postpass = attach_live_hydraulic_postpass_for_mesh(
            case,
            native,
            highest,
            candidate_id=candidate_id,
        )
        highest["live_thermal_state_hydraulic_postpass"] = live_postpass
        analysis["HIGHEST_MESH_LIVE_HYDRAULIC_POSTPASS"] = live_postpass
        if live_postpass:
            analysis["HIGHEST_MESH_LIVE_TUBE_DP_PA"] = live_postpass.get("recalculated_tube_dp_pa")
            analysis["HIGHEST_MESH_LIVE_SHELL_DP_PA"] = live_postpass.get(
                "recalculated_shell_dp_pa"
            )
            analysis["HYDRAULIC_CONSTRAINT_STATUS"] = live_postpass.get(
                "hydraulic_constraint_status"
            )
            analysis["CORRELATION_APPLICABILITY_STATUS"] = live_postpass.get(
                "correlation_applicability_status"
            )

    (output_dir / "LIVE_MULTI_MESH_LEVEL_RESULTS.json").write_text(
        json.dumps(
            {
                "schema_version": "hxforge.live-multi-mesh-level-results.v1",
                "candidate_id": candidate_id,
                "candidate_hash": native.candidate_hash,
                "mesh_levels_requested": list(mesh_levels),
                "levels": mesh_rows,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (output_dir / "LIVE_MULTI_MESH_ANALYSIS.json").write_text(
        json.dumps(analysis, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    md_lines = [
        f"# R16 Live multi-mesh rating — {case.engineering_case_id}",
        "",
        f"- Candidate: `{candidate_id}`",
        f"- Mesh levels requested: {list(mesh_levels)}",
        "",
        *render_multi_mesh_markdown_table(analysis),
    ]
    if live_postpass:
        md_lines.extend(
            [
                "## Highest-mesh live hydraulic post-pass",
                "",
                f"- Tube Δp: {live_postpass.get('recalculated_tube_dp_pa')} Pa",
                f"- Shell Δp: {live_postpass.get('recalculated_shell_dp_pa')} Pa",
                f"- Hydraulic status: {live_postpass.get('hydraulic_constraint_status')}",
                f"- Applicability: {live_postpass.get('correlation_applicability_status')}",
                "",
            ]
        )
    (output_dir / "R16_MULTI_MESH_ENGINEERING_REPORT.md").write_text(
        "\n".join(md_lines) + "\n", encoding="utf-8"
    )

    total_seconds = round(time.perf_counter() - t0, 3)
    raw: dict[str, Any] = {
        "schema_version": "hxforge.experimental-live-multi-mesh-raw.v1",
        "task_id": "V07_LIVE_MULTI_MESH_RATING_CONVERGENCE_R16",
        "engineering_case_id": case.engineering_case_id,
        "candidate_id": candidate_id,
        "mesh_levels": list(mesh_levels),
        "analysis": analysis,
        "total_numerical_seconds": total_seconds,
        "full_rating_converged": False,
        "production_sizing_verified": False,
    }
    raw_path = output_dir / "RAW_RESULT.json"
    raw_path.write_text(json.dumps(raw, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    status = "EXPERIMENTAL_COMPLETE"
    if (
        analysis.get("MESH_CONVERGENCE_STATUS") == "NUMERICAL_BLOCKED"
        or analysis.get("REAL_N1_RATING_STATUS") != "NUMERIC_VALID"
    ):
        status = "PARTIAL_RATING_BLOCKED"

    return LiveMultiMeshOutcome(
        status=status,
        engineering_case_id=case.engineering_case_id,
        output_dir=output_dir,
        raw_result_path=raw_path,
        analysis=analysis,
        total_numerical_seconds=total_seconds,
        cli_success=analysis.get("REAL_N1_RATING_STATUS") == "NUMERIC_VALID",
    )


def live_multi_mesh_exit_code(outcome: LiveMultiMeshOutcome) -> int:
    return 0 if outcome.cli_success else 1
