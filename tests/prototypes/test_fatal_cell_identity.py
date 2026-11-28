from __future__ import annotations

import json
from pathlib import Path

import pytest

from prototypes.v08_thermal_rating.fatal_cell_identity import select_fatal_cell_from_evidence

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE = REPO_ROOT / "tests/fixtures/v08_03/e1baa795_fatal_cell_identity_minimal.json"


def test_fatal_cell_identity_fixture_required_in_ci() -> None:
    assert FIXTURE.is_file(), "fatal cell minimal fixture missing from repo"
    wrapper = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert wrapper["fixture_schema"] == "V08_03_FATAL_CELL_IDENTITY_MINIMAL_V1"
    fatal = wrapper["fatal_cell"]
    assert fatal["candidate_id"] == wrapper["source_candidate_id"]
    assert fatal["termination_failure_code"] == wrapper["termination_failure_code"]
    assert fatal["mesh_subdivisions"] == wrapper["failed_mesh_subdivisions"]
    assert fatal["physical_support_id"].endswith(":support:2")
    assert fatal["mesh_subdivisions"] == wrapper["failed_mesh_subdivisions"]
    assert fatal["outer_iteration"] >= 1


def test_fatal_cell_identity_selection_matches_fixture_shape() -> None:
    """If full blocked evidence is present locally, selection must match fixture fields."""
    cid = json.loads(FIXTURE.read_text(encoding="utf-8"))["source_candidate_id"]
    evidence = Path(f"/opt/cursor/artifacts/v08_03_blocked_cell_evidence_{cid}.json")
    if not evidence.is_file():
        pytest.skip("full blocked-cell evidence not available in this environment")
    payload = json.loads(evidence.read_text(encoding="utf-8"))
    fatal = select_fatal_cell_from_evidence(payload)
    assert fatal["candidate_id"] == json.loads(FIXTURE.read_text())["source_candidate_id"]
