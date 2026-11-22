"""V08-03 isolated Task037 authorities: content-bound fingerprints, no T039 hash reuse."""

# ruff: noqa: E501

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from hexagent.exchangers.shell_tube.overall_heat_transfer_resistance.canonical import (
    _authority_record_bytes,
    sha256_hex,
)
from hexagent.exchangers.shell_tube.overall_heat_transfer_resistance.models import (
    InsideFoulingResistanceAuthority,
    OutsideFoulingResistanceAuthority,
    Task037Request,
    TubeWallMaterialAuthority,
    TubeWallThermalConductivityAuthority,
)
from hexagent.release_demo.v0_4 import task039

TASK172_STAGE2_EVIDENCE = (
    "docs/tasks/evidence/TASK-172-stage2-task172-runtime-and-task174-hydraulics-r1.json",
    "docs/tasks/evidence/TASK-172-r117-approved-tube-geometry-catalog-r1.json",
    "V08-03-TASK037-EXPERIMENTAL-AUTHORITY-R1",
)

T039_DEMO_FOULING_EVIDENCE = (
    "ISSUE_214/R2/SUCCESS_VECTOR/INSIDE_FOULING",
    "ISSUE_214/R2/SUCCESS_VECTOR/OUTSIDE_FOULING",
    "T039-R2-SUCCESS-AUTHORITY-VECTOR",
    "V08-03-FOULING-SENSITIVITY-T039-DEMO-ONLY",
)

FoulingScenario = Literal["CLEAN", "T039_DEMO_FOULING"]
AuthorityProvenanceGrade = Literal["VERIFIED", "EXPERIMENTAL", "BLOCKED"]

T039_FIXTURE_MATERIAL_HASH = "2d0920034ab6f54acd3c20e339465cf26566d394aac289d6627d9dafcf2e11c4"
T039_FIXTURE_CONDUCTIVITY_HASH = "3022152e4cbbbe376674c44aabf01ea10504d524f4c5f7090e03a9cb98c99134"
T039_DEMO_CONDUCTIVITY_W_M_K = Decimal("16")
V08_STAGE2_CONDUCTIVITY_W_M_K = Decimal("14.0")


def _v08_content_fingerprint(record_bytes: bytes) -> str:
    return sha256_hex(record_bytes)


def _material_preimage_bytes(authority: TubeWallMaterialAuthority) -> bytes:
    fields = (
        "authority_id",
        "material_id",
        "material_grade",
        "source_id",
        "source_version",
        "source_location",
        "source_class",
        "permission_status",
        "approval_status",
        "evidence_refs",
    )
    return _authority_record_bytes(authority, "v08.task037.wall-material-authority.v1", fields)


def _conductivity_preimage_bytes(authority: TubeWallThermalConductivityAuthority) -> bytes:
    fields = (
        "authority_id",
        "material_id",
        "thermal_conductivity_w_m_k",
        "evaluation_temperature_k",
        "evaluation_context_id",
        "evaluation_basis",
        "applicability_authority_hash",
        "source_id",
        "source_version",
        "source_location",
        "source_class",
        "permission_status",
        "approval_status",
        "evidence_refs",
    )
    return _authority_record_bytes(authority, "v08.task037.wall-conductivity-authority.v1", fields)


def _fouling_preimage_bytes(
    authority: InsideFoulingResistanceAuthority | OutsideFoulingResistanceAuthority,
) -> bytes:
    payload = {
        "authority_id": authority.authority_id,
        "side": authority.side,
        "reference_surface": authority.reference_surface,
        "fouling_resistance_m2_k_w": str(authority.fouling_resistance_m2_k_w),
        "resistance_units": authority.resistance_units,
        "fluid_service_id": authority.fluid_service_id,
        "source_id": authority.source_id,
        "source_version": authority.source_version,
        "source_location": authority.source_location,
        "source_class": authority.source_class,
        "permission_status": authority.permission_status,
        "approval_status": authority.approval_status,
        "evidence_refs": list(authority.evidence_refs),
    }
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return text.encode("utf-8")


def _with_content_hash_material(
    *,
    authority_id: str,
    material_id: str,
    material_grade: str,
    source_id: str,
    source_version: str,
    source_location: str,
    source_class: str,
    permission_status: str,
    approval_status: str,
    evidence_refs: tuple[str, ...],
) -> TubeWallMaterialAuthority:
    provisional = TubeWallMaterialAuthority(
        authority_id,
        material_id,
        material_grade,
        source_id,
        source_version,
        source_location,
        source_class,
        permission_status,
        approval_status,
        evidence_refs,
        "0" * 64,
    )
    digest = _v08_content_fingerprint(_material_preimage_bytes(provisional))
    return TubeWallMaterialAuthority(
        authority_id,
        material_id,
        material_grade,
        source_id,
        source_version,
        source_location,
        source_class,
        permission_status,
        approval_status,
        evidence_refs,
        digest,
    )


def _with_content_hash_conductivity(
    *,
    authority_id: str,
    material_id: str,
    thermal_conductivity_w_m_k: Decimal,
    evaluation_temperature_k: Decimal,
    evaluation_context_id: str,
    evaluation_basis: str,
    applicability_preimage: str,
    source_id: str,
    source_version: str,
    source_location: str,
    source_class: str,
    permission_status: str,
    approval_status: str,
    evidence_refs: tuple[str, ...],
) -> TubeWallThermalConductivityAuthority:
    applicability = _v08_content_fingerprint(
        applicability_preimage.encode("utf-8")
        if isinstance(applicability_preimage, str)
        else applicability_preimage
    )
    provisional = TubeWallThermalConductivityAuthority(
        authority_id,
        material_id,
        thermal_conductivity_w_m_k,
        evaluation_temperature_k,
        evaluation_context_id,
        evaluation_basis,
        applicability,
        source_id,
        source_version,
        source_location,
        source_class,
        permission_status,
        approval_status,
        evidence_refs,
        "0" * 64,
    )
    digest = _v08_content_fingerprint(_conductivity_preimage_bytes(provisional))
    return TubeWallThermalConductivityAuthority(
        authority_id,
        material_id,
        thermal_conductivity_w_m_k,
        evaluation_temperature_k,
        evaluation_context_id,
        evaluation_basis,
        applicability,
        source_id,
        source_version,
        source_location,
        source_class,
        permission_status,
        approval_status,
        evidence_refs,
        digest,
    )


def _with_content_hash_fouling(
    *,
    authority_id: str,
    side: str,
    reference_surface: str,
    fouling_resistance_m2_k_w: Decimal,
    resistance_units: str,
    fluid_service_id: str,
    source_id: str,
    source_version: str,
    source_location: str,
    source_class: str,
    permission_status: str,
    approval_status: str,
    evidence_refs: tuple[str, ...],
) -> InsideFoulingResistanceAuthority | OutsideFoulingResistanceAuthority:
    cls = (
        InsideFoulingResistanceAuthority if side == "INSIDE" else OutsideFoulingResistanceAuthority
    )
    provisional = cls(
        authority_id,
        side,
        fouling_resistance_m2_k_w,
        reference_surface,
        fluid_service_id,
        source_id,
        source_version,
        source_location,
        source_class,
        permission_status,
        approval_status,
        evidence_refs,
        "0" * 64,
        resistance_units,
    )
    digest = _v08_content_fingerprint(_fouling_preimage_bytes(provisional))
    return cls(
        authority_id,
        side,
        fouling_resistance_m2_k_w,
        reference_surface,
        fluid_service_id,
        source_id,
        source_version,
        source_location,
        source_class,
        permission_status,
        approval_status,
        evidence_refs,
        digest,
        resistance_units,
    )


def build_v08_experimental_task037_request(
    fouling_scenario: FoulingScenario,
) -> Task037Request:
    """316L @ 14 W/(m·K) per TASK-172 stage-2; fouling per scenario (not T039 hash inheritance)."""
    material = _with_content_hash_material(
        authority_id="V08-EXP-WALL-MAT-316L-R1",
        material_id="V08-MAT-316L-WATER-SERVICE",
        material_grade="316L",
        source_id="TASK-172-STAGE2-WALL-MATERIAL",
        source_version="R1",
        source_location=TASK172_STAGE2_EVIDENCE[0],
        source_class="INTERNAL_ENGINEERING_RULE",
        permission_status="INTERNAL_USE_AUTHORIZED",
        approval_status="APPROVED",
        evidence_refs=TASK172_STAGE2_EVIDENCE,
    )
    mean_t = Decimal("302.5")
    cond_preimage = f"V08-EXP-COND-APPLICABILITY|k={V08_STAGE2_CONDUCTIVITY_W_M_K}|t={mean_t}"
    conductivity = _with_content_hash_conductivity(
        authority_id="V08-EXP-WALL-COND-316L-R1",
        material_id="V08-MAT-316L-WATER-SERVICE",
        thermal_conductivity_w_m_k=V08_STAGE2_CONDUCTIVITY_W_M_K,
        evaluation_temperature_k=mean_t,
        evaluation_context_id="HXFORGE_330KW_STRICT_DP_MEAN_INLET_T",
        evaluation_basis="TASK-172-STAGE2-REFERENCE",
        applicability_preimage=cond_preimage,
        source_id="TASK-172-STAGE2-WALL-CONDUCTIVITY",
        source_version="R1",
        source_location=TASK172_STAGE2_EVIDENCE[0],
        source_class="INTERNAL_ENGINEERING_RULE",
        permission_status="INTERNAL_USE_AUTHORIZED",
        approval_status="APPROVED",
        evidence_refs=TASK172_STAGE2_EVIDENCE,
    )
    if fouling_scenario == "CLEAN":
        inside = _with_content_hash_fouling(
            authority_id="V08-EXP-FOUL-IN-CLEAN-R1",
            side="INSIDE",
            reference_surface="INNER_TUBE_SURFACE",
            fouling_resistance_m2_k_w=Decimal("0"),
            resistance_units="m2_K_per_W",
            fluid_service_id="TUBE-WATER-330KW",
            source_id="TASK-172-STAGE2-CLEAN-SURFACE",
            source_version="R1",
            source_location=TASK172_STAGE2_EVIDENCE[0],
            source_class="APPROVED_ENGINEERING_BASIS",
            permission_status="INTERNAL_USE_AUTHORIZED",
            approval_status="APPROVED",
            evidence_refs=TASK172_STAGE2_EVIDENCE + ("surface_profile=CLEAN",),
        )
        outside = _with_content_hash_fouling(
            authority_id="V08-EXP-FOUL-OUT-CLEAN-R1",
            side="OUTSIDE",
            reference_surface="OUTER_TUBE_SURFACE",
            fouling_resistance_m2_k_w=Decimal("0"),
            resistance_units="m2_K_per_W",
            fluid_service_id="SHELL-WATER-330KW",
            source_id="TASK-172-STAGE2-CLEAN-SURFACE",
            source_version="R1",
            source_location=TASK172_STAGE2_EVIDENCE[0],
            source_class="APPROVED_ENGINEERING_BASIS",
            permission_status="INTERNAL_USE_AUTHORIZED",
            approval_status="APPROVED",
            evidence_refs=TASK172_STAGE2_EVIDENCE + ("surface_profile=CLEAN",),
        )
        fouling_note = "CLEAN_ZERO_FOULING_TASK172_STAGE2"
    else:
        inside = _with_content_hash_fouling(
            authority_id="V08-EXP-FOUL-IN-T039-DEMO-R1",
            side="INSIDE",
            reference_surface="INNER_TUBE_SURFACE",
            fouling_resistance_m2_k_w=Decimal("0.0001"),
            resistance_units="m2_K_per_W",
            fluid_service_id="TUBE-WATER-T039-DEMO",
            source_id="T039-INTERNAL-FOULING-SOURCE",
            source_version="R2",
            source_location="ISSUE_214/R2/SUCCESS_VECTOR/INSIDE_FOULING",
            source_class="APPROVED_ENGINEERING_BASIS",
            permission_status="INTERNAL_USE_AUTHORIZED",
            approval_status="APPROVED",
            evidence_refs=T039_DEMO_FOULING_EVIDENCE,
        )
        outside = _with_content_hash_fouling(
            authority_id="V08-EXP-FOUL-OUT-T039-DEMO-R1",
            side="OUTSIDE",
            reference_surface="OUTER_TUBE_SURFACE",
            fouling_resistance_m2_k_w=Decimal("0.0002"),
            resistance_units="m2_K_per_W",
            fluid_service_id="SHELL-WATER-T039-DEMO",
            source_id="T039-INTERNAL-FOULING-SOURCE",
            source_version="R2",
            source_location="ISSUE_214/R2/SUCCESS_VECTOR/OUTSIDE_FOULING",
            source_class="APPROVED_ENGINEERING_BASIS",
            permission_status="INTERNAL_USE_AUTHORIZED",
            approval_status="APPROVED",
            evidence_refs=T039_DEMO_FOULING_EVIDENCE,
        )
        fouling_note = "T039_DEMO_FOULING_SENSITIVITY_ONLY"
    _ = fouling_note
    base = task039._build_task037_request()
    return Task037Request(
        schema_version=base.schema_version,
        task037_version=base.task037_version,
        implementation_software_version=base.implementation_software_version,
        wall_material_authority=material,
        wall_thermal_conductivity_authority=conductivity,
        inside_fouling_authority=inside,
        outside_fouling_authority=outside,
        evidence_refs=(
            *TASK172_STAGE2_EVIDENCE,
            f"V08-03-FOULING-SCENARIO={fouling_scenario}",
            "EXPERIMENTAL_ENGINEERING_BASIS_NOT_MANUFACTURING_APPROVED",
        ),
    )


@dataclass(frozen=True)
class Task037AuthorityProvenanceAudit:
    task037_authority_provenance: AuthorityProvenanceGrade
    material_hash_reuse_corrected: bool
    conductivity_hash_reuse_corrected: bool
    fouling_basis_reconciled: bool
    inherited_t039_fixture_material_hash: str
    inherited_t039_fixture_conductivity_hash: str
    v08_experimental_material_hash: str
    v08_experimental_conductivity_hash: str
    t039_material_grade: str
    v08_material_grade: str
    t039_conductivity_w_m_k: str
    v08_conductivity_w_m_k: str
    notes: tuple[str, ...]


def audit_task037_authority_provenance() -> Task037AuthorityProvenanceAudit:
    """Document prior T039 hash reuse and V08 content-bound correction."""
    t039 = task039._build_task037_request()
    clean = build_v08_experimental_task037_request("CLEAN")
    legacy_pollution = (
        clean.wall_material_authority.authority_hash == t039.wall_material_authority.authority_hash
        or clean.wall_thermal_conductivity_authority.authority_hash
        == t039.wall_thermal_conductivity_authority.authority_hash
    )
    mat_ok = (
        clean.wall_material_authority.authority_hash != t039.wall_material_authority.authority_hash
        and clean.wall_material_authority.material_grade
        != t039.wall_material_authority.material_grade
    )
    cond_ok = (
        clean.wall_thermal_conductivity_authority.authority_hash
        != t039.wall_thermal_conductivity_authority.authority_hash
        and clean.wall_thermal_conductivity_authority.thermal_conductivity_w_m_k
        != t039.wall_thermal_conductivity_authority.thermal_conductivity_w_m_k
    )
    fouling_ok = (
        clean.inside_fouling_authority.fouling_resistance_m2_k_w == Decimal("0")
        and clean.outside_fouling_authority.fouling_resistance_m2_k_w == Decimal("0")
        and clean.inside_fouling_authority.authority_hash
        != t039.inside_fouling_authority.authority_hash
    )
    grade: AuthorityProvenanceGrade = (
        "EXPERIMENTAL" if mat_ok and cond_ok and fouling_ok and not legacy_pollution else "BLOCKED"
    )
    notes = (
        "prior_v08_shell_052_reused_t039_authority_hash_fields",
        "v08_experimental_uses_content_bound_sha256_preimage",
        "clean_fouling_grounded_in_task172_stage2_surface_profile",
        "t039_demo_fouling_marked_sensitivity_only",
    )
    return Task037AuthorityProvenanceAudit(
        task037_authority_provenance=grade,
        material_hash_reuse_corrected=mat_ok,
        conductivity_hash_reuse_corrected=cond_ok,
        fouling_basis_reconciled=fouling_ok,
        inherited_t039_fixture_material_hash=t039.wall_material_authority.authority_hash,
        inherited_t039_fixture_conductivity_hash=t039.wall_thermal_conductivity_authority.authority_hash,
        v08_experimental_material_hash=clean.wall_material_authority.authority_hash,
        v08_experimental_conductivity_hash=clean.wall_thermal_conductivity_authority.authority_hash,
        t039_material_grade=t039.wall_material_authority.material_grade,
        v08_material_grade=clean.wall_material_authority.material_grade,
        t039_conductivity_w_m_k=str(
            t039.wall_thermal_conductivity_authority.thermal_conductivity_w_m_k
        ),
        v08_conductivity_w_m_k=str(
            clean.wall_thermal_conductivity_authority.thermal_conductivity_w_m_k
        ),
        notes=notes,
    )


__all__ = [
    "FoulingScenario",
    "Task037AuthorityProvenanceAudit",
    "T039_FIXTURE_MATERIAL_HASH",
    "audit_task037_authority_provenance",
    "build_v08_experimental_task037_request",
]
