#!/usr/bin/env python3
"""Run V08-02 geometry candidate generation for a general user design case JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from prototypes.v08_geometry_candidate_generation.pipeline import (
    generate_geometry_from_user_case_path,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="V08-02 geometry candidate generation")
    parser.add_argument("user_case_json", type=Path)
    parser.add_argument(
        "--discrete-space",
        type=Path,
        default=None,
        help="Optional override path to V08 discrete space authority JSON",
    )
    args = parser.parse_args()
    result = generate_geometry_from_user_case_path(
        args.user_case_json,
        discrete_space_path=args.discrete_space,
    )
    json.dump(result.as_dict(), sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0 if result.status == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
