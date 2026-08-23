"""Frozen twelve-vector registry and representative oracle checks."""

from dataclasses import replace
from decimal import Decimal

from hexagent.exchangers.shell_tube.shell_side_flow_state import validate_request
from hexagent.exchangers.shell_tube.shell_side_flow_state.canonical import (
    mass_flow_authority_hash,
)
from hexagent.exchangers.shell_tube.shell_side_flow_state.formulas import evaluate_raw
from hexagent.exchangers.shell_tube.shell_side_flow_state.models import BlockerCode
from hexagent.exchangers.shell_tube.shell_side_flow_state.schema import parse_request
from hexagent.exchangers.shell_tube.tube_side_thermal import (
    PhaseRegion,
    recompute_property_snapshot_hash,
)

from . import copy_request

VECTOR_IDS = (
    "V01_VALID_SINGLE_PHASE_LIQUID",
    "V02_VALID_SINGLE_PHASE_GAS",
    "V03_ZERO_MASS_FLOW_BLOCKED",
    "V04_NEGATIVE_MASS_FLOW_BLOCKED",
    "V05_PROPERTY_HASH_MISMATCH",
    "V06_MASS_FLOW_AUTHORITY_HASH_MISMATCH",
    "V07_TASK031_GEOMETRY_IDENTITY_MISMATCH",
    "V08_SAME_CASE_BINDING_MISMATCH",
    "V09_NON_NEWTONIAN_RHEOLOGY_BLOCKED",
    "V10_UNSUPPORTED_FLOW_MODEL_BLOCKED",
    "V11_PUBLIC_QUANTIZATION_COLLISION",
    "V12_HIGH_PRECISION_OPERATION_ORDER",
)


def test_t032_vec_001_external_12_vector_registry_and_oracles() -> None:
    assert len(VECTOR_IDS) == 12
    valid = validate_request(copy_request())
    assert valid.flow_state is not None
    assert valid.flow_state.shell_side_mass_velocity_kg_m2_s == Decimal("20.0000000")

    raw = copy_request()
    raw["property_snapshot"]["phase_region"] = "SINGLE_PHASE_GAS"
    liquid_request = parse_request(copy_request())
    gas_snapshot = replace(
        liquid_request.property_snapshot,
        phase_region=PhaseRegion.SINGLE_PHASE_GAS,
    )
    gas_hash = recompute_property_snapshot_hash(gas_snapshot)
    raw["property_snapshot"]["property_snapshot_hash"] = gas_hash
    raw["property_snapshot_hash"] = gas_hash
    raw["mass_flow_authority"]["property_snapshot_hash"] = gas_hash
    gas_authority = replace(
        liquid_request.mass_flow_authority,
        property_snapshot_hash=gas_hash,
    )
    raw["mass_flow_authority"]["authority_hash"] = mass_flow_authority_hash(gas_authority)
    gas = validate_request(raw)
    assert gas.flow_state is not None
    assert gas.flow_state.phase_region.value == "SINGLE_PHASE_GAS"

    for value, expected_code in (
        ("0.0000000", BlockerCode.SSFS_MASS_FLOW_NON_POSITIVE),
        ("-1.0000000", BlockerCode.SSFS_MASS_FLOW_NON_POSITIVE),
    ):
        request = parse_request(copy_request())
        authority = replace(request.mass_flow_authority, mass_flow_rate_kg_s=Decimal(value))
        mutated = copy_request()
        mutated["mass_flow_authority"]["mass_flow_rate_kg_s"] = value
        mutated["mass_flow_authority"]["authority_hash"] = mass_flow_authority_hash(authority)
        result = validate_request(mutated)
        assert result.blockers[0].code == expected_code

    high_precision = evaluate_raw(
        mass_flow_rate=Decimal("2.0000000000000000000000000001"),
        flow_area=Decimal("0.1000000000000000000000000003"),
        hydraulic_diameter=Decimal("0.0200000000000000000000000001"),
        density=Decimal("998.2000000000000000000000000002"),
        dynamic_viscosity=Decimal("0.0010020000000000000000000001"),
        specific_heat_capacity=Decimal("4182.0000000000000000000000000001"),
        thermal_conductivity=Decimal("0.5980000000000000000000000001"),
    )
    assert high_precision.mass_velocity > 0
    assert high_precision.bulk_velocity > 0
