"""Hydraulic constraint decision source for experimental sizing (R15)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase

HYDRAULIC_DECISION_SOURCE_REFERENCE = "HYDRAULIC_REFERENCE_MODEL_PREVIEW"
HYDRAULIC_DECISION_SOURCE_LIVE = "EXPERIMENTAL_LIVE_THERMAL_STATE_HYDRAULIC_POSTPASS"


def live_hydraulic_postpass_enabled(case: EngineeringCase) -> bool:
    return bool(getattr(case, "experimental_live_thermal_hydraulic_postpass", False))


def _rating_numeric_valid(row: dict[str, Any]) -> bool:
    return row.get("mesh_status") == "NUMERIC_VALID" or row.get("status") == "NUMERIC_VALID"


def _preview_constraint_status(
    case: EngineeringCase,
    *,
    rating_status: str,
    constraint_preview: dict[str, Any] | None,
    row: dict[str, Any] | None = None,
) -> str:
    if rating_status != "NUMERIC_VALID":
        return "NOT_EVALUATED"
    if constraint_preview is None:
        return "NOT_EVALUATED"
    duty_w = row.get("total_duty_w") if row else constraint_preview.get("rated_duty_w")
    if duty_w is None:
        duty_ok = constraint_preview.get("duty_constraint") == "SATISFIED"
    else:
        duty_ok = Decimal(str(duty_w)) >= case.target_duty_w

    tube_dp_val = constraint_preview.get("modeled_tube_dp_pa")
    shell_dp_val = constraint_preview.get("modeled_shell_dp_pa")
    if tube_dp_val is None or shell_dp_val is None:
        tube_dp = constraint_preview.get("tube_dp_constraint")
        shell_dp = constraint_preview.get("shell_dp_constraint")
        if duty_w is None and (
            constraint_preview.get("duty_constraint") == "NOT_EVALUATED"
            or tube_dp == "NOT_EVALUATED"
            or shell_dp == "NOT_EVALUATED"
        ):
            return "NOT_EVALUATED"
        tube_ok = tube_dp == "SATISFIED"
        shell_ok = shell_dp == "SATISFIED"
    else:
        tube_ok = Decimal(str(tube_dp_val)) <= case.max_tube_side_pressure_drop_pa
        shell_ok = Decimal(str(shell_dp_val)) <= case.max_shell_side_pressure_drop_pa

    if duty_ok and tube_ok and shell_ok:
        return "PRELIMINARY_CONSTRAINT_SATISFIED"
    if duty_w is None and constraint_preview.get("duty_constraint") == "NOT_EVALUATED":
        return "NOT_EVALUATED"
    return "PRELIMINARY_CONSTRAINT_FAILED"


def _live_hydraulic_constraint_status(
    case: EngineeringCase,
    row: dict[str, Any],
    *,
    rating_status: str,
) -> str:
    if rating_status != "NUMERIC_VALID":
        return "NOT_EVALUATED"
    duty_w = row.get("total_duty_w")
    if duty_w is None:
        return "NOT_EVALUATED"
    if Decimal(str(duty_w)) < case.target_duty_w:
        return "PRELIMINARY_CONSTRAINT_FAILED"

    postpass = row.get("live_thermal_state_hydraulic_postpass")
    if postpass is None:
        return "NOT_EVALUATED"

    applicability = postpass.get("correlation_applicability_status")
    if applicability not in {None, "APPLICABLE"}:
        return "PRELIMINARY_CONSTRAINT_FAILED"

    hydraulic_status = postpass.get("hydraulic_constraint_status")
    if hydraulic_status == "BLOCKED":
        return "PRELIMINARY_CONSTRAINT_FAILED"
    if hydraulic_status in {None, "NOT_EVALUATED"}:
        return "NOT_EVALUATED"
    if hydraulic_status == "NOT_SATISFIED":
        return "PRELIMINARY_CONSTRAINT_FAILED"
    if hydraulic_status == "SATISFIED":
        tube_c = postpass.get("tube_dp_constraint")
        shell_c = postpass.get("shell_dp_constraint")
        if tube_c != "SATISFIED" or shell_c != "SATISFIED":
            return "PRELIMINARY_CONSTRAINT_FAILED"
        if postpass.get("task174_style_outlet_pressure_window_pass") is False:
            return "PRELIMINARY_CONSTRAINT_FAILED"
        return "PRELIMINARY_CONSTRAINT_SATISFIED"
    return "NOT_EVALUATED"


def build_hydraulic_constraint_decision(
    case: EngineeringCase,
    row: dict[str, Any],
    *,
    rating_status: str,
) -> dict[str, Any]:
    preview = row.get("constraint_preview") or {}
    postpass = row.get("live_thermal_state_hydraulic_postpass")
    reference_status = _preview_constraint_status(
        case,
        rating_status=rating_status,
        constraint_preview=preview if preview else None,
        row=row,
    )
    use_live = live_hydraulic_postpass_enabled(case)
    source = HYDRAULIC_DECISION_SOURCE_LIVE if use_live else HYDRAULIC_DECISION_SOURCE_REFERENCE
    live_status = (
        _live_hydraulic_constraint_status(case, row, rating_status=rating_status)
        if use_live
        else None
    )
    effective_status = live_status if use_live else reference_status

    ref_feasible = reference_status == "PRELIMINARY_CONSTRAINT_SATISFIED"
    live_feasible = (
        live_status == "PRELIMINARY_CONSTRAINT_SATISFIED" if live_status is not None else None
    )
    eff_feasible = effective_status == "PRELIMINARY_CONSTRAINT_SATISFIED"
    feasibility_changed = None
    if use_live and live_status is not None:
        feasibility_changed = ref_feasible != eff_feasible

    blockers = list(postpass.get("blockers") or []) if postpass else []

    return {
        "schema_version": "hxforge.experimental-hydraulic-constraint-decision.v1",
        "hydraulic_decision_source": source,
        "REFERENCE_CONSTRAINT_STATUS": reference_status,
        "LIVE_HYDRAULIC_CONSTRAINT_STATUS": live_status,
        "EFFECTIVE_CONSTRAINT_STATUS": effective_status,
        "reference_feasible": ref_feasible,
        "live_feasible": live_feasible,
        "effective_feasible": eff_feasible,
        "reference_vs_live_feasibility_changed": feasibility_changed,
        "target_duty_w": str(case.target_duty_w),
        "rated_duty_w": row.get("total_duty_w"),
        "max_tube_dp_pa": str(case.max_tube_side_pressure_drop_pa),
        "max_shell_dp_pa": str(case.max_shell_side_pressure_drop_pa),
        "reference_tube_dp_pa": preview.get("modeled_tube_dp_pa"),
        "reference_shell_dp_pa": preview.get("modeled_shell_dp_pa"),
        "reference_tube_dp_constraint": preview.get("tube_dp_constraint"),
        "reference_shell_dp_constraint": preview.get("shell_dp_constraint"),
        "live_recalculated_tube_dp_pa": (
            postpass.get("recalculated_tube_dp_pa") if postpass else None
        ),
        "live_recalculated_shell_dp_pa": (
            postpass.get("recalculated_shell_dp_pa") if postpass else None
        ),
        "live_tube_dp_constraint": postpass.get("tube_dp_constraint") if postpass else None,
        "live_shell_dp_constraint": postpass.get("shell_dp_constraint") if postpass else None,
        "live_hydraulic_constraint_status": (
            postpass.get("hydraulic_constraint_status") if postpass else None
        ),
        "correlation_applicability_status": (
            postpass.get("correlation_applicability_status") if postpass else None
        ),
        "tube_outlet_pressure_pa": (postpass.get("tube_outlet_pressure_pa") if postpass else None),
        "shell_outlet_pressure_pa": (
            postpass.get("shell_outlet_pressure_pa") if postpass else None
        ),
        "task174_style_outlet_pressure_window_pass": (
            postpass.get("task174_style_outlet_pressure_window_pass") if postpass else None
        ),
        "postpass_blockers": blockers,
        "live_postpass_present": postpass is not None,
    }


def effective_constraint_status_for_row(case: EngineeringCase, row: dict[str, Any]) -> str:
    from prototypes.v07_general_rating_sizing_mvp.experimental_candidate_eligibility import (
        _rating_status,
    )

    rating_status = _rating_status(row.get("mesh_status") or row.get("status"))
    decision = build_hydraulic_constraint_decision(case, row, rating_status=rating_status)
    return str(decision["EFFECTIVE_CONSTRAINT_STATUS"])


def effective_shell_dp_pa(case: EngineeringCase, row: dict[str, Any]) -> Decimal | None:
    if live_hydraulic_postpass_enabled(case):
        postpass = row.get("live_thermal_state_hydraulic_postpass") or {}
        raw = postpass.get("recalculated_shell_dp_pa")
        if raw is not None:
            return Decimal(str(raw))
    preview = row.get("constraint_preview") or {}
    raw = preview.get("modeled_shell_dp_pa")
    if raw is None:
        return None
    return Decimal(str(raw))


def build_live_hydraulic_sizing_summary(
    case: EngineeringCase,
    rating_rows: list[dict[str, Any]],
    *,
    ranking: dict[str, Any] | None = None,
    target_directed_decision: dict[str, Any] | None = None,
) -> dict[str, Any]:
    decisions = []
    for row in rating_rows:
        from prototypes.v07_general_rating_sizing_mvp.experimental_candidate_eligibility import (
            _rating_status,
        )

        mesh_status = row.get("mesh_status") or row.get("status")
        rating_status = _rating_status(mesh_status)
        decisions.append(
            {
                "candidate_id": row.get("candidate_id"),
                **build_hydraulic_constraint_decision(case, row, rating_status=rating_status),
            }
        )
    enabled = live_hydraulic_postpass_enabled(case)
    return {
        "schema_version": "hxforge.live-hydraulic-sizing-summary.v1",
        "live_thermal_state_hydraulic_postpass_enabled": enabled,
        "hydraulic_decision_source": (
            HYDRAULIC_DECISION_SOURCE_LIVE if enabled else HYDRAULIC_DECISION_SOURCE_REFERENCE
        ),
        "disclosure": (
            "Sizing eligibility and ranking use live thermal-state hydraulic post-pass results."
            if enabled
            else "Sizing eligibility and ranking use Task174 reference hydraulic preview only."
        ),
        "per_candidate": decisions,
        "feasible_candidate_ids": (ranking or {}).get("feasible_candidate_ids"),
        "target_directed_decision": target_directed_decision,
        "production_sizing_verified": False,
    }


def append_hydraulic_sizing_markdown_lines(
    lines: list[str],
    *,
    case: EngineeringCase,
    row: dict[str, Any] | None,
    decision: dict[str, Any] | None,
) -> None:
    enabled = live_hydraulic_postpass_enabled(case)
    lines.extend(["## Hydraulic constraint decision (experimental)", ""])
    if not enabled:
        lines.append(
            "- Live thermal-state hydraulic post-pass: **disabled** "
            "(reference Task174 preview used for constraint checks)."
        )
        if decision:
            lines.append(
                f"- Constraint decision source: **{decision.get('hydraulic_decision_source')}**"
            )
        lines.append("")
        return

    lines.append("- Live thermal-state hydraulic post-pass: **enabled**")
    if decision is None and row is not None:
        from prototypes.v07_general_rating_sizing_mvp.experimental_candidate_eligibility import (
            _rating_status,
        )

        mesh_status = row.get("mesh_status") or row.get("status")
        decision = build_hydraulic_constraint_decision(
            case, row, rating_status=_rating_status(mesh_status)
        )
    if decision is None:
        lines.append("- No rated candidate hydraulic decision available.")
        lines.append("")
        return

    lines.append(f"- Constraint decision source: **{decision.get('hydraulic_decision_source')}**")
    lines.append(f"- Reference shell Δp: {decision.get('reference_shell_dp_pa')} Pa")
    lines.append(f"- Live shell Δp: {decision.get('live_recalculated_shell_dp_pa')} Pa")
    lines.append(f"- Shell Δp limit: {decision.get('max_shell_dp_pa')} Pa")
    lines.append(
        f"- Reference constraints: duty/ref hydraulics → "
        f"**{decision.get('REFERENCE_CONSTRAINT_STATUS')}**"
    )
    lines.append(
        f"- Live hydraulic constraints → **{decision.get('LIVE_HYDRAULIC_CONSTRAINT_STATUS')}**"
    )
    eff = decision.get("EFFECTIVE_CONSTRAINT_STATUS")
    lines.append(f"- Effective sizing eligibility: **{eff}**")
    changed = decision.get("reference_vs_live_feasibility_changed")
    if changed is not None:
        lines.append(f"- Reference vs live feasibility changed: **{changed}**")
    lines.append(f"- Correlation applicability: {decision.get('correlation_applicability_status')}")
    lines.append(
        f"- Outlet pressures (Pa): tube {decision.get('tube_outlet_pressure_pa')}, "
        f"shell {decision.get('shell_outlet_pressure_pa')}"
    )
    blockers = decision.get("postpass_blockers") or []
    if blockers:
        lines.append(f"- Post-pass blockers: `{blockers}`")
    elif decision.get("live_hydraulic_constraint_status") == "BLOCKED":
        lines.append("- Post-pass blockers: present (hydraulic status BLOCKED)")
    lines.append("")
