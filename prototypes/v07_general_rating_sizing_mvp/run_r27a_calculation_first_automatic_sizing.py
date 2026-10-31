"""R27A: CLI entry for calculation-first automatic sizing."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from prototypes.v07_general_rating_sizing_mvp.calculation_first_automatic_sizing import (
    run_calculation_first_automatic_sizing,
    write_calculation_first_sizing_reports,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import (
    load_general_engineering_case_json,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run calculation-first automatic shell-and-tube sizing from design JSON."
    )
    parser.add_argument(
        "--fixture",
        default="tests/fixtures/r26e_multi_candidate_engineering_sizing_case.json",
        help="General engineering case JSON (process conditions + search constraints).",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory for R27A_CALCULATION_FIRST_SIZING.json and .md reports.",
    )
    parser.add_argument("--max-candidates", type=int, default=None)
    parser.add_argument(
        "--n1-only",
        action="store_true",
        help="Skip full mesh/hydraulic ladder (screening-only, faster).",
    )
    parser.add_argument(
        "--skip-authorized-full-path",
        action="store_true",
        help="Skip R26G authorized full-path hydraulic pass per rated candidate.",
    )
    args = parser.parse_args()
    case = load_general_engineering_case_json(Path(args.fixture).read_text(encoding="utf-8"))
    report = run_calculation_first_automatic_sizing(
        case,
        max_candidates=args.max_candidates,
        run_full_mesh_hydraulic=not args.n1_only,
        run_authorized_full_path_hydraulic=not args.skip_authorized_full_path,
    )
    json_path, md_path = write_calculation_first_sizing_reports(report, Path(args.output_dir))
    summary = {
        "TASK_ID": report["TASK_ID"],
        "workflow_status": report["workflow_status"],
        "recommended_candidate_id": report["recommendation"]["recommended_candidate_id"],
        "report_json_path": str(json_path),
        "report_md_path": str(md_path),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
