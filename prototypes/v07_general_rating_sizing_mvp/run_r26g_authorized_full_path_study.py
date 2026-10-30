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
    args = parser.parse_args()
    case = load_general_engineering_case_json(Path(args.fixture).read_text(encoding="utf-8"))
    report = run_r26g_authorized_full_path_hydraulic_study(
        case, use_demonstration_path_inputs=args.use_demonstration_path_inputs
    )
    Path(args.output).write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
