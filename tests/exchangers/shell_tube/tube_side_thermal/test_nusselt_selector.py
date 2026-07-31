"""TASK-026 Nusselt selector tests (T1-R2 numbered_inventory items 16-20).

Frozen test reference set (T1-R2):
  16. test_re_equals_2300_emits_BL_REGIME_NO_CORRELATION_APPLICABLE
  17. test_transition_interval_emits_BL_REGIME_NO_CORRELATION_APPLICABLE
  18. test_re_equals_3000_selects_turbulent
  19. test_pr_outside_selected_correlation_emits_BL_CORRELATION_NOT_APPLICABLE
  20. test_cwt_vs_chf_selection_by_thermal_boundary

T1-R2 module allocation: 5 tests in this module.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from hexagent.exchangers.shell_tube.tube_side_thermal import (
    DEFERRED_CAPABILITIES_V1,
    IMPLEMENTATION_SOFTWARE_VERSION,
    INPUT_EVIDENCE_REFS_V1,
    SCHEMA_VERSION,
    TASK026_VERSION,
    FlowRegime,
    FrozenProvenance,
    PhaseAssertion,
    PhaseRegion,
    PropertySnapshot,
    ThermalBoundaryCondition,
    TubeSideThermalRequest,
    compute_tube_side_heat_transfer_coefficient,
    recompute_property_snapshot_hash,
)


def _build_request_for_re(
    re_target: Decimal,
    pr: Decimal,
    thermal_boundary: ThermalBoundaryCondition,
) -> TubeSideThermalRequest:
    """Pick inputs so the pipeline produces re_target post-S12 quantization."""
    mu = Decimal('0.001')
    D_h = Decimal('0.01')
    k = Decimal('0.5984')
    A_total = Decimal('0.01')
    c_p = pr * k / mu  # Pr = mu * c_p / k -> c_p = Pr * k / mu
    # rho for Re = re_target
    # v = Re * mu / (rho * D_h);  v = m_dot / (rho * A); m_dot = v * rho * A
    # Set v = 0.05 (laminar), then rho = Re * mu / (v * D_h)
    if re_target < Decimal('2300'):
        # Laminar regime.
        v = Decimal('0.05')
        rho = re_target * mu / (v * D_h)
        m_dot = v * rho * A_total
    else:
        # For turbulent, use higher velocity.
        v = Decimal('50.0')
        rho = re_target * mu / (v * D_h)
        m_dot = v * rho * A_total
    ps = PropertySnapshot(
        density_kg_m3=rho,
        dynamic_viscosity_pa_s=mu,
        thermal_conductivity_w_m_k=k,
        specific_heat_capacity_j_kg_k=c_p,
        bulk_temperature_k=Decimal('293.15'),
        bulk_pressure_pa=Decimal('101325'),
        phase_region=PhaseRegion.SINGLE_PHASE_LIQUID,
        property_source_id='CoolProp-6.6',
        property_source_version='1.0.0',
        property_snapshot_hash='0' * 64,
    )
    h = recompute_property_snapshot_hash(ps)
    ps2 = PropertySnapshot(
        density_kg_m3=rho, dynamic_viscosity_pa_s=mu,
        thermal_conductivity_w_m_k=k, specific_heat_capacity_j_kg_k=c_p,
        bulk_temperature_k=ps.bulk_temperature_k, bulk_pressure_pa=ps.bulk_pressure_pa,
        phase_region=ps.phase_region, property_source_id=ps.property_source_id,
        property_source_version=ps.property_source_version, property_snapshot_hash=h,
    )
    prov = FrozenProvenance(
        task_id='TASK-026',
        design_contract_path='/tmp/TASK-026-DESIGN-CONTRACT-DRAFT-R6-R7.md',
        implementation_software_version=IMPLEMENTATION_SOFTWARE_VERSION,
        input_evidence_refs=INPUT_EVIDENCE_REFS_V1,
        upstream_identity_hashes=('a' * 64,),
    )
    return TubeSideThermalRequest(
        schema_version=SCHEMA_VERSION,
        task026_version=TASK026_VERSION,
        implementation_software_version=IMPLEMENTATION_SOFTWARE_VERSION,
        property_snapshot_hash=h,
        property_snapshot=ps2,
        phase_assertion=PhaseAssertion.SINGLE_PHASE_LIQUID,
        thermal_boundary_condition=thermal_boundary,
        mass_flow_rate_kg_s=m_dot,
        deferred_capabilities=DEFERRED_CAPABILITIES_V1,
        provenance=prov,
    )


class Task025ValidResult:
    def __init__(self, A_total: Decimal, D_h: Decimal) -> None:
        self.single_tube_flow_area_m2 = A_total
        self.total_parallel_flow_area_m2 = A_total
        self.flow_cross_section_wetted_perimeter_m = Decimal('0.0314159265358979')
        self.total_flow_cross_section_wetted_perimeter_m = Decimal('0.0314159265358979')
        self.hydraulic_diameter_m = D_h
        self.internal_volume_m3 = Decimal('0.0001')
        self.internal_heat_transfer_surface_area_m2 = Decimal('0.01')
        self.result_hash = 'a' * 64
        self.hydraulic_authority_hash = 'b' * 64


def test_re_equals_2300_emits_BL_REGIME_NO_CORRELATION_APPLICABLE() -> None:
    """T1-R2 16 — Re = 2300 emits transition gap blocker."""
    req = _build_request_for_re(
        Decimal('2300'),
        Decimal('7.0026'),
        ThermalBoundaryCondition.CWT,
    )
    result = compute_tube_side_heat_transfer_coefficient(
        req, Task025ValidResult(Decimal('0.01'), Decimal('0.01'))
    )
    if hasattr(result, 'flow_regime'):
        # might be laminar if pre-quantize Re < 2300
        pytest.fail(f"expected blocked result, got success with regime={result.flow_regime}")
    codes = [b.code for b in result.blockers]
    assert 'BL_REGIME_NO_CORRELATION_APPLICABLE' in codes


def test_transition_interval_emits_BL_REGIME_NO_CORRELATION_APPLICABLE() -> None:
    """T1-R2 17 — Re in [2300, 3000) emits transition gap blocker."""
    req = _build_request_for_re(
        Decimal('2650'),
        Decimal('7.0026'),
        ThermalBoundaryCondition.CWT,
    )
    result = compute_tube_side_heat_transfer_coefficient(
        req, Task025ValidResult(Decimal('0.01'), Decimal('0.01'))
    )
    if hasattr(result, 'flow_regime'):
        pytest.fail(f"expected blocked result, got success with regime={result.flow_regime}")
    codes = [b.code for b in result.blockers]
    assert 'BL_REGIME_NO_CORRELATION_APPLICABLE' in codes


def test_re_equals_3000_selects_turbulent() -> None:
    """T1-R2 18 — Re = 3000 selects turbulent regime."""
    # Adjust rho to ensure Re_post = 3000.0 exactly
    mu = Decimal('0.001')
    D_h = Decimal('0.01')
    k = Decimal('0.5984')
    A_total = Decimal('0.01')
    pr = Decimal('7.0026')
    pr * k / mu
    v = Decimal('50.0')
    rho = Decimal('3000') * mu / (v * D_h)
    m_dot = v * rho * A_total
    req = _build_request_for_re(Decimal('3000'), pr, ThermalBoundaryCondition.CWT)
    # Override m_dot to use exact target
    object.__setattr__(req, 'mass_flow_rate_kg_s', m_dot)
    result = compute_tube_side_heat_transfer_coefficient(
        req, Task025ValidResult(A_total, D_h)
    )
    assert hasattr(result, 'flow_regime')
    assert result.flow_regime == FlowRegime.TURBULENT


def test_pr_outside_selected_correlation_emits_BL_CORRELATION_NOT_APPLICABLE() -> None:
    """T1-R2 19 — Pr outside envelope -> BL_CORRELATION_NOT_APPLICABLE."""
    # Re = 5000 (turbulent), Pr = 0.3 (outside 0.5..2000 envelope)
    req = _build_request_for_re(
        Decimal('5000'),
        Decimal('0.3'),
        ThermalBoundaryCondition.CWT,
    )
    result = compute_tube_side_heat_transfer_coefficient(
        req, Task025ValidResult(Decimal('0.01'), Decimal('0.01'))
    )
    if hasattr(result, 'flow_regime'):
        pytest.fail(f"expected blocked result, got success with regime={result.flow_regime}")
    codes = [b.code for b in result.blockers]
    assert 'BL_CORRELATION_NOT_APPLICABLE' in codes


def test_cwt_vs_chf_selection_by_thermal_boundary() -> None:
    """T1-R2 20 — CWT vs CHF selects the right laminar constant."""
    mu = Decimal('0.001')
    D_h = Decimal('0.01')
    Decimal('0.5984')
    A_total = Decimal('0.01')
    Decimal('4190.35584')
    rho = Decimal('499.0020') * mu / (Decimal('0.0500898') * D_h)
    m_dot = Decimal('0.0500898') * rho * A_total
    # Build CWT request directly with the right thermal boundary.
    req_cwt = _build_request_for_re(
        Decimal('499.0020'), Decimal('7.0026'), ThermalBoundaryCondition.CWT
    )
    # The helper picks m_dot internally; for the exact target we replace via
    # direct construction (frozen dataclass; object.__setattr__ is required).
    object.__setattr__(req_cwt, 'mass_flow_rate_kg_s', m_dot)
    r1 = compute_tube_side_heat_transfer_coefficient(
        req_cwt, Task025ValidResult(A_total, D_h)
    )
    if not hasattr(r1, 'correlation_id'):
        # Pipeline may have blocked; surface blocker codes for diagnosis.
        codes = [b.code for b in r1.blockers]
        pytest.fail(f"expected success, got blockers: {codes}")
    assert r1.correlation_id == 'tube_laminar_cwt'
    assert r1.nusselt_number == Decimal('3.6600')

    req_chf = _build_request_for_re(
        Decimal('499.0020'), Decimal('7.0026'), ThermalBoundaryCondition.CHF
    )
    object.__setattr__(req_chf, 'mass_flow_rate_kg_s', m_dot)
    r2 = compute_tube_side_heat_transfer_coefficient(
        req_chf, Task025ValidResult(A_total, D_h)
    )
    if not hasattr(r2, 'correlation_id'):
        codes = [b.code for b in r2.blockers]
        pytest.fail(f"expected success, got blockers: {codes}")
    assert r2.correlation_id == 'tube_laminar_chf'
    assert r2.nusselt_number == Decimal('4.3600')
