#!/usr/bin/env python3
"""Capture R27E current results, compare with R27D exact-head baseline, and recover five."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from prototypes.v07_general_rating_sizing_mvp.r27e_reference_regression import (
    capture_reference_metrics,
    compare_reference_metrics,
    load_reference_fixture,
)
from prototypes.v07_general_rating_sizing_mvp.r27e_targeted_recovery import (
    run_r27e_targeted_recovery,
    write_r27e_recovery_report,
)
from tests.prototypes.r26g_r26ga_shared_setup import shared_r26e_engineering_case


def main() -> None:
    case = shared_r26e_engineering_case()
    output_dir = Path("/opt/cursor/artifacts/r27e-recovery")
    output_dir.mkdir(parents=True, exist_ok=True)

    current = capture_reference_metrics(case)
    current_path = output_dir / "R27E_SEVEN_REFERENCE_CURRENT.json"
    current_path.write_text(json.dumps(current, indent=2, default=str) + "\n", encoding="utf-8")

    # NEVER create an R27D fixture by running R27E code. It must be captured from
    # #310 exact head by scripts/r27e_capture_r27d_reference.py.
    fixture = _ROOT / "tests/fixtures/r27e_r27d_seven_reference_baseline.json"
    if fixture.is_file():
        baseline = load_reference_fixture(fixture)
        deltas = compare_reference_metrics(baseline, current)
        regression_status = "PASS" if not deltas else "FAIL"
    else:
        deltas = [{"error": "r27d_exact_head_baseline_missing"}]
        regression_status = "NOT_VERIFIED"

    regression_report = {
        "TASK_ID": "V07_R27E_PHYSICAL_MODEL_ISOLATION_AND_REGRESSION_FIX",
        "status": regression_status,
        "reference_candidate_count": current["reference_candidate_count"],
        "baseline_path": str(fixture),
        "current_path": str(current_path),
        "deltas": deltas,
    }
    (output_dir / "R27E_SEVEN_REFERENCE_REGRESSION.json").write_text(
        json.dumps(regression_report, indent=2, default=str) + "\n", encoding="utf-8"
    )

    report = run_r27e_targeted_recovery(case)
    write_r27e_recovery_report(report, output_dir)
    print(json.dumps({
        "reference_candidate_count": current["reference_candidate_count"],
        "regression_status": regression_status,
        "regression_delta_count": len(deltas),
        "recovery_candidate_count": len(report["recovery_candidates"]),
    }, indent=2))
    if regression_status == "FAIL":
        raise SystemExit("R27E numerical regression against verified R27D baseline failed")


if __name__ == "__main__":
    main()
