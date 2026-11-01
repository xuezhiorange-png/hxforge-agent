"""R27C: CLI for nozzle pressure-budget co-optimization sizing."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import (
    load_general_engineering_case_json,
)
from prototypes.v07_general_rating_sizing_mvp.nozzle_cooptimization_sizing import (
    run_nozzle_pressure_budget_cooptimization,
    write_nozzle_cooptimization_reports,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run R27C nozzle pressure-budget co-optimization.")
    parser.add_argument(
        "--fixture",
        default="tests/fixtures/r26e_multi_candidate_engineering_sizing_case.json",
    )
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--max-candidates", type=int, default=None)
    args = parser.parse_args()
    case = load_general_engineering_case_json(Path(args.fixture).read_text(encoding="utf-8"))
    report = run_nozzle_pressure_budget_cooptimization(
        case,
        max_candidates=args.max_candidates,
    )
    json_path, md_path = write_nozzle_cooptimization_reports(report, Path(args.output_dir))
    print(
        json.dumps(
            {
                "TASK_ID": report["TASK_ID"],
                "found_feasible_design": report["found_feasible_design"],
                "recommended_candidate_id": report["recommendation"]["recommended_candidate_id"],
                "report_json_path": str(json_path),
                "report_md_path": str(md_path),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
