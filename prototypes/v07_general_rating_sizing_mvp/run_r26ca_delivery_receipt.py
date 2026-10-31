"""Emit R26C-A engineering delivery receipt JSON to stdout or --output path."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import (
    load_general_engineering_case_json,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_engineering_rating_live_bridge import (
    build_experimental_engineering_rating_live_package,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fixture",
        default="tests/fixtures/r23_variable_water_temperature_n1_case.json",
    )
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    case_path = Path(args.fixture)
    case = load_general_engineering_case_json(case_path.read_text(encoding="utf-8"))
    package = build_experimental_engineering_rating_live_package(
        case, run_mesh_ladder=True, run_hydraulic_sensitivity=True
    )
    receipt = package["engineering_delivery_receipt"]
    payload = json.dumps(receipt, indent=2, default=str)
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
    else:
        print(payload)


if __name__ == "__main__":
    main()
