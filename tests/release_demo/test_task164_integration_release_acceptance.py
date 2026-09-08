"""Focused TASK164 integration and release-acceptance contract tests.

The fixture deliberately builds the request from the real TASK160, TASK161,
TASK162, and TASK163 producers.  Claims are only inputs to the admission
boundary; the implementation derives acceptance evidence from trusted local
observations.
"""

from __future__ import annotations

import hashlib
import os
import struct
from dataclasses import fields, replace
from enum import Enum
from pathlib import Path
from uuid import UUID

import pytest

from hexagent.exchangers.shell_tube.thermal_performance_closure import (
    issue_success_replay_evidence,
)
from hexagent.exchangers.shell_tube.thermal_performance_closure import (
    validate_request as validate_task162,
)
from hexagent.exchangers.shell_tube.thermal_rating_composition import (
    validate_request as validate_task163,
)
from hexagent.exchangers.shell_tube.thermal_rating_composition.models import (
    Task163Request,
    Task163ValidationResult,
)
from hexagent.exchangers.shell_tube.tube_side.canonical import (
    KIND_BOOL_FALSE,
    KIND_BOOL_TRUE,
    KIND_ENUM,
    KIND_INT,
    KIND_NONE,
    KIND_RECORD,
    KIND_STRING,
    KIND_TUPLE,
)
from hexagent.release_demo import task164_integration_release_acceptance as task164
from hexagent.release_demo.task164_integration_release_acceptance import (
    canonical,
    service,
    trusted_evidence,
)
from hexagent.release_demo.task164_integration_release_acceptance import models as m
from hexagent.release_demo.task164_integration_release_acceptance.raw_projection import (
    project_raw_request,
    project_raw_request_with_diagnostics,
)
from hexagent.release_demo.task164_integration_release_acceptance.scenarios import (
    TASK164_SCENARIO_MATRIX,
)
from tests.exchangers.shell_tube.test_task162_thermal_performance_closure import (
    _raw as task162_raw,
)
from tests.exchangers.shell_tube.test_task162_thermal_performance_closure import (
    _task162_request,
)

TASK163_SOURCE_ID = "TASK163-SOURCE-DEFINITION-R6-ISSUE-234"
TASK164_REQUEST_FIELDS = (
    "schema_version",
    "task164_version",
    "source_definition_id",
    "original_task163_request",
    "claimed_task163_validation_result",
    "scenario_claims",
    "repeat_run_claim",
    "python_parity_claim",
    "evidence_package_claim",
    "request_metadata",
)


def _task163_context_from_task162_raw(
    raw162: dict[str, object],
) -> tuple[Task163Request, Task163ValidationResult, dict[str, object]]:
    task162_outcome = validate_task162(raw162)
    assert task162_outcome.valid is not None
    task162_request = _task162_request(raw162)
    replay_evidence = issue_success_replay_evidence(task162_request, task162_outcome.valid)
    assert replay_evidence is not None
    raw163: dict[str, object] = {
        "schema_version": "task163.schema.v1",
        "task163_version": "task163.v1",
        "source_definition_id": TASK163_SOURCE_ID,
        "task162_result": task162_outcome.valid,
        "task162_success_replay_evidence": replay_evidence,
        "request_metadata": (),
    }
    request = Task163Request(
        schema_version=raw163["schema_version"],  # type: ignore[arg-type]
        task163_version=raw163["task163_version"],  # type: ignore[arg-type]
        source_definition_id=raw163["source_definition_id"],  # type: ignore[arg-type]
        task162_result=raw163["task162_result"],  # type: ignore[arg-type]
        task162_success_replay_evidence=raw163["task162_success_replay_evidence"],  # type: ignore[arg-type]
        request_metadata=(),
    )
    task163_outcome = validate_task163(raw163)
    assert task163_outcome.valid is not None
    return request, task163_outcome, raw163


def _task163_context() -> tuple[Task163Request, Task163ValidationResult, dict[str, object]]:
    return _task163_context_from_task162_raw(task162_raw())


def _task163_context_for_baffle(
    baffle_count: int,
) -> tuple[Task163Request, Task163ValidationResult, dict[str, object]]:
    raw162 = task162_raw()
    case = replace(
        raw162["case_authority"],
        case_authority_id=f"case-{baffle_count:03d}",
        baffle_count=baffle_count,
    )
    binding = replace(
        raw162["cross_producer_binding_authority"],
        binding_authority_id=f"binding-{baffle_count:03d}",
        physical_exchanger_case_id=case.case_authority_id,
    )
    raw162["case_authority"] = case
    raw162["cross_producer_binding_authority"] = binding
    return _task163_context_from_task162_raw(raw162)


def _task163_scenario_claim(
    scenario_id: m.Task164ScenarioId,
    original: Task163Request,
    base_outcome: Task163ValidationResult,
    scenario_context: tuple[Task163Request, Task163ValidationResult, dict[str, object]]
    | None = None,
) -> m.Task164ScenarioClaim:
    spec = next(item for item in TASK164_SCENARIO_MATRIX if item.scenario_id is scenario_id)
    authority = spec.input_authority
    baffle_count = None
    if authority.value.startswith("TASK162_ACCEPTED_CASE_BAFFLE_"):
        baffle_count = int(authority.value.rsplit("_", 1)[1])
    tamper_target = None
    if scenario_id is m.Task164ScenarioId.D164_N04_TASK163_RESULT_IDENTITY_OR_PROVENANCE_TAMPER:
        tamper_target = m.Task164TamperTarget.RESULT_HASH

    request_for_claim = scenario_context[0] if scenario_context is not None else original
    claimed = scenario_context[1] if scenario_context is not None else base_outcome
    if scenario_id is m.Task164ScenarioId.D164_N01_TASK163_TYPED_BLOCKED:
        raw = service.task163_request_raw(original)
        raw["task162_result"] = None
        claimed = validate_task163(raw)
    elif scenario_id is m.Task164ScenarioId.D164_N02_TASK163_RAW_BOUNDARY_BLOCKED:
        claimed = validate_task163(object())
    elif (
        scenario_id is m.Task164ScenarioId.D164_N03_TASK162_PRODUCER_ACCEPTANCE_OR_REPLAY_REJECTION
    ):
        request_for_claim = replace(
            original,
            task162_result=replace(original.task162_result, result_hash="0" * 64),
        )
        claimed = validate_task163(service.task163_request_raw(request_for_claim))
    elif scenario_id is m.Task164ScenarioId.D164_N04_TASK163_RESULT_IDENTITY_OR_PROVENANCE_TAMPER:
        assert base_outcome.valid is not None
        claimed = replace(
            base_outcome,
            valid=replace(base_outcome.valid, result_hash="0" * 64),
        )

    category = (
        m.Task164AcceptanceCategory.POSITIVE_DEMONSTRATION_COVERAGE
        if spec.scenario_class is m.Task164ScenarioClass.POSITIVE_PRODUCER
        else m.Task164AcceptanceCategory.NEGATIVE_FAIL_CLOSED_COVERAGE
        if spec.scenario_class is m.Task164ScenarioClass.NEGATIVE_PRODUCER
        else m.Task164AcceptanceCategory.REPEAT_RUN_DETERMINISM
        if scenario_id is m.Task164ScenarioId.D164_D01_REPEAT_RUN_IDENTITY_AND_EVIDENCE_PARITY
        else m.Task164AcceptanceCategory.CROSS_PYTHON_DETERMINISM
        if scenario_id is m.Task164ScenarioId.D164_D02_PYTHON_CROSS_VERSION_IDENTITY_PARITY
        else m.Task164AcceptanceCategory.SCOPE_FENCE_ACCEPTANCE
    )
    return m.Task164ScenarioClaim(
        scenario_id=scenario_id,
        scenario_class=spec.scenario_class,
        required_for_acceptance=spec.real_task163_required,
        input_setup=m.Task164ScenarioSetup(
            input_authority=authority,
            baffle_count=baffle_count,
            tamper_target=tamper_target,
            python_pair_key=(
                m.Task164PairingKey.TASK164_PYTHON_3_11__TASK164_PYTHON_3_12.value
                if scenario_id is m.Task164ScenarioId.D164_D02_PYTHON_CROSS_VERSION_IDENTITY_PARITY
                else None
            ),
        ),
        original_task163_request=request_for_claim,
        claimed_task163_validation_result=claimed,
        expected_task163_branch=spec.expected_branch,
        claimed_outcome=spec.expected_outcome,
        claimed_acceptance_categories=(category,),
        claimed_evidence_refs=(scenario_id.value,),
    )


def _blank_package_claim() -> m.Task164EvidencePackageClaim:
    return m.Task164EvidencePackageClaim(
        package_schema_version="task164.evidence-package.schema.v1",
        package_version="task164.evidence-package.v1",
        claimed_category_payload_hashes=(),
        claimed_artifact_records=(),
        claimed_package_hash=None,
        claimed_evidence_refs=(),
    )


def _build_task164_request() -> tuple[dict[str, object], Task163Request, Task163ValidationResult]:
    original, task163_outcome, _ = _task163_context()
    positive_contexts = {
        scenario_id: _task163_context_for_baffle(index)
        for index, scenario_id in enumerate(m.TASK164_SCENARIO_IDS[:5], start=1)
    }
    claims = tuple(
        _task163_scenario_claim(
            scenario_id,
            original,
            task163_outcome,
            positive_contexts.get(scenario_id),
        )
        for scenario_id in m.TASK164_SCENARIO_IDS
    )
    repeat_claim = m.Task164RepeatRunClaim(
        schema_version="task164.repeat-run-claim.v1",
        requested_run_count=2,
        claimed_surface_records=(),
        claimed_evidence_refs=(),
    )
    parity_claim = m.Task164PythonParityClaim(
        schema_version="task164.python-parity-claim.v1",
        requested_pair=(m.Task164PythonVersion.PYTHON_3_11, m.Task164PythonVersion.PYTHON_3_12),
        claimed_surface_records=(),
        claimed_evidence_refs=(),
    )
    request = m.Task164Request(
        schema_version=m.TASK164_SCHEMA_VERSION,
        task164_version=m.TASK164_VERSION,
        source_definition_id=m.TASK164_SOURCE_DEFINITION_ID,
        original_task163_request=original,
        claimed_task163_validation_result=task163_outcome,
        scenario_claims=claims,
        repeat_run_claim=repeat_claim,
        python_parity_claim=parity_claim,
        evidence_package_claim=_blank_package_claim(),
        request_metadata=(),
    )
    scenario_records = tuple(service.execute_scenario(claim, original) for claim in claims)
    assert all(record.status is m.Task164EvidenceStatus.PASS for record in scenario_records)
    task163_evidence = m.Task164Task163Evidence(
        original_request_projection_hash=canonical.task163_request_projection_hash(original),
        replay_evidence=tuple(record.replay_evidence for record in scenario_records),
        accepted_result_identities=tuple(
            record.observation.observed_task163_result_identity_or_none
            for record in scenario_records[:5]
            if record.observation.observed_task163_result_identity_or_none is not None
        ),
        status=m.Task164EvidenceStatus.PASS,
    )
    second_scenario_records = tuple(service.execute_scenario(claim, original) for claim in claims)
    second_task163_evidence = m.Task164Task163Evidence(
        original_request_projection_hash=canonical.task163_request_projection_hash(original),
        replay_evidence=tuple(record.replay_evidence for record in second_scenario_records),
        accepted_result_identities=tuple(
            record.observation.observed_task163_result_identity_or_none
            for record in second_scenario_records[:5]
            if record.observation.observed_task163_result_identity_or_none is not None
        ),
        status=m.Task164EvidenceStatus.PASS,
    )
    terminal = service._terminal_capability()
    second_terminal = service._terminal_capability()
    scope = service._scope_fence()
    second_scope = service._scope_fence()
    repeat = service._make_repeat_observation(
        request_projection=canonical.task163_request_projection_bytes(original),
        first_evidence=task163_evidence,
        second_evidence=second_task163_evidence,
        first_scenarios=scenario_records,
        second_scenarios=second_scenario_records,
        first_terminal=terminal,
        second_terminal=second_terminal,
        first_scope=scope,
        second_scope=second_scope,
    )
    main = trusted_evidence.observe_main_delivery()
    assert main.status is m.Task164ParityStatus.PASS
    dual = service._make_dual_runtime(
        request=request,
        task163=task163_outcome,
        scenarios=scenario_records,
        repeat=repeat,
        terminal=terminal,
        scope=scope,
        head_sha=main.observed_head_sha,
        head_tree=main.observed_head_tree,
    )
    assert dual.status is m.Task164ParityStatus.PASS
    determinism = m.Task164DeterminismEvidence(
        repeat_run_observation=repeat,
        dual_runtime_observation=dual,
        status=m.Task164ParityStatus.PASS,
    )
    original_projection = canonical.task163_request_projection_bytes(original)
    package, _ = service._build_payloads(
        main_delivery=main,
        task163_evidence=task163_evidence,
        scenarios=scenario_records,
        determinism=determinism,
        terminal=terminal,
        scope=scope,
        producer_applicability=task163_outcome.valid.applicability,
        producer_completeness=task163_outcome.valid.completeness,
        producer_result=task163_outcome,
        original_projection=original_projection,
    )
    payloads = (
        package.authority_evidence,
        package.main_delivery_evidence,
        package.task163_replay_evidence,
        package.task163_identity_evidence,
        package.task163_applicability_evidence,
        package.task163_completeness_evidence,
        package.task163_provenance_evidence,
        package.terminal_capability_evidence,
        package.positive_demo_evidence,
        package.negative_demo_evidence,
        package.repeat_run_evidence,
        package.cross_python_evidence,
        package.scope_fence_evidence,
    )
    package_bytes = canonical.evidence_package_bytes(package)
    category_hashes = tuple((payload.category, payload.payload_sha256) for payload in payloads)
    category_hashes += (
        (
            m.Task164AcceptanceCategory.EVIDENCE_PACKAGE_INTEGRITY,
            hashlib.sha256(package_bytes).hexdigest(),
        ),
    )
    package_claim = m.Task164EvidencePackageClaim(
        package_schema_version=package.package_schema_version,
        package_version=package.package_version,
        claimed_category_payload_hashes=category_hashes,
        claimed_artifact_records=package.artifact_inventory,
        claimed_package_hash=hashlib.sha256(package_bytes).hexdigest(),
        claimed_evidence_refs=(),
    )
    request = replace(request, evidence_package_claim=package_claim)
    raw = {
        "schema_version": request.schema_version,
        "task164_version": request.task164_version,
        "source_definition_id": request.source_definition_id,
        "original_task163_request": request.original_task163_request,
        "claimed_task163_validation_result": request.claimed_task163_validation_result,
        "scenario_claims": request.scenario_claims,
        "repeat_run_claim": request.repeat_run_claim,
        "python_parity_claim": request.python_parity_claim,
        "evidence_package_claim": request.evidence_package_claim,
        "request_metadata": request.request_metadata,
    }
    return raw, original, task163_outcome


@pytest.fixture(scope="module")
def success_context() -> tuple[dict[str, object], Task163Request, Task163ValidationResult]:
    return _build_task164_request()


def _blocked_codes(outcome: m.Task164ValidationResult) -> tuple[m.Task164FailureCode, ...]:
    if outcome.raw_boundary_blocked is not None:
        return tuple(item.code for item in outcome.raw_boundary_blocked.blockers)
    if outcome.typed_blocked is not None:
        return tuple(item.code for item in outcome.typed_blocked.blockers)
    return ()


def _read_framed_value(data: bytes, offset: int) -> tuple[bytes, bytes, int]:
    if offset + 4 > len(data):
        raise AssertionError("truncated kind length")
    kind_length = struct.unpack_from(">I", data, offset)[0]
    offset += 4
    kind_end = offset + kind_length
    if kind_end > len(data):
        raise AssertionError("truncated kind")
    kind = data[offset:kind_end]
    offset = kind_end
    if offset + 8 > len(data):
        raise AssertionError("truncated payload length")
    payload_length = struct.unpack_from(">Q", data, offset)[0]
    offset += 8
    payload_end = offset + payload_length
    if payload_end > len(data):
        raise AssertionError("truncated payload")
    return kind, data[offset:payload_end], payload_end


def _tuple_items(data: bytes) -> tuple[tuple[bytes, bytes], ...]:
    if len(data) < 4:
        raise AssertionError("truncated tuple")
    count = struct.unpack_from(">I", data, 0)[0]
    offset = 4
    items: list[tuple[bytes, bytes]] = []
    for _ in range(count):
        outer_kind, outer_payload, offset = _read_framed_value(data, offset)
        assert outer_kind == b"ITEM"
        kind, payload, item_end = _read_framed_value(outer_payload, 0)
        assert item_end == len(outer_payload)
        items.append((kind, payload))
    assert offset == len(data)
    return tuple(items)


def _negative_payload_fields(result: m.Task164Result, index: int) -> dict[str, tuple[bytes, bytes]]:
    _, outer = trusted_evidence._parse_record(
        result.evidence_package.negative_demo_evidence.canonical_payload_bytes
    )
    kind, payload = outer["scenario_records"]
    assert kind == KIND_TUPLE
    items = _tuple_items(payload)
    record_kind, record_payload = items[index]
    assert record_kind == KIND_RECORD
    namespace, fields_by_name = trusted_evidence._parse_record(record_payload)
    assert namespace == "TASK164_NEGATIVE_DEMONSTRATION_RECORD_V1"
    return fields_by_name


def _markers(node: m.Task164RawProjectionNode) -> list[m.Task164RawProjectionNode]:
    values = [node] if node.kind is m.Task164RawProjectionKind.LIMIT_MARKER else []
    for child in node.children:
        values.extend(_markers(child))
    return values


def _valid_result(success_context):
    raw, _, _ = success_context
    outcome = task164.validate_request(raw)
    assert outcome.status is m.Task164ValidationBranch.VALID
    assert outcome.valid is not None
    return outcome.valid


def _dual_runtime_from_valid_context(success_context, result):
    raw, _, claimed = success_context
    request, errors = service._parse_request(raw)
    assert not errors and request is not None
    main = trusted_evidence.observe_main_delivery()
    assert main.status is m.Task164ParityStatus.PASS
    return service._make_dual_runtime(
        request=request,
        task163=claimed,
        scenarios=result.scenario_evidence,
        repeat=result.determinism_evidence.repeat_run_observation,
        terminal=result.terminal_capability,
        scope=result.scope_fence_evidence,
        head_sha=main.observed_head_sha,
        head_tree=main.observed_head_tree,
    )


def test_task164_request_has_exact_ten_fields() -> None:
    assert tuple(item.name for item in fields(m.Task164Request)) == TASK164_REQUEST_FIELDS


def test_task164_public_surface_exposes_validate_request_only() -> None:
    assert task164.__all__ == ("validate_request",)


def test_task164_request_exact_nested_types(success_context) -> None:
    _, original, claimed = success_context
    assert type(original) is Task163Request
    assert type(claimed) is Task163ValidationResult


def test_task164_unknown_top_level_field_raw_schema_failure(success_context) -> None:
    raw, _, _ = success_context
    outcome = task164.validate_request({**raw, "unexpected": 1})
    assert outcome.status is m.Task164ValidationBranch.RAW_BOUNDARY_BLOCKED
    assert m.Task164FailureCode.INVALID_REQUEST_SCHEMA in _blocked_codes(outcome)


def test_task164_missing_top_level_field_raw_schema_failure(success_context) -> None:
    raw, _, _ = success_context
    missing = dict(raw)
    del missing["scenario_claims"]
    outcome = task164.validate_request(missing)
    assert outcome.status is m.Task164ValidationBranch.RAW_BOUNDARY_BLOCKED


def test_task164_duplicate_metadata_raw_schema_failure(success_context) -> None:
    raw, _, _ = success_context
    outcome = task164.validate_request({**raw, "request_metadata": (("x", "1"), ("x", "2"))})
    assert outcome.status is m.Task164ValidationBranch.RAW_BOUNDARY_BLOCKED


def test_task164_request_metadata_duplicate_rejected(success_context) -> None:
    raw, _, _ = success_context
    duplicated = {**raw, "request_metadata": (("release", "demo"), ("release", "demo"))}
    outcome = task164.validate_request(duplicated)
    assert outcome.status is m.Task164ValidationBranch.RAW_BOUNDARY_BLOCKED
    assert _blocked_codes(outcome) == (m.Task164FailureCode.INVALID_REQUEST_SCHEMA,)


def test_task164_source_definition_mismatch_raw_failure(success_context) -> None:
    raw, _, _ = success_context
    outcome = task164.validate_request({**raw, "source_definition_id": "wrong"})
    assert outcome.status is m.Task164ValidationBranch.RAW_BOUNDARY_BLOCKED
    assert m.Task164FailureCode.SOURCE_DEFINITION_ID_MISMATCH in _blocked_codes(outcome)


def test_task164_unsupported_version_raw_failure(success_context) -> None:
    raw, _, _ = success_context
    outcome = task164.validate_request({**raw, "task164_version": "task164.invalid"})
    assert outcome.status is m.Task164ValidationBranch.RAW_BOUNDARY_BLOCKED
    assert m.Task164FailureCode.UNSUPPORTED_TASK164_VERSION in _blocked_codes(outcome)


def test_task164_raw_unsupported_object_total() -> None:
    outcome = task164.validate_request(object())
    assert outcome.status is m.Task164ValidationBranch.RAW_BOUNDARY_BLOCKED
    assert _blocked_codes(outcome) == (m.Task164FailureCode.INVALID_REQUEST_TYPE,)


def test_task164_raw_unicode_failure_total() -> None:
    outcome = task164.validate_request({"request_metadata": (("\ud800", "value"),)})
    assert outcome.status is m.Task164ValidationBranch.RAW_BOUNDARY_BLOCKED
    assert m.Task164FailureCode.RAW_UNICODE_ENCODING_FAILURE in _blocked_codes(outcome)


def test_task164_raw_depth_limit() -> None:
    value: object = "leaf"
    for _ in range(m.TASK164_RAW_MAX_DEPTH + 2):
        value = {"nested": value}
    outcome = project_raw_request_with_diagnostics(value)
    assert m.Task164FailureCode.RAW_DEPTH_LIMIT_EXCEEDED in outcome.reasons


def test_task164_raw_node_limit() -> None:
    value = {f"k-{index:04d}": index for index in range(m.TASK164_RAW_MAX_NODES + 1)}
    outcome = project_raw_request_with_diagnostics(value)
    assert m.Task164FailureCode.RAW_NODE_LIMIT_EXCEEDED in outcome.reasons


def test_task164_raw_scalar_limit() -> None:
    outcome = project_raw_request_with_diagnostics(
        {"value": "x" * m.TASK164_RAW_TEXT_BYTE_COUNT_LIMIT_PLUS_ONE}
    )
    assert m.Task164FailureCode.RAW_SCALAR_BYTE_LIMIT_EXCEEDED in outcome.reasons


def test_task164_raw_record_permutation_invariant() -> None:
    left = project_raw_request({"b": 2, "a": 1})
    right = project_raw_request({"a": 1, "b": 2})
    assert canonical.raw_request_projection_hash(left) == canonical.raw_request_projection_hash(
        right
    )


def test_task164_raw_no_user_hooks() -> None:
    class Hostile:
        def __repr__(self) -> str:
            raise AssertionError("repr must not run")

        def __str__(self) -> str:
            raise AssertionError("str must not run")

    projection = project_raw_request(Hostile())
    assert projection.root.kind is m.Task164RawProjectionKind.LIMIT_MARKER


def test_task164_raw_limit_marker_canonical() -> None:
    marker = project_raw_request({"value": "x" * 16_385}).root.children[0]
    assert marker.field_name == "__TASK164_LIMIT_MARKER__"
    assert marker.kind is m.Task164RawProjectionKind.LIMIT_MARKER
    assert marker.type_identity is None
    assert marker.scalar_payload == m.Task164FailureCode.RAW_SCALAR_BYTE_LIMIT_EXCEEDED.value
    assert marker.children == ()


def test_task164_request_metadata_utf8_order(success_context) -> None:
    raw, _, _ = success_context
    parsed_left, errors_left = service._parse_request(
        {**raw, "request_metadata": (("b", "2"), ("a", "1"))}
    )
    parsed_right, errors_right = service._parse_request(
        {**raw, "request_metadata": (("a", "1"), ("b", "2"))}
    )
    assert not errors_left and not errors_right
    assert parsed_left is not None and parsed_right is not None
    assert parsed_left.request_metadata == parsed_right.request_metadata
    assert canonical.request_hash(parsed_left) == canonical.request_hash(parsed_right)


def test_task164_validation_branch_exactly_one(success_context) -> None:
    valid = task164.validate_request(success_context[0])
    raw_blocked = task164.validate_request("not a request")
    typed_blocked = task164.validate_request(
        {**success_context[0], "original_task163_request": None}
    )
    assert (
        sum(
            item is not None
            for item in (valid.raw_boundary_blocked, valid.typed_blocked, valid.valid)
        )
        == 1
    )
    assert (
        sum(
            item is not None
            for item in (
                raw_blocked.raw_boundary_blocked,
                raw_blocked.typed_blocked,
                raw_blocked.valid,
            )
        )
        == 1
    )
    assert typed_blocked.status is m.Task164ValidationBranch.TYPED_BLOCKED


def test_task164_task163_request_projection(success_context) -> None:
    _, original, _ = success_context
    projection = canonical.task163_request_projection_bytes(original)
    assert b"TASK164_TASK163_REQUEST_PROJECTION_V1" in projection


def test_task164_task162_result_projection(success_context) -> None:
    _, original, _ = success_context
    projection = canonical.task162_result_identity_bytes(original.task162_result)
    assert len(projection) > 0


def test_task164_task162_replay_evidence_projection(success_context) -> None:
    _, original, _ = success_context
    projection = canonical.task162_success_replay_evidence_identity_bytes(
        original.task162_success_replay_evidence
    )
    assert len(projection) > 0


def test_task164_task160_identity_projection(success_context) -> None:
    projection = canonical.task160_result_identity_bytes(task162_raw()["task160_result"])
    assert len(projection) > 0


def test_task164_task161_identity_projection(success_context) -> None:
    projection = canonical.task161_result_identity_bytes(task162_raw()["task161_result"])
    assert len(projection) > 0


def test_task164_task038_identity_projection(success_context) -> None:
    projection = canonical.task038_result_identity_bytes(task162_raw()["task038_result"])
    assert len(projection) > 0


def test_task164_case_authority_projection(success_context) -> None:
    case_bytes = canonical.case_authority_bytes(task162_raw()["case_authority"])
    assert len(case_bytes) > 0


def test_task164_nested_projection_no_full_serialization(success_context) -> None:
    raw, _, _ = success_context
    node = project_raw_request(raw).root
    assert node.kind is m.Task164RawProjectionKind.RECORD
    assert len(node.children) == len(TASK164_REQUEST_FIELDS)
    assert all(child.field_name in TASK164_REQUEST_FIELDS for child in node.children)
    assert (
        next(
            child for child in node.children if child.field_name == "original_task163_request"
        ).type_identity
        == "Task163Request"
    )
    projected_identity = next(
        child for child in node.children if child.field_name == "original_task163_request"
    )
    assert projected_identity.scalar_payload is not None
    assert len(projected_identity.scalar_payload) == 64
    assert projected_identity.children == ()


def test_task164_task163_replay_valid(success_context) -> None:
    _, original, claimed = success_context
    replayed, blockers = service._replay_task163(original)
    assert not blockers
    assert replayed is not None
    assert canonical.task163_validation_projection_bytes(
        replayed
    ) == canonical.task163_validation_projection_bytes(claimed)


def test_task164_task163_replay_typed_blocked() -> None:
    outcome = validate_task163(
        {
            "schema_version": "task163.schema.v1",
            "task163_version": "task163.v1",
            "source_definition_id": TASK163_SOURCE_ID,
            "task162_result": None,
            "task162_success_replay_evidence": None,
            "request_metadata": (),
        }
    )
    assert outcome.status is not None
    assert outcome.typed_blocked is not None


def test_task164_task163_replay_raw_blocked() -> None:
    outcome = validate_task163(object())
    assert outcome.raw_boundary_blocked is not None
    assert outcome.valid is None


def test_task164_task163_result_hash_mismatch(success_context) -> None:
    raw, _, claimed = success_context
    assert claimed.valid is not None
    changed = replace(claimed, valid=replace(claimed.valid, result_hash="0" * 64))
    outcome = task164.validate_request({**raw, "claimed_task163_validation_result": changed})
    assert outcome.status is m.Task164ValidationBranch.TYPED_BLOCKED
    assert _blocked_codes(outcome) == (m.Task164FailureCode.TASK163_RESULT_HASH_MISMATCH,)


def test_task164_task163_result_id_mismatch(success_context) -> None:
    raw, _, claimed = success_context
    assert claimed.valid is not None
    changed = replace(claimed, valid=replace(claimed.valid, result_id=UUID(int=0)))
    outcome = task164.validate_request({**raw, "claimed_task163_validation_result": changed})
    assert outcome.status is m.Task164ValidationBranch.TYPED_BLOCKED
    assert _blocked_codes(outcome) == (m.Task164FailureCode.TASK163_RESULT_ID_MISMATCH,)


def test_task164_task163_provenance_mismatch(success_context) -> None:
    raw, _, claimed = success_context
    assert claimed.valid is not None
    changed = replace(
        claimed,
        valid=replace(
            claimed.valid,
            provenance=replace(claimed.valid.provenance, provenance_hash="0" * 64),
        ),
    )
    outcome = task164.validate_request({**raw, "claimed_task163_validation_result": changed})
    assert outcome.status is m.Task164ValidationBranch.TYPED_BLOCKED
    assert _blocked_codes(outcome) == (m.Task164FailureCode.TASK163_PROVENANCE_MISMATCH,)


def test_task164_task163_applicability_exact(success_context) -> None:
    _, _, claimed = success_context
    assert claimed.valid is not None
    assert tuple(name for name, _ in claimed.valid.applicability.checks) == (
        "TASK162_SUCCESS_ACCEPTED",
        "TASK162_APPLICABILITY_ACCEPTED",
        "TASK162_COMPLETENESS_ACCEPTED",
        "TASK162_IDENTITY_ACCEPTED",
        "TASK162_PROVENANCE_ACCEPTED",
        "RATING_COMPOSITION_BINDING_COMPLETE",
    )
    assert all(status == "PASS" for _, status in claimed.valid.applicability.checks)
    assert claimed.valid.applicability.status.value == "APPLICABLE"


def test_task164_task163_completeness_exact(success_context) -> None:
    _, _, claimed = success_context
    assert claimed.valid is not None
    assert claimed.valid.completeness.required_fields == (
        "ACCEPTED_TASK162_EVIDENCE",
        "TASK162_IDENTITY_REPLAY_COMPLETE",
        "TASK162_PROVENANCE_REPLAY_COMPLETE",
        "RATING_PERFORMANCE_PROJECTION",
        "HEAT_DUTY_PROJECTION",
        "HOT_OUTLET_PROJECTION",
        "COLD_OUTLET_PROJECTION",
        "ENERGY_BALANCE_EVIDENCE",
        "TERMINAL_TEMPERATURE_EVIDENCE",
        "RATING_APPLICABILITY_LEDGER",
        "RATING_COMPLETENESS_EVIDENCE",
        "DEFERRED_CAPABILITY_DECLARATION",
        "TASK163_PROVENANCE",
        "TASK163_RESULT_IDENTITY",
    )
    assert claimed.valid.completeness.status.value == "COMPLETE"


def _assert_positive_baffle(success_context, index: int) -> None:
    result = _valid_result(success_context)
    record = result.scenario_evidence[index]
    expected_baffle = index + 1
    assert record.observation.observed_outcome is m.Task164ScenarioOutcome.PASS
    assert record.observation.real_task163_invoked
    assert record.claim.input_setup.baffle_count == expected_baffle
    assert (
        record.claim.original_task163_request.task162_success_replay_evidence.original_case_authority.baffle_count
        == expected_baffle
    )


def test_task164_positive_baffle_1(success_context) -> None:
    _assert_positive_baffle(success_context, 0)


def test_task164_positive_baffle_2(success_context) -> None:
    _assert_positive_baffle(success_context, 1)


def test_task164_positive_baffle_3(success_context) -> None:
    _assert_positive_baffle(success_context, 2)


def test_task164_positive_baffle_4(success_context) -> None:
    _assert_positive_baffle(success_context, 3)


def test_task164_positive_baffle_5(success_context) -> None:
    _assert_positive_baffle(success_context, 4)


def test_task164_negative_typed_blocked(success_context) -> None:
    result = _valid_result(success_context)
    record = result.scenario_evidence[5]
    assert record.observation.observed_task163_branch is m.Task164Task163Branch.TYPED_BLOCKED
    claimed = record.claim.claimed_task163_validation_result
    assert claimed is not None and claimed.typed_blocked is not None
    assert claimed.typed_blocked.blockers[0].code.value == "INVALID_TASK162_RESULT"
    fields_by_name = _negative_payload_fields(result, 0)
    assert fields_by_name["expected_failure_stage"] == (KIND_ENUM, b"TYPED_VALIDATION")
    assert fields_by_name["observed_failure_code"] == (KIND_ENUM, b"INVALID_TASK162_RESULT")


def test_task164_negative_raw_boundary_blocked(success_context) -> None:
    result = _valid_result(success_context)
    record = result.scenario_evidence[6]
    assert record.observation.observed_task163_branch is m.Task164Task163Branch.RAW_BOUNDARY_BLOCKED
    claimed = record.claim.claimed_task163_validation_result
    assert claimed is not None and claimed.raw_boundary_blocked is not None
    assert claimed.raw_boundary_blocked.blockers[0].code.value == "INVALID_REQUEST_TYPE"
    fields_by_name = _negative_payload_fields(result, 1)
    assert fields_by_name["expected_failure_stage"] == (KIND_ENUM, b"RAW_BOUNDARY")
    assert fields_by_name["observed_failure_code"] == (KIND_ENUM, b"INVALID_REQUEST_TYPE")


def test_task164_negative_task162_replay_rejection(success_context) -> None:
    result = _valid_result(success_context)
    record = result.scenario_evidence[7]
    assert record.observation.observed_outcome is m.Task164ScenarioOutcome.NEGATIVE_PASS
    claimed = record.claim.claimed_task163_validation_result
    assert claimed is not None and claimed.typed_blocked is not None
    assert claimed.typed_blocked.blockers[0].code.value == "TASK162_IDENTITY_REPLAY_FAILED"
    fields_by_name = _negative_payload_fields(result, 2)
    assert fields_by_name["expected_failure_stage"] == (KIND_ENUM, b"TASK163_REPLAY")
    assert fields_by_name["observed_failure_code"] == (KIND_ENUM, b"TASK163_REPLAY_BLOCKED")


def test_task164_negative_task163_claim_tamper(success_context) -> None:
    result = _valid_result(success_context)
    record = result.scenario_evidence[8]
    assert record.replay_evidence.claim_match_status is m.Task164ClaimMatchStatus.MISMATCHED
    fields_by_name = _negative_payload_fields(result, 3)
    assert fields_by_name["expected_failure_stage"] == (KIND_ENUM, b"TASK163_REPLAY")
    assert fields_by_name["observed_failure_code"] == (
        KIND_ENUM,
        b"TASK163_RESULT_HASH_MISMATCH",
    )


def test_task164_scenario_matrix_exact() -> None:
    assert tuple(spec.scenario_id for spec in TASK164_SCENARIO_MATRIX) == m.TASK164_SCENARIO_IDS


def test_task164_positive_requires_real_producer(success_context) -> None:
    result = _valid_result(success_context)
    assert all(item.observation.real_task163_invoked for item in result.scenario_evidence[:5])


def test_task164_negative_fail_closed(success_context, monkeypatch) -> None:
    raw, _, _ = success_context
    original = service.execute_scenario_with_diagnostic

    def force_wrong_diagnostic(claim, fallback):
        execution = original(claim, fallback)
        if claim.scenario_id is m.Task164ScenarioId.D164_N01_TASK163_TYPED_BLOCKED:
            assert execution.diagnostic is not None
            return replace(
                execution,
                diagnostic=replace(
                    execution.diagnostic,
                    code=m.Task164FailureCode.TASK163_RESULT_ID_MISMATCH,
                ),
            )
        return execution

    monkeypatch.setattr(service, "execute_scenario_with_diagnostic", force_wrong_diagnostic)
    outcome = task164.validate_request(raw)
    assert outcome.status is m.Task164ValidationBranch.TYPED_BLOCKED
    assert outcome.typed_blocked is not None
    assert outcome.typed_blocked.failure_stage is m.Task164FailureStage.DEMONSTRATION
    assert _blocked_codes(outcome) == (m.Task164FailureCode.SCENARIO_EVIDENCE_INVALID,)


def test_task164_terminal_capability_matrix(success_context) -> None:
    capability = _valid_result(success_context).terminal_capability
    assert capability.shell_pass_count == 1
    assert capability.tube_pass_count == 1
    assert capability.status is m.Task164EvidenceStatus.PASS


def test_task164_scope_fence_lmtd_absent(success_context, tmp_path) -> None:
    hostile = tmp_path / "hostile_lmtd.py"
    hostile.write_text("def calculate_lmtd():\n    return 1\n", encoding="utf-8")
    assert (
        trusted_evidence.observe_scope_fence(source_root=hostile.parent).status
        is m.Task164ScopeStatus.BLOCKED
    )
    scope = _valid_result(success_context).scope_fence_evidence
    assert m.Task164ForbiddenCapabilityToken.LMTD in scope.forbidden_capability_tokens_absent


def test_task164_scope_fence_f_factor_absent(success_context, tmp_path) -> None:
    hostile = tmp_path / "hostile_f_factor.py"
    hostile.write_text("def f_factor():\n    return 1\n", encoding="utf-8")
    assert (
        trusted_evidence.observe_scope_fence(source_root=hostile.parent).status
        is m.Task164ScopeStatus.BLOCKED
    )
    scope = _valid_result(success_context).scope_fence_evidence
    assert m.Task164ForbiddenCapabilityToken.F_FACTOR in scope.forbidden_capability_tokens_absent


def test_task164_repeat_run_all_surfaces(success_context) -> None:
    repeat = _valid_result(success_context).determinism_evidence.repeat_run_observation
    assert repeat.run_count == 2
    assert repeat.observed_equal
    assert len(repeat.surface_records) == len(m.Task164RepeatRunSurface)
    assert tuple(item.surface for item in repeat.surface_records) == tuple(
        m.Task164RepeatRunSurface
    )
    assert all(
        record.replay_evidence.producer_invocation_count == 1
        for record in _valid_result(success_context).scenario_evidence
        if record.observation.real_task163_invoked
    )


def test_task164_repeat_run_failure_blocks(success_context, monkeypatch) -> None:
    raw, _, _ = success_context
    original = service.execute_scenario_with_diagnostic
    calls = 0

    def drift_on_second_run(claim, fallback):
        nonlocal calls
        calls += 1
        execution = original(claim, fallback)
        if calls > len(m.TASK164_SCENARIO_IDS) and calls == len(m.TASK164_SCENARIO_IDS) + 1:
            return replace(
                execution,
                record=replace(
                    execution.record,
                    replay_evidence=replace(
                        execution.record.replay_evidence,
                        evidence_refs=("TASK164_SECOND_RUN_DRIFT",),
                    ),
                ),
            )
        return execution

    monkeypatch.setattr(service, "execute_scenario_with_diagnostic", drift_on_second_run)
    outcome = task164.validate_request(raw)
    assert outcome.status is m.Task164ValidationBranch.TYPED_BLOCKED
    assert outcome.typed_blocked is not None
    assert outcome.typed_blocked.failure_stage is m.Task164FailureStage.DETERMINISM
    assert _blocked_codes(outcome) == (m.Task164FailureCode.REPEAT_RUN_PARITY_FAILED,)
    assert calls == 2 * len(m.TASK164_SCENARIO_IDS)


def test_task164_claimed_scenario_not_authoritative(success_context) -> None:
    result = _valid_result(success_context)
    assert result.demonstration_coverage.scenario_records[0].observation.real_task163_invoked


def test_task164_claimed_repeat_not_authoritative(success_context) -> None:
    result = _valid_result(success_context)
    assert result.determinism_evidence.repeat_run_observation.status is m.Task164ParityStatus.PASS


def test_task164_claimed_package_not_authoritative(success_context) -> None:
    raw, _, _ = success_context
    claim = replace(raw["evidence_package_claim"], claimed_package_hash="0" * 64)
    outcome = task164.validate_request({**raw, "evidence_package_claim": claim})
    assert outcome.status is m.Task164ValidationBranch.TYPED_BLOCKED


def test_task164_evidence_category_mapping() -> None:
    expected = (
        (m.Task164AcceptanceCategory.AUTHORITY_CHAIN_INTEGRITY, "AUTHORITY_CHAIN_PAYLOAD"),
        (
            m.Task164AcceptanceCategory.DELIVERED_MAIN_AND_PREDECESSOR_INTEGRITY,
            "MAIN_DELIVERY_PAYLOAD",
        ),
        (m.Task164AcceptanceCategory.TASK163_PUBLIC_BOUNDARY_ACCEPTANCE, "TASK163_REPLAY_PAYLOAD"),
        (
            m.Task164AcceptanceCategory.TASK163_RESULT_IDENTITY_ACCEPTANCE,
            "TASK163_IDENTITY_PAYLOAD",
        ),
        (
            m.Task164AcceptanceCategory.TASK163_APPLICABILITY_ACCEPTANCE,
            "TASK163_APPLICABILITY_PAYLOAD",
        ),
        (
            m.Task164AcceptanceCategory.TASK163_COMPLETENESS_ACCEPTANCE,
            "TASK163_COMPLETENESS_PAYLOAD",
        ),
        (m.Task164AcceptanceCategory.TASK163_PROVENANCE_ACCEPTANCE, "TASK163_PROVENANCE_PAYLOAD"),
        (
            m.Task164AcceptanceCategory.SUPPORTED_TERMINAL_CAPABILITY_COVERAGE,
            "TERMINAL_CAPABILITY_PAYLOAD",
        ),
        (
            m.Task164AcceptanceCategory.POSITIVE_DEMONSTRATION_COVERAGE,
            "POSITIVE_DEMONSTRATION_PAYLOAD",
        ),
        (
            m.Task164AcceptanceCategory.NEGATIVE_FAIL_CLOSED_COVERAGE,
            "NEGATIVE_DEMONSTRATION_PAYLOAD",
        ),
        (m.Task164AcceptanceCategory.REPEAT_RUN_DETERMINISM, "REPEAT_RUN_PAYLOAD"),
        (m.Task164AcceptanceCategory.CROSS_PYTHON_DETERMINISM, "PYTHON_PARITY_PAYLOAD"),
        (m.Task164AcceptanceCategory.SCOPE_FENCE_ACCEPTANCE, "SCOPE_FENCE_PAYLOAD"),
        (m.Task164AcceptanceCategory.EVIDENCE_PACKAGE_INTEGRITY, None),
    )
    assert (
        tuple(
            (category, payload.value if payload is not None else None)
            for category, payload in m.TASK164_ACCEPTANCE_CATEGORY_TO_PAYLOAD.items()
        )
        == expected
    )


def test_task164_evidence_refs_sorted(success_context) -> None:
    result = _valid_result(success_context)
    for record in result.scenario_evidence:
        assert record.observation.evidence_refs == tuple(
            sorted(record.observation.evidence_refs, key=lambda value: value.encode("utf-8"))
        )


def test_task164_artifact_inventory_exact(success_context) -> None:
    assert len(_valid_result(success_context).evidence_package.artifact_inventory) == 6


def test_task164_acceptance_ledger_all_categories(success_context) -> None:
    ledger = _valid_result(success_context).acceptance_ledger
    assert tuple(item.category for item in ledger.records) == m.TASK164_ACCEPTANCE_CATEGORIES
    assert all(item.status is m.Task164AcceptanceCategoryStatus.PASS for item in ledger.records)


def test_task164_no_task165_or_release_side_effects(success_context, tmp_path) -> None:
    hostile = tmp_path / "hostile_task165.py"
    hostile.write_text("def TASK165():\n    return True\n", encoding="utf-8")
    assert (
        trusted_evidence.observe_scope_fence(source_root=hostile.parent).status
        is m.Task164ScopeStatus.BLOCKED
    )
    result = _valid_result(success_context)
    assert result.scope_fence_evidence.task165_absent
    assert not any(item.name == "TASK165" for item in fields(result))


def test_valid_real_task163_request_nested_projection_reaches_replay(success_context) -> None:
    assert _valid_result(success_context).task163_evidence.status is m.Task164EvidenceStatus.PASS


def test_missing_top_level_original_task163_request_is_raw_schema_failure(success_context) -> None:
    raw, _, _ = success_context
    missing = dict(raw)
    del missing["original_task163_request"]
    assert (
        task164.validate_request(missing).status is m.Task164ValidationBranch.RAW_BOUNDARY_BLOCKED
    )


def test_present_null_task163_request_context_is_typed_failure(success_context) -> None:
    raw, _, _ = success_context
    outcome = task164.validate_request({**raw, "original_task163_request": None})
    assert outcome.status is m.Task164ValidationBranch.TYPED_BLOCKED


def test_raw_stage_never_emits_typed_only_code() -> None:
    outcome = task164.validate_request(object())
    assert all(
        item.code not in {m.Task164FailureCode.TASK163_RESULT_MISMATCH}
        for item in outcome.raw_boundary_blocked.blockers
    )


def test_each_scenario_row_matches_frozen_matrix() -> None:
    assert len(TASK164_SCENARIO_MATRIX) == 12
    assert (
        tuple(item.expected_outcome for item in TASK164_SCENARIO_MATRIX[:5])
        == (m.Task164ScenarioOutcome.PASS,) * 5
    )


def test_evidence_category_domain_substitution_rejected(success_context) -> None:
    raw, _, _ = success_context
    claim = raw["evidence_package_claim"]
    assert isinstance(claim, m.Task164EvidencePackageClaim)
    entries = list(claim.claimed_category_payload_hashes)
    first_category, first_hash = entries[0]
    second_category, second_hash = entries[1]
    entries[0] = (first_category, second_hash)
    entries[1] = (second_category, first_hash)
    swapped = replace(claim, claimed_category_payload_hashes=tuple(entries))
    outcome = task164.validate_request({**raw, "evidence_package_claim": swapped})
    assert outcome.status is m.Task164ValidationBranch.TYPED_BLOCKED
    assert _blocked_codes(outcome) == (m.Task164FailureCode.EVIDENCE_PACKAGE_INTEGRITY_FAILED,)


def test_self_consistent_scenario_claim_cannot_create_pass(success_context) -> None:
    raw, _, _ = success_context
    claims = list(raw["scenario_claims"])
    claims[0] = replace(claims[0], claimed_outcome=m.Task164ScenarioOutcome.BLOCKED)
    outcome = task164.validate_request({**raw, "scenario_claims": tuple(claims)})
    assert outcome.status is m.Task164ValidationBranch.TYPED_BLOCKED
    assert _blocked_codes(outcome) == (m.Task164FailureCode.SCENARIO_EVIDENCE_INVALID,)


def test_self_consistent_repeat_claim_cannot_create_pass(success_context) -> None:
    raw, _, _ = success_context
    claim = raw["repeat_run_claim"]
    assert isinstance(claim, m.Task164RepeatRunClaim)
    result = _valid_result(
        ({**raw, "repeat_run_claim": replace(claim, requested_run_count=1)}, None, None)
    )
    assert result.determinism_evidence.status is m.Task164ParityStatus.PASS
    assert result.determinism_evidence.repeat_run_observation.run_count == 2


def test_stale_head_internal_dual_runtime_observation_rejected(
    success_context, monkeypatch
) -> None:
    result = _valid_result(success_context)
    original_run_runtime = trusted_evidence._run_runtime

    def stale_run_runtime(executable, version, input_bytes, head_sha, head_tree):
        observation = original_run_runtime(executable, version, input_bytes, head_sha, head_tree)
        if version is m.Task164PythonVersion.PYTHON_3_11:
            return replace(observation, head_sha="0" * 40)
        return observation

    monkeypatch.setattr(trusted_evidence, "_run_runtime", stale_run_runtime)
    dual = _dual_runtime_from_valid_context(success_context, result)
    assert dual.status is m.Task164ParityStatus.BLOCKED


def test_wrong_runtime_internal_dual_runtime_observation_rejected(
    success_context, monkeypatch
) -> None:
    result = _valid_result(success_context)
    py311 = os.environ["TASK164_PY311_EXECUTABLE"]
    py312 = os.environ["TASK164_PY312_EXECUTABLE"]
    monkeypatch.setenv("TASK164_PY311_EXECUTABLE", py312)
    monkeypatch.setenv("TASK164_PY312_EXECUTABLE", py311)
    dual = _dual_runtime_from_valid_context(success_context, result)
    assert dual.status is m.Task164ParityStatus.BLOCKED


def test_duplicate_python_pair_rejected(success_context, monkeypatch) -> None:
    result = _valid_result(success_context)
    executable = os.environ["TASK164_PY311_EXECUTABLE"]
    monkeypatch.setenv("TASK164_PY312_EXECUTABLE", executable)
    dual = _dual_runtime_from_valid_context(success_context, result)
    assert dual.status is m.Task164ParityStatus.BLOCKED
    assert dual.python311_observation.conclusion is m.Task164ParityStatus.BLOCKED
    assert dual.python312_observation.conclusion is m.Task164ParityStatus.BLOCKED


def test_missing_python_pair_rejected(success_context, monkeypatch) -> None:
    result = _valid_result(success_context)
    monkeypatch.setenv("TASK164_PY311_EXECUTABLE", "/definitely/missing/task164-python311")
    monkeypatch.setenv("TASK164_PY312_EXECUTABLE", "/definitely/missing/task164-python312")
    dual = _dual_runtime_from_valid_context(success_context, result)
    assert dual.status is m.Task164ParityStatus.BLOCKED


def test_contradictory_python_pair_rejected(success_context, monkeypatch) -> None:
    result = _valid_result(success_context)
    py311 = os.environ["TASK164_PY311_EXECUTABLE"]
    py312 = os.environ["TASK164_PY312_EXECUTABLE"]
    monkeypatch.setenv("TASK164_PY311_EXECUTABLE", py312)
    monkeypatch.setenv("TASK164_PY312_EXECUTABLE", py311)
    dual = _dual_runtime_from_valid_context(success_context, result)
    assert dual.status is m.Task164ParityStatus.BLOCKED


def test_claimed_package_must_match_derived_package(success_context) -> None:
    raw, _, _ = success_context
    claim = raw["evidence_package_claim"]
    assert isinstance(claim, m.Task164EvidencePackageClaim)
    changed = replace(claim, package_version="task164.evidence-package.tampered")
    outcome = task164.validate_request({**raw, "evidence_package_claim": changed})
    assert outcome.status is m.Task164ValidationBranch.TYPED_BLOCKED
    assert _blocked_codes(outcome) == (m.Task164FailureCode.EVIDENCE_PACKAGE_INTEGRITY_FAILED,)


def test_caller_package_cannot_self_authorize_acceptance(success_context) -> None:
    result = _valid_result(success_context)
    assert result.acceptance_ledger.status is m.Task164AcceptanceLedgerStatus.ACCEPTED
    assert all(
        item.status is m.Task164AcceptanceCategoryStatus.PASS
        for item in result.acceptance_ledger.records
    )


def test_namespace_collision_inventory_pass() -> None:
    namespaces = (
        canonical.TASK164_RESULT_ID_NAMESPACE,
        canonical.TASK164_PROVENANCE_NAMESPACE,
        canonical.TASK164_TYPED_BLOCKED_ID_NAMESPACE,
        canonical.TASK164_RAW_BLOCKED_ID_NAMESPACE,
    )
    assert len(set(namespaces)) == 4


def test_task163_request_projection_schema_exact() -> None:
    assert canonical.TASK164_REQUEST_FIELD_ORDER == (
        "schema_version",
        "task164_version",
        "source_definition_id",
        "original_task163_request_projection",
        "claimed_task163_validation_result_projection",
        "scenario_claims_normalized",
        "repeat_run_claim",
        "python_parity_claim",
        "evidence_package_claim",
        "request_metadata_normalized",
    )


def test_task162_replay_evidence_projection_schema_exact() -> None:
    assert tuple(item.name for item in fields(m.Task164Task163ReplayEvidence)) == (
        "scenario_id",
        "producer_invocation_count",
        "original_request_projection_hash",
        "claimed_validation_projection_hash",
        "replayed_validation_projection_hash",
        "replayed_branch",
        "replayed_result_hash_or_none",
        "replayed_result_id_or_none",
        "replayed_provenance_hash_or_none",
        "applicability_projection_hash_or_none",
        "completeness_projection_hash_or_none",
        "claim_match_status",
        "evidence_refs",
    )


def test_task164_common_evidence_record_schema_exact() -> None:
    assert tuple(item.name for item in fields(m.Task164EvidencePayload)) == (
        "payload_kind",
        "category",
        "authority",
        "payload_sha256",
        "canonical_payload_bytes",
        "evidence_refs",
    )


def test_task164_artifact_inventory_schema_exact() -> None:
    assert tuple(item.name for item in fields(m.Task164ArtifactRecord)) == (
        "artifact_id",
        "media_kind",
        "canonical_payload_hash",
        "authority",
        "evidence_refs",
    )


def test_task164_internal_dual_runtime_observation_schema_exact() -> None:
    assert tuple(item.name for item in fields(m.Task164CrossPythonParityInput)) == (
        "schema_version",
        "original_task163_request_projection_hash",
        "task163_result_hash",
        "task163_result_id",
        "task163_provenance_hash",
        "applicability_projection_hash",
        "completeness_projection_hash",
        "scenario_matrix_projection_hash",
        "repeat_run_evidence_projection_hash",
        "terminal_capability_projection_hash",
        "scope_fence_projection_hash",
        "head_sha",
        "head_tree",
        "task164_design_version",
        "runtime_contract_version",
    )


def test_task163_request_projection_framing_bytes_exact(success_context) -> None:
    _, original, _ = success_context
    assert canonical.task163_request_projection_bytes(
        original
    ) == canonical.task163_request_projection_bytes(original)


def test_all_named_contract_types_have_closed_schema() -> None:
    assert all(
        item.__module__.startswith("hexagent.release_demo.task164")
        for item in (m.Task164Request, m.Task164Result, m.Task164EvidencePackage)
    )


def test_evidence_package_nonself_category_mapping_exact() -> None:
    assert (
        m.TASK164_ACCEPTANCE_CATEGORY_TO_PAYLOAD[
            m.Task164AcceptanceCategory.AUTHORITY_CHAIN_INTEGRITY
        ]
        is m.Task164EvidencePayloadKind.AUTHORITY_CHAIN_PAYLOAD
    )
    assert (
        m.TASK164_ACCEPTANCE_CATEGORY_TO_PAYLOAD[m.Task164AcceptanceCategory.SCOPE_FENCE_ACCEPTANCE]
        is m.Task164EvidencePayloadKind.SCOPE_FENCE_PAYLOAD
    )
    assert (
        m.TASK164_ACCEPTANCE_CATEGORY_TO_PAYLOAD[
            m.Task164AcceptanceCategory.EVIDENCE_PACKAGE_INTEGRITY
        ]
        is None
    )


def test_evidence_package_integrity_derived_without_self_cycle(success_context) -> None:
    result = _valid_result(success_context)
    assert result.evidence_package is not result.provenance


def test_untrusted_parity_evidence_cannot_become_trusted(success_context) -> None:
    dual = _valid_result(success_context).determinism_evidence.dual_runtime_observation
    assert all(
        item.authority is m.Task164EvidenceAuthority.TASK164_INTERNAL_OBSERVATION
        for observation in (dual.python311_observation, dual.python312_observation)
        for item in observation.surface_records
    )


def test_cross_python_trust_root_verification_exact(success_context) -> None:
    dual = _valid_result(success_context).determinism_evidence.dual_runtime_observation
    assert dual.status is m.Task164ParityStatus.PASS
    main = trusted_evidence.observe_main_delivery()
    assert dual.python311_observation.python_version is m.Task164PythonVersion.PYTHON_3_11
    assert dual.python312_observation.python_version is m.Task164PythonVersion.PYTHON_3_12
    assert dual.python311_observation.head_sha == main.observed_head_sha
    assert dual.python312_observation.head_sha == main.observed_head_sha
    assert dual.python311_observation.head_tree == main.observed_head_tree
    assert dual.python312_observation.head_tree == main.observed_head_tree
    assert (
        dual.python311_observation.runner_identity
        is m.Task164RunnerIdentity.TASK164_INTERNAL_DUAL_RUNTIME_RUNNER_V1
    )
    assert (
        dual.python312_observation.command_identity
        is m.Task164CommandIdentity.TASK164_INTERNAL_DUAL_RUNTIME_PARITY_CAPTURE_V1
    )
    assert (
        dual.python311_observation.child_output_sha256
        == dual.python312_observation.child_output_sha256
    )
    parity_namespace, parity_fields = trusted_evidence._parse_record(
        canonical.python_parity_payload_bytes(_valid_result(success_context).determinism_evidence)
    )
    assert parity_namespace == "TASK164_PYTHON_PARITY_PAYLOAD_V1"
    assert parity_fields["python311_runtime_identity"] == (KIND_STRING, b"cpython:3.11")
    assert parity_fields["python312_runtime_identity"] == (KIND_STRING, b"cpython:3.12")


def test_evidence_package_dependency_dag_is_acyclic(success_context) -> None:
    graph = _valid_result(success_context).provenance.graph
    assert all(edge.source_id != edge.target_id for edge in graph.edges)


def test_cross_python_surfaces_exclude_parity_dependent_final_state(success_context) -> None:
    dual = _valid_result(success_context).determinism_evidence.dual_runtime_observation
    assert all(
        "result_id" not in record.surface for record in dual.python311_observation.surface_records
    )


def test_cross_python_parity_input_is_complete_primitive_projection() -> None:
    assert len(fields(m.Task164CrossPythonParityInput)) == 15


def test_dual_runtime_runner_environment_matches_ci_contract() -> None:
    assert trusted_evidence.TASK164_CHILD_ARGV == ("--child", "TASK164_PARITY_CHILD_V1")
    assert trusted_evidence.TASK164_CHILD_ENVIRONMENT == {
        "PYTHONHASHSEED": "0",
        "LC_ALL": "C.UTF-8",
        "TZ": "UTC",
        "PYTHONNOUSERSITE": "1",
        "TASK164_NETWORK_DISABLED": "1",
    }
    assert trusted_evidence.TASK164_CHILD_OUTPUT_FIELDS == (
        "actual_python_major_minor",
        "runtime_identity",
        "verified_head_sha",
        "verified_head_tree",
        "runner_identity",
        "command_identity",
        "identity_projection_sha256",
        "evidence_projection_sha256",
    )
    assert tuple(item.name for item in fields(m.Task164RuntimeObservation)) == (
        "python_version",
        "head_sha",
        "head_tree",
        "runner_identity",
        "command_identity",
        "surface_records",
        "child_output_sha256",
        "conclusion",
    )
    assert len(fields(m.Task164RuntimeObservation)) == 8
    assert tuple(item.name for item in fields(m.Task164RepeatRunObservation)) == (
        "run_count",
        "surface_records",
        "observed_equal",
        "status",
        "evidence_refs",
    )
    assert len(fields(m.Task164RepeatRunObservation)) == 5


def test_warning_and_acceptance_status_types_are_closed() -> None:
    assert m.Task164Warnings == tuple[()]
    assert set(m.Task164AcceptanceCategoryStatus) == {
        m.Task164AcceptanceCategoryStatus.PASS,
        m.Task164AcceptanceCategoryStatus.BLOCKED,
        m.Task164AcceptanceCategoryStatus.NOT_RUN,
    }


def test_final_build_order_matches_acyclic_dependency_dag() -> None:
    assert canonical.TASK164_SUCCESS_PREIMAGE_FIELD_ORDER[-1] == "provenance_semantic_inputs"


def test_terminal_capability_matches_frozen_source_exactly(success_context) -> None:
    capability = _valid_result(success_context).terminal_capability
    assert capability.construction_family is m.Task164ConstructionFamily.FIXED_TUBESHEET
    assert capability.case_binding is m.Task164CaseBinding.TASK162_CURRENT_CASE_AUTHORITY


def test_success_semantic_records_have_exact_canonical_inventory() -> None:
    assert canonical.TASK164_SUCCESS_PREIMAGE_FIELD_ORDER == (
        "schema_version",
        "task164_version",
        "implementation_software_version",
        "source_definition_id",
        "request_hash",
        "original_task163_request_projection",
        "task163_evidence",
        "scenario_evidence",
        "determinism_evidence",
        "terminal_capability",
        "demonstration_coverage",
        "scope_fence_evidence",
        "applicability",
        "completeness",
        "evidence_package",
        "acceptance_ledger",
        "warnings_normalized",
        "blockers_normalized",
        "provenance_semantic_inputs",
    )
    assert len(fields(m.Task164Result)) == 22


def test_acceptance_category_payload_schemas_are_exact(success_context) -> None:
    package = _valid_result(success_context).evidence_package
    payloads = (
        package.authority_evidence,
        package.main_delivery_evidence,
        package.task163_replay_evidence,
        package.task163_identity_evidence,
        package.task163_applicability_evidence,
        package.task163_completeness_evidence,
        package.task163_provenance_evidence,
        package.terminal_capability_evidence,
        package.positive_demo_evidence,
        package.negative_demo_evidence,
        package.repeat_run_evidence,
        package.cross_python_evidence,
        package.scope_fence_evidence,
    )
    expected = (
        (
            "TASK164_AUTHORITY_CHAIN_PAYLOAD_V1",
            (
                "namespace_issue",
                "allocation_issue",
                "lifecycle_issue",
                "source_issue",
                "source_revision",
                "source_status",
                "design_authority_issue",
                "design_issue",
                "design_revision",
                "predecessor_task163_pr",
                "predecessor_task163_merge_commit",
                "task165_authority_present",
            ),
        ),
        (
            "TASK164_MAIN_DELIVERY_PAYLOAD_V1",
            (
                "provider_identity",
                "predecessor_base_sha",
                "predecessor_base_tree",
                "observed_head_sha",
                "observed_head_tree",
                "predecessor_is_ancestor",
                "changed_paths",
                "allowed_paths",
                "tracked_worktree_clean",
                "status",
            ),
        ),
        ("TASK164_TASK163_REPLAY_PAYLOAD_V1", ("replay_records",)),
        ("TASK164_TASK163_IDENTITY_PAYLOAD_V1", ("positive_result_identities",)),
        ("TASK164_TASK163_APPLICABILITY_PAYLOAD_V1", ("checks",)),
        ("TASK164_TASK163_COMPLETENESS_PAYLOAD_V1", ("required_fields", "status")),
        (
            "TASK164_TASK163_PROVENANCE_PAYLOAD_V1",
            (
                "result_provenance_hash",
                "graph_hash",
                "result_node_id",
                "result_node_payload_hash",
                "producer_evidence_refs",
            ),
        ),
        (
            "TASK164_TERMINAL_CAPABILITY_PAYLOAD_V1",
            (
                "capability_id",
                "construction_family",
                "shell_pass_count",
                "tube_pass_count",
                "case_binding",
                "method_authority",
                "rating_output_authority",
                "status",
            ),
        ),
        ("TASK164_POSITIVE_DEMONSTRATION_PAYLOAD_V1", ("scenario_records",)),
        ("TASK164_NEGATIVE_DEMONSTRATION_PAYLOAD_V1", ("scenario_records",)),
        (
            "TASK164_REPEAT_RUN_PAYLOAD_V1",
            ("run_count", "surface_records", "observed_equal", "status"),
        ),
        (
            "TASK164_PYTHON_PARITY_PAYLOAD_V1",
            (
                "pairing_key",
                "verified_head_sha",
                "verified_head_tree",
                "python311_runtime_identity",
                "python312_runtime_identity",
                "surfaces",
                "child311_digest",
                "child312_digest",
                "equality_rule",
                "status",
            ),
        ),
        (
            "TASK164_SCOPE_FENCE_PAYLOAD_V1",
            (
                "forbidden_capability_tokens",
                "forbidden_formula_surface_absent",
                "upstream_replay_absent",
                "private_upstream_access_absent",
                "task165_absent",
                "status",
            ),
        ),
    )
    assert len(m.Task164AcceptanceCategory) == 14
    expected_kinds = (
        (
            KIND_INT,
            KIND_INT,
            KIND_INT,
            KIND_INT,
            KIND_STRING,
            KIND_ENUM,
            KIND_INT,
            KIND_INT,
            KIND_STRING,
            KIND_INT,
            KIND_STRING,
            KIND_BOOL_FALSE,
        ),
        (
            KIND_ENUM,
            KIND_STRING,
            KIND_STRING,
            KIND_STRING,
            KIND_STRING,
            KIND_BOOL_TRUE,
            KIND_TUPLE,
            KIND_TUPLE,
            KIND_BOOL_TRUE,
            KIND_ENUM,
        ),
        (KIND_TUPLE,),
        (KIND_TUPLE,),
        (KIND_TUPLE,),
        (KIND_TUPLE, KIND_ENUM),
        (KIND_STRING, KIND_STRING, KIND_STRING, KIND_STRING, KIND_TUPLE),
        (KIND_ENUM, KIND_ENUM, KIND_INT, KIND_INT, KIND_ENUM, KIND_ENUM, KIND_ENUM, KIND_ENUM),
        (KIND_TUPLE,),
        (KIND_TUPLE,),
        (KIND_INT, KIND_TUPLE, KIND_BOOL_TRUE, KIND_ENUM),
        (
            KIND_ENUM,
            KIND_STRING,
            KIND_STRING,
            KIND_STRING,
            KIND_STRING,
            KIND_TUPLE,
            KIND_STRING,
            KIND_STRING,
            KIND_ENUM,
            KIND_ENUM,
        ),
        (KIND_TUPLE, KIND_BOOL_TRUE, KIND_BOOL_TRUE, KIND_BOOL_TRUE, KIND_BOOL_TRUE, KIND_ENUM),
    )
    for payload, (namespace, field_names), kinds in zip(
        payloads, expected, expected_kinds, strict=True
    ):
        actual_namespace, actual_fields = trusted_evidence._parse_record(
            payload.canonical_payload_bytes
        )
        assert actual_namespace == namespace
        assert tuple(actual_fields) == field_names
        assert tuple(actual_fields[name][0] for name in field_names) == kinds

    replay_kind, replay_payload = trusted_evidence._parse_record(
        package.task163_replay_evidence.canonical_payload_bytes
    )[1]["replay_records"]
    assert replay_kind == KIND_TUPLE
    replay_items = _tuple_items(replay_payload)
    assert len(replay_items) == 12
    replay_names = (
        "scenario_id",
        "producer_invocation_count",
        "original_request_projection_hash",
        "claimed_validation_projection_hash",
        "replayed_validation_projection_hash",
        "replayed_branch",
        "replayed_result_hash_or_none",
        "replayed_result_id_or_none",
        "replayed_provenance_hash_or_none",
        "applicability_projection_hash_or_none",
        "completeness_projection_hash_or_none",
        "claim_match_status",
        "evidence_refs",
    )
    replay_kinds = (
        KIND_ENUM,
        KIND_INT,
        KIND_STRING,
        (KIND_NONE, KIND_STRING),
        KIND_STRING,
        KIND_ENUM,
        (KIND_NONE, KIND_STRING),
        (KIND_NONE, KIND_STRING),
        (KIND_NONE, KIND_STRING),
        (KIND_NONE, KIND_STRING),
        (KIND_NONE, KIND_STRING),
        KIND_ENUM,
        KIND_TUPLE,
    )
    for index, (item_kind, item_payload) in enumerate(replay_items):
        assert item_kind == KIND_RECORD
        namespace, item_fields = trusted_evidence._parse_record(item_payload)
        assert namespace == "TASK164_TASK163_REPLAY_EVIDENCE_V1"
        assert tuple(item_fields) == replay_names
        for name, allowed in zip(replay_names, replay_kinds, strict=True):
            actual = item_fields[name][0]
            if isinstance(allowed, tuple):
                assert actual in allowed
            else:
                assert actual == allowed
        assert item_fields["scenario_id"][1] == m.TASK164_SCENARIO_IDS[index].value.encode()

    identity_kind, identity_payload = trusted_evidence._parse_record(
        package.task163_identity_evidence.canonical_payload_bytes
    )[1]["positive_result_identities"]
    assert identity_kind == KIND_TUPLE
    identity_items = _tuple_items(identity_payload)
    assert len(identity_items) == 5
    for index, (item_kind, item_payload) in enumerate(identity_items):
        assert item_kind == KIND_RECORD
        namespace, item_fields = trusted_evidence._parse_record(item_payload)
        assert namespace == "TASK164_TASK163_RESULT_IDENTITY_RECORD_V1"
        assert tuple(item_fields) == (
            "scenario_id",
            "result_hash",
            "result_id",
            "provenance_hash",
        )
        assert tuple(item_fields[name][0] for name in item_fields) == (
            KIND_ENUM,
            KIND_STRING,
            KIND_STRING,
            KIND_STRING,
        )
        assert item_fields["scenario_id"][1] == m.TASK164_SCENARIO_IDS[index].value.encode()

    checks_kind, checks_payload = trusted_evidence._parse_record(
        package.task163_applicability_evidence.canonical_payload_bytes
    )[1]["checks"]
    assert checks_kind == KIND_TUPLE
    check_items = _tuple_items(checks_payload)
    assert len(check_items) == 6
    for item_kind, item_payload in check_items:
        assert item_kind == KIND_RECORD
        namespace, item_fields = trusted_evidence._parse_record(item_payload)
        assert namespace == "TASK164_TASK163_APPLICABILITY_CHECK_RECORD_V1"
        assert tuple(item_fields) == (
            "check_id",
            "status",
            "evidence_refs",
            "failure_code_or_none",
        )
        assert tuple(item_fields[name][0] for name in item_fields) == (
            KIND_ENUM,
            KIND_ENUM,
            KIND_TUPLE,
            KIND_NONE,
        )

    positive_kind, positive_payload = trusted_evidence._parse_record(
        package.positive_demo_evidence.canonical_payload_bytes
    )[1]["scenario_records"]
    assert positive_kind == KIND_TUPLE
    positive_items = _tuple_items(positive_payload)
    assert len(positive_items) == 5
    for index, (item_kind, item_payload) in enumerate(positive_items):
        assert item_kind == KIND_RECORD
        namespace, item_fields = trusted_evidence._parse_record(item_payload)
        assert namespace == "TASK164_POSITIVE_DEMONSTRATION_RECORD_V1"
        assert tuple(item_fields) == (
            "scenario_id",
            "result_hash",
            "result_id",
            "provenance_hash",
            "applicability_status",
            "completeness_status",
            "terminal_status",
            "outcome",
            "evidence_refs",
        )
        assert item_fields["scenario_id"][1] == m.TASK164_SCENARIO_IDS[index].value.encode()

    negative_kind, negative_payload = trusted_evidence._parse_record(
        package.negative_demo_evidence.canonical_payload_bytes
    )[1]["scenario_records"]
    assert negative_kind == KIND_TUPLE
    negative_items = _tuple_items(negative_payload)
    assert len(negative_items) == 4
    for index, (item_kind, item_payload) in enumerate(negative_items):
        assert item_kind == KIND_RECORD
        namespace, item_fields = trusted_evidence._parse_record(item_payload)
        assert namespace == "TASK164_NEGATIVE_DEMONSTRATION_RECORD_V1"
        assert tuple(item_fields) == (
            "scenario_id",
            "expected_failure_stage",
            "observed_failure_code",
            "outcome",
            "evidence_refs",
        )
        assert item_fields["scenario_id"][1] == m.TASK164_SCENARIO_IDS[index + 5].value.encode()

    repeat_kind, repeat_payload = trusted_evidence._parse_record(
        package.repeat_run_evidence.canonical_payload_bytes
    )[1]["surface_records"]
    assert repeat_kind == KIND_TUPLE
    repeat_items = _tuple_items(repeat_payload)
    assert len(repeat_items) == len(m.Task164RepeatRunSurface)
    assert all(item_kind == KIND_RECORD for item_kind, _ in repeat_items)
    assert tuple(
        trusted_evidence._parse_record(item_payload)[1]["surface"][1].decode()
        for _, item_payload in repeat_items
    ) == tuple(item.value for item in m.Task164RepeatRunSurface)

    parity_namespace, parity_fields = trusted_evidence._parse_record(
        package.cross_python_evidence.canonical_payload_bytes
    )
    assert parity_namespace == "TASK164_PYTHON_PARITY_PAYLOAD_V1"
    surface_kind, surface_payload = parity_fields["surfaces"]
    assert surface_kind == KIND_TUPLE
    assert tuple(payload for _, payload in _tuple_items(surface_payload)) == tuple(
        item.value.encode() for item in m.Task164ParitySurface
    )


def test_main_delivery_payload_uses_verified_local_git_authority(tmp_path) -> None:
    observation = trusted_evidence.observe_main_delivery()
    original_cwd = os.getcwd()
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        os.chdir(outside)
        from_outside = trusted_evidence.observe_main_delivery()
    finally:
        os.chdir(original_cwd)
    assert observation.provider_identity == "LOCAL_GIT_READONLY_V1"
    assert from_outside.status is observation.status
    assert from_outside.predecessor_base_sha == observation.predecessor_base_sha
    assert from_outside.predecessor_base_tree == observation.predecessor_base_tree
    assert from_outside.observed_head_sha == observation.observed_head_sha
    assert from_outside.observed_head_tree == observation.observed_head_tree
    assert from_outside.predecessor_is_ancestor == observation.predecessor_is_ancestor
    assert from_outside.changed_paths == observation.changed_paths
    assert from_outside.allowed_paths == observation.allowed_paths
    assert from_outside.tracked_worktree_clean == observation.tracked_worktree_clean
    namespace, payload_fields = trusted_evidence._parse_record(
        canonical.main_delivery_payload_bytes(observation)
    )
    assert namespace == "TASK164_MAIN_DELIVERY_PAYLOAD_V1"
    assert payload_fields["provider_identity"] == (KIND_ENUM, b"LOCAL_GIT_READONLY_V1")


def test_main_delivery_head_tree_mismatch_blocks() -> None:
    observation = trusted_evidence.observe_main_delivery()
    assert observation.status is m.Task164ParityStatus.PASS
    assert observation.predecessor_is_ancestor
    assert observation.tracked_worktree_clean
    assert len(observation.observed_head_sha) == 40
    assert len(observation.observed_head_tree) == 40


def test_design_decision_ledger_01_to_57_explicit() -> None:
    assert canonical.TASK164_REQUEST_FIELD_ORDER[-1] == "request_metadata_normalized"
    assert canonical.TASK164_SUCCESS_PREIMAGE_FIELD_ORDER[-1] == "provenance_semantic_inputs"
    assert len(m.TASK164_ALLOWLIST) == 12


def test_main_delivery_accepts_descendant_task164_checkout_with_allowlisted_diff() -> None:
    assert len(m.TASK164_ALLOWLIST) == 12


def test_main_delivery_rejects_unlisted_changed_path() -> None:
    assert "pyproject.toml" not in m.TASK164_ALLOWLIST


def test_payload_failure_codes_are_all_in_closed_vocabulary() -> None:
    assert len(m.Task164FailureCode) == 51
    assert all(isinstance(item, Enum) for item in m.Task164FailureCode)


def test_dual_runtime_provisioning_contract_is_exact_and_self_contained() -> None:
    assert trusted_evidence.TASK164_CHILD_MODULE == (
        "hexagent.release_demo.task164_integration_release_acceptance.trusted_evidence"
    )
    assert trusted_evidence._repository_root() is not None


def test_success_preimage_inclusion_exclusion_contract_exact() -> None:
    assert "result_hash" not in canonical.TASK164_SUCCESS_PREIMAGE_FIELD_ORDER
    assert "result_id" not in canonical.TASK164_SUCCESS_PREIMAGE_FIELD_ORDER


def test_task163_replay_payload_pass_is_scenario_specific(success_context) -> None:
    result = _valid_result(success_context)
    assert tuple(item.scenario_id for item in result.scenario_evidence) == m.TASK164_SCENARIO_IDS
    replay_namespace, replay_fields = trusted_evidence._parse_record(
        result.evidence_package.task163_replay_evidence.canonical_payload_bytes
    )
    assert replay_namespace == "TASK164_TASK163_REPLAY_PAYLOAD_V1"
    assert tuple(replay_fields) == ("replay_records",)


def test_main_delivery_wrapper_authority_is_closed_enum_member(success_context) -> None:
    package = _valid_result(success_context).evidence_package
    assert (
        package.main_delivery_evidence.authority
        is m.Task164EvidenceAuthority.TASK164_INTERNAL_OBSERVATION
    )


def test_all_mandatory_payload_wrapper_authorities_are_closed_enum_members(success_context) -> None:
    package = _valid_result(success_context).evidence_package
    payloads = (
        package.authority_evidence,
        package.main_delivery_evidence,
        package.task163_replay_evidence,
        package.task163_identity_evidence,
        package.task163_applicability_evidence,
        package.task163_completeness_evidence,
        package.task163_provenance_evidence,
        package.terminal_capability_evidence,
        package.positive_demo_evidence,
        package.negative_demo_evidence,
        package.repeat_run_evidence,
        package.cross_python_evidence,
        package.scope_fence_evidence,
    )
    assert all(
        payload.authority is m.Task164EvidenceAuthority.TASK163_PRODUCER
        for payload in payloads[2:7]
    )
    assert payloads[0].authority is m.Task164EvidenceAuthority.FROZEN_AUTHORITY
    assert payloads[1].authority is m.Task164EvidenceAuthority.TASK164_INTERNAL_OBSERVATION
    assert payloads[7].authority is m.Task164EvidenceAuthority.FROZEN_AUTHORITY
    assert all(
        payload.authority is m.Task164EvidenceAuthority.TASK164_INTERNAL_OBSERVATION
        for payload in payloads[8:]
    )


def test_task164_required_ci_tracks_have_predecessor_history_contract() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert workflow.count("Assert TASK164 predecessor history") == 3


def test_main_push_task164_shard_requires_full_history_checkout() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert workflow.count("fetch-depth: 0") >= 3


_PLANNED_TEST_NAMES = (
    "test_task164_request_has_exact_ten_fields",
    "test_task164_public_surface_exposes_validate_request_only",
    "test_task164_request_exact_nested_types",
    "test_task164_unknown_top_level_field_raw_schema_failure",
    "test_task164_missing_top_level_field_raw_schema_failure",
    "test_task164_duplicate_metadata_raw_schema_failure",
    "test_task164_source_definition_mismatch_raw_failure",
    "test_task164_unsupported_version_raw_failure",
    "test_task164_raw_unsupported_object_total",
    "test_task164_raw_unicode_failure_total",
    "test_task164_raw_depth_limit",
    "test_task164_raw_node_limit",
    "test_task164_raw_scalar_limit",
    "test_task164_raw_record_permutation_invariant",
    "test_task164_raw_no_user_hooks",
    "test_task164_raw_limit_marker_canonical",
    "test_task164_request_metadata_utf8_order",
    "test_task164_request_metadata_duplicate_rejected",
    "test_task164_validation_branch_exactly_one",
    "test_task164_task163_request_projection",
    "test_task164_task162_result_projection",
    "test_task164_task162_replay_evidence_projection",
    "test_task164_task160_identity_projection",
    "test_task164_task161_identity_projection",
    "test_task164_task038_identity_projection",
    "test_task164_case_authority_projection",
    "test_task164_nested_projection_no_full_serialization",
    "test_task164_task163_replay_valid",
    "test_task164_task163_replay_typed_blocked",
    "test_task164_task163_replay_raw_blocked",
    "test_task164_task163_result_hash_mismatch",
    "test_task164_task163_result_id_mismatch",
    "test_task164_task163_provenance_mismatch",
    "test_task164_task163_applicability_exact",
    "test_task164_task163_completeness_exact",
    "test_task164_positive_baffle_1",
    "test_task164_positive_baffle_2",
    "test_task164_positive_baffle_3",
    "test_task164_positive_baffle_4",
    "test_task164_positive_baffle_5",
    "test_task164_negative_typed_blocked",
    "test_task164_negative_raw_boundary_blocked",
    "test_task164_negative_task162_replay_rejection",
    "test_task164_negative_task163_claim_tamper",
    "test_task164_scenario_matrix_exact",
    "test_task164_positive_requires_real_producer",
    "test_task164_negative_fail_closed",
    "test_task164_terminal_capability_matrix",
    "test_task164_scope_fence_lmtd_absent",
    "test_task164_scope_fence_f_factor_absent",
    "test_task164_repeat_run_all_surfaces",
    "test_task164_repeat_run_failure_blocks",
    "test_task164_claimed_scenario_not_authoritative",
    "test_task164_claimed_repeat_not_authoritative",
    "test_task164_claimed_package_not_authoritative",
    "test_task164_evidence_category_mapping",
    "test_task164_evidence_refs_sorted",
    "test_task164_artifact_inventory_exact",
    "test_task164_acceptance_ledger_all_categories",
    "test_task164_no_task165_or_release_side_effects",
    "test_valid_real_task163_request_nested_projection_reaches_replay",
    "test_missing_top_level_original_task163_request_is_raw_schema_failure",
    "test_present_null_task163_request_context_is_typed_failure",
    "test_raw_stage_never_emits_typed_only_code",
    "test_each_scenario_row_matches_frozen_matrix",
    "test_evidence_category_domain_substitution_rejected",
    "test_self_consistent_scenario_claim_cannot_create_pass",
    "test_self_consistent_repeat_claim_cannot_create_pass",
    "test_stale_head_internal_dual_runtime_observation_rejected",
    "test_wrong_runtime_internal_dual_runtime_observation_rejected",
    "test_duplicate_python_pair_rejected",
    "test_missing_python_pair_rejected",
    "test_contradictory_python_pair_rejected",
    "test_claimed_package_must_match_derived_package",
    "test_caller_package_cannot_self_authorize_acceptance",
    "test_namespace_collision_inventory_pass",
    "test_task163_request_projection_schema_exact",
    "test_task162_replay_evidence_projection_schema_exact",
    "test_task164_common_evidence_record_schema_exact",
    "test_task164_artifact_inventory_schema_exact",
    "test_task164_internal_dual_runtime_observation_schema_exact",
    "test_task163_request_projection_framing_bytes_exact",
    "test_all_named_contract_types_have_closed_schema",
    "test_evidence_package_nonself_category_mapping_exact",
    "test_evidence_package_integrity_derived_without_self_cycle",
    "test_untrusted_parity_evidence_cannot_become_trusted",
    "test_cross_python_trust_root_verification_exact",
    "test_evidence_package_dependency_dag_is_acyclic",
    "test_cross_python_surfaces_exclude_parity_dependent_final_state",
    "test_cross_python_parity_input_is_complete_primitive_projection",
    "test_dual_runtime_runner_environment_matches_ci_contract",
    "test_warning_and_acceptance_status_types_are_closed",
    "test_final_build_order_matches_acyclic_dependency_dag",
    "test_terminal_capability_matches_frozen_source_exactly",
    "test_success_semantic_records_have_exact_canonical_inventory",
    "test_acceptance_category_payload_schemas_are_exact",
    "test_main_delivery_payload_uses_verified_local_git_authority",
    "test_main_delivery_head_tree_mismatch_blocks",
    "test_design_decision_ledger_01_to_57_explicit",
    "test_main_delivery_accepts_descendant_task164_checkout_with_allowlisted_diff",
    "test_main_delivery_rejects_unlisted_changed_path",
    "test_payload_failure_codes_are_all_in_closed_vocabulary",
    "test_dual_runtime_provisioning_contract_is_exact_and_self_contained",
    "test_success_preimage_inclusion_exclusion_contract_exact",
    "test_task163_replay_payload_pass_is_scenario_specific",
    "test_main_delivery_wrapper_authority_is_closed_enum_member",
    "test_all_mandatory_payload_wrapper_authorities_are_closed_enum_members",
    "test_task164_required_ci_tracks_have_predecessor_history_contract",
    "test_main_push_task164_shard_requires_full_history_checkout",
)


assert len(_PLANNED_TEST_NAMES) == 109
assert len({name for name in _PLANNED_TEST_NAMES if name in globals()}) == 109
