"""Exact provenance and final identity stage coverage."""

from hexagent.exchangers.shell_tube.shell_side_pressure_drop import validate_request
from hexagent.exchangers.shell_tube.shell_side_pressure_drop import validation as validation_module
from hexagent.exchangers.shell_tube.shell_side_pressure_drop.canonical import (
    PROVENANCE_HASH_FIELDS,
    CanonicalizationError,
)
from tests.exchangers.shell_tube.shell_side_pressure_drop.test_task034_success_contract import (
    make_valid_raw_request,
)


def test_b044_sspd_provenance_canonicalization_failure_token_is_frozen(monkeypatch):
    assert "provenance_hash" not in PROVENANCE_HASH_FIELDS

    def fail(_prehash):
        raise CanonicalizationError("provenance projection rejected")

    monkeypatch.setattr(validation_module, "finalize_provenance", fail)
    result = validate_request(make_valid_raw_request())
    assert "SSPD_PROVENANCE_CANONICALIZATION_FAILURE" in {item.code for item in result.blockers}


def test_b045_sspd_result_id_finalization(monkeypatch):
    def fail(_result_hash):
        raise ValueError("uuid5 failure")

    monkeypatch.setattr(validation_module, "result_id", fail)
    result = validate_request(make_valid_raw_request())
    assert "SSPD_RESULT_ID_FINALIZATION_FAILURE" in {item.code for item in result.blockers}
