"""Canonical frames and identity derivation for the TASK036 release demo."""

from __future__ import annotations

import dataclasses
import hashlib
import json
import math
import uuid
from collections.abc import Mapping, Sequence
from decimal import Decimal
from enum import Enum
from typing import Any, cast

from .schema import (
    ACCEPTANCE_CHECKLIST_PREHASH_FIELDS,
    DEMO_INPUT_FIELDS,
    DETERMINISM_EVIDENCE_PREHASH_FIELDS,
    MANIFEST_PREHASH_FIELDS,
    PROVENANCE_PREHASH_FIELDS,
    RAW_BOUNDARY_BLOCKED_RESULT_PREHASH_FIELDS,
    RELEASE_ACCEPTANCE_LEDGER_PREHASH_FIELDS,
    RESULT_ID_NAMESPACE,
    RESULT_ID_PREFIX,
    SUCCESS_RESULT_KIND_TAG,
    SUCCESS_RESULT_PREHASH_FIELDS,
    TYPED_BLOCKED_RESULT_KIND_TAG,
    TYPED_BLOCKED_RESULT_PREHASH_FIELDS,
    UPSTREAM_EVIDENCE_LEDGER_PREHASH_FIELDS,
    VERSION_METADATA_PREHASH_FIELDS,
)


class CanonicalizationError(ValueError):
    """Raised when a value is outside the frozen canonical domain."""


def normalize_value(value: Any, *, _seen: set[int] | None = None) -> Any:
    """Return the frozen JSON-compatible primitive projection.

    Decimal values are already producer-owned strings in semantic records, but
    accepting Decimal here keeps the identity helpers safe for typed upstream
    result objects.  Binary floats, sets, and cyclic containers are forbidden
    by the R5 canonical contract.
    """

    if value is None or type(value) is bool or type(value) is int or type(value) is str:
        return value
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise CanonicalizationError("non-finite Decimal is not canonical")
        return str(value)
    if isinstance(value, Enum):
        return normalize_value(value.value, _seen=_seen)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise CanonicalizationError("non-finite float is not canonical")
        raise CanonicalizationError("binary float is forbidden in semantic projections")
    if isinstance(value, (set, frozenset)):
        raise CanonicalizationError("unordered collections are forbidden")

    seen = set() if _seen is None else _seen
    if isinstance(value, (Mapping, list, tuple)) or dataclasses.is_dataclass(value):
        identity = id(value)
        if identity in seen:
            raise CanonicalizationError("cyclic container is not canonical")
        seen.add(identity)
        try:
            if dataclasses.is_dataclass(value) and not isinstance(value, type):
                return {
                    field.name: normalize_value(getattr(value, field.name), _seen=seen)
                    for field in dataclasses.fields(cast(Any, value))
                }
            if isinstance(value, Mapping):
                result: dict[str, Any] = {}
                for key, item in value.items():
                    if type(key) is not str:
                        raise CanonicalizationError("mapping keys must be strings")
                    result[key] = normalize_value(item, _seen=seen)
                return result
            return [normalize_value(item, _seen=seen) for item in cast(Sequence[Any], value)]
        finally:
            seen.remove(identity)

    raise CanonicalizationError(f"unsupported canonical value: {type(value)!r}")


def _field_value(record: Any, field: str) -> Any:
    if isinstance(record, Mapping):
        if field not in record:
            raise CanonicalizationError(f"missing canonical field: {field}")
        return record[field]
    try:
        return getattr(record, field)
    except AttributeError as exc:
        raise CanonicalizationError(f"missing canonical field: {field}") from exc


def ordered_field_projection(record: Any, fields: Sequence[str]) -> list[list[Any]]:
    """Project a record as the declared ordered field-pair list."""

    return [[field, normalize_value(_field_value(record, field))] for field in fields]


def canonical_frame(
    namespace: str,
    canonical_kind_tag: str,
    record: Any,
    fields: Sequence[str],
) -> dict[str, Any]:
    return {
        "namespace": namespace,
        "canonical_kind_tag": canonical_kind_tag,
        "ordered_field_projection": ordered_field_projection(record, fields),
    }


def canonical_bytes(
    namespace: str,
    canonical_kind_tag: str,
    record: Any,
    fields: Sequence[str],
) -> bytes:
    frame = canonical_frame(namespace, canonical_kind_tag, record, fields)
    try:
        return json.dumps(
            frame,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise CanonicalizationError("record cannot be canonically encoded") from exc


def canonical_json(value: Any, *, trailing_newline: bool = False) -> bytes:
    """Encode a normalized JSON document with the frozen stable settings."""

    try:
        encoded = json.dumps(
            normalize_value(value),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise CanonicalizationError("value cannot be canonically encoded") from exc
    return encoded + (b"\n" if trailing_newline else b"")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_hex(value: Any) -> str:
    return sha256_bytes(canonical_json(value))


def hash_record(
    namespace: str,
    canonical_kind_tag: str,
    record: Any,
    fields: Sequence[str],
) -> str:
    return sha256_bytes(canonical_bytes(namespace, canonical_kind_tag, record, fields))


def demo_input_hash(record: Any) -> str:
    return hash_record("task036.demo-input.v1", "TASK036_DEMO_INPUT", record, DEMO_INPUT_FIELDS)


def success_result_canonical_bytes(record: Any) -> bytes:
    return canonical_bytes(
        "task036.success-result.v1",
        SUCCESS_RESULT_KIND_TAG,
        record,
        SUCCESS_RESULT_PREHASH_FIELDS,
    )


def success_result_hash(record: Any) -> str:
    return sha256_bytes(success_result_canonical_bytes(record))


def typed_blocked_result_hash(record: Any) -> str:
    return hash_record(
        "task036.typed-blocked-result.v1",
        TYPED_BLOCKED_RESULT_KIND_TAG,
        record,
        TYPED_BLOCKED_RESULT_PREHASH_FIELDS,
    )


def raw_boundary_blocked_result_hash(record: Any) -> str:
    return hash_record(
        "task036.raw-boundary-blocked-result.v1",
        "TASK036_RAW_BOUNDARY_BLOCKED_RESULT",
        record,
        RAW_BOUNDARY_BLOCKED_RESULT_PREHASH_FIELDS,
    )


def release_acceptance_ledger_hash(record: Any) -> str:
    return hash_record(
        "task036.release-acceptance-ledger.v1",
        "TASK036_RELEASE_ACCEPTANCE_LEDGER",
        record,
        RELEASE_ACCEPTANCE_LEDGER_PREHASH_FIELDS,
    )


def upstream_evidence_ledger_hash(record: Any) -> str:
    return hash_record(
        "task036.upstream-evidence-ledger.v1",
        "TASK036_UPSTREAM_EVIDENCE_LEDGER",
        record,
        UPSTREAM_EVIDENCE_LEDGER_PREHASH_FIELDS,
    )


def acceptance_checklist_hash(record: Any) -> str:
    return hash_record(
        "task036.acceptance-checklist.v1",
        "TASK036_ACCEPTANCE_CHECKLIST",
        record,
        ACCEPTANCE_CHECKLIST_PREHASH_FIELDS,
    )


def manifest_hash(record: Any) -> str:
    return hash_record(
        "task036.manifest.v1",
        "TASK036_MANIFEST",
        record,
        MANIFEST_PREHASH_FIELDS,
    )


def version_metadata_hash(record: Any) -> str:
    return hash_record(
        "task036.version-metadata.v1",
        "TASK036_VERSION_METADATA",
        record,
        VERSION_METADATA_PREHASH_FIELDS,
    )


def provenance_hash(record: Any) -> str:
    return hash_record(
        "task036.provenance.v1",
        "TASK036_PROVENANCE",
        record,
        PROVENANCE_PREHASH_FIELDS,
    )


def determinism_evidence_hash(record: Any) -> str:
    return hash_record(
        "task036.determinism-evidence.v1",
        "TASK036_DETERMINISM_EVIDENCE",
        record,
        DETERMINISM_EVIDENCE_PREHASH_FIELDS,
    )


def result_id(result_hash: str, kind_tag: str = SUCCESS_RESULT_KIND_TAG) -> str:
    """Derive the internal UUIDv5 identity from the frozen two-field preimage."""

    try:
        namespace = uuid.UUID(RESULT_ID_NAMESPACE)
    except ValueError as exc:  # pragma: no cover - frozen constant guard
        raise CanonicalizationError("invalid frozen result-id namespace") from exc
    return str(uuid.uuid5(namespace, RESULT_ID_PREFIX + kind_tag + ":" + result_hash.lower()))


def release_acceptance_result_id(ledger_hash: str) -> str:
    """Return the distinct, mechanically derived release-acceptance ID."""

    return "sha256:" + ledger_hash


def artifact_digest(data: bytes) -> str:
    """Digest exact final file bytes, not a normalized semantic projection."""

    return sha256_bytes(data)


__all__ = [
    "CanonicalizationError",
    "acceptance_checklist_hash",
    "artifact_digest",
    "canonical_bytes",
    "canonical_frame",
    "canonical_json",
    "demo_input_hash",
    "determinism_evidence_hash",
    "hash_record",
    "manifest_hash",
    "normalize_value",
    "ordered_field_projection",
    "provenance_hash",
    "raw_boundary_blocked_result_hash",
    "release_acceptance_ledger_hash",
    "release_acceptance_result_id",
    "result_id",
    "sha256_bytes",
    "sha256_hex",
    "success_result_canonical_bytes",
    "success_result_hash",
    "typed_blocked_result_hash",
    "upstream_evidence_ledger_hash",
    "version_metadata_hash",
]
