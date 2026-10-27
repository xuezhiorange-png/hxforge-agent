"""Experimental counterflow engineering rating (R26/R26A) — full Task171 topology."""

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

_ENERGY_REL_TOL = 1.6e-5
_ENERGY_ABS_TOL_W = 1.0
_CELL_THERMAL_REL_TOL = 2e-6
_CELL_THERMAL_ABS_TOL_W = 0.5
_MESH_DUTY_REL_TOL = 0.02
_PICARD_MAX_ITER = 128
_PICARD_RTOL = 1e-7
_AREA_REL_TOL = 1e-9


@dataclass(frozen=True)
class EngineeringAcceptanceLimits:
    energy_relative_tolerance: float = _ENERGY_REL_TOL
    energy_absolute_tolerance_w: float = _ENERGY_ABS_TOL_W
    cell_thermal_relative_tolerance: float = _CELL_THERMAL_REL_TOL
    cell_thermal_absolute_tolerance_w: float = _CELL_THERMAL_ABS_TOL_W


@dataclass(frozen=True)
class CellThermalClosure:
    q_thermal_w: float
    tube_htc_w_m2_k: float
    shell_htc_w_m2_k: float
    wall_inner_k: float
    wall_outer_k: float
    qi_w: float
    qwall_w: float
    qo_w: float
    g_i_w_per_k: float
    g_wall_w_per_k: float
    g_o_w_per_k: float
    wall_resistance_k_per_w: float
    scalar_root_residual_w: float
    property_applicability_ok: bool


@dataclass
class EngineeringCellResult:
    global_index: int
    interval_index: int
    subdivision_index: int
    physical_segment_id: str
    axial_start_m: float
    axial_end_m: float
    heat_rate_w: float
    tube_inlet_enthalpy_j_kg: float
    tube_outlet_enthalpy_j_kg: float
    shell_inlet_enthalpy_j_kg: float
    shell_outlet_enthalpy_j_kg: float
    tube_bulk_temperature_k: float
    shell_bulk_temperature_k: float
    thermal_residual_w: float
    inner_residual_w: float
    wall_residual_w: float
    outer_residual_w: float
    enthalpy_residual_w: float
    closure: CellThermalClosure


@dataclass
class CoolPropCallStats:
    tp_calls: int = 0
    ph_calls: int = 0
    cache_hits: int = 0

    @property
    def total_calls(self) -> int:
        return self.tp_calls + self.ph_calls


@dataclass
class EngineeringMeshMetadata:
    physical_interval_count: int
    cell_count: int
    total_tube_length_m: float
    task171_total_inside_area_m2: float
    task171_total_outside_area_m2: float
    summed_cell_inside_area_m2: float
    summed_cell_outside_area_m2: float
    all_physical_supports_covered: bool
    total_area_conservation: bool


@dataclass
class EngineeringRatingResult:
    schema_version: str
    status: Literal["EXPERIMENTAL_ENGINEERING_NUMERIC_VALID", "EXPERIMENTAL_ENGINEERING_BLOCKED"]
    failure_code: str | None
    diagnostics: list[str]
    mesh_subdivisions: int
    candidate_id: str
    mesh_metadata: EngineeringMeshMetadata | None
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
    max_inner_wall_outer_closure_residual_w: float | None
    cells: list[EngineeringCellResult]
    picard_iterations: int
    coolprop_stats: CoolPropCallStats
    wall_seconds: float
    correlation_notes: list[str] = field(default_factory=list)

    @property
    def property_provider_state_lookup_count(self) -> int:
        return self.coolprop_stats.total_calls


@dataclass(frozen=True)
class _GlobalCellBinding:
    global_index: int
    interval_index: int
    subdivision_index: int
    axial_start_m: float
    axial_end_m: float
    physical_segment_id: str
    support: Any


def _instrument_provider(
    provider: CoolPropProvider,
) -> tuple[CoolPropProvider, CoolPropCallStats, dict[tuple[Any, ...], Any]]:
    stats = CoolPropCallStats()
    cache: dict[tuple[Any, ...], Any] = {}
    base_tp = provider.state_tp
    base_ph = provider.state_ph

    def state_tp(*args: Any, **kwargs: Any) -> Any:
        key = ("tp", args, tuple(sorted(kwargs.items())))
        if key in cache:
            stats.cache_hits += 1
            return cache[key]
        stats.tp_calls += 1
        state = base_tp(*args, **kwargs)
        cache[key] = state
        return state

    def state_ph(*args: Any, **kwargs: Any) -> Any:
        key = ("ph", args, tuple(sorted(kwargs.items())))
        if key in cache:
            stats.cache_hits += 1
            return cache[key]
        stats.ph_calls += 1
        state = base_ph(*args, **kwargs)
        cache[key] = state
        return state

    provider.state_tp = state_tp  # type: ignore[method-assign]
    provider.state_ph = state_ph  # type: ignore[method-assign]
    return provider, stats, cache


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


def _build_global_cell_grid(
    ctx: Any,
    subdivisions: int,
) -> tuple[list[_GlobalCellBinding], EngineeringMeshMetadata]:
    definition = ctx.request.task171_result.topology_definition
    if definition is None:
        raise ValueError("missing_topology_definition")
    intervals = definition.intervals
    interval_count = len(intervals)
    expected_cells = interval_count * subdivisions
    bindings: list[_GlobalCellBinding] = []
    seen_support_keys: set[tuple[int, int]] = set()
    for interval_index in range(interval_count):
        for subdivision_index in range(subdivisions):
            support = t173._build_candidate_local_support(
                ctx, interval_index, subdivisions, subdivision_index
            )
            key = (interval_index, subdivision_index)
            if key in seen_support_keys:
                raise ValueError("duplicate_support_binding")
            seen_support_keys.add(key)
            bindings.append(
                _GlobalCellBinding(
                    global_index=-1,
                    interval_index=interval_index,
                    subdivision_index=subdivision_index,
                    axial_start_m=float(support.support_start_m),
                    axial_end_m=float(support.support_end_m),
                    physical_segment_id=support.physical_segment_id,
                    support=support,
                )
            )
    if len(bindings) != expected_cells:
        raise ValueError("incomplete_cell_count")
    bindings.sort(
        key=lambda item: (item.axial_start_m, item.interval_index, item.subdivision_index)
    )
    ordered: list[_GlobalCellBinding] = []
    for idx, item in enumerate(bindings):
        ordered.append(
            _GlobalCellBinding(
                global_index=idx,
                interval_index=item.interval_index,
                subdivision_index=item.subdivision_index,
                axial_start_m=item.axial_start_m,
                axial_end_m=item.axial_end_m,
                physical_segment_id=item.physical_segment_id,
                support=item.support,
            )
        )
    total_in = sum(float(iv.inside_area_m2) for iv in intervals)
    total_out = sum(float(iv.outside_area_m2) for iv in intervals)
    summed_in = sum(float(b.support.inside_area_m2) for b in ordered)
    summed_out = sum(float(b.support.outside_area_m2) for b in ordered)
    length = max(b.axial_end_m for b in ordered) - min(b.axial_start_m for b in ordered)
    area_ok = (
        abs(summed_in - total_in) <= _AREA_REL_TOL * max(total_in, 1.0)
        and abs(summed_out - total_out) <= _AREA_REL_TOL * max(total_out, 1.0)
    )
    meta = EngineeringMeshMetadata(
        physical_interval_count=interval_count,
        cell_count=len(ordered),
        total_tube_length_m=length,
        task171_total_inside_area_m2=total_in,
        task171_total_outside_area_m2=total_out,
        summed_cell_inside_area_m2=summed_in,
        summed_cell_outside_area_m2=summed_out,
        all_physical_supports_covered=len(seen_support_keys) == expected_cells,
        total_area_conservation=area_ok,
    )
    if not meta.all_physical_supports_covered or not meta.total_area_conservation:
        raise ValueError("mesh_topology_incomplete")
    return ordered, meta


def _cell_thermal_closure(
    request: CandidateTask172LocalRequest,
    provider: CoolPropProvider,
    tube_bulk_k: float,
    shell_bulk_k: float,
    *,
    conductance_cache: dict[tuple[Any, ...], float],
) -> CellThermalClosure:
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
    support_key = (
        req.support.physical_segment_id,
        int(req.support.subdivision_index),
        float(req.support.inside_area_m2),
        float(req.support.outside_area_m2),
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
    g_wall = 1.0 / wall_r
    tube_k = float(tube_bulk_k)
    shell_k = float(shell_bulk_k)
    if shell_k > tube_k:
        raise ValueError("non_physical_temperature_crossing")

    def twi_from_two(two_value: float) -> tuple[float, float, float, float]:
        cache_key = ("g_o", support_key, tube_k, shell_k, two_value)
        if cache_key in conductance_cache:
            g_o = conductance_cache[cache_key]
        else:
            g_o = task172_service._shell_outer_wall_conductance_w_per_k(
                req,
                provider,
                shell_bulk_snapshot,
                shell_h_base,
                two_value,
                property_eval_cache=None,
                property_eval_counter=None,
            )
            conductance_cache[cache_key] = g_o
        q_outer = g_o * (two_value - shell_k)
        twi_value = two_value + q_outer * wall_r
        return q_outer, twi_value, g_o, two_value

    def scalar_f_two(two_value: float) -> float:
        q_outer, twi_value, _, _ = twi_from_two(two_value)
        if twi_value > tube_k:
            return -1.0
        cache_key = ("g_i", support_key, tube_k, shell_k, twi_value)
        if cache_key in conductance_cache:
            g_i = conductance_cache[cache_key]
        else:
            g_i = task172_service._tube_inner_wall_conductance_w_per_k(
                req,
                provider,
                tube_bulk_snapshot,
                tube_h_base,
                twi_value,
                property_eval_cache=None,
                property_eval_counter=None,
            )
            conductance_cache[cache_key] = g_i
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

    u_root = brentq(scalar_f_u, 0.0, 1.0, maxiter=48, xtol=1e-12, rtol=1e-12)
    two_root = two_low + float(u_root) * span
    qo, twi, go, _ = twi_from_two(two_root)
    gi_key = ("g_i", support_key, tube_k, shell_k, twi)
    gi = conductance_cache[gi_key]
    ai = float(req.support.inside_area_m2)
    ao = float(req.support.outside_area_m2)
    hi = gi / ai if ai > 0 else 0.0
    ho = go / ao if ao > 0 else 0.0
    qi = gi * (tube_k - twi)
    qwall = g_wall * (twi - two_root)
    scalar_residual = qi - qo
    return CellThermalClosure(
        q_thermal_w=qo,
        tube_htc_w_m2_k=hi,
        shell_htc_w_m2_k=ho,
        wall_inner_k=twi,
        wall_outer_k=two_root,
        qi_w=qi,
        qwall_w=qwall,
        qo_w=qo,
        g_i_w_per_k=gi,
        g_wall_w_per_k=g_wall,
        g_o_w_per_k=go,
        wall_resistance_k_per_w=wall_r,
        scalar_root_residual_w=scalar_residual,
        property_applicability_ok=True,
    )


def _solve_counterflow_picard(
    native: NativeCellContext,
    provider: CoolPropProvider,
    grid: list[_GlobalCellBinding],
    *,
    tube_inlet_t_k: float,
    shell_inlet_t_k: float,
    tube_pressure_pa: float,
    shell_pressure_pa: float,
) -> tuple[list[EngineeringCellResult], int]:
    ctx = native.context
    n = len(grid)
    m_tube = float(t173.effective_tube_mass_flow_kg_s())
    m_shell = float(t173.effective_shell_mass_flow_kg_s())
    h_tube = [0.0] * (n + 1)
    h_shell = [0.0] * (n + 1)
    h_tube[0] = _enthalpy_j_kg(provider, tube_inlet_t_k, tube_pressure_pa)
    h_shell[n] = _enthalpy_j_kg(provider, shell_inlet_t_k, shell_pressure_pa)

    for i in range(1, n + 1):
        frac = i / n
        h_tube[i] = h_tube[0] - frac * (h_tube[0] - h_shell[n]) * 0.12
    for i in range(n - 1, -1, -1):
        h_shell[i] = h_shell[n] + (1.0 - i / n) * (h_tube[0] - h_shell[n]) * 0.12

    delta_t_in = abs(tube_inlet_t_k - shell_inlet_t_k)
    relax = 0.35 if delta_t_in > 8.0 else 0.5
    relax = min(relax, 0.45 * (5.0 / max(n, 1)) ** 0.25)
    conductance_cache: dict[tuple[Any, ...], float] = {}
    token = t173._CANDIDATE_RATING_CONTEXT.set(ctx)
    try:
        ref_support = grid[0].support
        tube_state0 = t173._state_from_enthalpy(provider, Decimal(str(h_tube[0])), side="TUBE")
        shell_staten = t173._state_from_enthalpy(
            provider, Decimal(str(h_shell[n])), side="SHELL"
        )
        base_request = t173._task172_request(
            ref_support, tube_state0, shell_staten, native.shell_authority
        )
        if type(base_request) is not CandidateTask172LocalRequest:
            raise TypeError("expected candidate task172 request")

        for iteration in range(_PICARD_MAX_ITER):
            max_dh = 0.0
            h_tube_new = [h_tube[0]]
            h_shell_new = [0.0] * (n + 1)
            h_shell_new[n] = h_shell[n]
            cell_rows: list[EngineeringCellResult] = []
            for binding in grid:
                i = binding.global_index
                req = base_request.model_copy(update={"support": binding.support})
                t_tube = _temperature_k_from_h(
                    provider, 0.5 * (h_tube[i] + h_tube[i + 1]), side="TUBE"
                )
                t_shell = _temperature_k_from_h(
                    provider, 0.5 * (h_shell[i] + h_shell[i + 1]), side="SHELL"
                )
                closure = _cell_thermal_closure(
                    req,
                    provider,
                    t_tube,
                    t_shell,
                    conductance_cache=conductance_cache,
                )
                q_cell = closure.q_thermal_w
                h_t_out = h_tube[i] - q_cell / m_tube
                h_s_out = h_shell[i + 1] + q_cell / m_shell
                h_t_next = (1.0 - relax) * h_tube[i + 1] + relax * h_t_out
                h_s_next = (1.0 - relax) * h_shell[i] + relax * h_s_out
                h_tube_new.append(h_t_next)
                h_shell_new[i] = h_s_next
                q_ent = m_tube * (h_tube[i] - h_t_out)
                cell_rows.append(
                    EngineeringCellResult(
                        global_index=binding.global_index,
                        interval_index=binding.interval_index,
                        subdivision_index=binding.subdivision_index,
                        physical_segment_id=binding.physical_segment_id,
                        axial_start_m=binding.axial_start_m,
                        axial_end_m=binding.axial_end_m,
                        heat_rate_w=q_cell,
                        tube_inlet_enthalpy_j_kg=h_tube[i],
                        tube_outlet_enthalpy_j_kg=h_t_out,
                        shell_inlet_enthalpy_j_kg=h_shell[i + 1],
                        shell_outlet_enthalpy_j_kg=h_s_out,
                        tube_bulk_temperature_k=t_tube,
                        shell_bulk_temperature_k=t_shell,
                        thermal_residual_w=abs(q_ent - closure.q_thermal_w),
                        inner_residual_w=abs(q_ent - closure.qi_w),
                        wall_residual_w=abs(q_ent - closure.qwall_w),
                        outer_residual_w=abs(q_ent - closure.qo_w),
                        enthalpy_residual_w=abs(q_ent - q_cell),
                        closure=closure,
                    )
                )
                max_dh = max(
                    max_dh,
                    abs(h_t_out - h_tube[i + 1]),
                    abs(h_s_out - h_shell[i]),
                )
            h_tube = h_tube_new
            h_shell_new[n] = h_shell[n]
            h_shell = h_shell_new
            if max_dh < _PICARD_RTOL * max(abs(h_tube[0]), abs(h_shell[n]), 1.0):
                return cell_rows, iteration + 1
        raise RuntimeError(f"picard_nonconvergence;cells={n}")
    finally:
        t173._CANDIDATE_RATING_CONTEXT.reset(token)


def _accept_cells(
    cells: list[EngineeringCellResult],
    limits: EngineeringAcceptanceLimits,
    tube_t_in: float,
    shell_t_in: float,
    tube_out_t: float,
    shell_out_t: float,
    energy_rel: float,
    q_hot: float,
    q_cold: float,
) -> tuple[str, str | None, list[str]]:
    diagnostics: list[str] = []
    failure: str | None = None
    if (
        energy_rel > limits.energy_relative_tolerance
        or abs(q_hot - q_cold) > limits.energy_absolute_tolerance_w
    ):
        failure = "ENERGY_BALANCE_TOLERANCE"
        diagnostics.append(f"energy_rel={energy_rel}")
    for cell in cells:
        rel = abs(cell.thermal_residual_w) / max(abs(cell.heat_rate_w), 1.0)
        if (
            cell.thermal_residual_w > limits.cell_thermal_absolute_tolerance_w
            and rel > limits.cell_thermal_relative_tolerance
        ):
            failure = failure or "CELL_THERMAL_CLOSURE"
            diagnostics.append(
                f"cell={cell.global_index};Rthermal={cell.thermal_residual_w};"
                f"Rinner={cell.inner_residual_w};Rwall={cell.wall_residual_w};"
                f"Router={cell.outer_residual_w}"
            )
            break
    if tube_out_t > tube_t_in or shell_out_t < shell_t_in:
        failure = failure or "TEMPERATURE_CROSSING"
        diagnostics.append(f"tube_out={tube_out_t};shell_out={shell_out_t}")
    status = ENGINEERING_NUMERIC_VALID if failure is None else ENGINEERING_BLOCKED
    return status, failure, diagnostics


def run_experimental_engineering_rating(
    case: EngineeringCase,
    *,
    subdivisions: int = 1,
    native: NativeCellContext | None = None,
    limits: EngineeringAcceptanceLimits | None = None,
) -> EngineeringRatingResult:
    limits = limits or EngineeringAcceptanceLimits()
    t0 = time.perf_counter()
    provider = CoolPropProvider()
    provider, coolprop_stats, _cache = _instrument_provider(provider)
    native_ctx = native or build_native_cell_context(case)
    diagnostics: list[str] = []
    correlation_notes = [
        "tube_side: single-phase correlation with C3 wall Prandtl correction",
        "shell_side: Bell-Delaware with wall viscosity J_mu correction",
        "properties: CoolProp HEOS::Water",
        "topology: full Task171 physical interval coverage (R26A)",
    ]
    tube_t_in = float(t173.TUBE_INLET_T_K)
    shell_t_in = float(t173.SHELL_INLET_T_K)

    def _blocked(
        code: str,
        extra: list[str] | None = None,
        mesh_meta: EngineeringMeshMetadata | None = None,
    ) -> EngineeringRatingResult:
        elapsed = time.perf_counter() - t0
        return EngineeringRatingResult(
            schema_version=_SCHEMA,
            status=ENGINEERING_BLOCKED,
            failure_code=code,
            diagnostics=(extra or []) + diagnostics,
            mesh_subdivisions=subdivisions,
            candidate_id=native_ctx.candidate_id,
            mesh_metadata=mesh_meta,
            duty_w=None,
            tube_inlet_temperature_k=tube_t_in,
            shell_inlet_temperature_k=shell_t_in,
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
            max_inner_wall_outer_closure_residual_w=None,
            cells=[],
            picard_iterations=0,
            coolprop_stats=coolprop_stats,
            wall_seconds=elapsed,
            correlation_notes=correlation_notes,
        )

    try:
        with native_thermal_boundary_session(case, provider, enable_live_binding=True):
            tube_t_in = float(t173.effective_tube_inlet_temperature_k())
            shell_t_in = float(t173.effective_shell_inlet_temperature_k())
            tube_p = float(t173.effective_tube_property_evaluation_pressure_pa())
            shell_p = float(t173.effective_shell_property_evaluation_pressure_pa())
            token = t173._CANDIDATE_RATING_CONTEXT.set(native_ctx.context)
            try:
                grid, mesh_meta = _build_global_cell_grid(native_ctx.context, subdivisions)
            finally:
                t173._CANDIDATE_RATING_CONTEXT.reset(token)
            cells, picard_iter = _solve_counterflow_picard(
                native_ctx,
                provider,
                grid,
                tube_inlet_t_k=tube_t_in,
                shell_inlet_t_k=shell_t_in,
                tube_pressure_pa=tube_p,
                shell_pressure_pa=shell_p,
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
            max_cell_res = max(c.thermal_residual_w for c in cells)
            max_closure = max(
                max(c.inner_residual_w, c.wall_residual_w, c.outer_residual_w) for c in cells
            )
            tube_out_t = _temperature_k_from_h(provider, h_t_out, side="TUBE")
            shell_out_t = _temperature_k_from_h(provider, h_s_out, side="SHELL")
            status, failure_code, accept_diag = _accept_cells(
                cells,
                limits,
                tube_t_in,
                shell_t_in,
                tube_out_t,
                shell_out_t,
                energy_rel,
                q_hot,
                q_cold,
            )
            diagnostics.extend(accept_diag)
            elapsed = time.perf_counter() - t0
            return EngineeringRatingResult(
                schema_version=_SCHEMA,
                status=status,
                failure_code=failure_code,
                diagnostics=diagnostics,
                mesh_subdivisions=subdivisions,
                candidate_id=native_ctx.candidate_id,
                mesh_metadata=mesh_meta,
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
                max_inner_wall_outer_closure_residual_w=max_closure,
                cells=cells,
                picard_iterations=picard_iter,
                coolprop_stats=coolprop_stats,
                wall_seconds=elapsed,
                correlation_notes=correlation_notes,
            )
    except t173._Stage3Failure as exc:
        return _blocked(exc.code, list(exc.diagnostics))
    except ValueError as exc:
        return _blocked("MESH_TOPOLOGY_INVALID", [str(exc)])
    except Exception as exc:
        return _blocked(type(exc).__name__, [str(exc)])


def epsilon_ntu_counterflow_duty_w(
    *,
    hot_capacity_w_per_k: float,
    cold_capacity_w_per_k: float,
    u_a_w_per_k: float,
    hot_inlet_k: float,
    cold_inlet_k: float,
) -> float:
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


def constant_u_counterflow_fv_duty_w(
    *,
    n_cells: int,
    hot_capacity_w_per_k: float,
    cold_capacity_w_per_k: float,
    u_a_total_w_per_k: float,
    hot_inlet_k: float,
    cold_inlet_k: float,
    max_iter: int = 256,
) -> float:
    """Constant-U counterflow FV reference (validation only)."""
    n = n_cells
    ua_cell = u_a_total_w_per_k / n
    m_hot = hot_capacity_w_per_k
    m_cold = cold_capacity_w_per_k
    th = [0.0] * (n + 1)
    tc = [0.0] * (n + 1)
    th[0] = hot_inlet_k
    tc[n] = cold_inlet_k
    for i in range(1, n + 1):
        th[i] = th[0] - (th[0] - tc[n]) * (i / n) * 0.2
    for i in range(n - 1, -1, -1):
        tc[i] = tc[n] + (th[0] - tc[n]) * (1.0 - i / n) * 0.2
    relax = 0.55
    for _ in range(max_iter):
        max_delta = 0.0
        th_new = [th[0]]
        tc_new = [0.0] * (n + 1)
        tc_new[n] = tc[n]
        for i in range(n):
            dt = max(th[i] - tc[i + 1], 1e-6)
            q = ua_cell * dt
            t_h_out = th[i] - q / m_hot
            t_c_out = tc[i + 1] + q / m_cold
            th_new.append((1.0 - relax) * th[i + 1] + relax * t_h_out)
            tc_new[i] = (1.0 - relax) * tc[i] + relax * t_c_out
            max_delta = max(max_delta, abs(th_new[-1] - th[i + 1]), abs(tc_new[i] - tc[i]))
        th, tc = th_new, tc_new
        if max_delta < 1e-9:
            break
    return m_hot * (hot_inlet_k - th[n])


def evaluate_mesh_convergence(
    case: EngineeringCase,
    *,
    native: NativeCellContext | None = None,
) -> dict[str, Any]:
    """Run n=1,2,4 and report duty/outlet mesh deltas."""
    meshes = (1, 2, 4)
    results: dict[int, EngineeringRatingResult] = {}
    for n in meshes:
        results[n] = run_experimental_engineering_rating(case, subdivisions=n, native=native)
    def rel_change(a: float | None, b: float | None) -> float | None:
        if a is None or b is None or abs(a) < 1e-9:
            return None
        return abs(b - a) / abs(a)

    r12 = rel_change(results[1].duty_w, results[2].duty_w)
    r24 = rel_change(results[2].duty_w, results[4].duty_w)
    converged = (
        all(results[n].status == ENGINEERING_NUMERIC_VALID for n in meshes)
        and r12 is not None
        and r24 is not None
        and r12 <= _MESH_DUTY_REL_TOL
        and r24 <= _MESH_DUTY_REL_TOL
    )
    return {
        "results": results,
        "n1_n2_duty_relative_change": r12,
        "n2_n4_duty_relative_change": r24,
        "full_rating_converged": converged,
    }
