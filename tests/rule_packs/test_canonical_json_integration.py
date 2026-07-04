"""Tests for the shared canonical JSON module + license boundary classifications.

These tests are co-located here because the license boundary module imports
the shared canonical_json module; we cover the integration as well.
"""

from __future__ import annotations

import pytest

from hexagent.rule_packs.errors import RulePackValidationError
from hexagent.rule_packs.license_boundary import (
    PROJECT_INTERNAL_AUTHORITY,
    PUBLIC_DOMAIN_TOKEN,
    classify_license_evidence,
)


@pytest.mark.parametrize(
    "value, expected_form",
    [
        (PROJECT_INTERNAL_AUTHORITY, "project_internal_authority"),
        (PUBLIC_DOMAIN_TOKEN, "public_domain"),
        ("Apache-2.0", "spdx"),
        ("CC-BY-4.0", "spdx"),
        ("GPL-3.0-or-later", "spdx"),
        ("permission-evidence://vendor/foo", "permission_evidence_pointer"),
    ],
)
def test_classify_license_evidence_accepts_controlled_forms(value: str, expected_form: str) -> None:
    assert classify_license_evidence(value).value == expected_form


@pytest.mark.parametrize("value", ["", None, "unknown-form"])  # type: ignore[arg-type]
def test_classify_license_evidence_rejects_invalid(value: object) -> None:
    with pytest.raises(RulePackValidationError):
        classify_license_evidence(value)  # type: ignore[arg-type]
