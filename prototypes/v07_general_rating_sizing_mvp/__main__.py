"""CLI: uv run python -m prototypes.v07_general_rating_sizing_mvp"""

# ruff: noqa: E501

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from prototypes.v07_general_rating_sizing_mvp.cli_exit import experimental_live_rating_exit_code
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import (
    load_general_engineering_case_json,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_input import GeneralEngineeringCaseV1
from prototypes.v07_general_rating_sizing_mvp.experimental_live_workflow import (
    run_experimental_live_rating_workflow,
)
from prototypes.v07_general_rating_sizing_mvp.target_directed_live_sizing_workflow import (
    run_target_directed_live_sizing_workflow,
)
from prototypes.v07_general_rating_sizing_mvp.workflow import run_general_engineering_workflow


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="HXForge general rating + sizing MVP (experimental)"
    )
    parser.add_argument("--input", required=True, type=Path, help="General engineering case JSON")
    parser.add_argument("--output", required=True, type=Path, help="Output artifact directory")
    parser.add_argument(
        "--mode",
        choices=(
            "legacy-v1-workflow",
            "experimental-live-rating",
            "experimental-target-directed-sizing-r12",
        ),
        default="legacy-v1-workflow",
        help="legacy-v1-workflow: v1 sizing path; experimental-live-rating: live n=1 mesh CLI",
    )
    parser.add_argument(
        "--mesh",
        type=int,
        default=1,
        help="Mesh subdivisions for experimental-live-rating (only n=1 is supported)",
    )
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="Run Task168 enumeration only (skip Task173 full rating)",
    )
    parser.add_argument(
        "--objective",
        choices=(
            "PARETO_ONLY",
            "MIN_NOMINAL_TUBE_AREA",
            "MAX_DUTY",
            "MIN_SHELL_DP_PREVIEW",
        ),
        default=None,
        help="Experimental sizing objective (default PARETO_ONLY; non-production)",
    )
    args = parser.parse_args(argv)
    if args.mode == "experimental-target-directed-sizing-r12":
        if args.mesh != 1:
            print(json.dumps({"error": "only --mesh 1 is supported in R12"}), file=sys.stderr)
            return 2
        case = load_general_engineering_case_json(args.input.read_text(encoding="utf-8"))
        outcome = run_target_directed_live_sizing_workflow(case, args.output, mesh_level=args.mesh)
        (args.output / "WORKFLOW_OUTCOME.json").write_text(
            json.dumps(outcome.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(json.dumps(outcome.to_dict(), indent=2))
        return experimental_live_rating_exit_code(outcome)

    if args.mode == "experimental-live-rating":
        if args.mesh != 1:
            print(json.dumps({"error": "only --mesh 1 is supported in R9"}), file=sys.stderr)
            return 2
        case = load_general_engineering_case_json(args.input.read_text(encoding="utf-8"))
        outcome = run_experimental_live_rating_workflow(
            case,
            args.output,
            mesh_level=args.mesh,
            enable_ephemeral_tp_cache=False,
            cli_objective=args.objective,
        )
        (args.output / "WORKFLOW_OUTCOME.json").write_text(
            json.dumps(outcome.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(json.dumps(outcome.to_dict(), indent=2))
        return experimental_live_rating_exit_code(outcome)

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
