"""R26D: multi-candidate experimental engineering sizing."""

# ruff: noqa: E501

from __future__ import annotations

import argparse
import json
from pathlib import Path

from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import (
    load_general_engineering_case_json,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_multi_candidate_engineering_sizing import (
    run_experimental_multi_candidate_engineering_sizing,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fixture",
        default="tests/fixtures/r26d_multi_candidate_engineering_sizing_case.json",
    )
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-candidates", type=int, default=None)
    parser.add_argument("--n1-only", action="store_true")
    args = parser.parse_args()
    case = load_general_engineering_case_json(Path(args.fixture).read_text(encoding="utf-8"))
    result = run_experimental_multi_candidate_engineering_sizing(
        case,
        max_candidates=args.max_candidates,
        run_full_mesh_hydraulic=not args.n1_only,
    )
    Path(args.output).write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
