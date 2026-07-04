"""Canonical JSON and SHA-256 helpers for benchmark cases.

The implementation intentionally keeps benchmark numeric payloads as decimal
strings. That avoids platform-dependent float rendering and keeps canonical
hash input deterministic under the TASK-011 contract.
"""

from __future__ import annotations

import hashlib
import json
import math
import unicodedata
from typing import Any

_EXCLUDED_HASH_FIELDS = {"canonical_hash", "mutable_review_comments"}


def _normalize_for_hash(value: Any) -> Any:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, bool) or value is None or isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("NaN and Infinity are forbidden in benchmark cases")
        raise TypeError("benchmark numeric values must be decimal strings, not floats")
    if isinstance(value, list):
        return [_normalize_for_hash(item) for item in value]
    if isinstance(value, dict):
        return {
            unicodedata.normalize("NFC", str(key)): _normalize_for_hash(item)
            for key, item in value.items()
            if key not in _EXCLUDED_HASH_FIELDS
        }
    return value


def canonical_json_bytes(value: dict[str, Any]) -> bytes:
    normalized = _normalize_for_hash(value)
    return json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def canonical_sha256(value: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()
