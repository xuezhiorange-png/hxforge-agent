from __future__ import annotations

from hexagent.exchangers.shell_tube.baffle_geometry.validation import to_canonical_primitive
from hexagent.exchangers.shell_tube.shell_side_hydraulic_geometry import (
    validate_request as validate_task031_request,
)
from hexagent.exchangers.shell_tube.shell_side_hydraulic_geometry.authority import (
    layout_hash_payload,
    verify_task021_layout,
    verify_task024_result,
)
from hexagent.exchangers.shell_tube.shell_side_hydraulic_geometry.schema import parse_request
from hexagent.exchangers.shell_tube.tube_layout import canonical as task021_canonical
from hexagent.exchangers.shell_tube.tube_layout import validate_request as validate_task021_request
from hexagent.exchangers.shell_tube.tube_layout.canonical import (
    FrozenJsonObject,
    internal_frozen_to_primitive,
)
from tests.exchangers.shell_tube.shell_side_hydraulic_geometry.test_validation import (
    _resync_task024_geometry_identity,
    base_fixture_v1,
)
from tests.exchangers.shell_tube.tube_layout._builders import make_request as make_task021_request


def test_task021_layout_identity_replay_passes_for_base_fixture() -> None:
    request = parse_request(base_fixture_v1())
    verify_task021_layout(request.tube_layout)
    expected = task021_canonical.sha256_hex(layout_hash_payload(request.tube_layout))
    assert expected == request.tube_layout.layout_hash


def test_task024_geometry_identity_replay_passes_for_base_fixture() -> None:
    request = parse_request(base_fixture_v1())
    verify_task024_result(request.baffle_geometry_result)


def test_actual_task021_public_layout_with_frozen_warning_details_passes_task031() -> None:
    task021_result = validate_task021_request(
        make_task021_request(), software_version="regression", git_commit="base"
    )
    assert task021_result.status.value == "VALID"
    assert task021_result.layout is not None
    actual_layout = task021_result.layout

    assert actual_layout.warnings
    assert all(isinstance(item.details, FrozenJsonObject) for item in actual_layout.warnings)
    layout_payload = to_canonical_primitive(actual_layout)
    assert [item["details"] for item in layout_payload["warnings"]] == [
        internal_frozen_to_primitive(item.details) for item in actual_layout.warnings
    ]

    task031_payload = base_fixture_v1()
    task031_payload["tube_layout"] = layout_payload
    geometry = task031_payload["baffle_geometry_result"]["geometry"]
    geometry["task020_configuration_id"] = actual_layout.task020_configuration_id
    geometry["task020_configuration_hash"] = actual_layout.task020_configuration_hash
    geometry["task021_layout_id"] = actual_layout.layout_id
    geometry["task021_layout_hash"] = actual_layout.layout_hash
    geometry["tube_outer_diameter_m"] = actual_layout.tube_geometry.outer_diameter_m
    _resync_task024_geometry_identity(task031_payload)

    task031_result = validate_task031_request(task031_payload)
    assert task031_result.status.value == "VALID"
    assert task031_result.geometry is not None

    parsed_request = parse_request(task031_payload)
    assert parsed_request.tube_layout.layout_hash == actual_layout.layout_hash
    assert (
        task021_canonical.sha256_hex(layout_hash_payload(parsed_request.tube_layout))
        == actual_layout.layout_hash
    )
