#!/usr/bin/env python3
"""Materialize R27D seven-candidate baseline fixture and R27E recovery artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from prototypes.v07_general_rating_sizing_mvp.r27e_reference_regression import capture_reference_metrics
from prototypes.v07_general_rating_sizing_mvp.r27e_targeted_recovery import (
    run_r27e_targeted_recovery,
    write_r27e_recovery_report,
)
from tests.prototypes.r26g_r26ga_shared_setup import shared_r26e_engineering_case


def main() -> None:
    case = shared_r26e_engineering_case()
    baseline = capture_reference_metrics(case)
    fixture = Path("tests/fixtures/r27e_r27d_seven_reference_baseline.json")
    fixture.parent.mkdir(parents=True, exist_ok=True)
    fixture.write_text(json.dumps(baseline, indent=2), encoding="utf-8")
    report = run_r27e_targeted_recovery(case)
    write_r27e_recovery_report(report, Path("/opt/cursor/artifacts/r27e-recovery"))
    print("baseline_candidates", baseline["reference_candidate_count"])


if __name__ == "__main__":
    main()
