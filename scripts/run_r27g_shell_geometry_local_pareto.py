#!/usr/bin/env python3
"""Generate R27G local shell geometry Pareto report."""

from __future__ import annotations

import argparse
import json
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
        default=Path("/opt/cursor/artifacts/r27g-local-pareto"),
    )
    parser.add_argument(
        "--fixture-copy",
        type=Path,
        default=Path("tests/fixtures/R27G_SHELL_GEOMETRY_LOCAL_PARETO.json"),
    )
    parser.add_argument(
        "--skip-full-mesh",
        action="store_true",
        help="Phase A only (no mesh rating); for fast structural tests.",
    )
    args = parser.parse_args()

    from prototypes.v07_general_rating_sizing_mvp.r27g_shell_geometry_local_pareto import (
        run_r27g_shell_geometry_local_pareto,
        write_r27g_reports,
    )
    from tests.prototypes.r26g_r26ga_shared_setup import shared_r26e_engineering_case

    case = shared_r26e_engineering_case()
    report = run_r27g_shell_geometry_local_pareto(
        case,
        run_full_mesh_hydraulic=not args.skip_full_mesh,
    )
    write_r27g_reports(report, args.output_dir)
    args.fixture_copy.parent.mkdir(parents=True, exist_ok=True)
    args.fixture_copy.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    summary = {"fixture": str(args.fixture_copy), "verdict": report["engineering_verdict"]}
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
