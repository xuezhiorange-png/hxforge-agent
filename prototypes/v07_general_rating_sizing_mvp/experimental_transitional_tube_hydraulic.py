"""Experimental transitional tube friction (Churchill 1977) — opt-in only (R20).

Does not modify frozen Task027 Colebrook/laminar/gap policy.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal, localcontext
from typing import Any, Literal

from hexagent.exchangers.shell_tube.tube_side.friction_pressure_drop import (
    FRICTION_FACTOR_QUANTUM,
    LAMINAR_UPPER_RE,
    PRESSURE_DROP_QUANTUM,
    TURBULENT_LOWER_RE,
    AbsoluteRoughnessAuthority,
    SmoothRoughnessAuthority,
    _task027_decimal_context,
    classify_reynolds,
    compute_pressure_drop,
    compute_relative_roughness,
    quantize_roughness,
    validate_relative_roughness,
)
from hexagent.exchangers.shell_tube.tube_side_local_loss.result import Task028SuccessResult

EXPERIMENTAL_TRANSITIONAL_TUBE_HYDRAULIC_SCOPE = "EXPERIMENTAL_TRANSITIONAL_TUBE_HYDRAULIC"
FRICTION_CORRELATION_ID = "CHURCHILL_1977_UNIVERSAL"
FRICTION_FACTOR_CONVENTION = "DARCY"
APPLICABILITY_STATUS = "EXPERIMENTAL_TRANSITIONAL_APPLICABLE"
UNCERTAINTY_DISCLOSURE = (
    "Transitional Reynolds band (2000<Re<4000): Churchill 1977 is an engineering estimate only; "
    "not production Task027 authority."
)

Blocker = dict[str, str]


def experimental_transitional_tube_hydraulic_enabled(case: Any) -> bool:
    return bool(getattr(case, "experimental_transitional_tube_hydraulic", False))


def fanning_from_darcy(darcy_f: Decimal) -> Decimal:
    return darcy_f / Decimal(4)


def darcy_from_fanning(fanning_f: Decimal) -> Decimal:
    return fanning_f * Decimal(4)


def churchill_1977_darcy_friction_factor(
    reynolds: Decimal,
    relative_roughness: Decimal,
) -> Decimal:
    """Churchill (1977) universal Darcy friction factor (ACHP / original paper form)."""
    if reynolds <= Decimal(0):
        raise ValueError("reynolds must be positive")
    if relative_roughness < Decimal(0) or relative_roughness > Decimal("0.05"):
        raise ValueError("relative_roughness must be in [0, 0.05]")

    re_f = float(reynolds)
    eps_d = float(relative_roughness)
    term_inner = (7.0 / re_f) ** 0.9 + 0.27 * eps_d
    if term_inner <= 0.0 or not math.isfinite(term_inner):
        raise ValueError("invalid Churchill inner term")
    a = (-2.457 * math.log(term_inner)) ** 16
    b = (37530.0 / re_f) ** 16
    inner = (8.0 / re_f) ** 12 + (a + b) ** (-1.5)
    if inner <= 0.0 or not math.isfinite(inner):
        raise ValueError("invalid Churchill combination term")
    f_d = 8.0 * (inner ** (1.0 / 12.0))
    if not math.isfinite(f_d) or f_d <= 0.0:
        raise ValueError("Churchill friction factor non-positive or non-finite")
    ctx = _task027_decimal_context()
    with localcontext(ctx):
        return Decimal(str(f_d)).quantize(FRICTION_FACTOR_QUANTUM)


def transitional_reynolds_applicable(reynolds: Decimal) -> bool:
    return LAMINAR_UPPER_RE < reynolds < TURBULENT_LOWER_RE


def resolve_relative_roughness(
    roughness_authority: SmoothRoughnessAuthority | AbsoluteRoughnessAuthority,
    hydraulic_diameter_m: Decimal,
) -> tuple[Decimal | None, list[Blocker]]:
    if isinstance(roughness_authority, SmoothRoughnessAuthority):
        return Decimal(0), []
    quantized_absolute = quantize_roughness(roughness_authority.absolute_roughness_m)
    relative_roughness = compute_relative_roughness(quantized_absolute, hydraulic_diameter_m)
    rr_blockers = validate_relative_roughness(relative_roughness)
    if rr_blockers:
        return None, [
            {
                "code": str(entry.code.value),
                "scope": "TASK027_ROUGHNESS",
                "detail": "relative roughness out of envelope for transitional model",
            }
            for entry in rr_blockers
        ]
    return relative_roughness, []


def sum_task028_local_loss_pa(result028: Task028SuccessResult) -> Decimal:
    total = Decimal(0)
    for component in result028.component_results:
        total += component.component_irreversible_pressure_loss_pa
    ctx = _task027_decimal_context()
    with localcontext(ctx):
        return total.quantize(PRESSURE_DROP_QUANTUM)


@dataclass(frozen=True)
class ExperimentalTransitionalTubeHydraulicResult:
    status: Literal["SUCCESS", "BLOCKED"]
    blockers: tuple[Blocker, ...]
    disclosure: dict[str, str]
    friction_dp_pa: Decimal | None
    local_loss_dp_pa: Decimal | None
    total_tube_dp_pa: Decimal | None
    task028_component_count: int
    task028_component_completeness: Literal["COMPLETE", "BLOCKED"]


def compute_experimental_transitional_tube_hydraulic(
    *,
    task025_result: Any,
    task026_result: Any,
    property_snapshot: Any,
    roughness_authority: SmoothRoughnessAuthority | AbsoluteRoughnessAuthority,
    task028_result: Task028SuccessResult | None,
) -> ExperimentalTransitionalTubeHydraulicResult:
    blockers: list[Blocker] = []
    reynolds = task026_result.reynolds_number
    regime = classify_reynolds(reynolds)
    if regime != "gap":
        blockers.append(
            {
                "code": "BL_R20_TRANSITION_REYNOLDS_OUT_OF_SCOPE",
                "scope": "EXPERIMENTAL_TRANSITIONAL_TUBE_HYDRAULIC",
                "detail": f"Churchill transitional model requires 2000<Re<4000; regime={regime}",
            }
        )
        return ExperimentalTransitionalTubeHydraulicResult(
            status="BLOCKED",
            blockers=tuple(blockers),
            disclosure={},
            friction_dp_pa=None,
            local_loss_dp_pa=None,
            total_tube_dp_pa=None,
            task028_component_count=0,
            task028_component_completeness="BLOCKED",
        )

    rel_rough, rr_blockers = resolve_relative_roughness(
        roughness_authority, task025_result.hydraulic_diameter_m
    )
    blockers.extend(rr_blockers)
    if rel_rough is None:
        return ExperimentalTransitionalTubeHydraulicResult(
            status="BLOCKED",
            blockers=tuple(blockers),
            disclosure={},
            friction_dp_pa=None,
            local_loss_dp_pa=None,
            total_tube_dp_pa=None,
            task028_component_count=0,
            task028_component_completeness="BLOCKED",
        )

    if task028_result is None:
        blockers.append(
            {
                "code": "BL_R20_TASK028_INCOMPLETE",
                "scope": "TASK028",
                "detail": "local loss components required for complete tube ΔP",
            }
        )
        return ExperimentalTransitionalTubeHydraulicResult(
            status="BLOCKED",
            blockers=tuple(blockers),
            disclosure={},
            friction_dp_pa=None,
            local_loss_dp_pa=None,
            total_tube_dp_pa=None,
            task028_component_count=0,
            task028_component_completeness="BLOCKED",
        )

    try:
        darcy_f = churchill_1977_darcy_friction_factor(reynolds, rel_rough)
    except (ValueError, ArithmeticError) as exc:
        blockers.append(
            {
                "code": "BL_R20_CHURCHILL_EVALUATION_FAILED",
                "scope": "EXPERIMENTAL_TRANSITIONAL_TUBE_HYDRAULIC",
                "detail": str(exc),
            }
        )
        return ExperimentalTransitionalTubeHydraulicResult(
            status="BLOCKED",
            blockers=tuple(blockers),
            disclosure={},
            friction_dp_pa=None,
            local_loss_dp_pa=None,
            total_tube_dp_pa=None,
            task028_component_count=len(task028_result.component_results),
            task028_component_completeness="BLOCKED",
        )

    friction_length_m = task025_result.internal_flow_authority.length_m
    friction_dp_raw = compute_pressure_drop(
        darcy_friction_factor=darcy_f,
        friction_length_m=friction_length_m,
        hydraulic_diameter_m=task025_result.hydraulic_diameter_m,
        density_kg_m3=property_snapshot.density_kg_m3,
        bulk_velocity_m_s=task026_result.bulk_velocity_m_s,
    )
    ctx = _task027_decimal_context()
    with localcontext(ctx):
        friction_dp = friction_dp_raw.quantize(PRESSURE_DROP_QUANTUM)
        local_dp = sum_task028_local_loss_pa(task028_result)
        total_dp = (friction_dp + local_dp).quantize(PRESSURE_DROP_QUANTUM)

    disclosure = {
        "hydraulic_model_scope": EXPERIMENTAL_TRANSITIONAL_TUBE_HYDRAULIC_SCOPE,
        "friction_correlation_id": FRICTION_CORRELATION_ID,
        "friction_factor_convention": FRICTION_FACTOR_CONVENTION,
        "task025_total_parallel_flow_area_m2": str(task025_result.total_parallel_flow_area_m2),
        "task025_hydraulic_diameter_m": str(task025_result.hydraulic_diameter_m),
        "bulk_velocity_m_s": str(task026_result.bulk_velocity_m_s),
        "reynolds_number": str(reynolds),
        "relative_roughness": str(rel_rough),
        "darcy_friction_factor": str(darcy_f),
        "fanning_friction_factor": str(fanning_from_darcy(darcy_f)),
        "tube_friction_dp_pa": str(friction_dp),
        "tube_local_loss_dp_pa": str(local_dp),
        "total_tube_dp_pa": str(total_dp),
        "correlation_applicability_status": APPLICABILITY_STATUS,
        "uncertainty_disclosure": UNCERTAINTY_DISCLOSURE,
        "task028_component_count": str(len(task028_result.component_results)),
        "task028_component_completeness": "COMPLETE",
        "legacy_task027_path": "UNCHANGED_FROZEN_GAP_FAIL_CLOSED",
        "legacy_task029_path": "NOT_USED_FOR_EXPERIMENTAL_TOTAL",
    }
    return ExperimentalTransitionalTubeHydraulicResult(
        status="SUCCESS",
        blockers=(),
        disclosure=disclosure,
        friction_dp_pa=friction_dp,
        local_loss_dp_pa=local_dp,
        total_tube_dp_pa=total_dp,
        task028_component_count=len(task028_result.component_results),
        task028_component_completeness="COMPLETE",
    )
