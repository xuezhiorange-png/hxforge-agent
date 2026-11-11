#!/usr/bin/env python3
"""V08-03 330 kW primary axial closeout (physical closure vs production C-ULP)."""

# ruff: noqa: E402, E501

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(_REPO), str(_REPO / "src")]

from prototypes.v08_thermal_rating.axial_rating_engine_v1 import (
    closeout_to_jsonable,
    run_primary_330kw_closeout,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="V08-03 330 kW axial rating closeout")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("/opt/cursor/artifacts/v08_03_330kw_axial_rating_closeout.json"),
    )
    parser.add_argument("--max-candidates", type=int, default=2)
    parser.add_argument(
        "--skip-production",
        action="store_true",
        help="Only run isolated physics trials (faster; omits full validate_candidate_rating).",
    )
    args = parser.parse_args()
    closeout = run_primary_330kw_closeout(
        max_candidates=args.max_candidates,
        skip_production_rating=args.skip_production,
    )
    payload = closeout_to_jsonable(closeout)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"aggregate_delivery": payload["aggregate_delivery"], "out": str(args.out)}))


if __name__ == "__main__":
    main()
