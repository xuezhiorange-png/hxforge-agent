"""
TASK-009 catalog content-hash authority and canonical ordering.
"""

from __future__ import annotations

import hashlib
from typing import Any

from hexagent.core.canonical import canonical_json

HASH_PREFIX = "sha256:"
HASH_HEX_LENGTH = 64


def catalog_identity_key(cat: Any) -> tuple[str, str, str, str, str]:
    return (
        cat.catalog_id,
        cat.catalog_version,
        cat.catalog_content_hash,
        cat.source_identity,
        cat.schema_version,
    )


def validate_identity_fields(
    catalog_id: str,
    catalog_version: str,
    source_identity: str,
    schema_version: str,
) -> None:
    _check_identity_field("catalog_id", catalog_id)
    _check_identity_field("catalog_version", catalog_version)
    _check_identity_field("source_identity", source_identity)
    _check_identity_field("schema_version", schema_version)


def _check_identity_field(name: str, value: str) -> None:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string, got {type(value).__name__}")
    if not value:
        raise ValueError(f"{name} must not be empty")
    if not value.isascii():
        raise ValueError(f"{name} must be ASCII: {value!r}")


def validate_hash_format(hash_value: str) -> None:
    if not isinstance(hash_value, str):
        raise ValueError(f"catalog_content_hash must be a string, got {type(hash_value).__name__}")
    if not hash_value.startswith(HASH_PREFIX):
        raise ValueError(
            f"catalog_content_hash must start with '{HASH_PREFIX}', got {hash_value!r}"
        )
    hex_part = hash_value[len(HASH_PREFIX) :]
    if len(hex_part) != HASH_HEX_LENGTH:
        raise ValueError(
            f"catalog_content_hash hex part must be {HASH_HEX_LENGTH} chars, got {len(hex_part)}"
        )
    try:
        int(hex_part, 16)
    except ValueError as exc:
        raise ValueError(f"catalog_content_hash hex part is not valid hex: {hex_part!r}") from exc
    if hex_part != hex_part.lower():
        raise ValueError(f"catalog_content_hash hex part must be lowercase: {hex_part!r}")


def canonical_sort_assembly_options(
    assembly_options: tuple[Any, ...],
) -> tuple[Any, ...]:
    seen: set[str] = set()
    for opt in assembly_options:
        oid = opt.get("assembly_option_id", "") if isinstance(opt, dict) else opt.assembly_option_id
        if oid in seen:
            raise ValueError(f"Duplicate assembly_option_id: {oid!r}")
        seen.add(oid)
    return tuple(
        sorted(
            assembly_options,
            key=lambda o: o["assembly_option_id"] if isinstance(o, dict) else o.assembly_option_id,
        )
    )


def canonical_catalog_payload(
    catalog_id: str,
    catalog_version: str,
    source_identity: str,
    schema_version: str,
    assembly_options: tuple[dict[str, Any], ...],
) -> dict[str, Any]:
    return {
        "catalog_id": catalog_id,
        "catalog_version": catalog_version,
        "source_identity": source_identity,
        "schema_version": schema_version,
        "assembly_options": list(assembly_options),
    }


def compute_catalog_content_hash(
    catalog_id: str,
    catalog_version: str,
    source_identity: str,
    schema_version: str,
    assembly_options: tuple[dict[str, Any], ...],
) -> str:
    payload = canonical_catalog_payload(
        catalog_id=catalog_id,
        catalog_version=catalog_version,
        source_identity=source_identity,
        schema_version=schema_version,
        assembly_options=assembly_options,
    )
    canon_str = canonical_json(payload)
    digest = hashlib.sha256(canon_str.encode("utf-8")).hexdigest()
    return f"{HASH_PREFIX}{digest}"


def validate_and_hash_catalog(
    catalog_id: str,
    catalog_version: str,
    source_identity: str,
    schema_version: str,
    assembly_options: tuple[Any, ...],
    claimed_hash: str,
) -> tuple[tuple[Any, ...], str]:
    validate_identity_fields(
        catalog_id=catalog_id,
        catalog_version=catalog_version,
        source_identity=source_identity,
        schema_version=schema_version,
    )
    validate_hash_format(claimed_hash)
    sorted_options = canonical_sort_assembly_options(assembly_options)
    option_dicts: tuple[dict[str, Any], ...] = tuple(
        o if isinstance(o, dict) else o.model_dump() for o in sorted_options
    )
    computed_hash = compute_catalog_content_hash(
        catalog_id=catalog_id,
        catalog_version=catalog_version,
        source_identity=source_identity,
        schema_version=schema_version,
        assembly_options=option_dicts,
    )
    if claimed_hash != computed_hash:
        raise ValueError(
            f"catalog_content_hash mismatch: claimed {claimed_hash!r}, computed {computed_hash!r}"
        )
    return sorted_options, computed_hash


__all__ = [
    "HASH_PREFIX",
    "catalog_identity_key",
    "canonical_catalog_payload",
    "canonical_sort_assembly_options",
    "compute_catalog_content_hash",
    "validate_and_hash_catalog",
    "validate_hash_format",
    "validate_identity_fields",
]
