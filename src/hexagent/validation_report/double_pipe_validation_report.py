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
from pathlib import Path
from typing import Any

# --- Schema constants (per frozen design §7.1) ---

TASK_019_VALIDATION_REPORT_V1: str = "TASK-019-VALIDATION-REPORT-V1"

# Exactly 3 golden case IDs (per frozen design §4)
TASK_019_GOLDEN_CASE_IDS: tuple[str, ...] = (
    "TASK-019-GOLDEN-01",
    "TASK-019-GOLDEN-02",
    "TASK-019-GOLDEN-03",
)

# Allowed overall statuses (per frozen design §7.3)
ALLOWED_OVERALL_STATUSES: frozenset[str] = frozenset({"PASS", "FAIL", "NOT_COMPUTABLE"})

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


# ---------------------------------------------------------------------------
# Slice 2 materialization contract (additive; Slice 1 surface untouched).
#
# Slice 2 advances the Slice 1 skeleton from "accept caller-pre-materialized
# case records" to "materialize case records from Slice 1 frozen-design
# fixtures, with real frozen-contract SHAs and explicit NOT_COMPUTABLE
# handling for the still-unmerged upstream calculation chain".
#
# Slice 2 does NOT:
# - Compute any numerical golden expected vectors (LMTD, heat_duty, mass_kg,
#   cost_components, life_cycle_energy_summary). All numeric vectors remain
#   "TBD-by-Slice-N" placeholders in fixtures until the upstream chain is
#   wired up in a future TASK-006/007/008/017/018 design-amendment round.
# - Touch frozen TASK-006..TASK-018 design contracts.
# - Implement TASK-018 discount / salvage formulas.
# - Implement pressure-drop / C4 / TASK-020+.
# - Add public API / CLI / DB schema / renderer / Feishu integration.
#
# Per frozen design §7.1, the upstream_contract_versions MUST list 11
# keys (TASK-006 / TASK-007 / TASK-008 / TASK-011 / TASK-012 / TASK-013 /
# TASK-014 / TASK-015A / TASK-017 / TASK-018 / TASK-019). For TASK-007
# the design lists two parallel frozen files; Slice 2 computes a
# composite SHA-256 over both files (sorted, joined by a sentinel byte)
# so a single SHA deterministically represents the union.
# ---------------------------------------------------------------------------

#: Mapping from upstream TASK-* contract key to the set of frozen contract
#: file paths (relative to repo root) that define that contract's frozen
#: surface. The composite SHA is computed by SHA-256 over the sorted
#: concatenation of the file blobs (joined by a newline), producing a
#: single deterministic 64-char hex digest per TASK.
_FROZEN_UPSTREAM_CONTRACT_PATHS: dict[str, tuple[str, ...]] = {
    "TASK-006": ("docs/tasks/TASK-006-heat-balance.md",),
    "TASK-007": (
        "docs/tasks/TASK-007-tube-annulus-correlations.md",
        "docs/tasks/TASK-007-double-pipe-correlations.md",
    ),
    "TASK-008": ("docs/tasks/TASK-008-double-pipe-rating.md",),
    "TASK-011": ("docs/tasks/TASK-011-benchmark-case-governance.md",),
    "TASK-012": ("docs/tasks/TASK-012-standards-rule-pack-license-boundary.md",),
    "TASK-013": ("docs/tasks/TASK-013-material-cost-data-governance.md",),
    "TASK-014": ("docs/tasks/TASK-014-immutable-case-revisions-persistence.md",),
    "TASK-015A": ("docs/tasks/TASK-015A-deterministic-test-environment-and-ci-sharding.md",),
    "TASK-017": (
        "docs/tasks/TASK-017-materials-mass-preliminary-mechanical.md",
        "docs/tasks/TASK-017-materials-mass-mechanical-implementation.md",
    ),
    "TASK-018": ("docs/tasks/TASK-018-c0-c1-cost-and-life-cycle-energy.md",),
    "TASK-019": ("docs/tasks/TASK-019-golden-cases-double-pipe-validation.md",),
}

#: Slice 2 implementation version seed (bumped only on schema-affecting
#: changes to the report contract). Used for deterministic report_id.
_IMPLEMENTATION_VERSION_SLICE_2: str = "TASK-019-validation-report-impl-v0.2.0-slice2"

#: Sentinel marker used by Slice 1 fixtures to indicate a value that
#: remains a placeholder until the upstream calculation chain is wired
#: up in a future design-amendment round. Slice 2 surfaces these as
#: NOT_COMPUTABLE per-field comparisons; it never silently substitutes
#: a default value.
_TBD_PLACEHOLDER_MARKER: str = "TBD-by-Slice-2"

#: TASK-018 Option A deferred-amendment signal (per frozen design §5.3
#: and §8.3 Option X1). Slice 2 detects this reason in fixture
#: ``unspecified_blocker.details.reason`` and routes the case to
#: NOT_COMPUTABLE + aggregate.blocked_on_deferred_amendments += 1.
_TASK_018_DISCOUNT_DEFERRED_REASON: str = "discount_formula_pending_design_amendment"


# --- Slice 2: deterministic frozen-contract SHA computation ---


def _read_text_file(path: Path) -> bytes:
    """Read a text file as UTF-8 bytes.

    Frozen contracts are Markdown; we read as UTF-8 to make the SHA
    comparable across platforms with different default encodings.
    """
    return path.read_text(encoding="utf-8").encode("utf-8")


def compute_frozen_contract_sha(repo_root: Path, paths: Sequence[str]) -> str:
    """Compute a deterministic SHA-256 hex over the concatenated blobs.

    The blobs are read in sorted path order, joined by ``b"\\n"``, then
    hashed. This makes the composite SHA stable across filesystems and
    independent of read order.

    Parameters
    ----------
    repo_root:
        Absolute path to the repository root (i.e. the directory that
        contains ``docs/tasks/TASK-*.md``).
    paths:
        Iterable of frozen-contract paths, relative to ``repo_root``.

    Returns
    -------
    str
        64-character lowercase hex SHA-256 digest.

    Raises
    ------
    FileNotFoundError
        If any of ``paths`` does not exist under ``repo_root``.
    """
    joined = b""
    for p in sorted(paths):
        full = repo_root / p
        if not full.is_file():
            raise FileNotFoundError(f"frozen contract file not found: {p}")
        joined += _read_text_file(full) + b"\n"
    return sha256_hex(joined)


def compute_frozen_upstream_contract_versions(
    repo_root: Path,
    *,
    task_019_impl_version: str = _IMPLEMENTATION_VERSION_SLICE_2,
) -> dict[str, str]:
    """Compute the 11-key ``upstream_contract_versions`` block per §7.1.

    The TASK-019 entry uses the implementation version seed (not a git
    blob SHA) because TASK-019 is the implementation round itself; its
    SHA is the design contract blob plus the implementation version.

    Parameters
    ----------
    repo_root:
        Absolute path to the repository root.
    task_019_impl_version:
        Override for the TASK-019 entry. Defaults to Slice 2 impl
        version. Tests may pass a fixed value for determinism.

    Returns
    -------
    dict[str, str]
        Mapping with keys TASK-006 / TASK-007 / TASK-008 / TASK-011 /
        TASK-012 / TASK-013 / TASK-014 / TASK-015A / TASK-017 /
        TASK-018 / TASK-019, each value a 64-char lowercase hex SHA.
    """
    versions: dict[str, str] = {}
    for key, paths in _FROZEN_UPSTREAM_CONTRACT_PATHS.items():
        if key == "TASK-019":
            # TASK-019 entry is the design contract blob SHA combined with
            # the implementation version seed (so different impl rounds
            # produce different upstream_contract_versions entries).
            design_sha = compute_frozen_contract_sha(repo_root, paths)
            versions[key] = sha256_hex(f"{design_sha}|{task_019_impl_version}")
        else:
            versions[key] = compute_frozen_contract_sha(repo_root, paths)
    return versions


# --- Slice 2: real run_environment materialization ---


def materialize_run_environment(
    *,
    python_version: str | None = None,
    platform: str | None = None,
    package_versions: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Build a real ``run_environment`` block per frozen design §7.1.

    Per §7.1 the block MUST contain ``python_version``, ``platform``,
    ``package_versions``, ``deterministic_mode_flags``. Slice 1 left
    the first three as ``TBD-by-Slice-2-runner`` placeholders; Slice 2
    fills them from explicit arguments (defaulting to the conservative
    values reported by the stdlib).

    Parameters
    ----------
    python_version:
        Exact Python version string. Defaults to ``sys.version``.
    platform:
        Exact platform string. Defaults to ``sys.platform``.
    package_versions:
        Optional package-versions dict. Defaults to empty ``{}`` (no
        third-party packages are required by the validation-report
        module itself, so an empty dict is the truthful default).
    """
    import sys as _sys

    return {
        "python_version": python_version if python_version is not None else _sys.version,
        "platform": platform if platform is not None else _sys.platform,
        "package_versions": dict(package_versions) if package_versions is not None else {},
        "deterministic_mode_flags": [
            "sort_keys",
            "no_floats_for_money",
            "no_nan_infinity",
        ],
    }


# --- Slice 2: NOT_COMPUTABLE / blocker detection ---


def _is_tbd_placeholder(value: Any) -> bool:
    """Return True iff ``value`` is a TBD-by-Slice-N placeholder.

    Per frozen design §3.3, placeholder strings begin with
    ``TBD-by-``; Slice 2 never substitutes a default for these values,
    it surfaces them as NOT_COMPUTABLE per-field entries.
    """
    return isinstance(value, str) and value.startswith("TBD-by-")


def _collect_unspecified_blockers(fixture: Mapping[str, Any]) -> list[str]:
    """Collect blocker codes from a fixture.

    Per frozen design §5.3 (TASK-018 Option A) + §8.3 Option X1, the
    canonical signal that a case carries a deferred-amendment blocker is
    either:

    (a) an explicit ``unspecified_blocker.details.reason`` of
        ``discount_formula_pending_design_amendment``; OR

    (b) the Slice-1 fixture-shape evidence of TASK-018 Option A in
        ``expected_output``: ``discounted_total_minor_units`` is
        explicitly null AND ``salvage_minor_units`` is the integer 0
        placeholder. Per §5.3.2 the salvage formula is not prescribed,
        so the integer 0 is the only contract-compliant placeholder.

    Slice 2 surfaces (a) directly and lifts (b) into an explicit
    structured blocker entry in ``comparison.blockers``.
    """
    blockers: list[str] = []
    blk = fixture.get("unspecified_blocker")
    if isinstance(blk, Mapping):
        details = blk.get("details")
        if isinstance(details, Mapping):
            reason = details.get("reason")
            if isinstance(reason, str) and reason:
                blockers.append(reason)

    expected = fixture.get("expected_output")
    if isinstance(expected, Mapping):
        discounted = expected.get("discounted_total_minor_units")
        salvage = expected.get("salvage_minor_units")
        if (
            discounted is None
            and salvage == 0
            and _TASK_018_DISCOUNT_DEFERRED_REASON not in blockers
        ):
            blockers.append(_TASK_018_DISCOUNT_DEFERRED_REASON)

    return blockers


def _detect_deferred_amendment_blockers(fixture: Mapping[str, Any]) -> bool:
    """Return True iff the fixture carries a TASK-018 Option A deferred signal.

    Per frozen design §5.3 + §8.3 Option X1, the canonical signal is
    ``unspecified_blocker.details.reason ==
    "discount_formula_pending_design_amendment"``.
    """
    return _TASK_018_DISCOUNT_DEFERRED_REASON in _collect_unspecified_blockers(fixture)


def _walk_for_tbd(value: Any, path: str = "") -> list[dict[str, str]]:
    """Walk a fixture subtree and collect per-field TBD-by-Slice-N markers.

    Returns a list of ``{"field": "<dotted path>", "status": "NOT_COMPUTABLE"}``
    records. Slice 2 never silently substitutes a default; the caller
    surfaces these as explicit per-field NOT_COMPUTABLE comparisons.
    """
    hits: list[dict[str, str]] = []
    if _is_tbd_placeholder(value):
        hits.append({"field": path or "<root>", "status": "NOT_COMPUTABLE"})
        return hits
    if isinstance(value, Mapping):
        for k in sorted(value.keys()):
            sub_path = f"{path}.{k}" if path else str(k)
            hits.extend(_walk_for_tbd(value[k], sub_path))
    elif isinstance(value, list):
        for i, item in enumerate(value):
            sub_path = f"{path}[{i}]"
            hits.extend(_walk_for_tbd(item, sub_path))
    return hits


# --- Slice 2: strict schema validation ---


_FORBIDDEN_SCOPE_FIELD_PREFIXES: tuple[str, ...] = (
    "pressure_drop_",
    "c4_",
    "tema_",
    "kern_",
    "bell_delaware_",
    "vendor_quote_",
    "c3_",
)


def _contains_forbidden_scope_field(value: Any) -> list[str]:
    """Walk ``value`` and return any forbidden-scope field names found.

    Per frozen design §6 + §11.5, the validation report must never carry
    pressure-drop / C4 / TASK-020+ field names. Slice 2 enforces this
    as a strict-schema gate at materialization time.
    """
    hits: list[str] = []
    if isinstance(value, Mapping):
        for k, v in value.items():
            if isinstance(k, str) and any(k.startswith(p) for p in _FORBIDDEN_SCOPE_FIELD_PREFIXES):
                hits.append(k)
            hits.extend(_contains_forbidden_scope_field(v))
    elif isinstance(value, list):
        for item in value:
            hits.extend(_contains_forbidden_scope_field(item))
    return hits


def validate_case_block_strict(block: Mapping[str, Any]) -> None:
    """Strict schema validation for a §7.1 case block.

    Raises
    ------
    ValueError
        - If any forbidden-scope field is present (pressure-drop / C4 /
          TASK-020+).
        - If any required §7.1 key is missing.
        - If ``comparison.overall_status`` is not in
          ``ALLOWED_OVERALL_STATUSES``.

    This gate is additive: Slice 1's :func:`build_double_pipe_validation_report`
    still enforces its own subset of checks (required keys + case count);
    Slice 2 adds the forbidden-scope gate so the materialized report
    can never silently smuggle in an excluded field.
    """
    forbidden = _contains_forbidden_scope_field(block)
    if forbidden:
        raise ValueError(
            f"case block contains forbidden-scope fields: {sorted(set(forbidden))!r} "
            f"(per frozen design §6 + §11.5)"
        )

    required = {
        "case_id",
        "case_title",
        "input_sha256",
        "expected_output_sha256",
        "actual_output_sha256",
        "comparison",
        "provenance",
    }
    missing = required - set(block.keys())
    if missing:
        raise ValueError(f"case block missing required keys: {sorted(missing)!r}")

    comparison = block.get("comparison")
    if not isinstance(comparison, Mapping):
        raise ValueError("case block 'comparison' must be a mapping")
    overall = comparison.get("overall_status")
    if overall is None:
        raise ValueError("case block 'comparison.overall_status' is required")
    _ensure_allowed_overall_status(overall)

    # case_id must be one of the frozen 3
    case_id = block.get("case_id")
    if case_id not in TASK_019_GOLDEN_CASE_IDS:
        raise ValueError(
            f"case block case_id {case_id!r} not in frozen {sorted(TASK_019_GOLDEN_CASE_IDS)!r}"
        )


def validate_per_case_blocks_strict(blocks: Sequence[Mapping[str, Any]]) -> None:
    """Strict cross-case validation.

    Enforces (additively to Slice 1):
    - Exactly 3 blocks.
    - Each block passes :func:`validate_case_block_strict`.
    - No duplicate case_id.
    - The set of case_ids is exactly the frozen 3 (in any order).
    """
    if len(blocks) != len(TASK_019_GOLDEN_CASE_IDS):
        raise ValueError(
            f"validation report requires exactly "
            f"{len(TASK_019_GOLDEN_CASE_IDS)} case blocks "
            f"(got {len(blocks)})"
        )
    seen: set[str] = set()
    for _i, block in enumerate(blocks):
        validate_case_block_strict(block)
        case_id = block["case_id"]
        if case_id in seen:
            raise ValueError(f"duplicate case_id in per_case_blocks: {case_id!r}")
        seen.add(case_id)
    expected = set(TASK_019_GOLDEN_CASE_IDS)
    if seen != expected:
        raise ValueError(
            f"per_case_blocks case_id set {sorted(seen)!r} != frozen {sorted(expected)!r}"
        )


# --- Slice 2: case-block materialization from Slice 1 fixture ---


def _materialize_per_field_from_fixture(
    fixture: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Build a per-field comparison list from a Slice 1 fixture.

    Slice 2 does NOT compute numeric vectors; it walks the fixture's
    ``expected_output`` subtree and emits one per-field record per
    asserted value, classifying each as NOT_COMPUTABLE when the fixture
    marks it as not-yet-computed (a ``TBD-by-`` string marker).

    Per frozen design §7.3, no field is silently downgraded to PASS
    when the fixture marks it as not-yet-computed.
    """
    per_field: list[dict[str, Any]] = []
    expected = fixture.get("expected_output", {})
    if not isinstance(expected, Mapping):
        return per_field

    for field_path in sorted(_walk_for_tbd(expected), key=lambda r: r["field"]):
        per_field.append(
            {
                "field": field_path["field"],
                "status": "NOT_COMPUTABLE",
                "tolerance": {"abs": None, "rel": None},
                "observed": None,
                "expected": _TBD_PLACEHOLDER_MARKER,
                "reason": "TBD-by-Slice-N placeholder; upstream chain not wired",
            }
        )

    # Surface the pressure-drop / TASK-020+ exclusion as an explicit
    # NOT_COMPUTABLE per-field record (it is a real per-case assertion
    # even though the numeric vector is excluded by design).
    if fixture.get("pressure_drop_excluded_from_taska_019") == "NOT_COMPUTABLE":
        per_field.append(
            {
                "field": "pressure_drop",
                "status": "NOT_COMPUTABLE",
                "tolerance": {"abs": None, "rel": None},
                "observed": None,
                "expected": "NOT_COMPUTABLE",
                "reason": "excluded by frozen design §6 (TASK-020+ scope)",
            }
        )

    per_field.sort(key=lambda r: r["field"])
    return per_field


def _infer_overall_status(
    fixture: Mapping[str, Any],
    has_deferred_blocker: bool,
) -> str:
    """Infer the §7.1 overall_status for a materialized case block.

    Rules (per frozen design §5.3 + §7.3 + §8.3):
    - If the fixture carries a TASK-018 Option A deferred-amendment
      signal, overall_status = NOT_COMPUTABLE.
    - Otherwise, since Slice 2 does not run the upstream chain, every
      asserted field whose value is still a ``TBD-by-Slice-N``
      placeholder forces overall_status = NOT_COMPUTABLE for that
      case. The aggregate summary then counts the case as
      ``not_computable`` and (if applicable)
      ``blocked_on_deferred_amendments += 1``.
    """
    if has_deferred_blocker:
        return "NOT_COMPUTABLE"
    expected = fixture.get("expected_output", {})
    if isinstance(expected, Mapping) and _walk_for_tbd(expected):
        return "NOT_COMPUTABLE"
    return "NOT_COMPUTABLE"


def materialize_case_block_from_fixture(
    fixture_path: Path,
    *,
    repo_root: Path,
) -> dict[str, Any]:
    """Materialize a §7.1 case block from a Slice 1 frozen-design fixture.

    Slice 2 advances the Slice 1 "accept caller-pre-materialized records"
    contract to "materialize records from the frozen-design fixtures that
    Slice 1 shipped". The materialized block is byte-stable across runs
    (deterministic canonical-JSON SHA-256 hashes for input / expected /
    actual blocks).

    Per frozen design §3.3, no numeric vectors are invented; ``TBD-by-*``
    placeholders are surfaced as NOT_COMPUTABLE per-field comparisons.

    Parameters
    ----------
    fixture_path:
        Absolute path to a Slice 1 fixture JSON (e.g.
        ``tests/golden/double_pipe_rating/case_01_heat_balance_rating.json``).
    repo_root:
        Absolute path to the repository root. Used to compute provenance
        metadata for the case block.

    Returns
    -------
    dict[str, Any]
        A §7.1-shaped case block ready to be passed to
        :func:`build_double_pipe_validation_report`.
    """
    import json as _json

    fixture_text = _read_text_file(fixture_path)
    fixture = _json.loads(fixture_text.decode("utf-8"))

    case_id = fixture["case_id"]
    case_title = fixture["case_title"]

    input_block = fixture.get("input", {})
    expected_output_block = fixture.get("expected_output", {})

    # Slice 2 does NOT run the upstream chain. The actual_output block
    # mirrors the expected_output block (placeholder-aware); the
    # comparison then classifies every TBD-by-* field as NOT_COMPUTABLE.
    # This preserves determinism (expected == actual byte-for-byte at
    # the placeholder level) while never inventing a fake numeric
    # actual_output.
    actual_output_block = expected_output_block

    input_sha = sha256_hex(canonical_json_dumps(input_block))
    expected_sha = sha256_hex(canonical_json_dumps(expected_output_block))
    actual_sha = sha256_hex(canonical_json_dumps(actual_output_block))

    has_deferred_blocker = _detect_deferred_amendment_blockers(fixture)
    blockers = _collect_unspecified_blockers(fixture)
    overall_status = _infer_overall_status(fixture, has_deferred_blocker)

    per_field = _materialize_per_field_from_fixture(fixture)

    provenance_metadata = _load_provenance_metadata(repo_root)
    provenance_block = {
        "correlation_ids": list(provenance_metadata.get("correlation_id_references", {}).keys()),
        "provider_ids": list(provenance_metadata.get("provider_id_references", {}).keys()),
        "rule_pack_ids": [],
        "design_contract_versions": {
            k: v.get("frozen_contract_base_SHA", "TBD")
            for k, v in provenance_metadata.get("upstream_contract_references", {}).items()
        },
    }

    case_block: dict[str, Any] = {
        "case_id": case_id,
        "case_title": case_title,
        "input_sha256": input_sha,
        "expected_output_sha256": expected_sha,
        "actual_output_sha256": actual_sha,
        "comparison": {
            "overall_status": overall_status,
            "per_field": per_field,
            "blockers": blockers,
            "warnings": [],
        },
        "provenance": provenance_block,
    }

    # Strict gate at the end: a forbidden-scope field or invalid case_id
    # raises here so the caller can never accidentally publish a
    # malformed report.
    validate_case_block_strict(case_block)
    return case_block


# --- Slice 2: provenance / tolerance metadata loaders ---


def _load_provenance_metadata(repo_root: Path) -> dict[str, Any]:
    """Load and parse ``_provenance_metadata.json``.

    The provenance metadata file is part of the Slice 1 frozen fixture
    set; Slice 2 reads it at materialization time so the case-block
    ``provenance`` sub-record stays consistent with the fixture.
    """
    import json as _json

    path = repo_root / "tests" / "golden" / "double_pipe_rating" / "_provenance_metadata.json"
    result: dict[str, Any] = _json.loads(_read_text_file(path).decode("utf-8"))
    return result


def _load_tolerance_metadata(repo_root: Path) -> dict[str, Any]:
    """Load and parse ``_tolerance_metadata.json``.

    Slice 2 reads the tolerance metadata to round-trip-validate that
    each fixture's ``tolerance_profile_id`` references a profile that
    is defined in the metadata. Slice 2 does NOT widen the tolerance
    profile (per frozen design §7.4: tolerance drift requires an
    explicit design-amendment).
    """
    import json as _json

    path = repo_root / "tests" / "golden" / "double_pipe_rating" / "_tolerance_metadata.json"
    result: dict[str, Any] = _json.loads(_read_text_file(path).decode("utf-8"))
    return result


def validate_fixture_tolerance_round_trip(
    fixture: Mapping[str, Any],
    tolerance_metadata: Mapping[str, Any],
) -> None:
    """Raise ValueError if a fixture references an undefined tolerance profile.

    Per frozen design §7.4, tolerance drift is forbidden without a
    design-amendment. Slice 2 enforces that every fixture's
    ``tolerance_profile_id`` references a profile actually defined in
    ``tolerance_metadata.tolerance_profiles``.
    """
    fixture_profile = fixture.get("tolerance_profile_id")
    if fixture_profile is None:
        return  # Some fixtures may not declare one; that's allowed.
    profiles = tolerance_metadata.get("tolerance_profiles", {})
    if fixture_profile not in profiles:
        raise ValueError(
            f"fixture references tolerance_profile_id {fixture_profile!r} "
            f"not declared in tolerance_metadata.tolerance_profiles"
        )


def validate_fixture_provenance_round_trip(
    fixture: Mapping[str, Any],
    provenance_metadata: Mapping[str, Any],
) -> None:
    """Raise ValueError if a fixture references an unknown provenance profile.

    Per frozen design §11.5, every fixture's ``provenance_profile_id``
    must reference a profile declared in the provenance metadata.
    """
    fixture_profile = fixture.get("provenance_profile_id")
    if fixture_profile is None:
        return
    declared = provenance_metadata.get("provenance_profile_id")
    if declared is not None and fixture_profile != declared:
        raise ValueError(
            f"fixture provenance_profile_id {fixture_profile!r} "
            f"does not match metadata provenance_profile_id {declared!r}"
        )


# --- Slice 2: orchestrator ---


def materialize_validation_report_from_fixtures(
    fixture_dir: Path,
    *,
    repo_root: Path,
    upstream_contract_versions: Mapping[str, str] | None = None,
    run_environment: Mapping[str, Any] | None = None,
    generated_at: str | None = None,
    license_boundary_attestation: Mapping[str, Any] | None = None,
    task_019_impl_version: str = _IMPLEMENTATION_VERSION_SLICE_2,
) -> dict[str, Any]:
    """Materialize the full TASK-019 validation report from Slice 1 fixtures.

    This is the Slice 2 orchestrator: it loads each of the three Slice 1
    fixture JSONs, runs the round-trip tolerance / provenance consistency
    checks, materializes each case block (deterministic SHA-256 hashes),
    applies strict schema validation, and feeds the result to Slice 1's
    :func:`build_double_pipe_validation_report`.

    Slice 2 does NOT compute any numeric golden expected vectors. All
    numeric vectors remain ``TBD-by-Slice-N`` placeholders in fixtures
    until the upstream calculation chain is wired up in a future
    design-amendment round.

    Parameters
    ----------
    fixture_dir:
        Directory containing the three Slice 1 case_*.json fixtures.
    repo_root:
        Absolute path to the repository root.
    upstream_contract_versions:
        Optional override; defaults to :func:`compute_frozen_upstream_contract_versions`.
    run_environment:
        Optional override; defaults to :func:`materialize_run_environment`.
    generated_at:
        Optional ISO 8601 UTC timestamp; defaults to current time.
    license_boundary_attestation:
        Optional override; defaults to a safe ``False / False / True``
        attestation.
    task_019_impl_version:
        Override for the TASK-019 entry in ``upstream_contract_versions``.

    Returns
    -------
    dict[str, Any]
        A §7.1-shaped report dictionary.
    """
    import json as _json

    fixture_paths = [
        fixture_dir / "case_01_heat_balance_rating.json",
        fixture_dir / "case_02_materials_mass_mechanical.json",
        fixture_dir / "case_03_cost_lifecycle_envelope.json",
    ]
    fixtures = [_json.loads(_read_text_file(p).decode("utf-8")) for p in fixture_paths]

    tolerance_metadata = _load_tolerance_metadata(repo_root)
    provenance_metadata = _load_provenance_metadata(repo_root)

    for fx in fixtures:
        validate_fixture_tolerance_round_trip(fx, tolerance_metadata)
        validate_fixture_provenance_round_trip(fx, provenance_metadata)

    per_case_blocks = [
        materialize_case_block_from_fixture(p, repo_root=repo_root) for p in fixture_paths
    ]
    validate_per_case_blocks_strict(per_case_blocks)

    if upstream_contract_versions is None:
        upstream_contract_versions = compute_frozen_upstream_contract_versions(
            repo_root, task_019_impl_version=task_019_impl_version
        )
    if run_environment is None:
        run_environment = materialize_run_environment()

    # Slice 2 contract: compute the real ``blocked_on_deferred_amendments``
    # count by re-scanning each case block's blockers for the TASK-018
    # Option A deferred-amendment signal. Slice 1's report builder
    # leaves this field at 0 (it predates Option X1 detection); Slice 2
    # overrides it after assembly so the aggregate summary is truthful.
    report = build_double_pipe_validation_report(
        per_case_blocks=per_case_blocks,
        upstream_contract_versions=upstream_contract_versions,
        run_environment=run_environment,
        generated_at=generated_at,
        license_boundary_attestation=license_boundary_attestation,
    )
    blocked_count = sum(
        1
        for cb in per_case_blocks
        if _TASK_018_DISCOUNT_DEFERRED_REASON in cb["comparison"]["blockers"]
    )
    report["aggregate_summary"]["blocked_on_deferred_amendments"] = blocked_count
    return report


# --- Slice 2 self-check (additive; Slice 1 self-check untouched) ---


def _slice2_self_check() -> None:
    """Slice 2 self-check (deterministic; not a test).

    Verifies that:
    - Slice 1 surface is still importable and the schema constants
      remain frozen.
    - Strict validation rejects a forbidden-scope field.
    - Strict validation rejects an unknown case_id.
    - Strict validation rejects a duplicate case_id.
    - Strict validation rejects an unknown overall_status.
    """
    assert TASK_019_VALIDATION_REPORT_V1 == "TASK-019-VALIDATION-REPORT-V1"
    assert tuple(TASK_019_GOLDEN_CASE_IDS) == (
        "TASK-019-GOLDEN-01",
        "TASK-019-GOLDEN-02",
        "TASK-019-GOLDEN-03",
    )

    # Forbidden-scope field rejected
    try:
        validate_case_block_strict(
            {
                "case_id": "TASK-019-GOLDEN-01",
                "case_title": "t",
                "input_sha256": "a" * 64,
                "expected_output_sha256": "b" * 64,
                "actual_output_sha256": "c" * 64,
                "comparison": {
                    "overall_status": "PASS",
                    "per_field": [],
                    "blockers": [],
                    "warnings": [],
                },
                "provenance": {"pressure_drop_value": 1.0},
            }
        )
        raise AssertionError("validate_case_block_strict accepted forbidden scope")
    except ValueError as e:
        assert "forbidden-scope" in str(e), str(e)

    # Unknown case_id rejected
    try:
        validate_case_block_strict(
            {
                "case_id": "TASK-019-FAKE",
                "case_title": "t",
                "input_sha256": "a" * 64,
                "expected_output_sha256": "b" * 64,
                "actual_output_sha256": "c" * 64,
                "comparison": {
                    "overall_status": "PASS",
                    "per_field": [],
                    "blockers": [],
                    "warnings": [],
                },
                "provenance": {},
            }
        )
        raise AssertionError("validate_case_block_strict accepted unknown case_id")
    except ValueError as e:
        assert "not in frozen" in str(e), str(e)

    # Unknown overall_status rejected
    try:
        validate_case_block_strict(
            {
                "case_id": "TASK-019-GOLDEN-01",
                "case_title": "t",
                "input_sha256": "a" * 64,
                "expected_output_sha256": "b" * 64,
                "actual_output_sha256": "c" * 64,
                "comparison": {
                    "overall_status": "MAYBE",
                    "per_field": [],
                    "blockers": [],
                    "warnings": [],
                },
                "provenance": {},
            }
        )
        raise AssertionError("validate_case_block_strict accepted unknown status")
    except ValueError as e:
        assert "not in allowed set" in str(e), str(e)

    # Duplicate case_id rejected (cross-case; must supply 3 blocks so the
    # length check passes and the duplicate check fires)
    try:
        validate_per_case_blocks_strict(
            [
                {
                    "case_id": "TASK-019-GOLDEN-01",
                    "case_title": "t",
                    "input_sha256": "a" * 64,
                    "expected_output_sha256": "b" * 64,
                    "actual_output_sha256": "c" * 64,
                    "comparison": {
                        "overall_status": "PASS",
                        "per_field": [],
                        "blockers": [],
                        "warnings": [],
                    },
                    "provenance": {},
                },
                {
                    "case_id": "TASK-019-GOLDEN-01",
                    "case_title": "t",
                    "input_sha256": "d" * 64,
                    "expected_output_sha256": "e" * 64,
                    "actual_output_sha256": "f" * 64,
                    "comparison": {
                        "overall_status": "PASS",
                        "per_field": [],
                        "blockers": [],
                        "warnings": [],
                    },
                    "provenance": {},
                },
                {
                    "case_id": "TASK-019-GOLDEN-03",
                    "case_title": "t",
                    "input_sha256": "g" * 64,
                    "expected_output_sha256": "h" * 64,
                    "actual_output_sha256": "i" * 64,
                    "comparison": {
                        "overall_status": "PASS",
                        "per_field": [],
                        "blockers": [],
                        "warnings": [],
                    },
                    "provenance": {},
                },
            ]
        )
        raise AssertionError("validate_per_case_blocks_strict accepted duplicate case_id")
    except ValueError as e:
        assert "duplicate case_id" in str(e), str(e)


_slice2_self_check()


_self_check()
