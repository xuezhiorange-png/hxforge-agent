"""TASK-016 pipe-side hairpin reference blocker tests.

These tests close the PR #67 merge-preflight P1 finding by proving that
hairpin pipe-side references receive the same blocker treatment as tube-side
references under the frozen TASK-016 catalog contract.
"""

from __future__ import annotations

from typing import Any

import pytest

from hexagent.geometry_catalogs import (
    APPROVAL_STATE_APPROVED,
    GEOMETRY_TYPE_HAIRPIN,
    GEOMETRY_TYPE_PIPE,
    GEOMETRY_TYPE_TUBE,
    GeometryCatalogBlockerError,
    load_geometry_catalog,
)
from hexagent.geometry_catalogs.blockers import (
    BLOCKER_GEOMETRY_REFERENCE_MISSING,
    BLOCKER_GEOMETRY_REFERENCE_UNAPPROVED,
)

pytestmark = pytest.mark.pure


def _approved_source() -> dict[str, Any]:
    return {
        "source_id": "src-1",
        "source_type": "internal",
        "source_revision": "rev-1",
        "source_location": "catalogs/v1.yaml",
        "evidence_ref": "ev-1",
        "approved_by": "reviewer-A",
        "approved_at": "2026-07-01T00:00:00Z",
    }


def _tube_record() -> dict[str, Any]:
    return {
        "geometry_id": "tube/std/od0.019/id0.015/r1",
        "geometry_type": GEOMETRY_TYPE_TUBE,
        "approval_state": APPROVAL_STATE_APPROVED,
        "nominal_label": "3/4 in BWG",
        "outer_diameter_m": 0.019,
        "inner_diameter_m": 0.015,
        "wall_thickness_m": 0.002,
        "cross_section_area_m2": 1.9635e-4,
        "flow_area_m2": 1.7671e-4,
        "hydraulic_diameter_m": 0.0168,
        "source_binding": _approved_source(),
        "revision": "r1",
        "tags": [],
    }


def _pipe_record(
    *,
    geometry_id: str = "pipe/nps1/sch40/r1",
    approval_state: str = APPROVAL_STATE_APPROVED,
) -> dict[str, Any]:
    return {
        "geometry_id": geometry_id,
        "geometry_type": GEOMETRY_TYPE_PIPE,
        "approval_state": approval_state,
        "nominal_label": "NPS 1 SCH 40",
        "nominal_pipe_size_label": "NPS 1",
        "schedule_label": "SCH 40",
        "outer_diameter_m": 0.0334,
        "inner_diameter_m": 0.0266,
        "wall_thickness_m": 0.0034,
        "flow_area_m2": 5.5597e-4,
        "hydraulic_diameter_m": 0.0266,
        "source_binding": _approved_source(),
        "revision": "r1",
        "tags": [],
    }


def _hairpin_record(*, pipe_id: str) -> dict[str, Any]:
    return {
        "geometry_id": "hairpin/utube1/r1",
        "geometry_type": GEOMETRY_TYPE_HAIRPIN,
        "approval_state": APPROVAL_STATE_APPROVED,
        "nominal_label": "utube1",
        "hairpin_id": "utube1",
        "tube_geometry_id": "tube/std/od0.019/id0.015/r1",
        "pipe_geometry_id": pipe_id,
        "number_of_tubes": 1,
        "effective_length_m": 2.0,
        "bend_radius_m": 0.05,
        "centerline_spacing_m": 0.05,
        "flow_path_descriptor": "u-tube",
        "source_binding": _approved_source(),
        "revision": "r1",
        "tags": [],
    }


def _catalog_payload(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "catalog_id": "approved-geometry-catalog",
        "catalog_version": "0.1.0",
        "authority": "internal-review",
        "source_revision": "rev-1",
        "records": records,
    }


def test_hairpin_missing_pipe_reference_returns_blocker() -> None:
    missing_pipe_id = "pipe/does/not/exist/r1"
    payload = _catalog_payload(
        records=[
            _tube_record(),
            _hairpin_record(pipe_id=missing_pipe_id),
        ]
    )

    with pytest.raises(GeometryCatalogBlockerError) as excinfo:
        load_geometry_catalog(payload)

    assert excinfo.value.error_code == BLOCKER_GEOMETRY_REFERENCE_MISSING
    assert excinfo.value.context["reference_field"] == "pipe_geometry_id"
    assert excinfo.value.context["missing_id"] == missing_pipe_id


def test_hairpin_reference_to_non_approved_pipe_returns_blocker() -> None:
    pending_pipe_id = "pipe/pending/nps1/sch40/r1"
    payload = _catalog_payload(
        records=[
            _tube_record(),
            _pipe_record(geometry_id=pending_pipe_id, approval_state="pending"),
            _hairpin_record(pipe_id=pending_pipe_id),
        ]
    )

    with pytest.raises(GeometryCatalogBlockerError) as excinfo:
        load_geometry_catalog(payload)

    assert excinfo.value.error_code == BLOCKER_GEOMETRY_REFERENCE_UNAPPROVED
    assert excinfo.value.context["reference_field"] == "pipe_geometry_id"
    assert excinfo.value.context["referenced_state"] == "pending"
