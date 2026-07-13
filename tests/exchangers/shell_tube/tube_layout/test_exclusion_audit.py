from __future__ import annotations

from copy import deepcopy

from hexagent.exchangers.shell_tube.tube_layout import validate_request
from tests.exchangers.shell_tube.tube_layout._builders import make_request


def test_multi_zone_overlap_counts_once_globally_and_once_per_zone() -> None:
    payload = deepcopy(make_request())
    payload["exclusion_zones"] = [
        {
            "zone_id": "b",
            "zone_type": "CIRCLE",
            "center_x_m": "0",
            "center_y_m": "0",
            "clearance_m": "0",
            "reason_code": "B",
            "evidence_refs": ["b-ref"],
            "width_m": None,
            "height_m": None,
            "radius_m": "0.001",
        },
        {
            "zone_id": "a",
            "zone_type": "CIRCLE",
            "center_x_m": "0",
            "center_y_m": "0",
            "clearance_m": "0",
            "reason_code": "A",
            "evidence_refs": ["a-ref"],
            "width_m": None,
            "height_m": None,
            "radius_m": "0.001",
        },
    ]
    result = validate_request(payload, software_version="0.1.0", git_commit="abc")
    assert result.layout is not None
    assert result.layout.exclusion_rejection_count == 1
    assert [item.zone_id for item in result.layout.exclusion_audit] == ["a", "b"]
    assert [item.rejected_position_count for item in result.layout.exclusion_audit] == [
        1,
        1,
    ]
