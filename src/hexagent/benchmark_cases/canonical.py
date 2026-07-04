"""Canonical JSON and SHA-256 helpers for benchmark cases.

This module is a thin backward-compatible re-export of the shared canonical
JSON helpers in ``hexagent.canonical_json``. The shared module is the single
source of truth for canonical JSON behavior across TASK-011 benchmark cases
and TASK-012 rule-packs (per the TASK-012 frozen design contract, Section 13
and Section 18, deliverable 3).

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
NOT perform UAX #15 NFC normalization on string keys/values, the shared
module applies NFC normalization explicitly before serialization. Hash-time
exclusion semantics are enforced by the shared wrapper.
"""

from __future__ import annotations

from hexagent.canonical_json import (
    EXCLUDED_HASH_FIELDS,
    canonical_json_bytes,
    canonical_sha256,
)

__all__ = ["EXCLUDED_HASH_FIELDS", "canonical_json_bytes", "canonical_sha256"]
