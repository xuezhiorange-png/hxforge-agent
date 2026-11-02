#!/usr/bin/env python3
"""V07 final live E2E delivery acceptance CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _reclassify_r27h_fixture() -> dict:
    from prototypes.v07_general_rating_sizing_mvp.calculation_first_automatic_sizing import (
        _constraint_summary,
        _geometry_report_block,
    )
    from prototypes.v07_general_rating_sizing_mvp.r27h_candidate_space_extension import (
        _classify_r27h_final,
        _finalize_report,
        _mesh_rating_evidence_from_multi_row,
        build_r27h_selection,
        load_r27h_engineering_case,
    )

    fixture = Path("tests/fixtures/R27H_CANDIDATE_SPACE_EXTENSION.json")
    raw = json.loads(fixture.read_text(encoding="utf-8"))
    case = load_r27h_engineering_case()
    sel = build_r27h_selection(case)
    for row in raw.get("candidates") or []:
        if not row.get("loss_scenario_results"):
            continue
        ev0 = row.get("mesh_rating_evidence") or {}
        if ev0.get("full_rating_converged") is not True and not row.get(
            "engineering_delivery_receipt"
        ):
            continue
        rec = next(r for r in sel.records if r.candidate_id == row["candidate_id"])
        gf = row.get("geometry_fingerprint") or {}
        multi_row = {
            "FULL_RATING_CONVERGED": ev0.get("full_rating_converged", True),
            "rating_participation_status": row.get("rating_participation_status", "FULLY_RATED"),
            "screening_n1_status": row.get(
                "screening_n1_status", "EXPERIMENTAL_ENGINEERING_NUMERIC_VALID"
            ),
            "n1_thermal_numeric_status": row.get("n1_thermal_numeric_status"),
            "duty_w_at_finest_mesh": (row.get("constraints") or {}).get("duty_w_at_finest_mesh"),
            "live_thermal_state_hydraulic_postpass": row.get(
                "live_thermal_state_hydraulic_postpass"
            )
            or {
                "correlation_applicability_status": "APPLICABLE",
                "tube_dp_constraint": (row.get("constraints") or {}).get("tube_dp_constraint"),
                "shell_dp_constraint": (row.get("constraints") or {}).get("shell_dp_constraint"),
                "hydraulic_constraint_status": (row.get("constraints") or {}).get(
                    "hydraulic_constraint_status"
                ),
            },
            "TUBE_DP_MARGIN_PA": (row.get("constraints") or {}).get("tube_dp_margin_pa"),
            "SHELL_DP_MARGIN_PA": (row.get("constraints") or {}).get("shell_dp_margin_pa"),
            "NOMINAL_EXPERIMENTAL_SIZING_FEASIBLE": row.get(
                "NOMINAL_EXPERIMENTAL_SIZING_FEASIBLE", True
            ),
            "candidate_geometry_authority": {
                "shell_inside_diameter_m": gf.get("shell_inside_diameter_m"),
                "physical_tube_count": gf.get("physical_tube_count"),
                "tube_length_m": gf.get("tube_length_m"),
                "baffle_spacing_m": gf.get("baffle_spacing_m"),
            },
        }
        multi_row["constraints"] = _constraint_summary(multi_row, target_duty_w=case.target_duty_w)
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
        "--case",
        type=Path,
        default=Path("tests/fixtures/v07_live_acceptance_user_case.json"),
        help="User engineering case JSON (330 kW baseline by default).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/opt/cursor/artifacts/v07-final-acceptance"),
    )
    parser.add_argument(
        "--reuse-r27h-fixture",
        action="store_true",
        help="REPLAY only: reclassify sealed R27H fixture; not live E2E.",
    )
    parser.add_argument(
        "--independent-input-test",
        action="store_true",
        help="Run controlled input-change verification (Phase A); writes sidecar JSON.",
    )
    args = parser.parse_args()

    from prototypes.v07_general_rating_sizing_mvp.v07_version_delivery import (
        ExecutionMode,
        load_user_case_json,
        run_v07_live_e2e,
        verify_independent_input_effects,
        write_v07_delivery_artifacts,
    )

    case = load_user_case_json(args.case)

    independent_sidecar: dict | None = None
    if args.independent_input_test:
        independent_sidecar = verify_independent_input_effects(case)

    if args.reuse_r27h_fixture:
        r27h = _reclassify_r27h_fixture()
        report = run_v07_live_e2e(
            case,
            mode=ExecutionMode.FIXTURE_REPLAY,
            r27h_precomputed=r27h,
        )
    else:
        report = run_v07_live_e2e(case, mode=ExecutionMode.LIVE_COMPUTE)

    if independent_sidecar is not None:
        report["independent_input_change_test"] = independent_sidecar
        side_path = args.output_dir / "INDEPENDENT_INPUT_CHANGE_TEST.json"
        args.output_dir.mkdir(parents=True, exist_ok=True)
        side_path.write_text(json.dumps(independent_sidecar, indent=2) + "\n", encoding="utf-8")

    write_v07_delivery_artifacts(report, args.output_dir)
    fixture_out = Path("tests/fixtures/V07_VERSION_DELIVERY_ACCEPTANCE.json")
    if report.get("execution_mode") == ExecutionMode.LIVE_COMPUTE.value:
        fixture_out.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")

    summary = {
        **report.get("delivery_summary", {}),
        "execution_mode": report.get("execution_mode"),
        "FIXTURE_REPLAY_USED_FOR_LIVE_ACCEPTANCE": report.get(
            "FIXTURE_REPLAY_USED_FOR_LIVE_ACCEPTANCE", False
        ),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
