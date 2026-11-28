"""Isolated subprocess worker for legacy low-mesh numeric runs under a wall budget.

Reads a JSON job from stdin, runs ``_run_mesh_numeric_with_profile_impl`` in a
fresh interpreter, and writes a JSON result to stdout. Used only when
``resource_budget_wall_s`` is set on ``run_mesh_numeric_with_profile``.
"""

from __future__ import annotations

import json
import os
import sys
import time
from decimal import Decimal
from typing import Any

_LEGACY_MESH_WORKER_MARKER = "HXFORGE_LEGACY_MESH_BUDGET_WORKER"


def _parse_decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(value)


def execute_legacy_mesh_job(job: dict[str, Any]) -> dict[str, Any]:
    from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import (
        load_general_engineering_case,
    )
    from prototypes.v07_general_rating_sizing_mvp.positive_duty_cell import (
        _run_mesh_numeric_with_profile_impl,
        build_native_cell_context,
    )

    os.environ[_LEGACY_MESH_WORKER_MARKER] = "1"
    inject_sleep_s = job.get("_test_inject_sleep_s")
    if inject_sleep_s is not None:
        time.sleep(float(inject_sleep_s))

    case_data = job.get("case")
    if case_data is None:
        raise ValueError("legacy mesh budget worker requires a serialized engineering case")
    case = load_general_engineering_case(case_data)
    native = build_native_cell_context(case, candidate_id=job.get("candidate_id"))
    mesh, profile, obs = _run_mesh_numeric_with_profile_impl(
        native,
        subdivisions=int(job["subdivisions"]),
        enable_ephemeral_tp_cache=bool(job.get("enable_ephemeral_tp_cache", False)),
        case=case,
        enable_live_thermal_boundary=bool(job.get("enable_live_thermal_boundary", False)),
        tube_property_evaluation_pressure_pa=_parse_decimal(
            job.get("tube_property_evaluation_pressure_pa")
        ),
        shell_property_evaluation_pressure_pa=_parse_decimal(
            job.get("shell_property_evaluation_pressure_pa")
        ),
    )
    return {
        "status": "ok",
        "mesh": mesh,
        "profile": profile,
        "observables_present": obs is not None,
    }


def main() -> None:
    try:
        job = json.load(sys.stdin)
        payload = execute_legacy_mesh_job(job)
        json.dump(payload, sys.stdout)
    except BaseException as exc:
        json.dump(
            {"status": "error", "error_type": type(exc).__name__, "error": str(exc)},
            sys.stdout,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
