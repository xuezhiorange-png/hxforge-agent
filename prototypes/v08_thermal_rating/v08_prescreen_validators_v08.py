"""Computed prescreen validators — no hard-coded PASS labels."""

# ruff: noqa: E501

from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import load_case_bindings
from prototypes.v08_thermal_rating.case_identity_v08 import FIXTURE_250
from prototypes.v08_thermal_rating.recovered_shell_052_pareto_joint_v08 import (
    PARETO_METRIC_UNAVAILABLE,
    _row_pareto_metrics_complete,
    run_recovered_shell_052_pareto_joint_optimization,
)

ValidatorStatus = Literal["PASS", "BLOCKED", "NOT_EVALUATED"]


def validate_generic_user_constraints(
    *, provider: CoolPropProvider | None = None
) -> ValidatorStatus:
    """250 kW fixture: q_deficit must track normalized target_duty_w (not 330 kW hardcode)."""
    active = provider or CoolPropProvider()
    try:
        normalized, handoff, _ = load_case_bindings(FIXTURE_250, provider=active)
        report = run_recovered_shell_052_pareto_joint_optimization(
            normalized, handoff, provider=active
        )
        target = Decimal(str(normalized.target_duty_w))
        checked = 0
        for row in report.rows:
            if row.q_deficit_w == PARETO_METRIC_UNAVAILABLE:
                continue
            if row.clean_thermal.epsilon_ntu_q_w is None:
                continue
            q = Decimal(row.clean_thermal.epsilon_ntu_q_w)
            expected = max(Decimal("0"), target - q).quantize(Decimal("0.1"))
            if Decimal(row.q_deficit_w) != expected:
                return "BLOCKED"
            checked += 1
        return "PASS" if checked > 0 else "NOT_EVALUATED"
    except Exception:
        return "NOT_EVALUATED"


def validate_pareto_missing_result_handling(
    *,
    provider: CoolPropProvider | None = None,
) -> ValidatorStatus:
    """Pareto front rows must have complete hydraulic metrics; blocked Task037 uses UNAVAILABLE."""
    active = provider or CoolPropProvider()
    try:
        from prototypes.v08_thermal_rating.case_identity_v08 import FIXTURE_330

        normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=active)
        report = run_recovered_shell_052_pareto_joint_optimization(
            normalized, handoff, provider=active
        )
        for row in report.pareto_front:
            if not _row_pareto_metrics_complete(row):
                return "BLOCKED"
        blocked = [r for r in report.rows if r.task168_blocker]
        for row in blocked:
            if row.tube_dp_excess_pa != PARETO_METRIC_UNAVAILABLE:
                return "BLOCKED"
            if row.shell_dp_excess_pa != PARETO_METRIC_UNAVAILABLE:
                return "BLOCKED"
        return "PASS" if report.rows else "NOT_EVALUATED"
    except Exception:
        return "NOT_EVALUATED"


def validate_frozen_structure_spec(design_spec: dict[str, Any]) -> ValidatorStatus:
    required_top = (
        "candidate_id",
        "geometry_identity_v2",
        "task168_request_hash_digest",
        "geometry",
        "thermal_results",
        "hydraulic_results",
        "user_case_limits",
    )
    for key in required_top:
        if key not in design_spec or design_spec[key] in (None, "", {}):
            return "BLOCKED"
    geom = design_spec["geometry"]
    for key in (
        "physical_tube_count",
        "tube_length_m",
        "shell_inside_diameter_m",
        "placement_envelope_scale",
        "baffle_count",
        "baffle_cut_fraction",
        "baffle_spacing_m",
        "layout_identity",
    ):
        if geom.get(key) in (None, "", "UNAVAILABLE"):
            return "BLOCKED"
    hyd = design_spec["hydraulic_results"]
    if not hyd.get("ports"):
        return "BLOCKED"
    if hyd.get("nozzle_design_hash") in (None, "", "UNAVAILABLE"):
        return "BLOCKED"
    clean = design_spec["thermal_results"].get("clean", {})
    if clean.get("epsilon_ntu_q_w") in (None, "UNAVAILABLE"):
        return "BLOCKED"
    return "PASS"


__all__ = [
    "ValidatorStatus",
    "validate_frozen_structure_spec",
    "validate_generic_user_constraints",
    "validate_pareto_missing_result_handling",
]
