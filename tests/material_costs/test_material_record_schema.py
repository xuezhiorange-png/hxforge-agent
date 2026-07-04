"""Schema tests for TASK-013 material records (Sections 5 / 16)."""

from __future__ import annotations

import pytest

from hexagent.canonical_json import canonical_sha256
from hexagent.material_costs.models import FormFactor, MaterialFamily, SourceClass
from hexagent.material_costs.schema import validate_material_record_schema

from ._factories import base_material_record


def test_required_fields_pass() -> None:
    record = base_material_record()
    issues = validate_material_record_schema(record)
    assert issues == []


def test_missing_required_field_is_blocker() -> None:
    record = base_material_record()
    record.pop("material_record_id")
    issues = validate_material_record_schema(record)
    assert any("material_record_id" in msg for msg in issues)


def test_unknown_enum_value_fails_closed() -> None:
    record = base_material_record()
    record["material_family"] = "unobtainium"
    issues = validate_material_record_schema(record)
    assert any("material_family" in msg and "unknown" in msg for msg in issues)


def test_unknown_form_factor_fails_closed() -> None:
    record = base_material_record()
    record["form_factor"] = "billett"  # the legacy typo deliberately rejected
    issues = validate_material_record_schema(record)
    assert any("form_factor" in msg and "unknown" in msg for msg in issues)


@pytest.mark.parametrize("family", list(MaterialFamily))
def test_all_material_families_accepted(family: MaterialFamily) -> None:
    record = base_material_record()
    record["material_family"] = family.value
    record["record_hash"] = canonical_sha256(
        {k: v for k, v in record.items() if k != "record_hash"}
    )
    issues = validate_material_record_schema(record)
    assert issues == [], issues


@pytest.mark.parametrize("form_factor", list(FormFactor))
def test_all_form_factors_accepted(form_factor: FormFactor) -> None:
    record = base_material_record()
    record["form_factor"] = form_factor.value
    record["record_hash"] = canonical_sha256(
        {k: v for k, v in record.items() if k != "record_hash"}
    )
    issues = validate_material_record_schema(record)
    assert issues == [], issues


def test_record_hash_mismatch_is_blocker() -> None:
    record = base_material_record()
    record["record_hash"] = "0" * 64
    issues = validate_material_record_schema(record)
    assert any("record_hash" in msg and "mismatch" in msg for msg in issues)


def test_record_hash_deterministic_across_replays() -> None:
    a = base_material_record()
    b = base_material_record()
    assert a["record_hash"] == b["record_hash"]


def test_changing_value_changes_record_hash() -> None:
    a = base_material_record()
    b = base_material_record()
    b["material_grade_or_designation"] = "316L"
    b["record_hash"] = canonical_sha256({k: v for k, v in b.items() if k != "record_hash"})
    assert a["record_hash"] != b["record_hash"]


def test_region_must_be_iso_alpha2_or_intl() -> None:
    record = base_material_record()
    record["region"] = "USA"  # 3 letters, not alpha-2
    record["record_hash"] = canonical_sha256(
        {k: v for k, v in record.items() if k != "record_hash"}
    )
    issues = validate_material_record_schema(record)
    assert any("region" in msg for msg in issues)


def test_effective_date_must_be_rfc3339_utc() -> None:
    record = base_material_record()
    record["effective_date"] = "2026-01-01"  # missing time + Z
    record["record_hash"] = canonical_sha256(
        {k: v for k, v in record.items() if k != "record_hash"}
    )
    issues = validate_material_record_schema(record)
    assert any("effective_date" in msg for msg in issues)


def test_provenance_edges_required_and_non_empty() -> None:
    record = base_material_record()
    record["provenance_edges"] = []
    record["record_hash"] = canonical_sha256(
        {k: v for k, v in record.items() if k != "record_hash"}
    )
    issues = validate_material_record_schema(record)
    assert any("provenance_edges" in msg for msg in issues)


def test_property_values_shape_required_subfields() -> None:
    record = base_material_record()
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
    issues = validate_material_record_schema(record)
    assert issues == []


def test_property_values_missing_subfield_is_blocker() -> None:
    record = base_material_record()
    record["property_values"] = [
        {
            "property_name": "yield_strength",
            "value_si": "250",
            "unit_si": "MPa",
            # source_pointer omitted
            "quality_flags": ["assumed_value"],
        }
    ]
    record["record_hash"] = canonical_sha256(
        {k: v for k, v in record.items() if k != "record_hash"}
    )
    issues = validate_material_record_schema(record)
    assert any("source_pointer" in msg for msg in issues)


@pytest.mark.parametrize("source_class", list(SourceClass))
def test_every_source_class_accepted_at_schema_layer(
    source_class: SourceClass,
) -> None:
    """Schema accepts every Section 4 source class; license-boundary
    layer is what enforces RESTRICTED numeric-payload bans."""
    record = base_material_record()
    record["source_class"] = source_class.value
    record["record_hash"] = canonical_sha256(
        {k: v for k, v in record.items() if k != "record_hash"}
    )
    # INTERNAL / USER / VENDOR records require human_entered_evidence
    # (verified by validation layer, not by schema layer).
    if source_class in {
        SourceClass.INTERNAL_ENGINEERING_ASSUMPTION,
        SourceClass.USER_PROVIDED_PROJECT_DATA,
    }:
        record.setdefault(
            "human_entered_evidence",
            {
                "actor": "x",
                "entered_at": "2026-01-01T00:00:00Z",
            },
        )
    if source_class == SourceClass.RESTRICTED_REFERENCE_METADATA_ONLY:
        record.pop("human_entered_evidence", None)
    record["record_hash"] = canonical_sha256(
        {k: v for k, v in record.items() if k != "record_hash"}
    )
    issues = validate_material_record_schema(record)
    assert issues == [], issues
