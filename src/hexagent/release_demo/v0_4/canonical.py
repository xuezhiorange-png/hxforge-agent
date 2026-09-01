"""TASK039 fixed-width canonical codec and identity helpers.

The codec has no dependence on mapping iteration for identity-bearing fields:
callers provide the ordered field tuple for every record.  It intentionally
rejects binary floats, unordered collections, object representations and
implicit string conversion.
"""

from __future__ import annotations

import dataclasses
import hashlib
import math
import struct
import uuid
from collections.abc import Mapping, Sequence
from decimal import Decimal
from enum import Enum
from typing import Any

from .schema import (
    ACCEPTANCE_CHECKLIST_FIELDS,
    ACCEPTANCE_ITEM_FIELDS,
    ACCEPTANCE_LEDGER_FIELDS,
    BLOCKER_ENTRY_FIELDS,
    HISTORICAL_AUTHORITY_FIELDS,
    MANIFEST_RUNTIME_FIELDS,
    PROVENANCE_FULL_FIELDS,
    PROVENANCE_NAMESPACE,
    PROVENANCE_PREHASH_FIELDS,
    RESULT_NAMESPACE,
    RESULT_PREHASH_FIELDS,
    UUID_NAME_PREFIX,
    UUID_NAMESPACE,
    WARNING_ENTRY_FIELDS,
)

KIND_NONE = "NONE"
KIND_BOOL_TRUE = "BOOL_TRUE"
KIND_BOOL_FALSE = "BOOL_FALSE"
KIND_INT = "INT"
KIND_STRING = "STRING"
KIND_BYTES = "BYTES"
KIND_DECIMAL = "DECIMAL"
KIND_ENUM = "ENUM"
KIND_TUPLE = "TUPLE"
KIND_RECORD = "RECORD"


@dataclasses.dataclass(frozen=True)
class CanonicalSpec:
    """A closed recursive field/kind projection for identity-bearing data."""

    kind: str
    namespace: str | None = None
    fields: tuple[str, ...] = ()
    kinds: tuple[tuple[str, Any], ...] = ()
    item_spec: Any = None


def record_spec(
    namespace: str,
    fields: Sequence[str],
    kinds: Mapping[str, Any] | None = None,
) -> CanonicalSpec:
    ordered = tuple(fields)
    return CanonicalSpec(
        kind=KIND_RECORD,
        namespace=namespace,
        fields=ordered,
        kinds=tuple((name, (kinds or {}).get(name)) for name in ordered),
    )


def tuple_spec(item_spec: Any = None) -> CanonicalSpec:
    return CanonicalSpec(kind=KIND_TUPLE, item_spec=item_spec)


class CanonicalizationError(ValueError):
    """Raised when a value is outside the TASK039 canonical domain."""


def _u32(value: int) -> bytes:
    if value < 0 or value > 0xFFFFFFFF:
        raise CanonicalizationError("U32 value out of range")
    return struct.pack(">I", value)


def _u64(value: int) -> bytes:
    if value < 0 or value > 0xFFFFFFFFFFFFFFFF:
        raise CanonicalizationError("U64 value out of range")
    return struct.pack(">Q", value)


def _ascii(value: str, label: str) -> bytes:
    try:
        return value.encode("ascii")
    except UnicodeEncodeError as exc:
        raise CanonicalizationError(f"{label} must be ASCII") from exc


def frame(kind: str, payload: bytes) -> bytes:
    """Encode one frozen ``FRAME``."""

    kind_bytes = _ascii(kind, "canonical kind")
    return _u32(len(kind_bytes)) + kind_bytes + _u64(len(payload)) + payload


def frame_string(value: str) -> bytes:
    if type(value) is not str:
        raise CanonicalizationError("STRING requires exact str")
    return frame(KIND_STRING, value.encode("utf-8"))


def _record_value(record: Any, field: str) -> Any:
    if isinstance(record, Mapping):
        if field not in record:
            raise CanonicalizationError(f"missing canonical field: {field}")
        return record[field]
    try:
        return getattr(record, field)
    except AttributeError as exc:
        raise CanonicalizationError(f"missing canonical field: {field}") from exc


def _primitive(value: Any) -> Any:
    if value is None or type(value) is bool or type(value) is int or type(value) is str:
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise CanonicalizationError("non-finite Decimal is forbidden")
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise CanonicalizationError("non-finite float is forbidden")
        raise CanonicalizationError("binary float is forbidden")
    if isinstance(value, (set, frozenset)):
        raise CanonicalizationError("set/frozenset is forbidden")
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _primitive(getattr(value, field.name))
            for field in dataclasses.fields(value)
        }
    if isinstance(value, Mapping):
        if any(type(key) is not str for key in value):
            raise CanonicalizationError("mapping keys must be exact str")
        # This projection is for untyped evidence display only.  Identity
        # records use record_bytes with an explicit field tuple.
        return {key: _primitive(value[key]) for key in sorted(value)}
    if isinstance(value, (tuple, list)):
        return [_primitive(item) for item in value]
    if isinstance(value, bytes):
        return value
    raise CanonicalizationError(f"unsupported canonical value: {type(value).__name__}")


def _infer_kind(value: Any) -> str:
    if value is None:
        return KIND_NONE
    if type(value) is bool:
        return KIND_BOOL_TRUE if value else KIND_BOOL_FALSE
    if type(value) is int:
        return KIND_INT
    if type(value) is str:
        return KIND_STRING
    if isinstance(value, bytes):
        return KIND_BYTES
    if isinstance(value, Decimal):
        return KIND_DECIMAL
    if isinstance(value, Enum):
        return KIND_ENUM
    if isinstance(value, (tuple, list)):
        return KIND_TUPLE
    if isinstance(value, Mapping) or dataclasses.is_dataclass(value):
        return KIND_RECORD
    raise CanonicalizationError(f"cannot infer canonical kind for {type(value).__name__}")


def frame_value(
    value: Any,
    *,
    kind: str | CanonicalSpec | None = None,
    namespace: str | None = None,
    fields: Sequence[str] | None = None,
    kinds: Mapping[str, Any] | None = None,
) -> bytes:
    """Encode a value with an explicit or safely inferred frozen kind."""

    spec = kind if isinstance(kind, CanonicalSpec) else None
    actual_kind = _infer_kind(value) if kind is None else (spec.kind if spec else kind)
    if actual_kind == KIND_NONE:
        if value is not None:
            raise CanonicalizationError("NONE value must be None")
        payload = b""
    elif actual_kind == KIND_BOOL_TRUE:
        if value is not True:
            raise CanonicalizationError("BOOL_TRUE value mismatch")
        payload = b""
    elif actual_kind == KIND_BOOL_FALSE:
        if value is not False:
            raise CanonicalizationError("BOOL_FALSE value mismatch")
        payload = b""
    elif actual_kind == KIND_INT:
        if type(value) is not int:
            raise CanonicalizationError("INT requires exact int")
        payload = _ascii(str(value), "INT")
    elif actual_kind == KIND_STRING:
        if type(value) is not str:
            raise CanonicalizationError("STRING requires exact str")
        payload = value.encode("utf-8")
    elif actual_kind == KIND_BYTES:
        if not isinstance(value, bytes):
            raise CanonicalizationError("BYTES requires bytes")
        payload = value
    elif actual_kind == KIND_DECIMAL:
        if type(value) is not Decimal or not value.is_finite():
            raise CanonicalizationError("DECIMAL requires finite Decimal")
        payload = _ascii(str(value), "DECIMAL")
    elif actual_kind == KIND_ENUM:
        if not isinstance(value, Enum) and type(value) is not str:
            raise CanonicalizationError("ENUM requires Enum or exact str")
        enum_value = value.value if isinstance(value, Enum) else value
        if type(enum_value) is not str:
            raise CanonicalizationError("ENUM value must be str")
        payload = enum_value.encode("utf-8")
    elif actual_kind == KIND_TUPLE:
        if not isinstance(value, (tuple, list)):
            raise CanonicalizationError("TUPLE requires tuple/list")
        item_spec = None if spec is None else spec.item_spec
        payload = _u32(len(value)) + b"".join(
            frame_value(item, kind=item_spec) if item_spec is not None else frame_value(item)
            for item in value
        )
    elif actual_kind == KIND_RECORD:
        if not isinstance(value, Mapping) and not dataclasses.is_dataclass(value):
            raise CanonicalizationError("RECORD requires mapping/dataclass")
        if spec is not None:
            namespace = spec.namespace
            fields = spec.fields
            kinds = dict(spec.kinds)
        if fields is None:
            if not isinstance(value, Mapping):
                fields = tuple(item.name for item in dataclasses.fields(value))
            else:
                # Nested TASK039 records are constructed from closed dict
                # literals in task039.py.  Their insertion order is therefore
                # the declared local projection order; arbitrary caller
                # mappings still cannot reach an identity function without
                # the outer record's explicit field tuple.
                fields = tuple(value.keys())
        payload = record_bytes(
            namespace or "task039.anonymous-record.v1", value, fields, kinds=kinds
        )
    else:
        raise CanonicalizationError(f"unknown canonical kind: {actual_kind}")
    return frame(actual_kind, payload)


def frame_tuple(values: Sequence[Any]) -> bytes:
    if not isinstance(values, (tuple, list)):
        raise CanonicalizationError("TUPLE requires tuple/list")
    return frame(KIND_TUPLE, _u32(len(values)) + b"".join(frame_value(v) for v in values))


def frame_record(
    namespace: str,
    record: Any,
    fields: Sequence[str],
    kinds: Mapping[str, Any] | None = None,
) -> bytes:
    return frame(KIND_RECORD, record_bytes(namespace, record, fields, kinds=kinds))


def record_bytes(
    namespace: str,
    record: Any,
    fields: Sequence[str],
    *,
    kinds: Mapping[str, Any] | None = None,
) -> bytes:
    """Encode ``RECORD`` payload using the supplied ordered fields."""

    namespace_bytes = namespace.encode("utf-8")
    ordered = tuple(fields)
    if len(set(ordered)) != len(ordered):
        raise CanonicalizationError("record fields must be unique")
    parts = [_u32(len(namespace_bytes)), namespace_bytes, _u32(len(ordered))]
    for name in ordered:
        if type(name) is not str or not name:
            raise CanonicalizationError("record field names must be non-empty str")
        value = _record_value(record, name)
        declared = None if kinds is None else kinds.get(name)
        # RECORD names are length-prefixed UTF-8 names, followed by the
        # ordered value frame.  They are not themselves value frames.  This
        # is the distinction that keeps the frozen nested-record oracle
        # byte-compatible with the R4 grammar.
        name_bytes = name.encode("utf-8")
        parts.append(_u32(len(name_bytes)))
        parts.append(name_bytes)
        parts.append(frame_value(value, kind=declared))
    return b"".join(parts)


_STRING = KIND_STRING
_INT = KIND_INT
_ENUM = KIND_ENUM

_PROVENANCE_KINDS = {
    "task_id": _STRING,
    "source_definition_issue": _INT,
    "source_definition_revision": _STRING,
    "allocation_issue": _INT,
    "allocation_revision": _STRING,
    "base_main_sha": _STRING,
    "base_main_tree": _STRING,
    "unauthorized_mutation_commit": _STRING,
    "repair_commit": _STRING,
    "task038_merge_commit": _STRING,
    "task038_post_merge_main_ci_run": _STRING,
    "v03_tag": _STRING,
    "v03_tag_target_commit": _STRING,
    "v03_github_release_id": _INT,
    "v03_manifest_hash": _STRING,
    "release_version": _STRING,
    "production_graph_hash": _STRING,
    "success_demo_hash": _STRING,
    "blocked_demo_hashes": tuple_spec(_STRING),
    "artifact_manifest_hash": _STRING,
    "acceptance_checklist_hash": _STRING,
    "evidence_refs": tuple_spec(_STRING),
    "provenance_hash": _STRING,
}
PROVENANCE_PREHASH_SPEC = record_spec(
    "task039.release-provenance.v1", PROVENANCE_PREHASH_FIELDS, _PROVENANCE_KINDS
)
PROVENANCE_FULL_SPEC = record_spec(
    "task039.release-provenance.v1", PROVENANCE_FULL_FIELDS, _PROVENANCE_KINDS
)

HISTORICAL_AUTHORITY_SPEC = record_spec(
    "task039.historical-release-authority.v1",
    HISTORICAL_AUTHORITY_FIELDS,
    {
        "tag": _STRING,
        "target_commit": _STRING,
        "github_release_id": _INT,
        "manifest_hash": _STRING,
        "release_version": _STRING,
        "acceptance_status": _ENUM,
    },
)
ACCEPTANCE_ITEM_SPEC = record_spec(
    "task039.release-acceptance-item.v1",
    ACCEPTANCE_ITEM_FIELDS,
    {
        "test_id": _STRING,
        "category": _ENUM,
        "status": _ENUM,
        "evidence_refs": tuple_spec(_STRING),
        "failure_meaning": _STRING,
    },
)
ACCEPTANCE_LEDGER_SPEC = record_spec(
    "task039.release-acceptance-ledger.v1",
    ACCEPTANCE_LEDGER_FIELDS,
    {
        "schema_version": _STRING,
        "checklist_id": _STRING,
        "item_count": _INT,
        "pass_count": _INT,
        "items": tuple_spec(ACCEPTANCE_ITEM_SPEC),
        "aggregate_status": _ENUM,
    },
)
WARNING_SPEC = record_spec(
    "task039.warning-entry.v1",
    WARNING_ENTRY_FIELDS,
    {"code": _ENUM, "stage": _STRING, "field_path": _STRING},
)
BLOCKER_SPEC = record_spec(
    "task039.blocker-entry.v1",
    BLOCKER_ENTRY_FIELDS,
    {
        "code": _ENUM,
        "stage": _STRING,
        "field_path": _STRING,
        "reason": _STRING,
        "producer_or_owner": _STRING,
    },
)

_RESULT_KINDS: dict[str, Any] = {
    "schema_version": _STRING,
    "profile_id": _STRING,
    "release_version": _STRING,
    "source_definition_issue": _INT,
    "source_definition_revision": _STRING,
    "allocation_issue": _INT,
    "allocation_revision": _STRING,
    "base_main_sha": _STRING,
    "base_main_tree": _STRING,
    "task038_merge_commit": _STRING,
    "task038_post_merge_main_ci_run": _STRING,
    "historical_release_authority": HISTORICAL_AUTHORITY_SPEC,
    "production_graph_hash": _STRING,
    "success_demo_hash": _STRING,
    "blocked_demo_hashes": tuple_spec(_STRING),
    "artifact_manifest_hash": _STRING,
    "version_metadata_hash": _STRING,
    "determinism_evidence_hash": _STRING,
    "acceptance_checklist_hash": _STRING,
    "release_acceptance_ledger": ACCEPTANCE_LEDGER_SPEC,
    "warnings": tuple_spec(WARNING_SPEC),
    "blockers": tuple_spec(BLOCKER_SPEC),
    "provenance": PROVENANCE_FULL_SPEC,
}
RESULT_SPEC = record_spec(
    RESULT_NAMESPACE,
    RESULT_PREHASH_FIELDS,
    _RESULT_KINDS,
)


def canonical_bytes(namespace: str, record: Any, fields: Sequence[str]) -> bytes:
    return frame_record(namespace, record, fields)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_hex(value: bytes | str) -> str:
    data = value.encode("utf-8") if isinstance(value, str) else value
    return sha256_bytes(data)


def result_id(result_hash_value: str) -> str:
    return str(uuid.uuid5(uuid.UUID(UUID_NAMESPACE), UUID_NAME_PREFIX + result_hash_value))


def _hash_named(namespace: str, record: Any, fields: Sequence[str]) -> str:
    return sha256_bytes(frame_record(namespace, record, fields))


def result_canonical_bytes(record: Any) -> bytes:
    # The top-level result preimage is the RECORD itself.  Nested RECORD
    # values are framed by ``record_bytes`` according to their declared kind,
    # but the preimage's published byte count is the RECORD payload, matching
    # the frozen Design oracle.
    return record_bytes(
        RESULT_SPEC.namespace or RESULT_NAMESPACE,
        record,
        RESULT_SPEC.fields,
        kinds=dict(RESULT_SPEC.kinds),
    )


def result_hash(record: Any) -> str:
    return sha256_bytes(result_canonical_bytes(record))


def result_identity(record: Any) -> tuple[str, str]:
    digest = result_hash(record)
    return digest, result_id(digest)


def provenance_prehash_bytes(record: Any) -> bytes:
    return record_bytes(
        PROVENANCE_PREHASH_SPEC.namespace or PROVENANCE_NAMESPACE,
        record,
        PROVENANCE_PREHASH_SPEC.fields,
        kinds=dict(PROVENANCE_PREHASH_SPEC.kinds),
    )


def provenance_hash(record: Any) -> str:
    return sha256_bytes(provenance_prehash_bytes(record))


def provenance_full_bytes(record: Any) -> bytes:
    return record_bytes(
        PROVENANCE_FULL_SPEC.namespace or PROVENANCE_NAMESPACE,
        record,
        PROVENANCE_FULL_SPEC.fields,
        kinds=dict(PROVENANCE_FULL_SPEC.kinds),
    )


def acceptance_checklist_hash(record: Any) -> str:
    return _hash_named("task039.acceptance-checklist.v1", record, ACCEPTANCE_CHECKLIST_FIELDS[:-1])


def acceptance_ledger_hash(record: Any) -> str:
    return sha256_bytes(
        record_bytes(
            ACCEPTANCE_LEDGER_SPEC.namespace or "task039.release-acceptance-ledger.v1",
            record,
            ACCEPTANCE_LEDGER_SPEC.fields,
            kinds=dict(ACCEPTANCE_LEDGER_SPEC.kinds),
        )
    )


def manifest_hash(record: Any) -> str:
    return _hash_named("task039.release-manifest.v1", record, MANIFEST_RUNTIME_FIELDS[:-1])


def artifact_digest(value: bytes) -> str:
    return sha256_bytes(value)


def canonical_json_value(value: Any) -> Any:
    """Return a JSON-safe projection for deterministic artifact rendering."""

    return _primitive(value)


__all__ = [
    "CanonicalSpec",
    "CanonicalizationError",
    "KIND_BOOL_FALSE",
    "KIND_BOOL_TRUE",
    "KIND_BYTES",
    "KIND_DECIMAL",
    "KIND_ENUM",
    "KIND_INT",
    "KIND_NONE",
    "KIND_RECORD",
    "KIND_STRING",
    "KIND_TUPLE",
    "artifact_digest",
    "acceptance_checklist_hash",
    "acceptance_ledger_hash",
    "canonical_bytes",
    "canonical_json_value",
    "frame",
    "frame_record",
    "frame_string",
    "frame_tuple",
    "frame_value",
    "manifest_hash",
    "provenance_full_bytes",
    "provenance_hash",
    "provenance_prehash_bytes",
    "record_bytes",
    "result_canonical_bytes",
    "result_hash",
    "result_identity",
    "result_id",
    "record_spec",
    "sha256_bytes",
    "sha256_hex",
    "tuple_spec",
]
