"""TASK164 canonical projections, evidence records, hashes, and UUIDs.

All framing primitives come from the repository-owned tube-side canonical
module.  This module only composes those primitives for the TASK164 schemas;
it never serializes arbitrary objects or replays an upstream calculation.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid5

from hexagent.domain.provenance import ProvenanceGraph
from hexagent.exchangers.shell_tube.thermal_performance_closure.canonical import (
    case_authority_bytes,
)
from hexagent.exchangers.shell_tube.thermal_rating_composition.canonical import (
    task038_result_identity_projection,
    task160_result_identity_projection,
    task161_result_identity_projection,
    task162_result_identity_projection,
    task162_success_replay_evidence_identity_projection,
)
from hexagent.exchangers.shell_tube.thermal_rating_composition.models import (
    Task162SuccessReplayEvidenceIdentityProjection,
    Task163Applicability,
    Task163Completeness,
    Task163ValidationResult,
)
from hexagent.exchangers.shell_tube.tube_side.canonical import (
    KIND_BOOL_FALSE,
    KIND_BOOL_TRUE,
    KIND_BYTES,
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
    TASK164_SCENARIO_IDS,
    TASK164_SCENARIO_SOURCE_ORDER,
    TASK164_SUCCESS_PREIMAGE_FIELD_ORDER,
    Task164AcceptanceCategoryRecord,
    Task164AcceptanceLedger,
    Task164Applicability,
    Task164ApplicabilityRecord,
    Task164ArtifactRecord,
    Task164Blocker,
    Task164Completeness,
    Task164DemonstrationCoverage,
    Task164DeterminismEvidence,
    Task164DualRuntimeObservation,
    Task164EvidencePackage,
    Task164EvidencePackageClaim,
    Task164EvidencePayload,
    Task164FailureCode,
    Task164FailureStage,
    Task164ObservedIdentity,
    Task164PreResultIdentityInputs,
    Task164ProvenanceSemanticInputs,
    Task164PythonParityClaim,
    Task164RawBoundaryBlockedResult,
    Task164RawProjectionKind,
    Task164RawProjectionNode,
    Task164RawRequestProjection,
    Task164RepeatRunClaim,
    Task164RepeatRunObservation,
    Task164RepeatRunSurface,
    Task164Request,
    Task164RuntimeObservation,
    Task164ScenarioClaim,
    Task164ScenarioId,
    Task164ScenarioObservation,
    Task164ScenarioRecord,
    Task164ScenarioSetup,
    Task164ScopeFenceEvidence,
    Task164SurfaceHashRecord,
    Task164Task163Evidence,
    Task164Task163ReplayEvidence,
    Task164TerminalCapability,
    Task164TypedBlockedResult,
    runtime_identity_for_version,
)
from .trusted_evidence import MainDeliveryObservation

TASK164_REQUEST_HASH_DOMAIN = "TASK164_REQUEST_HASH_V1"
TASK164_SUCCESS_HASH_DOMAIN = "TASK164_SUCCESS_RESULT_HASH_V1"
TASK164_TYPED_BLOCKED_HASH_DOMAIN = "TASK164_TYPED_BLOCKED_RESULT_HASH_V1"
TASK164_RAW_BLOCKED_HASH_DOMAIN = "TASK164_RAW_BOUNDARY_BLOCKED_RESULT_HASH_V1"
TASK164_RESULT_ID_NAMESPACE = UUID("a1640000-0000-5000-8000-000000000164")
TASK164_PROVENANCE_NAMESPACE = UUID("a1640000-0000-5001-8000-000000000164")
TASK164_TYPED_BLOCKED_ID_NAMESPACE = UUID("a1640000-0000-5002-8000-000000000164")
TASK164_RAW_BLOCKED_ID_NAMESPACE = UUID("a1640000-0000-5003-8000-000000000164")
TASK164_RESULT_ID_PREFIX = "task164-result-v1::"
TASK164_TYPED_BLOCKED_ID_PREFIX = "task164-typed-blocked-v1::"
TASK164_RAW_BLOCKED_ID_PREFIX = "task164-raw-boundary-blocked-v1::"


# The exact constants are duplicated as explicit module-level contracts so
# callers/tests do not need to depend on an implementation module.
TASK164_REQUEST_FIELD_ORDER: tuple[str, ...] = (
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


def _string(value: str) -> bytes:
    if type(value) is not str:
        raise TypeError("canonical string requires exact str")
    return value.encode("utf-8", "strict")


def _ascii(value: str) -> bytes:
    if type(value) is not str:
        raise TypeError("canonical ASCII value requires exact str")
    return value.encode("ascii", "strict")


def _integer(value: int) -> bytes:
    if type(value) is not int:
        raise TypeError("canonical integer requires exact int")
    return str(value).encode("ascii")


def _decimal(value: Decimal) -> bytes:
    if type(value) is not Decimal or not value.is_finite():
        raise ValueError("canonical Decimal must be finite")
    return str(value).encode("ascii")


def _enum(value: Enum | str) -> bytes:
    if isinstance(value, Enum):
        token = value.value
        if type(token) is not str:
            raise TypeError("canonical enum value must be exact str")
        return _string(token)
    return _string(value)


def _boolean(value: bool) -> tuple[bytes, bytes]:
    if type(value) is not bool:
        raise TypeError("canonical boolean requires exact bool")
    return (KIND_BOOL_TRUE if value else KIND_BOOL_FALSE), b""


def _none_or_string(value: str | None) -> tuple[bytes, bytes]:
    if value is None:
        return KIND_NONE, b""
    return KIND_STRING, _string(value)


def _uuid_text(value: UUID | str) -> bytes:
    if type(value) is UUID:
        return _ascii(str(value).lower())
    if type(value) is str:
        return _ascii(value.lower())
    raise TypeError("canonical UUID requires UUID or exact str")


def _field(name: str, kind: bytes, payload: bytes) -> tuple[str, bytes, bytes]:
    return name, kind, payload


def _nested(name: str, payload: bytes) -> tuple[str, bytes, bytes]:
    return _field(name, KIND_RECORD, payload)


def _tuple_values(values: Iterable[tuple[bytes, bytes]]) -> bytes:
    return frame_tuple(tuple(frame_value(kind, payload) for kind, payload in values))


def _tuple_strings(values: Iterable[str]) -> bytes:
    return _tuple_values((KIND_STRING, _string(value)) for value in values)


def _tuple_enums(values: Iterable[Enum | str]) -> bytes:
    return _tuple_values((KIND_ENUM, _enum(value)) for value in values)


def _tuple_records(values: Iterable[bytes]) -> bytes:
    return _tuple_values((KIND_RECORD, value) for value in values)


def _tuple_pairs(values: Iterable[tuple[str, str]]) -> bytes:
    ordered = sorted(values, key=lambda item: (_string(item[0]), _string(item[1])))
    return _tuple_records(
        frame_record(
            "TASK164_STRING_PAIR_V1",
            (
                _field("key", KIND_STRING, _string(key)),
                _field("value", KIND_STRING, _string(value)),
            ),
        )
        for key, value in ordered
    )


def _hash(domain: str, fields: Sequence[tuple[str, bytes, bytes]]) -> str:
    return sha256_hex_from_framed_bytes(frame_record(domain, fields))


def _hash_field(name: str, value: str) -> tuple[str, bytes, bytes]:
    return _field(name, KIND_STRING, _string(value))


def _required_sha256(value: str | None) -> str:
    """Accept the repository's two hash spellings without changing them."""

    if type(value) is not str:
        raise ValueError("expected SHA-256 text")
    digest = value[7:] if value.startswith("sha256:") else value
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        raise ValueError("expected lowercase SHA-256 text")
    return value


def _required_nonempty_string(value: str | None) -> str:
    if type(value) is not str or not value:
        raise ValueError("expected non-empty string")
    return value


def _observed_identity_bytes(value: Task164ObservedIdentity) -> bytes:
    return frame_record(
        "TASK164_OBSERVED_IDENTITY_V1",
        (
            _hash_field("result_hash", value.result_hash),
            _hash_field("result_id", value.result_id.lower()),
            _hash_field("provenance_hash", value.provenance_hash),
        ),
    )


def _scenario_setup_bytes(value: Task164ScenarioSetup) -> bytes:
    return frame_record(
        "TASK164_SCENARIO_SETUP_V1",
        (
            _field("input_authority", KIND_ENUM, _enum(value.input_authority)),
            _field(
                "baffle_count",
                KIND_NONE if value.baffle_count is None else KIND_INT,
                b"" if value.baffle_count is None else _integer(value.baffle_count),
            ),
            _field(
                "tamper_target",
                KIND_NONE if value.tamper_target is None else KIND_ENUM,
                b"" if value.tamper_target is None else _enum(value.tamper_target),
            ),
            _field(
                "python_pair_key",
                KIND_NONE if value.python_pair_key is None else KIND_STRING,
                b"" if value.python_pair_key is None else _string(value.python_pair_key),
            ),
        ),
    )


def task163_validation_projection_bytes(value: Task163ValidationResult) -> bytes:
    """Return the bounded identity projection of a producer validation result."""

    fields: list[tuple[str, bytes, bytes]] = [
        _field("status", KIND_ENUM, _enum(value.status)),
    ]
    if value.valid is not None:
        result = value.valid
        fields.append(
            _nested(
                "valid_result_identity",
                frame_record(
                    "TASK164_TASK163_RESULT_IDENTITY_V1",
                    (
                        _hash_field("schema_version", result.schema_version),
                        _hash_field("task163_version", result.task163_version),
                        _hash_field("source_definition_id", result.source_definition_id),
                        _hash_field("request_hash", result.request_hash),
                        _hash_field("result_hash", result.result_hash),
                        _hash_field("result_id", str(result.result_id).lower()),
                        _hash_field("provenance_hash", result.provenance.provenance_hash),
                    ),
                ),
            )
        )
    elif value.typed_blocked is not None:
        blocked = value.typed_blocked
        fields.extend(
            (
                _hash_field("blocked_result_hash", blocked.blocked_result_hash),
                _field("blocked_result_id", KIND_STRING, _uuid_text(blocked.blocked_result_id)),
            )
        )
    elif value.raw_boundary_blocked is not None:
        raw_blocked = value.raw_boundary_blocked
        fields.extend(
            (
                _hash_field("blocked_result_hash", raw_blocked.blocked_result_hash),
                _field("blocked_result_id", KIND_STRING, _uuid_text(raw_blocked.blocked_result_id)),
            )
        )
    else:
        raise ValueError("validation result has no branch")
    return frame_record("TASK164_TASK163_VALIDATION_PROJECTION_V1", fields)


def _scenario_claim_bytes(value: Task164ScenarioClaim) -> bytes:
    original = (
        KIND_NONE,
        b"",
    )
    claimed = (
        KIND_NONE,
        b"",
    )
    if value.original_task163_request is not None:
        original = (KIND_RECORD, task163_request_projection_bytes(value.original_task163_request))
    if value.claimed_task163_validation_result is not None:
        claimed = (
            KIND_RECORD,
            task163_validation_projection_bytes(value.claimed_task163_validation_result),
        )
    return frame_record(
        "TASK164_SCENARIO_CLAIM_V1",
        (
            _field("scenario_id", KIND_ENUM, _enum(value.scenario_id)),
            _field("scenario_class", KIND_ENUM, _enum(value.scenario_class)),
            _field("required_for_acceptance", *_boolean(value.required_for_acceptance)),
            _nested("input_setup", _scenario_setup_bytes(value.input_setup)),
            _field("original_task163_request", *original),
            _field("claimed_task163_validation_result", *claimed),
            _field("expected_task163_branch", KIND_ENUM, _enum(value.expected_task163_branch)),
            _field("claimed_outcome", KIND_ENUM, _enum(value.claimed_outcome)),
            _field(
                "claimed_acceptance_categories",
                KIND_TUPLE,
                _tuple_enums(value.claimed_acceptance_categories),
            ),
            _field(
                "claimed_evidence_refs", KIND_TUPLE, _tuple_strings(value.claimed_evidence_refs)
            ),
        ),
    )


def task163_request_projection_bytes(value: object) -> bytes:
    """Project the original TASK163 request without serializing its contents."""

    from hexagent.exchangers.shell_tube.thermal_rating_composition.models import Task163Request

    if type(value) is not Task163Request:
        raise TypeError("expected exact Task163Request")
    task162 = task162_result_identity_projection(value.task162_result)
    replay = task162_success_replay_evidence_identity_projection(
        value.task162_success_replay_evidence
    )
    return frame_record(
        "TASK164_TASK163_REQUEST_PROJECTION_V1",
        (
            _hash_field("schema_version", value.schema_version),
            _hash_field("task163_version", value.task163_version),
            _hash_field("source_definition_id", value.source_definition_id),
            _nested("task162_result_identity", _task162_identity_bytes(task162)),
            _nested(
                "task162_success_replay_evidence_identity", _replay_evidence_identity_bytes(replay)
            ),
            _field("request_metadata_normalized", KIND_TUPLE, _tuple_pairs(value.request_metadata)),
        ),
    )


def task163_request_projection_hash(value: object) -> str:
    return sha256_hex_from_framed_bytes(task163_request_projection_bytes(value))


def task160_result_identity_bytes(value: object) -> bytes:
    return _task160_identity_bytes(task160_result_identity_projection(value))


def task161_result_identity_bytes(value: object) -> bytes:
    return _task161_identity_bytes(task161_result_identity_projection(value))


def task038_result_identity_bytes(value: object) -> bytes:
    return _task038_identity_bytes(task038_result_identity_projection(value))


def task162_result_identity_bytes(value: object) -> bytes:
    return _task162_identity_bytes(task162_result_identity_projection(value))


def task162_success_replay_evidence_identity_bytes(value: object) -> bytes:
    return _replay_evidence_identity_bytes(
        task162_success_replay_evidence_identity_projection(value)
    )


def _task160_identity_bytes(value: object) -> bytes:
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


def _task161_identity_bytes(value: object) -> bytes:
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


def _task038_identity_bytes(value: object) -> bytes:
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


def _task162_identity_bytes(value: object) -> bytes:
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


def _producer_pairs(values: Iterable[tuple[str, str]]) -> bytes:
    ordered = sorted(values, key=lambda item: (_string(item[0]), _string(item[1])))
    return _tuple_records(
        frame_record(
            "TASK163_STRING_PAIR_V1",
            (
                _field("key", KIND_STRING, _string(key)),
                _field("value", KIND_STRING, _string(item)),
            ),
        )
        for key, item in ordered
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
                _producer_pairs(value.original_task162_request_metadata),
            ),
        ),
    )


def task162_case_authority_identity(value: object) -> str:
    return sha256_hex_from_framed_bytes(case_authority_bytes(value))  # type: ignore[arg-type]


def request_canonical_bytes(value: Task164Request) -> bytes:
    claims = tuple(
        sorted(
            value.scenario_claims, key=lambda item: TASK164_SCENARIO_SOURCE_ORDER[item.scenario_id]
        )
    )
    return frame_record(
        TASK164_REQUEST_HASH_DOMAIN,
        (
            _hash_field("schema_version", value.schema_version),
            _hash_field("task164_version", value.task164_version),
            _hash_field("source_definition_id", value.source_definition_id),
            _nested(
                "original_task163_request_projection",
                task163_request_projection_bytes(value.original_task163_request),
            ),
            _nested(
                "claimed_task163_validation_result_projection",
                task163_validation_projection_bytes(value.claimed_task163_validation_result),
            ),
            _field(
                "scenario_claims_normalized",
                KIND_TUPLE,
                _tuple_records(_scenario_claim_bytes(item) for item in claims),
            ),
            _nested("repeat_run_claim", repeat_run_claim_bytes(value.repeat_run_claim)),
            _nested("python_parity_claim", python_parity_claim_bytes(value.python_parity_claim)),
            _nested(
                "evidence_package_claim", evidence_package_claim_bytes(value.evidence_package_claim)
            ),
            _field("request_metadata_normalized", KIND_TUPLE, _tuple_pairs(value.request_metadata)),
        ),
    )


def request_hash(value: Task164Request) -> str:
    return sha256_hex_from_framed_bytes(request_canonical_bytes(value))


def _surface_hash_bytes(value: Task164SurfaceHashRecord) -> bytes:
    return frame_record(
        "TASK164_SURFACE_HASH_RECORD_V1",
        (
            _field("surface", KIND_ENUM, _enum(value.surface)),
            _hash_field("sha256", value.sha256),
            _field("authority", KIND_ENUM, _enum(value.authority)),
            _field("evidence_ref", KIND_STRING, _string(value.evidence_ref)),
        ),
    )


def repeat_run_claim_bytes(value: Task164RepeatRunClaim) -> bytes:
    ordered = tuple(sorted(value.claimed_surface_records, key=lambda item: item.surface.value))
    return frame_record(
        "TASK164_REPEAT_RUN_CLAIM_V1",
        (
            _hash_field("schema_version", value.schema_version),
            _field("requested_run_count", KIND_INT, _integer(value.requested_run_count)),
            _field(
                "claimed_surface_records",
                KIND_TUPLE,
                _tuple_records(_surface_hash_bytes(item) for item in ordered),
            ),
            _field(
                "claimed_evidence_refs",
                KIND_TUPLE,
                _tuple_strings(sorted(value.claimed_evidence_refs, key=lambda item: _string(item))),
            ),
        ),
    )


def python_parity_claim_bytes(value: Task164PythonParityClaim) -> bytes:
    ordered = tuple(sorted(value.claimed_surface_records, key=lambda item: item.surface.value))
    return frame_record(
        "TASK164_PYTHON_PARITY_CLAIM_V1",
        (
            _hash_field("schema_version", value.schema_version),
            _field("requested_pair", KIND_TUPLE, _tuple_enums(value.requested_pair)),
            _field(
                "claimed_surface_records",
                KIND_TUPLE,
                _tuple_records(_surface_hash_bytes(item) for item in ordered),
            ),
            _field(
                "claimed_evidence_refs",
                KIND_TUPLE,
                _tuple_strings(sorted(value.claimed_evidence_refs, key=lambda item: _string(item))),
            ),
        ),
    )


def _replay_evidence_bytes(value: Task164Task163ReplayEvidence) -> bytes:
    return frame_record(
        "TASK164_TASK163_REPLAY_EVIDENCE_V1",
        (
            _field("scenario_id", KIND_ENUM, _enum(value.scenario_id)),
            _field(
                "producer_invocation_count", KIND_INT, _integer(value.producer_invocation_count)
            ),
            _hash_field("original_request_projection_hash", value.original_request_projection_hash),
            _field(
                "claimed_validation_projection_hash",
                *_none_or_string(value.claimed_validation_projection_hash),
            ),
            _hash_field(
                "replayed_validation_projection_hash", value.replayed_validation_projection_hash
            ),
            _field("replayed_branch", KIND_ENUM, _enum(value.replayed_branch)),
            _field(
                "replayed_result_hash_or_none", *_none_or_string(value.replayed_result_hash_or_none)
            ),
            _field(
                "replayed_result_id_or_none", *_none_or_string(value.replayed_result_id_or_none)
            ),
            _field(
                "replayed_provenance_hash_or_none",
                *_none_or_string(value.replayed_provenance_hash_or_none),
            ),
            _field(
                "applicability_projection_hash_or_none",
                *_none_or_string(value.applicability_projection_hash_or_none),
            ),
            _field(
                "completeness_projection_hash_or_none",
                *_none_or_string(value.completeness_projection_hash_or_none),
            ),
            _field("claim_match_status", KIND_ENUM, _enum(value.claim_match_status)),
            _field("evidence_refs", KIND_TUPLE, _tuple_strings(value.evidence_refs)),
        ),
    )


def _scenario_observation_bytes(value: Task164ScenarioObservation) -> bytes:
    identity = (
        (KIND_NONE, b"")
        if value.observed_task163_result_identity_or_none is None
        else (KIND_RECORD, _observed_identity_bytes(value.observed_task163_result_identity_or_none))
    )
    return frame_record(
        "TASK164_SCENARIO_OBSERVATION_V1",
        (
            _field("scenario_id", KIND_ENUM, _enum(value.scenario_id)),
            _field("real_task163_invoked", *_boolean(value.real_task163_invoked)),
            _field(
                "producer_invocation_count", KIND_INT, _integer(value.producer_invocation_count)
            ),
            _field("observed_task163_branch", KIND_ENUM, _enum(value.observed_task163_branch)),
            _field("observed_task163_result_identity_or_none", *identity),
            _field(
                "observed_task163_applicability_status_or_none",
                *_none_or_string(
                    value.observed_task163_applicability_status_or_none.value
                    if value.observed_task163_applicability_status_or_none is not None
                    else None
                ),
            ),
            _field(
                "observed_task163_completeness_status_or_none",
                *_none_or_string(
                    value.observed_task163_completeness_status_or_none.value
                    if value.observed_task163_completeness_status_or_none is not None
                    else None
                ),
            ),
            _field("observed_outcome", KIND_ENUM, _enum(value.observed_outcome)),
            _field("evidence_refs", KIND_TUPLE, _tuple_strings(value.evidence_refs)),
        ),
    )


def _acceptance_category_record_bytes(value: Task164AcceptanceCategoryRecord) -> bytes:
    return frame_record(
        "TASK164_ACCEPTANCE_CATEGORY_RECORD_V1",
        (
            _field("category", KIND_ENUM, _enum(value.category)),
            _field("status", KIND_ENUM, _enum(value.status)),
            _field("evidence_refs", KIND_TUPLE, _tuple_strings(value.evidence_refs)),
            _field(
                "failure_code_or_none",
                *_none_or_string(
                    value.failure_code_or_none.value if value.failure_code_or_none else None
                ),
            ),
        ),
    )


def _scenario_record_bytes(value: Task164ScenarioRecord) -> bytes:
    return frame_record(
        "TASK164_SCENARIO_RECORD_V1",
        (
            _field("scenario_id", KIND_ENUM, _enum(value.scenario_id)),
            _nested("claim", _scenario_claim_bytes(value.claim)),
            _nested("observation", _scenario_observation_bytes(value.observation)),
            _nested("replay_evidence", _replay_evidence_bytes(value.replay_evidence)),
            _field(
                "acceptance_records",
                KIND_TUPLE,
                _tuple_records(
                    _acceptance_category_record_bytes(item) for item in value.acceptance_records
                ),
            ),
            _field("status", KIND_ENUM, _enum(value.status)),
        ),
    )


def task163_evidence_bytes(value: Task164Task163Evidence) -> bytes:
    return frame_record(
        "TASK164_TASK163_EVIDENCE_V1",
        (
            _hash_field("original_request_projection_hash", value.original_request_projection_hash),
            _field(
                "replay_evidence",
                KIND_TUPLE,
                _tuple_records(_replay_evidence_bytes(item) for item in value.replay_evidence),
            ),
            _field(
                "accepted_result_identities",
                KIND_TUPLE,
                _tuple_records(
                    _observed_identity_bytes(item) for item in value.accepted_result_identities
                ),
            ),
            _field("status", KIND_ENUM, _enum(value.status)),
        ),
    )


def task163_replay_payload_bytes(value: Task164Task163Evidence) -> bytes:
    return frame_record(
        "TASK164_TASK163_REPLAY_PAYLOAD_V1",
        (
            _field(
                "replay_records",
                KIND_TUPLE,
                _tuple_records(_replay_evidence_bytes(item) for item in value.replay_evidence),
            ),
        ),
    )


def task163_identity_payload_bytes(value: Task164Task163Evidence) -> bytes:
    records = tuple(
        frame_record(
            "TASK164_TASK163_RESULT_IDENTITY_RECORD_V1",
            (
                _field("scenario_id", KIND_ENUM, _enum(TASK164_SCENARIO_IDS[index])),
                _hash_field("result_hash", identity.result_hash),
                _field("result_id", KIND_STRING, _string(identity.result_id.lower())),
                _hash_field("provenance_hash", identity.provenance_hash),
            ),
        )
        for index, identity in enumerate(value.accepted_result_identities)
    )
    return frame_record(
        "TASK164_TASK163_IDENTITY_PAYLOAD_V1",
        (("positive_result_identities", KIND_TUPLE, _tuple_records(records)),),
    )


def _task163_applicability_bytes(value: Task163Applicability) -> bytes:
    if type(value) is not Task163Applicability:
        raise TypeError("expected exact producer Task163Applicability")
    return frame_record(
        "TASK164_TASK163_APPLICABILITY_PAYLOAD_V1",
        (
            _field(
                "checks",
                KIND_TUPLE,
                _tuple_records(
                    frame_record(
                        "TASK164_TASK163_APPLICABILITY_CHECK_RECORD_V1",
                        (
                            _field("check_id", KIND_ENUM, _enum(name)),
                            _field("status", KIND_ENUM, _enum(status)),
                            _field("evidence_refs", KIND_TUPLE, _tuple_strings(())),
                            _field("failure_code_or_none", KIND_NONE, b""),
                        ),
                    )
                    for name, status in value.checks
                ),
            ),
        ),
    )


def _task163_completeness_bytes(value: Task163Completeness) -> bytes:
    if type(value) is not Task163Completeness:
        raise TypeError("expected exact producer Task163Completeness")
    return frame_record(
        "TASK164_TASK163_COMPLETENESS_PAYLOAD_V1",
        (
            _field("required_fields", KIND_TUPLE, _tuple_enums(value.required_fields)),
            _field("status", KIND_ENUM, _enum(value.status)),
        ),
    )


def task163_applicability_payload_bytes(value: Task163Applicability) -> bytes:
    return _task163_applicability_bytes(value)


def task163_completeness_payload_bytes(value: Task163Completeness) -> bytes:
    return _task163_completeness_bytes(value)


def task163_provenance_payload_bytes(
    value: Task164Task163Evidence,
    *,
    producer_result: Task163ValidationResult | None = None,
) -> bytes:
    """Project the producer's accepted provenance, never a local substitute."""

    if type(producer_result) is not Task163ValidationResult or producer_result.valid is None:
        raise ValueError("accepted Task163 result is required for provenance projection")
    producer = producer_result.valid
    graph = producer.provenance.graph
    result_nodes = tuple(
        node
        for node in graph.nodes
        if node.label == "TASK163_RESULT" and node.node_id == producer.result_id
    )
    if len(result_nodes) != 1 or producer.provenance.provenance_hash != graph.compute_hash():
        raise ValueError("producer provenance graph is not self-consistent")
    evidence_refs = tuple(
        sorted(
            {evidence_ref for item in value.replay_evidence for evidence_ref in item.evidence_refs},
            key=_string,
        )
    )
    return frame_record(
        "TASK164_TASK163_PROVENANCE_PAYLOAD_V1",
        (
            _hash_field("result_provenance_hash", producer.provenance.provenance_hash),
            _hash_field("graph_hash", graph.compute_hash()),
            _field("result_node_id", KIND_STRING, _uuid_text(result_nodes[0].node_id)),
            _field(
                "result_node_payload_hash",
                KIND_STRING,
                _string(result_nodes[0].payload_hash),
            ),
            _field("producer_evidence_refs", KIND_TUPLE, _tuple_strings(evidence_refs)),
        ),
    )


def main_delivery_payload_bytes(value: MainDeliveryObservation) -> bytes:
    """Canonicalize the trusted local-Git delivery observation.

    The observation is deliberately structural: callers cannot inject a
    free-form authority string into a payload wrapper.  The wrapper's
    authority is a registered ``Task164EvidenceAuthority`` value.
    """

    if value.provider_identity != "LOCAL_GIT_READONLY_V1":
        raise ValueError("main delivery provider identity is not registered")

    return frame_record(
        "TASK164_MAIN_DELIVERY_PAYLOAD_V1",
        (
            _field("provider_identity", KIND_ENUM, _enum(value.provider_identity)),
            _hash_field("predecessor_base_sha", value.predecessor_base_sha),
            _hash_field("predecessor_base_tree", value.predecessor_base_tree),
            _hash_field("observed_head_sha", value.observed_head_sha),
            _hash_field("observed_head_tree", value.observed_head_tree),
            _field("predecessor_is_ancestor", *_boolean(value.predecessor_is_ancestor)),
            _field("changed_paths", KIND_TUPLE, _tuple_strings(value.changed_paths)),
            _field("allowed_paths", KIND_TUPLE, _tuple_strings(value.allowed_paths)),
            _field("tracked_worktree_clean", *_boolean(value.tracked_worktree_clean)),
            _field("status", KIND_ENUM, _enum(value.status)),
        ),
    )


def determinism_evidence_bytes(value: Task164DeterminismEvidence) -> bytes:
    return frame_record(
        "TASK164_DETERMINISM_EVIDENCE_V1",
        (
            _nested(
                "repeat_run_observation", repeat_run_observation_bytes(value.repeat_run_observation)
            ),
            _nested(
                "dual_runtime_observation",
                dual_runtime_observation_bytes(value.dual_runtime_observation),
            ),
            _field("status", KIND_ENUM, _enum(value.status)),
        ),
    )


def _repeat_surface_order(value: Task164SurfaceHashRecord) -> int:
    if type(value.surface) is not Task164RepeatRunSurface:
        raise ValueError("repeat-run observation contains a non-repeat surface")
    return tuple(Task164RepeatRunSurface).index(value.surface)


def repeat_run_observation_bytes(value: Task164RepeatRunObservation) -> bytes:
    ordered = tuple(sorted(value.surface_records, key=_repeat_surface_order))
    return frame_record(
        "TASK164_REPEAT_RUN_OBSERVATION_V1",
        (
            _field("run_count", KIND_INT, _integer(value.run_count)),
            _field(
                "surface_records",
                KIND_TUPLE,
                _tuple_records(_surface_hash_bytes(item) for item in ordered),
            ),
            _field("observed_equal", *_boolean(value.observed_equal)),
            _field("status", KIND_ENUM, _enum(value.status)),
            _field("evidence_refs", KIND_TUPLE, _tuple_strings(value.evidence_refs)),
        ),
    )


def _runtime_observation_bytes(value: Task164RuntimeObservation) -> bytes:
    return frame_record(
        "TASK164_RUNTIME_OBSERVATION_V1",
        (
            _field("python_version", KIND_ENUM, _enum(value.python_version)),
            _hash_field("head_sha", value.head_sha),
            _hash_field("head_tree", value.head_tree),
            _field("runner_identity", KIND_ENUM, _enum(value.runner_identity)),
            _field("command_identity", KIND_ENUM, _enum(value.command_identity)),
            _field(
                "surface_records",
                KIND_TUPLE,
                _tuple_records(_surface_hash_bytes(item) for item in value.surface_records),
            ),
            _hash_field("child_output_sha256", value.child_output_sha256),
            _field("conclusion", KIND_ENUM, _enum(value.conclusion)),
        ),
    )


def dual_runtime_observation_bytes(value: Task164DualRuntimeObservation) -> bytes:
    return frame_record(
        "TASK164_DUAL_RUNTIME_OBSERVATION_V1",
        (
            _field("pairing_key", KIND_ENUM, _enum(value.pairing_key)),
            _nested(
                "python311_observation", _runtime_observation_bytes(value.python311_observation)
            ),
            _nested(
                "python312_observation", _runtime_observation_bytes(value.python312_observation)
            ),
            _field("status", KIND_ENUM, _enum(value.status)),
            _field("evidence_refs", KIND_TUPLE, _tuple_strings(value.evidence_refs)),
        ),
    )


def terminal_capability_bytes(value: Task164TerminalCapability) -> bytes:
    return frame_record(
        "TASK164_TERMINAL_CAPABILITY_PAYLOAD_V1",
        (
            _field("capability_id", KIND_ENUM, _enum(value.capability_id)),
            _field("construction_family", KIND_ENUM, _enum(value.construction_family)),
            _field("shell_pass_count", KIND_INT, _integer(value.shell_pass_count)),
            _field("tube_pass_count", KIND_INT, _integer(value.tube_pass_count)),
            _field("case_binding", KIND_ENUM, _enum(value.case_binding)),
            _field("method_authority", KIND_ENUM, _enum(value.method_authority)),
            _field("rating_output_authority", KIND_ENUM, _enum(value.rating_output_authority)),
            _field("status", KIND_ENUM, _enum(value.status)),
        ),
    )


def _applicability_record_bytes(value: Task164ApplicabilityRecord) -> bytes:
    return frame_record(
        "TASK164_APPLICABILITY_RECORD_V1",
        (
            _field("check", KIND_ENUM, _enum(value.check)),
            _field("status", KIND_ENUM, _enum(value.status)),
            _field("evidence_refs", KIND_TUPLE, _tuple_strings(value.evidence_refs)),
            _field(
                "failure_code_or_none",
                *_none_or_string(
                    value.failure_code_or_none.value if value.failure_code_or_none else None
                ),
            ),
        ),
    )


def applicability_bytes(value: Task164Applicability) -> bytes:
    return frame_record(
        "TASK164_APPLICABILITY_V1",
        (
            _field(
                "records",
                KIND_TUPLE,
                _tuple_records(_applicability_record_bytes(item) for item in value.records),
            ),
            _field("status", KIND_ENUM, _enum(value.status)),
        ),
    )


def completeness_bytes(value: Task164Completeness) -> bytes:
    return frame_record(
        "TASK164_COMPLETENESS_V1",
        (
            _field("required_items", KIND_TUPLE, _tuple_enums(value.required_items)),
            _field("status", KIND_ENUM, _enum(value.status)),
        ),
    )


def demonstration_bytes(value: Task164DemonstrationCoverage) -> bytes:
    ordered = tuple(
        sorted(
            value.scenario_records, key=lambda item: TASK164_SCENARIO_SOURCE_ORDER[item.scenario_id]
        )
    )
    return frame_record(
        "TASK164_DEMONSTRATION_COVERAGE_V1",
        (
            _field("required_scenario_ids", KIND_TUPLE, _tuple_enums(value.required_scenario_ids)),
            _field(
                "scenario_records",
                KIND_TUPLE,
                _tuple_records(_scenario_record_bytes(item) for item in ordered),
            ),
            _field("positive_count", KIND_INT, _integer(value.positive_count)),
            _field("negative_count", KIND_INT, _integer(value.negative_count)),
            _field("determinism_count", KIND_INT, _integer(value.determinism_count)),
            _field("scope_fence_count", KIND_INT, _integer(value.scope_fence_count)),
            _field("status", KIND_ENUM, _enum(value.status)),
        ),
    )


def positive_demonstration_payload_bytes(
    values: Iterable[Task164ScenarioRecord],
) -> bytes:
    records = tuple(
        frame_record(
            "TASK164_POSITIVE_DEMONSTRATION_RECORD_V1",
            (
                _field("scenario_id", KIND_ENUM, _enum(item.scenario_id)),
                _hash_field(
                    "result_hash",
                    _required_sha256(item.replay_evidence.replayed_result_hash_or_none),
                ),
                _field(
                    "result_id",
                    KIND_STRING,
                    _string(
                        _required_nonempty_string(
                            item.replay_evidence.replayed_result_id_or_none
                        ).lower()
                    ),
                ),
                _hash_field(
                    "provenance_hash",
                    _required_sha256(item.replay_evidence.replayed_provenance_hash_or_none),
                ),
                _field(
                    "applicability_status",
                    *_none_or_string(
                        item.observation.observed_task163_applicability_status_or_none.value
                        if item.observation.observed_task163_applicability_status_or_none
                        is not None
                        else None
                    ),
                ),
                _field(
                    "completeness_status",
                    *_none_or_string(
                        item.observation.observed_task163_completeness_status_or_none.value
                        if item.observation.observed_task163_completeness_status_or_none is not None
                        else None
                    ),
                ),
                _field("terminal_status", KIND_ENUM, _enum(item.status)),
                _field("outcome", KIND_ENUM, _enum(item.observation.observed_outcome)),
                _field("evidence_refs", KIND_TUPLE, _tuple_strings(item.observation.evidence_refs)),
            ),
        )
        for item in values
        if item.scenario_id in TASK164_SCENARIO_IDS[:5]
    )
    return frame_record(
        "TASK164_POSITIVE_DEMONSTRATION_PAYLOAD_V1",
        (("scenario_records", KIND_TUPLE, _tuple_records(records)),),
    )


def negative_demonstration_payload_bytes(
    values: Iterable[Task164ScenarioRecord],
    *,
    observed_diagnostics: Mapping[Task164ScenarioId, object] | None = None,
) -> bytes:
    selected = tuple(item for item in values if item.scenario_id in TASK164_SCENARIO_IDS[5:9])
    if observed_diagnostics is None:
        from .scenarios import diagnostic_for_record

        observed_diagnostics = {item.scenario_id: diagnostic_for_record(item) for item in selected}

    def diagnostic(item: Task164ScenarioRecord) -> tuple[Task164FailureStage, Task164FailureCode]:
        value = observed_diagnostics.get(item.scenario_id)
        if value is None:
            raise ValueError("missing observed scenario diagnostic")
        stage = getattr(value, "stage", None)
        code = getattr(value, "code", None)
        if type(stage) is not Task164FailureStage or type(code) is not Task164FailureCode:
            raise TypeError("invalid observed scenario diagnostic")
        return stage, code

    records = tuple(
        frame_record(
            "TASK164_NEGATIVE_DEMONSTRATION_RECORD_V1",
            (
                _field("scenario_id", KIND_ENUM, _enum(item.scenario_id)),
                _field(
                    "expected_failure_stage",
                    KIND_ENUM,
                    _enum(diagnostic(item)[0]),
                ),
                _field("observed_failure_code", KIND_ENUM, _enum(diagnostic(item)[1])),
                _field("outcome", KIND_ENUM, _enum(item.observation.observed_outcome)),
                _field("evidence_refs", KIND_TUPLE, _tuple_strings(item.observation.evidence_refs)),
            ),
        )
        for item in selected
    )
    return frame_record(
        "TASK164_NEGATIVE_DEMONSTRATION_PAYLOAD_V1",
        (("scenario_records", KIND_TUPLE, _tuple_records(records)),),
    )


def repeat_run_payload_bytes(
    value: Task164DeterminismEvidence | Task164RepeatRunObservation,
) -> bytes:
    observation = (
        value.repeat_run_observation if isinstance(value, Task164DeterminismEvidence) else value
    )
    ordered = tuple(sorted(observation.surface_records, key=_repeat_surface_order))
    return frame_record(
        "TASK164_REPEAT_RUN_PAYLOAD_V1",
        (
            _field("run_count", KIND_INT, _integer(observation.run_count)),
            _field(
                "surface_records",
                KIND_TUPLE,
                _tuple_records(_surface_hash_bytes(item) for item in ordered),
            ),
            _field("observed_equal", *_boolean(observation.observed_equal)),
            _field("status", KIND_ENUM, _enum(observation.status)),
        ),
    )


def python_parity_payload_bytes(value: Task164DeterminismEvidence) -> bytes:
    first = value.dual_runtime_observation.python311_observation
    second = value.dual_runtime_observation.python312_observation
    surfaces = tuple(item.surface for item in first.surface_records)
    return frame_record(
        "TASK164_PYTHON_PARITY_PAYLOAD_V1",
        (
            _field(
                "pairing_key",
                KIND_ENUM,
                _enum(value.dual_runtime_observation.pairing_key),
            ),
            _hash_field("verified_head_sha", first.head_sha),
            _hash_field("verified_head_tree", first.head_tree),
            _field(
                "python311_runtime_identity",
                KIND_STRING,
                _string(runtime_identity_for_version(first.python_version)),
            ),
            _field(
                "python312_runtime_identity",
                KIND_STRING,
                _string(runtime_identity_for_version(second.python_version)),
            ),
            _field("surfaces", KIND_TUPLE, _tuple_enums(surfaces)),
            _hash_field("child311_digest", first.child_output_sha256),
            _hash_field("child312_digest", second.child_output_sha256),
            _field(
                "equality_rule",
                KIND_ENUM,
                _string("ALL_DECLARED_SURFACES_AND_DIGESTS_EQUAL"),
            ),
            _field("status", KIND_ENUM, _enum(value.dual_runtime_observation.status)),
        ),
    )


def scenario_matrix_bytes(values: Iterable[Task164ScenarioRecord]) -> bytes:
    """Canonicalize the fixed scenario records in matrix order."""

    ordered = tuple(
        sorted(values, key=lambda item: TASK164_SCENARIO_SOURCE_ORDER[item.scenario_id])
    )
    return frame_record(
        "TASK164_SCENARIO_MATRIX_V1",
        (
            _field(
                "scenario_records",
                KIND_TUPLE,
                _tuple_records(_scenario_record_bytes(item) for item in ordered),
            ),
        ),
    )


def scope_fence_bytes(value: Task164ScopeFenceEvidence) -> bytes:
    return frame_record(
        "TASK164_SCOPE_FENCE_PAYLOAD_V1",
        (
            _field(
                "forbidden_capability_tokens",
                KIND_TUPLE,
                _tuple_enums(value.forbidden_capability_tokens_absent),
            ),
            _field(
                "forbidden_formula_surface_absent",
                *_boolean(value.forbidden_formula_surface_absent),
            ),
            _field("upstream_replay_absent", *_boolean(value.upstream_replay_absent)),
            _field(
                "private_upstream_access_absent", *_boolean(value.private_upstream_access_absent)
            ),
            _field("task165_absent", *_boolean(value.task165_absent)),
            _field("status", KIND_ENUM, _enum(value.status)),
        ),
    )


def evidence_payload_bytes(value: Task164EvidencePayload) -> bytes:
    return frame_record(
        "TASK164_EVIDENCE_PAYLOAD_WRAPPER_V1",
        (
            _field("payload_kind", KIND_ENUM, _enum(value.payload_kind)),
            _field("category", KIND_ENUM, _enum(value.category)),
            _field("authority", KIND_ENUM, _enum(value.authority)),
            _hash_field("payload_sha256", value.payload_sha256),
            _field("canonical_payload_bytes", KIND_BYTES, value.canonical_payload_bytes),
            _field("evidence_refs", KIND_TUPLE, _tuple_strings(value.evidence_refs)),
        ),
    )


def artifact_bytes(value: Task164ArtifactRecord) -> bytes:
    return frame_record(
        "TASK164_ARTIFACT_RECORD_V1",
        (
            _field("artifact_id", KIND_ENUM, _enum(value.artifact_id)),
            _field("media_kind", KIND_ENUM, _enum(value.media_kind)),
            _hash_field("canonical_payload_hash", value.canonical_payload_hash),
            _field("authority", KIND_ENUM, _enum(value.authority)),
            _field("evidence_refs", KIND_TUPLE, _tuple_strings(value.evidence_refs)),
        ),
    )


def evidence_package_bytes(value: Task164EvidencePackage) -> bytes:
    payload_fields = (
        ("authority_evidence", value.authority_evidence),
        ("main_delivery_evidence", value.main_delivery_evidence),
        ("task163_replay_evidence", value.task163_replay_evidence),
        ("task163_identity_evidence", value.task163_identity_evidence),
        ("task163_applicability_evidence", value.task163_applicability_evidence),
        ("task163_completeness_evidence", value.task163_completeness_evidence),
        ("task163_provenance_evidence", value.task163_provenance_evidence),
        ("terminal_capability_evidence", value.terminal_capability_evidence),
        ("positive_demo_evidence", value.positive_demo_evidence),
        ("negative_demo_evidence", value.negative_demo_evidence),
        ("repeat_run_evidence", value.repeat_run_evidence),
        ("cross_python_evidence", value.cross_python_evidence),
        ("scope_fence_evidence", value.scope_fence_evidence),
    )
    return frame_record(
        "TASK164_EVIDENCE_PACKAGE_V1",
        (
            _hash_field("package_schema_version", value.package_schema_version),
            _hash_field("package_version", value.package_version),
            *(_nested(name, evidence_payload_bytes(payload)) for name, payload in payload_fields),
            _field(
                "artifact_inventory",
                KIND_TUPLE,
                _tuple_records(artifact_bytes(item) for item in value.artifact_inventory),
            ),
        ),
    )


def evidence_package_claim_bytes(value: Task164EvidencePackageClaim) -> bytes:
    ordered = tuple(sorted(value.claimed_category_payload_hashes, key=lambda item: item[0].value))
    category_records = tuple(
        frame_record(
            "TASK164_CATEGORY_HASH_V1",
            (
                _field("category", KIND_ENUM, _enum(category)),
                _hash_field("payload_hash", payload_hash),
            ),
        )
        for category, payload_hash in ordered
    )
    return frame_record(
        "TASK164_EVIDENCE_PACKAGE_CLAIM_V1",
        (
            _hash_field("package_schema_version", value.package_schema_version),
            _hash_field("package_version", value.package_version),
            _field("claimed_category_payload_hashes", KIND_TUPLE, _tuple_records(category_records)),
            _field(
                "claimed_artifact_records",
                KIND_TUPLE,
                _tuple_records(artifact_bytes(item) for item in value.claimed_artifact_records),
            ),
            _field("claimed_package_hash", *_none_or_string(value.claimed_package_hash)),
            _field(
                "claimed_evidence_refs", KIND_TUPLE, _tuple_strings(value.claimed_evidence_refs)
            ),
        ),
    )


def acceptance_ledger_bytes(value: Task164AcceptanceLedger) -> bytes:
    return frame_record(
        "TASK164_ACCEPTANCE_LEDGER_V1",
        (
            _field(
                "records",
                KIND_TUPLE,
                _tuple_records(_acceptance_category_record_bytes(item) for item in value.records),
            ),
            _hash_field("package_hash", value.package_hash),
            _field("status", KIND_ENUM, _enum(value.status)),
        ),
    )


def semantic_inputs_bytes(value: Task164ProvenanceSemanticInputs) -> bytes:
    return frame_record(
        "TASK164_PROVENANCE_SEMANTIC_INPUTS_V1",
        tuple(
            _hash_field(name, getattr(value, name))
            for name in (
                "source_authority_payload_hash",
                "task163_evidence_payload_hash",
                "scenario_matrix_payload_hash",
                "determinism_payload_hash",
                "acceptance_ledger_payload_hash",
                "evidence_package_payload_hash",
            )
        ),
    )


def _task163_result_hash_projection(result: object) -> bytes:
    return task163_validation_projection_bytes(result)  # type: ignore[arg-type]


def _result_fields(
    value: Task164PreResultIdentityInputs,
) -> tuple[tuple[str, bytes, bytes], ...]:
    return (
        _hash_field("schema_version", value.schema_version),
        _hash_field("task164_version", value.task164_version),
        _hash_field("implementation_software_version", value.implementation_software_version),
        _hash_field("source_definition_id", value.source_definition_id),
        _hash_field("request_hash", value.request_hash),
        _field(
            "original_task163_request_projection",
            KIND_RECORD,
            value.original_task163_request_projection,
        ),
        _nested("task163_evidence", task163_evidence_bytes(value.task163_evidence)),
        _field(
            "scenario_evidence",
            KIND_TUPLE,
            _tuple_records(_scenario_record_bytes(item) for item in value.scenario_evidence),
        ),
        _nested("determinism_evidence", determinism_evidence_bytes(value.determinism_evidence)),
        _nested("terminal_capability", terminal_capability_bytes(value.terminal_capability)),
        _nested("demonstration_coverage", demonstration_bytes(value.demonstration_coverage)),
        _nested("scope_fence_evidence", scope_fence_bytes(value.scope_fence_evidence)),
        _nested("applicability", applicability_bytes(value.applicability)),
        _nested("completeness", completeness_bytes(value.completeness)),
        _nested("evidence_package", evidence_package_bytes(value.evidence_package)),
        _nested("acceptance_ledger", acceptance_ledger_bytes(value.acceptance_ledger)),
        _field("warnings_normalized", KIND_TUPLE, _tuple_values(())),
        _field(
            "blockers_normalized",
            KIND_TUPLE,
            _tuple_records(_blocker_bytes(item) for item in value.blockers_normalized),
        ),
        _nested(
            "provenance_semantic_inputs", semantic_inputs_bytes(value.provenance_semantic_inputs)
        ),
    )


def _blocker_bytes(value: Task164Blocker) -> bytes:
    return frame_record(
        "TASK164_BLOCKER_V1",
        (
            _field("stage", KIND_ENUM, _enum(value.stage)),
            _field("code", KIND_ENUM, _enum(value.code)),
            _field("evidence_refs", KIND_TUPLE, _tuple_strings(value.evidence_refs)),
        ),
    )


def success_canonical_bytes(value: Task164PreResultIdentityInputs) -> bytes:
    fields = _result_fields(value)
    if tuple(name for name, _, _ in fields) != TASK164_SUCCESS_PREIMAGE_FIELD_ORDER:
        raise AssertionError("TASK164 success preimage order drift")
    return frame_record(TASK164_SUCCESS_HASH_DOMAIN, fields)


def success_hash_from_inputs(value: Task164PreResultIdentityInputs) -> str:
    return sha256_hex_from_framed_bytes(success_canonical_bytes(value))


def result_id(result_hash: str) -> UUID:
    return uuid5(TASK164_RESULT_ID_NAMESPACE, TASK164_RESULT_ID_PREFIX + result_hash)


def typed_blocked_canonical_bytes(value: Task164TypedBlockedResult) -> bytes:
    return frame_record(
        TASK164_TYPED_BLOCKED_HASH_DOMAIN,
        (
            _hash_field("schema_version", value.schema_version),
            _hash_field("task164_version", value.task164_version),
            _hash_field("implementation_software_version", value.implementation_software_version),
            _field("failure_stage", KIND_ENUM, _enum(value.failure_stage)),
            _hash_field("request_hash", value.request_hash),
            _field(
                "original_task163_request_projection_hash_or_none",
                *_none_or_string(value.original_task163_request_projection_hash_or_none),
            ),
            _field(
                "blockers_normalized",
                KIND_TUPLE,
                _tuple_records(_blocker_bytes(item) for item in value.blockers),
            ),
            _field("warnings_normalized", KIND_TUPLE, _tuple_values(())),
        ),
    )


def typed_blocked_hash(value: Task164TypedBlockedResult) -> str:
    return sha256_hex_from_framed_bytes(typed_blocked_canonical_bytes(value))


def typed_blocked_id(blocked_hash: str) -> UUID:
    return uuid5(TASK164_TYPED_BLOCKED_ID_NAMESPACE, TASK164_TYPED_BLOCKED_ID_PREFIX + blocked_hash)


def raw_projection_node_bytes(value: Task164RawProjectionNode) -> bytes:
    children = value.children
    if value.kind is Task164RawProjectionKind.RECORD:
        children = tuple(
            sorted(
                children,
                key=lambda item: (_string(item.field_name), raw_projection_node_bytes(item)),
            )
        )
    return frame_record(
        "TASK164_RAW_PROJECTION_NODE_V1",
        (
            _field("field_name", KIND_STRING, _string(value.field_name)),
            _field("kind", KIND_ENUM, _enum(value.kind)),
            _field("type_identity", *_none_or_string(value.type_identity)),
            _field("scalar_payload", *_none_or_string(value.scalar_payload)),
            _field(
                "children",
                KIND_TUPLE,
                _tuple_records(raw_projection_node_bytes(item) for item in children),
            ),
        ),
    )


canonical_projected_node_bytes = raw_projection_node_bytes


def raw_request_projection_bytes(value: Task164RawRequestProjection) -> bytes:
    return frame_record(
        "TASK164_RAW_PROJECTION_V1",
        (
            _hash_field("schema_version", value.schema_version),
            _field("root", KIND_RECORD, raw_projection_node_bytes(value.root)),
        ),
    )


def raw_request_projection_hash(value: Task164RawRequestProjection) -> str:
    return sha256_hex_from_framed_bytes(raw_request_projection_bytes(value))


def raw_blocked_canonical_bytes(value: Task164RawBoundaryBlockedResult) -> bytes:
    return frame_record(
        TASK164_RAW_BLOCKED_HASH_DOMAIN,
        (
            _hash_field("schema_version", value.schema_version),
            _hash_field("task164_version", value.task164_version),
            _hash_field("implementation_software_version", value.implementation_software_version),
            _field("failure_stage", KIND_ENUM, _enum(value.failure_stage)),
            _field(
                "raw_request_projection",
                KIND_RECORD,
                raw_request_projection_bytes(value.raw_request_projection),
            ),
            _hash_field("raw_request_projection_hash", value.raw_request_projection_hash),
            _field(
                "blockers_normalized",
                KIND_TUPLE,
                _tuple_records(_blocker_bytes(item) for item in value.blockers),
            ),
            _field("warnings_normalized", KIND_TUPLE, _tuple_values(())),
        ),
    )


def raw_blocked_hash(value: Task164RawBoundaryBlockedResult) -> str:
    return sha256_hex_from_framed_bytes(raw_blocked_canonical_bytes(value))


def raw_blocked_id(blocked_hash: str) -> UUID:
    return uuid5(TASK164_RAW_BLOCKED_ID_NAMESPACE, TASK164_RAW_BLOCKED_ID_PREFIX + blocked_hash)


def provenance_graph_bytes(graph: ProvenanceGraph) -> bytes:
    nodes = sorted(graph.nodes, key=lambda node: (node.node_type.value, str(node.node_id).lower()))
    edges = sorted(
        graph.edges,
        key=lambda edge: (str(edge.source_id).lower(), str(edge.target_id).lower(), edge.relation),
    )
    node_bytes = (
        frame_record(
            "TASK164_PROVENANCE_NODE_V1",
            (
                _field("node_id", KIND_STRING, _uuid_text(node.node_id)),
                _field("node_type", KIND_ENUM, _enum(node.node_type)),
                _field("label", KIND_STRING, _string(node.label)),
                _field("payload_hash", KIND_STRING, _string(node.payload_hash)),
            ),
        )
        for node in nodes
    )
    edge_bytes = (
        frame_record(
            "TASK164_PROVENANCE_EDGE_V1",
            (
                _field("source_id", KIND_STRING, _uuid_text(edge.source_id)),
                _field("target_id", KIND_STRING, _uuid_text(edge.target_id)),
                _field("relation", KIND_STRING, _string(edge.relation)),
            ),
        )
        for edge in edges
    )
    return frame_record(
        "TASK164_PROVENANCE_GRAPH_V1",
        (
            _field("schema_version", KIND_STRING, _string(graph.schema_version)),
            _field("nodes", KIND_TUPLE, _tuple_records(node_bytes)),
            _field("edges", KIND_TUPLE, _tuple_records(edge_bytes)),
        ),
    )


def provenance_hash(graph: ProvenanceGraph) -> str:
    return sha256_hex_from_framed_bytes(provenance_graph_bytes(graph))


__all__ = [
    "TASK164_REQUEST_FIELD_ORDER",
    "TASK164_SUCCESS_PREIMAGE_FIELD_ORDER",
    "canonical_projected_node_bytes",
    "case_authority_bytes",
    "completeness_bytes",
    "demonstration_bytes",
    "determinism_evidence_bytes",
    "dual_runtime_observation_bytes",
    "evidence_package_bytes",
    "evidence_package_claim_bytes",
    "evidence_payload_bytes",
    "frame_record",
    "frame_tuple",
    "frame_value",
    "provenance_graph_bytes",
    "provenance_hash",
    "raw_blocked_canonical_bytes",
    "raw_blocked_hash",
    "raw_blocked_id",
    "raw_projection_node_bytes",
    "raw_request_projection_bytes",
    "raw_request_projection_hash",
    "request_canonical_bytes",
    "request_hash",
    "result_id",
    "scenario_matrix_bytes",
    "sha256_hex_from_framed_bytes",
    "success_canonical_bytes",
    "main_delivery_payload_bytes",
    "success_hash_from_inputs",
    "task038_result_identity_bytes",
    "task160_result_identity_bytes",
    "task161_result_identity_bytes",
    "task162_case_authority_identity",
    "task162_result_identity_bytes",
    "task162_success_replay_evidence_identity_bytes",
    "task163_request_projection_bytes",
    "task163_request_projection_hash",
    "task163_replay_payload_bytes",
    "task163_identity_payload_bytes",
    "task163_applicability_payload_bytes",
    "task163_completeness_payload_bytes",
    "task163_provenance_payload_bytes",
    "task163_validation_projection_bytes",
    "positive_demonstration_payload_bytes",
    "negative_demonstration_payload_bytes",
    "repeat_run_payload_bytes",
    "python_parity_payload_bytes",
    "typed_blocked_canonical_bytes",
    "typed_blocked_hash",
    "typed_blocked_id",
]
