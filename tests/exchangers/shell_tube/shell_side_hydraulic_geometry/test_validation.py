# ruff: noqa: E501
from __future__ import annotations

import copy
import json
import uuid
from pathlib import Path
from typing import Any, cast

import pytest

from hexagent.exchangers.shell_tube.shell_side_hydraulic_geometry import validate_request
from hexagent.exchangers.shell_tube.shell_side_hydraulic_geometry.authority import (
    _task024_geometry_hash_payload,
    layout_hash_payload,
)
from hexagent.exchangers.shell_tube.shell_side_hydraulic_geometry.canonical import sha256_hex
from hexagent.exchangers.shell_tube.shell_side_hydraulic_geometry.models import ValidationStatus
from hexagent.exchangers.shell_tube.shell_side_hydraulic_geometry.schema import parse_request
from hexagent.exchangers.shell_tube.tube_layout import canonical as task021_canonical
from hexagent.exchangers.shell_tube.tube_layout.canonical import canonical_json

_TASK024_GEOMETRY_URN_PREFIX = "urn:hxforge:task024:baffle-geometry:v1:"

_DESIGN_PATH = (
    Path(__file__).resolve().parents[4]
    / "docs"
    / "tasks"
    / "TASK-031-shell-and-tube-shell-side-flow-path-hydraulic-geometry.md"
)
_VECTOR_WARNING_ORDER = (
    "SSHG_CENTRAL_CROSSFLOW_SCREENING_GEOMETRY_ONLY",
    "SSHG_FLOW_STATE_THERMAL_PRESSURE_DROP_DEFERRED",
    "SSHG_FORMULA_AUTHORITY_SCREENING_MODEL_ONLY",
    "SSHG_LEAKAGE_BYPASS_CORRECTIONS_EXCLUDED",
    "SSHG_MINIMUM_AREA_SELECTION_DEFERRED",
    "SSHG_NO_FULL_EXCHANGER_RATING_CLAIM",
    "SSHG_WINDOW_INLET_OUTLET_FLOW_AREAS_DEFERRED",
)
_VECTOR_WARNING_ORDER_STAGE_6_ONLY = tuple(
    code for code in _VECTOR_WARNING_ORDER if code != "SSHG_FORMULA_AUTHORITY_SCREENING_MODEL_ONLY"
)


def _load_design_fixture() -> dict[str, Any]:
    text = _DESIGN_PATH.read_text(encoding="utf-8")
    marker = '"schema_version": "task031.shell-side-hydraulic-geometry-request.v1"'
    idx = text.index(marker)
    start = text.rfind("```json", 0, idx)
    end = text.index("```", start + 8)
    return cast(dict[str, Any], json.loads(text[start + 7 : end]))


def base_fixture_v1() -> dict[str, Any]:
    return copy.deepcopy(_load_design_fixture())


def _mutate(payload: dict[str, Any], path: str, value: Any) -> None:
    parts = [part for part in path.strip("/").split("/") if part]
    cursor: Any = payload
    for part in parts[:-1]:
        cursor = cursor[part]
    cursor[parts[-1]] = value


def _layout_rule_snapshot_hash(rule: dict[str, Any]) -> str:
    payload = {key: value for key, value in rule.items() if key != "snapshot_hash"}
    return sha256_hex(canonical_json(payload))


def _resync_task021_layout_identity(payload: dict[str, Any]) -> None:
    rule = payload["tube_layout"]["layout_rule_authority"]
    snapshot_hash = _layout_rule_snapshot_hash(rule)
    rule["snapshot_hash"] = snapshot_hash
    payload["tube_layout"]["provenance"]["layout_rule_snapshot_hash"] = snapshot_hash
    request = parse_request(payload)
    layout_hash = sha256_hex(layout_hash_payload(request.tube_layout))
    layout_id = task021_canonical.layout_id(layout_hash)
    payload["tube_layout"]["layout_hash"] = layout_hash
    payload["tube_layout"]["layout_id"] = layout_id
    geometry = payload["baffle_geometry_result"].get("geometry")
    if geometry is not None:
        geometry["task021_layout_id"] = layout_id
        geometry["task021_layout_hash"] = layout_hash


def _resync_task024_geometry_identity(payload: dict[str, Any]) -> None:
    request = parse_request(payload)
    geometry = request.baffle_geometry_result.geometry
    if geometry is None:
        return
    geometry_hash = sha256_hex(_task024_geometry_hash_payload(geometry))
    geometry_id = str(uuid.uuid5(uuid.NAMESPACE_URL, _TASK024_GEOMETRY_URN_PREFIX + geometry_hash))
    payload["baffle_geometry_result"]["geometry"]["geometry_hash"] = geometry_hash
    payload["baffle_geometry_result"]["geometry"]["geometry_id"] = geometry_id


@pytest.mark.parametrize(
    (
        "vector_id",
        "mutations",
        "expected_status",
        "expected_blockers",
        "expected_warnings",
        "oracle",
        "resync_layout",
        "resync_geometry",
    ),
    [
        (
            "V1",
            (),
            ValidationStatus.VALID,
            (),
            _VECTOR_WARNING_ORDER,
            {"As": "0.007500000000000000000000", "De": "0.022882879761"},
            False,
            False,
        ),
        (
            "V2",
            (("/tube_layout/layout_rule_authority/pattern_family", "TRIANGULAR"),),
            ValidationStatus.VALID,
            (),
            _VECTOR_WARNING_ORDER,
            {"As": "0.007500000000000000000000", "De": "0.017271637857"},
            True,
            True,
        ),
        (
            "V3",
            (
                (
                    "/baffle_geometry_result/geometry/design_authority/spacing_sequence_m",
                    ["0.100000000000", "0.125000000000", "0.130000000000"],
                ),
                (
                    "/baffle_geometry_result/geometry/design_authority/authority_hash",
                    "a6ff07c6ebbd3853cb70f1c327b900bc04f4d781d0d79d276ab1540b2bbf768a",
                ),
            ),
            ValidationStatus.VALID,
            (),
            _VECTOR_WARNING_ORDER,
            {"As": "0.007500000000000000000000", "De": "0.022882879761"},
            False,
            True,
        ),
        (
            "V4",
            (
                ("/baffle_geometry_result/geometry/design_authority/baffle_count", 3),
                (
                    "/baffle_geometry_result/geometry/design_authority/spacing_sequence_m",
                    ["0.100000000000", "0.125000000000", "0.125000000000", "0.140000000000"],
                ),
                (
                    "/baffle_geometry_result/geometry/design_authority/authority_hash",
                    "cf6ba663d93364fefea2d44dc892eb529d33da766999661d3b5b56899e9e0bff",
                ),
            ),
            ValidationStatus.VALID,
            (),
            _VECTOR_WARNING_ORDER,
            {"As": "0.007500000000000000000000", "De": "0.022882879761"},
            False,
            True,
        ),
        (
            "V5",
            (
                ("/baffle_geometry_result/geometry/design_authority/baffle_count", 3),
                (
                    "/baffle_geometry_result/geometry/design_authority/spacing_sequence_m",
                    ["0.100000000000", "0.125000000000", "0.130000000000", "0.140000000000"],
                ),
                (
                    "/baffle_geometry_result/geometry/design_authority/authority_hash",
                    "8283c50b01611e5ebab8e86d188be4cc558e500fa24d5d8235490acb23f8d391",
                ),
                (
                    "/baffle_geometry_result/geometry/geometry_hash",
                    "d53ca543989ba9ce2bb02c89376d443518b259852fd043d54dbc5be6aad4cf72",
                ),
            ),
            ValidationStatus.BLOCKED,
            ("SSHG_TASK024_IDENTITY_MISMATCH",),
            (),
            None,
            False,
            False,
        ),
        (
            "V6",
            (
                ("/tube_layout/layout_rule_authority/pitch_m", "0.019000000000"),
                ("/tube_layout/tube_geometry/outer_diameter_m", "0.019000000000"),
            ),
            ValidationStatus.BLOCKED,
            ("SSHG_PITCH_NOT_GREATER_THAN_TUBE_OD",),
            _VECTOR_WARNING_ORDER_STAGE_6_ONLY,
            None,
            False,
            False,
        ),
        (
            "V7",
            (("/tube_layout/layout_rule_authority/pitch_m", "0.018000000000"),),
            ValidationStatus.BLOCKED,
            ("SSHG_PITCH_NOT_GREATER_THAN_TUBE_OD",),
            _VECTOR_WARNING_ORDER_STAGE_6_ONLY,
            None,
            False,
            False,
        ),
        (
            "V8",
            (("/tube_layout/layout_rule_authority/pattern_family", "ROSETTE"),),
            ValidationStatus.BLOCKED,
            ("SSHG_TASK021_LAYOUT_INVALID",),
            (),
            None,
            False,
            False,
        ),
        (
            "V9",
            (("/baffle_geometry_result/geometry/tube_outer_diameter_m", "0.020000000000"),),
            ValidationStatus.BLOCKED,
            ("SSHG_TASK024_IDENTITY_MISMATCH",),
            (),
            None,
            False,
            False,
        ),
        (
            "V10",
            (
                (
                    "/baffle_geometry_result/geometry/task021_layout_hash",
                    "97d1200527c15fe8fe9b3e778f1054cea32bf4d575ff96250eb2ceeb6666fb90",
                ),
            ),
            ValidationStatus.BLOCKED,
            ("SSHG_TASK024_IDENTITY_MISMATCH",),
            (),
            None,
            False,
            False,
        ),
        (
            "V12",
            (("/baffle_geometry_result/geometry", None),),
            ValidationStatus.BLOCKED,
            ("SSHG_TASK024_GEOMETRY_MISSING",),
            (),
            None,
            False,
            False,
        ),
        (
            "V13",
            (
                (
                    "/baffle_geometry_result/geometry/shell_inside_diameter_m",
                    "0.000000000001",
                ),
                (
                    "/baffle_geometry_result/geometry/design_authority/spacing_sequence_m",
                    ["0.000000000001", "0.000000000001", "0.000000000001"],
                ),
            ),
            ValidationStatus.BLOCKED,
            ("SSHG_PUBLIC_AREA_QUANTIZATION_COLLISION",),
            _VECTOR_WARNING_ORDER_STAGE_6_ONLY,
            None,
            False,
            True,
        ),
        (
            "V14",
            (
                (
                    "/engineering_authority/authority_hash",
                    "1cb5cf1ff9f28fb2dec074f6458473e60d0866c744fbd97501e41d68b5837980",
                ),
            ),
            ValidationStatus.BLOCKED,
            ("SSHG_ENGINEERING_AUTHORITY_IDENTITY_MISMATCH",),
            _VECTOR_WARNING_ORDER_STAGE_6_ONLY,
            None,
            False,
            False,
        ),
    ],
)
def test_engineering_vectors(
    vector_id: str,
    mutations: tuple[tuple[str, Any], ...],
    expected_status: ValidationStatus,
    expected_blockers: tuple[str, ...],
    expected_warnings: tuple[str, ...],
    oracle: dict[str, str] | None,
    resync_layout: bool,
    resync_geometry: bool,
) -> None:
    payload = base_fixture_v1()
    for path, value in mutations:
        _mutate(payload, path, value)
    if resync_layout:
        _resync_task021_layout_identity(payload)
    if resync_geometry:
        _resync_task024_geometry_identity(payload)
    result = validate_request(payload)
    assert result.status is expected_status, vector_id
    assert tuple(item.code for item in result.blockers) == expected_blockers, vector_id
    assert tuple(item.code for item in result.warnings) == expected_warnings, vector_id
    if oracle is not None:
        assert result.geometry is not None
        assert result.geometry.central_crossflow_flow_area_m2 == oracle["As"]
        assert result.geometry.shell_side_equivalent_hydraulic_diameter_m == oracle["De"]


def test_v11_task024_blocked_result_replay() -> None:
    payload = base_fixture_v1()
    blocked_fragment = {
        "status": "BLOCKED",
        "geometry": None,
        "warnings": [],
        "blockers": [
            {
                "code": "BFG_DECIMAL_LEXICAL_INVALID",
                "field_path": ".design_authority.baffle_thickness_m",
                "message_key": "decimal_lexical_invalid",
                "evidence_refs": [],
                "details": [],
            }
        ],
        "deferred_capabilities": payload["baffle_geometry_result"]["deferred_capabilities"],
        "blocked_result_hash": "5af8473ec8b1f17477c55b91ee668d3e5ae76dbd67d565f7b0586560db1365e4",
    }
    payload["baffle_geometry_result"] = blocked_fragment
    result = validate_request(payload)
    assert result.status is ValidationStatus.BLOCKED
    assert [item.code for item in result.blockers] == ["SSHG_TASK024_RESULT_HAS_BLOCKERS"]


def test_public_api_exports_only_validate_request() -> None:
    import hexagent.exchangers.shell_tube.shell_side_hydraulic_geometry as package

    assert package.__all__ == ["validate_request"]
