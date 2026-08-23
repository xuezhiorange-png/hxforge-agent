"""Canonical projection, blocker, warning, and result identity tests."""

from hexagent.exchangers.shell_tube.shell_side_flow_state import canonical, validate_request
from hexagent.exchangers.shell_tube.shell_side_flow_state.blocker_registry import (
    make_blocker,
    sort_blockers,
)
from hexagent.exchangers.shell_tube.shell_side_flow_state.models import (
    BlockerCode,
    ValidationStatus,
    WarningCode,
)
from hexagent.exchangers.shell_tube.shell_side_flow_state.warning_registry import (
    eligible_warnings,
    make_warning,
    sort_warnings,
)
from hexagent.exchangers.shell_tube.tube_layout.canonical import canonical_json

from . import copy_request


def test_t032_can_001_request_canonical_bytes_and_hash() -> None:
    raw = copy_request()
    request = __import__(
        "hexagent.exchangers.shell_tube.shell_side_flow_state.schema",
        fromlist=["parse_request"],
    ).parse_request(raw)
    projection = canonical.request_canonical_projection(request)
    assert canonical_json(projection).encode("utf-8")
    assert canonical.request_hash(request) == canonical.sha256_hex(
        [canonical.REQUEST_HASH_NAMESPACE, canonical.primitive(projection)]
    )
    assert request.evidence_refs == ("request-a", "request-z")


def test_t032_can_002_success_result_hash_self_exclusion_and_uuid() -> None:
    result = validate_request(copy_request())
    assert result.status is ValidationStatus.VALID
    assert result.flow_state is not None
    flow_state = result.flow_state
    assert canonical.success_result_hash(flow_state) == flow_state.result_hash
    assert canonical.result_id(flow_state.result_hash) == flow_state.result_id
    assert flow_state.result_hash not in canonical.success_result_canonical_projection(flow_state)
    assert flow_state.result_id not in canonical.success_result_canonical_projection(flow_state)


def test_t032_can_003_typed_blocked_stage_gated_identity_slots() -> None:
    raw = copy_request()
    raw["task031_result"]["geometry"]["geometry_hash"] = "0" * 64
    result = validate_request(raw)
    assert result.blocked_result is not None
    blocked = result.blocked_result
    assert blocked.failure_stage == "S02"
    assert blocked.task031_geometry_id is None
    assert blocked.task031_geometry_hash is None
    assert blocked.property_snapshot_hash is None
    assert blocked.mass_flow_authority_hash is None
    assert blocked.request_hash is not None
    assert blocked.result_hash
    assert blocked.result_id


def test_t032_can_004_raw_boundary_blocked_projection_and_hash() -> None:
    result = validate_request(None)
    assert result.raw_boundary_blocked_result is not None
    blocked = result.raw_boundary_blocked_result
    assert blocked.raw_request_projection.projection_kind == "NONE"
    expected = canonical.raw_boundary_blocked_result_hash(
        schema_version=blocked.schema_version,
        profile_id=blocked.profile_id,
        implementation_software_version=blocked.implementation_software_version,
        raw_request_projection=blocked.raw_request_projection,
        blockers=blocked.blockers,
        warnings=blocked.warnings,
        deferred_capabilities=blocked.deferred_capabilities,
    )
    assert blocked.blocked_result_hash == expected


def test_t032_msg_001_blocker_entry_canonicalization_and_sort() -> None:
    later = make_blocker(
        BlockerCode.SSFS_SAME_CASE_BINDING_MISMATCH,
        stage="S05",
        field_path="b",
        payload={"z": "last", "a": "first"},
        evidence_refs=("z-ref", "a-ref", "a-ref"),
    )
    earlier = make_blocker(
        BlockerCode.SSFS_PROFILE_ID_UNSUPPORTED,
        stage="S01",
        field_path="profile_id",
    )
    assert later.payload == (("a", "first"), ("z", "last"))
    assert later.evidence_refs == ("a-ref", "z-ref")
    assert sort_blockers((later, earlier)) == (earlier, later)
    primitive = canonical.message_to_primitive(later)
    assert primitive["payload"] == [["a", "first"], ["z", "last"]]


def test_t032_msg_002_warning_entry_canonicalization_and_eligibility() -> None:
    warning = make_warning(WarningCode.SSFS_FLOW_REGIME_CLASSIFICATION_DEFERRED)
    assert warning.prerequisite_stage == "S06"
    assert warning.evidence_refs == ()
    assert sort_warnings((warning,)) == (warning,)
    assert eligible_warnings(completed_stage=5) == ()
    assert len(eligible_warnings(completed_stage=6)) == 6
    assert len(eligible_warnings(completed_stage=7)) == 7
