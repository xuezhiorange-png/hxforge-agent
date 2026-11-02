#!/usr/bin/env python3
"""Generate R27F full-path pressure budget report for eight rated candidates."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/opt/cursor/artifacts/r27f-pressure-budget"),
    )
    parser.add_argument(
        "--fixture-copy",
        type=Path,
        default=Path("tests/fixtures/R27F_FULL_PATH_PRESSURE_BUDGET.json"),
    )
    args = parser.parse_args()
    from prototypes.v07_general_rating_sizing_mvp.r27f_full_path_pressure_budget import (
        run_r27f_full_path_pressure_budget,
        write_r27f_reports,
    )
    from tests.prototypes.r26g_r26ga_shared_setup import shared_r26e_engineering_case

    case = shared_r26e_engineering_case()
    report = run_r27f_full_path_pressure_budget(case)
    write_r27f_reports(report, args.output_dir)
    args.fixture_copy.parent.mkdir(parents=True, exist_ok=True)
    args.fixture_copy.write_text(
        (__import__("json").dumps(report, indent=2, default=str) + "\n"),
        encoding="utf-8",
    )
    summary = {"output_dir": str(args.output_dir), "fixture": str(args.fixture_copy)}
    print(__import__("json").dumps(summary, indent=2))


if __name__ == "__main__":
    main()
