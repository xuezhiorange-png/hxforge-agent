"""Validation result + approval-gate tests for TASK-013 material / cost
records (Sections 13 / 15)."""

from __future__ import annotations

import pytest

from hexagent.canonical_json import canonical_sha256
from hexagent.material_costs.models import ApprovalState, CostCategory, SourceClass
from hexagent.material_costs.validation import (
    ValidationResult,
    validate_cost_record,
    validate_material_record,
)

from ._factories import base_cost_record, base_material_record


def test_blockers_and_warnings_are_separate_collections() -> None:
    record = base_material_record()
    record["quality_flags"] = ["assumed_value"]
    record["record_hash"] = canonical_sha256(
        {k: v for k, v in record.items() if k != "record_hash"}
    )
    result = validate_material_record(record)
    # assumed_value in quality_flags → warning (Section 15).
    assert any(w.kind == "warning" for w in result.warnings)
    assert all(b.kind == "blocker" for b in result.blockers)


def test_warning_is_not_downgradable_to_blocker_or_vice_versa() -> None:
    """The blocker / warning collections MUST remain disjoint per
    Section 15."""
    record = base_material_record()
    record["provenance_edges"] = []  # structural blocker (Section 8)
    record["quality_flags"] = ["assumed_value"]  # warning (Section 15)
    record["record_hash"] = canonical_sha256(
        {k: v for k, v in record.items() if k != "record_hash"}
    )
    result = validate_material_record(record)
    assert any("provenance_edges" in b.message for b in result.blockers)
    assert any(w.path == "material_record.quality_flags" for w in result.warnings)
    # Disjoint check
    blocker_paths = {b.path for b in result.blockers}
    warning_paths = {w.path for w in result.warnings}
    assert blocker_paths.isdisjoint(warning_paths)


def test_material_approval_gate_unknown_state_is_blocker() -> None:
    record = base_material_record()
    record["approval_state"] = "approved-with-asterisks"
    record["record_hash"] = canonical_sha256(
        {k: v for k, v in record.items() if k != "record_hash"}
    )
    result = validate_material_record(record)
    assert not result.ok
    assert any("approval_state" in b.message for b in result.blockers)


def test_material_under_review_requires_provenance_edges() -> None:
    record = base_material_record()
    record["approval_state"] = ApprovalState.UNDER_REVIEW.value
    record["provenance_edges"] = []
    record["record_hash"] = canonical_sha256(
        {k: v for k, v in record.items() if k != "record_hash"}
    )
    result = validate_material_record(record)
    assert not result.ok
    assert any("provenance_edges" in b.message for b in result.blockers)


def test_human_entered_evidence_required_for_user_source_class() -> None:
    record = base_material_record()
    record["source_class"] = SourceClass.USER_PROVIDED_PROJECT_DATA.value
    record["human_entered_evidence"] = {}  # empty
    record["record_hash"] = canonical_sha256(
        {k: v for k, v in record.items() if k != "record_hash"}
    )
    result = validate_material_record(record)
    assert not result.ok
    assert any(
        b.path.endswith("human_entered_evidence") and "required" in b.message
        for b in result.blockers
    )


def test_cost_category_escalation_index_requires_public_index() -> None:
    record = base_cost_record()
    record["cost_category"] = CostCategory.COST_ESCALATION_INDEX.value
    record["cost_basis"] = "internal_assumption"  # must be public_index
    record["record_hash"] = canonical_sha256(
        {k: v for k, v in record.items() if k != "record_hash"}
    )
    result = validate_cost_record(record)
    assert not result.ok
    assert any("public_index" in b.message for b in result.blockers)


def test_cost_category_price_index_requires_public_index() -> None:
    record = base_cost_record()
    record["cost_category"] = CostCategory.PRICE_INDEX.value
    record["cost_basis"] = "vendor_quote"
    record["record_hash"] = canonical_sha256(
        {k: v for k, v in record.items() if k != "record_hash"}
    )
    result = validate_cost_record(record)
    assert not result.ok


def test_public_index_basis_blocker_for_non_escalation_category() -> None:
    record = base_cost_record()
    record["cost_category"] = CostCategory.MATERIAL_UNIT_PRICE.value
    record["cost_basis"] = "public_index"
    record["record_hash"] = canonical_sha256(
        {k: v for k, v in record.items() if k != "record_hash"}
    )
    result = validate_cost_record(record)
    assert not result.ok
    assert any("public_index" in b.message and "reserved" in b.message for b in result.blockers)


def test_validation_result_ok_when_blockers_empty() -> None:
    record = base_material_record()
    record["record_hash"] = canonical_sha256(
        {k: v for k, v in record.items() if k != "record_hash"}
    )
    result = validate_material_record(record)
    assert result.ok


def test_validation_result_ok_with_warnings_present() -> None:
    record = base_material_record()
    record["quality_flags"] = ["assumed_value"]  # warning only
    record["record_hash"] = canonical_sha256(
        {k: v for k, v in record.items() if k != "record_hash"}
    )
    result = validate_material_record(record)
    assert result.ok  # warnings do not flip ok
    assert any(w.kind == "warning" for w in result.warnings)


def test_blockers_from_license_boundary_are_structured() -> None:
    record = base_material_record()
    record["source_class"] = SourceClass.RESTRICTED_REFERENCE_METADATA_ONLY.value
    record["property_values"] = [
        {
            "property_name": "yield_strength",
            "value_si": "250",
            "unit_si": "MPa",
            "source_pointer": "internal://restricted/asme-yields",
            "quality_flags": ["assumed_value"],
        }
    ]
    record["record_hash"] = canonical_sha256(
        {k: v for k, v in record.items() if k != "record_hash"}
    )
    result = validate_material_record(record)
    assert not result.ok
    # All blockers have kind="blocker" and a path attribute.
    for b in result.blockers:
        assert b.kind == "blocker"
        assert b.path
        assert b.message


def test_validate_with_non_dict_raises() -> None:
    from hexagent.material_costs.errors import MaterialCostValidationError

    with pytest.raises(MaterialCostValidationError):
        validate_material_record("not a dict")


def test_validation_result_to_dict_shape() -> None:
    record = base_material_record()
    record["record_hash"] = canonical_sha256(
        {k: v for k, v in record.items() if k != "record_hash"}
    )
    result = validate_material_record(record)
    payload = result.to_dict()
    assert "blockers" in payload
    assert "warnings" in payload
    assert isinstance(payload["blockers"], list)
    assert isinstance(payload["warnings"], list)


def test_validation_result_merge_combines_collections() -> None:
    a = ValidationResult(
        blockers=[],
    )
    b = ValidationResult()
    from hexagent.material_costs.validation import ValidationIssue

    b.blockers.append(ValidationIssue(kind="blocker", path="x", message="y"))
    merged = a.merge(b)
    assert len(merged.blockers) == 1


def test_escalation_index_record_with_public_index_passes_escalation_check() -> None:
    record = base_cost_record()
    record["cost_category"] = CostCategory.COST_ESCALATION_INDEX.value
    record["cost_basis"] = "public_index"
    record["record_hash"] = canonical_sha256(
        {k: v for k, v in record.items() if k != "record_hash"}
    )
    # The escalation rule passes; other rules may surface blockers,
    # so we only assert that no escalation-specific blocker exists.
    result = validate_cost_record(record)
    assert not any("public_index" in b.message and "reserved" in b.message for b in result.blockers)
