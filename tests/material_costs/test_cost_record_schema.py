"""Schema tests for TASK-013 cost records (Sections 6 / 16)."""

from __future__ import annotations

import pytest

from hexagent.canonical_json import canonical_sha256
from hexagent.material_costs.models import (
    CostBasis,
    CostCategory,
    QuantityBasis,
    SourceClass,
)
from hexagent.material_costs.schema import validate_cost_record_schema

from ._factories import base_cost_record


def test_required_fields_pass() -> None:
    record = base_cost_record()
    issues = validate_cost_record_schema(record)
    assert issues == []


def test_missing_required_field_is_blocker() -> None:
    record = base_cost_record()
    record.pop("cost_record_id")
    issues = validate_cost_record_schema(record)
    assert any("cost_record_id" in msg for msg in issues)


def test_unknown_enum_value_fails_closed() -> None:
    record = base_cost_record()
    record["cost_category"] = "rocket_fuel"
    record["record_hash"] = canonical_sha256(
        {k: v for k, v in record.items() if k != "record_hash"}
    )
    issues = validate_cost_record_schema(record)
    assert any("cost_category" in msg and "unknown" in msg for msg in issues)


@pytest.mark.parametrize("category", list(CostCategory))
def test_all_cost_categories_accepted_at_schema_layer(category: CostCategory) -> None:
    record = base_cost_record()
    record["cost_category"] = category.value
    # Escalation index categories require public_index basis (enforced by
    # the validation layer; the schema layer accepts the category value).
    if category in {CostCategory.COST_ESCALATION_INDEX, CostCategory.PRICE_INDEX}:
        record["cost_basis"] = CostBasis.PUBLIC_INDEX.value
    record["record_hash"] = canonical_sha256(
        {k: v for k, v in record.items() if k != "record_hash"}
    )
    issues = validate_cost_record_schema(record)
    assert issues == [], issues


@pytest.mark.parametrize("basis", list(CostBasis))
def test_all_cost_bases_accepted_at_schema_layer(basis: CostBasis) -> None:
    record = base_cost_record()
    record["cost_basis"] = basis.value
    # public_index on a non-index category is enforced by the
    # validation layer; the schema layer only checks enum membership.
    if basis == CostBasis.PUBLIC_INDEX:
        record["cost_category"] = CostCategory.COST_ESCALATION_INDEX.value
    record["record_hash"] = canonical_sha256(
        {k: v for k, v in record.items() if k != "record_hash"}
    )
    issues = validate_cost_record_schema(record)
    assert issues == [], issues


@pytest.mark.parametrize("quantity_basis", list(QuantityBasis))
def test_all_quantity_bases_accepted(quantity_basis: QuantityBasis) -> None:
    record = base_cost_record()
    record["quantity_basis"] = quantity_basis.value
    record["record_hash"] = canonical_sha256(
        {k: v for k, v in record.items() if k != "record_hash"}
    )
    issues = validate_cost_record_schema(record)
    assert issues == [], issues


def test_record_hash_mismatch_is_blocker() -> None:
    record = base_cost_record()
    record["record_hash"] = "f" * 64
    issues = validate_cost_record_schema(record)
    assert any("record_hash" in msg and "mismatch" in msg for msg in issues)


def test_record_hash_deterministic_across_replays() -> None:
    a = base_cost_record()
    b = base_cost_record()
    assert a["record_hash"] == b["record_hash"]


def test_currency_must_be_3_letter_alpha() -> None:
    record = base_cost_record()
    record["currency"] = "DOLLAR"
    record["record_hash"] = canonical_sha256(
        {k: v for k, v in record.items() if k != "record_hash"}
    )
    issues = validate_cost_record_schema(record)
    assert any("currency" in msg for msg in issues)


def test_cost_value_required_subfields_present() -> None:
    record = base_cost_record()
    record["cost_value"] = {
        "value": "4.20",
        "currency": "USD",
        "quantity_value_si": "1.0",
        "unit_basis": "kg",
        "source_pointer": "internal://handbook/SA-106-B-price",
    }
    record["record_hash"] = canonical_sha256(
        {k: v for k, v in record.items() if k != "record_hash"}
    )
    issues = validate_cost_record_schema(record)
    assert issues == []


def test_cost_value_missing_subfield_is_blocker() -> None:
    record = base_cost_record()
    record["cost_value"] = {
        "value": "4.20",
        # currency omitted
        "quantity_value_si": "1.0",
        "unit_basis": "kg",
        "source_pointer": "internal://handbook/SA-106-B-price",
    }
    record["record_hash"] = canonical_sha256(
        {k: v for k, v in record.items() if k != "record_hash"}
    )
    issues = validate_cost_record_schema(record)
    assert any("currency" in msg for msg in issues)


@pytest.mark.parametrize("source_class", list(SourceClass))
def test_every_source_class_accepted_at_schema_layer(
    source_class: SourceClass,
) -> None:
    """Schema accepts every Section 4 source class; license-boundary
    layer is what enforces RESTRICTED numeric-payload bans."""
    record = base_cost_record()
    record["source_class"] = source_class.value
    record["record_hash"] = canonical_sha256(
        {k: v for k, v in record.items() if k != "record_hash"}
    )
    if source_class in {
        SourceClass.INTERNAL_ENGINEERING_ASSUMPTION,
        SourceClass.USER_PROVIDED_PROJECT_DATA,
    }:
        record.setdefault(
            "human_entered_evidence",
            {"actor": "x", "entered_at": "2026-01-01T00:00:00Z"},
        )
    if source_class == SourceClass.RESTRICTED_REFERENCE_METADATA_ONLY:
        record.pop("human_entered_evidence", None)
    record["record_hash"] = canonical_sha256(
        {k: v for k, v in record.items() if k != "record_hash"}
    )
    issues = validate_cost_record_schema(record)
    assert issues == [], issues
