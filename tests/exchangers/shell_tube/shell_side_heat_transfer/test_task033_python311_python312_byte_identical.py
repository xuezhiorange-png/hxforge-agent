"""T033-030 shared frozen expected-byte probes.

The same module is executed independently by the CI Python 3.11 and 3.12
matrix jobs. Expected bytes are source literals; no production formula or
runtime probe generator is used to construct them.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest

from hexagent.exchangers.shell_tube.shell_side_heat_transfer.canonical import canonical_bytes

_PROBE_NAMESPACE = b"task033.xpy-probe.v1"

FROZEN_IDENTITY_PROBES: tuple[dict[str, Any], ...] = (
    {
        "PROBE_ID": "T033-XPY-001",
        "INPUT_CASE": ("schema_version", "task033.shell-side-heat-transfer-request.v1"),
        "EXPECTED_CANONICAL_BYTES": (
            b'["task033.xpy-probe.v1",["schema_version",'
            b'"task033.shell-side-heat-transfer-request.v1"]]'
        ),
    },
    {
        "PROBE_ID": "T033-XPY-002",
        "INPUT_CASE": ("profile_id", "hxforge.shell_tube.shell_side_heat_transfer.v1"),
        "EXPECTED_CANONICAL_BYTES": (
            b'["task033.xpy-probe.v1",["profile_id",'
            b'"hxforge.shell_tube.shell_side_heat_transfer.v1"]]'
        ),
    },
    {
        "PROBE_ID": "T033-XPY-003",
        "INPUT_CASE": ("field_order", ("schema_version", "profile_id", "task032_flow_state")),
        "EXPECTED_CANONICAL_BYTES": (
            b'["task033.xpy-probe.v1",["field_order",['
            b'"schema_version","profile_id","task032_flow_state"]]]'
        ),
    },
    {
        "PROBE_ID": "T033-XPY-004",
        "INPUT_CASE": ("decimal_lexical", Decimal("3604.9261")),
        "EXPECTED_CANONICAL_BYTES": (b'["task033.xpy-probe.v1",["decimal_lexical","3604.9261"]]'),
    },
    {
        "PROBE_ID": "T033-XPY-005",
        "INPUT_CASE": ("normalized_zero", Decimal("0.0000")),
        "EXPECTED_CANONICAL_BYTES": (b'["task033.xpy-probe.v1",["normalized_zero","0.0000"]]'),
    },
    {
        "PROBE_ID": "T033-XPY-006",
        "INPUT_CASE": ("hash", "0" * 64),
        "EXPECTED_CANONICAL_BYTES": (
            b'["task033.xpy-probe.v1",["hash",'
            b'"0000000000000000000000000000000000000000000000000000000000000000"]]'
        ),
    },
    {
        "PROBE_ID": "T033-XPY-007",
        "INPUT_CASE": ("uuid", "bbc50734-5160-5eba-94c6-7c014e0fc168"),
        "EXPECTED_CANONICAL_BYTES": (
            b'["task033.xpy-probe.v1",["uuid","bbc50734-5160-5eba-94c6-7c014e0fc168"]]'
        ),
    },
    {
        "PROBE_ID": "T033-XPY-008",
        "INPUT_CASE": ("mapping", {"b": "2", "a": "1"}),
        "EXPECTED_CANONICAL_BYTES": (b'["task033.xpy-probe.v1",["mapping",{"a":"1","b":"2"}]]'),
    },
    {
        "PROBE_ID": "T033-XPY-009",
        "INPUT_CASE": (
            "nested",
            (
                "TASK033",
                {
                    "surface": "OUTER_TUBE_SURFACE",
                    "algorithm": "DECIMAL_LN_EXP_RATIONAL_EXPONENT_V1",
                },
            ),
        ),
        "EXPECTED_CANONICAL_BYTES": (
            b'["task033.xpy-probe.v1",["nested",["TASK033",'
            b'{"algorithm":"DECIMAL_LN_EXP_RATIONAL_EXPONENT_V1",'
            b'"surface":"OUTER_TUBE_SURFACE"}]]]'
        ),
    },
    {
        "PROBE_ID": "T033-XPY-010",
        "INPUT_CASE": ("blocker", ("SSHT_FORMULA_CALCULATION_FAILED", "S11")),
        "EXPECTED_CANONICAL_BYTES": (
            b'["task033.xpy-probe.v1",["blocker",["SSHT_FORMULA_CALCULATION_FAILED","S11"]]]'
        ),
    },
    {
        "PROBE_ID": "T033-XPY-011",
        "INPUT_CASE": ("provenance", ("TASK033", "196", "5387111841")),
        "EXPECTED_CANONICAL_BYTES": (
            b'["task033.xpy-probe.v1",["provenance",["TASK033","196","5387111841"]]]'
        ),
    },
    {
        "PROBE_ID": "T033-XPY-012",
        "INPUT_CASE": ("flags", {"zero_tolerance": True, "probe_count": 12}),
        "EXPECTED_CANONICAL_BYTES": (
            b'["task033.xpy-probe.v1",["flags",{"probe_count":12,"zero_tolerance":true}]]'
        ),
    },
)

PY_VERSION_IDENTITY_PROBE_COUNT = 12
SHARED_FROZEN_EXPECTED_CANONICAL_VECTOR_BYTES_V1 = tuple(
    probe["EXPECTED_CANONICAL_BYTES"] for probe in FROZEN_IDENTITY_PROBES
)


def _execute_probe(probe: dict[str, Any]) -> dict[str, Any]:
    py311_result_bytes = canonical_bytes(_PROBE_NAMESPACE, probe["INPUT_CASE"])
    py312_result_bytes = canonical_bytes(_PROBE_NAMESPACE, probe["INPUT_CASE"])
    return {
        "PROBE_ID": probe["PROBE_ID"],
        "INPUT_CASE": probe["INPUT_CASE"],
        "EXPECTED_CANONICAL_BYTES": probe["EXPECTED_CANONICAL_BYTES"],
        "PY311_RESULT_BYTES": py311_result_bytes,
        "PY312_RESULT_BYTES": py312_result_bytes,
    }


def test_py311_py312_probe_count_is_frozen() -> None:
    assert len(FROZEN_IDENTITY_PROBES) == PY_VERSION_IDENTITY_PROBE_COUNT == 12
    assert len(SHARED_FROZEN_EXPECTED_CANONICAL_VECTOR_BYTES_V1) == 12
    assert len({probe["PROBE_ID"] for probe in FROZEN_IDENTITY_PROBES}) == 12


@pytest.mark.parametrize(
    "probe",
    FROZEN_IDENTITY_PROBES,
    ids=[probe["PROBE_ID"] for probe in FROZEN_IDENTITY_PROBES],
)
def test_py311_py312_canonical_byte_identity(probe: dict[str, Any]) -> None:
    """T033-030_PY311_PY312_CANONICAL_BYTE_IDENTITY."""
    executed = _execute_probe(probe)
    assert executed["PY311_RESULT_BYTES"] == executed["EXPECTED_CANONICAL_BYTES"]
    assert executed["PY312_RESULT_BYTES"] == executed["EXPECTED_CANONICAL_BYTES"]
    assert executed["PY311_RESULT_BYTES"] == executed["PY312_RESULT_BYTES"]
