"""Shared canonical JSON + SHA-256 helpers.

The TASK-012 frozen design contract (docs/tasks/TASK-012-standards-rule-pack-license-boundary.md,
review Head 28b6330f8c5221d75f101f6810157d81a428f446) requires Section 13:

* Canonical JSON per RFC 8785.
* Recursive lexicographic byte-wise key ordering (RFC 8785 §3.2.3).
* NFC unicode normalization on every string key and value (RFC 8785 §3.2.2.2,
  UAX #15).
* Numeric representation as the shortest round-trippable decimal string
  (RFC 8785 §3.3.1).
* Integers serialized without a decimal point.
* Booleans serialized as ``true`` / ``false`` lowercase.
* Non-finite floats (NaN, ±Infinity) are FORBIDDEN at hash time
  (Section 13 non_finite_floats row).
* Hash algorithm: SHA-256 (FIPS 180-4); hash_scope = per-artifact (rule or manifest).
* Excluded from hash input: ``canonical_hash``, ``mutable_review_comments``.

This module is the SHARED canonicalization helper for both TASK-011 benchmark
cases and TASK-012 rule-packs. The TASK-012 runtime MUST NOT introduce a
parallel canonical module; cross-domain coupling is forbidden.

This module is the new home for the canonical JSON behavior; the existing
``hexagent.benchmark_cases.canonical`` module continues to work and re-exports
these helpers to preserve backward compatibility.
"""

from __future__ import annotations

import hashlib
import unicodedata
from typing import Any

import rfc8785

# Fields excluded from hash input per Section 13 (excluded_hash_fields row).
EXCLUDED_HASH_FIELDS: frozenset[str] = frozenset({"canonical_hash", "mutable_review_comments"})


def _strip_excluded(value: Any) -> Any:
    """Recursively drop top-level ``EXCLUDED_HASH_FIELDS`` from dicts and
    apply NFC normalization (UAX #15) to every string.
    """
    if isinstance(value, dict):
        return {
            unicodedata.normalize("NFC", str(key)): _strip_excluded(item)
            for key, item in value.items()
            if key not in EXCLUDED_HASH_FIELDS
        }
    if isinstance(value, list):
        return [_strip_excluded(item) for item in value]
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    return value


def canonical_json_bytes(value: dict[str, Any]) -> bytes:
    """Return the RFC 8785 canonical JSON byte string for ``value``.

    ``value`` must be a JSON-compatible mapping; non-finite floats raise
    ``ValueError`` (rfc8785 enforces this) and unhashable types raise
    ``TypeError``.
    """
    cleaned = _strip_excluded(value)
    return rfc8785.dumps(cleaned)


def canonical_sha256(value: dict[str, Any]) -> str:
    """Return the SHA-256 hex digest of the canonical JSON of ``value``."""
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()
