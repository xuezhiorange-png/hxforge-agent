"""R8 evidence: PH boundary closure and live n=1 mesh."""

# ruff: noqa: E501

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v07_general_rating_sizing_mvp.boundary_ph_diagnostics import (
    build_boundary_ph_reconstruction_diagnostics,
)
from prototypes.v07_general_rating_sizing_mvp.candidate_selection import (
    enumerate_experimental_rating_candidates,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import (
    load_general_engineering_case_json,
)
from prototypes.v07_general_rating_sizing_mvp.native_thermal_boundary_binding import (
    build_native_thermal_boundary_from_case,
    disclosure_document,
)
from prototypes.v07_general_rating_sizing_mvp.positive_duty_cell import (
    build_native_cell_context,
    run_mesh_numeric_with_profile,
    solve_positive_duty_cell_root,
)
from prototypes.v07_general_rating_sizing_mvp.report import write_engineering_reports

LIVE_CASE = Path(__file__).resolve().parent / "cases" / "mvp_tube_hot_shell_cold_r7.json"
_DEFAULT_EVIDENCE_DIR = "docs/tasks/evidence/V07-GENERAL-RATING-LIVE-BOUNDARY-N1-CLOSURE-R8"
_FEASIBLE_SHELL_LEFT_TEMPERATURE_K = 298.5


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    provider = CoolPropProvider()
    case = load_general_engineering_case_json(LIVE_CASE.read_text(encoding="utf-8"))
    binding = build_native_thermal_boundary_from_case(case, provider)
    binding_doc = disclosure_document(binding)
    (output_dir / "THERMAL_BOUNDARY_BINDING.json").write_text(
        json.dumps(binding_doc, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    ph_diag = build_boundary_ph_reconstruction_diagnostics(case, provider=provider)
    (output_dir / "BOUNDARY_PH_RECONSTRUCTION_DIAGNOSTICS.json").write_text(
        json.dumps(ph_diag, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    sel = enumerate_experimental_rating_candidates(case)
    native = build_native_cell_context(case, selection=sel)
    cell_root = solve_positive_duty_cell_root(
        native,
        shell_left_basis="feasible_shell_left_face",
        shell_temperature_k=_FEASIBLE_SHELL_LEFT_TEMPERATURE_K,
        case=case,
        enable_live_thermal_boundary=True,
    )
    mesh, profile, obs = run_mesh_numeric_with_profile(
        native,
        subdivisions=1,
        case=case,
        enable_live_thermal_boundary=True,
        enable_ephemeral_tp_cache=False,
    )
    numeric_valid = mesh.get("status") == "NUMERIC_VALID"
    if numeric_valid:
        (output_dir / "LIVE_N1_MESH_RESULT.json").write_text(
            json.dumps(mesh, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    else:
        (output_dir / "LIVE_N1_BLOCKED_RESULT.json").write_text(
            json.dumps(mesh, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    experimental_mesh = {
        "live_boundary_n1_numeric_valid": numeric_valid,
        "cell_root": cell_root,
        "mesh_result": mesh,
        "solver_performance_profile": profile,
        "property_provider_identity": "CoolPropProvider",
        "ephemeral_tp_cache_enabled": False,
        "ph_boundary_diagnostics": ph_diag,
    }
    report_paths = write_engineering_reports(
        case,
        preflight={"status": "VALID", "candidate_count": 1},
        sizing_outcome=None,
        output_dir=output_dir,
        workflow_status="PARTIAL_RATING_ACCEPTED" if numeric_valid else "PARTIAL_RATING_BLOCKED",
        experimental_mesh=experimental_mesh,
    )

    total_seconds = round(time.perf_counter() - t0, 3)
    raw: dict[str, Any] = {
        "schema_version": "hxforge.general-r8-raw-result.v1",
        "task_id": "V07_GENERAL_RATING_LIVE_BOUNDARY_N1_CLOSURE_R8",
        "live_case_id": case.engineering_case_id,
        "candidate_id": native.candidate_id,
        "rating_request_hash": native.rating_request_hash,
        "live_boundary_n1_numeric_valid": numeric_valid,
        "cell_root": cell_root,
        "mesh": mesh,
        "mesh_observables": (
            {
                "total_duty_w": str(obs.total_duty_w),
                "tube_outlet_temperature_k": str(obs.tube_outlet_temperature_k),
                "shell_outlet_temperature_k": str(obs.shell_outlet_temperature_k),
                "energy_balance_residual_w": str(obs.energy_balance_residual_w),
                "terminal_boundary_residual_k": str(obs.terminal_boundary_residual_k),
            }
            if obs is not None
            else None
        ),
        "total_numerical_seconds": total_seconds,
        "report_json_path": str(report_paths[0]),
        "report_md_path": str(report_paths[1]),
    }
    raw_path = output_dir / "RAW_RESULT.json"
    raw_path.write_text(json.dumps(raw, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    manifest_entries: dict[str, str] = {}
    for name in (
        "BOUNDARY_PH_RECONSTRUCTION_DIAGNOSTICS.json",
        "THERMAL_BOUNDARY_BINDING.json",
        "LIVE_N1_MESH_RESULT.json",
        "LIVE_N1_BLOCKED_RESULT.json",
        "ENGINEERING_REPORT.json",
        "ENGINEERING_REPORT.md",
        "RAW_RESULT.json",
    ):
        path = output_dir / name
        if path.is_file():
            manifest_entries[name] = _sha256_file(path)
    (output_dir / "EVIDENCE_MANIFEST.json").write_text(
        json.dumps(
            {
                "schema_version": "hxforge.evidence-manifest.v1",
                "task_id": "V07_GENERAL_RATING_LIVE_BOUNDARY_N1_CLOSURE_R8",
                "files": manifest_entries,
                "total_numerical_seconds": total_seconds,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return raw


if __name__ == "__main__":
    import sys

    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(_DEFAULT_EVIDENCE_DIR)
    print(
        json.dumps({"status": "ok", "numeric_valid": main(out)["live_boundary_n1_numeric_valid"]})
    )
