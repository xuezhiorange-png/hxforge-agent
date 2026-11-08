from __future__ import annotations

import json
from pathlib import Path

from prototypes.v08_thermal_rating.fatal_cell_identity import select_fatal_cell_from_evidence

CANDIDATE_ID = "e1baa795-9cf5-5718-8fa8-0688d2102c5c"
EVIDENCE = Path(f"/opt/cursor/artifacts/v08_03_blocked_cell_evidence_{CANDIDATE_ID}.json")


def test_fatal_cell_identity_selects_mesh2_support2_outer28() -> None:
  if not EVIDENCE.is_file():
      return
  payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
  fatal = select_fatal_cell_from_evidence(payload)
  assert fatal["mesh_subdivisions"] == 2
  assert fatal["outer_iteration"] == 28
  assert fatal["physical_support_id"].endswith(":support:2")
  assert fatal["termination_failure_code"] == "BLOCKED_CELL_VALID_EVALUATION_BRACKET_UNRESOLVED"
