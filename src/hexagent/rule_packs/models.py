"""Frozen enums and structural constants for rule-pack validation.

These enums are derived directly from the TASK-012 frozen design contract
(docs/tasks/TASK-012-standards-rule-pack-license-boundary.md, review Head
28b6330f8c5221d75f101f6810157d81a428f446):

* Section 4 — seven source_class values (closed set).
* Section 7.2 — twelve identity fields and required / conditional flag.
* Section 7.2 / Section 14 — approval_status enum (frozen state machine).
* Section 6.2 — eight forbidden_content_marker values.
* Section 4.2 / Section 16.3a — vendor permission scope tokens.
"""

from __future__ import annotations

from enum import StrEnum


class SourceClass(StrEnum):
    """Closed set of rule source classes (Section 4)."""

    PUBLIC_DOMAIN = "PUBLIC_DOMAIN"
    OPEN_LICENSE = "OPEN_LICENSE"
    USER_PROVIDED_LICENSED_SUMMARY = "USER_PROVIDED_LICENSED_SUMMARY"
    INTERNAL_ENGINEERING_RULE = "INTERNAL_ENGINEERING_RULE"
    DERIVED_ENGINEERING_RULE = "DERIVED_ENGINEERING_RULE"
    REFERENCE_ONLY_RESTRICTED_STANDARD = "REFERENCE_ONLY_RESTRICTED_STANDARD"
    VENDOR_PERMISSIONED = "VENDOR_PERMISSIONED"


class ApprovalStatus(StrEnum):
    """Frozen approval state machine (Section 7.2 + Section 14).

    This enum MUST match Section 14 exactly. Any future extension is a
    design-contract revision.
    """

    DRAFT = "draft"
    NEEDS_SOURCE = "needs_source"
    NEEDS_LICENSE_EVIDENCE = "needs_license_evidence"
    NEEDS_NORMALIZATION = "needs_normalization"
    NEEDS_EXPECTED_OUTPUTS = "needs_expected_outputs"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class ForbiddenContentMarker(StrEnum):
    """Eight forbidden content markers (Section 6.2)."""

    STANDARD_FULL_TEXT = "standard_full_text"
    PAID_STANDARD_EXCERPT = "paid_standard_excerpt"
    COPIED_TABLE = "copied_table"
    SCANNED_PAGE = "scanned_page"
    FIGURE_REPRODUCTION = "figure_reproduction"
    FORMULA_IMAGE = "formula_image"
    VERBATIM_CLAUSE = "verbatim_clause"
    UNLICENSED_VENDOR_CATALOG = "unlicensed_vendor_catalog"


class LicenseEvidenceForm(StrEnum):
    """Allowed forms of license_evidence (Section 7.2).

    Three controlled forms plus the project-internal marker for rules that
    cite no external standard body.
    """

    SPDX = "spdx"
    PUBLIC_DOMAIN = "public_domain"
    PERMISSION_EVIDENCE_POINTER = "permission_evidence_pointer"
    PROJECT_INTERNAL_AUTHORITY = "project_internal_authority"


class VendorPermissionScope(StrEnum):
    """Vendor permission scope tokens (Section 4.2 / Section 16.3a)."""

    REPOSITORY_STORAGE = "repository_storage"
    REPOSITORY_REDISTRIBUTION = "repository_redistribution"
    USAGE_SCOPE = "usage_scope"
    PUBLIC_ARTIFACT_ALLOWED = "public_artifact_allowed"


# Source classes that MUST use ``project_internal_authority`` for
# license_evidence (Section 7.2 internal_authority rule + Section 4.2).
INTERNAL_AUTHORITY_SOURCES: frozenset[SourceClass] = frozenset(
    {SourceClass.INTERNAL_ENGINEERING_RULE, SourceClass.DERIVED_ENGINEERING_RULE}
)

# Source classes whose body MUST NOT be stored in the repository
# (Section 4.1 + Section 16).
METADATA_ONLY_SOURCES: frozenset[SourceClass] = frozenset(
    {SourceClass.REFERENCE_ONLY_RESTRICTED_STANDARD}
)

# Source classes whose body MUST NOT be redistributed
# (Section 16.3 — non-redistributable sources).
NON_REDISTRIBUTABLE_SOURCES: frozenset[SourceClass] = frozenset(
    {SourceClass.USER_PROVIDED_LICENSED_SUMMARY, SourceClass.REFERENCE_ONLY_RESTRICTED_STANDARD}
)

# VENDOR_PERMISSIONED rules MUST declare every permission_scope token that
# any operation (repository storage / redistribution / runtime loading /
# public artifact emission) will eventually require (Section 4.2 /
# Section 16.3a). The validator enforces this set on the rule-pack so
# operations cannot discover a missing scope at operation time.
VENDOR_PERMISSION_SCOPE_REQUIRED_TOKENS: frozenset[str] = frozenset(
    {
        VendorPermissionScope.REPOSITORY_STORAGE.value,
        VendorPermissionScope.REPOSITORY_REDISTRIBUTION.value,
        VendorPermissionScope.USAGE_SCOPE.value,
        VendorPermissionScope.PUBLIC_ARTIFACT_ALLOWED.value,
    }
)

# Top-level manifest fields per Section 7.1.
MANIFEST_REQUIRED_FIELDS: frozenset[str] = frozenset(
    {
        "rule_pack_id",
        "rule_pack_version",
        "rule_count",
        "rules",
        "target_jurisdiction",
        "target_standard_family",
        "creation_timestamp_utc",
        "review_id",
        "canonical_hash",
    }
)

# Rule artifact required fields (Section 7.2, schema-direct policy).
RULE_REQUIRED_FIELDS: frozenset[str] = frozenset(
    {
        "rule_id",
        "rule_version",
        "rule_title",
        "source_class",
        "jurisdiction",
        "standard_family",
        "bibliographic_reference",
        "license_evidence",
        "source_evidence",
        "rule_body",
        "forbidden_content_marker_check",
        "applicability_envelope",
        "uncertainty",
        "review_status",
        "approval_status",
        "canonical_hash",
        "provenance_edges",
    }
)

# Twelve identity fields (P1-3 Scheme A). These appear DIRECTLY on the rule
# artifact (not nested in source_evidence).
RULE_IDENTITY_DIRECT_FIELDS: frozenset[str] = frozenset(
    {
        "rule_id",
        "rule_version",
        "source_class",
        "jurisdiction",
        "standard_family",
        "bibliographic_reference",
        "license_evidence",
        "review_status",
        "approval_status",
        "canonical_hash",
        "provenance_edges",
        # Plus rule_pack_id (manifest-scoped) — surfaced via the manifest
        # and treated as part of the identity tuple.
        "rule_pack_id",
    }
)

# Conditional fields required by source_class (Section 7.2 + Section 8 + 9).
CONDITIONAL_RULE_FIELDS: dict[SourceClass, frozenset[str]] = {
    SourceClass.USER_PROVIDED_LICENSED_SUMMARY: frozenset({"human_entered_evidence"}),
    SourceClass.INTERNAL_ENGINEERING_RULE: frozenset({"human_entered_evidence"}),
    SourceClass.VENDOR_PERMISSIONED: frozenset({"human_entered_evidence"}),
    SourceClass.DERIVED_ENGINEERING_RULE: frozenset({"derived_rule_evidence"}),
}

# source_evidence required fields (Section 10).
SOURCE_EVIDENCE_REQUIRED_FIELDS: frozenset[str] = frozenset(
    {
        "source_class",
        "source_reference",
        "source_title_or_identifier",
        "source_locator_or_citation",
        "source_jurisdiction",
        "license_evidence",
    }
)

# Mirror fields where rule identity MUST be byte-equal to source_evidence
# (Section 7.2 direct-field policy). Section 10 requires these four fields
# on source_evidence, and the rule-level identity tuple (Section 7.2 +
# RULE_IDENTITY_DIRECT_FIELDS) carries the same four on the rule artifact
# itself. Mirror enforcement guarantees they agree.
SOURCE_EVIDENCE_MIRROR_FIELDS: dict[str, str] = {
    "source_class": "source_class",
    "license_evidence": "license_evidence",
    "jurisdiction": "source_jurisdiction",
    "bibliographic_reference": "source_reference",
}

# Standard family tokens (Section 7.2 standard_family column).
ALLOWED_STANDARD_FAMILIES: frozenset[str] = frozenset(
    {"ASME", "TEMA", "API", "ISO", "GB", "EN", "JIS", "DIN", "NFPA", "ASTM", "VENDOR", "INTERNAL"}
)

# Jurisdictions: ISO 3166-1 alpha-2 + INTL.
INTL_JURISDICTION = "INTL"
