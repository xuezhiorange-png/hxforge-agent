"""Hydraulic pressure-drop decomposition for engineering reports (R26F)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase


def _dec(value: Any) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def build_hydraulic_dp_breakdown(
    postpass: dict[str, Any] | None,
    *,
    case: EngineeringCase,
) -> dict[str, Any]:
    if not postpass:
        return {
            "status": "NOT_EVALUATED",
            "TUBE_FRICTION_DP_PA": None,
            "TUBE_LOCAL_LOSS_DP_PA": None,
            "TUBE_TOTAL_DP_PA": None,
            "SHELL_INTERNAL_DP_PA": None,
            "SHELL_NOZZLE_AND_LOCAL_DP_PA": None,
            "SHELL_TOTAL_DP_PA": None,
            "TUBE_DP_MARGIN_PA": None,
            "SHELL_DP_MARGIN_PA": None,
        }

    max_tube = case.max_tube_side_pressure_drop_pa
    max_shell = case.max_shell_side_pressure_drop_pa
    tube_total = _dec(postpass.get("recalculated_tube_dp_pa"))
    shell_total = _dec(postpass.get("recalculated_shell_dp_pa"))

    exp = postpass.get("experimental_transitional_tube_hydraulic") or {}
    tube_friction = _dec(exp.get("tube_friction_dp_pa"))
    tube_local = _dec(exp.get("tube_local_loss_dp_pa"))
    if tube_friction is None and tube_total is not None and tube_local is not None:
        tube_friction = tube_total - tube_local

    shell_parts = postpass.get("shell_dp_components_pa") or {}
    shell_internal = _dec(shell_parts.get("total"))
    if shell_internal is None and shell_total is not None:
        shell_internal = shell_total

    shell_nozzle_doc = postpass.get("shell_nozzle_local_loss_engineering")
    shell_nozzle_dp = _dec(
        (shell_nozzle_doc or {}).get("total_nozzle_and_transition_dp_pa")
    )
    if shell_nozzle_dp is None:
        shell_nozzle_dp = Decimal("0")
        shell_nozzle_status = "NOT_MODELED_INPUT_REQUIRED"
    else:
        shell_nozzle_status = "INCLUDED"

    tube_margin = (max_tube - tube_total) if tube_total is not None else None
    shell_margin = (max_shell - shell_total) if shell_total is not None else None

    components_audit = {
        "tube_local_loss_components": (
            (postpass.get("tube_local_loss_engineering") or {}).get(
                "computed_local_loss_components"
            )
            or []
        ),
        "shell_bell_delaware_components_pa": shell_parts,
        "shell_nozzle_path_status": shell_nozzle_status,
        "double_counting_guard": (
            "Shell nozzle/transition losses are excluded from Bell–Delaware internal total "
            "until authorized shell_hydraulic_path_engineering is supplied."
        ),
    }

    reconciliation_ok = None
    if tube_total is not None and tube_friction is not None and tube_local is not None:
        reconciliation_ok = abs((tube_friction + tube_local) - tube_total) <= Decimal("0.01")
    if shell_total is not None and shell_internal is not None:
        expected_shell = shell_internal + shell_nozzle_dp
        if reconciliation_ok is None:
            reconciliation_ok = abs(expected_shell - shell_total) <= Decimal("0.01")
        else:
            reconciliation_ok = reconciliation_ok and (
                abs(expected_shell - shell_total) <= Decimal("0.01")
            )

    return {
        "status": "COMPUTED" if tube_total is not None and shell_total is not None else "BLOCKED",
        "TUBE_FRICTION_DP_PA": str(tube_friction) if tube_friction is not None else None,
        "TUBE_LOCAL_LOSS_DP_PA": str(tube_local) if tube_local is not None else None,
        "TUBE_TOTAL_DP_PA": str(tube_total) if tube_total is not None else None,
        "SHELL_INTERNAL_DP_PA": str(shell_internal) if shell_internal is not None else None,
        "SHELL_NOZZLE_AND_LOCAL_DP_PA": str(shell_nozzle_dp),
        "SHELL_TOTAL_DP_PA": str(shell_total) if shell_total is not None else None,
        "TUBE_DP_MARGIN_PA": str(tube_margin) if tube_margin is not None else None,
        "SHELL_DP_MARGIN_PA": str(shell_margin) if shell_margin is not None else None,
        "component_audit": components_audit,
        "total_reconciliation_ok": reconciliation_ok,
    }


def tube_dp_components_summary(breakdown: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if breakdown.get("TUBE_FRICTION_DP_PA") is not None:
        rows.append(
            {
                "component_id": "TUBE_BUNDLE_FRICTION",
                "path": "TUBE_INTERNAL",
                "dp_pa": breakdown["TUBE_FRICTION_DP_PA"],
                "included_in_model": "R20_TRANSITIONAL_FRICTION",
            }
        )
    for comp in breakdown.get("component_audit", {}).get("tube_local_loss_components") or []:
        rows.append(
            {
                "component_id": comp.get("component_id"),
                "path": "TUBE_LOCAL_LOSS",
                "dp_pa": comp.get("component_irreversible_pressure_loss_pa"),
                "reference_flow_area_m2": comp.get("reference_flow_area_m2"),
                "loss_coefficient": comp.get("loss_coefficient"),
                "included_in_model": "TASK028",
            }
        )
    return rows


def shell_dp_components_summary(breakdown: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    parts = breakdown.get("component_audit", {}).get("shell_bell_delaware_components_pa") or {}
    for key in ("central_crossflow", "window", "end_zone"):
        if parts.get(key) is not None:
            rows.append(
                {
                    "component_id": f"SHELL_BD_{key.upper()}",
                    "path": "SHELL_INTERNAL_BELL_DELAWARE",
                    "dp_pa": parts[key],
                    "included_in_model": "TASK166",
                }
            )
    if breakdown.get("SHELL_NOZZLE_AND_LOCAL_DP_PA") not in (None, "0"):
        rows.append(
            {
                "component_id": "SHELL_NOZZLE_AND_TRANSITION",
                "path": "SHELL_EXTERNAL",
                "dp_pa": breakdown["SHELL_NOZZLE_AND_LOCAL_DP_PA"],
                "included_in_model": "NOT_MODELED",
            }
        )
    elif breakdown.get("component_audit", {}).get("shell_nozzle_path_status") == (
        "NOT_MODELED_INPUT_REQUIRED"
    ):
        rows.append(
            {
                "component_id": "SHELL_INLET_OUTLET_NOZZLE",
                "path": "SHELL_EXTERNAL",
                "dp_pa": None,
                "included_in_model": "ENGINEERING_GEOMETRY_INPUT_REQUIRED",
            }
        )
    return rows
