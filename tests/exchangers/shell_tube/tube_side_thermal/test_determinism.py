"""TASK-026 determinism tests (T1-R2 numbered_inventory item 36).

Frozen test reference set (T1-R2):
  36. test_same_input_yields_identical_canonical_output_across_runs

T1-R2 module allocation: 1 test in this module.
"""

from __future__ import annotations

from decimal import Decimal

from hexagent.exchangers.shell_tube.tube_side_thermal import (
    DEFERRED_CAPABILITIES_V1,
    IMPLEMENTATION_SOFTWARE_VERSION,
    INPUT_EVIDENCE_REFS_V1,
    SCHEMA_VERSION,
    TASK026_VERSION,
    FrozenProvenance,
    PhaseAssertion,
    PhaseRegion,
    PropertySnapshot,
    ThermalBoundaryCondition,
    TubeSideThermalRequest,
    compute_tube_side_heat_transfer_coefficient,
    recompute_property_snapshot_hash,
)


def _build_request_once() -> TubeSideThermalRequest:
    mu = Decimal("0.001")
    D_h = Decimal("0.01")
    k = Decimal("0.5984")
    A_total = Decimal("0.01")
    c_p = Decimal("4190.35584")
    rho = Decimal("499.0020") * mu / (Decimal("0.0500898") * D_h)
    m_dot = Decimal("0.0500898") * rho * A_total
    ps = PropertySnapshot(
        density_kg_m3=rho,
        dynamic_viscosity_pa_s=mu,
        thermal_conductivity_w_m_k=k,
        specific_heat_capacity_j_kg_k=c_p,
        bulk_temperature_k=Decimal("293.15"),
        bulk_pressure_pa=Decimal("101325"),
        phase_region=PhaseRegion.SINGLE_PHASE_LIQUID,
        property_source_id="CoolProp-6.6",
        property_source_version="1.0.0",
        property_snapshot_hash="0" * 64,
    )
    h = recompute_property_snapshot_hash(ps)
    ps2 = PropertySnapshot(
        density_kg_m3=rho,
        dynamic_viscosity_pa_s=mu,
        thermal_conductivity_w_m_k=k,
        specific_heat_capacity_j_kg_k=c_p,
        bulk_temperature_k=ps.bulk_temperature_k,
        bulk_pressure_pa=ps.bulk_pressure_pa,
        phase_region=ps.phase_region,
        property_source_id=ps.property_source_id,
        property_source_version=ps.property_source_version,
        property_snapshot_hash=h,
    )
    prov = FrozenProvenance(
        task_id="TASK-026",
        design_contract_path="/tmp/TASK-026-DESIGN-CONTRACT-DRAFT-R6-R7.md",
        implementation_software_version=IMPLEMENTATION_SOFTWARE_VERSION,
        input_evidence_refs=INPUT_EVIDENCE_REFS_V1,
        upstream_identity_hashes=("a" * 64,),
    )
    return TubeSideThermalRequest(
        schema_version=SCHEMA_VERSION,
        task026_version=TASK026_VERSION,
        implementation_software_version=IMPLEMENTATION_SOFTWARE_VERSION,
        property_snapshot_hash=h,
        property_snapshot=ps2,
        phase_assertion=PhaseAssertion.SINGLE_PHASE_LIQUID,
        thermal_boundary_condition=ThermalBoundaryCondition.CWT,
        mass_flow_rate_kg_s=m_dot,
        deferred_capabilities=DEFERRED_CAPABILITIES_V1,
        provenance=prov,
    )


class Task025ValidResult:
    def __init__(self, A_total: Decimal, D_h: Decimal) -> None:
        self.single_tube_flow_area_m2 = A_total
        self.total_parallel_flow_area_m2 = A_total
        self.flow_cross_section_wetted_perimeter_m = Decimal("0.0314159265358979")
        self.total_flow_cross_section_wetted_perimeter_m = Decimal("0.0314159265358979")
        self.hydraulic_diameter_m = D_h
        self.internal_volume_m3 = Decimal("0.0001")
        self.internal_heat_transfer_surface_area_m2 = Decimal("0.01")
        self.result_hash = "a" * 64
        self.hydraulic_authority_hash = "b" * 64


def test_same_input_yields_identical_canonical_output_across_runs() -> None:
    """T1-R2 36 — Same input produces identical canonical output across runs."""
    req = _build_request_once()
    upstream = Task025ValidResult(Decimal("0.01"), Decimal("0.01"))
    r1 = compute_tube_side_heat_transfer_coefficient(req, upstream)
    r2 = compute_tube_side_heat_transfer_coefficient(req, upstream)
    assert hasattr(r1, "flow_regime") and hasattr(r2, "flow_regime")
    assert r1.result_hash == r2.result_hash
    assert r1.result_id == r2.result_id
    assert r1.bulk_velocity_m_s == r2.bulk_velocity_m_s
    assert r1.reynolds_number == r2.reynolds_number
    assert r1.prandtl_number == r2.prandtl_number
    assert r1.nusselt_number == r2.nusselt_number
    assert (
        r1.tube_side_heat_transfer_coefficient_w_m2_k
        == r2.tube_side_heat_transfer_coefficient_w_m2_k
    )
