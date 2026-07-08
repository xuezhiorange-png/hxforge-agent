"""TASK-019 double-pipe validation-report skeleton.

Slice 1 scope (per Charles authorization TASK019_IMPL_SLICE1_*):
- Deterministic helpers (canonical JSON, SHA-256, UUID v5).
- Schema constants (TASK-019-VALIDATION-REPORT-V1 + 3 case IDs + allowed statuses).
- A skeleton report builder that accepts already-materialized case records
  and returns a deterministic report dictionary matching the frozen §7.1 shape.

NOT in Slice 1:
- Does NOT execute the full TASK-006 / TASK-007 / TASK-008 / TASK-017 /
  TASK-018 calculation chain.
- Does NOT compute final golden expected vectors.
- Does NOT introduce public API, CLI, DB schema, renderer, external
  integration, or Feishu integration.
- Does NOT implement TASK-018 discount / salvage formula.
- Does NOT introduce pressure-drop / C4 / TASK-020+ content.
"""

from __future__ import annotations

import datetime as _dt
import hashlib as _hashlib
import json as _json
import uuid as _uuid
from collections.abc import Mapping, Sequence
from typing import Any

# --- Schema constants (per frozen design §7.1) ---

TASK_019_VALIDATION_REPORT_V1: str = "TASK-019-VALIDATION-REPORT-V1"

# Exactly 3 golden case IDs (per frozen design §4)
TASK_019_GOLDEN_CASE_IDS: tuple = (
    "TASK-019-GOLDEN-01",
    "TASK-019-GOLDEN-02",
    "TASK-019-GOLDEN-03",
)

# Allowed overall statuses (per frozen design §7.3)
ALLOWED_OVERALL_STATUSES: frozenset = frozenset({"PASS", "FAIL", "NOT_COMPUTABLE"})

# Stable schema-version + implementation-version seeds for deterministic report_id.
# Implementation version is bumped only on schema-affecting changes; for Slice 1
# we use the design-frozen schema version V1.
_IMPLEMENTATION_VERSION: str = "TASK-019-validation-report-impl-v0.1.0-slice1"


# --- Deterministic helpers ---


def canonical_json_dumps(obj: Any) -> str:
    """Serialize ``obj`` to a deterministic canonical JSON string.

    Per MASTER_DEVELOPMENT_SPEC §15.3: sorted keys, compact separators,
    no insignificant whitespace, no NaN / Infinity, integers for minor units
    only (no float for money).

    Implementation note: this helper does not validate schema; it is purely a
    serialization primitive. The caller is responsible for ensuring the
    payload is JSON-serializable and that money fields are integers.
    """
    return _json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def sha256_hex(payload: str | bytes) -> str:
    """Return the SHA-256 lowercase hex digest of ``payload``.

    Per frozen design §3.3: SHA-256, lowercase hex, 64 characters.
    """
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    return _hashlib.sha256(payload).hexdigest()


def _stable_report_id_seed(
    *,
    schema_version: str,
    case_ids: Sequence[str],
    impl_version: str,
) -> str:
    """Construct a stable seed string for UUID v5 derivation."""
    return f"{schema_version}|{impl_version}|" + "|".join(sorted(case_ids))


def deterministic_report_id(
    *,
    schema_version: str = TASK_019_VALIDATION_REPORT_V1,
    case_ids: Sequence[str] = TASK_019_GOLDEN_CASE_IDS,
    impl_version: str = _IMPLEMENTATION_VERSION,
) -> str:
    """Derive a deterministic UUID v5 from the schema + case IDs + impl version.

    Per frozen design §3.3: deterministic UUID v5 derived from stable schema
    + golden case IDs + implementation version. Using a fixed UUID namespace
    so that re-running the same build produces the same report_id.
    """
    # Fixed UUID namespace (deterministic across runs / machines).
    # Generated once and hard-coded; do NOT change across implementation
    # versions to preserve cross-run determinism.
    namespace = _uuid.UUID("9c1b1f5e-7a4e-4f3a-8d2b-1f3a5e6c7d8e")
    seed = _stable_report_id_seed(
        schema_version=schema_version,
        case_ids=tuple(case_ids),
        impl_version=impl_version,
    )
    return str(_uuid.uuid5(namespace, seed))


def _now_utc_iso8601() -> str:
    """Return the current UTC time as an ISO 8601 string with explicit Z suffix.

    Per frozen design §3.3: ISO 8601 UTC, explicit Z suffix. Slice 1 callers
    that want full determinism may pass a fixed ``generated_at`` value
    explicitly when invoking :func:`build_double_pipe_validation_report`.
    """
    return _dt.datetime.now(_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


# --- Slice 1 helper for environment metadata (deterministic) ---


def _stable_run_environment_metadata() -> dict[str, Any]:
    """Return a deterministic, conservative run-environment metadata block.

    Per frozen design §7.1: ``run_environment`` is required but Slice 1
    callers MAY pass a fully populated block. This helper returns the
    minimum required fields, leaving ``package_versions`` and
    ``deterministic_mode_flags`` to be filled in by the future Slice 2
    implementation runner.
    """
    return {
        "python_version": "TBD-by-Slice-2-runner",
        "platform": "TBD-by-Slice-2-runner",
        "package_versions": {},
        "deterministic_mode_flags": [
            "sort_keys",
            "no_floats_for_money",
            "no_nan_infinity",
        ],
    }


# --- Slice 1 upstream contract versions (frozen contract base SHAs) ---


def _frozen_upstream_contract_versions() -> dict[str, str]:
    """Record frozen contract base SHAs for the 10 upstream contracts.

    These are the contract base SHAs from TASK-018 closeout (PR #86 merge
    main HEAD ``bf8988d9b7890793f2804c45e45f1a940413aa84``).

    Per frozen design §7.1: ``upstream_contract_versions`` is required and
    must reference each upstream contract the Slice 1 schema consumes.
    Slice 1 lists them as ``<contract-name>`` -> ``<base-SHA>``.
    """
    # Contract base SHA from TASK-018 closeout / TASK-017 implementation
    # PR #75 merge. The TASK-019 implementation is anchored to this base.
    return {
        "TASK-006": "TBD-by-Slice-1-implementation",
        "TASK-007": "TBD-by-Slice-1-implementation",
        "TASK-008": "TBD-by-Slice-1-implementation",
        "TASK-011": "TBD-by-Slice-1-implementation",
        "TASK-012": "TBD-by-Slice-1-implementation",
        "TASK-013": "TBD-by-Slice-1-implementation",
        "TASK-014": "TBD-by-Slice-1-implementation",
        "TASK-015A": "TBD-by-Slice-1-implementation",
        "TASK-017": "TBD-by-Slice-1-implementation",
        "TASK-018": "TBD-by-Slice-1-implementation",
        "TASK-019": _IMPLEMENTATION_VERSION,
    }


# --- Validation helpers ---


def _ensure_allowed_overall_status(overall_status: str) -> str:
    if overall_status not in ALLOWED_OVERALL_STATUSES:
        raise ValueError(
            f"overall_status {overall_status!r} not in allowed set "
            f"{sorted(ALLOWED_OVERALL_STATUSES)!r}"
        )
    return overall_status


def _ensure_case_count(per_case_blocks: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    if len(per_case_blocks) != len(TASK_019_GOLDEN_CASE_IDS):
        raise ValueError(
            f"validation report skeleton requires exactly "
            f"{len(TASK_019_GOLDEN_CASE_IDS)} case blocks "
            f"(got {len(per_case_blocks)})"
        )
    return [dict(block) for block in per_case_blocks]


# --- Report builder skeleton (per frozen design §7.1) ---


def build_double_pipe_validation_report(
    *,
    per_case_blocks: Sequence[Mapping[str, Any]],
    upstream_contract_versions: Mapping[str, str] | None = None,
    run_environment: Mapping[str, Any] | None = None,
    generated_at: str | None = None,
    license_boundary_attestation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a TASK-019 validation-report skeleton.

    Slice 1 scope: a deterministic report builder that accepts already-
    materialized case records and returns a deterministic report dictionary
    matching the frozen §7.1 shape. Does NOT execute the full upstream
    calculation chain. Does NOT compute final golden expected vectors.

    Parameters
    ----------
    per_case_blocks:
        Sequence of exactly 3 case records. Each record MUST include the
        following top-level keys (per frozen design §7.1):
            - case_id
            - case_title
            - input_sha256
            - expected_output_sha256
            - actual_output_sha256
            - comparison (with overall_status + per_field + blockers + warnings)
            - provenance
    upstream_contract_versions:
        Optional override; defaults to :func:`_frozen_upstream_contract_versions`.
    run_environment:
        Optional override; defaults to :func:`_stable_run_environment_metadata`.
    generated_at:
        Optional ISO 8601 UTC timestamp; defaults to current time. For
        full determinism, pass a fixed value.
    license_boundary_attestation:
        Optional override; defaults to a safe Slice 1 stub.

    Returns
    -------
    Dict[str, Any]
        A deterministic report dictionary matching the frozen §7.1 shape.

    Raises
    ------
    ValueError
        If any per-case block is missing required keys, or if
        ``overall_status`` is not in ``ALLOWED_OVERALL_STATUSES``, or if
        the case count is not exactly 3.
    """
    # Validate case count
    blocks = _ensure_case_count(per_case_blocks)

    # Validate required keys per case
    required_keys = {
        "case_id",
        "case_title",
        "input_sha256",
        "expected_output_sha256",
        "actual_output_sha256",
        "comparison",
        "provenance",
    }
    for i, block in enumerate(blocks):
        missing = required_keys - set(block.keys())
        if missing:
            raise ValueError(f"per_case_blocks[{i}] missing required keys: {sorted(missing)!r}")
        comparison = block.get("comparison", {})
        overall = comparison.get("overall_status")
        if overall is not None:
            _ensure_allowed_overall_status(overall)

    # Compute aggregate summary
    total = len(blocks)
    passed = sum(1 for b in blocks if b["comparison"].get("overall_status") == "PASS")
    failed = sum(1 for b in blocks if b["comparison"].get("overall_status") == "FAIL")
    not_computable = sum(
        1 for b in blocks if b["comparison"].get("overall_status") == "NOT_COMPUTABLE"
    )
    # Blocked-on-deferred-amendments is not yet represented as a separate
    # status (per frozen design §8 Option X1 default). It will be
    # introduced in a future design-amendment round if Option X2 is
    # adopted. For Slice 1, blocked-on-deferred is reported as
    # ``NOT_COMPUTABLE`` with a ``details.reason`` annotation.
    blocked_on_deferred = 0

    if upstream_contract_versions is None:
        upstream_contract_versions = _frozen_upstream_contract_versions()
    if run_environment is None:
        run_environment = _stable_run_environment_metadata()
    if generated_at is None:
        generated_at = _now_utc_iso8601()
    if license_boundary_attestation is None:
        license_boundary_attestation = {
            "any_restricted_source_inputs": False,
            "any_restricted_source_outputs": False,
            "restricted_source_pointer_only_observed": True,
        }

    # Deterministic report_id derived from case IDs (sorted) + schema + impl
    case_ids = tuple(b["case_id"] for b in blocks)
    report_id = deterministic_report_id(case_ids=case_ids)

    report: dict[str, Any] = {
        "report_schema_version": TASK_019_VALIDATION_REPORT_V1,
        "report_id": report_id,
        "generated_at": generated_at,
        "upstream_contract_versions": dict(upstream_contract_versions),
        "run_environment": dict(run_environment),
        "golden_cases": blocks,
        "aggregate_summary": {
            "total_cases": total,
            "passed": passed,
            "failed": failed,
            "not_computable": not_computable,
            "blocked_on_deferred_amendments": blocked_on_deferred,
        },
        "license_boundary_attestation": dict(license_boundary_attestation),
    }
    return report


# --- Slice 1 self-check (deterministic; not a test) ---


def _self_check() -> None:
    """Slice 1 self-check (deterministic; not a test).

    Verifies that:
    - ``canonical_json_dumps`` is deterministic across repeated calls.
    - ``sha256_hex`` returns 64 lowercase hex chars.
    - ``deterministic_report_id`` returns a stable UUID for the same seed.
    - ``build_double_pipe_validation_report`` produces a §7.1-shaped dict.
    """
    # canonical_json determinism
    obj1 = {"b": 1, "a": 2, "nested": {"y": 2, "x": 1}}
    s1 = canonical_json_dumps(obj1)
    s2 = canonical_json_dumps(obj1)
    assert s1 == s2, "canonical_json_dumps is not deterministic"
    assert s1 == '{"a":2,"b":1,"nested":{"x":1,"y":2}}', (
        f"canonical_json_dumps produced unexpected output: {s1!r}"
    )

    # sha256_hex shape
    h1 = sha256_hex("hello")
    assert len(h1) == 64 and h1 == h1.lower(), f"sha256_hex returned non-canonical hash: {h1!r}"
    h2 = sha256_hex("hello")
    assert h1 == h2, "sha256_hex is not deterministic"

    # deterministic_report_id shape + stability
    rid1 = deterministic_report_id()
    rid2 = deterministic_report_id()
    assert rid1 == rid2, "deterministic_report_id is not deterministic"
    # UUID v5 string format (version digit 5 is at position 14 per RFC 4122)
    assert len(rid1) == 36 and rid1[14] == "5", (
        f"deterministic_report_id returned non-UUIDv5 string: {rid1!r}"
    )


_self_check()
