"""Engineering tube-side local loss geometry binding for live post-pass (R21)."""

from __future__ import annotations

import math
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase
from prototypes.v07_general_rating_sizing_mvp.experimental_transitional_tube_hydraulic import (
    experimental_transitional_tube_hydraulic_enabled,
)

BLOCKER_CODE = "BLOCKED_LOCAL_LOSS_ENGINEERING_GEOMETRY_REQUIRED"

GeometryBasis = Literal["EXPERIMENTAL_ASSUMED_DEMO", "AUTHORIZED_ENGINEERING_INPUT"]
CompletenessDeclaration = Literal["ENTRANCE_ONLY_ASSUMED", "FULL_TUBE_SIDE_PATH"]
ComponentTypeLiteral = Literal[
    "ENTRANCE",
    "EXIT",
    "CHANNEL_HEAD",
    "NOZZLE",
    "CONTRACTION",
    "EXPANSION",
]


class TubeLocalLossEngineeringComponent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=False)

    component_id: str = Field(min_length=1, max_length=64)
    component_type: ComponentTypeLiteral
    loss_coefficient: Decimal
    reference_flow_area_m2: Decimal | None = None
    nozzle_inside_diameter_m: Decimal | None = None
    multiplicity: int = Field(default=1, ge=1, le=32)
    path_sequence_index: int = Field(default=0, ge=0, le=64)
    upstream_reference_plane: str = Field(min_length=3, max_length=128)
    downstream_reference_plane: str = Field(min_length=3, max_length=128)
    flow_direction_assertion: Literal["START_TO_END"] = "START_TO_END"
    loss_coefficient_convention: Literal[
        "K_EQ_IRREVERSIBLE_DELTA_P_OVER_RHO_VREF_SQUARED_OVER_2"
    ] = "K_EQ_IRREVERSIBLE_DELTA_P_OVER_RHO_VREF_SQUARED_OVER_2"
    coefficient_source_id: str = Field(min_length=3, max_length=256)
    coefficient_source_version: str = Field(min_length=1, max_length=64)
    coefficient_source_location: str = Field(min_length=3, max_length=512)
    coefficient_permission_status: Literal["ADMITTED"] = "ADMITTED"
    geometry_evidence_refs: tuple[str, ...] = Field(min_length=1, max_length=8)

    @field_validator("loss_coefficient", "reference_flow_area_m2", "nozzle_inside_diameter_m")
    @classmethod
    def positive_when_present(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return None
        if not value.is_finite() or value <= 0:
            raise ValueError("numeric engineering local-loss fields must be positive")
        return value

    @model_validator(mode="after")
    def area_or_nozzle(self) -> TubeLocalLossEngineeringComponent:
        if self.reference_flow_area_m2 is None and self.nozzle_inside_diameter_m is None:
            raise ValueError(
                "each component requires reference_flow_area_m2 or nozzle_inside_diameter_m"
            )
        if self.reference_flow_area_m2 is not None and self.nozzle_inside_diameter_m is not None:
            raise ValueError("provide reference_flow_area_m2 or nozzle_inside_diameter_m, not both")
        return self


class TubeLocalLossEngineeringInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=False)

    geometry_basis: GeometryBasis
    completeness_declaration: CompletenessDeclaration
    components: tuple[TubeLocalLossEngineeringComponent, ...] = Field(min_length=1, max_length=16)

    @model_validator(mode="after")
    def completeness_policy(self) -> TubeLocalLossEngineeringInput:
        types = {component.component_type for component in self.components}
        if self.completeness_declaration == "FULL_TUBE_SIDE_PATH":
            if "ENTRANCE" not in types or "EXIT" not in types:
                raise ValueError(
                    "FULL_TUBE_SIDE_PATH requires at least one ENTRANCE and one EXIT component"
                )
        elif (
            self.completeness_declaration == "ENTRANCE_ONLY_ASSUMED"
            and self.geometry_basis != "EXPERIMENTAL_ASSUMED_DEMO"
        ):
            raise ValueError("ENTRANCE_ONLY_ASSUMED is allowed only for EXPERIMENTAL_ASSUMED_DEMO")
        return self


def nozzle_flow_area_m2(nozzle_inside_diameter_m: Decimal) -> Decimal:
    area = Decimal(str(math.pi)) * (nozzle_inside_diameter_m / Decimal(2)) ** 2
    return area.quantize(Decimal("0.0000000001"))


def experimental_engineering_tube_local_loss_enabled(case: EngineeringCase) -> bool:
    return bool(getattr(case, "experimental_engineering_tube_local_loss", False))


def engineering_tube_local_loss_input(
    case: EngineeringCase,
) -> TubeLocalLossEngineeringInput | None:
    raw = getattr(case, "tube_local_loss_engineering", None)
    if raw is None:
        return None
    if isinstance(raw, TubeLocalLossEngineeringInput):
        return raw
    if isinstance(raw, dict):
        return TubeLocalLossEngineeringInput.model_validate(raw)
    return None


def validate_engineering_local_loss_activation(case: EngineeringCase) -> list[dict[str, str]]:
    blockers: list[dict[str, str]] = []
    if not experimental_engineering_tube_local_loss_enabled(case):
        return blockers
    if not getattr(case, "experimental_live_thermal_hydraulic_postpass", False):
        blockers.append(
            {
                "code": BLOCKER_CODE,
                "scope": "ENGINEERING_CASE",
                "detail": "experimental_engineering_tube_local_loss requires live post-pass",
            }
        )
    if not experimental_transitional_tube_hydraulic_enabled(case):
        blockers.append(
            {
                "code": BLOCKER_CODE,
                "scope": "ENGINEERING_CASE",
                "detail": (
                    "experimental_engineering_tube_local_loss requires "
                    "R20 transitional tube hydraulics"
                ),
            }
        )
    spec = engineering_tube_local_loss_input(case)
    if spec is None:
        blockers.append(
            {
                "code": BLOCKER_CODE,
                "scope": "ENGINEERING_CASE",
                "detail": "tube_local_loss_engineering specification missing",
            }
        )
    return blockers


def resolved_reference_flow_area_m2(component: TubeLocalLossEngineeringComponent) -> Decimal:
    if component.reference_flow_area_m2 is not None:
        return component.reference_flow_area_m2
    assert component.nozzle_inside_diameter_m is not None
    return nozzle_flow_area_m2(component.nozzle_inside_diameter_m)


def build_task028_component_authorities(
    spec: TubeLocalLossEngineeringInput,
) -> list[dict[str, Any]]:
    authorities: list[dict[str, Any]] = []
    for component in spec.components:
        ref_area = resolved_reference_flow_area_m2(component)
        authorities.append(
            {
                "component_id": component.component_id,
                "component_type": component.component_type,
                "path_sequence_index": component.path_sequence_index,
                "flow_direction_assertion": component.flow_direction_assertion,
                "loss_coefficient": component.loss_coefficient,
                "loss_coefficient_convention": component.loss_coefficient_convention,
                "reference_flow_area_m2": ref_area,
                "multiplicity": component.multiplicity,
                "upstream_reference_plane": component.upstream_reference_plane,
                "downstream_reference_plane": component.downstream_reference_plane,
                "geometry_evidence_refs": list(component.geometry_evidence_refs),
                "coefficient_source_id": component.coefficient_source_id,
                "coefficient_source_version": component.coefficient_source_version,
                "coefficient_source_location": component.coefficient_source_location,
                "coefficient_permission_status": component.coefficient_permission_status,
            }
        )
    return authorities


def engineering_geometry_disclosure(
    case: EngineeringCase,
    spec: TubeLocalLossEngineeringInput,
) -> dict[str, str]:
    areas = [str(resolved_reference_flow_area_m2(c)) for c in spec.components]
    return {
        "engineering_geometry_completeness": spec.completeness_declaration,
        "geometry_basis": spec.geometry_basis,
        "assumed_geometry_status": (
            "EXPERIMENTAL_ASSUMED_GEOMETRY_ONLY"
            if spec.geometry_basis == "EXPERIMENTAL_ASSUMED_DEMO"
            else "AUTHORIZED_ENGINEERING_INPUT"
        ),
        "local_component_count": str(len(spec.components)),
        "local_component_areas_m2": ";".join(areas),
        "local_loss_coefficient_sources": ";".join(
            f"{c.component_id}:{c.coefficient_source_id}@{c.coefficient_source_version}"
            for c in spec.components
        ),
        "tube_equipment_mass_flow_binding": "EQUIPMENT_TOTAL_TUBE_SIDE",
        "task025_parallel_area_binding": "TUBE_BUNDLE_TOTAL_NOT_NOZZLE",
    }


def demo_100mm_entrance_component() -> TubeLocalLossEngineeringComponent:
    """Explicit R21 demo entrance (100 mm ID, K=0.5) — not production equipment data."""
    return TubeLocalLossEngineeringComponent(
        component_id="R21-DEMO-ENTRANCE-100MM",
        component_type="ENTRANCE",
        loss_coefficient=Decimal("0.5"),
        nozzle_inside_diameter_m=Decimal("0.100"),
        multiplicity=1,
        path_sequence_index=0,
        upstream_reference_plane="TUBE_LOCAL_LOSS_START_PLANE",
        downstream_reference_plane="TUBE_INTERNAL_FLOW_START_PLANE",
        coefficient_source_id="R21-EXPERIMENTAL-DEMO-ENTRANCE-K",
        coefficient_source_version="2026-R21",
        coefficient_source_location="HXForge R21 assumed demo scenario (100 mm nozzle, K=0.5)",
        geometry_evidence_refs=("R21-ASSUMED-NOZZLE-100MM-ID-NOT-EQUIPMENT-DESIGN",),
    )


def component_results_disclosure(task028_result: Any) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for component in task028_result.component_results:
        rows.append(
            {
                "component_id": component.component_id,
                "component_type": str(component.component_type.value),
                "reference_flow_area_m2": str(component.reference_flow_area_m2),
                "loss_coefficient": str(component.loss_coefficient),
                "multiplicity": str(component.multiplicity),
                "component_irreversible_pressure_loss_pa": str(
                    component.component_irreversible_pressure_loss_pa
                ),
            }
        )
    return rows
