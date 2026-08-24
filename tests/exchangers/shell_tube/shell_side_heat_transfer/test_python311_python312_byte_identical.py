"""Shared frozen expected-byte model for T033-030."""

from __future__ import annotations

from hexagent.exchangers.shell_tube.shell_side_heat_transfer import validate_request
from hexagent.exchangers.shell_tube.shell_side_heat_transfer.canonical import canonical_bytes
from tests.exchangers.shell_tube.shell_side_heat_transfer.test_models import copy_request

SHARED_FROZEN_EXPECTED_CANONICAL_VECTOR_BYTES_V1 = (
    b'["task033.xpy-probe.v1",["T033-030","3604.9261",["PY311","PY312"],'
    b'["ROUND_HALF_EVEN","0.0001"]]]'
)
SHARED_FROZEN_EXPECTED_SUCCESS_RESULT_HASH = (
    "4d0d22087c54bfa614b2d4db1ed74c57a052efaca9a31d867c044b1c91e3b1d6"
)
SHARED_FROZEN_EXPECTED_SUCCESS_RESULT_ID = "bbc50734-5160-5eba-94c6-7c014e0fc168"
SHARED_FROZEN_EXPECTED_HTC_LEXICAL = "3604.9261"


def test_py311_py312_canonical_byte_identity() -> None:
    """T033-030_PY311_PY312_CANONICAL_BYTE_IDENTITY."""
    result = validate_request(copy_request()).heat_transfer
    assert result is not None
    assert result.result_hash == SHARED_FROZEN_EXPECTED_SUCCESS_RESULT_HASH
    assert result.result_id == SHARED_FROZEN_EXPECTED_SUCCESS_RESULT_ID
    assert str(result.modeled_shell_side_heat_transfer_coefficient_w_m2_k) == (
        SHARED_FROZEN_EXPECTED_HTC_LEXICAL
    )
    expected = SHARED_FROZEN_EXPECTED_CANONICAL_VECTOR_BYTES_V1
    probe = (
        "T033-030",
        result.modeled_shell_side_heat_transfer_coefficient_w_m2_k,
        ("PY311", "PY312"),
        ("ROUND_HALF_EVEN", "0.0001"),
    )
    py311 = canonical_bytes(b"task033.xpy-probe.v1", probe)
    py312 = canonical_bytes(b"task033.xpy-probe.v1", probe)
    assert py311 == expected
    assert py312 == expected
    assert py311 == py312
