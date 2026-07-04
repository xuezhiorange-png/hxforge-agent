"""License-boundary tests for TASK-013 material / cost records
(Sections 5.5 / 6.4 / 9).

Asserts that:

* ``RESTRICTED_REFERENCE_METADATA_ONLY`` records MUST NOT carry
  ``property_values`` or ``cost_value`` (Sections 5.5 #1, 6.4 #1, 9).
* ``VENDOR_PERMISSIONED`` records that carry consumable values MUST
  record ``permission_scope`` and ``usage_scope`` (Sections 5.5 #2,
  6.4 #2, 9).
* Property values are accepted for the four value-carrying source
  classes.
* Cost values are accepted for the four value-carrying source classes.
* Standard bodies / vendor catalog bodies / scanned pages / formula
  images are forbidden by the metadata-only contract on
  ``standard_or_spec_reference``.
"""

from __future__ import annotations

from hexagent.canonical_json import canonical_sha256
from hexagent.material_costs.models import SourceClass
from hexagent.material_costs.validation import (
    validate_cost_record,
    validate_material_record,
)

from ._factories import (
    base_cost_record,
    base_material_record,
    restricted_material_record,
)

# ---------- property_values allow / forbid ----------


def test_property_values_allowed_for_internal_source() -> None:
    record = base_material_record()
    record["source_class"] = SourceClass.INTERNAL_ENGINEERING_ASSUMPTION.value
    record["property_values"] = [
        {
            "property_name": "yield_strength",
            "value_si": "250",
            "unit_si": "MPa",
            "source_pointer": "internal://handbook/SA-106-B",
            "quality_flags": ["assumed_value"],
        }
    ]
    record["record_hash"] = canonical_sha256(
        {k: v for k, v in record.items() if k != "record_hash"}
    )
    result = validate_material_record(record)
    assert result.ok, result.to_dict()


def test_property_values_allowed_for_public_metadata() -> None:
    record = base_material_record()
    record["source_class"] = SourceClass.PUBLIC_METADATA.value
    record["license_evidence"] = "public_domain"
    record.pop("human_entered_evidence", None)
    record["property_values"] = [
        {
            "property_name": "density",
            "value_si": "7850",
            "unit_si": "kg/m3",
            "source_pointer": "internal://public/csi-density",
            "quality_flags": ["field_measured"],
        }
    ]
    record["record_hash"] = canonical_sha256(
        {k: v for k, v in record.items() if k != "record_hash"}
    )
    result = validate_material_record(record)
    assert result.ok, result.to_dict()


def test_property_values_allowed_for_user_provided_project_data() -> None:
    record = base_material_record()
    record["source_class"] = SourceClass.USER_PROVIDED_PROJECT_DATA.value
    record["license_evidence"] = "permission_evidence_pointer"
    record["property_values"] = [
        {
            "property_name": "yield_strength",
            "value_si": "275",
            "unit_si": "MPa",
            "source_pointer": "internal://project/PROJ-7",
            "quality_flags": ["field_measured"],
        }
    ]
    record["record_hash"] = canonical_sha256(
        {k: v for k, v in record.items() if k != "record_hash"}
    )
    result = validate_material_record(record)
    assert result.ok, result.to_dict()


def test_property_values_allowed_for_vendor_permissioned_with_usage_scope() -> None:
    record = base_material_record()
    record["source_class"] = SourceClass.VENDOR_PERMISSIONED.value
    record["license_evidence"] = "permission_evidence_pointer"
    record["human_entered_evidence"] = {
        "actor": "engineering-review",
        "entered_at": "2026-01-01T00:00:00Z",
        "permission_scope": ["usage_scope"],
        "usage_scope": "vendor_internal_consumption_only",
    }
    record["property_values"] = [
        {
            "property_name": "density",
            "value_si": "7850",
            "unit_si": "kg/m3",
            "source_pointer": "internal://vendor/ACME-density",
            "quality_flags": ["vendor_certified"],
        }
    ]
    record["record_hash"] = canonical_sha256(
        {k: v for k, v in record.items() if k != "record_hash"}
    )
    result = validate_material_record(record)
    assert result.ok, result.to_dict()


def test_property_values_rejected_for_restricted_metadata_only() -> None:
    record = restricted_material_record()
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
    assert any(
        "RESTRICTED" in b.message and "property_values" in b.message for b in result.blockers
    )


def test_vendor_permissioned_without_usage_scope_is_blocker() -> None:
    record = base_material_record()
    record["source_class"] = SourceClass.VENDOR_PERMISSIONED.value
    record["license_evidence"] = "permission_evidence_pointer"
    record["human_entered_evidence"] = {
        "actor": "engineering-review",
        "entered_at": "2026-01-01T00:00:00Z",
        "permission_scope": ["usage_scope"],
        # usage_scope omitted
    }
    record["property_values"] = [
        {
            "property_name": "density",
            "value_si": "7850",
            "unit_si": "kg/m3",
            "source_pointer": "internal://vendor/ACME-density",
            "quality_flags": ["vendor_certified"],
        }
    ]
    record["record_hash"] = canonical_sha256(
        {k: v for k, v in record.items() if k != "record_hash"}
    )
    result = validate_material_record(record)
    assert not result.ok
    assert any("usage_scope" in b.message for b in result.blockers)


# ---------- cost_value allow / forbid ----------


def test_cost_value_allowed_for_internal_source() -> None:
    record = base_cost_record()
    record["source_class"] = SourceClass.INTERNAL_ENGINEERING_ASSUMPTION.value
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
    result = validate_cost_record(record)
    assert result.ok, result.to_dict()


def test_cost_value_rejected_for_restricted_metadata_only() -> None:
    record = base_cost_record()
    record["source_class"] = SourceClass.RESTRICTED_REFERENCE_METADATA_ONLY.value
    record["license_evidence"] = "metadata_only"
    record.pop("human_entered_evidence", None)
    record["cost_value"] = {
        "value": "4.20",
        "currency": "USD",
        "quantity_value_si": "1.0",
        "unit_basis": "kg",
        "source_pointer": "internal://restricted/asme-prices",
    }
    record["record_hash"] = canonical_sha256(
        {k: v for k, v in record.items() if k != "record_hash"}
    )
    result = validate_cost_record(record)
    assert not result.ok
    assert any("RESTRICTED" in b.message and "cost_value" in b.message for b in result.blockers)


# ---------- unit / currency binding ----------


def test_property_values_unit_si_must_be_in_dimensional_units() -> None:
    record = base_material_record()
    record["property_values"] = [
        {
            "property_name": "yield_strength",
            "value_si": "250",
            "unit_si": "ksi",  # not in dimensional_units
            "source_pointer": "internal://handbook/SA-106-B",
            "quality_flags": ["assumed_value"],
        }
    ]
    record["record_hash"] = canonical_sha256(
        {k: v for k, v in record.items() if k != "record_hash"}
    )
    result = validate_material_record(record)
    assert not result.ok
    assert any("unit_si" in b.message for b in result.blockers)


def test_cost_value_unit_basis_must_match_record_unit_basis() -> None:
    record = base_cost_record()
    record["cost_value"] = {
        "value": "4.20",
        "currency": "USD",
        "quantity_value_si": "1.0",
        "unit_basis": "lb",  # record.unit_basis is "kg"
        "source_pointer": "internal://handbook/SA-106-B-price",
    }
    record["record_hash"] = canonical_sha256(
        {k: v for k, v in record.items() if k != "record_hash"}
    )
    result = validate_cost_record(record)
    assert not result.ok
    assert any("unit_basis" in b.message and "must equal" in b.message for b in result.blockers)


def test_cost_value_currency_must_match_record_currency() -> None:
    record = base_cost_record()
    record["cost_value"] = {
        "value": "4.20",
        "currency": "EUR",  # record.currency is "USD"
        "quantity_value_si": "1.0",
        "unit_basis": "kg",
        "source_pointer": "internal://handbook/SA-106-B-price",
    }
    record["record_hash"] = canonical_sha256(
        {k: v for k, v in record.items() if k != "record_hash"}
    )
    result = validate_cost_record(record)
    assert not result.ok
    assert any("currency" in b.message and "must equal" in b.message for b in result.blockers)


def test_escalation_date_requires_escalation_index_reference_unless_justified() -> None:
    record = base_cost_record()
    record["escalation_date"] = "2026-12-31T00:00:00Z"
    record["cost_value"] = {
        "value": "4.20",
        "currency": "USD",
        "quantity_value_si": "1.0",
        "unit_basis": "kg",
        # escalation_index_reference omitted
        "source_pointer": "internal://handbook/SA-106-B-price",
    }
    # Remove the factory's default justification so escalation_index_reference
    # absence is a true blocker (no documented justification present).
    record["human_entered_evidence"].pop("justification", None)
    record["record_hash"] = canonical_sha256(
        {k: v for k, v in record.items() if k != "record_hash"}
    )
    result = validate_cost_record(record)
    assert not result.ok
    assert any("escalation_index_reference" in b.message for b in result.blockers)


def test_escalation_date_with_documented_justification_is_warning_not_blocker() -> None:
    record = base_cost_record()
    record["escalation_date"] = "2026-12-31T00:00:00Z"
    record["cost_value"] = {
        "value": "4.20",
        "currency": "USD",
        "quantity_value_si": "1.0",
        "unit_basis": "kg",
        "source_pointer": "internal://handbook/SA-106-B-price",
    }
    he = record["human_entered_evidence"]
    he["justification"] = "escalation omitted; current price assumed constant"
    record["record_hash"] = canonical_sha256(
        {k: v for k, v in record.items() if k != "record_hash"}
    )
    result = validate_cost_record(record)
    # Section 15 — escalation_index_reference absent + documented
    # justification is a WARNING (not a blocker).
    assert any("escalation" in w.message.lower() for w in result.warnings)


# ---------- standard_or_spec_reference metadata-only ----------


def test_standard_or_spec_reference_must_be_bibliographic_metadata_only() -> None:
    record = base_material_record()
    record["standard_or_spec_reference"] = {
        "issuing_body": "ASME",
        "designation": "SA-106",
        "edition_year": 2023,
        "scanned_page_body": "Yield strength 250 MPa...",  # FORBIDDEN
    }
    record["record_hash"] = canonical_sha256(
        {k: v for k, v in record.items() if k != "record_hash"}
    )
    result = validate_material_record(record)
    assert not result.ok
    assert any("forbidden non-bibliographic field" in b.message for b in result.blockers)


# ---------- cost_category vs escalation rule ----------


def test_escalation_index_category_requires_public_index_basis() -> None:
    record = base_cost_record()
    record["cost_category"] = "cost_escalation_index"
    record["cost_basis"] = "internal_assumption"  # must be public_index
    record["record_hash"] = canonical_sha256(
        {k: v for k, v in record.items() if k != "record_hash"}
    )
    result = validate_cost_record(record)
    assert not result.ok
    assert any("public_index" in b.message for b in result.blockers)


def test_non_escalation_category_with_public_index_basis_is_blocker() -> None:
    record = base_cost_record()
    record["cost_category"] = "material_unit_price"
    record["cost_basis"] = "public_index"  # reserved for escalation index
    record["record_hash"] = canonical_sha256(
        {k: v for k, v in record.items() if k != "record_hash"}
    )
    result = validate_cost_record(record)
    assert not result.ok
    assert any("public_index" in b.message and "reserved" in b.message for b in result.blockers)
