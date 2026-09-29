"""TASK172 local wall/film closure using the reviewed native component APIs."""

from __future__ import annotations

import math
import sys
from dataclasses import fields
from decimal import Decimal, localcontext
from typing import Any, cast

import numpy as np
from pydantic import ValidationError
from scipy.optimize import least_squares

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.bell_delaware.heat_transfer import calculate_heat_transfer
from hexagent.exchangers.shell_tube.bell_delaware.models import BellGeometry
from hexagent.exchangers.shell_tube.overall_heat_transfer_resistance.engineering import (
    compute_wall_resistance,
)
from hexagent.exchangers.shell_tube.shell_side_flow_state.formulas import (
    evaluate_raw as evaluate_shell_flow_raw,
)
from hexagent.exchangers.shell_tube.tube_side_thermal import (
    FlowRegime,
    ThermalBoundaryCondition,
    check_pr_envelope,
    compute_single_phase,
    recompute_property_snapshot_hash,
)
from hexagent.exchangers.shell_tube.tube_side_thermal import (
    PhaseRegion as Task026PhaseRegion,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.property_snapshot import PropertySnapshot
from hexagent.properties.base import (
    FluidIdentifier,
    FluidState,
    PhaseRegion,
    PropertyProvider,
    ReferenceStatePolicy,
)
from hexagent.properties.coolprop_provider import CoolPropProvider

from .models import (
    COOLPROP_GIT_REVISION,
    COOLPROP_VERSION,
    MATERIAL_SOURCE_SHA256,
    PROFILE_ID,
    TASK172_IMPLEMENTATION_VERSION,
    TASK172_REQUEST_SCHEMA,
    TASK172_RESULT_SCHEMA,
    TOTAL_PARALLEL_FLOW_AREA_M2,
    TUBE_ID_M,
    TUBE_OD_M,
    WALL_CONDUCTIVITY_W_M_K,
    Task172BlockedResult,
    Task172LocalOutcome,
    Task172LocalRequest,
    Task172LocalResult,
)

_T_MIN = Decimal("298.15")
_T_MAX = Decimal("300.00")
_P_MIN = Decimal("100000")
_P_MAX = Decimal("101325")
_TUBE_C3_RE_MIN = Decimal("3000")
_TUBE_C3_RE_MAX = Decimal("5000000")
_PR_MIN = Decimal("0.5")
_PR_MAX = Decimal("2000")
_PR_RATIO_MIN = Decimal("0.05")
_PR_RATIO_MAX = Decimal("20")
_C3_EXPONENT = Decimal("0.11")
_JMU_EXPONENT = Decimal("0.14")
_C_ROUND = 1.0
_CALLBACK_CAP = 24
_NUMERICAL_PROFILE_ID = "R94_R98_STAGE1_CASE_PROFILE_CROUND_1.0"
_TASK026_PROPERTY_SOURCE_ID = "CoolProp::HEOS::Water"
_TASK026_PROPERTY_SOURCE_VERSION = f"{COOLPROP_VERSION}+{COOLPROP_GIT_REVISION}"
_EVIDENCE_REFS = (
    "docs/tasks/evidence/TASK-172-stage1-pre-runtime-authority-bundle-r1.json",
    "docs/tasks/evidence/TASK-172-stage1-independent-review-r1.json",
    "docs/tasks/evidence/TASK-172-r119d-case-bound-task171-native-materialization-r1.json",
)


class _RuntimeFailure(Exception):
    def __init__(self, code: str, field_path: str) -> None:
        super().__init__(code)
        self.code = code
        self.field_path = field_path


def _decimal(value: Decimal) -> str:
    if type(value) is not Decimal or not value.is_finite():
        raise TypeError("canonical TASK172 projections accept finite Decimal values only")
    return str(value)


def _bell_geometry_projection(geometry: BellGeometry) -> dict[str, str | int | list[str]]:
    if type(geometry) is not BellGeometry:
        raise TypeError("TASK172 requires the exact native TASK166 BellGeometry")
    projected: dict[str, str | int | list[str]] = {}
    for field in fields(BellGeometry):
        value = getattr(geometry, field.name)
        if type(value) is Decimal:
            projected[field.name] = _decimal(value)
        elif type(value) is int or type(value) is str:
            projected[field.name] = value
        elif type(value) is tuple and all(type(item) is str for item in value):
            projected[field.name] = list(cast(tuple[str, ...], value))
        else:
            raise TypeError(f"unsupported native BellGeometry field type: {field.name}")
    return projected


def _request_projection(request: Task172LocalRequest) -> dict[str, Any]:
    support = request.support
    tube = request.tube_bulk_state
    shell = request.shell_bulk_state
    shell_flow = request.shell_flow_authority
    task031 = shell_flow.task031_geometry
    task166 = shell_flow.task166_result
    bell_geometry = task166.bell_geometry
    if bell_geometry is None:
        raise TypeError("validated TASK166 result must carry BellGeometry")
    return {
        "schema_version": TASK172_REQUEST_SCHEMA,
        "case_id": request.case_id,
        "case_revision_id": request.case_revision_id,
        "topology": request.topology.model_dump(mode="json"),
        "support": {
            "physical_segment_id": support.physical_segment_id,
            "physical_segment_start_m": _decimal(support.physical_segment_start_m),
            "physical_segment_end_m": _decimal(support.physical_segment_end_m),
            "support_start_m": _decimal(support.support_start_m),
            "support_end_m": _decimal(support.support_end_m),
            "subdivisions_per_physical_interval_per_side": (
                support.subdivisions_per_physical_interval_per_side
            ),
            "subdivision_index": support.subdivision_index,
            "mesh_level_identity": support.mesh_level_identity,
            "tube_cell_id": support.tube_cell_id,
            "shell_cell_id": support.shell_cell_id,
            "wall_interface_id": support.wall_interface_id,
            "inside_area_m2": _decimal(support.inside_area_m2),
            "outside_area_m2": _decimal(support.outside_area_m2),
        },
        "tube_bulk_state": {
            "temperature_k": _decimal(tube.temperature_k),
            "pressure_pa": _decimal(tube.pressure_pa),
        },
        "shell_bulk_state": {
            "temperature_k": _decimal(shell.temperature_k),
            "pressure_pa": _decimal(shell.pressure_pa),
        },
        "tube_mass_flow_kg_s": _decimal(request.tube_mass_flow_kg_s),
        "shell_mass_flow_kg_s": _decimal(request.shell_mass_flow_kg_s),
        "property_profile_id": request.property_profile_id,
        "property_profile_canonical_hash": request.property_profile_canonical_hash,
        "r94_model_profile_canonical_hash": request.r94_model_profile_canonical_hash,
        "r98_overlay_canonical_hash": request.r98_overlay_canonical_hash,
        "stage1_authority_evidence_canonical_hash": (
            request.stage1_authority_evidence_canonical_hash
        ),
        "shell_jmu_model_authority_canonical_hash": (
            request.shell_jmu_model_authority_canonical_hash
        ),
        "shell_flow_authority": {
            "task031_geometry_id": task031.geometry_id,
            "task031_geometry_hash": task031.geometry_hash,
            "task031_crossflow_area_m2": task031.central_crossflow_flow_area_m2,
            "task031_equivalent_hydraulic_diameter_m": (
                task031.shell_side_equivalent_hydraulic_diameter_m
            ),
            "task166_result_id": task166.result_id,
            "task166_result_hash": task166.result_hash,
            "bell_geometry": _bell_geometry_projection(bell_geometry),
        },
        "material_source_sha256": request.material_source_sha256,
        "clean_wall_authority_hash": request.clean_wall_authority_hash,
        "cylindrical_mapping_hash": request.cylindrical_mapping_hash,
        "tube_inside_fouling_m2_k_w": _decimal(request.tube_inside_fouling_m2_k_w),
        "shell_outside_fouling_m2_k_w": _decimal(request.shell_outside_fouling_m2_k_w),
    }


def _result_projection(fields: dict[str, Any]) -> dict[str, Any]:
    omitted = {
        "schema_version",
        "status",
        "request_hash",
        "result_hash",
        "result_id",
        "warnings",
        "blockers",
    }
    projected: dict[str, Any] = {}
    for key, value in fields.items():
        if key in omitted:
            continue
        if type(value) is Decimal:
            projected[key] = _decimal(value)
        elif type(value) is tuple and all(type(item) is Decimal for item in value):
            projected[key] = [_decimal(item) for item in value]
        elif type(value) is tuple and all(type(item) is str for item in value):
            projected[key] = list(value)
        else:
            projected[key] = value
    return projected


def recompute_task172_request_hash(request: Task172LocalRequest) -> str:
    """Replay the exact canonical request identity without invoking producers."""
    if type(request) is not Task172LocalRequest:
        raise TypeError("request hash replay requires exact Task172LocalRequest")
    return canonical_sha256(_request_projection(request))


def recompute_task172_support_id(request: Task172LocalRequest) -> str:
    """Replay the native TASK172 physical-support identity bound by a request."""
    if type(request) is not Task172LocalRequest:
        raise TypeError("support identity replay requires exact Task172LocalRequest")
    support = request.support
    return canonical_sha256(
        {
            "topology_id": request.topology.topology_id,
            "mesh_identity": request.topology.mesh_identity,
            "physical_ownership_hash": request.topology.physical_ownership_hash,
            "physical_segment_id": support.physical_segment_id,
            "mesh_level_identity": support.mesh_level_identity,
            "subdivisions_per_physical_interval_per_side": (
                support.subdivisions_per_physical_interval_per_side
            ),
            "subdivision_index": support.subdivision_index,
            "support_start_m": _decimal(support.support_start_m),
            "support_end_m": _decimal(support.support_end_m),
            "tube_cell_id": support.tube_cell_id,
            "shell_cell_id": support.shell_cell_id,
            "wall_interface_id": support.wall_interface_id,
        }
    )


def recompute_task172_result_hash(result: Task172LocalResult) -> str:
    """Replay the successful result identity from its closed public fields."""
    if type(result) is not Task172LocalResult:
        raise TypeError("result hash replay requires exact Task172LocalResult")
    fields = result.model_dump(mode="python")
    return canonical_sha256(
        {
            "schema_version": TASK172_RESULT_SCHEMA,
            "request_hash": result.request_hash,
            "result": _result_projection(fields),
        }
    )


def recompute_task172_local_roundoff_bounds(
    request: Task172LocalRequest,
    result: Task172LocalResult,
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    """Replay accepted R98 residual bounds and the published wall-value ULP floor.

    The first three returned values are the existing inner-film, cylindrical
    wall, and outer-film residual operation bounds. The fourth is a
    componentwise inverse-Jacobian bound for both wall temperatures, plus the
    representable spacing of the published values. This diagnostic replay
    does not alter TASK172 physics or result IDs.
    """
    if type(request) is not Task172LocalRequest or type(result) is not Task172LocalResult:
        raise TypeError("roundoff replay requires exact TASK172 request/result models")
    if (
        recompute_task172_request_hash(request) != result.request_hash
        or recompute_task172_result_hash(result) != result.result_hash
        or request.support.tube_cell_id != result.tube_cell_id
        or request.support.shell_cell_id != result.shell_cell_id
        or request.support.wall_interface_id != result.wall_interface_id
        or request.topology.topology_id != result.topology_id
    ):
        raise ValueError("TASK172 result does not bind the supplied request/support")

    q = float(result.signed_q_hot_to_cold_w)
    residuals = tuple(float(value) for value in result.residual_vector_w)
    q_i, q_wall, q_o = (q - residual for residual in residuals)
    g_i = float(result.tube_htc_w_m2_k) * float(request.support.inside_area_m2)
    g_wall = 1.0 / float(result.wall_resistance_k_w)
    g_o = float(result.shell_htc_w_m2_k) * float(request.support.outside_area_m2)
    tube_bulk = float(request.tube_bulk_state.temperature_k)
    shell_bulk = float(request.shell_bulk_state.temperature_k)
    wall_inner = float(result.wall_temperature_inner_k)
    wall_outer = float(result.wall_temperature_outer_k)
    bounds = _c_residual_bounds(
        q,
        q_i,
        q_wall,
        q_o,
        g_i,
        g_wall,
        g_o,
        tube_bulk,
        shell_bulk,
        wall_inner,
        wall_outer,
    )
    outward_bounds = tuple(math.nextafter(value, math.inf) for value in bounds)

    def add_up(left: float, right: float) -> float:
        return math.nextafter(left + right, math.inf)

    def multiply_up(left: float, right: float) -> float:
        return math.nextafter(left * right, math.inf)

    def add_down(left: float, right: float) -> float:
        return max(0.0, math.nextafter(left + right, -math.inf))

    def multiply_down(left: float, right: float) -> float:
        return max(0.0, math.nextafter(left * right, -math.inf))

    def divide_up(numerator: float, denominator: float) -> float:
        return math.nextafter(numerator / denominator, math.inf)

    determinant_lower = add_down(
        add_down(
            multiply_down(g_i, g_wall),
            multiply_down(g_i, g_o),
        ),
        multiply_down(g_wall, g_o),
    )
    if determinant_lower <= 0.0:
        raise ValueError("TASK172 wall conductance Jacobian is not positively invertible")
    inner_numerator_upper = add_up(
        add_up(
            multiply_up(add_up(g_wall, g_o), outward_bounds[0]),
            multiply_up(g_o, outward_bounds[1]),
        ),
        multiply_up(g_wall, outward_bounds[2]),
    )
    outer_numerator_upper = add_up(
        add_up(
            multiply_up(g_wall, outward_bounds[0]),
            multiply_up(g_i, outward_bounds[1]),
        ),
        multiply_up(add_up(g_i, g_wall), outward_bounds[2]),
    )
    temperature_floor = max(
        math.ulp(wall_inner),
        math.ulp(wall_outer),
        divide_up(inner_numerator_upper, determinant_lower),
        divide_up(outer_numerator_upper, determinant_lower),
    )
    temperature_floor = math.nextafter(temperature_floor, math.inf)
    return (
        Decimal(str(outward_bounds[0])),
        Decimal(str(outward_bounds[1])),
        Decimal(str(outward_bounds[2])),
        Decimal(str(temperature_floor)),
    )


def recompute_task172_blocked_result_hash(result: Task172BlockedResult) -> str:
    """Replay the fail-closed result identity without consulting runtime state."""
    if type(result) is not Task172BlockedResult:
        raise TypeError("blocked-result replay requires exact Task172BlockedResult")
    return canonical_sha256(
        {
            "schema_version": "task172.local-constitutive-blocked.v1",
            "failure_code": result.failure_code,
            "field_path": result.field_path,
            "request_hash": result.request_hash,
            "diagnostic_last_iterate": list(result.diagnostic_last_iterate),
        }
    )


def _blocked(
    code: str,
    field_path: str,
    request_hash: str | None,
    diagnostics: tuple[str, ...] = (),
) -> Task172BlockedResult:
    projection = {
        "schema_version": "task172.local-constitutive-blocked.v1",
        "failure_code": code,
        "field_path": field_path,
        "request_hash": request_hash,
        "diagnostic_last_iterate": list(diagnostics),
    }
    digest = canonical_sha256(projection)
    return Task172BlockedResult(
        status="BLOCKED",
        failure_code=code,
        field_path=field_path,
        request_hash=request_hash,
        diagnostic_last_iterate=diagnostics,
        blockers=(code,),
        blocked_result_hash=digest,
    )


def _provider_state(provider: PropertyProvider, temperature: Decimal, pressure: Decimal) -> Any:
    if not _T_MIN <= temperature <= _T_MAX:
        raise _RuntimeFailure(
            "BLOCKED_PROPERTY_TEMPERATURE_DOMAIN_EXIT", "property_state.temperature_k"
        )
    if not _P_MIN <= pressure <= _P_MAX:
        raise _RuntimeFailure("BLOCKED_PROPERTY_PRESSURE_DOMAIN_EXIT", "property_state.pressure_pa")
    try:
        state = provider.state_tp(
            FluidIdentifier("Water", "HEOS"), float(temperature), float(pressure)
        )
    except Exception as exc:
        raise _RuntimeFailure("BLOCKED_PROPERTY_EVALUATION_FAILURE", "property_state") from exc
    provenance = state.provenance
    if (
        type(state) is not FluidState
        or provenance.backend_name != "CoolProp"
        or provenance.backend_version != COOLPROP_VERSION
        or provenance.backend_git_revision != COOLPROP_GIT_REVISION
        or provenance.reference_state_policy is not ReferenceStatePolicy.DEF
    ):
        raise _RuntimeFailure(
            "BLOCKED_PROPERTY_PROVIDER_IDENTITY_MISMATCH", "property_state.provenance"
        )
    if state.phase is not PhaseRegion.LIQUID:
        raise _RuntimeFailure("BLOCKED_PROPERTY_PHASE", "property_state.phase")
    if state.temperature_k != float(temperature) or state.pressure_pa != float(pressure):
        raise _RuntimeFailure("BLOCKED_PROPERTY_STATE_LOCATION_MISMATCH", "property_state")
    numeric_values = (
        state.density_kg_m3,
        state.cp_j_kg_k,
        state.viscosity_pa_s,
        state.conductivity_w_m_k,
        state.enthalpy_j_kg,
    )
    if any(not math.isfinite(value) or value <= 0.0 for value in numeric_values):
        raise _RuntimeFailure("BLOCKED_PROPERTY_FIELD_INVALID", "property_state")
    return state


def _snapshot(
    provider: PropertyProvider,
    request: Task172LocalRequest,
    side: str,
    location_id: str,
    temperature: Decimal,
    pressure: Decimal,
) -> tuple[PropertySnapshot, str, Any]:
    state = _provider_state(provider, temperature, pressure)
    try:
        phase = Task026PhaseRegion.SINGLE_PHASE_LIQUID
        provisional = PropertySnapshot(
            density_kg_m3=Decimal(str(state.density_kg_m3)),
            dynamic_viscosity_pa_s=Decimal(str(state.viscosity_pa_s)),
            thermal_conductivity_w_m_k=Decimal(str(state.conductivity_w_m_k)),
            specific_heat_capacity_j_kg_k=Decimal(str(state.cp_j_kg_k)),
            bulk_temperature_k=temperature,
            bulk_pressure_pa=pressure,
            phase_region=phase,
            property_source_id=_TASK026_PROPERTY_SOURCE_ID,
            property_source_version=_TASK026_PROPERTY_SOURCE_VERSION,
            property_snapshot_hash="0" * 64,
        )
        task026_hash = recompute_property_snapshot_hash(provisional)
        snapshot = PropertySnapshot(
            density_kg_m3=provisional.density_kg_m3,
            dynamic_viscosity_pa_s=provisional.dynamic_viscosity_pa_s,
            thermal_conductivity_w_m_k=provisional.thermal_conductivity_w_m_k,
            specific_heat_capacity_j_kg_k=provisional.specific_heat_capacity_j_kg_k,
            bulk_temperature_k=provisional.bulk_temperature_k,
            bulk_pressure_pa=provisional.bulk_pressure_pa,
            phase_region=provisional.phase_region,
            property_source_id=provisional.property_source_id,
            property_source_version=provisional.property_source_version,
            property_snapshot_hash=task026_hash,
        )
        identity = canonical_sha256(
            {
                "profile_id": request.property_profile_id,
                "case_id": request.case_id,
                "side": side,
                "location_id": location_id,
                "temperature_k": _decimal(temperature),
                "pressure_pa": _decimal(pressure),
                "property_source_id": _TASK026_PROPERTY_SOURCE_ID,
                "property_source_version": _TASK026_PROPERTY_SOURCE_VERSION,
                "backend": "HEOS::Water",
                "backend_version": provider.version,
                "backend_git_revision": provider.git_revision,
                "reference_state": "DEF",
                "task026_property_snapshot_hash": task026_hash,
                "density_kg_m3": _decimal(snapshot.density_kg_m3),
                "specific_heat_capacity_j_kg_k": _decimal(snapshot.specific_heat_capacity_j_kg_k),
                "dynamic_viscosity_pa_s": _decimal(snapshot.dynamic_viscosity_pa_s),
                "thermal_conductivity_w_m_k": _decimal(snapshot.thermal_conductivity_w_m_k),
                "enthalpy_j_kg": str(state.enthalpy_j_kg),
            }
        )
    except _RuntimeFailure:
        raise
    except Exception as exc:
        raise _RuntimeFailure("BLOCKED_PROPERTY_SNAPSHOT_CONSTRUCTION", location_id) from exc
    return snapshot, identity, state


def _tube_base_htc(
    snapshot: PropertySnapshot, mass_flow: Decimal
) -> tuple[Decimal, Decimal, Decimal, str, str]:
    output = compute_single_phase(
        mass_flow,
        snapshot.density_kg_m3,
        snapshot.dynamic_viscosity_pa_s,
        snapshot.thermal_conductivity_w_m_k,
        snapshot.specific_heat_capacity_j_kg_k,
        TOTAL_PARALLEL_FLOW_AREA_M2,
        TUBE_ID_M,
        ThermalBoundaryCondition.CWT,
    )
    if output.flow_regime is not FlowRegime.TURBULENT:
        raise _RuntimeFailure("BLOCKED_TUBE_C3_REGIME_NOT_APPLICABLE", "tube_correlation")
    if not _TUBE_C3_RE_MIN < output.reynolds_number < _TUBE_C3_RE_MAX:
        raise _RuntimeFailure("BLOCKED_TUBE_C3_REYNOLDS_OUT_OF_DOMAIN", "tube_correlation.reynolds")
    if not check_pr_envelope(output.flow_regime, output.prandtl_number):
        raise _RuntimeFailure("BLOCKED_TUBE_C3_PRANDTL_OUT_OF_DOMAIN", "tube_correlation.prandtl")
    return (
        output.tube_side_heat_transfer_coefficient_w_m2_k,
        output.reynolds_number,
        output.prandtl_number,
        output.correlation_id,
        output.correlation_version,
    )


def _shell_base_htc(
    request: Task172LocalRequest,
    snapshot: PropertySnapshot,
    mass_flow: Decimal,
) -> tuple[Decimal, Decimal, Decimal, Any]:
    geometry = request.shell_flow_authority
    task031_geometry = geometry.task031_geometry
    raw_flow = evaluate_shell_flow_raw(
        mass_flow_rate=mass_flow,
        flow_area=Decimal(task031_geometry.central_crossflow_flow_area_m2),
        hydraulic_diameter=Decimal(task031_geometry.shell_side_equivalent_hydraulic_diameter_m),
        density=snapshot.density_kg_m3,
        dynamic_viscosity=snapshot.dynamic_viscosity_pa_s,
        specific_heat_capacity=snapshot.specific_heat_capacity_j_kg_k,
        thermal_conductivity=snapshot.thermal_conductivity_w_m_k,
    )
    mass_velocity = raw_flow.mass_velocity
    reynolds = raw_flow.reynolds
    prandtl = raw_flow.prandtl
    if not Decimal("0") < reynolds <= Decimal("100000"):
        raise _RuntimeFailure(
            "BLOCKED_SHELL_BELL_REYNOLDS_OUT_OF_DOMAIN", "shell_correlation.reynolds"
        )
    if not _PR_MIN <= prandtl <= _PR_MAX:
        raise _RuntimeFailure(
            "BLOCKED_SHELL_BELL_PRANDTL_OUT_OF_DOMAIN", "shell_correlation.prandtl"
        )
    flow = {
        "shell_side_reynolds_number": reynolds,
        "shell_side_prandtl_number": prandtl,
        "shell_side_mass_velocity_kg_m2_s": mass_velocity,
        "property_snapshot": {
            "density_kg_m3": snapshot.density_kg_m3,
            "dynamic_viscosity_pa_s": snapshot.dynamic_viscosity_pa_s,
            "thermal_conductivity_w_m_k": snapshot.thermal_conductivity_w_m_k,
            "specific_heat_capacity_j_kg_k": snapshot.specific_heat_capacity_j_kg_k,
        },
    }
    try:
        bell_geometry = geometry.task166_result.bell_geometry
        if bell_geometry is None:
            raise _RuntimeFailure("BLOCKED_TASK166_GEOMETRY_MISSING", "shell_flow_authority")
        calculation = calculate_heat_transfer(bell_geometry, flow)
    except Exception as exc:
        raise _RuntimeFailure(
            "BLOCKED_SHELL_BELL_CORRELATION_FAILURE", "shell_correlation"
        ) from exc
    return (
        calculation.corrected_shell_side_heat_transfer_coefficient,
        reynolds,
        prandtl,
        calculation,
    )


def _decimal_power(value: Decimal, exponent: Decimal) -> Decimal:
    with localcontext() as context:
        context.prec = 80
        result = value.__pow__(exponent)
    if not result.is_finite() or result <= 0:
        raise _RuntimeFailure("BLOCKED_CORRELATION_NONFINITE", "wall_correction")
    return result


def _c_residual_bounds(
    q_ts: float,
    q_i: float,
    q_wall: float,
    q_o: float,
    g_i: float,
    g_wall: float,
    g_o: float,
    tube_bulk: float,
    shell_bulk: float,
    wall_inner: float,
    wall_outer: float,
) -> tuple[float, float, float]:
    eps = sys.float_info.epsilon
    gamma_1 = eps / (1.0 - eps)
    gamma_2 = 2.0 * eps / (1.0 - 2.0 * eps)
    c = _C_ROUND
    bound_i = c * (
        math.ulp(q_ts)
        + math.ulp(q_i)
        + g_i * (math.ulp(tube_bulk) + math.ulp(wall_inner) + math.ulp(tube_bulk - wall_inner))
        + gamma_2 * abs(q_i)
    )
    bound_wall = c * (
        math.ulp(q_ts)
        + math.ulp(q_wall)
        + g_wall * (math.ulp(wall_inner) + math.ulp(wall_outer) + math.ulp(wall_inner - wall_outer))
        + gamma_1 * abs(q_wall)
    )
    bound_o = c * (
        math.ulp(q_ts)
        + math.ulp(q_o)
        + g_o * (math.ulp(wall_outer) + math.ulp(shell_bulk) + math.ulp(wall_outer - shell_bulk))
        + gamma_2 * abs(q_o)
    )
    return bound_i, bound_wall, bound_o


def _eval_trial(
    request: Task172LocalRequest,
    provider: PropertyProvider,
    tube_bulk_snapshot: PropertySnapshot,
    shell_bulk_snapshot: PropertySnapshot,
    tube_htc_base: Decimal,
    shell_geometry_htc: Decimal,
    wall_resistance: Decimal,
    q_hc: float,
    wall_inner: float,
    wall_outer: float,
) -> dict[str, Any]:
    values = (q_hc, wall_inner, wall_outer)
    if any(not math.isfinite(value) for value in values):
        raise _RuntimeFailure("BLOCKED_NONFINITE_TRIAL", "solver.variables")
    ti = Decimal(str(wall_inner))
    to = Decimal(str(wall_outer))
    support = request.support
    tube_wall, tube_wall_id, _tube_wall_state = _snapshot(
        provider,
        request,
        "TUBE",
        f"{support.wall_interface_id}:TUBE_FLUID_WALL_INTERFACE",
        ti,
        request.tube_bulk_state.pressure_pa,
    )
    shell_wall, shell_wall_id, _shell_wall_state = _snapshot(
        provider,
        request,
        "SHELL",
        f"{support.wall_interface_id}:SHELL_FLUID_WALL_INTERFACE",
        to,
        request.shell_bulk_state.pressure_pa,
    )
    tube_pr_wall = (
        tube_wall.dynamic_viscosity_pa_s
        * tube_wall.specific_heat_capacity_j_kg_k
        / tube_wall.thermal_conductivity_w_m_k
    )
    tube_pr_bulk = (
        tube_bulk_snapshot.dynamic_viscosity_pa_s
        * tube_bulk_snapshot.specific_heat_capacity_j_kg_k
        / tube_bulk_snapshot.thermal_conductivity_w_m_k
    )
    if not _PR_MIN <= tube_pr_wall <= _PR_MAX:
        raise _RuntimeFailure(
            "BLOCKED_TUBE_C3_WALL_PR_OUT_OF_DOMAIN", "tube_correlation.wall_prandtl"
        )
    pr_ratio = tube_pr_bulk / tube_pr_wall
    if not _PR_RATIO_MIN <= pr_ratio <= _PR_RATIO_MAX:
        raise _RuntimeFailure("BLOCKED_TUBE_C3_PR_RATIO_OUT_OF_DOMAIN", "tube_correlation.pr_ratio")
    tube_factor = _decimal_power(pr_ratio, _C3_EXPONENT)
    tube_htc = tube_htc_base * tube_factor

    shell_jmu_ratio = shell_bulk_snapshot.dynamic_viscosity_pa_s / shell_wall.dynamic_viscosity_pa_s
    shell_jmu = _decimal_power(shell_jmu_ratio, _JMU_EXPONENT)
    shell_htc = shell_geometry_htc * shell_jmu

    ai = support.inside_area_m2
    ao = support.outside_area_m2
    h_i = float(tube_htc)
    h_o = float(shell_htc)
    area_i = float(ai)
    area_o = float(ao)
    wall_r = float(wall_resistance)
    if min(h_i, h_o, area_i, area_o, wall_r) <= 0.0:
        raise _RuntimeFailure("BLOCKED_INVALID_CONDUCTANCE", "wall_network")
    g_i = h_i * area_i
    g_wall = 1.0 / wall_r
    g_o = h_o * area_o
    tube_bulk = float(request.tube_bulk_state.temperature_k)
    shell_bulk = float(request.shell_bulk_state.temperature_k)
    q_ts = q_hc  # reviewed effective sign is s_ts=+1 for tube HOT / shell COLD
    q_i = g_i * (tube_bulk - wall_inner)
    q_wall = g_wall * (wall_inner - wall_outer)
    q_o = g_o * (wall_outer - shell_bulk)
    residuals = (q_ts - q_i, q_ts - q_wall, q_ts - q_o)
    if any(not math.isfinite(item) for item in (*residuals, g_i, g_wall, g_o)):
        raise _RuntimeFailure("BLOCKED_NONFINITE_TRIAL", "solver.residual")
    return {
        "residuals": residuals,
        "bounds": _c_residual_bounds(
            q_ts,
            q_i,
            q_wall,
            q_o,
            g_i,
            g_wall,
            g_o,
            tube_bulk,
            shell_bulk,
            wall_inner,
            wall_outer,
        ),
        "tube_htc": tube_htc,
        "shell_htc": shell_htc,
        "tube_wall_snapshot_id": tube_wall_id,
        "shell_wall_snapshot_id": shell_wall_id,
        "tube_pr_wall": tube_pr_wall,
        "shell_jmu": shell_jmu,
        "g_i": g_i,
        "g_wall": g_wall,
        "g_o": g_o,
    }


def _build_valid_result(
    request: Task172LocalRequest,
    request_hash: str,
    support_id: str,
    tube_bulk_id: str,
    shell_bulk_id: str,
    tube_re: Decimal,
    tube_pr: Decimal,
    shell_re: Decimal,
    shell_pr: Decimal,
    tube_corr_id: str,
    tube_corr_version: str,
    final: dict[str, Any],
    solution: tuple[float, float, float],
    solver_status: str,
    nfev: int,
    callback_count: int,
) -> Task172LocalResult:
    q, twi, two = solution
    residuals = cast(tuple[float, float, float], final["residuals"])
    fields: dict[str, Any] = {
        "schema_version": TASK172_RESULT_SCHEMA,
        "implementation_version": TASK172_IMPLEMENTATION_VERSION,
        "status": "VALIDATED",
        "case_id": request.case_id,
        "case_revision_id": request.case_revision_id,
        "topology_id": request.topology.topology_id,
        "task171_result_hash": request.topology.task171_result_hash,
        "task171_mesh_identity": request.topology.mesh_identity,
        "physical_ownership_hash": request.topology.physical_ownership_hash,
        "definition_projection_hash": request.topology.definition_projection_hash,
        "selected_thermal_role_variant": request.topology.selected_variant,
        "thermal_role_selection_authority_id": (
            request.topology.thermal_role_selection_authority_id
        ),
        "physical_support_id": support_id,
        "physical_segment_id": request.support.physical_segment_id,
        "mesh_level_identity": request.support.mesh_level_identity,
        "subdivisions_per_physical_interval_per_side": (
            request.support.subdivisions_per_physical_interval_per_side
        ),
        "subdivision_index": request.support.subdivision_index,
        "tube_cell_id": request.support.tube_cell_id,
        "shell_cell_id": request.support.shell_cell_id,
        "wall_interface_id": request.support.wall_interface_id,
        "tube_bulk_temperature_k": request.tube_bulk_state.temperature_k,
        "shell_bulk_temperature_k": request.shell_bulk_state.temperature_k,
        "tube_property_snapshot_identity": tube_bulk_id,
        "shell_property_snapshot_identity": shell_bulk_id,
        "tube_wall_property_snapshot_identity": final["tube_wall_snapshot_id"],
        "shell_wall_property_snapshot_identity": final["shell_wall_snapshot_id"],
        "tube_htc_w_m2_k": final["tube_htc"],
        "shell_htc_w_m2_k": final["shell_htc"],
        "wall_temperature_inner_k": Decimal(str(twi)),
        "wall_temperature_outer_k": Decimal(str(two)),
        "signed_q_hot_to_cold_w": Decimal(str(q)),
        "inner_film_resistance_k_w": Decimal(str(1.0 / float(final["g_i"]))),
        "wall_resistance_k_w": Decimal(str(1.0 / float(final["g_wall"]))),
        "outer_film_resistance_k_w": Decimal(str(1.0 / float(final["g_o"]))),
        "residual_vector_w": tuple(Decimal(str(value)) for value in residuals),
        "residual_acceptance_state": "PASS_C_RESIDUAL_SPECIFIC_ULP_OPERATION_BOUND",
        "solver_status": solver_status,
        "solver_nfev": nfev,
        "residual_callback_count": callback_count,
        "tube_reynolds_number": tube_re,
        "tube_prandtl_number_bulk": tube_pr,
        "shell_reynolds_number": shell_re,
        "shell_prandtl_number": shell_pr,
        "shell_j_mu": final["shell_jmu"],
        "tube_correlation_id": tube_corr_id,
        "tube_correlation_version": tube_corr_version,
        "shell_correlation_id": "TASK166_BELL_DELAWARE_WITH_REVIEWED_LOCAL_JMU",
        "property_profile_id": PROFILE_ID,
        "property_profile_canonical_hash": request.property_profile_canonical_hash,
        "shell_jmu_model_authority_canonical_hash": (
            request.shell_jmu_model_authority_canonical_hash
        ),
        "material_source_sha256": MATERIAL_SOURCE_SHA256,
        "clean_wall_authority_hash": request.clean_wall_authority_hash,
        "cylindrical_mapping_hash": request.cylindrical_mapping_hash,
        "numerical_profile_id": _NUMERICAL_PROFILE_ID,
        "r94_model_profile_canonical_hash": request.r94_model_profile_canonical_hash,
        "r98_overlay_canonical_hash": request.r98_overlay_canonical_hash,
        "stage1_authority_evidence_canonical_hash": (
            request.stage1_authority_evidence_canonical_hash
        ),
        "request_hash": request_hash,
        "provenance_refs": _EVIDENCE_REFS,
        "warnings": (),
        "blockers": (),
    }
    projected = _result_projection(fields)
    result_hash = canonical_sha256(
        {
            "schema_version": TASK172_RESULT_SCHEMA,
            "request_hash": request_hash,
            "result": projected,
        }
    )
    fields["result_hash"] = result_hash
    fields["result_id"] = f"urn:hxforge:task172:{result_hash}"
    return Task172LocalResult(**fields)


def _solve(request: Task172LocalRequest, provider: PropertyProvider) -> Task172LocalResult:
    if (
        provider.name != "CoolProp"
        or provider.version != COOLPROP_VERSION
        or provider.git_revision != COOLPROP_GIT_REVISION
        or provider.reference_state_policy is not ReferenceStatePolicy.DEF
    ):
        raise _RuntimeFailure("BLOCKED_PROPERTY_PROVIDER_IDENTITY_MISMATCH", "property_provider")

    support = request.support
    support_id = recompute_task172_support_id(request)
    tube_bulk_snapshot, tube_bulk_id, _tube_state = _snapshot(
        provider,
        request,
        "TUBE",
        f"{support.tube_cell_id}:CELL_MEAN",
        request.tube_bulk_state.temperature_k,
        request.tube_bulk_state.pressure_pa,
    )
    shell_bulk_snapshot, shell_bulk_id, _shell_state = _snapshot(
        provider,
        request,
        "SHELL",
        f"{support.shell_cell_id}:CELL_MEAN",
        request.shell_bulk_state.temperature_k,
        request.shell_bulk_state.pressure_pa,
    )
    tube_h_base, tube_re, tube_pr, tube_corr_id, tube_corr_version = _tube_base_htc(
        tube_bulk_snapshot, request.tube_mass_flow_kg_s
    )
    shell_h_base, shell_re, shell_pr, _shell_calculation = _shell_base_htc(
        request, shell_bulk_snapshot, request.shell_mass_flow_kg_s
    )
    try:
        wall_resistance_result = compute_wall_resistance(
            TUBE_ID_M,
            TUBE_OD_M,
            WALL_CONDUCTIVITY_W_M_K,
            support.inside_area_m2,
        )
    except Exception as exc:
        raise _RuntimeFailure("BLOCKED_WALL_RESISTANCE_EVALUATION", "wall_resistance") from exc
    wall_resistance = wall_resistance_result.wall_bundle_conduction_resistance_k_w
    if wall_resistance <= 0:
        raise _RuntimeFailure("BLOCKED_WALL_RESISTANCE_INVALID", "wall_resistance")

    # I1: direct algebraic seed; C3 is evaluated at the bulk state and J_mu is
    # neutral only for initialization. I2 below restores both active corrections.
    tube_bulk_conductance = float(tube_h_base * support.inside_area_m2)
    shell_seed_conductance = float(shell_h_base * support.outside_area_m2)
    delta_t = float(request.tube_bulk_state.temperature_k - request.shell_bulk_state.temperature_k)
    resistance_i_seed = 1.0 / tube_bulk_conductance
    resistance_o_seed = 1.0 / shell_seed_conductance
    resistance_wall = float(wall_resistance)
    q_seed = delta_t / (resistance_i_seed + resistance_wall + resistance_o_seed)
    if q_seed == 0.0 or delta_t == 0.0:
        if delta_t != 0.0:
            raise _RuntimeFailure("BLOCKED_ZERO_DUTY_SEED_INCONSISTENT", "initialization.zero_duty")
        zero_temperature = float(request.tube_bulk_state.temperature_k)
        zero_solution = (0.0, zero_temperature, zero_temperature)
        zero_final = _eval_trial(
            request,
            provider,
            tube_bulk_snapshot,
            shell_bulk_snapshot,
            tube_h_base,
            shell_h_base,
            wall_resistance,
            *zero_solution,
        )
        zero_residuals = cast(tuple[float, float, float], zero_final["residuals"])
        zero_bounds = cast(tuple[float, float, float], zero_final["bounds"])
        if any(
            abs(value) > bound for value, bound in zip(zero_residuals, zero_bounds, strict=True)
        ):
            raise _RuntimeFailure(
                "BLOCKED_ZERO_DUTY_RESIDUAL_ACCEPTANCE", "initialization.zero_duty"
            )
        return _build_valid_result(
            request,
            canonical_sha256(_request_projection(request)),
            support_id,
            tube_bulk_id,
            shell_bulk_id,
            tube_re,
            tube_pr,
            shell_re,
            shell_pr,
            tube_corr_id,
            tube_corr_version,
            zero_final,
            zero_solution,
            "EXACT_ZERO_DUTY_BRANCH",
            0,
            0,
        )
    wall_inner_seed = float(request.tube_bulk_state.temperature_k) - q_seed * resistance_i_seed
    wall_outer_seed = float(request.shell_bulk_state.temperature_k) + q_seed * resistance_o_seed
    if not all(math.isfinite(value) for value in (q_seed, wall_inner_seed, wall_outer_seed)):
        raise _RuntimeFailure("BLOCKED_INITIALIZATION_FAILURE", "initialization.seed")
    if not _T_MIN <= Decimal(str(wall_inner_seed)) <= _T_MAX:
        raise _RuntimeFailure(
            "BLOCKED_INITIALIZATION_STATE_OUT_OF_DOMAIN", "initialization.wall_inner"
        )
    if not _T_MIN <= Decimal(str(wall_outer_seed)) <= _T_MAX:
        raise _RuntimeFailure(
            "BLOCKED_INITIALIZATION_STATE_OUT_OF_DOMAIN", "initialization.wall_outer"
        )

    callback_count = 0
    last_iterate: tuple[float, float, float] = (q_seed, wall_inner_seed, wall_outer_seed)

    def residual(values: np.ndarray) -> np.ndarray:
        nonlocal callback_count, last_iterate
        callback_count += 1
        if callback_count > _CALLBACK_CAP:
            raise _RuntimeFailure("BLOCKED_SOLVER_RESOURCE_EXHAUSTION", "solver.callback_cap")
        q, twi, two = (float(value) for value in values)
        last_iterate = (q, twi, two)
        evaluated = _eval_trial(
            request,
            provider,
            tube_bulk_snapshot,
            shell_bulk_snapshot,
            tube_h_base,
            shell_h_base,
            wall_resistance,
            q,
            twi,
            two,
        )
        return np.asarray(evaluated["residuals"], dtype=float) / abs(q_seed)

    try:
        solver = least_squares(
            residual,
            np.asarray([q_seed, wall_inner_seed, wall_outer_seed], dtype=float),
            method="trf",
            loss="linear",
            ftol=1e-6,
            xtol=1e-12,
            gtol=1e-12,
            jac="2-point",
            diff_step=1e-5,
            x_scale=[abs(q_seed), abs(delta_t), abs(delta_t)],
            max_nfev=6,
            bounds=(
                np.asarray([-np.inf, float(_T_MIN), float(_T_MIN)], dtype=float),
                np.asarray([np.inf, float(_T_MAX), float(_T_MAX)], dtype=float),
            ),
            tr_solver="exact",
            tr_options={},
            f_scale=1.0,
            jac_sparsity=None,
        )
    except _RuntimeFailure:
        raise
    except Exception as exc:
        raise _RuntimeFailure("BLOCKED_SOLVER_FAILURE", "solver") from exc

    solution = tuple(float(value) for value in solver.x)
    q, twi, two = cast(tuple[float, float, float], solution)
    final = _eval_trial(
        request,
        provider,
        tube_bulk_snapshot,
        shell_bulk_snapshot,
        tube_h_base,
        shell_h_base,
        wall_resistance,
        q,
        twi,
        two,
    )
    if not solver.success or solver.nfev > 6 or callback_count > _CALLBACK_CAP:
        raise _RuntimeFailure("BLOCKED_NONCONVERGENCE", "solver.termination")
    residual_values = cast(tuple[float, float, float], final["residuals"])
    bounds = cast(tuple[float, float, float], final["bounds"])
    if any(abs(value) > bound for value, bound in zip(residual_values, bounds, strict=True)):
        diagnostics = tuple(str(value) for value in (*solution, *residual_values, *bounds))
        raise _RuntimeFailure("BLOCKED_RESIDUAL_ACCEPTANCE", ";".join(diagnostics))
    if q < 0.0:
        raise _RuntimeFailure("BLOCKED_NEGATIVE_PHYSICAL_HEAT_RATE", "signed_q_hot_to_cold_w")
    if not (
        float(request.shell_bulk_state.temperature_k)
        <= two
        <= twi
        <= float(request.tube_bulk_state.temperature_k)
    ):
        raise _RuntimeFailure("BLOCKED_PHYSICAL_WALL_ORDERING", "wall_temperatures")
    return _build_valid_result(
        request,
        canonical_sha256(_request_projection(request)),
        support_id,
        tube_bulk_id,
        shell_bulk_id,
        tube_re,
        tube_pr,
        shell_re,
        shell_pr,
        tube_corr_id,
        tube_corr_version,
        final,
        (q, twi, two),
        f"SCIPY_TRF_STATUS_{solver.status}",
        int(solver.nfev),
        callback_count,
    )


def validate_request(raw_request: object, provider: PropertyProvider) -> Task172LocalOutcome:
    """Validate and execute one local interface closure; never return a partial result."""
    if type(raw_request) is not Task172LocalRequest:
        if type(raw_request) is not dict:
            return _blocked("BLOCKED_INVALID_REQUEST_TYPE", "request", None)
        try:
            request = Task172LocalRequest.model_validate(raw_request, strict=True)
        except ValidationError:
            return _blocked("BLOCKED_INVALID_REQUEST_SCHEMA", "request", None)
    else:
        request = raw_request
    try:
        if type(provider) is not CoolPropProvider:
            raise _RuntimeFailure(
                "BLOCKED_PROPERTY_PROVIDER_IDENTITY_MISMATCH", "property_provider"
            )
        return _solve(request, provider)
    except _RuntimeFailure as exc:
        diagnostics = tuple(exc.field_path.split(";")) if ";" in exc.field_path else ()
        try:
            digest = canonical_sha256(_request_projection(request))
        except Exception:
            digest = None
        return _blocked(exc.code, exc.field_path, digest, diagnostics)
    except Exception:
        return _blocked("BLOCKED_RUNTIME_INTERNAL_FAILURE", "runtime", None)


__all__ = [
    "recompute_task172_blocked_result_hash",
    "recompute_task172_local_roundoff_bounds",
    "recompute_task172_request_hash",
    "recompute_task172_result_hash",
    "recompute_task172_support_id",
    "validate_request",
]
