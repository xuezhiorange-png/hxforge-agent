"""Equipment-side mass flow binding for experimental live hydraulic post-pass (R19A)."""

from __future__ import annotations

from decimal import Decimal

from prototypes.v07_general_rating_sizing_mvp.case_streams import (
    shell_stream_spec,
    tube_stream_spec,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase

# Task168 implementation-validation Task026 templates may carry sub-equipment reference
# flows (historically ~0.499 kg/s). Engineering cases express equipment-side totals
# (12 kg/s tube, 20 kg/s shell) that must pair with Task025 total_parallel_flow_area_m2.

TASK172_EQUIPMENT_TOTAL_MASS_FLOW_DEFINITION = (
    "Task172 local constitutive requests use equipment-side total tube/shell mass "
    "flow_kg_s from the active experimental thermal boundary (same totals as the "
    "engineering case tube_side/shell_side streams)."
)


def equipment_tube_mass_flow_kg_s(case: EngineeringCase) -> Decimal:
    """Total tube-side mass flow through Task025 total_parallel_flow_area_m2."""
    return tube_stream_spec(case).mass_flow_kg_s


def equipment_shell_mass_flow_kg_s(case: EngineeringCase) -> Decimal:
    """Total shell-side mass flow for Task032 mass-flow authority."""
    return shell_stream_spec(case).mass_flow_kg_s


def live_postpass_binding_document(
    *,
    case: EngineeringCase,
    task026_input_mass_flow_kg_s: Decimal,
    task032_input_mass_flow_kg_s: Decimal,
    task025_total_parallel_flow_area_m2: Decimal,
    historical_task026_template_mass_flow_kg_s: Decimal | None,
) -> dict[str, str]:
    tube_equipment = equipment_tube_mass_flow_kg_s(case)
    shell_equipment = equipment_shell_mass_flow_kg_s(case)
    return {
        "equipment_tube_mass_flow_kg_s": str(tube_equipment),
        "equipment_shell_mass_flow_kg_s": str(shell_equipment),
        "task026_input_mass_flow_kg_s": str(task026_input_mass_flow_kg_s),
        "task032_input_mass_flow_kg_s": str(task032_input_mass_flow_kg_s),
        "task025_total_parallel_flow_area_m2": str(task025_total_parallel_flow_area_m2),
        "historical_task026_template_mass_flow_kg_s": (
            str(historical_task026_template_mass_flow_kg_s)
            if historical_task026_template_mass_flow_kg_s is not None
            else "UNKNOWN"
        ),
        "task172_mass_flow_definition": TASK172_EQUIPMENT_TOTAL_MASS_FLOW_DEFINITION,
        "tube_binding_status": (
            "MATCHED_EQUIPMENT_TOTAL"
            if task026_input_mass_flow_kg_s == tube_equipment
            else "MISMATCH"
        ),
        "shell_binding_status": (
            "MATCHED_EQUIPMENT_TOTAL"
            if task032_input_mass_flow_kg_s == shell_equipment
            else "MISMATCH"
        ),
    }
