"""TASK163 canonical projections, framing, hashes, and UUID identities."""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid5

from hexagent.exchangers.shell_tube.flow_arrangement_performance_method_authority.models import (
    Task161Result,
)
from hexagent.exchangers.shell_tube.thermal_performance_closure.canonical import (
    case_authority_bytes,
    energy_balance_bytes,
    selected_method_identity_bytes,
    terminal_closure_bytes,
)
from hexagent.exchangers.shell_tube.tube_side.canonical import (
    KIND_BOOL_FALSE,
    KIND_BOOL_TRUE,
    KIND_DECIMAL,
    KIND_ENUM,
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
    Task038ResultIdentityProjection,
    Task160ResultIdentityProjection,
    Task161ResultIdentityProjection,
    Task162ResultIdentityProjection,
    Task162SuccessReplayEvidenceIdentityProjection,
    Task163Applicability,
    Task163Blocker,
    Task163Completeness,
    Task163DeferredCapabilities,
    Task163HeatDutyProjection,
    Task163OutletTemperatureProjection,
    Task163PreResultIdentityInputs,
    Task163ProvenanceSemanticInputs,
    Task163RatingPerformanceProjection,
    Task163RawBoundaryBlockedResult,
    Task163RawProjectionKind,
    Task163RawProjectionNode,
    Task163RawRequestProjection,
    Task163Request,
    Task163Task162Evidence,
    Task163TypedBlockedResult,
    Task163Warning,
)

TASK163_REQUEST_HASH_DOMAIN = "TASK163_REQUEST_HASH_V1"
TASK163_SUCCESS_HASH_DOMAIN = "TASK163_SUCCESS_RESULT_HASH_V1"
TASK163_TYPED_BLOCKED_HASH_DOMAIN = "TASK163_TYPED_BLOCKED_RESULT_HASH_V1"
TASK163_RAW_BLOCKED_HASH_DOMAIN = "TASK163_RAW_BOUNDARY_BLOCKED_RESULT_HASH_V1"
TASK163_RAW_PROJECTION_DOMAIN = "TASK163_RAW_REQUEST_PROJECTION_V1"
TASK163_RAW_PROJECTION_NODE_DOMAIN = "TASK163_RAW_PROJECTION_NODE_V1"

TASK163_SUCCESS_ID_PREFIX = "task163-result-v1::"
TASK163_TYPED_BLOCKED_ID_PREFIX = "task163-typed-blocked-v1::"
TASK163_RAW_BLOCKED_ID_PREFIX = "task163-raw-boundary-blocked-v1::"

TASK163_RESULT_ID_NAMESPACE = UUID("a1630000-0000-5000-8000-000000000163")
TASK163_PROVENANCE_NAMESPACE = UUID("a1630000-0000-5001-8000-000000000163")
TASK163_BLOCKED_ID_NAMESPACE = UUID("a1630000-0000-5002-8000-000000000163")

TASK163_REQUEST_FIELD_ORDER: tuple[str, ...] = (
    "schema_version",
    "task163_version",
    "source_definition_id",
    "task162_result_identity_projection",
    "task162_success_replay_evidence_identity_projection",
    "request_metadata",
)

TASK163_SUCCESS_PREIMAGE_FIELD_ORDER: tuple[str, ...] = (
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
    "warnings_normalized",
    "blockers_normalized",
    "provenance_semantic_inputs",
)


def _string(value: str) -> bytes:
    if type(value) is not str:
        raise TypeError("TASK163 canonical string requires exact str")
    return value.encode("utf-8", "strict")


def _decimal(value: Decimal) -> bytes:
    if type(value) is not Decimal or not value.is_finite():
        raise ValueError("TASK163 canonical Decimal must be finite")
    return str(value).encode("ascii")


def _integer(value: int) -> bytes:
    if type(value) is not int:
        raise TypeError("TASK163 canonical integer requires exact int")
    return str(value).encode("ascii")


def _enum(value: Enum | str) -> bytes:
    token = value.value if isinstance(value, Enum) else value
    return _string(token)


def _boolean(value: bool) -> tuple[bytes, bytes]:
    if type(value) is not bool:
        raise TypeError("TASK163 canonical boolean requires exact bool")
    return (KIND_BOOL_TRUE if value else KIND_BOOL_FALSE), b""


def _none_or_string(value: str | None) -> tuple[bytes, bytes]:
    if value is None:
        return KIND_NONE, b""
    return KIND_STRING, _string(value)


def _field(name: str, kind: bytes, payload: bytes) -> tuple[str, bytes, bytes]:
    return name, kind, payload


def _nested(name: str, payload: bytes) -> tuple[str, bytes, bytes]:
    return _field(name, KIND_RECORD, payload)


def _strings(values: Iterable[str]) -> bytes:
    return frame_tuple(tuple(frame_value(KIND_STRING, _string(value)) for value in values))


def _records(values: Iterable[bytes]) -> bytes:
    return frame_tuple(tuple(values))


def _pairs(values: Iterable[tuple[str, str]]) -> bytes:
    ordered = sorted(values, key=lambda item: (_string(item[0]), _string(item[1])))
    return _records(
        frame_record(
            "TASK163_STRING_PAIR_V1",
            (
                _field("key", KIND_STRING, _string(key)),
                _field("value", KIND_STRING, _string(value)),
            ),
        )
        for key, value in ordered
    )


def task160_result_identity_projection(value: object) -> Task160ResultIdentityProjection:
    from hexagent.exchangers.shell_tube.thermal_stream_state.models import Task160Result

    if type(value) is not Task160Result:
        raise TypeError("expected exact Task160Result")
    return Task160ResultIdentityProjection(
        schema_version=value.schema_version,
        task160_version=value.task160_version,
        request_hash=value.request_hash,
        result_hash=value.result_hash,
        result_id=str(value.result_id).lower(),
        provenance_hash=value.provenance.provenance_hash,
    )


def task161_result_identity_projection(value: object) -> Task161ResultIdentityProjection:
    if type(value) is not Task161Result:
        raise TypeError("expected exact Task161Result")
    return Task161ResultIdentityProjection(
        schema_version=value.schema_version,
        task161_version=value.task161_version,
        source_definition_id=value.source_definition_id,
        request_hash=value.request_hash,
        result_hash=value.result_hash,
        result_id=str(value.result_id).lower(),
        provenance_hash=value.provenance.provenance_hash,
    )


def task038_result_identity_projection(value: object) -> Task038ResultIdentityProjection:
    from hexagent.exchangers.shell_tube.overall_heat_transfer_coefficient_ua.models import (
        Task038SuccessResult,
    )

    if type(value) is not Task038SuccessResult:
        raise TypeError("expected exact Task038SuccessResult")
    return Task038ResultIdentityProjection(
        schema_version=value.schema_version,
        task038_version=value.task038_version,
        profile_id=value.profile_id,
        request_hash=value.request_hash,
        result_hash=value.result_hash,
        result_id=str(value.result_id).lower(),
        provenance_hash=value.provenance.provenance_hash,
    )


def task162_result_identity_projection(value: object) -> Task162ResultIdentityProjection:
    from hexagent.exchangers.shell_tube.thermal_performance_closure.models import Task162Result

    if type(value) is not Task162Result:
        raise TypeError("expected exact Task162Result")
    return Task162ResultIdentityProjection(
        schema_version=value.schema_version,
        task162_version=value.task162_version,
        implementation_software_version=value.implementation_software_version,
        source_definition_id=value.source_definition_id,
        request_hash=value.request_hash,
        result_hash=value.result_hash,
        result_id=str(value.result_id).lower(),
        provenance_hash=value.provenance.provenance_hash,
    )


def task162_success_replay_evidence_identity_projection(
    value: object,
) -> Task162SuccessReplayEvidenceIdentityProjection:
    from hexagent.exchangers.shell_tube.thermal_performance_closure.models import (
        Task162SuccessReplayEvidence,
    )

    if type(value) is not Task162SuccessReplayEvidence:
        raise TypeError("expected exact Task162SuccessReplayEvidence")
    return Task162SuccessReplayEvidenceIdentityProjection(
        evidence_schema_version=value.evidence_schema_version,
        task162_schema_version=value.task162_schema_version,
        task162_version=value.task162_version,
        task162_implementation_software_version=value.task162_implementation_software_version,
        task162_source_definition_id=value.task162_source_definition_id,
        task162_result_hash=value.task162_result_hash,
        task162_result_id=str(value.task162_result_id).lower(),
        task160_result_identity_projection=task160_result_identity_projection(
            value.original_task160_result
        ),
        task161_result_identity_projection=task161_result_identity_projection(
            value.original_task161_result
        ),
        task038_result_identity_projection=task038_result_identity_projection(
            value.original_task038_success_result
        ),
        original_case_authority_identity=sha256_hex_from_framed_bytes(
            case_authority_bytes(value.original_case_authority)
        ),
        original_task162_request_metadata=tuple(
            sorted(
                value.request_metadata,
                key=lambda item: (_string(item[0]), _string(item[1])),
            )
        ),
    )


def _task160_identity_bytes(value: Task160ResultIdentityProjection) -> bytes:
    return frame_record(
        "TASK163_TASK160_RESULT_IDENTITY_V1",
        tuple(
            _field(name, KIND_STRING, _string(getattr(value, name)))
            for name in (
                "schema_version",
                "task160_version",
                "request_hash",
                "result_hash",
                "result_id",
                "provenance_hash",
            )
        ),
    )


def _task161_identity_bytes(value: Task161ResultIdentityProjection) -> bytes:
    return frame_record(
        "TASK163_TASK161_RESULT_IDENTITY_V1",
        tuple(
            _field(name, KIND_STRING, _string(getattr(value, name)))
            for name in (
                "schema_version",
                "task161_version",
                "source_definition_id",
                "request_hash",
                "result_hash",
                "result_id",
                "provenance_hash",
            )
        ),
    )


def _task038_identity_bytes(value: Task038ResultIdentityProjection) -> bytes:
    return frame_record(
        "TASK163_TASK038_RESULT_IDENTITY_V1",
        tuple(
            _field(name, KIND_STRING, _string(getattr(value, name)))
            for name in (
                "schema_version",
                "task038_version",
                "profile_id",
                "request_hash",
                "result_hash",
                "result_id",
                "provenance_hash",
            )
        ),
    )


def _task162_identity_bytes(value: Task162ResultIdentityProjection) -> bytes:
    return frame_record(
        "TASK163_TASK162_RESULT_IDENTITY_V1",
        tuple(
            _field(name, KIND_STRING, _string(getattr(value, name)))
            for name in (
                "schema_version",
                "task162_version",
                "implementation_software_version",
                "source_definition_id",
                "request_hash",
                "result_hash",
                "result_id",
                "provenance_hash",
            )
        ),
    )


def _replay_evidence_identity_bytes(
    value: Task162SuccessReplayEvidenceIdentityProjection,
) -> bytes:
    return frame_record(
        "TASK163_TASK162_REPLAY_EVIDENCE_IDENTITY_V1",
        (
            *(
                _field(name, KIND_STRING, _string(getattr(value, name)))
                for name in (
                    "evidence_schema_version",
                    "task162_schema_version",
                    "task162_version",
                    "task162_implementation_software_version",
                    "task162_source_definition_id",
                    "task162_result_hash",
                    "task162_result_id",
                )
            ),
            _nested(
                "task160_result_identity_projection",
                _task160_identity_bytes(value.task160_result_identity_projection),
            ),
            _nested(
                "task161_result_identity_projection",
                _task161_identity_bytes(value.task161_result_identity_projection),
            ),
            _nested(
                "task038_result_identity_projection",
                _task038_identity_bytes(value.task038_result_identity_projection),
            ),
            _field(
                "original_case_authority_identity",
                KIND_STRING,
                _string(value.original_case_authority_identity),
            ),
            _field(
                "original_task162_request_metadata",
                KIND_TUPLE,
                _pairs(value.original_task162_request_metadata),
            ),
        ),
    )


def _task162_evidence_bytes(value: Task163Task162Evidence) -> bytes:
    return frame_record(
        "TASK163_TASK162_EVIDENCE_V1",
        (
            _nested(
                "task162_result_identity_projection",
                _task162_identity_bytes(value.task162_result_identity_projection),
            ),
            _nested(
                "task162_success_replay_evidence_identity_projection",
                _replay_evidence_identity_bytes(
                    value.task162_success_replay_evidence_identity_projection
                ),
            ),
        ),
    )


def _rating_projection_bytes(value: Task163RatingPerformanceProjection) -> bytes:
    return frame_record(
        "TASK163_RATING_PERFORMANCE_PROJECTION_V1",
        (
            _nested(
                "selected_method_identity",
                selected_method_identity_bytes(value.selected_method_identity),
            ),
            _field(
                "selected_baffle_relation", KIND_STRING, _string(value.selected_baffle_relation)
            ),
            _field("ntu", KIND_DECIMAL, _decimal(value.ntu)),
            _field("r_source", KIND_DECIMAL, _decimal(value.r_source)),
            _field("p_source", KIND_DECIMAL, _decimal(value.p_source)),
            _field("epsilon", KIND_DECIMAL, _decimal(value.epsilon)),
        ),
    )


def _heat_duty_bytes(value: Task163HeatDutyProjection) -> bytes:
    return frame_record(
        "TASK163_HEAT_DUTY_PROJECTION_V1",
        tuple(
            _field(name, KIND_DECIMAL, _decimal(getattr(value, name)))
            for name in ("q_max", "q_method", "q_hot", "q_cold")
        ),
    )


def _outlet_bytes(value: Task163OutletTemperatureProjection) -> bytes:
    return frame_record(
        "TASK163_OUTLET_TEMPERATURE_PROJECTION_V1",
        (
            _field("hot_outlet_temperature", KIND_DECIMAL, _decimal(value.hot_outlet_temperature)),
            _field(
                "cold_outlet_temperature", KIND_DECIMAL, _decimal(value.cold_outlet_temperature)
            ),
        ),
    )


def _applicability_bytes(value: Task163Applicability) -> bytes:
    return frame_record(
        "TASK163_APPLICABILITY_V1",
        (
            _field("status", KIND_ENUM, _enum(value.status)),
            _field(
                "checks",
                KIND_TUPLE,
                _records(
                    frame_record(
                        "TASK163_APPLICABILITY_CHECK_V1",
                        (
                            _field("name", KIND_ENUM, _enum(name)),
                            _field("status", KIND_ENUM, _enum(status)),
                        ),
                    )
                    for name, status in value.checks
                ),
            ),
        ),
    )


def _completeness_bytes(value: Task163Completeness) -> bytes:
    return frame_record(
        "TASK163_COMPLETENESS_V1",
        (
            _field("status", KIND_ENUM, _enum(value.status)),
            _field(
                "required_fields",
                KIND_TUPLE,
                frame_tuple(
                    tuple(frame_value(KIND_ENUM, _enum(field)) for field in value.required_fields)
                ),
            ),
        ),
    )


def _deferred_bytes(value: Task163DeferredCapabilities) -> bytes:
    return frame_record(
        "TASK163_DEFERRED_CAPABILITIES_V1",
        (
            _field("status", KIND_ENUM, _enum(value.status)),
            _field(
                "capabilities",
                KIND_TUPLE,
                frame_tuple(
                    tuple(frame_value(KIND_ENUM, _enum(item)) for item in value.capabilities)
                ),
            ),
        ),
    )


def _warning_bytes(value: Task163Warning) -> bytes:
    return frame_record(
        "TASK163_WARNING_V1",
        (
            _field("code", KIND_STRING, _string(value.code)),
            _field("evidence_refs", KIND_TUPLE, _strings(value.evidence_refs)),
        ),
    )


def _blocker_bytes(value: Task163Blocker) -> bytes:
    return frame_record(
        "TASK163_BLOCKER_V1",
        (
            _field("code", KIND_ENUM, _enum(value.code)),
            _field("stage", KIND_ENUM, _enum(value.stage)),
            _field("evidence_refs", KIND_TUPLE, _strings(value.evidence_refs)),
        ),
    )


def _semantic_inputs_bytes(value: Task163ProvenanceSemanticInputs) -> bytes:
    return frame_record(
        "TASK163_PROVENANCE_SEMANTIC_INPUTS_V1",
        tuple(
            _field(name, KIND_STRING, _string(getattr(value, name)))
            for name in (
                "source_authority_payload_hash",
                "task162_result_evidence_payload_hash",
                "rating_composition_payload_hash",
                "applicability_payload_hash",
                "completeness_payload_hash",
            )
        ),
    )


def _pre_result_fields(
    value: Task163PreResultIdentityInputs,
) -> tuple[tuple[str, bytes, bytes], ...]:
    return (
        _field("schema_version", KIND_STRING, _string(value.schema_version)),
        _field("task163_version", KIND_STRING, _string(value.task163_version)),
        _field(
            "implementation_software_version",
            KIND_STRING,
            _string(value.implementation_software_version),
        ),
        _field("source_definition_id", KIND_STRING, _string(value.source_definition_id)),
        _field("request_hash", KIND_STRING, _string(value.request_hash)),
        _nested("task162_evidence", _task162_evidence_bytes(value.task162_evidence)),
        _nested(
            "rating_performance_projection",
            _rating_projection_bytes(value.rating_performance_projection),
        ),
        _nested("heat_duty_projection", _heat_duty_bytes(value.heat_duty_projection)),
        _nested(
            "outlet_temperature_projection", _outlet_bytes(value.outlet_temperature_projection)
        ),
        _nested("energy_balance_evidence", energy_balance_bytes(value.energy_balance_evidence)),
        _nested(
            "terminal_temperature_evidence",
            terminal_closure_bytes(value.terminal_temperature_evidence),
        ),
        _nested("applicability", _applicability_bytes(value.applicability)),
        _nested("completeness", _completeness_bytes(value.completeness)),
        _nested("deferred_capabilities", _deferred_bytes(value.deferred_capabilities)),
        _field(
            "warnings_normalized",
            KIND_TUPLE,
            _records(_warning_bytes(item) for item in value.warnings_normalized),
        ),
        _field(
            "blockers_normalized",
            KIND_TUPLE,
            _records(_blocker_bytes(item) for item in value.blockers_normalized),
        ),
        _nested(
            "provenance_semantic_inputs", _semantic_inputs_bytes(value.provenance_semantic_inputs)
        ),
    )


def success_canonical_bytes(value: Task163PreResultIdentityInputs) -> bytes:
    return frame_record(TASK163_SUCCESS_HASH_DOMAIN, _pre_result_fields(value))


def success_hash_from_inputs(value: Task163PreResultIdentityInputs) -> str:
    return sha256_hex_from_framed_bytes(success_canonical_bytes(value))


def result_id(result_hash: str) -> UUID:
    return uuid5(TASK163_RESULT_ID_NAMESPACE, TASK163_SUCCESS_ID_PREFIX + result_hash)


def request_canonical_bytes(value: Task163Request) -> bytes:
    task162 = task162_result_identity_projection(value.task162_result)
    evidence = task162_success_replay_evidence_identity_projection(
        value.task162_success_replay_evidence
    )
    return frame_record(
        TASK163_REQUEST_HASH_DOMAIN,
        (
            _field("schema_version", KIND_STRING, _string(value.schema_version)),
            _field("task163_version", KIND_STRING, _string(value.task163_version)),
            _field("source_definition_id", KIND_STRING, _string(value.source_definition_id)),
            _nested("task162_result_identity_projection", _task162_identity_bytes(task162)),
            _nested(
                "task162_success_replay_evidence_identity_projection",
                _replay_evidence_identity_bytes(evidence),
            ),
            _field("request_metadata", KIND_TUPLE, _pairs(value.request_metadata)),
        ),
    )


def request_hash(value: Task163Request) -> str:
    return sha256_hex_from_framed_bytes(request_canonical_bytes(value))


def typed_blocked_canonical_bytes(value: Task163TypedBlockedResult) -> bytes:
    task162_identity = (
        KIND_NONE,
        b"",
    )
    if value.task162_result_identity_or_none is not None:
        task162_identity = (
            KIND_RECORD,
            _task162_identity_bytes(value.task162_result_identity_or_none),
        )
    return frame_record(
        TASK163_TYPED_BLOCKED_HASH_DOMAIN,
        (
            _field("schema_version", KIND_STRING, _string(value.schema_version)),
            _field("task163_version", KIND_STRING, _string(value.task163_version)),
            _field(
                "implementation_software_version",
                KIND_STRING,
                _string(value.implementation_software_version),
            ),
            _field("failure_stage", KIND_ENUM, _enum(value.failure_stage)),
            _field("request_hash", KIND_STRING, _string(value.request_hash)),
            _field("task162_result_identity_or_none", *task162_identity),
            _field(
                "blockers_normalized",
                KIND_TUPLE,
                _records(_blocker_bytes(item) for item in value.blockers),
            ),
            _field(
                "warnings_normalized",
                KIND_TUPLE,
                _records(_warning_bytes(item) for item in value.warnings),
            ),
        ),
    )


def typed_blocked_hash(value: Task163TypedBlockedResult) -> str:
    return sha256_hex_from_framed_bytes(typed_blocked_canonical_bytes(value))


def typed_blocked_id(blocked_hash: str) -> UUID:
    return uuid5(TASK163_BLOCKED_ID_NAMESPACE, TASK163_TYPED_BLOCKED_ID_PREFIX + blocked_hash)


def raw_projection_node_bytes(value: Task163RawProjectionNode) -> bytes:
    children = value.children
    if value.kind is Task163RawProjectionKind.RECORD:
        children = tuple(
            sorted(
                children,
                key=lambda child: (_string(child.field_name), raw_projection_node_bytes(child)),
            )
        )
    type_kind, type_payload = _none_or_string(value.type_identity)
    scalar_kind, scalar_payload = _none_or_string(value.scalar_payload)
    return frame_record(
        TASK163_RAW_PROJECTION_NODE_DOMAIN,
        (
            _field("field_name", KIND_STRING, _string(value.field_name)),
            _field("kind", KIND_ENUM, _enum(value.kind)),
            _field("type_identity", type_kind, type_payload),
            _field("scalar_payload", scalar_kind, scalar_payload),
            _field(
                "children",
                KIND_TUPLE,
                _records(raw_projection_node_bytes(child) for child in children),
            ),
        ),
    )


canonical_projected_node_bytes = raw_projection_node_bytes


def raw_request_projection_bytes(value: object) -> bytes:
    if type(value) is not Task163RawRequestProjection:
        raise TypeError("expected exact Task163RawRequestProjection")
    return frame_record(
        TASK163_RAW_PROJECTION_DOMAIN,
        (
            _field("schema_version", KIND_STRING, _string(value.schema_version)),
            _field("root", KIND_RECORD, raw_projection_node_bytes(value.root)),
        ),
    )


def raw_request_projection_hash(value: Task163RawRequestProjection) -> str:
    return sha256_hex_from_framed_bytes(raw_request_projection_bytes(value))


def raw_blocked_canonical_bytes(value: Task163RawBoundaryBlockedResult) -> bytes:
    return frame_record(
        TASK163_RAW_BLOCKED_HASH_DOMAIN,
        (
            _field("schema_version", KIND_STRING, _string(value.schema_version)),
            _field("task163_version", KIND_STRING, _string(value.task163_version)),
            _field(
                "implementation_software_version",
                KIND_STRING,
                _string(value.implementation_software_version),
            ),
            _field("failure_stage", KIND_ENUM, _enum(value.failure_stage)),
            _field(
                "raw_request_projection",
                KIND_RECORD,
                raw_request_projection_bytes(value.raw_request_projection),
            ),
            _field(
                "raw_request_projection_hash",
                KIND_STRING,
                _string(value.raw_request_projection_hash),
            ),
            _field(
                "blockers_normalized",
                KIND_TUPLE,
                _records(_blocker_bytes(item) for item in value.blockers),
            ),
            _field(
                "warnings_normalized",
                KIND_TUPLE,
                _records(_warning_bytes(item) for item in value.warnings),
            ),
        ),
    )


def raw_blocked_hash(value: Task163RawBoundaryBlockedResult) -> str:
    return sha256_hex_from_framed_bytes(raw_blocked_canonical_bytes(value))


def raw_blocked_id(blocked_hash: str) -> UUID:
    return uuid5(TASK163_BLOCKED_ID_NAMESPACE, TASK163_RAW_BLOCKED_ID_PREFIX + blocked_hash)


__all__ = [
    "TASK163_BLOCKED_ID_NAMESPACE",
    "TASK163_PROVENANCE_NAMESPACE",
    "TASK163_RAW_BLOCKED_HASH_DOMAIN",
    "TASK163_RAW_BLOCKED_ID_PREFIX",
    "TASK163_RAW_PROJECTION_DOMAIN",
    "TASK163_RAW_PROJECTION_NODE_DOMAIN",
    "TASK163_REQUEST_FIELD_ORDER",
    "TASK163_REQUEST_HASH_DOMAIN",
    "TASK163_RESULT_ID_NAMESPACE",
    "TASK163_SUCCESS_HASH_DOMAIN",
    "TASK163_SUCCESS_ID_PREFIX",
    "TASK163_SUCCESS_PREIMAGE_FIELD_ORDER",
    "TASK163_TYPED_BLOCKED_HASH_DOMAIN",
    "TASK163_TYPED_BLOCKED_ID_PREFIX",
    "canonical_projected_node_bytes",
    "raw_blocked_canonical_bytes",
    "raw_blocked_hash",
    "raw_blocked_id",
    "raw_projection_node_bytes",
    "raw_request_projection_bytes",
    "raw_request_projection_hash",
    "request_canonical_bytes",
    "request_hash",
    "result_id",
    "sha256_hex_from_framed_bytes",
    "success_canonical_bytes",
    "success_hash_from_inputs",
    "task038_result_identity_projection",
    "task160_result_identity_projection",
    "task161_result_identity_projection",
    "task162_result_identity_projection",
    "task162_success_replay_evidence_identity_projection",
    "typed_blocked_canonical_bytes",
    "typed_blocked_hash",
    "typed_blocked_id",
]
