"""TASK-015 governance error model tests.

Implements the TASK-015 frozen design contract
(docs/tasks/TASK-015-ci-security-and-release-automation.md,
Frozen Contract Authority SHA
``39135e269b014e9c9310ac403a60591393d46b2d``).

Section 8.1 — 7 structured error classes with machine-readable
context.
Section 8.2 — disambiguation rule (GovernanceAuthorityError vs
SpecIdentifierCollision).
"""

from __future__ import annotations

import json

import pytest

from hexagent.governance import (
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

# ---------------------------------------------------------------------------
# Section 8.1 — error classes exist and carry error_code + structured context
# ---------------------------------------------------------------------------


def test_spec_schema_error_has_error_code_and_context() -> None:
    err = SpecSchemaError(
        "bad schema",
        spec_path="docs/governance/ci_pipeline_spec.yaml",
        field_path="schema_version",
        reason="not_int",
        schema_version=1,
    )
    assert err.error_code == "spec_schema_error"
    assert err.spec_path == "docs/governance/ci_pipeline_spec.yaml"
    assert err.context["field_path"] == "schema_version"
    assert err.context["reason"] == "not_int"
    assert err.context["schema_version"] == 1


def test_spec_identifier_collision_has_error_code_and_context() -> None:
    err = SpecIdentifierCollision(
        "collision",
        spec_path="docs/governance/a.yaml",
        identifier="ci-pipeline",
        collision_with="docs/governance/b.yaml",
    )
    assert err.error_code == "spec_identifier_collision"
    assert err.identifier == "ci-pipeline"
    assert err.collision_with == "docs/governance/b.yaml"


def test_spec_deprecated_reference_has_error_code_and_context() -> None:
    err = SpecDeprecatedReference(
        "deprecated",
        spec_path="docs/governance/a.yaml",
        identifier="old-name",
        deprecated_at="2026-01-01T00:00:00Z",
    )
    assert err.error_code == "spec_deprecated_reference"
    assert err.deprecated_at == "2026-01-01T00:00:00Z"


def test_spec_forward_incompatible_has_error_code_and_context() -> None:
    err = SpecForwardIncompatible(
        "forward-incompatible",
        spec_path="docs/governance/a.yaml",
        schema_version=2,
        expected_schema_version=1,
    )
    assert err.error_code == "spec_forward_incompatible"
    assert err.schema_version == 2
    assert err.expected_schema_version == 1


def test_failure_taxonomy_error_has_error_code_and_context() -> None:
    err = FailureTaxonomyError(
        "unknown mode",
        spec_path="docs/governance/a.yaml",
        failure_mode="unknown_mode",
        known_failure_modes=FAILURE_TAXONOMY_MODES,
    )
    assert err.error_code == "failure_taxonomy_error"
    assert err.failure_mode == "unknown_mode"
    assert set(err.context["known_failure_modes"]) == set(FAILURE_TAXONOMY_MODES)


def test_restricted_content_violation_has_error_code_and_context() -> None:
    err = RestrictedContentViolation(
        "vendor catalog body",
        spec_path="docs/governance/a.yaml",
        violation_kind="vendor_catalog_body",
        offending_excerpt="snippet",
        path="description",
    )
    assert err.error_code == "restricted_content_violation"
    assert err.violation_kind == "vendor_catalog_body"


def test_restricted_content_violation_rejects_invalid_kind() -> None:
    """Section 8.1 — violation_kind MUST be one of VALID_VIOLATION_KINDS."""
    with pytest.raises(ValueError):
        RestrictedContentViolation(
            "bad kind",
            spec_path="docs/governance/a.yaml",
            violation_kind="not_a_real_kind",
        )


def test_governance_authority_error_has_error_code_and_context() -> None:
    err = GovernanceAuthorityError(
        "missing authority",
        spec_path="docs/governance/a.yaml",
        missing_authority="task_011_frozen_contract",
        reference="task-011",
    )
    assert err.error_code == "governance_authority_error"
    assert err.missing_authority == "task_011_frozen_contract"


def test_governance_authority_error_rejects_invalid_kind() -> None:
    with pytest.raises(ValueError):
        GovernanceAuthorityError(
            "bad",
            spec_path="docs/governance/a.yaml",
            missing_authority="not_a_real_authority",
        )


def test_task015_error_is_common_base() -> None:
    """Section 8.1 — common base :class:`Task015Error`."""
    err = SpecSchemaError(
        "x",
        spec_path="docs/governance/a.yaml",
        field_path="schema_version",
        reason="x",
    )
    assert isinstance(err, Task015Error)


def test_all_errors_are_json_serializable() -> None:
    """Section 8.3 — error context MUST be JSON-serializable."""
    instances = [
        SpecSchemaError(
            "bad",
            spec_path="a.yaml",
            field_path="schema_version",
            reason="not_int",
        ),
        SpecIdentifierCollision(
            "collision",
            spec_path=None,
            identifier="x",
            collision_with="y.yaml",
        ),
        SpecDeprecatedReference(
            "deprecated",
            spec_path="a.yaml",
            identifier="x",
            deprecated_at="2026-01-01T00:00:00Z",
        ),
        SpecForwardIncompatible(
            "fwd",
            spec_path="a.yaml",
            schema_version=2,
            expected_schema_version=1,
        ),
        FailureTaxonomyError(
            "bad",
            spec_path="a.yaml",
            failure_mode="x",
            known_failure_modes=FAILURE_TAXONOMY_MODES,
        ),
        RestrictedContentViolation(
            "bad",
            spec_path="a.yaml",
            violation_kind="vendor_catalog_body",
        ),
        GovernanceAuthorityError(
            "bad",
            spec_path="a.yaml",
            missing_authority="task_011_frozen_contract",
        ),
    ]
    for err in instances:
        # to_dict() and full JSON round-trip MUST work.
        d = err.to_dict()
        json.dumps(d)
        # spec_path key MUST exist (Section 8.3 contract).
        assert "spec_path" in d
        assert "context" in d


# ---------------------------------------------------------------------------
# Section 8.2 — disambiguation rule
# ---------------------------------------------------------------------------


def test_governance_authority_error_and_spec_identifier_collision_are_distinct() -> None:
    """Section 8.2 — GovernanceAuthorityError is NOT
    SpecIdentifierCollision and vice versa."""
    auth_err = GovernanceAuthorityError(
        "x",
        spec_path="docs/governance/a.yaml",
        missing_authority="task_011_frozen_contract",
    )
    coll_err = SpecIdentifierCollision(
        "x",
        spec_path="docs/governance/a.yaml",
        identifier="ci-pipeline",
        collision_with="docs/governance/b.yaml",
    )
    assert type(auth_err) is not type(coll_err)
    assert auth_err.error_code != coll_err.error_code
    assert not isinstance(auth_err, SpecIdentifierCollision)
    assert not isinstance(coll_err, GovernanceAuthorityError)


def test_governed_frozen_contracts_enum_is_closed() -> None:
    """Section 8.1 — GovernanceAuthorityError.missing_authority is a
    closed enum of 6 values."""
    expected = frozenset(
        {
            "task_011_frozen_contract",
            "task_012_frozen_contract",
            "task_013_frozen_contract",
            "task_014_frozen_contract",
            "task_015_frozen_contract",
            "task_015a_frozen_contract",
        }
    )
    assert expected == GOVERNED_FROZEN_CONTRACTS


def test_valid_violation_kinds_enum_is_closed() -> None:
    """Section 8.1 — RestrictedContentViolation.violation_kind is a
    closed enum of 7 values per Section 10."""
    expected = frozenset(
        {
            "standard_body",
            "vendor_catalog_body",
            "paid_price_list",
            "restricted_property_table",
            "scanned_page",
            "formula_image",
            "copied_standard_table",
        }
    )
    assert expected == VALID_VIOLATION_KINDS


def test_restricted_content_violation_error_code_is_stable() -> None:
    """Section 8.1 — ``restricted_content_violation`` MUST be the
    error_code in ALL cases. CI MUST NOT downgrade to a warning."""
    err = RestrictedContentViolation(
        "x",
        spec_path="a.yaml",
        violation_kind="standard_body",
    )
    assert err.error_code == "restricted_content_violation"


def test_all_error_codes_are_distinct() -> None:
    """Section 8.1 — each error class MUST have a distinct error_code."""
    classes = [
        SpecSchemaError("x", spec_path="a", field_path="f", reason="r"),
        SpecIdentifierCollision("x", spec_path=None, identifier="i", collision_with="j"),
        SpecDeprecatedReference("x", spec_path="a", identifier="i"),
        SpecForwardIncompatible("x", spec_path="a", schema_version=2, expected_schema_version=1),
        FailureTaxonomyError(
            "x", spec_path="a", failure_mode="f", known_failure_modes=FAILURE_TAXONOMY_MODES
        ),
        RestrictedContentViolation("x", spec_path="a", violation_kind="standard_body"),
        GovernanceAuthorityError("x", spec_path="a", missing_authority="task_011_frozen_contract"),
    ]
    codes = [c.error_code for c in classes]
    assert len(set(codes)) == len(codes), f"duplicate error_codes: {codes}"
