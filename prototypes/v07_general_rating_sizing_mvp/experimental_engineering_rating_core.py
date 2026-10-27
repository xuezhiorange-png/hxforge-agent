"""Experimental counterflow engineering rating (R26/R26A) — full Task171 topology."""

from __future__ import annotations

import math
import time
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Literal

import numpy as np
from scipy.optimize import brentq, least_squares

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

_ENERGY_REL_TOL = 1e-8
_ENERGY_ABS_TOL_W = 1e-3
_CELL_THERMAL_REL_TOL = 2e-6
_CELL_THERMAL_ABS_TOL_W = 0.5
_MESH_DUTY_REL_TOL = 0.02
_MESH_OUTLET_REL_TOL_K = 0.05
_MAX_Q_SOLVER_NFEV = 1200
_MAX_Q_SOLVER_WALL_S = 300.0
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
    area_ok = abs(summed_in - total_in) <= _AREA_REL_TOL * max(total_in, 1.0) and abs(
        summed_out - total_out
    ) <= _AREA_REL_TOL * max(total_out, 1.0)
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


def build_warm_start_q_from_parent_cells(
    grid: Sequence[_GlobalCellBinding],
    parent_cells: Sequence[EngineeringCellResult],
    *,
    child_subdivisions: int,
    parent_subdivisions: int,
) -> np.ndarray:
    """Map parent (interval, subdivision) duties onto child cells without overlap gaps."""
    if child_subdivisions % parent_subdivisions != 0:
        raise ValueError("subdivisions_not_divisible")
    ratio = child_subdivisions // parent_subdivisions
    parent_q: dict[tuple[int, int], float] = {
        (cell.interval_index, cell.subdivision_index): cell.heat_rate_w for cell in parent_cells
    }
    child_area_by_parent: dict[tuple[int, int], float] = defaultdict(float)
    child_area: dict[int, float] = {}
    for binding in grid:
        parent_sub_idx = binding.subdivision_index // ratio
        key = (binding.interval_index, parent_sub_idx)
        if key not in parent_q:
            raise ValueError(f"missing_parent_cell:{key}")
        area = float(binding.support.inside_area_m2)
        child_area[binding.global_index] = area
        child_area_by_parent[key] += area
    q_initial = np.zeros(len(grid), dtype=float)
    for binding in grid:
        parent_sub_idx = binding.subdivision_index // ratio
        key = (binding.interval_index, parent_sub_idx)
        total_area = child_area_by_parent[key]
        if total_area <= 0.0:
            raise ValueError(f"zero_parent_area:{key}")
        share = child_area[binding.global_index] / total_area
        q_initial[binding.global_index] = parent_q[key] * share
    for key, q_parent in parent_q.items():
        child_sum = sum(
            q_initial[b.global_index]
            for b in grid
            if (b.interval_index, b.subdivision_index // ratio) == key
        )
        tol = max(1e-6, abs(q_parent) * 1e-9)
        if abs(child_sum - q_parent) > tol:
            raise ValueError(f"warm_start_duty_partition:{key}")
    return q_initial


def _min_cell_approach_temperature_k(result: EngineeringRatingResult) -> float | None:
    if not result.cells:
        return None
    return min(
        cell.tube_bulk_temperature_k - cell.shell_bulk_temperature_k for cell in result.cells
    )


def _local_closure_valid(
    result: EngineeringRatingResult,
    limits: EngineeringAcceptanceLimits,
) -> bool:
    if result.status != ENGINEERING_NUMERIC_VALID:
        return False
    if (
        result.max_cell_thermal_residual_w is None
        or result.max_inner_wall_outer_closure_residual_w is None
    ):
        return False
    if result.energy_balance_relative_error is None:
        return False
    if (
        result.energy_balance_relative_error > limits.energy_relative_tolerance
        or result.max_cell_thermal_residual_w > limits.cell_thermal_absolute_tolerance_w
        or result.max_inner_wall_outer_closure_residual_w > limits.cell_thermal_absolute_tolerance_w
    ):
        return False
    for cell in result.cells:
        rel = abs(cell.thermal_residual_w) / max(abs(cell.heat_rate_w), 1.0)
        if cell.thermal_residual_w > limits.cell_thermal_absolute_tolerance_w and rel > (
            limits.cell_thermal_relative_tolerance
        ):
            return False
    return True


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


def _enthalpies_from_q_vector(
    q: np.ndarray,
    *,
    h_t_in: float,
    h_s_in: float,
    m_tube: float,
    m_shell: float,
) -> tuple[list[float], list[float]]:
    n = int(q.size)
    ht = [float(h_t_in)]
    hs = [0.0] * (n + 1)
    hs[n] = float(h_s_in)
    for i in range(n):
        ht.append(ht[i] - float(q[i]) / m_tube)
    for i in range(n - 1, -1, -1):
        hs[i] = hs[i + 1] + float(q[i]) / m_shell
    return ht, hs


def _check_enthalpy_domain(provider: CoolPropProvider, enthalpies: list[float]) -> None:
    h_min = float(t173._effective_h_min_j_kg())
    h_max = float(t173.effective_admitted_h_max_j_kg(provider))
    for value in enthalpies:
        if value < h_min or value > h_max:
            raise ValueError(f"enthalpy_domain_exit;h={value}")


def _initial_q_guess(
    n: int,
    *,
    h_t_in: float,
    h_s_in: float,
    m_tube: float,
    delta_t_in: float,
    q_seed: np.ndarray | None,
) -> np.ndarray:
    if q_seed is not None and q_seed.size == n:
        return np.maximum(q_seed.astype(float), 1.0)
    total_est = max(m_tube * max(h_t_in - h_s_in, 0.0) * 0.08, 5000.0)
    if delta_t_in > 8.0:
        total_est = max(total_est, 250_000.0 / max(n / 5.0, 1.0))
    return np.full(n, total_est / n, dtype=float)


def _build_cells_from_q(
    q: np.ndarray,
    *,
    grid: list[_GlobalCellBinding],
    provider: CoolPropProvider,
    base_request: CandidateTask172LocalRequest,
    h_t_in: float,
    h_s_in: float,
    m_tube: float,
    m_shell: float,
    conductance_cache: dict[tuple[Any, ...], float],
) -> list[EngineeringCellResult]:
    ht, hs = _enthalpies_from_q_vector(
        q, h_t_in=h_t_in, h_s_in=h_s_in, m_tube=m_tube, m_shell=m_shell
    )
    rows: list[EngineeringCellResult] = []
    for binding in grid:
        i = binding.global_index
        q_i = float(q[i])
        req = base_request.model_copy(update={"support": binding.support})
        h_tb = 0.5 * (ht[i] + ht[i + 1])
        h_sb = 0.5 * (hs[i] + hs[i + 1])
        t_tube = _temperature_k_from_h(provider, h_tb, side="TUBE")
        t_shell = _temperature_k_from_h(provider, h_sb, side="SHELL")
        closure = _cell_thermal_closure(
            req,
            provider,
            t_tube,
            t_shell,
            conductance_cache=conductance_cache,
        )
        r_hot = m_tube * (ht[i] - ht[i + 1]) - q_i
        r_cold = m_shell * (hs[i] - hs[i + 1]) - q_i
        rows.append(
            EngineeringCellResult(
                global_index=binding.global_index,
                interval_index=binding.interval_index,
                subdivision_index=binding.subdivision_index,
                physical_segment_id=binding.physical_segment_id,
                axial_start_m=binding.axial_start_m,
                axial_end_m=binding.axial_end_m,
                heat_rate_w=q_i,
                tube_inlet_enthalpy_j_kg=ht[i],
                tube_outlet_enthalpy_j_kg=ht[i + 1],
                shell_inlet_enthalpy_j_kg=hs[i + 1],
                shell_outlet_enthalpy_j_kg=hs[i],
                tube_bulk_temperature_k=t_tube,
                shell_bulk_temperature_k=t_shell,
                thermal_residual_w=abs(q_i - closure.q_thermal_w),
                inner_residual_w=abs(q_i - closure.qi_w),
                wall_residual_w=abs(q_i - closure.qwall_w),
                outer_residual_w=abs(q_i - closure.qo_w),
                enthalpy_residual_w=max(abs(r_hot), abs(r_cold)),
                closure=closure,
            )
        )
    return rows


def _solve_global_q_vector(
    native: NativeCellContext,
    provider: CoolPropProvider,
    grid: list[_GlobalCellBinding],
    *,
    tube_inlet_t_k: float,
    shell_inlet_t_k: float,
    tube_pressure_pa: float,
    shell_pressure_pa: float,
    q_initial: np.ndarray | None = None,
) -> tuple[list[EngineeringCellResult], int]:
    ctx = native.context
    n = len(grid)
    m_tube = float(t173.effective_tube_mass_flow_kg_s())
    m_shell = float(t173.effective_shell_mass_flow_kg_s())
    h_t_in = _enthalpy_j_kg(provider, tube_inlet_t_k, tube_pressure_pa)
    h_s_in = _enthalpy_j_kg(provider, shell_inlet_t_k, shell_pressure_pa)
    conductance_cache: dict[tuple[Any, ...], float] = {}
    token = t173._CANDIDATE_RATING_CONTEXT.set(ctx)
    solver_t0 = time.perf_counter()
    try:
        ref_support = grid[0].support
        tube_state0 = t173._state_from_enthalpy(provider, Decimal(str(h_t_in)), side="TUBE")
        shell_staten = t173._state_from_enthalpy(provider, Decimal(str(h_s_in)), side="SHELL")
        base_request = t173._task172_request(
            ref_support, tube_state0, shell_staten, native.shell_authority
        )
        if type(base_request) is not CandidateTask172LocalRequest:
            raise TypeError("expected candidate task172 request")

        q0 = _initial_q_guess(
            n,
            h_t_in=h_t_in,
            h_s_in=h_s_in,
            m_tube=m_tube,
            delta_t_in=abs(tube_inlet_t_k - shell_inlet_t_k),
            q_seed=q_initial,
        )

        def residuals(q_raw: np.ndarray) -> np.ndarray:
            if time.perf_counter() - solver_t0 > _MAX_Q_SOLVER_WALL_S:
                raise RuntimeError("global_q_solver_wall_budget")
            q_vec = np.maximum(q_raw, 0.0)
            ht, hs = _enthalpies_from_q_vector(
                q_vec, h_t_in=h_t_in, h_s_in=h_s_in, m_tube=m_tube, m_shell=m_shell
            )
            _check_enthalpy_domain(provider, ht + hs)
            out = np.zeros(n, dtype=float)
            for binding in grid:
                i = binding.global_index
                req = base_request.model_copy(update={"support": binding.support})
                h_tb = 0.5 * (ht[i] + ht[i + 1])
                h_sb = 0.5 * (hs[i] + hs[i + 1])
                t_tube = _temperature_k_from_h(provider, h_tb, side="TUBE")
                t_shell = _temperature_k_from_h(provider, h_sb, side="SHELL")
                if t_shell > t_tube:
                    raise ValueError("temperature_crossing")
                closure = _cell_thermal_closure(
                    req,
                    provider,
                    t_tube,
                    t_shell,
                    conductance_cache=conductance_cache,
                )
                out[i] = q_vec[i] - closure.q_thermal_w
            return out

        lower = np.zeros(n, dtype=float)
        upper = np.full(n, np.inf, dtype=float)
        solution = least_squares(
            residuals,
            q0,
            bounds=(lower, upper),
            method="trf",
            ftol=1e-10,
            xtol=1e-10,
            gtol=1e-10,
            max_nfev=_MAX_Q_SOLVER_NFEV,
        )
        if not solution.success:
            raise RuntimeError(f"global_q_solver_nonconvergence;{solution.status}")
        q_final = np.maximum(solution.x, 0.0)
        ht_final, hs_final = _enthalpies_from_q_vector(
            q_final, h_t_in=h_t_in, h_s_in=h_s_in, m_tube=m_tube, m_shell=m_shell
        )
        _check_enthalpy_domain(provider, ht_final + hs_final)
        cells = _build_cells_from_q(
            q_final,
            grid=grid,
            provider=provider,
            base_request=base_request,
            h_t_in=h_t_in,
            h_s_in=h_s_in,
            m_tube=m_tube,
            m_shell=m_shell,
            conductance_cache=conductance_cache,
        )
        max_r = float(np.max(np.abs(solution.fun)))
        if max_r > _CELL_THERMAL_ABS_TOL_W:
            raise RuntimeError(f"global_q_residual_floor;max={max_r}")
        return cells, int(solution.nfev)
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
        inner = cell.inner_residual_w
        wall = cell.wall_residual_w
        outer = cell.outer_residual_w
        if cell.enthalpy_residual_w > 1e-9:
            failure = failure or "FACE_ENTHALPY_CONSERVATION"
            diagnostics.append(f"cell={cell.global_index};face={cell.enthalpy_residual_w}")
            break
        thermal_fail = (
            cell.thermal_residual_w > limits.cell_thermal_absolute_tolerance_w
            and rel > limits.cell_thermal_relative_tolerance
        )
        branch_fail = (
            inner > limits.cell_thermal_absolute_tolerance_w
            or wall > limits.cell_thermal_absolute_tolerance_w
            or outer > limits.cell_thermal_absolute_tolerance_w
        )
        if thermal_fail or branch_fail:
            failure = failure or "CELL_THERMAL_CLOSURE"
            diagnostics.append(
                f"cell={cell.global_index};Rthermal={cell.thermal_residual_w};"
                f"Rinner={inner};Rwall={wall};Router={outer}"
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
    mesh_result_cache: dict[int, EngineeringRatingResult] | None = None,
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
        "solver: global cell Q vector with direct face enthalpy reconstruction (R26B)",
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
            q_initial: np.ndarray | None = None
            if subdivisions > 1:
                parent_sub = subdivisions // 2
                parent_cells: list[EngineeringCellResult] | None = None
                if mesh_result_cache is not None:
                    cached_parent = mesh_result_cache.get(parent_sub)
                    if (
                        cached_parent is not None
                        and cached_parent.status == ENGINEERING_NUMERIC_VALID
                        and cached_parent.cells
                    ):
                        parent_cells = cached_parent.cells
                if parent_cells is None:
                    parent_grid, _ = _build_global_cell_grid(native_ctx.context, parent_sub)
                    parent_cells, _ = _solve_global_q_vector(
                        native_ctx,
                        provider,
                        parent_grid,
                        tube_inlet_t_k=tube_t_in,
                        shell_inlet_t_k=shell_t_in,
                        tube_pressure_pa=tube_p,
                        shell_pressure_pa=shell_p,
                    )
                q_initial = build_warm_start_q_from_parent_cells(
                    grid,
                    parent_cells,
                    child_subdivisions=subdivisions,
                    parent_subdivisions=parent_sub,
                )
            cells, solver_nfev = _solve_global_q_vector(
                native_ctx,
                provider,
                grid,
                tube_inlet_t_k=tube_t_in,
                shell_inlet_t_k=shell_t_in,
                tube_pressure_pa=tube_p,
                shell_pressure_pa=shell_p,
                q_initial=q_initial,
            )
            h_t_in = cells[0].tube_inlet_enthalpy_j_kg
            h_t_out = cells[-1].tube_outlet_enthalpy_j_kg
            h_s_in = cells[-1].shell_inlet_enthalpy_j_kg
            h_s_out = cells[0].shell_outlet_enthalpy_j_kg
            m_tube = float(t173.effective_tube_mass_flow_kg_s())
            m_shell = float(t173.effective_shell_mass_flow_kg_s())
            q_hot = m_tube * (h_t_in - h_t_out)
            q_cold = m_shell * (h_s_out - h_s_in)
            q_total = sum(cell.heat_rate_w for cell in cells)
            duty = q_total
            denom = max(abs(q_hot), abs(q_cold), 1.0)
            energy_rel = abs(q_hot - q_cold) / denom
            diagnostics.append(f"q_hot_minus_q_cold_w={q_hot - q_cold}")
            diagnostics.append(f"q_hot_minus_q_total_w={q_hot - q_total}")
            diagnostics.append(f"q_cold_minus_q_total_w={q_cold - q_total}")
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
            result = EngineeringRatingResult(
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
                picard_iterations=solver_nfev,
                coolprop_stats=coolprop_stats,
                wall_seconds=elapsed,
                correlation_notes=correlation_notes,
            )
            if mesh_result_cache is not None:
                mesh_result_cache[subdivisions] = result
            return result
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
    duty_seed_w: float | None = None,
) -> float:
    """Constant-U global Q solve (same face-enthalpy structure as engineering core)."""
    n = int(n_cells)
    ua_cell = u_a_total_w_per_k / n
    m_hot = hot_capacity_w_per_k
    m_cold = cold_capacity_w_per_k
    th_in = hot_inlet_k
    tc_in = cold_inlet_k

    def temperatures_from_q(q: np.ndarray) -> tuple[list[float], list[float]]:
        th = [th_in]
        tc = [0.0] * (n + 1)
        tc[n] = tc_in
        for i in range(n):
            th.append(th[i] - float(q[i]) / m_hot)
        for i in range(n - 1, -1, -1):
            tc[i] = tc[i + 1] + float(q[i]) / m_cold
        return th, tc

    def residuals(q_raw: np.ndarray) -> np.ndarray:
        q_vec = np.maximum(q_raw, 0.0)
        th, tc = temperatures_from_q(q_vec)
        out = np.zeros(n, dtype=float)
        for i in range(n):
            dt = th[i] - tc[i + 1]
            if dt <= 0.0:
                raise ValueError("temperature_crossing")
            out[i] = q_vec[i] - ua_cell * dt
        return out

    if duty_seed_w is not None and duty_seed_w > 0.0:
        q0 = np.full(n, duty_seed_w / n, dtype=float)
    else:
        q0 = np.full(n, ua_cell * max(th_in - tc_in, 1.0) / n)
    solution = least_squares(
        residuals,
        q0,
        bounds=(np.zeros(n), np.full(n, np.inf)),
        method="trf",
        max_nfev=400,
    )
    if not solution.success:
        raise RuntimeError("constant_u_global_q_failed")
    th, _tc = temperatures_from_q(np.maximum(solution.x, 0.0))
    return m_hot * (th_in - th[n])


def _duty_relative_change(a: float | None, b: float | None) -> float | None:
    if a is None or b is None or abs(a) < 1e-9:
        return None
    return abs(b - a) / abs(a)


def _outlet_temperature_delta_k(
    left: EngineeringRatingResult, right: EngineeringRatingResult
) -> tuple[float | None, float | None]:
    if (
        left.tube_outlet_temperature_k is None
        or right.tube_outlet_temperature_k is None
        or left.shell_outlet_temperature_k is None
        or right.shell_outlet_temperature_k is None
    ):
        return None, None
    return (
        abs(right.tube_outlet_temperature_k - left.tube_outlet_temperature_k),
        abs(right.shell_outlet_temperature_k - left.shell_outlet_temperature_k),
    )


def compute_mesh_convergence_flags(
    results: dict[int, EngineeringRatingResult],
    *,
    limits: EngineeringAcceptanceLimits | None = None,
) -> dict[str, Any]:
    """Derive R26C mesh stability flags from already-solved mesh results."""
    limits = limits or EngineeringAcceptanceLimits()
    meshes = (1, 2, 4)
    r12 = _duty_relative_change(results[1].duty_w, results[2].duty_w)
    r24 = _duty_relative_change(results[2].duty_w, results[4].duty_w)
    n1_n2_out = _outlet_temperature_delta_k(results[1], results[2])
    n2_n4_out = _outlet_temperature_delta_k(results[2], results[4])
    all_numeric_valid = all(results[n].status == ENGINEERING_NUMERIC_VALID for n in meshes)
    duty_mesh_stable = (
        all_numeric_valid
        and r12 is not None
        and r24 is not None
        and r12 <= _MESH_DUTY_REL_TOL
        and r24 <= _MESH_DUTY_REL_TOL
    )
    outlet_temperature_mesh_stable = False
    if all_numeric_valid and n1_n2_out[0] is not None and n2_n4_out[0] is not None:
        outlet_temperature_mesh_stable = (
            n1_n2_out[0] <= _MESH_OUTLET_REL_TOL_K
            and n1_n2_out[1] is not None
            and n1_n2_out[1] <= _MESH_OUTLET_REL_TOL_K
            and n2_n4_out[0] <= _MESH_OUTLET_REL_TOL_K
            and n2_n4_out[1] is not None
            and n2_n4_out[1] <= _MESH_OUTLET_REL_TOL_K
        )
    local_closure_valid = all_numeric_valid and _local_closure_valid(results[4], limits)
    full_rating_converged = (
        duty_mesh_stable and outlet_temperature_mesh_stable and local_closure_valid
    )
    return {
        "n1_n2_duty_relative_change": r12,
        "n2_n4_duty_relative_change": r24,
        "n1_n2_tube_outlet_delta_k": n1_n2_out[0],
        "n1_n2_shell_outlet_delta_k": n1_n2_out[1],
        "n2_n4_tube_outlet_delta_k": n2_n4_out[0],
        "n2_n4_shell_outlet_delta_k": n2_n4_out[1],
        "DUTY_MESH_STABLE": duty_mesh_stable,
        "OUTLET_TEMPERATURE_MESH_STABLE": outlet_temperature_mesh_stable,
        "LOCAL_CLOSURE_VALID": local_closure_valid,
        "FULL_RATING_CONVERGED": full_rating_converged,
        "full_rating_converged": full_rating_converged,
    }


def evaluate_mesh_convergence(
    case: EngineeringCase,
    *,
    native: NativeCellContext | None = None,
    mesh_result_cache: dict[int, EngineeringRatingResult] | None = None,
    limits: EngineeringAcceptanceLimits | None = None,
) -> dict[str, Any]:
    """Run n=1,2,4 sequentially with optional cache (no duplicate parent mesh solves)."""
    limits = limits or EngineeringAcceptanceLimits()
    meshes = (1, 2, 4)
    cache = mesh_result_cache if mesh_result_cache is not None else {}
    results: dict[int, EngineeringRatingResult] = {}
    for n in meshes:
        results[n] = run_experimental_engineering_rating(
            case,
            subdivisions=n,
            native=native,
            limits=limits,
            mesh_result_cache=cache,
        )

    flags = compute_mesh_convergence_flags(results, limits=limits)
    per_mesh: dict[int, dict[str, Any]] = {}
    for n in meshes:
        res = results[n]
        per_mesh[n] = {
            "duty_w": res.duty_w,
            "tube_outlet_temperature_k": res.tube_outlet_temperature_k,
            "shell_outlet_temperature_k": res.shell_outlet_temperature_k,
            "max_cell_thermal_residual_w": res.max_cell_thermal_residual_w,
            "max_inner_wall_outer_closure_residual_w": res.max_inner_wall_outer_closure_residual_w,
            "min_cell_approach_temperature_k": _min_cell_approach_temperature_k(res),
            "energy_balance_relative_error": res.energy_balance_relative_error,
            "wall_seconds": res.wall_seconds,
            "status": res.status,
        }
    return {
        "schema_version": "hxforge.experimental-engineering-mesh-convergence.v26c",
        "results": results,
        "per_mesh": per_mesh,
        **flags,
    }
