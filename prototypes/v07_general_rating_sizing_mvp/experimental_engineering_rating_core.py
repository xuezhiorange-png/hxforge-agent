"""Experimental counterflow engineering rating (R26) — independent of Task172 VALIDATED gate."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Literal

from scipy.optimize import brentq

from hexagent.exchangers.shell_tube.overall_heat_transfer_resistance.engineering import (
    compute_wall_resistance,
)
from hexagent.exchangers.shell_tube.task172_local_runtime import service as task172_service
from hexagent.exchangers.shell_tube.task172_local_runtime.models import (
    CandidateTask172LocalRequest,
    LocalState,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173
from hexagent.properties.base import FluidIdentifier
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase
from prototypes.v07_general_rating_sizing_mvp.native_thermal_boundary_binding import (
    native_thermal_boundary_session,
)
from prototypes.v07_general_rating_sizing_mvp.positive_duty_cell import (
    NativeCellContext,
    build_native_cell_context,
)

ENGINEERING_NUMERIC_VALID = "EXPERIMENTAL_ENGINEERING_NUMERIC_VALID"
ENGINEERING_BLOCKED = "EXPERIMENTAL_ENGINEERING_BLOCKED"
_SCHEMA = "hxforge.experimental-engineering-rating.v1"

_WATER = FluidIdentifier("Water", "HEOS")

# Relative/absolute energy balance tolerance (engineering, not Task172 C-bound).
_ENERGY_REL_TOL = 1e-8
_ENERGY_ABS_TOL_W = 1e-3
_CELL_THERMAL_REL_TOL = 2e-6
_CELL_THERMAL_ABS_TOL_W = 0.5
_PICARD_MAX_ITER = 64
_PICARD_RTOL = 1e-7
_SHOOTING_XTOL = 1e-9


@dataclass(frozen=True)
class EngineeringAcceptanceLimits:
    energy_relative_tolerance: float = _ENERGY_REL_TOL
    energy_absolute_tolerance_w: float = _ENERGY_ABS_TOL_W
    cell_thermal_relative_tolerance: float = _CELL_THERMAL_REL_TOL
    cell_thermal_absolute_tolerance_w: float = _CELL_THERMAL_ABS_TOL_W


@dataclass
class EngineeringCellResult:
    index: int
    heat_rate_w: float
    tube_inlet_enthalpy_j_kg: float
    tube_outlet_enthalpy_j_kg: float
    shell_inlet_enthalpy_j_kg: float
    shell_outlet_enthalpy_j_kg: float
    tube_bulk_temperature_k: float
    shell_bulk_temperature_k: float
    thermal_residual_w: float
    enthalpy_residual_w: float


@dataclass
class EngineeringRatingResult:
    schema_version: str
    status: Literal["EXPERIMENTAL_ENGINEERING_NUMERIC_VALID", "EXPERIMENTAL_ENGINEERING_BLOCKED"]
    failure_code: str | None
    diagnostics: list[str]
    mesh_subdivisions: int
    candidate_id: str
    duty_w: float | None
    tube_inlet_temperature_k: float
    shell_inlet_temperature_k: float
    tube_outlet_temperature_k: float | None
    shell_outlet_temperature_k: float | None
    tube_inlet_enthalpy_j_kg: float | None
    shell_inlet_enthalpy_j_kg: float | None
    tube_outlet_enthalpy_j_kg: float | None
    shell_outlet_enthalpy_j_kg: float | None
    hot_side_enthalpy_duty_w: float | None
    cold_side_enthalpy_duty_w: float | None
    energy_balance_relative_error: float | None
    max_cell_thermal_residual_w: float | None
    cells: list[EngineeringCellResult]
    picard_iterations: int
    property_provider_state_lookup_count: int
    wall_seconds: float
    correlation_notes: list[str] = field(default_factory=list)


@dataclass
class _PropertyCounter:
    count: int = 0


def _counting_provider(provider: CoolPropProvider) -> tuple[CoolPropProvider, _PropertyCounter]:
    counter = _PropertyCounter()
    base_tp = provider.state_tp

    def state_tp(*args: Any, **kwargs: Any) -> Any:
        counter.count += 1
        return base_tp(*args, **kwargs)

    provider.state_tp = state_tp  # type: ignore[method-assign]
    return provider, counter


def _enthalpy_j_kg(provider: CoolPropProvider, temperature_k: float, pressure_pa: float) -> float:
    state = provider.state_tp(_WATER, float(temperature_k), float(pressure_pa))
    return float(state.enthalpy_j_kg)


def _temperature_k_from_h(
    provider: CoolPropProvider, enthalpy_j_kg: float, *, side: Literal["TUBE", "SHELL"]
) -> float:
    thermo = t173._state_from_enthalpy(provider, Decimal(str(enthalpy_j_kg)), side=side)
    return float(thermo.native.temperature_k)


def _wall_resistance_k_per_w(request: CandidateTask172LocalRequest) -> float:
    support = request.support
    bell = request.candidate_binding.task166_result.bell_geometry
    if bell is None:
        raise ValueError("missing Bell geometry")
    tube_id = request.candidate_binding.task025_result.hydraulic_diameter_m
    result = compute_wall_resistance(
        tube_id,
        bell.tube_outer_diameter_m,
        task172_service.WALL_CONDUCTIVITY_W_M_K,
        support.inside_area_m2,
    )
    return float(result.wall_bundle_conduction_resistance_k_w)


def _cell_thermal_heat_rate_w(
    request: CandidateTask172LocalRequest,
    provider: CoolPropProvider,
    tube_bulk_k: float,
    shell_bulk_k: float,
    *,
    property_cache: dict[tuple[str, int], float],
    property_counter: list[int],
) -> float:
    """Q from physical Two scalar balance (same conductance model as Task172 R25D, no C-bound)."""
    req = request.model_copy(
        update={
            "tube_bulk_state": LocalState(
                temperature_k=Decimal(str(tube_bulk_k)),
                pressure_pa=request.tube_bulk_state.pressure_pa,
            ),
            "shell_bulk_state": LocalState(
                temperature_k=Decimal(str(shell_bulk_k)),
                pressure_pa=request.shell_bulk_state.pressure_pa,
            ),
        }
    )
    tube_bulk_snapshot, _, _ = task172_service._snapshot(
        provider,
        req,
        "TUBE",
        f"{req.support.tube_cell_id}:CELL_MEAN",
        req.tube_bulk_state.temperature_k,
        req.tube_bulk_state.pressure_pa,
    )
    shell_bulk_snapshot, _, _ = task172_service._snapshot(
        provider,
        req,
        "SHELL",
        f"{req.support.shell_cell_id}:CELL_MEAN",
        req.shell_bulk_state.temperature_k,
        req.shell_bulk_state.pressure_pa,
    )
    tube_h_base, _, _, _, _ = task172_service._tube_base_htc(
        req, tube_bulk_snapshot, req.tube_mass_flow_kg_s
    )
    shell_h_base, _, _, _ = task172_service._shell_base_htc(
        req, shell_bulk_snapshot, req.shell_mass_flow_kg_s
    )
    wall_r = _wall_resistance_k_per_w(req)
    tube_k = float(tube_bulk_k)
    shell_k = float(shell_bulk_k)
    if shell_k > tube_k:
        raise ValueError("non_physical_temperature_crossing")

    def twi_from_two(two_value: float) -> tuple[float, float]:
        g_o = task172_service._shell_outer_wall_conductance_w_per_k(
            req,
            provider,
            shell_bulk_snapshot,
            shell_h_base,
            two_value,
            property_eval_cache=property_cache,
            property_eval_counter=property_counter,
        )
        q_outer = g_o * (two_value - shell_k)
        twi_value = two_value + q_outer * wall_r
        return q_outer, twi_value

    def scalar_f_two(two_value: float) -> float:
        q_outer, twi_value = twi_from_two(two_value)
        if twi_value > tube_k:
            return -1.0
        g_i = task172_service._tube_inner_wall_conductance_w_per_k(
            req,
            provider,
            tube_bulk_snapshot,
            tube_h_base,
            twi_value,
            property_eval_cache=property_cache,
            property_eval_counter=property_counter,
        )
        q_inner = g_i * (tube_k - twi_value)
        return q_inner - q_outer

    two_low = shell_k
    lo, hi = two_low, tube_k
    if twi_from_two(hi)[1] <= tube_k:
        two_high = hi
    else:
        for _ in range(32):
            mid = 0.5 * (lo + hi)
            if twi_from_two(mid)[1] <= tube_k:
                lo = mid
            else:
                hi = mid
            if hi - lo <= max(math.ulp(tube_k), 1e-12):
                break
        two_high = lo

    f_lo = scalar_f_two(two_low)
    f_hi = scalar_f_two(two_high)
    if f_lo < 0.0 or f_hi > 0.0:
        raise ValueError(f"no_scalar_bracket;{f_lo};{f_hi}")
    span = two_high - two_low
    if span <= 0.0:
        raise ValueError("degenerate_two_span")

    def scalar_f_u(u_value: float) -> float:
        u_clamped = min(max(float(u_value), 0.0), 1.0)
        return scalar_f_two(two_low + u_clamped * span)

    u_root = brentq(scalar_f_u, 0.0, 1.0, maxiter=32, xtol=1e-12, rtol=1e-12)
    two_root = two_low + float(u_root) * span
    q_outer, _ = twi_from_two(two_root)
    if q_outer < 0.0:
        raise ValueError("negative_q")
    return q_outer


def _solve_counterflow_picard(
    native: NativeCellContext,
    provider: CoolPropProvider,
    *,
    subdivisions: int,
    tube_inlet_t_k: float,
    shell_inlet_t_k: float,
    tube_pressure_pa: float,
    shell_pressure_pa: float,
    limits: EngineeringAcceptanceLimits,
) -> tuple[list[EngineeringCellResult], int]:
    ctx = native.context
    n = subdivisions
    m_tube = float(t173.effective_tube_mass_flow_kg_s())
    m_shell = float(t173.effective_shell_mass_flow_kg_s())
    h_tube = [0.0] * (n + 1)
    h_shell = [0.0] * (n + 1)
    h_tube[0] = _enthalpy_j_kg(provider, tube_inlet_t_k, tube_pressure_pa)
    h_shell[n] = _enthalpy_j_kg(provider, shell_inlet_t_k, shell_pressure_pa)

    # Initial linear enthalpy guess along length.
    for i in range(1, n + 1):
        frac = i / n
        h_tube[i] = h_tube[0] + frac * (h_shell[n] - h_tube[0]) * 0.15
    for i in range(n - 1, -1, -1):
        h_shell[i] = h_shell[n] + (1.0 - i / n) * (h_tube[0] - h_shell[n]) * 0.15

    q_cells = [0.0] * n
    prop_cache: dict[tuple[str, int], float] = {}
    prop_counter = [0]
    h_min = float(t173._effective_h_min_j_kg())
    h_max = float(t173.effective_admitted_h_max_j_kg(provider))
    relax = 0.35 if abs(tube_inlet_t_k - shell_inlet_t_k) > 8.0 else 0.55
    token = t173._CANDIDATE_RATING_CONTEXT.set(ctx)
    try:
        base_support = t173._build_candidate_local_support(ctx, 0, n, 0)
        tube_state0 = t173._state_from_enthalpy(provider, Decimal(str(h_tube[0])), side="TUBE")
        shell_staten = t173._state_from_enthalpy(
            provider, Decimal(str(h_shell[n])), side="SHELL"
        )
        base_request = t173._task172_request(
            base_support, tube_state0, shell_staten, native.shell_authority
        )
        if type(base_request) is not CandidateTask172LocalRequest:
            raise TypeError("expected candidate task172 request")

        for iteration in range(_PICARD_MAX_ITER):
            max_dh = 0.0
            h_tube_new = [h_tube[0]]
            h_shell_new = [0.0] * (n + 1)
            h_shell_new[n] = h_shell[n]
            cell_rows: list[EngineeringCellResult] = []
            for i in range(n):
                support = t173._build_candidate_local_support(ctx, 0, n, i)
                req = base_request.model_copy(update={"support": support})
                t_tube = _temperature_k_from_h(
                    provider, 0.5 * (h_tube[i] + h_tube[i + 1]), side="TUBE"
                )
                t_shell = _temperature_k_from_h(
                    provider, 0.5 * (h_shell[i] + h_shell[i + 1]), side="SHELL"
                )
                q_th = _cell_thermal_heat_rate_w(
                    req,
                    provider,
                    t_tube,
                    t_shell,
                    property_cache=prop_cache,
                    property_counter=prop_counter,
                )
                q_cells[i] = q_th
                h_t_out = h_tube[i] - q_th / m_tube
                h_s_out = h_shell[i + 1] + q_th / m_shell
                h_t_next = (1.0 - relax) * h_tube[i + 1] + relax * h_t_out
                h_s_next = (1.0 - relax) * h_shell[i] + relax * h_s_out
                h_tube_new.append(min(max(h_t_next, h_min), h_max))
                h_shell_new[i] = min(max(h_s_next, h_min), h_max)
                q_ent = m_tube * (h_tube[i] - h_t_out)
                cell_rows.append(
                    EngineeringCellResult(
                        index=i,
                        heat_rate_w=q_th,
                        tube_inlet_enthalpy_j_kg=h_tube[i],
                        tube_outlet_enthalpy_j_kg=h_t_out,
                        shell_inlet_enthalpy_j_kg=h_shell[i + 1],
                        shell_outlet_enthalpy_j_kg=h_s_out,
                        tube_bulk_temperature_k=t_tube,
                        shell_bulk_temperature_k=t_shell,
                        thermal_residual_w=0.0,
                        enthalpy_residual_w=abs(q_th - q_ent),
                    )
                )
                max_dh = max(max_dh, abs(h_t_out - h_tube[i + 1]), abs(h_s_out - h_shell[i]))
            h_tube = h_tube_new
            h_shell = h_shell_new
            if max_dh < _PICARD_RTOL * max(abs(h_tube[0]), abs(h_shell[n]), 1.0):
                return cell_rows, iteration + 1
        raise RuntimeError("picard_nonconvergence")
    finally:
        t173._CANDIDATE_RATING_CONTEXT.reset(token)


def run_experimental_engineering_rating(
    case: EngineeringCase,
    *,
    subdivisions: int = 1,
    native: NativeCellContext | None = None,
    limits: EngineeringAcceptanceLimits | None = None,
) -> EngineeringRatingResult:
    """Counterflow FV rating with live CoolProp and Bell/tube HTC correlations."""
    limits = limits or EngineeringAcceptanceLimits()
    t0 = time.perf_counter()
    provider = CoolPropProvider()
    provider, counter = _counting_provider(provider)
    native_ctx = native or build_native_cell_context(case)
    diagnostics: list[str] = []
    correlation_notes = [
        "tube_side: single-phase correlation with C3 wall Prandtl correction",
        "shell_side: Bell-Delaware with wall viscosity J_mu correction",
        "properties: CoolProp HEOS::Water",
    ]
    tube_t_in = float(t173.TUBE_INLET_T_K)
    shell_t_in = float(t173.SHELL_INLET_T_K)
    try:
        with native_thermal_boundary_session(case, provider, enable_live_binding=True):
            tube_t_in = float(t173.effective_tube_inlet_temperature_k())
            shell_t_in = float(t173.effective_shell_inlet_temperature_k())
            tube_p = float(t173.effective_tube_property_evaluation_pressure_pa())
            shell_p = float(t173.effective_shell_property_evaluation_pressure_pa())
            cells, picard_iter = _solve_counterflow_picard(
                native_ctx,
                provider,
                subdivisions=subdivisions,
                tube_inlet_t_k=tube_t_in,
                shell_inlet_t_k=shell_t_in,
                tube_pressure_pa=tube_p,
                shell_pressure_pa=shell_p,
                limits=limits,
            )
            h_t_in = cells[0].tube_inlet_enthalpy_j_kg
            h_t_out = cells[-1].tube_outlet_enthalpy_j_kg
            h_s_in = cells[-1].shell_inlet_enthalpy_j_kg
            h_s_out = cells[0].shell_outlet_enthalpy_j_kg
            m_tube = float(t173.effective_tube_mass_flow_kg_s())
            m_shell = float(t173.effective_shell_mass_flow_kg_s())
            q_hot = m_tube * (h_t_in - h_t_out)
            q_cold = m_shell * (h_s_out - h_s_in)
            duty = 0.5 * (q_hot + q_cold)
            denom = max(abs(q_hot), abs(q_cold), 1.0)
            energy_rel = abs(q_hot - q_cold) / denom
            max_cell_res = max(c.enthalpy_residual_w for c in cells)
            tube_out_t = _temperature_k_from_h(provider, h_t_out, side="TUBE")
            shell_out_t = _temperature_k_from_h(provider, h_s_out, side="SHELL")
            status = ENGINEERING_NUMERIC_VALID
            failure_code = None
            if (
                energy_rel > limits.energy_relative_tolerance
                and abs(q_hot - q_cold) > limits.energy_absolute_tolerance_w
            ):
                status = ENGINEERING_BLOCKED
                failure_code = "ENERGY_BALANCE_TOLERANCE"
                diagnostics.append(f"energy_rel={energy_rel}")
            if max_cell_res > limits.cell_thermal_absolute_tolerance_w:
                status = ENGINEERING_BLOCKED
                failure_code = failure_code or "CELL_ENTHALPY_CLOSURE"
                diagnostics.append(f"max_cell_enthalpy_residual_w={max_cell_res}")
            if tube_out_t > tube_t_in or shell_out_t < shell_t_in:
                status = ENGINEERING_BLOCKED
                failure_code = failure_code or "TEMPERATURE_CROSSING"
                diagnostics.append(f"tube_out={tube_out_t};shell_out={shell_out_t}")
            elapsed = time.perf_counter() - t0
            return EngineeringRatingResult(
                schema_version=_SCHEMA,
                status=status,
                failure_code=failure_code,
                diagnostics=diagnostics,
                mesh_subdivisions=subdivisions,
                candidate_id=native_ctx.candidate_id,
                duty_w=duty,
                tube_inlet_temperature_k=tube_t_in,
                shell_inlet_temperature_k=shell_t_in,
                tube_outlet_temperature_k=tube_out_t,
                shell_outlet_temperature_k=shell_out_t,
                tube_inlet_enthalpy_j_kg=h_t_in,
                shell_inlet_enthalpy_j_kg=h_s_in,
                tube_outlet_enthalpy_j_kg=h_t_out,
                shell_outlet_enthalpy_j_kg=h_s_out,
                hot_side_enthalpy_duty_w=q_hot,
                cold_side_enthalpy_duty_w=q_cold,
                energy_balance_relative_error=energy_rel,
                max_cell_thermal_residual_w=max_cell_res,
                cells=cells,
                picard_iterations=picard_iter,
                property_provider_state_lookup_count=counter.count,
                wall_seconds=elapsed,
                correlation_notes=correlation_notes,
            )
    except t173._Stage3Failure as exc:
        elapsed = time.perf_counter() - t0
        return EngineeringRatingResult(
            schema_version=_SCHEMA,
            status=ENGINEERING_BLOCKED,
            failure_code=exc.code,
            diagnostics=list(exc.diagnostics),
            mesh_subdivisions=subdivisions,
            candidate_id=native_ctx.candidate_id,
            duty_w=None,
            tube_inlet_temperature_k=float(t173.effective_tube_inlet_temperature_k()),
            shell_inlet_temperature_k=float(t173.effective_shell_inlet_temperature_k()),
            tube_outlet_temperature_k=None,
            shell_outlet_temperature_k=None,
            tube_inlet_enthalpy_j_kg=None,
            shell_inlet_enthalpy_j_kg=None,
            tube_outlet_enthalpy_j_kg=None,
            shell_outlet_enthalpy_j_kg=None,
            hot_side_enthalpy_duty_w=None,
            cold_side_enthalpy_duty_w=None,
            energy_balance_relative_error=None,
            max_cell_thermal_residual_w=None,
            cells=[],
            picard_iterations=0,
            property_provider_state_lookup_count=counter.count,
            wall_seconds=elapsed,
            correlation_notes=correlation_notes,
        )
    except Exception as exc:
        elapsed = time.perf_counter() - t0
        return EngineeringRatingResult(
            schema_version=_SCHEMA,
            status=ENGINEERING_BLOCKED,
            failure_code=type(exc).__name__,
            diagnostics=[str(exc)],
            mesh_subdivisions=subdivisions,
            candidate_id=native_ctx.candidate_id,
            duty_w=None,
            tube_inlet_temperature_k=float(t173.TUBE_INLET_T_K),
            shell_inlet_temperature_k=float(t173.SHELL_INLET_T_K),
            tube_outlet_temperature_k=None,
            shell_outlet_temperature_k=None,
            tube_inlet_enthalpy_j_kg=None,
            shell_inlet_enthalpy_j_kg=None,
            tube_outlet_enthalpy_j_kg=None,
            shell_outlet_enthalpy_j_kg=None,
            hot_side_enthalpy_duty_w=None,
            cold_side_enthalpy_duty_w=None,
            energy_balance_relative_error=None,
            max_cell_thermal_residual_w=None,
            cells=[],
            picard_iterations=0,
            property_provider_state_lookup_count=counter.count,
            wall_seconds=elapsed,
            correlation_notes=correlation_notes,
        )


def epsilon_ntu_counterflow_duty_w(
    *,
    hot_capacity_w_per_k: float,
    cold_capacity_w_per_k: float,
    u_a_w_per_k: float,
    hot_inlet_k: float,
    cold_inlet_k: float,
) -> float:
    """Constant-property ε-NTU counterflow reference (validation only)."""
    c_min = min(hot_capacity_w_per_k, cold_capacity_w_per_k)
    c_max = max(hot_capacity_w_per_k, cold_capacity_w_per_k)
    if c_min <= 0.0 or u_a_w_per_k <= 0.0:
        raise ValueError("invalid_capacity_or_ua")
    ntu = u_a_w_per_k / c_min
    cr = c_min / c_max
    if abs(1.0 - cr) < 1e-14:
        eps = ntu / (1.0 + ntu)
    else:
        eps = (1.0 - math.exp(-ntu * (1.0 - cr))) / (1.0 - cr * math.exp(-ntu * (1.0 - cr)))
    return eps * c_min * (hot_inlet_k - cold_inlet_k)
