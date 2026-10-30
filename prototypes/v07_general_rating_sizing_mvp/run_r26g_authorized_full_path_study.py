"""R26G: write authorized full-path hydraulic study JSON report."""

# ruff: noqa: E501

from __future__ import annotations

import argparse
import json
from pathlib import Path

from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import (
    load_general_engineering_case_json,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_engineering_authorized_full_path_study import (
    load_hydraulic_path_inputs_from_json_files,
    run_r26g_authorized_full_path_hydraulic_study,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fixture",
        default="tests/fixtures/r26e_multi_candidate_engineering_sizing_case.json",
    )
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--use-demonstration-path-inputs",
        action="store_true",
        help="Bind R26G DEMONSTRATION path inputs for software verification only.",
    )
    parser.add_argument(
        "--path-input-json",
        action="append",
        default=[],
        help="Owner-supplied EngineeringHydraulicPathInputV1 JSON (repeat per candidate).",
    )
    args = parser.parse_args()
    if args.use_demonstration_path_inputs and args.path_input_json:
        raise SystemExit(
            "Provide either --use-demonstration-path-inputs or --path-input-json, not both."
        )
    case = load_general_engineering_case_json(Path(args.fixture).read_text(encoding="utf-8"))
    path_inputs = None
    if args.path_input_json:
        path_inputs = load_hydraulic_path_inputs_from_json_files(args.path_input_json)
    report = run_r26g_authorized_full_path_hydraulic_study(
        case,
        use_demonstration_path_inputs=args.use_demonstration_path_inputs,
        hydraulic_path_inputs=path_inputs,
    )
    Path(args.output).write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
