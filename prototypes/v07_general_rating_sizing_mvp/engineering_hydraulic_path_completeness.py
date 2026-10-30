"""Engineering completeness checks for authorized full-path hydraulics (R26G)."""

# ruff: noqa: E501

from __future__ import annotations

from typing import Any

from prototypes.v07_general_rating_sizing_mvp.engineering_hydraulic_path_input_v1 import (
    EngineeringHydraulicPathInputV1,
    HydraulicPathComponentV1,
)

REQUIRED_TUBE_TYPES_FOR_FULL_PATH = frozenset({"NOZZLE", "CHANNEL_HEAD", "ENTRANCE", "EXIT"})
REQUIRED_SHELL_EXTERNAL_TYPES_FOR_FULL_PATH = frozenset(
    {
        "SHELL_INLET_NOZZLE",
        "SHELL_OUTLET_NOZZLE",
        "SHELL_INLET_TRANSITION",
        "SHELL_OUTLET_TRANSITION",
    }
)

ENGINEERING_LIMITS_NOT_VERIFIED = (
    "Mechanical strength, vibration, tubesheet, fabrication, and code compliance "
    "are not verified by hydraulic path completeness."
)


def _sorted_components(
    components: tuple[HydraulicPathComponentV1, ...],
) -> list[HydraulicPathComponentV1]:
    return sorted(components, key=lambda c: c.path_sequence_index)


def assess_hydraulic_path_completeness(
    path_input: EngineeringHydraulicPathInputV1,
) -> dict[str, Any]:
    tube_types = {c.component_type for c in path_input.tube_side_components}
    shell_types = {c.component_type for c in path_input.shell_external_components}
    missing_tube = sorted(REQUIRED_TUBE_TYPES_FOR_FULL_PATH - tube_types)
    missing_shell = sorted(REQUIRED_SHELL_EXTERNAL_TYPES_FOR_FULL_PATH - shell_types)

    demo_only = any(
        c.engineering_input_status == "DEMONSTRATION"
        for c in (*path_input.tube_side_components, *path_input.shell_external_components)
    )
    authorized_only = all(
        c.engineering_input_status == "AUTHORIZED_ENGINEERING_INPUT"
        for c in (*path_input.tube_side_components, *path_input.shell_external_components)
    )

    sequence_ok_tube = _sequence_covers_inlet_to_outlet(
        _sorted_components(path_input.tube_side_components)
    )
    sequence_ok_shell = _sequence_covers_inlet_to_outlet(
        _sorted_components(path_input.shell_external_components)
    )

    if path_input.path_completeness_declaration != "FULL_TUBE_AND_SHELL_EXTERNAL_PATH":
        overall = "PARTIAL_DECLARED"
    elif missing_tube or missing_shell:
        overall = "INCOMPLETE_COMPONENT_COVERAGE"
    elif not sequence_ok_tube or not sequence_ok_shell:
        overall = "INCOMPLETE_SEQUENCE"
    elif demo_only:
        overall = "DEMONSTRATION_FULL_PATH_DECLARED"
    elif authorized_only:
        overall = "AUTHORIZED_INPUT_PRESENT"
    else:
        overall = "MIXED_INPUT_STATUS"

    return {
        "path_completeness_status": overall,
        "FULL_PATH_VERIFICATION_STATUS": (
            "NOT_VERIFIED"
            if overall != "AUTHORIZED_INPUT_PRESENT"
            else "INPUT_PRESENT_NOT_FULLY_VERIFIED"
        ),
        "missing_tube_component_types": missing_tube,
        "missing_shell_external_component_types": missing_shell,
        "tube_sequence_covers_inlet_to_outlet": sequence_ok_tube,
        "shell_external_sequence_covers_inlet_to_outlet": sequence_ok_shell,
        "demonstration_input_present": demo_only,
        "authorized_input_present": authorized_only,
        "double_counting_guard": path_input.bell_delaware_internal_scope,
        "engineering_limits_not_verified": ENGINEERING_LIMITS_NOT_VERIFIED,
        "disclosure": (
            "AUTHORIZED_INPUT_PRESENT does not upgrade to FULL_PATH_VERIFIED; "
            "two nozzle components alone do not imply equipment path completeness."
        ),
    }


def _sequence_covers_inlet_to_outlet(components: list[HydraulicPathComponentV1]) -> bool:
    if len(components) < 2:
        return False
    indices = [c.path_sequence_index for c in components]
    if indices != sorted(indices):
        return False
    return len(set(indices)) == len(indices)
