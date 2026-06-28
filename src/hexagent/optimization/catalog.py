"""
TASK-009 catalog content-hash authority and canonical ordering.

This module defines the **single authoritative** hash computation for
catalog snapshots.  All callers — model validators, test fixtures,
production code — must use ``compute_catalog_content_hash()``.
"""

from __future__ import annotations

import hashlib
from typing import Any

from hexagent.core.canonical import canonical_json
from hexagent.optimization.errors import CatalogInvalid

HASH_PREFIX = "sha256:"
HASH_HEX_LENGTH = 64


# ---------------------------------------------------------------------------
# Identity key — for duplicate detection and sorting
# ---------------------------------------------------------------------------


def catalog_identity_key(cat: Any) -> tuple[str, str, str, str, str]:
    """Return the canonical identity tuple for a catalog snapshot.

    Accepts any object with the required attributes (duck-typed to avoid
    circular imports).
    """
    return (
        cat.catalog_id,
        cat.catalog_version,
        cat.catalog_content_hash,
        cat.source_identity,
        cat.schema_version,
    )


# ---------------------------------------------------------------------------
# Identity field validation
# ---------------------------------------------------------------------------


def validate_identity_fields(
    catalog_id: str,
    catalog_version: str,
    source_identity: str,
    schema_version: str,
) -> None:
    """Validate that all identity fields are non-empty ASCII strings."""
    _check_field("catalog_id", catalog_id)
    _check_field("catalog_version", catalog_version)
    _check_field("source_identity", source_identity)
    _check_field("schema_version", schema_version)


def _check_field(name: str, value: str) -> None:
    if not isinstance(value, str):
        raise CatalogInvalid(f"{name} must be a string, got {type(value).__name__}")
    if not value:
        raise CatalogInvalid(f"{name} must not be empty")
    if not value.isascii():
        raise CatalogInvalid(f"{name} must be ASCII: {value!r}")


# ---------------------------------------------------------------------------
# Hash format validation
# ---------------------------------------------------------------------------


def validate_hash_format(hash_value: str) -> str:
    """Validate ``sha256:<64-lowercase-hex>`` and return the hex part."""
    if not isinstance(hash_value, str):
        raise CatalogInvalid(
            f"catalog_content_hash must be a string, got {type(hash_value).__name__}"
        )
    if not hash_value.startswith(HASH_PREFIX):
        raise CatalogInvalid(
            f"catalog_content_hash must start with '{HASH_PREFIX}', got {hash_value!r}"
        )
    hex_part = hash_value[len(HASH_PREFIX) :]
    if len(hex_part) != HASH_HEX_LENGTH:
        raise CatalogInvalid(
            f"catalog_content_hash hex part must be {HASH_HEX_LENGTH} chars, got {len(hex_part)}"
        )
    try:
        int(hex_part, 16)
    except ValueError as exc:
        raise CatalogInvalid(
            f"catalog_content_hash hex part is not valid hex: {hex_part!r}"
        ) from exc
    if hex_part != hex_part.lower():
        raise CatalogInvalid(f"catalog_content_hash hex part must be lowercase: {hex_part!r}")
    return hex_part


# ---------------------------------------------------------------------------
# Canonical payload & hash computation — single authoritative implementation
# ---------------------------------------------------------------------------


def _compute_payload(
    *,
    catalog_id: str,
    catalog_version: str,
    source_identity: str,
    schema_version: str,
    assembly_options: tuple[Any, ...],
) -> dict[str, object]:
    """Build canonical payload dict from typed models for hashing.

    Options are sorted internally by ``assembly_option_id`` and dumped
    via ``model_dump(mode=\"python\")`` so that all canonicalised
    representations (normalised quantum, sorted metadata tuples) are
    captured.
    """
    sorted_options = tuple(sorted(assembly_options, key=lambda o: o.assembly_option_id))
    return {
        "catalog_id": catalog_id,
        "catalog_version": catalog_version,
        "source_identity": source_identity,
        "schema_version": schema_version,
        "assembly_options": [opt.model_dump(mode="python") for opt in sorted_options],
    }


def canonical_catalog_payload(
    *,
    catalog_id: str,
    catalog_version: str,
    source_identity: str,
    schema_version: str,
    assembly_options: tuple[Any, ...],
) -> dict[str, object]:
    """Public entry point for the canonical payload dict."""
    return _compute_payload(
        catalog_id=catalog_id,
        catalog_version=catalog_version,
        source_identity=source_identity,
        schema_version=schema_version,
        assembly_options=assembly_options,
    )


def compute_catalog_content_hash(
    *,
    catalog_id: str,
    catalog_version: str,
    source_identity: str,
    schema_version: str,
    assembly_options: tuple[Any, ...],
) -> str:
    """Compute the SHA-256 content hash from typed assembly options.

    The function sorts options internally so that equivalent catalogs
    with different input orders produce identical hashes.
    """
    payload = _compute_payload(
        catalog_id=catalog_id,
        catalog_version=catalog_version,
        source_identity=source_identity,
        schema_version=schema_version,
        assembly_options=assembly_options,
    )
    canon_str = canonical_json(payload)
    digest = hashlib.sha256(canon_str.encode("utf-8")).hexdigest()
    return f"{HASH_PREFIX}{digest}"


__all__ = [
    "HASH_PREFIX",
    "catalog_identity_key",
    "canonical_catalog_payload",
    "compute_catalog_content_hash",
    "validate_hash_format",
    "validate_identity_fields",
]
