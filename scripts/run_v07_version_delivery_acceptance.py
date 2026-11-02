#!/usr/bin/env python3
"""V07 version delivery end-to-end acceptance."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _reclassify_r27h_fixture() -> dict:
    from decimal import Decimal

    from prototypes.v07_general_rating_sizing_mvp.calculation_first_automatic_sizing import (
        _constraint_summary,
        _geometry_report_block,
    )
    from prototypes.v07_general_rating_sizing_mvp.r27h_candidate_space_extension import (
        _DESIGN_DUTY_W,
        _classify_r27h_final,
        _finalize_report,
        _mesh_rating_evidence_from_multi_row,
        build_r27h_selection,
        load_r27h_engineering_case,
    )

    fixture = Path("tests/fixtures/R27H_CANDIDATE_SPACE_EXTENSION.json")
    raw = json.loads(fixture.read_text())
    case = load_r27h_engineering_case()
    sel = build_r27h_selection(case)
    for row in raw.get("candidates") or []:
        if not row.get("loss_scenario_results"):
            continue
        rec = next(r for r in sel.records if r.candidate_id == row["candidate_id"])
        gf = row.get("geometry_fingerprint") or {}
        multi_row = {
            "FULL_RATING_CONVERGED": True,
            "rating_participation_status": "FULLY_RATED",
            "screening_n1_status": "EXPERIMENTAL_ENGINEERING_NUMERIC_VALID",
            "n1_thermal_numeric_status": "EXPERIMENTAL_ENGINEERING_NUMERIC_VALID",
            "duty_w_at_finest_mesh": (row.get("constraints") or {}).get("duty_w_at_finest_mesh"),
            "live_thermal_state_hydraulic_postpass": {
                "correlation_applicability_status": "APPLICABLE",
                "tube_dp_constraint": (row.get("constraints") or {}).get("tube_dp_constraint"),
                "shell_dp_constraint": (row.get("constraints") or {}).get("shell_dp_constraint"),
                "hydraulic_constraint_status": (row.get("constraints") or {}).get(
                    "hydraulic_constraint_status"
                ),
            },
            "TUBE_DP_MARGIN_PA": (row.get("constraints") or {}).get("tube_dp_margin_pa"),
            "SHELL_DP_MARGIN_PA": (row.get("constraints") or {}).get("shell_dp_margin_pa"),
            "NOMINAL_EXPERIMENTAL_SIZING_FEASIBLE": True,
            "candidate_geometry_authority": {
                "shell_inside_diameter_m": gf.get("shell_inside_diameter_m"),
                "physical_tube_count": gf.get("physical_tube_count"),
                "tube_length_m": gf.get("tube_length_m"),
                "baffle_spacing_m": gf.get("baffle_spacing_m"),
            },
        }
        multi_row["constraints"] = _constraint_summary(multi_row, target_duty_w=_DESIGN_DUTY_W)
        row["constraints"] = multi_row["constraints"]
        row["mesh_rating_evidence"] = _mesh_rating_evidence_from_multi_row(multi_row)
        row["geometry"] = _geometry_report_block(row=multi_row, case=case)
        row["r27h_classification"] = _classify_r27h_final(
            record=rec,
            table_row=row["table_row"],
            phase_a=row["phase_a"],
            multi_row=multi_row,
            scenario_results=row["loss_scenario_results"],
            case=case,
        )
    partial = _finalize_report(case, sel, raw["candidates"], stopped_after_phase_a=False)
    raw["engineering_answers"] = partial["engineering_answers"]
    raw["mid_band_formal_pareto"] = partial["mid_band_formal_pareto"]
    raw["mid_band_margin_pareto"] = partial["mid_band_margin_pareto"]
    fixture.write_text(json.dumps(raw, indent=2, default=str) + "\n")
    return raw


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/opt/cursor/artifacts/v07-version-delivery"),
    )
    parser.add_argument(
        "--reuse-r27h-fixture",
        action="store_true",
        help="Reclassify sealed R27H mesh results (no remesh).",
    )
    args = parser.parse_args()

    from prototypes.v07_general_rating_sizing_mvp.v07_version_delivery import (
        load_v07_acceptance_case,
        run_v07_end_to_end_acceptance,
        write_v07_delivery_artifacts,
    )

    if args.reuse_r27h_fixture:
        r27h = _reclassify_r27h_fixture()
        case = load_v07_acceptance_case()
        report = run_v07_end_to_end_acceptance(case, run_full_mesh=False)
        report["r27h_search_report"] = r27h
        from prototypes.v07_general_rating_sizing_mvp.v07_version_delivery import (
            _acceptance_matrix,
            _build_design_report,
        )

        answers = r27h.get("engineering_answers") or {}
        best_row = next(
            (
                c
                for c in r27h.get("candidates") or []
                if c.get("candidate_id_prefix") == answers.get("best_candidate_id_prefix")
            ),
            None,
        )
        mid = ((best_row or {}).get("loss_scenario_results") or {}).get("mid_band") or {}
        fp = mid.get("full_path_hydraulic_verification") or {}
        sens = (best_row or {}).get("r27h_classification") or {}
        report["acceptance_function_matrix"] = _acceptance_matrix(r27h)
        report["design_report"] = _build_design_report(
            case,
            best_row,
            fp,
            (sens.get("sensitivity") or {}).get("max_nozzle_velocity_audit") or {},
            sens,
        )
        passed = sum(1 for v in report["acceptance_function_matrix"].values() if v == "PASS")
        partial = sum(1 for v in report["acceptance_function_matrix"].values() if v == "PARTIAL")
        failed = sum(1 for v in report["acceptance_function_matrix"].values() if v == "FAIL")
        report["delivery_summary"] = {
            "passed": passed,
            "partial": partial,
            "failed": failed,
            "delivery_status": (
                "EXPERIMENTAL_E2E_COMPLETE_WITH_ASSUMPTION_K_DESIGN"
                if answers.get("mid_band_full_path_feasible_count", 0) > 0
                else "EXPERIMENTAL_E2E_COMPLETE_NO_ROBUST_MID_BAND_MARGIN"
            ),
        }
    else:
        case = load_v07_acceptance_case()
        report = run_v07_end_to_end_acceptance(case, run_full_mesh=True)

    write_v07_delivery_artifacts(report, args.output_dir)
    Path("tests/fixtures/V07_VERSION_DELIVERY_ACCEPTANCE.json").write_text(
        json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8"
    )
    print(json.dumps(report["delivery_summary"], indent=2))


if __name__ == "__main__":
    main()
