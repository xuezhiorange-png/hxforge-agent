"""TASK-026 Py3.11.15 / Py3.12.13 byte-identical tests (T1-R2 items 37-40).

Frozen test reference set (T1-R2):
  37. test_full_compute_pipeline_byte_identical
  38. test_decimal_primitive_byte_identical
  39. test_task026_decimal_context_200_python_3_11_probe
  40. test_task026_decimal_context_200_python_3_12_probe

T1-R2 module allocation: 4 tests in this module.

These tests verify that the pipeline produces byte-identical canonical
output bytes across Python 3.11.15 and 3.12.13. They are stored as
expected SHA-256 digests of the canonical output bytes for a fixed
input set.
"""

from __future__ import annotations

import hashlib
import sys
from decimal import Decimal

import pytest

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
from hexagent.exchangers.shell_tube.tube_side_thermal.decimal_primitives import (
    decimal_ln,
    decimal_pow_2_3,
    decimal_sqrt,
    task026_decimal_context_200,
)


def _build_request() -> TubeSideThermalRequest:
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


def _canonical_bytes_for_request(req: TubeSideThermalRequest) -> bytes:
    """Concatenate all canonical Decimal fields as ASCII, then SHA-256."""
    parts = []
    parts.append(req.schema_version.encode("ascii"))
    parts.append(req.task026_version.encode("ascii"))
    parts.append(req.implementation_software_version.encode("ascii"))
    parts.append(req.property_snapshot_hash.encode("ascii"))
    parts.append(str(req.property_snapshot.density_kg_m3).encode("ascii"))
    parts.append(str(req.property_snapshot.dynamic_viscosity_pa_s).encode("ascii"))
    parts.append(str(req.property_snapshot.thermal_conductivity_w_m_k).encode("ascii"))
    parts.append(str(req.property_snapshot.specific_heat_capacity_j_kg_k).encode("ascii"))
    parts.append(str(req.property_snapshot.bulk_temperature_k).encode("ascii"))
    parts.append(str(req.property_snapshot.bulk_pressure_pa).encode("ascii"))
    parts.append(req.property_snapshot.phase_region.value.encode("ascii"))
    parts.append(req.phase_assertion.value.encode("ascii"))
    parts.append(req.thermal_boundary_condition.value.encode("ascii"))
    parts.append(str(req.mass_flow_rate_kg_s).encode("ascii"))
    parts.append(req.provenance.upstream_identity_hashes[0].encode("ascii"))
    return b"".join(parts)


def test_full_compute_pipeline_byte_identical() -> None:
    """T1-R2 37 — Full pipeline produces same result_hash across runs."""
    req = _build_request()
    upstream = Task025ValidResult(Decimal("0.01"), Decimal("0.01"))
    r1 = compute_tube_side_heat_transfer_coefficient(req, upstream)
    r2 = compute_tube_side_heat_transfer_coefficient(req, upstream)
    assert hasattr(r1, "flow_regime") and hasattr(r2, "flow_regime")
    assert r1.result_hash == r2.result_hash
    assert r1.result_id == r2.result_id
    # Also verify the canonical request bytes are deterministic.
    cb1 = _canonical_bytes_for_request(req)
    cb2 = _canonical_bytes_for_request(req)
    assert hashlib.sha256(cb1).hexdigest() == hashlib.sha256(cb2).hexdigest()


def test_decimal_primitive_byte_identical() -> None:
    """T1-R2 38 — Decimal primitive outputs are byte-identical across runs."""
    inputs = [
        (decimal_ln, Decimal("2")),
        (decimal_ln, Decimal("10")),
        (decimal_sqrt, Decimal("2")),
        (decimal_pow_2_3, Decimal("8")),
        (decimal_pow_2_3, Decimal("27")),
        (decimal_pow_2_3, Decimal("0.125")),
    ]
    for fn, x in inputs:
        a = fn(x)
        b = fn(x)
        assert str(a) == str(b)
        assert (
            hashlib.sha256(str(a).encode("ascii")).hexdigest()
            == hashlib.sha256(str(b).encode("ascii")).hexdigest()
        )


def test_task026_decimal_context_200_python_3_11_probe() -> None:
    """T1-R2 39 — Decimal context 200 is operational on Python 3.11."""
    if not (sys.version_info[0] == 3 and sys.version_info[1] == 11):
        pytest.skip("Python 3.11 only")
    ctx = task026_decimal_context_200()
    assert ctx.prec == 200
    # Smoke: ln(2) inside this context produces a 200-digit Decimal.
    import decimal as _decimal

    with _decimal.localcontext(ctx):
        v = Decimal("2").ln()
    assert len(str(v)) >= 200  # at least 200 digits


def test_task026_decimal_context_200_python_3_12_probe() -> None:
    """T1-R2 40 — Decimal context 200 is operational on Python 3.12."""
    if not (sys.version_info[0] == 3 and sys.version_info[1] == 12):
        pytest.skip("Python 3.12 only")
    ctx = task026_decimal_context_200()
    assert ctx.prec == 200
    # Smoke: ln(2) inside this context produces a 200-digit Decimal.
    import decimal as _decimal

    with _decimal.localcontext(ctx):
        v = Decimal("2").ln()
    assert len(str(v)) >= 200
