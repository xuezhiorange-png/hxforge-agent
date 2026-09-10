"""v0.6 multi-family applicability tests for TASK160-TASK162.

These tests exercise the real producer boundaries.  They intentionally keep
the historical fixed-tubesheet fixture and its identities as a regression
anchor while proving that the new family profile is an applicability bridge,
not a second thermal-performance implementation.
"""

from __future__ import annotations

from copy import deepcopy

import pytest

from hexagent.exchangers.shell_tube.flow_arrangement_performance_method_authority import (
    Task161ValidationStatus,
)
from hexagent.exchangers.shell_tube.flow_arrangement_performance_method_authority import (
    validate_request as validate_task161,
)
from hexagent.exchangers.shell_tube.thermal_performance_closure import (
    Task162ValidationStatus,
)
from hexagent.exchangers.shell_tube.thermal_performance_closure import (
    validate_request as validate_task162,
)
from hexagent.exchangers.shell_tube.thermal_stream_state import (
    TASK160_V06_ENVELOPE_AUTHORITY_ID,
    TASK160_V06_ENVELOPE_EVIDENCE_REF,
    TASK160_V06_ENVELOPE_SOURCE_ID,
    TASK160_V06_ENVELOPE_SOURCE_VERSION,
)
from hexagent.exchangers.shell_tube.thermal_stream_state import (
    validate_request as validate_task160,
)

from .test_task161_flow_arrangement_performance_method_authority import task161_raw
from .test_task162_thermal_performance_closure import _binding, _case, _task038
from .thermal_stream_state.test_ingress_models import make_r607_raw

LEGACY_TASK160_HASH = "e9889477b0dc0cb0291b6bda528d0b5afd2e129d0f6232e4691d9b7c6ed46be7"
LEGACY_TASK160_ID = "2b3810e1-f264-5f36-b6fd-422611a76407"
LEGACY_TASK161_HASH = "8b05fc63a73408097c886fca665612ebf93cc3f62edb47de82d43212373e33c0"
LEGACY_TASK161_ID = "959430a6-317d-5f1e-8d61-aac46c49c3c1"
LEGACY_TASK162_HASH = "5921c106e50f57e481bdf30f4edef98615540a8f2f5c5a45ea8052fe8ddce0e0"
LEGACY_TASK162_ID = "c7b062cd-4c06-5f4d-add0-e5255ea3289b"


def _raw_task160(family: str, *, v06: bool = True) -> dict[str, object]:
    raw = deepcopy(make_r607_raw())
    envelope = raw["envelope_authority"]
    assert isinstance(envelope, dict)
    envelope["construction_family"] = family
    if v06:
        envelope.update(
            {
                "authority_source_identity": TASK160_V06_ENVELOPE_SOURCE_ID,
                "authority_source_version": TASK160_V06_ENVELOPE_SOURCE_VERSION,
                "authority_identity": TASK160_V06_ENVELOPE_AUTHORITY_ID,
                "evidence_refs": [
                    "envelope-authority-0001",
                    TASK160_V06_ENVELOPE_EVIDENCE_REF,
                ],
            }
        )
    return raw


def _task160(family: str, *, v06: bool = True) -> object:
    result = validate_task160(_raw_task160(family, v06=v06))
    assert result.valid is not None
    return result.valid


def _task161(task160: object) -> object:
    result = validate_task161(task161_raw(task160))
    assert result.status is Task161ValidationStatus.VALID
    assert result.valid is not None
    return result.valid


def _task162(task160: object, task161: object) -> object:
    task038 = _task038(task160)
    result = validate_task162(
        {
            "schema_version": "task162.schema.v1",
            "task162_version": "task162.v1",
            "source_definition_id": "TASK162-SOURCE-DEFINITION-R1-ISSUE-229",
            "task160_result": task160,
            "task161_result": task161,
            "task038_result": task038,
            "cross_producer_binding_authority": _binding(task160, task161, task038),
            "case_authority": _case(),
            "request_metadata": [],
        }
    )
    assert result.status is Task162ValidationStatus.VALID
    assert result.valid is not None
    return result.valid


def test_legacy_fixed_tubesheet_identities_remain_exact() -> None:
    task160 = validate_task160(make_r607_raw()).valid
    assert task160 is not None
    assert task160.result_hash == LEGACY_TASK160_HASH
    assert str(task160.result_id) == LEGACY_TASK160_ID

    task161 = _task161(task160)
    assert task161.result_hash == LEGACY_TASK161_HASH
    assert str(task161.result_id) == LEGACY_TASK161_ID

    # The existing helper uses the legacy TASK160 fixture for the fixed path.
    task162 = _task162(task160, task161)
    assert task162.result_hash == LEGACY_TASK162_HASH
    assert str(task162.result_id) == LEGACY_TASK162_ID


@pytest.mark.parametrize("family", ["U_TUBE", "FLOATING_HEAD"])
def test_non_fixed_families_require_and_accept_the_v06_task160_envelope(
    family: str,
) -> None:
    accepted = validate_task160(_raw_task160(family))
    assert accepted.valid is not None
    assert accepted.valid.envelope_authority.construction_family.value == family
    assert accepted.valid.applicability.checks[5].check_id.value == "A06_V06"

    legacy_metadata = validate_task160(_raw_task160(family, v06=False))
    assert legacy_metadata.valid is None
    assert any(item.code == "B022" for item in legacy_metadata.blockers)


def test_v06_task160_rejects_non_one_pass_without_expanding_scope() -> None:
    raw = _raw_task160("U_TUBE")
    envelope = raw["envelope_authority"]
    assert isinstance(envelope, dict)
    envelope["tube_pass_count"] = 2
    result = validate_task160(raw)
    assert result.valid is None
    assert any(item.code == "B022" for item in result.blockers)


@pytest.mark.parametrize("family", ["U_TUBE", "FLOATING_HEAD"])
def test_task161_uses_explicit_v06_profile_for_non_fixed_family(family: str) -> None:
    task160 = _task160(family)
    task161 = _task161(task160)
    assert task161.flow_arrangement_catalog.catalog_id.endswith("_V06_SHELL_TUBE")
    assert task161.flow_arrangement_catalog.hxforge_construction_intersection == (
        "FIXED_TUBESHEET|U_TUBE|FLOATING_HEAD"
    )
    assert task161.performance_method_catalog.method_revision == "V1_V06_SHELL_TUBE"
    assert task161.performance_method_catalog.authority_hash != "0" * 64
    assert TASK160_V06_ENVELOPE_EVIDENCE_REF in task161.flow_arrangement_catalog.evidence_refs


@pytest.mark.parametrize("family", ["U_TUBE", "FLOATING_HEAD"])
def test_task162_closes_v06_family_without_new_thermal_physics(family: str) -> None:
    task160 = _task160(family)
    task161 = _task161(task160)
    task162 = _task162(task160, task161)
    assert task162.case_binding_evidence.physical_configuration_authority == family
    assert task162.applicability.checks[0] == ("TASK160_V06_ENVELOPE_ACCEPTED", "PASS")
    assert task162.applicability.checks[1] == ("TASK161_V06_METHOD_PROFILE_ACCEPTED", "PASS")


def test_v06_profile_preserves_the_same_table7_thermal_relation() -> None:
    fixed160 = validate_task160(make_r607_raw()).valid
    assert fixed160 is not None
    fixed161 = _task161(fixed160)
    fixed162 = _task162(fixed160, fixed161)

    v06_160 = _task160("U_TUBE")
    v06_161 = _task161(v06_160)
    v06_162 = _task162(v06_160, v06_161)

    assert fixed162.p_source == v06_162.p_source
    assert fixed162.epsilon == v06_162.epsilon
    assert fixed162.q_method == v06_162.q_method
    assert fixed162.selected_method_identity.relation_id == (
        v06_162.selected_method_identity.relation_id
    )
    assert fixed162.selected_method_identity.method_authority_id == (
        v06_162.selected_method_identity.method_authority_id
    )
    assert fixed162.result_hash != v06_162.result_hash


def test_v06_task160_identity_changes_by_family_but_legacy_does_not() -> None:
    u_tube = _task160("U_TUBE")
    floating = _task160("FLOATING_HEAD")
    assert u_tube.result_hash != floating.result_hash
    assert u_tube.result_id != floating.result_id


def test_v06_envelope_authority_identity_is_source_bound() -> None:
    raw = _raw_task160("U_TUBE")
    envelope = raw["envelope_authority"]
    assert isinstance(envelope, dict)
    envelope["authority_source_identity"] = "unrelated-source"
    result = validate_task160(raw)
    assert result.valid is None
    assert any(item.code == "B022" for item in result.blockers)
