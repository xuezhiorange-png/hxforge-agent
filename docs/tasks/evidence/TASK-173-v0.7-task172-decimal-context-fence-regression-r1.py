#!/usr/bin/env python3
"""Exercise the diagnostic Decimal-context fence with a no-solver stub."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_DIR = ROOT / "docs/tasks/evidence"
RUNNER_PATH = EVIDENCE_DIR / "TASK-173-v0.7-task172-decimal-context-adjudication-r1.py"
CONTROL_PATH = EVIDENCE_DIR / (
    "TASK-173-v0.7-task172-decimal-context-adjudication-r1-calls/control.json"
)


def main() -> int:
    control = json.loads(CONTROL_PATH.read_text(encoding="utf-8"))
    spec = importlib.util.spec_from_file_location("task172_decimal_context_fence_test", RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load the diagnostic runner context fence")
    runner = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = runner
    spec.loader.exec_module(runner)
    result = runner._preflight_context_fence(control["r2_baseline_context"]["decimal_context"])
    if (
        result["pass"] is not True
        or result["outer_context_precision_during_test"] != 100
        or result["validator_context_precision"] != 28
    ):
        raise RuntimeError("diagnostic context-fence regression failed")
    print("OUTER_DECIMAL_CONTEXT_PRECISION=100")
    print("NATIVE_VALIDATOR_CONTEXT_PRECISION=28")
    print("TASK172_CONTEXT_LEAK_REGRESSION=PASS")
    print("NATIVE_TASK172_VALIDATIONS=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
