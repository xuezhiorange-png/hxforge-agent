"""TASK-015 governance package.

Implements the TASK-015 frozen design contract
(docs/tasks/TASK-015-ci-security-and-release-automation.md,
Frozen Contract Authority SHA
``39135e269b014e9c9310ac403a60591393d46b2d``).

First slice (per preflight inventory recommended first slice):
* :mod:`hexagent.governance.errors` — 7 structured error classes
  (Section 8.1)
* :mod:`hexagent.governance.spec_validator` — deterministic YAML / JSON
  parse, schema validation, identifier uniqueness, restricted-content
  marker rejection (Section 9 / 11.1 / 11.2)

Public surface is intentionally narrow and storage-neutral (Section 5 +
Section 6). No public HTTP / RPC / API behavior is introduced.
"""

from __future__ import annotations

from hexagent.governance.errors import (
    FAILURE_TAXONOMY_MODES,
    GOVERNED_FROZEN_CONTRACTS,
    VALID_VIOLATION_KINDS,
    FailureTaxonomyError,
    GovernanceAuthorityError,
    RestrictedContentViolation,
    SpecDeprecatedReference,
    SpecForwardIncompatible,
    SpecIdentifierCollision,
    SpecSchemaError,
    Task015Error,
)
from hexagent.governance.spec_validator import (
    ALL_SPEC_PATHS,
    COMMON_REQUIRED_FIELDS,
    RESTRICTED_COPIED_TABLE_PHRASES,
    RESTRICTED_MARKER_METADATA_FIELDS,
    RESTRICTED_PAID_PRICE_LIST_PHRASES,
    RESTRICTED_PROPERTY_TABLE_PHRASES,
    RESTRICTED_SCANNED_PAGE_PATTERNS,
    RESTRICTED_STANDARDS_BODY_TOKENS,
    RESTRICTED_VENDOR_CATALOG_PHRASES,
    SPEC_IDENTIFIER_FIELDS,
    SPEC_PATH_CI_PIPELINE,
    SPEC_PATH_FAILURE_TAXONOMY,
    SPEC_PATH_RELEASE,
    SPEC_PATH_SECURITY_GATE,
    SPEC_REQUIRED_FIELDS,
    SUPPORTED_SCHEMA_VERSIONS,
    ValidationFinding,
    ValidationReport,
    canonicalize,
    compute_content_hash,
    load_spec,
    utc_now_iso8601,
    validate_all_specs,
    validate_spec,
)

__all__ = [
    # Errors (Section 8.1)
    "FAILURE_TAXONOMY_MODES",
    "GOVERNED_FROZEN_CONTRACTS",
    "VALID_VIOLATION_KINDS",
    "FailureTaxonomyError",
    "GovernanceAuthorityError",
    "RestrictedContentViolation",
    "SpecDeprecatedReference",
    "SpecForwardIncompatible",
    "SpecIdentifierCollision",
    "SpecSchemaError",
    "Task015Error",
    # Validator
    "ALL_SPEC_PATHS",
    "COMMON_REQUIRED_FIELDS",
    "RESTRICTED_COPIED_TABLE_PHRASES",
    "RESTRICTED_MARKER_METADATA_FIELDS",
    "RESTRICTED_PAID_PRICE_LIST_PHRASES",
    "RESTRICTED_PROPERTY_TABLE_PHRASES",
    "RESTRICTED_SCANNED_PAGE_PATTERNS",
    "RESTRICTED_STANDARDS_BODY_TOKENS",
    "RESTRICTED_VENDOR_CATALOG_PHRASES",
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
