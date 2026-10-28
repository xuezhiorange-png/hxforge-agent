"""Engineering hydraulic path geometry authority and completeness (R26F)."""

# ruff: noqa: E501

from __future__ import annotations

from decimal import Decimal
from typing import Any

from prototypes.v07_general_rating_sizing_mvp.candidate_selection import CandidateSelectionRecord
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase
from prototypes.v07_general_rating_sizing_mvp.engineering_tube_local_loss_geometry import (
    TubeLocalLossEngineeringInput,
    engineering_tube_local_loss_input,
    experimental_engineering_tube_local_loss_enabled,
)

_SCHEMA = "hxforge.engineering-hydraulic-path-geometry.v26f"

# Validated R26D long-baseline reference (4.85 m / 0.97 m / 0.56 m shell) — not re-rated every run.
R26D_HISTORICAL_LONG_BASELINE_REFERENCE: dict[str, str] = {
    "authority": "HISTORICAL_R26D_REFERENCE_NOT_IN_CURRENT_RATING_SET",
    "tube_length_m": "4.85",
    "baffle_spacing_m": "0.97",
    "shell_inside_diameter_m": "0.56",
    "physical_tube_count": "337",
    "nominal_tube_outer_area_m2": "97.8174849461698980665925",
    "note": "Reference geometry from R26D demonstration case; may be absent from current rating budget.",
}

REQUIRED_TUBE_PATH_COMPONENT_TYPES = frozenset(
    {"ENTRANCE", "EXIT", "CHANNEL_HEAD", "NOZZLE", "CONTRACTION", "EXPANSION"}
)
REQUIRED_SHELL_NOZZLE_ROLES = ("SHELL_INLET_NOZZLE", "SHELL_OUTLET_NOZZLE")


def candidate_geometry_from_selection_record(
    record: CandidateSelectionRecord,
) -> dict[str, Any]:
    """Authoritative Task168/Task021 geometry facts for reporting (no display overrides)."""
    return {
        "schema_version": _SCHEMA,
        "geometry_authority": "TASK168_TASK021_SELECTION_RECORD",
        "candidate_id": record.candidate_id,
        "candidate_hash": record.candidate_hash,
        "geometry_projection_hash": record.geometry_projection_hash,
        "shell_inside_diameter_m": record.shell_inside_diameter_m,
        "physical_tube_count": record.physical_tube_count,
        "tube_length_m": record.tube_length_m,
        "baffle_spacing_m": record.baffle_spacing_m,
        "nominal_tube_outer_area_m2": record.nominal_tube_outer_area_proxy_m2,
        "task174_status": record.task174_status,
        "rating_request_ready": record.rating_request_ready,
    }


def assess_tube_side_path_completeness(
    case: EngineeringCase,
    spec: TubeLocalLossEngineeringInput | None,
) -> dict[str, Any]:
    if not experimental_engineering_tube_local_loss_enabled(case):
        return {
            "tube_side_path_status": "NOT_APPLICABLE",
            "missing_inputs": [],
        }
    if spec is None:
        return {
            "tube_side_path_status": "ENGINEERING_GEOMETRY_INPUT_REQUIRED",
            "missing_inputs": ["tube_local_loss_engineering specification"],
        }
    present_types = {c.component_type for c in spec.components}
    missing: list[str] = []
    if spec.completeness_declaration == "ENTRANCE_ONLY_ASSUMED":
        missing.append("FULL_TUBE_SIDE_PATH not declared (ENTRANCE_ONLY_ASSUMED)")
        if "EXIT" not in present_types:
            missing.append("tube EXIT local-loss component")
        if "CHANNEL_HEAD" not in present_types:
            missing.append("tube channel head / header flow path")
        for role in ("INLET_NOZZLE", "OUTLET_NOZZLE"):
            missing.append(f"tube {role} with authorized geometry and K source")
    if spec.geometry_basis == "EXPERIMENTAL_ASSUMED_DEMO":
        missing.append("AUTHORIZED_ENGINEERING_INPUT for production path (demo basis only)")
    return {
        "tube_side_path_status": (
            "DEMONSTRATION_ENTRANCE_ONLY"
            if spec.completeness_declaration == "ENTRANCE_ONLY_ASSUMED"
            else "PARTIAL_DECLARED"
        ),
        "geometry_basis": spec.geometry_basis,
        "completeness_declaration": spec.completeness_declaration,
        "declared_component_types": sorted(present_types),
        "missing_inputs": missing,
    }


def assess_shell_side_nozzle_path(case: EngineeringCase) -> dict[str, Any]:
    raw = getattr(case, "shell_hydraulic_path_engineering", None)
    if not raw:
        return {
            "shell_nozzle_path_status": "ENGINEERING_GEOMETRY_INPUT_REQUIRED",
            "missing_inputs": list(REQUIRED_SHELL_NOZZLE_ROLES),
            "note": (
                "Bell–Delaware covers shell-side internal bundle pressure drop only; "
                "inlet/outlet nozzle and shell transitions are not modeled without "
                "shell_hydraulic_path_engineering input."
            ),
        }
    return {
        "shell_nozzle_path_status": "AUTHORIZED_INPUT_PRESENT",
        "declared": raw,
        "missing_inputs": [],
    }


def assess_full_hydraulic_path_input_status(case: EngineeringCase) -> dict[str, Any]:
    spec = engineering_tube_local_loss_input(case)
    tube = assess_tube_side_path_completeness(case, spec)
    shell = assess_shell_side_nozzle_path(case)
    if tube.get("tube_side_path_status") == "DEMONSTRATION_ENTRANCE_ONLY" and shell.get(
        "shell_nozzle_path_status"
    ) == "ENGINEERING_GEOMETRY_INPUT_REQUIRED":
        overall = "DEMONSTRATION_PARTIAL_PATH_ONLY"
    elif shell.get("shell_nozzle_path_status") == "ENGINEERING_GEOMETRY_INPUT_REQUIRED":
        overall = "ENGINEERING_GEOMETRY_INPUT_REQUIRED"
    else:
        overall = "AUTHORIZED_PATH_DECLARED"
    return {
        "FULL_PATH_INPUT_STATUS": overall,
        "tube_side": tube,
        "shell_side": shell,
        "PRODUCTION_DESIGN_APPROVED": False,
        "disclosure": (
            "Demonstration entrance K=0.5 does not grant engineering design approval. "
            "Missing shell nozzle / header geometry must be owner-supplied before full-path sizing."
        ),
    }


def historical_long_baseline_area() -> Decimal:
    return Decimal(R26D_HISTORICAL_LONG_BASELINE_REFERENCE["nominal_tube_outer_area_m2"])
