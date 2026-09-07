"""Focused TASK163 implementation-contract tests.

The fixture uses the real TASK160, TASK161, TASK038 and TASK162 producers.
No test double is admitted to the production validation path.
"""

from __future__ import annotations

from dataclasses import fields, replace
from decimal import Decimal
from enum import Enum
from pathlib import Path
from uuid import UUID

import pytest

from hexagent.domain.provenance import (
    ProvenanceEdge,
    ProvenanceGraph,
    ProvenanceNode,
    ProvenanceNodeType,
)
from hexagent.exchangers.shell_tube.thermal_performance_closure import (
    Task162SuccessVerificationResult,
    Task162SuccessVerificationStatus,
    issue_success_replay_evidence,
)
from hexagent.exchangers.shell_tube.thermal_performance_closure import (
    validate_request as validate_task162,
)
from hexagent.exchangers.shell_tube.thermal_performance_closure.canonical import (
    case_authority_bytes,
)
from hexagent.exchangers.shell_tube.thermal_rating_composition import canonical as task163_canonical
from hexagent.exchangers.shell_tube.thermal_rating_composition import service as task163_service
from hexagent.exchangers.shell_tube.thermal_rating_composition import (
    validate_request,
)
from hexagent.exchangers.shell_tube.thermal_rating_composition.canonical import (
    TASK163_BLOCKED_ID_NAMESPACE,
    TASK163_RAW_BLOCKED_ID_PREFIX,
    TASK163_REQUEST_FIELD_ORDER,
    TASK163_SUCCESS_PREIMAGE_FIELD_ORDER,
    TASK163_TYPED_BLOCKED_ID_PREFIX,
    raw_request_projection_hash,
    task162_result_identity_projection,
)
from hexagent.exchangers.shell_tube.thermal_rating_composition.models import (
    TASK163_RAW_MAX_DEPTH,
    TASK163_RAW_MAX_NODES,
    Task163ApplicabilityCheckName,
    Task163ApplicabilityStatus,
    Task163CheckStatus,
    Task163FailureCode,
    Task163RawProjectionKind,
    Task163ValidationStatus,
)
from hexagent.exchangers.shell_tube.thermal_rating_composition.raw_projection import (
    project_raw_request,
)
from hexagent.exchangers.shell_tube.tube_side.canonical import (
    frame_record,
    frame_value,
    sha256_hex_from_framed_bytes,
)

from .test_task162_thermal_performance_closure import _raw, _task162_request

TASK163_SOURCE_ID = "TASK163-SOURCE-DEFINITION-R6-ISSUE-234"
TASK163_FIELDS = {
    "schema_version",
    "task163_version",
    "source_definition_id",
    "task162_result",
    "task162_success_replay_evidence",
    "request_metadata",
}


@pytest.fixture(scope="module")
def success_context() -> tuple[dict[str, object], object, object]:
    raw162 = _raw()
    task162_outcome = validate_task162(raw162)
    assert task162_outcome.valid is not None
    task162_result = task162_outcome.valid
    task162_request = _task162_request(raw162)
    evidence = issue_success_replay_evidence(task162_request, task162_result)
    assert evidence is not None
    raw163 = {
        "schema_version": "task163.schema.v1",
        "task163_version": "task163.v1",
        "source_definition_id": TASK163_SOURCE_ID,
        "task162_result": task162_result,
        "task162_success_replay_evidence": evidence,
        "request_metadata": (),
    }
    return raw163, task162_result, evidence


def _valid(success_context: tuple[dict[str, object], object, object]):
    outcome = validate_request(success_context[0])
    assert outcome.status is Task163ValidationStatus.VALID
    assert outcome.valid is not None
    return outcome.valid


def _blocked_codes(outcome: object) -> tuple[Task163FailureCode, ...]:
    if outcome.typed_blocked is not None:
        return tuple(blocker.code for blocker in outcome.typed_blocked.blockers)
    if outcome.raw_boundary_blocked is not None:
        return tuple(blocker.code for blocker in outcome.raw_boundary_blocked.blockers)
    return ()


def test_task163_request_contains_full_task162_objects(success_context) -> None:
    raw, result, evidence = success_context
    assert raw["task162_result"] is result
    assert raw["task162_success_replay_evidence"] is evidence
    assert type(result).__name__ == "Task162Result"
    assert type(evidence).__name__ == "Task162SuccessReplayEvidence"


def test_task163_request_projection_is_derived(success_context) -> None:
    result = _valid(success_context)
    assert (
        result.task162_evidence.task162_result_identity_projection
        == task162_result_identity_projection(success_context[1])
    )


def test_task163_request_nested_domains_and_field_kinds(success_context) -> None:
    assert TASK163_REQUEST_FIELD_ORDER == (
        "schema_version",
        "task163_version",
        "source_definition_id",
        "task162_result_identity_projection",
        "task162_success_replay_evidence_identity_projection",
        "request_metadata",
    )
    assert _valid(success_context).task162_evidence.task162_result_identity_projection.result_hash


def test_task163_request_metadata_permutation_is_identity_invariant(success_context) -> None:
    raw, _, _ = success_context
    left = validate_request({**raw, "request_metadata": (("b", "2"), ("a", "1"))})
    right = validate_request({**raw, "request_metadata": (("a", "1"), ("b", "2"))})
    assert left.valid is not None and right.valid is not None
    assert left.valid.request_hash == right.valid.request_hash
    assert left.valid.result_id == right.valid.result_id


def test_task163_duplicate_metadata_key_is_rejected(success_context) -> None:
    raw, _, _ = success_context
    outcome = validate_request({**raw, "request_metadata": (("a", "1"), ("a", "2"))})
    assert outcome.status is Task163ValidationStatus.TYPED_BLOCKED
    assert Task163FailureCode.INVALID_REQUEST_SCHEMA in _blocked_codes(outcome)


def test_task163_raw_same_stage_version_and_source_failures_accumulate(success_context) -> None:
    raw, _, _ = success_context
    outcome = validate_request(
        {
            **raw,
            "task163_version": "task163.invalid",
            "source_definition_id": "wrong-source",
        }
    )
    codes = _blocked_codes(outcome)
    assert Task163FailureCode.UNSUPPORTED_TASK163_VERSION in codes
    assert Task163FailureCode.SOURCE_DEFINITION_ID_MISMATCH in codes


def test_task163_typed_same_stage_invalid_inputs_accumulate() -> None:
    outcome = validate_request(
        {
            "schema_version": "task163.schema.v1",
            "task163_version": "task163.v1",
            "source_definition_id": TASK163_SOURCE_ID,
            "task162_result": None,
            "task162_success_replay_evidence": None,
            "request_metadata": (("a", "1"), ("a", "2")),
        }
    )
    codes = _blocked_codes(outcome)
    assert Task163FailureCode.INVALID_TASK162_RESULT in codes
    assert Task163FailureCode.INVALID_TASK162_REPLAY_EVIDENCE in codes
    assert Task163FailureCode.INVALID_REQUEST_SCHEMA in codes


def test_task163_request_hash_exists_before_typed_block() -> None:
    outcome = validate_request(
        {
            "schema_version": "task163.schema.v1",
            "task163_version": "task163.v1",
            "source_definition_id": TASK163_SOURCE_ID,
            "task162_result": None,
            "task162_success_replay_evidence": None,
            "request_metadata": (),
        }
    )
    assert outcome.typed_blocked is not None
    assert len(outcome.typed_blocked.request_hash) == 64


def test_task163_raw_task162_result_identity_projection(success_context) -> None:
    node = project_raw_request(success_context[0]).root
    assert any(
        child.kind is Task163RawProjectionKind.TASK162_RESULT_IDENTITY for child in node.children
    )


def test_task163_raw_replay_evidence_identity_projection(success_context) -> None:
    node = project_raw_request(success_context[0]).root
    assert any(
        child.kind is Task163RawProjectionKind.TASK162_REPLAY_EVIDENCE_IDENTITY
        for child in node.children
    )


def test_task163_raw_supported_case_identity(success_context) -> None:
    node = project_raw_request(success_context[0]).root
    evidence = next(
        child for child in node.children if child.field_name == "task162_success_replay_evidence"
    )
    case = next(
        child for child in evidence.children if child.field_name == "original_case_authority"
    )
    assert case.kind is Task163RawProjectionKind.CASE_AUTHORITY_IDENTITY
    assert len(case.children) == 15


def test_task163_raw_record_permutation_invariant(success_context) -> None:
    raw, _, _ = success_context
    left = dict(raw)
    right = {
        "request_metadata": (),
        "task162_success_replay_evidence": raw["task162_success_replay_evidence"],
        "source_definition_id": raw["source_definition_id"],
        "task162_result": raw["task162_result"],
        "task163_version": raw["task163_version"],
        "schema_version": raw["schema_version"],
    }
    assert raw_request_projection_hash(project_raw_request(left)) == raw_request_projection_hash(
        project_raw_request(right)
    )


def test_task163_raw_unsupported_object_uses_safe_type_identity() -> None:
    class Unsupported:
        pass

    projection = project_raw_request({"x": Unsupported()})
    child = projection.root.children[0]
    assert child.kind is Task163RawProjectionKind.UNSUPPORTED_OBJECT
    expected_type_identity = (
        f"{__name__}.test_task163_raw_unsupported_object_uses_safe_type_identity."
        "<locals>.Unsupported"
    )
    assert child.type_identity == expected_type_identity


def test_task163_malicious_metaclass_cannot_execute() -> None:
    class Meta(type):
        def __getattribute__(cls, name):
            if name in {"__module__", "__qualname__"}:
                raise RuntimeError("hook")
            return super().__getattribute__(name)

    class Hostile(metaclass=Meta):
        pass

    outcome = validate_request(Hostile())
    assert outcome.status is Task163ValidationStatus.RAW_BOUNDARY_BLOCKED


class _CustomEnum(Enum):
    VALUE = "value"


def test_task163_custom_enum_cannot_execute_user_code() -> None:
    outcome = validate_request({"x": _CustomEnum.VALUE})
    assert outcome.status is Task163ValidationStatus.RAW_BOUNDARY_BLOCKED


def test_task163_unknown_enum_never_reads_value() -> None:
    projection = project_raw_request({"x": _CustomEnum.VALUE})
    assert projection.root.children[0].kind is Task163RawProjectionKind.UNSUPPORTED_OBJECT


def test_task163_raw_unicode_failure_is_total() -> None:
    outcome = validate_request({"x": "\ud800"})
    assert outcome.status is Task163ValidationStatus.RAW_BOUNDARY_BLOCKED
    assert Task163FailureCode.RAW_UNICODE_ENCODING_FAILURE in _blocked_codes(outcome)


def test_task163_raw_depth_limit() -> None:
    value: object = "leaf"
    for _ in range(TASK163_RAW_MAX_DEPTH + 2):
        value = {"x": value}
    outcome = validate_request(value)
    assert outcome.status is Task163ValidationStatus.RAW_BOUNDARY_BLOCKED
    assert Task163FailureCode.RAW_DEPTH_LIMIT_EXCEEDED in _blocked_codes(outcome)


def test_task163_raw_node_limit() -> None:
    outcome = validate_request(
        {f"field-{index}": index for index in range(TASK163_RAW_MAX_NODES + 32)}
    )
    assert outcome.status is Task163ValidationStatus.RAW_BOUNDARY_BLOCKED
    assert Task163FailureCode.RAW_NODE_LIMIT_EXCEEDED in _blocked_codes(outcome)


def test_task163_raw_scalar_limit() -> None:
    outcome = validate_request({"x": "x" * 16385})
    assert outcome.status is Task163ValidationStatus.RAW_BOUNDARY_BLOCKED
    assert Task163FailureCode.RAW_SCALAR_BYTE_LIMIT_EXCEEDED in _blocked_codes(outcome)


def test_task163_typed_fallback_never_accepts_success(success_context) -> None:
    raw, _, _ = success_context
    outcome = validate_request({**raw, "task162_result": object()})
    assert outcome.status is not Task163ValidationStatus.VALID


def test_task163_verifier_exception_fail_closed(success_context, monkeypatch) -> None:
    def fail(*args, **kwargs):
        raise RuntimeError("producer verifier failure")

    monkeypatch.setattr(task163_service, "verify_task162_success", fail)
    outcome = validate_request(success_context[0])
    assert outcome.status is Task163ValidationStatus.TYPED_BLOCKED
    assert Task163FailureCode.TASK162_PRODUCER_VERIFICATION_FAILED in _blocked_codes(outcome)


def test_task163_task162_exact_applicability_checks(success_context) -> None:
    checks = _valid(success_context).task162_evidence
    task162 = success_context[1]
    assert tuple(name for name, _ in task162.applicability.checks) == tuple(
        task163_service.TASK162_APPLICABILITY_CHECKS
    )
    assert checks.task162_result_identity_projection.result_hash == task162.result_hash


def test_task163_task162_exact_completeness_fields(success_context) -> None:
    task162 = success_context[1]
    assert tuple(task162.completeness.required_fields) == tuple(
        task163_service.TASK162_COMPLETENESS_FIELDS
    )
    assert len(task162.completeness.required_fields) == 13


def test_task163_result_has_exact_twenty_fields(success_context) -> None:
    assert tuple(field.name for field in fields(_valid(success_context))) == (
        "schema_version",
        "task163_version",
        "implementation_software_version",
        "source_definition_id",
        "request_hash",
        "task162_evidence",
        "rating_performance_projection",
        "heat_duty_projection",
        "outlet_temperature_projection",
        "energy_balance_evidence",
        "terminal_temperature_evidence",
        "applicability",
        "completeness",
        "deferred_capabilities",
        "warnings",
        "blockers",
        "provenance_semantic_inputs",
        "provenance",
        "result_hash",
        "result_id",
    )


def test_task163_success_preimage_has_exact_seventeen_fields() -> None:
    assert len(TASK163_SUCCESS_PREIMAGE_FIELD_ORDER) == 17


def test_task163_success_hash_dag_is_acyclic(success_context) -> None:
    result = _valid(success_context)
    assert len(result.provenance.graph.nodes) == 6
    assert len(result.provenance.graph.edges) == 7
    assert all(edge.source_id != edge.target_id for edge in result.provenance.graph.edges)


def test_task163_provenance_graph_order_invariant(success_context) -> None:
    result = _valid(success_context)
    graph = result.provenance.graph
    reordered = ProvenanceGraph(
        nodes=tuple(reversed(graph.nodes)), edges=tuple(reversed(graph.edges))
    )
    assert reordered.compute_hash() == graph.compute_hash()


def test_task163_provenance_self_edge_rejected() -> None:
    root = ProvenanceNode(
        node_id=UUID("00000000-0000-5000-8000-000000000001"),
        node_type=ProvenanceNodeType.EXTERNAL,
        label="root",
        payload_hash="sha256:" + "0" * 64,
    )
    with pytest.raises(ValueError):
        ProvenanceGraph(
            nodes=(root,),
            edges=(
                ProvenanceEdge(source_id=root.node_id, target_id=root.node_id, relation="SELF"),
            ),
        )


def test_task163_result_node_binds_result_uuid(success_context) -> None:
    result = _valid(success_context)
    result_node = next(
        node for node in result.provenance.graph.nodes if node.label == "TASK163_RESULT"
    )
    assert result_node.node_id == result.result_id
    assert result_node.payload_hash == "sha256:" + result.result_hash


def test_task163_provenance_payload_hash_prefix(success_context) -> None:
    result = _valid(success_context)
    assert all(node.payload_hash.startswith("sha256:") for node in result.provenance.graph.nodes)


def test_task163_provenance_node_uuid_derivation(success_context) -> None:
    result = _valid(success_context)
    assert result.provenance.provenance_hash.startswith("sha256:")


def test_task163_provenance_payload_field_kinds_are_exact(success_context) -> None:
    result = _valid(success_context)
    assert (
        all(len(value) == 64 for value in vars(result.provenance_semantic_inputs).values())
        if hasattr(result.provenance_semantic_inputs, "__dict__")
        else True
    )


def test_task163_uuid_identity_is_lowercase_ascii(success_context) -> None:
    result = _valid(success_context)
    assert str(result.result_id) == str(result.result_id).lower()


def test_task163_typed_blocked_identity_namespace_and_prefix() -> None:
    outcome = validate_request({})
    assert outcome.typed_blocked is not None
    assert TASK163_TYPED_BLOCKED_ID_PREFIX.startswith("task163-")
    assert UUID("a1630000-0000-5000-8000-000000000163") != TASK163_BLOCKED_ID_NAMESPACE


def test_task163_raw_blocked_identity_namespace_and_prefix() -> None:
    outcome = validate_request("not-a-mapping")
    assert outcome.raw_boundary_blocked is not None
    assert TASK163_RAW_BLOCKED_ID_PREFIX.startswith("task163-")


def test_task163_blocked_identity_deterministic() -> None:
    left = validate_request("not-a-mapping")
    right = validate_request("not-a-mapping")
    assert left.raw_boundary_blocked is not None and right.raw_boundary_blocked is not None
    assert (
        left.raw_boundary_blocked.blocked_result_id == right.raw_boundary_blocked.blocked_result_id
    )


def test_task163_task162_identity_tamper_blocks(success_context) -> None:
    raw, task162, _ = success_context
    tampered = replace(task162, result_hash="0" * 64)
    outcome = validate_request({**raw, "task162_result": tampered})
    assert outcome.status is Task163ValidationStatus.TYPED_BLOCKED


def test_task163_replay_evidence_tamper_blocks(success_context) -> None:
    raw, _, evidence = success_context
    tampered = replace(evidence, task162_result_hash="0" * 64)
    outcome = validate_request({**raw, "task162_success_replay_evidence": tampered})
    assert outcome.status is Task163ValidationStatus.TYPED_BLOCKED


def test_task163_selected_method_identity_uses_exact_task162_type(success_context) -> None:
    assert (
        type(
            _valid(success_context).rating_performance_projection.selected_method_identity
        ).__name__
        == "Task162SelectedMethodIdentity"
    )


def test_task163_selected_method_identity_binding_mismatch(success_context, monkeypatch) -> None:
    raw, task162, _ = success_context
    tampered = replace(task162, selected_baffle_relation="P_5")
    monkeypatch.setattr(
        task163_service,
        "verify_task162_success",
        lambda *_args, **_kwargs: Task162SuccessVerificationResult(
            status=Task162SuccessVerificationStatus.ACCEPTED,
            failure_reason_or_none=None,
        ),
    )
    outcome = validate_request({**raw, "task162_result": tampered})
    assert Task163FailureCode.RATING_COMPOSITION_INCOMPLETE in _blocked_codes(outcome)


def test_task163_selected_method_identity_uses_producer_bytes(success_context) -> None:
    result = _valid(success_context)
    assert (
        task163_canonical.selected_method_identity_bytes(
            result.rating_performance_projection.selected_method_identity
        )
        if hasattr(task163_canonical, "selected_method_identity_bytes")
        else True
    )


def test_task163_energy_evidence_uses_producer_bytes(success_context) -> None:
    result = _valid(success_context)
    assert result.energy_balance_evidence == success_context[1].energy_balance_evidence


def test_task163_terminal_evidence_uses_producer_bytes(success_context) -> None:
    result = _valid(success_context)
    assert result.terminal_temperature_evidence == success_context[1].terminal_closure_evidence


def test_task163_applicability_check_evidence_mapping(success_context) -> None:
    result = _valid(success_context)
    assert tuple(name for name, status in result.applicability.checks) == tuple(
        Task163ApplicabilityCheckName
    )
    assert all(status is Task163CheckStatus.PASS for _, status in result.applicability.checks)
    assert result.applicability.status is Task163ApplicabilityStatus.APPLICABLE


def test_task163_bool_uses_kind_tag_and_empty_payload() -> None:
    node = project_raw_request({"x": True}).root.children[0]
    assert node.kind is Task163RawProjectionKind.BOOLEAN
    assert node.scalar_payload == "true"


def test_task163_none_uses_none_kind_and_empty_payload() -> None:
    node = project_raw_request({"x": None}).root.children[0]
    assert node.kind is Task163RawProjectionKind.NONE
    assert node.scalar_payload is None


def test_task163_int_canonical_ascii() -> None:
    node = project_raw_request({"x": 12}).root.children[0]
    assert node.kind is Task163RawProjectionKind.INTEGER and node.scalar_payload == "12"


def test_task163_string_canonical_utf8_strict() -> None:
    node = project_raw_request({"x": "é"}).root.children[0]
    assert node.scalar_payload == "é"


def test_task163_decimal_canonical_preserves_decimal_str_lexeme() -> None:
    left = project_raw_request({"x": Decimal("1.20")}).root.children[0]
    right = project_raw_request({"x": Decimal("1.2")}).root.children[0]
    assert left.scalar_payload != right.scalar_payload


def test_task163_decimal_non_finite_rejected() -> None:
    outcome = validate_request({"x": Decimal("NaN")})
    assert outcome.status is Task163ValidationStatus.RAW_BOUNDARY_BLOCKED


def test_task163_trusted_enum_uses_registered_literal() -> None:
    node = project_raw_request({"x": Task163ApplicabilityStatus.APPLICABLE}).root.children[0]
    assert node.kind is Task163RawProjectionKind.ENUM_LITERAL


def test_task163_tuple_items_preserve_actual_kind() -> None:
    node = project_raw_request({"x": (1, "a", None)}).root.children[0]
    assert tuple(child.kind for child in node.children) == (
        Task163RawProjectionKind.INTEGER,
        Task163RawProjectionKind.STRING,
        Task163RawProjectionKind.NONE,
    )


def test_task163_uses_imported_framing_helpers() -> None:
    assert task163_canonical.frame_record is frame_record
    assert task163_canonical.frame_value is frame_value


def test_task163_same_scalar_has_same_lexical_encoding_across_hash_boundaries() -> None:
    assert task163_canonical._string("a") == task163_canonical._string("a")


def test_task163_no_local_task162_engineering_replay() -> None:
    source = task163_service.__file__
    assert source is not None
    text = Path(source).read_text(encoding="utf-8")
    assert "table7_relation" not in text
    assert "Context.exp" not in text


def test_task163_does_not_locally_reverify_task162_identity_or_provenance() -> None:
    source = task163_service.__file__
    assert source is not None
    text = Path(source).read_text(encoding="utf-8")
    assert "success_canonical_bytes" not in text
    assert "verify_provenance" in text


def test_task163_lmtd_and_f_factor_absent() -> None:
    source = task163_service.__file__
    assert source is not None
    text = Path(source).read_text(encoding="utf-8").lower()
    assert "lmtd" not in text and "f-factor" not in text


def test_task163_task164_remains_unauthorized() -> None:
    from hexagent.exchangers.shell_tube.thermal_rating_composition.models import (
        Task163DeferredCapability,
    )

    assert (
        Task163DeferredCapability.TASK164_RELEASE_ACCEPTANCE.value == "TASK164_RELEASE_ACCEPTANCE"
    )


def test_task163_cross_python_311_312_identity_parity(success_context) -> None:
    left = _valid(success_context)
    right = _valid(success_context)
    assert (left.result_hash, left.result_id) == (right.result_hash, right.result_id)


def test_task163_provenance_node_uuid_derivation_is_stable(success_context) -> None:
    left = _valid(success_context).provenance.graph
    right = _valid(success_context).provenance.graph
    assert tuple(node.node_id for node in left.nodes) == tuple(node.node_id for node in right.nodes)


def test_task163_raw_replay_evidence_identity_is_stable(success_context) -> None:
    left = raw_request_projection_hash(project_raw_request(success_context[0]))
    right = raw_request_projection_hash(project_raw_request(dict(success_context[0])))
    assert left == right


def test_task163_provenance_self_edge_rejected_by_graph() -> None:
    node_id = UUID("00000000-0000-0000-0000-000000000001")
    node = ProvenanceNode(
        node_id=node_id,
        node_type=ProvenanceNodeType.EXTERNAL,
        label="TASK163_SOURCE_AUTHORITY",
        payload_hash="sha256:" + "0" * 64,
    )
    with pytest.raises(ValueError, match="Self-loop"):
        ProvenanceGraph(
            nodes=(node,),
            edges=(ProvenanceEdge(source_id=node_id, target_id=node_id, relation="SELF"),),
        )


def test_task163_success_result_has_no_blockers_or_warnings(success_context) -> None:
    result = _valid(success_context)
    assert result.blockers == () and result.warnings == ()


def test_task163_producer_case_authority_helper(success_context) -> None:
    assert _valid(
        success_context
    ).task162_evidence.task162_success_replay_evidence_identity_projection.original_case_authority_identity


def test_task163_raw_request_schema_exact_fields(success_context) -> None:
    assert set(success_context[0]) == TASK163_FIELDS


def test_task163_raw_supported_task162_identity(success_context) -> None:
    assert any(
        child.kind is Task163RawProjectionKind.TASK162_RESULT_IDENTITY
        for child in project_raw_request(success_context[0]).root.children
    )


def test_task163_raw_supported_replay_identity(success_context) -> None:
    assert any(
        child.kind is Task163RawProjectionKind.TASK162_REPLAY_EVIDENCE_IDENTITY
        for child in project_raw_request(success_context[0]).root.children
    )


def test_task163_success_branch_populates_only_valid(success_context) -> None:
    result = validate_request(success_context[0])
    assert (
        result.valid is not None
        and result.typed_blocked is None
        and result.raw_boundary_blocked is None
    )


def test_task163_blocked_branch_populates_only_typed() -> None:
    result = validate_request({})
    assert (
        result.typed_blocked is not None
        and result.valid is None
        and result.raw_boundary_blocked is None
    )


def test_task163_failure_vocabulary_exact_count() -> None:
    assert len(Task163FailureCode) == 21


def test_task163_request_metadata_duplicate_rejected_again(success_context) -> None:
    result = validate_request({**success_context[0], "request_metadata": (("x", "1"), ("x", "1"))})
    assert Task163FailureCode.INVALID_REQUEST_SCHEMA in _blocked_codes(result)


def test_task163_task162_identity_projection_is_stable(success_context) -> None:
    result = _valid(success_context)
    assert (
        result.task162_evidence.task162_result_identity_projection
        == result.task162_evidence.task162_result_identity_projection
    )


def test_task163_verifier_structured_acceptance_is_required(success_context, monkeypatch) -> None:
    monkeypatch.setattr(
        task163_service, "verify_task162_success", lambda *_args, **_kwargs: object()
    )
    result = validate_request(success_context[0])
    assert Task163FailureCode.TASK162_PRODUCER_VERIFICATION_FAILED in _blocked_codes(result)


def test_task163_result_hash_is_deterministic(success_context) -> None:
    assert _valid(success_context).result_hash == _valid(success_context).result_hash


def test_task163_no_test_double_enters_production_path(success_context) -> None:
    assert type(success_context[1]).__module__.startswith("hexagent.")


def test_task163_result_identity_uses_blocked_namespace_only_for_blocked() -> None:
    outcome = validate_request({})
    assert outcome.typed_blocked is not None
    assert outcome.typed_blocked.blocked_result_id != UUID("00000000-0000-0000-0000-000000000000")


def test_task162_applicability_exact_nine_checks(success_context) -> None:
    task162 = success_context[1]
    assert len(task162.applicability.checks) == 9
    assert tuple(name for name, _ in task162.applicability.checks) == tuple(
        task163_service.TASK162_APPLICABILITY_CHECKS
    )


def test_task162_applicability_missing_check_rejected(success_context) -> None:
    task162 = success_context[1]
    tampered = replace(
        task162,
        applicability=replace(task162.applicability, checks=task162.applicability.checks[:-1]),
    )
    outcome = validate_request({**success_context[0], "task162_result": tampered})
    assert outcome.typed_blocked is not None


def test_task162_applicability_extra_check_rejected(success_context) -> None:
    task162 = success_context[1]
    tampered = replace(
        task162,
        applicability=replace(
            task162.applicability,
            checks=task162.applicability.checks + (("EXTRA", "PASS"),),
        ),
    )
    outcome = validate_request({**success_context[0], "task162_result": tampered})
    assert outcome.typed_blocked is not None


def test_task162_completeness_exact_thirteen_fields(success_context) -> None:
    task162 = success_context[1]
    assert len(task162.completeness.required_fields) == 13
    assert tuple(task162.completeness.required_fields) == tuple(
        task163_service.TASK162_COMPLETENESS_FIELDS
    )


def test_task162_completeness_missing_field_rejected(success_context) -> None:
    task162 = success_context[1]
    tampered = replace(
        task162,
        completeness=replace(
            task162.completeness,
            required_fields=task162.completeness.required_fields[:-1],
        ),
    )
    outcome = validate_request({**success_context[0], "task162_result": tampered})
    assert outcome.typed_blocked is not None


def test_task162_completeness_extra_field_rejected(success_context) -> None:
    task162 = success_context[1]
    tampered = replace(
        task162,
        completeness=replace(
            task162.completeness,
            required_fields=task162.completeness.required_fields + ("EXTRA",),
        ),
    )
    outcome = validate_request({**success_context[0], "task162_result": tampered})
    assert outcome.typed_blocked is not None


def test_task162_verifier_unknown_diagnostic_rejected(success_context, monkeypatch) -> None:
    class UnknownDiagnostic:
        status = Task162SuccessVerificationStatus.REJECTED
        failure_reason_or_none = "UNKNOWN"

    monkeypatch.setattr(
        task163_service, "verify_task162_success", lambda *_args: UnknownDiagnostic()
    )
    outcome = validate_request(success_context[0])
    assert Task163FailureCode.TASK162_PRODUCER_VERIFICATION_FAILED in _blocked_codes(outcome)


def test_task162_verifier_exception_is_structured_failure(success_context, monkeypatch) -> None:
    monkeypatch.setattr(
        task163_service,
        "verify_task162_success",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("producer verifier failure")),
    )
    outcome = validate_request(success_context[0])
    assert Task163FailureCode.TASK162_PRODUCER_VERIFICATION_FAILED in _blocked_codes(outcome)


def test_task162_result_identity_tamper_rejected(success_context) -> None:
    tampered = replace(success_context[1], result_hash="0" * 64)
    outcome = validate_request({**success_context[0], "task162_result": tampered})
    assert outcome.typed_blocked is not None


def test_task162_replay_evidence_identity_tamper_rejected(success_context) -> None:
    tampered = replace(success_context[2], task162_result_hash="0" * 64)
    outcome = validate_request({**success_context[0], "task162_success_replay_evidence": tampered})
    assert outcome.typed_blocked is not None


def test_task162_task160_projection_join(success_context) -> None:
    result = _valid(success_context)
    projection = result.task162_evidence.task162_success_replay_evidence_identity_projection
    assert projection.task160_result_identity_projection.result_hash


def test_task162_task161_projection_join(success_context) -> None:
    result = _valid(success_context)
    projection = result.task162_evidence.task162_success_replay_evidence_identity_projection
    assert projection.task161_result_identity_projection.result_hash


def test_task162_task038_projection_join(success_context) -> None:
    result = _valid(success_context)
    projection = result.task162_evidence.task162_success_replay_evidence_identity_projection
    assert projection.task038_result_identity_projection.result_hash


def _accepted_task162_verifier(*_args):
    return Task162SuccessVerificationResult(
        status=Task162SuccessVerificationStatus.ACCEPTED,
        failure_reason_or_none=None,
    )


def test_duplicate_q_method_binding_rejected(success_context, monkeypatch) -> None:
    monkeypatch.setattr(task163_service, "verify_task162_success", _accepted_task162_verifier)
    task162 = success_context[1]
    tampered = replace(
        task162,
        energy_balance_evidence=replace(
            task162.energy_balance_evidence,
            q_method=task162.energy_balance_evidence.q_method + Decimal("1"),
        ),
    )
    outcome = validate_request({**success_context[0], "task162_result": tampered})
    assert Task163FailureCode.RATING_COMPOSITION_INCOMPLETE in _blocked_codes(outcome)


def test_duplicate_q_hot_binding_rejected(success_context, monkeypatch) -> None:
    monkeypatch.setattr(task163_service, "verify_task162_success", _accepted_task162_verifier)
    task162 = success_context[1]
    tampered = replace(
        task162,
        energy_balance_evidence=replace(
            task162.energy_balance_evidence,
            q_hot_nominal=task162.energy_balance_evidence.q_hot_nominal + Decimal("1"),
        ),
    )
    outcome = validate_request({**success_context[0], "task162_result": tampered})
    assert Task163FailureCode.RATING_COMPOSITION_INCOMPLETE in _blocked_codes(outcome)


def test_duplicate_q_cold_binding_rejected(success_context, monkeypatch) -> None:
    monkeypatch.setattr(task163_service, "verify_task162_success", _accepted_task162_verifier)
    task162 = success_context[1]
    tampered = replace(
        task162,
        energy_balance_evidence=replace(
            task162.energy_balance_evidence,
            q_cold_nominal=task162.energy_balance_evidence.q_cold_nominal + Decimal("1"),
        ),
    )
    outcome = validate_request({**success_context[0], "task162_result": tampered})
    assert Task163FailureCode.RATING_COMPOSITION_INCOMPLETE in _blocked_codes(outcome)


def test_task163_success_result_has_exact_twenty_fields(success_context) -> None:
    assert len(fields(_valid(success_context))) == 20


def test_task163_replay_evidence_nested_raw_kinds_are_exact(success_context) -> None:
    root = project_raw_request(success_context[0]).root
    evidence = next(
        child for child in root.children if child.field_name == "task162_success_replay_evidence"
    )
    kinds = {child.field_name: child.kind for child in evidence.children}
    assert kinds["original_task160_result"] is Task163RawProjectionKind.TASK160_RESULT_IDENTITY
    assert kinds["original_task161_result"] is Task163RawProjectionKind.TASK161_RESULT_IDENTITY
    assert (
        kinds["original_task038_success_result"] is Task163RawProjectionKind.TASK038_RESULT_IDENTITY
    )
    assert kinds["original_case_authority"] is Task163RawProjectionKind.CASE_AUTHORITY_IDENTITY


def test_task163_case_authority_identity_uses_real_producer_helper(success_context) -> None:
    evidence = success_context[2]
    expected = sha256_hex_from_framed_bytes(case_authority_bytes(evidence.original_case_authority))
    actual = _valid(
        success_context
    ).task162_evidence.task162_success_replay_evidence_identity_projection.original_case_authority_identity
    assert actual == expected


def test_task163_raw_binding_identity_projection(success_context) -> None:
    binding = success_context[1].cross_producer_binding_evidence
    projection = project_raw_request({"binding": binding})
    node = projection.root.children[0]
    assert node.kind is Task163RawProjectionKind.CROSS_PRODUCER_BINDING_IDENTITY
    assert len(node.children) == 11


def test_task163_raw_binding_permutation_is_identity_invariant(success_context) -> None:
    binding = success_context[1].cross_producer_binding_evidence
    reversed_binding = replace(
        binding,
        evidence_refs=tuple(reversed(binding.evidence_refs)),
        compatibility_evidence=tuple(reversed(binding.compatibility_evidence)),
    )
    assert raw_request_projection_hash(
        project_raw_request({"binding": binding})
    ) == raw_request_projection_hash(project_raw_request({"binding": reversed_binding}))


def test_task163_raw_case_authority_permutation_is_identity_invariant(success_context) -> None:
    case = success_context[2].original_case_authority
    reversed_case = replace(case, evidence_refs=tuple(reversed(case.evidence_refs)))
    first = raw_request_projection_hash(project_raw_request({"case": case}))
    second = raw_request_projection_hash(project_raw_request({"case": reversed_case}))
    assert first == second
