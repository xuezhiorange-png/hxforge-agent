from __future__ import annotations

from hexagent.exchangers.shell_tube.shell_side_hydraulic_geometry.authority import (
    layout_hash_payload,
    verify_task021_layout,
    verify_task024_result,
)
from hexagent.exchangers.shell_tube.shell_side_hydraulic_geometry.schema import parse_request
from hexagent.exchangers.shell_tube.tube_layout import canonical as task021_canonical
from tests.exchangers.shell_tube.shell_side_hydraulic_geometry.test_validation import (
    base_fixture_v1,
)


def test_task021_layout_identity_replay_passes_for_base_fixture() -> None:
    request = parse_request(base_fixture_v1())
    verify_task021_layout(request.tube_layout)
    expected = task021_canonical.sha256_hex(layout_hash_payload(request.tube_layout))
    assert expected == request.tube_layout.layout_hash


def test_task024_geometry_identity_replay_passes_for_base_fixture() -> None:
    request = parse_request(base_fixture_v1())
    verify_task024_result(request.baffle_geometry_result)
