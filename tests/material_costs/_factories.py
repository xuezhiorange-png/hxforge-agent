"""Shared fixture factories for TASK-013 material / cost record tests.

All factories produce records that comply with the TASK-013 frozen
design contract and use only license-safe metadata. No standard body,
vendor catalog body, restricted price list, restricted property
table, scanned page, formula image, or copyrighted excerpt appears in
any fixture (Section 9 / Section 18 / Section 20 final paragraph).
"""

from __future__ import annotations

import copy
from typing import Any

from hexagent.canonical_json import canonical_sha256

_BASE_MATERIAL: dict[str, Any] = {
    "material_record_id": "MAT-001",
    "material_record_version": "1.0.0",
    "material_family": "carbon_steel",
    "material_grade_or_designation": "SA-106-B",
    "form_factor": "pipe",
    "region": "US",
    "effective_date": "2026-01-01T00:00:00Z",
    "source_class": "INTERNAL_ENGINEERING_ASSUMPTION",
    "source_reference": "internal://handbook/SA-106-B",
    "license_evidence": "project_internal_authority",
    "dimensional_units": {
        "yield_strength": "MPa",
        "density": "kg/m3",
    },
    "quality_flags": ["assumed_value"],
    "approval_state": "approved",
    "provenance_edges": ["edge:internal-handbook/SA-106-B"],
    "human_entered_evidence": {
        "actor": "engineering-review",
        "entered_at": "2026-01-01T00:00:00Z",
        "justification": "internal default for SA-106-B pipe",
    },
}


def _hash(record: dict[str, Any]) -> str:
    """Compute the content-addressable SHA-256 record_hash (Section 16)."""
    return canonical_sha256({k: v for k, v in record.items() if k != "record_hash"})


def base_material_record() -> dict[str, Any]:
    """Return a minimal license-safe material record fixture."""
    rec = copy.deepcopy(_BASE_MATERIAL)
    rec["record_hash"] = _hash(rec)
    return rec


def base_cost_record() -> dict[str, Any]:
    """Return a minimal license-safe cost record fixture."""
    rec: dict[str, Any] = {
        "cost_record_id": "COST-001",
        "cost_record_version": "1.0.0",
        "cost_category": "material_unit_price",
        "cost_basis": "internal_assumption",
        "currency": "USD",
        "region": "US",
        "effective_date": "2026-01-01T00:00:00Z",
        "quantity_basis": "per_mass",
        "unit_basis": "kg",
        "source_class": "INTERNAL_ENGINEERING_ASSUMPTION",
        "source_reference": "internal://handbook/SA-106-B-price",
        "license_evidence": "project_internal_authority",
        "quality_flags": ["assumed_value"],
        "approval_state": "approved",
        "provenance_edges": ["edge:internal-handbook/SA-106-B-price"],
        "human_entered_evidence": {
            "actor": "engineering-review",
            "entered_at": "2026-01-01T00:00:00Z",
            "justification": "internal default cost",
        },
    }
    rec["record_hash"] = _hash(rec)
    return rec


def restricted_material_record() -> dict[str, Any]:
    """A RESTRICTED_REFERENCE_METADATA_ONLY material record fixture
    (metadata-only; no property_values)."""
    rec = copy.deepcopy(_BASE_MATERIAL)
    rec["material_record_id"] = "MAT-RESTRICTED-001"
    rec["source_class"] = "RESTRICTED_REFERENCE_METADATA_ONLY"
    rec["source_reference"] = "internal://restricted-bib/ASME-SA-106"
    rec["license_evidence"] = "metadata_only"
    rec["standard_or_spec_reference"] = {
        "issuing_body": "ASME",
        "designation": "SA-106",
        "edition_year": 2023,
        "clause_locator": "Section II Part A",
        "bibliographic_metadata": {"kind": "restricted_bibliographic_only"},
    }
    # RESTRICTED must NOT carry human_entered_evidence per the contract
    # (only USER/INTERNAL/VENDOR records require it).
    rec.pop("human_entered_evidence", None)
    rec["record_hash"] = _hash(rec)
    return rec
