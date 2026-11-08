"""Write repo-local minimal fatal-cell fixture from blocked-cell evidence export."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

from prototypes.v08_thermal_rating.fatal_cell_identity import select_fatal_cell_from_evidence

FIXTURE = _REPO_ROOT / "tests/fixtures/v08_03/e1baa795_fatal_cell_identity_minimal.json"


def write_minimal_from_evidence(payload: dict) -> dict:
    fatal = select_fatal_cell_from_evidence(payload)
    minimal = {
        "fixture_schema": "V08_03_FATAL_CELL_IDENTITY_MINIMAL_V1",
        "source_candidate_id": payload.get("candidate_id"),
        "candidate_hash": payload.get("candidate_hash"),
        "candidate_rating_request_hash": payload.get("candidate_rating_request_hash"),
        "geometry_projection_hash": payload.get("geometry_projection_hash"),
        "termination_failure_code": payload.get("task173_failure_code"),
        "failed_mesh_subdivisions": payload.get("task173_failed_mesh_subdivisions"),
        "fatal_cell": fatal,
    }
    FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE.write_text(json.dumps(minimal, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return minimal


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: export_fatal_cell_minimal_fixture.py <blocked_cell_evidence.json>", file=sys.stderr)
        return 2
    payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    minimal = write_minimal_from_evidence(payload)
    print(FIXTURE)
    print(
        json.dumps(
            {
                "mesh": minimal["fatal_cell"]["mesh_subdivisions"],
                "outer": minimal["fatal_cell"]["outer_iteration"],
                "support": minimal["fatal_cell"]["physical_support_id"][-10:],
            }
        )
    )
    return 0


if __name__ == "__main__":
    os.environ.setdefault("PYTHONHASHSEED", "0")
    raise SystemExit(main())
