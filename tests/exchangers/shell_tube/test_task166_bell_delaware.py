"""Focused production tests for the TASK-166 Bell--Delaware authority.

The request fixture is a structural projection of accepted upstream
evidence.  It deliberately contains no substitute h/pressure-drop values;
the production service derives Bell-specific geometry and both rating
surfaces from the declared inputs.
"""

from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, getcontext, localcontext
from enum import Enum
from typing import cast

import pytest

from hexagent.exchangers.shell_tube.bell_delaware import authority, validate_request
from hexagent.exchangers.shell_tube.bell_delaware.decimal_math import engineering_context
from hexagent.exchangers.shell_tube.bell_delaware.errors import BlockerCode
from hexagent.exchangers.shell_tube.bell_delaware.models import Task166Result, ValidationStatus
from hexagent.exchangers.shell_tube.bell_delaware.raw_projection import (
    RawProjectionFailure,
    project_raw,
)


def _identity(case_id: str = "case-166") -> dict[str, str]:
    return {
        "physical_exchanger_case_id": case_id,
        "result_hash": "sha256:" + case_id + "-hash",
        "result_id": "id-" + case_id,
        "status": "VALID",
    }


def _request(
    *,
    layout: str = "LAYOUT_30_DEG",
    reynolds: str = "1000",
    baffle_count: object = 5,
    inlet_spacing: str = "0.2",
    outlet_spacing: str = "0.2",
) -> dict[str, object]:
    identity = _identity()
    return {
        "schema_version": authority.REQUEST_SCHEMA_VERSION,
        "task166_version": "1.0",
        "source_definition_id": authority.SOURCE_DEFINITION_ID,
        "task020_configuration": {
            **identity,
            "construction_family": "FIXED_TUBESHEET",
            "shell_type": "TEMA_E",
            "shell_pass_count": 1,
        },
        "tube_layout": {
            **identity,
            "layout_id": "layout-166",
            "layout_angle": layout,
            "tube_outer_diameter_m": "0.025",
            "tube_pitch_m": "0.030",
            "tube_count": "100",
        },
        "shell_bundle_geometry": {
            **identity,
            "shell_inside_diameter_m": "1",
            "bundle_outer_diameter_m": "0.9",
            "shell_to_bundle_diametral_clearance_m": "0.05",
        },
        "baffle_geometry": {
            **identity,
            "baffle_type": "SINGLE_SEGMENTAL",
            "baffle_cut_fraction": "0.25",
            "baffle_count": baffle_count,
            "central_baffle_spacing_m": "0.2",
            "inlet_baffle_spacing_m": inlet_spacing,
            "outlet_baffle_spacing_m": outlet_spacing,
            "shell_to_baffle_diametral_clearance_m": "0.003",
            "tube_to_baffle_hole_diametral_clearance_m": "0.002",
        },
        "shell_side_hydraulic_geometry": {
            **identity,
            "central_crossflow_flow_area_m2": "0.0325",
        },
        "shell_side_flow_state": {
            **identity,
            "phase": "SINGLE_PHASE_LIQUID",
            "rheology": "NEWTONIAN",
            "shell_side_reynolds_number": reynolds,
            "shell_side_prandtl_number": "4",
            "shell_side_mass_velocity_kg_m2_s": "20",
            "shell_side_mass_flow_rate_kg_s": "0.78",
        },
        "shell_side_flow_state_request": {
            "property_snapshot": {
                "density_kg_m3": "1000",
                "dynamic_viscosity_pa_s": "0.001",
                "specific_heat_capacity_j_kg_k": "4200",
            },
            "mass_flow_authority": {
                "shell_side_mass_flow_rate_kg_s": "0.78",
            },
        },
        "request_metadata": (("case", "166"),),
    }


def _codes(outcome: object) -> set[BlockerCode]:
    branch = getattr(outcome, "typed_blocked", None) or getattr(
        outcome, "raw_boundary_blocked", None
    )
    return set() if branch is None else {item.code for item in branch.blockers}


def _valid(raw: dict[str, object]) -> Task166Result:
    outcome = validate_request(raw)
    assert outcome.status is ValidationStatus.VALID
    assert outcome.valid is not None
    return outcome.valid


def _reverse_records(value: object) -> object:
    if type(value) is dict:
        return {key: _reverse_records(item) for key, item in reversed(tuple(value.items()))}
    if type(value) is list:
        return [_reverse_records(item) for item in value]
    if type(value) is tuple:
        return tuple(_reverse_records(item) for item in value)
    return value


def test_valid_result_contains_full_heat_transfer_and_pressure_surfaces() -> None:
    result = _valid(_request())
    assert result.corrected_shell_side_heat_transfer_coefficient > Decimal("0")
    assert all(
        value > Decimal("0")
        for value in (result.j_c, result.j_l, result.j_b, result.j_s, result.j_r)
    )
    assert result.bell_geometry is not None
    with localcontext(engineering_context()):
        assert result.j_c == Decimal("0.55") + Decimal("0.72") * (
            result.bell_geometry.pure_crossflow_tube_fraction
        )
    with localcontext(engineering_context()):
        assert result.total_shell_pressure_drop == (
            result.crossflow_pressure_drop
            + result.window_pressure_drop
            + result.end_zone_pressure_drop
        )
    assert result.provenance is not None
    assert result.provenance.self_edge_count == 0
    assert result.provenance.cycle_count == 0
    assert result.applicability is not None
    assert result.applicability.status.value == "APPLICABLE"
    assert result.completeness is not None
    assert result.completeness.status == "COMPLETE"


@pytest.mark.parametrize("layout", ["LAYOUT_30_DEG", "LAYOUT_45_DEG", "LAYOUT_90_DEG"])
@pytest.mark.parametrize("reynolds", ["1", "10", "100", "1000", "100000"])
def test_parameter_rows_and_layouts_are_explicitly_selected(layout: str, reynolds: str) -> None:
    result = _valid(_request(layout=layout, reynolds=reynolds))
    assert result.heat_transfer_parameter_row_identity.startswith(layout + ":")
    assert result.pressure_drop_parameter_row_identity.startswith(layout + ":")
    assert result.factor_evidence


def test_js_has_exact_uniform_spacing_limit() -> None:
    result = _valid(_request(inlet_spacing="0.2", outlet_spacing="0.2"))
    assert result.j_s == Decimal("1")


@pytest.mark.parametrize("reynolds", ["99", "100"])
def test_js_uses_authoritative_reynolds_branch(reynolds: str) -> None:
    result = _valid(_request(reynolds=reynolds, inlet_spacing="0.15", outlet_spacing="0.25"))
    assert result.j_s != Decimal("1")
    assert result.j_s > Decimal("0")


def test_unequal_end_zone_terms_are_source_decomposed() -> None:
    result = _valid(_request(inlet_spacing="0.15", outlet_spacing="0.25"))
    with localcontext(engineering_context()):
        assert result.entrance_zone_contribution + result.exit_zone_contribution == (
            result.end_zone_pressure_drop
        )
    assert result.entrance_zone_contribution != result.exit_zone_contribution


def test_identity_binding_is_required_across_upstream_records() -> None:
    raw = _request()
    tube_layout = cast(dict[str, object], raw["tube_layout"])
    raw["tube_layout"] = {**tube_layout, "physical_exchanger_case_id": "other"}
    outcome = validate_request(raw)
    assert outcome.status is ValidationStatus.TYPED_BLOCKED
    assert BlockerCode.UPSTREAM_CASE_BINDING_MISMATCH in _codes(outcome)


def test_missing_bell_geometry_fails_closed() -> None:
    raw = _request()
    baffle = dict(cast(dict[str, object], raw["baffle_geometry"]))
    del baffle["tube_to_baffle_hole_diametral_clearance_m"]
    raw["baffle_geometry"] = baffle
    outcome = validate_request(raw)
    assert outcome.status is ValidationStatus.TYPED_BLOCKED
    assert BlockerCode.REQUIRED_GEOMETRY_MISSING in _codes(outcome)


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("phase", "TWO_PHASE", BlockerCode.PHASE_UNSUPPORTED),
        ("rheology", "NON_NEWTONIAN", BlockerCode.RHEOLOGY_UNSUPPORTED),
    ],
)
def test_unsupported_flow_envelope_is_blocked(
    field: str, value: str, expected: BlockerCode
) -> None:
    raw = _request()
    flow = dict(cast(dict[str, object], raw["shell_side_flow_state"]))
    flow[field] = value
    raw["shell_side_flow_state"] = flow
    outcome = validate_request(raw)
    assert outcome.status is ValidationStatus.TYPED_BLOCKED
    assert expected in _codes(outcome)


def test_unsupported_configuration_and_layout_do_not_fallback_to_kern() -> None:
    raw = _request()
    config = dict(cast(dict[str, object], raw["task020_configuration"]))
    config["shell_type"] = "TEMA_F"
    raw["task020_configuration"] = config
    outcome = validate_request(raw)
    assert outcome.status is ValidationStatus.TYPED_BLOCKED
    assert BlockerCode.SHELL_TYPE_UNSUPPORTED in _codes(outcome)

    layout_case = validate_request(_request(layout="LAYOUT_15_DEG"))
    assert layout_case.status is ValidationStatus.TYPED_BLOCKED
    assert BlockerCode.TUBE_LAYOUT_UNSUPPORTED in _codes(layout_case)


@pytest.mark.parametrize("construction_family", ["FIXED_TUBESHEET", "U_TUBE", "FLOATING_HEAD"])
def test_v06_construction_family_applicability_does_not_add_formula_branches(
    construction_family: str,
) -> None:
    raw = _request()
    config = dict(cast(dict[str, object], raw["task020_configuration"]))
    config["construction_family"] = construction_family
    raw["task020_configuration"] = config

    result = _valid(raw)
    assert result.corrected_shell_side_heat_transfer_coefficient > Decimal("0")
    assert result.total_shell_pressure_drop > Decimal("0")
    assert result.bell_geometry is not None
    assert result.applicability is not None
    assert result.applicability.status.value == "APPLICABLE"


def test_unsupported_construction_family_remains_fail_closed() -> None:
    raw = _request()
    config = dict(cast(dict[str, object], raw["task020_configuration"]))
    config["construction_family"] = "SPLIT_RING"
    raw["task020_configuration"] = config

    outcome = validate_request(raw)
    assert outcome.status is ValidationStatus.TYPED_BLOCKED
    assert BlockerCode.CONFIGURATION_UNSUPPORTED in _codes(outcome)


@pytest.mark.parametrize("baffle_count", [0, 1, True, 2.5, "2"])
def test_invalid_baffle_counts_are_not_coerced(baffle_count: object) -> None:
    outcome = validate_request(_request(baffle_count=baffle_count))
    assert outcome.status is not ValidationStatus.VALID
    assert BlockerCode.INVALID_GEOMETRY_DOMAIN in _codes(
        outcome
    ) or BlockerCode.UNSUPPORTED_RAW_VALUE in _codes(outcome)


def test_baffle_count_above_two_is_supported_without_clamping() -> None:
    result = _valid(_request(baffle_count=6))
    assert result.bell_geometry is not None
    assert result.bell_geometry.baffle_count == 6


def test_source_definition_mismatch_is_typed_blocked() -> None:
    raw = _request()
    raw["source_definition_id"] = "wrong-source"
    outcome = validate_request(raw)
    assert outcome.status is ValidationStatus.TYPED_BLOCKED
    assert BlockerCode.SOURCE_DEFINITION_MISMATCH in _codes(outcome)


def test_raw_boundary_rejects_float_custom_objects_and_surrogates() -> None:
    float_outcome = validate_request({"value": 1.25})
    assert float_outcome.status is ValidationStatus.RAW_BOUNDARY_BLOCKED
    assert BlockerCode.UNSUPPORTED_RAW_VALUE in _codes(float_outcome)

    class Hostile:
        def __repr__(self) -> str:
            raise AssertionError("repr must not be called")

        def __str__(self) -> str:
            raise AssertionError("str must not be called")

    hostile_outcome = validate_request(Hostile())
    assert hostile_outcome.status is ValidationStatus.RAW_BOUNDARY_BLOCKED
    assert BlockerCode.UNSUPPORTED_RAW_VALUE in _codes(hostile_outcome)

    surrogate = _request()
    surrogate["request_metadata"] = (("bad\ud800", "value"),)
    surrogate_outcome = validate_request(surrogate)
    assert surrogate_outcome.status is ValidationStatus.RAW_BOUNDARY_BLOCKED
    assert BlockerCode.RAW_UNICODE_ENCODING_FAILURE in _codes(surrogate_outcome)


def test_raw_limits_are_bounded() -> None:
    too_many = {"items": list(range(authority.RAW_MAX_NODES + 1))}
    outcome = validate_request(too_many)
    assert outcome.status is ValidationStatus.RAW_BOUNDARY_BLOCKED
    assert BlockerCode.RAW_NODE_LIMIT_EXCEEDED in _codes(outcome)

    deep: dict[str, object] = {}
    cursor: dict[str, object] = deep
    for _index in range(authority.RAW_MAX_DEPTH + 2):
        cursor["next"] = {}
        cursor = cast(dict[str, object], cursor["next"])
    outcome = validate_request(deep)
    assert outcome.status is ValidationStatus.RAW_BOUNDARY_BLOCKED
    assert BlockerCode.RAW_DEPTH_LIMIT_EXCEEDED in _codes(outcome)

    outcome = validate_request({"value": "x" * (authority.RAW_MAX_SCALAR_BYTES + 1)})
    assert outcome.status is ValidationStatus.RAW_BOUNDARY_BLOCKED
    assert BlockerCode.RAW_SCALAR_BYTE_LIMIT_EXCEEDED in _codes(outcome)


class _CustomEnum(Enum):
    VALUE = "value"


def test_raw_projection_does_not_execute_custom_enum_behavior() -> None:
    with pytest.raises(RawProjectionFailure):
        project_raw(_CustomEnum.VALUE)


def test_canonical_identity_is_mapping_order_and_ambient_context_invariant() -> None:
    raw = _request()
    baseline = _valid(raw)
    permuted = _reverse_records(deepcopy(raw))
    assert isinstance(permuted, dict)
    reordered = _valid(permuted)
    assert reordered.request_hash == baseline.request_hash
    assert reordered.result_hash == baseline.result_hash
    assert reordered.result_id == baseline.result_id

    with localcontext(getcontext()) as context:
        context.prec = 6
        context.rounding = "ROUND_DOWN"
        altered_context = _valid(_request())
    assert altered_context.result_hash == baseline.result_hash
    assert altered_context.result_id == baseline.result_id


def test_source_roles_keep_bell_separate_from_legacy_kern_authority() -> None:
    assert authority.PRIMARY_IMPLEMENTATION_SOURCE_ID.startswith("SRC-AICHE")
    assert authority.JAMIL_PARAMETER_SOURCE_ID != authority.PRIMARY_IMPLEMENTATION_SOURCE_ID
    assert authority.SAIF_TARIQ_JS_SOURCE_ID != authority.PRIMARY_IMPLEMENTATION_SOURCE_ID
    assert authority.SOURCE_CONFLICT_POLICY == "FAIL_CLOSED"
    assert authority.PSI_N_REQUIRED_BY_TASK166 is False
