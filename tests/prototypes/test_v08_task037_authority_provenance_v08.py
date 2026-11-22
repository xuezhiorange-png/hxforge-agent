"""Task037 V08 authority must not reuse Task039 fixture hashes."""

# ruff: noqa: E501

from __future__ import annotations

from hexagent.release_demo.v0_4 import task039
from prototypes.v08_thermal_rating.v08_task037_experimental_authority_v08 import (
    T039_FIXTURE_CONDUCTIVITY_HASH,
    T039_FIXTURE_MATERIAL_HASH,
    audit_task037_authority_provenance,
    build_v08_experimental_task037_request,
)


def test_t039_fixture_hashes_distinct_from_v08_experimental() -> None:
    t039 = task039._build_task037_request()
    assert t039.wall_material_authority.authority_hash == T039_FIXTURE_MATERIAL_HASH
    assert t039.wall_material_authority.material_grade == "FIXTURE-GRADE"
    clean = build_v08_experimental_task037_request("CLEAN")
    fouled = build_v08_experimental_task037_request("T039_DEMO_FOULING")
    assert clean.wall_material_authority.authority_hash != T039_FIXTURE_MATERIAL_HASH
    assert clean.wall_material_authority.material_grade == "316L"
    assert (
        clean.wall_thermal_conductivity_authority.authority_hash != T039_FIXTURE_CONDUCTIVITY_HASH
    )
    assert (
        clean.wall_thermal_conductivity_authority.thermal_conductivity_w_m_k
        != t039.wall_thermal_conductivity_authority.thermal_conductivity_w_m_k
    )
    assert clean.inside_fouling_authority.fouling_resistance_m2_k_w == 0
    assert (
        fouled.inside_fouling_authority.fouling_resistance_m2_k_w
        != clean.inside_fouling_authority.fouling_resistance_m2_k_w
    )
    assert (
        fouled.inside_fouling_authority.authority_hash
        != clean.inside_fouling_authority.authority_hash
    )


def test_audit_documents_hash_reuse_correction() -> None:
    audit = audit_task037_authority_provenance()
    assert audit.material_hash_reuse_corrected is True
    assert audit.conductivity_hash_reuse_corrected is True
    assert audit.fouling_basis_reconciled is True
    assert audit.task037_authority_provenance == "EXPERIMENTAL"
