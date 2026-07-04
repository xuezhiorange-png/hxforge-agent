"""License boundary enforcement for rule-pack artifacts.

Implements the TASK-012 frozen design contract, Section 4.1 (governance
matrix), Section 4.2 (CONDITIONAL condition clauses), Section 5 (license
boundary model), Section 6 (allowed vs forbidden content), and Section 16
(distribution boundary):

* The eight forbidden_content_marker values from Section 6.2 are hard
  rejects.
* ``license_evidence`` is REQUIRED for every rule (Section 7.2). Allowed
  forms: SPDX identifier, ``public_domain``, permission-evidence pointer,
  ``project_internal_authority``.
* INTERNAL_ENGINEERING_RULE and DERIVED_ENGINEERING_RULE MUST use
  ``project_internal_authority``.
* VENDOR_PERMISSIONED requires explicit permission scope tokens
  (``repository_storage``, ``repository_redistribution``, ``usage_scope``,
  ``public_artifact_allowed``) before storage / redistribution / runtime
  loading is permitted.
* REFERENCE_ONLY_RESTRICTED_STANDARD bodies MUST NEVER be stored.
* Body storage / redistribution decisions follow the Section 4.1 matrix
  with Section 4.2 CONDITIONAL condition clauses.
"""

from __future__ import annotations

from typing import Any

from hexagent.rule_packs.errors import RulePackValidationError
from hexagent.rule_packs.models import (
    INTERNAL_AUTHORITY_SOURCES,
    METADATA_ONLY_SOURCES,
    NON_REDISTRIBUTABLE_SOURCES,
    ForbiddenContentMarker,
    LicenseEvidenceForm,
    SourceClass,
    VendorPermissionScope,
)

# License evidence value tokens (Section 7.2 — four controlled forms).
PROJECT_INTERNAL_AUTHORITY = "project_internal_authority"
PUBLIC_DOMAIN_TOKEN = "public_domain"


# SPDX identifier short forms (Section 7.2). This is a non-exhaustive list
# of common SPDX short identifiers that the future CI may extend. We accept
# any token that is in this set OR that exactly matches an SPDX expression
# composed of these tokens (e.g. "Apache-2.0", "CC-BY-4.0", "GPL-3.0-or-later",
# "MIT", "MIT-0", "BSD-2-Clause", "LGPL-2.1-only", etc.).
_KNOWN_SPDX_TOKENS: frozenset[str] = frozenset(
    {
        # Permissive
        "MIT",
        "MIT-0",
        "Apache-2.0",
        "Apache-1.1",
        "BSD-2-Clause",
        "BSD-3-Clause",
        "ISC",
        "Unlicense",
        "CC0-1.0",
        "Zlib",
        "BSL-1.0",
        # Weak copyleft
        "LGPL-2.1-only",
        "LGPL-2.1-or-later",
        "LGPL-3.0-only",
        "LGPL-3.0-or-later",
        "MPL-2.0",
        "EPL-2.0",
        "CDDL-1.0",
        "CDDL-1.1",
        # Copyleft
        "GPL-2.0-only",
        "GPL-2.0-or-later",
        "GPL-3.0-only",
        "GPL-3.0-or-later",
        "AGPL-3.0-only",
        "AGPL-3.0-or-later",
        # Creative Commons (non-code)
        "CC-BY-4.0",
        "CC-BY-SA-4.0",
        "CC-BY-NC-4.0",
        "CC-BY-NC-SA-4.0",
        "CC-BY-3.0",
        "CC-BY-SA-3.0",
    }
)


def _is_spdx_identifier(value: str) -> bool:
    """Return True if value is a recognized SPDX short identifier.

    We accept tokens in the known SPDX set. The future CI may extend this
    list to cover the full SPDX license list. Tokens that look SPDX-like
    but are not in the known set are rejected as unknown.
    """
    if not isinstance(value, str) or not value:
        return False
    return value in _KNOWN_SPDX_TOKENS


def _is_permission_evidence_pointer(value: str) -> bool:
    """Return True if value looks like a permission-evidence artifact pointer.

    Section 7.2 license_evidence forms include "a permission-evidence pointer
    to a recorded artifact". We require a URI-like form so that arbitrary
    arbitrary tokens (e.g. "unknown-form") are rejected rather than silently
    accepted as permission pointers.
    """
    if not isinstance(value, str) or not value:
        return False
    if value in (PUBLIC_DOMAIN_TOKEN, PROJECT_INTERNAL_AUTHORITY):
        return False
    if _is_spdx_identifier(value):
        return False
    # Accept only URI-like forms: <scheme>://<token>
    return "://" in value


def classify_license_evidence(value: str) -> LicenseEvidenceForm:
    """Classify a license_evidence string against the four controlled forms.

    Raises ``RulePackValidationError`` if the value does not match any
    controlled form (Section 7.2 license_evidence REQUIRED for every rule).
    """
    if not isinstance(value, str) or not value:
        raise RulePackValidationError(
            "license_evidence must be a non-empty string",
            path="license_evidence",
        )
    if value == PROJECT_INTERNAL_AUTHORITY:
        return LicenseEvidenceForm.PROJECT_INTERNAL_AUTHORITY
    if value == PUBLIC_DOMAIN_TOKEN:
        return LicenseEvidenceForm.PUBLIC_DOMAIN
    if _is_spdx_identifier(value):
        return LicenseEvidenceForm.SPDX
    if _is_permission_evidence_pointer(value):
        return LicenseEvidenceForm.PERMISSION_EVIDENCE_POINTER
    raise RulePackValidationError(
        f"license_evidence={value!r} does not match any controlled form "
        "(SPDX identifier, 'public_domain', permission-evidence pointer, "
        "or 'project_internal_authority')",
        path="license_evidence",
    )


def enforce_license_evidence_required(rule: dict[str, Any]) -> LicenseEvidenceForm:
    """Enforce Section 7.2 license_evidence REQUIRED for every rule."""
    if "license_evidence" not in rule:
        raise RulePackValidationError(
            "license_evidence is REQUIRED for every rule (Section 7.2)",
            path="license_evidence",
        )
    return classify_license_evidence(rule["license_evidence"])


def _parse_source_class(rule: dict[str, Any]) -> SourceClass:
    """Parse ``rule["source_class"]`` and raise ``RulePackValidationError`` on failure."""
    value: Any = rule.get("source_class")
    if value is None or not isinstance(value, str):
        raise RulePackValidationError(
            "rule.source_class is required and must be a string",
            path="source_class",
        )
    try:
        return SourceClass(value)
    except ValueError as exc:
        raise RulePackValidationError(
            f"unknown source_class {value!r}",
            path="source_class",
        ) from exc


def enforce_internal_authority_for_internal_sources(rule: dict[str, Any]) -> None:
    """Enforce Section 7.2 internal_authority policy for INTERNAL / DERIVED."""
    source_class = _parse_source_class(rule)
    if (
        source_class in INTERNAL_AUTHORITY_SOURCES
        and rule.get("license_evidence") != PROJECT_INTERNAL_AUTHORITY
    ):
        raise RulePackValidationError(
            f"source_class={source_class.value} requires "
            f"license_evidence={PROJECT_INTERNAL_AUTHORITY!r} "
            "(Section 7.2 internal_authority rule)",
            path="license_evidence",
        )


def enforce_no_forbidden_marker(rule: dict[str, Any]) -> None:
    """Enforce Section 6.2 forbidden content marker rule.

    A rule whose body self-attests any forbidden marker via
    ``forbidden_content_marker_check`` is rejected.
    """
    check = rule.get("forbidden_content_marker_check")
    if check is None:
        # ``forbidden_content_marker_check`` is REQUIRED (Section 7.2).
        # Absence is reported elsewhere; here we only enforce the array
        # when present.
        return
    if not isinstance(check, list):
        raise RulePackValidationError(
            "forbidden_content_marker_check must be an array",
            path="forbidden_content_marker_check",
        )
    allowed = {m.value for m in ForbiddenContentMarker}
    for marker in check:
        if marker not in allowed:
            raise RulePackValidationError(
                f"forbidden_content_marker_check contains unknown marker "
                f"{marker!r}; allowed: {sorted(allowed)}",
                path="forbidden_content_marker_check",
            )
    # A non-empty array is a self-attestation that the body contains a
    # forbidden marker — reject.
    if check:
        raise RulePackValidationError(
            f"forbidden_content_marker_check must be empty; got {check!r} "
            "(Section 6.2 hard reject)",
            path="forbidden_content_marker_check",
        )


def enforce_vendor_permission_scope(
    rule: dict[str, Any],
    *,
    operation: str,
) -> None:
    """Enforce VENDOR_PERMISSIONED scope rules (Section 4.2 / Section 16.3a).

    ``operation`` is one of:

    * ``"repository_storage"`` — body may be stored if permission scope
      includes ``repository_storage``.
    * ``"repository_redistribution"`` — body may be redistributed if
      permission scope includes ``repository_redistribution``.
    * ``"runtime_rulepack"`` — runtime may load the body if permission
      evidence satisfies the local kernel's usage scope.
    * ``"public_artifact"`` — public artifact emission may include the
      body if permission scope includes ``public_artifact_allowed``.
    """
    if rule.get("source_class") != SourceClass.VENDOR_PERMISSIONED.value:
        return
    # The permission evidence MUST be recorded under human_entered_evidence.
    human = rule.get("human_entered_evidence") or {}
    permission = human.get("vendor_permission_evidence") or {}
    scope = permission.get("permission_scope")
    if not isinstance(scope, list):
        raise RulePackValidationError(
            "VENDOR_PERMISSIONED rule missing vendor_permission_evidence."
            "permission_scope list (Section 4.2)",
            path="human_entered_evidence.vendor_permission_evidence.permission_scope",
        )
    scope_set = set(scope)
    required_map = {
        "repository_storage": VendorPermissionScope.REPOSITORY_STORAGE.value,
        "repository_redistribution": VendorPermissionScope.REPOSITORY_REDISTRIBUTION.value,
        "runtime_rulepack": VendorPermissionScope.USAGE_SCOPE.value,
        "public_artifact": VendorPermissionScope.PUBLIC_ARTIFACT_ALLOWED.value,
    }
    if operation not in required_map:
        raise RulePackValidationError(
            f"unknown license_boundary operation {operation!r}",
            path="license_boundary",
        )
    required = required_map[operation]
    if required not in scope_set:
        raise RulePackValidationError(
            f"VENDOR_PERMISSIONED operation={operation!r} requires "
            f"permission_scope token {required!r}; got {sorted(scope_set)} "
            "(Section 4.2 / Section 16.3a)",
            path="human_entered_evidence.vendor_permission_evidence.permission_scope",
        )


def enforce_metadata_only(rule: dict[str, Any]) -> None:
    """Reject storage of a body for metadata-only source classes.

    Section 4.1: ``REFERENCE_ONLY_RESTRICTED_STANDARD`` body is metadata-only.
    Section 6.2 ``scanned_page`` / ``copied_table`` / ``verbatim_clause`` /
    ``paid_standard_excerpt`` all apply; the body MUST NOT contain any
    restricted content. We enforce the structural invariant: no rule_body
    field beyond bibliographic metadata.
    """
    source_class = _parse_source_class(rule)
    if source_class not in METADATA_ONLY_SOURCES:
        return
    # The body field MUST be absent OR must be a metadata object containing
    # only bibliographic keys. We accept either form but reject any
    # rule_body that looks like engineering content.
    body = rule.get("rule_body")
    if body is None:
        return
    if isinstance(body, dict):
        allowed_keys = {
            "bibliographic_metadata",
            "citation",
            "external_pointer",
            "section_locator",
        }
        bad = set(body.keys()) - allowed_keys
        if bad:
            raise RulePackValidationError(
                f"REFERENCE_ONLY_RESTRICTED_STANDARD rule_body may only "
                f"contain metadata keys {sorted(allowed_keys)}; got "
                f"{sorted(body.keys())} (Section 4.1 metadata-only)",
                path="rule_body",
            )
        return
    raise RulePackValidationError(
        "REFERENCE_ONLY_RESTRICTED_STANDARD rule_body must be absent or "
        "a metadata dict (Section 4.1 metadata-only)",
        path="rule_body",
    )


def enforce_non_redistribution(rule: dict[str, Any]) -> None:
    """Reject redistribution markers on non-redistributable sources.

    Section 16: USER_PROVIDED_LICENSED_SUMMARY and
    REFERENCE_ONLY_RESTRICTED_STANDARD bodies MUST NOT be exported.
    """
    source_class = _parse_source_class(rule)
    if source_class not in NON_REDISTRIBUTABLE_SOURCES:
        return
    # If a redistribution hint is present (e.g. rule_body contains a
    # marker like ``redistribute: true``), reject. We accept any
    # rule_body that does not carry a redistribution marker.
    body = rule.get("rule_body")
    if isinstance(body, dict) and body.get("redistribute") is True:
        raise RulePackValidationError(
            f"source_class={source_class.value} is non-redistributable "
            "(Section 16.3); rule_body.redistribute must not be true",
            path="rule_body",
        )


def enforce_full_license_boundary(rule: dict[str, Any]) -> None:
    """Run all license-boundary checks for a single rule.

    Used by the validator CLI. Each helper raises ``RulePackValidationError``
    with a precise ``path`` so JSON reports can pinpoint the failure.
    """
    enforce_license_evidence_required(rule)
    enforce_internal_authority_for_internal_sources(rule)
    enforce_no_forbidden_marker(rule)
    enforce_metadata_only(rule)
    enforce_non_redistribution(rule)
