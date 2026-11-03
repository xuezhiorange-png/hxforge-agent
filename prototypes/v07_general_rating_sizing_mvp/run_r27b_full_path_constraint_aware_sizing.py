"""R27B: CLI entry for full-path constraint-aware calculation-first sizing."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import (
    load_general_engineering_case_json,
)
from prototypes.v07_general_rating_sizing_mvp.full_path_constraint_aware_sizing import (
    run_full_path_constraint_aware_sizing,
    write_full_path_constraint_aware_sizing_reports,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run R27B full-path constraint-aware automatic sizing from design JSON."
    )
    parser.add_argument(
        "--fixture",
        default="tests/fixtures/r26e_multi_candidate_engineering_sizing_case.json",
        help="General engineering case JSON.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory for R27B_FULL_PATH_CONSTRAINT_AWARE_SIZING.json and .md.",
    )
    parser.add_argument("--max-candidates", type=int, default=None)
    parser.add_argument(
        "--loss-scenario",
        default="mid_band",
        choices=["mid_band", "low_loss_sensitivity", "high_loss_sensitivity"],
    )
    args = parser.parse_args()
    case = load_general_engineering_case_json(Path(args.fixture).read_text(encoding="utf-8"))
    report = run_full_path_constraint_aware_sizing(
        case,
        max_candidates=args.max_candidates,
        loss_scenario_key=args.loss_scenario,
    )
    json_path, md_path = write_full_path_constraint_aware_sizing_reports(
        report, Path(args.output_dir)
    )
    summary = {
        "TASK_ID": report["TASK_ID"],
        "found_feasible_design": report["found_feasible_design"],
        "recommended_candidate_id": report["recommendation"]["recommended_candidate_id"],
        "report_json_path": str(json_path),
        "report_md_path": str(md_path),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
