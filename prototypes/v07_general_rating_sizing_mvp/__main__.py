"""CLI: uv run python -m prototypes.v07_general_rating_sizing_mvp"""

# ruff: noqa: E501

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from prototypes.v07_general_rating_sizing_mvp.engineering_input import GeneralEngineeringCaseV1
from prototypes.v07_general_rating_sizing_mvp.workflow import run_general_engineering_workflow


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="HXForge general rating + sizing MVP (experimental)"
    )
    parser.add_argument("--input", required=True, type=Path, help="General engineering case JSON")
    parser.add_argument("--output", required=True, type=Path, help="Output artifact directory")
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="Run Task168 enumeration only (skip Task173 full rating)",
    )
    args = parser.parse_args(argv)
    case = GeneralEngineeringCaseV1.model_validate_json(args.input.read_text(encoding="utf-8"))
    outcome = run_general_engineering_workflow(
        case,
        args.output,
        run_full_rating=not args.preflight_only,
    )
    (args.output / "WORKFLOW_OUTCOME.json").write_text(
        json.dumps(outcome.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(outcome.to_dict(), indent=2))
    return (
        0
        if outcome.status
        in {
            "PREFLIGHT_COMPLETE",
            "PARTIAL_RATING_ACCEPTED",
            "SIZING_EVALUATED",
            "PARTIAL_RATING_BLOCKED",
        }
        else 1
    )


if __name__ == "__main__":
    sys.exit(main())
