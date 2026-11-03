"""R26F: write hydraulic path study JSON report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import (
    load_general_engineering_case_json,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_engineering_hydraulic_path_study import (
    run_experimental_engineering_hydraulic_path_study,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fixture",
        default="tests/fixtures/r26e_multi_candidate_engineering_sizing_case.json",
    )
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    case = load_general_engineering_case_json(Path(args.fixture).read_text(encoding="utf-8"))
    report = run_experimental_engineering_hydraulic_path_study(case)
    Path(args.output).write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
