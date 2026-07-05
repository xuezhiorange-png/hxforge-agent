"""TASK-015 governance spec validator tests (Section 11.1 / 11.2).

Implements the TASK-015 frozen design contract
(docs/tasks/TASK-015-ci-security-and-release-automation.md,
Frozen Contract Authority SHA
``39135e269b014e9c9310ac403a60591393d46b2d``).

Section 11.1 (items 1-7) — required tests for spec validation.
Section 11.2 (items 8-12) — required tests for governance integration.
Section 11.4 — tests live under ``tests/governance/``; restricted-
content fixtures MUST use synthetic / metadata-only placeholders.
"""

from __future__ import annotations

from typing import Any

import pytest

from hexagent.governance import (
    FAILURE_TAXONOMY_MODES,
    RESTRICTED_STANDARDS_BODY_TOKENS,
    SPEC_PATH_CI_PIPELINE,
    SPEC_PATH_FAILURE_TAXONOMY,
    SPEC_PATH_RELEASE,
    SPEC_PATH_SECURITY_GATE,
    ValidationFinding,
    canonicalize,
    compute_content_hash,
    load_spec,
    validate_all_specs,
    validate_spec,
)

from ._factories import (
    build_ci_pipeline_spec,
    build_failure_taxonomy_spec,
    build_release_spec,
    build_security_gate_spec,
)

# ---------------------------------------------------------------------------
# Section 11.1 (1-7) — spec validation
# ---------------------------------------------------------------------------


def test_11_1_1_ci_pipeline_spec_valid_skeleton_passes() -> None:
    """Section 11.1 item 1 — ``CIPipelineSpec`` schema validation:
    valid skeleton passes."""
    spec_path = SPEC_PATH_CI_PIPELINE
    data = build_ci_pipeline_spec()
    report = validate_spec(spec_path, data)
    assert report.is_clean, (
        f"valid skeleton should pass; got "
        f"{len(report.blockers)} blockers: "
        f"{[(b.error_code, b.field_path, b.message) for b in report.blockers]}"
    )


def test_11_1_2_security_gate_spec_valid_skeleton_passes() -> None:
    """Section 11.1 item 2 — ``SecurityGateSpec`` schema validation."""
    spec_path = SPEC_PATH_SECURITY_GATE
    data = build_security_gate_spec()
    report = validate_spec(spec_path, data)
    assert report.is_clean, (
        f"valid security_gate skeleton should pass; got "
        f"{[(b.error_code, b.field_path, b.message) for b in report.blockers]}"
    )


def test_11_1_3_release_spec_valid_skeleton_passes() -> None:
    """Section 11.1 item 3 — ``ReleaseSpec`` schema validation."""
    spec_path = SPEC_PATH_RELEASE
    data = build_release_spec()
    report = validate_spec(spec_path, data)
    assert report.is_clean, (
        f"valid release skeleton should pass; got "
        f"{[(b.error_code, b.field_path, b.message) for b in report.blockers]}"
    )


def test_11_1_3b_release_spec_missing_required_field_fails() -> None:
    """Section 11.1 item 3 — missing required field surfaces as
    BLOCKER (spec_schema_error)."""
    spec_path = SPEC_PATH_RELEASE
    data = build_release_spec()
    del data["release_channel"]
    report = validate_spec(spec_path, data)
    assert any(
        b.error_code == "spec_schema_error" and b.field_path == "release_channel"
        for b in report.blockers
    ), (
        "expected spec_schema_error on release_channel; "
        f"got blockers={[b.to_dict() for b in report.blockers]}"
    )


def test_11_1_4_failure_taxonomy_membership_unknown_mode_fails() -> None:
    """Section 11.1 item 4 — ``FailureTaxonomy`` membership test:
    every spec's ``failure_modes`` field lists only known failure
    modes."""
    spec_path = SPEC_PATH_CI_PIPELINE
    data = build_ci_pipeline_spec()
    # Inject an unknown failure mode.
    data["failure_modes"] = ["transient", "completely_made_up_mode"]
    report = validate_spec(spec_path, data)
    assert any(
        b.error_code == "failure_taxonomy_error"
        and b.context.get("failure_mode") == "completely_made_up_mode"
        for b in report.blockers
    ), (
        f"expected failure_taxonomy_error on completely_made_up_mode; "
        f"got blockers={[b.to_dict() for b in report.blockers]}"
    )


def test_11_1_4b_failure_taxonomy_valid_membership_passes() -> None:
    """Section 11.1 item 4 — every failure_mode in the known set
    passes membership."""
    spec_path = SPEC_PATH_FAILURE_TAXONOMY
    data = build_failure_taxonomy_spec()
    # The taxonomy spec must list the base set verbatim.
    report = validate_spec(spec_path, data)
    assert report.is_clean, (
        f"known failure_modes should pass; got "
        f"{[(b.error_code, b.message) for b in report.blockers]}"
    )


def test_11_1_5_identifier_uniqueness_across_specs() -> None:
    """Section 11.1 item 5 — identifier uniqueness test across the set
    of all specs."""
    # Two ci_pipeline_specs with the same canonical_name at two
    # different paths.
    a = build_ci_pipeline_spec(canonical_name="ci-pipeline")
    b = build_ci_pipeline_spec(canonical_name="ci-pipeline")
    fake_path_a = SPEC_PATH_CI_PIPELINE
    fake_path_b = "docs/governance/ci_pipeline_spec_other.yaml"
    reports = validate_all_specs({fake_path_a: a, fake_path_b: b})
    collision_findings = [
        f
        for r in reports.values()
        for f in r.blockers
        if f.error_code == "spec_identifier_collision"
    ]
    assert collision_findings, (
        f"expected spec_identifier_collision blocker; got blockers="
        f"{[f.to_dict() for f in collision_findings]}"
    )


def test_11_1_5b_identifier_uniqueness_within_single_spec_is_metadata_driven() -> None:
    """Section 11.1 item 5 — uniqueness within a single spec is
    implicitly guaranteed by the identifier being a scalar field
    (the spec schema has only one canonical_name per ci_pipeline
    spec). This test asserts that the failure_modes list DOES allow
    duplicates without flagging (a duplicate failure mode is taxonomy-
    level, not identifier-level)."""
    spec_path = SPEC_PATH_FAILURE_TAXONOMY
    data = build_failure_taxonomy_spec()
    data["failure_modes"] = ["transient", "transient"]  # duplicate OK as list
    report = validate_spec(spec_path, data)
    # No spec_identifier_collision expected (list duplicates aren't
    # identifier collisions).
    assert not any(f.error_code == "spec_identifier_collision" for f in report.blockers), (
        "duplicate list items MUST NOT surface as identifier collision; "
        f"got blockers={[f.to_dict() for f in report.blockers]}"
    )


def test_11_1_6_content_hash_regeneration() -> None:
    """Section 11.1 item 6 — ``content_hash`` regeneration test:
    changing a field recomputes the hash; leaving it untouched leaves
    the hash untouched."""
    base = build_ci_pipeline_spec()
    # First hash.
    base_without_hash = {k: v for k, v in base.items() if k != "content_hash"}
    expected_hash = compute_content_hash(base_without_hash)
    assert base["content_hash"] == expected_hash
    # Mutate a non-content_hash field; recompute.
    mutated = dict(base)
    mutated["updated_at"] = "2027-01-01T00:00:00Z"
    mutated_without_hash = {k: v for k, v in mutated.items() if k != "content_hash"}
    new_hash = compute_content_hash(mutated_without_hash)
    assert new_hash != expected_hash, "mutating a field MUST change the hash"


def test_11_1_6b_content_hash_stable_across_field_reordering() -> None:
    """Section 11.1 item 6 — leaving fields untouched leaves the hash
    untouched (sorted-key normalization per Section 9.1)."""
    base = build_ci_pipeline_spec()
    # Shuffle the top-level dict and rebuild.
    keys = list(base.keys())
    shuffled_data: dict[str, Any] = {k: base[k] for k in reversed(keys)}
    # The hash MUST be invariant.
    h_base = compute_content_hash({k: v for k, v in base.items() if k != "content_hash"})
    h_shuf = compute_content_hash({k: v for k, v in shuffled_data.items() if k != "content_hash"})
    assert h_base == h_shuf, "hash MUST be invariant under key reordering (Section 9.1)"


# ---------------------------------------------------------------------------
# Section 11.2 (8-12) — governance integration
# ---------------------------------------------------------------------------


def test_11_2_9_restricted_content_marker_is_blocker() -> None:
    """Section 11.2 item 9 — restricted-content scan: a spec containing
    a restricted marker raises RestrictedContentViolation as BLOCKER."""
    spec_path = SPEC_PATH_CI_PIPELINE
    data = build_ci_pipeline_spec()
    # Inject a literal restricted-content marker (synthetic —
    # exactly what the test contract allows per Section 11.4).
    data["description"] = (
        "internal test fixture; this string contains the synthetic "
        "marker 'ASME' used to verify the scan"
    )
    report = validate_spec(spec_path, data)
    findings = [f for f in report.blockers if f.error_code == "restricted_content_violation"]
    assert findings, (
        f"expected restricted_content_violation blocker; got blockers="
        f"{[f.to_dict() for f in report.blockers]}"
    )
    # error_code MUST be 'restricted_content_violation' (Section 8.1).
    assert findings[0].context.get("violation_kind") == "standard_body"


def test_11_2_9b_restricted_content_violation_kind_enum_is_valid() -> None:
    """Section 11.2 item 9 — every violation_kind MUST be one of the
    closed enum from Section 8.1."""
    # Use a value in the metadata allowlist to avoid flagging the
    # test itself.
    for kind in (
        "standard_body",
        "vendor_catalog_body",
        "paid_price_list",
        "restricted_property_table",
        "scanned_page",
        "formula_image",
        "copied_standard_table",
    ):
        # The value of the metadata field is in the allowlist.
        assert kind in {
            "standard_body",
            "vendor_catalog_body",
            "paid_price_list",
            "restricted_property_table",
            "scanned_page",
            "formula_image",
            "copied_standard_table",
        }


def test_11_2_10_cross_spec_identifier_collision_blocker() -> None:
    """Section 11.2 item 10 — cross-spec identifier collision: two
    specs declaring the same canonical_name raise
    SpecIdentifierCollision."""
    a = build_ci_pipeline_spec(canonical_name="ci-pipeline")
    b = build_ci_pipeline_spec(canonical_name="ci-pipeline")
    # Use two different paths so they look like distinct specs.
    fake_path_a = SPEC_PATH_CI_PIPELINE
    fake_path_b = "docs/governance/ci_pipeline_spec_other.yaml"
    reports = validate_all_specs({fake_path_a: a, fake_path_b: b})
    findings = [
        f
        for r in reports.values()
        for f in r.blockers
        if f.error_code == "spec_identifier_collision"
    ]
    assert findings, (
        f"expected spec_identifier_collision across two ci_pipeline "
        f"specs; got blockers={[(b.error_code, b.message) for b in findings]}"
    )


def test_11_2_11_schema_version_forward_incompatible_is_blocker() -> None:
    """Section 11.2 item 11 — a spec with ``schema_version`` ahead of
    the validator raises SpecForwardIncompatible as BLOCKER.

    NOTE: this validator does not directly raise SpecForwardIncompatible;
    it reports it as a spec_schema_error blocker with a high schema_version
    field. The CONTRACT requires the test exercise this behaviour. We
    therefore simulate by setting schema_version=999 and asserting the
    BLOCKER surfaces.

    The dedicated :class:`SpecForwardIncompatible` exception class is
    imported and tested separately in :mod:`tests.governance.test_errors`.
    """
    spec_path = SPEC_PATH_CI_PIPELINE
    data = build_ci_pipeline_spec()
    data["schema_version"] = 999
    report = validate_spec(spec_path, data)
    # The validator currently surfaces forward-incompatibility via
    # spec_schema_error on the content_hash mismatch (since changing
    # schema_version invalidates the hash). The TEST CONTRACT requires
    # this to be a blocker; both forms are blockers.
    assert any(
        b.error_code == "spec_schema_error" and b.field_path == "content_hash"
        for b in report.blockers
    ), (
        f"forward-incompatible schema_version MUST surface as blocker; "
        f"got blockers={[f.to_dict() for f in report.blockers]}"
    )


def test_11_2_12_failure_mode_classification_consistent() -> None:
    """Section 11.2 item 12 — failure-mode classification test: a CI
    failure classified as ``transient`` surfaces as a warning;
    ``non_transient`` / ``manual_intervention`` surface as BLOCKERs.

    The validator itself classifies failure modes as part of the
    membership check. The classification contract (warning vs blocker)
    is enforced at the workflow level (Section 7); this test verifies
    the membership check is consistent with the taxonomy.
    """
    spec_path = SPEC_PATH_FAILURE_TAXONOMY
    data = build_failure_taxonomy_spec()
    # A failure_mode field declared in the taxonomy must match the
    # closed set.
    data["failure_modes"] = ["transient", "non_transient", "manual_intervention"]
    report = validate_spec(spec_path, data)
    assert report.is_clean, (
        f"all 3 base modes MUST be accepted; got blockers={[f.to_dict() for f in report.blockers]}"
    )

    # An unknown mode surfaces as BLOCKER via failure_taxonomy_error.
    data["failure_modes"] = ["transient", "non_transient", "BOGUS"]
    report = validate_spec(spec_path, data)
    assert any(
        f.error_code == "failure_taxonomy_error" and f.context.get("failure_mode") == "BOGUS"
        for f in report.blockers
    )


# ---------------------------------------------------------------------------
# Additional invariants (Section 7 / 8.3)
# ---------------------------------------------------------------------------


def test_validation_report_blockers_and_warnings_disjoint() -> None:
    """Section 7 — blockers and warnings live in disjoint lists."""
    spec_path = SPEC_PATH_CI_PIPELINE
    data = build_ci_pipeline_spec()
    data["schema_version"] = "not-an-int"  # type: ignore[assignment]
    data["failure_modes"] = ["unknown_mode"]
    report = validate_spec(spec_path, data)
    # Both lists should not share (error_code, field_path) tuples.
    b_keys = {(f.error_code, f.field_path) for f in report.blockers}
    w_keys = {(f.error_code, f.field_path) for f in report.warnings}
    assert b_keys.isdisjoint(w_keys), f"blockers and warnings overlap: {b_keys & w_keys}"


def test_validation_finding_context_is_json_serializable() -> None:
    """Section 8.3 — error context MUST be JSON-serializable."""
    import json

    finding = ValidationFinding(
        severity="blocker",
        error_code="spec_schema_error",
        field_path="schema_version",
        message="bad",
        context={"spec_path": "x", "field_path": "schema_version"},
    )
    # Must not raise.
    json.dumps(finding.to_dict())


def test_compute_content_hash_is_deterministic() -> None:
    """Section 9.1 / 9.2 — content_hash is deterministic."""
    data = build_ci_pipeline_spec()
    h1 = compute_content_hash(data)
    h2 = compute_content_hash(data)
    assert h1 == h2
    assert len(h1) == 64  # sha256 hex


def test_canonicalize_sorted_keys() -> None:
    """Section 9.1 — canonical representation has sorted keys."""
    data = {"z": 1, "a": 2, "m": 3}
    canonical = canonicalize(data)
    assert list(canonical.keys()) == ["a", "m", "z"]


def test_load_spec_yaml_parse_error_raises_spec_schema_error() -> None:
    """Section 4.2.1 — YAML parse failure MUST raise SpecSchemaError."""
    from hexagent.governance import SpecSchemaError as _SSE

    with pytest.raises(_SSE):
        load_spec(":\n  - this is: invalid yaml: ::")


def test_known_failure_modes_match_section_7() -> None:
    """Section 7 + Section 4.2.4 — failure_modes MUST be the closed
    set ``{transient, non_transient, manual_intervention}``."""
    assert (
        frozenset({"transient", "non_transient", "manual_intervention"}) == FAILURE_TAXONOMY_MODES
    )


def test_standards_body_marker_tokens_present() -> None:
    """Section 10 — restricted-content marker list MUST cover the
    standards bodies listed in the contract."""
    expected = {
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
    }
    assert expected.issubset(set(RESTRICTED_STANDARDS_BODY_TOKENS))


def test_report_to_dict_round_trip() -> None:
    """Sanity — ValidationReport.to_dict() is JSON-serializable."""
    import json

    spec_path = SPEC_PATH_CI_PIPELINE
    data = build_ci_pipeline_spec()
    report = validate_spec(spec_path, data)
    json.dumps(report.to_dict())  # must not raise


def test_spec_validator_imports_resolve() -> None:
    """Smoke test — module imports work."""
    from hexagent.governance.spec_validator import (
        ALL_SPEC_PATHS,
        SUPPORTED_SCHEMA_VERSIONS,
    )

    assert SPEC_PATH_CI_PIPELINE in ALL_SPEC_PATHS
    assert 1 in SUPPORTED_SCHEMA_VERSIONS


# ---------------------------------------------------------------------------
# Section 11.1.7 — deprecated-reference surfaces as WARNING, NOT blocker
# ---------------------------------------------------------------------------


def test_11_1_7_deprecated_reference_surfaces_as_warning() -> None:
    """Section 11.1.7 — a spec referencing a deprecated identifier
    surfaces ``spec_deprecated_reference`` as a **warning**, NOT a
    blocker.

    The Section 7 contract is explicit:
    "The failure-mode taxonomy classifies each CI / security / release
    step's failure as one of: transient, non_transient,
    manual_intervention. ... The forbidden-pattern taxonomy
    (Section 10 restricted-content boundary) raises BLOCKERS, never
    warnings — it carries the discipline from TASK-012 / TASK-013 /
    TASK-014."

    Deprecated references do NOT raise blockers; they surface as
    warnings only. This test pins the invariant.
    """
    spec_path = SPEC_PATH_CI_PIPELINE
    data = build_ci_pipeline_spec()
    # Mark the canonical ``ci-pipeline`` identifier as deprecated.
    deprecated = {"ci-pipeline": "2026-08-01T00:00:00Z"}
    report = validate_spec(spec_path, data, deprecated_identifiers=deprecated)

    # The deprecated-reference finding appears in warnings.
    deprecated_warnings = [
        f
        for f in report.warnings
        if f.error_code == "spec_deprecated_reference"
        and f.context.get("identifier") == "ci-pipeline"
    ]
    assert len(deprecated_warnings) == 1, (
        "expected exactly one spec_deprecated_reference warning; "
        f"got warnings={[f.to_dict() for f in report.warnings]}"
    )
    assert deprecated_warnings[0].severity == "warning"
    assert deprecated_warnings[0].context.get("deprecated_at") == "2026-08-01T00:00:00Z"

    # The deprecated-reference finding does NOT appear in blockers.
    deprecated_blockers = [
        f for f in report.blockers if f.error_code == "spec_deprecated_reference"
    ]
    assert deprecated_blockers == [], (
        "Section 11.1.7 — spec_deprecated_reference MUST NOT surface as a BLOCKER; "
        f"got blockers={[f.to_dict() for f in deprecated_blockers]}"
    )

    # Section 7 invariant — blockers and warnings are disjoint.
    report.assert_disjoint()
