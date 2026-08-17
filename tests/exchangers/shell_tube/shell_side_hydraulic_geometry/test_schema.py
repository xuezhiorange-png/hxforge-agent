from __future__ import annotations

import pytest

from hexagent.exchangers.shell_tube.shell_side_hydraulic_geometry.models import (
    REQUEST_SCHEMA_VERSION,
)
from hexagent.exchangers.shell_tube.shell_side_hydraulic_geometry.schema import (
    SchemaFailure,
    parse_request,
)
from tests.exchangers.shell_tube.shell_side_hydraulic_geometry.test_validation import (
    base_fixture_v1,
)


def test_parse_request_accepts_base_fixture() -> None:
    request = parse_request(base_fixture_v1())
    assert request.schema_version == REQUEST_SCHEMA_VERSION
    assert request.tube_layout.layout_hash == (
        "97d1200527c15fe8fe9b3e778f1054cea32bf4d575ff96250eb2ceeb6666fb9f"
    )


def test_parse_request_rejects_non_dict() -> None:
    with pytest.raises(SchemaFailure) as exc_info:
        parse_request([])
    assert exc_info.value.stage == 1


def test_parse_request_rejects_unsupported_schema_version() -> None:
    payload = base_fixture_v1()
    payload["schema_version"] = "unsupported"
    with pytest.raises(SchemaFailure) as exc_info:
        parse_request(payload)
    assert exc_info.value.stage == 1
