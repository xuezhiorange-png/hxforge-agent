"""Canonical JSON and SHA-256 helpers for benchmark cases.

The TASK-011 frozen design contract (docs/tasks/TASK-011-benchmark-case-governance.md,
SHA 7cfdb4f0989b6d384533c7a29e9a2156c731bd0f) requires Section 17:

* Canonical JSON per RFC 8785.
* Recursive lexicographic byte-wise key ordering (RFC 8785 §3.2.3).
* NFC unicode normalization on every string key and value (RFC 8785 §3.2.2.2,
  UAX #15).
* Numeric representation as the shortest round-trippable decimal string
  (RFC 8785 §3.3.1; contract §17.3).
* Integers serialized without a decimal point (contract §17.3).
* Booleans serialized as ``true`` / ``false`` lowercase (contract §17.3).
* Non-finite floats (NaN, ±Infinity) are FORBIDDEN at hash time
  (contract §17.3).
* Hash algorithm: SHA-256 (FIPS 180-4); hash_scope = case-level
  (contract §17.1).
* Excluded from hash input: ``canonical_hash``, ``mutable_review_comments``,
  and any field not in the §17.2 mandatory hashed field list (contract
  §17.1, ``mutable_review_comments``, ``approval_comments``).

The reference implementation is delegated to the third-party ``rfc8785``
package for §3.2.3 key ordering, §3.3.1 shortest-decimal numeric
serialization, and JSON byte emission. Because the rfc8785 package does
NOT perform UAX #15 NFC normalization on string keys/values, this module
applies NFC normalization explicitly before serialization. Hash-time
exclusion semantics are enforced by the wrapper.
"""

from __future__ import annotations

import hashlib
import unicodedata
from typing import Any

import rfc8785

# Fields excluded from hash input per contract §17.1.
# ``canonical_hash`` is the hash field itself; ``mutable_review_comments`` is
# explicitly excluded; ``approval_comments`` is excluded unless it is part of
# ``approval_snapshot`` (which is NOT excluded — it is part of the case
# snapshot and IS hashed when present).
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
