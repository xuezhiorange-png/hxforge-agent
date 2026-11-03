"""R27D: CLI for thermal–hydraulic–geometry co-optimization sizing."""

# ruff: noqa: E501

from __future__ import annotations

import argparse
import json
from pathlib import Path

from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import (
    load_general_engineering_case_json,
)
from prototypes.v07_general_rating_sizing_mvp.thermal_hydraulic_geometry_cooptimization_sizing import (
    run_thermal_hydraulic_geometry_cooptimization,
    write_r27d_reports,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run R27D thermal–hydraulic–geometry co-optimization sizing."
    )
    parser.add_argument(
        "--fixture",
        default="tests/fixtures/r26e_multi_candidate_engineering_sizing_case.json",
    )
    parser.add_argument("--output-dir", required=True)
    parser.add_argument(
        "--max-candidates-to-rate",
        type=int,
        default=None,
        help="Override solver budget; default rates all Task174-ready distinct geometries.",
    )
    parser.add_argument(
        "--search-incomplete-budget",
        action="store_true",
        help="Use case solver_budget.max_candidates_to_rate instead of all Task174-ready.",
    )
    args = parser.parse_args()
    case = load_general_engineering_case_json(Path(args.fixture).read_text(encoding="utf-8"))
    report = run_thermal_hydraulic_geometry_cooptimization(
        case,
        rate_all_distinct_task174_ready=not args.search_incomplete_budget,
        max_candidates_to_rate_override=args.max_candidates_to_rate,
    )
    json_path, md_path = write_r27d_reports(report, Path(args.output_dir))
    print(
        json.dumps(
            {
                "TASK_ID": report["TASK_ID"],
                "found_feasible_design": report["found_feasible_design"],
                "recommended_candidate_id": report["recommendation"]["recommended_candidate_id"],
                "search_status": report["search_coverage"]["search_status"],
                "report_json_path": str(json_path),
                "report_md_path": str(md_path),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
