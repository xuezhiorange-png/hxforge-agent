"""Canonicalization + hash helpers for TASK-014 immutable case revisions.

Implements Section 11 of the TASK-014 frozen design contract
(docs/tasks/TASK-014-immutable-case-revisions-persistence.md,
Frozen Contract Authority SHA
``6f337a6e81a8c2a7ba8059285aeef39bba59c7cb``).

Section 11.1 — REUSES ``hexagent.canonical_json.canonical_sha256``. No
parallel canonicalization helper is introduced.

Section 11.2 — three hash inputs:

* ``payload_hash`` — SHA-256 hex of the canonicalized
  ``case_revisions.payload`` (with ``record_hash`` excluded if present).
* ``domain_snapshot_hash`` — SHA-256 hex of the canonicalized domain
  snapshot, joined into a single canonical object excluding the volatile
  fields listed in Section 11.3.
* ``parent_chain_hash`` (optional) — SHA-256 hex of the canonicalized
  ``case_revision_parents`` rows ordered by ``link_order`` ascending.

Section 11.3 — excluded volatile fields:

* ``created_at``, ``created_by``
* ``committed_at``, ``committed_by``
* ``expected_parent_revision_id``
* ``idempotency_key``
* ``optimistic_concurrency_token``
* ``archived_at``, ``tombstone_at``, ``superseded_by``

Section 11.4 — golden vectors (10 fixtures) are exercised by the test
suite under ``tests/case_revisions/test_canonical.py``.
"""

from __future__ import annotations

from typing import Any

from hexagent.canonical_json import canonical_sha256

# --- Volatile fields excluded from hash inputs (Section 11.3) --------------

# These fields MUST NOT affect payload_hash or domain_snapshot_hash. They
# are audit / concurrency / lifecycle metadata, not semantic payload.

PAYLOAD_HASH_EXCLUDED_FIELDS: frozenset[str] = frozenset({"record_hash"})

DOMAIN_SNAPSHOT_HASH_EXCLUDED_FIELDS: frozenset[str] = frozenset(
    {
        "created_at",
        "created_by",
        "committed_at",
        "committed_by",
        "expected_parent_revision_id",
        "idempotency_key",
        "optimistic_concurrency_token",
        "archived_at",
        "tombstone_at",
        "superseded_by",
    }
)

# All volatile fields excluded from BOTH hash inputs (union, for tests).
ALL_VOLATILE_FIELDS: frozenset[str] = (
    PAYLOAD_HASH_EXCLUDED_FIELDS | DOMAIN_SNAPSHOT_HASH_EXCLUDED_FIELDS
)


# --- Hash helpers ----------------------------------------------------------


def _strip_fields(value: Any, excluded: frozenset[str]) -> Any:
    """Recursively drop top-level keys in ``excluded`` from dicts.

    Unlike ``hexagent.canonical_json._strip_excluded`` (which only drops
    ``canonical_hash`` and ``mutable_review_comments``), this helper
    accepts a caller-specified excluded set so we can honour the
    Section 11.3 volatile-fields list.
    """
    if isinstance(value, dict):
        return {k: _strip_fields(v, excluded) for k, v in value.items() if k not in excluded}
    if isinstance(value, list):
        return [_strip_fields(item, excluded) for item in value]
    return value


def compute_payload_hash(payload: dict[str, Any]) -> str:
    """Section 11.2 — SHA-256 hex of the canonicalized ``payload`` field
    (with ``record_hash`` excluded if present)."""
    if not isinstance(payload, dict):
        raise TypeError(f"payload must be a dict; got {type(payload).__name__}")
    cleaned = _strip_fields(payload, PAYLOAD_HASH_EXCLUDED_FIELDS)
    return canonical_sha256(cleaned)


def compute_domain_snapshot_hash(
    *,
    identity: dict[str, Any],
    payload: dict[str, Any],
    provenance: dict[str, Any],
    parent_chain: tuple[dict[str, Any], ...] | list[dict[str, Any]] = (),
) -> str:
    """Section 11.2 — SHA-256 hex of the canonicalized domain snapshot.

    Joins ``{identity, payload, provenance, parent_chain}`` into a single
    canonical object. Volatile fields (Section 11.3) are excluded.
    """
    snapshot = {
        "identity": identity,
        "payload": payload,
        "provenance": provenance,
        "parent_chain": list(parent_chain),
    }
    cleaned = _strip_fields(snapshot, DOMAIN_SNAPSHOT_HASH_EXCLUDED_FIELDS)
    return canonical_sha256(cleaned)


def compute_parent_chain_hash(
    parent_links: tuple[dict[str, Any], ...] | list[dict[str, Any]],
) -> str:
    """Section 11.2 — SHA-256 hex of the canonicalized parent-chain rows
    ordered by ``link_order`` ascending.

    The caller MUST pass the rows already ordered by ``link_order`` ASC;
    we canonicalize that ordering deterministically (sorted by key).
    """
    if not isinstance(parent_links, (list, tuple)):
        raise TypeError(f"parent_links must be a list/tuple; got {type(parent_links).__name__}")
    rows = [dict(link) for link in parent_links]
    return canonical_sha256({"parent_chain_rows": rows})


def hash_field_kind(field_name: str) -> str | None:
    """Return the canonical hash-field kind for a stored hash field name,
    or ``None`` if the field is not a hash field.

    Used by :class:`hexagent.case_revisions.errors.RevisionHashMismatch`
    to validate ``context.hash_field``.
    """
    from hexagent.case_revisions.errors import VALID_HASH_FIELDS

    if field_name in VALID_HASH_FIELDS:
        return field_name
    return None


__all__ = [
    "ALL_VOLATILE_FIELDS",
    "DOMAIN_SNAPSHOT_HASH_EXCLUDED_FIELDS",
    "PAYLOAD_HASH_EXCLUDED_FIELDS",
    "compute_domain_snapshot_hash",
    "compute_parent_chain_hash",
    "compute_payload_hash",
    "hash_field_kind",
]
