"""TASK160 canonical projections and deterministic identities.

All byte framing primitives are imported from the existing TASK025
implementation.  This module only supplies task-local field projections;
it does not introduce another framing protocol.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid5

from hexagent.exchangers.shell_tube.tube_side.canonical import (
    KIND_BOOL_FALSE,
    KIND_BOOL_TRUE,
    KIND_DECIMAL,
    KIND_ENUM,
    KIND_INT,
    KIND_NONE,
    KIND_RECORD,
    KIND_STRING,
    KIND_TUPLE,
    frame_record,
    frame_tuple,
    frame_value,
    sha256_hex_from_framed_bytes,
)

from .models import (
    ApplicabilityCheck,
    ApplicabilityLedger,
    CapacityRatedStream,
    CompletenessCheck,
    CompletenessLedger,
    PropertyEvaluationContext,
    PropertySnapshotIdentity,
    RatingStreamInput,
    RawProjectionNode,
    RoleResolvedRatingStream,
    Task160AdapterEvidence,
    Task160Blocker,
    Task160EnvelopeAuthority,
    Task160PropertySnapshot,
    Task160ProvenanceInputs,
    Task160RawRequestProjection,
    Task160Request,
    Task160Result,
    ValidatedRatingStreamState,
)

TASK160_SOURCE_DEFINITION_ID = "TASK160-SOURCE-DEFINITION-R1-ISSUE-221"
TASK160_RESULT_ID_NAMESPACE = "a1600000-0000-5000-8000-000000000160"
SUCCESS_ID_PREFIX = "task160-result-v1::"
TYPED_BLOCKED_ID_PREFIX = "task160-blocked-v1::"
RAW_BLOCKED_ID_PREFIX = "task160-raw-blocked-v1::"

TASK160_DETAIL_PAIR_DOMAIN = "task160.detail-pair.v1"
TASK160_RAW_PROJECTION_DOMAIN = "TASK160_RAW_REQUEST_PROJECTION_V1"
TASK160_RAW_PROJECTION_NODE_DOMAIN = "TASK160_RAW_PROJECTION_NODE_V1"
TASK160_RAW_REQUEST_PROJECTION_SCHEMA_VERSION = "task160.raw-projection.v1"

REQUEST_HASH_DOMAIN = "TASK160_REQUEST_HASH_V1"
SUCCESS_HASH_DOMAIN = "TASK160_SUCCESS_RESULT_HASH_V1"
TYPED_BLOCKED_HASH_DOMAIN = "TASK160_TYPED_BLOCKED_RESULT_HASH_V1"
RAW_BLOCKED_HASH_DOMAIN = "TASK160_RAW_BLOCKED_RESULT_HASH_V1"

DETAIL_PAIR_FIELDS = ("key", "value")


def _enum_payload(value: Enum | str) -> bytes:
    literal = value.value if isinstance(value, Enum) else value
    return str(literal).encode("ascii")


def _string(value: str) -> bytes:
    return frame_value(KIND_STRING, value.encode("utf-8"))


def _enum(value: Enum | str) -> bytes:
    return frame_value(KIND_ENUM, _enum_payload(value))


def _integer(value: int) -> bytes:
    return frame_value(KIND_INT, str(value).encode("ascii"))


def _decimal(value: Decimal) -> bytes:
    return frame_value(KIND_DECIMAL, str(value).encode("ascii"))


def _none() -> bytes:
    return frame_value(KIND_NONE, b"")


def _boolean(value: bool) -> bytes:
    return frame_value(KIND_BOOL_TRUE if value else KIND_BOOL_FALSE, b"")


def _tuple_payload(payloads: Sequence[bytes]) -> bytes:
    # The existing frame_tuple applies FRAME("ITEM", payload) itself.  A
    # record item therefore receives the direct frame_record bytes.
    return frame_tuple(payloads)


def _tuple_strings(values: Iterable[str]) -> bytes:
    return _tuple_payload([_string(value) for value in values])


def _tuple_enums(values: Iterable[Enum | str]) -> bytes:
    return _tuple_payload([_enum(value) for value in values])


def _tuple_records(values: Iterable[bytes]) -> bytes:
    return _tuple_payload(list(values))


def _record_field(name: str, kind: bytes, payload: bytes) -> tuple[str, bytes, bytes]:
    return (name, kind, payload)


def detail_pair_bytes(key: str, value: str) -> bytes:
    return frame_record(
        TASK160_DETAIL_PAIR_DOMAIN,
        (
            _record_field("key", KIND_STRING, key.encode("utf-8")),
            _record_field("value", KIND_STRING, value.encode("utf-8")),
        ),
    )


def _details(values: Iterable[tuple[str, str]]) -> bytes:
    return _tuple_records(detail_pair_bytes(key, value) for key, value in values)


def _property_snapshot_identity_bytes(value: PropertySnapshotIdentity) -> bytes:
    return frame_record(
        "TASK160_PROPERTY_SNAPSHOT_IDENTITY_V1",
        (
            _record_field("scheme", KIND_ENUM, _enum_payload(value.scheme)),
            _record_field("value", KIND_STRING, value.value.encode("utf-8")),
        ),
    )


def property_snapshot_identity_bytes(value: PropertySnapshotIdentity) -> bytes:
    return _property_snapshot_identity_bytes(value)


def _property_context_bytes(value: PropertyEvaluationContext) -> bytes:
    pressure_kind, pressure_payload = (
        (KIND_NONE, b"")
        if value.evaluation_pressure_Pa_absolute is None
        else (KIND_DECIMAL, str(value.evaluation_pressure_Pa_absolute).encode("ascii"))
    )
    return frame_record(
        "TASK160_PROPERTY_EVALUATION_CONTEXT_V1",
        (
            _record_field("evaluation_basis", KIND_ENUM, _enum_payload(value.evaluation_basis)),
            _record_field("query_type", KIND_ENUM, _enum_payload(value.query_type)),
            _record_field(
                "evaluation_temperature_K",
                KIND_DECIMAL,
                str(value.evaluation_temperature_K).encode("ascii"),
            ),
            _record_field("evaluation_pressure_Pa_absolute", pressure_kind, pressure_payload),
            _record_field("context_identity", KIND_STRING, value.context_identity.encode("utf-8")),
        ),
    )


def _property_snapshot_bytes(value: Task160PropertySnapshot) -> bytes:
    return frame_record(
        "TASK160_PROPERTY_SNAPSHOT_V1",
        (
            _record_field(
                "specific_heat_J_kg_K",
                KIND_DECIMAL,
                str(value.specific_heat_J_kg_K).encode("ascii"),
            ),
            _record_field(
                "property_source_identity",
                KIND_STRING,
                value.property_source_identity.encode("utf-8"),
            ),
            _record_field(
                "property_source_version",
                KIND_STRING,
                value.property_source_version.encode("utf-8"),
            ),
            _record_field(
                "property_snapshot_identity",
                KIND_RECORD,
                _property_snapshot_identity_bytes(value.property_snapshot_identity),
            ),
            _record_field(
                "property_evaluation_context",
                KIND_RECORD,
                _property_context_bytes(value.property_evaluation_context),
            ),
        ),
    )


def _provenance_inputs_bytes(value: Task160ProvenanceInputs) -> bytes:
    return frame_record(
        "TASK160_PROVENANCE_INPUTS_V1",
        (
            _record_field("producer_identity", KIND_TUPLE, _tuple_strings(value.producer_identity)),
            _record_field(
                "upstream_identity_hashes",
                KIND_TUPLE,
                _tuple_strings(value.upstream_identity_hashes),
            ),
            _record_field(
                "source_evidence_refs", KIND_TUPLE, _tuple_strings(value.source_evidence_refs)
            ),
            _record_field(
                "adapter_evidence_refs", KIND_TUPLE, _tuple_strings(value.adapter_evidence_refs)
            ),
        ),
    )


def rating_stream_bytes(value: RatingStreamInput) -> bytes:
    pressure_kind, pressure_payload = (
        (KIND_NONE, b"")
        if value.inlet_pressure_Pa_absolute is None
        else (KIND_DECIMAL, str(value.inlet_pressure_Pa_absolute).encode("ascii"))
    )
    return frame_record(
        "TASK160_RATING_STREAM_INPUT_V1",
        (
            _record_field("stream_id", KIND_STRING, value.stream_id.encode("utf-8")),
            _record_field("side_binding", KIND_ENUM, _enum_payload(value.side_binding)),
            _record_field(
                "fluid_or_service_identity",
                KIND_STRING,
                value.fluid_or_service_identity.encode("utf-8"),
            ),
            _record_field("phase_assertion", KIND_ENUM, _enum_payload(value.phase_assertion)),
            _record_field(
                "inlet_temperature_K",
                KIND_DECIMAL,
                str(value.inlet_temperature_K).encode("ascii"),
            ),
            _record_field("inlet_pressure_Pa_absolute", pressure_kind, pressure_payload),
            _record_field(
                "mass_flow_kg_s", KIND_DECIMAL, str(value.mass_flow_kg_s).encode("ascii")
            ),
            _record_field(
                "property_snapshot", KIND_RECORD, _property_snapshot_bytes(value.property_snapshot)
            ),
            _record_field(
                "provenance_inputs", KIND_RECORD, _provenance_inputs_bytes(value.provenance_inputs)
            ),
        ),
    )


def validated_rating_stream_state_bytes(value: ValidatedRatingStreamState) -> bytes:
    return frame_record(
        "TASK160_VALIDATED_RATING_STREAM_STATE_V1",
        (_record_field("input", KIND_RECORD, rating_stream_bytes(value.input)),),
    )


def role_resolved_stream_bytes(value: RoleResolvedRatingStream) -> bytes:
    return frame_record(
        "TASK160_ROLE_RESOLVED_RATING_STREAM_V1",
        (
            _record_field(
                "input_state", KIND_RECORD, validated_rating_stream_state_bytes(value.input_state)
            ),
            _record_field("thermal_role", KIND_ENUM, _enum_payload(value.thermal_role)),
        ),
    )


def capacity_rated_stream_bytes(value: CapacityRatedStream) -> bytes:
    return frame_record(
        "TASK160_CAPACITY_RATED_STREAM_V1",
        (
            _record_field(
                "role_resolved_stream",
                KIND_RECORD,
                role_resolved_stream_bytes(value.role_resolved_stream),
            ),
            _record_field(
                "heat_capacity_rate_W_K",
                KIND_DECIMAL,
                str(value.heat_capacity_rate_W_K).encode("ascii"),
            ),
        ),
    )


def envelope_authority_bytes(value: Task160EnvelopeAuthority) -> bytes:
    return frame_record(
        "TASK160_ENVELOPE_AUTHORITY_V1",
        (
            _record_field(
                "construction_family", KIND_ENUM, _enum_payload(value.construction_family)
            ),
            _record_field(
                "shell_pass_count", KIND_INT, str(value.shell_pass_count).encode("ascii")
            ),
            _record_field("tube_pass_count", KIND_INT, str(value.tube_pass_count).encode("ascii")),
            _record_field(
                "authority_source_identity",
                KIND_STRING,
                value.authority_source_identity.encode("utf-8"),
            ),
            _record_field(
                "authority_source_version",
                KIND_STRING,
                value.authority_source_version.encode("utf-8"),
            ),
            _record_field(
                "authority_identity", KIND_STRING, value.authority_identity.encode("utf-8")
            ),
            _record_field("evidence_refs", KIND_TUPLE, _tuple_strings(value.evidence_refs)),
        ),
    )


def adapter_evidence_bytes(value: Task160AdapterEvidence) -> bytes:
    source_kind, source_payload = (
        (KIND_NONE, b"")
        if value.source_result_identity is None
        else (KIND_STRING, value.source_result_identity.encode("utf-8"))
    )
    return frame_record(
        "TASK160_ADAPTER_EVIDENCE_V1",
        (
            _record_field("adapter_id", KIND_STRING, value.adapter_id.encode("utf-8")),
            _record_field("source_task_id", KIND_STRING, value.source_task_id.encode("utf-8")),
            _record_field("source_result_identity", source_kind, source_payload),
            _record_field("admitted_fields", KIND_TUPLE, _tuple_strings(value.admitted_fields)),
            _record_field("rejected_fields", KIND_TUPLE, _tuple_strings(value.rejected_fields)),
            _record_field(
                "source_evidence_refs", KIND_TUPLE, _tuple_strings(value.source_evidence_refs)
            ),
            _record_field("evidence_hash", KIND_STRING, value.evidence_hash.encode("utf-8")),
        ),
    )


def blocker_bytes(value: Task160Blocker) -> bytes:
    return frame_record(
        "TASK160_BLOCKER_V1",
        (
            _record_field("code", KIND_ENUM, value.code.encode("ascii")),
            _record_field("stage", KIND_ENUM, _enum_payload(value.stage)),
            _record_field("field_path", KIND_STRING, value.field_path.encode("utf-8")),
            _record_field("evidence_refs", KIND_TUPLE, _tuple_strings(value.evidence_refs)),
            _record_field("details", KIND_TUPLE, _details(value.details)),
        ),
    )


def _check_bytes(value: ApplicabilityCheck | CompletenessCheck) -> bytes:
    return frame_record(
        "TASK160_APPLICABILITY_CHECK_V1"
        if hasattr(value.check_id, "name") and str(value.check_id.value).startswith("A")
        else "TASK160_COMPLETENESS_CHECK_V1",
        (
            _record_field("check_id", KIND_ENUM, _enum_payload(value.check_id)),
            _record_field("passed", KIND_BOOL_TRUE if value.passed else KIND_BOOL_FALSE, b""),
            _record_field("blocker_codes", KIND_TUPLE, _tuple_enums(value.blocker_codes)),
            _record_field("evidence_refs", KIND_TUPLE, _tuple_strings(value.evidence_refs)),
            _record_field("details", KIND_TUPLE, _details(value.details)),
        ),
    )


def applicability_ledger_bytes(value: ApplicabilityLedger) -> bytes:
    return frame_record(
        "TASK160_APPLICABILITY_LEDGER_V1",
        (
            _record_field("status", KIND_ENUM, _enum_payload(value.status)),
            _record_field(
                "checks", KIND_TUPLE, _tuple_records(_check_bytes(item) for item in value.checks)
            ),
            _record_field(
                "blockers",
                KIND_TUPLE,
                _tuple_records(blocker_bytes(item) for item in value.blockers),
            ),
        ),
    )


def completeness_ledger_bytes(value: CompletenessLedger) -> bytes:
    return frame_record(
        "TASK160_COMPLETENESS_LEDGER_V1",
        (
            _record_field("status", KIND_ENUM, _enum_payload(value.status)),
            _record_field(
                "checks", KIND_TUPLE, _tuple_records(_check_bytes(item) for item in value.checks)
            ),
            _record_field(
                "blockers",
                KIND_TUPLE,
                _tuple_records(blocker_bytes(item) for item in value.blockers),
            ),
        ),
    )


def _ordered_streams(values: Iterable[RatingStreamInput]) -> tuple[RatingStreamInput, ...]:
    return tuple(
        sorted(
            values,
            key=lambda item: (0 if item.side_binding.value == "TUBE_SIDE" else 1, item.stream_id),
        )
    )


def _ordered_capacity_streams(
    values: Iterable[CapacityRatedStream],
) -> tuple[CapacityRatedStream, ...]:
    return tuple(
        sorted(
            values,
            key=lambda item: (0 if item.side_binding.value == "TUBE_SIDE" else 1, item.stream_id),
        )
    )


def _ordered_adapters(
    values: Iterable[Task160AdapterEvidence],
) -> tuple[Task160AdapterEvidence, ...]:
    return tuple(
        sorted(values, key=lambda item: (item.source_task_id, item.adapter_id, item.evidence_hash))
    )


def request_hash_fields(request: Task160Request) -> tuple[tuple[str, bytes, bytes], ...]:
    streams = _ordered_streams(request.stream_records)
    return (
        _record_field("schema_version", KIND_STRING, request.schema_version.encode("utf-8")),
        _record_field("task160_version", KIND_STRING, request.task160_version.encode("utf-8")),
        _record_field(
            "implementation_software_version",
            KIND_STRING,
            request.implementation_software_version.encode("utf-8"),
        ),
        _record_field(
            "stream_records_normalized_by_side",
            KIND_TUPLE,
            _tuple_records(rating_stream_bytes(item) for item in streams),
        ),
        _record_field(
            "envelope_authority", KIND_RECORD, envelope_authority_bytes(request.envelope_authority)
        ),
        _record_field(
            "adapter_evidence_normalized",
            KIND_TUPLE,
            _tuple_records(
                adapter_evidence_bytes(item) for item in _ordered_adapters(request.adapter_evidence)
            ),
        ),
        _record_field(
            "deferred_capabilities_normalized",
            KIND_TUPLE,
            _tuple_strings(request.deferred_capabilities),
        ),
        _record_field(
            "provenance_inputs", KIND_RECORD, _provenance_inputs_bytes(request.provenance_inputs)
        ),
        _record_field(
            "TASK160_SOURCE_DEFINITION_ID",
            KIND_STRING,
            TASK160_SOURCE_DEFINITION_ID.encode("utf-8"),
        ),
    )


def request_canonical_bytes(request: Task160Request) -> bytes:
    return frame_record(REQUEST_HASH_DOMAIN, request_hash_fields(request))


def request_hash(request: Task160Request) -> str:
    return sha256_hex_from_framed_bytes(request_canonical_bytes(request))


def success_hash_fields(
    *,
    request_hash_value: str,
    stream_records: Iterable[CapacityRatedStream],
    envelope_authority: Task160EnvelopeAuthority,
    adapter_evidence: Iterable[Task160AdapterEvidence],
    deferred_capabilities: Iterable[str],
    c_dot_hot_W_K: Decimal,
    c_dot_cold_W_K: Decimal,
    applicability: ApplicabilityLedger,
    completeness: CompletenessLedger,
    provenance_inputs: Task160ProvenanceInputs,
    schema_version: str,
    task160_version: str,
    implementation_software_version: str,
) -> tuple[tuple[str, bytes, bytes], ...]:
    streams = _ordered_capacity_streams(stream_records)
    return (
        _record_field("schema_version", KIND_STRING, schema_version.encode("utf-8")),
        _record_field("task160_version", KIND_STRING, task160_version.encode("utf-8")),
        _record_field(
            "implementation_software_version",
            KIND_STRING,
            implementation_software_version.encode("utf-8"),
        ),
        _record_field("request_hash", KIND_STRING, request_hash_value.encode("utf-8")),
        _record_field(
            "stream_records_normalized_by_side",
            KIND_TUPLE,
            _tuple_records(capacity_rated_stream_bytes(item) for item in streams),
        ),
        _record_field(
            "envelope_authority", KIND_RECORD, envelope_authority_bytes(envelope_authority)
        ),
        _record_field(
            "adapter_evidence_normalized",
            KIND_TUPLE,
            _tuple_records(
                adapter_evidence_bytes(item) for item in _ordered_adapters(adapter_evidence)
            ),
        ),
        _record_field(
            "deferred_capabilities_normalized", KIND_TUPLE, _tuple_strings(deferred_capabilities)
        ),
        _record_field("c_dot_hot_W_K", KIND_DECIMAL, str(c_dot_hot_W_K).encode("ascii")),
        _record_field("c_dot_cold_W_K", KIND_DECIMAL, str(c_dot_cold_W_K).encode("ascii")),
        _record_field("applicability", KIND_RECORD, applicability_ledger_bytes(applicability)),
        _record_field("completeness", KIND_RECORD, completeness_ledger_bytes(completeness)),
        _record_field("warnings_normalized", KIND_TUPLE, _tuple_payload([])),
        _record_field(
            "provenance_inputs", KIND_RECORD, _provenance_inputs_bytes(provenance_inputs)
        ),
        _record_field(
            "TASK160_SOURCE_DEFINITION_ID",
            KIND_STRING,
            TASK160_SOURCE_DEFINITION_ID.encode("utf-8"),
        ),
    )


def success_canonical_bytes(
    result: Task160Result | None = None,
    *,
    schema_version: str | None = None,
    task160_version: str | None = None,
    implementation_software_version: str | None = None,
    request_hash_value: str | None = None,
    stream_records: Iterable[CapacityRatedStream] | None = None,
    envelope_authority: Task160EnvelopeAuthority | None = None,
    adapter_evidence: Iterable[Task160AdapterEvidence] | None = None,
    deferred_capabilities: Iterable[str] | None = None,
    c_dot_hot_W_K: Decimal | None = None,
    c_dot_cold_W_K: Decimal | None = None,
    applicability: ApplicabilityLedger | None = None,
    completeness: CompletenessLedger | None = None,
    provenance_inputs: Task160ProvenanceInputs | None = None,
) -> bytes:
    if result is not None:
        request_hash_value = result.request_hash
        stream_records = result.stream_records
        envelope_authority = result.envelope_authority
        adapter_evidence = result.adapter_evidence
        deferred_capabilities = result.deferred_capabilities
        c_dot_hot_W_K = result.c_dot_hot_W_K
        c_dot_cold_W_K = result.c_dot_cold_W_K
        applicability = result.applicability
        completeness = result.completeness
        provenance_inputs = Task160ProvenanceInputs(
            result.provenance.producer_identity,
            result.provenance.upstream_identity_hashes,
            result.provenance.source_evidence_refs,
            result.provenance.adapter_evidence_refs,
        )
        schema_version = result.schema_version
        task160_version = result.task160_version
        implementation_software_version = result.implementation_software_version
    else:
        schema_version = schema_version or "task160.schema.v1"
        task160_version = task160_version or "task160.v1"
        implementation_software_version = (
            implementation_software_version or "task160.local-implementation.v1"
        )
    if any(
        item is None
        for item in (
            request_hash_value,
            stream_records,
            envelope_authority,
            adapter_evidence,
            deferred_capabilities,
            c_dot_hot_W_K,
            c_dot_cold_W_K,
            applicability,
            completeness,
            provenance_inputs,
        )
    ):
        raise TypeError("all success identity inputs are required")
    assert isinstance(request_hash_value, str)
    assert stream_records is not None
    assert envelope_authority is not None
    assert adapter_evidence is not None
    assert deferred_capabilities is not None
    assert c_dot_hot_W_K is not None
    assert c_dot_cold_W_K is not None
    assert applicability is not None
    assert completeness is not None
    assert provenance_inputs is not None
    return frame_record(
        SUCCESS_HASH_DOMAIN,
        success_hash_fields(
            request_hash_value=request_hash_value,
            stream_records=stream_records,
            envelope_authority=envelope_authority,
            adapter_evidence=adapter_evidence,
            deferred_capabilities=deferred_capabilities,
            c_dot_hot_W_K=c_dot_hot_W_K,
            c_dot_cold_W_K=c_dot_cold_W_K,
            applicability=applicability,
            completeness=completeness,
            provenance_inputs=provenance_inputs,
            schema_version=schema_version,
            task160_version=task160_version,
            implementation_software_version=implementation_software_version,
        ),
    )


def success_hash_from_inputs(**kwargs: object) -> str:
    return sha256_hex_from_framed_bytes(success_canonical_bytes(**kwargs))  # type: ignore[arg-type]


def typed_blocked_hash_fields(
    *,
    schema_version: str,
    task160_version: str,
    implementation_software_version: str,
    failure_stage: Enum | str,
    request_hash_value: str,
    blockers: Iterable[Task160Blocker],
    deferred_capabilities: Iterable[str],
    producer_identity: Iterable[str],
    provenance_inputs: Task160ProvenanceInputs,
) -> tuple[tuple[str, bytes, bytes], ...]:
    return (
        _record_field("schema_version", KIND_STRING, schema_version.encode("utf-8")),
        _record_field("task160_version", KIND_STRING, task160_version.encode("utf-8")),
        _record_field(
            "implementation_software_version",
            KIND_STRING,
            implementation_software_version.encode("utf-8"),
        ),
        _record_field("failure_stage", KIND_ENUM, _enum_payload(failure_stage)),
        _record_field("request_hash", KIND_STRING, request_hash_value.encode("utf-8")),
        _record_field(
            "blockers", KIND_TUPLE, _tuple_records(blocker_bytes(item) for item in blockers)
        ),
        _record_field("warnings_normalized", KIND_TUPLE, _tuple_payload([])),
        _record_field(
            "deferred_capabilities_normalized", KIND_TUPLE, _tuple_strings(deferred_capabilities)
        ),
        _record_field("producer_identity", KIND_TUPLE, _tuple_strings(producer_identity)),
        _record_field(
            "provenance_inputs", KIND_RECORD, _provenance_inputs_bytes(provenance_inputs)
        ),
        _record_field(
            "TASK160_SOURCE_DEFINITION_ID",
            KIND_STRING,
            TASK160_SOURCE_DEFINITION_ID.encode("utf-8"),
        ),
    )


def typed_blocked_hash(**kwargs: object) -> str:
    return sha256_hex_from_framed_bytes(
        frame_record(TYPED_BLOCKED_HASH_DOMAIN, typed_blocked_hash_fields(**kwargs))  # type: ignore[arg-type]
    )


def raw_blocked_hash_fields(
    *,
    schema_version: str,
    task160_version: str,
    implementation_software_version: str,
    failure_stage: Enum | str,
    raw_request_projection_hash: str,
    blockers: Iterable[Task160Blocker],
    deferred_capabilities: Iterable[str],
) -> tuple[tuple[str, bytes, bytes], ...]:
    return (
        _record_field("schema_version", KIND_STRING, schema_version.encode("utf-8")),
        _record_field("task160_version", KIND_STRING, task160_version.encode("utf-8")),
        _record_field(
            "implementation_software_version",
            KIND_STRING,
            implementation_software_version.encode("utf-8"),
        ),
        _record_field("failure_stage", KIND_ENUM, _enum_payload(failure_stage)),
        _record_field(
            "raw_request_projection_hash", KIND_STRING, raw_request_projection_hash.encode("utf-8")
        ),
        _record_field(
            "blockers", KIND_TUPLE, _tuple_records(blocker_bytes(item) for item in blockers)
        ),
        _record_field("warnings_normalized", KIND_TUPLE, _tuple_payload([])),
        _record_field(
            "deferred_capabilities_normalized", KIND_TUPLE, _tuple_strings(deferred_capabilities)
        ),
        _record_field(
            "TASK160_SOURCE_DEFINITION_ID",
            KIND_STRING,
            TASK160_SOURCE_DEFINITION_ID.encode("utf-8"),
        ),
    )


def raw_blocked_hash(**kwargs: object) -> str:
    return sha256_hex_from_framed_bytes(
        frame_record(RAW_BLOCKED_HASH_DOMAIN, raw_blocked_hash_fields(**kwargs))  # type: ignore[arg-type]
    )


def raw_projection_node_bytes(value: RawProjectionNode) -> bytes:
    scalar_kind, scalar_payload = (
        (KIND_NONE, b"")
        if value.scalar_payload is None
        else (KIND_STRING, value.scalar_payload.encode("utf-8"))
    )
    return frame_record(
        TASK160_RAW_PROJECTION_NODE_DOMAIN,
        (
            _record_field("field_name", KIND_STRING, value.field_name.encode("utf-8")),
            _record_field("kind", KIND_ENUM, _enum_payload(value.kind)),
            _record_field("scalar_payload", scalar_kind, scalar_payload),
            _record_field(
                "children",
                KIND_TUPLE,
                _tuple_records(raw_projection_node_bytes(item) for item in value.children),
            ),
        ),
    )


def raw_request_projection_bytes(value: Task160RawRequestProjection) -> bytes:
    return frame_record(
        TASK160_RAW_PROJECTION_DOMAIN,
        (
            _record_field("schema_version", KIND_STRING, value.schema_version.encode("utf-8")),
            _record_field("root", KIND_RECORD, raw_projection_node_bytes(value.root)),
        ),
    )


def raw_request_projection_hash(value: Task160RawRequestProjection) -> str:
    return sha256_hex_from_framed_bytes(raw_request_projection_bytes(value))


def result_id(result_hash: str) -> UUID:
    return uuid5(UUID(TASK160_RESULT_ID_NAMESPACE), SUCCESS_ID_PREFIX + result_hash)


def typed_blocked_result_id(blocked_result_hash: str) -> UUID:
    return uuid5(UUID(TASK160_RESULT_ID_NAMESPACE), TYPED_BLOCKED_ID_PREFIX + blocked_result_hash)


def raw_blocked_result_id(blocked_result_hash: str) -> UUID:
    return uuid5(UUID(TASK160_RESULT_ID_NAMESPACE), RAW_BLOCKED_ID_PREFIX + blocked_result_hash)


def to_provenance_payload_hash(bare_sha256_hex: str) -> str:
    if len(bare_sha256_hex) != 64 or any(
        char not in "0123456789abcdef" for char in bare_sha256_hex
    ):
        raise ValueError("artifact hash must be 64 lowercase hexadecimal characters")
    return "sha256:" + bare_sha256_hex


__all__ = [
    "RAW_BLOCKED_ID_PREFIX",
    "REQUEST_HASH_DOMAIN",
    "SUCCESS_ID_PREFIX",
    "SUCCESS_HASH_DOMAIN",
    "TASK160_DETAIL_PAIR_DOMAIN",
    "TASK160_RESULT_ID_NAMESPACE",
    "TASK160_SOURCE_DEFINITION_ID",
    "TYPED_BLOCKED_ID_PREFIX",
    "TYPED_BLOCKED_HASH_DOMAIN",
    "adapter_evidence_bytes",
    "applicability_ledger_bytes",
    "blocker_bytes",
    "capacity_rated_stream_bytes",
    "completeness_ledger_bytes",
    "detail_pair_bytes",
    "envelope_authority_bytes",
    "frame_record",
    "frame_tuple",
    "frame_value",
    "property_snapshot_identity_bytes",
    "raw_blocked_hash",
    "raw_blocked_hash_fields",
    "raw_blocked_result_id",
    "raw_request_projection_bytes",
    "raw_request_projection_hash",
    "rating_stream_bytes",
    "request_canonical_bytes",
    "request_hash",
    "request_hash_fields",
    "result_id",
    "role_resolved_stream_bytes",
    "sha256_hex_from_framed_bytes",
    "success_canonical_bytes",
    "success_hash_fields",
    "success_hash_from_inputs",
    "to_provenance_payload_hash",
    "typed_blocked_hash",
    "typed_blocked_hash_fields",
    "typed_blocked_result_id",
    "validated_rating_stream_state_bytes",
]
