"""TASK-015 spec validator.

Implements the TASK-015 frozen design contract
(docs/tasks/TASK-015-ci-security-and-release-automation.md,
Frozen Contract Authority SHA
``39135e269b014e9c9310ac403a60591393d46b2d``).

Section 9 — Determinism / hashing / provenance.

* 9.1 Determinism — the in-memory representation MUST be byte-identical
  across runs given the same file content. Field ordering MUST NOT
  affect the canonical representation (sorted-key normalization).
* 9.2 Hashing — every spec file MUST have a ``sha256`` ``content_hash``
  field computed over the canonical in-memory representation.
* 9.3 Provenance — every spec MUST declare ``owner`` (GitHub username)
  and ``updated_at`` ISO-8601 timestamp (Section 4.2).

Section 10 — Restricted-content boundary. The scan is metadata-driven
(marker list at the end of this module) and follows the TASK-014
pattern: only string *values* are scanned (keys are metadata), and
the standard-body tokens use word-boundary matching to avoid false
positives on, e.g., the literal string ``ISO`` appearing inside
``source_kind="iso8601"``.

Section 11.1 / 11.2 — required tests (this module is what they
exercise).

This module is deliberately small and self-contained. It does NOT
parse :class:`pathlib.Path` non-spec files; it operates on YAML /
JSON in-memory data plus a ``spec_path`` label so the validator can
also be exercised on synthetic test inputs (Section 11.4 — tests use
synthetic / metadata-only placeholders).
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import yaml  # type: ignore[import-untyped]

from hexagent.governance.errors import (
    FAILURE_TAXONOMY_MODES,
    SpecSchemaError,
)

# ---------------------------------------------------------------------------
# Spec paths (Section 4.1)
# ---------------------------------------------------------------------------

SPEC_PATH_CI_PIPELINE = "docs/governance/ci_pipeline_spec.yaml"
SPEC_PATH_SECURITY_GATE = "docs/governance/security_gate_spec.yaml"
SPEC_PATH_RELEASE = "docs/governance/release_spec.yaml"
SPEC_PATH_FAILURE_TAXONOMY = "docs/governance/failure_taxonomy.yaml"

ALL_SPEC_PATHS: tuple[str, ...] = (
    SPEC_PATH_CI_PIPELINE,
    SPEC_PATH_SECURITY_GATE,
    SPEC_PATH_RELEASE,
    SPEC_PATH_FAILURE_TAXONOMY,
)

# ---------------------------------------------------------------------------
# Schema-version policy (Section 4.2.2)
# ---------------------------------------------------------------------------

SUPPORTED_SCHEMA_VERSIONS: frozenset[int] = frozenset({1})

# ---------------------------------------------------------------------------
# Required fields per spec type (Section 4.2)
# ---------------------------------------------------------------------------

# Top-level required fields shared by every spec.
COMMON_REQUIRED_FIELDS: tuple[str, ...] = (
    "schema_version",
    "owner",
    "updated_at",
    "failure_modes",
    "content_hash",
)

# Per-spec required additional fields (Section 4.1 / 4.3).
SPEC_REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    SPEC_PATH_CI_PIPELINE: ("canonical_name",),
    SPEC_PATH_SECURITY_GATE: ("gate_id",),
    SPEC_PATH_RELEASE: ("release_channel",),
    SPEC_PATH_FAILURE_TAXONOMY: (),  # failure_modes is required and IS the content
}

# Per-spec identifier field used for cross-spec uniqueness checks
# (Section 4.3 + Section 11.1 item 5 + Section 11.2 item 10).
SPEC_IDENTIFIER_FIELDS: dict[str, str] = {
    SPEC_PATH_CI_PIPELINE: "canonical_name",
    SPEC_PATH_SECURITY_GATE: "gate_id",
    SPEC_PATH_RELEASE: "release_channel",
    SPEC_PATH_FAILURE_TAXONOMY: "",  # taxonomy has no single identifier
}


# ---------------------------------------------------------------------------
# Restricted-content marker scan (Section 10)
#
# Per Section 11.4 tests use synthetic / metadata-only placeholders
# (e.g., ``internal://handbook/<id>``); literal restricted markers MUST
# NOT appear in source code. The marker list below is metadata-driven
# (Section 10 final paragraph).
#
# Following the TASK-014 pattern, only string *values* are scanned (keys
# are metadata and exempt). Standard-body tokens use word-boundary
# matching so legitimate references like ``source_kind="iso8601"`` do
# not trigger a false positive.
# ---------------------------------------------------------------------------

# Section 15.1 — standards-body tokens (Section 10 in TASK-015).
# Word-boundary match (case-insensitive) to avoid false positives on
# field values like ``source_kind="iso8601"``.
RESTRICTED_STANDARDS_BODY_TOKENS: tuple[str, ...] = (
    "ASME",
    "ASTM",
    "ISO",
    "EN",
    "GB",
    "JIS",
    "DIN",
    "NFPA",
    "TEMA",
    "API",
    "AWS",
    "ASHRAE",
    "IIAR",
    "EIGA",
)

# Section 15.2 — vendor catalog body phrase (Section 10 in TASK-015).
RESTRICTED_VENDOR_CATALOG_PHRASES: tuple[str, ...] = (
    "vendor catalog body",
    "vendor catalogue body",
)

# Section 15.3 — paid price list phrase.
RESTRICTED_PAID_PRICE_LIST_PHRASES: tuple[str, ...] = (
    "paid price list",
    "price list body",
)

# Section 15.4 — restricted material property table phrase.
RESTRICTED_PROPERTY_TABLE_PHRASES: tuple[str, ...] = (
    "restricted material property table",
    "restricted property table",
)

# Section 15.5 — scanned page / formula image pattern.
RESTRICTED_SCANNED_PAGE_PATTERNS: tuple[str, ...] = (
    r"scanned page",
    r"scan://[^\s]*\d",
    r"image://[^\s]*\d",
    r"formula image",
)

# Section 15.6 — copied standard table phrase.
RESTRICTED_COPIED_TABLE_PHRASES: tuple[str, ...] = (
    "copied standard table",
    "table reproduced from standard",
)

# Backwards-compat alias kept so older call sites do not break.
RESTRICTED_CONTENT_TOKENS: tuple[str, ...] = RESTRICTED_STANDARDS_BODY_TOKENS

# Allowlist of field names whose string values are LEGITIMATE metadata
# enumerations of restricted-content categories (Section 10 + Section
# 11.4). The marker list IS the metadata; the spec is allowed to name
# its own markers in these fields without flagging itself.
RESTRICTED_MARKER_METADATA_FIELDS: frozenset[str] = frozenset(
    {"restricted_source_categories", "violation_kind", "kind"}
)


# ---------------------------------------------------------------------------
# Validation report model (Section 7 — disjoint blockers vs warnings)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ValidationFinding:
    """A single validation finding (Section 7 + 8.3).

    Findings are either blockers (refuse pipeline start) or warnings
    (advisory). The two lists are disjoint (Section 7); see
    :meth:`ValidationReport.assert_disjoint`.
    """

    severity: str  # "blocker" or "warning"
    error_code: str
    field_path: str
    message: str
    context: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "error_code": self.error_code,
            "field_path": self.field_path,
            "message": self.message,
            "context": dict(self.context),
        }


@dataclass(frozen=True)
class ValidationReport:
    """Result of validating one spec or all specs (Section 7)."""

    spec_path: str
    blockers: tuple[ValidationFinding, ...]
    warnings: tuple[ValidationFinding, ...]

    @property
    def is_clean(self) -> bool:
        return not self.blockers and not self.warnings

    def assert_disjoint(self) -> None:
        """Section 7 — blockers and warnings live in disjoint lists."""
        b_paths = {(f.error_code, f.field_path) for f in self.blockers}
        w_paths = {(f.error_code, f.field_path) for f in self.warnings}
        overlap = b_paths & w_paths
        if overlap:
            raise AssertionError(
                f"blockers and warnings overlap on {sorted(overlap)} in spec {self.spec_path!r}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "spec_path": self.spec_path,
            "blockers": [f.to_dict() for f in self.blockers],
            "warnings": [f.to_dict() for f in self.warnings],
        }


# ---------------------------------------------------------------------------
# Deterministic parse (Section 9.1)
# ---------------------------------------------------------------------------


def _sorted_dump(data: Any) -> Any:
    """Return a JSON-roundtrip representation of ``data`` with sorted
    keys (Section 9.1 — field ordering MUST NOT affect canonical form).
    """
    if isinstance(data, Mapping):
        return {k: _sorted_dump(data[k]) for k in sorted(data.keys())}
    if isinstance(data, list):
        return [_sorted_dump(v) for v in data]
    return data


def canonicalize(spec_data: Mapping[str, Any]) -> dict[str, Any]:
    """Return the canonical in-memory representation (Section 9.1).

    Sorted keys at every depth, no whitespace instability.
    """
    result = _sorted_dump(dict(spec_data))
    # ``_sorted_dump`` returns the same structural type (``dict`` /
    # ``list`` / scalar) but the recursive boundary makes the static
    # type ``Any``. We assert the runtime invariant here.
    assert isinstance(result, dict)
    return result


def compute_content_hash(spec_data: Mapping[str, Any]) -> str:
    """Compute the ``content_hash`` (Section 9.2 — sha256 over canonical
    representation, UTF-8, no whitespace).
    """
    canonical = canonicalize(spec_data)
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_spec(source: str | bytes) -> dict[str, Any]:
    """Deterministically parse a YAML source (Section 4.2.1).

    Section 4.2.1 — every spec file MUST be valid YAML 1.2 AND valid
    JSON (round-trip parsable). This loader uses :mod:`yaml` SafeLoader
    which is YAML 1.1-compatible but accepts the subset used by the
    section 4.2.1 rule; round-trip is verified at the call site.

    Returns a dict; raises :class:`SpecSchemaError` on parse failure.
    """
    try:
        if isinstance(source, bytes):
            source = source.decode("utf-8")
        data = yaml.safe_load(source)
    except yaml.YAMLError as exc:
        raise SpecSchemaError(
            f"yaml parse error: {exc}",
            spec_path="<inline>",
            field_path="<root>",
            reason=f"yaml_parse_error: {exc}",
        ) from exc
    if not isinstance(data, dict):
        raise SpecSchemaError(
            "spec root MUST be a mapping",
            spec_path="<inline>",
            field_path="<root>",
            reason="root_not_mapping",
        )
    # Verify JSON round-trip (Section 4.2.1).
    try:
        json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        raise SpecSchemaError(
            f"spec is not JSON-roundtrip-parseable: {exc}",
            spec_path="<inline>",
            field_path="<root>",
            reason=f"json_roundtrip_error: {exc}",
        ) from exc
    return data


# ---------------------------------------------------------------------------
# Field validators (Section 11.1)
# ---------------------------------------------------------------------------


def _is_iso8601_utc(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        # Accept either "2026-07-05T07:00:00Z" or with offset.
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def _validate_field_types(spec_path: str, data: Mapping[str, Any]) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    schema_version = data.get("schema_version")
    if not isinstance(schema_version, int) or isinstance(schema_version, bool):
        findings.append(
            ValidationFinding(
                severity="blocker",
                error_code="spec_schema_error",
                field_path="schema_version",
                message="schema_version MUST be an integer",
                context={"spec_path": spec_path, "field_path": "schema_version"},
            )
        )
    if not isinstance(data.get("owner"), str) or not data.get("owner", "").strip():
        findings.append(
            ValidationFinding(
                severity="blocker",
                error_code="spec_schema_error",
                field_path="owner",
                message="owner MUST be a non-empty string",
                context={"spec_path": spec_path, "field_path": "owner"},
            )
        )
    if not _is_iso8601_utc(data.get("updated_at")):
        findings.append(
            ValidationFinding(
                severity="blocker",
                error_code="spec_schema_error",
                field_path="updated_at",
                message="updated_at MUST be an ISO-8601 UTC timestamp",
                context={"spec_path": spec_path, "field_path": "updated_at"},
            )
        )
    if not isinstance(data.get("failure_modes"), list):
        findings.append(
            ValidationFinding(
                severity="blocker",
                error_code="spec_schema_error",
                field_path="failure_modes",
                message="failure_modes MUST be a list",
                context={"spec_path": spec_path, "field_path": "failure_modes"},
            )
        )
    if not isinstance(data.get("content_hash"), str):
        findings.append(
            ValidationFinding(
                severity="blocker",
                error_code="spec_schema_error",
                field_path="content_hash",
                message="content_hash MUST be a string (sha256 hex)",
                context={"spec_path": spec_path, "field_path": "content_hash"},
            )
        )
    return findings


def _validate_failure_modes(
    spec_path: str,
    data: Mapping[str, Any],
    known_failure_modes: frozenset[str],
) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    failure_modes = data.get("failure_modes")
    if not isinstance(failure_modes, list):
        return findings  # already raised by _validate_field_types
    for fm in failure_modes:
        if not isinstance(fm, str) or fm not in known_failure_modes:
            findings.append(
                ValidationFinding(
                    severity="blocker",
                    error_code="failure_taxonomy_error",
                    field_path=f"failure_modes[{fm!r}]",
                    message=(
                        f"unknown failure_mode {fm!r}; must be one of {sorted(known_failure_modes)}"
                    ),
                    context={
                        "spec_path": spec_path,
                        "field_path": "failure_modes",
                        "failure_mode": fm,
                        "known_failure_modes": sorted(known_failure_modes),
                    },
                )
            )
    return findings


def _validate_restricted_content(
    spec_path: str,
    data: Mapping[str, Any],
) -> list[ValidationFinding]:
    """Scan the spec for restricted-source markers (Section 10).

    Following the TASK-014 restricted.py pattern: only string *values*
    are scanned (keys are metadata and exempt). Standard-body tokens
    use word-boundary matching so legitimate references like
    ``source_kind="iso8601"`` do not flag. Values inside the
    RESTRICTED_MARKER_METADATA_FIELDS allowlist (e.g.,
    ``restricted_source_categories``) are exempt because they are the
    metadata-driven marker list itself (Section 10 final paragraph).
    """
    findings: list[ValidationFinding] = []
    for path, value in _extract_text_fields(data):
        # Skip the metadata-driven marker list itself.
        leaf_key = path.rsplit(".", 1)[-1] if "." in path else path
        leaf_key = leaf_key.split("[")[0]
        if leaf_key in RESTRICTED_MARKER_METADATA_FIELDS:
            continue

        # Section 15.1 — standards-body tokens (word-boundary match).
        for token in RESTRICTED_STANDARDS_BODY_TOKENS:
            if re.search(rf"\b{re.escape(token)}\b", value, flags=re.IGNORECASE):
                findings.append(
                    ValidationFinding(
                        severity="blocker",
                        error_code="restricted_content_violation",
                        field_path=path,
                        message=(
                            f"restricted standards-body token {token!r} "
                            f"found at {path!r} (Section 10)"
                        ),
                        context={
                            "spec_path": spec_path,
                            "violation_kind": "standard_body",
                            "offending_excerpt": value[:200],
                            "path": path,
                        },
                    )
                )
                return findings

        # Section 15.2 — vendor catalog body phrase.
        phrase = _scan_string_for_phrases(value, RESTRICTED_VENDOR_CATALOG_PHRASES)
        if phrase is not None:
            findings.append(
                ValidationFinding(
                    severity="blocker",
                    error_code="restricted_content_violation",
                    field_path=path,
                    message=(
                        f"vendor catalog body phrase {phrase!r} found at {path!r} (Section 10)"
                    ),
                    context={
                        "spec_path": spec_path,
                        "violation_kind": "vendor_catalog_body",
                        "offending_excerpt": value[:200],
                        "path": path,
                    },
                )
            )
            return findings

        # Section 15.3 — paid price list phrase.
        phrase = _scan_string_for_phrases(value, RESTRICTED_PAID_PRICE_LIST_PHRASES)
        if phrase is not None:
            findings.append(
                ValidationFinding(
                    severity="blocker",
                    error_code="restricted_content_violation",
                    field_path=path,
                    message=(f"paid price list phrase {phrase!r} found at {path!r} (Section 10)"),
                    context={
                        "spec_path": spec_path,
                        "violation_kind": "paid_price_list",
                        "offending_excerpt": value[:200],
                        "path": path,
                    },
                )
            )
            return findings

        # Section 15.4 — restricted property table phrase.
        phrase = _scan_string_for_phrases(value, RESTRICTED_PROPERTY_TABLE_PHRASES)
        if phrase is not None:
            findings.append(
                ValidationFinding(
                    severity="blocker",
                    error_code="restricted_content_violation",
                    field_path=path,
                    message=(
                        f"restricted property table phrase {phrase!r} "
                        f"found at {path!r} (Section 10)"
                    ),
                    context={
                        "spec_path": spec_path,
                        "violation_kind": "restricted_property_table",
                        "offending_excerpt": value[:200],
                        "path": path,
                    },
                )
            )
            return findings

        # Section 15.5 — scanned page / formula image pattern.
        pattern = _scan_string_for_patterns(value, RESTRICTED_SCANNED_PAGE_PATTERNS)
        if pattern is not None:
            violation_kind = "scanned_page" if "scan" in pattern.lower() else "formula_image"
            findings.append(
                ValidationFinding(
                    severity="blocker",
                    error_code="restricted_content_violation",
                    field_path=path,
                    message=(
                        f"scanned page / formula image pattern {pattern!r} "
                        f"found at {path!r} (Section 10)"
                    ),
                    context={
                        "spec_path": spec_path,
                        "violation_kind": violation_kind,
                        "offending_excerpt": value[:200],
                        "path": path,
                    },
                )
            )
            return findings

        # Section 15.6 — copied standard table phrase.
        phrase = _scan_string_for_phrases(value, RESTRICTED_COPIED_TABLE_PHRASES)
        if phrase is not None:
            findings.append(
                ValidationFinding(
                    severity="blocker",
                    error_code="restricted_content_violation",
                    field_path=path,
                    message=(
                        f"copied standard table phrase {phrase!r} found at {path!r} (Section 10)"
                    ),
                    context={
                        "spec_path": spec_path,
                        "violation_kind": "copied_standard_table",
                        "offending_excerpt": value[:200],
                        "path": path,
                    },
                )
            )
            return findings

    return findings


def _extract_text_fields(payload: Any, path: str = "") -> list[tuple[str, str]]:
    """Yield ``(path, string)`` for every string leaf in ``payload``.

    Section 10 — only string *values* are scanned (keys are metadata
    and exempt).
    """
    out: list[tuple[str, str]] = []
    if isinstance(payload, str):
        out.append((path, payload))
    elif isinstance(payload, Mapping):
        for key, value in payload.items():
            child = f"{path}.{key}" if path else str(key)
            out.extend(_extract_text_fields(value, child))
    elif isinstance(payload, list):
        for idx, item in enumerate(payload):
            child = f"{path}[{idx}]"
            out.extend(_extract_text_fields(item, child))
    return out


def _scan_string_for_phrases(value: str, phrases: Iterable[str]) -> str | None:
    lowered = value.lower()
    for phrase in phrases:
        if phrase.lower() in lowered:
            return phrase
    return None


def _scan_string_for_patterns(value: str, patterns: Iterable[str]) -> str | None:
    for pattern in patterns:
        if re.search(pattern, value, flags=re.IGNORECASE):
            return pattern
    return None


# ---------------------------------------------------------------------------
# Cross-spec checks (Section 11.1 item 5 / 11.2 item 10)
# ---------------------------------------------------------------------------


def _identifier_value(spec_path: str, data: Mapping[str, Any]) -> str | None:
    """Return the identifier value for ``spec_path`` or ``None``.

    Resolution order:

    1. Per-spec path lookup in :data:`SPEC_IDENTIFIER_FIELDS` (the
       canonical 4 paths).
    2. Inference from spec content: if the spec has a single one of
       the known identifier field names (``canonical_name``,
       ``gate_id``, ``release_channel``), use it.
    """
    field_name = SPEC_IDENTIFIER_FIELDS.get(spec_path, "")
    if field_name:
        value = data.get(field_name)
        if not isinstance(value, str) or not value.strip():
            return None
        return value
    # Fall back to inferring from spec content (used by tests with
    # synthetic spec paths).
    for candidate in ("canonical_name", "gate_id", "release_channel"):
        value = data.get(candidate)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _check_duplicate_identifiers(
    specs: Iterable[tuple[str, Mapping[str, Any]]],
) -> list[ValidationFinding]:
    """Section 11.1 item 5 + 11.2 item 10 — identifier uniqueness
    within and across specs.
    """
    findings: list[ValidationFinding] = []
    by_id: dict[str, list[str]] = {}
    for spec_path, data in specs:
        ident = _identifier_value(spec_path, data)
        if ident is None:
            continue
        by_id.setdefault(ident, []).append(spec_path)
    for ident, paths in by_id.items():
        if len(paths) > 1:
            for spec_path in paths[1:]:
                findings.append(
                    ValidationFinding(
                        severity="blocker",
                        error_code="spec_identifier_collision",
                        field_path=_identifier_field_for(spec_path),
                        message=(
                            f"identifier {ident!r} collides with {sorted(set(paths) - {spec_path})}"
                        ),
                        context={
                            "spec_path": spec_path,
                            "identifier": ident,
                            "collision_with": sorted(set(paths) - {spec_path})[0],
                        },
                    )
                )
    return findings


def _identifier_field_for(spec_path: str) -> str:
    field_name = SPEC_IDENTIFIER_FIELDS.get(spec_path, "")
    if field_name:
        return field_name
    # Fallback used by synthetic-paths in tests; the validator does not
    # need to inspect the spec to find the field — the path-driven
    # lookup is canonical.
    return "identifier"


# ---------------------------------------------------------------------------
# Top-level validation entry points
# ---------------------------------------------------------------------------


def _validate_deprecated_references(
    spec_path: str,
    spec_data: Mapping[str, Any],
    deprecated_identifiers: Mapping[str, str],
) -> list[ValidationFinding]:
    """Section 11.1.7 — a spec referencing a deprecated identifier
    surfaces a ``spec_deprecated_reference`` finding as a **warning**
    (not a blocker). This is the Section 7 contract:
    deprecated-reference is warning, not blocker.

    ``deprecated_identifiers`` maps the canonical identifier
    (e.g. ``ci-pipeline``) to its ``deprecated_at`` ISO-8601
    timestamp. The validator scans the spec's identifier field (per
    :data:`SPEC_IDENTIFIER_FIELDS`) and, when matched, emits a
    warning finding carrying ``identifier`` / ``deprecated_at`` in
    its context.
    """
    if not deprecated_identifiers:
        return []
    field_name = SPEC_IDENTIFIER_FIELDS.get(spec_path, "")
    if not field_name:
        return []
    identifier = spec_data.get(field_name)
    if not isinstance(identifier, str):
        return []
    deprecated_at = deprecated_identifiers.get(identifier)
    if deprecated_at is None:
        return []
    return [
        ValidationFinding(
            severity="warning",
            error_code="spec_deprecated_reference",
            field_path=field_name,
            message=(
                f"identifier {identifier!r} is deprecated "
                f"(deprecated_at={deprecated_at!r}); new workflows MUST NOT reference it"
            ),
            context={
                "spec_path": spec_path,
                "identifier": identifier,
                "deprecated_at": deprecated_at,
            },
        )
    ]


def _validate_frozen_contract_authority(
    spec_path: str,
    spec_data: Mapping[str, Any],
    established: frozenset[str],
) -> list[ValidationFinding]:
    """Section 11.2.8 — check ``release_gate.frozen_contract_references``
    against the set of established frozen contracts.

    Each reference that is NOT in ``established`` raises a BLOCKER
    ``governance_authority_error``. References that are valid governed
    frozen contracts (per :data:`GOVERNED_FROZEN_CONTRACTS`) but not
    yet established are surfaced as missing-authority blockers per
    Section 8.1 + Section 8.2.

    References that are NOT in :data:`GOVERNED_FROZEN_CONTRACTS` at all
    are out-of-scope for this helper (they would be a different error
    class — the spec author is using an unknown identifier).
    """
    from hexagent.governance.errors import GOVERNED_FROZEN_CONTRACTS

    findings: list[ValidationFinding] = []
    release_gate = spec_data.get("release_gate")
    if not isinstance(release_gate, Mapping):
        return findings
    references = release_gate.get("frozen_contract_references")
    if not isinstance(references, list):
        return findings
    for ref in references:
        if not isinstance(ref, str):
            continue
        if ref not in GOVERNED_FROZEN_CONTRACTS:
            # Out of scope: unknown identifier. Surface as a schema
            # blocker so the author knows.
            findings.append(
                ValidationFinding(
                    severity="blocker",
                    error_code="spec_schema_error",
                    field_path="release_gate.frozen_contract_references",
                    message=(
                        f"unknown frozen-contract reference {ref!r}; "
                        f"must be one of {sorted(GOVERNED_FROZEN_CONTRACTS)}"
                    ),
                    context={
                        "spec_path": spec_path,
                        "reference": ref,
                    },
                )
            )
            continue
        if ref not in established:
            findings.append(
                ValidationFinding(
                    severity="blocker",
                    error_code="governance_authority_error",
                    field_path="release_gate.frozen_contract_references",
                    message=(f"frozen contract {ref!r} is referenced but not yet established"),
                    context={
                        "spec_path": spec_path,
                        "missing_authority": ref,
                    },
                )
            )
    return findings


def validate_spec(
    spec_path: str,
    spec_data: Mapping[str, Any],
    *,
    known_failure_modes: frozenset[str] | None = None,
    established_frozen_contracts: frozenset[str] | None = None,
    deprecated_identifiers: Mapping[str, str] | None = None,
) -> ValidationReport:
    """Validate a single spec (Section 11.1).

    Returns a :class:`ValidationReport`. The report's ``blockers`` and
    ``warnings`` are disjoint (Section 7); see
    :meth:`ValidationReport.assert_disjoint`.

    ``established_frozen_contracts`` (Section 11.2.8) is the set of
    governed frozen-contract identifiers that are currently established
    on ``main``. ``None`` (the default) means ALL governed frozen
    contracts are established — matching the production state after
    TASK-015 first-slice merge. Tests that exercise the
    unestablished path pass an explicit ``frozenset(...)``.

    ``deprecated_identifiers`` (Section 11.1.7) maps an identifier to
    its ``deprecated_at`` ISO-8601 timestamp. ``None`` (the default)
    means no identifiers are deprecated — matching the production
    state where no spec has been moved to ``deprecated:``.
    """
    from hexagent.governance.errors import GOVERNED_FROZEN_CONTRACTS

    known = known_failure_modes if known_failure_modes is not None else FAILURE_TAXONOMY_MODES
    established = (
        established_frozen_contracts
        if established_frozen_contracts is not None
        else GOVERNED_FROZEN_CONTRACTS
    )
    deprecated = deprecated_identifiers if deprecated_identifiers is not None else {}

    blockers: list[ValidationFinding] = []
    warnings: list[ValidationFinding] = []

    # 1. Required fields per spec type.
    required = COMMON_REQUIRED_FIELDS + SPEC_REQUIRED_FIELDS.get(spec_path, ())
    for field_name in required:
        if field_name not in spec_data:
            blockers.append(
                ValidationFinding(
                    severity="blocker",
                    error_code="spec_schema_error",
                    field_path=field_name,
                    message=f"missing required field {field_name!r}",
                    context={"spec_path": spec_path, "field_path": field_name},
                )
            )

    # 2. Field type / format validation.
    blockers.extend(_validate_field_types(spec_path, spec_data))

    # 3. Failure-mode membership (Section 11.1 item 4).
    blockers.extend(_validate_failure_modes(spec_path, spec_data, known))

    # 4. Restricted-content scan (Section 10 / 11.2 item 9).
    blockers.extend(_validate_restricted_content(spec_path, spec_data))

    # 5. Content-hash correctness (Section 9.2 / 11.1 item 6).
    expected_hash = compute_content_hash(_spec_for_hash(spec_data))
    stored_hash = spec_data.get("content_hash")
    if isinstance(stored_hash, str) and stored_hash != expected_hash:
        blockers.append(
            ValidationFinding(
                severity="blocker",
                error_code="spec_schema_error",
                field_path="content_hash",
                message="content_hash does not match canonical sha256 of spec",
                context={
                    "spec_path": spec_path,
                    "field_path": "content_hash",
                    "expected_content_hash": expected_hash,
                },
            )
        )

    # 6. Frozen-contract authority (Section 11.2.8 / 8.2).
    blockers.extend(_validate_frozen_contract_authority(spec_path, spec_data, established))

    # 7. Deprecated-reference warning (Section 11.1.7 / Section 7).
    warnings.extend(_validate_deprecated_references(spec_path, spec_data, deprecated))

    report = ValidationReport(
        spec_path=spec_path,
        blockers=tuple(blockers),
        warnings=tuple(warnings),
    )
    report.assert_disjoint()
    return report


def _spec_for_hash(spec_data: Mapping[str, Any]) -> dict[str, Any]:
    """Compute the content_hash over the spec EXCLUDING the
    ``content_hash`` field itself (Section 9.2 — the hash is the
    identity of the spec at a given moment, computed over the rest of
    the canonical representation).
    """
    return {k: v for k, v in spec_data.items() if k != "content_hash"}


def validate_all_specs(
    specs: Mapping[str, Mapping[str, Any]],
    *,
    known_failure_modes: frozenset[str] | None = None,
) -> dict[str, ValidationReport]:
    """Validate all specs and add cross-spec identifier-collision
    findings (Section 11.1 item 5 / 11.2 item 10).

    Returns a mapping ``spec_path -> ValidationReport``. The cross-spec
    findings are appended to the relevant per-spec report.
    """
    known = known_failure_modes if known_failure_modes is not None else FAILURE_TAXONOMY_MODES

    reports: dict[str, ValidationReport] = {
        spec_path: validate_spec(spec_path, data, known_failure_modes=known)
        for spec_path, data in specs.items()
    }
    # Cross-spec identifier uniqueness.
    cross_findings = _check_duplicate_identifiers(specs.items())
    # Bucket cross-findings by spec_path.
    for finding in cross_findings:
        spec_path = finding.context.get("spec_path")
        if not isinstance(spec_path, str) or spec_path not in reports:
            continue
        existing = reports[spec_path]
        reports[spec_path] = ValidationReport(
            spec_path=existing.spec_path,
            blockers=existing.blockers + (finding,),
            warnings=existing.warnings,
        )
    for report in reports.values():
        report.assert_disjoint()
    return reports


# ---------------------------------------------------------------------------
# Convenience helper for now()
# ---------------------------------------------------------------------------


def utc_now_iso8601() -> str:
    """Return current UTC time as ISO-8601 with 'Z' suffix."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


__all__ = [
    "ALL_SPEC_PATHS",
    "COMMON_REQUIRED_FIELDS",
    "RESTRICTED_CONTENT_TOKENS",
    "SPEC_IDENTIFIER_FIELDS",
    "SPEC_PATH_CI_PIPELINE",
    "SPEC_PATH_FAILURE_TAXONOMY",
    "SPEC_PATH_RELEASE",
    "SPEC_PATH_SECURITY_GATE",
    "SPEC_REQUIRED_FIELDS",
    "SUPPORTED_SCHEMA_VERSIONS",
    "ValidationFinding",
    "ValidationReport",
    "canonicalize",
    "compute_content_hash",
    "load_spec",
    "utc_now_iso8601",
    "validate_all_specs",
    "validate_spec",
]
