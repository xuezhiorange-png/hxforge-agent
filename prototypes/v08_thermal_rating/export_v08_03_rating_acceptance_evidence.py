"""Run V08-03 rating pipeline (limited) and write machine-readable acceptance evidence."""

# ruff: noqa: E402

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(_REPO), str(_REPO / "src")]

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_general_user_case.loader import load_general_user_design_case_json
from prototypes.v08_general_user_case.pipeline import validate_and_build_solver_handoff
from prototypes.v08_thermal_rating.export_v08_03_blocked_cell_evidence import DEFAULT_FIXTURE
from prototypes.v08_thermal_rating.pipeline import run_v08_thermal_rating


def main() -> int:
    out = Path("/opt/cursor/artifacts/v08_03_rating_acceptance_evidence.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    case = load_general_user_design_case_json(DEFAULT_FIXTURE.read_text(encoding="utf-8"))
    pipeline = validate_and_build_solver_handoff(case, provider=CoolPropProvider())
    result = run_v08_thermal_rating(
        pipeline.normalized,
        pipeline.handoff,
        provider=CoolPropProvider(),
        max_valid_geometry=12,
        min_accepted_distinct_geometries=2,
    )
    payload = {
        "TASK_ID": "V08_03_NUMERICAL_CLOSURE_AND_RATING_ACCEPTANCE",
        "engineering_acceptance": result.engineering_acceptance,
        "distinct_fully_converged": result.distinct_fully_converged_rating_count,
        "distinct_attempted": result.distinct_structural_geometries_attempted,
        "model_blockers": list(result.model_blockers),
        "candidates": [asdict(row) for row in result.candidates_rated],
    }
    out.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
